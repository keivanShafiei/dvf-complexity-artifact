#!/usr/bin/env python3
"""
Incremental GGNI spectral heuristic solver for DVF.

Key changes relative to the original single-pass version:
1. The prescribed displacement u_bar is applied in n_steps increments.
2. The bond-state vector s is carried across increments and updated irreversibly:
      s^{(k+1)}_ij <= s^{(k)}_ij
   so once a bond is severed, it never re-enters the Laplacian.
3. At each increment, the solver logs epistemic diagnostics:
      - spectral gap (lambda2)
      - number of severed bonds
      - total energy
   plus a few auxiliary fields that are useful for debugging and audits.
4. The sparse generalized eigensolver uses the previous increment's Fiedler
   vector as the initial guess v0 to accelerate convergence.

Thermodynamic consistency note
------------------------------
The incremental scheme is history-dependent and damage-irreversible.
This is the discrete analogue of the fracture dissipation inequality:
the update can only remove bonds, never restore them, so the damage
internal variable evolves monotonically and the crack path depends on
the loading history rather than only the terminal load. That is exactly
the behavior needed for a path-dependent variational fracture model.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import scipy.linalg as la
import scipy.sparse as sp
from scipy.sparse.linalg import ArpackNoConvergence, eigsh

from ._common import (
    build_graph_from_npz,
    compute_bond_strain,
    compute_energy,
    get_terminals,
    assemble_stiffness,
    solve_fem,
)


def _build_affinity(
    s: np.ndarray,
    phi: np.ndarray,
    weights: np.ndarray,
    beta: float,
    Gc: float,
) -> np.ndarray:
    """
    Build the bond affinity vector.

    Severed bonds are forced to remain exactly zero in the affinity field.
    This preserves irreversibility at the spectral-graph level, not only in s.
    """
    denom = Gc * weights + 1e-12
    affinity = s.astype(np.float64) * np.exp(-beta * phi / denom)
    affinity[s == 0] = 0.0
    return affinity


def _build_laplacian_from_affinity(
    affinity: np.ndarray,
    edges: np.ndarray,
    n_nodes: int,
) -> Tuple[sp.csr_matrix, sp.csr_matrix]:
    """
    Build the weighted graph Laplacian L and a diagonal regularization of D.

    The small diagonal regularization is only for numerical robustness when the
    graph becomes disconnected or nearly disconnected.
    """
    W = sp.csr_matrix((affinity, (edges[:, 0], edges[:, 1])), shape=(n_nodes, n_nodes))
    W = (W + W.T) * 0.5

    deg = np.asarray(W.sum(axis=1)).ravel()
    D = sp.diags(deg)

    L = D - W

    # Robust diagonal regularization for the generalized eigenproblem.
    # This does not reintroduce affinity on severed bonds; it only prevents
    # singular M matrices when the graph fragments.
    reg = 1e-10 * max(float(deg.max()) if deg.size else 0.0, 1.0)
    deg_reg = deg.copy()
    deg_reg[deg_reg < reg] = reg
    D_reg = sp.diags(deg_reg)

    return L.tocsr(), D_reg.tocsr()


def _compute_fiedler_vector(
    L: sp.csr_matrix,
    D_reg: sp.csr_matrix,
    v0: Optional[np.ndarray],
) -> Tuple[float, np.ndarray]:
    """
    Compute the second generalized eigenpair of L v = lambda D v.

    Parameters
    ----------
    L:
        Weighted Laplacian.
    D_reg:
        Regularized diagonal degree matrix.
    v0:
        Initial guess for eigsh. The previous increment's Fiedler vector is used
        here to accelerate convergence.

    Returns
    -------
    lambda2:
        Second smallest generalized eigenvalue.
    fiedler:
        Associated eigenvector. If the solve fails, returns zeros safely.
    """
    n = L.shape[0]
    if n < 3:
        return 0.0, np.zeros(n, dtype=np.float64)

    if v0 is not None:
        v0 = np.asarray(v0, dtype=np.float64).reshape(-1)
        if v0.shape[0] != n or not np.all(np.isfinite(v0)):
            v0 = None
        elif np.linalg.norm(v0) > 0:
            v0 = v0 / np.linalg.norm(v0)
        else:
            v0 = None

    try:
        # Generalized sparse eigenproblem:
        #     L v = lambda D v
        # where the previous Fiedler vector is passed as v0.
        vals, vecs = eigsh(
            L,
            M=D_reg,
            k=2,
            which="SM",
            v0=v0,
            tol=1e-8,
        )
        order = np.argsort(vals)
        lambda2 = float(vals[order[1]])
        fiedler = np.asarray(vecs[:, order[1]], dtype=np.float64)
        
        # Sign alignment for stability
        if v0 is not None and np.dot(fiedler, v0) < 0:
            fiedler = -fiedler
            
        return lambda2, fiedler
    except (ArpackNoConvergence, RuntimeError, ValueError):
        # Dense fallback for robustness on small or difficult instances.
        try:
            vals, vecs = la.eigh(L.toarray(), D_reg.toarray())
            order = np.argsort(vals)
            if len(order) < 2:
                return 0.0, np.zeros(n, dtype=np.float64)
            lambda2 = float(vals[order[1]])
            fiedler = np.asarray(vecs[:, order[1]], dtype=np.float64)
            
            # Sign alignment for stability
            if v0 is not None and np.dot(fiedler, v0) < 0:
                fiedler = -fiedler
                
            return lambda2, fiedler
        except Exception:
            return 0.0, np.zeros(n, dtype=np.float64)


def run_incremental_ggni(
    graph_path: str,
    beta: float,
    tau: float,
    Gc: float,
    u_bar: float,
    n_steps: int = 1,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Run incremental GGNI fracture evolution with irreversible bond damage.

    Parameters
    ----------
    graph_path:
        Path to the .npz graph file.
    beta, tau, Gc, u_bar:
        Standard GGNI parameters.
    n_steps:
        Number of displacement increments. A value of 1 reproduces the original
        terminal-load single-pass behavior.

    Returns
    -------
    result:
        Final solver summary suitable for the existing JSON output.
    trace:
        Per-increment epistemic trace records.
    """
    if n_steps < 1:
        raise ValueError("n_steps must be >= 1")

    data = np.load(graph_path)
    edges, weights, stiffness, coords = build_graph_from_npz(data)
    s_nodes, t_nodes = get_terminals(data, coords)

    N = len(coords)
    M = len(edges)
    n_dofs = 2 * N

    # Damage state: 1 = intact, 0 = severed.
    # This vector is updated irreversibly across increments.
    s = np.ones(M, dtype=np.int8)

    trace: List[Dict[str, Any]] = []
    fiedler_prev: Optional[np.ndarray] = None

    t0 = time.time()

    u = np.zeros(n_dofs, dtype=np.float64)
    lambda2 = 0.0

    # Incremental displacement ramp.
    for step in range(1, n_steps + 1):
        u_bar_step = float(u_bar) * step / float(n_steps)
        load_factor = float(step) / float(n_steps)
        
        n_severed_start = int(np.count_nonzero(s == 0))

        # At each load increment, we allow an inner damage-relaxation loop.
        # This captures stress redistribution at fixed external load until the
        # bond set becomes stable for this increment.
        for _ in range(M):
            K = assemble_stiffness(edges, s, stiffness, coords)
            u = solve_fem(K, s_nodes, t_nodes, u_bar_step, n_dofs)

            # Bond strain energy under the current equilibrium displacement.
            phi = compute_bond_strain(u, edges, stiffness, coords)

            # Affinity is zero on broken bonds by construction.
            affinity = _build_affinity(s, phi, weights, beta=beta, Gc=Gc)

            # Graph Laplacian and spectral diagnostics.
            L, D_reg = _build_laplacian_from_affinity(affinity, edges, N)
            lambda2, fiedler = _compute_fiedler_vector(L, D_reg, fiedler_prev)

            spec_grad = np.abs(fiedler[edges[:, 0]] - fiedler[edges[:, 1]])
            max_g = float(spec_grad.max()) if spec_grad.size else 0.0
            threshold = tau * max_g if max_g > 0.0 else 0.0
            spectral_cut = spec_grad > threshold

            # Griffith criterion at the current equilibrium state.
            energy_cut = phi > (Gc * weights)

            # Irreversible damage update:
            # only intact bonds can be severed, and broken bonds remain broken.
            newly_broken = np.where((s == 1) & spectral_cut & energy_cut)[0]
            if newly_broken.size == 0:
                # Stable damage state for this increment.
                fiedler_prev = fiedler
                break

            s[newly_broken] = 0
            fiedler_prev = fiedler

            # The loop continues with the updated damage state and the same
            # external displacement u_bar_step, allowing redistribution before
            # advancing to the next increment.

        # Recompute the converged state for this increment after the final
        # irreversible update, ensuring the logged energy is the energy of the
        # stable post-damage equilibrium at this load level.
        K = assemble_stiffness(edges, s, stiffness, coords)
        u = solve_fem(K, s_nodes, t_nodes, u_bar_step, n_dofs)
        phi = compute_bond_strain(u, edges, stiffness, coords)
        affinity = _build_affinity(s, phi, weights, beta=beta, Gc=Gc)
        L, D_reg = _build_laplacian_from_affinity(affinity, edges, N)
        lambda2, fiedler_prev = _compute_fiedler_vector(L, D_reg, fiedler_prev)

        E_total, E_elastic, E_fracture = compute_energy(
            u, s, edges, weights, stiffness, coords, Gc
        )
        
        n_severed_end = int(np.count_nonzero(s == 0))
        newly_severed = n_severed_end - n_severed_start

        trace.append(
            {
                "step": int(step),
                "load_factor": load_factor,
                "u_bar": float(u_bar_step),
                "state": "stable" if lambda2 > 1e-6 else "degenerate",
                "lambda2": float(lambda2),
                "n_severed": n_severed_end,
                "newly_severed": newly_severed,
                "total_energy": float(E_total),
                "elastic_energy": float(E_elastic),
                "fracture_energy": float(E_fracture),
                "mean_phi": float(phi.mean()) if phi.size else 0.0,
                "mean_affinity": float(affinity.mean()) if affinity.size else 0.0,
            }
        )

    t1 = time.time()

    severed = np.where(s == 0)[0].tolist()
    E_total, E_elastic, E_fracture = compute_energy(
        u, s, edges, weights, stiffness, coords, Gc
    )

    result = {
        "solver": "ggni",
        "n_steps": int(n_steps),
        "energy": float(E_total),
        "fracture_energy": float(E_fracture),
        "elastic_energy": float(E_elastic),
        "severed_bonds": sorted(severed),
        "spectral_gap": float(lambda2),
        "runtime": float(t1 - t0),
        "note": (
            "Incremental GGNI with irreversible damage: "
            "u_bar is ramped over n_steps, severed bonds remain zero affinity, "
            "and the previous Fiedler vector is used as eigsh v0."
        ),
    }

    return result, trace


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--graph", required=True)
    p.add_argument("--beta", type=float, default=4.0)
    p.add_argument("--tau", type=float, default=0.15)
    p.add_argument("--Gc", type=float, default=1.0)
    p.add_argument("--u_bar", type=float, default=5.0)
    p.add_argument(
        "--n_steps",
        type=int,
        default=1,
        help="Number of incremental load steps (default: 1 for backward compatibility).",
    )
    p.add_argument("--out", required=True)
    p.add_argument("--trace", required=True)
    args = p.parse_args()

    result, trace = run_incremental_ggni(
        graph_path=args.graph,
        beta=args.beta,
        tau=args.tau,
        Gc=args.Gc,
        u_bar=args.u_bar,
        n_steps=args.n_steps,
    )

    out_path = Path(args.out)
    trace_path = Path(args.trace)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w") as f:
        json.dump(result, f, indent=2)

    with trace_path.open("w") as f:
        json.dump(trace, f, indent=2)


if __name__ == "__main__":
    main()

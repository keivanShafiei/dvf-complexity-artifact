
"""Alternating minimization baseline (faithful gradient-like descent).

Loop:
  u^{k+1} = argmin_u E(u, s^k)       -> FEM solve
  s^{k+1}_ij = 1[phi_ij(u^{k+1}) <= Gc * w_ij]   -> closed-form Griffith

Remark rem:algorithmic_implications (NP-hardness and local minima) predicts this scheme gets trapped in a local minimum
of the non-convex landscape.

NOTE: This is a GREEDY coordinate-wise descent on s (equivalent to
gradient descent on the relaxed indicator), NOT a mock. The "all
bonds broken" outcome emerges dynamically from the iteration when
the elastic energy released exceeds the fracture penalty everywhere.
"""
import argparse, json, time, os
import numpy as np
from ._common import (build_graph_from_npz, get_terminals,
                     assemble_stiffness, solve_fem,
                     compute_bond_strain, compute_energy)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--graph", required=True)
    p.add_argument("--Gc", type=float, default=1.0)
    p.add_argument("--u_bar", type=float, default=5.0)
    p.add_argument("--max_iter", type=int, default=50)
    p.add_argument("--tol", type=float, default=1e-8)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    data = np.load(args.graph)
    edges, weights, stiffness, coords = build_graph_from_npz(data)
    s_nodes, t_nodes = get_terminals(data, coords)
    N = len(coords)
    M = len(edges)
    n_dofs = 2 * N

    s = np.ones(M, dtype=int)
    t0 = time.time()
    K = assemble_stiffness(edges, s, stiffness, coords)
    u = solve_fem(K, s_nodes, t_nodes, args.u_bar, n_dofs)
    E_prev, _, _ = compute_energy(u, s, edges, weights, stiffness, coords, args.Gc)

    iterations = 0
    for it in range(args.max_iter):
        iterations = it + 1
        # Step 1: s update (closed-form Griffith at fixed u)
        phi = compute_bond_strain(u, edges, stiffness, coords)
        s_new = (phi <= args.Gc * weights).astype(int)
        # Step 2: u update (FEM at fixed s)
        K = assemble_stiffness(edges, s_new, stiffness, coords)
        u_new = solve_fem(K, s_nodes, t_nodes, args.u_bar, n_dofs)
        E_new, _, _ = compute_energy(u_new, s_new, edges, weights, stiffness, coords, args.Gc)
        # Monotonicity check (should always hold for proper alternating min)
        if E_new > E_prev + 1e-10:
            # safeguard: keep previous state
            break
        if abs(E_prev - E_new) < args.tol and np.array_equal(s, s_new):
            s, u, E_prev = s_new, u_new, E_new
            break
        s, u, E_prev = s_new, u_new, E_new
    t1 = time.time()

    E_total, E_elastic, E_fracture = compute_energy(
        u, s, edges, weights, stiffness, coords, args.Gc
    )
    severed = np.where(s == 0)[0].tolist()
    result = {
        "solver": "gd",
        "energy": E_total,
        "fracture_energy": E_fracture,
        "elastic_energy": E_elastic,
        "severed_bonds": sorted(severed),
        "iterations": iterations,
        "runtime": float(t1 - t0),
        "note": "Alternating minimization (local minimum trap per Remark rem:algorithmic_implications (NP-hardness and local minima))."
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)

if __name__ == "__main__":
    main()

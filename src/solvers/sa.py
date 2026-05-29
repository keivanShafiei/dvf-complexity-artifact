#!/usr/bin/env python3
"""Simulated Annealing with Griffith-aware bond selection and irreversibility."""
import argparse, json, time, os, sys
import numpy as np
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.solvers._common import (build_graph_from_npz, get_terminals,
                                  assemble_stiffness, solve_fem,
                                  compute_bond_strain, compute_energy)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--graph", required=True)
    p.add_argument("--Gc", type=float, default=1.0)
    p.add_argument("--u_bar", type=float, default=1.5)
    p.add_argument("--T0", type=float, default=0.5)
    p.add_argument("--Tmin", type=float, default=0.01)
    p.add_argument("--alpha", type=float, default=0.95)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    np.random.seed(args.seed)

    data = np.load(args.graph)
    edges, weights, stiffness, coords = build_graph_from_npz(data)
    s_nodes, t_nodes = get_terminals(data, coords)
    N = len(coords); M = len(edges); n_dofs = 2 * N

    s = np.ones(M, dtype=int)
    K = assemble_stiffness(edges, s, stiffness, coords)
    u = solve_fem(K, s_nodes, t_nodes, args.u_bar, n_dofs)
    E_curr, _, _ = compute_energy(u, s, edges, weights, stiffness, coords, args.Gc)
    s_best, u_best, E_best = s.copy(), u.copy(), E_curr

    T = args.T0
    iters = 0; accepts = 0
    t0 = time.time()
    
    while T > args.Tmin:
        steps = max(20, M // 5)
        for _ in range(steps):
            iters += 1
            
            # Compute Griffith criterion for all intact bonds
            phi = compute_bond_strain(u, edges, stiffness, coords)
            griffith_ratio = phi / (args.Gc * weights + 1e-12)
            
            # Only consider intact bonds with phi > 0.5 * Gc * w
            candidates = np.where((s == 1) & (griffith_ratio > 0.5))[0]
            if len(candidates) == 0:
                break
            
            # Select bond with probability proportional to Griffith ratio
            probs = griffith_ratio[candidates]
            probs = probs / probs.sum()
            idx = np.random.choice(candidates, p=probs)
            
            # Try breaking this bond
            s_trial = s.copy()
            s_trial[idx] = 0
            K_trial = assemble_stiffness(edges, s_trial, stiffness, coords)
            u_trial = solve_fem(K_trial, s_nodes, t_nodes, args.u_bar, n_dofs)
            E_trial, _, _ = compute_energy(u_trial, s_trial, edges, weights, stiffness, coords, args.Gc)
            
            dE = E_trial - E_curr
            if dE <= 0 or np.random.rand() < np.exp(-dE / T):
                s, u, E_curr = s_trial, u_trial, E_trial
                accepts += 1
                if E_curr < E_best:
                    E_best = E_curr
                    s_best = s.copy()
                    u_best = u.copy()
        T *= args.alpha
    t1 = time.time()

    # FIX: Pass u_best as first argument to compute_energy
    E_tot, E_el, E_fr = compute_energy(u_best, s_best, edges, weights, stiffness, coords, args.Gc)
    severed = np.where(s_best == 0)[0].tolist()
    result = {
        "solver": "sa",
        "energy": E_tot,
        "fracture_energy": E_fr,
        "elastic_energy": E_el,
        "severed_bonds": sorted(severed),
        "iterations": iters,
        "acceptance_rate": float(accepts / max(1, iters)),
        "runtime": float(t1 - t0),
        "note": "Griffith-aware SA with irreversibility constraint."
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)

if __name__ == "__main__":
    main()

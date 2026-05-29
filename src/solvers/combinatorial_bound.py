
"""Combinatorial upper bound under relaxed kinematics.
1. Find min-cut partition (S, T) -> define s_ij (cut = severed).
2. Fix s, solve FEM for u freely in R^{N x d} with Dirichlet BCs.
3. Compute E_elastic(u, s) + E_fracture(s).

Because s is fixed to the rigid-optimal cut but u is allowed to
relax, E_elastic can be lower than in the rigid case (often 0 for
disconnected components). This is the fair combinatorial baseline
against which SA / GGNI / GD must be compared in relaxed kinematics.
"""
import argparse, json, time, os
import numpy as np
from ._common import (build_graph_from_npz, get_terminals,
                     build_nx_graph_for_mincut, assemble_stiffness,
                     solve_fem, compute_energy)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--graph", required=True)
    p.add_argument("--Gc", type=float, default=1.0)
    p.add_argument("--u_bar", type=float, default=5.0)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    data = np.load(args.graph)
    edges, weights, stiffness, coords = build_graph_from_npz(data)
    s_nodes, t_nodes = get_terminals(data, coords)
    N = len(coords)
    n_dofs = 2 * N
    M = len(edges)

    # Step 1: min-cut
    G, super_s, super_t = build_nx_graph_for_mincut(edges, weights, s_nodes, t_nodes, args.Gc)
    t0 = time.time()
    cut_value, (S, T) = nx_minimum_cut(G, super_s, super_t)

    # Step 2: s from partition
    s = np.ones(M, dtype=int)
    for u, v, d in G.edges(data=True):
        if "idx" in d:
            if (u in S and v in T) or (u in T and v in S):
                s[d["idx"]] = 0

    # Step 3: FEM solve with this s (u free)
    K = assemble_stiffness(edges, s, stiffness, coords)
    u = solve_fem(K, s_nodes, t_nodes, args.u_bar, n_dofs)
    E_total, E_elastic, E_fracture = compute_energy(
        u, s, edges, weights, stiffness, coords, args.Gc
    )
    t1 = time.time()

    severed = np.where(s == 0)[0].tolist()
    result = {
        "solver": "combinatorial_bound",
        "energy": E_total,
        "fracture_energy": E_fracture,
        "elastic_energy": E_elastic,
        "severed_bonds": sorted(severed),
        "cut_value": float(cut_value),
        "runtime": float(t1 - t0),
        "note": "Upper bound on relaxed optimum: min-cut topology + free FEM u."
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)

def nx_minimum_cut(G, s, t):
    import networkx as nx
    return nx.minimum_cut(G, s, t, capacity="capacity")

if __name__ == "__main__":
    main()


"""Mincut under rigid-block kinematics.
Implements Proposition 5.1: when u_i in {0, u_bar} (piecewise constant
on the partition), E_h reduces to Gc * sum (1-s_ij)*w_ij over cut edges,
which is exactly minimum s-t cut with capacities Gc*w_ij.

Output: pure fracture energy, no elastic relaxation, no u field.
"""
import argparse, json, time, os
import numpy as np
from ._common import (build_graph_from_npz, get_terminals,
                     build_nx_graph_for_mincut)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--graph", required=True)
    p.add_argument("--Gc", type=float, default=1.0)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    data = np.load(args.graph)
    edges, weights, stiffness, coords = build_graph_from_npz(data)
    s_nodes, t_nodes = get_terminals(data, coords)
    G, super_s, super_t = build_nx_graph_for_mincut(edges, weights, s_nodes, t_nodes, args.Gc)

    t0 = time.time()
    cut_value, (S, T) = nx_minimum_cut(G, super_s, super_t)
    t1 = time.time()

    severed = []
    for u, v, d in G.edges(data=True):
        if "idx" in d:
            if (u in S and v in T) or (u in T and v in S):
                severed.append(d["idx"])

    result = {
        "solver": "mincut_rigid",
        "energy": float(cut_value),
        "fracture_energy": float(cut_value),
        "elastic_energy": 0.0,
        "severed_bonds": sorted(severed),
        "runtime": float(t1 - t0),
        "note": "Exact min-cut under rigid-block kinematics (Prop 5.1). "
                "This is an UPPER BOUND on the relaxed-kinematics optimum."
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)

def nx_minimum_cut(G, s, t):
    import networkx as nx
    return nx.minimum_cut(G, s, t, capacity="capacity")

if __name__ == "__main__":
    main()

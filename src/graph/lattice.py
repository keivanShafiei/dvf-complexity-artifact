import numpy as np
import argparse
import os

def generate_lattice(n, out):
    N = n * n
    # FIX C5: Generate and save coordinates
    coords = np.array([[i, j] for j in range(n) for i in range(n)], dtype=float)
    edges = []
    for j in range(n):
        for i in range(n):
            idx = j * n + i
            if i < n - 1: edges.append([idx, idx + 1])
            if j < n - 1: edges.append([idx, idx + n])
    edges = np.array(edges, dtype=int)
    M = len(edges)
    w = np.ones(M)
    K = np.ones(M)
    
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    np.savez(out, edges=edges, w=w, K=K, n=N, coords=coords)
    print(f"Generated lattice: {N} nodes, {M} edges -> {out}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    generate_lattice(args.n, args.out)

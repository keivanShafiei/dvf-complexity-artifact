#!/usr/bin/env python3
"""
Run parameter sensitivity sweep for GGNI.
Generates experiments/data/results/sensitivity_heatmap.npy
"""
import argparse
import subprocess
import json
import numpy as np
from pathlib import Path


def run_sweep(graph_path: str, out_path: str):
    """Run parameter sweep over beta and tau_spec."""
    beta_values = [2.0, 4.0, 6.0, 8.0]
    tau_values = [0.05, 0.10, 0.15, 0.20, 0.30]
    
    # Reference energy (Min-Cut optimal)
    ref_energy = 1.967  # Geometria_Transfinita
    
    results = np.zeros((len(beta_values), len(tau_values)))
    
    for i, beta in enumerate(beta_values):
        for j, tau in enumerate(tau_values):
            print(f"Running β={beta}, τ={tau}...", end=" ")
            
            out_json = f"/tmp/sweep_{beta}_{tau}.json"
            trace_json = f"/tmp/sweep_{beta}_{tau}_trace.json"
            
            cmd = [
                "python", "-m", "src.solvers.ggni",
                "--graph", graph_path,
                "--beta", str(beta),
                "--tau", str(tau),
                "--Gc", "1.0",
                "--u_bar", "5.0",
                "--n_steps", "20",
                "--out", out_json,
                "--trace", trace_json
            ]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                with open(out_json) as f:
                    result = json.load(f)
                energy = result["energy"]
                ratio = energy / ref_energy
                results[i, j] = ratio
                print(f"E_h = {energy:.3f}, Ratio = {ratio:.2f}×")
            except Exception as e:
                print(f"ERROR: {e}")
                results[i, j] = np.nan
    
    np.save(out_path, results)
    print(f"✅ Heatmap data saved to {out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    
    run_sweep(args.graph, args.out)


if __name__ == "__main__":
    main()

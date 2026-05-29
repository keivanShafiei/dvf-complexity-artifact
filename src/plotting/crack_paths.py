#!/usr/bin/env python3
"""Plot crack paths for all 5 solvers on a given mesh"""
import argparse
import json
import numpy as np
import matplotlib.pyplot as plt

def load_results(paths):
    results = {}
    for name, path in paths.items():
        with open(path) as f:
            results[name] = json.load(f)
    return results

def plot_crack_paths(graph_path, results, output_path):
    data = np.load(graph_path)
    coords = data['coords']
    edges = data['edges']
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()
    
    solver_names = ['mincut', 'comb', 'ggni', 'gd', 'sa']
    titles = ['Min-Cut (Rigid)', 'Combinatorial Bound', 'GGNI (Spectral)', 
              'Gradient Descent', 'Simulated Annealing']
    
    for idx, (solver, title) in enumerate(zip(solver_names, titles)):
        if solver not in results:
            continue
            
        ax = axes[idx]
        result = results[solver]
        severed = set(result.get('severed_bonds', []))
        
        # رسم یال‌های سالم
        for i, (u, v) in enumerate(edges):
            color = 'red' if i in severed else 'lightgray'
            width = 2.0 if i in severed else 0.5
            ax.plot([coords[u, 0], coords[v, 0]], 
                   [coords[u, 1], coords[v, 1]], 
                   color=color, linewidth=width, alpha=0.6)
        
        ax.set_title(f'{title}\nE={result["energy"]:.2f}, {len(severed)} cuts')
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
    
    # حذف subplot خالی
    axes[-1].axis('off')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--graph', required=True)
    parser.add_argument('--mincut', required=True)
    parser.add_argument('--comb', required=True)
    parser.add_argument('--ggni', required=True)
    parser.add_argument('--gd', required=True)
    parser.add_argument('--sa', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    
    paths = {
        'mincut': args.mincut,
        'comb': args.comb,
        'ggni': args.ggni,
        'gd': args.gd,
        'sa': args.sa
    }
    
    results = load_results(paths)
    plot_crack_paths(args.graph, results, args.out)
    print(f"✅ Crack paths plot saved: {args.out}")

if __name__ == '__main__':
    main()

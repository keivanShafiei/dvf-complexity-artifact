#!/usr/bin/env python3
"""Plot energy decomposition for all 5 solvers"""
import argparse
import json
import matplotlib.pyplot as plt
import numpy as np

def load_results(paths):
    results = {}
    for name, path in paths.items():
        with open(path) as f:
            results[name] = json.load(f)
    return results

def plot_energy_comparison(results, output_path):
    solvers = ['mincut', 'comb', 'ggni', 'gd', 'sa']
    labels = ['Min-Cut\n(Rigid)', 'Combinatorial\nBound', 'GGNI\n(Spectral)', 
              'Gradient\nDescent', 'Simulated\nAnnealing']
    
    energies = []
    elastic = []
    fracture = []
    
    for solver in solvers:
        if solver in results:
            energies.append(results[solver]['energy'])
            elastic.append(results[solver].get('elastic_energy', 0))
            fracture.append(results[solver].get('fracture_energy', 0))
        else:
            energies.append(0)
            elastic.append(0)
            fracture.append(0)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x = np.arange(len(solvers))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, elastic, width, label='Elastic Energy', color='#2ca02c')
    bars2 = ax.bar(x + width/2, fracture, width, label='Fracture Energy', color='#d62728')
    
    # اضافه کردن مقدار عددی روی هر bar
    for bar in bars1:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2f}', ha='center', va='bottom', fontsize=8)
    
    for bar in bars2:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2f}', ha='center', va='bottom', fontsize=8)
    
    ax.set_xlabel('Solver')
    ax.set_ylabel('Energy')
    ax.set_title('Energy Decomposition by Solver')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

def main():
    parser = argparse.ArgumentParser()
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
    plot_energy_comparison(results, args.out)
    print(f"✅ Energy comparison plot saved: {args.out}")

if __name__ == '__main__':
    main()

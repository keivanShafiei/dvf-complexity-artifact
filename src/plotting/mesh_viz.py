
import argparse, numpy as np, json, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh_graph", required=True)
    parser.add_argument("--results", nargs='+', required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    data = np.load(args.mesh_graph)
    edges, coords = data['edges'], data['coords']
    
    fig, axes = plt.subplots(1, len(args.results), figsize=(6 * len(args.results), 5))
    if len(args.results) == 1: axes = [axes]

    for ax, res_path in zip(axes, args.results):
        with open(res_path) as f: res = json.load(f)
        
        solver_name = res.get('solver', 'Unknown').replace('_', ' ').title()
        energy = res.get('energy', 0.0)
        severed = set(res.get('severed_bonds', []))
        
        intact_count = len(edges) - len(severed)

        # رسم پیوندهای سالم
        for i, (u, v) in enumerate(edges):
            if i not in severed:
                ax.plot([coords[u, 0], coords[v, 0]], [coords[u, 1], coords[v, 1]], 
                        color='lightgray', linewidth=0.8, zorder=1)
        
        # رسم پیوندهای شکسته (مسیر ترک)
        if len(severed) > 0 and intact_count > 0:
            # رسم ترک‌های نرمال
            for i in severed:
                u, v = edges[i]
                ax.plot([coords[u, 0], coords[v, 0]], [coords[u, 1], coords[v, 1]], 
                        color='red', linewidth=1.5, zorder=2)
        elif intact_count == 0 or len(severed) > 0.8 * len(edges):
            # حالت Over-fragmentation (مثل GD در Geometria_Physical)
            ax.text(0.5, 0.5, "Complete\nFragmentation\n(Local Min Trap)", 
                    transform=ax.transAxes, ha='center', va='center', 
                    fontsize=11, color='darkred', fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="darkred", alpha=0.9))
            # رسم کمرنگ تمام پیوندها به عنوان ترک
            for i, (u, v) in enumerate(edges):
                ax.plot([coords[u, 0], coords[v, 0]], [coords[u, 1], coords[v, 1]], 
                        color='red', linewidth=0.3, alpha=0.2, zorder=1)

        ax.set_title(f"{solver_name}\n$E_h = {energy:.3f}$", fontsize=12, fontweight='bold')
        ax.set_aspect('equal')
        ax.axis('off')

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    plt.tight_layout()
    plt.savefig(args.out, dpi=300, bbox_inches="tight")
    plt.close()

if __name__ == "__main__":
    main()

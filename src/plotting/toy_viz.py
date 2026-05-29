
import argparse, json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mf", required=True)
    parser.add_argument("--ggni", required=True)
    parser.add_argument("--gd", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    with open(args.mf) as f: mf = json.load(f)
    with open(args.ggni) as f: ggni = json.load(f)
    with open(args.gd) as f: gd = json.load(f)

    # استخراج نام دیتاست از مسیر فایل
    dataset_name = os.path.basename(args.mf).split('_maxflow')[0]
    is_real_mesh = not dataset_name.startswith("lsn")

    fig, ax = plt.subplots(figsize=(8, 5))
    solvers = ["Max-Flow\n(Exact)", "GGNI\n(Spectral)", "Gradient\nDescent"]
    energies = [mf["energy"], ggni["energy"], gd["energy"]]
    
    colors = ["#2ca02c", "#1f77b4", "#d62728"] # سبز برای بهینه، آبی برای هیوریستیک، قرمز برای GD
    bars = ax.bar(solvers, energies, color=colors, edgecolor="black", linewidth=1.2, width=0.6)
    
    # اضافه کردن خطوط راهنما
    opt_energy = mf["energy"]
    ax.axhline(y=opt_energy, color="gray", linestyle="--", alpha=0.8, linewidth=1.5, label=f"Global Optimum ($E^* = {opt_energy:.2f}$)")
    
    # نوشتن مقادیر روی میله‌ها
    for bar, energy in zip(bars, energies):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.5, 
                f'{energy:.2f}', ha='center', va='bottom', fontweight='bold', fontsize=11)

    title = f"Energy Decomposition on {'Real Unstructured Mesh' if is_real_mesh else 'Structured Lattice'} ({dataset_name})"
    ax.set_ylabel("Total Energy ($E_h$)", fontsize=12, fontweight='bold')
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(fontsize=11, loc='upper left')
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', linestyle=':', alpha=0.6)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    plt.tight_layout()
    plt.savefig(args.out, dpi=300, bbox_inches="tight")
    plt.close()

if __name__ == "__main__":
    main()

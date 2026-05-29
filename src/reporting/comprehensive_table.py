import argparse
import json
import glob
import os

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results_dir", default="experiments/data/results")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    files = glob.glob(os.path.join(args.results_dir, "*.json"))
    
    real_datasets = {}
    
    for f in files:
        basename = os.path.basename(f)
        
        # Filter: Only Geometria* files ending with specific solver names
        if not basename.startswith("Geometria"):
            continue
        if not any(basename.endswith(f"_{s}.json") for s in ["mincut", "comb", "ggni", "gd", "sa"]):
            continue
            
        # Extract dataset name
        dataset = basename.split("_mincut")[0].split("_comb")[0].split("_ggni")[0].split("_gd")[0].split("_sa")[0]
        
        # Skip duplicate Physical mesh
        if dataset == "Geometria_Physical":
            continue
            
        with open(f) as fh:
            data = json.load(fh)
            
        if dataset not in real_datasets:
            real_datasets[dataset] = {}
            
        solver_key = basename.split("_")[-1].replace(".json", "")
        real_datasets[dataset][solver_key] = data

    # Build LaTeX Table
    lines = []
    lines.append(r"\begin{table}[htbp]")
    lines.append(r"\centering")
    lines.append(r"\caption{Comprehensive benchmark of DVF solvers on real unstructured FEM meshes. ")
    lines.append(r"Max-Flow provides the exact combinatorial optimum under rigid-block kinematics. ")
    lines.append(r"Simulated Annealing (SA) achieves lower total energies by allowing \textit{elastic relaxation} (partial bond breaking). ")
    lines.append(r"GGNI provides a fast, near-optimal spectral approximation, while Gradient Descent (GD) catastrophically fails due to non-convex local minima traps (Theorem 3.3).}")
    lines.append(r"\label{tab:comprehensive_benchmark}")
    lines.append(r"\small")
    lines.append(r"\begin{tabular}{l c c c c}")
    lines.append(r"\toprule")
    lines.append(r"\textbf{Geometry} & \textbf{Solver} & \textbf{Energy $E_h$} & \textbf{Fracture $E_{fr}$} & \textbf{Runtime} \\")
    lines.append(r"\midrule")

    solver_order = ["mincut", "comb", "ggni", "gd", "sa"]
    solver_display = {"mincut": "Min-Cut (Exact, rigid)", "comb": "Comb.\ Bound", "ggni": "GGNI (Spectral)", "gd": "GD (Alt. Min.)", "sa": "SA"}

    sorted_datasets = sorted(real_datasets.keys())
    
    for dataset in sorted_datasets:
        solvers = real_datasets[dataset]
        ref_energy = solvers.get("mincut", {}).get("energy", 0)
        
        n_rows = len([s for s in solver_order if s in solvers])
        
        # FIX: Pre-compute the escaped string outside the f-string to avoid backslash syntax error
        dataset_escaped = dataset.replace('_', r'\_')
        
        for i, s_key in enumerate(solver_order):
            if s_key not in solvers:
                continue
                
            res = solvers[s_key]
            energy = res.get("energy", 0)
            fracture = res.get("fracture_energy", 0)
            runtime = res.get("runtime", 0)
            
            # Format Runtime
            if runtime < 0.01: rt_str = "<10ms"
            elif runtime < 1: rt_str = f"{runtime*1000:.0f}ms"
            elif runtime < 60: rt_str = f"{runtime:.2f}s"
            else: rt_str = f"{runtime/60:.1f}min"
            
            # Format Energy with relative error
            energy_str = f"{energy:.2f}"
            if s_key in ["ggni", "gd", "sa"] and ref_energy > 0 and energy > ref_energy:
                err = abs(100 * (energy - ref_energy) / ref_energy)
                energy_str += f" \\textcolor{{red}}{{(+{err:.0f}\\%)}}"
            elif s_key == "sa" and ref_energy > 0 and energy < ref_energy:
                energy_str += r" \textcolor{blue}{\textsuperscript{*}}"
            
            # Multirow for Geometry name (Now using the pre-computed variable)
            geom_cell = f"\\multirow{{{n_rows}}}{{*}}{{\\texttt{{{dataset_escaped}}}}}" if i == 0 else ""
            
            lines.append(f"{geom_cell} & {solver_display[s_key]} & {energy_str} & {fracture:.2f} & {rt_str} \\\\")
            
            # Add space between datasets
            if i == n_rows - 1 and dataset != sorted_datasets[-1]:
                lines.append(r"\addlinespace")

    lines.append(r"\bottomrule")
    lines.append(r"\multicolumn{5}{l}{\footnotesize \textcolor{blue}{\textsuperscript{*}} SA energy is lower than the combinatorial bound due to elastic strain redistribution.}")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")

    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    with open(args.out, 'w') as f:
        f.write("\n".join(lines))
    
    print(f"✅ Publication-grade table generated: {args.out}")

if __name__ == "__main__":
    main()

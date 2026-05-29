
import argparse
import json
import os

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    # Organize by (solver, k)
    results = {}
    for path in args.inputs:
        with open(path) as f:
            data = json.load(f)
        solver = data["solver"]
        k = data["k"]
        if solver not in results:
            results[solver] = {}
        results[solver][k] = data["energy"]

    # Build LaTeX rows
    rows = []
    solver_order = ["maxflow", "ggni", "gd"]
    solver_names = {"maxflow": "Max-Flow (Exact)", 
                    "ggni": "GGNI (Spectral)", 
                    "gd": "Gradient Descent"}
    
    for s in solver_order:
        if s in results:
            e2 = results[s].get(2, "—")
            e3 = results[s].get(3, "—")
            e2_str = f"{e2:.2f}" if isinstance(e2, (int, float)) else str(e2)
            e3_str = f"{e3:.2f}" if isinstance(e3, (int, float)) else str(e3)
            rows.append(f"{solver_names[s]} & {e2_str} & {e3_str} \\\\")

    latex = r"""\begin{tabular}{lcc}
\toprule
Method & k=2 & k=3 \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}"""

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(latex)
    print(f"📜 LaTeX table saved: {args.out}")

if __name__ == "__main__":
    main()

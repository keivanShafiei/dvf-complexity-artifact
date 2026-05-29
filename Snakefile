from snakemake.utils import min_version
min_version("7.32.0")

configfile: "experiments/configs/paper_final.yaml"

DATASET = config.get("dataset", "")

if DATASET:
    TARGETS = [
        "figures/" + DATASET + "_fracture.pdf",
        "artifact/reproducibility_manifest.json"
    ]
else:
    TARGETS = [
        "figures/toy_model_crack_paths.pdf",
        "figures/complexity_scaling.pdf",
        "tables/toy_model_results.tex",
        "artifact/reproducibility_manifest.json"
    ]

rule all:
    input:
        # Toy model results
        "experiments/data/results/maxflow_5x5_k2.json",
        "experiments/data/results/ggni_5x5_k2.json",
        "experiments/data/results/gd_5x5_k2.json",
        # Real mesh results
        expand("experiments/data/results/{dataset}_mincut.json", dataset=config.get("datasets", [])),
        expand("experiments/data/results/{dataset}_comb.json", dataset=config.get("datasets", [])),
        expand("experiments/data/results/{dataset}_ggni.json", dataset=config.get("datasets", [])),
        expand("experiments/data/results/{dataset}_gd.json", dataset=config.get("datasets", [])),
        expand("experiments/data/results/{dataset}_sa.json", dataset=config.get("datasets", [])),
        # Figures
        expand("figures/{dataset}_crack_paths.pdf", dataset=config.get("datasets", [])),
        expand("figures/{dataset}_energy_comparison.pdf", dataset=config.get("datasets", [])),
        # Tables and manifest
        "tables/comprehensive_benchmark.tex",
        "artifact/reproducibility_manifest.json"


# ==========================================
# REAL DATA PIPELINE
# ==========================================

rule convert_real_mesh:
    input:  "data/raw/{dataset}.msh"
    output: "experiments/data/graphs/{dataset}.npz"
    params: strategy=config.get("real", {}).get("terminal_strategy", "x_min_x_max")
    shell:  "python -m src.io.mesh_to_graph --mesh {input} --out {output} --strategy {params.strategy}"


# ==========================================
# TOY MODEL PIPELINE
# ==========================================

rule generate_lattice:
    output: "experiments/data/graphs/lsn_{n}x{n}.npz"
    shell: "python -m src.graph.lattice --n {wildcards.n} --out {output}"



rule latex_table:
    input: 
        "experiments/data/results/maxflow_5x5_k2.json",
        "experiments/data/results/maxflow_5x5_k3.json",
        "experiments/data/results/ggni_5x5_k2.json",
        "experiments/data/results/ggni_5x5_k3.json",
        "experiments/data/results/gd_5x5_k2.json",
        "experiments/data/results/gd_5x5_k3.json"
    output: "tables/toy_model_results.tex"
    shell: "python -m src.reporting.table --inputs {input} --out {output}"

# ==========================================
# MANIFEST
# ==========================================

rule manifest:
    input: [t for t in TARGETS if not t.endswith(".json")]
    output: "artifact/reproducibility_manifest.json"
    shell: "python -m artifact.evaluation.generate_manifest --inputs {input} --out {output}"
    

# ==========================================
# SIMULATED ANNEALING BASELINE (Modern Stochastic Optimizer)
# ==========================================

# ==========================================
# COMPREHENSIVE SUMMARY TABLE
# ==========================================
rule comprehensive_table:
    output: "tables/comprehensive_benchmark.tex"
    shell: "python -m src.reporting.comprehensive_table --out {output}"

# ==========================================
# OPTION C: 5 FAITHFUL SOLVERS
# ==========================================

rule run_mincut_rigid:
    input:  "experiments/data/graphs/{dataset}.npz"
    output: "experiments/data/results/{dataset}_mincut.json"
    params: Gc=config.get("real", {}).get("Gc", 1.0)
    shell: "python -m src.solvers.mincut_rigid --graph {input} --Gc {params.Gc} --out {output}"

rule run_combinatorial_bound:
    input:  "experiments/data/graphs/{dataset}.npz"
    output: "experiments/data/results/{dataset}_comb.json"
    params: Gc=config.get("real", {}).get("Gc", 1.0),
            u_bar=config.get("real", {}).get("u_bar", 5.0)
    shell: "python -m src.solvers.combinatorial_bound --graph {input} --Gc {params.Gc} --u_bar {params.u_bar} --out {output}"

rule run_ggni:
    input:
        graph="experiments/data/graphs/{dataset}.npz"
    output:
        json="experiments/data/results/{dataset}_ggni.json",
        trace="experiments/data/epistemic/{dataset}_ggni_trace.json"
    params:
        beta=lambda wc: config.get("real", {}).get("beta", 4.0),
        tau=lambda wc: config.get("real", {}).get("tau_spec", 0.15),
        Gc=lambda wc: config.get("real", {}).get("Gc", 1.0),
        u_bar=lambda wc: config.get("real", {}).get("u_bar", 5.0),
        n_steps=lambda wc: config.get("real", {}).get("n_steps", 20)  # ← اضافه شده!
    log:
        "logs/ggni/{dataset}.log"
    shell:
        """
        python -m src.solvers.ggni \
            --graph {input.graph} \
            --beta {params.beta} \
            --tau {params.tau} \
            --Gc {params.Gc} \
            --u_bar {params.u_bar} \
            --n_steps {params.n_steps} \
            --out {output.json} \
            --trace {output.trace} \
            2>&1 | tee {log}
        """

rule run_gd:
    input:  "experiments/data/graphs/{dataset}.npz"
    output: "experiments/data/results/{dataset}_gd.json"
    params: Gc=config.get("real", {}).get("Gc", 1.0),
            u_bar=config.get("real", {}).get("u_bar", 5.0)
    shell: "python -m src.solvers.gd --graph {input} --Gc {params.Gc} --u_bar {params.u_bar} --out {output}"

rule run_sa:
    input:  "experiments/data/graphs/{dataset}.npz"
    output: "experiments/data/results/{dataset}_sa.json"
    params: Gc=config.get("real", {}).get("Gc", 1.0),
            u_bar=config.get("real", {}).get("u_bar", 5.0)
    shell: "python -m src.solvers.sa --graph {input} --Gc {params.Gc} --u_bar {params.u_bar} --out {output}"

# ==========================================
# PLOTTING RULES (Option C Solvers)
# ==========================================

rule plot_real_crack_paths:
    input:
        mesh="experiments/data/graphs/{dataset}.npz",
        mincut="experiments/data/results/{dataset}_mincut.json",
        comb="experiments/data/results/{dataset}_comb.json",
        ggni="experiments/data/results/{dataset}_ggni.json",
        gd="experiments/data/results/{dataset}_gd.json",
        sa="experiments/data/results/{dataset}_sa.json"
    output: "figures/{dataset}_crack_paths.pdf"
    shell: "python -m src.plotting.crack_paths --graph {input.mesh} "
           "--mincut {input.mincut} --comb {input.comb} --ggni {input.ggni} "
           "--gd {input.gd} --sa {input.sa} --out {output}"

rule plot_energy_comparison:
    input:
        mincut="experiments/data/results/{dataset}_mincut.json",
        comb="experiments/data/results/{dataset}_comb.json",
        ggni="experiments/data/results/{dataset}_ggni.json",
        gd="experiments/data/results/{dataset}_gd.json",
        sa="experiments/data/results/{dataset}_sa.json"
    output: "figures/{dataset}_energy_comparison.pdf"
    shell: "python -m src.plotting.energy_comparison "
           "--mincut {input.mincut} --comb {input.comb} --ggni {input.ggni} "
           "--gd {input.gd} --sa {input.sa} --out {output}"
         
# ==========================================
# ADVANCED FIGURES (Solver Comparison, Spectral Analysis, Sensitivity)
# ==========================================

rule plot_solver_comparison:
    input:
        expand("experiments/data/results/{dataset}_mincut.json", dataset=config.get("datasets", [])),
        expand("experiments/data/results/{dataset}_comb.json", dataset=config.get("datasets", [])),
        expand("experiments/data/results/{dataset}_ggni.json", dataset=config.get("datasets", [])),
        expand("experiments/data/results/{dataset}_gd.json", dataset=config.get("datasets", [])),
        expand("experiments/data/results/{dataset}_sa.json", dataset=config.get("datasets", []))
    output: "figures/fig_solver_comparison.pdf"
    shell: "python -m src.plotting.solver_comparison --results-dir experiments/data/results --out {output}"

rule plot_spectral_analysis:
    input:
        graph="experiments/data/graphs/Geometria_Transfinita.npz",
        ggni="experiments/data/results/Geometria_Transfinita_ggni.json",
        trace="experiments/data/epistemic/Geometria_Transfinita_ggni_trace.json"
    params:
        beta=lambda wc: config.get("real", {}).get("beta", 4.0),
        tau=lambda wc: config.get("real", {}).get("tau_spec", 0.15)
    output: "figures/fig_spectral_analysis.pdf"
    shell: "python -m src.plotting.spectral_analysis "
           "--graph {input.graph} --ggni {input.ggni} --trace {input.trace} "
           "--beta {params.beta} --tau {params.tau} --out {output}"

rule run_sensitivity_sweep:
    input:
        graph="experiments/data/graphs/Geometria_Transfinita.npz"
    output:
        heatmap="experiments/data/results/sensitivity_heatmap.npy"
    shell: "python -m src.analysis.sensitivity_sweep "
           "--graph {input.graph} --out {output.heatmap}"

rule plot_sensitivity_scaling:
    input:
        heatmap="experiments/data/results/sensitivity_heatmap.npy"
    output: "figures/fig_ggni_sensitivity_scaling.pdf"
    shell: "python -m src.plotting.sensitivity_scaling "
           "--heatmap {input.heatmap} --out {output}"

#!/usr/bin/env bash
set -euo pipefail
echo "=========================================="
echo "  DVF Artifact Certification Pipeline"
echo "=========================================="
echo "[1/4] Hardware & environment validation..."
python -m artifact.evaluation.hardware_validation
echo "[2/4] Full reproduction (Snakemake)..."
snakemake --cores all --use-conda --configfile=experiments/configs/paper_final.yaml
echo "[3/4] Epistemic & thermodynamic tests..."
pytest tests/ -v -k "semantic_drift or clausius_duhem"
echo "[4/4] SHA-256 manifest verification..."
python -m artifact.evaluation.verify_manifest --manifest artifact/reproducibility_manifest.json --targets figures/ tables/
echo "=========================================="
echo "  CERTIFICATION SUCCESSFUL"
echo "=========================================="

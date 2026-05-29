from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from src.core.epistemic_metadata import SpectralDiagnostics
import logging
logger = logging.getLogger(__name__)

SolverAction = Literal[
    "standard_ggni", "k_way_spectral_split", "recursive_subdomain_solve",
    "fallback_to_energy_refinement", "halt_simulation",
]

@dataclass
class AdaptiveSpectralPolicy:
    ipr_threshold: float = 0.15
    multiplicity_tol: float = 1e-4
    min_lambda_2: float = 1e-8

    def evaluate(self, diag: SpectralDiagnostics, k_terminals: int = 2) -> SolverAction:
        logger.info(f"Spectral: state={diag.state} λ2={diag.lambda_2:.3e} "
                    f"gap={diag.spectral_gap:.3e} IPR={diag.ipr:.3e} comps={diag.component_count}")
        if diag.state == "fragmented" and diag.component_count >= k_terminals:
            return "fallback_to_energy_refinement"
        if diag.state == "collapsed" or diag.lambda_2 < self.min_lambda_2:
            return "recursive_subdomain_solve" if diag.component_count > 1 else "fallback_to_energy_refinement"
        if diag.state == "near_multiplicity":
            return "k_way_spectral_split"
        if diag.state == "localized":
            return "standard_ggni"
        return "standard_ggni"

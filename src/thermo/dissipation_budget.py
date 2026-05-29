from __future__ import annotations
from src.core.epistemic_metadata import DissipationBudget

def compute_dissipation_budget(state_prev, state_next, delta_W_ext: float,
                               regularization_penalty: float = 0.0,
                               machine_tol: float = 1e-12) -> DissipationBudget:
    dE_elastic = state_next.elastic_energy - state_prev.elastic_energy
    D_fracture = state_next.fracture_energy - state_prev.fracture_energy
    D_regularization = regularization_penalty
    D_total = delta_W_ext - (dE_elastic + D_fracture + D_regularization)
    D_numerical = D_total - D_fracture - D_regularization
    ok = (D_fracture >= -machine_tol) and (D_total >= -machine_tol) and (abs(D_numerical) < 1e-8)
    return DissipationBudget(
        d_fracture=float(D_fracture), d_regularization=float(D_regularization),
        d_numerical=float(D_numerical), d_total=float(D_total),
        clausius_duhem_satisfied=bool(ok),
    )

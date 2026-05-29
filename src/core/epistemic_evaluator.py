from __future__ import annotations
from src.core.epistemic_metadata import EpistemicStepMetadata, SpectralDiagnostics
from src.thermo.dissipation_budget import compute_dissipation_budget
from src.thermo.variational_gap import VariationalGapMonitor

class ThermodynamicInconsistencyError(RuntimeError):
    pass

class UnifiedEpistemicEvaluator:
    def __init__(self, energy_functional, constraint_mgr,
                 gap_tol: float = 1e-8, thermo_tol: float = 1e-10):
        self.constraint_mgr = constraint_mgr
        self.gap_tol = gap_tol
        self.thermo_tol = thermo_tol
        self.u_gap_monitor = VariationalGapMonitor(energy=energy_functional, tol=gap_tol)

    def evaluate_step(self, step_id, load_factor, state_prev, state_next,
                      delta_W_ext, spectral_diag: SpectralDiagnostics,
                      regularization_penalty: float = 0.0) -> EpistemicStepMetadata:
        budget = compute_dissipation_budget(
            state_prev, state_next, delta_W_ext, regularization_penalty, self.thermo_tol
        )
        if not budget.clausius_duhem_satisfied:
            raise ThermodynamicInconsistencyError(
                f"Step {step_id}: D_numerical={budget.d_numerical:.3e} exceeds tolerance."
            )
        u_mask = self.constraint_mgr.build_dirichlet_mask(state_next.dirichlet_dofs)
        u_gap_result = self.u_gap_monitor.check(state_next.u, admissible_mask=u_mask)

        return EpistemicStepMetadata(
            step=step_id, load_factor=load_factor, spectral=spectral_diag,
            thermo=budget, variational_gap=u_gap_result.gap,
            active_solver_role=state_next.solver_role,
            component_count=spectral_diag.component_count,
            conditioning_estimate=state_next.condition_number,
        )

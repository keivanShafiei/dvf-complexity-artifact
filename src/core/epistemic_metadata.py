from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Literal
import json
import numpy as np

@dataclass(frozen=True)
class SpectralDiagnostics:
    lambda_2: float
    lambda_3: float
    spectral_gap: float
    ipr: float
    state: Literal["stable", "localized", "near_multiplicity", "fragmented", "collapsed"]
    component_count: int

@dataclass(frozen=True)
class DissipationBudget:
    d_fracture: float
    d_regularization: float
    d_numerical: float
    d_total: float
    clausius_duhem_satisfied: bool

@dataclass(frozen=True)
class EpistemicStepMetadata:
    step: int
    load_factor: float
    spectral: SpectralDiagnostics
    thermo: DissipationBudget
    variational_gap: float
    active_solver_role: str
    component_count: int
    conditioning_estimate: float

    def to_dict(self) -> dict:
        d = asdict(self)
        d["spectral"] = asdict(self.spectral)
        d["thermo"] = asdict(self.thermo)
        return d

class EpistemicTraceLogger:
    def __init__(self, path: str):
        self.path = path
        self._records = []

    def log(self, meta: EpistemicStepMetadata):
        self._records.append(meta.to_dict())

    def flush(self):
        with open(self.path, "w") as f:
            json.dump(self._records, f, indent=2, default=float)

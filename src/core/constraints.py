from __future__ import annotations
from dataclasses import dataclass
import numpy as np

@dataclass
class ConstraintMasks:
    u_admissible: np.ndarray
    s_admissible: np.ndarray

class ConstraintManager:
    def __init__(self, n_dofs: int, n_bonds: int):
        self.n_dofs = n_dofs
        self.n_bonds = n_bonds

    def build_dirichlet_mask(self, constrained_dof_indices: np.ndarray) -> np.ndarray:
        mask = np.ones(self.n_dofs, dtype=bool)
        if constrained_dof_indices.size:
            mask[constrained_dof_indices] = False
        return mask

    def build_irreversibility_mask(self, s_current: np.ndarray) -> np.ndarray:
        return s_current.astype(bool)

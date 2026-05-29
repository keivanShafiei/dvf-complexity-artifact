from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional, Protocol, Sequence, Union
import numpy as np

ArrayLike = Union[np.ndarray, Sequence[float]]

class EnergyFunctional(Protocol):
    def __call__(self, x: np.ndarray) -> float: ...

GradientFunction = Callable[[np.ndarray], np.ndarray]

@dataclass(frozen=True)
class VariationalGapResult:
    gap: float
    projected_gradient: np.ndarray
    raw_gradient: np.ndarray
    admissible_dofs: np.ndarray
    is_stationary: bool

def _as_1d(x: ArrayLike, name="x") -> np.ndarray:
    a = np.asarray(x, dtype=np.float64).reshape(-1)
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{name} contains NaN/Inf.")
    return a

def _validate_mask(mask, n):
    if mask is None:
        return np.ones(n, dtype=bool)
    m = np.asarray(mask, dtype=bool).reshape(-1)
    if m.shape[0] != n:
        raise ValueError(f"mask length {m.shape[0]} != {n}")
    return m

def finite_difference_gradient(energy, x, eps=1e-8, admissible_mask=None):
    x = _as_1d(x); n = x.size
    mask = _validate_mask(admissible_mask, n)
    g = np.zeros(n, dtype=np.float64)
    xw = x.copy()
    for i in range(n):
        if not mask[i]: continue
        h = eps * max(1.0, abs(x[i]))
        xw[i] = x[i] + h; ep = float(energy(xw))
        xw[i] = x[i] - h; em = float(energy(xw))
        xw[i] = x[i]
        g[i] = (ep - em) / (2.0 * h)
    return g

def projected_gradient(gradient, admissible_mask=None):
    g = _as_1d(gradient, "gradient")
    mask = _validate_mask(admissible_mask, g.size)
    gp = np.zeros_like(g); gp[mask] = g[mask]
    return gp

def compute_variational_gap(x, energy=None, gradient=None,
                            admissible_mask=None, tol=1e-8, fd_eps=1e-8):
    x = _as_1d(x)
    mask = _validate_mask(admissible_mask, x.size)
    if gradient is not None:
        raw = _as_1d(gradient(x), "gradient(x)")
    else:
        if energy is None:
            raise ValueError("Provide energy or gradient.")
        raw = finite_difference_gradient(energy, x, eps=fd_eps, admissible_mask=mask)
    proj = projected_gradient(raw, mask)
    gap = float(np.linalg.norm(proj, ord=2))
    return VariationalGapResult(gap=gap, projected_gradient=proj, raw_gradient=raw,
                                admissible_dofs=mask, is_stationary=gap <= tol)

class VariationalGapMonitor:
    def __init__(self, energy=None, gradient=None, admissible_mask=None,
                 tol=1e-8, fd_eps=1e-8):
        if energy is None and gradient is None:
            raise ValueError("Provide energy or gradient.")
        self.energy = energy; self.gradient = gradient
        self.admissible_mask = None if admissible_mask is None else np.asarray(admissible_mask, dtype=bool)
        self.tol = float(tol); self.fd_eps = float(fd_eps)

    def check(self, x, admissible_mask=None):
        mask = admissible_mask if admissible_mask is not None else self.admissible_mask
        return compute_variational_gap(x, energy=self.energy, gradient=self.gradient,
                                       admissible_mask=mask, tol=self.tol, fd_eps=self.fd_eps)

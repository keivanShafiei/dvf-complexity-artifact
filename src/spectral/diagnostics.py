from __future__ import annotations
import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import eigsh, ArpackNoConvergence
from scipy.sparse.csgraph import connected_components
from src.core.epistemic_metadata import SpectralDiagnostics
import logging
logger = logging.getLogger(__name__)

def compute_normalized_laplacian(W: sp.csr_matrix):
    deg = np.array(W.sum(axis=1)).flatten()
    with np.errstate(divide="ignore", invalid="ignore"):
        d_inv_sqrt = np.where(deg > 1e-14, 1.0 / np.sqrt(deg), 0.0)
    D_inv_sqrt = sp.diags(d_inv_sqrt)
    n = W.shape[0]
    L = sp.eye(n, format="csr") - (D_inv_sqrt @ W @ D_inv_sqrt)
    L = (L + L.T) / 2.0
    return L.tocsr(), deg

def compute_spectral_diagnostics(W: sp.csr_matrix, s_state: np.ndarray,
                                 ipr_threshold=0.15, multiplicity_tol=1e-4,
                                 zero_eigenvalue_tol=1e-8) -> SpectralDiagnostics:
    n = W.shape[0]
    intact = (W > 1e-12).astype(int)
    n_comp, _ = connected_components(intact, directed=False)
    L, deg = compute_normalized_laplacian(W)

    if n_comp > 2:
        return SpectralDiagnostics(0.0, 0.0, 0.0, 1.0, "fragmented", n_comp)

    try:
        k = min(4, n - 2) if n > 4 else 2
        evals, evecs = eigsh(L, k=k, which="SM", sigma=1e-6, tol=1e-8)
        idx = np.argsort(evals); evals = evals[idx]; evecs = evecs[:, idx]
        l2 = evals[1] if len(evals) > 1 else 0.0
        l3 = evals[2] if len(evals) > 2 else l2
        v = evecs[:, 1] if len(evals) > 1 else np.zeros(n)
    except ArpackNoConvergence:
        logger.warning("ARPACK failed; falling back to dense eigensolver.")
        ev, evec = np.linalg.eigh(L.toarray())
        l2 = ev[1]; l3 = ev[2] if n > 2 else l2
        v = evec[:, 1]

    ipr = float(np.sum(v**4) / (np.sum(v**2)**2 + 1e-16))
    gap = float(l3 - l2)

    if l2 < zero_eigenvalue_tol and n_comp > 1: state = "collapsed"
    elif n_comp > 1: state = "fragmented"
    elif gap < multiplicity_tol: state = "near_multiplicity"
    elif ipr > ipr_threshold: state = "localized"
    else: state = "stable"

    return SpectralDiagnostics(float(l2), float(l3), gap, ipr, state, n_comp)

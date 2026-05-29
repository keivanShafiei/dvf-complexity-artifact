
import numpy as np
from .assembly import assemble_stiffness_matrix

def compute_elastic_energy(u, K):
    return 0.5 * u.dot(K.dot(u))

def compute_fracture_energy(s, w, Gc=1.0):
    return Gc * np.sum((1 - s) * w)

def compute_dvf_energy(u, s, edges, w, coords, Gc=1.0, kappa=1.0):
    n_dofs = len(u)
    K = assemble_stiffness_matrix(edges, s, coords, kappa=kappa, n_dofs=n_dofs)
    E_elastic = compute_elastic_energy(u, K)
    E_fracture = compute_fracture_energy(s, w, Gc)
    return E_elastic + E_fracture, E_elastic, E_fracture

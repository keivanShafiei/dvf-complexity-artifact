
"""Shared physics helpers for all DVF solvers.
All solvers use the SAME energy functional:
    E_h(u, s) = 0.5 * sum s_ij * kappa_ij * ||u_i - u_j||^2
              + Gc * sum (1 - s_ij) * w_ij
with u in R^{N x d} free under Dirichlet BCs.
"""
import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve


def build_graph_from_npz(data):
    edges = data["edges"]
    weights = data["w"]
    stiffness = data.get("K", np.ones(len(edges)))
    coords = data.get("coords", None)
    return edges, weights, stiffness, coords


def get_terminals(data, coords):
    """Identify source/sink nodes from coords (x-min/x-max) or npz keys."""
    s_nodes = data.get("s_terminals", None)
    t_nodes = data.get("t_terminals", None)
    if s_nodes is None or t_nodes is None or len(s_nodes) == 0 or len(t_nodes) == 0:
        if coords is None:
            s_nodes = np.array([0])
            t_nodes = np.array([int(data["edges"].max())])
        else:
            x = coords[:, 0]
            tol = 1e-6 * max(1.0, x.max() - x.min())
            s_nodes = np.where(x <= x.min() + tol)[0]
            t_nodes = np.where(x >= x.max() - tol)[0]
    return np.asarray(s_nodes), np.asarray(t_nodes)


def assemble_stiffness(edges, s, stiffness, coords):
    """Assemble K(s) using central-force springs along bond directions.
    kappa_eff = stiffness[idx] / L for bond (i,j)."""
    N = len(coords)
    n_dofs = 2 * N
    rows, cols, vals = [], [], []
    for idx, (i, j) in enumerate(edges):
        if s[idx] == 0:
            continue
        i, j = int(i), int(j)
        dx = coords[j] - coords[i]
        L = np.linalg.norm(dx)
        if L < 1e-12:
            continue
        nx, ny = dx / L
        k = stiffness[idx] / L
        kxx, kxy, kyy = k*nx*nx, k*nx*ny, k*ny*ny
        blocks = [(i, i,  1), (i, j, -1), (j, i, -1), (j, j,  1)]
        for a, b, sign in blocks:
            rows.extend([2*a,   2*a,   2*a+1, 2*a+1])
            cols.extend([2*b,   2*b+1, 2*b,   2*b+1])
            vals.extend([sign*kxx, sign*kxy, sign*kxy, sign*kyy])
    return sp.coo_matrix((vals, (rows, cols)), shape=(n_dofs, n_dofs)).tocsr()


def solve_fem(K, s_nodes, t_nodes, u_bar, n_dofs):
    """Solve K u = 0 with Dirichlet: u=0 on source, u=(u_bar, u_bar) on sink."""
    fixed_dofs, u_bc = [], np.zeros(n_dofs)
    for node in s_nodes:
        fixed_dofs.extend([2*int(node), 2*int(node)+1])
    for node in t_nodes:
        fixed_dofs.extend([2*int(node), 2*int(node)+1])
        u_bc[2*int(node)] = u_bar
        u_bc[2*int(node)+1] = u_bar
    fixed_dofs = np.array(sorted(set(fixed_dofs)))
    all_dofs = np.arange(n_dofs)
    free_dofs = np.setdiff1d(all_dofs, fixed_dofs)
    if len(free_dofs) == 0:
        return u_bc
    K_ff = K[np.ix_(free_dofs, free_dofs)]
    K_fc = K[np.ix_(free_dofs, fixed_dofs)]
    diag_max = K_ff.diagonal().max() if K_ff.nnz > 0 else 1.0
    reg = 1e-8 * max(diag_max, 1.0)
    K_ff = K_ff + reg * sp.eye(K_ff.shape[0])
    try:
        u_f = spsolve(K_ff, -K_fc.dot(u_bc[fixed_dofs]))
    except Exception:
        u_f = np.zeros(len(free_dofs))
    u = np.zeros(n_dofs)
    u[free_dofs] = u_f
    u[fixed_dofs] = u_bc[fixed_dofs]
    return u


def compute_bond_strain(u, edges, stiffness, coords):
    """phi_ij = 0.5 * (kappa_ij / L) * ((u_j - u_i) . n_ij)^2
    (axial strain energy stored in central-force spring)."""
    phi = np.zeros(len(edges))
    for idx, (i, j) in enumerate(edges):
        i, j = int(i), int(j)
        dx = coords[j] - coords[i]
        L = np.linalg.norm(dx)
        if L < 1e-12:
            continue
        n = dx / L
        du = u[2*j:2*j+2] - u[2*i:2*i+2]
        delta_axial = du.dot(n)
        phi[idx] = 0.5 * (stiffness[idx] / L) * delta_axial ** 2
    return phi


def compute_energy(u, s, edges, weights, stiffness, coords, Gc):
    K = assemble_stiffness(edges, s, stiffness, coords)
    E_elastic = 0.5 * float(u.dot(K.dot(u)))
    E_fracture = float(Gc * np.sum((1 - s) * weights))
    return E_elastic + E_fracture, E_elastic, E_fracture


def build_nx_graph_for_mincut(edges, weights, s_nodes, t_nodes, Gc):
    """Build NetworkX graph for s-t min-cut with capacities Gc*w_ij."""
    import networkx as nx
    N = int(edges.max()) + 1
    G = nx.Graph()
    for idx, (i, j) in enumerate(edges):
        G.add_edge(int(i), int(j), capacity=float(Gc * weights[idx]), idx=int(idx))
    super_s, super_t = N, N + 1
    for node in s_nodes:
        G.add_edge(super_s, int(node), capacity=float("inf"))
    for node in t_nodes:
        G.add_edge(int(node), super_t, capacity=float("inf"))
    return G, super_s, super_t

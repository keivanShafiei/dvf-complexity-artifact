
import numpy as np
from scipy import sparse

def assemble_stiffness_matrix(edges, s, coords, kappa=1.0, n_dofs=None):
    """
    اسمبل ماتریس سختی با استفاده از فنرهای نیروی مرکزی در راستای پیوندها.
    """
    N = len(coords)
    if n_dofs is None:
        n_dofs = 2 * N
    
    rows, cols, vals = [], [], []
    
    for idx, (i, j) in enumerate(edges):
        if s[idx] == 0:
            continue
            
        dx = coords[j] - coords[i]
        L = np.linalg.norm(dx)
        if L < 1e-12:
            continue
        
        # کسینوس‌های جهت‌دار
        nx, ny = dx / L
        k = kappa / L  # سختی فنر معادل
        
        k_xx = k * nx * nx
        k_xy = k * nx * ny
        k_yy = k * ny * ny
        
        # بلوک K_ii
        rows.extend([2*i, 2*i, 2*i+1, 2*i+1])
        cols.extend([2*i, 2*i+1, 2*i, 2*i+1])
        vals.extend([k_xx, k_xy, k_xy, k_yy])
        
        # بلوک K_ij
        rows.extend([2*i, 2*i, 2*i+1, 2*i+1])
        cols.extend([2*j, 2*j+1, 2*j, 2*j+1])
        vals.extend([-k_xx, -k_xy, -k_xy, -k_yy])
        
        # بلوک K_ji
        rows.extend([2*j, 2*j, 2*j+1, 2*j+1])
        cols.extend([2*i, 2*i+1, 2*i, 2*i+1])
        vals.extend([-k_xx, -k_xy, -k_xy, -k_yy])
        
        # بلوک K_jj
        rows.extend([2*j, 2*j, 2*j+1, 2*j+1])
        cols.extend([2*j, 2*j+1, 2*j, 2*j+1])
        vals.extend([k_xx, k_xy, k_xy, k_yy])
        
    K = sparse.coo_matrix((vals, (rows, cols)), shape=(n_dofs, n_dofs)).tocsr()
    return K

def solve_displacement(K, free_dofs, fixed_dofs, u_bc):
    """
    حل سیستم با رگولاریزاسیون برای جلوگیری از تکینگی جزایر معلق.
    """
    K_ff = K[free_dofs, :][:, free_dofs]
    
    # رگولاریزاسیون: تثبیت مدهای جسم صلب بدون تغییر فیزیک مسئله
    max_diag = K_ff.diagonal().max() if K_ff.nnz > 0 else 1.0
    reg = 1e-8 * max_diag if max_diag > 0 else 1e-10
    K_ff = K_ff + reg * sparse.eye(K_ff.shape[0])
    
    K_fc = K[free_dofs, :][:, fixed_dofs]
    u_c = np.array([u_bc[d] for d in fixed_dofs])
    f_eq = -K_fc.dot(u_c)
    
    u_f = sparse.linalg.spsolve(K_ff, f_eq)
    
    u = np.zeros(K.shape[0])
    for i, d in enumerate(free_dofs): u[d] = u_f[i]
    for i, d in enumerate(fixed_dofs): u[d] = u_bc[d]
    return u

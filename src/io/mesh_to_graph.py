# src/io/mesh_to_graph.py
"""
Robust Mesh-to-Graph Converter for Real FEM/Experimental Data.
Converts .msh/.vtk/.xml to DVF-compatible .npz format with Voronoi weights.
"""
import argparse
import numpy as np
import meshio
from scipy.spatial import Voronoi, Delaunay
import os
import logging

logging.basicConfig(level=logging.INFO)

def _compute_dual_weights(points, edges, tolerance=1e-9):
    """
    Computes geometric weights w_ij for DVF fracture energy.
    Uses Voronoi ridge lengths where stable, falls back to dual-area approximation.
    """
    N = len(points)
    w = np.zeros(len(edges), dtype=np.float64)
    
    try:
        # Try Voronoi for accurate H^{d-1} facet measures
        vor = Voronoi(points)
        ridge_map = {}
        for ridge, pts, norm in zip(vor.ridge_vertices, vor.ridge_points, vor.ridge_normals):
            if -1 not in ridge:
                p1, p2 = vor.vertices[ridge]
                length = np.linalg.norm(p1 - p2)
                u, v = sorted(tuple(pts))
                ridge_map[(u, v)] = length
        for i, (u, v) in enumerate(edges):
            w[i] = ridge_map.get((u, v), 1.0)
    except Exception:
        # Fallback: dual-area approximation (robust for distorted FE meshes)
        tri = Delaunay(points)
        areas = np.zeros(N)
        for simplex in tri.simplices:
            p0, p1, p2 = points[simplex]
            area = 0.5 * np.abs((p1[0]-p0[0])*(p2[1]-p0[1]) - (p1[1]-p0[1])*(p2[0]-p0[0]))
            areas[simplex] += area / 3.0
        for i, (u, v) in enumerate(edges):
            w[i] = (areas[u] + areas[v]) / (2.0 * max(np.linalg.norm(points[u]-points[v]), tolerance))
            
    return w

def select_terminals_by_coords(points, strategy="x_min_x_max", tol=1e-6):
    """
    Maps physical coordinates to terminal sets for DVF boundary conditions.
    Supports: x_min_x_max, circular, custom_mask
    """
    N = len(points)
    if strategy == "x_min_x_max":
        x = points[:, 0]
        s_nodes = np.where(x <= x.min() + tol)[0]
        t_nodes = np.where(x >= x.max() - tol)[0]
        return s_nodes, t_nodes
    elif strategy == "circular":
        r = np.linalg.norm(points, axis=1)
        r_min, r_max = r.min(), r.max()
        inner = np.where(r <= r_min + tol)[0]
        outer = np.where(r >= r_max - tol)[0]
        return inner, outer
    else:
        raise ValueError(f"Unknown terminal strategy: {strategy}")

def convert_real_mesh(mesh_path, out_path, strategy="x_min_x_max", tol=1e-6):
    logging.info(f"Reading mesh: {mesh_path}")
    mesh = meshio.read(mesh_path)
    points = mesh.points[:, :2]  # Assume 2D for DVF
    
    # Extract edges from element connectivity
    # FIX: Handle numpy arrays correctly to avoid "truth value of an array" ValueError
    triangles = mesh.cells_dict.get('triangle')
    quads = mesh.cells_dict.get('quad')
    
    cells = None
    if triangles is not None and len(triangles) > 0:
        cells = triangles
    elif quads is not None and len(quads) > 0:
        cells = quads
        
    if cells is None or len(cells) == 0:
        raise ValueError(
            f"No 'triangle' or 'quad' cells found in {mesh_path}. "
            f"Available cell types: {list(mesh.cells_dict.keys())}"
        )
    
    edge_set = set()
    for cell in cells:
        for i in range(len(cell)):
            for j in range(i+1, len(cell)):
                edge_set.add(tuple(sorted((cell[i], cell[j]))))
                
    edges = np.array(list(edge_set), dtype=np.int32)
    w = _compute_dual_weights(points, edges)
    K_local = np.ones(len(edges), dtype=np.float64)
    
    # Save terminals for downstream solver config
    s_nodes, t_nodes = select_terminals_by_coords(points, strategy, tol)
    
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    np.savez(
        out_path,
        edges=edges,
        w=w,
        K=K_local,
        n=len(points),
        coords=points,
        s_terminals=s_nodes,
        t_terminals=t_nodes
    )
    logging.info(f"Graph saved: {len(points)} nodes, {len(edges)} bonds -> {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--strategy", default="x_min_x_max")
    parser.add_argument("--tol", type=float, default=1e-6)
    args = parser.parse_args()
    convert_real_mesh(args.mesh, args.out, args.strategy, args.tol)

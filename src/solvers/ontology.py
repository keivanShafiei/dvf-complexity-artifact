from enum import Enum

class SolverRole(Enum):
    COMBINATORIAL_REFERENCE = "MaxFlow (exact global minimizer, k=2)"
    BOUNDED_TREEWIDTH_VALIDATION = "DP (exact for bounded tree-width)"
    TOPOLOGY_PREDICTOR = "GGNI (heuristic spectral exploration, NOT a minimizer)"
    VARIATIONAL_REFINER = "GD (local descent to stationary point)"
    PRODUCTION_SOLVER = "Hybrid GGNI+GD (predictor-refiner)"

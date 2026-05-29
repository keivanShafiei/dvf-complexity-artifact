import meshio
import numpy as np

def read_fem_mesh(filepath):
    """
    خواندن فایل مش واقعی و تبدیل به فرمت تعاملی گراف (V, E, w)
    """
    mesh = meshio.read(filepath)
    
    # استخراج نقاط (Nodes)
    points = mesh.points
    
    # استخراج یال‌ها (Edges) از المان‌ها (مثلاً مثلث‌ها یا چهارضلعی‌ها)
    # این بخش بسته به نوع المان (Triangle/Quad) تغییر می‌کند
    edges = set()
    if 'triangle' in mesh.cells_dict:
        cells = mesh.cells_dict['triangle']
        for tri in cells:
            edges.add((tri[0], tri[1]))
            edges.add((tri[1], tri[2]))
            edges.add((tri[2], tri[0]))
            
    return points, np.array(list(edges))

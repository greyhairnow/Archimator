from __future__ import annotations

import os
from typing import TYPE_CHECKING, List, Tuple

from PIL import Image

try:
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
except Exception:  # pragma: no cover
    plt = None  # type: ignore

try:
    import tkinter as tk
except Exception:  # pragma: no cover
    tk = None  # type: ignore

if TYPE_CHECKING:
    from .gui_client import MeasureAppGUI


def generate_3d_image(polygons: List[List[Tuple[float, float]]], height: float = 1.0) -> Image.Image:
    if plt is None:
        raise RuntimeError("matplotlib is not available")
    fig = plt.figure(figsize=(6, 6))
    ax = fig.add_subplot(111, projection='3d')
    for idx, pts in enumerate(polygons):
        if len(pts) < 3:
            continue
        xs = [p[0] for p in pts] + [pts[0][0]]
        ys = [p[1] for p in pts] + [pts[0][1]]
        zs_bottom = [0] * len(xs)
        zs_top = [height] * len(xs)
        color = f'C{idx % 10}'
        ax.plot(xs, ys, zs_bottom, color=color, alpha=0.6)
        ax.plot(xs, ys, zs_top, color=color, alpha=0.6)
        for i in range(len(pts)):
            x0, y0 = pts[i]
            ax.plot([x0, x0], [y0, y0], [0, height], color=color, alpha=0.6)
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Height')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_zlim(0, height)
    ax.view_init(elev=20, azim=30)
    ax.grid(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_zticks([])
    buf = os.path.join('/tmp', 'extrusion.png')
    fig.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    img = Image.open(buf)
    return img


def show_3d_view(app: "MeasureAppGUI") -> None:
    if not app.polygons:
        from tkinter import messagebox
        messagebox.showwarning("Warning", "Draw at least one polygon first.")
        return
    if app.image is None:
        return
    width, height_img = app.image.size
    norm_polys: List[List[Tuple[float, float]]] = []
    for poly in app.polygons:
        pts = [(x / width, y / height_img) for (x, y) in poly.points]
        norm_polys.append(pts)
    height = float(app.config.get('extrusion_height', 1.0))
    try:
        img3d = generate_3d_image(norm_polys, height)
        if tk is None:
            return
        top = tk.Toplevel(app.root)
        top.title("3D View")
        from PIL import ImageTk
        photo3d = ImageTk.PhotoImage(img3d)
        lbl = tk.Label(top, image=photo3d)
        lbl.image = photo3d
        lbl.pack()
    except Exception as e:
        from tkinter import messagebox
        messagebox.showerror("Error", f"Failed to generate 3D view: {e}")



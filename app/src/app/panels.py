from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

try:
    from tkinter import messagebox
except Exception:  # pragma: no cover
    messagebox = None  # type: ignore

try:
    from .model import point_in_polygon
except Exception:
    from model import point_in_polygon

if TYPE_CHECKING:
    from .gui_client import MeasureAppGUI


def optimize_panels(app: "MeasureAppGUI") -> None:
    if app.selected_polygon is None:
        if messagebox:
            messagebox.showwarning("Warning", "Select a polygon first.")
        return
    poly = app.polygons[app.selected_polygon]
    panel_w_real = float(app.config.get('panel_width', 1.0))
    panel_h_real = float(app.config.get('panel_height', 1.0))
    if app.scale_factor == 0:
        return
    panel_w_px = panel_w_real / app.scale_factor
    panel_h_px = panel_h_real / app.scale_factor
    xs = [p[0] for p in poly.points]
    ys = [p[1] for p in poly.points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width = max_x - min_x
    height = max_y - min_y
    cols = int(width // panel_w_px)
    rows = int(height // panel_h_px)
    rects: List[List[Tuple[float, float]]] = []
    for i in range(cols):
        for j in range(rows):
            rx = min_x + i * panel_w_px
            ry = min_y + j * panel_h_px
            r_points = [
                (rx, ry),
                (rx + panel_w_px, ry),
                (rx + panel_w_px, ry + panel_h_px),
                (rx, ry + panel_h_px)
            ]
            cx = rx + panel_w_px / 2
            cy = ry + panel_h_px / 2
            if point_in_polygon((cx, cy), poly.points):
                rects.append(r_points)
    app.redraw()
    for rect in rects:
        coords: List[float] = []
        for x, y in rect:
            coords.extend([x * app.zoom_level, y * app.zoom_level])
        app.canvas.create_polygon(coords, fill='', outline='orange', width=1, dash=(4, 2))

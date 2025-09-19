from __future__ import annotations

import math
from typing import TYPE_CHECKING, List, Tuple

try:
    from tkinter import messagebox
except Exception:  # pragma: no cover
    messagebox = None  # type: ignore

if TYPE_CHECKING:
    from .gui_client import MeasureAppGUI


def straighten_polygon(app: "MeasureAppGUI") -> None:
    if app.selected_polygon is None:
        if messagebox:
            messagebox.showwarning("Warning", "Select a polygon first.")
        return
    poly = app.polygons[app.selected_polygon]
    if len(poly.points) < 3:
        if messagebox:
            messagebox.showwarning("Warning", "Polygon must have at least 3 points.")
        return
    app._straighten_backup = poly.points.copy()
    pts = poly.points
    n = len(pts)
    green_indices: List[int] = []
    for i in range(n):
        x, y = pts[i]
        x_prev, y_prev = pts[i - 1]
        x_next, y_next = pts[(i + 1) % n]
        v1 = (x - x_prev, y - y_prev)
        v2 = (x_next - x, y_next - y)
        dot = v1[0] * v2[0] + v1[1] * v2[1]
        det = v1[0] * v2[1] - v1[1] * v2[0]
        ang = math.atan2(det, dot)
        deg = abs(math.degrees(ang))
        if abs(deg - 90) < 8:
            green_indices.append(i)
    if len(green_indices) < 2:
        if messagebox:
            messagebox.showinfo("Straighten", "No sufficient green points to straighten.")
        return
    new_points: List[Tuple[float, float]] = []
    for idx in range(len(green_indices)):
        i1 = green_indices[idx]
        i2 = green_indices[(idx + 1) % len(green_indices)]
        x1, y1 = pts[i1]
        new_points.append((x1, y1))
        intermediates: List[int] = []
        j = (i1 + 1) % n
        while j != i2:
            intermediates.append(j)
            j = (j + 1) % n
        if intermediates:
            x2, y2 = pts[i2]
            count = len(intermediates) + 1
            for k, _ in enumerate(intermediates, start=1):
                t = k / count
                xm = x1 + t * (x2 - x1)
                ym = y1 + t * (y2 - y1)
                new_points.append((xm, ym))
    if len(new_points) > 2:
        new_points[-1] = new_points[0]
    poly.points = new_points
    poly.compute_metrics()
    app.redraw()


def undo_straighten(app: "MeasureAppGUI") -> None:
    if app.selected_polygon is None or app._straighten_backup is None:
        if messagebox:
            messagebox.showwarning("Warning", "No straighten operation to undo.")
        return
    poly = app.polygons[app.selected_polygon]
    poly.points = app._straighten_backup
    poly.compute_metrics()
    app._straighten_backup = None
    app.redraw()


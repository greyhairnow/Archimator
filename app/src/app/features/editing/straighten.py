from __future__ import annotations

import math
from typing import TYPE_CHECKING, List, Tuple

try:
    from tkinter import messagebox
except Exception:  # pragma: no cover
    messagebox = None  # type: ignore

if TYPE_CHECKING:
    try:
        from ...gui_client import MeasureAppGUI  # type: ignore
    except Exception:
        from gui_client import MeasureAppGUI  # type: ignore


def _rectangle_map(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Project polygon vertices onto the minimal axis-aligned rectangle bounding them."""
    if len(points) < 4:
        return points[:]

    closed = points[0] == points[-1]
    pts = points[:-1] if closed else points[:]
    if len(pts) < 4:
        return points[:]

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width = max_x - min_x
    height = max_y - min_y
    if width < 1e-9 or height < 1e-9:
        return points[:]

    perim_rect = 2.0 * (width + height)

    # cumulative lengths along original polygon perimeter
    seg_lengths = [0.0]
    total = 0.0
    for idx in range(len(pts)):
        x1, y1 = pts[idx]
        x2, y2 = pts[(idx + 1) % len(pts)]
        total += math.hypot(x2 - x1, y2 - y1)
        seg_lengths.append(total)
    if total < 1e-9:
        return points[:]

    mapped: List[Tuple[float, float]] = []
    for idx in range(len(pts)):
        frac = seg_lengths[idx] / total
        dist = frac * perim_rect
        dist_mod = dist % perim_rect
        if dist_mod <= width:
            mapped.append((min_x + dist_mod, min_y))
        elif dist_mod <= width + height:
            mapped.append((max_x, min_y + (dist_mod - width)))
        elif dist_mod <= 2 * width + height:
            mapped.append((max_x - (dist_mod - (width + height)), max_y))
        else:
            mapped.append((min_x, max_y - (dist_mod - (2 * width + height))))

    if closed:
        mapped.append(mapped[0])

    return mapped


def _compute_straightened_points(pts: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    return _rectangle_map(pts)


def straighten_polygon(app: "MeasureAppGUI") -> None:
    """Straighten the selected polygon into its bounding rectangle."""
    if app.selected_polygon is None:
        if messagebox:
            messagebox.showwarning("Warning", "Select a polygon first.")
        return
    poly = app.polygons[app.selected_polygon]
    if len(poly.points) < 3:
        if messagebox:
            messagebox.showwarning("Warning", "Polygon must have at least 3 points.")
        return
    proposed = _compute_straightened_points(poly.points)
    if proposed == poly.points:
        return
    app._straighten_backup = poly.points.copy()
    poly.points = proposed
    poly.compute_metrics()
    try:
        if hasattr(app, "update_info_label"):
            app.update_info_label()
    except Exception:
        pass
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
    try:
        if hasattr(app, "update_info_label"):
            app.update_info_label()
    except Exception:
        pass
    app.redraw()

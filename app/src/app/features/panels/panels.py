from __future__ import annotations

import math
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

try:
    from tkinter import messagebox
except Exception:  # pragma: no cover
    messagebox = None  # type: ignore

try:
    from ...core.model import point_in_polygon
except Exception:
    from core.model import point_in_polygon

if TYPE_CHECKING:
    try:
        from ...gui_client import MeasureAppGUI  # type: ignore
    except Exception:
        from gui_client import MeasureAppGUI  # type: ignore

EPSILON = 1e-9


def _rect_corners(x: float, y: float, w: float, h: float) -> List[Tuple[float, float]]:
    return [
        (x, y),
        (x + w, y),
        (x + w, y + h),
        (x, y + h),
    ]


def _point_in_rect(pt: Tuple[float, float], rect: List[Tuple[float, float]]) -> bool:
    x, y = pt
    x0, y0 = rect[0]
    x2, y2 = rect[2]
    return (x0 - EPSILON) <= x <= (x2 + EPSILON) and (y0 - EPSILON) <= y <= (y2 + EPSILON)


def _segments_intersect(a1: Tuple[float, float], a2: Tuple[float, float],
                        b1: Tuple[float, float], b2: Tuple[float, float]) -> bool:
    def orientation(p, q, r):
        val = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
        if abs(val) < EPSILON:
            return 0
        return 1 if val > 0 else 2

    def on_segment(p, q, r):
        return (min(p[0], r[0]) - EPSILON <= q[0] <= max(p[0], r[0]) + EPSILON and
                min(p[1], r[1]) - EPSILON <= q[1] <= max(p[1], r[1]) + EPSILON)

    o1 = orientation(a1, a2, b1)
    o2 = orientation(a1, a2, b2)
    o3 = orientation(b1, b2, a1)
    o4 = orientation(b1, b2, a2)

    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and on_segment(a1, b1, a2):
        return True
    if o2 == 0 and on_segment(a1, b2, a2):
        return True
    if o3 == 0 and on_segment(b1, a1, b2):
        return True
    if o4 == 0 and on_segment(b1, a2, b2):
        return True
    return False


def _rect_polygon_overlap(rect: List[Tuple[float, float]], polygon: List[Tuple[float, float]]) -> bool:
    # Any polygon vertex inside rectangle
    if any(_point_in_rect(pt, rect) for pt in polygon):
        return True
    # Any rectangle corner inside polygon
    if any(point_in_polygon(pt, polygon) for pt in rect):
        return True
    # Edge intersection checks
    rect_edges = list(zip(rect, rect[1:] + rect[:1]))
    poly_edges = list(zip(polygon, polygon[1:] + polygon[:1]))
    for e1 in rect_edges:
        for e2 in poly_edges:
            if _segments_intersect(e1[0], e1[1], e2[0], e2[1]):
                return True
    return False


def _estimate_overlap_fraction(rect: List[Tuple[float, float]], polygon: List[Tuple[float, float]],
                                samples: int = 8) -> float:
    x0, y0 = rect[0]
    x2, y2 = rect[2]
    width = max(x2 - x0, EPSILON)
    height = max(y2 - y0, EPSILON)
    inside = 0
    total = samples * samples
    for i in range(samples):
        for j in range(samples):
            px = x0 + (i + 0.5) * width / samples
            py = y0 + (j + 0.5) * height / samples
            if point_in_polygon((px, py), polygon):
                inside += 1
    return inside / total if total else 0.0


def _classify_tile(rect: List[Tuple[float, float]], polygon: List[Tuple[float, float]]) -> Tuple[str, float]:
    if all(point_in_polygon(corner, polygon) for corner in rect):
        return "full", 1.0
    if not _rect_polygon_overlap(rect, polygon):
        return "excluded", 0.0
    overlap_fraction = _estimate_overlap_fraction(rect, polygon)
    if overlap_fraction <= EPSILON:
        return "excluded", 0.0
    return "partial", overlap_fraction


def _generate_layout(poly_pts: List[Tuple[float, float]], panel_w_px: float, panel_h_px: float,
                     offset_x: float, offset_y: float) -> Dict[str, object]:
    xs = [p[0] for p in poly_pts]
    ys = [p[1] for p in poly_pts]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    col_start = math.floor((min_x - offset_x) / panel_w_px)
    col_end = math.ceil((max_x - offset_x) / panel_w_px)
    row_start = math.floor((min_y - offset_y) / panel_h_px)
    row_end = math.ceil((max_y - offset_y) / panel_h_px)

    tiles: List[Dict[str, object]] = []
    partial_overlaps: List[float] = []
    full_count = 0
    partial_count = 0

    for col in range(col_start, col_end):
        rx = col * panel_w_px + offset_x
        for row in range(row_start, row_end):
            ry = row * panel_h_px + offset_y
            rect = _rect_corners(rx, ry, panel_w_px, panel_h_px)
            kind, overlap = _classify_tile(rect, poly_pts)
            if kind == "full":
                full_count += 1
                tiles.append({"points": rect, "type": "full"})
            elif kind == "partial":
                partial_count += 1
                partial_overlaps.append(overlap)
                tiles.append({"points": rect, "type": "partial", "overlap": overlap})

    return {
        "tiles": tiles,
        "full_count": full_count,
        "partial_count": partial_count,
        "partial_overlaps": partial_overlaps,
    }


def optimize_panels(app: "MeasureAppGUI") -> None:
    if app.selected_polygon is None:
        if messagebox:
            messagebox.showwarning("Warning", "Select a polygon first.")
        return
    if app.scale_factor <= 0:
        if messagebox:
            messagebox.showwarning("Warning", "Set a valid scale before optimising panels.")
        return

    poly = app.polygons[app.selected_polygon]
    panel_w_real = float(app.config.get('panel_width', 1.0))
    panel_h_real = float(app.config.get('panel_height', 1.0))

    if panel_w_real <= 0 or panel_h_real <= 0:
        if messagebox:
            messagebox.showwarning("Warning", "Panel dimensions must be greater than zero.")
        return

    panel_w_px = panel_w_real / app.scale_factor
    panel_h_px = panel_h_real / app.scale_factor

    if panel_w_px <= EPSILON or panel_h_px <= EPSILON:
        if messagebox:
            messagebox.showwarning("Warning", "Panel dimensions are too small for the current scale.")
        return

    offsets = [(0.0, 0.0)]
    offsets.append((panel_w_px / 2.0, 0.0))
    offsets.append((0.0, panel_h_px / 2.0))
    offsets.append((panel_w_px / 2.0, panel_h_px / 2.0))

    best_layout: Optional[Dict[str, object]] = None
    best_metric: Optional[Tuple[int, int, float]] = None

    for off_x, off_y in offsets:
        layout = _generate_layout(poly.points, panel_w_px, panel_h_px, off_x, off_y)
        if layout["full_count"] == 0 and layout["partial_count"] == 0:
            continue
        partial_overlaps = layout["partial_overlaps"]
        tile_area_real = panel_w_real * panel_h_real
        partial_waste_area = tile_area_real * sum(1.0 - frac for frac in partial_overlaps)
        polygon_area_real = poly.area_px * (app.scale_factor ** 2)
        waste_pct = 0.0
        if polygon_area_real > EPSILON:
            waste_pct = (partial_waste_area / polygon_area_real) * 100.0
        layout["waste_pct"] = waste_pct
        metric = (-layout["full_count"], layout["partial_count"], waste_pct)
        if best_metric is None or metric < best_metric:
            best_layout = layout
            best_metric = metric

    if best_layout is None:
        if messagebox:
            messagebox.showinfo("Optimize Panels", "No tiles could be placed for the selected polygon.")
        app.panel_tiles_overlay = None
        app.update_info_label()
        app.redraw()
        return

    full_count = best_layout["full_count"]
    partial_count = best_layout["partial_count"]
    waste_pct = best_layout.get("waste_pct", 0.0)

    app.panel_tiles_overlay = {
        "polygon_index": app.selected_polygon,
        "tiles": best_layout["tiles"],
        "full_count": full_count,
        "partial_count": partial_count,
        "waste_pct": waste_pct,
    }

    if hasattr(app, "show_status_message"):
        app.show_status_message(
            f"Tile optimisation - Full: {full_count}, Partial: {partial_count}, Waste: {waste_pct:.1f}%"
        )

    app.update_info_label()
    app.redraw()


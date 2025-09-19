from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .gui_client import MeasureAppGUI


def on_drag_start(app: "MeasureAppGUI", event) -> None:
    if app.image is None or app.selected_polygon is None:
        return
    if app.scale_mode or app.draw_mode:
        return
    x = app.canvas.canvasx(event.x)
    y = app.canvas.canvasy(event.y)
    poly = app.polygons[app.selected_polygon]
    pts = poly.points
    n = len(pts)
    for i in range(n):
        px, py = pts[i]
        canvas_x = px * app.zoom_level
        canvas_y = py * app.zoom_level
        if abs(x - canvas_x) <= 8 and abs(y - canvas_y) <= 8:
            x_prev, y_prev = pts[i - 1]
            x_next, y_next = pts[(i + 1) % n]
            v1 = (px - x_prev, py - y_prev)
            v2 = (x_next - px, y_next - py)
            dot = v1[0] * v2[0] + v1[1] * v2[1]
            det = v1[0] * v2[1] - v1[1] * v2[0]
            ang = math.atan2(det, dot)
            deg = abs(math.degrees(ang))
            if abs(deg - 90) >= 8:
                app.dragging = True
                app.drag_point_index = i
                app.drag_start_x = x
                app.drag_start_y = y
                app.canvas.config(cursor="hand2")
                break


def on_drag_move(app: "MeasureAppGUI", event) -> None:
    if not app.dragging or app.drag_point_index is None:
        return
    x = app.canvas.canvasx(event.x)
    y = app.canvas.canvasy(event.y)
    poly = app.polygons[app.selected_polygon]
    new_x = x / app.zoom_level
    new_y = y / app.zoom_level
    poly.points[app.drag_point_index] = (new_x, new_y)
    poly.compute_metrics()
    app.redraw()
    app.update_info_label()


def on_drag_end(app: "MeasureAppGUI", event) -> None:
    if app.dragging:
        app.dragging = False
        app.drag_point_index = None
        app.canvas.config(cursor="")
        app.redraw()
        app.update_info_label()


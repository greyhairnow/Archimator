from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

try:
    from tkinter import messagebox, simpledialog
except Exception:  # pragma: no cover
    messagebox = None  # type: ignore
    simpledialog = None  # type: ignore

if TYPE_CHECKING:
    from .gui_client import MeasureAppGUI

try:
    from .model import PolygonData
except Exception:
    from model import PolygonData


def set_draw_mode(app: "MeasureAppGUI") -> None:
    if app.image is None:
        if messagebox:
            messagebox.showwarning("Warning", "Load a PDF first.")
        return
    app.draw_mode = True
    app.scale_mode = False
    app.current_polygon.clear()
    if messagebox:
        messagebox.showinfo(
            "Draw Polygon",
            "Click points to define the polygon. Click near the first point to finish.",
        )
    app.canvas.bind("<Motion>", app.on_canvas_motion)


def draw_on_canvas_click(app: "MeasureAppGUI", event) -> bool:
    if not app.draw_mode:
        return False
    x = app.canvas.canvasx(event.x)
    y = app.canvas.canvasy(event.y)
    app.current_polygon.append((x / app.zoom_level, y / app.zoom_level))
    if len(app.current_polygon) >= 3:
        fx, fy = app.current_polygon[0]
        if abs((x / app.zoom_level) - fx) < 5 and abs((y / app.zoom_level) - fy) < 5:
            app.current_polygon[-1] = (fx, fy)
            finish_polygon(app)
            return True
    app.redraw()
    return True


def finish_polygon(app: "MeasureAppGUI") -> None:
    if len(app.current_polygon) < 3:
        app.current_polygon.clear()
        return
    poly = PolygonData(points=app.current_polygon.copy())
    poly.compute_metrics()
    room_id = (simpledialog.askstring("Metadata", "Enter Room ID:") or '') if simpledialog else ''
    room_name = (simpledialog.askstring("Metadata", "Enter Room Name:") or '') if simpledialog else ''
    poly.metadata = {'id': room_id, 'name': room_name}
    app.polygons.append(poly)
    app.current_polygon.clear()
    app.draw_mode = False
    app.selected_polygon = len(app.polygons) - 1
    app.update_info_label()
    app.redraw()


from __future__ import annotations

import math
from typing import TYPE_CHECKING

try:
    from tkinter import messagebox, simpledialog
except Exception:  # pragma: no cover
    messagebox = None  # type: ignore
    simpledialog = None  # type: ignore

if TYPE_CHECKING:
    # When packaged the module lives under app.src.app.features.editing
    try:
        from ...gui_client import MeasureAppGUI  # type: ignore
    except Exception:  # script-run fallback
        from gui_client import MeasureAppGUI  # type: ignore

try:
    from ...core.model import PolygonData  # packaged import
except Exception:
    from core.model import PolygonData  # script-run fallback


# Visual parameters for interactive drawing
DRAW_MARKER_RADIUS: int = 8
FIRST_MARKER_EXTRA: int = 2
DRAW_MARKER_FILL: str = 'red'
DRAW_MARKER_OUTLINE: str = 'white'
DRAW_MARKER_OUTLINE_WIDTH: int = 4
DRAW_PREVIEW_COLOR: str = 'red'
DRAW_PREVIEW_DASH: tuple[int, int] = (4, 4)
DRAW_PREVIEW_WIDTH: int = 4
CLOSE_THRESHOLD_PX: int = 10


def clear_draw_preview(app: "MeasureAppGUI") -> None:
    line_id = getattr(app, 'draw_preview_line_id', None)
    if line_id is not None:
        try:
            app.canvas.delete(line_id)
        except Exception:
            pass
        app.draw_preview_line_id = None


def draw_on_motion(app: "MeasureAppGUI", event) -> None:
    if not app.draw_mode or not app.current_polygon:
        clear_draw_preview(app)
        return
    last_x, last_y = app.current_polygon[-1]
    x1 = last_x * app.zoom_level
    y1 = last_y * app.zoom_level
    x2 = app.canvas.canvasx(event.x)
    y2 = app.canvas.canvasy(event.y)
    line_id = getattr(app, 'draw_preview_line_id', None)
    if line_id is None:
        app.draw_preview_line_id = app.canvas.create_line(
            x1,
            y1,
            x2,
            y2,
            fill=DRAW_PREVIEW_COLOR,
            width=DRAW_PREVIEW_WIDTH,
            dash=DRAW_PREVIEW_DASH,
        )
    else:
        try:
            app.canvas.coords(line_id, x1, y1, x2, y2)
        except Exception:
            app.draw_preview_line_id = app.canvas.create_line(
                x1,
                y1,
                x2,
                y2,
                fill=DRAW_PREVIEW_COLOR,
                width=DRAW_PREVIEW_WIDTH,
                dash=DRAW_PREVIEW_DASH,
            )


def set_draw_mode(app: "MeasureAppGUI") -> None:
    if app.image is None:
        if messagebox:
            messagebox.showwarning("Warning", "Load a PDF first.")
        return
    app.draw_mode = True
    app.scale_mode = False
    app.current_polygon.clear()
    clear_draw_preview(app)
    app.canvas.config(cursor="tcross")
    if messagebox:
        messagebox.showinfo(
            "Draw Polygon",
            "Click points to define the polygon. Click the first point again to finish.",
        )
    app.canvas.bind("<Motion>", app.on_canvas_motion)


def draw_on_canvas_click(app: "MeasureAppGUI", event) -> bool:
    if not app.draw_mode:
        return False
    canvas_x = app.canvas.canvasx(event.x)
    canvas_y = app.canvas.canvasy(event.y)
    norm_x = canvas_x / app.zoom_level
    norm_y = canvas_y / app.zoom_level

    closing = False
    if app.current_polygon:
        first_x, first_y = app.current_polygon[0]
        first_canvas_x = first_x * app.zoom_level
        first_canvas_y = first_y * app.zoom_level
        dist = math.hypot(canvas_x - first_canvas_x, canvas_y - first_canvas_y)
        if dist <= CLOSE_THRESHOLD_PX and len(app.current_polygon) >= 3:
            closing = True

    clear_draw_preview(app)

    if closing:
        finish_polygon(app)
        return True

    app.current_polygon.append((norm_x, norm_y))
    app.redraw()
    return True


def finish_polygon(app: "MeasureAppGUI") -> None:
    if len(app.current_polygon) < 3:
        app.current_polygon.clear()
        app.draw_mode = False
        clear_draw_preview(app)
        app.canvas.config(cursor="")
        app.hide_zoom_preview()
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
    clear_draw_preview(app)
    app.canvas.config(cursor="")
    app.hide_zoom_preview()
    app.update_info_label()
    app.redraw()

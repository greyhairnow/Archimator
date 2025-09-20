
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


# Palette for completed polygon overlays
POLYGON_FILL_COLORS: tuple[str, ...] = (
    '#9bd6ff',  # pale blue
    '#c5f5c9',  # pale green
    '#ffe0b3',  # pale orange
    '#f7c6ff',  # pale violet
)


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


def _prompt_room_metadata(app: "MeasureAppGUI") -> tuple[str, str] | None:
    """Show a single dialog to collect Room ID and Name with basic validation.
    Returns (id, name) or None if cancelled.
    """
    try:
        import tkinter as tk
        from tkinter import simpledialog as sd
    except Exception:
        return ("", "")

    class MetaDialog(sd.Dialog):
        def body(self, master):  # type: ignore[override]
            tk.Label(master, text="Room ID:").grid(row=0, column=0, sticky="e")
            tk.Label(master, text="Room Name:").grid(row=1, column=0, sticky="e")
            self.id_var = tk.StringVar()
            self.name_var = tk.StringVar()
            self.id_entry = tk.Entry(master, textvariable=self.id_var)
            self.name_entry = tk.Entry(master, textvariable=self.name_var)
            self.id_entry.grid(row=0, column=1, padx=6, pady=4)
            self.name_entry.grid(row=1, column=1, padx=6, pady=4)
            return self.id_entry

        def validate(self) -> bool:  # type: ignore[override]
            rid = self.id_var.get().strip()
            rname = self.name_var.get().strip()
            if not rid or not rname:
                try:
                    if messagebox:
                        messagebox.showwarning("Validation", "Room ID and Name are required.")
                except Exception:
                    pass
                return False
            return True

        def apply(self) -> None:  # type: ignore[override]
            self.result = (self.id_var.get().strip(), self.name_var.get().strip())

    dlg = MetaDialog(app.root, title="Room Metadata")
    return getattr(dlg, "result", None)


def edit_polygon_metadata(app: "MeasureAppGUI") -> None:
    """Edit metadata for the currently selected polygon using the same dialog."""
    if app.selected_polygon is None:
        if messagebox:
            messagebox.showwarning("Warning", "No polygon selected.")
        return
    poly = app.polygons[app.selected_polygon]
    try:
        import tkinter as tk
        from tkinter import simpledialog as sd
    except Exception:
        return

    class MetaDialog(sd.Dialog):
        def body(self, master):  # type: ignore[override]
            tk.Label(master, text="Room ID:").grid(row=0, column=0, sticky="e")
            tk.Label(master, text="Room Name:").grid(row=1, column=0, sticky="e")
            self.id_var = tk.StringVar(value=str(poly.metadata.get('id', '')))
            self.name_var = tk.StringVar(value=str(poly.metadata.get('name', '')))
            self.id_entry = tk.Entry(master, textvariable=self.id_var)
            self.name_entry = tk.Entry(master, textvariable=self.name_var)
            self.id_entry.grid(row=0, column=1, padx=6, pady=4)
            self.name_entry.grid(row=1, column=1, padx=6, pady=4)
            return self.id_entry

        def validate(self) -> bool:  # type: ignore[override]
            rid = self.id_var.get().strip()
            rname = self.name_var.get().strip()
            if not rid or not rname:
                try:
                    if messagebox:
                        messagebox.showwarning("Validation", "Room ID and Name are required.")
                except Exception:
                    pass
                return False
            return True

        def apply(self) -> None:  # type: ignore[override]
            self.result = (self.id_var.get().strip(), self.name_var.get().strip())

    dlg = MetaDialog(app.root, title="Edit Room Metadata")
    result = getattr(dlg, "result", None)
    if result is None:
        return
    room_id, room_name = result
    poly.metadata = {'id': room_id, 'name': room_name}
    app.update_info_label()
    app.redraw()


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
    result = _prompt_room_metadata(app)
    if result is None:
        # If cancelled, default to empty strings
        room_id, room_name = "", ""
    else:
        room_id, room_name = result
    poly.metadata = {'id': room_id.strip(), 'name': room_name.strip()}
    fill_index = len(app.polygons) % len(POLYGON_FILL_COLORS)
    poly.fill_color = POLYGON_FILL_COLORS[fill_index]
    app.polygons.append(poly)
    app.current_polygon.clear()
    app.draw_mode = False
    app.selected_polygon = len(app.polygons) - 1
    clear_draw_preview(app)
    app.canvas.config(cursor="")
    app.hide_zoom_preview()
    app.update_info_label()
    app.redraw()

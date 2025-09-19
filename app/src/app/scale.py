from __future__ import annotations

import math
from typing import Optional, TYPE_CHECKING

try:
    import tkinter as tk
    from tkinter import simpledialog, messagebox, ttk
except Exception:  # pragma: no cover
    tk = None  # type: ignore
    simpledialog = None  # type: ignore
    messagebox = None  # type: ignore

if TYPE_CHECKING:
    from .gui_client import MeasureAppGUI


def set_scale_mode(app: "MeasureAppGUI") -> None:
    if app.image is None:
        if messagebox:
            messagebox.showwarning("Warning", "Load a PDF first.")
        return
    app.scale_mode = True
    app.draw_mode = False
    app.scale_points.clear()
    if app.scale_marker_id is not None:
        app.canvas.delete(app.scale_marker_id)
        app.scale_marker_id = None
    if app.scale_line_id is not None:
        app.canvas.delete(app.scale_line_id)
        app.scale_line_id = None
    clear_scale_preview(app)
    app.canvas.config(cursor="crosshair")
    app.root.bind("<Escape>", lambda e: cancel_scale_mode(app))
    if messagebox:
        messagebox.showinfo(
            "Set Unit/Scale",
            "Click two points on a known distance.\nA target cursor will appear for precise placement.\nPress Esc at any time to cancel.",
        )
    app.canvas.bind("<Motion>", lambda e: scale_on_motion(app, e))


def clear_scale_preview(app: "MeasureAppGUI") -> None:
    if app.scale_preview_line_id is not None:
        app.canvas.delete(app.scale_preview_line_id)
        app.scale_preview_line_id = None


def exit_scale_mode(app: "MeasureAppGUI") -> None:
    app.scale_mode = False
    app.canvas.config(cursor="")
    clear_scale_preview(app)
    app.hide_zoom_preview()
    app.root.unbind("<Escape>")
    app.scale_line_id = None
    app.scale_marker_id = None


def cancel_scale_mode(app: "MeasureAppGUI") -> None:
    if not app.scale_mode:
        return
    if app.scale_marker_id is not None:
        app.canvas.delete(app.scale_marker_id)
        app.scale_marker_id = None
    if app.scale_line_id is not None:
        app.canvas.delete(app.scale_line_id)
        app.scale_line_id = None
    app.scale_points.clear()
    exit_scale_mode(app)
    app.redraw()


def _prompt_scale_unit(app: "MeasureAppGUI") -> Optional[tuple[str, float]]:
    """Show a single dialog to choose unit and enter length; returns (unit, length)."""
    if simpledialog is None or tk is None:
        return ("units", 1.0)

    class UnitLengthDialog(simpledialog.Dialog):
        def __init__(self, parent, title: str = "Set Unit/Scale"):
            self.selected_unit: Optional[str] = None
            self.entered_length: Optional[float] = None
            super().__init__(parent, title)

        def body(self, master):
            tk.Label(master, text="Unit:").grid(row=0, column=0, sticky="e", padx=6, pady=6)
            tk.Label(master, text="Length:").grid(row=1, column=0, sticky="e", padx=6, pady=6)

            units = ["mm", "cm", "m", "in", "ft", "yd", "km", "mi"]
            self.unit_var = tk.StringVar(value="m")
            self.unit_combo = ttk.Combobox(master, textvariable=self.unit_var, values=units, state="readonly", width=8)
            self.unit_combo.grid(row=0, column=1, sticky="w", padx=6, pady=6)
            self.unit_combo.current(2)

            self.len_var = tk.StringVar(value="1.0")
            self.len_entry = tk.Entry(master, textvariable=self.len_var, width=12)
            self.len_entry.grid(row=1, column=1, sticky="w", padx=6, pady=6)
            return self.len_entry

        def validate(self):
            unit = self.unit_var.get().strip()
            if not unit:
                if messagebox:
                    messagebox.showerror("Set Unit/Scale", "Please choose a unit.")
                return False
            try:
                length = float(self.len_var.get())
            except ValueError:
                if messagebox:
                    messagebox.showerror("Set Unit/Scale", "Enter a numeric value for the length.")
                return False
            if length <= 0:
                if messagebox:
                    messagebox.showerror("Set Unit/Scale", "Length must be greater than zero.")
                return False
            self.selected_unit = unit
            self.entered_length = length
            return True

        def apply(self):
            pass

    dlg = UnitLengthDialog(app.root)
    if dlg.selected_unit is None or dlg.entered_length is None:
        return None
    return dlg.selected_unit, dlg.entered_length


def _prompt_scale_length(app: "MeasureAppGUI", unit: str) -> Optional[float]:
    if simpledialog is None:
        return 1.0
    while True:
        prompt = f"Enter real-world length between the two points (in {unit}):"
        real_len_str = simpledialog.askstring("Set Unit/Scale", prompt)
        if real_len_str is None:
            return None
        try:
            real_len = float(real_len_str)
        except (TypeError, ValueError):
            if messagebox:
                messagebox.showerror("Set Unit/Scale", "Enter a numeric value for the length.")
            continue
        if real_len <= 0:
            if messagebox:
                messagebox.showerror("Set Unit/Scale", "Length must be greater than zero.")
            continue
        return real_len


def scale_on_motion(app: "MeasureAppGUI", event) -> None:
    if not (app.scale_mode or app.draw_mode):
        app.hide_zoom_preview()
        clear_scale_preview(app)
        return
    app.show_zoom_preview(event.x, event.y)
    if app.scale_mode and len(app.scale_points) == 1:
        px, py = app.scale_points[0]
        x1 = px * app.zoom_level
        y1 = py * app.zoom_level
        x2 = app.canvas.canvasx(event.x)
        y2 = app.canvas.canvasy(event.y)
        if app.scale_preview_line_id is None:
            app.scale_preview_line_id = app.canvas.create_line(
                x1, y1, x2, y2,
                fill='blue', width=2, dash=(4, 4)
            )
        else:
            app.canvas.coords(app.scale_preview_line_id, x1, y1, x2, y2)
    else:
        clear_scale_preview(app)


def scale_on_canvas_click(app: "MeasureAppGUI", event) -> bool:
    """Handle a click in scale mode. Return True if handled."""
    if not app.scale_mode:
        return False
    x = app.canvas.canvasx(event.x)
    y = app.canvas.canvasy(event.y)
    app.scale_points.append((x / app.zoom_level, y / app.zoom_level))
    if len(app.scale_points) == 1:
        if app.scale_marker_id is not None:
            app.canvas.delete(app.scale_marker_id)
        px, py = app.scale_points[0]
        px *= app.zoom_level
        py *= app.zoom_level
        app.scale_marker_id = app.canvas.create_oval(
            px - 12, py - 12, px + 12, py + 12,
            fill='blue', outline='black', width=3
        )
        app.redraw()
        return True
    if len(app.scale_points) == 2:
        px1, py1 = app.scale_points[0]
        px2, py2 = app.scale_points[1]
        px1_canvas, py1_canvas = px1 * app.zoom_level, py1 * app.zoom_level
        px2_canvas, py2_canvas = px2 * app.zoom_level, py2 * app.zoom_level
        if app.scale_marker_id is not None:
            app.canvas.delete(app.scale_marker_id)
            app.scale_marker_id = None
        clear_scale_preview(app)
        dx = px2 - px1
        dy = py2 - py1
        pixel_dist = math.hypot(dx, dy)
        if pixel_dist == 0:
            if messagebox:
                messagebox.showerror("Set Unit/Scale", "Select two distinct points to set the scale.")
            app.scale_points.clear()
            app.redraw()
            return True
        app.scale_line_id = app.canvas.create_line(
            px1_canvas, py1_canvas, px2_canvas, py2_canvas,
            fill='purple', width=4, dash=(6, 2)
        )
        app.canvas.create_oval(px1_canvas - 8, py1_canvas - 8, px1_canvas + 8, py1_canvas + 8,
                               fill='purple', outline='black', width=2)
        app.canvas.create_oval(px2_canvas - 8, py2_canvas - 8, px2_canvas + 8, py2_canvas + 8,
                               fill='purple', outline='black', width=2)
        unit_len = _prompt_scale_unit(app)
        if unit_len is None:
            cancel_scale_mode(app)
            return True
        unit, real_len = unit_len
        app.scale_factor = real_len / pixel_dist
        app.scale_unit = unit
        app.scale_label.config(text=f"Scale: {app.scale_factor:.4f} {app.scale_unit}/pixel")
        app.scale_artifact = {
            'points': app.scale_points.copy(),
            'real_length': real_len,
            'pixel_length': pixel_dist,
            'unit': app.scale_unit,
            'scale_factor': app.scale_factor
        }
        app.scale_points.clear()
        exit_scale_mode(app)
        app.update_info_label()
        app.redraw()
        return True
    return False

from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image
try:
    import tkinter as tk
except Exception:  # pragma: no cover - preview only in GUI environments
    tk = None  # type: ignore

if TYPE_CHECKING:
    from .gui_client import MeasureAppGUI


def show_zoom_preview(app: "MeasureAppGUI", x: float, y: float) -> None:
    if app.image is None:
        return
    src = app.display_image if app.display_image is not None else app.image
    if src is None:
        return
    img_x = int(app.canvas.canvasx(x))
    img_y = int(app.canvas.canvasy(y))
    w, h = src.size
    if w <= 0 or h <= 0:
        return
    img_x = max(0, min(img_x, w - 1))
    img_y = max(0, min(img_y, h - 1))
    region_size = max(20, min(80, app.zoom_preview_size // 2 * 2))
    half = region_size // 2
    left = max(img_x - half, 0)
    upper = max(img_y - half, 0)
    right = min(img_x + half, w)
    lower = min(img_y + half, h)
    if right <= left:
        right = min(left + 1, w)
        left = max(0, right - 1)
    if lower <= upper:
        lower = min(upper + 1, h)
        upper = max(0, lower - 1)
    crop = src.crop((left, upper, right, lower))
    zoomed = crop.resize((app.zoom_preview_size, app.zoom_preview_size), Image.NEAREST)
    from PIL import ImageTk
    preview_img = ImageTk.PhotoImage(zoomed)
    if app.zoom_preview_win is None or not app.zoom_preview_win.winfo_exists():
        if tk is None:
            return
        app.zoom_preview_win = tk.Toplevel(app.root)
        app.zoom_preview_win.title("Zoom Preview")
        app.zoom_preview_win.resizable(False, False)
        app.zoom_preview_win.transient(app.root)
        app.zoom_preview_label = tk.Label(app.zoom_preview_win, image=preview_img)
        app.zoom_preview_label.image = preview_img
        app.zoom_preview_label.pack()
    else:
        app.zoom_preview_label.config(image=preview_img)
        app.zoom_preview_label.image = preview_img
    abs_x = app.root.winfo_pointerx()
    abs_y = app.root.winfo_pointery()
    app.zoom_preview_win.geometry(f"+{abs_x+20}+{abs_y+20}")


def hide_zoom_preview(app: "MeasureAppGUI") -> None:
    if app.zoom_preview_win and app.zoom_preview_win.winfo_exists():
        app.zoom_preview_win.destroy()
        app.zoom_preview_win = None
        app.zoom_preview_label = None


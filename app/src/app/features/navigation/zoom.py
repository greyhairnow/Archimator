from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .gui_client import MeasureAppGUI

from PIL import Image

ZOOM_MIN = 0.01
ZOOM_MAX = 64.0
ZOOM_STEP = 1.25


def zoom_in(app: "MeasureAppGUI") -> None:
    set_zoom(app, app.zoom_level * ZOOM_STEP)


def zoom_out(app: "MeasureAppGUI") -> None:
    set_zoom(app, app.zoom_level / ZOOM_STEP)


def set_zoom(app: "MeasureAppGUI", zoom: float) -> None:
    if app.image is None:
        return

    new_zoom = max(ZOOM_MIN, min(zoom, ZOOM_MAX))
    canvas = app.canvas
    canvas.update_idletasks()

    view_w = max(canvas.winfo_width(), 1)
    view_h = max(canvas.winfo_height(), 1)

    pointer_widget_x = canvas.winfo_pointerx() - canvas.winfo_rootx()
    pointer_widget_y = canvas.winfo_pointery() - canvas.winfo_rooty()
    pointer_inside = 0 <= pointer_widget_x <= view_w and 0 <= pointer_widget_y <= view_h

    old_zoom = max(app.zoom_level, ZOOM_MIN)

    if pointer_inside:
        canvas_x_before = canvas.canvasx(pointer_widget_x)
        canvas_y_before = canvas.canvasy(pointer_widget_y)
        image_x = canvas_x_before / old_zoom
        image_y = canvas_y_before / old_zoom
    else:
        canvas_x_before = canvas.canvasx(view_w / 2)
        canvas_y_before = canvas.canvasy(view_h / 2)
        image_x = canvas_x_before / old_zoom
        image_y = canvas_y_before / old_zoom

    app.zoom_level = new_zoom

    img = app.image
    if app.image_rotation != 0:
        img = img.rotate(-app.image_rotation, expand=True)

    new_width = max(1, int(round(img.width * new_zoom)))
    new_height = max(1, int(round(img.height * new_zoom)))

    try:
        resample = Image.Resampling.LANCZOS
    except AttributeError:
        resample = Image.LANCZOS
    resized = img.resize((new_width, new_height), resample)

    from PIL import ImageTk

    app.photo = ImageTk.PhotoImage(resized)
    app.display_image = resized
    canvas.config(scrollregion=(0, 0, resized.width, resized.height))

    new_canvas_x = image_x * new_zoom
    new_canvas_y = image_y * new_zoom

    if pointer_inside:
        target_left = new_canvas_x - pointer_widget_x
        target_top = new_canvas_y - pointer_widget_y
    else:
        target_left = new_canvas_x - view_w / 2
        target_top = new_canvas_y - view_h / 2

    max_left = max(0, resized.width - view_w)
    max_top = max(0, resized.height - view_h)

    left = 0 if resized.width <= view_w else max(0, min(target_left, max_left))
    top = 0 if resized.height <= view_h else max(0, min(target_top, max_top))

    if resized.width > 0:
        canvas.xview_moveto(left / resized.width)
    if resized.height > 0:
        canvas.yview_moveto(top / resized.height)

    app.redraw()

    preview_win = getattr(app, 'zoom_preview_win', None)
    if preview_win and preview_win.winfo_exists():
        last_pointer = getattr(app, '_last_pointer_canvas', None)
        if last_pointer:
            px, py = last_pointer
        else:
            px, py = view_w / 2, view_h / 2
        app.show_zoom_preview(px, py)

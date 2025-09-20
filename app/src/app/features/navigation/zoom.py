from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .gui_client import MeasureAppGUI

from PIL import Image


def zoom_in(app: "MeasureAppGUI") -> None:
    app.set_zoom(app.zoom_level * 1.2)


def zoom_out(app: "MeasureAppGUI") -> None:
    app.set_zoom(app.zoom_level / 1.2)


def set_zoom(app: "MeasureAppGUI", zoom: float) -> None:
    if app.image is None:
        return
    zoom = max(0.2, min(zoom, 5.0))
    app.zoom_level = zoom
    img = app.image
    if app.image_rotation != 0:
        img = img.rotate(-app.image_rotation, expand=True)
    new_size = (int(img.width * app.zoom_level), int(img.height * app.zoom_level))
    try:
        resample = Image.Resampling.LANCZOS
    except AttributeError:
        resample = Image.LANCZOS
    img = img.resize(new_size, resample)
    from PIL import ImageTk

    app.photo = ImageTk.PhotoImage(img)
    app.display_image = img
    app.canvas.config(scrollregion=(0, 0, img.width, img.height))
    app.redraw()



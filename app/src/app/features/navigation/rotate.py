from __future__ import annotations

import math
from typing import TYPE_CHECKING, Tuple

from PIL import Image

if TYPE_CHECKING:
    from .gui_client import MeasureAppGUI


def rotate_left(app: "MeasureAppGUI") -> None:
    if app.image is None:
        return
    app.image_rotation = (app.image_rotation - 90) % 360
    apply_rotation(app)


def rotate_right(app: "MeasureAppGUI") -> None:
    if app.image is None:
        return
    app.image_rotation = (app.image_rotation + 90) % 360
    apply_rotation(app)


def apply_rotation(app: "MeasureAppGUI") -> None:
    if app.image is None:
        return
    img = app.image.rotate(-app.image_rotation, expand=True)
    if app.zoom_level != 1.0:
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

    if app.image_rotation != 0 and app.image is not None:
        w, h = app.image.size
        temp_rotated = app.image.rotate(-app.image_rotation, expand=True)
        new_w, new_h = temp_rotated.size
        offset_x = (new_w - w) / 2
        offset_y = (new_h - h) / 2

        def rotate_point(px: float, py: float, width: float, height: float, angle: int) -> Tuple[float, float]:
            angle_rad = math.radians(angle)
            cx, cy = width / 2, height / 2
            dx, dy = px - cx, py - cy
            rx = dx * math.cos(angle_rad) - dy * math.sin(angle_rad)
            ry = dx * math.sin(angle_rad) + dy * math.cos(angle_rad)
            return rx + cx, ry + cy

        for poly in app.polygons:
            transformed = [rotate_point(x, y, w, h, app.image_rotation) for (x, y) in poly.points]
            transformed = [(x + offset_x, y + offset_y) for (x, y) in transformed]
            poly.points = transformed
            poly.compute_metrics()

        app.current_polygon = [rotate_point(x, y, w, h, app.image_rotation) for (x, y) in app.current_polygon]
        app.current_polygon = [(x + offset_x, y + offset_y) for (x, y) in app.current_polygon]
        app.scale_points = [rotate_point(x, y, w, h, app.image_rotation) for (x, y) in app.scale_points]
        app.scale_points = [(x + offset_x, y + offset_y) for (x, y) in app.scale_points]
        if app.scale_artifact and 'points' in app.scale_artifact:
            pts = app.scale_artifact['points']
            pts = [rotate_point(x, y, w, h, app.image_rotation) for (x, y) in pts]
            pts = [(x + offset_x, y + offset_y) for (x, y) in pts]
            app.scale_artifact['points'] = pts

    app.redraw()



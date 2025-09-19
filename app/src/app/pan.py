from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .gui_client import MeasureAppGUI


def pan_canvas(app: "MeasureAppGUI", dx: int, dy: int) -> None:
    app.canvas.xview_scroll(int(dx), 'units')
    app.canvas.yview_scroll(int(dy), 'units')


def on_pan_start(app: "MeasureAppGUI", event) -> None:
    app.canvas.scan_mark(event.x, event.y)


def on_pan_move(app: "MeasureAppGUI", event) -> None:
    app.canvas.scan_dragto(event.x, event.y, gain=1)


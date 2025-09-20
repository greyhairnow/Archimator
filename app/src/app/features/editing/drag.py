from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional, Tuple, List

if TYPE_CHECKING:
    try:
        from ...gui_client import MeasureAppGUI  # type: ignore
    except Exception:
        from gui_client import MeasureAppGUI  # type: ignore


def on_drag_start(app: "MeasureAppGUI", event) -> None:
    if app.image is None:
        return
    if app.scale_mode or app.draw_mode:
        return
    x = app.canvas.canvasx(event.x)
    y = app.canvas.canvasy(event.y)
    # Find a vertex under cursor across all polygons
    hit_poly_idx = None
    hit_vertex_idx = None
    for pidx, poly_try in enumerate(app.polygons):
        for i, (px, py) in enumerate(poly_try.points):
            canvas_x = px * app.zoom_level
            canvas_y = py * app.zoom_level
            if abs(x - canvas_x) <= 8 and abs(y - canvas_y) <= 8:
                hit_poly_idx = pidx
                hit_vertex_idx = i
                break
        if hit_poly_idx is not None:
            break
    if hit_poly_idx is None or hit_vertex_idx is None:
        return
    # Select polygon and start drag on that vertex
    app.selected_polygon = hit_poly_idx
    poly = app.polygons[app.selected_polygon]
    pts = poly.points
    i = hit_vertex_idx
    px, py = pts[i]
    app.dragging = True
    app.drag_point_index = i
    app.drag_start_x = x
    app.drag_start_y = y
    app.canvas.config(cursor="hand2")
    # Backup full polygon for undo of movement
    try:
        app._vertex_move_backup = (
            app.selected_polygon,
            i,
            list(pts),
        )
    except Exception:
        pass
    # Store original vertex for elastic spring
    app._drag_original_vertex = (px, py)
    # Initialize elastic artifacts container
    app._drag_artifacts = getattr(app, "_drag_artifacts", {"lines": [], "angle_text": None, "spring": None, "snap_text": None})
    # Show zoom preview immediately
    try:
        app.show_zoom_preview(event.x, event.y)
    except Exception:
        pass


def on_drag_move(app: "MeasureAppGUI", event) -> None:
    if not app.dragging or app.drag_point_index is None:
        return
    x = app.canvas.canvasx(event.x)
    y = app.canvas.canvasy(event.y)
    poly = app.polygons[app.selected_polygon]
    new_x = x / app.zoom_level
    new_y = y / app.zoom_level

    # Snap-to-line behavior when nearing 180 degrees
    idx = app.drag_point_index
    pts = poly.points
    n = len(pts)
    x_prev, y_prev = pts[idx - 1]
    x_next, y_next = pts[(idx + 1) % n]

    def angle_deg(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> float:
        v1 = (a[0] - b[0], a[1] - b[1])
        v2 = (c[0] - b[0], c[1] - b[1])
        dot = v1[0] * v2[0] + v1[1] * v2[1]
        det = v1[0] * v2[1] - v1[1] * v2[0]
        ang = math.atan2(det, dot)
        return abs(math.degrees(ang))

    # Project point onto line prev-next if near 180 within tolerance
    TOL_DEG = float(getattr(app, "snap_tolerance_deg", 3.0))
    deg = angle_deg((x_prev, y_prev), (new_x, new_y), (x_next, y_next))
    snapped = False
    # Snap only if Shift or Ctrl is pressed
    state = getattr(event, "state", 0)
    snap_mod_down = bool(state & 0x0001) or bool(state & 0x0004)
    if snap_mod_down and (abs(deg - 180.0) <= TOL_DEG or abs(deg) <= TOL_DEG):
        # Projection of point B onto line AC
        ax, ay = x_prev, y_prev
        cx, cy = x_next, y_next
        bx, by = new_x, new_y
        ACx, ACy = (cx - ax), (cy - ay)
        AC_len2 = ACx * ACx + ACy * ACy
        if AC_len2 > 1e-9:
            t = ((bx - ax) * ACx + (by - ay) * ACy) / AC_len2
            projx = ax + t * ACx
            projy = ay + t * ACy
            new_x, new_y = projx, projy
            snapped = True

    poly.points[idx] = (new_x, new_y)
    poly.compute_metrics()
    app.redraw()
    # Draw elastic connectors: prev->current and current->next and spring to original
    try:
        # Clean previous artifacts
        arts = getattr(app, "_drag_artifacts", None)
        if arts:
            for lid in arts.get("lines", []):
                try:
                    app.canvas.delete(lid)
                except Exception:
                    pass
            if arts.get("angle_text") is not None:
                try:
                    app.canvas.delete(arts["angle_text"])
                except Exception:
                    pass
            if arts.get("spring") is not None:
                try:
                    app.canvas.delete(arts["spring"])
                except Exception:
                    pass
            arts["lines"] = []
            arts["angle_text"] = None
            arts["spring"] = None
            if arts.get("snap_text") is not None:
                try:
                    app.canvas.delete(arts["snap_text"])
                except Exception:
                    pass
                arts["snap_text"] = None
        else:
            arts = {"lines": [], "angle_text": None, "spring": None, "snap_text": None}
            app._drag_artifacts = arts

        cx = new_x * app.zoom_level
        cy = new_y * app.zoom_level
        px = x_prev * app.zoom_level
        py = y_prev * app.zoom_level
        nx = x_next * app.zoom_level
        ny = y_next * app.zoom_level
        # Adjacent dashed lines
        line_color = 'lime' if snapped else 'orange'
        lid1 = app.canvas.create_line(px, py, cx, cy, fill=line_color, width=2, dash=(4, 3))
        lid2 = app.canvas.create_line(cx, cy, nx, ny, fill=line_color, width=2, dash=(4, 3))
        arts["lines"].extend([lid1, lid2])
        # Spring from original vertex to current
        orig: Optional[Tuple[float, float]] = getattr(app, "_drag_original_vertex", None)
        if orig is not None:
            ox, oy = orig
            ox_c = ox * app.zoom_level
            oy_c = oy * app.zoom_level
            spring = app.canvas.create_line(ox_c, oy_c, cx, cy, fill='gray', width=1, dash=(2, 2))
            arts["spring"] = spring
        # Angle indicator text near current point
        color = 'lime' if snapped or abs(deg - 180.0) <= TOL_DEG or abs(deg) <= TOL_DEG else 'yellow'
        txt = f"{deg:.1f}°"
        angle_id = app.canvas.create_text(cx + 12, cy - 12, text=txt, fill=color, font=("TkDefaultFont", 10, "bold"))
        arts["angle_text"] = angle_id
        # Snap tooltip cue
        if snapped:
            snap_id = app.canvas.create_text(cx + 12, cy + 8, text="Straight snap", fill='lime', font=("TkDefaultFont", 9))
            arts["snap_text"] = snap_id
        # Keep zoom preview following and emit status on first snap
        try:
            if snapped and not getattr(app, "_snap_message_shown", False):
                if hasattr(app, "show_status_message"):
                    app.show_status_message("Snapped to straight")
                app._snap_message_shown = True
            if not snapped:
                app._snap_message_shown = False
        except Exception:
            pass
        # Keep zoom preview following
        try:
            app.show_zoom_preview(event.x, event.y)
        except Exception:
            pass
    except Exception:
        pass
    app.update_info_label()


def on_drag_end(app: "MeasureAppGUI", event) -> None:
    if app.dragging:
        app.dragging = False
        app.drag_point_index = None
        app.canvas.config(cursor="")
        # Final snap check at drop
        if app.selected_polygon is not None:
            poly = app.polygons[app.selected_polygon]
            poly.compute_metrics()
        # Clear elastic artifacts
        try:
            arts = getattr(app, "_drag_artifacts", None)
            if arts:
                for lid in arts.get("lines", []):
                    try:
                        app.canvas.delete(lid)
                    except Exception:
                        pass
                if arts.get("angle_text") is not None:
                    try:
                        app.canvas.delete(arts["angle_text"])
                    except Exception:
                        pass
                if arts.get("spring") is not None:
                    try:
                        app.canvas.delete(arts["spring"])
                    except Exception:
                        pass
            app._drag_artifacts = {"lines": [], "angle_text": None, "spring": None, "snap_text": None}
            app._drag_original_vertex = None
        except Exception:
            pass
        app.hide_zoom_preview()
        app.redraw()
        app.update_info_label()


def undo_last_vertex_move(app: "MeasureAppGUI") -> None:
    """Undo the last vertex movement, if available."""
    backup = getattr(app, "_vertex_move_backup", None)
    if backup is None:
        # No backup to restore
        if hasattr(app, "messagebox") and app.messagebox:
            try:
                app.messagebox.showwarning("Warning", "No vertex movement to undo.")
            except Exception:
                pass
        return
    poly_idx, v_idx, pts = backup
    if poly_idx is None or poly_idx >= len(app.polygons):
        return
    poly = app.polygons[poly_idx]
    poly.points = list(pts)
    poly.compute_metrics()
    app._vertex_move_backup = None
    app.selected_polygon = poly_idx
    app.redraw()
    app.update_info_label()


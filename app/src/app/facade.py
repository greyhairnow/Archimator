from __future__ import annotations

"""
A thin facade that re-exports feature functions from the various modules.
GUI code can import just this module to avoid scattered imports.

Designed to work when imported either as part of the package
(e.g., 'from app.src.app import facade') or as a top-level module
when running gui_client.py directly.
"""

# Scale
try:
    from .scale import (
        set_scale_mode as scale_set_mode,
        clear_scale_preview as scale_clear_preview,
        exit_scale_mode as scale_exit_mode,
        cancel_scale_mode as scale_cancel_mode,
        scale_on_motion as scale_on_motion,
        scale_on_canvas_click as scale_on_canvas_click,
    )
except Exception:  # Fallback for script-run mode
    from scale import (
        set_scale_mode as scale_set_mode,
        clear_scale_preview as scale_clear_preview,
        exit_scale_mode as scale_exit_mode,
        cancel_scale_mode as scale_cancel_mode,
        scale_on_motion as scale_on_motion,
        scale_on_canvas_click as scale_on_canvas_click,
    )

# Draw
try:
    from .draw import (
        set_draw_mode as draw_set_mode,
        draw_on_canvas_click as draw_on_canvas_click,
        finish_polygon as draw_finish,
    )
except Exception:
    from draw import (
        set_draw_mode as draw_set_mode,
        draw_on_canvas_click as draw_on_canvas_click,
        finish_polygon as draw_finish,
    )

# File I/O
try:
    from .file_io import (
        load_pdf as file_load_pdf,
        load_config as file_load_config,
        save_config as file_save_config,
    )
except Exception:
    from file_io import (
        load_pdf as file_load_pdf,
        load_config as file_load_config,
        save_config as file_save_config,
    )

# Preview
try:
    from .preview import (
        show_zoom_preview as preview_show,
        hide_zoom_preview as preview_hide,
    )
except Exception:
    from preview import (
        show_zoom_preview as preview_show,
        hide_zoom_preview as preview_hide,
    )

# Navigation
try:
    from .pan import (
        pan_canvas as pan_canvas,
        on_pan_start as pan_on_start,
        on_pan_move as pan_on_move,
    )
except Exception:
    from pan import (
        pan_canvas as pan_canvas,
        on_pan_start as pan_on_start,
        on_pan_move as pan_on_move,
    )

try:
    from .zoom import (
        zoom_in as zoom_in,
        zoom_out as zoom_out,
        set_zoom as zoom_set,
    )
except Exception:
    from zoom import (
        zoom_in as zoom_in,
        zoom_out as zoom_out,
        set_zoom as zoom_set,
    )

try:
    from .rotate import (
        rotate_left as rotate_left,
        rotate_right as rotate_right,
        apply_rotation as rotate_apply,
    )
except Exception:
    from rotate import (
        rotate_left as rotate_left,
        rotate_right as rotate_right,
        apply_rotation as rotate_apply,
    )

# Dragging
try:
    from .drag import (
        on_drag_start as drag_start,
        on_drag_move as drag_move,
        on_drag_end as drag_end,
    )
except Exception:
    from drag import (
        on_drag_start as drag_start,
        on_drag_move as drag_move,
        on_drag_end as drag_end,
    )

# Straighten
try:
    from .straighten import (
        straighten_polygon as straighten_do,
        undo_straighten as straighten_undo,
    )
except Exception:
    from straighten import (
        straighten_polygon as straighten_do,
        undo_straighten as straighten_undo,
    )

# Export + Panels + 3D
try:
    from .export_mod import export_csv as export_csv
except Exception:
    from export_mod import export_csv as export_csv

try:
    from .panels import optimize_panels as panels_optimize
except Exception:
    from panels import optimize_panels as panels_optimize

try:
    from .three_d import show_3d_view as three_d_show
except Exception:
    from three_d import show_3d_view as three_d_show

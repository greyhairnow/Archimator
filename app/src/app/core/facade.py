from __future__ import annotations

"""
Unified facade that re-exports feature functions from modular packages.
Works both when imported as part of the package (from .core import facade)
and when running gui_client.py directly (import core.facade as facade).
"""

# Scale
try:
    from ..features.scale.scale import (
        set_scale_mode as scale_set_mode,
        clear_scale_preview as scale_clear_preview,
        exit_scale_mode as scale_exit_mode,
        cancel_scale_mode as scale_cancel_mode,
        scale_on_motion as scale_on_motion,
        scale_on_canvas_click as scale_on_canvas_click,
    )
except Exception:
    from features.scale.scale import (
        set_scale_mode as scale_set_mode,
        clear_scale_preview as scale_clear_preview,
        exit_scale_mode as scale_exit_mode,
        cancel_scale_mode as scale_cancel_mode,
        scale_on_motion as scale_on_motion,
        scale_on_canvas_click as scale_on_canvas_click,
    )

# Draw
try:
    from ..features.editing.draw import (
        set_draw_mode as draw_set_mode,
        draw_on_canvas_click as draw_on_canvas_click,
        draw_on_motion as draw_on_motion,
        clear_draw_preview as draw_clear_preview,
        finish_polygon as draw_finish,
    )
except Exception:
    from features.editing.draw import (
        set_draw_mode as draw_set_mode,
        draw_on_canvas_click as draw_on_canvas_click,
        draw_on_motion as draw_on_motion,
        clear_draw_preview as draw_clear_preview,
        finish_polygon as draw_finish,
    )

# File I/O
try:
    from ..file_io import (
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
    from ..ui.preview import (
        show_zoom_preview as preview_show,
        hide_zoom_preview as preview_hide,
    )
except Exception:
    from ui.preview import (
        show_zoom_preview as preview_show,
        hide_zoom_preview as preview_hide,
    )

# Navigation
try:
    from ..features.navigation.pan import (
        pan_canvas as pan_canvas,
        on_pan_start as pan_on_start,
        on_pan_move as pan_on_move,
    )
except Exception:
    from features.navigation.pan import (
        pan_canvas as pan_canvas,
        on_pan_start as pan_on_start,
        on_pan_move as pan_on_move,
    )

try:
    from ..features.navigation.zoom import (
        zoom_in as zoom_in,
        zoom_out as zoom_out,
        set_zoom as zoom_set,
    )
except Exception:
    from features.navigation.zoom import (
        zoom_in as zoom_in,
        zoom_out as zoom_out,
        set_zoom as zoom_set,
    )

try:
    from ..features.navigation.rotate import (
        rotate_left as rotate_left,
        rotate_right as rotate_right,
        apply_rotation as rotate_apply,
    )
except Exception:
    from features.navigation.rotate import (
        rotate_left as rotate_left,
        rotate_right as rotate_right,
        apply_rotation as rotate_apply,
    )

# Dragging
try:
    from ..features.editing.drag import (
        on_drag_start as drag_start,
        on_drag_move as drag_move,
        on_drag_end as drag_end,
        undo_last_vertex_move as drag_undo,
    )
except Exception:
    from features.editing.drag import (
        on_drag_start as drag_start,
        on_drag_move as drag_move,
        on_drag_end as drag_end,
        undo_last_vertex_move as drag_undo,
    )

# Straighten
try:
    from ..features.editing.straighten import (
        straighten_polygon as straighten_do,
        undo_straighten as straighten_undo,
    )
except Exception:
    from features.editing.straighten import (
        straighten_polygon as straighten_do,
        undo_straighten as straighten_undo,
    )

# Export + Panels + 3D
try:
    from ..app_io.export_mod import export_csv as export_csv
except Exception:
    from app_io.export_mod import export_csv as export_csv

try:
    from ..features.panels.panels import optimize_panels as panels_optimize
except Exception:
    from features.panels.panels import optimize_panels as panels_optimize

try:
    from ..visualization.three_d import show_3d_view as three_d_show
except Exception:
    from visualization.three_d import show_3d_view as three_d_show


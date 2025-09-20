#!/usr/bin/env python3
"""
GUI client for the architectural diagram measurement tool.

This script uses the Tkinter GUI library to provide a native windowed
experience for loading a PDF of an architectural drawing, measuring rooms by
drawing polygons, setting a reference scale, exporting measurement data and
performing simple panel layout optimisation.  It includes conveniences such
as zooming, panning, rotating the loaded image, a zoom preview window and
tools for editing polygons (straightening, vertex dragging).  It is designed
for use on platforms where Tkinter is available (e.g. a standard Python
installation on Windows, macOS or Linux with the Tk libraries installed).

Features:
  * Load a PDF and display the first page on a canvas.
  * Zoom in/out and pan the diagram via buttons or right‑click dragging.
  * Rotate the diagram in 90° increments.
  * Draw room outlines as polygons directly on the diagram.
  * Set a reference scale by drawing a line of known length; scale lines
    remain visible after confirmation.
  * Compute area and perimeter for each polygon in real units based on the
    scale factor.
  * Attach metadata (room ID and name) to polygons.
  * Export all measurements and metadata to a CSV file.
  * Generate a simple 3D extrusion of all rooms.
  * Optimise panel layout within a selected room using a simple tiling
    algorithm.
  * Straighten polygons by converting near‑right angles to perfectly straight
    segments, and undo the operation if necessary.
  * Drag individual polygon vertices (non‑right angles) to fine‑tune shapes.
  * Zoom preview window to help accurately place scale and polygon points.

Note: This script requires Tkinter to be installed.  It cannot run in
headless environments (such as this sandbox) where a GUI cannot be created.
Run it locally on a system with a graphical desktop. 
"""

import importlib.util
import json
import math
import sys
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

# Soft fill colours for polygon overlays (cycled per polygon)
POLYGON_FILL_COLORS: List[str] = [
    '#9bd6ff',  # pale blue
    '#c5f5c9',  # pale green
    '#ffe0b3',  # pale orange
    '#f7c6ff',  # pale violet
]


def _polygon_centroid(points: List[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
    """Return polygon centroid; fall back to vertex average for near-zero area."""
    if not points:
        return None
    area_acc = 0.0
    cx_acc = 0.0
    cy_acc = 0.0
    n = len(points)
    for i in range(n):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        area_acc += cross
        cx_acc += (x0 + x1) * cross
        cy_acc += (y0 + y1) * cross
    area = area_acc / 2.0
    if abs(area) < 1e-9:
        avg_x = sum(p[0] for p in points) / n
        avg_y = sum(p[1] for p in points) / n
        return (avg_x, avg_y)
    centroid_x = cx_acc / (6.0 * area)
    centroid_y = cy_acc / (6.0 * area)
    return (centroid_x, centroid_y)



# Ensure required third-party packages are available before proceeding.
REQUIRED_PACKAGES = {
    "pymupdf": "pymupdf",
    "PIL": "pillow",
    "matplotlib": "matplotlib",
}

missing_packages = [
    package_name
    for module_name, package_name in REQUIRED_PACKAGES.items()
    if importlib.util.find_spec(module_name) is None
]

if missing_packages:
    unique = sorted(set(missing_packages))
    package_list = " ".join(unique)
    message = (
        "Missing required packages: "
        + ", ".join(unique)
        + "\nInstall them with: pip install "
        + package_list
    )
    print(message, file=sys.stderr)
    raise SystemExit(1)

from PIL import Image, ImageDraw

try:
    import tkinter as tk
    from tkinter import filedialog, simpledialog, messagebox
    from PIL import ImageTk
except ImportError:
    # When Tkinter is unavailable (e.g. headless environment), set tk to None.
    tk = None  # type: ignore

try:
    from .core import facade
except Exception:
    import core.facade as facade  # type: ignore

## Note: pdf_page_to_image and generate_3d_image have been moved to modular components:
## - PDF loading is handled by file_io._pdf_page_to_image (via facade.file_load_pdf)
## - 3D generation lives in three_d.generate_3d_image (via facade.three_d_show)

if __package__:
    from .core.model import (
        PolygonData,
        shoelace_area,
        polygon_perimeter,
        point_in_polygon,
    )
else:
    from core.model import (
        PolygonData,
        shoelace_area,
        polygon_perimeter,
        point_in_polygon,
    )

class MeasureAppGUI:
    """Main class encapsulating the Tkinter application."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Architectural Diagram Measurement Tool")
        # Set a reasonable default size; user may resize later.
        self.root.geometry("1200x800")
        # Main frame contains canvas and control areas.
        main_frame = tk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True)
        # Frame to hold canvas and its pan/zoom controls below.
        canvas_frame = tk.Frame(main_frame)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # Canvas used to display the PDF image and drawings.
        # Starting size gives a reasonable default; will be adjusted once a PDF
        # is loaded.
        self.canvas = tk.Canvas(canvas_frame, bg='gray', width=800, height=600)
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        # Controls for pan, zoom and rotation beneath the canvas.
        ctrl_canvas_frame = tk.Frame(canvas_frame)
        ctrl_canvas_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.pan_zoom_buttons: List[tk.Button] = []
        self.add_pan_zoom_buttons(ctrl_canvas_frame)
        # Rotation buttons (delegate to facade to centralize behavior)
        self.rotate_left_btn = tk.Button(ctrl_canvas_frame, text="Rotate Left", command=lambda: facade.rotate_left(self))
        self.rotate_left_btn.pack(side=tk.LEFT, padx=2)
        self.rotate_right_btn = tk.Button(ctrl_canvas_frame, text="Rotate Right", command=lambda: facade.rotate_right(self))
        self.rotate_right_btn.pack(side=tk.LEFT, padx=2)
        # Control panel on the right for file loading and measurement options.
        side_frame = tk.Frame(main_frame)
        side_frame.pack(side=tk.RIGHT, fill=tk.Y)
        tk.Button(side_frame, text="Load PDF", command=self.load_pdf).pack(fill=tk.X)
        tk.Button(side_frame, text="Load Config", command=self.load_config).pack(fill=tk.X)
        tk.Button(side_frame, text="Save Config", command=self.save_config).pack(fill=tk.X)
        tk.Button(side_frame, text="Set Unit/Scale", command=self.set_scale_mode).pack(fill=tk.X)
        tk.Button(side_frame, text="Draw Polygon", command=self.set_draw_mode).pack(fill=tk.X)
        tk.Button(side_frame, text="Export CSV", command=self.export_csv).pack(fill=tk.X)
        tk.Button(side_frame, text="3D View", command=self.show_3d_view).pack(fill=tk.X)
        tk.Button(side_frame, text="Optimize Panels", command=self.optimize_panels).pack(fill=tk.X)
        self.straighten_btn = tk.Button(side_frame, text="Straighten Polygon", command=lambda: facade.straighten_do(self))
        self.straighten_btn.pack(fill=tk.X)
        tk.Button(side_frame, text="Undo Straighten", command=lambda: facade.straighten_undo(self)).pack(fill=tk.X)
        tk.Button(side_frame, text="Undo Vertex Move", command=lambda: facade.drag_undo(self)).pack(fill=tk.X)
        tk.Button(side_frame, text="Edit Metadata", command=lambda: facade.metadata_edit(self)).pack(fill=tk.X)
        # Labels to display the current scale and selection info.
        self.scale_unit = "units"
        self.scale_label = tk.Label(side_frame, text=f"Scale: 1.0 {self.scale_unit}/pixel")
        self.scale_label.pack(fill=tk.X, pady=(10, 0))
        self.info_label = tk.Label(side_frame, text="No polygon selected.")
        self.info_label.pack(fill=tk.X)
        # Status bar (messages like snap notifications)
        self.status_label = tk.Label(side_frame, text="", fg='gray')
        self.status_label.pack(fill=tk.X)
        # Initialize button states
        self.update_buttons_state()
        # Bind mouse events for drawing, panning and dragging.
        # Left mouse button handles drawing polygons and selecting regions.
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        # Right mouse button for panning via scan functionality.
        self.canvas.bind("<ButtonPress-3>", lambda e: facade.pan_on_start(self, e))
        self.canvas.bind("<B3-Motion>", lambda e: facade.pan_on_move(self, e))
        # Motion event for zoom preview (enabled only in drawing/scale modes).
        self.canvas.bind("<Motion>", self.on_canvas_motion)
        # Dragging vertices (left button press, move and release) outside of draw/scale mode.
        # Use add='+' to avoid overwriting the existing <Button-1> binding
        self.canvas.bind("<ButtonPress-1>", lambda e: facade.drag_start(self, e), add="+")
        self.canvas.bind("<B1-Motion>", lambda e: facade.drag_move(self, e))
        self.canvas.bind("<ButtonRelease-1>", lambda e: facade.drag_end(self, e))
        # Confirm/cancel for straighten preview

        # Data structures and state variables.
        self.image: Optional[Image.Image] = None  # Original PDF page (resized to fit)
        self.photo: Optional[ImageTk.PhotoImage] = None  # PhotoImage for Tkinter display
        self.display_image: Optional[Image.Image] = None  # PIL image currently shown on canvas (after rotation/zoom)
        self.polygons: List[PolygonData] = []  # Completed polygons
        self.current_polygon: List[Tuple[float, float]] = []  # Points of polygon being drawn
        self.draw_mode: bool = False  # True when drawing a new polygon
        self.scale_mode: bool = False  # True when setting the scale line
        self.scale_points: List[Tuple[float, float]] = []  # Two points selected for scale
        self.scale_artifact: Optional[dict] = None  # Persistent scale line info
        self.scale_marker_id: Optional[int] = None  # Canvas ID for first scale point marker
        self.scale_line_id: Optional[int] = None  # Canvas ID for scale line
        self.scale_factor: float = 1.0  # Units per pixel
        self.selected_polygon: Optional[int] = None  # Index of currently selected polygon
        # Configuration (panel size and extrusion height)
        self.config = {
            'panel_width': 1.0,
            'panel_height': 1.0,
            'extrusion_height': 1.0
        }
        # Scale preview state
        self.scale_preview_line_id: Optional[int] = None  # Canvas ID for scale rubber-band preview
        # Draw preview state
        self.draw_preview_line_id: Optional[int] = None  # Canvas ID for draw rubber-band preview
        # Zoom/pan/rotation state
        self.zoom_level: float = 1.0
        self.image_rotation: int = 0  # Rotation in degrees (0, 90, 180, 270)
        # Straightening state
        self._straighten_backup: Optional[List[Tuple[float, float]]] = None
        # Zoom preview window and configuration
        self.zoom_preview_win: Optional[tk.Toplevel] = None
        self.zoom_preview_label: Optional[tk.Label] = None
        self.zoom_preview_size: int = 80  # Size of zoom preview window (pixels)
        self.zoom_preview_zoom: float = 1.6  # Zoom factor for preview
        # Dragging state
        self.dragging: bool = False
        self.drag_point_index: Optional[int] = None
        self.drag_start_x: float = 0.0
        self.drag_start_y: float = 0.0
        self.snap_tolerance_deg: float = 3.0

    # ----- Pan/Zoom/Rotate Button Setup -----
    def add_pan_zoom_buttons(self, frame: tk.Frame) -> None:
        """Add pan and zoom buttons to the provided frame."""
        # Clear any existing buttons (useful when reinitialising)
        for btn in self.pan_zoom_buttons:
            btn.destroy()
        self.pan_zoom_buttons.clear()
        # Zoom controls
        self.pan_zoom_buttons.append(tk.Button(frame, text="Zoom In", command=lambda: facade.zoom_in(self)))
        self.pan_zoom_buttons.append(tk.Button(frame, text="Zoom Out", command=lambda: facade.zoom_out(self)))
        # Pan controls (move by 50 units at current zoom level)
        self.pan_zoom_buttons.append(tk.Button(frame, text="Pan Left", command=lambda: facade.pan_canvas(self, -50, 0)))
        self.pan_zoom_buttons.append(tk.Button(frame, text="Pan Right", command=lambda: facade.pan_canvas(self, 50, 0)))
        self.pan_zoom_buttons.append(tk.Button(frame, text="Pan Up", command=lambda: facade.pan_canvas(self, 0, -50)))
        self.pan_zoom_buttons.append(tk.Button(frame, text="Pan Down", command=lambda: facade.pan_canvas(self, 0, 50)))
        for btn in self.pan_zoom_buttons:
            btn.pack(side=tk.LEFT, padx=2)

    # ----- Rotation Controls -----
    def rotate_left(self) -> None:
        """Rotate the image 90° counter‑clockwise."""
        if self.image is None:
            return
        # Update rotation state and reapply rotation
        self.image_rotation = (self.image_rotation - 90) % 360
        self.apply_rotation()

    def rotate_right(self) -> None:
        """Rotate the image 90° clockwise."""
        if self.image is None:
            return
        self.image_rotation = (self.image_rotation + 90) % 360
        self.apply_rotation()

    def apply_rotation(self) -> None:
        """Apply the current rotation to the image and transform polygons and scale markers accordingly."""
        if self.image is None:
            return
        # Rotate the original image (before scaling) and update PhotoImage
        img = self.image.rotate(-self.image_rotation, expand=True)
        # Also apply current zoom level
        if self.zoom_level != 1.0:
            new_size = (int(img.width * self.zoom_level), int(img.height * self.zoom_level))
            try:
                resample = Image.Resampling.LANCZOS
            except AttributeError:
                resample = Image.LANCZOS
            img = img.resize(new_size, resample)
        self.photo = ImageTk.PhotoImage(img)
        self.display_image = img
        self.display_image = img
        # Update canvas scroll region
        self.canvas.config(scrollregion=(0, 0, img.width, img.height))
        # Transform existing polygons and scale points only when rotation
        # changes (note: this operation is destructive on stored points).
        if self.image_rotation != 0 and self.image is not None:
            # Use the original (resized) image dimensions before rotation to calculate center
            w, h = self.image.size
            # After rotation, new dimensions of rotated image (before zoom)
            temp_rotated = self.image.rotate(-self.image_rotation, expand=True)
            new_w, new_h = temp_rotated.size
            # Offset between original and rotated due to expansion
            offset_x = (new_w - w) / 2
            offset_y = (new_h - h) / 2
            def rotate_point(px: float, py: float, width: float, height: float, angle: int) -> Tuple[float, float]:
                """Rotate a point (px,py) around the centre of an image of size width x height by angle degrees."""
                angle_rad = math.radians(angle)
                cx, cy = width / 2, height / 2
                dx, dy = px - cx, py - cy
                rx = dx * math.cos(angle_rad) - dy * math.sin(angle_rad)
                ry = dx * math.sin(angle_rad) + dy * math.cos(angle_rad)
                return rx + cx, ry + cy
            # Transform polygons
            for poly in self.polygons:
                transformed = [rotate_point(x, y, w, h, self.image_rotation) for (x, y) in poly.points]
                # Adjust for expansion offset
                transformed = [(x + offset_x, y + offset_y) for (x, y) in transformed]
                poly.points = transformed
                poly.compute_metrics()
            # Transform current polygon
            self.current_polygon = [rotate_point(x, y, w, h, self.image_rotation) for (x, y) in self.current_polygon]
            self.current_polygon = [(x + offset_x, y + offset_y) for (x, y) in self.current_polygon]
            # Transform scale points
            self.scale_points = [rotate_point(x, y, w, h, self.image_rotation) for (x, y) in self.scale_points]
            self.scale_points = [(x + offset_x, y + offset_y) for (x, y) in self.scale_points]
            # Update scale artifact if present
            if self.scale_artifact and 'points' in self.scale_artifact:
                pts = self.scale_artifact['points']
                pts = [rotate_point(x, y, w, h, self.image_rotation) for (x, y) in pts]
                pts = [(x + offset_x, y + offset_y) for (x, y) in pts]
                self.scale_artifact['points'] = pts
        # Redraw the canvas
        self.redraw()

    # ----- Zoom and Pan -----
    def zoom_in(self) -> None:
        """Increase zoom level and redraw the image."""
        self.set_zoom(self.zoom_level * 1.2)

    def zoom_out(self) -> None:
        """Decrease zoom level and redraw the image."""
        self.set_zoom(self.zoom_level / 1.2)

    def set_zoom(self, zoom: float) -> None:
        """Set a new zoom level within allowable bounds and redraw the image."""
        if self.image is None:
            return
        zoom = max(0.2, min(zoom, 5.0))
        self.zoom_level = zoom
        # Start from the original resized image and apply zoom and rotation.
        img = self.image
        # Apply rotation first to preserve orientation before scaling
        if self.image_rotation != 0:
            img = img.rotate(-self.image_rotation, expand=True)
        # Apply zoom by resizing
        new_size = (int(img.width * self.zoom_level), int(img.height * self.zoom_level))
        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.LANCZOS
        img = img.resize(new_size, resample)
        self.photo = ImageTk.PhotoImage(img)
        self.display_image = img
        # Update scroll region for panning
        self.canvas.config(scrollregion=(0, 0, img.width, img.height))
        # Redraw contents at new zoom level
        self.redraw()

    def pan_canvas(self, dx: int, dy: int) -> None:
        """Pan the canvas by the specified amount (in canvas units)."""
        self.canvas.xview_scroll(int(dx), 'units')
        self.canvas.yview_scroll(int(dy), 'units')

    # ----- Panning via Right‑click Dragging -----
    def on_pan_start(self, event) -> None:
        """Record the starting point for a panning operation (right‑click)."""
        self.canvas.scan_mark(event.x, event.y)

    def on_pan_move(self, event) -> None:
        """Handle panning while dragging with the right mouse button."""
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    # ----- File and Configuration Management -----
    def load_pdf(self) -> None:
        facade.file_load_pdf(self)

    def load_config(self) -> None:
        facade.file_load_config(self)

    def save_config(self) -> None:
        facade.file_save_config(self)

    # ----- Mode Selection -----
    def set_scale_mode(self) -> None:
        facade.scale_set_mode(self)

    def clear_scale_preview(self) -> None:
        facade.scale_clear_preview(self)

    def exit_scale_mode(self) -> None:
        facade.scale_exit_mode(self)

    def cancel_scale_mode(self, event=None) -> None:
        facade.scale_cancel_mode(self)

    def _prompt_scale_unit(self) -> Optional[str]:
        """Prompt the user for the unit label; return None if cancelled."""
        while True:
            unit = simpledialog.askstring("Set Unit/Scale", "Enter units (e.g., m, cm, ft, in):")
            if unit is None:
                return None
            unit = unit.strip()
            if unit:
                return unit
            messagebox.showerror("Set Unit/Scale", "Unit is required.")

    def _prompt_scale_length(self, unit: str) -> Optional[float]:
        """Prompt for the real-world length in the supplied unit."""
        while True:
            prompt = f"Enter real-world length between the two points (in {unit}):"
            real_len_str = simpledialog.askstring("Set Unit/Scale", prompt)
            if real_len_str is None:
                return None
            try:
                real_len = float(real_len_str)
            except (TypeError, ValueError):
                messagebox.showerror("Set Unit/Scale", "Enter a numeric value for the length.")
                continue
            if real_len <= 0:
                messagebox.showerror("Set Unit/Scale", "Length must be greater than zero.")
                continue
            return real_len

    def set_draw_mode(self) -> None:
        facade.draw_set_mode(self)

    # ----- Canvas Click Handling -----
    def on_canvas_click(self, event) -> None:
        """Handle mouse clicks on the canvas for scale definition, drawing, and selection."""
        if self.image is None:
            return
        # If straighten preview is active, any left click applies it

        # Convert screen coordinates to canvas coordinates (taking panning into account)
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        # Scale mode: collect two points and compute scale factor
        if self.scale_mode:
            if facade.scale_on_canvas_click(self, event):
                return
            return
        # Draw mode: build up points for a new polygon
        if self.draw_mode:
            if facade.draw_on_canvas_click(self, event):
                return
        # Not in draw or scale mode: selection of an existing polygon
        self.selected_polygon = None
        # Convert click to image coordinates for point‑in‑polygon test
        point = (x / self.zoom_level, y / self.zoom_level)
        for idx, poly in enumerate(self.polygons):
            if point_in_polygon(point, poly.points):
                self.selected_polygon = idx
                break
        self.update_info_label()
        self.redraw()
        # Hide zoom preview when clicking outside scale/draw mode
        self.hide_zoom_preview()

    # ----- Polygon Completion -----
    def finish_polygon(self) -> None:
        facade.draw_finish(self)

    # ----- Dragging Polygon Vertices -----
    def on_drag_start(self, event) -> None:
        """Initiate dragging of a polygon vertex (non‑right angles only)."""
        if self.image is None or self.selected_polygon is None:
            return
        # Do not start dragging while in scale or draw mode
        if self.scale_mode or self.draw_mode:
            return
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        # Check if click is on a vertex of the selected polygon and if that vertex is a non‑right angle
        poly = self.polygons[self.selected_polygon]
        pts = poly.points
        n = len(pts)
        for i in range(n):
            px, py = pts[i]
            canvas_x = px * self.zoom_level
            canvas_y = py * self.zoom_level
            # Hit test within a small radius (8 pixels)
            if abs(x - canvas_x) <= 8 and abs(y - canvas_y) <= 8:
                # Compute angle at this vertex; if it's not near 90°, allow dragging
                x_prev, y_prev = pts[i - 1]
                x_next, y_next = pts[(i + 1) % n]
                v1 = (px - x_prev, py - y_prev)
                v2 = (x_next - px, y_next - py)
                dot = v1[0] * v2[0] + v1[1] * v2[1]
                det = v1[0] * v2[1] - v1[1] * v2[0]
                ang = math.atan2(det, dot)
                deg = abs(math.degrees(ang))
                if abs(deg - 90) >= 8:
                    self.dragging = True
                    self.drag_point_index = i
                    self.drag_start_x = x
                    self.drag_start_y = y
                    # Change cursor to indicate dragging
                    self.canvas.config(cursor="hand2")
                    break

    def on_drag_move(self, event) -> None:
        """Continue dragging a polygon vertex while mouse moves."""
        if not self.dragging or self.drag_point_index is None:
            return
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        poly = self.polygons[self.selected_polygon]
        # Update vertex position (convert back to image coords)
        new_x = x / self.zoom_level
        new_y = y / self.zoom_level
        poly.points[self.drag_point_index] = (new_x, new_y)
        poly.compute_metrics()
        self.redraw()
        self.update_info_label()

    def on_drag_end(self, event) -> None:
        """End dragging of a polygon vertex."""
        if self.dragging:
            self.dragging = False
            self.drag_point_index = None
            self.canvas.config(cursor="")
            self.redraw()
            self.update_info_label()

    # ----- Zoom Preview -----

    def show_zoom_preview(self, x: float, y: float) -> None:
        """Display a small window showing a magnified area around the pointer."""
        if self.image is None:
            return
        src = self.display_image if self.display_image is not None else self.image
        if src is None:
            return
        canvas_x = float(self.canvas.canvasx(x))
        canvas_y = float(self.canvas.canvasy(y))
        w, h = src.size
        if w <= 0 or h <= 0:
            return
        canvas_x = max(0.0, min(canvas_x, w - 1))
        canvas_y = max(0.0, min(canvas_y, h - 1))

        preview_zoom = max(0.5, float(getattr(self, "zoom_preview_zoom", 1.0)))
        region_size = int(round((self.zoom_preview_size / preview_zoom) * max(self.zoom_level, 0.01)))
        region_size = max(6, region_size)
        region_size = min(region_size, min(w, h))
        region_size = max(2, region_size - (region_size % 2))
        half = region_size // 2

        left = int(round(canvas_x)) - half
        upper = int(round(canvas_y)) - half
        left = max(0, min(left, w - region_size))
        upper = max(0, min(upper, h - region_size))
        right = left + region_size
        lower = upper + region_size

        pointer_rel_x = canvas_x - left
        pointer_rel_y = canvas_y - upper
        pointer_rel_x = max(0.0, min(pointer_rel_x, region_size - 1))
        pointer_rel_y = max(0.0, min(pointer_rel_y, region_size - 1))

        crop = src.crop((left, upper, right, lower))
        if crop.width == 0 or crop.height == 0:
            return

        scale = self.zoom_preview_size / region_size
        px = pointer_rel_x * scale
        py = pointer_rel_y * scale
        px = max(0.0, min(px, self.zoom_preview_size - 1))
        py = max(0.0, min(py, self.zoom_preview_size - 1))

        zoomed = crop.resize(
            (self.zoom_preview_size, self.zoom_preview_size),
            Image.NEAREST
        )
        draw = ImageDraw.Draw(zoomed)
        px_i = int(round(px))
        py_i = int(round(py))
        size_max = self.zoom_preview_size - 1
        arm = max(6, self.zoom_preview_size // 4)
        draw.line(
            [(px_i, max(0, py_i - arm)), (px_i, min(size_max, py_i + arm))],
            fill='red',
            width=2,
        )
        draw.line(
            [(max(0, px_i - arm), py_i), (min(size_max, px_i + arm), py_i)],
            fill='red',
            width=2,
        )
        dot_radius = 3
        draw.ellipse(
            (
                px_i - dot_radius,
                py_i - dot_radius,
                px_i + dot_radius,
                py_i + dot_radius,
            ),
            outline='white',
            fill='red',
            width=1,
        )

        preview_img = ImageTk.PhotoImage(zoomed)
        if self.zoom_preview_win is None or not self.zoom_preview_win.winfo_exists():
            self.zoom_preview_win = tk.Toplevel(self.root)
            self.zoom_preview_win.title("Zoom Preview")
            self.zoom_preview_win.resizable(False, False)
            # Do not allow the preview window to take focus away (transient)
            self.zoom_preview_win.transient(self.root)
            self.zoom_preview_label = tk.Label(self.zoom_preview_win, image=preview_img)
            self.zoom_preview_label.image = preview_img
            self.zoom_preview_label.pack()
        else:
            # Update existing preview image
            self.zoom_preview_label.config(image=preview_img)
            self.zoom_preview_label.image = preview_img
        # Position the preview window near the mouse pointer
        abs_x = self.root.winfo_pointerx()
        abs_y = self.root.winfo_pointery()
        self.zoom_preview_win.geometry(f"+{abs_x+20}+{abs_y+20}")

    def hide_zoom_preview(self) -> None:
        """Close the zoom preview window if it is open."""
        if self.zoom_preview_win and self.zoom_preview_win.winfo_exists():
            self.zoom_preview_win.destroy()
            self.zoom_preview_win = None
            self.zoom_preview_label = None

    def show_status_message(self, msg: str, duration_ms: int = 1200) -> None:
        """Show a transient status message in the side panel."""
        try:
            self.status_label.config(text=msg)
            if duration_ms > 0:
                self.root.after(duration_ms, lambda: self.status_label.config(text=""))
        except Exception:
            pass

    def on_canvas_motion(self, event) -> None:
        facade.scale_on_motion(self, event)
        facade.draw_on_motion(self, event)

    # ----- Buttons State -----
    def update_buttons_state(self) -> None:
        try:
            state = tk.NORMAL if self.selected_polygon is not None else tk.DISABLED
            self.straighten_btn.config(state=state)
        except Exception:
            pass

    # ----- Drawing and Display -----
    def redraw(self) -> None:
        """Clear and redraw the entire canvas, including image, polygons, and markers."""
        if self.image is None or self.photo is None:
            return
        # Clear the canvas
        self.canvas.delete("all")
        # Draw the base image at origin
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        # Draw persistent scale line if defined
        if self.scale_artifact and len(self.scale_artifact.get('points', [])) == 2:
            (x1, y1), (x2, y2) = self.scale_artifact['points']
            x1_canvas, y1_canvas = x1 * self.zoom_level, y1 * self.zoom_level
            x2_canvas, y2_canvas = x2 * self.zoom_level, y2 * self.zoom_level
            self.canvas.create_line(x1_canvas, y1_canvas, x2_canvas, y2_canvas,
                                    fill='purple', width=4, dash=(6, 2))
            self.canvas.create_oval(x1_canvas - 8, y1_canvas - 8, x1_canvas + 8, y1_canvas + 8,
                                    fill='purple', outline='black', width=2)
            self.canvas.create_oval(x2_canvas - 8, y2_canvas - 8, x2_canvas + 8, y2_canvas + 8,
                                    fill='purple', outline='black', width=2)
        # Draw marker for first scale point if still awaiting second point (in addition to any existing artifact)
        if self.scale_mode and len(self.scale_points) == 1:
            px, py = self.scale_points[0]
            px_canvas, py_canvas = px * self.zoom_level, py * self.zoom_level
            self.canvas.create_oval(px_canvas - 12, py_canvas - 12, px_canvas + 12, py_canvas + 12,
                                    fill='blue', outline='black', width=3)
        # Draw completed polygons

        for idx, poly in enumerate(self.polygons):
            coords = []
            for px, py in poly.points:
                coords.extend([px * self.zoom_level, py * self.zoom_level])
            fill_colour = getattr(poly, 'fill_color', POLYGON_FILL_COLORS[idx % len(POLYGON_FILL_COLORS)])
            self.canvas.create_polygon(
                coords,
                fill=fill_colour,
                outline='',
                width=0,
                stipple='gray12'
            )
            outline_color = 'red' if idx == self.selected_polygon else 'blue'
            self.canvas.create_polygon(coords, fill='', outline=outline_color, width=2)
            meta = getattr(poly, 'metadata', {}) or {}
            room_id = str(meta.get('id') or '').strip()
            room_name = str(meta.get('name') or '').strip()
            label_lines = [
                f"ID: {room_id or 'N/A'}",
                f"Name: {room_name or 'N/A'}",
            ]
            label_text = "\n".join(label_lines)
            centroid = _polygon_centroid(poly.points)
            if centroid:
                cx, cy = centroid
                cx_canvas = cx * self.zoom_level
                cy_canvas = cy * self.zoom_level
                font_size = max(9, int(12 * (self.zoom_level ** 0.3)))
                font = ("TkDefaultFont", font_size, "bold")
                self.canvas.create_text(cx_canvas + 1, cy_canvas + 1, text=label_text, fill='white', font=font, justify=tk.CENTER)
                self.canvas.create_text(cx_canvas, cy_canvas, text=label_text, fill='black', font=font, justify=tk.CENTER)
        # Draw current polygon (lines connecting points) while drawing
        if self.draw_mode and len(self.current_polygon) > 0:
            coords = []
            for px, py in self.current_polygon:
                coords.extend([px * self.zoom_level, py * self.zoom_level])
            if len(coords) >= 4:
                self.canvas.create_line(coords, fill='green', width=2)
            for idx, (px, py) in enumerate(self.current_polygon):
                cx = px * self.zoom_level
                cy = py * self.zoom_level
                radius = 6 + (2 if idx == 0 else 0)
                self.canvas.create_oval(
                    cx - radius,
                    cy - radius,
                    cx + radius,
                    cy + radius,
                    fill='red',
                    outline='white',
                    width=2,
                )
        # Highlight vertices of the selected polygon with angle information
        if self.selected_polygon is not None:
            poly = self.polygons[self.selected_polygon]
            pts = poly.points
            n = len(pts)
            for i in range(n):
                x, y = pts[i]
                x_prev, y_prev = pts[i - 1]
                x_next, y_next = pts[(i + 1) % n]
                v1 = (x - x_prev, y - y_prev)
                v2 = (x_next - x, y_next - y)
                # Compute angle between adjacent segments
                dot = v1[0] * v2[0] + v1[1] * v2[1]
                det = v1[0] * v2[1] - v1[1] * v2[0]
                ang = math.atan2(det, dot)
                deg = abs(math.degrees(ang))
                # Colour code: green for near‑90° (perpendicular), red otherwise
                color = 'green' if abs(deg - 90) < 8 else 'red'
                px_canvas, py_canvas = x * self.zoom_level, y * self.zoom_level
                self.canvas.create_oval(
                    px_canvas - 6, py_canvas - 6, px_canvas + 6, py_canvas + 6,
                    fill=color, outline='black', width=2
                )

    # ----- Information Label -----
    def update_info_label(self) -> None:
        """Update the info label to reflect selected polygon's metrics and metadata."""
        # Keep buttons in sync with selection
        self.update_buttons_state()
        if self.selected_polygon is None:
            self.info_label.config(text="No polygon selected.")
            return
        poly = self.polygons[self.selected_polygon]
        area_real = poly.area_px * (self.scale_factor ** 2)
        perim_real = poly.perimeter_px * self.scale_factor
        meta = poly.metadata
        unit_label = self.scale_unit or "units"
        info = (
            f"ID: {meta.get('id', '')}\n"
            f"Name: {meta.get('name', '')}\n"
            f"Area: {area_real:.2f} sq {unit_label}\n"
            f"Perimeter: {perim_real:.2f} {unit_label}"
        )
        self.info_label.config(text=info)

    # ----- Exporting Data -----
    def export_csv(self) -> None:
        facade.export_csv(self)

    # ----- 3D Visualisation -----
    def show_3d_view(self) -> None:
        facade.three_d_show(self)

    # ----- Panel Layout Optimisation -----
    def optimize_panels(self) -> None:
        facade.panels_optimize(self)

def main() -> None:
    if tk is None:
        # Tkinter is unavailable (e.g. headless environment)
        raise RuntimeError("Tkinter is not available in this environment. Please run this script on a system with a graphical desktop and Tk installed.")
    root = tk.Tk()
    app = MeasureAppGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()

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

import json
import math
import os
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

import fitz  # PyMuPDF
from PIL import Image

try:
    import tkinter as tk
    from tkinter import filedialog, simpledialog, messagebox
    from PIL import ImageTk
except ImportError:
    # When Tkinter is unavailable (e.g. headless environment), set tk to None.
    tk = None  # type: ignore

import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401


def pdf_page_to_image(pdf_path: str, page_number: int = 0) -> Image.Image:
    """Load the specified page of a PDF and convert it to a PIL Image."""
    with open(pdf_path, 'rb') as f:
        doc = fitz.open(stream=f.read(), filetype='pdf')
    if page_number < 0 or page_number >= len(doc):
        raise ValueError(f"Invalid page number {page_number} for PDF with {len(doc)} pages")
    page = doc.load_page(page_number)
    # Render at ~144 DPI for good detail (zoom factor 2).
    zoom = 2
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    mode = 'RGB' if pix.alpha == 0 else 'RGBA'
    img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
    return img


def generate_3d_image(polygons: List[List[Tuple[float, float]]], height: float = 1.0) -> Image.Image:
    """Generate a static 3D extrusion plot and return it as a PIL Image."""
    fig = plt.figure(figsize=(6, 6))
    ax = fig.add_subplot(111, projection='3d')
    for idx, pts in enumerate(polygons):
        if len(pts) < 3:
            continue
        xs = [p[0] for p in pts] + [pts[0][0]]
        ys = [p[1] for p in pts] + [pts[0][1]]
        zs_bottom = [0] * len(xs)
        zs_top = [height] * len(xs)
        color = f'C{idx % 10}'
        ax.plot(xs, ys, zs_bottom, color=color, alpha=0.6)
        ax.plot(xs, ys, zs_top, color=color, alpha=0.6)
        for i in range(len(pts)):
            x0, y0 = pts[i]
            ax.plot([x0, x0], [y0, y0], [0, height], color=color, alpha=0.6)
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Height')
    # Normalise axes to [0,1] for consistency; caller is expected to normalise
    # polygon coordinates relative to the page before calling this function.
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_zlim(0, height)
    ax.view_init(elev=20, azim=30)
    ax.grid(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_zticks([])
    buf = os.path.join('/tmp', 'extrusion.png')
    fig.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    img = Image.open(buf)
    return img


def shoelace_area(points: List[Tuple[float, float]]) -> float:
    """Return the absolute area of a polygon using the shoelace formula."""
    if len(points) < 3:
        return 0.0
    area = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def polygon_perimeter(points: List[Tuple[float, float]]) -> float:
    """Return the perimeter length of a polygon."""
    if len(points) < 2:
        return 0.0
    perim = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        perim += math.hypot(x2 - x1, y2 - y1)
    return perim


def point_in_polygon(pt: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
    """Ray casting algorithm to determine if a point lies within a polygon."""
    x, y = pt
    inside = False
    n = len(polygon)
    if n < 3:
        return False
    p1x, p1y = polygon[0]
    for i in range(n + 1):
        p2x, p2y = polygon[i % n]
        if min(p1y, p2y) < y <= max(p1y, p2y) and x <= max(p1x, p2x):
            if p1y != p2y:
                xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
            if p1x == p2x or x <= xinters:
                inside = not inside
        p1x, p1y = p2x, p2y
    return inside


@dataclass
class PolygonData:
    points: List[Tuple[float, float]] = field(default_factory=list)
    area_px: float = 0.0
    perimeter_px: float = 0.0
    metadata: dict = field(default_factory=dict)

    def compute_metrics(self) -> None:
        """Recompute area and perimeter in pixel units."""
        self.area_px = shoelace_area(self.points)
        self.perimeter_px = polygon_perimeter(self.points)


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
        # Rotation buttons.
        self.rotate_left_btn = tk.Button(ctrl_canvas_frame, text="Rotate Left", command=self.rotate_left)
        self.rotate_left_btn.pack(side=tk.LEFT, padx=2)
        self.rotate_right_btn = tk.Button(ctrl_canvas_frame, text="Rotate Right", command=self.rotate_right)
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
        tk.Button(side_frame, text="Straighten Polygon", command=self.straighten_polygon).pack(fill=tk.X)
        tk.Button(side_frame, text="Undo Straighten", command=self.undo_straighten).pack(fill=tk.X)
        # Labels to display the current scale and selection info.
        self.scale_unit = "units"
        self.scale_label = tk.Label(side_frame, text=f"Scale: 1.0 {self.scale_unit}/pixel")
        self.scale_label.pack(fill=tk.X, pady=(10, 0))
        self.info_label = tk.Label(side_frame, text="No polygon selected.")
        self.info_label.pack(fill=tk.X)
        # Bind mouse events for drawing, panning and dragging.
        # Left mouse button handles drawing polygons and selecting regions.
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        # Right mouse button for panning via scan functionality.
        self.canvas.bind("<ButtonPress-3>", self.on_pan_start)
        self.canvas.bind("<B3-Motion>", self.on_pan_move)
        # Motion event for zoom preview (enabled only in drawing/scale modes).
        self.canvas.bind("<Motion>", self.on_canvas_motion)
        # Dragging vertices (left button press, move and release) outside of draw/scale mode.
        self.canvas.bind("<ButtonPress-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_drag_end)
        # Data structures and state variables.
        self.image: Optional[Image.Image] = None  # Original PDF page (resized to fit)
        self.photo: Optional[ImageTk.PhotoImage] = None  # PhotoImage for Tkinter display
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
        self.scale_preview_line_id: Optional[int] = None  # Canvas ID for rubber-band preview
        # Zoom/pan/rotation state
        self.zoom_level: float = 1.0
        self.image_rotation: int = 0  # Rotation in degrees (0, 90, 180, 270)
        # Straightening backup for undo
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

    # ----- Pan/Zoom/Rotate Button Setup -----
    def add_pan_zoom_buttons(self, frame: tk.Frame) -> None:
        """Add pan and zoom buttons to the provided frame."""
        # Clear any existing buttons (useful when reinitialising)
        for btn in self.pan_zoom_buttons:
            btn.destroy()
        self.pan_zoom_buttons.clear()
        # Zoom controls
        self.pan_zoom_buttons.append(tk.Button(frame, text="Zoom In", command=self.zoom_in))
        self.pan_zoom_buttons.append(tk.Button(frame, text="Zoom Out", command=self.zoom_out))
        # Pan controls (move by 50 units at current zoom level)
        self.pan_zoom_buttons.append(tk.Button(frame, text="Pan Left", command=lambda: self.pan_canvas(-50, 0)))
        self.pan_zoom_buttons.append(tk.Button(frame, text="Pan Right", command=lambda: self.pan_canvas(50, 0)))
        self.pan_zoom_buttons.append(tk.Button(frame, text="Pan Up", command=lambda: self.pan_canvas(0, -50)))
        self.pan_zoom_buttons.append(tk.Button(frame, text="Pan Down", command=lambda: self.pan_canvas(0, 50)))
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
        """Prompt the user to select a PDF file and load its first page."""
        path = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        try:
            img = pdf_page_to_image(path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load PDF: {e}")
            return
        # Resize image to fit within the window while leaving space for controls.
        max_w = max(800, int(self.root.winfo_width() * 0.7))
        max_h = max(600, int(self.root.winfo_height() * 0.9))
        scale = min(max_w / img.width, max_h / img.height, 1.0)
        if scale < 1.0:
            new_size = (int(img.width * scale), int(img.height * scale))
            try:
                resample = Image.Resampling.LANCZOS
            except AttributeError:
                resample = Image.LANCZOS
            img = img.resize(new_size, resample)
        # Store the resized image (prior to rotation/zoom) and reset rotation/zoom
        self.image = img
        self.photo = ImageTk.PhotoImage(img)
        self.image_rotation = 0
        self.zoom_level = 1.0
        # Configure the canvas scroll region and display the image
        self.canvas.config(scrollregion=(0, 0, img.width, img.height))
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        # Reset measurement state
        self.polygons.clear()
        self.current_polygon.clear()
        self.scale_points.clear()
        self.scale_artifact = None
        self.scale_marker_id = None
        self.scale_line_id = None
        self.scale_factor = 1.0
        self.scale_unit = "units"
        self.scale_label.config(text=f"Scale: {self.scale_factor:.4f} {self.scale_unit}/pixel")
        self.clear_scale_preview()
        self.canvas.config(cursor="")
        self.root.unbind("<Escape>")
        self.info_label.config(text="No polygon selected.")
        self.selected_polygon = None
        self.draw_mode = False
        self.scale_mode = False
        self._straighten_backup = None
        # Hide any zoom preview window
        self.hide_zoom_preview()

    def load_config(self) -> None:
        """Load panel configuration from a JSON file."""
        path = filedialog.askopenfilename(title="Select Config JSON", filetypes=[("JSON files", "*.json")])
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            self.config.update(cfg)
            messagebox.showinfo("Config", "Configuration loaded.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration: {e}")

    def save_config(self) -> None:
        """Save the current configuration to a JSON file."""
        path = filedialog.asksaveasfilename(title="Save Config", defaultextension='.json', filetypes=[("JSON files", "*.json")])
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
            messagebox.showinfo("Config", "Configuration saved.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")

    # ----- Mode Selection -----
    def set_scale_mode(self) -> None:
        """Enter scale definition mode. The user will pick two points representing a known distance."""
        if self.image is None:
            messagebox.showwarning("Warning", "Load a PDF first.")
            return
        # Enable scale mode and disable draw mode
        self.scale_mode = True
        self.draw_mode = False
        # Clear existing scale points and transient artifacts
        self.scale_points.clear()
        # Remove any existing scale markers/lines from canvas
        if self.scale_marker_id is not None:
            self.canvas.delete(self.scale_marker_id)
            self.scale_marker_id = None
        if self.scale_line_id is not None:
            self.canvas.delete(self.scale_line_id)
            self.scale_line_id = None
        self.clear_scale_preview()
        self.canvas.config(cursor="target")
        self.root.bind("<Escape>", self.cancel_scale_mode)
        messagebox.showinfo(
            "Set Unit/Scale",
            "Click two points on a known distance.\n"
            "A target cursor will appear for precise placement.\n"
            "Press Esc at any time to cancel."
        )
        # Bind motion events to show zoom preview while selecting scale
        self.canvas.bind("<Motion>", self.on_canvas_motion)

    def clear_scale_preview(self) -> None:
        """Remove the temporary rubber-band line used while selecting scale points."""
        if self.scale_preview_line_id is not None:
            self.canvas.delete(self.scale_preview_line_id)
            self.scale_preview_line_id = None

    def exit_scale_mode(self) -> None:
        """Common cleanup executed when leaving scale mode."""
        self.scale_mode = False
        self.canvas.config(cursor="")
        self.clear_scale_preview()
        self.hide_zoom_preview()
        self.root.unbind("<Escape>")
        # Temporary scale line re-rendered via redraw; drop any stale canvas IDs.
        self.scale_line_id = None
        self.scale_marker_id = None

    def cancel_scale_mode(self, event=None) -> None:
        """Cancel scale selection without modifying the existing scale."""
        if not self.scale_mode:
            return
        if self.scale_marker_id is not None:
            self.canvas.delete(self.scale_marker_id)
            self.scale_marker_id = None
        if self.scale_line_id is not None:
            self.canvas.delete(self.scale_line_id)
            self.scale_line_id = None
        self.scale_points.clear()
        self.exit_scale_mode()
        self.redraw()

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
        """Enter polygon drawing mode to outline rooms."""
        if self.image is None:
            messagebox.showwarning("Warning", "Load a PDF first.")
            return
        self.draw_mode = True
        self.scale_mode = False
        self.current_polygon.clear()
        messagebox.showinfo("Draw Polygon", "Click points to define the polygon. Click near the first point to finish.")
        # Bind motion events to show zoom preview while drawing
        self.canvas.bind("<Motion>", self.on_canvas_motion)

    # ----- Canvas Click Handling -----
    def on_canvas_click(self, event) -> None:
        """Handle mouse clicks on the canvas for scale definition, drawing, and selection."""
        if self.image is None:
            return
        # Convert screen coordinates to canvas coordinates (taking panning into account)
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        # Scale mode: collect two points and compute scale factor
        if self.scale_mode:
            # Append the point (convert from display to image coordinates by dividing by zoom)
            self.scale_points.append((x / self.zoom_level, y / self.zoom_level))
            # If it's the first point, draw a large marker
            if len(self.scale_points) == 1:
                # Remove any previous marker
                if self.scale_marker_id is not None:
                    self.canvas.delete(self.scale_marker_id)
                px, py = self.scale_points[0]
                px *= self.zoom_level
                py *= self.zoom_level
                self.scale_marker_id = self.canvas.create_oval(
                    px - 10, py - 10, px + 10, py + 10,
                    fill='purple', outline='black', width=3
                )
                # Redraw to overlay marker on image
                self.redraw()
                return
            # Second point: draw persistent scale line and ask user for real length
            if len(self.scale_points) == 2:
                px1, py1 = self.scale_points[0]
                px2, py2 = self.scale_points[1]
                # Coordinates in canvas space for drawing
                px1_canvas, py1_canvas = px1 * self.zoom_level, py1 * self.zoom_level
                px2_canvas, py2_canvas = px2 * self.zoom_level, py2 * self.zoom_level
                # Remove the first marker
                if self.scale_marker_id is not None:
                    self.canvas.delete(self.scale_marker_id)
                    self.scale_marker_id = None
                self.clear_scale_preview()
                dx = px2 - px1
                dy = py2 - py1
                pixel_dist = math.hypot(dx, dy)
                if pixel_dist == 0:
                    messagebox.showerror("Set Unit/Scale", "Select two distinct points to set the scale.")
                    self.scale_points.clear()
                    self.redraw()
                    return
                # Draw dashed line and end circles for scale reference
                self.scale_line_id = self.canvas.create_line(
                    px1_canvas, py1_canvas, px2_canvas, py2_canvas,
                    fill='purple', width=4, dash=(6, 2)
                )
                self.canvas.create_oval(px1_canvas - 8, py1_canvas - 8, px1_canvas + 8, py1_canvas + 8,
                                        fill='purple', outline='black', width=2)
                self.canvas.create_oval(px2_canvas - 8, py2_canvas - 8, px2_canvas + 8, py2_canvas + 8,
                                        fill='purple', outline='black', width=2)
                unit = self._prompt_scale_unit()
                if unit is None:
                    self.cancel_scale_mode()
                    return
                real_len = self._prompt_scale_length(unit)
                if real_len is None:
                    self.cancel_scale_mode()
                    return
                self.scale_factor = real_len / pixel_dist
                self.scale_unit = unit
                self.scale_label.config(text=f"Scale: {self.scale_factor:.4f} {self.scale_unit}/pixel")
                # Store the scale artifact for persistent display
                self.scale_artifact = {
                    'points': self.scale_points.copy(),
                    'real_length': real_len,
                    'pixel_length': pixel_dist,
                    'unit': self.scale_unit,
                    'scale_factor': self.scale_factor
                }
                self.scale_points.clear()
                self.exit_scale_mode()
                self.update_info_label()
                # Redraw so the persistent scale line is integrated into the canvas
                self.redraw()
            return
        # Draw mode: build up points for a new polygon
        if self.draw_mode:
            # Append point in image coordinates (divide by zoom)
            self.current_polygon.append((x / self.zoom_level, y / self.zoom_level))
            # If user clicks near the first point and at least three points exist, close polygon
            if len(self.current_polygon) >= 3:
                fx, fy = self.current_polygon[0]
                if abs((x / self.zoom_level) - fx) < 5 and abs((y / self.zoom_level) - fy) < 5:
                    # Replace last point with the first to close the loop
                    self.current_polygon[-1] = (fx, fy)
                    self.finish_polygon()
                    return
            self.redraw()
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
        """Finalize the current polygon, compute metrics, prompt metadata and store it."""
        if len(self.current_polygon) < 3:
            self.current_polygon.clear()
            return
        poly = PolygonData(points=self.current_polygon.copy())
        poly.compute_metrics()
        room_id = simpledialog.askstring("Metadata", "Enter Room ID:") or ''
        room_name = simpledialog.askstring("Metadata", "Enter Room Name:") or ''
        poly.metadata = {'id': room_id, 'name': room_name}
        self.polygons.append(poly)
        self.current_polygon.clear()
        # Exit draw mode
        self.draw_mode = False
        # Select the newly created polygon
        self.selected_polygon = len(self.polygons) - 1
        self.update_info_label()
        self.redraw()

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

    # ----- Straightening Polygons -----
    def straighten_polygon(self) -> None:
        """Straighten the selected polygon by converting segments between near‑right angles to straight lines."""
        if self.selected_polygon is None:
            messagebox.showwarning("Warning", "Select a polygon first.")
            return
        poly = self.polygons[self.selected_polygon]
        if len(poly.points) < 3:
            messagebox.showwarning("Warning", "Polygon must have at least 3 points.")
            return
        # Backup original points for undo
        self._straighten_backup = poly.points.copy()
        pts = poly.points
        n = len(pts)
        # Identify indices of vertices with near‑right angles (within ±8° of 90°)
        green_indices = []
        for i in range(n):
            x, y = pts[i]
            x_prev, y_prev = pts[i - 1]
            x_next, y_next = pts[(i + 1) % n]
            v1 = (x - x_prev, y - y_prev)
            v2 = (x_next - x, y_next - y)
            dot = v1[0] * v2[0] + v1[1] * v2[1]
            det = v1[0] * v2[1] - v1[1] * v2[0]
            ang = math.atan2(det, dot)
            deg = abs(math.degrees(ang))
            if abs(deg - 90) < 8:
                green_indices.append(i)
        # Need at least two right‑angle vertices to straighten segments between them
        if len(green_indices) < 2:
            messagebox.showinfo("Straighten", "No sufficient green points to straighten.")
            return
        new_points: List[Tuple[float, float]] = []
        used = set()
        for idx in range(len(green_indices)):
            i1 = green_indices[idx]
            i2 = green_indices[(idx + 1) % len(green_indices)]
            x1, y1 = pts[i1]
            # Always keep the first green point
            new_points.append((x1, y1))
            used.add(i1)
            # Collect indices of intermediate points between i1 and i2 (wrapping around)
            intermediates = []
            j = (i1 + 1) % n
            while j != i2:
                intermediates.append(j)
                j = (j + 1) % n
            if intermediates:
                x2, y2 = pts[i2]
                count = len(intermediates) + 1
                # Linearly interpolate points along the straight segment
                for k, idx_mid in enumerate(intermediates, start=1):
                    t = k / count
                    xm = x1 + t * (x2 - x1)
                    ym = y1 + t * (y2 - y1)
                    new_points.append((xm, ym))
                    used.add(idx_mid)
        # Ensure polygon is closed
        if len(new_points) > 2:
            new_points[-1] = new_points[0]
        poly.points = new_points
        poly.compute_metrics()
        self.redraw()

    def undo_straighten(self) -> None:
        """Undo the last straightening operation on the selected polygon."""
        if self.selected_polygon is None or self._straighten_backup is None:
            messagebox.showwarning("Warning", "No straighten operation to undo.")
            return
        poly = self.polygons[self.selected_polygon]
        poly.points = self._straighten_backup
        poly.compute_metrics()
        self._straighten_backup = None
        self.redraw()

    # ----- Zoom Preview -----
    def show_zoom_preview(self, x: float, y: float) -> None:
        """Display a small window showing a magnified area around the pointer."""
        if self.image is None:
            return
        # Convert pointer coords to image space (accounting for panning via canvasx/canvasy)
        img_x = int(self.canvas.canvasx(x) / self.zoom_level)
        img_y = int(self.canvas.canvasy(y) / self.zoom_level)
        # Define region around pointer (50x50 pixels from original image)
        region_size = 50
        half = region_size // 2
        left = max(img_x - half, 0)
        upper = max(img_y - half, 0)
        right = min(img_x + half, self.image.width)
        lower = min(img_y + half, self.image.height)
        crop = self.image.crop((left, upper, right, lower))
        # Resize to preview window size using nearest neighbour for crispness
        zoomed = crop.resize(
            (self.zoom_preview_size, self.zoom_preview_size),
            Image.NEAREST
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

    def on_canvas_motion(self, event) -> None:
        """Handle mouse motion events to show zoom preview when appropriate."""
        # Show preview only during scale or draw mode
        if not (self.scale_mode or self.draw_mode):
            self.hide_zoom_preview()
            self.clear_scale_preview()
            return
        self.show_zoom_preview(event.x, event.y)
        if self.scale_mode and len(self.scale_points) == 1:
            px, py = self.scale_points[0]
            x1 = px * self.zoom_level
            y1 = py * self.zoom_level
            x2 = self.canvas.canvasx(event.x)
            y2 = self.canvas.canvasy(event.y)
            if self.scale_preview_line_id is None:
                self.scale_preview_line_id = self.canvas.create_line(
                    x1, y1, x2, y2,
                    fill='purple', width=2, dash=(2, 4)
                )
            else:
                self.canvas.coords(self.scale_preview_line_id, x1, y1, x2, y2)
        else:
            self.clear_scale_preview()

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
        # Draw marker for first scale point if still awaiting second point
        elif self.scale_mode and len(self.scale_points) == 1:
            px, py = self.scale_points[0]
            px_canvas, py_canvas = px * self.zoom_level, py * self.zoom_level
            self.canvas.create_oval(px_canvas - 10, py_canvas - 10, px_canvas + 10, py_canvas + 10,
                                    fill='purple', outline='black', width=3)
        # Draw completed polygons
        for idx, poly in enumerate(self.polygons):
            coords = []
            for px, py in poly.points:
                coords.extend([px * self.zoom_level, py * self.zoom_level])
            outline_color = 'red' if idx == self.selected_polygon else 'blue'
            self.canvas.create_polygon(coords, fill='', outline=outline_color, width=2)
        # Draw current polygon (lines connecting points) while drawing
        if self.draw_mode and len(self.current_polygon) > 0:
            coords = []
            for px, py in self.current_polygon:
                coords.extend([px * self.zoom_level, py * self.zoom_level])
            self.canvas.create_line(coords, fill='green', width=2)
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
        """Export measurements and metadata for all polygons to a CSV file."""
        if not self.polygons:
            messagebox.showwarning("Warning", "No polygons to export.")
            return
        path = filedialog.asksaveasfilename(title="Save CSV", defaultextension='.csv', filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('polygon_id,area,perimeter,metadata\n')
                for idx, poly in enumerate(self.polygons, start=1):
                    area_real = poly.area_px * (self.scale_factor ** 2)
                    perim_real = poly.perimeter_px * self.scale_factor
                    meta_str = json.dumps(poly.metadata)
                    f.write(f'{idx},{area_real},{perim_real},"{meta_str}"\n')
            messagebox.showinfo("Export", "Measurements exported successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export CSV: {e}")

    # ----- 3D Visualisation -----
    def show_3d_view(self) -> None:
        """Generate and display a 3D extrusion of all drawn polygons."""
        if not self.polygons:
            messagebox.showwarning("Warning", "Draw at least one polygon first.")
            return
        if self.image is None:
            return
        width, height_img = self.image.size
        # Normalise polygon coordinates to [0,1] for 3D plot
        norm_polys: List[List[Tuple[float, float]]] = []
        for poly in self.polygons:
            pts = [(x / width, y / height_img) for (x, y) in poly.points]
            norm_polys.append(pts)
        height = float(self.config.get('extrusion_height', 1.0))
        try:
            img3d = generate_3d_image(norm_polys, height)
            # Show in a new window
            top = tk.Toplevel(self.root)
            top.title("3D View")
            photo3d = ImageTk.PhotoImage(img3d)
            lbl = tk.Label(top, image=photo3d)
            lbl.image = photo3d  # Keep a reference
            lbl.pack()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate 3D view: {e}")

    # ----- Panel Layout Optimisation -----
    def optimize_panels(self) -> None:
        """Overlay an optimised panel layout inside the selected polygon."""
        if self.selected_polygon is None:
            messagebox.showwarning("Warning", "Select a polygon first.")
            return
        poly = self.polygons[self.selected_polygon]
        # Convert panel dimensions from real units to pixels
        panel_w_real = float(self.config.get('panel_width', 1.0))
        panel_h_real = float(self.config.get('panel_height', 1.0))
        if self.scale_factor == 0:
            return
        panel_w_px = panel_w_real / self.scale_factor
        panel_h_px = panel_h_real / self.scale_factor
        # Bounding box of polygon
        xs = [p[0] for p in poly.points]
        ys = [p[1] for p in poly.points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        width = max_x - min_x
        height = max_y - min_y
        cols = int(width // panel_w_px)
        rows = int(height // panel_h_px)
        rects: List[List[Tuple[float, float]]] = []
        for i in range(cols):
            for j in range(rows):
                rx = min_x + i * panel_w_px
                ry = min_y + j * panel_h_px
                r_points = [
                    (rx, ry),
                    (rx + panel_w_px, ry),
                    (rx + panel_w_px, ry + panel_h_px),
                    (rx, ry + panel_h_px)
                ]
                # Use the rectangle centre for a containment test (approximate)
                cx = rx + panel_w_px / 2
                cy = ry + panel_h_px / 2
                if point_in_polygon((cx, cy), poly.points):
                    rects.append(r_points)
        # Redraw existing content then overlay panel rectangles
        self.redraw()
        for rect in rects:
            coords: List[float] = []
            for x, y in rect:
                coords.extend([x * self.zoom_level, y * self.zoom_level])
            self.canvas.create_polygon(coords, fill='', outline='orange', width=1, dash=(4, 2))


def main() -> None:
    if tk is None:
        # Tkinter is unavailable (e.g. headless environment)
        raise RuntimeError("Tkinter is not available in this environment. Please run this script on a system with a graphical desktop and Tk installed.")
    root = tk.Tk()
    app = MeasureAppGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()

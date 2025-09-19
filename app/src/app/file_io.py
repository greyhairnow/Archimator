from __future__ import annotations

import json
from typing import TYPE_CHECKING, Optional

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
except Exception:  # pragma: no cover
    tk = None  # type: ignore
    filedialog = None  # type: ignore
    messagebox = None  # type: ignore

import pymupdf as fitz
from PIL import Image

if TYPE_CHECKING:
    from .gui_client import MeasureAppGUI


def _pdf_page_to_image(pdf_path: str, page_number: int = 0) -> Image.Image:
    """Load the specified page of a PDF and convert it to a PIL Image."""
    with open(pdf_path, 'rb') as f:
        doc = fitz.open(stream=f.read(), filetype='pdf')
    if page_number < 0 or page_number >= len(doc):
        raise ValueError(f"Invalid page number {page_number} for PDF with {len(doc)} pages")
    page = doc.load_page(page_number)
    zoom = 2
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    mode = 'RGB' if pix.alpha == 0 else 'RGBA'
    img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
    return img


def load_pdf(app: "MeasureAppGUI") -> None:
    if filedialog is None:
        return
    path = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF files", "*.pdf")])
    if not path:
        return
    try:
        img = _pdf_page_to_image(path)
    except Exception as e:
        if messagebox:
            messagebox.showerror("Error", f"Failed to load PDF: {e}")
        return
    max_w = max(800, int(app.root.winfo_width() * 0.7))
    max_h = max(600, int(app.root.winfo_height() * 0.9))
    scale = min(max_w / img.width, max_h / img.height, 1.0)
    if scale < 1.0:
        new_size = (int(img.width * scale), int(img.height * scale))
        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.LANCZOS
        img = img.resize(new_size, resample)

    from PIL import ImageTk

    app.current_document_path = path
    app.image = img
    app.photo = ImageTk.PhotoImage(img)
    app.display_image = img
    app.image_rotation = 0
    app.zoom_level = 1.0
    app.canvas.config(scrollregion=(0, 0, img.width, img.height))
    app.canvas.delete("all")
    app.canvas.create_image(0, 0, anchor=tk.NW, image=app.photo)
    # Reset measurement state
    app.polygons.clear()
    app.current_polygon.clear()
    app.scale_points.clear()
    app.scale_artifact = None
    app.scale_marker_id = None
    app.scale_line_id = None
    app.scale_factor = 1.0
    app.scale_unit = "units"
    app.scale_label.config(text=f"Scale: {app.scale_factor:.4f} {app.scale_unit}/pixel")
    app.info_label.config(text="No polygon selected.")
    app.selected_polygon = None
    app.draw_mode = False
    app.scale_mode = False
    app._straighten_backup = None
    app.hide_zoom_preview()


def load_config(app: "MeasureAppGUI") -> None:
    if filedialog is None:
        return
    path = filedialog.askopenfilename(title="Select Config JSON", filetypes=[("JSON files", "*.json")])
    if not path:
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        app.config.update(cfg)
        if messagebox:
            messagebox.showinfo("Config", "Configuration loaded.")
    except Exception as e:
        if messagebox:
            messagebox.showerror("Error", f"Failed to load configuration: {e}")


def save_config(app: "MeasureAppGUI") -> None:
    if filedialog is None:
        return
    path = filedialog.asksaveasfilename(title="Save Config", defaultextension='.json', filetypes=[("JSON files", "*.json")])
    if not path:
        return
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(app.config, f, indent=2)
        if messagebox:
            messagebox.showinfo("Config", "Configuration saved.")
    except Exception as e:
        if messagebox:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")

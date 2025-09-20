from __future__ import annotations

import json
from typing import TYPE_CHECKING

try:
    from tkinter import filedialog, messagebox
except Exception:  # pragma: no cover
    filedialog = None  # type: ignore
    messagebox = None  # type: ignore

if TYPE_CHECKING:
    from .gui_client import MeasureAppGUI


def export_csv(app: "MeasureAppGUI") -> None:
    if not app.polygons:
        if messagebox:
            messagebox.showwarning("Warning", "No polygons to export.")
        return
    if filedialog is None:
        return
    path = filedialog.asksaveasfilename(title="Save CSV", defaultextension='.csv', filetypes=[("CSV files", "*.csv")])
    if not path:
        return
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write('polygon_id,area,perimeter,metadata\n')
            for idx, poly in enumerate(app.polygons, start=1):
                area_real = poly.area_px * (app.scale_factor ** 2)
                perim_real = poly.perimeter_px * app.scale_factor
                meta_str = json.dumps(poly.metadata)
                f.write(f'{idx},{area_real},{perim_real},"{meta_str}"\n')
        if messagebox:
            messagebox.showinfo("Export", "Measurements exported successfully.")
    except Exception as e:
        if messagebox:
            messagebox.showerror("Error", f"Failed to export CSV: {e}")



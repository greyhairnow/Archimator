#!/usr/bin/env python3
"""
measure_app/main.py

A lightweight self‑contained web application for measuring areas on architectural
diagrams.  It exposes a tiny HTTP server that serves a HTML/JS frontend and a
handful of JSON endpoints.  Users can load a PDF and interactively draw
polygons on top of the diagram in their browser to estimate surface areas
and perimeters.  They can set a reference scale, attach metadata to each
polygon, export their measurements to CSV and even generate a simple 3D
extrusion of the layout.  Configuration options such as panel dimensions and
materials can be loaded from and saved to JSON files.

The server is deliberately implemented without external dependencies beyond
PyMuPDF (fitz), Pillow and Matplotlib, all of which are available in the
container environment.  It avoids frameworks like Flask to remain portable
and uses the built‑in `http.server` module instead.

To start the application run:

    python3 main.py

Then open your browser to http://localhost:8000 to interact with the tool.
"""

import base64
import io
import json
import os
import sys
import threading
import urllib.parse
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

REQUIRED_PACKAGES = [
    ("fitz", "pymupdf"),
    ("PIL", "pillow"),
    ("matplotlib", "matplotlib"),
]

def check_requirements():
    missing = []
    for mod, pkg in REQUIRED_PACKAGES:
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("\nERROR: Missing required packages:")
        for pkg in missing:
            print(f"    pip install {pkg}")
        print("Then re-run this script.\n")
        sys.exit(1)

check_requirements()

try:
    import fitz  # PyMuPDF for PDF to image conversion
except ImportError:
    print(
        "\nERROR: The 'fitz' module (PyMuPDF) is not installed.\n"
        "Please install it by running:\n"
        "    pip install pymupdf\n"
        "Then re-run this script.\n"
    )
    import sys; sys.exit(1)

from PIL import Image
import matplotlib
matplotlib.use('Agg')  # headless backend for 3D plot generation
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401, needed to register 3D projection


# Directory containing this script and the static assets
APP_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(APP_DIR, 'static')


def pdf_page_to_image(pdf_bytes: bytes, page_number: int = 0) -> Image.Image:
    """Convert a PDF page to a Pillow Image using PyMuPDF.

    Args:
        pdf_bytes: Raw bytes of the PDF document.
        page_number: Zero‑based index of the page to convert.

    Returns:
        A Pillow Image object representing the page.
    """
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    if page_number < 0 or page_number >= len(doc):
        raise ValueError(f"Invalid page number {page_number}. PDF has {len(doc)} pages.")
    page = doc.load_page(page_number)
    # Render at 150 DPI for a balance between quality and size
    zoom = 2  # 72dpi * 2 ~ 144dpi
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    mode = 'RGB' if pix.alpha == 0 else 'RGBA'
    img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
    return img


def encode_image_to_base64(img: Image.Image) -> str:
    """Encode a Pillow Image to a base64 PNG string for web transport."""
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('ascii')


def shoelace_area(points):
    """Compute the area of a polygon via the shoelace formula.

    Args:
        points: List of (x, y) tuples defining the polygon vertices in order.

    Returns:
        The signed area of the polygon. The absolute value is the actual area.
    """
    if len(points) < 3:
        return 0.0
    area = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return area / 2.0


def generate_3d_image(polygons, height=1.0):
    """Generate a static 3D extrusion of the polygons using matplotlib.

    Args:
        polygons: A list of dicts, each with keys 'points' (list of (x, y)
            coordinates) and optional 'color'. Coordinates should be normalised
            between 0 and 1.
        height: Extrusion height in the same units as the coordinate system.

    Returns:
        A base64 encoded PNG image of the 3D plot.
    """
    fig = plt.figure(figsize=(6, 6))
    ax = fig.add_subplot(111, projection='3d')
    # Plot each polygon as a prism extruded along z axis
    for idx, poly in enumerate(polygons):
        pts = poly['points']
        if len(pts) < 3:
            continue
        # Close the polygon
        xs = [p[0] for p in pts] + [pts[0][0]]
        ys = [p[1] for p in pts] + [pts[0][1]]
        zs_bottom = [0] * (len(xs))
        zs_top = [height] * (len(xs))
        color = poly.get('color', None) or f'C{idx % 10}'
        # Plot bottom face
        ax.plot(xs, ys, zs_bottom, color=color, alpha=0.6)
        # Plot top face
        ax.plot(xs, ys, zs_top, color=color, alpha=0.6)
        # Draw vertical edges
        for i in range(len(pts)):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % len(pts)]
            ax.plot([x0, x0], [y0, y0], [0, height], color=color, alpha=0.6)
    # Set axes limits and labels
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Height')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_zlim(0, height)
    ax.view_init(elev=20, azim=30)
    ax.grid(False)
    # Hide tick labels for a cleaner look
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_zticks([])
    buffer = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buffer, format='png', bbox_inches='tight')
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode('ascii')


class MeasureHTTPRequestHandler(SimpleHTTPRequestHandler):
    """Custom HTTP request handler serving the measure app and JSON endpoints."""

    # Use a slightly higher chunk size for file reading to reduce number of reads
    bufsize = 64 * 1024

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def log_message(self, format, *args):
        # Override to log to stderr; keep default logging
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(),
                                                self.log_date_time_string(),
                                                format % args))

    def do_POST(self):
        # Determine which endpoint we're handling
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        response = {}
        status = HTTPStatus.OK
        try:
            if path == '/upload_pdf':
                # Accept PDF upload and return a PNG of the first page
                form = self.parse_multipart(body)
                pdf_file = form.get('pdf')
                if not pdf_file:
                    raise ValueError('No PDF file provided')
                img = pdf_page_to_image(pdf_file)
                # Normalize image size if it's too large for typical screens
                max_dim = 2000
                if img.width > max_dim or img.height > max_dim:
                    scale = min(max_dim / img.width, max_dim / img.height)
                    new_size = (int(img.width * scale), int(img.height * scale))
                    img = img.resize(new_size, Image.ANTIALIAS)
                response = {
                    'image': encode_image_to_base64(img),
                    'width': img.width,
                    'height': img.height,
                }
            elif path == '/export_csv':
                # Export measurement data to a CSV string
                data = json.loads(body.decode('utf-8'))
                records = data.get('records', [])
                csv_lines = [
                    'polygon_id,area,perimeter,metadata\n'
                ]
                for rec in records:
                    poly_id = rec.get('id', '')
                    area = rec.get('area', '')
                    perimeter = rec.get('perimeter', '')
                    metadata = json.dumps(rec.get('metadata', {}), ensure_ascii=False)
                    csv_lines.append(f'{poly_id},{area},{perimeter},"{metadata}"\n')
                csv_str = ''.join(csv_lines)
                response = {'csv': base64.b64encode(csv_str.encode('utf-8')).decode('ascii')}
            elif path == '/generate_3d':
                data = json.loads(body.decode('utf-8'))
                polygons = data.get('polygons', [])
                height = float(data.get('height', 1.0))
                img_b64 = generate_3d_image(polygons, height)
                response = {'image': img_b64}
            elif path == '/optimize_layout':
                # Very simple panel packing algorithm.  Attempts to tile a polygon's
                # bounding box with rectangular panels of a given size; returns a
                # list of rectangles that fit entirely within the polygon.
                data = json.loads(body.decode('utf-8'))
                points = data.get('points', [])
                panel_width = float(data.get('panel_width', 1.0))
                panel_height = float(data.get('panel_height', 1.0))
                # Normalize polygon to bounding box [0,1] x [0,1]
                xs = [p[0] for p in points]
                ys = [p[1] for p in points]
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                width = max_x - min_x
                height_range = max_y - min_y
                # Sample grid inside bounding box
                rects = []
                rows = int(height_range // panel_height)
                cols = int(width // panel_width)
                for i in range(cols):
                    for j in range(rows):
                        # top left corner of rectangle
                        rx = min_x + i * panel_width
                        ry = min_y + j * panel_height
                        # define corners of this panel
                        r_points = [
                            [rx, ry],
                            [rx + panel_width, ry],
                            [rx + panel_width, ry + panel_height],
                            [rx, ry + panel_height]
                        ]
                        # Check if all rectangle corners are inside polygon (simple point in polygon)
                        if all(self.point_in_polygon(pt, points) for pt in r_points):
                            rects.append(r_points)
                response = {'rectangles': rects}
            elif path == '/load_config':
                # Load configuration JSON from uploaded file
                form = self.parse_multipart(body)
                cfg_file = form.get('config')
                if not cfg_file:
                    raise ValueError('No config file provided')
                cfg = json.loads(cfg_file.decode('utf-8'))
                response = {'config': cfg}
            elif path == '/save_config':
                data = json.loads(body.decode('utf-8'))
                cfg = data.get('config')
                # Save to a default location within the app directory
                cfg_path = os.path.join(APP_DIR, 'saved_config.json')
                with open(cfg_path, 'w', encoding='utf-8') as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
                response = {'status': 'saved', 'path': cfg_path}
            else:
                status = HTTPStatus.NOT_FOUND
                response = {'error': f'Unknown path {path}'}
        except Exception as e:
            status = HTTPStatus.INTERNAL_SERVER_ERROR
            response = {'error': str(e)}

        # Send response
        resp_bytes = json.dumps(response).encode('utf-8')
        self.send_response(status.value)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(resp_bytes)))
        self.end_headers()
        self.wfile.write(resp_bytes)

    def parse_multipart(self, body: bytes):
        """Parse multipart/form-data into a dict of fields -> bytes."""
        content_type = self.headers.get('Content-Type', '')
        if 'boundary=' not in content_type:
            raise ValueError('No boundary in Content-Type header')
        boundary = content_type.split('boundary=')[1].encode('utf-8')
        parts = body.split(b'--' + boundary)
        fields = {}
        for part in parts:
            if not part or part == b'--\r\n':
                continue
            headers, _, data = part.lstrip().partition(b'\r\n\r\n')
            header_lines = headers.decode('utf-8', errors='ignore').split('\r\n')
            disposition = [h for h in header_lines if h.startswith('Content-Disposition')]
            if not disposition:
                continue
            disp = disposition[0]
            # Extract the name attribute from the disposition
            name_part = [x for x in disp.split(';') if 'name=' in x]
            if not name_part:
                continue
            name = name_part[0].split('=')[1].strip().strip('"')
            # Remove trailing CRLF from data
            if data.endswith(b'\r\n'):
                data = data[:-2]
            fields[name] = data
        return fields

    @staticmethod
    def point_in_polygon(point, polygon):
        """Ray casting algorithm for determining if a point is inside a polygon.

        Args:
            point: [x, y] coordinate.
            polygon: list of [x, y] vertices.

        Returns:
            True if the point is inside the polygon, False otherwise.
        """
        x, y = point
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


def run_server(port: int = 8000):
    """Start the threaded HTTP server."""
    server_address = ('', port)
    handler_class = MeasureHTTPRequestHandler
    httpd = ThreadingHTTPServer(server_address, handler_class)
    print(f"Serving on http://localhost:{port} (Press CTRL+C to quit)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        httpd.server_close()


if __name__ == '__main__':
    run_server()
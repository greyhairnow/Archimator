// Front‑end logic for the measurement tool

// Global application state
let canvas = null;
let ctx = null;
let backgroundImg = new Image();
let imageLoaded = false;
let polygons = []; // {id, points: [{x,y}], area, perimeter, metadata, color}
let currentPolygon = [];
let selectedPolygon = null;
let drawingMode = false;
let scaleMode = false;
let scalePoints = [];
let scaleFactor = 1.0; // real units per pixel
let config = { panel_width: 1.0, panel_height: 1.0, extrusion_height: 1.0 };

// Utility: compute area and perimeter of polygon given list of points
function computeMetrics(pts) {
  let area = 0;
  let perimeter = 0;
  const n = pts.length;
  for (let i = 0; i < n; i++) {
    const x1 = pts[i].x;
    const y1 = pts[i].y;
    const x2 = pts[(i + 1) % n].x;
    const y2 = pts[(i + 1) % n].y;
    area += x1 * y2 - x2 * y1;
    perimeter += Math.hypot(x2 - x1, y2 - y1);
  }
  area = Math.abs(area) / 2.0;
  return { area, perimeter };
}

// Draw the image, existing polygons and current polygon
function redraw() {
  if (!canvas || !ctx || !imageLoaded) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(backgroundImg, 0, 0, canvas.width, canvas.height);
  // Draw existing polygons
  polygons.forEach(poly => {
    ctx.strokeStyle = poly === selectedPolygon ? '#e74c3c' : (poly.color || '#2980b9');
    ctx.lineWidth = poly === selectedPolygon ? 3 : 2;
    ctx.beginPath();
    poly.points.forEach((pt, idx) => {
      if (idx === 0) ctx.moveTo(pt.x, pt.y);
      else ctx.lineTo(pt.x, pt.y);
    });
    ctx.closePath();
    ctx.stroke();
    // Fill slightly if selected
    if (poly === selectedPolygon) {
      ctx.fillStyle = 'rgba(231, 76, 60, 0.1)';
      ctx.fill();
    }
  });
  // Draw current polygon lines
  if (drawingMode && currentPolygon.length > 0) {
    ctx.strokeStyle = '#27ae60';
    ctx.lineWidth = 2;
    ctx.beginPath();
    currentPolygon.forEach((pt, idx) => {
      if (idx === 0) ctx.moveTo(pt.x, pt.y);
      else ctx.lineTo(pt.x, pt.y);
    });
    ctx.stroke();
  }
  // Draw scale line if in scale mode
  if (scaleMode && scalePoints.length === 1) {
    const pt = scalePoints[0];
    ctx.strokeStyle = '#8e44ad';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(pt.x, pt.y, 4, 0, 2 * Math.PI);
    ctx.fillStyle = '#8e44ad';
    ctx.fill();
  } else if (scaleMode && scalePoints.length === 2) {
    ctx.strokeStyle = '#8e44ad';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(scalePoints[0].x, scalePoints[0].y);
    ctx.lineTo(scalePoints[1].x, scalePoints[1].y);
    ctx.stroke();
  }
}

// Convert mouse event coordinates to canvas coordinates
function getCanvasCoords(event) {
  const rect = canvas.getBoundingClientRect();
  const x = (event.clientX - rect.left) * (canvas.width / rect.width);
  const y = (event.clientY - rect.top) * (canvas.height / rect.height);
  return { x, y };
}

// Point in polygon for selection
function pointInPolygon(pt, poly) {
  let inside = false;
  const x = pt.x;
  const y = pt.y;
  const vertices = poly.points;
  for (let i = 0, j = vertices.length - 1; i < vertices.length; j = i++) {
    const xi = vertices[i].x, yi = vertices[i].y;
    const xj = vertices[j].x, yj = vertices[j].y;
    const intersect = ((yi > y) !== (yj > y)) &&
      (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
    if (intersect) inside = !inside;
  }
  return inside;
}

function showMessage(msg) {
  const messageDiv = document.getElementById('message');
  messageDiv.textContent = msg;
  if (msg) {
    setTimeout(() => { messageDiv.textContent = ''; }, 4000);
  }
}

// Initialize event listeners once DOM is loaded
window.addEventListener('DOMContentLoaded', () => {
  canvas = document.getElementById('diagramCanvas');
  ctx = canvas.getContext('2d');
  // Setup PDF input
  document.getElementById('pdfInput').addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('pdf', file);
    fetch('/upload_pdf', { method: 'POST', body: formData })
      .then(resp => resp.json())
      .then(data => {
        backgroundImg = new Image();
        backgroundImg.onload = () => {
          imageLoaded = true;
          canvas.width = backgroundImg.width;
          canvas.height = backgroundImg.height;
          redraw();
        };
        backgroundImg.src = 'data:image/png;base64,' + data.image;
        polygons = [];
        currentPolygon = [];
        selectedPolygon = null;
        scaleFactor = 1.0;
        document.getElementById('scaleInfo').textContent = '';
      })
      .catch(err => showMessage('Error uploading PDF: ' + err));
  });
  // Config load
  document.getElementById('configInput').addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        config = JSON.parse(reader.result);
        showMessage('Config loaded');
      } catch (err) {
        showMessage('Invalid config file');
      }
    };
    reader.readAsText(file);
  });
  // Config save
  document.getElementById('saveConfig').addEventListener('click', () => {
    const data = { config };
    fetch('/save_config', { method: 'POST', body: JSON.stringify(data) })
      .then(resp => resp.json())
      .then(res => showMessage('Config saved to server'))
      .catch(err => showMessage('Error saving config: ' + err));
  });
  // Set scale
  document.getElementById('setScale').addEventListener('click', () => {
    scaleMode = true;
    drawingMode = false;
    scalePoints = [];
    showMessage('Click two points on the known scale, then enter the real length');
  });
  // Draw polygon mode
  document.getElementById('drawPolygon').addEventListener('click', () => {
    if (!imageLoaded) { showMessage('Please load a PDF first'); return; }
    drawingMode = true;
    scaleMode = false;
    currentPolygon = [];
    selectedPolygon = null;
    redraw();
    showMessage('Click points to define the polygon. Double click to finish.');
  });
  // Export data
  document.getElementById('exportData').addEventListener('click', () => {
    if (polygons.length === 0) { showMessage('No polygons to export'); return; }
    const records = polygons.map(poly => ({
      id: poly.id,
      area: (poly.area * scaleFactor * scaleFactor).toFixed(3),
      perimeter: (poly.perimeter * scaleFactor).toFixed(3),
      metadata: poly.metadata || {}
    }));
    fetch('/export_csv', { method: 'POST', body: JSON.stringify({ records }) })
      .then(resp => resp.json())
      .then(data => {
        const csvData = atob(data.csv);
        const blob = new Blob([csvData], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'measurements.csv';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      });
  });
  // 3D view
  document.getElementById('view3d').addEventListener('click', () => {
    if (polygons.length === 0) { showMessage('Draw polygons first'); return; }
    // Normalize polygons to unit square relative to image size
    const normPolys = polygons.map((poly, idx) => {
      const pts = poly.points.map(pt => ({ x: pt.x / canvas.width, y: pt.y / canvas.height }));
      return { points: pts, color: null };
    });
    const height = config.extrusion_height || 1.0;
    fetch('/generate_3d', { method: 'POST', body: JSON.stringify({ polygons: normPolys, height }) })
      .then(resp => resp.json())
      .then(data => {
        const modal = document.getElementById('modal');
        const modalContent = document.getElementById('modalContent');
        modalContent.innerHTML = '<h3>3D View</h3><img src="data:image/png;base64,' + data.image + '" style="max-width:100%;">' +
          '<br><button id="closeModal">Close</button>';
        modal.classList.remove('hidden');
        document.getElementById('closeModal').addEventListener('click', () => {
          modal.classList.add('hidden');
        });
      });
  });
  // Optimize panel layout
  document.getElementById('optimizePanels').addEventListener('click', () => {
    if (!selectedPolygon) { showMessage('Select a polygon first'); return; }
    const panelWReal = config.panel_width || 1.0;
    const panelHReal = config.panel_height || 1.0;
    const panelW = panelWReal / scaleFactor;
    const panelH = panelHReal / scaleFactor;
    const pts = selectedPolygon.points.map(pt => [pt.x, pt.y]);
    fetch('/optimize_layout', { method: 'POST', body: JSON.stringify({ points: pts, panel_width: panelW, panel_height: panelH }) })
      .then(resp => resp.json())
      .then(data => {
        // Draw rectangles overlay
        redraw();
        ctx.strokeStyle = '#f1c40f';
        ctx.lineWidth = 1;
        data.rectangles.forEach(rect => {
          ctx.beginPath();
          ctx.moveTo(rect[0][0], rect[0][1]);
          for (let i = 1; i < rect.length; i++) {
            ctx.lineTo(rect[i][0], rect[i][1]);
          }
          ctx.closePath();
          ctx.stroke();
        });
      });
  });
  // Canvas click handler
  canvas.addEventListener('dblclick', (e) => {
    // Double click finishes current polygon if drawing
    if (drawingMode && currentPolygon.length >= 3) {
      finishCurrentPolygon();
    }
  });
  canvas.addEventListener('click', (e) => {
    if (!imageLoaded) return;
    const pt = getCanvasCoords(e);
    if (scaleMode) {
      scalePoints.push(pt);
      if (scalePoints.length === 2) {
        redraw();
        setTimeout(() => {
          const pixelDist = Math.hypot(scalePoints[1].x - scalePoints[0].x, scalePoints[1].y - scalePoints[0].y);
          const realLen = prompt('Enter the real length between the two points (in your desired units):');
          const val = parseFloat(realLen);
          if (val > 0) {
            scaleFactor = val / pixelDist;
            document.getElementById('scaleInfo').textContent = 'Scale: ' + scaleFactor.toFixed(4) + ' units per pixel';
          }
          scaleMode = false;
          scalePoints = [];
          redraw();
        }, 50);
      } else {
        redraw();
      }
      return;
    }
    if (drawingMode) {
      currentPolygon.push(pt);
      redraw();
      return;
    }
    // Selection mode
    selectedPolygon = null;
    for (let poly of polygons) {
      if (pointInPolygon(pt, poly)) {
        selectedPolygon = poly;
        break;
      }
    }
    updateInfoPanel();
    redraw();
  });
  // Keyboard listener: press Escape to cancel drawing
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      drawingMode = false;
      scaleMode = false;
      currentPolygon = [];
      scalePoints = [];
      redraw();
    }
  });
  // Metadata save
  document.getElementById('saveMetadata').addEventListener('click', () => {
    if (!selectedPolygon) return;
    const idVal = document.getElementById('metaId').value;
    const nameVal = document.getElementById('metaName').value;
    selectedPolygon.metadata = { id: idVal, name: nameVal };
    updateInfoPanel();
    showMessage('Metadata saved');
  });
});

function finishCurrentPolygon() {
  // Close polygon, compute metrics and store it
  if (currentPolygon.length < 3) return;
  const metrics = computeMetrics(currentPolygon);
  const polyId = 'poly' + (polygons.length + 1);
  const color = '#2980b9';
  polygons.push({ id: polyId, points: currentPolygon.slice(), area: metrics.area, perimeter: metrics.perimeter, metadata: {}, color });
  currentPolygon = [];
  drawingMode = false;
  showMessage('Polygon saved. Select it to add metadata.');
  redraw();
}

function updateInfoPanel() {
  const details = document.getElementById('polyDetails');
  const form = document.getElementById('metadataForm');
  if (selectedPolygon) {
    const areaReal = (selectedPolygon.area * scaleFactor * scaleFactor).toFixed(3);
    const perimReal = (selectedPolygon.perimeter * scaleFactor).toFixed(3);
    details.innerHTML = `<p>ID: ${selectedPolygon.id}</p>` +
      `<p>Area: ${areaReal} sq units</p>` +
      `<p>Perimeter: ${perimReal} units</p>` +
      `<p>Metadata: ${JSON.stringify(selectedPolygon.metadata)}</p>`;
    form.classList.remove('hidden');
    document.getElementById('metaId').value = selectedPolygon.metadata.id || '';
    document.getElementById('metaName').value = selectedPolygon.metadata.name || '';
  } else {
    details.textContent = 'No polygon selected.';
    form.classList.add('hidden');
  }
}
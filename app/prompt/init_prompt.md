As an advanced coding assistance, with advanced expertise, please create a desktop app, in python, with the following specifications.
 
# Design Specification

## Product Overview
A web-based application that transforms architectural PDFs into interactive measurement and estimation tools, enabling precise room dimensioning through polygon drawing and automated panel fitting calculations.

## Core Design Principles
- **Precision-First Interface**: Every interaction prioritizes measurement accuracy
- **Visual Clarity**: High contrast overlays on PDF backgrounds
- **Progressive Disclosure**: Complex features revealed as needed
- **Non-Destructive Workflow**: Original PDF remains unmodified

## Detailed Feature Specifications

### 1. PDF Loading & Display System

**Interface Components:**
- **Load PDF Button**: Prominent primary action button (min 44x44px touch target)
  - Icon: Document with upload arrow
  - States: Default, hover, loading, success, error
  - Supported formats: PDF up to 50MB
  
**Display Canvas:**
- **Viewport**: Full-screen mode with 16:9 aspect ratio optimization
- **Rendering**: Vector-based rendering for crisp zooming (up to 800%)
- **Pan & Zoom Controls**: 
  - Mouse wheel zoom with point-of-interest focus
  - Click-and-drag panning
  - Zoom slider (range: 25% - 800%)
  - Fit-to-screen button
  - 1:1 scale button

**Visual Feedback:**
- Loading spinner with percentage indicator
- Page thumbnails in collapsible sidebar (80px width)
- Current page indicator with total page count
- Grid overlay toggle (customizable spacing)

### 2. Configuration Management System

**Load Configuration Interface:**
- **File Browser Dialog**: 
  - Accepts: .json, .xml, .config formats
  - Preview pane showing configuration summary
  - Recent configurations dropdown (last 5)
  
**Configuration Display Panel:**
- **Collapsible sidebar** (320px width):
  - Panel dimensions section
  - Material properties accordion
  - Cost parameters table
  - Waste factor percentage slider (0-20%)
  
**Save Configuration:**
- Auto-save indicator with 5-minute intervals
- Manual save with keyboard shortcut (Ctrl+S)
- Version history with timestamps
- Export presets functionality

### 3. Scale Calibration System

**Auto-Detection Algorithm:**
- **Visual Indicators**:
  - Yellow highlighting box around detected scales
  - Confidence score display (0-100%)
  - Multiple scale detection with selection interface
  
**Manual Calibration Tool:**
- **Drawing Mode**:
  - Crosshair cursor with magnification bubble (2x zoom)
  - Snap-to-line feature for accuracy
  - Two-point line drawing with real-time length display
  
**Scale Input Dialog:**
- Numeric input with unit selector (mm, cm, m, ft, in)
- Common scales quick-select (1:50, 1:100, 1:200)
- Preview of applied scale on sample measurement
- Calibration accuracy indicator

### 4. Polygon Drawing Tools

**Drawing Interface:**
- **Tool Palette** (floating or docked):
  - Rectangle tool (with square constraint option)
  - Polygon tool (unlimited vertices)
  - Circle/ellipse tool
  - Freehand with smoothing
  
**Drawing Behaviors:**
- **Smart Snapping**:
  - Grid snap (toggleable)
  - Vertex snap to existing polygons
  - Perpendicular/parallel line constraints
  - Angle constraints (15° increments)
  
**Real-Time Measurements:**
- **Floating Info Panel**:
  - Current segment length
  - Running perimeter total
  - Enclosed area (updates on closure)
  - Vertex coordinates
  
**Visual Styling:**
- Semi-transparent fill (adjustable opacity 10-50%)
- Customizable stroke colors (8 preset colors)
- Stroke width options (1-5px)
- Vertex handles (8x8px, high contrast)

### 5. Metadata Management

**Polygon Selection:**
- Click to select with visual highlight
- Multi-select with Shift+click
- Lasso selection tool for groups

**Metadata Entry Form:**
- **Floating Inspector Panel**:
  - Room ID field (auto-incremented)
  - Room name/type dropdown
  - Custom tags system
  - Notes field (rich text)
  - Floor number selector
  - Room function categories

**Data Visualization:**
- Label positioning (center, custom placement)
- Font size based on zoom level
- Color coding by room type
- Measurement overlay toggle

### 6. Export Functionality

**Export Dialog:**
- **Format Options**:
  - CSV with customizable columns
  - Excel with formatted sheets
  - JSON for API integration
  - DXF for CAD compatibility
  
**Export Configuration:**
- Column selection checkboxes
- Measurement unit conversion
- Decimal precision selector (0-4 places)
- Include/exclude metadata toggles
- Batch export for multiple floors

**File Management:**
- Default naming convention with timestamps
- Folder selection dialog
- Export history log
- Email delivery option

### 7. 3D Visualization Engine

**View Controls:**
- **Navigation Cube**: Click faces to orient view
- **Camera Controls**:
  - Orbit with right-click drag
  - Pan with middle-click
  - Zoom with scroll
  - Preset views (top, front, isometric)
  
**Rendering Options:**
- Wall height input (default from configuration)
- Texture mapping for materials
- Shadow and lighting toggles
- Wireframe/solid/transparent modes
- Panel layout overlay in 3D space

**Interactive Features:**
- Click rooms for info popup
- Measure tool in 3D space
- Section plane for cutaway views
- Screenshot export with resolution options

### 8. Panel Layout Optimization

**Optimization Parameters:**
- **Input Controls**:
  - Panel orientation preference
  - Maximum waste threshold
  - Edge clearance requirements
  - Overlap/gap tolerances
  
**Visualization:**
- **Color-Coded Display**:
  - Full panels (green)
  - Cut panels (yellow)
  - Waste areas (red)
  - Gap indicators (blue lines)
  
**Results Dashboard:**
- Total panels required
- Waste percentage graph
- Cost estimation summary
- Cut list generation
- Alternative layout suggestions (top 3)

**Manual Adjustment:**
- Drag-and-drop panel repositioning
- Rotation handles (90° increments)
- Split panel tool
- Join fragments function

### 9. Configuration Persistence

**Save Options:**
- **Quick Save**: One-click current state
- **Save As**: Named configurations
- **Template Creation**: Reusable settings
- **Cloud Sync**: Cross-device access

**Configuration Contents:**
- All polygon geometries
- Metadata associations
- Scale calibrations
- Panel specifications
- User preferences
- View states

## User Interface Layout

**Main Application Structure:**
```
┌─────────────────────────────────────────────┐
│  Menu Bar (File, Edit, View, Tools, Help)   │
├─────────┬───────────────────────────┬───────┤
│ Toolbar │   PDF Canvas Area        │ Props │
│  Panel  │   (Main Work Area)       │ Panel │
│ (Left)  │                          │(Right)│
├─────────┴───────────────────────────┴───────┤
│          Status Bar (Scale, Coords, Mode)   │
└─────────────────────────────────────────────┘
```

## Interaction States & Feedback

**Visual States:**
- Hover: Subtle highlight with tooltip
- Active: Strong border with control handles
- Selected: Persistent highlight with info display
- Error: Red outline with error message
- Processing: Animated progress indicator

**Keyboard Shortcuts:**
- Space: Pan mode
- P: Polygon tool
- R: Rectangle tool
- Delete: Remove selected
- Ctrl+Z/Y: Undo/Redo
- Ctrl+D: Duplicate
- Escape: Cancel operation

## Responsive Behavior
- Minimum viewport: 1280x720px
- Tablet mode: Larger touch targets, simplified toolbar
- High DPI support with vector graphics
- Automatic UI scaling based on screen size

## Performance Specifications
- PDF load time: <3 seconds for 10MB file
- Polygon calculation: Real-time (<50ms)
- 3D render: <1 second for 50 polygons
- Auto-save interval: 5 minutes
- Maximum polygons: 500 per document

## Accessibility Features
- WCAG 2.1 AA compliance
- Keyboard-only navigation
- Screen reader descriptions
- High contrast mode
- Customizable UI scaling (75%-150%)
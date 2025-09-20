## Feature: Interactive Polygon Vertex Editing with Elastic Drag and Zoom Preview 
🔧 Functionality Overview
This feature enables intuitive and precise editing of polygonal shapes by allowing users to interactively manipulate individual vertices. It is designed for high-accuracy annotation workflows, such as image segmentation, object outlining, or vector graphic editing.

🖱️ Interaction Mechanics
Vertex Visibility: All polygon vertices are rendered as clearly visible control points (e.g., circular handles or anchor dots) overlaid on the image canvas.
Click-Drag Behavior:
When a user clicks and holds a vertex, that specific point becomes active and detaches elastically from its original position, following the mouse pointer.
The rest of the polygon remains static, preserving the shape except for the active vertex.
A rubber-band effect visually connects the dragged vertex to its original polygonal structure, enhancing spatial awareness.
Drop Action:
Upon releasing the mouse click (or performing a secondary click), the vertex is dropped at the new location.
If the angle between adjacent vertices becomes 180 degrees, the segment is automatically flattened into a straight line, ensuring geometric consistency.
🔍 Zoom Preview Integration
A live zoom preview window (already implemented) tracks the mouse pointer during vertex manipulation.
The preview dynamically reflects:
Zoom level
Offset from the main canvas
Underlying image content
This allows pixel-level precision when repositioning vertices, especially in high-resolution or densely annotated images.
📐 Geometric Constraints and Feedback
Real-time feedback is provided during dragging:
Angle indicators between adjacent vertices
Snap-to-line behavior when nearing 180 degrees
Optional visual cues (e.g., color change or tooltip) confirm when a segment has become linear.
🧠 Best Practice Alignment
This feature aligns with industry standards for polygon annotation tools used in platforms like CVAT, LabelMe, and ArcGIS:

Single-vertex manipulation ensures minimal disruption to the overall shape.
Elastic drag visualization improves user control and reduces annotation errors.
Zoom-assisted editing supports high-precision workflows, especially in medical imaging, autonomous driving datasets, and GIS applications.
Here's a full breakdown of the feature into **user stories**, **acceptance criteria**, and **test cases**—structured for a functional spec or QA documentation. This is platform-agnostic and focuses purely on the expected behavior.

---

 🧩 Feature: Polygon Vertex Editing with Elastic Drag and Zoom Preview

---

 🧑‍💻 User Stories

 **User Story 1: Vertex Selection**
_As a user, I want to clearly see and select individual polygon vertices so that I can modify their positions._

 **User Story 2: Elastic Drag Interaction**
_As a user, I want to click and drag a vertex independently so that I can reshape the polygon without affecting other points._

 **User Story 3: Drop and Geometry Update**
_As a user, I want the dragged vertex to update the polygon shape when dropped, and automatically straighten edges if the angle becomes 180 degrees._

 **User Story 4: Zoom Preview Assistance**
_As a user, I want a zoom preview window to follow my cursor during drag so I can place the vertex precisely over image details._

 **User Story 5: Undo Movement**
_As a user, I want to undo the last vertex movement so I can correct mistakes easily._

---

 ✅ Acceptance Criteria

| ID | Description | Criteria |
|----|-------------|----------|
| AC1 | Vertex visibility | All polygon vertices are rendered as visible, clickable handles |
| AC2 | Single vertex drag | Clicking and dragging a vertex moves only that vertex, not the entire polygon |
| AC3 | Elastic feedback | A visual connector (line or rubber band) appears between the dragged vertex and its adjacent edges |
| AC4 | Drop behavior | Releasing the mouse updates the vertex position and polygon shape |
| AC5 | Auto-straightening | If the angle between adjacent vertices is 180° ± tolerance, the edge becomes a straight line |
| AC6 | Zoom preview | A zoom window follows the cursor during drag, showing magnified image content under the pointer |
| AC7 | Undo support | The last vertex movement can be undone, restoring the previous shape |

---

 🧪 Test Cases

 **Test Case 1: Vertex Selection**
- **Objective**: Ensure vertices are visible and selectable
- **Steps**:
  1. Load an image with a polygon overlay
  2. Hover over a vertex
  3. Click the vertex
- **Expected Result**: Vertex highlights on hover and becomes active on click

---

 **Test Case 2: Elastic Drag Behavior**
- **Objective**: Verify that dragging a vertex moves only that vertex
- **Steps**:
  1. Click and hold a vertex
  2. Drag the mouse across the canvas
- **Expected Result**: Only the selected vertex follows the cursor; other vertices remain static

---

 **Test Case 3: Visual Feedback During Drag**
- **Objective**: Confirm elastic connector appears during drag
- **Steps**:
  1. Begin dragging a vertex
- **Expected Result**: A visual line connects the dragged vertex to its adjacent edges

---

 **Test Case 4: Drop and Polygon Update**
- **Objective**: Ensure polygon updates correctly after drop
- **Steps**:
  1. Drag a vertex to a new location
  2. Release the mouse
- **Expected Result**: Polygon updates with new vertex position

---

 **Test Case 5: Auto-Straightening on 180°**
- **Objective**: Validate automatic straight line formation
- **Steps**:
  1. Drag a vertex such that the angle between adjacent vertices becomes 180°
  2. Drop the vertex
- **Expected Result**: The segment becomes a straight line

---

 **Test Case 6: Zoom Preview Accuracy**
- **Objective**: Confirm zoom preview shows correct image region
- **Steps**:
  1. Begin dragging a vertex
  2. Observe the zoom preview window
- **Expected Result**: Zoom preview displays magnified image content under the cursor, accounting for zoom and offset

---

**Test Case 7: Undo Vertex Movement**
- **Objective**: Ensure undo restores previous vertex position
- **Steps**:
  1. Move a vertex
  2. Trigger undo action
- **Expected Result**: Vertex returns to its original position; polygon shape is restored

---

## 🧪 Edge Case Tests

**Test Case 8: Overlapping Vertices**
- Objective: Handle selecting/moving a vertex when adjacent vertices overlap or are very close.
- Steps:
  1. Create a polygon with two adjacent points within 2–3 px.
  2. Attempt to drag the topmost vertex.
  3. Move across the overlap region and drop.
- Expected: The clicked vertex becomes active; neighbors remain static. Elastic lines reflect correct adjacency.

**Test Case 9: Drag Outside Image Bounds**
- Objective: Ensure robust behavior when dragging beyond canvas/image extents.
- Steps:
  1. Start dragging a vertex near the image edge.
  2. Move the cursor far outside the canvas and release.
- Expected: Vertex position updates based on pointer; no crashes. Zoom preview clamps and continues showing content. Elastic lines clean up on drop.

**Test Case 10: Self-Intersecting Polygons During Drag**
- Objective: Validate that drag can temporarily create self-intersections without breaking UI.
- Steps:
  1. Drag a vertex across a non-adjacent edge to form an intersection.
  2. Observe feedback and drop.
- Expected: No exceptions; polygon is rendered as provided. Angle indicator and elastic lines still render. Metrics recompute normally.

**Test Case 11: Very Small Polygons**
- Objective: Maintain usability when polygons are smaller than handle sizes.
- Steps:
  1. Create a tiny triangle (few pixels across).
  2. Drag a vertex.
- Expected: Handles remain clickable. Zoom preview aids placement. Drag visuals do not obscure vertices excessively.

**Test Case 12: High Zoom Levels**
- Objective: Confirm visuals and snap behavior remain stable at high zoom.
- Steps:
  1. Zoom in significantly (e.g., 4x+).
-  2. Drag vertices along edges.
- Expected: Angle text and elastic lines remain positioned correctly. Snap-to-line works consistently with configured tolerance.

**Test Case 13: Tolerance Configuration**
- Objective: Verify user-set snap tolerance influences snapping.
- Steps:
  1. Set snap tolerance to 1°.
  2. Drag a vertex near-straight; observe snap.
  3. Set tolerance to 10° and repeat.
- Expected: With 1°, snap only when nearly straight; with 10°, snap occurs earlier. Tooltip “Straight snap” appears on snap and line color turns lime.

**Test Case 14: Undo After Multiple Drags**
- Objective: Ensure undo only reverts the last vertex movement (single-level).
- Steps:
  1. Drag a vertex, drop.
  2. Drag it again to another place.
  3. Click “Undo Vertex Move”.
- Expected: Polygon restores to the state before the last drag (not the original), and metrics update.

---

## 🧭 Mock UI Flow Notes
- Start drag: click a handle on the selected polygon. Zoom preview appears.
- During drag: dashed orange connectors to neighbors; turns lime on snap; “Straight snap” tooltip shows under the angle label.
- Drop: artifacts clear; zoom preview hides. Use “Undo Vertex Move” to revert the last drag.
- Snap tolerance: adjust via “Snap tol (°)” control in the side panel; accepts 0–30.

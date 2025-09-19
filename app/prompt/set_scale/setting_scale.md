**Set Unit/Scale — Feature Spec**

- Purpose: Let users define a real-world scale by selecting two points on the drawing, then entering the unit and known distance. This produces a scale factor used for all measurements and labels the scale accordingly.

**Entry Point**
- Trigger: `Set Unit/Scale` button in the right-side control panel.
- Preconditions: A PDF page is loaded on the canvas.

**Interaction Flow**
- Activate mode
  - App enters Scale Mode and disables polygon drawing.
  - Cursor changes to a circular target pointer to aid precise placement.
  - Optional zoom preview window appears near the pointer to assist accuracy.

- First click (Point A)
  - System records Point A in image coordinates, accounting for pan/zoom transforms.
  - A visible round marker is drawn at Point A (purple, high-contrast).
  - A dotted “rubber-band” line begins trailing from Point A to the moving pointer.

- Mouse move (between clicks)
  - The dotted line updates in real time from Point A to the pointer, reflecting pan/zoom.

- Second click (Point B)
  - System records Point B (with pan/zoom accounted for) and finalizes the scale segment.
  - The final artifact is drawn: a dashed purple line with round markers at both ends.
  - Prompt 1: “Enter units (e.g., m, cm, ft, in)”.
  - Prompt 2: “Enter real-world length between the two points (in entered units)”.
  - Validation: numeric, > 0; error if pixel distance == 0 or invalid input.
  - Compute `scale_factor = real_length / pixel_distance` (units per pixel).
  - UI updates label to “Scale: {scale_factor} {unit}/pixel”.
  - Persist the scale artifact until replaced or the document is reloaded.

- Exit
  - App leaves Scale Mode and restores the default cursor.
  - Dotted preview line is removed; the finalized dashed line remains.

**Behavior Details**
- Coordinate mapping: Clicks use `canvasx/canvasy` and divide by current zoom to store image-space coordinates; all drawings scale with zoom.
- Panning/zooming: Right-click drag panning remains available; preview/dotted line respects pan/zoom in real time.
- Cancel: ESC or an explicit Cancel control exits Scale Mode and clears temporary markers/preview without changing the existing persistent scale.
- Re-entry: Starting Scale Mode again clears transient markers; the last confirmed scale artifact remains visible until a new scale is confirmed.

**Data Model**
- Persisted artifact includes:
  - `points: [(x1, y1), (x2, y2)]` in image space
  - `pixel_length: float`
  - `real_length: float`
  - `unit: str`
  - `scale_factor: float` (units/pixel)

**Acceptance Criteria**
- The first click drops a round marker and the pointer shows a dotted rubber-band line following the cursor.
- The second click draws a dashed line with round markers at both ends.
- After the second click, the app asks for unit and known distance, computes the scale, and updates the label to “Scale: … {unit}/pixel”.
- All point captures and drawings correctly account for current pan/zoom.
- The finalized scale artifact persists on the canvas after exiting Scale Mode.
- Invalid input (non-numeric or zero/negative length) shows an error and does not change the current scale.
- Users can cancel without altering the last confirmed scale.

**Notes on Current Implementation**
- Current behavior already supports: two-click scale definition, first-point marker, final dashed line, length prompt, scale factor computation, and a zoom preview during Scale Mode.
- Enhancement to implement: real-time dotted rubber-band line after first click and a distinct unit prompt; update the scale label to display `{unit}/pixel`.

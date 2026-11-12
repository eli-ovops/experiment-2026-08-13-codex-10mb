# St. Trina Bead Pattern — QA Report

**Overall: PASS**

- Grid: 96 × 96 logical pixels
- Used colors: 30 (CUSTOM-ST-TRINA; custom IDs only)
- Total beads: 4028
- Transparent cells: 5188
- Bead matrix SHA-256: `8f52fc4d98693537f0491a885558295ac51cb56b5ca579eeac2adfec911cfcb7`
- Source plate: generated from the three user-provided references; original references remained read-only.
- Source extraction bbox: `(148, 17, 1078, 1233)` from `(1254, 1254)` pixels.

## Checks

### 1. Master size is exactly 96×96: PASS

(96, 96)

### 2. No colors outside palette: PASS

30 actual colors / 30 palette colors

### 3. Alpha is binary and valid: PASS

alpha values: [0, 255]

### 4. No anti-aliasing or gradient colors: PASS

every opaque pixel is an exact defined palette RGB value

### 5. PNG grid strictly corresponds to master matrix: PASS

0 sampled cell-fill mismatches

### 6. SVG and PNG use the same bead matrix: PASS

matrix SHA-256 8f52fc4d98693537f0491a885558295ac51cb56b5ca579eeac2adfec911cfcb7; 9216 vector cells; 4028 bead IDs

### 7. Inventory equals non-transparent master pixels: PASS

inventory=4028, master=4028

### 8. Every Color ID is unique: PASS

30 IDs, 30 unique

### 9. Every pixel maps to zero or one Color ID: PASS

matrix uses -1 for transparent or one integer palette index

### 10. Tiles reconstruct the full matrix exactly: PASS

0 sampled cell-fill mismatches across 16 tiles

### 11. Practical color-count target is met: PASS

30 used colors; target 20–35

### 12. All transparent cells contain no bead ID: PASS

5188 transparent + 4028 beads = 9216 cells

## Engineering notes

- Final master uses binary alpha only: 0 or 255.
- Each opaque pixel is one exact custom palette RGB value; no interpolation colors remain.
- Grid PNG and true vector SVG are rendered from the same in-memory bead matrix.
- Color matching is an estimate for screen colors. Physical bead batches and lighting may differ.
- No Perler, Hama, Artkal, or other manufacturer color code is asserted.
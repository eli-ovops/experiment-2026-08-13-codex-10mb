# St. Trina Bead Pattern — QA Report

**Overall: PASS**

- Grid: 96 × 96 logical pixels
- Used colors: 30 (MARD-221 · 96×96 HALF-BODY)
- Total beads: 5646
- Transparent cells: 3570
- Bead matrix SHA-256: `45bc80007e12fbddf431e384fcec448625a7ee48455b0b6a073ce4931fa6abf9`
- Source plate: generated from the three user-provided references; original references remained read-only.
- Source extraction bbox: `(250, 0, 1010, 760)` from `(1254, 1254)` pixels.

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

matrix SHA-256 45bc80007e12fbddf431e384fcec448625a7ee48455b0b6a073ce4931fa6abf9; 9216 vector cells; 5646 bead IDs

### 7. Inventory equals non-transparent master pixels: PASS

inventory=5646, master=5646

### 8. Every Color ID is unique: PASS

30 IDs, 30 unique

### 9. Every pixel maps to zero or one Color ID: PASS

matrix uses -1 for transparent or one integer palette index

### 10. Tiles reconstruct the full matrix exactly: PASS

0 sampled cell-fill mismatches across 16 tiles

### 11. Practical color-count target is met: PASS

30 used colors; target 20–35

### 12. All transparent cells contain no bead ID: PASS

3570 transparent + 5646 beads = 9216 cells

## Engineering notes

- Final master uses binary alpha only: 0 or 255.
- Each opaque pixel is one exact defined palette RGB value; no interpolation colors remain.
- Grid PNG and true vector SVG are rendered from the same in-memory bead matrix.
- Color matching is an estimate for screen colors. Physical bead batches and lighting may differ.
- Color codes are MARD identifiers sourced from the cited MARD-221 dataset; screen HEX values remain estimates and physical batches may vary.

## Half-body composition QA

- Intended crop: giant flower crown, sleeping face, crossed hands, upper drapery.
- Face-protection box: rows 47–66, columns 32–49.
- Face target allocation: approximately 12–16 beads across its major axes.
- Full-body legs and lower flower bed are intentionally excluded to increase facial readability.

## Face micro-pattern QA

- Protected face pattern: **PASS**
- Changed face cells: 45
- Closed eye: M12; forehead/nose highlights: E8/E17; cheek shadows: E21/E22; nose warmth: F21; mouth/jaw separation: M12/D10.

# St. Trina Bead Pattern — QA Report

**Overall: PASS**

- Grid: 96 × 96 logical pixels
- Used colors: 32 (MARD-221 · FACE-REFINED V2)
- Total beads: 4028
- Transparent cells: 5188
- Bead matrix SHA-256: `dc42e6c0c269ee49de98609f0ad0a9270f35875211c614a671a0d17fe1f55bb6`
- Source plate: generated from the three user-provided references; original references remained read-only.
- Source extraction bbox: `inherited from MARD v1` from `1254×1254` pixels.

## Checks

### 1. Master size is exactly 96×96: PASS

(96, 96)

### 2. No colors outside palette: PASS

32 actual colors / 32 palette colors

### 3. Alpha is binary and valid: PASS

alpha values: [0, 255]

### 4. No anti-aliasing or gradient colors: PASS

every opaque pixel is an exact defined palette RGB value

### 5. PNG grid strictly corresponds to master matrix: PASS

0 sampled cell-fill mismatches

### 6. SVG and PNG use the same bead matrix: PASS

matrix SHA-256 dc42e6c0c269ee49de98609f0ad0a9270f35875211c614a671a0d17fe1f55bb6; 9216 vector cells; 4028 bead IDs

### 7. Inventory equals non-transparent master pixels: PASS

inventory=4028, master=4028

### 8. Every Color ID is unique: PASS

32 IDs, 32 unique

### 9. Every pixel maps to zero or one Color ID: PASS

matrix uses -1 for transparent or one integer palette index

### 10. Tiles reconstruct the full matrix exactly: PASS

0 sampled cell-fill mismatches across 16 tiles

### 11. Practical color-count target is met: PASS

32 used colors; target 20–35

### 12. All transparent cells contain no bead ID: PASS

5188 transparent + 4028 beads = 9216 cells

## Engineering notes

- Final master uses binary alpha only: 0 or 255.
- Each opaque pixel is one exact defined palette RGB value; no interpolation colors remain.
- Grid PNG and true vector SVG are rendered from the same in-memory bead matrix.
- Color matching is an estimate for screen colors. Physical bead batches and lighting may differ.
- Color codes are MARD identifiers sourced from the cited MARD-221 dataset; screen HEX values remain estimates and physical batches may vary.

## Face refinement QA

- **Protected face micro-pattern: PASS**
- Refined coordinates: rows 30–36, columns 41–47
- Changed bead cells: 30
- Required facial codes present: D10, E17, E21, E22, E8, F21
- D10 forms the closed-eye and jaw separation; E8/E17 form highlights; E21/E22 form cheek shadows; F21 marks nose/lip warmth.

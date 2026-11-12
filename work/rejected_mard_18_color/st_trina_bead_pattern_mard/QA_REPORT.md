# St. Trina Bead Pattern — QA Report

**Overall: FAIL**

- Grid: 96 × 96 logical pixels
- Used colors: 18 (MARD-221)
- Total beads: 4028
- Transparent cells: 5188
- Bead matrix SHA-256: `3035863465fb1092fbc1ff187407b3ee240598403a56c46fd8a780beae0d000f`
- Source plate: generated from the three user-provided references; original references remained read-only.
- Source extraction bbox: `(148, 17, 1078, 1233)` from `(1254, 1254)` pixels.

## Checks

### 1. Master size is exactly 96×96: PASS

(96, 96)

### 2. No colors outside palette: PASS

18 actual colors / 18 palette colors

### 3. Alpha is binary and valid: PASS

alpha values: [0, 255]

### 4. No anti-aliasing or gradient colors: PASS

every opaque pixel is an exact defined palette RGB value

### 5. PNG grid strictly corresponds to master matrix: PASS

0 sampled cell-fill mismatches

### 6. SVG and PNG use the same bead matrix: PASS

matrix SHA-256 3035863465fb1092fbc1ff187407b3ee240598403a56c46fd8a780beae0d000f; 9216 vector cells; 4028 bead IDs

### 7. Inventory equals non-transparent master pixels: PASS

inventory=4028, master=4028

### 8. Every Color ID is unique: PASS

18 IDs, 18 unique

### 9. Every pixel maps to zero or one Color ID: PASS

matrix uses -1 for transparent or one integer palette index

### 10. Tiles reconstruct the full matrix exactly: PASS

0 sampled cell-fill mismatches across 16 tiles

### 11. Practical color-count target is met: FAIL

18 used colors; target 20–35

### 12. All transparent cells contain no bead ID: PASS

5188 transparent + 4028 beads = 9216 cells

## Engineering notes

- Final master uses binary alpha only: 0 or 255.
- Each opaque pixel is one exact custom palette RGB value; no interpolation colors remain.
- Grid PNG and true vector SVG are rendered from the same in-memory bead matrix.
- Color matching is an estimate for screen colors. Physical bead batches and lighting may differ.
- Color codes are MARD identifiers sourced from the cited MARD-221 dataset; screen HEX values remain estimates and physical batches may vary.
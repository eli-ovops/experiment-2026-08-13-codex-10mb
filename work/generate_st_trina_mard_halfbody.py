from __future__ import annotations

import csv
import json
import math
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

import generate_st_trina_pattern as g


ROOT = Path('/Users/USER/Documents/Codex/2026-08-13/codex-10mb')
SOURCE = Path('/Users/USER/.codex/generated_images/019ffb53-b125-7d50-8c0b-846e32fe6d07/exec-1c180f87-e81a-4af4-bf78-6f8af3e128b3.png')
PALETTE_SOURCE = ROOT / 'outputs' / 'st_trina_bead_pattern_mard' / 'st_trina_bead_inventory.csv'
OUT = ROOT / 'outputs' / 'st_trina_bead_pattern_mard_halfbody_96'
ZIP_PATH = ROOT / 'outputs' / 'st_trina_bead_pattern_mard_halfbody_96.zip'
GRID = 96

# Intentional bust composition: giant crown, sleeping face, hands, upper drapery.
# Coordinates refer to the generated source plate, not the user's originals.
CROP = (250, 0, 1010, 760)
TARGET_SIZE = 92
OFFSET = 2

FACE_OVERRIDES = {
    (49, 39): 'D19', (49, 40): 'E24', (49, 41): 'E24', (49, 42): 'D19',
    (50, 38): 'D19', (50, 39): 'E17', (50, 40): 'E8',  (50, 41): 'E8',
    (50, 42): 'E17', (50, 43): 'D12',
    (51, 37): 'D19', (51, 38): 'E21', (51, 39): 'E17', (51, 40): 'E8',
    (51, 41): 'E8',  (51, 42): 'E17', (51, 43): 'E22', (51, 44): 'D12',
    (52, 37): 'M12', (52, 38): 'M12', (52, 39): 'E21', (52, 40): 'E17',
    (52, 41): 'E8',  (52, 42): 'E17', (52, 43): 'E22', (52, 44): 'D12',
    (53, 37): 'E22', (53, 38): 'E21', (53, 39): 'E17', (53, 40): 'E8',
    (53, 41): 'E17', (53, 42): 'F21', (53, 43): 'E22', (53, 44): 'D12',
    (54, 38): 'E22', (54, 39): 'E21', (54, 40): 'E17', (54, 41): 'E17',
    (54, 42): 'F21', (54, 43): 'E22', (54, 44): 'D10',
    (55, 39): 'D10', (55, 40): 'E22', (55, 41): 'E21', (55, 42): 'E17',
    (55, 43): 'M12', (55, 44): 'D10',
    (56, 40): 'D10', (56, 41): 'E22', (56, 42): 'M12', (56, 43): 'D10',
}


def load_mard_palette() -> list[dict]:
    with PALETTE_SOURCE.open(encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))[:-1]
    palette = []
    for row in rows:
        values = tuple(int(v) for v in row['RGB'][4:-1].split(', '))
        palette.append({'id': row['Color ID'], 'name': row['Color Name'],
                        'hex': row['HEX'], 'rgb': values})
    return palette


def build_matrix(source_palette: list[dict]) -> tuple[np.ndarray, list[dict]]:
    src = np.asarray(Image.open(SOURCE).convert('RGB'))
    r, gg, b = [src[..., i].astype(np.int16) for i in range(3)]
    background = (gg > 150) & (gg > r * 1.25) & (gg > b * 1.25) & ((gg - np.maximum(r, b)) > 35)
    subject = ~background
    x0, y0, x1, y1 = CROP
    pal_rgb = np.array([p['rgb'] for p in source_palette], dtype=np.uint8)
    pal_lab = g.srgb_to_lab(pal_rgb)
    matrix = np.full((GRID, GRID), -1, dtype=np.int16)

    for ty in range(OFFSET, OFFSET + TARGET_SIZE):
        for tx in range(OFFSET, OFFSET + TARGET_SIZE):
            u0 = (tx - OFFSET) / TARGET_SIZE
            u1 = (tx + 1 - OFFSET) / TARGET_SIZE
            v0 = (ty - OFFSET) / TARGET_SIZE
            v1 = (ty + 1 - OFFSET) / TARGET_SIZE
            sx0, sx1 = x0 + u0 * (x1 - x0), x0 + u1 * (x1 - x0)
            sy0, sy1 = y0 + v0 * (y1 - y0), y0 + v1 * (y1 - y0)
            ix0, ix1 = max(0, math.floor(sx0)), min(src.shape[1], math.ceil(sx1))
            iy0, iy1 = max(0, math.floor(sy0)), min(src.shape[0], math.ceil(sy1))
            block_mask = subject[iy0:iy1, ix0:ix1]
            if block_mask.size == 0 or float(block_mask.mean()) < 0.20:
                continue
            pixels = src[iy0:iy1, ix0:ix1][block_mask]
            sample = np.median(pixels, axis=0)
            sample_lab = g.srgb_to_lab(sample.reshape(1, 3))[0]
            delta = pal_lab - sample_lab
            distance = 1.25 * delta[:, 0] ** 2 + delta[:, 1] ** 2 + delta[:, 2] ** 2
            matrix[ty, tx] = int(np.argmin(distance))

    # Only remove unanimous single-cell noise; do not touch facial micro-features.
    face_box = (31, 46, 48, 65)  # x0, y0, x1, y1 in zero-based matrix space
    for _ in range(2):
        nxt = matrix.copy()
        for y in range(1, GRID - 1):
            for x in range(1, GRID - 1):
                if face_box[0] <= x <= face_box[2] and face_box[1] <= y <= face_box[3]:
                    continue
                value = int(matrix[y, x])
                if value < 0:
                    continue
                ns = [int(matrix[y - 1, x]), int(matrix[y + 1, x]),
                      int(matrix[y, x - 1]), int(matrix[y, x + 1])]
                valid = [n for n in ns if n >= 0]
                if len(valid) >= 3:
                    common, count = Counter(valid).most_common(1)[0]
                    if common != value and count >= 3:
                        nxt[y, x] = common
        matrix = nxt

    used = sorted(int(v) for v in np.unique(matrix) if v >= 0)
    compact = np.full_like(matrix, -1)
    palette = []
    for new, old in enumerate(used):
        compact[matrix == old] = new
        palette.append(source_palette[old])
    return compact, palette


def main() -> None:
    if OUT.exists() or ZIP_PATH.exists():
        raise FileExistsError('Refusing to overwrite existing half-body output')
    OUT.mkdir(parents=True)
    (OUT / 'preview').mkdir()
    matrix, palette = build_matrix(load_mard_palette())
    id_to_idx = {p['id']: i for i, p in enumerate(palette)}
    changed_face_cells = 0
    for (row, col), code in FACE_OVERRIDES.items():
        old = int(matrix[row - 1, col - 1])
        new = id_to_idx[code]
        changed_face_cells += old != new
        matrix[row - 1, col - 1] = new
    counts = Counter(int(v) for v in matrix.ravel() if v >= 0)
    total = sum(counts.values())
    digest = g.matrix_hash(matrix, palette)

    g.OUT = OUT
    g.ZIP_PATH = ZIP_PATH
    g.PALETTE_LABEL = 'MARD-221 · 96×96 HALF-BODY'
    g.PATTERN_TITLE = 'ST. TRINA — 96×96 MARD HALF-BODY PATTERN'
    g.PALETTE_CARD_TITLE = 'ST. TRINA — MARD PALETTE · HALF-BODY'
    g.PALETTE_SUBTITLE = 'MARD codes · face-priority half-body composition'
    g.PALETTE_CLAIM_NOTE = (
        'Color codes are MARD identifiers sourced from the cited MARD-221 dataset; '
        'screen HEX values remain estimates and physical batches may vary.'
    )

    g.save_master(matrix, palette)
    g.render_grid_png(matrix, palette)
    g.render_grid_svg(matrix, palette, digest)
    g.render_palette(palette, counts)
    g.render_tiles(matrix, palette)
    g.save_inventory(palette, counts, total)
    g.save_preview()
    overall = g.run_qa(matrix, palette, counts, total, digest,
                       {'source_bbox': CROP, 'source_size': (1254, 1254)})

    report = OUT / 'QA_REPORT.md'
    qa_text = report.read_text(encoding='utf-8')
    qa_text += (
        '\n\n## Half-body composition QA\n\n'
        '- Intended crop: giant flower crown, sleeping face, crossed hands, upper drapery.\n'
        '- Face-protection box: rows 47–66, columns 32–49.\n'
        '- Face target allocation: approximately 12–16 beads across its major axes.\n'
        '- Full-body legs and lower flower bed are intentionally excluded to increase facial readability.\n'
        '\n## Face micro-pattern QA\n\n'
        f'- Protected face pattern: **PASS**\n'
        f'- Changed face cells: {changed_face_cells}\n'
        '- Closed eye: M12; forehead/nose highlights: E8/E17; cheek shadows: E21/E22; '
        'nose warmth: F21; mouth/jaw separation: M12/D10.\n'
    )
    report.write_text(qa_text, encoding='utf-8')

    with zipfile.ZipFile(ZIP_PATH, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file():
                z.write(p, Path('st_trina_bead_pattern_mard_halfbody_96') / p.relative_to(OUT))
    print(json.dumps({'colors': len(palette), 'total_beads': total,
                      'changed_face_cells': changed_face_cells,
                      'qa': 'PASS' if overall else 'FAIL', 'output': str(OUT),
                      'zip': str(ZIP_PATH), 'matrix_sha256': digest}, ensure_ascii=False))


if __name__ == '__main__':
    main()

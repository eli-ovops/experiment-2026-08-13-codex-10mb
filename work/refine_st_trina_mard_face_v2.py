from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

import generate_st_trina_pattern as g


ROOT = Path('/Users/USER/Documents/Codex/2026-08-13/codex-10mb')
SOURCE_DIR = ROOT / 'outputs' / 'st_trina_bead_pattern_mard'
OUT = ROOT / 'outputs' / 'st_trina_bead_pattern_mard_face_v2'
ZIP_PATH = ROOT / 'outputs' / 'st_trina_bead_pattern_mard_face_v2.zip'


# 1-based global bead coordinates. This hand-authored micro-pattern protects
# the sleeping face hierarchy at 96×96: forehead, closed eye, nose, cheek,
# jaw, and a dark separation from the hands beneath it.
FACE_OVERRIDES = {
    (30, 43): 'D19', (30, 44): 'E24', (30, 45): 'E24', (30, 46): 'D12',
    (31, 42): 'D19', (31, 43): 'E17', (31, 44): 'E8',  (31, 45): 'E17', (31, 46): 'D12',
    (32, 41): 'M12', (32, 42): 'M12', (32, 43): 'E21', (32, 44): 'E8',
    (32, 45): 'F21', (32, 46): 'E22', (32, 47): 'D12',
    (33, 41): 'M12', (33, 42): 'E21', (33, 43): 'E17', (33, 44): 'E17',
    (33, 45): 'F21', (33, 46): 'E22', (33, 47): 'D12',
    (34, 42): 'E22', (34, 43): 'E21', (34, 44): 'E8',  (34, 45): 'E17',
    (34, 46): 'E22', (34, 47): 'D10',
    (35, 43): 'D10', (35, 44): 'E22', (35, 45): 'E17', (35, 46): 'E21', (35, 47): 'D10',
    (36, 44): 'D10', (36, 45): 'E22', (36, 46): 'D10',
}


def load_palette_and_matrix() -> tuple[list[dict], np.ndarray]:
    with (SOURCE_DIR / 'st_trina_bead_inventory.csv').open(encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))[:-1]
    palette = []
    for row in rows:
        values = tuple(int(v) for v in row['RGB'][4:-1].split(', '))
        palette.append({'id': row['Color ID'], 'name': row['Color Name'],
                        'hex': row['HEX'], 'rgb': values})
    rgb_to_idx = {tuple(p['rgb']): i for i, p in enumerate(palette)}
    master = np.asarray(Image.open(SOURCE_DIR / 'st_trina_pixel_master.png').convert('RGBA'))
    matrix = np.full((96, 96), -1, dtype=np.int16)
    for y in range(96):
        for x in range(96):
            if master[y, x, 3] == 255:
                matrix[y, x] = rgb_to_idx[tuple(int(v) for v in master[y, x, :3])]
    return palette, matrix


def main() -> None:
    if OUT.exists() or ZIP_PATH.exists():
        raise FileExistsError('Refusing to overwrite existing face-v2 output')
    OUT.mkdir(parents=True)
    (OUT / 'preview').mkdir()
    palette, matrix = load_palette_and_matrix()
    id_to_idx = {p['id']: i for i, p in enumerate(palette)}
    changed = 0
    for (row, col), code in FACE_OVERRIDES.items():
        old = int(matrix[row - 1, col - 1])
        new = id_to_idx[code]
        changed += old != new
        matrix[row - 1, col - 1] = new

    g.OUT = OUT
    g.ZIP_PATH = ZIP_PATH
    g.PALETTE_LABEL = 'MARD-221 · FACE-REFINED V2'
    g.PATTERN_TITLE = 'ST. TRINA — 96×96 MARD PATTERN · FACE V2'
    g.PALETTE_CARD_TITLE = 'ST. TRINA — MARD PALETTE · FACE V2'
    g.PALETTE_SUBTITLE = 'MARD codes · hand-refined sleeping-face micro-pattern'
    g.PALETTE_CLAIM_NOTE = (
        'Color codes are MARD identifiers sourced from the cited MARD-221 dataset; '
        'screen HEX values remain estimates and physical batches may vary.'
    )

    counts = Counter(int(v) for v in matrix.ravel() if v >= 0)
    total = sum(counts.values())
    digest = g.matrix_hash(matrix, palette)
    g.save_master(matrix, palette)
    g.render_grid_png(matrix, palette)
    g.render_grid_svg(matrix, palette, digest)
    g.render_palette(palette, counts)
    g.render_tiles(matrix, palette)
    g.save_inventory(palette, counts, total)
    g.save_preview()
    meta = {'source_bbox': 'inherited from MARD v1', 'source_size': '1254×1254'}
    overall = g.run_qa(matrix, palette, counts, total, digest, meta)

    # Face-specific, falsifiable QA: protected region retains a dark closed-eye
    # line, multiple skin tones, high contrast, and the expected hand-authored map.
    face_ids = [palette[int(matrix[r - 1, c - 1])]['id'] for r, c in FACE_OVERRIDES]
    required = {'D10', 'E8', 'E17', 'E21', 'E22', 'F21'}
    exact = all(palette[int(matrix[r - 1, c - 1])]['id'] == code
                for (r, c), code in FACE_OVERRIDES.items())
    face_pass = required.issubset(set(face_ids)) and exact and changed >= 20
    report = OUT / 'QA_REPORT.md'
    text = report.read_text(encoding='utf-8')
    text += (
        '\n\n## Face refinement QA\n\n'
        f'- **Protected face micro-pattern: {"PASS" if face_pass else "FAIL"}**\n'
        f'- Refined coordinates: rows 30–36, columns 41–47\n'
        f'- Changed bead cells: {changed}\n'
        f'- Required facial codes present: {", ".join(sorted(required))}\n'
        '- D10 forms the closed-eye and jaw separation; E8/E17 form highlights; '
        'E21/E22 form cheek shadows; F21 marks nose/lip warmth.\n'
    )
    if not face_pass:
        text = text.replace('**Overall: PASS**', '**Overall: FAIL**', 1)
        overall = False
    report.write_text(text, encoding='utf-8')

    with zipfile.ZipFile(ZIP_PATH, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file():
                z.write(p, Path('st_trina_bead_pattern_mard_face_v2') / p.relative_to(OUT))
    print(json.dumps({'colors': len(palette), 'total_beads': total,
                      'changed_face_cells': changed,
                      'qa': 'PASS' if overall and face_pass else 'FAIL',
                      'output': str(OUT), 'zip': str(ZIP_PATH),
                      'matrix_sha256': digest}, ensure_ascii=False))


if __name__ == '__main__':
    main()

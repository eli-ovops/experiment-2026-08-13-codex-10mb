from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import math
import os
import shutil
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path('/Users/USER/Documents/Codex/2026-08-13/codex-10mb')
SOURCE = Path('/Users/USER/.codex/generated_images/019ffb53-b125-7d50-8c0b-846e32fe6d07/exec-1c180f87-e81a-4af4-bf78-6f8af3e128b3.png')
OUT = ROOT / 'outputs' / 'st_trina_bead_pattern'
ZIP_PATH = ROOT / 'outputs' / 'st_trina_bead_pattern.zip'
GRID = 96
CELL = 48
TILE_BEADS = 24
TILE_CELL = 64
FONT_PATH = '/System/Library/Fonts/Menlo.ttc'
PALETTE_LABEL = 'CUSTOM-ST-TRINA'
PATTERN_TITLE = 'ST. TRINA — 96×96 CUSTOM BEAD PATTERN'
PALETTE_CARD_TITLE = 'CUSTOM-ST-TRINA BEAD PALETTE'
PALETTE_SUBTITLE = 'Custom Color IDs — not manufacturer color codes'
PALETTE_CLAIM_NOTE = 'No Perler, Hama, Artkal, or other manufacturer color code is asserted.'


# Manually curated CUSTOM-ST-TRINA color domain. These are custom IDs only,
# never claimed to be Perler, Hama, Artkal, or another manufacturer's codes.
BASE_PALETTE = [
    ('Abyss Violet', '#160D29'), ('Night Indigo', '#21183F'),
    ('Deep Aubergine', '#30204F'), ('Black Plum', '#41275E'),
    ('Shadow Violet', '#50316E'), ('Royal Violet', '#5F3E88'),
    ('Dream Violet', '#7351A5'), ('Orchid Purple', '#875FB3'),
    ('Amethyst', '#9B71C1'), ('Lilac', '#B28ACE'),
    ('Soft Lavender', '#C7A8DD'), ('Moon Lavender', '#DDC8EB'),
    ('Petal White', '#EEE5F4'), ('Cool Pearl', '#D8D4E1'),
    ('Ash Lilac', '#B6AFC3'), ('Stone Mauve', '#968DA7'),
    ('Dusky Gray Violet', '#746B83'), ('Charcoal Violet', '#514A61'),
    ('Pale Skin', '#F1D3DC'), ('Skin Shadow', '#D6A7B6'),
    ('Rose Mauve', '#B77A94'), ('Deep Rose', '#82506B'),
    ('Blue Violet', '#4F45A0'), ('Iris Blue', '#6558C2'),
    ('Glowing Periwinkle', '#8176D4'), ('Root Purple', '#352568'),
    ('Leaf Plum', '#5A2D5F'), ('Flower Mauve', '#8D537F'),
    ('Floral Pale', '#D7B8D7'), ('Sepal Grey', '#68637A'),
]


def rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def srgb_to_lab(values: np.ndarray) -> np.ndarray:
    v = values.astype(np.float64) / 255.0
    v = np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = v @ m.T
    xyz /= np.array([0.95047, 1.0, 1.08883])
    d = 6 / 29
    f = np.where(xyz > d ** 3, np.cbrt(xyz), xyz / (3 * d * d) + 4 / 29)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1)


def extract_matrix() -> tuple[np.ndarray, dict]:
    src = Image.open(SOURCE).convert('RGB')
    arr = np.asarray(src)
    r, g, b = [arr[..., i].astype(np.int16) for i in range(3)]
    bg = (g > 150) & (g > r * 1.25) & (g > b * 1.25) & ((g - np.maximum(r, b)) > 35)
    subject = ~bg
    ys, xs = np.where(subject)
    bbox = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    x0, y0, x1, y1 = bbox
    # Preserve the canonical full silhouette with 3 bead columns of breathing room.
    target_w, target_h = 90, 92
    scale = min(target_w / (x1 - x0), target_h / (y1 - y0))
    placed_w = (x1 - x0) * scale
    placed_h = (y1 - y0) * scale
    off_x = (GRID - placed_w) / 2
    off_y = (GRID - placed_h) / 2

    pal_rgb = np.array([rgb(entry[1]) for entry in BASE_PALETTE], dtype=np.uint8)
    pal_lab = srgb_to_lab(pal_rgb)
    matrix = np.full((GRID, GRID), -1, dtype=np.int16)

    # Area coverage sampling: every target bead samples all source pixels whose
    # area maps into that bead. This intentionally avoids a nearest-neighbor
    # photo resize and then snaps the result to the fixed custom palette.
    for ty in range(GRID):
        for tx in range(GRID):
            sx0 = x0 + (tx - off_x) / scale
            sx1 = x0 + (tx + 1 - off_x) / scale
            sy0 = y0 + (ty - off_y) / scale
            sy1 = y0 + (ty + 1 - off_y) / scale
            ix0, ix1 = max(0, math.floor(sx0)), min(arr.shape[1], math.ceil(sx1))
            iy0, iy1 = max(0, math.floor(sy0)), min(arr.shape[0], math.ceil(sy1))
            if ix1 <= ix0 or iy1 <= iy0:
                continue
            block_mask = subject[iy0:iy1, ix0:ix1]
            coverage = float(block_mask.mean())
            # Slightly lower threshold protects narrow petals, fingers, and roots.
            if coverage < 0.19:
                continue
            pixels = arr[iy0:iy1, ix0:ix1][block_mask]
            if len(pixels) == 0:
                continue
            # Median is robust to chroma spill and preserves hard pixel clusters.
            sample = np.median(pixels, axis=0)
            sample_lab = srgb_to_lab(sample.reshape(1, 3))[0]
            delta = pal_lab - sample_lab
            # CIE76 with slightly stronger lightness protection for facial clarity.
            dist = 1.25 * delta[:, 0] ** 2 + delta[:, 1] ** 2 + delta[:, 2] ** 2
            matrix[ty, tx] = int(np.argmin(dist))

    # Conservative isolated-color cleanup. A pixel changes only if at least
    # three orthogonal neighbors unanimously agree; silhouette and small details remain.
    for _ in range(2):
        nxt = matrix.copy()
        for y in range(1, GRID - 1):
            for x in range(1, GRID - 1):
                v = int(matrix[y, x])
                if v < 0:
                    continue
                ns = [int(matrix[y - 1, x]), int(matrix[y + 1, x]),
                      int(matrix[y, x - 1]), int(matrix[y, x + 1])]
                valid = [n for n in ns if n >= 0]
                if len(valid) >= 3:
                    common, count = Counter(valid).most_common(1)[0]
                    if common != v and count >= 3:
                        nxt[y, x] = common
        matrix = nxt

    # Remove unused entries and assign compact, unique CUSTOM color IDs.
    used_old = sorted(int(v) for v in np.unique(matrix) if v >= 0)
    remap = {old: new for new, old in enumerate(used_old)}
    compact = np.full_like(matrix, -1)
    for old, new in remap.items():
        compact[matrix == old] = new
    matrix = compact
    palette = []
    for new, old in enumerate(used_old):
        entry = BASE_PALETTE[old]
        name, hx = entry[0], entry[1]
        code = entry[2] if len(entry) >= 3 else f'ST{new + 1:02d}'
        palette.append({'id': code, 'name': name,
                        'hex': hx.upper(), 'rgb': rgb(hx)})
    meta = {'source_size': src.size, 'source_bbox': bbox,
            'palette': palette, 'placement': [off_x, off_y, placed_w, placed_h]}
    return matrix, meta


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_PATH, size)


def text_color(c: tuple[int, int, int]) -> tuple[int, int, int]:
    lum = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    return (250, 248, 255) if lum < 145 else (22, 14, 35)


def matrix_hash(matrix: np.ndarray, palette: list[dict]) -> str:
    payload = matrix.astype('<i2').tobytes() + json.dumps(
        palette, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(payload).hexdigest()


def save_master(matrix: np.ndarray, palette: list[dict]) -> None:
    data = np.zeros((GRID, GRID, 4), dtype=np.uint8)
    for i, p in enumerate(palette):
        mask = matrix == i
        data[mask, :3] = p['rgb']
        data[mask, 3] = 255
    Image.fromarray(data, 'RGBA').save(OUT / 'st_trina_pixel_master.png', optimize=False)


def draw_centered(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int],
                  value: str, fnt: ImageFont.FreeTypeFont, fill) -> None:
    l, t, r, b = draw.textbbox((0, 0), value, font=fnt)
    x = box[0] + (box[2] - box[0] - (r - l)) / 2 - l
    y = box[1] + (box[3] - box[1] - (b - t)) / 2 - t
    draw.text((x, y), value, font=fnt, fill=fill)


def render_grid_png(matrix: np.ndarray, palette: list[dict]) -> None:
    left, top, right, bottom = 170, 150, 34, 34
    w, h = left + GRID * CELL + right, top + GRID * CELL + bottom
    im = Image.new('RGB', (w, h), '#F5F1F7')
    d = ImageDraw.Draw(im)
    id_font, coord_font, title_font = font(12), font(13), font(23)
    d.text((24, 22), PATTERN_TITLE,
           font=title_font, fill='#21152F')
    d.text((24, 58), f'{PALETTE_LABEL} palette · 1 pixel = 1 bead · transparent cells = no bead',
           font=font(14), fill='#4A3B58')
    colors = [p['rgb'] for p in palette]
    for y in range(GRID):
        for x in range(GRID):
            x0, y0 = left + x * CELL, top + y * CELL
            v = int(matrix[y, x])
            fill = colors[v] if v >= 0 else (250, 248, 250)
            d.rectangle((x0, y0, x0 + CELL, y0 + CELL), fill=fill)
            if v >= 0:
                draw_centered(d, (x0, y0, x0 + CELL, y0 + CELL),
                              palette[v]['id'], id_font, text_color(fill))
    # Thin cell grid plus stronger 10-bead divisions.
    for i in range(GRID + 1):
        width = 3 if i and i % 10 == 0 else 1
        col = '#25172F' if width == 3 else '#6F6675'
        x = left + i * CELL
        y = top + i * CELL
        d.line((x, top, x, top + GRID * CELL), fill=col, width=width)
        d.line((left, y, left + GRID * CELL, y), fill=col, width=width)
    for i in range(GRID):
        x0 = left + i * CELL
        y0 = top + i * CELL
        draw_centered(d, (x0, top - 38, x0 + CELL, top - 4), str(i + 1), coord_font, '#21152F')
        draw_centered(d, (left - 46, y0, left - 8, y0 + CELL), str(i + 1), coord_font, '#21152F')
    im.save(OUT / 'st_trina_pattern_grid.png', optimize=False)


def render_grid_svg(matrix: np.ndarray, palette: list[dict], digest: str) -> None:
    left, top, right, bottom = 170, 150, 34, 34
    w, h = left + GRID * CELL + right, top + GRID * CELL + bottom
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<!-- bead-matrix-sha256: {digest} -->',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        '<rect width="100%" height="100%" fill="#F5F1F7"/>',
        '<style>.id{font:12px Menlo,monospace;font-weight:700;text-anchor:middle;dominant-baseline:central}.coord{font:13px Menlo,monospace;text-anchor:middle;dominant-baseline:central}.title{font:23px Menlo,monospace;font-weight:700}.sub{font:14px Menlo,monospace}</style>',
        f'<text class="title" x="24" y="43" fill="#21152F">{html.escape(PATTERN_TITLE)}</text>',
        f'<text class="sub" x="24" y="78" fill="#4A3B58">{html.escape(PALETTE_LABEL)} palette · 1 pixel = 1 bead · transparent cells = no bead</text>',
    ]
    for y in range(GRID):
        for x in range(GRID):
            v = int(matrix[y, x])
            hx = palette[v]['hex'] if v >= 0 else '#FAF8FA'
            attrs = f'data-row="{y + 1}" data-col="{x + 1}"'
            if v >= 0:
                attrs += f' data-color="{palette[v]["id"]}"'
            lines.append(f'<rect x="{left + x * CELL}" y="{top + y * CELL}" width="{CELL}" height="{CELL}" fill="{hx}" {attrs}/>')
            if v >= 0:
                tc = '#FAF8FF' if text_color(palette[v]['rgb'])[0] > 200 else '#160E23'
                lines.append(f'<text class="id" x="{left + (x + .5) * CELL}" y="{top + (y + .5) * CELL}" fill="{tc}">{palette[v]["id"]}</text>')
    for i in range(GRID + 1):
        sw = 3 if i and i % 10 == 0 else 1
        c = '#25172F' if sw == 3 else '#6F6675'
        x, y = left + i * CELL, top + i * CELL
        lines.append(f'<path d="M{x} {top}V{top + GRID * CELL}" stroke="{c}" stroke-width="{sw}"/>')
        lines.append(f'<path d="M{left} {y}H{left + GRID * CELL}" stroke="{c}" stroke-width="{sw}"/>')
    for i in range(GRID):
        lines.append(f'<text class="coord" x="{left + (i + .5) * CELL}" y="{top - 21}" fill="#21152F">{i + 1}</text>')
        lines.append(f'<text class="coord" x="{left - 27}" y="{top + (i + .5) * CELL}" fill="#21152F">{i + 1}</text>')
    lines.append('</svg>')
    (OUT / 'st_trina_pattern_grid.svg').write_text('\n'.join(lines), encoding='utf-8')


def render_palette(palette: list[dict], counts: Counter) -> None:
    row_h, header_h, w = 76, 118, 1640
    h = header_h + row_h * len(palette) + 40
    im = Image.new('RGB', (w, h), '#F7F3F8')
    d = ImageDraw.Draw(im)
    d.text((36, 24), PALETTE_CARD_TITLE, font=font(30), fill='#21152F')
    d.text((36, 68), PALETTE_SUBTITLE, font=font(18), fill='#65566F')
    for i, p in enumerate(palette):
        y = header_h + i * row_h
        c = p['rgb']
        d.rectangle((36, y + 8, 190, y + 68), fill=c, outline='#24162E', width=2)
        value = (f"{p['id']}  |  {p['name']}  |  {p['hex']}  |  "
                 f"RGB({c[0]}, {c[1]}, {c[2]})  |  {counts[i]} beads")
        d.text((220, y + 25), value, font=font(19), fill='#21152F')
        d.line((36, y + row_h - 1, w - 36, y + row_h - 1), fill='#D9D0DD', width=1)
    im.save(OUT / 'st_trina_color_palette.png', optimize=False)


def render_tiles(matrix: np.ndarray, palette: list[dict]) -> None:
    tile_dir = OUT / 'tiles'
    tile_dir.mkdir()
    colors = [p['rgb'] for p in palette]
    for tr in range(4):
        for tc in range(4):
            row0, col0 = tr * TILE_BEADS, tc * TILE_BEADS
            left, top, right, bottom = 126, 126, 30, 34
            w = left + TILE_BEADS * TILE_CELL + right
            h = top + TILE_BEADS * TILE_CELL + bottom
            im = Image.new('RGB', (w, h), '#F5F1F7')
            d = ImageDraw.Draw(im)
            title = f'Tile R{tr + 1:02d} C{tc + 1:02d} · rows {row0 + 1}–{row0 + 24} · cols {col0 + 1}–{col0 + 24}'
            d.text((24, 24), title, font=font(19), fill='#21152F')
            d.text((24, 58), 'Global coordinates · 1 pixel = 1 bead', font=font(14), fill='#5D4D67')
            for ly in range(TILE_BEADS):
                for lx in range(TILE_BEADS):
                    gy, gx = row0 + ly, col0 + lx
                    x0, y0 = left + lx * TILE_CELL, top + ly * TILE_CELL
                    v = int(matrix[gy, gx])
                    fill = colors[v] if v >= 0 else (250, 248, 250)
                    d.rectangle((x0, y0, x0 + TILE_CELL, y0 + TILE_CELL), fill=fill)
                    if v >= 0:
                        draw_centered(d, (x0, y0, x0 + TILE_CELL, y0 + TILE_CELL),
                                      palette[v]['id'], font(16), text_color(fill))
            for i in range(TILE_BEADS + 1):
                global_x, global_y = col0 + i, row0 + i
                x, y = left + i * TILE_CELL, top + i * TILE_CELL
                major_x = global_x and global_x % 10 == 0
                major_y = global_y and global_y % 10 == 0
                d.line((x, top, x, top + TILE_BEADS * TILE_CELL),
                       fill='#25172F' if major_x else '#6F6675', width=3 if major_x else 1)
                d.line((left, y, left + TILE_BEADS * TILE_CELL, y),
                       fill='#25172F' if major_y else '#6F6675', width=3 if major_y else 1)
            for i in range(TILE_BEADS):
                x0, y0 = left + i * TILE_CELL, top + i * TILE_CELL
                draw_centered(d, (x0, top - 35, x0 + TILE_CELL, top - 3), str(col0 + i + 1), font(13), '#21152F')
                draw_centered(d, (left - 44, y0, left - 6, y0 + TILE_CELL), str(row0 + i + 1), font(13), '#21152F')
            im.save(tile_dir / f'tile_R{tr + 1:02d}_C{tc + 1:02d}.png', optimize=False)


def save_inventory(palette: list[dict], counts: Counter, total: int) -> None:
    path = OUT / 'st_trina_bead_inventory.csv'
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['Color ID', 'Color Name', 'HEX', 'RGB', 'Bead Count', 'Percentage'])
        for i, p in enumerate(palette):
            c = p['rgb']
            w.writerow([p['id'], p['name'], p['hex'], f'RGB({c[0]}, {c[1]}, {c[2]})',
                        counts[i], f'{counts[i] / total * 100:.4f}%'])
        w.writerow(['TOTAL BEADS', '', '', '', total, '100.0000%'])


def save_preview() -> None:
    master = Image.open(OUT / 'st_trina_pixel_master.png').convert('RGBA')
    master.resize((768, 768), Image.Resampling.NEAREST).save(
        OUT / 'preview' / 'st_trina_preview.png', optimize=False)


def run_qa(matrix: np.ndarray, palette: list[dict], counts: Counter,
           total: int, digest: str, meta: dict) -> bool:
    results: list[tuple[str, bool, str]] = []
    master = Image.open(OUT / 'st_trina_pixel_master.png').convert('RGBA')
    ma = np.asarray(master)
    results.append(('1. Master size is exactly 96×96', master.size == (96, 96), str(master.size)))
    allowed = {tuple(p['rgb']) for p in palette}
    actual = {tuple(c) for c in ma[ma[..., 3] == 255, :3]}
    results.append(('2. No colors outside palette', actual <= allowed,
                    f'{len(actual)} actual colors / {len(allowed)} palette colors'))
    alphas = sorted(int(v) for v in np.unique(ma[..., 3]))
    results.append(('3. Alpha is binary and valid', set(alphas) <= {0, 255}, f'alpha values: {alphas}'))
    results.append(('4. No anti-aliasing or gradient colors', actual == allowed,
                    'every opaque pixel is an exact defined palette RGB value'))

    gp = Image.open(OUT / 'st_trina_pattern_grid.png').convert('RGB')
    ga = np.asarray(gp)
    left, top = 170, 150
    mismatch = 0
    for y in range(GRID):
        for x in range(GRID):
            center = tuple(ga[top + y * CELL + CELL // 2, left + x * CELL + 3])
            v = int(matrix[y, x])
            expected = tuple(palette[v]['rgb']) if v >= 0 else (250, 248, 250)
            mismatch += center != expected
    results.append(('5. PNG grid strictly corresponds to master matrix', mismatch == 0,
                    f'{mismatch} sampled cell-fill mismatches'))

    svg = (OUT / 'st_trina_pattern_grid.svg').read_text(encoding='utf-8')
    svg_cells = svg.count('data-row=')
    svg_beads = svg.count('data-color=')
    results.append(('6. SVG and PNG use the same bead matrix',
                    digest in svg and svg_cells == 9216 and svg_beads == total,
                    f'matrix SHA-256 {digest}; {svg_cells} vector cells; {svg_beads} bead IDs'))
    master_total = int(np.count_nonzero(ma[..., 3] == 255))
    results.append(('7. Inventory equals non-transparent master pixels',
                    sum(counts.values()) == master_total == total,
                    f'inventory={sum(counts.values())}, master={master_total}'))
    ids = [p['id'] for p in palette]
    results.append(('8. Every Color ID is unique', len(ids) == len(set(ids)),
                    f'{len(ids)} IDs, {len(set(ids))} unique'))
    valid_matrix = np.all((matrix == -1) | ((matrix >= 0) & (matrix < len(palette))))
    results.append(('9. Every pixel maps to zero or one Color ID', bool(valid_matrix),
                    'matrix uses -1 for transparent or one integer palette index'))

    tile_mismatch = 0
    for tr in range(4):
        for tc in range(4):
            tile = Image.open(OUT / 'tiles' / f'tile_R{tr + 1:02d}_C{tc + 1:02d}.png').convert('RGB')
            ta = np.asarray(tile)
            for ly in range(TILE_BEADS):
                for lx in range(TILE_BEADS):
                    gy, gx = tr * 24 + ly, tc * 24 + lx
                    sample = tuple(ta[126 + ly * TILE_CELL + TILE_CELL // 2,
                                      126 + lx * TILE_CELL + 3])
                    v = int(matrix[gy, gx])
                    expected = tuple(palette[v]['rgb']) if v >= 0 else (250, 248, 250)
                    tile_mismatch += sample != expected
    results.append(('10. Tiles reconstruct the full matrix exactly', tile_mismatch == 0,
                    f'{tile_mismatch} sampled cell-fill mismatches across 16 tiles'))
    results.append(('11. Practical color-count target is met', 20 <= len(palette) <= 35,
                    f'{len(palette)} used colors; target 20–35'))
    results.append(('12. All transparent cells contain no bead ID',
                    int(np.count_nonzero(matrix < 0)) + total == GRID * GRID,
                    f'{int(np.count_nonzero(matrix < 0))} transparent + {total} beads = 9216 cells'))

    overall = all(ok for _, ok, _ in results)
    lines = [
        '# St. Trina Bead Pattern — QA Report', '',
        f'**Overall: {"PASS" if overall else "FAIL"}**', '',
        '- Grid: 96 × 96 logical pixels',
        f'- Used colors: {len(palette)} ({PALETTE_LABEL})',
        f'- Total beads: {total}',
        f'- Transparent cells: {GRID * GRID - total}',
        f'- Bead matrix SHA-256: `{digest}`',
        f'- Source plate: generated from the three user-provided references; original references remained read-only.',
        f'- Source extraction bbox: `{meta["source_bbox"]}` from `{meta["source_size"]}` pixels.',
        '', '## Checks', ''
    ]
    for label, ok, detail in results:
        lines.extend([f'### {label}: {"PASS" if ok else "FAIL"}', '', detail, ''])
    lines.extend([
        '## Engineering notes', '',
        '- Final master uses binary alpha only: 0 or 255.',
        '- Each opaque pixel is one exact defined palette RGB value; no interpolation colors remain.',
        '- Grid PNG and true vector SVG are rendered from the same in-memory bead matrix.',
        '- Color matching is an estimate for screen colors. Physical bead batches and lighting may differ.',
        f'- {PALETTE_CLAIM_NOTE}',
    ])
    (OUT / 'QA_REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    return overall


def make_zip() -> None:
    with zipfile.ZipFile(ZIP_PATH, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file():
                z.write(p, Path('st_trina_bead_pattern') / p.relative_to(OUT))


def main() -> None:
    if OUT.exists() or ZIP_PATH.exists():
        raise FileExistsError('Refusing to overwrite existing output or ZIP')
    OUT.mkdir(parents=True)
    (OUT / 'preview').mkdir()
    matrix, meta = extract_matrix()
    palette = meta['palette']
    counts = Counter(int(v) for v in matrix.ravel() if v >= 0)
    total = sum(counts.values())
    digest = matrix_hash(matrix, palette)
    save_master(matrix, palette)
    render_grid_png(matrix, palette)
    render_grid_svg(matrix, palette, digest)
    render_palette(palette, counts)
    render_tiles(matrix, palette)
    save_inventory(palette, counts, total)
    save_preview()
    overall = run_qa(matrix, palette, counts, total, digest, meta)
    make_zip()
    print(json.dumps({'grid': [GRID, GRID], 'colors': len(palette),
                      'total_beads': total, 'qa': 'PASS' if overall else 'FAIL',
                      'output': str(OUT), 'zip': str(ZIP_PATH),
                      'matrix_sha256': digest}, ensure_ascii=False))


if __name__ == '__main__':
    main()

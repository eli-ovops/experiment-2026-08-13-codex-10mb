from __future__ import annotations

import re
import urllib.request
from collections import Counter
from pathlib import Path

import numpy as np

import generate_st_trina_pattern as g


MARD_SOURCE = (
    'https://raw.githubusercontent.com/Jett-Wu/'
    'Perler_Beads_Generator/main/src/palette.ts'
)


def load_mard_221() -> list[tuple[str, str]]:
    with urllib.request.urlopen(MARD_SOURCE, timeout=20) as response:
        source = response.read().decode('utf-8')
    match = re.search(r"const rawColorsCsv = `\n(.*?)\n`;", source, re.S)
    if not match:
        raise RuntimeError('Could not locate MARD basic palette in source')
    rows = []
    for line in match.group(1).splitlines():
        code, hx = [v.strip() for v in line.split(',', 1)]
        rows.append((code, hx.upper()))
    if len(rows) != 221:
        raise RuntimeError(f'Expected MARD 221 colors, received {len(rows)}')
    return rows


def select_mard_subset(rows: list[tuple[str, str]]) -> list[tuple[str, str, str]]:
    custom_targets = list(g.BASE_PALETTE)
    all_mard = [(f'MARD {code}', hx, code) for code, hx in rows]
    g.BASE_PALETTE = all_mard
    full_matrix, meta = g.extract_matrix()
    counts = Counter(int(v) for v in full_matrix.ravel() if v >= 0)
    ranked_codes = [meta['palette'][i]['id'] for i, _ in counts.most_common()]

    # Start with the most-used exact MARD matches from the subject itself.
    chosen_codes = ranked_codes[:32]

    # Explicitly protect pale petals and face/hand skin families even when they
    # cover only a few beads. These indices refer to the curated source slots.
    mard_rgb = np.array([g.rgb(hx) for _, hx in rows], dtype=np.uint8)
    mard_lab = g.srgb_to_lab(mard_rgb)
    for target_index in (11, 12, 13, 18, 19, 20):
        entry = custom_targets[target_index]
        source_lab = g.srgb_to_lab(np.array([g.rgb(entry[1])], dtype=np.uint8))[0]
        delta = mard_lab - source_lab
        dist = 1.25 * delta[:, 0] ** 2 + delta[:, 1] ** 2 + delta[:, 2] ** 2
        code = rows[int(np.argmin(dist))][0]
        if code not in chosen_codes and len(chosen_codes) < 35:
            chosen_codes.append(code)

    for code in ranked_codes:
        if len(chosen_codes) >= 35:
            break
        if code not in chosen_codes:
            chosen_codes.append(code)
    selected = [(f'MARD {code}', hx, code) for code, hx in rows if code in chosen_codes]
    if not 20 <= len(selected) <= 35:
        raise RuntimeError(f'MARD subset has {len(selected)} colors; expected 20–35')
    return selected


def main() -> None:
    root = Path('/Users/USER/Documents/Codex/2026-08-13/codex-10mb')
    g.OUT = root / 'outputs' / 'st_trina_bead_pattern_mard'
    g.ZIP_PATH = root / 'outputs' / 'st_trina_bead_pattern_mard.zip'
    g.PALETTE_LABEL = 'MARD-221'
    g.PATTERN_TITLE = 'ST. TRINA — 96×96 MARD BEAD PATTERN'
    g.PALETTE_CARD_TITLE = 'ST. TRINA — MARD BEAD PALETTE'
    g.PALETTE_SUBTITLE = 'MARD codes mapped from the verified 221-color basic palette'
    g.PALETTE_CLAIM_NOTE = (
        'Color codes are MARD identifiers sourced from the cited MARD-221 dataset; '
        'screen HEX values remain estimates and physical batches may vary.'
    )
    g.BASE_PALETTE = select_mard_subset(load_mard_221())
    g.main()


if __name__ == '__main__':
    main()

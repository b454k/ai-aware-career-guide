#!/usr/bin/env python3
"""Extract the ILO's generative-AI exposure score for each ISCO-08 occupation (ROADMAP 6.2, D5 = B).

Source: Gmyrek et al. (2025), "Generative AI and Jobs: A Refined Global Index of Occupational
Exposure", ILO Working Paper 140, CC BY 4.0 (data/ilo/WP140_web.pdf, from scripts/download_sources.py).
Annex Table A1 (PDF pages 51-64) gives, for each of the 427 four-digit ISCO-08 occupations, the mean
and standard deviation of its tasks' exposure scores and its exposure gradient. The ILO publishes no
machine-readable version, so the table is read from the PDF twice:
  - from the page text, one cell per line (long names, and "Minimal Exposure", wrap onto two lines);
  - with PyMuPDF's table finder, an independent reading of the same pages.
Every row's code, group, mean and SD must agree between the two; names are taken from the text,
because the table finder garbles the "fi" ligature ("Classifei d"). Names are kept as published,
including two typos in the PDF ("Systems Aministrators", "Clearing and Forwarding Aents").

    python scripts/ai_impact/extract_ilo_wp140.py   -> data/processed/ilo_wp140_exposure.csv
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PDF = PROJECT_ROOT / "data" / "ilo" / "WP140_web.pdf"
OUTPUT = PROJECT_ROOT / "data" / "processed" / "ilo_wp140_exposure.csv"
PAGES = range(50, 64)  # PDF pages 51-64, 0-based
GROUPS = ("Gradient 4", "Gradient 3", "Gradient 2", "Gradient 1", "Minimal Exposure", "Not Exposed")
EXPECTED_ROWS = 427  # stated in the paper
NUMBER = re.compile(r"\d*\.?\d+")


def from_text(doc: fitz.Document) -> list[tuple[str, str, float, float, str]]:
    """(code, name, mean, sd, group) rows read from the page text."""
    lines = [line.strip() for n in PAGES for line in doc[n].get_text().splitlines() if line.strip()]
    rows, i = [], 0
    while i < len(lines) - 1:
        if lines[i] in GROUPS:
            group, i = lines[i], i + 1
        elif f"{lines[i]} {lines[i + 1]}" in GROUPS:
            group, i = f"{lines[i]} {lines[i + 1]}", i + 2
        else:
            i += 1
            continue
        code = lines[i]
        if not re.fullmatch(r"\d{4}", code):
            sys.exit(f"Expected a 4-digit ISCO code after {group!r}, got {code!r}")
        name, i = [], i + 1
        while not NUMBER.fullmatch(lines[i]):
            name.append(lines[i])
            i += 1
        rows.append((code, " ".join(" ".join(name).split()), float(lines[i]), float(lines[i + 1]), group))
        i += 2
    return rows


def from_tables(doc: fitz.Document) -> list[tuple[str, float, float, str]]:
    """(code, mean, sd, group) rows read by PyMuPDF's table finder."""
    rows = []
    for n in PAGES:
        for table in doc[n].find_tables().tables:
            for cells in table.extract():
                cells = [" ".join((cell or "").split()) for cell in cells]
                if len(cells) == 5 and re.fullmatch(r"\d{4}", cells[1]):
                    rows.append((cells[1], float(cells[3]), float(cells[4]), cells[0]))
    return rows


def main() -> int:
    doc = fitz.open(PDF)
    rows = from_text(doc)
    check = from_tables(doc)
    if [(code, mean, sd, group) for code, _, mean, sd, group in rows] != check:
        sys.exit(f"The two readings differ: text {len(rows)} rows, table finder {len(check)} rows")
    if len(rows) != EXPECTED_ROWS or len({row[0] for row in rows}) != EXPECTED_ROWS:
        sys.exit(f"Expected {EXPECTED_ROWS} distinct occupations, got {len(rows)} rows")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["isco08_code", "occupation", "exposure_mean", "exposure_sd", "exposure_gradient"])
        writer.writerows(rows)
    groups = {group: sum(row[4] == group for row in rows) for group in GROUPS}
    print(f"wrote {OUTPUT.relative_to(PROJECT_ROOT)}: {len(rows)} occupations, both readings agree; {groups}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Join each O*NET career to the ILO's exposure score of its ISCO-08 group (ROADMAP 6, D5 = B panel).

Inputs (both rebuilt by research-requirement scripts, so the result is committed for the app):
  data/processed/onet_isco08.csv          career -> ISCO-08 unit group (scripts/onet/build_onet_isco08.py, 6.3)
  data/processed/ilo_wp140_exposure.csv   ISCO-08 group -> ILO exposure (scripts/ai_impact/extract_ilo_wp140.py, 6.2)
Output: data/ilo/ilo_exposure_by_career.csv, one row per career that has a score, with how many careers in
this app share the group: an ISCO group is broader than an O*NET career, and the app says so.

    python scripts/ai_impact/build_ilo_by_career.py
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LINKS = PROJECT_ROOT / "data" / "processed" / "onet_isco08.csv"
ILO = PROJECT_ROOT / "data" / "processed" / "ilo_wp140_exposure.csv"
OUTPUT = PROJECT_ROOT / "data" / "ilo" / "ilo_exposure_by_career.csv"


def main() -> int:
    with LINKS.open(encoding="utf-8", newline="") as handle:
        links = [row for row in csv.DictReader(handle) if row["isco08_code"]]
    with ILO.open(encoding="utf-8", newline="") as handle:
        ilo = {row["isco08_code"]: row for row in csv.DictReader(handle)}
    careers_per_group = Counter(row["isco08_code"] for row in links)
    rows = [
        (
            link["onetsoc_code"], link["isco08_code"], ilo[link["isco08_code"]]["occupation"],
            ilo[link["isco08_code"]]["exposure_mean"], ilo[link["isco08_code"]]["exposure_sd"],
            ilo[link["isco08_code"]]["exposure_gradient"], careers_per_group[link["isco08_code"]], link["method"],
        )
        for link in links
        if link["isco08_code"] in ilo
    ]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["onetsoc_code", "isco08_code", "isco08_title", "exposure_mean", "exposure_sd",
                         "exposure_gradient", "careers_in_group", "link_method"])
        writer.writerows(rows)
    print(f"wrote {OUTPUT.relative_to(PROJECT_ROOT)}: {len(rows)} careers with an ILO score "
          f"({len(links) - len(rows)} linked careers in groups the ILO table lacks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

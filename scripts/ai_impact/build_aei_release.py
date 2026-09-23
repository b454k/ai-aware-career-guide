#!/usr/bin/env python3
"""Extract what the app can use from an Anthropic Economic Index "long format" release (ROADMAP 2.5).

Releases from 2026 on (e.g. release_2026_06_26) have one row per metric x place x
category; see data_documentation.md in the release folder. This keeps:
  - O*NET tasks (category onet, level 0) and occupations (soc_occupation, level 0),
    plus the overall row, for GLOBAL and Turkey (TUR);
  - both sources (claude_ai: Claude.ai chats; 1p_api: API calls, global only);
  - every metric except the 32 artifact_* labels.
A missing row means Anthropic did not publish that cell (sample thresholds), not zero.
node_external_id mixes task numbers, SOC codes and "-": read it as text.

    python scripts/ai_impact/build_aei_release.py release_2026_06_26
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RELEASES_DIR = PROJECT_ROOT / "data" / "anthropic_economic_index"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
EXPECTED_COLUMNS = [
    "date_start", "date_end", "geo_id", "geo_level", "category_name",
    "hierarchy_level", "metric_id", "value", "node_name", "node_external_id",
]


def main() -> int:
    release = sys.argv[1] if len(sys.argv) > 1 else "release_2026_06_26"
    files = sorted((RELEASES_DIR / release / "data").glob("aei_*.csv"))
    if not files:
        sys.exit(f"No aei_*.csv files in {RELEASES_DIR / release / 'data'}")
    output = OUTPUT_DIR / f"aei_{release}.csv"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    selects = []
    for path in files:
        source = "1p_api" if "_1p_api_" in path.name else "claude_ai"
        columns = [row[0] for row in con.execute(f"DESCRIBE SELECT * FROM read_csv_auto('{path.as_posix()}', types={{'node_external_id': 'VARCHAR'}})").fetchall()]
        if columns != EXPECTED_COLUMNS:  # the schema check D5 asked for
            sys.exit(f"Schema changed in {path.name}: {columns}")
        selects.append(f"SELECT '{source}' AS source, * FROM read_csv_auto('{path.as_posix()}', types={{'node_external_id': 'VARCHAR'}})")
    con.execute(
        f"""
        CREATE TABLE kept AS
        SELECT * FROM ({' UNION ALL '.join(selects)})
        WHERE geo_id IN ('GLOBAL', 'TUR')
          AND hierarchy_level = 0
          AND category_name IN ('overall', 'onet', 'soc_occupation')
          AND metric_id NOT LIKE 'artifact_%'
        """
    )
    con.execute(f"COPY (SELECT * FROM kept ORDER BY ALL) TO '{output.as_posix()}' (HEADER)")
    print(f"wrote {output.relative_to(PROJECT_ROOT)}")
    for row in con.execute(
        """
        SELECT source, geo_id, category_name, date_start, count(DISTINCT node_external_id) AS nodes, count(*) AS rows
        FROM kept GROUP BY ALL ORDER BY ALL
        """
    ).fetchall():
        print("  " + " | ".join(str(value) for value in row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

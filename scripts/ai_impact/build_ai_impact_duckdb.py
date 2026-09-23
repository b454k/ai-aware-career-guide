#!/usr/bin/env python3
"""Build data/duckdb/ai_impact.duckdb, the AI-impact tables the app reads (ROADMAP 3.2).

Inputs (all from Anthropic's Economic Index on Hugging Face, CC BY):
  data/anthropic_economic_index/labor_market_impacts/task_penetration.csv  (task text, coverage)
  data/anthropic_economic_index/labor_market_impacts/job_exposure.csv      (SOC code, observed exposure)
  data/processed/aei_release_2026_06_26.csv  (from scripts/ai_impact/build_aei_release.py)
and data/duckdb/onet.duckdb for the O*NET task IDs.

Tables:
  task_coverage       one row per O*NET occupation and task that Anthropic covers. task_penetration.csv
                      has only the task text, so tasks are joined by text: the exact wording first; for an
                      O*NET task with no exact match, the same text ignoring punctuation and case, if that
                      gives exactly one value. Every occupation with that task text gets the value.
  occupation_exposure observed exposure per SOC occupation, attached to O*NET code SOC + ".00".
  claude_usage        the 2026 release extract, as is.

    python scripts/ai_impact/build_ai_impact_duckdb.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LABOR_MARKET = PROJECT_ROOT / "data" / "anthropic_economic_index" / "labor_market_impacts"
AEI_EXTRACT = PROJECT_ROOT / "data" / "processed" / "aei_release_2026_06_26.csv"
ONET_DUCKDB = PROJECT_ROOT / "data" / "duckdb" / "onet.duckdb"
OUTPUT = PROJECT_ROOT / "data" / "duckdb" / "ai_impact.duckdb"

# Lower case, letters/digits/spaces only, single spaces: "topics, such" == "topics such".
NORMALIZED = "lower(regexp_replace(regexp_replace({text}, '[^A-Za-z0-9 ]', '', 'g'), ' +', ' ', 'g'))"


def main() -> int:
    for path in (LABOR_MARKET / "task_penetration.csv", LABOR_MARKET / "job_exposure.csv", AEI_EXTRACT, ONET_DUCKDB):
        if not path.exists():
            sys.exit(f"Missing input: {path.relative_to(PROJECT_ROOT)}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT.exists():
        OUTPUT.unlink()  # a build output, rebuilt from the inputs above
    con = duckdb.connect(str(OUTPUT))
    con.execute(f"ATTACH '{ONET_DUCKDB.as_posix()}' AS onet (READ_ONLY)")
    con.execute(
        f"CREATE TEMP TABLE penetration AS SELECT task, penetration FROM read_csv_auto('{(LABOR_MARKET / 'task_penetration.csv').as_posix()}')"
    )
    con.execute(
        f"""
        CREATE TABLE task_coverage AS
        WITH exact AS (
            SELECT t.onetsoc_code, t.task_id, t.task, max(p.penetration) AS coverage, 'exact' AS text_match
            FROM onet.task_statements AS t JOIN penetration AS p ON p.task = t.task
            GROUP BY ALL
        ),
        by_key AS (
            SELECT {NORMALIZED.format(text='task')} AS key, min(penetration) AS coverage
            FROM penetration GROUP BY 1 HAVING count(DISTINCT penetration) = 1
        ),
        loose AS (
            SELECT t.onetsoc_code, t.task_id, t.task, k.coverage, 'ignoring punctuation and case' AS text_match
            FROM onet.task_statements AS t JOIN by_key AS k ON k.key = {NORMALIZED.format(text='t.task')}
            WHERE NOT EXISTS (SELECT 1 FROM exact AS e WHERE e.onetsoc_code = t.onetsoc_code AND e.task_id = t.task_id)
        )
        SELECT * FROM exact UNION ALL SELECT * FROM loose
        """
    )
    con.execute(
        f"""
        CREATE TABLE occupation_exposure AS
        SELECT occ_code || '.00' AS onetsoc_code, title AS soc_title, observed_exposure
        FROM read_csv_auto('{(LABOR_MARKET / 'job_exposure.csv').as_posix()}', types={{'occ_code': 'VARCHAR'}})
        """
    )
    con.execute(
        f"CREATE TABLE claude_usage AS SELECT * FROM read_csv_auto('{AEI_EXTRACT.as_posix()}', types={{'node_external_id': 'VARCHAR'}})"
    )
    for table in ("task_coverage", "occupation_exposure", "claude_usage"):
        print(f"{table}: {con.execute(f'SELECT count(*) FROM {table}').fetchone()[0]} rows")
    print(con.execute("SELECT text_match, count(*) FROM task_coverage GROUP BY 1 ORDER BY 1").fetchall())
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

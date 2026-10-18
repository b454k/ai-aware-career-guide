#!/usr/bin/env python3
"""Each career's robot exposure, from Anthropic's "What work can robots do?" (Legate-Yang & Massenkoff, 2026-09-30).

Claude Opus 5, with web search, rated each physical O*NET 29.3 task by the setting in which robots it could cite
had done it: E1 a purpose-built robot cell, E2 a structured workplace run by an institution, E3 anywhere (E0:
no cited robot could). It also estimated each task's share of the job's working time.

Input: data/anthropic_economic_index/robot_exposure/robot_exposure_tasks.csv (100 MB, scripts/download_sources.py)
Outputs, committed for the app (the input is not):
  data/robots/robot_exposure_by_career.csv  per career: the study's index (0-3), and the share of working time
                                            in physical tasks and in each tier
  data/robots/robot_tasks_by_career.csv     per career, its TOP_TASKS robot-exposed tasks by share of working
                                            time, each with one cited robot (the year of its date only; the dates carry notes such as
                                            "2025 (current product page)"): the first source of the largest
                                            share of the task's cases rated at the task's tier or higher

    python scripts/ai_impact/build_robot_by_career.py
"""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TASKS = PROJECT_ROOT / "data" / "anthropic_economic_index" / "robot_exposure" / "robot_exposure_tasks.csv"
BY_CAREER = PROJECT_ROOT / "data" / "robots" / "robot_exposure_by_career.csv"
TOP = PROJECT_ROOT / "data" / "robots" / "robot_tasks_by_career.csv"
TIERS = ("E1", "E2", "E3")  # scores 1, 2, 3; E0 and non-physical tasks score 0
TOP_TASKS = 5


def example_robot(row: dict[str, str]) -> dict[str, str]:
    """The cited robot behind the task's tier: from the largest share of its cases rated at that tier or higher."""
    rank = TIERS.index(row["exposure_tier"])
    cases = [case for case in json.loads(row["instances"]) if case["tier"] in TIERS[rank:]]
    case = max(cases, key=lambda case: int(case["weight_pct"]))
    sources = {str(source["source"]): source for source in json.loads(row["sources"])}
    return sources[case["sources"].split(",")[0].strip()]


def year(date: str | None) -> str:
    found = re.search(r"\d{4}", date or "")
    return found.group() if found else ""


def main() -> int:
    csv.field_size_limit(1 << 30)
    shares: dict[str, dict[str, float]] = defaultdict(lambda: dict.fromkeys(("physical", *TIERS), 0.0))
    exposed: dict[str, list[dict[str, str]]] = defaultdict(list)
    with TASKS.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            career = shares[row["onetsoc_code"]]
            if row["physical"] == "Yes":
                career["physical"] += float(row["time_share"])
            if row["exposure_tier"] in TIERS:
                career[row["exposure_tier"]] += float(row["time_share"])
                exposed[row["onetsoc_code"]].append(row)

    BY_CAREER.parent.mkdir(parents=True, exist_ok=True)
    with BY_CAREER.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["onetsoc_code", "robot_exposure_index", "physical_share", "e1_share", "e2_share", "e3_share"])
        for code, career in sorted(shares.items()):
            index = sum(score * career[tier] for score, tier in enumerate(TIERS, start=1))
            writer.writerow([code, round(index, 3), *(round(career[key], 4) for key in ("physical", *TIERS))])
    with TOP.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["onetsoc_code", "task_id", "task_statement", "time_share", "exposure_tier", "robot_system",
                         "robot_developer", "robot_maturity", "robot_autonomy", "robot_year", "robot_url"])
        for code in sorted(exposed):
            for row in sorted(exposed[code], key=lambda row: -float(row["time_share"]))[:TOP_TASKS]:
                robot = example_robot(row)
                writer.writerow([code, row["task_id"], row["task_statement"], row["time_share"], row["exposure_tier"],
                                 robot["system"], robot["developer"], robot["maturity"], robot["autonomy_status"],
                                 year(robot["date"]), robot["url"]])
    print(f"wrote {BY_CAREER.relative_to(PROJECT_ROOT)}: {len(shares)} careers; "
          f"{TOP.relative_to(PROJECT_ROOT)}: top {TOP_TASKS} exposed tasks of {len(exposed)} careers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

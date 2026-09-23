#!/usr/bin/env python3
"""Snapshot the final report for fixed synthetic profiles (ROADMAP 0.4).

Runs the same steps as the app (score -> match -> build_final_career_report) with
the LLM disabled, so the output is deterministic. Use it to prove a change did not
alter the report by accident:

    python scripts/make_baseline.py            # write baseline/*.json
    python scripts/make_baseline.py --check    # rebuild and compare, exit 1 on difference
"""

from __future__ import annotations

import difflib
import json
import os
import sys
from pathlib import Path

os.environ["OPENAI_API_KEY"] = ""  # set before any .env load; load_dotenv never overrides it

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from career_rag import ip_final_report  # noqa: E402
from career_rag.config import CAREER_LISTINGS_PATH, QUESTIONS_PATH  # noqa: E402
from career_rag.interest_profiler_local import (  # noqa: E402
    build_profile_result,
    calculate_riasec_scores,
    load_interest_profiler_questions,
)
from career_rag.ip_career_matcher import build_career_matches, load_ip_career_listings  # noqa: E402

BASELINE_DIR = PROJECT_ROOT / "baseline"

# Synthetic profiles: how many activities to check per RIASEC area (first N by id),
# plus current and future Job Zone. Synthetic so no personal answers are committed.
PROFILES = {
    "investigative_conventional": ({"Investigative": 9, "Conventional": 7, "Realistic": 3}, 3, 4),
    "artistic_social": ({"Artistic": 9, "Social": 8, "Enterprising": 4}, 2, 4),
    "realistic_enterprising": ({"Realistic": 8, "Enterprising": 7, "Conventional": 5}, 2, 3),
}

# build_final_career_report saves to onet_interest_profiler/; keep the user's own report untouched.
ip_final_report.save_final_report = lambda *args, **kwargs: None
ip_final_report.save_markdown_report = lambda *args, **kwargs: None


def build_report(name: str) -> str:
    area_counts, current_zone, future_zone = PROFILES[name]
    questions = load_interest_profiler_questions(QUESTIONS_PATH)
    checked = [
        q["id"]
        for area, count in area_counts.items()
        for q in sorted((q for q in questions if q["area"] == area), key=lambda q: q["id"])[:count]
    ]
    scores = calculate_riasec_scores(questions, checked)
    matches = build_career_matches(
        scores=scores,
        current_job_zone=current_zone,
        future_job_zone=future_zone,
        career_listings=load_ip_career_listings(CAREER_LISTINGS_PATH),
    )
    result = build_profile_result(
        scores=scores,
        current_job_zone=current_zone,
        future_job_zone=future_zone,
        career_matches=matches,
    )
    result["profile_id"] = f"baseline-{name}"  # replaces a random uuid4
    result["timestamp"] = "2000-01-01T00:00:00+00:00"  # replaces datetime.now()
    report = ip_final_report.build_final_career_report(result, top_k=10)
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n"


def main() -> int:
    check = "--check" in sys.argv
    failed = False
    BASELINE_DIR.mkdir(exist_ok=True)
    for name in PROFILES:
        path = BASELINE_DIR / f"{name}.json"
        text = build_report(name)
        if not check:
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path.relative_to(PROJECT_ROOT)} ({len(text.splitlines())} lines)")
            continue
        old = path.read_text(encoding="utf-8")
        if old == text:
            print(f"MATCH    {name}")
            continue
        failed = True
        diff = list(difflib.unified_diff(old.splitlines(), text.splitlines(), "baseline", "now", lineterm="", n=1))
        print(f"DIFFERS  {name}: {sum(line[:1] in '+-' for line in diff[2:])} changed lines, first ones:")
        print("\n".join(diff[2:30]))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

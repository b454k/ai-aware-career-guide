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
from career_rag.config import QUESTIONS_PATH  # noqa: E402
from career_rag.interest_profiler_local import (  # noqa: E402
    build_profile_result,
    calculate_riasec_scores,
    load_interest_profiler_questions,
)
from career_rag.departments import DEPARTMENT_JOB_ZONE, department_codes  # noqa: E402
from career_rag.ip_career_matcher import build_career_matches  # noqa: E402

BASELINE_DIR = PROJECT_ROOT / "baseline"

# Synthetic profiles: how many activities to check per RIASEC area (first N by id),
# plus current and future Job Zone. Synthetic so no personal answers are committed.
PROFILES = {
    "investigative_conventional": ({"Investigative": 9, "Conventional": 7, "Realistic": 3}, 3, 4),
    "artistic_social": ({"Artistic": 9, "Social": 8, "Enterprising": 4}, 2, 4),
    "realistic_enterprising": ({"Realistic": 8, "Enterprising": 7, "Conventional": 5}, 2, 3),
}
# Also built in Turkish (ROADMAP 6.1d), saved as baseline/<name>.tr.json.
TURKISH_PROFILES = ["artistic_social"]
# Also built for a student who named a department (ROADMAP 9.1), saved as baseline/<name>.<label>.json.
DEPARTMENT_PROFILES = {"istatistik": ("investigative_conventional", "İstatistik")}

# build_final_career_report saves to onet_interest_profiler/; keep the user's own report untouched.
ip_final_report.save_final_report = lambda *args, **kwargs: None
ip_final_report.save_markdown_report = lambda *args, **kwargs: None


def build_profile(name: str, department: str | None = None) -> dict:
    """The profile the app would save for this synthetic set of answers (and department)."""
    area_counts, current_zone, future_zone = PROFILES[name]
    if department:
        current_zone = future_zone = DEPARTMENT_JOB_ZONE
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
        department_codes=department_codes(department) if department else (),
    )
    result = build_profile_result(
        scores=scores,
        current_job_zone=current_zone,
        future_job_zone=future_zone,
        career_matches=matches,
        department=department,
    )
    result["profile_id"] = f"baseline-{name}"  # replaces a random uuid4
    result["timestamp"] = "2000-01-01T00:00:00+00:00"  # replaces datetime.now()
    return result


def build_report(name: str, language: str = "en", department: str | None = None) -> str:
    report = ip_final_report.build_final_career_report(build_profile(name, department), top_k=10, language=language)
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n"


def main() -> int:
    check = "--check" in sys.argv
    failed = False
    BASELINE_DIR.mkdir(exist_ok=True)
    runs = ([(name, "en", None, name) for name in PROFILES]
            + [(name, "tr", None, f"{name}.tr") for name in TURKISH_PROFILES]
            + [(name, "en", department, f"{name}.{key}") for key, (name, department) in DEPARTMENT_PROFILES.items()])
    for name, language, department, label in runs:
        path = BASELINE_DIR / f"{label}.json"
        text = build_report(name, language, department)
        if not check:
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path.relative_to(PROJECT_ROOT)} ({len(text.splitlines())} lines)")
            continue
        old = path.read_text(encoding="utf-8")
        if old == text:
            print(f"MATCH    {label}")
            continue
        failed = True
        diff = list(difflib.unified_diff(old.splitlines(), text.splitlines(), "baseline", "now", lineterm="", n=1))
        print(f"DIFFERS  {label}: {sum(line[:1] in '+-' for line in diff[2:])} changed lines, first ones:")
        print("\n".join(diff[2:30]))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

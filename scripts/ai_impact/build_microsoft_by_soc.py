#!/usr/bin/env python3
"""Microsoft's AI applicability per occupation, from "Working with AI" (Tomlinson et al. 2025), ROADMAP 10.15.

About 200,000 anonymised Bing Copilot conversations (US, January-September 2024) were classified by an LLM into
O*NET intermediate work activities (IWAs): what the user wanted help with (user goal) and what Copilot did (AI
action), whether Copilot completed it, and how much of the activity its help covered (impact scope). An
occupation's AI applicability score averages, over its IWAs weighted by O*NET importance and relevance, the
completion x scope of the IWAs with enough conversations (share > 0.05%), user and AI side averaged.

Inputs: data/microsoft_working_with_ai/ (github.com/microsoft/working-with-ai at commit 18ec449, CC BY 4.0,
scripts/download_sources.py). Occupations are BLS National Employment Matrix codes (SOC 2018, some aggregated).
Outputs, committed for the app (the inputs are not):
  data/microsoft/ai_applicability_by_soc.csv  per code: the score, its rank among the 785 codes, and the
                                              user-side coverage, completion and scope
  data/microsoft/top_activities_by_soc.csv    per code, its TOP most important work activities that came up
                                              as a user goal, with the share of them Copilot completed

    python scripts/ai_impact/build_microsoft_by_soc.py
"""

from __future__ import annotations

import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE = PROJECT_ROOT / "data" / "microsoft_working_with_ai"
SCORES = PROJECT_ROOT / "data" / "microsoft" / "ai_applicability_by_soc.csv"
ACTIVITIES = PROJECT_ROOT / "data" / "microsoft" / "top_activities_by_soc.csv"
COVERAGE_THRESHOLD = 0.0005  # the paper's: an IWA counts when its share of conversations is above 0.05%
TOP = 5


def read(name: str) -> list[dict[str, str]]:
    with (SOURCE / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    scores = {row["SOC Code"]: float(row["ai_applicability_score"]) for row in read("ai_applicability_scores.csv")}
    metrics = {row["SOC Code"]: row for row in read("soc_metrics.csv")}
    iwas = {row["IWA"]: row for row in read("iwa_metrics.csv")}
    weights = {row.pop("SOC Code"): row for row in read("soc_iwa_weights.csv")}
    links = {}
    for row in read("soc_to_iwas.csv"):
        links.setdefault(row["SOC Code"], []).append(row["IWA"])

    ranked = sorted(scores, key=lambda code: -scores[code])
    SCORES.parent.mkdir(parents=True, exist_ok=True)
    with SCORES.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["soc_code", "title", "ai_applicability_score", "rank", "occupations", "coverage_user",
                         "completion_user", "impact_scope_user"])
        for rank, code in enumerate(ranked, start=1):
            row = metrics[code]
            writer.writerow([code, row["title"], round(scores[code], 4), rank, len(ranked),
                             *(round(float(row[key]), 4) for key in ("coverage_user", "completion_user", "impact_scope_user"))])
    count = 0
    with ACTIVITIES.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["soc_code", "iwa_id", "iwa_title", "weight", "completion_user"])
        for code in sorted(links):
            covered = [iwa for iwa in links[code] if float(iwas[iwa]["share_user"]) > COVERAGE_THRESHOLD]
            for iwa in sorted(covered, key=lambda iwa: -float(weights[code][iwa]))[:TOP]:
                writer.writerow([code, iwa, iwas[iwa]["title"], round(float(weights[code][iwa]), 4),
                                 round(float(iwas[iwa]["completion_user"]), 4)])
                count += 1
    print(f"wrote {SCORES.relative_to(PROJECT_ROOT)}: {len(ranked)} occupations; "
          f"{ACTIVITIES.relative_to(PROJECT_ROOT)}: {count} activities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

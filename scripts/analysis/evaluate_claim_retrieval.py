#!/usr/bin/env python3
"""Score the claims retrieval against your relevance judgments (ROADMAP 5.3, 4.1).

Reads evaluation/claim_relevance_labels.csv (the `relevant` column filled with 1/0) and
data/duckdb/research_claims.duckdb. For both ranking scores (raw cosine, centered):
  precision@1/3/5    share of relevant claims among the first k shown
  threshold sweep    for each minimum score: precision of what is shown, share of the
                     judged-relevant claims kept, and how many occupations show anything
Plus the best scores of some nonsense queries, which should fall below the chosen threshold.

    python scripts/analysis/evaluate_claim_retrieval.py [labels.csv]
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import duckdb
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "research"))

import match_claims_to_occupations as build  # noqa: E402

LABELS = PROJECT_ROOT / "evaluation" / "claim_relevance_labels.csv"
NONSENSE = ["asdf qwerty zxcv", "chocolate cake recipe with strawberries", "the history of the Roman empire"]


def main() -> int:
    labels_path = Path(sys.argv[1]) if len(sys.argv) > 1 else LABELS
    labels = {}
    for row in csv.DictReader(labels_path.open(encoding="utf-8")):
        if row["relevant"].strip() not in {"0", "1"}:
            sys.exit(f"Unjudged row: {row['onetsoc_code']} {row['claim_id']} (fill `relevant` with 1 or 0)")
        labels[(row["onetsoc_code"], row["claim_id"])] = int(row["relevant"])
    codes = sorted({code for code, _ in labels})
    con = duckdb.connect(str(build.OUTPUT), read_only=True)
    candidates = con.execute(
        "SELECT onetsoc_code, claim_id, score, centered FROM claim_candidates WHERE onetsoc_code IN "
        f"({', '.join('?' for _ in codes)})",
        codes,
    ).fetchall()
    judged = [(code, cid, score, centered, labels[(code, cid)]) for code, cid, score, centered in candidates if (code, cid) in labels]
    total_relevant = sum(item[4] for item in judged)
    print(f"judged: {len(judged)} claims, {len(codes)} occupations, {total_relevant} relevant\n")

    for name, column in (("raw score", 2), ("centered score", 3)):
        print(f"== {name}")
        for k in (1, 3, 5):
            hits = []
            for code in codes:
                ranked = sorted((item for item in judged if item[0] == code), key=lambda item: -item[column])[:k]
                hits += [item[4] for item in ranked]
            print(f"  precision@{k}: {np.mean(hits):.3f}")
        values = sorted({round(item[column], 3) for item in judged})
        print("  min score | shown | precision | relevant kept | occupations with any")
        for threshold in np.quantile(values, [0, 0.2, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]):
            shown = [item for item in judged if item[column] >= threshold]
            if not shown:
                continue
            precision = np.mean([item[4] for item in shown])
            kept = sum(item[4] for item in shown) / max(total_relevant, 1)
            print(f"  {threshold:9.3f} | {len(shown):5d} | {precision:9.3f} | {kept:13.3f} | {len({item[0] for item in shown})}/{len(codes)}")

    # What the app would show: at most k claims per career, each above the minimum score.
    print("\n== centered score, at most k claims per career")
    print("  min score | k | shown | precision | occupations with any | with a relevant one")
    for threshold in (0.08, 0.10, 0.12, 0.13, 0.14):
        for k in (1, 2, 3):
            per_code = []
            for code in codes:
                ranked = sorted((item for item in judged if item[0] == code), key=lambda item: -item[3])[:k]
                per_code.append([item[4] for item in ranked if item[3] >= threshold])
            hits = [hit for code_hits in per_code for hit in code_hits]
            precision = np.mean(hits) if hits else 0.0
            print(f"  {threshold:9.2f} | {k} | {len(hits):5d} | {precision:9.3f} | "
                  f"{sum(bool(h) for h in per_code):2d}/{len(codes)} | {sum(any(h) for h in per_code):2d}/{len(codes)}")

    vectors = np.load(build.OUTPUT.with_suffix(".claim_vectors.npy"))
    claim_means = np.load(build.OUTPUT.with_suffix(".claim_means.npy"))
    print("\n== nonsense queries: best raw score | best centered score")
    for query, vector in zip(NONSENSE, build.embed([build.BGE_QUERY_PREFIX + q for q in NONSENSE])):
        raw = vector @ vectors.T
        print(f"  {raw.max():.3f} | {(raw - claim_means).max():.3f}  {query}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

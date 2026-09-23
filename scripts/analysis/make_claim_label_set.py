#!/usr/bin/env python3
"""Write the claims to judge by hand for the retrieval evaluation (ROADMAP 5.3, 4.1).

40 occupations, spread over O*NET's job families (SOC major groups, fixed seed). For each,
the union of its top 5 claims by raw score and by centered score, in random order, so the
judge can't tell which method found a claim. The `relevant` column is left empty:

  relevant = 1 if the claim says something about this occupation, its field or industry,
               or its main tasks;
             0 if it is about other work, or so general it fits any career
               ("AI can perform some of the subtasks in an occupation").

It also writes the 50 randomly chosen claims for the label audit (ROADMAP 4.2): for each,
whether the claim, its impact type, direction and affected entity are right (1/0).

    python scripts/analysis/make_claim_label_set.py
      -> evaluation/claim_relevance_labels.csv, evaluation/claim_label_audit.csv
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLAIMS_DB = PROJECT_ROOT / "data" / "duckdb" / "research_claims.duckdb"
ONET_DB = PROJECT_ROOT / "data" / "duckdb" / "onet.duckdb"
OUTPUT = PROJECT_ROOT / "evaluation" / "claim_relevance_labels.csv"
AUDIT_OUTPUT = PROJECT_ROOT / "evaluation" / "claim_label_audit.csv"
CLAIMS = PROJECT_ROOT / "data" / "research" / "ai_impact_claims.jsonl"
AUDIT_SIZE = 50
AUDIT_FIELDS = [
    "claim_id", "evidence_quote", "claim_text", "impact_type_clean", "impact_direction_clean",
    "affected_entity_type", "affected_entity_text",
]
OCCUPATIONS = 40
TOP = 5
SEED = 2026


def main() -> int:
    for path in (OUTPUT, AUDIT_OUTPUT):
        if path.exists():
            raise SystemExit(f"{path} exists; it may hold your labels. Move it away first.")
    con = duckdb.connect(str(CLAIMS_DB), read_only=True)
    con.execute(f"ATTACH '{ONET_DB.as_posix()}' AS onet (READ_ONLY)")
    codes = [row[0] for row in con.execute("SELECT DISTINCT onetsoc_code FROM claim_candidates ORDER BY 1").fetchall()]
    rng = random.Random(SEED)
    by_group: dict[str, list[str]] = {}
    for code in codes:
        by_group.setdefault(code[:2], []).append(code)
    picked: list[str] = []
    while len(picked) < OCCUPATIONS:  # round-robin over job families
        for group in sorted(by_group):
            remaining = [code for code in by_group[group] if code not in picked]
            if remaining and len(picked) < OCCUPATIONS:
                picked.append(rng.choice(remaining))
    rows = []
    for code in sorted(picked):
        candidates = con.execute(
            f"""
            SELECT o.title, c.claim_id, r.claim_text, r.affected_entity_text
            FROM claim_candidates AS c
            JOIN research_claims AS r USING (claim_id)
            JOIN onet.occupation_data AS o USING (onetsoc_code)
            WHERE c.onetsoc_code = ? AND (c.rank_by_score <= {TOP} OR c.rank_by_centered <= {TOP})
            """,
            [code],
        ).fetchall()
        rng.shuffle(candidates)
        rows += [[code, title, claim_id, text, entity, ""] for title, claim_id, text, entity in candidates]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["onetsoc_code", "occupation", "claim_id", "claim_text", "affected", "relevant"])
        writer.writerows(rows)
    print(f"wrote {OUTPUT.relative_to(PROJECT_ROOT)}: {len(picked)} occupations, {len(rows)} claims to judge")

    claims = [json.loads(line) for line in CLAIMS.open(encoding="utf-8") if line.strip()]
    with AUDIT_OUTPUT.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([*AUDIT_FIELDS, "claim_correct", "impact_type_correct", "direction_correct", "entity_correct", "note"])
        for claim in random.Random(SEED).sample(claims, AUDIT_SIZE):
            writer.writerow([*(claim.get(field, "") for field in AUDIT_FIELDS), "", "", "", "", ""])
    print(f"wrote {AUDIT_OUTPUT.relative_to(PROJECT_ROOT)}: {AUDIT_SIZE} claims to audit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

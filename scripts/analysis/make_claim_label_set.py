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

A later labelling round (ROADMAP 8.4), when new claims reach what the app shows, keeps those labels:

    python scripts/analysis/make_claim_label_set.py --round 2026_10 --claims-after claim_002673
      -> evaluation/claim_relevance_labels_2026_10.csv: the same 40 occupations, only the pairs not judged
         before, from the same pool (top 5 by each score) plus the claims the app shows them now;
         evaluation/claim_label_audit_2026_10.csv: 50 random claims among those after --claims-after.
"""

from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLAIMS_DB = PROJECT_ROOT / "data" / "duckdb" / "research_claims.duckdb"
ONET_DB = PROJECT_ROOT / "data" / "duckdb" / "onet.duckdb"
OUTPUT = PROJECT_ROOT / "evaluation" / "claim_relevance_labels.csv"
AUDIT_OUTPUT = PROJECT_ROOT / "evaluation" / "claim_label_audit.csv"
CLAIMS = PROJECT_ROOT / "data" / "research" / "ai_impact_claims.jsonl"
SHOWN = PROJECT_ROOT / "data" / "research" / "career_research_claims.csv"
AUDIT_SIZE = 50
AUDIT_FIELDS = [
    "claim_id", "evidence_quote", "claim_text", "impact_type_clean", "impact_direction_clean",
    "affected_entity_type", "affected_entity_text",
]
OCCUPATIONS = 40
TOP = 5
SEED = 2026


def add_round(name: str, claims_after: str) -> int:
    """A new labelling round: unjudged pairs for the already labelled occupations, and an audit of newer claims."""
    output = OUTPUT.with_name(f"{OUTPUT.stem}_{name}.csv")
    audit_output = AUDIT_OUTPUT.with_name(f"{AUDIT_OUTPUT.stem}_{name}.csv")
    for path in (output, audit_output):
        if path.exists():
            raise SystemExit(f"{path} exists; it may hold your labels. Move it away first.")
    judged = set()
    for path in sorted(OUTPUT.parent.glob(f"{OUTPUT.stem}*.csv")):  # June's labels and earlier rounds
        with path.open(encoding="utf-8", newline="") as file:
            judged |= {(row["onetsoc_code"], row["claim_id"]) for row in csv.DictReader(file)}
    with SHOWN.open(encoding="utf-8", newline="") as file:
        shown = {(row["onetsoc_code"], row["claim_id"]) for row in csv.DictReader(file)}
    con = duckdb.connect(str(CLAIMS_DB), read_only=True)
    con.execute(f"ATTACH '{ONET_DB.as_posix()}' AS onet (READ_ONLY)")
    rng = random.Random(SEED)
    rows = []
    for code in sorted({code for code, _ in judged}):
        candidates = con.execute(
            f"""
            SELECT o.title, c.claim_id, r.claim_text, r.affected_entity_text,
                   coalesce(c.rank_by_score <= {TOP} OR c.rank_by_centered <= {TOP}, false)
            FROM claim_candidates AS c
            JOIN research_claims AS r USING (claim_id)
            JOIN onet.occupation_data AS o USING (onetsoc_code)
            WHERE c.onetsoc_code = ?
            ORDER BY c.claim_id
            """,
            [code],
        ).fetchall()
        new = [row[:4] for row in candidates if (row[4] or (code, row[1]) in shown) and (code, row[1]) not in judged]
        rng.shuffle(new)
        rows += [[code, title, claim_id, text, entity, ""] for title, claim_id, text, entity in new]
    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["onetsoc_code", "occupation", "claim_id", "claim_text", "affected", "relevant"])
        writer.writerows(rows)
    print(f"wrote {output.relative_to(PROJECT_ROOT)}: {len({row[0] for row in rows})} occupations, {len(rows)} claims to judge")

    claims = [json.loads(line) for line in CLAIMS.open(encoding="utf-8") if line.strip()]
    newer = [claim for claim in claims if claim["claim_id"] > claims_after]
    with audit_output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([*AUDIT_FIELDS, "claim_correct", "impact_type_correct", "direction_correct", "entity_correct", "note"])
        for claim in random.Random(SEED).sample(newer, AUDIT_SIZE):
            writer.writerow([*(claim.get(field, "") for field in AUDIT_FIELDS), "", "", "", "", ""])
    print(f"wrote {audit_output.relative_to(PROJECT_ROOT)}: {AUDIT_SIZE} of the {len(newer)} claims after {claims_after}")
    return 0


def main() -> int:
    if "--round" in sys.argv:
        return add_round(sys.argv[sys.argv.index("--round") + 1], sys.argv[sys.argv.index("--claims-after") + 1])
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

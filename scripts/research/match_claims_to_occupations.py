#!/usr/bin/env python3
"""Find the research claims relevant to each O*NET occupation, at build time (ROADMAP 4.1, D15 = B).

Reads data/research/ai_impact_claims.jsonl (the claims pipeline's clean output) and
data/duckdb/onet.duckdb, and writes data/duckdb/research_claims.duckdb:
  research_claims     the claims shown to users, with quote, source and pages
  claim_candidates    per occupation, the top claims by two scores (ROADMAP 5.3 compares them),
                      plus every claim the relevance check already judged relevant for it (no rank):
                      otherwise more similar new claims push relevant ones out of the top (CHANGELOG 058)
                        score     cosine similarity of the occupation's query and the claim
                        centered  that score minus the claim's average over all occupations, so
                                  a claim that fits every career ("AI can do some subtasks")
                                  loses its advantage over one that fits this career
The app keeps candidates above a minimum score (set from the ROADMAP 5.3 evaluation).
Claims with the same text (several claim IDs) are listed once per occupation.

Eligible claims: about AI (not generator_use_scope = "exclude") and with a quote found
in the source as written (not quote_validation = "fuzzy_match"), since the app shows the
quote. Embeddings: BGE-small, normalized; queries get BGE's query prefix.

Since ROADMAP 10.8 a claim is matched on the text the app shows: a hand text, else the AI-link check's
rewrite (check_claim_ai_link.py), else the extracted text, so a rewrite that names the occupation finds it.
Claims that can never be shown are left out, so they don't take candidate places: hidden by hand, judged
not about AI's effect on work, or not standing on their own (unless a hand text fixed them).

    python scripts/research/match_claims_to_occupations.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from career_rag.config import BGE_QUERY_PREFIX, EMBEDDING_MODEL_NAME, ONET_DUCKDB_PATH  # noqa: E402
import check_claim_ai_link  # noqa: E402  (its verdicts and rewrites so far)
import check_claim_relevance  # noqa: E402  (its answers so far, for the candidates)
import check_claim_standalone  # noqa: E402  (its answers so far)

CLAIMS = PROJECT_ROOT / "data" / "research" / "ai_impact_claims.jsonl"
OUTPUT = PROJECT_ROOT / "data" / "duckdb" / "research_claims.duckdb"
TOP_K = 10
CLAIM_COLUMNS = [
    "claim_id", "claim_text", "evidence_quote", "impact_type_clean", "impact_direction_clean",
    "affected_entity_text", "title", "authors", "year", "final_url", "page_start", "page_end",
]


def eligible(claim: dict) -> bool:
    return claim.get("generator_use_scope") != "exclude" and claim.get("quote_validation") != "fuzzy_match"


def claim_text(claim: dict, shown: str | None = None) -> str:
    """What is embedded for a claim: the text the app shows (`shown`, else the claim) and whom it is about."""
    mentions = claim.get("occupation_or_skill_mentions") or ""
    return f"{shown or claim['claim_text']} Affected: {claim.get('affected_entity_text') or ''}. {mentions}".strip()


def shown_texts_and_unshowable(claims: list[dict]) -> tuple[dict[str, str], set[str]]:
    """({claim_id: the text the app shows}, {claim_ids that can never be shown}), from the checks so far."""
    corrections = check_claim_relevance.load_corrections()
    links = check_claim_ai_link.load_answers()
    standalone = check_claim_standalone.load_answers()
    shown, unshowable = {}, set()
    for claim in claims:
        claim_id, original = claim["claim_id"], claim["claim_text"]
        link = links.get((claim_id, original)) or {}
        correction = corrections.get(claim_id, {})
        shown[claim_id] = check_claim_relevance.shown_claim_text(claim_id, original, {claim_id: link}, corrections)
        if correction.get("show") == "no" or (not correction.get("claim_text") and (
                link.get("verdict") == "none" or standalone.get((claim_id, original)))):
            unshowable.add(claim_id)
    return shown, unshowable


def occupation_query(title: str, description: str) -> str:
    return f"{BGE_QUERY_PREFIX}How is AI changing the work of {title}? {description}"


def embed(texts: list[str]) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return model.encode(texts, batch_size=64, normalize_embeddings=True, show_progress_bar=False)


def main() -> int:
    claims = [json.loads(line) for line in CLAIMS.open(encoding="utf-8") if line.strip()]
    kept = [claim for claim in claims if eligible(claim)]
    shown, unshowable = shown_texts_and_unshowable(kept)
    kept = [claim for claim in kept if claim["claim_id"] not in unshowable]
    changed = sum(shown[claim["claim_id"]] != claim["claim_text"] for claim in kept)
    print(f"claims: {len(claims)}, eligible and showable: {len(kept)} ({len(unshowable)} can't be shown); "
          f"matched on a changed text: {changed}")

    onet = duckdb.connect(str(ONET_DUCKDB_PATH), read_only=True)
    occupations = onet.execute(
        """
        SELECT onetsoc_code, title, description FROM occupation_data
        WHERE onetsoc_code IN (SELECT DISTINCT onetsoc_code FROM task_statements)
        ORDER BY onetsoc_code
        """
    ).fetchall()
    onet.close()

    claim_vectors = embed([claim_text(claim, shown[claim["claim_id"]]) for claim in kept])
    query_vectors = embed([occupation_query(title, description) for _, title, description in occupations])
    scores = query_vectors @ claim_vectors.T  # cosine similarity, vectors are normalized
    claim_means = scores.mean(axis=0)
    centered = scores - claim_means

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT.exists():
        OUTPUT.unlink()  # a build output, rebuilt from the inputs above
    con = duckdb.connect(str(OUTPUT))
    con.execute(f"CREATE TABLE research_claims ({', '.join(f'{c} VARCHAR' for c in CLAIM_COLUMNS)})")
    con.executemany(
        f"INSERT INTO research_claims VALUES ({', '.join('?' for _ in CLAIM_COLUMNS)})",
        [[str(claim.get(c) or "") for c in CLAIM_COLUMNS] for claim in kept],
    )
    con.execute(
        "CREATE TABLE claim_candidates (onetsoc_code VARCHAR, claim_id VARCHAR, score DOUBLE, centered DOUBLE, "
        "rank_by_score INTEGER, rank_by_centered INTEGER)"
    )
    index = {claim["claim_id"]: j for j, claim in enumerate(kept)}
    corrections = check_claim_relevance.load_corrections()
    judged_relevant: dict[str, set[int]] = {}
    text_answers = check_claim_relevance.load_text_answers(check_claim_relevance.MODEL)
    for (code, claim_id), relevant in check_claim_relevance.load_answers(check_claim_relevance.MODEL).items():
        if claim_id in index and shown[claim_id] != kept[index[claim_id]]["claim_text"]:
            relevant = text_answers.get((code, claim_id, shown[claim_id]), relevant)  # judged on the shown text (10.7)
        if relevant and claim_id in index and not check_claim_relevance.hidden_for(claim_id, code, corrections):
            judged_relevant.setdefault(code, set()).add(index[claim_id])
    rows = []
    for i, (code, _, _) in enumerate(occupations):
        ranks = {}
        for kind, order in (("score", np.argsort(-scores[i])), ("centered", np.argsort(-centered[i]))):
            seen_texts: set[str] = set()
            for j in order:
                text = shown[kept[j]["claim_id"]]
                if text in seen_texts:
                    continue
                seen_texts.add(text)
                ranks.setdefault(j, {})[kind] = len(seen_texts)
                if len(seen_texts) == TOP_K:
                    break
        for j in judged_relevant.get(code, set()) - ranks.keys():
            ranks[j] = {}
        for j, rank in ranks.items():
            rows.append((code, kept[j]["claim_id"], float(scores[i, j]), float(centered[i, j]), rank.get("score"), rank.get("centered")))
    con.executemany("INSERT INTO claim_candidates VALUES (?, ?, ?, ?, ?, ?)", rows)
    np.save(OUTPUT.with_suffix(".claim_vectors.npy"), claim_vectors)  # for the 5.3 evaluation
    np.save(OUTPUT.with_suffix(".claim_means.npy"), claim_means)  # to center a new query's scores
    print(f"occupations: {len(occupations)}; candidates stored: {len(rows)}")
    print(f"top-1 score range: {scores.max(axis=1).min():.3f} .. {scores.max(axis=1).max():.3f}")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

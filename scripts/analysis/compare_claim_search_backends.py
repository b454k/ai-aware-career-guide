#!/usr/bin/env python3
"""Chroma vs. exact NumPy search on the same claim embeddings (decision D6, ROADMAP 5.3).

Both rank claims by cosine similarity to each occupation's query; NumPy computes it exactly,
Chroma's HNSW index approximates it. Reports how much of NumPy's top 10 Chroma returns.
Needs data/duckdb/research_claims.duckdb and its .claim_vectors.npy
(scripts/research/match_claims_to_occupations.py) and requirements-dev.txt.

    python scripts/analysis/compare_claim_search_backends.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import chromadb
import duckdb
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "research"))

import match_claims_to_occupations as build  # noqa: E402
from career_rag.embeddings import embed_queries  # noqa: E402

K = 10


def main() -> int:
    vectors = np.load(build.OUTPUT.with_suffix(".claim_vectors.npy"))
    occupations = duckdb.connect(str(build.ONET_DUCKDB_PATH), read_only=True).execute(
        "SELECT onetsoc_code, title, description FROM occupation_data "
        "WHERE onetsoc_code IN (SELECT DISTINCT onetsoc_code FROM task_statements) ORDER BY 1"
    ).fetchall()
    queries = embed_queries([build.occupation_query(title, description) for _, title, description in occupations],
                            build.QUERY_INSTRUCTION)

    start = time.perf_counter()
    exact = np.argsort(-(queries @ vectors.T), axis=1)[:, :K].tolist()
    numpy_ms = (time.perf_counter() - start) * 1000

    collection = chromadb.EphemeralClient().create_collection("claims", metadata={"hnsw:space": "cosine"})
    for start_row in range(0, len(vectors), 1000):
        rows = range(start_row, min(start_row + 1000, len(vectors)))
        collection.add(ids=[str(i) for i in rows], embeddings=vectors[rows.start : rows.stop].tolist())
    start = time.perf_counter()
    result = collection.query(query_embeddings=queries.tolist(), n_results=K)
    chroma_ms = (time.perf_counter() - start) * 1000
    approx = [[int(i) for i in ids] for ids in result["ids"]]

    recall = [len(set(a) & set(e)) / K for a, e in zip(approx, exact)]
    identical = sum(a == e for a, e in zip(approx, exact))
    print(json.dumps({
        "occupations": len(occupations), "claims": len(vectors), "k": K,
        "chroma_recall_of_exact_top_k_mean": round(float(np.mean(recall)), 4),
        "chroma_recall_min": min(recall),
        "identical_lists": identical,
        "numpy_ms_all_queries": round(numpy_ms), "chroma_ms_all_queries": round(chroma_ms),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

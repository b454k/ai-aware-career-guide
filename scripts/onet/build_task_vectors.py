#!/usr/bin/env python3
"""Embed every O*NET task statement for the follow-up ranker's meaning match (CHANGELOG 104).

Each career's tasks are embedded with the local embedding model (career_rag/embeddings.py); the ranker compares
a student's answers with them. About 40 minutes on a laptop CPU for the 18,838 tasks.

Output, not committed (built): data/duckdb/onet_task_vectors.npz with `codes` and `task_ids` (one per row) and
`vectors` (float16, normalized).

    python scripts/onet/build_task_vectors.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import duckdb
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from career_rag.config import ONET_DUCKDB_PATH, TASK_VECTORS_PATH  # noqa: E402
from career_rag.embeddings import embed_documents  # noqa: E402

CHUNK = 512


def main() -> int:
    conn = duckdb.connect(str(ONET_DUCKDB_PATH), read_only=True)
    try:
        rows = conn.execute("SELECT onetsoc_code, task_id, task FROM task_statements ORDER BY onetsoc_code, task_id").fetchall()
    finally:
        conn.close()
    started = time.time()
    parts = []
    for start in range(0, len(rows), CHUNK):
        parts.append(embed_documents([task for _, _, task in rows[start:start + CHUNK]]).astype(np.float16))
        done = min(start + CHUNK, len(rows))
        print(f"{done:,} of {len(rows):,} tasks, {time.time() - started:.0f} s", flush=True)
    TASK_VECTORS_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez(TASK_VECTORS_PATH, codes=np.array([code for code, _, _ in rows]),
             task_ids=np.array([str(task_id) for _, task_id, _ in rows]), vectors=np.vstack(parts))
    print(f"wrote {TASK_VECTORS_PATH.relative_to(PROJECT_ROOT)}: {len(rows):,} tasks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

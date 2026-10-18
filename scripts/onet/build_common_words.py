#!/usr/bin/env python3
"""The words too common in O*NET to tell careers apart, for the follow-up ranker's word overlap.

The ranker compares a student's answers word by word with each career's skills and knowledge areas (its tasks by
meaning since CHANGELOG 104). Some words appear in nearly every career's list, because every career is rated on
O*NET's same standard skills ("Reading Comprehension", "Mathematics"), so sharing them told the ranker nothing and
gave most careers the same score. A word is listed for a part when it
appears in that part's text of at least COMMON_SHARE of the careers; the ranker then ignores it in that part.

Output, committed: data/ranker/common_words.csv (part, word, share of careers).

    python scripts/onet/build_common_words.py
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import duckdb  # noqa: E402

from career_rag.config import ONET_DUCKDB_PATH, RANKER_COMMON_WORDS_PATH  # noqa: E402
from career_rag.ip_refinement_ranker import RANKER_PARTS, _occupation_signal_bundle, _tokens  # noqa: E402

COMMON_SHARE = 0.25  # in at least a quarter of the careers


def main() -> int:
    conn = duckdb.connect(str(ONET_DUCKDB_PATH), read_only=True)
    try:
        codes = [code for (code,) in conn.execute("SELECT DISTINCT onetsoc_code FROM task_statements").fetchall()]
        counts = {part: Counter() for part in RANKER_PARTS}
        for code in codes:
            bundle = _occupation_signal_bundle(conn, code)
            for part, keys in RANKER_PARTS.items():
                counts[part].update(set().union(*(_tokens(text) for key in keys for text in bundle.get(key, []))))
    finally:
        conn.close()
    rows = [(part, word, round(count / len(codes), 3)) for part, counter in counts.items()
            for word, count in counter.most_common() if count / len(codes) >= COMMON_SHARE]
    RANKER_COMMON_WORDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RANKER_COMMON_WORDS_PATH.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["part", "word", "share_of_careers"])
        writer.writerows(rows)
    summary = ", ".join(f"{part} {sum(1 for row in rows if row[0] == part)} of {len(counts[part])}" for part in counts)
    print(f"wrote {RANKER_COMMON_WORDS_PATH.relative_to(PROJECT_ROOT)}: common words in {len(codes)} careers' texts: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

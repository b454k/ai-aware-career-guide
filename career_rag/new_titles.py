"""New job titles (2026 onward) and their closest O*NET roles (ROADMAP 6.6), shown under those roles (10.2).

Titles like "prompt engineer" have no O*NET occupation of their own. data/new_titles/new_job_titles.csv
lists each with its closest O*NET roles: O*NET's own listing where it has the title ("O*NET"), the same
with roles that don't fit the usual job left out or replaced ("O*NET, adjusted"), or chosen by hand
where O*NET doesn't have it ("proposed"). The list was reviewed by hand (CHANGELOG 063).
"""

from __future__ import annotations

import csv
from functools import lru_cache

from career_rag.config import NEW_TITLES_PATH

SOURCE_KEYS = {"O*NET": "onet", "O*NET, adjusted": "adjusted", "proposed": "proposed"}


@lru_cache(maxsize=1)
def load_new_titles() -> tuple[dict[str, str], ...]:
    with NEW_TITLES_PATH.open(encoding="utf-8", newline="") as handle:
        return tuple(csv.DictReader(handle))


def title_label(row: dict[str, str], language: str = "en") -> str:
    return row["title_tr"] if language == "tr" else row["title_en"]


def titles_for_career(onet_soc_code: str) -> list[dict[str, str]]:
    """The new titles whose closest O*NET occupations include this one, shown in its career detail (ROADMAP 10.2)."""
    return [row for row in load_new_titles() if onet_soc_code in row["onet_codes"].split(";")]

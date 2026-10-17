"""Turkish university departments and the O*NET careers they lead to (ROADMAP 9.1).

data/departments/departments.csv lists each department with its US fields of study (CIP 2020);
data/departments/department_careers.csv, built from NCES's CIP-to-SOC crosswalk and reviewed by hand,
lists the careers. A student who picks a department gets its careers, ranked by interest fit.
"""

from __future__ import annotations

import csv
from functools import lru_cache

from career_rag.config import DEPARTMENT_CAREERS_PATH, DEPARTMENTS_PATH

# A university department leads to a bachelor's degree: O*NET's Job Zone 4. The follow-up questions and
# their ranker still read Job Zones, so a department profile carries this one.
DEPARTMENT_JOB_ZONE = 4


@lru_cache(maxsize=1)
def load_departments() -> tuple[dict[str, str], ...]:
    with DEPARTMENTS_PATH.open(encoding="utf-8", newline="") as handle:
        return tuple(csv.DictReader(handle))


@lru_cache(maxsize=1)
def _codes_by_department() -> dict[str, tuple[str, ...]]:
    codes: dict[str, list[str]] = {}
    with DEPARTMENT_CAREERS_PATH.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            codes.setdefault(row["name_tr"], []).append(row["onetsoc_code"])
    return {name: tuple(values) for name, values in codes.items()}


def department_codes(name_tr: str) -> tuple[str, ...]:
    """The O*NET codes of a department's careers (empty if the department is unknown)."""
    return _codes_by_department().get(name_tr, ())


def department_label(name_tr: str, language: str = "en") -> str:
    row = next((row for row in load_departments() if row["name_tr"] == name_tr), None)
    if row is None:
        return name_tr
    return row["name_tr"] if language == "tr" else row["name_en"]

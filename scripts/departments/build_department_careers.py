#!/usr/bin/env python3
"""Link Turkish university departments to O*NET careers (ROADMAP 9.1).

  data/departments/departments.csv     each department's US fields of study (CIP 2020), chosen by hand and reviewed
  NCES CIP 2020 -> SOC 2018 crosswalk  the occupations each field of study leads to (official; expert-made, not empirical)
  O*NET                                every O*NET career within those SOC occupations that has task data

A SOC occupation can cover several O*NET careers, e.g. SOC 11-9121 is Natural Sciences Managers, but also
Clinical Research Coordinators and Water Resource Specialists. Such specialties are flagged, and the ones that
don't fit a department are listed in data/departments/department_career_exclusions.csv (reviewed by hand).

    python scripts/departments/build_department_careers.py
      -> data/departments/department_careers.csv (committed): one row per department and career
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import duckdb
import openpyxl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from career_rag.config import ONET_DUCKDB_PATH  # noqa: E402

DEPARTMENTS = PROJECT_ROOT / "data" / "departments" / "departments.csv"
EXCLUSIONS = PROJECT_ROOT / "data" / "departments" / "department_career_exclusions.csv"
OUTPUT = PROJECT_ROOT / "data" / "departments" / "department_careers.csv"
CROSSWALK = PROJECT_ROOT / "data" / "crosswalks" / "CIP2020_SOC2018_Crosswalk.xlsx"


def main() -> int:
    socs_by_cip: dict[str, set[str]] = defaultdict(set)
    sheet = openpyxl.load_workbook(CROSSWALK, read_only=True)["CIP-SOC"]
    for cip, _, soc, _ in list(sheet.iter_rows(values_only=True))[1:]:
        if soc != "99-9999":
            socs_by_cip[cip].add(soc)
    con = duckdb.connect(str(ONET_DUCKDB_PATH), read_only=True)
    careers = con.execute(
        "SELECT onetsoc_code, title FROM occupation_data "
        "WHERE onetsoc_code IN (SELECT DISTINCT onetsoc_code FROM task_statements) ORDER BY onetsoc_code"
    ).fetchall()
    con.close()
    careers_by_soc: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for code, title in careers:
        careers_by_soc[code[:7]].append((code, title))
    excluded = set()
    if EXCLUSIONS.exists():
        with EXCLUSIONS.open(encoding="utf-8", newline="") as handle:
            excluded = {(row["name_tr"], row["onetsoc_code"]) for row in csv.DictReader(handle)}

    rows, unused = [], set(excluded)
    with DEPARTMENTS.open(encoding="utf-8", newline="") as handle:
        departments = list(csv.DictReader(handle))
    for department in departments:
        seen = set()
        for cip in department["cip_codes"].split(";"):
            for soc in sorted(socs_by_cip[cip]):
                group = careers_by_soc.get(soc, [])
                for code, title in group:
                    key = (department["name_tr"], code)
                    if code in seen:
                        continue
                    seen.add(code)
                    if key in excluded:
                        unused.discard(key)
                        continue
                    # a specialty (not .00) next to its SOC's general career: is it about this field?
                    specialty = not code.endswith(".00") and len(group) > 1
                    rows.append([department["name_tr"], code, title, cip, soc, "specialty" if specialty else ""])
    if unused:
        sys.exit(f"exclusions that match nothing (renamed department or code?): {sorted(unused)[:5]}")
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["name_tr", "onetsoc_code", "title", "via_cip", "via_soc", "flag"])
        writer.writerows(rows)
    per_department = defaultdict(int)
    for row in rows:
        per_department[row[0]] += 1
    empty = [d["name_tr"] for d in departments if not per_department[d["name_tr"]]]
    print(f"wrote {OUTPUT.relative_to(PROJECT_ROOT)}: {len(rows)} links, {len(departments)} departments, "
          f"{sum(1 for r in rows if r[5])} specialties flagged; careers per department "
          f"{min(per_department.values())}-{max(per_department.values())}; without careers: {empty}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

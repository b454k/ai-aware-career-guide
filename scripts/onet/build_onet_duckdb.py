#!/usr/bin/env python3
"""Build the O*NET DuckDB database from O*NET's tab-delimited text release (ROADMAP 3.1).

Download e.g. db_31_0_text.zip from https://www.onetcenter.org/db_releases.html (CC BY 4.0),
unzip it, then:

    python scripts/onet/build_onet_duckdb.py data/onet/db_31_0_text data/duckdb/onet_31_0.duckdb
    python scripts/onet/build_onet_duckdb.py --compare data/duckdb/onet.duckdb data/duckdb/onet_31_0.duckdb

One table per .txt file. Table and column names follow O*NET's own SQL release
("Occupation Data.txt" -> occupation_data, "O*NET-SOC Code" -> onetsoc_code), "n/a" becomes
NULL and "08/2023" becomes the date 2023-08-01, as in the SQL release. The text files also
carry readable name columns (e.g. element_name next to element_id) that the SQL release
leaves out; they are kept.
--compare prints, per table, the row counts and how many rows differ, so an update
(e.g. 30.3 -> 31.0) is visible before it replaces the database the app reads.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import duckdb

# Where a header does not simply lower-case to O*NET's SQL column name.
COLUMN_EXCEPTIONS = {"Date": "date_updated", "Source(s)": "sources", "Index": "related_index"}


def sql_name(text: str) -> str:
    """ "O*NET-SOC Code" -> "onetsoc_code", "Abilities to Work Activities" -> "abilities_to_work_activities"."""
    text = text.replace("O*NET-SOC", "ONETSOC")
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def build(text_dir: Path, output: Path) -> None:
    files = sorted(text_dir.glob("*.txt"))
    files = [path for path in files if path.name.lower() != "read me.txt"]
    if not files:
        sys.exit(f"No O*NET .txt files in {text_dir}")
    if output.exists():
        sys.exit(f"{output} exists; choose a new file so the current database stays untouched")
    output.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(output))
    for path in files:
        source = (
            f"read_csv('{path.as_posix()}', delim='\\t', header=true, quote='', escape='', "
            "nullstr='n/a', sample_size=-1)"
        )
        headers = [row[0] for row in con.execute(f"DESCRIBE SELECT * FROM {source}").fetchall()]
        columns = ", ".join(
            f"strptime(\"{header}\", '%m/%Y')::DATE AS date_updated" if header == "Date"
            else f'"{header}" AS {COLUMN_EXCEPTIONS.get(header, sql_name(header))}'
            for header in headers
        )
        table = sql_name(path.stem)
        con.execute(f"CREATE TABLE {table} AS SELECT {columns} FROM {source}")
        print(f"{table}: {con.execute(f'SELECT count(*) FROM {table}').fetchone()[0]} rows")
    con.close()


def compare(old_path: Path, new_path: Path) -> None:
    con = duckdb.connect()
    con.execute(f"ATTACH '{old_path.as_posix()}' AS old (READ_ONLY)")
    con.execute(f"ATTACH '{new_path.as_posix()}' AS new (READ_ONLY)")

    def tables(db: str) -> set[str]:
        return {row[0] for row in con.execute(f"SELECT table_name FROM information_schema.tables WHERE table_catalog = '{db}'").fetchall()}

    def columns(db: str, table: str) -> dict[str, str]:
        return {row[0]: row[1] for row in con.execute(f"DESCRIBE {db}.{table}").fetchall()}

    def is_number(column_type: str) -> bool:
        return column_type.startswith(("DECIMAL", "DOUBLE", "FLOAT", "BIGINT", "INTEGER", "SMALLINT", "TINYINT"))

    old_tables, new_tables = tables("old"), tables("new")
    print(f"only in old: {sorted(old_tables - new_tables)}\nonly in new: {sorted(new_tables - old_tables)}")
    print("table | old rows | new rows | rows only in old | rows only in new | column differences")
    for table in sorted(old_tables & new_tables):
        old_columns, new_columns = columns("old", table), columns("new", table)
        shared = [column for column in old_columns if column in new_columns]
        # Numbers compare as numbers (the SQL release has DECIMAL(5,2), the text import DOUBLE), the rest as text.
        select = ", ".join(
            f"CAST({column} AS DOUBLE)" if is_number(old_columns[column]) and is_number(new_columns[column])
            else f"CAST({column} AS VARCHAR)"
            for column in shared
        )
        old_rows, new_rows = (con.execute(f"SELECT count(*) FROM {db}.{table}").fetchone()[0] for db in ("old", "new"))
        only_old = con.execute(f"SELECT count(*) FROM (SELECT {select} FROM old.{table} EXCEPT ALL SELECT {select} FROM new.{table})").fetchone()[0]
        only_new = con.execute(f"SELECT count(*) FROM (SELECT {select} FROM new.{table} EXCEPT ALL SELECT {select} FROM old.{table})").fetchone()[0]
        column_note = "" if list(old_columns) == list(new_columns) else f"old {list(old_columns)} / new {list(new_columns)}"
        print(f"{table} | {old_rows} | {new_rows} | {only_old} | {only_new} | {column_note}")


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--compare":
        compare(Path(sys.argv[2]), Path(sys.argv[3]))
    elif len(sys.argv) == 3:
        build(Path(sys.argv[1]), Path(sys.argv[2]))
    else:
        sys.exit(__doc__)

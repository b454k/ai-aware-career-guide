#!/usr/bin/env python3
"""Diagnostics for the local O*NET DuckDB database.

This script only reads existing project artifacts unless a report output path is
explicitly requested. It replaces the older one-off check/inspect/test scripts.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "duckdb" / "onet.duckdb"

SUPPLEMENTAL_TABLES = [
    "gwas_to_iwas",
    "gwas_to_iwas_to_dwas",
    "tasks_to_dwas",
    "emerging_tasks",
    "related_occupations",
    "job_titles",
    "sample_of_reported_titles",
    "abilities_to_work_activities",
    "abilities_to_work_context",
    "essential_skills_to_work_activities",
    "essential_skills_to_work_context",
    "transferable_skills_to_work_activities",
    "transferable_skills_to_work_context",
    "work_styles_to_work_activities",
    "work_styles_to_work_context",
]


def main() -> int:
    """Run the requested diagnostic command."""
    parser = build_parser()
    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    try:
        return int(args.func(args) or 0)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")

    add_simple_command(subparsers, "tables", "List DuckDB tables.", list_tables)

    schema_parser = add_simple_command(
        subparsers,
        "schema",
        "Print or save DuckDB schema details.",
        inspect_schema,
    )
    schema_parser.add_argument("--output", type=Path, default=None)

    supplemental_parser = add_simple_command(
        subparsers,
        "supplemental-schema",
        "Inspect supplemental O*NET tables.",
        inspect_supplemental_schema,
    )
    supplemental_parser.add_argument("--output", type=Path, default=None)

    occupation_parser = add_simple_command(
        subparsers,
        "occupation",
        "Explore major O*NET tables for one occupation.",
        explore_occupation,
    )
    occupation_parser.add_argument("--code", default="11-2021.00")
    occupation_parser.add_argument("--limit", type=int, default=20)

    codes_parser = add_simple_command(
        subparsers,
        "codes",
        "Show occupation codes with broad table coverage.",
        check_codes,
    )
    codes_parser.add_argument("--limit", type=int, default=30)

    return parser


def add_simple_command(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    name: str,
    help_text: str,
    func: Any,
) -> argparse.ArgumentParser:
    """Register one subcommand."""
    parser = subparsers.add_parser(name, help=help_text, description=help_text)
    parser.set_defaults(func=func)
    return parser


def connect_duckdb(read_only: bool = True) -> duckdb.DuckDBPyConnection:
    """Connect to the existing O*NET DuckDB database."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"DuckDB database not found: {DB_PATH}")
    return duckdb.connect(str(DB_PATH), read_only=read_only)


def quote_identifier(identifier: str) -> str:
    """Quote a DuckDB identifier safely."""
    return '"' + identifier.replace('"', '""') + '"'


def list_tables(_args: argparse.Namespace) -> int:
    """List DuckDB tables."""
    with connect_duckdb() as conn:
        tables = [row[0] for row in conn.execute("SHOW TABLES").fetchall()]
    print("Tables:")
    for table in tables:
        print(f"  {table}")
    return 0


def inspect_schema(args: argparse.Namespace) -> int:
    """Print or save the DuckDB schema."""
    with connect_duckdb() as conn:
        lines = build_schema_report(conn, None)
    emit_report(lines, args.output)
    return 0


def inspect_supplemental_schema(args: argparse.Namespace) -> int:
    """Print or save schema and samples for supplemental tables."""
    with connect_duckdb() as conn:
        lines = [
            "O*NET Supplemental Tables Schema Report",
            f"Timestamp: {datetime.now().isoformat(timespec='seconds')}",
            f"Database: {DB_PATH}",
        ]
        existing_tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
        for table in SUPPLEMENTAL_TABLES:
            if table in existing_tables:
                lines.extend(build_schema_report(conn, [table], sample_rows=5))
            else:
                lines.extend(["", f"TABLE: {table}", "  Missing, not inspected."])

    emit_report(lines, args.output)
    return 0


def build_schema_report(
    conn: duckdb.DuckDBPyConnection,
    tables: list[str] | None,
    sample_rows: int = 0,
) -> list[str]:
    """Build schema lines for selected tables or all tables."""
    if tables is None:
        tables = [row[0] for row in conn.execute("SHOW TABLES").fetchall()]

    lines: list[str] = []
    for table in tables:
        quoted = quote_identifier(table)
        lines.extend(["", "=" * 80, f"TABLE: {table}", "=" * 80])
        count = conn.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0]
        lines.append(f"Rows: {count:,}")
        lines.append("Columns:")
        for column in conn.execute(f"DESCRIBE {quoted}").fetchall():
            lines.append(f"  - {column[0]}: {column[1]}")
        if sample_rows:
            lines.append(f"First {sample_rows} rows:")
            rows = conn.execute(f"SELECT * FROM {quoted} LIMIT {sample_rows}").fetchall()
            if rows:
                for row in rows:
                    lines.append("  " + " | ".join("" if value is None else str(value) for value in row))
            else:
                lines.append("  (no rows)")
    return lines


def emit_report(lines: list[str], output: Path | None) -> None:
    """Print a report and optionally write it to disk."""
    text = "\n".join(lines).strip() + "\n"
    print(text)
    if output:
        output = output if output.is_absolute() else PROJECT_ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        print(f"Report saved to {output}")


def explore_occupation(args: argparse.Namespace) -> int:
    """Explore major O*NET tables for one occupation."""
    code = args.code.strip()
    if not code:
        raise ValueError("--code must not be empty")

    with connect_duckdb() as conn:
        title = conn.execute(
            "SELECT title FROM occupation_data WHERE onetsoc_code = ?",
            [code],
        ).fetchone()
        print("=" * 80)
        print(f"O*NET DATABASE EXPLORATION FOR {code}")
        print("=" * 80)
        print(f"Title: {title[0] if title else 'N/A'}")

        for table, label, order_scale in [
            ("essential_skills", "ESSENTIAL SKILLS", "IM"),
            ("transferable_skills", "TRANSFERABLE SKILLS", "IM"),
            ("knowledge", "KNOWLEDGE AREAS", "IM"),
            ("abilities", "ABILITIES", "IM"),
            ("work_activities", "WORK ACTIVITIES", "IM"),
            ("work_styles", "WORK STYLES", None),
        ]:
            print_ranked_content_model(conn, table, label, code, args.limit, order_scale)

        print_work_context(conn, code, args.limit)

    return 0


def print_ranked_content_model(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    label: str,
    code: str,
    limit: int,
    scale_id: str | None,
) -> None:
    """Print ranked content-model rows for one occupation."""
    where = "WHERE source.onetsoc_code = ?"
    params: list[Any] = [code]
    if scale_id:
        where += " AND source.scale_id = ?"
        params.append(scale_id)
    params.append(limit)

    query = f"""
        SELECT source.element_id, cmr.element_name, source.data_value, source.scale_id
        FROM {quote_identifier(table)} source
        JOIN content_model_reference cmr ON source.element_id = cmr.element_id
        {where}
        ORDER BY source.data_value DESC
        LIMIT ?
    """
    rows = conn.execute(query, params).fetchall()
    print_section_rows(label, ["element_id", "element_name", "data_value", "scale_id"], rows)


def print_work_context(conn: duckdb.DuckDBPyConnection, code: str, limit: int) -> None:
    """Print ranked work-context rows for one occupation."""
    rows = conn.execute(
        """
        SELECT wc.element_id, cmr.element_name, wc.data_value, wc.scale_id,
               wc.category, wcc.category_description
        FROM work_context wc
        JOIN content_model_reference cmr ON wc.element_id = cmr.element_id
        LEFT JOIN work_context_categories wcc
          ON wc.element_id = wcc.element_id
         AND wc.scale_id = wcc.scale_id
         AND wc.category = wcc.category
        WHERE wc.onetsoc_code = ?
        ORDER BY wc.data_value DESC
        LIMIT ?
        """,
        [code, limit],
    ).fetchall()
    print_section_rows(
        "WORK CONTEXT ITEMS",
        ["element_id", "element_name", "data_value", "scale_id", "category", "description"],
        rows,
    )


def print_section_rows(label: str, headers: list[str], rows: list[tuple[Any, ...]]) -> None:
    """Print a small table-like section."""
    print("\n" + label)
    print("-" * 80)
    print(" | ".join(headers))
    for row in rows:
        print(" | ".join("" if value is None else str(value) for value in row))
    if not rows:
        print("(no rows)")


def check_codes(args: argparse.Namespace) -> int:
    """Show occupation codes and broad table coverage."""
    tables = [
        "essential_skills",
        "transferable_skills",
        "knowledge",
        "abilities",
        "work_activities",
        "work_styles",
        "work_context",
    ]
    with connect_duckdb() as conn:
        print("First occupation codes:")
        for row in conn.execute(
            "SELECT onetsoc_code, title FROM occupation_data ORDER BY onetsoc_code LIMIT 5"
        ).fetchall():
            print(f"  {row[0]} | {row[1]}")

        codes = conn.execute(
            "SELECT DISTINCT onetsoc_code FROM occupation_data LIMIT ?",
            [args.limit],
        ).fetchall()
        best_code = None
        best_count = 0
        print("\nOccupation data coverage:")
        for (code,) in codes:
            counts = {
                table: conn.execute(
                    f"SELECT COUNT(*) FROM {quote_identifier(table)} WHERE onetsoc_code = ?",
                    [code],
                ).fetchone()[0]
                for table in tables
            }
            coverage_count = sum(1 for count in counts.values() if count > 0)
            if coverage_count >= 5:
                print(f"\n{code}:")
                for table, count in counts.items():
                    print(f"  {table}: {count}")
            if coverage_count > best_count:
                best_count = coverage_count
                best_code = code
        print(f"\nBest occupation code with broad data coverage: {best_code}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

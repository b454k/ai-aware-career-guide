#!/usr/bin/env python3
"""Build or rebuild the local artifacts needed by the Career RAG app."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ONET_TEXT_DIR = PROJECT_ROOT / "data" / "onet" / "db_31_0" / "db_31_0_text"
ONET_DUCKDB = PROJECT_ROOT / "data" / "duckdb" / "onet.duckdb"


def run_step(label: str, args: list[str], env: dict[str, str] | None = None) -> None:
    """Run one build step and stop with a clear message on failure."""
    print("\n" + "=" * 100)
    print(f"STEP: {label}")
    print("=" * 100)
    print("Command: " + " ".join(args))

    step_env = os.environ.copy()
    step_env["PYTHONPATH"] = str(PROJECT_ROOT)
    if env:
        step_env.update(env)

    completed = subprocess.run(
        args,
        cwd=PROJECT_ROOT,
        env=step_env,
        check=False,
    )
    if completed.returncode != 0:
        print(f"FAILED: {label} (exit code {completed.returncode})", file=sys.stderr)
        raise SystemExit(completed.returncode)
    print(f"SUCCESS: {label}")


def script(path: str) -> list[str]:
    return [sys.executable, path]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-onet",
        action="store_true",
        help="Skip building data/duckdb/onet.duckdb.",
    )
    parser.add_argument(
        "--skip-ai-impact",
        action="store_true",
        help="Skip the Anthropic AI-impact steps.",
    )
    parser.add_argument(
        "--skip-research-claims",
        action="store_true",
        help="Skip research claim Chroma embedding.",
    )
    parser.add_argument(
        "--skip-smoke-test",
        action="store_true",
        help="Do not run scripts/check_artifacts.py at the end.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.skip_onet:
        if ONET_DUCKDB.exists():
            print(f"O*NET database already exists, not rebuilt: {ONET_DUCKDB.relative_to(PROJECT_ROOT)}")
        else:
            # O*NET 31.0 text release, unzipped (https://www.onetcenter.org/db_releases.html).
            run_step(
                "Build O*NET DuckDB database from O*NET's text files",
                script("scripts/onet/build_onet_duckdb.py") + [str(ONET_TEXT_DIR), str(ONET_DUCKDB)],
            )

    if not args.skip_ai_impact:
        run_step(
            "Extract the 2026 Anthropic Economic Index release",
            script("scripts/ai_impact/build_aei_release.py") + ["release_2026_06_26"],
        )
        run_step(
            "Build the AI-impact DuckDB database",
            script("scripts/ai_impact/build_ai_impact_duckdb.py"),
        )

    if not args.skip_research_claims:
        run_step(
            "Build research claim Chroma collection",
            script("scripts/research/embed_ai_impact_claims.py"),
        )

    if not args.skip_smoke_test:
        run_step("Run artifact smoke checks", script("scripts/check_artifacts.py"))

    print("\nAll requested artifact build steps completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

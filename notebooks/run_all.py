#!/usr/bin/env python3
"""Run notebooks top to bottom and save their outputs (ROADMAP 5.1).

A notebook is committed only after this runs it cleanly, so the outputs in git are the
ones its code produces now. Timing metadata is not recorded, so a rerun with unchanged
results leaves the file unchanged.

    python notebooks/run_all.py                 # every notebooks/*.ipynb
    python notebooks/run_all.py 54_ai_coverage  # only the named ones
"""

from __future__ import annotations

import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

NOTEBOOKS = Path(__file__).resolve().parent


def main() -> int:
    names = sys.argv[1:]
    paths = [NOTEBOOKS / f"{name}.ipynb" for name in names] if names else sorted(NOTEBOOKS.glob("*.ipynb"))
    for path in paths:
        notebook = nbformat.read(path, as_version=4)
        NotebookClient(
            notebook, timeout=600, kernel_name="python3", record_timing=False,
            resources={"metadata": {"path": str(NOTEBOOKS)}},
        ).execute()
        nbformat.write(notebook, path)
        print(f"ran {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

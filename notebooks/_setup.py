"""First cell of every notebook (ROADMAP 5.1):

    import _setup
    _setup.setup()

Puts the project root on sys.path and makes it the working directory, so imports and
relative paths work as in the scripts; turns on autoreload, so edits to career_rag/ are
picked up without restarting the kernel; and switches the OpenAI LLM off unless a
notebook passes llm=True, so results don't depend on (or pay for) an LLM by accident.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def setup(llm: bool = False) -> None:
    if not llm:
        os.environ["OPENAI_API_KEY"] = ""  # set before any .env load; load_dotenv never overrides it
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    os.chdir(PROJECT_ROOT)
    from IPython import get_ipython

    shell = get_ipython()
    if shell is not None:
        shell.run_line_magic("load_ext", "autoreload")
        shell.run_line_magic("autoreload", "2")

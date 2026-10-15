"""Shared configuration constants for the Career RAG project."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"


def _path_from_env(name: str, default: Path) -> Path:
    """Return an absolute path from an env var or a project-relative default."""
    value = os.getenv(name)
    path = Path(value).expanduser() if value else default
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


DATA_DIR = _path_from_env("CAREER_RAG_DATA_DIR", PROJECT_ROOT / "data")
ONET_INTEREST_PROFILER_DIR = _path_from_env(
    "CAREER_RAG_IP_DIR",
    PROJECT_ROOT / "onet_interest_profiler",
)

RESEARCH_DIR = _path_from_env("CAREER_RAG_RESEARCH_DIR", DATA_DIR / "research")

ONET_DUCKDB_PATH = _path_from_env(
    "ONET_DUCKDB_PATH",
    DATA_DIR / "duckdb" / "onet.duckdb",
)
# Built by scripts/ai_impact/build_ai_impact_duckdb.py (ROADMAP 3.2): Anthropic task coverage,
# observed exposure and the 2026 Claude usage extract.
AI_IMPACT_DUCKDB_PATH = _path_from_env(
    "AI_IMPACT_DUCKDB_PATH",
    DATA_DIR / "duckdb" / "ai_impact.duckdb",
)
# Written by scripts/research/check_claim_relevance.py (ROADMAP 4.1c) and committed (D17 = B):
# the research claims each occupation shows, at most 3.
RESEARCH_CLAIMS_PATH = _path_from_env(
    "RESEARCH_CLAIMS_PATH",
    DATA_DIR / "research" / "career_research_claims.csv",
)
# Written by scripts/i18n/translate_content.py (ROADMAP 6.1c) and committed: O*NET content and
# research claims in Turkish, translated once at build time (D8 = B).
CONTENT_TRANSLATIONS_PATH = _path_from_env(
    "CONTENT_TRANSLATIONS_PATH",
    DATA_DIR / "i18n" / "content_tr.csv",
)
PROFILE_RESULT_PATH = _path_from_env(
    "PROFILE_RESULT_PATH",
    ONET_INTEREST_PROFILER_DIR / "ip_profile_result.json",
)
QUESTIONS_PATH = _path_from_env(
    "QUESTIONS_PATH",
    ONET_INTEREST_PROFILER_DIR / "interest_profiler_questions.json",
)
FINAL_REPORT_JSON_PATH = _path_from_env(
    "FINAL_REPORT_JSON_PATH",
    ONET_INTEREST_PROFILER_DIR / "ip_final_career_report.json",
)
FINAL_REPORT_MD_PATH = _path_from_env(
    "FINAL_REPORT_MD_PATH",
    ONET_INTEREST_PROFILER_DIR / "ip_final_career_report.md",
)

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

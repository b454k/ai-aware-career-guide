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
# Written by scripts/ai_impact/build_ilo_by_career.py and committed: each career's ISCO-08 group and the
# ILO's generative-AI exposure score for it (ROADMAP 6.2, 6.3; D5 = B).
ILO_EXPOSURE_PATH = _path_from_env(
    "ILO_EXPOSURE_PATH",
    DATA_DIR / "ilo" / "ilo_exposure_by_career.csv",
)
# Written by scripts/ai_impact/build_robot_by_career.py and committed: each career's robot exposure from
# Anthropic's "What work can robots do?" (2026), and its most robot-exposed tasks with a cited robot (10.14).
ROBOT_EXPOSURE_PATH = _path_from_env("ROBOT_EXPOSURE_PATH", DATA_DIR / "robots" / "robot_exposure_by_career.csv")
ROBOT_TASKS_PATH = _path_from_env("ROBOT_TASKS_PATH", DATA_DIR / "robots" / "robot_tasks_by_career.csv")
# Written by scripts/ai_impact/build_microsoft_by_soc.py and committed: Microsoft's AI applicability per BLS
# occupation code, and each code's most important work activities people brought to Copilot (10.15).
MICROSOFT_SCORES_PATH = _path_from_env("MICROSOFT_SCORES_PATH", DATA_DIR / "microsoft" / "ai_applicability_by_soc.csv")
MICROSOFT_ACTIVITIES_PATH = _path_from_env(
    "MICROSOFT_ACTIVITIES_PATH", DATA_DIR / "microsoft" / "top_activities_by_soc.csv"
)
# Committed, extracted by hand from BLS's workbooks (data/bls/README.md): the 2025-35 projections, BLS's reasons,
# and the O*NET-SOC codes whose BLS code is not their first seven characters (10.16).
BLS_DIR = _path_from_env("BLS_DIR", DATA_DIR / "bls")
# Written by scripts/i18n/translate_content.py (ROADMAP 6.1c) and committed: O*NET content and
# research claims in Turkish, translated once at build time (D8 = B).
CONTENT_TRANSLATIONS_PATH = _path_from_env(
    "CONTENT_TRANSLATIONS_PATH",
    DATA_DIR / "i18n" / "content_tr.csv",
)
# Committed, reviewed by hand: Turkish university departments and the O*NET careers they lead to (ROADMAP 9.1),
# built by scripts/departments/build_department_careers.py.
DEPARTMENTS_PATH = _path_from_env("DEPARTMENTS_PATH", DATA_DIR / "departments" / "departments.csv")
DEPARTMENT_CAREERS_PATH = _path_from_env(
    "DEPARTMENT_CAREERS_PATH",
    DATA_DIR / "departments" / "department_careers.csv",
)
# Committed and reviewed by hand: new job titles (2026 onward) and their closest O*NET roles (ROADMAP 6.6).
NEW_TITLES_PATH = _path_from_env(
    "NEW_TITLES_PATH",
    DATA_DIR / "new_titles" / "new_job_titles.csv",
)
PROFILE_RESULT_PATH = _path_from_env(
    "PROFILE_RESULT_PATH",
    ONET_INTEREST_PROFILER_DIR / "ip_profile_result.json",
)
QUESTIONS_PATH = _path_from_env(
    "QUESTIONS_PATH",
    ONET_INTEREST_PROFILER_DIR / "interest_profiler_questions.json",
)
MINI_IP_QUESTIONS_PATH = _path_from_env(
    "MINI_IP_QUESTIONS_PATH",
    ONET_INTEREST_PROFILER_DIR / "interest_profiler_questions_30.json",
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

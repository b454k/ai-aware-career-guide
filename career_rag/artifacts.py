"""Validation helpers for local Career RAG runtime artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from career_rag.config import (
    AI_IMPACT_DUCKDB_PATH,
    CONTENT_TRANSLATIONS_PATH,
    ONET_DUCKDB_PATH,
    PROFILE_RESULT_PATH,
    PROJECT_ROOT,
    RESEARCH_CLAIMS_PATH,
)


SETUP_BUILD_COMMAND = r"python scripts\build_all_artifacts.py"
SETUP_CHECK_COMMAND = r"python scripts\check_artifacts.py"

# Only what the app reads at runtime.
REQUIRED_PATH_ARTIFACTS = [
    {
        "id": "onet_duckdb",
        "label": "O*NET DuckDB database",
        "path": ONET_DUCKDB_PATH,
        "kind": "file",
    },
    {
        "id": "ai_impact_duckdb",
        "label": "AI-impact DuckDB database (scripts/ai_impact/build_ai_impact_duckdb.py)",
        "path": AI_IMPACT_DUCKDB_PATH,
        "kind": "file",
    },
    {
        "id": "research_claims",
        "label": "Research claims per career (committed; scripts/research/check_claim_relevance.py)",
        "path": RESEARCH_CLAIMS_PATH,
        "kind": "file",
    },
    {
        "id": "content_translations",
        "label": "Turkish career content (committed; scripts/i18n/translate_content.py)",
        "path": CONTENT_TRANSLATIONS_PATH,
        "kind": "file",
    },
]


class MissingRagArtifactsError(RuntimeError):
    """Raised when local RAG artifacts are missing or unusable."""

    def __init__(self, missing_artifacts: list[dict[str, Any]]) -> None:
        self.missing_artifacts = missing_artifacts
        super().__init__(format_missing_artifacts_error(missing_artifacts))


def project_relative(path: str | Path) -> str:
    """Return a project-relative display path when possible."""
    resolved = Path(path)
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def _path_exists(path: Path, kind: str) -> bool:
    if kind == "dir":
        return path.is_dir()
    return path.is_file()


def path_artifact_statuses() -> list[dict[str, Any]]:
    """Return existence status for required file/folder artifacts."""
    statuses: list[dict[str, Any]] = []
    for artifact in REQUIRED_PATH_ARTIFACTS:
        path = Path(artifact["path"])
        statuses.append(
            {
                **artifact,
                "path": str(path),
                "display_path": project_relative(path),
                "exists": _path_exists(path, str(artifact["kind"])),
                "count": None,
                "error": "",
            }
        )
    return statuses


def inspect_rag_artifacts() -> dict[str, Any]:
    """Inspect required local artifacts and return a UI/script-friendly payload."""
    path_statuses = path_artifact_statuses()
    all_statuses = list(path_statuses)
    missing = [status for status in all_statuses if not status.get("exists")]
    return {
        "project_root": str(PROJECT_ROOT),
        "profile_result_path": str(PROFILE_RESULT_PATH),
        "profile_result_display_path": project_relative(PROFILE_RESULT_PATH),
        "statuses": all_statuses,
        "path_statuses": path_statuses,
        "missing": missing,
        "rag_enabled": not missing,
        "build_command": SETUP_BUILD_COMMAND,
        "check_command": SETUP_CHECK_COMMAND,
    }


def format_missing_artifacts_error(missing_artifacts: list[dict[str, Any]]) -> str:
    """Build an actionable missing-artifacts message."""
    lines = [
        "RAG artifacts missing. Please run the setup/build command.",
        "",
        "Missing or unusable artifacts:",
    ]
    for artifact in missing_artifacts:
        detail = artifact.get("display_path") or artifact.get("path")
        count = artifact.get("count")
        error = artifact.get("error")
        suffix = ""
        if count is not None:
            suffix += f" (count={count})"
        if error:
            suffix += f" - {error}"
        lines.append(f"- {artifact.get('label')}: {detail}{suffix}")

    lines.extend(
        [
            "",
            "Rebuild artifacts from raw/local sources:",
            f"  {SETUP_BUILD_COMMAND}",
            "",
            "Then verify:",
            f"  {SETUP_CHECK_COMMAND}",
        ]
    )
    return "\n".join(lines)


def ensure_required_artifacts() -> dict[str, Any]:
    """Raise if any required RAG artifact is missing."""
    inspection = inspect_rag_artifacts()
    missing = inspection["missing"]
    if missing:
        raise MissingRagArtifactsError(missing)
    return inspection

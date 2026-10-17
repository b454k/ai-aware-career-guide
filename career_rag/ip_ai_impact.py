"""AI-impact evidence helpers for Interest Profiler final reports."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from career_rag.config import AI_IMPACT_DUCKDB_PATH, ILO_EXPOSURE_PATH, ONET_DUCKDB_PATH, RESEARCH_CLAIMS_PATH
from career_rag.ui_i18n import ui_text


DB_PATH = ONET_DUCKDB_PATH

# Anthropic's task coverage ("penetration", labor-market impacts report): 0 = not covered
# (too little work-related Claude usage, or not an LLM-capable task); covered tasks are
# weighted 1.0 for automation-style use and 0.5 for augmentation-style use, so values in
# between are a mix and 0.75 is an even split.
TASK_COVERAGE_DOC_TYPE = "ai_task_penetration"
COVERAGE_EVEN_SPLIT = 0.75
AI_TASK_TABLE_LIMIT = 6
# A career's tasks, most important first: O*NET's importance rating (task_ratings, scale IM),
# as on O*NET's own pages. 12 careers have no ratings; theirs keep task-ID order.
TASKS_BY_IMPORTANCE_SQL = """
    SELECT t.task_id, t.task, t.task_type
    FROM task_statements AS t
    LEFT JOIN task_ratings AS r
        ON r.onetsoc_code = t.onetsoc_code AND r.task_id = t.task_id AND r.scale_id = 'IM'
    WHERE t.onetsoc_code = ?
    ORDER BY r.data_value DESC NULLS LAST, t.task_id
    LIMIT ?
"""
NO_LOCAL_ANTHROPIC_EVIDENCE = (
    "No local Anthropic evidence found for this exact O*NET task"
)

ANTHROPIC_LABOR_MARKET_URL = "https://www.anthropic.com/research/labor-market-impacts"
ILO_WP140_URL = "https://www.ilo.org/publications/generative-ai-and-jobs-refined-global-index-occupational-exposure"
AEI_RELEASE_URL = "https://huggingface.co/datasets/Anthropic/EconomicIndex/tree/main/release_2026_06_26"
# Per-occupation Claude.ai metrics shown to users (D14 = C); names as in the release documentation.
CLAUDE_USAGE_METRICS = {
    "pct": "global_pct",  # share of all conversations in the geography, percent
    "collaboration_bucket_automation_pct": "automation_pct",  # directive + feedback loop
    "collaboration_bucket_augmentation_pct": "augmentation_pct",  # learning + task iteration + validation
    "human_only_time_mean": "human_only_hours",  # model estimate, hours
    "human_with_ai_time_mean": "with_ai_minutes",  # model estimate, minutes
}


def build_ai_impact_for_occupation(
    onet_soc_code: str,
    onet_tasks: list[Any] | None = None,
    citation_manager: Any | None = None,
) -> dict[str, Any]:
    """Build task-level AI-impact rows from exact local O*NET tasks, and the other AI sources (ai_snapshot sums them up)."""
    anthropic_id = _register_anthropic_source(citation_manager)
    rows = _local_ai_rows_for_soc(onet_soc_code)
    task_records = _task_records_for_occupation(onet_soc_code, onet_tasks)
    task_rows_by_id = _task_rows_by_task_id(rows)

    task_breakdown = []
    used_retrieved = False
    validation_warnings: list[str] = []
    for task_record in task_records:
        row, validation_warning = _best_evidence_for_task(
            task_record=task_record,
            rows=task_rows_by_id.get(str(task_record.get("task_id") or ""), []),
        )
        if validation_warning:
            validation_warnings.append(validation_warning)
        if row:
            used_retrieved = True
            task_breakdown.append(_format_retrieved_task_row(task_record, row, anthropic_id))
        else:
            task_breakdown.append(
                _format_unobserved_task_row(task_record, validation_warning)
            )

    return {
        "claude_usage": _claude_usage(onet_soc_code, citation_manager),
        "ilo_exposure": _ilo_exposure(onet_soc_code, citation_manager),
        "research_claims": _research_claims(onet_soc_code, citation_manager),
        "evidence_status": (
            "exact_onet_task_evidence"
            if used_retrieved
            else "no_exact_task_anthropic_evidence"
        ),
        "task_breakdown": task_breakdown,
        "validation_warnings": validation_warnings,
    }


def _claude_usage(onet_soc_code: str, citation_manager: Any | None) -> dict[str, Any] | None:
    """Latest month of Claude.ai usage for this occupation, worldwide and in Turkey (ROADMAP 2.5)."""
    month, by_occupation = _claude_usage_by_occupation()
    values = by_occupation.get(str(onet_soc_code or "").strip())
    if not values or "global_pct" not in values:
        return None
    source_id = None
    if citation_manager is not None:
        source_id = citation_manager.add_source(
            title=ui_text("source.usage.title", citation_manager.language),
            source_type="anthropic",
            url=AEI_RELEASE_URL,
            local_file="data/duckdb/ai_impact.duckdb (table claude_usage)",
            retrieved_section=ui_text("source.usage.section", citation_manager.language, month=month),
            note=ui_text("source.usage.note", citation_manager.language),
        )
    return {
        "month": month,
        **values,
        "turkey_pct": values.get("turkey_pct"),
        "source_ids": [source_id] if source_id else [],
    }


@lru_cache(maxsize=1)
def _claude_usage_by_occupation() -> tuple[str, dict[str, dict[str, float]]]:
    """{O*NET-SOC code: metrics} for the latest month in the extract, Claude.ai only."""
    import duckdb

    conn = duckdb.connect(str(AI_IMPACT_DUCKDB_PATH), read_only=True)
    try:
        rows = conn.execute(
            """
            SELECT CAST(date_start AS VARCHAR), geo_id, node_external_id, metric_id, value
            FROM claude_usage
            WHERE source = 'claude_ai' AND category_name = 'soc_occupation'
            """
        ).fetchall()
    finally:
        conn.close()
    month = max(row[0] for row in rows)
    by_occupation: dict[str, dict[str, float]] = {}
    for date_start, geo_id, code, metric, value in rows:
        if date_start != month:
            continue
        if geo_id == "GLOBAL" and metric in CLAUDE_USAGE_METRICS:
            by_occupation.setdefault(code, {})[CLAUDE_USAGE_METRICS[metric]] = value
        elif geo_id == "TUR" and metric == "pct":
            by_occupation.setdefault(code, {})["turkey_pct"] = value
    return month, by_occupation


def _ilo_exposure(onet_soc_code: str, citation_manager: Any | None) -> dict[str, Any] | None:
    """The ILO's exposure score for this career's ISCO-08 group (D5 = B: a second, assessed source)."""
    row = _ilo_exposure_by_occupation().get(str(onet_soc_code or "").strip())
    if not row:
        return None
    source_id = None
    if citation_manager is not None:
        source_id = citation_manager.add_source(
            title="Gmyrek et al. (2025), Generative AI and Jobs: A Refined Global Index of Occupational Exposure, ILO Working Paper 140",
            source_type="ilo",
            url=ILO_WP140_URL,
            local_file="data/ilo/ilo_exposure_by_career.csv",
            retrieved_section=ui_text("source.ilo.section", citation_manager.language),
            note=ui_text("source.ilo.note", citation_manager.language),
        )
    return {
        "isco08_code": row["isco08_code"],
        "isco08_title": row["isco08_title"],
        "gradient": row["exposure_gradient"],
        "mean": float(row["exposure_mean"]),
        "sd": float(row["exposure_sd"]),
        "careers_in_group": int(row["careers_in_group"]),
        "source_ids": [source_id] if source_id else [],
    }


@lru_cache(maxsize=1)
def _ilo_exposure_by_occupation() -> dict[str, dict[str, str]]:
    import csv

    with ILO_EXPOSURE_PATH.open(encoding="utf-8", newline="") as handle:
        return {row["onetsoc_code"]: row for row in csv.DictReader(handle)}


def _research_claims(onet_soc_code: str, citation_manager: Any | None) -> list[dict[str, Any]]:
    """Research claims about this occupation (ROADMAP 4.1c), each with its verbatim quote and source."""
    claims = []
    for row in _research_claims_by_occupation().get(str(onet_soc_code or "").strip(), []):
        pages = row["page_start"] if row["page_start"] == row["page_end"] else f"{row['page_start']}-{row['page_end']}"
        source_id = None
        if citation_manager is not None:
            source_id = citation_manager.add_source(
                title=f"{row['title']} ({row['authors']}, {row['year']})",
                source_type="research",
                url=row["final_url"],
                local_file="data/research/career_research_claims.csv",
                note=ui_text("source.research.note", citation_manager.language),
            )
        claims.append(
            {
                "claim": row["claim_text"],
                "quote": row["evidence_quote"],
                "pages": pages,
                "source": f"{row['title']} ({row['year']})",  # named on the card, without a number (ROADMAP 9.5)
                "source_ids": [source_id] if source_id else [],
            }
        )
    return claims


@lru_cache(maxsize=1)
def _research_claims_by_occupation() -> dict[str, list[dict[str, str]]]:
    """{O*NET-SOC code: claims in display order} from the committed file."""
    import csv

    by_occupation: dict[str, list[dict[str, str]]] = {}
    with RESEARCH_CLAIMS_PATH.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            by_occupation.setdefault(row["onetsoc_code"], []).append(row)
    return by_occupation


def _register_anthropic_source(citation_manager: Any | None) -> int | None:
    if citation_manager is None:
        return None

    anthropic_id = citation_manager.add_source(
        title=ui_text("source.anthropic.title", citation_manager.language),
        source_type="anthropic",
        url=ANTHROPIC_LABOR_MARKET_URL,
        local_file="data/duckdb/ai_impact.duckdb",
        retrieved_section=ui_text("source.anthropic.section", citation_manager.language),
        note=ui_text("source.anthropic.note", citation_manager.language),
    )
    return anthropic_id


def _marker(source_id: int | None) -> str:
    return f"[{source_id}]" if source_id else ""


@lru_cache(maxsize=1)
def _ai_rows_by_occupation() -> dict[str, list[dict[str, Any]]]:
    """Anthropic task coverage and observed exposure per O*NET code, from ai_impact.duckdb (ROADMAP 3.2)."""
    import duckdb

    conn = duckdb.connect(str(AI_IMPACT_DUCKDB_PATH), read_only=True)
    try:
        coverage = conn.execute("SELECT onetsoc_code, CAST(task_id AS VARCHAR), task, coverage FROM task_coverage").fetchall()
        exposure = conn.execute("SELECT onetsoc_code, observed_exposure FROM occupation_exposure").fetchall()
    finally:
        conn.close()
    rows: dict[str, list[dict[str, Any]]] = {}
    for code, task_id, task, value in coverage:
        rows.setdefault(code, []).append(
            {
                "doc_type": TASK_COVERAGE_DOC_TYPE,
                "soc_code": code,
                "onet_task_id": task_id,
                "task_text": task,
                "metric_name": "penetration",
                "metric_value": value,
            }
        )
    for code, value in exposure:
        rows.setdefault(code, []).append(
            {"doc_type": "ai_occupation_impact", "soc_code": code, "metric_name": "observed_exposure", "metric_value": value}
        )
    return rows


def _local_ai_rows_for_soc(onet_soc_code: str) -> list[dict[str, Any]]:
    return list(_ai_rows_by_occupation().get(str(onet_soc_code or "").strip(), []))


def _task_records_for_occupation(
    onet_soc_code: str,
    onet_tasks: list[Any] | None,
) -> list[dict[str, Any]]:
    records = _fetch_onet_task_records(onet_soc_code, AI_TASK_TABLE_LIMIT)
    if records:
        return records
    return _coerce_task_records(onet_soc_code, onet_tasks, AI_TASK_TABLE_LIMIT)


def _fetch_onet_task_records(onet_soc_code: str, limit: int) -> list[dict[str, Any]]:
    code = str(onet_soc_code or "").strip()
    if not code or not DB_PATH.exists():
        return []
    try:
        import duckdb
    except ImportError:
        return []

    conn = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        rows = conn.execute(
            TASKS_BY_IMPORTANCE_SQL,
            [code, limit],
        ).fetchall()
    finally:
        conn.close()

    records = []
    for task_id, task, task_type in rows:
        task_text = _clean_text(task)
        if not task_text:
            continue
        records.append(
            {
                "onet_soc_code": code,
                "task_id": _task_id_string(task_id),
                "task": task_text,
                "task_type": _clean_text(task_type) or None,
            }
        )
    return records


def _coerce_task_records(
    onet_soc_code: str,
    onet_tasks: list[Any] | None,
    limit: int,
) -> list[dict[str, Any]]:
    records = []
    for item in list(onet_tasks or [])[:limit]:
        if isinstance(item, dict):
            task_text = _clean_text(
                item.get("task")
                or item.get("task_text")
                or item.get("displayed_task")
                or item.get("matched_onet_task")
            )
            task_id = _task_id_string(item.get("task_id") or item.get("onet_task_id"))
            task_type = _clean_text(item.get("task_type")) or None
        else:
            task_text = _clean_text(item)
            task_id = ""
            task_type = None
        if not task_text:
            continue
        records.append(
            {
                "onet_soc_code": str(onet_soc_code or "").strip(),
                "task_id": task_id,
                "task": task_text,
                "task_type": task_type,
            }
        )
    return records


def _task_rows_by_task_id(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if str(row.get("doc_type") or "") != TASK_COVERAGE_DOC_TYPE:
            continue
        task_id = _task_id_string(row.get("onet_task_id"))
        if not task_id:
            continue
        grouped.setdefault(task_id, []).append(row)
    return grouped


def _best_evidence_for_task(
    task_record: dict[str, Any],
    rows: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, str | None]:
    displayed_task = _clean_text(task_record.get("task"))
    task_id = _task_id_string(task_record.get("task_id"))
    valid_rows = []
    invalid_rows = []
    for row in rows:
        source_task = _clean_text(row.get("task_text"))
        if source_task and not _same_task_statement(displayed_task, source_task):
            invalid_rows.append(source_task)
            continue
        valid_rows.append(row)

    if valid_rows:
        # Anthropic's file can hold two wordings of one task (e.g. an extra comma) with
        # different values; the wording identical to the displayed O*NET task wins.
        exact = [row for row in valid_rows if _clean_text(row.get("task_text")) == displayed_task]
        return (exact or valid_rows)[0], None

    if invalid_rows:
        warning = (
            f"Validation warning: skipped Anthropic evidence for O*NET task ID {task_id} "
            "because its task statement did not match the displayed O*NET task."
        )
        return None, warning
    return None, None


def _format_retrieved_task_row(
    task_record: dict[str, Any],
    row: dict[str, Any],
    anthropic_id: int | None,
) -> dict[str, Any]:
    task_text = _clean_text(task_record.get("task"))
    task_id = _task_id_string(task_record.get("task_id"))
    score = _as_float(row.get("metric_value"))
    score_display = _score_display(score)
    source_marker = _marker(anthropic_id)
    if score is None:
        score_type = "anthropic_task_coverage_missing"
        evidence_status = "exact_task_id_match_metric_missing"
        evidence = (
            f"Anthropic's task coverage row for O*NET task ID {task_id} has no value. {source_marker}"
        ).strip()
    else:
        score_type = "anthropic_task_coverage"
        evidence_status = "exact_task_id_match"
        evidence = (
            f"Anthropic's task coverage for O*NET task ID {task_id} is {score_display} "
            f"(0 = not covered, 0.5 = augmentation-style use, 1 = automation-style use). {source_marker}"
        ).strip()

    return {
        "task": task_text,
        "displayed_task": task_text,
        "onet_task_id": task_id,
        "matched_onet_task": task_text,
        "matched_anthropic_task": task_text,
        "ai_coverage": _coverage_label(score),
        "score": round(float(score), 4) if score is not None else None,
        "score_display": score_display,
        "score_type": score_type,
        "evidence_status": evidence_status,
        "evidence": evidence,
        "source_ids": [anthropic_id] if anthropic_id else [],
    }


def _format_unobserved_task_row(
    task_record: dict[str, Any],
    validation_warning: str | None = None,
) -> dict[str, Any]:
    task_text = _clean_text(task_record.get("task"))
    evidence = NO_LOCAL_ANTHROPIC_EVIDENCE
    if validation_warning:
        evidence = f"{evidence}. {validation_warning}"
    return {
        "task": task_text,
        "displayed_task": task_text,
        "onet_task_id": _task_id_string(task_record.get("task_id")),
        "matched_onet_task": task_text,
        "matched_anthropic_task": None,
        "ai_coverage": _coverage_label(None),
        "score": None,
        "score_display": "N/A",
        "score_type": "no_coverage_data",
        "evidence_status": "no_exact_task_evidence",
        "evidence": evidence,
        "source_ids": [],
        "validation_warning": validation_warning,
    }


ILO_LEVELS = {"Gradient 4": "high", "Gradient 3": "high", "Gradient 2": "medium",
              "Gradient 1": "low", "Minimal Exposure": "low", "Not Exposed": "low"}


def ai_snapshot(ai_impact: dict[str, Any]) -> dict[str, Any]:
    """A career's AI evidence in a few plain facts, and one sentence by a stated rule (ROADMAP 9.2).

    The sources stay separate (D5: no combined score): how many of the shown tasks have Claude use, the ILO's
    rating in three levels, the number of research findings. The sentence only compares the first two:
    it says when they agree, and when they disagree, instead of averaging them.
    """
    scored = [row for row in ai_impact.get("task_breakdown") or [] if row.get("score_type") == "anthropic_task_coverage"]
    seen = sum(1 for row in scored if (row.get("score") or 0) > 0)
    claude = None if not scored else "much" if seen * 2 >= len(scored) else "some" if seen else "none"
    ilo = ILO_LEVELS.get((ai_impact.get("ilo_exposure") or {}).get("gradient"))
    if claude is None and ilo is None:
        verdict = "none"
    elif claude == "none" and ilo == "high":
        verdict = "disagree_unseen"
    elif claude == "much" and ilo == "low":
        verdict = "disagree_used"
    elif claude in ("much", None) and ilo in ("high", None):
        verdict = "high_reach"
    elif claude in ("none", None) and ilo in ("low", None):
        verdict = "low_reach"
    else:
        verdict = "partial"
    return {"tasks_seen": seen, "tasks_scored": len(scored), "ilo_level": ilo,
            "research_count": len(ai_impact.get("research_claims") or []), "verdict": verdict}


def _observed_exposure(rows: list[dict[str, Any]]) -> float | None:
    """Return the occupation's observed_exposure value; other metrics have other meanings and units."""
    values = [
        _as_float(row.get("metric_value"))
        for row in rows
        if _clean_text(row.get("metric_name")) == "observed_exposure"
    ]
    values = [value for value in values if value is not None]
    if not values:
        return None
    return max(values)


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _task_id_string(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    if re.fullmatch(r"\d+\.0+", text):
        return text.split(".", 1)[0]
    return text


def _same_task_statement(left: Any, right: Any) -> bool:
    return _normalize(left) == _normalize(right)


def _coverage_label(coverage: float | None) -> str:
    """Name Anthropic's task coverage value in Anthropic's own terms (see TASK_COVERAGE_DOC_TYPE)."""
    if coverage is None:
        return "No data"
    if coverage == 0:
        return "Not covered"
    if coverage > COVERAGE_EVEN_SPLIT:
        return "Covered: mostly automation"
    if coverage < COVERAGE_EVEN_SPLIT:
        return "Covered: mostly augmentation"
    return "Covered: mixed"


def _score_display(score: float | None) -> str:
    if score is None:
        return "N/A"
    return f"{score:.4g}"


def _normalize(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None



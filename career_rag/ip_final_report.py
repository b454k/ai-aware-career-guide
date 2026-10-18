"""Final career report builder for the O*NET Interest Profiler flow."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from career_rag.artifacts import ensure_required_artifacts
from career_rag.config import (
    FINAL_REPORT_JSON_PATH,
    FINAL_REPORT_MD_PATH,
    ONET_DUCKDB_PATH,
    ONET_INTEREST_PROFILER_DIR,
    QUESTIONS_PATH,
)
from career_rag.interest_profiler_local import (
    RIASEC_INTERESTS,
    load_interest_profiler_questions,
    make_holland_code,
    prepare_profile_for_rag,
)
from career_rag.ip_ai_impact import TASKS_BY_IMPORTANCE_SQL, build_ai_impact_for_occupation
from career_rag.ip_career_matcher import load_zone_occupations, onet_fit_list
from career_rag.occupation_aliases import build_occupation_index, resolve_career_alias
from career_rag.ui_i18n import (
    claude_usage_lines,
    content_text,
    ilo_exposure_lines,
    robot_exposure_lines,
    interest_label,
    job_zone_number,
    job_zone_preparation,
    month_label,
    normalize_language,
    question_text,
    ui_text,
)


DATA_DIR = ONET_INTEREST_PROFILER_DIR
DB_PATH = ONET_DUCKDB_PATH

IP_SHORT_FORM_URL = "https://www.onetcenter.org/dl_tools/ipsf/Interest_Profiler.pdf"
IP_MATCHING_RULE_URL = "https://www.onetcenter.org/dl_files/Mini-IP_Linking.pdf"
ONET_IP_RESOURCE_URL = "https://www.onetcenter.org/IP.html"

# Skills shown as "foundational" rather than technical: a hand-picked subset of O*NET's
# Basic Skills (2.A) and Social Skills (2.B.1). Not an O*NET category; e.g. Critical
# Thinking and Mathematics are left out and so count as technical.
FOUNDATIONAL_SOFT_SKILLS = {
    "active listening",
    "active learning",
    "reading comprehension",
    "writing",
    "speaking",
    "social perceptiveness",
    "monitoring",
    "coordination",
}

# O*NET education_categories, element 2.D.1 "Required Level of Education". Levels without an
# entry (1, 3, 4, 7, 9) are described by their own O*NET name in the report.
EDUCATION_LEVELS = {
    2: "high_school",  # High School Diploma or the equivalent
    5: "associate",  # Associate's Degree or other 2-year degree
    6: "bachelor",
    8: "master",
    10: "doctoral",  # First Professional Degree / Doctor's Degree - Professional Practice
    11: "doctoral",  # Doctoral Degree / Doctor's Degree - Research/Scholarship
    12: "doctoral",  # Post-Doctoral Training
}

class CitationManager:
    """Assign stable numeric citations to report sources."""

    def __init__(self, language: str = "en") -> None:
        self.language = language  # source titles, sections and notes are written in this language
        self._sources: list[dict[str, Any]] = []
        self._key_to_id: dict[tuple[str, str, str, str], int] = {}

    def add_source(
        self,
        title: str,
        source_type: str,
        url: str | None = None,
        local_file: str | None = None,
        retrieved_section: str | None = None,
        note: str | None = None,
    ) -> int:
        """Add or reuse one source and return its numeric ID."""
        key = (
            str(title or "").strip(),
            str(source_type or "").strip(),
            str(url or "").strip(),
            str(local_file or "").strip(),
        )
        existing = self._key_to_id.get(key)
        if existing is not None:
            return existing

        source_id = len(self._sources) + 1
        self._key_to_id[key] = source_id
        self._sources.append(
            {
                "id": source_id,
                "title": str(title or "").strip(),
                "source_type": str(source_type or "").strip(),
                "url": str(url or "").strip() or None,
                "local_file": str(local_file or "").strip() or None,
                "retrieved_section": str(retrieved_section or "").strip() or None,
                "note": str(note or "").strip() or None,
            }
        )
        return source_id

    def marker(self, source_id: int | None) -> str:
        """Return a citation marker like [1]."""
        return f"[{source_id}]" if source_id else ""

    def sources(self) -> list[dict[str, Any]]:
        """Return sources in display order."""
        return list(self._sources)


def build_final_career_report(profile_for_rag: dict[str, Any], top_k: int = 10, language: str = "en") -> dict[str, Any]:
    """Build, save, and return the structured final career report, with its own sentences in `language`."""
    ensure_required_artifacts()
    top_k = max(1, min(int(top_k), 10))
    language = normalize_language(language)
    citation_manager = CitationManager(language)
    ip_source_id = _add_interest_profiler_source(citation_manager)

    profile_used = _build_profile_used(profile_for_rag, citation_manager.marker(ip_source_id), language)
    occupation_index = build_occupation_index(DB_PATH)
    candidate_groups = _candidate_groups_from_profile(profile_for_rag, profile_used)

    top_matches: list[dict[str, Any]] = []
    used_soc_codes: set[str] = set()
    used_candidate_titles: set[str] = set()
    for group in candidate_groups:
        group_limit = int(group.get("limit") or 5)
        group_count = 0
        for candidate in group.get("candidates") or []:
            if len(top_matches) >= top_k or group_count >= group_limit:
                break
            display_title = str(candidate.get("career_title") or candidate.get("title") or "").strip()
            if not display_title:
                continue
            title_key = _title_key(display_title)
            if title_key in used_candidate_titles:
                continue
            resolution = resolve_career_alias(display_title, occupation_index)
            soc_code = resolution.get("onet_soc_code")
            if not soc_code or soc_code in used_soc_codes:
                continue
            details = get_onet_occupation_details(soc_code, citation_manager)
            if not details.get("description"):
                continue

            used_candidate_titles.add(title_key)
            used_soc_codes.add(str(soc_code))
            group_count += 1
            rank = len(top_matches) + 1
            top_matches.append(
                _build_match(
                    rank=rank,
                    display_title=display_title,
                    resolution=resolution,
                    details=details,
                    profile_used=profile_used,
                    citation_manager=citation_manager,
                    match_group=str(group.get("label") or ""),
                    target_job_zone=group.get("job_zone"),
                    fit=candidate.get("fit"),
                    interest_similarity=candidate.get("interest_similarity"),
                    language=language,
                )
            )

    alternatives = _build_alternatives_by_level(profile_for_rag, profile_used, used_soc_codes, citation_manager, language)

    if not top_matches:
        raise RuntimeError(
            "Retrieval returned zero occupation-specific O*NET evidence. "
            "Check the local DuckDB artifacts with "
            "`python scripts\\check_artifacts.py` before generating a report."
        )

    report = {
        "language": language,
        "report_generation_method": "template_fallback_local_evidence",
        "top_match_grouping": "department_10" if profile_for_rag.get("department") else "current_zone_5_future_zone_5",
        "llm_system_prompt_available": True,
        "profile_used": profile_used,
        "core_skills_across_matches": _core_skills_from_matches(top_matches),
        "top_matches": top_matches,
        "alternative_careers": alternatives,
        "alternative_grouping": "job_zone_3",  # the best 3 at each preparation level (Phase 10)
        "sources": citation_manager.sources(),
    }

    save_final_report(report)
    save_markdown_report(report)
    return report


def get_onet_occupation_details(
    onet_soc_code: str,
    citation_manager: CitationManager | None = None,
) -> dict[str, Any]:
    """Retrieve one occupation's details from local DuckDB O*NET tables."""
    try:
        import duckdb
    except ImportError as exc:
        raise RuntimeError("duckdb is required to retrieve O*NET occupation details.") from exc

    if not DB_PATH.exists():
        raise FileNotFoundError(f"O*NET DuckDB database not found: {DB_PATH}")

    conn = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        occupation = conn.execute(
            """
            SELECT onetsoc_code, title, description
            FROM occupation_data
            WHERE onetsoc_code = ?
            LIMIT 1
            """,
            [onet_soc_code],
        ).fetchone()
        if not occupation:
            return {}

        code, title, description = occupation
        source_id = None
        if citation_manager is not None:
            source_id = citation_manager.add_source(
                title=ui_text("source.onet.title", citation_manager.language, title=content_text(title, citation_manager.language)),
                source_type="onet",
                url=_onet_summary_url(str(code)),
                local_file="data/duckdb/onet.duckdb",
                retrieved_section=ui_text("source.onet.section", citation_manager.language),
                note=ui_text("source.onet.note", citation_manager.language, code=code),
            )
        citation = citation_manager.marker(source_id) if citation_manager else ""
        task_records = _fetch_task_records(conn, str(code), limit=6)
        education_levels = _fetch_education_levels(conn, str(code), limit=4)

        details = {
            "occupation_title": str(title),
            "onet_soc_code": str(code),
            "description": _with_marker(description, citation),
            "tasks": _with_marker_list([item["task"] for item in task_records], citation),
            "task_records": task_records,
            "skills": _with_marker_list(_fetch_element_names(conn, "essential_skills", str(code), limit=12), citation),
            "knowledge": _with_marker_list(_fetch_element_names(conn, "knowledge", str(code), limit=8), citation),
            "abilities": _with_marker_list(_fetch_element_names(conn, "abilities", str(code), limit=5), citation),
            "education": _with_marker_list(
                _dedupe_text([f"{level['label']} ({level['percent']:.2f}%)" for level in education_levels]),
                citation,
            ),
            "education_levels": education_levels,
            "job_zone": _fetch_job_zone(conn, str(code), citation),
            "work_context": _with_marker_list(_fetch_work_context(conn, str(code), limit=5), citation),
            "software": _with_marker_list(_fetch_software(conn, str(code), limit=16), citation),
            "related_occupations": _with_marker_list(_fetch_related(conn, str(code), limit=5), citation),
            "citation": citation,
        }
    finally:
        conn.close()

    return details


def save_final_report(
    report: dict[str, Any],
    path: str | Path = FINAL_REPORT_JSON_PATH,
) -> Path:
    """Save the final career report JSON."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=True)
        file.write("\n")
    return output_path


def save_markdown_report(
    report: dict[str, Any],
    path: str | Path = FINAL_REPORT_MD_PATH,
) -> Path:
    """Save a readable markdown version of the final report."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_to_markdown(report), encoding="utf-8")
    return output_path


def report_to_markdown(report: dict[str, Any]) -> str:
    """Render a compact markdown version of the report."""
    profile = report.get("profile_used") or {}
    lines = [
        "# Final Career Report",
        "",
        "## Profile Summary",
        f"- Holland code used for matching: {profile.get('final_holland_code', '')}",
        f"- Current Job Zone: {profile.get('current_job_zone', '')}",
        f"- Future Job Zone: {profile.get('future_job_zone', '')}",
        f"- Preferences: {', '.join(profile.get('sub_preferences') or [])}",
        "",
        "## Top Career Matches",
    ]

    for match in report.get("top_matches") or []:
        lines.extend(
            [
                "",
                f"### {match.get('rank')}. {match.get('display_title')}",
                f"Resolved O*NET title: {match.get('resolved_onet_title')}",
                f"Fit (O*NET): {match.get('fit_label')}",
                "",
                "Why it fits:",
            ]
        )
        lines.extend(f"- {item}" for item in match.get("why_it_fits") or [])
        lines.extend(
            [
                "",
                f"What this job does: {match.get('onet_details', {}).get('description', '')}",
                "",
                "AI impact:",
            ]
        )
        for row in match.get("ai_impact", {}).get("task_breakdown") or []:
            score = row.get("score_display")
            if not score:
                score = "N/A" if row.get("score") is None else str(row.get("score"))
            lines.append(
                f"- {row.get('task')}: {row.get('ai_coverage')} "
                f"({score}, {row.get('score_type')}) - {row.get('evidence')}"
            )
        usage = match.get("ai_impact", {}).get("claude_usage")
        if usage:
            lines.append(f"How people use Claude for this work ({month_label(usage['month'])}):")
            lines.extend(f"- {line}" for line in claude_usage_lines(usage))
        ilo = match.get("ai_impact", {}).get("ilo_exposure")
        if ilo:
            lines.append("ILO exposure of the occupation group:")
            lines.extend(f"- {line}" for line in ilo_exposure_lines(ilo))
        robot = match.get("ai_impact", {}).get("robot_exposure")
        if robot:
            lines.append("What robots can already do in this work (Anthropic robot study):")
            lines.extend(f"- {line}" for line in robot_exposure_lines(robot))
            lines.extend(f"- {item['task']} ({item['tier']}; example: {item['system']}, {item['url']})" for item in robot["tasks"])
        research = match.get("ai_impact", {}).get("research_claims") or []
        if research:
            lines.append("What research says:")
            lines.extend(
                f"- {item['claim']} Quote: \"{item['quote']}\" (p. {item['pages']}) {' '.join(f'[{i}]' for i in item['source_ids'])}"
                for item in research
            )
        lines.extend(
            [
                "",
                f"Key skills: {', '.join(_flatten_key_skills(match.get('key_skills') or {}))}",
                f"Education needed: {match.get('education_needed')}",
            ]
        )

    lines.extend(["", "## Alternative Careers (the best fits at each preparation level)"])
    for item in report.get("alternative_careers") or []:
        lines.append(f"- Job Zone {item.get('target_job_zone')}: {item.get('display_title')} ({item.get('fit_label')})")

    lines.extend(["", "## Sources"])
    for source in report.get("sources") or []:
        parts = [f"[{source.get('id')}] {source.get('title')}"]
        if source.get("retrieved_section"):
            parts.append(str(source["retrieved_section"]))
        if source.get("url"):
            parts.append(str(source["url"]))
        if source.get("local_file"):
            parts.append(str(source["local_file"]))
        if source.get("note"):
            parts.append(str(source["note"]))
        lines.append("- " + " - ".join(parts))

    return "\n".join(lines).rstrip() + "\n"


def _add_interest_profiler_source(citation_manager: CitationManager) -> int:
    return citation_manager.add_source(
        title=ui_text("source.ip.title", citation_manager.language),
        source_type="local_pdf",
        url=ONET_IP_RESOURCE_URL,
        local_file="onet_interest_profiler/Interest_Profiler.pdf; data/duckdb/onet.duckdb",
        retrieved_section=ui_text("source.ip.section", citation_manager.language),
        note=ui_text("source.ip.note", citation_manager.language, short_form=IP_SHORT_FORM_URL, rule=IP_MATCHING_RULE_URL),
    )


def _build_profile_used(profile_input: dict[str, Any], ip_marker: str, language: str = "en") -> dict[str, Any]:
    is_raw_profile = "raw_riasec_scores" in profile_input
    prepared = prepare_profile_for_rag(profile_input) if is_raw_profile else dict(profile_input)

    raw_scores = prepared.get("riasec_scores") or {}
    raw_scores = {interest: int(raw_scores.get(interest, 0)) for interest in RIASEC_INTERESTS}
    initial_holland = (
        profile_input.get("initial_holland_code")
        if is_raw_profile
        else prepared.get("holland_code")
    )
    initial_holland = str(initial_holland or prepared.get("holland_code") or "")

    followup_refinement = profile_input.get("followup_refinement") or {} if is_raw_profile else {}
    questions_asked = list(followup_refinement.get("questions_asked") or [])
    final_refinement = (followup_refinement.get("final_refinement") or {}) if questions_asked else {}
    raw_sub_preferences = list(
        profile_input.get("preferences_used")
        or final_refinement.get("key_sub_preferences")
        or []
    )

    sub_preferences = _dedupe_text(raw_sub_preferences) or _normalize_sub_preferences(raw_sub_preferences)
    initial_top = list(prepared.get("top_interests") or [])
    final_top = list(final_refinement.get("refined_top_interests") or initial_top)
    final_holland = make_holland_code(final_top[:3]) if final_top else str(prepared.get("holland_code") or "")

    guidance = final_refinement.get("career_matching_guidance") or {}
    current_job_zone = int(prepared.get("current_job_zone") or 0)
    future_job_zone = int(prepared.get("future_job_zone") or 0)
    return {
        "profile_id": profile_input.get("profile_id"),
        "timestamp": profile_input.get("timestamp"),
        "riasec_scores": raw_scores,
        "top_interests": initial_top[:3],
        "holland_code": initial_holland,
        "initial_code": initial_holland,
        "initial_holland_code": initial_holland,
        "final_top_interests": final_top[:3],
        "refined_interests": final_top[:3],
        "final_code": final_holland,
        "final_holland_code": final_holland,
        "current_zone": current_job_zone,
        "future_zone": future_job_zone,
        "current_job_zone": current_job_zone,
        "future_job_zone": future_job_zone,
        "preferences_used": sub_preferences,
        "sub_preferences": sub_preferences,
        "followup_answers": questions_asked,
        "followup_answer_text": _followup_answer_text(questions_asked),
        "future_vision_summary": str(final_refinement.get("future_vision_summary") or "").strip(),
        "concerns_noted": list(final_refinement.get("concerns_noted") or []),
        # The follow-up agent's note is one fixed sentence, so it is shown from the template in `language`.
        "career_matching_guidance": ui_text(
            "report.guidance.followup" if guidance.get("notes")
            else "report.guidance.department" if profile_input.get("department") else "report.guidance.default",
            language,
        ),
        "profile_citation": ip_marker,
        "liked_activity_ids": list(profile_input.get("liked_activity_ids") or []),
        **({"department": profile_input["department"]} if profile_input.get("department") else {}),
    }


def _followup_answer_text(questions_asked: list[dict[str, Any]]) -> str:
    parts = []
    for item in questions_asked:
        question = str(item.get("question") or "").strip()
        answer = str(item.get("answer") or "").strip()
        if answer:
            parts.append(f"{question} {answer}".strip())
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def _candidate_groups_from_profile(
    profile_input: dict[str, Any],
    profile_used: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return report candidates split into current-zone and future-zone pools, or one department pool (ROADMAP 9.1)."""
    profile_used = profile_used or {}
    if profile_input.get("department"):
        return [
            {
                "label": "Careers from your department",
                "job_zone": None,
                "limit": 10,
                "candidates": _candidate_records_for_department(profile_input),
            }
        ]
    try:
        current_zone = int(profile_input.get("current_job_zone") or profile_used.get("current_job_zone") or 0)
        future_zone = int(profile_input.get("future_job_zone") or profile_used.get("future_job_zone") or 0)
    except (TypeError, ValueError):
        current_zone = int(profile_used.get("current_job_zone") or 0)
        future_zone = int(profile_used.get("future_job_zone") or 0)

    return [
        {
            "label": "Current Job Zone options",
            "job_zone": current_zone,
            "limit": 5,
            "candidates": _candidate_records_for_zone(profile_input, current_zone),
        },
        {
            "label": "Future Job Zone options",
            "job_zone": future_zone,
            "limit": 5,
            "candidates": _candidate_records_for_zone(profile_input, future_zone),
        },
    ]


def _candidate_records_for_zone(
    profile_input: dict[str, Any],
    zone: int,
) -> list[dict[str, Any]]:
    if zone not in {1, 2, 3, 4, 5}:
        return []

    followup_questions = list((profile_input.get("followup_refinement") or {}).get("questions_asked") or [])
    final_ranked = profile_input.get("final_ranked_matches") or profile_input.get("refined_career_matches") or []
    records = [
        {**item, "career_title": str(item.get("career_title") or item.get("title") or "").strip()}
        for item in final_ranked
        if (
            isinstance(item, dict)
            and str(item.get("career_title") or item.get("title") or "").strip()
            and _safe_int(item.get("job_zone")) == zone
        )
    ]

    if followup_questions and not final_ranked:
        raise RuntimeError(
            "Follow-up answers exist, but refined/final ranked matches are missing. "
            "Finish or recompute the follow-up refinement before generating the report."
        )

    career_matches = profile_input.get("career_matches") or {}
    for key in ("current_zone", "future_zone"):
        for career in career_matches.get(key, []) or []:
            if _safe_int(career.get("job_zone")) == zone:
                records.append({**career, "career_title": str(career.get("career_title") or "").strip()})

    if not records:
        prepared = prepare_profile_for_rag(profile_input) if "raw_riasec_scores" in profile_input else dict(profile_input)
        records.extend(
            {"career_title": str(title).strip(), "job_zone": zone}
            for title in prepared.get("career_titles_to_retrieve") or []
        )

    return _dedupe_candidate_records(records)


def _candidate_records_for_department(profile_input: dict[str, Any]) -> list[dict[str, Any]]:
    """The department's careers: the follow-up order if there is one, else the order by fit."""
    final_ranked = profile_input.get("final_ranked_matches") or profile_input.get("refined_career_matches") or []
    records = final_ranked or (profile_input.get("career_matches") or {}).get("department") or []
    return _dedupe_candidate_records(
        [{**item, "career_title": str(item.get("career_title") or "").strip()} for item in records if isinstance(item, dict)]
    )


def _dedupe_candidate_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped = []
    for record in records:
        title = str(record.get("career_title") or record.get("title") or "").strip()
        if not title:
            continue
        key = _title_key(title)
        if key in seen:
            continue
        seen.add(key)
        deduped.append({**record, "career_title": title})
    return deduped


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _title_key(title: Any) -> str:
    return re.sub(r"\s+", " ", str(title or "").strip()).lower()


def _build_match(
    rank: int,
    display_title: str,
    resolution: dict[str, Any],
    details: dict[str, Any],
    profile_used: dict[str, Any],
    citation_manager: CitationManager,
    match_group: str = "",
    target_job_zone: Any = None,
    fit: Any = None,
    interest_similarity: Any = None,
    language: str = "en",
) -> dict[str, Any]:
    resolved_title = str(resolution.get("resolved_onet_title") or details.get("occupation_title"))
    soc_code = str(resolution.get("onet_soc_code") or details.get("onet_soc_code"))
    ai_impact = build_ai_impact_for_occupation(
        onet_soc_code=soc_code,
        onet_tasks=details.get("task_records") or [
            _strip_marker(item) for item in details.get("tasks", [])
        ],
        citation_manager=citation_manager,
    )
    alias_note = ""
    if display_title != resolved_title:
        alias_note = ui_text(
            "report.resolution_note",
            language,
            display_title=content_text(display_title, language),
            resolved_title=content_text(resolved_title, language),
        )

    return {
        "rank": rank,
        "display_title": display_title,
        "resolved_onet_title": resolved_title,
        "onet_soc_code": soc_code,
        "alias_resolution": resolution,
        "resolution_note": alias_note,
        # O*NET's fit band for this Job Zone (ip_career_matcher.onet_fit_list), not a made-up score.
        "fit_label": fit,
        "interest_similarity": interest_similarity,
        "match_group": match_group,
        "target_job_zone": target_job_zone,
        "why_it_fits": _why_it_fits(soc_code, profile_used, language),
        "onet_details": details,
        "ai_impact": ai_impact,
        "key_skills": _key_skills(details),
        "education_needed": _education_needed(details),
    }


ALTERNATIVE_JOB_ZONES = (2, 3, 4, 5)  # O*NET 30.3 stores Job Zones 1 and 2 as one, "1-2"
ALTERNATIVES_PER_ZONE = 3


def _build_alternatives_by_level(
    profile_for_rag: dict[str, Any],
    profile_used: dict[str, Any],
    used_soc_codes: set[str],
    citation_manager: CitationManager,
    language: str = "en",
) -> list[dict[str, Any]]:
    """The best fits outside the top matches at every preparation level, from no degree to graduate school,
    by O*NET's rule (Best, Great, then Good fit; never a negative r). Full career entries, without the
    department line in "why it fits"."""
    scores = profile_for_rag.get("riasec_scores") or profile_for_rag.get("raw_riasec_scores") or {}
    profile = {key: value for key, value in profile_used.items() if key != "department"}
    alternatives: list[dict[str, Any]] = []
    for zone in ALTERNATIVE_JOB_ZONES:
        candidates = [
            candidate
            for candidate in onet_fit_list(scores, load_zone_occupations(zone, DB_PATH))
            if candidate["onet_soc_code"] not in used_soc_codes
        ][:ALTERNATIVES_PER_ZONE]
        for candidate in candidates:
            code = str(candidate["onet_soc_code"])
            details = get_onet_occupation_details(code, citation_manager)
            if not details.get("description"):
                continue
            match = _build_match(
                rank=len(alternatives) + 1,
                display_title=candidate["career_title"],
                resolution={"onet_soc_code": code, "resolved_onet_title": candidate["career_title"]},
                details=details,
                profile_used=profile,
                citation_manager=citation_manager,
                match_group=f"job_zone_{zone}",
                target_job_zone=zone,
                fit=candidate.get("fit"),
                interest_similarity=candidate.get("interest_similarity"),
                language=language,
            )
            alternatives.append(match)
    return alternatives


def _fetch_task_records(conn: Any, code: str, limit: int) -> list[dict[str, Any]]:
    rows = conn.execute(TASKS_BY_IMPORTANCE_SQL, [code, limit]).fetchall()
    records = []
    seen_tasks: set[str] = set()
    for task_id, task, task_type in rows:
        task_text = re.sub(r"\s+", " ", str(task or "")).strip()
        if not task_text:
            continue
        task_key = task_text.lower()
        if task_key in seen_tasks:
            continue
        seen_tasks.add(task_key)
        records.append(
            {
                "onet_soc_code": str(code),
                "task_id": _task_id_string(task_id),
                "task": task_text,
                "task_type": re.sub(r"\s+", " ", str(task_type or "")).strip() or None,
            }
        )
    return records


def _fetch_element_names(conn: Any, table_name: str, code: str, limit: int) -> list[str]:
    rows = conn.execute(
        f"""
        SELECT cmr.element_name
        FROM {table_name} AS item
        JOIN content_model_reference AS cmr
            ON item.element_id = cmr.element_id
        WHERE item.onetsoc_code = ?
            AND item.scale_id = 'IM'
        ORDER BY item.data_value DESC, cmr.element_name
        LIMIT ?
        """,
        [code, limit],
    ).fetchall()
    return _dedupe_text(row[0] for row in rows)


def _fetch_education_levels(conn: Any, code: str, limit: int) -> list[dict[str, Any]]:
    """The most common answers to O*NET's "required level of education" question, with category numbers."""
    rows = conn.execute(
        """
        SELECT CAST(e.category AS INTEGER), ec.category_description, e.data_value
        FROM education AS e
        LEFT JOIN education_categories AS ec
            ON e.element_id = ec.element_id
            AND e.scale_id = ec.scale_id
            AND e.category = ec.category
        WHERE e.onetsoc_code = ?
            AND ec.category_description IS NOT NULL
        ORDER BY e.data_value DESC
        LIMIT ?
        """,
        [code, limit],
    ).fetchall()
    return [
        {"category": category, "label": str(description), "percent": float(data_value)}
        for category, description, data_value in rows
        if description
    ]


def _fetch_job_zone(conn: Any, code: str, citation: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT
            CAST(jz.job_zone AS INTEGER),
            jzr.name,
            jzr.experience,
            jzr.education,
            jzr.job_training
        FROM job_zones AS jz
        LEFT JOIN job_zone_reference AS jzr
            ON jz.job_zone = jzr.job_zone
        WHERE jz.onetsoc_code = ?
        LIMIT 1
        """,
        [code],
    ).fetchone()
    if not row:
        return {}
    return {
        "zone": int(row[0]),
        "name": _with_marker(row[1], citation),
        "experience": _with_marker(row[2], citation),
        "education": _with_marker(row[3], citation),
        "training": _with_marker(row[4], citation),
    }


def _fetch_work_context(conn: Any, code: str, limit: int) -> list[str]:
    rows = conn.execute(
        """
        SELECT cmr.element_name, wcc.category_description
        FROM work_context AS wc
        JOIN content_model_reference AS cmr
            ON wc.element_id = cmr.element_id
        LEFT JOIN work_context_categories AS wcc
            ON wc.element_id = wcc.element_id
            AND wc.scale_id = wcc.scale_id
            AND wc.category = wcc.category
        WHERE wc.onetsoc_code = ?
        ORDER BY wc.data_value DESC
        LIMIT ?
        """,
        [code, limit],
    ).fetchall()
    values = []
    for name, category in rows:
        if category:
            values.append(f"{name}: {category}")
        else:
            values.append(str(name))
    return _dedupe_text(values)


def _fetch_software(conn: Any, code: str, limit: int) -> list[str]:
    rows = conn.execute(
        """
        SELECT DISTINCT workplace_example, in_demand
        FROM software_skills
        WHERE onetsoc_code = ?
            AND workplace_example IS NOT NULL
        ORDER BY
            CASE WHEN UPPER(COALESCE(in_demand, '')) = 'Y' THEN 0 ELSE 1 END,
            workplace_example
        LIMIT ?
        """,
        [code, limit],
    ).fetchall()
    values = []
    for skill, in_demand in rows:
        text = str(skill or "").strip()
        if not text:
            continue
        if str(in_demand or "").strip().upper() == "Y":
            text += " (In demand)"
        values.append(text)
    return _dedupe_text(values)


def _fetch_related(conn: Any, code: str, limit: int) -> list[str]:
    rows = conn.execute(
        """
        SELECT related_title.title
        FROM related_occupations AS related
        JOIN occupation_data AS related_title
            ON related.related_onetsoc_code = related_title.onetsoc_code
        WHERE related.onetsoc_code = ?
        ORDER BY related.related_index, related_title.title
        LIMIT ?
        """,
        [code, limit],
    ).fetchall()
    return _dedupe_text(row[0] for row in rows)


def _normalize_sub_preferences(values: list[Any]) -> list[str]:
    text = " ".join(str(item) for item in values).lower()
    preferences = []
    if not text.strip():
        return []
    if "technology" in text or "tech" in text:
        preferences.append("technology")
    if "data" in text or "math" in text or "analyt" in text or "problem" in text or "technology" in text:
        preferences.append("math and analytical work")
        preferences.append("analytical thinking and problem solving")
    if "fast" in text or "multiple projects" in text or "short time" in text:
        preferences.append("fast-paced short projects")
    if "start" in text or "own thing" in text or "entrepreneur" in text:
        preferences.append("starting own thing")
    if "teaching" in text or "guiding" in text or "listen" in text:
        preferences.append("teaching/guiding with some listening")
    if "social" in text or "people" in text or "teaching" in text:
        preferences.append("lower social interaction than people-heavy careers")
    if "ai" in text:
        preferences.append("AI-aware career planning")
    return _dedupe_text(preferences)


def _core_skills_from_matches(top_matches: list[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for match in top_matches:
        details = match.get("onet_details") or {}
        values.extend(_strip_marker(item) for item in details.get("skills") or [])
        values.extend(_strip_marker(item) for item in details.get("knowledge") or [])
    return _dedupe_text(values)[:10]


def _career_top_interests(onet_soc_code: str) -> list[str]:
    """The career's two strongest interest areas in O*NET's interest profile (scale OI)."""
    import duckdb

    conn = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        rows = conn.execute(
            """
            SELECT r.element_name, i.data_value FROM career_interest_types AS i
            JOIN content_model_reference AS r ON r.element_id = i.element_id
            WHERE i.onetsoc_code = ? AND i.scale_id = 'OI'
            ORDER BY i.data_value DESC, r.element_name
            """,
            [onet_soc_code],
        ).fetchall()
    finally:
        conn.close()
    return [name for name, _ in rows if name in RIASEC_INTERESTS][:2]


def _why_it_fits(onet_soc_code: str, profile_used: dict[str, Any], language: str = "en") -> list[str]:
    """Why this career is on the student's list, from their own answers (ROADMAP 9.4)."""
    marker = profile_used.get("profile_citation") or ""
    student = list(profile_used.get("final_top_interests") or profile_used.get("top_interests") or [])
    career = _career_top_interests(onet_soc_code)
    names = lambda areas: ", ".join(interest_label(area, language) for area in areas)  # noqa: E731
    bullets = []
    if career:
        shared = [area for area in career if area in student]
        key = ("report.why.interests_shared" if len(shared) == len(career)
               else "report.why.interests_one" if shared else "report.why.interests_other")
        bullets.append(ui_text(key, language, career=names(career), shared=names(shared), student=names(student), marker=marker))
        liked = set(profile_used.get("liked_activity_ids") or [])
        questions = load_interest_profiler_questions(QUESTIONS_PATH)
        activities = [  # the career's strongest area first
            question_text(question, language)
            for area in career
            for question in questions
            if question["id"] in liked and question["area"] == area
        ][:3]
        if activities:
            bullets.append(ui_text("report.why.activities", language, activities="; ".join(f"“{a}”" for a in activities)))
    if profile_used.get("department"):
        bullets.append(ui_text("report.why.department", language))

    # what the follow-up answers added (ROADMAP 2.4)
    preferences = set(profile_used.get("sub_preferences") or [])
    preference_text = " ".join(preferences).lower()
    if "technology" in preferences or "technology" in preference_text:
        bullets.append(ui_text("report.why.technology", language, marker=marker))
    if (
        "math and analytical work" in preferences
        or "analytical thinking and problem solving" in preferences
        or "data" in preference_text
        or "research" in preference_text
        or "problem" in preference_text
    ):
        bullets.append(ui_text("report.why.analytical", language))
    if "fast-paced short projects" in preferences or "fast-paced" in preference_text:
        bullets.append(ui_text("report.why.fast_paced", language))
    if "starting own thing" in preferences or "leading" in preference_text:
        bullets.append(ui_text("report.why.own_thing", language))
    if "lower social interaction than people-heavy careers" in preferences or "lower social" in preference_text:
        bullets.append(ui_text("report.why.lower_social", language))
    return bullets[:5]


def _key_skills(details: dict[str, Any]) -> dict[str, list[str]]:
    raw_skills = list(details.get("skills") or [])
    software = _dedupe_text(details.get("software") or [])[:16]
    knowledge = _dedupe_text(details.get("knowledge") or [])[:8]

    foundational = []
    technical = []
    for skill in raw_skills:
        key = _strip_marker(skill).lower()
        if key in FOUNDATIONAL_SOFT_SKILLS:
            foundational.append(skill)
        else:
            technical.append(skill)

    return {
        "software_tools": software,
        "technical_and_domain": _dedupe_text(technical)[:10],
        "foundational_communication": _dedupe_text(foundational)[:8],
        "knowledge_areas": knowledge,
    }


def _flatten_key_skills(grouped: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in (
        "software_tools",
        "technical_and_domain",
        "knowledge_areas",
        "foundational_communication",
    ):
        values.extend(str(item) for item in grouped.get(key) or [])
    return _dedupe_text(values)[:18]


def _education_needed(details: dict[str, Any]) -> str:
    job_zone = details.get("job_zone") or {}
    zone = job_zone.get("zone")
    education_summary = _education_needed_from_percentages(details.get("education_levels") or [])
    if education_summary:
        return education_summary
    zone_education = _strip_marker(job_zone.get("education") or "")
    if zone and zone_education:
        explanation = job_zone_preparation(zone, "en")
        return (
            f"O*NET places this occupation in Job Zone {job_zone_number(zone)} ({explanation}). "
            f"Typical preparation: {zone_education}"
        )
    return "Education information was limited in the retrieved O*NET rows."


def _education_needed_from_percentages(education_levels: list[dict[str, Any]]) -> str:
    if not education_levels:
        return ""
    leading = sorted(education_levels, key=lambda item: item["percent"], reverse=True)[:2]
    return _plain_education_needed_summary(leading)


def _plain_education_needed_summary(entries: list[dict[str, Any]]) -> str:
    positive_entries = [entry for entry in entries if entry["percent"] > 0]
    if not positive_entries:
        return ""
    top_label = positive_entries[0]["label"]
    top_level = education_level(positive_entries[0]["category"])
    levels = {education_level(entry["category"]) for entry in positive_entries}
    if top_level == "master":
        if "bachelor" in levels:
            return (
                "Most O*NET responses point to a master's degree for this role; "
                "bachelor's-degree paths are present but less common."
            )
        return "Most O*NET responses point to a master's degree for this role."
    if top_level == "bachelor":
        if "master" in levels:
            return (
                "Most O*NET responses point to a bachelor's degree; "
                "master's-level preparation is also common."
            )
        return "Most O*NET responses point to a bachelor's degree for this role."
    if top_level == "doctoral":
        return "Most O*NET responses point to doctoral or professional-degree preparation for this role."
    if top_level == "associate":
        return "Most O*NET responses point to associate-degree or vocational preparation for this role."
    if top_level == "high_school":
        return "Most O*NET responses point to high-school-level preparation for this role."
    return f"Most O*NET responses point to {top_label.lower()} for this role."


def education_level(category: Any) -> str:
    """Level of an O*NET education answer by its category number (1-12, same on scales RL and RQ).

    By number, not by words: 30.3 described category 3 as "Post-Secondary Certificate -
    awarded for training completed after high school ...", which a word search took for
    high school, and "Post-Master's Certificate" (9) contains "master" (ROADMAP 2.10).
    """
    try:
        return EDUCATION_LEVELS.get(int(category), "other")
    except (TypeError, ValueError):
        return "other"


def _with_marker(value: Any, marker: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    if marker and marker not in text:
        return f"{text} {marker}"
    return text


def _with_marker_list(values: list[str], marker: str) -> list[str]:
    return [_with_marker(value, marker) for value in values if str(value or "").strip()]


def _strip_marker(value: Any) -> str:
    return re.sub(r"\s*\[\d+\]\s*$", "", str(value or "")).strip()


def _onet_summary_url(onet_soc_code: str) -> str:
    return f"https://www.onetonline.org/link/summary/{str(onet_soc_code).strip()}"


def _task_id_string(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if re.fullmatch(r"\d+\.0+", text):
        return text.split(".", 1)[0]
    return text


def _dedupe_text(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result

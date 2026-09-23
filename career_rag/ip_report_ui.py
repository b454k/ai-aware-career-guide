"""Streamlit rendering helpers for the final Interest Profiler career report."""

from __future__ import annotations

import re
from html import escape
from typing import Any

import streamlit as st

from career_rag.ip_final_report import FOUNDATIONAL_SOFT_SKILLS
from career_rag.ui_i18n import (
    claude_usage_lines,
    display_label,
    dynamic_list,
    dynamic_text,
    dynamic_translation_available,
    interest_label,
    job_zone_number,
    job_zone_preparation,
    month_label,
    normalize_language,
    ui_text,
)


def _render_report_styles() -> None:
    st.markdown(
        """
        <style>
        .report-cover {
            border: 1px solid #2a2a2f;
            border-radius: 8px;
            background: #141416;
            padding: 1rem;
            margin: 0.75rem 0 1rem;
        }
        .report-cover h2,
        .match-title {
            color: #ffffff;
            font-size: 1.25rem;
            line-height: 1.15;
            font-weight: 850;
            margin: 0;
        }
        .report-muted {
            color: #a4a4aa;
            line-height: 1.45;
            margin: 0.45rem 0 0;
        }
        .report-kicker {
            color: #a4a4aa;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.45rem;
        }
        .report-stat-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.55rem;
            margin-top: 0.85rem;
        }
        .report-stat {
            border: 1px solid #2a2a2f;
            border-radius: 8px;
            background: #1b1b1e;
            padding: 0.65rem 0.55rem;
            min-width: 0;
        }
        .report-stat-label {
            color: #a4a4aa;
            font-size: 0.66rem;
            font-weight: 800;
            text-transform: uppercase;
        }
        .report-stat-value {
            color: #ffffff;
            font-size: 0.95rem;
            font-weight: 850;
            margin-top: 0.2rem;
            overflow-wrap: anywhere;
        }
        .report-stat-detail {
            color: #a4a4aa;
            font-size: 0.72rem;
            line-height: 1.3;
            margin-top: 0.2rem;
        }
        .report-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.38rem;
            margin-top: 0.75rem;
        }
        .report-chip,
        .impact-badge {
            display: inline-flex;
            align-items: center;
            border: 1px solid #3a3a40;
            border-radius: 999px;
            padding: 0.22rem 0.55rem;
            color: #ffffff;
            background: #202024;
            font-size: 0.74rem;
            font-weight: 800;
            line-height: 1.2;
        }
        .match-card {
            border: 1px solid #2a2a2f;
            border-radius: 8px;
            background: #141416;
            padding: 1rem;
            margin: 0.75rem 0 0.45rem;
        }
        .match-topline {
            display: flex;
            justify-content: space-between;
            gap: 0.75rem;
            align-items: flex-start;
        }
        .match-rank {
            color: #a4a4aa;
            font-size: 0.8rem;
            font-weight: 850;
            white-space: nowrap;
        }
        .match-reason {
            color: #d6d6da;
            line-height: 1.45;
            margin: 0.75rem 0 0;
            font-size: 0.92rem;
        }
        .report-group-label {
            color: #ffffff;
            font-size: 0.9rem;
            font-weight: 850;
            margin: 1rem 0 0.25rem;
        }
        .impact-covered {
            background: #f4f4f5;
            border-color: #f4f4f5;
            color: #050505;
        }
        .impact-not-covered,
        .impact-no-data {
            background: #242428;
            border-color: #4a4a50;
            color: #f4f4f5;
        }
        .report-section-rule {
            border-top: 1px solid #2a2a2f;
            margin: 1rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _html(value: Any) -> str:
    return escape(str(value or ""))


def _report_stat_html(label: str, value: Any, detail: str = "") -> str:
    detail_html = f"<div class='report-stat-detail'>{_html(detail)}</div>" if detail else ""
    return (
        "<div class='report-stat'>"
        f"<div class='report-stat-label'>{_html(label)}</div>"
        f"<div class='report-stat-value'>{_html(value)}</div>"
        f"{detail_html}"
        "</div>"
    )


def _chip_html(label: Any, class_name: str = "report-chip") -> str:
    return f"<span class='{class_name}'>{_html(label)}</span>"


def _impact_badge_html(level: str, language: str = "en") -> str:
    css_level = re.sub(r"[^a-z]+", "-", str(level or "unavailable").lower()).strip("-") or "unavailable"
    return _chip_html(display_label(level, language), f"impact-badge impact-{css_level}")


def render_final_career_report(report: dict[str, Any], language: str = "en") -> None:
    """Render the final career report in a clean tabbed Streamlit layout."""
    if not report:
        st.info(ui_text("report.no_final", language))
        return
    _render_report_styles()
    if normalize_language(language) == "tr" and not dynamic_translation_available(language):
        st.warning(ui_text("translation.unavailable", language))

    _render_report_cover(report, language)

    tabs = st.tabs(
        [
            ui_text("report.tab.summary", language),
            ui_text("report.tab.top_matches", language),
            ui_text("report.tab.alternatives", language),
            ui_text("report.tab.sources", language),
        ]
    )

    with tabs[0]:
        _render_summary(report, language)
    with tabs[1]:
        _render_top_matches(report, language)
    with tabs[2]:
        _render_alternatives(report, language)
    with tabs[3]:
        _render_sources(report, language)


def _render_report_cover(report: dict[str, Any], language: str = "en") -> None:
    profile = report.get("profile_used") or {}
    top_interests = profile.get("final_top_interests") or profile.get("top_interests") or []
    chips = "".join(_chip_html(interest_label(item, language)) for item in top_interests[:3])
    stats = "".join(
        [
            _report_stat_html(
                ui_text("report.summary.final_code", language),
                profile.get("final_holland_code") or profile.get("holland_code") or "",
            ),
            # Number large, education text small: the full zone title did not fit a third of a phone.
            _report_stat_html(
                ui_text("report.summary.current_zone", language),
                job_zone_number(profile.get("current_job_zone")),
                job_zone_preparation(profile.get("current_job_zone"), language),
            ),
            _report_stat_html(
                ui_text("report.summary.future_zone", language),
                job_zone_number(profile.get("future_job_zone")),
                job_zone_preparation(profile.get("future_job_zone"), language),
            ),
        ]
    )
    st.markdown(
        (
            "<div class='report-cover'>"
            f"<div class='report-kicker'>{_html(ui_text('final.header', language))}</div>"
            f"<h2>{_html(ui_text('report.summary.header', language))}</h2>"
            f"<div class='report-chip-row'>{chips}</div>"
            f"<div class='report-stat-grid'>{stats}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_summary(report: dict[str, Any], language: str = "en") -> None:
    profile = report.get("profile_used") or {}
    st.subheader(ui_text("report.summary.header", language))

    top_interests = profile.get("final_top_interests") or profile.get("top_interests") or []
    chips = "".join(_chip_html(interest_label(item, language)) for item in top_interests[:3])
    stats = "".join(
        [
            _report_stat_html(
                ui_text("report.summary.final_code", language),
                profile.get("final_holland_code", ""),
            ),
            # Number large, education text small: the full zone title did not fit a third of a phone.
            _report_stat_html(
                ui_text("report.summary.current_zone", language),
                job_zone_number(profile.get("current_job_zone")),
                job_zone_preparation(profile.get("current_job_zone"), language),
            ),
            _report_stat_html(
                ui_text("report.summary.future_zone", language),
                job_zone_number(profile.get("future_job_zone")),
                job_zone_preparation(profile.get("future_job_zone"), language),
            ),
        ]
    )
    st.markdown(
        (
            "<div class='report-cover'>"
            f"<div class='report-kicker'>{_html(ui_text('report.summary.top_interests', language))}</div>"
            f"<div class='report-chip-row'>{chips}</div>"
            f"<div class='report-stat-grid'>{stats}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    preferences = profile.get("sub_preferences") or []
    if preferences:
        st.markdown(f"**{ui_text('report.summary.preferences', language)}**")
        _render_grouped_preferences(preferences, language)
    if profile.get("career_matching_guidance"):
        st.caption(dynamic_text(profile["career_matching_guidance"], language, "career matching guidance"))


def _render_top_matches(report: dict[str, Any], language: str = "en") -> None:
    st.subheader(ui_text("report.top_matches.header", language))
    matches = report.get("top_matches") or []
    st.caption(ui_text("report.top_matches.caption", language))

    for group_label, group_matches in _group_top_matches(matches):
        if group_label:
            st.markdown(
                f"<div class='report-group-label'>{_html(display_label(group_label, language))}</div>",
                unsafe_allow_html=True,
            )
        for match in group_matches:
            _render_match_card(match, language)
            with st.expander(ui_text("report.top_matches.detail_card", language)):
                _render_job_detail(match, language)


def _render_match_card(match: dict[str, Any], language: str = "en") -> None:
    title = _match_display_title(match, language)
    rank = match.get("rank") or ""
    fit_label = _format_fit_value(match.get("fit_label") or match.get("fit_score"), language)
    impact_level = _ai_level_for_match(match)
    reason = ""
    reasons = match.get("why_it_fits") or []
    if reasons:
        reason = dynamic_text(_without_citations(reasons[0]), language, "career match reason")
    details = match.get("onet_details") or {}
    zone = _job_zone_title((details.get("job_zone") or {}).get("zone") or match.get("target_job_zone"), language)
    st.markdown(
        (
            "<div class='match-card'>"
            "<div class='match-topline'>"
            "<div>"
            f"<div class='report-kicker'>{_html(zone)}</div>"
            f"<div class='match-title'>{_html(title)}</div>"
            "</div>"
            f"<div class='match-rank'>#{_html(rank)}</div>"
            "</div>"
            "<div class='report-chip-row'>"
            f"{_chip_html(fit_label)}"
            f"{_impact_badge_html(impact_level, language)}"
            "</div>"
            f"<p class='match-reason'>{_html(reason)}</p>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    if match.get("resolution_note"):
        st.caption(dynamic_text(match["resolution_note"], language, "career title resolution note"))


def _render_job_detail(match: dict[str, Any], language: str = "en") -> None:
    details = match.get("onet_details") or {}
    reasons = match.get("why_it_fits") or []
    if reasons:
        st.markdown(f"**{ui_text('report.top_matches.fit', language)}**")
        _write_bullets(reasons, language)
        _write_source_indexes(reasons)

    st.markdown(f"**{ui_text('report.job.what_does', language)}**")
    description = details.get("description") or ui_text("report.job.no_description", language)
    st.write(dynamic_text(_without_citations(description), language, "O*NET occupation description"))
    _write_source_indexes(description)

    st.markdown(f"**{ui_text('report.job.ai_impact', language)}**")
    _render_ai_summary(match, language)
    _render_ai_table(match, language)
    _render_claude_usage(match, language)

    st.markdown(f"**{ui_text('report.job.main_tasks', language)}**")
    tasks = details.get("tasks") or []
    _write_bullets(tasks, language)
    _write_source_indexes(tasks)

    st.markdown(f"**{ui_text('report.job.key_skills', language)}**")
    _render_key_skills(match, language)

    st.markdown(f"**{ui_text('report.job.education_zone', language)}**")
    _render_education_job_zone(match, language)

    _render_next_steps_if_available(match, language)

    st.markdown(f"**{ui_text('report.job.day_life', language)}**")
    day_text = match.get("day_in_the_life") or ""
    if day_text:
        st.info(dynamic_text(_clean_day_text(day_text), language, "day-in-the-life career narrative"))
        _write_source_indexes([day_text, details.get("tasks") or [], details.get("work_context") or []])


def _render_ai_summary(match: dict[str, Any], language: str = "en") -> None:
    ai_impact = match.get("ai_impact") or {}
    level = _ai_level_for_match(match)
    summary = ai_impact.get("future_outlook_summary") or ""
    st.markdown(_impact_badge_html(level, language), unsafe_allow_html=True)
    if summary:
        st.write(dynamic_text(_without_citations(summary), language, "AI-impact summary"))
        _write_source_indexes(summary)
    elif ai_impact.get("task_breakdown"):
        st.caption(ui_text("report.ai.caption", language))
    else:
        st.info(ui_text("report.ai.no_rows", language))


def _render_next_steps_if_available(match: dict[str, Any], language: str = "en") -> None:
    values = (
        match.get("roadmap")
        or match.get("next_steps")
        or match.get("skills_to_learn")
        or match.get("learning_plan")
        or []
    )
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list) or not values:
        return
    st.markdown("**Next Steps**")
    _write_bullets(values, language)


def _render_ai_table(match: dict[str, Any], language: str = "en") -> None:
    rows = []
    for item in match.get("ai_impact", {}).get("task_breakdown") or []:
        score = item.get("score_display")
        if not score:
            score = ui_text("common.na", language) if item.get("score") is None else item.get("score")
        rows.append(
            {
                ui_text("report.ai.table.task", language): dynamic_text(
                    item.get("task"), language, "AI-impact task"
                ),
                ui_text("report.ai.table.signal", language): display_label(
                    item.get("ai_coverage"), language
                ),
                ui_text("report.ai.table.score", language): score,
                ui_text("report.ai.table.source", language): _format_source_ids(item.get("source_ids") or []),
            }
        )
    if rows:
        _render_stacked_rows(rows)
        st.caption(ui_text("report.ai.caption", language))
    else:
        st.info(ui_text("report.ai.no_rows", language))


def _render_claude_usage(match: dict[str, Any], language: str = "en") -> None:
    usage = (match.get("ai_impact") or {}).get("claude_usage")
    if not usage:
        return
    st.markdown(f"**{ui_text('report.usage.title', language, month=month_label(usage['month'], language))}**")
    for line in claude_usage_lines(usage, language):  # already in the chosen language
        st.write(f"- {line}")
    st.caption(_format_source_ids(usage.get("source_ids") or []))


def _render_alternatives(report: dict[str, Any], language: str = "en") -> None:
    st.subheader(ui_text("report.alternatives.header", language))
    alternatives = report.get("alternative_careers") or []
    if not alternatives:
        st.info(ui_text("report.alternatives.none", language))
        return
    source_map = _source_map(report)
    for item in alternatives[:5]:
        zone = _job_zone_title((item.get("job_zone") or {}).get("zone"), language)
        source_links = _source_links(item, source_map)
        title = dynamic_text(item.get("title"), language, "alternative career title")
        st.markdown(
            (
                "<div class='match-card'>"
                f"<div class='match-title'>{_html(title)}</div>"
                f"<p class='report-muted'>{_html(zone)}</p>"
                f"<div class='report-chip-row'>{_html(source_links)}</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )


def _render_sources(report: dict[str, Any], language: str = "en") -> None:
    st.subheader(ui_text("report.sources.header", language))
    with st.expander(ui_text("report.sources.expander", language), expanded=True):
        for source in report.get("sources") or []:
            title = dynamic_text(source.get("title"), language, "source title")
            label = f"[{source.get('id')}] {title}"
            if source.get("url"):
                st.markdown(f"**[{label}]({source['url']})**")
            else:
                st.markdown(f"**{label}**")
            if source.get("retrieved_section"):
                st.write(dynamic_text(source["retrieved_section"], language, "retrieved source section"))
            if source.get("note"):
                st.caption(dynamic_text(source["note"], language, "source note"))
            if source.get("url"):
                st.write(source["url"])


def _render_stacked_rows(rows: list[dict[str, Any]]) -> None:
    """One small card per row: the first column as text, the others as "label: value" below.

    A multi-column table does not fit the 460px phone layout (its narrow columns broke
    words letter by letter), so rows are stacked instead.
    """
    if not rows:
        return
    columns = list(rows[0])
    cards = []
    for row in rows:
        meta = "".join(
            f"<span class='stacked-meta-item'><span class='stacked-meta-label'>{escape(str(column))}:</span> "
            f"{escape(str(row.get(column) or ''))}</span>"
            for column in columns[1:]
        )
        cards.append(
            f"<div class='stacked-row'><div class='stacked-text'>{escape(str(row.get(columns[0]) or ''))}</div>"
            f"<div class='stacked-meta'>{meta}</div></div>"
        )
    st.markdown(
        (
            "<style>"
            ".stacked-row{border:1px solid #2a2a2f;border-radius:8px;background:#101012;"
            "padding:0.6rem 0.7rem;margin:0 0 0.45rem;}"
            ".stacked-text{color:#f4f4f5;font-size:0.9rem;line-height:1.4;}"
            ".stacked-meta{display:flex;flex-wrap:wrap;gap:0.25rem 0.9rem;margin-top:0.4rem;"
            "color:#d6d6da;font-size:0.8rem;}"
            ".stacked-meta-label{color:#a4a4aa;}"
            "</style>"
            + "".join(cards)
        ),
        unsafe_allow_html=True,
    )


def _write_bullets(items: list[Any], language: str = "en") -> None:
    if not items:
        st.write(ui_text("report.no_local_evidence", language))
        return
    for item in items:
        st.write(f"- {dynamic_text(_without_citations(item), language, 'report bullet')}")


def _render_key_skills(match: dict[str, Any], language: str = "en") -> None:
    grouped = match.get("key_skills") or {}
    if not grouped:
        details = match.get("onet_details") or {}
        grouped = _fallback_key_skills(details)

    ordered_groups = [
        ("software_tools", ui_text("report.skills.software", language)),
        ("technical_and_domain", ui_text("report.skills.technical", language)),
        ("foundational_communication", ui_text("report.skills.foundational", language)),
        ("knowledge_areas", ui_text("report.skills.knowledge", language)),
    ]
    rendered_any = False
    for key, label in ordered_groups:
        values = grouped.get(key) or []
        if not values:
            continue
        rendered_any = True
        st.caption(label)
        st.markdown(
            _skill_chip_html(dynamic_list(values, language, f"{label} skills")),
            unsafe_allow_html=True,
        )
        _write_source_indexes(values)
    if not rendered_any:
        st.write(ui_text("report.no_local_evidence", language))


def _render_grouped_preferences(preferences: list[Any], language: str = "en") -> None:
    grouped = _group_preferences(preferences)
    for label, values in grouped.items():
        if not values:
            continue
        st.caption(display_label(label, language))
        st.markdown(
            _skill_chip_html(dynamic_list(values, language, f"{label} preferences")),
            unsafe_allow_html=True,
        )


def _group_preferences(preferences: list[Any]) -> dict[str, list[str]]:
    groups = {
        "Tasks and tools": [],
        "Work style": [],
        "People and setting": [],
        "Career direction": [],
        "Other": [],
    }
    for preference in _dedupe_text(preferences):
        key = preference.lower()
        if any(term in key for term in ("technology", "data", "math", "analyt", "problem", "research", "ai")):
            groups["Tasks and tools"].append(preference)
        elif any(term in key for term in ("fast", "pace", "structured", "independent", "autonomy", "schedule")):
            groups["Work style"].append(preference)
        elif any(term in key for term in ("social", "people", "teaching", "guiding", "listening", "interaction")):
            groups["People and setting"].append(preference)
        elif any(term in key for term in ("own", "leading", "career", "consult", "security", "impact")):
            groups["Career direction"].append(preference)
        else:
            groups["Other"].append(preference)
    return groups


def _render_education_job_zone(match: dict[str, Any], language: str = "en") -> None:
    details = match.get("onet_details") or {}
    job_zone = details.get("job_zone") or {}
    education = _dedupe_text(details.get("education") or [])
    education_entries = _education_entries(education)

    prep_summary = _education_preparation_summary(job_zone, education_entries, language)
    if prep_summary:
        st.write(ui_text("report.education.typical", language) + prep_summary)

    training = dynamic_text(
        _clean_job_zone_training(job_zone.get("training")),
        language,
        "O*NET job zone training",
    )
    if training:
        st.write(ui_text("report.education.training", language) + training)

    if education:
        st.caption(ui_text("report.education.responses", language))
        _write_bullets([_format_education_entry(item) for item in education_entries], language)

    if not education and not prep_summary and not training:
        st.write(ui_text("report.education.none", language))
    _write_source_indexes([job_zone, education])


def _fallback_key_skills(details: dict[str, Any]) -> dict[str, list[str]]:
    skills = [_without_citations(item) for item in details.get("skills") or []]
    software = [_without_citations(item) for item in details.get("software") or []]
    knowledge = [_without_citations(item) for item in details.get("knowledge") or []]
    foundational = [item for item in skills if _skill_key(item) in FOUNDATIONAL_SOFT_SKILLS]
    technical = [item for item in skills if _skill_key(item) not in FOUNDATIONAL_SOFT_SKILLS]
    return {
        "software_tools": software,
        "technical_and_domain": technical,
        "foundational_communication": foundational,
        "knowledge_areas": knowledge,
    }


def _skill_chip_html(values: list[Any]) -> str:
    chips = []
    for value in values:
        text = _without_citations(value)
        if not text:
            continue
        chips.append(f"<span class='skill-chip'>{text}</span>")
    if not chips:
        return ""
    return (
        "<style>"
        ".skill-chip{display:inline-block;margin:0 0.35rem 0.35rem 0;"
        "padding:0.22rem 0.5rem;border:1px solid #3a3a40;"
        "border-radius:999px;background:#202024;color:#ffffff;font-size:0.86rem;"
        "font-weight:750;}"
        "</style>"
        + "".join(chips)
    )


def _match_display_title(match: dict[str, Any], language: str = "en") -> str:
    return dynamic_text(
        match.get("display_title") or ui_text("report.career_fallback", language),
        language,
        "career match title",
    )


def _format_fit_value(value: Any, language: str = "en") -> str:
    if isinstance(value, str) and value.strip():
        return display_label(value, language)
    if isinstance(value, (int, float)):
        if 0 <= float(value) <= 1:
            return f"{float(value) * 100:.0f}% fit"
        return f"{float(value):.1f}"
    return ui_text("common.na", language)


def _ai_level_for_match(match: dict[str, Any]) -> str:
    """Summarize the displayed tasks' Anthropic coverage for the career badge."""
    rows = (match.get("ai_impact") or {}).get("task_breakdown") or []
    labels = [str(row.get("ai_coverage") or "") for row in rows]
    if any(label.startswith("Covered") for label in labels):
        return "Covered"
    if "Not covered" in labels:
        return "Not covered"
    return "No data"


def _match_title(match: dict[str, Any], language: str = "en") -> str:
    title = dynamic_text(
        match.get("display_title") or ui_text("report.career_fallback", language),
        language,
        "career match title",
    )
    details = match.get("onet_details") or {}
    zone = (details.get("job_zone") or {}).get("zone")
    if zone:
        return f"{title} - {_job_zone_title(zone, language)}"
    return title


def _job_zone_detail(job_zone: dict[str, Any], language: str = "en") -> str:
    zone = job_zone.get("zone")
    name = _without_citations(job_zone.get("name") or "")
    education = _without_citations(job_zone.get("education") or "")
    training = _without_citations(job_zone.get("training") or "")
    parts = [_job_zone_title(zone, language)]
    if name:
        parts.append(dynamic_text(name, language, "O*NET job zone name"))
    if education:
        parts.append(
            ui_text(
                "report.job_zone.typical_education",
                language,
                education=dynamic_text(education, language, "O*NET job zone education"),
            )
        )
    if training:
        parts.append(
            ui_text(
                "report.job_zone.training",
                language,
                training=dynamic_text(training, language, "O*NET job zone training"),
            )
        )
    return ". ".join(parts) + "."


def _job_zone_title(zone: Any, language: str = "en") -> str:
    try:
        zone_int = int(zone)
    except (TypeError, ValueError):
        return ui_text("report.job_zone.unavailable", language)
    explanation = job_zone_preparation(zone_int, language)
    return ui_text("report.job_zone.title", language, zone=job_zone_number(zone_int), explanation=explanation)


def _group_top_matches(matches: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    groups: list[tuple[str, list[dict[str, Any]]]] = []
    seen_labels: set[str] = set()
    for match in matches:
        label = str(match.get("match_group") or "").strip()
        if label in seen_labels:
            continue
        seen_labels.add(label)
        groups.append((label, [item for item in matches if str(item.get("match_group") or "").strip() == label]))
    if groups:
        return groups
    return [("", matches)]


def _shared_match_reasons(matches: list[dict[str, Any]]) -> list[str]:
    reasons: list[Any] = []
    for match in matches:
        reasons.extend(match.get("why_it_fits") or [])
    return _dedupe_text(_normalize_shared_reason(_without_citations(reason)) for reason in reasons)[:4]


def _normalize_shared_reason(value: Any) -> str:
    text = str(value or "").strip()
    return re.sub(r"^This role is\b", "These roles are", text, flags=re.IGNORECASE)


def _clean_day_text(value: Any) -> str:
    text = _without_citations(value)
    return re.sub(r"^my inference:\s*", "", text, flags=re.IGNORECASE).strip()


def _education_entries(values: list[Any]) -> list[dict[str, Any]]:
    entries = [_parse_education_entry(value) for value in values]
    return [entry for entry in entries if entry.get("label") or entry.get("text")]


def _parse_education_entry(value: Any) -> dict[str, Any]:
    text = _without_citations(value)
    match = re.match(r"^(?P<label>.+?)\s*\((?P<number>\d+(?:\.\d+)?)%?\)$", text)
    if not match:
        return {"label": text, "percent": None, "text": text}
    number = float(match.group("number"))
    label = match.group("label").strip()
    return {"label": label, "percent": number, "text": f"{label} ({number:g}%)"}


def _format_education_entry(entry: dict[str, Any]) -> str:
    return str(entry.get("text") or entry.get("label") or "")


def _education_preparation_summary(
    job_zone: dict[str, Any],
    education_entries: list[dict[str, Any]],
    language: str = "en",
) -> str:
    entries_with_percent = [
        entry for entry in education_entries if isinstance(entry.get("percent"), (int, float))
    ]
    if entries_with_percent:
        sorted_entries = sorted(
            entries_with_percent,
            key=lambda entry: float(entry.get("percent") or 0),
            reverse=True,
        )
        positive_entries = [
            entry for entry in sorted_entries if float(entry.get("percent") or 0) > 0
        ]
        if positive_entries:
            return _plain_education_summary(positive_entries, language)

    fallback = dynamic_text(
        _clean_job_zone_education(job_zone.get("education")),
        language,
        "O*NET job zone education",
    )
    return fallback


def _is_bachelors_or_higher(label: Any) -> bool:
    text = str(label or "").lower()
    return any(term in text for term in ("bachelor", "master", "doctoral", "professional degree"))


def _plain_education_summary(entries: list[dict[str, Any]], language: str = "en") -> str:
    top = entries[0]
    top_level = _degree_level(top.get("label"))
    bachelor_entry = next((entry for entry in entries if _degree_level(entry.get("label")) == "bachelor"), None)
    master_entry = next((entry for entry in entries if _degree_level(entry.get("label")) == "master"), None)

    if top_level == "master":
        if bachelor_entry:
            return ui_text("report.education.master_with_bachelor", language)
        return ui_text("report.education.master", language)
    if top_level == "bachelor":
        if master_entry:
            return ui_text("report.education.bachelor_with_master", language)
        return ui_text("report.education.bachelor", language)
    if top_level == "doctoral":
        return ui_text("report.education.doctoral", language)
    if top_level == "associate":
        return ui_text("report.education.associate", language)
    if top_level == "high_school":
        return ui_text("report.education.high_school", language)

    label = _without_citations(top.get("label"))
    if label:
        return ui_text("report.education.dynamic", language, label=label.lower())
    return ""


def _degree_level(label: Any) -> str:
    text = str(label or "").lower()
    if "master" in text:
        return "master"
    if "bachelor" in text:
        return "bachelor"
    if "doctoral" in text or "professional degree" in text:
        return "doctoral"
    if "associate" in text or "2-year" in text:
        return "associate"
    if "high school" in text or "ged" in text:
        return "high_school"
    return "other"


def _clean_job_zone_education(value: Any) -> str:
    text = _without_citations(value)
    text = re.sub(r",?\s*but some do not\.?", ".", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


def _clean_job_zone_training(value: Any) -> str:
    text = _without_citations(value)
    return re.sub(r"\s+", " ", text).strip()


def _join_natural(values: Any) -> str:
    items = [str(value).strip() for value in values if str(value).strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return f"{', '.join(items[:-1])} and {items[-1]}"


def _without_citations(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = re.sub(r"\s*\[\d+\]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _citation_numbers(value: Any) -> list[int]:
    numbers: list[int] = []
    seen: set[int] = set()

    def collect(item: Any) -> None:
        if isinstance(item, dict):
            for nested in item.values():
                collect(nested)
            return
        if isinstance(item, (list, tuple, set)):
            for nested in item:
                collect(nested)
            return
        for raw_number in re.findall(r"\[(\d+)\]", str(item or "")):
            number = int(raw_number)
            if number not in seen:
                seen.add(number)
                numbers.append(number)

    collect(value)
    return numbers


def _write_source_indexes(value: Any) -> None:
    numbers = _citation_numbers(value)
    if numbers:
        st.caption(" ".join(f"[{number}]" for number in numbers))


def _format_source_ids(values: list[Any]) -> str:
    ids = []
    for value in values:
        try:
            source_id = int(value)
        except (TypeError, ValueError):
            continue
        ids.append(f"[{source_id}]")
    return " ".join(ids)


def _source_map(report: dict[str, Any]) -> dict[int, dict[str, Any]]:
    sources: dict[int, dict[str, Any]] = {}
    for source in report.get("sources") or []:
        try:
            source_id = int(source.get("id"))
        except (TypeError, ValueError):
            continue
        sources[source_id] = source
    return sources


def _source_links(item: dict[str, Any], sources: dict[int, dict[str, Any]]) -> str:
    links = []
    for number in _citation_numbers(item):
        source = sources.get(number) or {}
        url = source.get("url")
        if url:
            links.append(f"[[{number}]]({url})")
        else:
            links.append(f"[{number}]")
    return " ".join(links)


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


def _skill_key(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())

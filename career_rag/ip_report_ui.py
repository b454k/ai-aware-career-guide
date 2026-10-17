"""Streamlit rendering helpers for the final Interest Profiler career report."""

from __future__ import annotations

import re
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st

from career_rag.departments import department_label
from career_rag.ip_ai_impact import ai_snapshot
from career_rag.ip_final_report import FOUNDATIONAL_SOFT_SKILLS, education_level
from career_rag.ui_i18n import (
    claude_usage_lines,
    content_text,
    display_label,
    education_category_name,
    ilo_exposure_lines,
    interest_label,
    job_zone_number,
    job_zone_preparation,
    month_label,
    normalize_language,
    ui_text,
)


def _render_report_styles() -> None:
    css = (Path(__file__).parent / "static" / "report.css").read_text(encoding="utf-8")
    st.markdown(f"<style>\n{css}</style>", unsafe_allow_html=True)


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


def render_final_career_report(report: dict[str, Any], language: str = "en") -> None:
    """Render the final career report in a clean tabbed Streamlit layout."""
    if not report:
        st.info(ui_text("report.no_final", language))
        return
    _render_report_styles()

    _render_report_cover(report, language)

    # The comparison opens first (ROADMAP 9.3); the key keeps the open tab when a table row is selected.
    tabs = st.tabs(
        [
            ui_text("report.tab.summary", language),
            ui_text("report.tab.top_matches", language),
            ui_text("report.tab.alternatives", language),
            ui_text("report.tab.sources", language),
        ],
        default=ui_text("report.tab.top_matches", language),
        key=f"report_tabs_{language}",
    )

    with tabs[0]:
        _render_summary(report, language)
    with tabs[1]:
        _render_top_matches(report, language)
    with tabs[2]:
        _render_alternatives(report, language)
    with tabs[3]:
        _render_sources(report, language)


def render_new_title_view(view: dict[str, Any], language: str = "en") -> None:
    """The closest O*NET roles of a new job title (ROADMAP 6.6), each with the report's job detail."""
    _render_report_styles()
    st.info(
        ui_text("new_titles.note", language, title=view["title"])
        + " "
        + ui_text(f"new_titles.source.{view['source_key']}", language)
    )
    for match in view["roles"]:
        st.markdown(f"#### {_match_display_title(match, language)}")
        with st.expander(ui_text("report.top_matches.detail_card", language)):
            _render_job_detail(match, language, key=f"new_title_{view['title']}_{match.get('onet_soc_code')}")
    _render_sources(view, language)


def _level_stats(profile: dict[str, Any], language: str = "en") -> list[str]:
    """The department the careers come from (ROADMAP 9.1), or the current and future Job Zones."""
    if profile.get("department"):
        return [_report_stat_html(ui_text("report.summary.department", language), department_label(profile["department"], language))]
    # Number large, education text small: the full zone title did not fit a third of a phone.
    return [
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
            *_level_stats(profile, language),
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
            *_level_stats(profile, language),
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
        st.caption(profile["career_matching_guidance"])


def _render_top_matches(report: dict[str, Any], language: str = "en") -> None:
    st.subheader(ui_text("report.top_matches.header", language))
    matches = report.get("top_matches") or []
    department = (report.get("profile_used") or {}).get("department")
    st.caption(ui_text("report.top_matches.caption_department" if department else "report.top_matches.caption", language))

    # A comparison table first; the selected career's card and details below it (ROADMAP 9.3).
    with_groups = len({match.get("match_group") for match in matches}) > 1
    # On a phone the table scrolls sideways; the rank and the career stay in view.
    pinned = {
        ui_text("report.compare.rank", language): st.column_config.NumberColumn(width="small", pinned=True),
        ui_text("report.compare.career", language): st.column_config.TextColumn(width="medium", pinned=True),
    }
    event = st.dataframe(
        [_comparison_row(match, language, with_groups) for match in matches],
        column_config=pinned,
        hide_index=True,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        key="report_comparison",
    )
    if not event.selection.rows:
        st.info(ui_text("report.compare.pick", language))
        return
    match = matches[event.selection.rows[0]]
    _render_match_card(match, language)
    _render_job_detail(match, language, key=f"report_{match.get('onet_soc_code')}")


def _comparison_row(match: dict[str, Any], language: str = "en", with_group: bool = False) -> dict[str, Any]:
    snapshot = ai_snapshot(match.get("ai_impact") or {})
    zone = ((match.get("onet_details") or {}).get("job_zone") or {}).get("zone") or match.get("target_job_zone")
    row = {  # what a student scans first comes first
        ui_text("report.compare.rank", language): match.get("rank"),
        ui_text("report.compare.career", language): _match_display_title(match, language),
        ui_text("report.compare.fit", language): _format_fit_value(match.get("fit_label"), language),
        ui_text("report.compare.picture", language): ui_text(f"snapshot.short.{snapshot['verdict']}", language),
        ui_text("report.compare.ai_use", language): (
            ui_text("snapshot.tasks_short", language, seen=snapshot["tasks_seen"], total=snapshot["tasks_scored"])
            if snapshot["tasks_scored"] else "–"
        ),
        ui_text("report.compare.experts", language): ui_text(f"snapshot.ilo_short.{snapshot['ilo_level'] or 'none'}", language),
        ui_text("report.compare.education", language): job_zone_preparation(zone, language) if zone else "–",
    }
    if with_group:  # Job Zone mode: the current zone's five, then the future zone's five
        future = str(match.get("match_group") or "").startswith("Future")
        row[ui_text("report.compare.group", language)] = ui_text(
            "report.summary.future_zone" if future else "report.summary.current_zone", language
        )
    return row


def _render_match_card(match: dict[str, Any], language: str = "en") -> None:
    title = _match_display_title(match, language)
    rank = match.get("rank") or ""
    fit_label = _format_fit_value(match.get("fit_label") or match.get("fit_score"), language)
    reason = ""
    reasons = match.get("why_it_fits") or []
    if reasons:
        reason = _without_citations(reasons[0])
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
            f"{_chip_html(_snapshot_chip(match, language))}"
            "</div>"
            f"<p class='match-reason'>{_html(reason)}</p>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    if match.get("resolution_note"):
        st.caption(match["resolution_note"])


def _render_job_detail(match: dict[str, Any], language: str = "en", key: str = "job") -> None:
    details = match.get("onet_details") or {}
    reasons = match.get("why_it_fits") or []
    if reasons:
        st.markdown(f"**{ui_text('report.top_matches.fit', language)}**")
        _write_bullets(reasons, language, translate=False)
        _write_source_indexes(reasons)

    st.markdown(f"**{ui_text('report.job.what_does', language)}**")
    description = details.get("description") or ui_text("report.job.no_description", language)
    st.write(content_text(_without_citations(description), language, "O*NET occupation description"))
    _write_source_indexes(description)

    st.markdown(f"**{ui_text('report.job.ai_impact', language)}**")
    _render_ai_snapshot(match, language)
    if st.toggle(ui_text("snapshot.details", language), key=f"{key}_ai_details"):
        _render_ai_table(match, language)
        _render_claude_usage(match, language)
        _render_ilo_exposure(match, language)
        _render_research_claims(match, language)

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
        st.info(_clean_day_text(day_text))  # written in the report's language (6.1e)
        _write_source_indexes([day_text, details.get("tasks") or [], details.get("work_context") or []])


def _snapshot_chip(match: dict[str, Any], language: str = "en") -> str:
    snapshot = ai_snapshot(match.get("ai_impact") or {})
    if not snapshot["tasks_scored"]:
        return ui_text("snapshot.chip_none", language)
    return ui_text("snapshot.chip", language, seen=snapshot["tasks_seen"], total=snapshot["tasks_scored"])


def _render_ai_snapshot(match: dict[str, Any], language: str = "en") -> None:
    """The career's AI evidence in one sentence and three facts (ROADMAP 9.2); the details follow on request."""
    snapshot = ai_snapshot(match.get("ai_impact") or {})
    seen, total, count = snapshot["tasks_seen"], snapshot["tasks_scored"], snapshot["research_count"]
    claude = "snapshot.claude.none" if not total else "snapshot.claude.seen" if seen else "snapshot.claude.zero"
    research = "snapshot.research.many" if count > 1 else "snapshot.research.one" if count else "snapshot.research.none"
    st.markdown(f"**{ui_text('snapshot.verdict.' + snapshot['verdict'], language)}**")
    facts = [
        ui_text(claude, language, seen=seen, total=total),
        ui_text(f"snapshot.ilo.{snapshot['ilo_level'] or 'none'}", language),
        ui_text(research, language, count=count),
    ]
    st.markdown("\n".join(f"- {fact}" for fact in facts))


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
                ui_text("report.ai.table.task", language): content_text(
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


def _render_ilo_exposure(match: dict[str, Any], language: str = "en") -> None:
    """The ILO's assessed exposure next to Anthropic's observed use (D5 = B); never combined into one score."""
    ai_impact = match.get("ai_impact") or {}
    if "ilo_exposure" not in ai_impact:  # a report saved before this panel
        return
    st.markdown(f"**{ui_text('report.ilo.title', language)}**")
    ilo = ai_impact["ilo_exposure"]
    if not ilo:
        st.caption(ui_text("report.ilo.none", language))
        return
    for line in ilo_exposure_lines(ilo, language):
        st.write(f"- {line}")
    st.caption(_format_source_ids(ilo.get("source_ids") or []))


def _render_research_claims(match: dict[str, Any], language: str = "en") -> None:
    claims = (match.get("ai_impact") or {}).get("research_claims")
    if claims is None:  # a report saved before ROADMAP 4.1c
        return
    st.markdown(f"**{ui_text('report.research.title', language)}**")
    if not claims:
        st.caption(ui_text("report.research.none", language))
        return
    for item in claims:
        claim = content_text(item["claim"], language, "research finding about AI and work")
        st.write(f"- {claim}")
        where = f"{ui_text('report.research.pages', language, pages=item['pages'])} {_format_source_ids(item['source_ids'])}"
        if claim.strip().rstrip(".").lower() == item["quote"].strip().rstrip(".").lower():
            st.caption(where)  # the claim is the quote itself
        else:
            st.caption(f"{ui_text('report.research.in_source', language)}: “{item['quote']}” ({where})")
    st.caption(ui_text("report.research.caption", language))


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
        title = content_text(item.get("title"), language, "alternative career title")
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
    if normalize_language(language) == "tr":
        st.caption(ui_text("report.sources.translation_note", language))
    with st.expander(ui_text("report.sources.expander", language), expanded=True):
        for source in report.get("sources") or []:
            label = f"[{source.get('id')}] {source.get('title')}"
            if source.get("url"):
                st.markdown(f"**[{label}]({source['url']})**")
            else:
                st.markdown(f"**{label}**")
            if source.get("retrieved_section"):
                st.write(source["retrieved_section"])
            if source.get("note"):
                st.caption(source["note"])
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


def _write_bullets(items: list[Any], language: str = "en", translate: bool = True) -> None:
    # translate=False: the report builder already wrote these sentences in the report's language (6.1d),
    # or the caller localized them; otherwise items are O*NET content, looked up in the table (6.1c).
    if not items:
        st.write(ui_text("report.no_local_evidence", language))
        return
    for item in items:
        text = _without_citations(item)
        st.write(f"- {content_text(text, language, 'report bullet') if translate else text}")


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
            _skill_chip_html([_skill_text(value, language) for value in values]),
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
            _skill_chip_html(values),  # the student's own answers, shown as typed
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

    prep_summary = _education_preparation_summary(job_zone, details.get("education_levels") or [], language)
    if prep_summary:
        st.write(ui_text("report.education.typical", language) + prep_summary)

    training = content_text(
        _clean_job_zone_training(job_zone.get("training")),
        language,
        "O*NET job zone training",
    )
    if training:
        st.write(ui_text("report.education.training", language) + training)

    if education:
        st.caption(ui_text("report.education.responses", language))
        _write_bullets([_format_education_entry(item, language) for item in education_entries], language, translate=False)

    if not education and not prep_summary and not training:
        st.write(ui_text("report.education.none", language))
    _write_source_indexes([job_zone, education])


def _skill_text(value: Any, language: str = "en") -> str:
    """A skill chip in the display language: the name from the content table (6.1c), O*NET's
    "(In demand)" mark on software from the UI texts. Citation markers are dropped before the lookup."""
    text = _without_citations(value)
    in_demand = text.endswith(" (In demand)")
    if in_demand:
        text = text[: -len(" (In demand)")]
    text = content_text(text, language)
    return f"{text} ({ui_text('report.skills.in_demand', language)})" if in_demand else text


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
    return content_text(
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


def _job_zone_title(zone: Any, language: str = "en") -> str:
    try:
        zone_int = int(zone)
    except (TypeError, ValueError):
        return ui_text("report.job_zone.unavailable", language)
    explanation = job_zone_preparation(zone_int, language)
    return ui_text("report.job_zone.title", language, zone=job_zone_number(zone_int), explanation=explanation)


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


def _format_education_entry(entry: dict[str, Any], language: str = "en") -> str:
    # The level's name is O*NET content (translated by the table); the percentage is not.
    label = content_text(entry.get("label"), language)
    return label if entry.get("percent") is None else f"{label} ({entry['percent']:g}%)"


def _education_preparation_summary(
    job_zone: dict[str, Any],
    education_levels: list[dict[str, Any]],
    language: str = "en",
) -> str:
    # education_levels carries O*NET's category numbers (ip_final_report._fetch_education_levels).
    positive_entries = sorted(
        (level for level in education_levels if level["percent"] > 0),
        key=lambda level: level["percent"],
        reverse=True,
    )
    if positive_entries:
        return _plain_education_summary(positive_entries, language)

    fallback = content_text(
        _clean_job_zone_education(job_zone.get("education")),
        language,
        "O*NET job zone education",
    )
    return fallback


def _plain_education_summary(entries: list[dict[str, Any]], language: str = "en") -> str:
    top = entries[0]
    top_level = education_level(top.get("category"))
    bachelor_entry = next((entry for entry in entries if education_level(entry.get("category")) == "bachelor"), None)
    master_entry = next((entry for entry in entries if education_level(entry.get("category")) == "master"), None)

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

    label = education_category_name(top.get("category"), language) or _without_citations(top.get("label")).lower()
    if label:
        return ui_text("report.education.dynamic", language, label=label)
    return ""


def _clean_job_zone_education(value: Any) -> str:
    # Keeps O*NET's "but some do not" (D13; this copy was missed in 2.8, fixed in 2.10).
    text = _without_citations(value)
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

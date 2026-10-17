"""Streamlit rendering of the final career report: the careers list beside the selected career (Phase 10)."""

from __future__ import annotations

import re
from typing import Any

import streamlit as st

from career_rag.ip_ai_impact import ai_snapshot, claude_share_standing
from career_rag.ip_final_report import FOUNDATIONAL_SOFT_SKILLS, education_level
from career_rag.new_titles import SOURCE_KEYS, title_label, titles_for_career
from career_rag.ui_i18n import (
    claude_usage_lines,
    claude_usage_notes,
    content_text,
    display_label,
    education_category_name,
    ilo_exposure_lines,
    job_zone_number,
    job_zone_preparation,
    month_label,
    normalize_language,
    ui_text,
)

FIT_COLORS = {"Best fit": "green", "Great fit": "green", "Good fit": "blue", "Weak fit": "orange"}


def render_careers(report: dict[str, Any], language: str = "en") -> None:
    """The student's careers and the alternatives on the left, the selected one on the right."""
    top = report.get("top_matches") or []
    department = (report.get("profile_used") or {}).get("department")
    if department and top and all(match.get("fit_label") == "Weak fit" for match in top):
        st.warning(ui_text("report.department.all_weak", language))
    # one table for the top matches, one per preparation level for the alternatives
    groups = {"top": top}
    for match in report.get("alternative_careers") or []:
        groups.setdefault(f"zone_{match.get('target_job_zone')}", []).append(match)
    pick = _picked(groups)

    list_column, detail_column = st.columns(2, gap="large")
    with list_column:
        st.markdown(f"#### {ui_text('report.list.department' if department else 'report.list.matches', language)}")
        st.caption(ui_text("report.top_matches.caption_department" if department else "report.top_matches.caption", language))
        _career_table("top", top, pick, language, with_level=not department)  # Job Zone mode: two levels
        st.markdown(f"#### {ui_text('report.alternatives.header', language)}")
        st.caption(ui_text("report.alternatives.caption", language))
        if len(groups) == 1:
            st.info(ui_text("report.alternatives.none", language))
        for group, matches in groups.items():
            if group != "top":
                st.markdown(f"**{_job_zone_title(matches[0].get('target_job_zone'), language)}**")
                _career_table(group, matches, pick, language, with_level=False)
    with detail_column, st.container(key="career_detail"):  # stays in view while the list scrolls (app.css)
        group, index = pick
        if groups.get(group):
            _render_career(groups[group][index], language)


def _picked(groups: dict[str, list[dict[str, Any]]]) -> tuple[str, int]:
    """The selected career as (table, row); the first top match until the student picks one."""
    group, index = st.session_state.get("ip_pick") or ("top", 0)
    if index >= len(groups.get(group) or []):
        group, index = next(((name, 0) for name, matches in groups.items() if matches), ("top", 0))
    st.session_state["ip_pick"] = (group, index)
    return group, index


def _on_pick(group: str, key: str) -> None:
    rows = st.session_state[key].selection.rows
    if rows:
        st.session_state["ip_pick"] = (group, rows[0])
    # new keys for every table, so the others drop their highlighted row
    st.session_state["ip_pick_version"] = st.session_state.get("ip_pick_version", 0) + 1


def _career_table(
    group: str, matches: list[dict[str, Any]], pick: tuple[str, int], language: str, with_level: bool
) -> None:
    if not matches:
        st.info(ui_text("report.no_local_evidence", language))
        return
    key = f"careers_{group}_{st.session_state.get('ip_pick_version', 0)}"
    selected = [pick[1]] if pick[0] == group else []
    st.dataframe(
        [_list_row(match, language, with_level) for match in matches],
        hide_index=True,
        height=35 * (len(matches) + 1) + 3,  # every row, no inner scrolling
        column_config={
            ui_text("report.compare.career", language): st.column_config.TextColumn(width=300),
            ui_text("report.compare.fit", language): st.column_config.TextColumn(width=90),
        },
        on_select=lambda: _on_pick(group, key),
        selection_mode="single-row",
        selection_default={"selection": {"rows": selected, "columns": []}},
        key=key,
    )


def _list_row(match: dict[str, Any], language: str, with_level: bool) -> dict[str, Any]:
    snapshot = ai_snapshot(match.get("ai_impact") or {})
    row = {
        ui_text("report.compare.career", language): _match_display_title(match, language),
        ui_text("report.compare.fit", language): _format_fit_value(match.get("fit_label"), language),
        ui_text("report.compare.picture", language): ui_text(f"snapshot.short.{snapshot['verdict']}", language),
    }
    if with_level:
        row[ui_text("report.compare.level", language)] = job_zone_preparation(_zone(match), language) if _zone(match) else "–"
    return row


def _zone(match: dict[str, Any]) -> Any:
    return ((match.get("onet_details") or {}).get("job_zone") or {}).get("zone") or match.get("target_job_zone")


def _render_career(match: dict[str, Any], language: str = "en") -> None:
    """One career: its name and three badges, then its details in four tabs."""
    with st.container(border=True):
        st.subheader(_match_display_title(match, language))
        with st.container(horizontal=True):
            st.badge(_format_fit_value(match.get("fit_label"), language), color=FIT_COLORS.get(match.get("fit_label"), "gray"))
            st.badge(_snapshot_chip(match, language), color="violet")
            st.badge(_job_zone_title(_zone(match), language), color="gray")
        if match.get("resolution_note"):
            st.caption(match["resolution_note"])

        overview, evidence, skills = st.tabs(
            [ui_text(f"report.detail.{name}", language) for name in ("overview", "evidence", "skills")]
        )
        with overview:
            _render_overview(match, language)
        with evidence:
            _render_ai_table(match, language)
            _render_claude_usage(match, language)
            _render_ilo_exposure(match, language)
            _render_research_claims(match, language)
        with skills:
            st.markdown(f"**{ui_text('report.job.education_zone', language)}**")
            _render_education_job_zone(match, language)
            st.markdown(f"**{ui_text('report.job.key_skills', language)}**")
            _render_key_skills(match, language)


def _render_overview(match: dict[str, Any], language: str = "en") -> None:
    reasons = match.get("why_it_fits") or []
    if reasons:
        st.markdown(f"**{ui_text('report.top_matches.fit', language)}**")
        _write_bullets(reasons, language, translate=False)

    st.markdown(f"**{ui_text('report.job.what_does', language)}**")
    description = (match.get("onet_details") or {}).get("description") or ui_text("report.job.no_description", language)
    st.write(content_text(_without_citations(description), language, "O*NET occupation description"))

    st.markdown(f"**{ui_text('report.job.ai_impact', language)}**")
    _render_ai_snapshot(match, language)
    _render_new_titles(match, language)

    st.markdown(f"**{ui_text('report.job.main_tasks', language)}**")
    _write_bullets((match.get("onet_details") or {}).get("tasks") or [], language)


def _render_new_titles(match: dict[str, Any], language: str = "en") -> None:
    """New job titles whose closest O*NET occupations include this one (ROADMAP 10.2, from 6.6)."""
    rows = titles_for_career(str(match.get("onet_soc_code") or ""))
    if not rows:
        return
    st.markdown(f"**{ui_text('report.new_titles.header', language)}**")
    st.caption(ui_text("report.new_titles.note", language))  # O*NET has no equivalent; only the closest are shown
    for row in rows:
        source = ui_text(f"report.new_titles.source.{SOURCE_KEYS[row['source']]}", language)
        st.write(f"- **{title_label(row, language)}**: {source}")


def _snapshot_chip(match: dict[str, Any], language: str = "en") -> str:
    snapshot = ai_snapshot(match.get("ai_impact") or {})
    if not snapshot["tasks_scored"]:
        return ui_text("snapshot.chip_none", language)
    return ui_text("snapshot.chip", language, seen=snapshot["tasks_seen"], total=snapshot["tasks_scored"])


def _render_ai_snapshot(match: dict[str, Any], language: str = "en") -> None:
    """The career's AI evidence in one sentence and three facts (ROADMAP 9.2); the details are in their own tab."""
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


def _render_ai_table(match: dict[str, Any], language: str = "en") -> None:
    """The main tasks people already use Claude for, each with how they use it, and what that means (10.4)."""
    snapshot = ai_snapshot(match.get("ai_impact") or {})
    seen, total = snapshot["tasks_seen"], snapshot["tasks_scored"]
    st.markdown(f"**{ui_text('report.ai.table.title', language)}**")
    if not seen:
        st.write(ui_text("snapshot.claude.zero" if total else "snapshot.claude.none", language, total=total))
        return
    st.write(ui_text("snapshot.claude.seen", language, seen=seen, total=total))
    for item in match["ai_impact"].get("task_breakdown") or []:
        if str(item.get("ai_coverage") or "").startswith("Covered"):
            task = content_text(item.get("task"), language, "AI-impact task")
            st.write(f"- {task} **{display_label(item.get('ai_coverage'), language)}**")
    st.caption(ui_text("report.ai.labels", language))


def _render_claude_usage(match: dict[str, Any], language: str = "en") -> None:
    usage = (match.get("ai_impact") or {}).get("claude_usage")
    if not usage:
        return
    st.markdown(f"**{ui_text('report.usage.title', language, month=month_label(usage['month'], language))}**")
    rank, total = claude_share_standing(usage["global_pct"])
    for line, note in zip(claude_usage_lines(usage, language), claude_usage_notes(usage, rank, total, language)):
        st.write(f"- {line}")
        if note:
            st.caption(note)


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
    gradients = ("Not Exposed", "Minimal Exposure", "Gradient 1", "Gradient 2", "Gradient 3", "Gradient 4")
    names = ui_text("report.ilo.levels", language).split("|")
    levels = " → ".join(f"**{name}**" if gradient == ilo["gradient"] else name for gradient, name in zip(gradients, names))
    st.caption(ui_text("report.ilo.scale", language, levels=levels))


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
        # the source by name (older reports have only its number), and the pages when known
        where = item.get("source") or _format_source_ids(item["source_ids"])
        if item.get("pages"):
            where += f", {ui_text('report.research.pages', language, pages=item['pages'])}"
        if claim.strip().rstrip(".").lower() == item["quote"].strip().rstrip(".").lower():
            st.caption(where)  # the claim is the quote itself
        else:
            st.caption(f"{ui_text('report.research.in_source', language)}: “{item['quote']}” ({where})")


def render_about_data(report: dict[str, Any], language: str = "en") -> None:
    """What the data means, said once instead of on every career (ROADMAP 9.5), then the sources."""
    sections = [
        ("about.careers.title", ["about.careers.text"]),
        ("about.picture.title", ["about.picture.text"]),
        ("about.anthropic.title", ["report.ai.caption", "about.anthropic.estimates"]),
        ("about.ilo.title", ["about.ilo.text"]),
        ("about.research.title", ["report.research.caption"]),
    ]
    for title, texts in sections:
        st.markdown(f"**{ui_text(title, language)}**")
        for text in texts:
            st.write(ui_text(text, language))
    _render_sources(report, language)


def _render_sources(report: dict[str, Any], language: str = "en") -> None:
    st.subheader(ui_text("report.sources.header", language))
    if normalize_language(language) == "tr":
        st.caption(ui_text("report.sources.translation_note", language))
    with st.expander(ui_text("report.sources.expander", language), expanded=False):
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
        st.write(" · ".join(_skill_text(value, language) for value in values))
    if not rendered_any:
        st.write(ui_text("report.no_local_evidence", language))


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


def _skill_text(value: Any, language: str = "en") -> str:
    """A skill in the display language, from the content table (6.1c), without O*NET's "(In demand)" mark (10.4).
    Citation markers are dropped before the lookup."""
    return content_text(_without_citations(value).removesuffix(" (In demand)"), language)


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


def _format_source_ids(values: list[Any]) -> str:
    ids = []
    for value in values:
        try:
            source_id = int(value)
        except (TypeError, ValueError):
            continue
        ids.append(f"[{source_id}]")
    return " ".join(ids)


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

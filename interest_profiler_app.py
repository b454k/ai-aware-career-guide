"""Streamlit UI: the O*NET Interest Profiler test, then the career report (a desktop layout, Phase 10)."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st

from career_rag.artifacts import (
    MissingRagArtifactsError,
    format_missing_artifacts_error,
    inspect_rag_artifacts,
)
from career_rag.config import (
    FINAL_REPORT_JSON_PATH,
    MINI_IP_QUESTIONS_PATH,
    PROFILE_RESULT_PATH,
    QUESTIONS_PATH,
)
from career_rag.interest_profiler_local import (
    build_profile_result,
    canonical_interest,
    calculate_mini_ip_scores,
    calculate_riasec_scores,
    load_mini_ip_questions,
    save_profile_result,
)
from career_rag.ip_career_matcher import (
    ONET_JOB_ZONES,
    build_career_matches,
)
from career_rag.ip_followup_agent import (
    MAX_FOLLOWUP_QUESTIONS,
    build_followup_question_plan,
    complete_followup_refinement,
    get_next_followup_question,
    record_followup_answer,
)
from career_rag.departments import DEPARTMENT_JOB_ZONE, department_codes, department_label, load_departments
from career_rag.ip_final_report import build_final_career_report
from career_rag.ip_refinement_ranker import update_profile_with_followup
from career_rag.ip_report_ui import render_about_data, render_careers
from career_rag.ui_i18n import (
    LANGUAGE_BUTTON_LABELS,
    LANGUAGE_SESSION_KEY,
    artifact_label,
    content_text,
    followup_question_text,
    interest_label,
    job_zone_label,
    job_zone_number,
    job_zone_preparation,
    normalize_language,
    question_text,
    ui_text,
)


RESULT_PATH = PROFILE_RESULT_PATH
FINAL_REPORT_PATH = FINAL_REPORT_JSON_PATH

METHOD_REFERENCES = [
    {
        "label": (
            "Renji, N. M., Rao, B., & Lipizzi, C. (2025). Steve: LLM powered chatbot "
            "for career progression. arXiv:2504.03789."
        ),
        "url": "https://arxiv.org/abs/2504.03789",
    },
    {
        "label": (
            "Jeon, H., et al. (2025). Letters from future self: Supporting young adults' "
            "career exploration with LLM-powered agents. CHI 2025."
        ),
        "url": "https://arxiv.org/abs/2502.18881",
    },
    {
        "label": "Anthropic Economic Index and labor-market impact research.",
        "url": "https://www.anthropic.com/research/labor-market-impacts",
    },
]


def _safe_html(value: Any) -> str:
    return escape(str(value or ""))


def _render_global_styles() -> None:
    """The few styles the light theme (.streamlit/config.toml) doesn't cover: the activity card."""
    css = (Path(__file__).parent / "career_rag" / "static" / "app.css").read_text(encoding="utf-8")
    st.markdown(f"<style>\n{css}</style>", unsafe_allow_html=True)


@st.cache_data
def _load_questions() -> list[dict[str, Any]]:
    from career_rag.interest_profiler_local import load_interest_profiler_questions

    return load_interest_profiler_questions(QUESTIONS_PATH)


@st.cache_data
def _load_mini_ip() -> list[dict[str, Any]]:
    return load_mini_ip_questions(MINI_IP_QUESTIONS_PATH, _load_questions())


TESTS = ("mini_ip_30", "short_form_60")  # O*NET's Mini-IP is the default (ROADMAP 9.8)


def _chosen_test() -> str:
    test = st.session_state.get("ip_test")
    return test if test in TESTS else TESTS[0]


def _test_questions(test: str) -> list[dict[str, Any]]:
    return _load_mini_ip() if test == "mini_ip_30" else _load_questions()


def _go_to_first_unanswered_card() -> None:
    questions = _test_questions(_chosen_test())
    st.session_state["ip_card_index"] = _first_unanswered_index(questions, st.session_state.get("ip_card_answers") or {})


def _interest_scores(test: str) -> dict[str, int]:
    """The six scores from the cards answered yes in the chosen test."""
    liked = _liked_question_ids(_test_questions(test))
    if test == "mini_ip_30":
        return calculate_mini_ip_scores(_load_questions(), liked)
    return calculate_riasec_scores(_load_questions(), liked)


@st.cache_data(ttl=30)
def _inspect_rag_artifacts_cached() -> dict[str, Any]:
    return inspect_rag_artifacts()


def _format_job_zone_for_language(zone: int, language: str) -> str:
    zone = int(zone)
    return f"{job_zone_number(zone)} - {job_zone_label(zone, language)} ({_job_zone_explanation(zone, language)})"


def _job_zone_explanation(zone: Any, language: str = "en") -> str:
    return job_zone_preparation(zone, language)


def _current_language() -> str:
    language = normalize_language(st.session_state.get(LANGUAGE_SESSION_KEY, "en"))
    st.session_state[LANGUAGE_SESSION_KEY] = language
    return language


def _render_language_switch() -> str:
    language = _current_language()
    st.caption(ui_text("language.label", language))
    for column, code in zip(st.columns(2), ("en", "tr")):
        with column:
            if st.button(
                LANGUAGE_BUTTON_LABELS[code],
                key=f"language_switch_{code}",
                type="primary" if language == code else "secondary",
                use_container_width=True,
            ):
                st.session_state[LANGUAGE_SESSION_KEY] = code
                st.rerun()
    return _current_language()


def _render_sidebar(result: dict[str, Any] | None, screen: str) -> str:
    """The app's name, the language, the student's profile and the way between the two screens."""
    with st.sidebar:
        st.title(ui_text("app.title", _current_language()))
        language = _render_language_switch()
        st.caption(ui_text("app.caption", language))
        if result:
            _render_profile_summary_card(result, language)
            if screen == "results":
                _screen_button("results.change_answers", "test", language)
            else:
                _screen_button("results.back", "results", language)
        with st.expander(ui_text("app.method_references", language), expanded=False):
            for source in METHOD_REFERENCES:
                st.markdown(f"- [{source['label']}]({source['url']})")
    return language


def _reset_followup_state() -> None:
    st.session_state["ip_followup_active"] = False
    st.session_state["ip_followup_complete"] = False
    st.session_state["ip_followup_plan"] = []
    st.session_state["ip_followup_answers"] = []


def _set_profile_result(result: dict[str, Any], source: str) -> None:
    st.session_state["profile_result"] = result
    st.session_state["ip_profile_result"] = result
    st.session_state["profile_result_source"] = source


def _clear_old_final_report_state() -> None:
    st.session_state["final_report"] = None
    st.session_state["ip_final_career_report"] = None
    st.session_state["followup_answers"] = None
    st.session_state["ip_followup_answers"] = None


def _load_profile_result_from_json() -> dict[str, Any] | None:
    if not RESULT_PATH.exists():
        return None
    try:
        with RESULT_PATH.open("r", encoding="utf-8") as file:
            value = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _get_current_profile_result() -> tuple[dict[str, Any] | None, str]:
    result = st.session_state.get("profile_result")
    if isinstance(result, dict):
        return result, "session_state"

    legacy_result = st.session_state.get("ip_profile_result")
    if isinstance(legacy_result, dict):
        _set_profile_result(legacy_result, "session_state")
        return legacy_result, "session_state"

    saved_result = _load_profile_result_from_json()
    if saved_result:
        _set_profile_result(saved_result, "JSON")
        return saved_result, "JSON"
    return None, "none"


def _has_followup_answer(result: dict[str, Any]) -> bool:
    followup = result.get("followup_refinement") or {}
    return bool(followup.get("questions_asked"))


def _validate_report_matches_profile(report: dict[str, Any], profile_result: dict[str, Any]) -> list[str]:
    profile_used = report.get("profile_used") or {}
    expected_initial = str(
        profile_result.get("holland_code")
        or profile_result.get("initial_code")
        or profile_result.get("initial_holland_code")
        or ""
    )
    expected_current = int(profile_result.get("current_job_zone") or 0)
    expected_future = int(profile_result.get("future_job_zone") or 0)
    actual_initial = str(profile_used.get("initial_code") or profile_used.get("initial_holland_code") or "")
    actual_current = int(profile_used.get("current_zone") or profile_used.get("current_job_zone") or 0)
    actual_future = int(profile_used.get("future_zone") or profile_used.get("future_job_zone") or 0)
    actual_final = str(profile_used.get("final_code") or profile_used.get("final_holland_code") or "")

    errors = []
    if actual_initial != expected_initial:
        errors.append(f"initial_code mismatch: report={actual_initial}, profile={expected_initial}")
    if actual_current != expected_current:
        errors.append(f"current_zone mismatch: report={actual_current}, profile={expected_current}")
    if actual_future != expected_future:
        errors.append(f"future_zone mismatch: report={actual_future}, profile={expected_future}")
    if not _has_followup_answer(profile_result) and actual_final != expected_initial:
        errors.append(f"final_code mismatch without follow-up: report={actual_final}, initial={expected_initial}")
    return errors


def _ensure_interest_card_state(questions: list[dict[str, Any]]) -> None:
    valid_ids = {int(question["id"]) for question in _load_questions()}  # kept for all 60, so switching tests keeps them
    raw_answers = st.session_state.get("ip_card_answers")
    if not isinstance(raw_answers, dict):
        raw_answers = {}

    answers: dict[int, bool] = {}
    for raw_id, liked in raw_answers.items():
        try:
            question_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if question_id in valid_ids and isinstance(liked, bool):
            answers[question_id] = liked
    st.session_state["ip_card_answers"] = answers

    try:
        index = int(st.session_state.get("ip_card_index", 0))
    except (TypeError, ValueError):
        index = 0
    index = max(0, min(index, len(questions)))
    if index >= len(questions) and len(answers) < len(questions):
        index = _first_unanswered_index(questions, answers)
    st.session_state["ip_card_index"] = index


def _first_unanswered_index(questions: list[dict[str, Any]], answers: dict[int, bool]) -> int:
    for index, question in enumerate(questions):
        if int(question["id"]) not in answers:
            return index
    return len(questions)


def _answered_card_count(questions: list[dict[str, Any]]) -> int:
    answers = st.session_state.get("ip_card_answers") or {}
    valid_ids = {int(question["id"]) for question in questions}
    return sum(1 for question_id in valid_ids if question_id in answers)


def _liked_question_ids(questions: list[dict[str, Any]]) -> list[int]:
    answers = st.session_state.get("ip_card_answers") or {}
    return [
        int(question["id"])
        for question in questions
        if answers.get(int(question["id"])) is True
    ]


def _record_interest_card_answer(question_id: int, liked: bool, questions: list[dict[str, Any]]) -> None:
    answers = st.session_state.setdefault("ip_card_answers", {})
    answers[int(question_id)] = bool(liked)
    current_index = int(st.session_state.get("ip_card_index", 0))
    next_index = len(questions)
    for index in range(current_index + 1, len(questions)):
        if int(questions[index]["id"]) not in answers:
            next_index = index
            break
    if next_index == len(questions) and current_index + 1 < len(questions):
        next_index = current_index + 1
    st.session_state["ip_card_index"] = min(next_index, len(questions))


def _reset_interest_cards() -> None:
    st.session_state["ip_card_answers"] = {}
    st.session_state["ip_card_index"] = 0


def _submit_interest_profile(
    test: str,
    current_job_zone: int,
    future_job_zone: int,
    department: str | None = None,
) -> None:
    checked_ids = _liked_question_ids(_test_questions(test))
    scores = _interest_scores(test)
    career_matches = build_career_matches(
        scores=scores,
        current_job_zone=current_job_zone,
        future_job_zone=future_job_zone,
        department_codes=department_codes(department) if department else (),
    )
    result = build_profile_result(
        scores=scores,
        current_job_zone=current_job_zone,
        future_job_zone=future_job_zone,
        career_matches=career_matches,
        department=department,
        liked_activity_ids=checked_ids,
        interest_test=test,
    )
    _clear_old_final_report_state()
    save_profile_result(result, RESULT_PATH)
    _set_profile_result(result, "session_state")
    _reset_followup_state()
    st.session_state["ip_screen"] = "results"


def _render_profile_summary_card(result: dict[str, Any], language: str) -> None:
    top_interests = result.get("final_top_interests") or result.get("top_interests") or []
    code = result.get("final_holland_code") or result.get("holland_code") or ""
    with st.container(border=True):
        st.caption(ui_text("hero.status", language))
        with st.container(horizontal=True):
            for interest in top_interests[:3]:
                st.badge(interest_label(interest, language), color="blue")
        st.write(f"{ui_text('profile.code', language)}: **{code}**")
        if result.get("department"):
            st.write(f"{ui_text('profile.department', language)}: **{department_label(result['department'], language)}**")
        else:
            current = result.get("current_job_zone") or result.get("current_zone") or ""
            future = result.get("future_job_zone") or result.get("future_zone") or ""
            st.write(f"{ui_text('profile.current_zone', language)}: **{job_zone_number(current)}**")
            st.write(f"{ui_text('profile.future_zone', language)}: **{job_zone_number(future)}**")


def _render_initial_form(language: str) -> None:
    test = _chosen_test()
    questions = _test_questions(test)
    _ensure_interest_card_state(questions)
    total = len(questions)
    answered = _answered_card_count(questions)

    st.header(ui_text("assessment.header", language))
    st.caption(ui_text("initial.activities_header", language, count=total) + " · " + ui_text("assessment.caption", language))
    st.radio(
        ui_text("assessment.test", language),
        TESTS,
        format_func=lambda name: ui_text(f"assessment.test.{name}", language),
        horizontal=True,
        key="ip_test",
        on_change=_go_to_first_unanswered_card,
    )

    if not questions:
        st.warning(ui_text("report.no_local_evidence", language))
        return

    if answered < total:
        index = int(st.session_state.get("ip_card_index", 0))
        index = max(0, min(index, total - 1))
        question = questions[index]
        question_id = int(question["id"])
        answers = st.session_state.get("ip_card_answers") or {}
        previous_answer = answers.get(question_id)
        previous_html = ""
        if previous_answer is True:
            previous_html = (
                f"<div class='answer-memory'>{_safe_html(ui_text('assessment.previous_yes', language))}</div>"
            )
        elif previous_answer is False:
            previous_html = (
                f"<div class='answer-memory'>{_safe_html(ui_text('assessment.previous_no', language))}</div>"
            )

        current_label = ui_text("assessment.progress", language).format(
            current=index + 1,
            total=total,
        )
        answered_label = ui_text("assessment.completed", language).format(
            answered=answered,
            total=total,
        )
        st.markdown(
            (
                "<div class='swipe-card'>"
                "<div>"
                "<div class='swipe-progress-row'>"
                f"<span>{_safe_html(current_label)}</span>"
                f"<span>{_safe_html(answered_label)}</span>"
                "</div>"
                f"<div class='activity-prompt'>{_safe_html(ui_text('assessment.activity_prompt', language))}</div>"
                f"<p class='activity-text'>{_safe_html(question_text(question, language))}</p>"
                "</div>"
                f"{previous_html}"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        st.progress(answered / total)

        no_col, yes_col = st.columns(2)
        with no_col:
            if st.button(
                ui_text("assessment.no", language),
                key=f"activity_no_{question_id}",
                use_container_width=True,
            ):
                _record_interest_card_answer(question_id, False, questions)
                st.rerun()
        with yes_col:
            if st.button(
                ui_text("assessment.yes", language),
                key=f"activity_yes_{question_id}",
                type="primary",
                use_container_width=True,
            ):
                _record_interest_card_answer(question_id, True, questions)
                st.rerun()

        back_col, reset_col = st.columns(2)
        with back_col:
            if st.button(
                ui_text("assessment.back", language),
                key="activity_back",
                disabled=index <= 0,
                use_container_width=True,
            ):
                st.session_state["ip_card_index"] = max(0, index - 1)
                st.rerun()
        with reset_col:
            if st.button(
                ui_text("assessment.reset", language),
                key="activity_reset",
                use_container_width=True,
            ):
                _reset_interest_cards()
                st.rerun()
        return

    st.progress(1.0)
    st.success(f"**{ui_text('assessment.done_title', language)}** {ui_text('assessment.done_text', language)}")

    # Outside the form, so that choosing a department hides the Job Zone questions at once (ROADMAP 9.1).
    not_listed = "__not_listed__"
    choice = st.selectbox(
        ui_text("initial.department_question", language),
        options=[row["name_tr"] for row in load_departments()] + [not_listed],
        index=None,
        placeholder=ui_text("initial.department_placeholder", language),
        format_func=lambda name: (
            ui_text("initial.department_other", language) if name == not_listed else department_label(name, language)
        ),
        help=ui_text("initial.department_help", language),
        key="ip_department",
    )
    department = choice if choice and choice != not_listed else None

    with st.form("interest_profiler_zone_form"):
        if department:
            current_job_zone = future_job_zone = DEPARTMENT_JOB_ZONE
        else:
            st.markdown(f"**{ui_text('initial.current_job_zone_heading', language)}**")
            current_job_zone = st.selectbox(
                ui_text("initial.current_job_zone_question", language),
                options=list(ONET_JOB_ZONES),
                format_func=lambda zone: _format_job_zone_for_language(zone, language),
                index=1,
                key="ip_current_job_zone",
            )
            st.markdown(f"**{ui_text('initial.future_job_zone_heading', language)}**")
            future_job_zone = st.selectbox(
                ui_text("initial.future_job_zone_question", language),
                options=list(ONET_JOB_ZONES),
                format_func=lambda zone: _format_job_zone_for_language(zone, language),
                index=2,
                key="ip_future_job_zone",
            )
        submitted = st.form_submit_button(
            ui_text("assessment.submit", language),
            use_container_width=True,
        )

    reset_col, _ = st.columns([1, 1])
    with reset_col:
        if st.button(
            ui_text("assessment.reset", language),
            key="activity_reset_after_complete",
            use_container_width=True,
        ):
            _reset_interest_cards()
            st.rerun()

    if not submitted:
        return
    if _answered_card_count(questions) < total:
        st.warning(ui_text("assessment.incomplete", language))
        return
    # O*NET matches by the shape of the six scores; equal scores have no shape (O*NET rule 9).
    if len(set(_interest_scores(test).values())) == 1:
        st.warning(ui_text("assessment.flat_profile", language))
        return
    with st.spinner(ui_text("assessment.spinner", language)):
        _submit_interest_profile(test, current_job_zone, future_job_zone, department)
    st.success(ui_text("assessment.saved", language))
    st.rerun()


def _render_followup(result: dict[str, Any], language: str) -> None:
    ambiguity = result.get("score_ambiguity") or {}
    followup_refinement = result.get("followup_refinement")

    st.caption(ui_text("followup.optional_note", language))
    rag_ready, inspection = _rag_artifacts_ready()
    if not rag_ready and not followup_refinement:
        _render_missing_artifacts_message(inspection, language)
        return

    if followup_refinement and followup_refinement.get("method") == "in_progress":
        if not rag_ready:
            _render_missing_artifacts_message(inspection, language)
            return
        st.session_state["ip_followup_plan"] = (
            st.session_state.get("ip_followup_plan")
            or followup_refinement.get("question_plan")
            or build_followup_question_plan(result)
        )
        st.session_state["ip_followup_answers"] = (
            st.session_state.get("ip_followup_answers")
            or followup_refinement.get("questions_asked")
            or []
        )
        st.session_state["ip_followup_active"] = True
        _render_followup_question(result, language)
        return

    if followup_refinement:
        _show_followup_refinement(result, language)
        return

    if st.session_state.get("ip_followup_active"):
        if not rag_ready:
            _render_missing_artifacts_message(inspection, language)
            return
        _render_followup_question(result, language)
        return

    if st.session_state.get("ip_followup_complete"):
        return

    if ambiguity.get("has_ambiguity"):
        st.info(ui_text("followup.ambiguity_info", language))
    else:
        st.info(ui_text("followup.clear_info", language))

    continue_col, skip_col = st.columns(2)
    with continue_col:
        if st.button(ui_text("followup.continue", language), use_container_width=True):
            st.session_state["ip_followup_plan"] = build_followup_question_plan(result)
            st.session_state["ip_followup_answers"] = []
            st.session_state["ip_followup_active"] = True
            st.session_state["ip_followup_complete"] = False
            st.rerun()
    with skip_col:
        if st.button(ui_text("followup.skip", language), use_container_width=True):
            st.session_state["ip_followup_complete"] = True
            st.rerun()


def _render_followup_question(result: dict[str, Any], language: str) -> None:
    in_progress = result.get("followup_refinement") or {}
    question_plan = (
        st.session_state.get("ip_followup_plan")
        or in_progress.get("question_plan")
        or build_followup_question_plan(result)
    )
    questions_asked = (
        st.session_state.get("ip_followup_answers")
        or in_progress.get("questions_asked")
        or []
    )
    current = get_next_followup_question(question_plan, questions_asked)

    if current is None:
        try:
            refinement = complete_followup_refinement(result, questions_asked)
            updated = update_profile_with_followup(result, refinement)
        except MissingRagArtifactsError as exc:
            st.error(_format_missing_artifacts_error_for_ui({"missing": exc.missing_artifacts}, language))
            return
        except Exception as exc:
            st.error(ui_text("followup.rag_error_prefix", language) + str(exc))
            return
        save_profile_result(updated, RESULT_PATH)
        _set_profile_result(updated, "session_state")
        st.session_state["final_report"] = None
        st.session_state["ip_final_career_report"] = None
        st.session_state["ip_followup_active"] = False
        st.session_state["ip_followup_complete"] = True
        st.rerun()
        return

    progress_text = ui_text(
        "followup.question_progress",
        language,
        current=len(questions_asked) + 1,
        maximum=MAX_FOLLOWUP_QUESTIONS,
    )
    with st.container(border=True):
        st.caption(progress_text)
        st.markdown(f"#### {followup_question_text(current, language)}")
    with st.form(f"followup_question_{len(questions_asked)}"):
        answer = st.text_area(ui_text("followup.answer_label", language), key=f"followup_answer_{len(questions_asked)}")
        submitted = st.form_submit_button(ui_text("followup.submit_answer", language), use_container_width=True)

    if not submitted:
        return
    if not answer.strip():
        st.warning(ui_text("followup.empty_answer_warning", language))
        return

    updated_plan, updated_answers = record_followup_answer(question_plan, questions_asked, answer)
    st.session_state["ip_followup_plan"] = updated_plan
    st.session_state["ip_followup_answers"] = updated_answers
    st.session_state["followup_answers"] = updated_answers
    partial = {
        **result,
        "followup_refinement": {
            "method": "in_progress",
            "question_plan": updated_plan,
            "questions_asked": updated_answers,
            "final_refinement": {},
            "json_valid": True,
        },
    }
    save_profile_result(partial, RESULT_PATH)
    _set_profile_result(partial, "session_state")
    st.rerun()


# The ranker's weights (ip_refinement_ranker._score_match), shown with each part's name.
SCORE_PARTS = ("riasec_interest_fit", "job_zone_fit", "task_work_activity_similarity",
               "skills_knowledge_similarity", "work_context_fit", "ai_impact_preference")


def _show_followup_refinement(result: dict[str, Any], language: str) -> None:
    """What each answer was read as, and how the answers changed the code and the order (ROADMAP 10.4)."""
    refinement = result.get("followup_refinement") or {}
    if not refinement.get("json_valid", True):
        st.warning(ui_text("followup.invalid_json_warning", language))
    areas = lambda letters: ", ".join(interest_label(canonical_interest(letter), language) for letter in letters)  # noqa: E731

    readings = {item.get("question_id"): item for item in refinement.get("question_results") or []}
    st.markdown(f"#### {ui_text('followup.effects.answers', language)}")
    for item in refinement.get("questions_asked") or []:
        reading = readings.get(item.get("id")) or {}
        with st.container(border=True):
            st.markdown(f"**{followup_question_text(item, language)}**")
            st.write(f"{ui_text('followup.effects.your_answer', language)}: {item.get('answer')}")
            st.write(f"{ui_text('followup.effects.read_as', language)}: **{areas(reading.get('dominant_categories') or []) or '–'}**")
            if reading.get("reasoning"):
                st.caption(reading["reasoning"])  # the model's own words, in English

    filtering = refinement.get("filtering_result") or {}
    votes = filtering.get("vote_detail") or {}
    if votes:
        st.markdown(f"#### {ui_text('followup.effects.code', language)}")
        before, after = filtering.get("original_code"), filtering.get("refined_code")
        st.write(ui_text("followup.effects.code_same" if before == after else "followup.effects.code_changed",
                         language, before=before, after=after))
        st.dataframe(
            [{ui_text("followup.effects.area", language): areas([letter]), ui_text("followup.effects.votes", language): round(value, 1)}
             for letter, value in sorted(votes.items(), key=lambda item: -item[1])],
            hide_index=True,
        )

    ranked = result.get("final_ranked_matches") or []
    if ranked:
        st.markdown(f"#### {ui_text('followup.effects.order', language)}")
        st.caption(ui_text("followup.effects.order_note", language))
        rows = []
        for rank, match in enumerate(ranked, start=1):
            parts = match.get("score_components") or {}
            rows.append({
                ui_text("followup.effects.now", language): rank,
                ui_text("followup.effects.before", language): match.get("original_rank"),
                ui_text("report.compare.career", language): content_text(match.get("career_title"), language),
                ui_text("followup.effects.score", language): round(100 * (match.get("score") or 0)),
                **{ui_text(f"followup.effects.part.{part}", language): round(100 * (parts.get(part) or 0)) for part in SCORE_PARTS},
            })
        st.dataframe(rows, hide_index=True)


def _rag_artifacts_ready() -> tuple[bool, dict[str, Any]]:
    inspection = _inspect_rag_artifacts_cached()
    return bool(inspection.get("rag_enabled")), inspection


def _render_missing_artifacts_message(inspection: dict[str, Any], language: str) -> None:
    st.error(_format_missing_artifacts_error_for_ui(inspection, language))


def _format_missing_artifacts_error_for_ui(inspection: dict[str, Any], language: str) -> str:
    missing = list(inspection.get("missing") or [])
    if normalize_language(language) == "en":
        return format_missing_artifacts_error(missing)

    build_command = inspection.get("build_command") or r"python scripts\build_all_artifacts.py"
    check_command = inspection.get("check_command") or r"python scripts\check_artifacts.py"
    lines = [
        ui_text("artifacts.missing_title", language),
        "",
        ui_text("artifacts.missing_list", language),
    ]
    for artifact in missing:
        detail = artifact.get("display_path") or artifact.get("path")
        count = artifact.get("count")
        error = artifact.get("error")
        suffix = ""
        if count is not None:
            suffix += f" (count={count})"
        if error:
            suffix += f" - {error}"
        lines.append(f"- {artifact_label(artifact, language)}: {detail}{suffix}")

    lines.extend(
        [
            "",
            ui_text("artifacts.rebuild", language),
            f"  {build_command}",
            "",
            ui_text("artifacts.verify", language),
            f"  {check_command}",
        ]
    )
    return "\n".join(lines)


def _load_saved_final_report() -> dict[str, Any] | None:
    if not FINAL_REPORT_PATH.exists():
        return None
    try:
        with FINAL_REPORT_PATH.open("r", encoding="utf-8") as file:
            value = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _current_report(result: dict[str, Any], language: str) -> dict[str, Any] | None:
    """The report for this profile and language: from the session or the saved file, else built now.
    Building makes no LLM call since "a day in the life" was removed, so it needs no button."""
    if (result.get("followup_refinement") or {}).get("method") == "in_progress":
        st.info(ui_text("final.finish_followup_info", language))
        return None
    rag_ready, inspection = _rag_artifacts_ready()
    if not rag_ready:
        _render_missing_artifacts_message(inspection, language)
        return None

    report = st.session_state.get("final_report") or _load_saved_final_report()
    if report and (_validate_report_matches_profile(report, result) or not _report_uses_current_future_grouping(report)):
        report = None  # made for other answers, or in an older format
    if report and report.get("language", "en") == language:  # the report's sentences are in one language (6.1d)
        st.session_state["final_report"] = report
        return report
    return _build_and_store_report(result, language)


def _build_and_store_report(result: dict[str, Any], language: str) -> dict[str, Any] | None:
    """Build the final report in `language` and keep it in the session; None (with an error shown) on failure."""
    with st.spinner(ui_text("final.spinner", language)):
        try:
            report = build_final_career_report(result, top_k=10, language=language)
            validation_errors = _validate_report_matches_profile(report, result)
            if validation_errors:
                st.error(ui_text("final.validation_failed_prefix", language) + "; ".join(validation_errors))
                return None
        except Exception as exc:
            st.error(ui_text("final.generation_error_prefix", language) + str(exc))
            return None
    st.session_state["final_report"] = report
    st.session_state["ip_final_career_report"] = report
    return report


def _report_uses_current_future_grouping(report: dict[str, Any]) -> bool:
    # Reports saved in an older format are rebuilt; "department_10" is a department's report (ROADMAP 9.1).
    if report.get("top_match_grouping") not in {"current_zone_5_future_zone_5", "department_10"}:
        return False
    if report.get("alternative_grouping") != "job_zone_3":  # alternatives by preparation level (Phase 10)
        return False
    return all(match.get("match_group") for match in report.get("top_matches") or [])


def _current_screen(has_profile: bool) -> str:
    """"test" or "results" (ROADMAP 9.6); a saved profile opens on its results."""
    screen = st.session_state.get("ip_screen") or ("results" if has_profile else "test")
    if not has_profile:
        screen = "test"
    st.session_state["ip_screen"] = screen
    return screen


def _screen_button(label_key: str, screen: str, language: str) -> None:
    if st.button(ui_text(label_key, language), key=f"to_{screen}", use_container_width=True):
        st.session_state["ip_screen"] = screen
        st.rerun()


def _render_results_screen(result: dict[str, Any], language: str) -> None:
    st.title(ui_text("results.header", language))
    report = _current_report(result, language)
    careers, refine, about = st.tabs(
        [ui_text("report.tab.careers", language), ui_text("followup.header", language), ui_text("report.tab.about", language)],
        key=f"results_tabs_{language}",  # keeps the open tab when a career is picked
    )
    with careers:
        if report:
            render_careers(report, language)
    with refine:
        _render_followup(result, language)
    with about:
        render_about_data(report or {}, language)


def _render_test_screen(language: str) -> None:
    _, middle, _ = st.columns([1, 2, 1])  # one readable column in the middle of the screen
    with middle:
        _render_initial_form(language)


def main() -> None:
    st.set_page_config(page_title="AI Aware Career Guide", layout="wide")
    _render_global_styles()
    result, _source = _get_current_profile_result()
    screen = _current_screen(bool(result))
    language = _render_sidebar(result, screen)
    if screen == "results":
        _render_results_screen(result, language)
    else:
        _render_test_screen(language)


if __name__ == "__main__":
    main()

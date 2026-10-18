"""Follow-up-aware ranking for Interest Profiler career candidates."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from career_rag.artifacts import ensure_required_artifacts
from career_rag.config import ONET_DUCKDB_PATH, RANKER_COMMON_WORDS_PATH, TASK_VECTORS_PATH
from career_rag.ip_ai_impact import _local_ai_rows_for_soc, _observed_exposure
from career_rag.interest_profiler_local import (
    canonical_interest,
    make_holland_code,
)
from career_rag.occupation_aliases import build_occupation_index, resolve_career_alias


DB_PATH = ONET_DUCKDB_PATH
RANKED_MATCH_KEYS = ["department", "future_zone", "current_zone"]  # "department": ROADMAP 9.1
# The career texts the answers are compared with word by word, by the bundle keys that make them up. A word common
# in a part's text across careers is ignored there (data/ranker/common_words.csv, scripts/onet/build_common_words.py).
RANKER_PARTS = {"skills": ("skills", "knowledge")}
# The answers-vs-tasks part compares meaning, not words (CHANGELOG 104): each answer and every O*NET task are
# embedded (data/duckdb/onet_task_vectors.npz), and an answer is the query this instruction describes.
ANSWER_INSTRUCTION = "Given a student's answer about the work they would enjoy, retrieve job tasks that match it"
# Only the answers that describe the work itself: the others are about setting, values or fears, and their topic
# matched the opposite ("little human interaction" came closest to waiters' tasks; "everyday doing the same
# thing", a fear, to file clerks').
TASK_QUESTIONS = ("work_with", "skill_anchor", "dream_scenario")
# The work-setting part (CHANGELOG 103): for each setting preference found in the answers, O*NET's rating of the
# matching work-context items (scale CX, 1 = never or none to 5 = every day or constant), and whether a higher
# rating fits the preference. It replaced word overlap with the career's work-context texts, which were mostly
# items the job never involves ("Outdoors, Exposed to All Weather Conditions: Never" matched "outdoors").
SETTING_RATINGS = {
    "outdoor or field work": (("Outdoors, Exposed to All Weather Conditions", "Outdoors, Under Cover"), True),
    "lower social intensity": (("Contact With Others",), False),
    "structured independent work": (("Freedom to Make Decisions",), True),
}

STOPWORDS = {
    "a",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "do",
    "for",
    "from",
    "have",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
    "work",
    "working",
    "would",
}

# Hand-written vocabulary; its origin is not documented. Some mappings are questionable
# (e.g. "environment" -> outdoor work, "realistic" -> stability concern); see
# docs/CHANGELOG.md entry 017. To be revisited with the follow-up question redesign.
PREFERENCE_KEYWORDS = {
    "ai-aware career planning": ("ai", "automation", "automated", "artificial intelligence", "future proof"),
    "technology systems": ("technology", "tech", "software", "computer", "systems", "digital", "programming"),
    "data and numbers": ("data", "numbers", "analytics", "analysis", "statistical", "statistics", "math"),
    "research and problem solving": ("research", "science", "investigate", "understand", "problem", "solve"),
    "hands-on technical work": ("hands-on", "tools", "machines", "equipment", "build", "repair", "fix", "fixing"),
    "outdoor or field work": ("outdoor", "outside", "field", "nature", "environment"),
    "creative design or writing": ("creative", "design", "visual", "writing", "art", "arts", "artist", "music", "perform"),
    "teaching or guiding people": ("teach", "teaching", "guide", "guiding", "help", "support", "mentor"),
    "leading or persuading": ("lead", "leading", "persuade", "sell", "sales", "pitch", "manage"),
    "structured independent work": ("structured", "organized", "records", "process", "independent", "alone"),
    "fast-paced projects": ("fast", "pace", "short projects", "multiple projects", "startup"),
    "job stability concern": ("stability", "stable", "secure", "risk", "worry", "concern", "realistic"),
    "lower social intensity": ("less people", "low social", "alone", "independent", "not talking", "by myself",
                               "on my own", "little human", "little interaction", "less interaction", "few people"),
}


def build_initial_ranked_matches(career_matches: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten original IP match groups into a stable candidate-pool order."""
    flattened: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    for group in RANKED_MATCH_KEYS:
        for index, career in enumerate(career_matches.get(group, []) or [], start=1):
            title = _clean_text(career.get("career_title"))
            if not title:
                continue
            title_key = _normalize(title)
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            flattened.append(
                {
                    **career,
                    "career_title": title,
                    "source_match_group": group,
                    "original_rank": len(flattened) + 1,
                    "original_group_rank": index,
                    "ranking_explanation": {
                        "original_profile": _original_profile_reason(career, group),
                        "followup_effects": [],
                    },
                }
            )
    return flattened


def build_refined_career_recommendations(
    profile_result: dict[str, Any],
    followup_refinement: dict[str, Any] | None,
    db_path: str | Path = DB_PATH,
) -> dict[str, Any]:
    """Return profile fields for final follow-up-aware career ranking."""
    initial_matches = build_initial_ranked_matches(profile_result.get("career_matches") or {})
    questions_asked = list((followup_refinement or {}).get("questions_asked") or [])
    final_refinement = (followup_refinement or {}).get("final_refinement") or {}
    preferences_used = extract_structured_preferences(followup_refinement)

    if not questions_asked:
        initial_with_scores = [
            {
                **match,
                "score": round(1.0 - index * 0.001, 4),
                "score_components": _empty_score_components(),
            }
            for index, match in enumerate(initial_matches)
        ]
        return _ranking_payload(
            initial_matches=initial_matches,
            final_matches=initial_with_scores,
            profile_result=profile_result,
            followup_refinement=followup_refinement,
            preferences_used=preferences_used,
            warnings=[],
        )

    ensure_required_artifacts()
    target_interests = _target_interests(profile_result, final_refinement)
    target_zone = _target_job_zone(profile_result, final_refinement)
    preference_text = _preference_text(followup_refinement)
    occupation_index = build_occupation_index(db_path)

    scored_matches = []
    try:
        import duckdb
    except ImportError as exc:
        raise RuntimeError("duckdb is required for follow-up RAG ranking.") from exc

    if not Path(db_path).exists():
        raise FileNotFoundError(f"O*NET DuckDB database not found: {db_path}")

    meaning_fit = _meaning_fit_by_career([
        str(item.get("answer") or "") for item in questions_asked
        if item.get("id") in TASK_QUESTIONS and str(item.get("answer") or "").strip()
    ])
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        for match in initial_matches:
            scored_matches.append(
                _score_match(
                    match=match,
                    profile_result=profile_result,
                    target_interests=target_interests,
                    target_zone=target_zone,
                    preference_text=preference_text,
                    preferences_used=preferences_used,
                    occupation_index=occupation_index,
                    conn=conn,
                    meaning_fit=meaning_fit,
                )
            )
    finally:
        if conn is not None:
            conn.close()

    scored_matches.sort(
        key=lambda item: (
            -float(item.get("score") or 0),
            int(item.get("original_rank") or 9999),
        )
    )

    warnings = []
    if _title_order(scored_matches) == _title_order(initial_matches):
        warnings.append(
            "Follow-up answers exist, but final_ranked_matches is identical to the original career_matches order."
        )

    return _ranking_payload(
        initial_matches=initial_matches,
        final_matches=scored_matches,
        profile_result=profile_result,
        followup_refinement=followup_refinement,
        preferences_used=preferences_used,
        warnings=warnings,
    )


def extract_structured_preferences(
    followup_refinement: dict[str, Any] | None,
) -> list[str]:
    """Convert follow-up answers into reusable preference labels.

    The labels are found in the student's own answers only (ROADMAP 10.12). The refinement's summaries
    carry question names and interest letters ("structure_preference: AI - no clear agenda"), and "AI"
    there means Artistic + Investigative: read as artificial intelligence, it tagged every such student
    "ai-aware career planning".
    """
    if not followup_refinement:
        return []
    final_refinement = followup_refinement.get("final_refinement") or {}
    combined = _preference_text(followup_refinement).lower()
    preferences = [
        label
        for label, keywords in PREFERENCE_KEYWORDS.items()
        if any(_mentions(combined, keyword) for keyword in keywords)
    ]

    for item in final_refinement.get("key_sub_preferences") or []:
        cleaned = _clean_text(item)
        if cleaned and cleaned not in preferences:
            preferences.append(cleaned)
    return preferences[:12]


def _score_match(
    match: dict[str, Any],
    profile_result: dict[str, Any],
    target_interests: list[str],
    target_zone: int,
    preference_text: str,
    preferences_used: list[str],
    occupation_index: list[dict[str, Any]],
    conn: Any | None,
    meaning_fit: dict[str, float] | None = None,
) -> dict[str, Any]:
    resolution = resolve_career_alias(match.get("career_title", ""), occupation_index)
    bundle = _occupation_signal_bundle(conn, resolution.get("onet_soc_code")) if conn else {}
    scores = profile_result.get("riasec_scores") or profile_result.get("raw_riasec_scores") or {}

    components = {
        "riasec_interest_fit": _riasec_interest_fit(match.get("interest"), target_interests, scores),
        "job_zone_fit": _job_zone_fit(match.get("job_zone"), target_zone),
        "task_work_activity_similarity": (meaning_fit or {}).get(str(resolution.get("onet_soc_code") or ""), 0.0),
        "skills_knowledge_similarity": _text_similarity(
            preference_text,
            [*bundle.get("skills", []), *bundle.get("knowledge", [])],
            _common_words()["skills"],
        ),
        "work_context_fit": _work_context_fit(preferences_used, bundle.get("setting_ratings", {})),
        "ai_impact_preference": _ai_preference_score(
            preference_text,
            resolution.get("onet_soc_code"),
        ),
    }
    # Hand-chosen weights, not validated against any data; the same holds for the
    # constants inside the scoring helpers below. Evaluate before relying on them (ROADMAP 5.2).
    weights = {
        "riasec_interest_fit": 0.28,
        "job_zone_fit": 0.18,
        "task_work_activity_similarity": 0.22,
        "skills_knowledge_similarity": 0.17,
        "work_context_fit": 0.10,
        "ai_impact_preference": 0.05,
    }
    total = sum(components[key] * weight for key, weight in weights.items())
    explanation = _ranking_explanation(match, components, target_interests, target_zone)
    return {
        **match,
        "resolved_onet_title": resolution.get("resolved_onet_title"),
        "onet_soc_code": resolution.get("onet_soc_code"),
        "score": round(total, 4),
        "score_components": {key: round(value, 4) for key, value in components.items()},
        "ranking_explanation": explanation,
    }


def _occupation_signal_bundle(conn: Any, soc_code: Any) -> dict[str, list[str]]:
    code = _clean_text(soc_code)
    if not code:
        return {}
    return {
        "skills": _fetch_element_names(conn, "essential_skills", code, 25),
        "knowledge": _fetch_element_names(conn, "knowledge", code, 25),
        "setting_ratings": _fetch_setting_ratings(conn, code),
    }


def _fetch_element_names(conn: Any, table_name: str, code: str, limit: int) -> list[str]:
    if not _table_exists(conn, table_name):
        return []
    return _fetch_column(
        conn,
        f"""
        SELECT cmr.element_name
        FROM {table_name} AS item
        JOIN content_model_reference AS cmr
            ON item.element_id = cmr.element_id
        WHERE item.onetsoc_code = ?
        ORDER BY item.data_value DESC, cmr.element_name
        LIMIT ?
        """,
        [code, limit],
    )


def _fetch_setting_ratings(conn: Any, code: str) -> dict[str, float]:
    """{work-context item: O*NET's rating, 1 to 5} for the items SETTING_RATINGS reads."""
    names = sorted({name for elements, _ in SETTING_RATINGS.values() for name in elements})
    rows = conn.execute(
        f"""
        SELECT element_name, data_value FROM work_context
        WHERE onetsoc_code = ? AND scale_id = 'CX' AND element_name IN ({", ".join("?" * len(names))})
        """,
        [code, *names],
    ).fetchall()
    return {name: float(value) for name, value in rows}


def _fetch_column(conn: Any, query: str, params: list[Any]) -> list[str]:
    rows = conn.execute(query, params).fetchall()
    return [_clean_text(row[0]) for row in rows if _clean_text(row[0])]


def _table_exists(conn: Any, table_name: str) -> bool:
    return bool(
        conn.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_name = ?
            LIMIT 1
            """,
            [table_name],
        ).fetchone()
    )


def _target_interests(profile_result: dict[str, Any], final_refinement: dict[str, Any]) -> list[str]:
    values = (
        (final_refinement.get("career_matching_guidance") or {}).get("prioritize_interests")
        or final_refinement.get("refined_top_interests")
        or profile_result.get("final_top_interests")
        or profile_result.get("initial_top_interests")
        or []
    )
    result = []
    for value in values:
        try:
            result.append(canonical_interest(value))
        except ValueError:
            continue
    return result[:3] or list(profile_result.get("initial_top_interests") or [])[:3]


def _target_job_zone(profile_result: dict[str, Any], final_refinement: dict[str, Any]) -> int:
    guidance = final_refinement.get("career_matching_guidance") or {}
    try:
        zone = int(guidance.get("job_zone_to_use") or profile_result.get("future_job_zone") or 0)
    except (TypeError, ValueError):
        zone = 0
    return zone if zone in {1, 2, 3, 4, 5} else int(profile_result.get("future_job_zone") or 3)


def _riasec_interest_fit(candidate_interest: Any, target_interests: list[str], scores: dict[str, Any]) -> float:
    try:
        interest = canonical_interest(candidate_interest)
    except ValueError:
        return 0.0
    try:
        raw_score = float(scores.get(interest, 0))
    except (TypeError, ValueError):
        raw_score = 0.0
    raw_component = min(1.0, max(0.0, raw_score / 10.0))
    if interest in target_interests:
        rank_component = 1.0 - 0.16 * target_interests.index(interest)
    else:
        rank_component = 0.25
    return max(0.0, min(1.0, 0.55 * rank_component + 0.45 * raw_component))


def _job_zone_fit(candidate_zone: Any, target_zone: int) -> float:
    try:
        zone = int(candidate_zone)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, 1.0 - abs(zone - target_zone) / 4.0)


def _text_similarity(query: str, documents: list[str], common: frozenset[str] = frozenset()) -> float:
    """The best share of words one document shares with the query, ignoring the `common` words."""
    query_tokens = _tokens(query) - common
    if not query_tokens or not documents:
        return 0.0
    best = 0.0
    for document in documents:
        doc_tokens = _tokens(document) - common
        if not doc_tokens:
            continue
        overlap = len(query_tokens & doc_tokens)
        if not overlap:
            continue
        score = overlap / max(6, min(len(query_tokens), len(doc_tokens)))
        best = max(best, min(1.0, score))
    return best


def _work_context_fit(preferences_used: list[str], ratings: dict[str, float]) -> float:
    """How well the career's O*NET work-context ratings fit the setting preferences in the answers, 0 to 1:
    the average over those preferences; 0.5 when the answers name none or the career has no rating."""
    fits = []
    for label, (elements, higher_fits) in SETTING_RATINGS.items():
        values = [ratings[name] for name in elements if name in ratings]
        if label in preferences_used and values:
            share = (max(values) - 1) / 4  # 1 (never, none) -> 0; 5 (every day, constant) -> 1
            fits.append(share if higher_fits else 1 - share)
    return sum(fits) / len(fits) if fits else 0.5


def _meaning_fit_by_career(answers: list[str]) -> dict[str, float]:
    """{O*NET-SOC code: how close in meaning the answers are to the career's tasks, as the share of all careers
    that are less close, 0 to 1}.

    For each answer, a career's closeness is its best-matching task's cosine similarity minus that answer's
    average over all careers, so an answer that fits every career ("visible outcome") moves none of them.
    A career's closeness is the average over the answers.
    """
    if not answers:
        return {}
    from career_rag.embeddings import embed_queries

    codes, starts, vectors = _task_vectors()
    similarity = embed_queries(answers, ANSWER_INSTRUCTION) @ vectors.T  # answers x tasks
    best = np.maximum.reduceat(similarity, starts, axis=1)  # answers x careers: each career's closest task
    closeness = (best - best.mean(axis=1, keepdims=True)).mean(axis=0)
    ranks = closeness.argsort().argsort()
    return {code: float(rank / (len(codes) - 1)) for code, rank in zip(codes, ranks)}


@lru_cache(maxsize=1)
def _task_vectors() -> tuple[list[str], Any, Any]:
    """(career codes in order, the row where each career's tasks start, the task vectors as float32)."""
    data = np.load(TASK_VECTORS_PATH)
    codes, starts = np.unique(data["codes"], return_index=True)  # the rows are sorted by career code
    return [str(code) for code in codes], starts, data["vectors"].astype(np.float32)


@lru_cache(maxsize=1)
def _common_words() -> dict[str, frozenset[str]]:
    """{part: the words in at least a quarter of the careers' text for that part}, which can't tell careers apart:
    "making" (from "Making Decisions and Solving Problems") was in 96% of careers' tasks and activities, "people"
    in 69%, so most careers got the same one-word overlap."""
    import csv

    words: dict[str, set[str]] = {part: set() for part in RANKER_PARTS}
    with RANKER_COMMON_WORDS_PATH.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            words[row["part"]].add(row["word"])
    return {part: frozenset(found) for part, found in words.items()}


def _ai_preference_score(preference_text: str, soc_code: Any) -> float:
    text = preference_text.lower()
    if not any(_mentions(text, term) for term in ("ai", "automation", "technology", "future proof", "stability")):
        return 0.5
    exposure = _observed_exposure(_local_ai_rows_for_soc(str(soc_code or "")))
    if exposure is None:
        return 0.5
    if any(_mentions(text, term) for term in ("stability", "stable", "secure", "worry", "concern", "automation")):
        return max(0.0, min(1.0, 1.0 - exposure))
    return max(0.0, min(1.0, exposure))


def _ranking_explanation(
    match: dict[str, Any],
    components: dict[str, float],
    target_interests: list[str],
    target_zone: int,
) -> dict[str, Any]:
    effects = []
    if components["task_work_activity_similarity"] >= 0.75:
        effects.append("The follow-up answers are closer in meaning to this occupation's O*NET tasks than to most careers'.")
    if components["skills_knowledge_similarity"] >= 0.25:
        effects.append("Follow-up preferences matched its O*NET skills or knowledge areas.")
    if components["work_context_fit"] >= 0.65:
        effects.append("Work-context signals align with the follow-up constraints.")
    if components["job_zone_fit"] < 0.75:
        effects.append(f"Job Zone {match.get('job_zone')} is farther from the follow-up target zone {target_zone}.")
    if components["task_work_activity_similarity"] < 0.25 and components["skills_knowledge_similarity"] < 0.10:
        effects.append("The follow-up answers are far in meaning from this occupation's tasks, and share few skill words.")
    return {
        "original_profile": _original_profile_reason(match, match.get("source_match_group")),
        "followup_effects": effects,
        "target_interests": target_interests,
        "target_job_zone": target_zone,
    }


def _original_profile_reason(match: dict[str, Any], group: Any) -> str:
    fit = _clean_text(match.get("fit"))
    similarity = _clean_text(match.get("interest_similarity"))
    zone = _clean_text(match.get("job_zone"))
    group_text = _clean_text(group).replace("_", " ")
    return f"O*NET Interest Profiler match: {fit} (r = {similarity}) in Job Zone {zone} ({group_text})."


def _ranking_payload(
    initial_matches: list[dict[str, Any]],
    final_matches: list[dict[str, Any]],
    profile_result: dict[str, Any],
    followup_refinement: dict[str, Any] | None,
    preferences_used: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    debug = {
        "initial_code": profile_result.get("initial_code") or profile_result.get("initial_holland_code"),
        "final_code": profile_result.get("final_code") or profile_result.get("final_holland_code"),
        "followup_refinement": followup_refinement,
        "preferences_used": preferences_used,
        "top_10_initial_matches": _debug_match_rows(initial_matches[:10]),
        "top_10_refined_matches": _debug_match_rows(final_matches[:10]),
        "score_components": [
            {
                "career_title": item.get("career_title"),
                "score": item.get("score"),
                "score_components": item.get("score_components"),
                "ranking_explanation": item.get("ranking_explanation"),
            }
            for item in final_matches[:10]
        ],
        "validation_warnings": warnings,
    }
    return {
        "preferences_used": preferences_used,
        "refined_career_matches": final_matches,
        "final_ranked_matches": final_matches,
        "refinement_debug": debug,
        "validation_warnings": warnings,
    }


def _debug_match_rows(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "career_title": item.get("career_title"),
            "interest": item.get("interest"),
            "job_zone": item.get("job_zone"),
            "score": item.get("score"),
        }
        for item in matches
    ]


def _empty_score_components() -> dict[str, float]:
    return {
        "riasec_interest_fit": 1.0,
        "job_zone_fit": 1.0,
        "task_work_activity_similarity": 0.0,
        "skills_knowledge_similarity": 0.0,
        "work_context_fit": 0.5,
        "ai_impact_preference": 0.5,
    }


def _preference_text(followup_refinement: dict[str, Any] | None) -> str:
    """The student's own answers, the only text compared with careers (ROADMAP 10.12).

    It used to include the question names ("structure_preference", "impact_type"), the interest letters
    and tags added by the app, and generated summaries ("Dream scenario: …"): their words matched
    nearly every career's tasks, so most careers got the same one-word overlap.
    """
    return " ".join(str(item.get("answer") or "") for item in (followup_refinement or {}).get("questions_asked") or [])


def _mentions(text: str, keyword: str) -> bool:
    """True if `keyword` starts a word in `text`; keywords of 3 letters or fewer must be whole words.

    Plain substring checks matched "ai" inside "training" and "pace" inside "space".
    """
    ending = r"\b" if len(keyword) <= 3 else ""
    return re.search(rf"\b{re.escape(keyword)}{ending}", text) is not None


def _title_order(matches: list[dict[str, Any]]) -> list[str]:
    return [_normalize(item.get("career_title")) for item in matches]


def _tokens(value: Any) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", str(value or "").lower())
        if len(token) > 2 and token not in STOPWORDS
    }


def _normalize(value: Any) -> str:
    text = str(value or "").lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def update_profile_with_followup(
    profile_result: dict[str, Any],
    followup_refinement: dict[str, Any],
) -> dict[str, Any]:
    """Attach follow-up refinement and rebuild final career ranking."""
    updated = dict(profile_result)
    updated["followup_refinement"] = followup_refinement

    final_refinement = followup_refinement.get("final_refinement") or {}
    questions_asked = list(followup_refinement.get("questions_asked") or [])
    initial_top = [canonical_interest(interest) for interest in updated.get("initial_top_interests", [])]
    proposed_top = final_refinement.get("refined_top_interests") or initial_top
    if questions_asked and _refined_interests_justified(updated, final_refinement, proposed_top):
        refined_top = [canonical_interest(interest) for interest in proposed_top][:3]
    else:
        refined_top = initial_top
    refined_holland = make_holland_code(refined_top)

    updated["final_top_interests"] = refined_top
    updated["final_holland_code"] = refined_holland
    updated["refined_interests"] = updated["final_top_interests"]
    updated["final_code"] = updated["final_holland_code"]

    ranking_update = build_refined_career_recommendations(updated, followup_refinement)

    updated["preferences_used"] = ranking_update.get("preferences_used", [])
    updated["refined_career_matches"] = ranking_update.get("refined_career_matches", [])
    updated["final_ranked_matches"] = ranking_update.get("final_ranked_matches", [])
    updated["refinement_debug"] = ranking_update.get("refinement_debug", {})
    updated["validation_warnings"] = ranking_update.get("validation_warnings", [])
    updated["ready_for_rag"] = True
    return updated


def _refined_interests_justified(
    profile_result: dict[str, Any],
    final_refinement: dict[str, Any],
    proposed_top: Any,
) -> bool:
    try:
        proposed = [canonical_interest(interest) for interest in list(proposed_top)[:3]]
    except (TypeError, ValueError):
        return False
    initial_top = [canonical_interest(interest) for interest in profile_result.get("initial_top_interests", [])]
    if proposed == initial_top:
        return True

    ambiguity = profile_result.get("score_ambiguity") or {}
    ambiguous = [canonical_interest(interest) for interest in ambiguity.get("ambiguous_categories", [])]
    guidance = final_refinement.get("career_matching_guidance") or {}
    prioritized = []
    for interest in guidance.get("prioritize_interests") or []:
        try:
            prioritized.append(canonical_interest(interest))
        except ValueError:
            continue
    tie_resolution = final_refinement.get("tie_resolution") or {}
    resolved_order = []
    for interest in tie_resolution.get("resolved_order") or []:
        try:
            resolved_order.append(canonical_interest(interest))
        except ValueError:
            continue

    if ambiguity.get("has_ambiguity") and set(proposed).issubset(set(initial_top) | set(ambiguous)):
        return bool(resolved_order or prioritized)
    return bool(prioritized and proposed[: len(prioritized)] == prioritized[: len(proposed)])

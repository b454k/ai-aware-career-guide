"""Local career matching for O*NET Interest Profiler results."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from career_rag.config import ONET_DUCKDB_PATH
from career_rag.interest_profiler_local import RIASEC_INTERESTS

# career_interest_types element ids, in RIASEC order (content_model_reference 1.B.1.a-f).
INTEREST_ELEMENTS = dict(zip(["1.B.1.a", "1.B.1.b", "1.B.1.c", "1.B.1.d", "1.B.1.e", "1.B.1.f"], RIASEC_INTERESTS))

# The Job Zones since O*NET 30.3: zones 1 and 2 merged into "Job Zone 1-2", stored as 2.
# validate_job_zone still accepts 1 from older saved profiles (read as 2).
ONET_JOB_ZONES = (2, 3, 4, 5)


def validate_job_zone(job_zone: Any) -> int:
    """Validate an O*NET Job Zone value."""
    try:
        zone = int(job_zone)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Job Zone must be an integer 1-5: {job_zone!r}") from exc
    if zone not in {1, *ONET_JOB_ZONES}:
        raise ValueError(f"Job Zone must be an integer 1-5: {zone}.")
    return zone


# O*NET's own matching rule for the Interest Profiler Short Form (Gregory & Lewis 2016,
# "Linking Client Assessment Profiles to O*NET Occupational Profiles", pp. 11-12):
# Pearson r between the user's six scores and the occupation's six interest scores.
BEST_FIT_MIN_R = 0.729  # "very strong" match, p < .05 one-tailed
GREAT_FIT_MIN_R = 0.608  # "strong" match, p < .10 one-tailed
FILL_TO = 10  # if fewer Best + Great, fill up to 10 with the next non-negative r ("Good fit")


def pearson(xs: list[float], ys: list[float]) -> float | None:
    """Pearson correlation; None when either profile is flat (all six values equal)."""
    mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if not var_x or not var_y:
        return None
    return cov / (var_x * var_y) ** 0.5


def onet_fit_list(scores: dict[str, Any], occupations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply O*NET's rule to one Job Zone's occupations (each with `interest_scores` in RIASEC order).

    O*NET shows each fit band alphabetically; we sort by r instead, so the first
    careers shown are the strongest matches.
    """
    user = [float(scores.get(interest, 0)) for interest in RIASEC_INTERESTS]
    scored = []
    for occupation in occupations:
        r = pearson(user, occupation["interest_scores"])
        if r is not None:
            scored.append((r, occupation))
    scored.sort(key=lambda item: (-item[0], item[1]["career_title"]))

    strong = [(r, occ) for r, occ in scored if r >= GREAT_FIT_MIN_R]
    fill = [(r, occ) for r, occ in scored if 0 <= r < GREAT_FIT_MIN_R][: max(0, FILL_TO - len(strong))]
    return [
        {
            **{key: value for key, value in occ.items() if key != "interest_scores"},
            "fit": "Best fit" if r >= BEST_FIT_MIN_R else "Great fit" if r >= GREAT_FIT_MIN_R else "Good fit",
            "interest_similarity": round(r, 3),
        }
        for r, occ in strong + fill
    ]


def load_zone_occupations(job_zone: int, db_path: str | Path = ONET_DUCKDB_PATH) -> list[dict[str, Any]]:
    """All occupations in a Job Zone with their six O*NET interest scores (scale OI)."""
    import duckdb

    # O*NET 30.3 merged Job Zones 1 and 2 into "Job Zone 1-2", stored as 2 (ROADMAP 2.8).
    db_zone = 2 if job_zone == 1 else job_zone
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = conn.execute(
            """
            SELECT o.onetsoc_code, o.title, i.element_id, i.data_value
            FROM job_zones AS z
            JOIN occupation_data AS o ON o.onetsoc_code = z.onetsoc_code
            JOIN career_interest_types AS i ON i.onetsoc_code = z.onetsoc_code AND i.scale_id = 'OI'
            WHERE z.job_zone = ?
            """,
            [db_zone],
        ).fetchall()
    finally:
        conn.close()

    by_code: dict[str, dict[str, Any]] = {}
    for code, title, element_id, value in rows:
        occupation = by_code.setdefault(code, {"career_title": title, "onet_soc_code": code, "scores": {}})
        occupation["scores"][INTEREST_ELEMENTS[element_id]] = float(value)
    occupations = []
    for occupation in by_code.values():
        profile = occupation.pop("scores")
        if len(profile) != len(RIASEC_INTERESTS):
            continue
        occupations.append(
            {
                **occupation,
                "job_zone": job_zone,
                # The occupation's highest interest ("high-point code"), used by the follow-up ranker.
                "interest": max(RIASEC_INTERESTS, key=lambda interest: profile[interest]),
                "interest_scores": [profile[interest] for interest in RIASEC_INTERESTS],
            }
        )
    return occupations


def build_career_matches(
    scores: dict[str, Any],
    current_job_zone: int,
    future_job_zone: int,
    db_path: str | Path = ONET_DUCKDB_PATH,
) -> dict[str, list[dict[str, Any]]]:
    """O*NET's matching careers for the current and the future Job Zone (ROADMAP 2.6, D11 = A2)."""
    return {
        key: onet_fit_list(scores, load_zone_occupations(validate_job_zone(zone), db_path))
        for key, zone in (("current_zone", current_job_zone), ("future_zone", future_job_zone))
    }

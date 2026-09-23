"""Local career matching for O*NET Interest Profiler results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from career_rag.config import ONET_DUCKDB_PATH
from career_rag.interest_profiler_local import (
    RIASEC_CODES,
    RIASEC_INTERESTS,
    canonical_interest,
)

# career_interest_types element ids, in RIASEC order (content_model_reference 1.B.1.a-f).
INTEREST_ELEMENTS = dict(zip(["1.B.1.a", "1.B.1.b", "1.B.1.c", "1.B.1.d", "1.B.1.e", "1.B.1.f"], RIASEC_INTERESTS))


JOB_ZONE_LABELS = {
    1: "Little or No Preparation Needed",
    2: "Some Preparation Needed",
    3: "Medium Preparation Needed",
    4: "Considerable Preparation Needed",
    5: "Extensive Preparation Needed",
}


def validate_job_zone(job_zone: Any) -> int:
    """Validate an O*NET Job Zone value."""
    try:
        zone = int(job_zone)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Job Zone must be an integer 1-5: {job_zone!r}") from exc
    if zone not in JOB_ZONE_LABELS:
        raise ValueError(f"Job Zone must be an integer 1-5: {zone}.")
    return zone


def _validate_assignment_note(note: Any) -> str | None:
    if note is None:
        return None
    note_text = str(note).strip()
    allowed = {
        "assigned_based_on_second_highest_interest",
        "assigned_based_on_third_highest_interest",
    }
    if note_text not in allowed:
        raise ValueError(f"Unknown Interest Profiler assignment note: {note!r}")
    return note_text


def validate_ip_career_listings(listings: Any) -> list[dict[str, Any]]:
    """Validate PDF-derived Interest Profiler career listings."""
    if not isinstance(listings, list):
        raise ValueError("IP career listings JSON must contain a list.")

    required_keys = {
        "interest",
        "interest_code",
        "job_zone",
        "job_zone_label",
        "career_title",
    }
    validated: list[dict[str, Any]] = []

    for index, listing in enumerate(listings, start=1):
        if not isinstance(listing, dict):
            raise ValueError(f"Career listing {index} must be an object.")

        missing = required_keys - set(listing)
        if missing:
            raise ValueError(f"Career listing {index} is missing fields: {sorted(missing)}.")

        interest = canonical_interest(str(listing["interest"]))
        interest_code = str(listing["interest_code"]).strip().upper()
        if interest_code != RIASEC_CODES[interest]:
            raise ValueError(
                f"Career listing {index} has interest_code {interest_code!r}, "
                f"expected {RIASEC_CODES[interest]!r}."
            )

        zone = validate_job_zone(listing["job_zone"])
        label = str(listing["job_zone_label"]).strip()
        if label != JOB_ZONE_LABELS[zone]:
            raise ValueError(
                f"Career listing {index} has job_zone_label {label!r}, "
                f"expected {JOB_ZONE_LABELS[zone]!r}."
            )

        title = str(listing["career_title"]).strip()
        if not title:
            raise ValueError(f"Career listing {index} career_title cannot be empty.")
        if "**" in title:
            raise ValueError(f"Career listing {index} career_title must not include asterisks.")

        validated.append(
            {
                "interest": interest,
                "interest_code": interest_code,
                "job_zone": zone,
                "job_zone_label": label,
                "career_title": title,
                "assignment_note": _validate_assignment_note(listing.get("assignment_note")),
            }
        )

    return validated


def load_ip_career_listings(path: str | Path) -> list[dict[str, Any]]:
    """Load the local PDF-derived O*NET Interest Profiler career listings."""
    listings_path = Path(path)
    with listings_path.open("r", encoding="utf-8") as file:
        listings = json.load(file)
    return validate_ip_career_listings(listings)


def match_careers(
    career_listings: list[dict[str, Any]],
    interest: str,
    job_zone: int,
) -> list[dict[str, Any]]:
    """Return all career listings matching one RIASEC interest and Job Zone."""
    validated_listings = validate_ip_career_listings(career_listings)
    canonical = canonical_interest(interest)
    zone = validate_job_zone(job_zone)
    return [
        listing
        for listing in validated_listings
        if listing["interest"] == canonical and listing["job_zone"] == zone
    ]


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


def match_nearby_careers(
    career_listings: list[dict[str, Any]],
    interest: str,
    job_zone: int,
) -> list[dict[str, Any]]:
    """Return clearly labeled adjacent Job Zone alternatives for empty exact matches."""
    zone = validate_job_zone(job_zone)
    nearby_zones = [candidate for candidate in (zone - 1, zone + 1) if candidate in JOB_ZONE_LABELS]
    alternatives: list[dict[str, Any]] = []
    for nearby_zone in nearby_zones:
        for career in match_careers(career_listings, interest, nearby_zone):
            alternatives.append({**career, "nearby_alternative_for_job_zone": zone})
    return alternatives


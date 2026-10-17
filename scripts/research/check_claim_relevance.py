#!/usr/bin/env python3
"""Ask an LLM which candidate claims are actually about each occupation (ROADMAP 4.1c, D16 = C).

Embedding similarity finds claims that sound like a career, not claims about it (CHANGELOG 031),
so each occupation's candidates from research_claims.duckdb are checked once, at build time,
with the same rule used for the hand labels in evaluation/claim_relevance_labels.csv.
The LLM only filters: the app still shows each claim's verbatim quote and source.

Answers are appended to data/research/claim_relevance_checks.jsonl (one line per call). Pairs of
occupation and claim already checked with the same model and prompt are skipped, so a rerun after
new claims are added (ROADMAP 8.2) only pays for the new pairs.
Then it writes data/research/career_research_claims.csv, what the app shows (D17 = B, committed):
for each occupation, at most SHOWN_PER_OCCUPATION claims the LLM judged relevant, highest centered
score first, one per claim text, and only claims with a centered score >= 0 (the claim fits this
career at least as well as careers on average; on the labelled set this guard changed nothing).
Claims that don't stand on their own are left out too (check_claim_standalone.py, ROADMAP 4.2), and so
are claims that say nothing about AI's effect on work (check_claim_ai_link.py, ROADMAP 10.6); a claim that is
about AI only through its source is shown in the check's rewrite, which states the link. A hand correction
(claim_corrections.csv) wins over both: its text is shown, and `show = no` hides a claim. When the shown
text differs from the extracted one (a hand text or a rewrite), relevance is asked again with the shown text,
for every career the claim is a candidate for (ROADMAP 10.7): those answers are kept with the text they judged.
Model: gpt-5.4-mini, chosen on the 40 labelled careers against gpt-4o-mini, gpt-4.1-mini and
gpt-5.4-nano (CHANGELOG 032).

    python scripts/research/check_claim_relevance.py [--model M] [--codes-from evaluation/claim_relevance_labels.csv]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import duckdb
from dotenv import load_dotenv
from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from career_rag.config import ENV_PATH, ONET_DUCKDB_PATH  # noqa: E402
import check_claim_ai_link  # noqa: E402
import check_claim_standalone  # noqa: E402

CLAIMS_DB = PROJECT_ROOT / "data" / "duckdb" / "research_claims.duckdb"
CHECKS = PROJECT_ROOT / "data" / "research" / "claim_relevance_checks.jsonl"
SHOWN = PROJECT_ROOT / "data" / "research" / "career_research_claims.csv"
CORRECTIONS = PROJECT_ROOT / "data" / "research" / "claim_corrections.csv"
SHOWN_PER_OCCUPATION = 3
SHOWN_COLUMNS = ["claim_text", "evidence_quote", "title", "authors", "year", "final_url", "page_start", "page_end"]
MODEL = "gpt-5.4-mini"
PROMPT_VERSION = 1
SYSTEM_PROMPT = (
    "You check whether research claims about AI and work are about a given occupation. "
    "A claim is relevant if it is about this occupation, its field or industry, or its main tasks. "
    "It is not relevant if it is generic (it would fit almost any job) or about other work. "
    'Answer in JSON: {"relevant": [the numbers of the relevant claims]}, an empty list if none.'
)


def user_prompt(title: str, description: str, claims: list[tuple[str, str, str]]) -> str:
    lines = [f"Occupation: {title}", f"Description: {description}", "", "Claims:"]
    lines += [f"{n}. {text} (about: {affected})" for n, (_, text, affected) in enumerate(claims, start=1)]
    return "\n".join(lines)


def check(client: OpenAI, model: str, title: str, description: str, claims: list[tuple[str, str, str]]):
    """Return ({claim_id: relevant}, prompt tokens, completion tokens)."""
    last_error = None
    for attempt in range(1, 4):
        try:
            # Reasoning models (gpt-5.x, o-series) take no temperature; they get low reasoning effort.
            settings = {"reasoning_effort": "low"} if model.startswith(("gpt-5", "o")) else {"temperature": 0}
            response = client.chat.completions.create(
                model=model,
                **settings,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt(title, description, claims)},
                ],
            )
            numbers = {int(n) for n in json.loads(response.choices[0].message.content)["relevant"]}
            if not numbers <= set(range(1, len(claims) + 1)):
                raise ValueError(f"numbers out of range: {sorted(numbers)}")
            answers = {claim_id: n in numbers for n, (claim_id, _, _) in enumerate(claims, start=1)}
            return answers, response.usage.prompt_tokens, response.usage.completion_tokens
        except Exception as exc:  # network errors and malformed answers are retried alike
            last_error = exc
            time.sleep(1.5 * attempt)
    raise RuntimeError(f"OpenAI call failed after 3 attempts: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--codes-from", type=Path, help="a CSV with an onetsoc_code column: check only those")
    parser.add_argument("--model", default=MODEL, help=f"default: {MODEL}")
    args = parser.parse_args()

    load_dotenv(ENV_PATH)
    model = args.model
    answers = load_answers(model)

    con = duckdb.connect(str(CLAIMS_DB), read_only=True)
    con.execute(f"ATTACH '{ONET_DUCKDB_PATH}' AS onet (READ_ONLY)")
    rows = con.execute(
        """
        SELECT c.onetsoc_code, o.title, o.description, c.claim_id, r.claim_text, r.affected_entity_text
        FROM claim_candidates c
        JOIN research_claims r USING (claim_id)
        JOIN onet.occupation_data o USING (onetsoc_code)
        ORDER BY c.onetsoc_code, c.centered DESC
        """
    ).fetchall()
    con.close()
    occupations: dict[str, tuple[str, str, list]] = {}
    for code, title, description, claim_id, text, affected in rows:
        occupations.setdefault(code, (title, description, []))[2].append((claim_id, text, affected))

    codes = sorted(occupations)
    if args.codes_from:
        wanted = {row["onetsoc_code"] for row in csv.DictReader(args.codes_from.open(encoding="utf-8"))}
        codes = [code for code in codes if code in wanted]
    todo = {}
    for code in codes:
        title, description, claims = occupations[code]
        unchecked = [claim for claim in claims if (code, claim[0]) not in answers]
        if unchecked:
            todo[code] = (title, description, unchecked)
    print(f"model: {model}; occupations: {len(codes)}, with unchecked pairs: {len(todo)}, "
          f"pairs to check: {sum(len(item[2]) for item in todo.values())}")

    run_checks(model, todo, with_texts=False)

    if not args.codes_from:
        answers = load_answers(model)
        relevant_ids = {claim_id for (_, claim_id), relevant in answers.items() if relevant}
        not_standalone = check_claim_standalone.check_claims(relevant_ids)
        ai_links = check_claim_ai_link.check_claims(relevant_ids)
        # the text the app would show, where it differs from the extracted one, is checked again (10.7)
        corrections = load_corrections()
        shown_text = {}
        for code, (title, description, claims) in occupations.items():
            for claim_id, original, _ in claims:
                text = shown_claim_text(claim_id, original, ai_links, corrections)
                if text != original and corrections.get(claim_id, {}).get("show") != "no":
                    shown_text[(code, claim_id)] = text
        text_answers = load_text_answers(model)
        retodo = {}
        for code, (title, description, claims) in occupations.items():
            changed = [(claim_id, shown_text[(code, claim_id)], affected) for claim_id, _, affected in claims
                       if (code, claim_id) in shown_text and (code, claim_id, shown_text[(code, claim_id)]) not in text_answers]
            if changed:
                retodo[code] = (title, description, changed)
        print(f"claims shown in a changed text: {len({claim_id for _, claim_id in shown_text})}; "
              f"pairs to check again with that text: {sum(len(item[2]) for item in retodo.values())}")
        run_checks(model, retodo, with_texts=True)
        text_answers = load_text_answers(model)
        current = {pair: text_answers.get((*pair, shown_text[pair]), False) if pair in shown_text else relevant
                   for pair, relevant in answers.items()}
        write_shown(current, not_standalone, ai_links)
    return 0


def run_checks(model: str, todo: dict[str, tuple[str, str, list]], with_texts: bool) -> None:
    """Ask about each occupation's claims in `todo` and append the answers; `with_texts` keeps the text judged."""
    if not todo:
        return
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt_tokens = completion_tokens = 0
    CHECKS.parent.mkdir(parents=True, exist_ok=True)
    with CHECKS.open("a", encoding="utf-8") as out, ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(check, client, model, *item): code for code, item in todo.items()}
        for future in as_completed(futures):
            new_answers, prompt_used, completion_used = future.result()
            prompt_tokens += prompt_used
            completion_tokens += completion_used
            row = {"onetsoc_code": futures[future], "model": model, "prompt_version": PROMPT_VERSION, "answers": new_answers}
            if with_texts:
                row["texts"] = {claim_id: text for claim_id, text, _ in todo[futures[future]][2]}
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
    print(f"tokens: {prompt_tokens} prompt, {completion_tokens} completion")


def shown_claim_text(claim_id: str, original: str, ai_links: dict[str, dict], corrections: dict) -> str:
    """The text the app shows for a claim: a hand text, else the AI-link check's rewrite, else the extracted text."""
    if corrections.get(claim_id, {}).get("claim_text"):
        return corrections[claim_id]["claim_text"]
    link = ai_links.get(claim_id) or {}
    return link["rewrite"] if link.get("verdict") == "context" else original


def load_answers(model: str) -> dict[tuple[str, str], bool]:
    """{(occupation, claim_id): relevant}, judged on the extracted text, from earlier runs with this model and prompt."""
    answers = {}
    if CHECKS.exists():
        for line in CHECKS.open(encoding="utf-8"):
            row = json.loads(line)
            if row["model"] == model and row["prompt_version"] == PROMPT_VERSION and "texts" not in row:
                answers.update({(row["onetsoc_code"], claim_id): value for claim_id, value in row["answers"].items()})
    return answers


def load_text_answers(model: str) -> dict[tuple[str, str, str], bool]:
    """{(occupation, claim_id, text): relevant}, judged on a changed text (a hand text or a rewrite, 10.7)."""
    answers = {}
    if CHECKS.exists():
        for line in CHECKS.open(encoding="utf-8"):
            row = json.loads(line)
            if row["model"] == model and row["prompt_version"] == PROMPT_VERSION and "texts" in row:
                answers.update({(row["onetsoc_code"], claim_id, row["texts"][claim_id]): value
                                for claim_id, value in row["answers"].items()})
    return answers


def select_shown(candidates: list[tuple[str, str, float]], relevant: set[str]) -> list[str]:
    """Claim IDs to show for one occupation, from (claim_id, claim_text, centered) candidates."""
    shown, texts = [], set()
    for claim_id, text, centered in sorted(candidates, key=lambda item: -item[2]):
        if claim_id in relevant and centered >= 0 and text not in texts:
            shown.append(claim_id)
            texts.add(text)
    return shown[:SHOWN_PER_OCCUPATION]


def write_shown(answers: dict[tuple[str, str], bool], not_standalone: dict[str, str], ai_links: dict[str, dict]) -> None:
    """`not_standalone`: {claim_id: reason, or "" if the claim stands on its own} (check_claim_standalone.py);
    `ai_links`: {claim_id: {"verdict": direct/context/none, "rewrite": text for context}} (check_claim_ai_link.py)."""
    con = duckdb.connect(str(CLAIMS_DB), read_only=True)
    rows = con.execute(
        f"""
        SELECT c.onetsoc_code, c.claim_id, c.centered, {', '.join(f'r.{column}' for column in SHOWN_COLUMNS)}
        FROM claim_candidates c JOIN research_claims r USING (claim_id)
        """
    ).fetchall()
    con.close()
    by_code: dict[str, dict[str, tuple]] = {}
    for code, claim_id, centered, *fields in rows:
        by_code.setdefault(code, {})[claim_id] = (centered, fields)
    corrections = load_corrections()
    occupations = 0
    with SHOWN.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["onetsoc_code", "rank", "claim_id", *SHOWN_COLUMNS])
        for code in sorted(by_code):
            claims = by_code[code]
            relevant = {claim_id for claim_id in claims if answers.get((code, claim_id)) and shown_ok(
                claim_id, not_standalone, ai_links, corrections) and not hidden_for(claim_id, code, corrections)}
            candidates = [(claim_id, fields[0], centered) for claim_id, (centered, fields) in claims.items()]
            shown = select_shown(candidates, relevant)
            occupations += bool(shown)
            for rank, claim_id in enumerate(shown, start=1):
                fields = list(claims[claim_id][1])
                if ai_links[claim_id]["verdict"] == "context":  # about AI only through its source
                    fields[0] = ai_links[claim_id]["rewrite"]
                for column, value in corrections.get(claim_id, {}).items():  # corrected by hand, so it wins
                    if column in SHOWN_COLUMNS:
                        fields[SHOWN_COLUMNS.index(column)] = value
                writer.writerow([code, rank, claim_id, *fields])
    print(f"{SHOWN.relative_to(PROJECT_ROOT)}: {occupations} of {len(by_code)} occupations show at least one claim; "
          f"{len(corrections)} hand corrections; {sum(map(bool, not_standalone.values()))} relevant claims don't stand "
          f"on their own; {sum(link['verdict'] == 'none' for link in ai_links.values())} aren't about AI's effect on work")


def hidden_for(claim_id: str, code: str, corrections: dict) -> bool:
    """Whether a claim was hidden by hand for this career only (`hide_for`, 10.9), e.g. a pair the check got wrong."""
    return code in corrections.get(claim_id, {}).get("hide_for", "").split(";")


def shown_ok(claim_id: str, not_standalone: dict[str, str], ai_links: dict[str, dict], corrections: dict) -> bool:
    """Whether a claim the relevance check accepted may be shown: hidden by hand never; corrected by hand always;
    else only if it stands on its own and is about AI's effect on work."""
    correction = corrections.get(claim_id, {})
    if correction.get("show") == "no":
        return False
    if correction.get("claim_text"):
        return True
    return not not_standalone.get(claim_id) and ai_links[claim_id]["verdict"] != "none"


def load_corrections() -> dict[str, dict[str, str]]:
    """{claim_id: {column: corrected value}} from data/research/claim_corrections.csv (committed).

    Claims were extracted by an LLM and only some were checked by hand (4.2). When a shown claim is
    found to misstate its quote, the corrected text goes there with the reason; when the extracted
    quote is unreadable on its own (e.g. a bare number from a table), the corrected quote does; `show`
    is "no" for a claim reviewed and hidden (10.6); `hide_for` lists the O*NET codes (";"-separated) of
    careers it is hidden for, when only those pairs are wrong (10.9). Empty cells keep the extracted value. They are applied
    here, where the shown claims are written, so they reach the app and the Turkish translation (6.1c).
    """
    with CORRECTIONS.open(encoding="utf-8", newline="") as handle:
        return {
            row["claim_id"]: {column: row[column] for column in ("claim_text", "evidence_quote", "show", "hide_for") if row.get(column)}
            for row in csv.DictReader(handle)
        }


if __name__ == "__main__":
    raise SystemExit(main())

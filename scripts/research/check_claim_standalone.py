#!/usr/bin/env python3
"""Ask an LLM which claims don't stand on their own (ROADMAP 4.2).

The claim audit (notebook 42) found claim texts that a student can't understand without the paper:
unresolved references ("the sector", "these effects"), a model's own terms ("Both groups lose at αNE"),
or a finding about one group of workers that reads as true of every job. Showing the verbatim quote
doesn't help, because the quote lacks the context too. Whether a claim stands on its own doesn't depend
on the career, so each claim is checked once (not once per career and claim), and only claims the
relevance check (check_claim_relevance.py) judged relevant for some career, since only those can be shown.

Answers are appended to data/research/claim_standalone_checks.jsonl, keyed by claim ID, claim text, model
and prompt version, so a rerun after new claims are added (ROADMAP 8.2) only pays for the new ones.
check_claim_relevance.py leaves rejected claims out of what the app shows, unless a hand correction
(data/research/claim_corrections.csv) has fixed the text.

    python scripts/research/check_claim_standalone.py --audit   # only the audited claims, compared with the judgments
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from career_rag.config import ENV_PATH  # noqa: E402

CHECKS = PROJECT_ROOT / "data" / "research" / "claim_standalone_checks.jsonl"
CLAIMS = PROJECT_ROOT / "data" / "research" / "ai_impact_claims.jsonl"
AUDITS = sorted((PROJECT_ROOT / "evaluation").glob("claim_label_audit*.csv"))
MODEL = "gpt-5.4-mini"  # the relevance check's model (CHANGELOG 032)
PROMPT_VERSION = 2  # 1: also "says no more than its quote", answers by number only (CHANGELOG 061)
BATCH = 10
SYSTEM_PROMPT = (
    "You check claims extracted from research papers about AI and work. Each claim will be shown to a student "
    "on its own, without the paper. Decide for each claim whether it stands on its own: a reader who has not "
    "seen the paper understands what it says and whom or what it is about. It does not stand on its own if:\n"
    "- it refers to something it does not name: 'the firm', 'this effect', 'the program', 'those workers', "
    "'the difference', 'our data', 'in this case';\n"
    "- it uses a paper's own model terms, symbols or labels that a student would not know;\n"
    "- it reports a result from one study, group or setting (one experiment, one profession, one company) "
    "without saying so, so that it reads as true of all work or all workers;\n"
    "- the subject is missing: it does not say what technology, effect or measure it is about.\n"
    "Judge each claim separately; the quote is context only.\n"
    'Answer in JSON: {"results": [{"id": "<claim id>", "stands_alone": true or false, '
    '"reason": "<short reason if false, else empty>"}]}, one entry per claim, in the given order.'
)


def user_prompt(claims: list[dict]) -> str:
    return "\n".join(f"{claim['claim_id']}: {claim['claim_text']}\n   Quote: {claim['evidence_quote']}" for claim in claims)


def check(client: OpenAI, claims: list[dict]) -> tuple[dict[str, str], int, int]:
    """Return ({claim_id: reason or ""}, prompt tokens, completion tokens); "" means the claim stands on its own."""
    last_error = None
    for attempt in range(1, 4):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                reasoning_effort="medium",
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt(claims)}],
            )
            results = json.loads(response.choices[0].message.content)["results"]
            answers = {row["id"]: "" if row["stands_alone"] else (str(row["reason"]) or "does not stand on its own")
                       for row in results}
            if sorted(answers) != sorted(claim["claim_id"] for claim in claims):  # every claim, by ID (lesson 24)
                raise ValueError(f"answers for {sorted(answers)}")
            return answers, response.usage.prompt_tokens, response.usage.completion_tokens
        except Exception as exc:  # network errors and malformed answers are retried alike
            last_error = exc
            time.sleep(1.5 * attempt)
    raise RuntimeError(f"OpenAI call failed after 3 attempts: {last_error}")


def load_answers() -> dict[tuple[str, str], str]:
    """{(claim_id, claim_text): reason or ""} from earlier runs with this model and prompt."""
    answers = {}
    if CHECKS.exists():
        for line in CHECKS.open(encoding="utf-8"):
            row = json.loads(line)
            if row["model"] == MODEL and row["prompt_version"] == PROMPT_VERSION:
                answers[(row["claim_id"], row["claim_text"])] = row["reason"]
    return answers


def check_claims(claim_ids: set[str]) -> dict[str, str]:
    """Check the claims not checked before; return {claim_id: reason or ""} for all of `claim_ids`."""
    claims = [claim for line in CLAIMS.open(encoding="utf-8") if line.strip()
              for claim in [json.loads(line)] if claim["claim_id"] in claim_ids]
    answers = load_answers()
    todo = [claim for claim in claims if (claim["claim_id"], claim["claim_text"]) not in answers]
    print(f"standalone check ({MODEL}, prompt {PROMPT_VERSION}): {len(claims)} claims, {len(todo)} not checked before")
    if todo:
        load_dotenv(ENV_PATH)
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        texts = {claim["claim_id"]: claim["claim_text"] for claim in todo}
        prompt_tokens = completion_tokens = 0
        with CHECKS.open("a", encoding="utf-8") as out, ThreadPoolExecutor(max_workers=8) as pool:
            batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
            for future in as_completed([pool.submit(check, client, batch) for batch in batches]):
                new_answers, prompt_used, completion_used = future.result()
                prompt_tokens += prompt_used
                completion_tokens += completion_used
                for claim_id, reason in new_answers.items():  # each batch saved as it arrives (lesson 24)
                    out.write(json.dumps({"claim_id": claim_id, "claim_text": texts[claim_id], "model": MODEL,
                                          "prompt_version": PROMPT_VERSION, "reason": reason}, ensure_ascii=False) + "\n")
                    answers[(claim_id, texts[claim_id])] = reason
        print(f"tokens: {prompt_tokens} prompt, {completion_tokens} completion")
    return {claim["claim_id"]: answers[(claim["claim_id"], claim["claim_text"])] for claim in claims}


def audit() -> None:
    """Compare the check with the audited claim texts (claim_correct, notebook 42)."""
    rows = [row for path in AUDITS for row in csv.DictReader(path.open(encoding="utf-8", newline=""))]
    reasons = check_claims({row["claim_id"] for row in rows})
    pairs = [(row["claim_correct"] == "1", reasons[row["claim_id"]] == "") for row in rows]
    for truth in (True, False):
        for passed in (True, False):
            print(f"audit says {'right' if truth else 'wrong'}, check says {'pass' if passed else 'fail'}: "
                  f"{sum(pair == (truth, passed) for pair in pairs)}")
    for row in rows:
        if (row["claim_correct"] == "1") != (reasons[row["claim_id"]] == ""):
            print(f"\n{row['claim_id']} audit={row['claim_correct']} ({row['note']})\n  claim: {row['claim_text']}\n"
                  f"  check: {reasons[row['claim_id']] or 'pass'}")


if __name__ == "__main__":
    if "--audit" not in sys.argv[1:]:
        sys.exit(__doc__)
    audit()

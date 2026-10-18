#!/usr/bin/env python3
"""Ask an LLM whether each shown finding is supported by its own quote (ROADMAP 10.13).

The extraction checked that a quote appears in its source word for word (quote_validation), never that it
supports the claim. From tables this went wrong: in Table 2 of Hampole & Papanikolaou (2025), "AI applications
and most exposed tasks at JPMorgan Chase and Walmart", the row heading "Predictive Modeling & Financial
Forecasting" became the claim "AI is used for predictive modeling and financial forecasting" and the next
cell, an O*NET task ("Consult financial literature to ensure use of the latest models or statistical
techniques."), its quote.

Each finding the app could show is checked in the text it would be shown in (after the AI-link check's
rewrite, check_claim_ai_link.py), with its quote and source title:
- supported: the quote says what the finding says;
- rewrite: the quote supports a different or narrower statement; the model writes that statement, from the
  quote and title only, and it is what the app shows (after review, CHANGELOG 095);
- unsupported: the quote can't support a useful finding on its own. check_claim_relevance.py leaves it out.
Hand texts (claim_corrections.csv) were checked against their quotes by a person and are not sent.

Answers are appended to data/research/claim_quote_checks.jsonl, keyed by claim ID, the text checked, model and
prompt version, so a changed text is checked again and a rerun only pays for new ones.

It runs from check_claim_relevance.py, which also writes evaluation/claim_quote_review.csv for review.
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

CHECKS = PROJECT_ROOT / "data" / "research" / "claim_quote_checks.jsonl"
REVIEW = PROJECT_ROOT / "evaluation" / "claim_quote_review.csv"
MODEL = "gpt-5.4-mini"  # the other claim checks' model (CHANGELOG 032)
PROMPT_VERSION = 1
BATCH = 10
VERDICTS = ("supported", "rewrite", "unsupported")
SYSTEM_PROMPT = (
    "You check findings extracted from research papers and reports about AI and work. A student sees each "
    "finding with its quote as the evidence. Decide for each finding whether its quote supports it as written:\n"
    "- supported: the quote says what the finding says. The finding may paraphrase or shorten it, or name the "
    "study or source it comes from, but it makes no claim the quote doesn't make.\n"
    "- rewrite: the quote supports a different or narrower statement (for example the finding was taken from a "
    "table heading or a neighbouring sentence, or it generalizes beyond the quote). Write 'rewrite': one plain "
    "sentence that says only what the quote supports, keeping its specifics (occupation, task, number) and the "
    "AI or automation link if the quote or the source title shows it. Add nothing that is not in the quote or "
    "the source title.\n"
    "- unsupported: the quote can't support a useful finding on its own (a fragment, a label, a number without "
    "what it measures, or a sentence about something else).\n"
    "Judge each finding separately.\n"
    'Answer in JSON: {"results": [{"id": "<finding id>", "verdict": "supported" or "rewrite" or "unsupported", '
    '"rewrite": "<only for rewrite, else empty>", "reason": "<a few words>"}]}, one entry per finding, in order.'
)


def user_prompt(items: list[dict]) -> str:
    return "\n".join(
        f"{item['claim_id']}: {item['text']}\n   Quote: {item['quote']}\n   Source: {item['title']}"
        for item in items
    )


def check(client: OpenAI, items: list[dict]) -> tuple[dict[str, dict], int, int]:
    """Return ({claim_id: {"verdict", "rewrite", "reason"}}, prompt tokens, completion tokens)."""
    last_error = None
    for attempt in range(1, 4):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                reasoning_effort="low",
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt(items)}],
            )
            answers = {}
            for row in json.loads(response.choices[0].message.content)["results"]:
                verdict, rewrite = row["verdict"], str(row.get("rewrite") or "").strip()
                if verdict not in VERDICTS or (verdict == "rewrite") != bool(rewrite):
                    raise ValueError(f"{row['id']}: verdict {verdict!r} with rewrite {rewrite!r}")
                answers[row["id"]] = {"verdict": verdict, "rewrite": rewrite, "reason": str(row.get("reason") or "")}
            if sorted(answers) != sorted(item["claim_id"] for item in items):  # every finding, by ID (lesson 24)
                raise ValueError(f"answers for {sorted(answers)}")
            return answers, response.usage.prompt_tokens, response.usage.completion_tokens
        except Exception as exc:  # network errors and malformed answers are retried alike
            last_error = exc
            time.sleep(1.5 * attempt)
    raise RuntimeError(f"OpenAI call failed after 3 attempts: {last_error}")


def load_answers() -> dict[tuple[str, str], dict]:
    """{(claim_id, text checked): {"verdict", "rewrite", "reason"}} from earlier runs with this model and prompt."""
    answers = {}
    if CHECKS.exists():
        for line in CHECKS.open(encoding="utf-8"):
            row = json.loads(line)
            if row["model"] == MODEL and row["prompt_version"] == PROMPT_VERSION:
                answers[(row["claim_id"], row["text"])] = {key: row[key] for key in ("verdict", "rewrite", "reason")}
    return answers


def check_claims(items: list[dict]) -> dict[tuple[str, str], dict]:
    """Check the items (claim_id, text, quote, title) not checked before; return all answers so far."""
    answers = load_answers()
    todo = [item for item in items if (item["claim_id"], item["text"]) not in answers]
    print(f"quote check ({MODEL}, prompt {PROMPT_VERSION}): {len(items)} findings, {len(todo)} to check now")
    if todo:
        load_dotenv(ENV_PATH)
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        prompt_tokens = completion_tokens = 0
        with CHECKS.open("a", encoding="utf-8") as out, ThreadPoolExecutor(max_workers=8) as pool:
            batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
            futures = {pool.submit(check, client, batch): batch for batch in batches}
            for future in as_completed(futures):
                new_answers, prompt_used, completion_used = future.result()
                prompt_tokens += prompt_used
                completion_tokens += completion_used
                texts = {item["claim_id"]: item["text"] for item in futures[future]}
                for claim_id, answer in new_answers.items():  # each batch saved as it arrives (lesson 24)
                    out.write(json.dumps({"claim_id": claim_id, "text": texts[claim_id], "model": MODEL,
                                          "prompt_version": PROMPT_VERSION, **answer}, ensure_ascii=False) + "\n")
                    answers[(claim_id, texts[claim_id])] = answer
                out.flush()
        print(f"tokens: {prompt_tokens} prompt, {completion_tokens} completion")
    return answers


def review(items: list[dict]) -> None:
    """Every verdict and rewrite of these items, for a person to read before the rewrites are shown."""
    answers = load_answers()
    REVIEW.parent.mkdir(parents=True, exist_ok=True)
    with REVIEW.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["claim_id", "verdict", "text", "rewrite", "quote", "title", "reason"])
        rows = [(item, answers[(item["claim_id"], item["text"])]) for item in items if (item["claim_id"], item["text"]) in answers]
        for item, answer in sorted(rows, key=lambda row: (VERDICTS.index(row[1]["verdict"]), row[0]["claim_id"])):
            writer.writerow([item["claim_id"], answer["verdict"], item["text"], answer["rewrite"], item["quote"],
                             item["title"], answer["reason"]])
    counts = {verdict: sum(answer["verdict"] == verdict for _, answer in rows) for verdict in VERDICTS}
    print(f"wrote {REVIEW.relative_to(PROJECT_ROOT)}: {counts}")


if __name__ == "__main__":
    sys.exit(__doc__)

#!/usr/bin/env python3
"""Ask an LLM whether each claim says something about AI's effect on work (ROADMAP 10.6).

The app shows research findings under "What research says" about AI and a career, but the relevance check
(check_claim_relevance.py) only asks whether a claim is about the career, not whether it is about AI. Some
shown claims weren't ("Effective reforms require a proactive approach to update curricula…"), and some were
about AI only in their source: "Cognitive skills like Reading Comprehension… show high presence" means "in
Claude conversations", which the sentence no longer says. The extraction's own `ai_relevance` label didn't
separate these: it called 252 of the 658 relevant claims indirect, including AI findings.

Each claim (with its quote and source title) gets one of three verdicts:
- direct: as written, it is about how AI or automation affects work;
- context: it is about AI only through its source; the model rewrites it to state the link, from the claim,
  quote and title only, and the rewrite is what the app shows (after review, CHANGELOG 087);
- none: not about AI's effect on work. check_claim_relevance.py leaves it out of what the app shows.

Whether a claim is about AI doesn't depend on the career, so each claim is checked once. Answers are appended
to data/research/claim_ai_link_checks.jsonl, keyed by claim ID, claim text, model and prompt version, so a
rerun after new claims are added (ROADMAP 8.2) only pays for the new ones.

    python scripts/research/check_claim_ai_link.py --pilot 10   # one batch, to measure tokens
    python scripts/research/check_claim_ai_link.py --review     # writes evaluation/claim_ai_link_review.csv
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

CHECKS = PROJECT_ROOT / "data" / "research" / "claim_ai_link_checks.jsonl"
CLAIMS = PROJECT_ROOT / "data" / "research" / "ai_impact_claims.jsonl"
REVIEW = PROJECT_ROOT / "evaluation" / "claim_ai_link_review.csv"
MODEL = "gpt-5.4-mini"  # the relevance and standalone checks' model (CHANGELOG 032)
PROMPT_VERSION = 2  # 1 called a finding "direct" when only its source title named AI, and rewrote vaguely ("AI is associated with…")
BATCH = 10
VERDICTS = ("direct", "context", "none")
SYSTEM_PROMPT = (
    "You check findings extracted from research papers and reports. A student sees each finding, with its "
    "quote, under the heading 'What research says about AI and this job'. Decide for each finding:\n"
    "- direct: the finding's own sentence names AI, generative AI, language models, chatbots, automation, robots "
    "or an AI tool, and says how it affects work: jobs, tasks, skills, wages, hiring, productivity or workers. "
    "A sentence that only implies AI through its source title is not direct.\n"
    "- context: the finding's sentence does not name AI or automation, but its quote or source shows that it is "
    "a result about AI's effect on work (for example a result from a study of AI exposure or of AI use). Then "
    "write 'rewrite': the same finding in one plain sentence that names the AI link and keeps the specifics of "
    "the quote (the occupation, task, skill, measure or number). Use only what the finding, its quote and the "
    "source title say; add no number, group or fact that is not in them, and no vague link such as 'is "
    "associated with' when the source says more.\n"
    "- none: it is not about AI's or automation's effect on work (for example general labor-market, education "
    "policy or sector statistics), even if the source is about AI.\n"
    "Judge each finding separately.\n"
    'Answer in JSON: {"results": [{"id": "<finding id>", "verdict": "direct" or "context" or "none", '
    '"rewrite": "<only for context, else empty>", "reason": "<a few words>"}]}, one entry per finding, in order.'
)


def user_prompt(claims: list[dict]) -> str:
    return "\n".join(
        f"{claim['claim_id']}: {claim['claim_text']}\n   Quote: {claim['evidence_quote']}\n"
        f"   Source: {claim['title']} ({claim['year']})"
        for claim in claims
    )


def check(client: OpenAI, claims: list[dict]) -> tuple[dict[str, dict], int, int]:
    """Return ({claim_id: {"verdict", "rewrite", "reason"}}, prompt tokens, completion tokens)."""
    last_error = None
    for attempt in range(1, 4):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                reasoning_effort="low",
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt(claims)}],
            )
            answers = {}
            for row in json.loads(response.choices[0].message.content)["results"]:
                verdict, rewrite = row["verdict"], str(row.get("rewrite") or "").strip()
                if verdict not in VERDICTS or (verdict == "context") != bool(rewrite):
                    raise ValueError(f"{row['id']}: verdict {verdict!r} with rewrite {rewrite!r}")
                answers[row["id"]] = {"verdict": verdict, "rewrite": rewrite, "reason": str(row.get("reason") or "")}
            if sorted(answers) != sorted(claim["claim_id"] for claim in claims):  # every claim, by ID (lesson 24)
                raise ValueError(f"answers for {sorted(answers)}")
            return answers, response.usage.prompt_tokens, response.usage.completion_tokens
        except Exception as exc:  # network errors and malformed answers are retried alike
            last_error = exc
            time.sleep(1.5 * attempt)
    raise RuntimeError(f"OpenAI call failed after 3 attempts: {last_error}")


def load_answers() -> dict[tuple[str, str], dict]:
    """{(claim_id, claim_text): {"verdict", "rewrite", "reason"}} from earlier runs with this model and prompt."""
    answers = {}
    if CHECKS.exists():
        for line in CHECKS.open(encoding="utf-8"):
            row = json.loads(line)
            if row["model"] == MODEL and row["prompt_version"] == PROMPT_VERSION:
                answers[(row["claim_id"], row["claim_text"])] = {key: row[key] for key in ("verdict", "rewrite", "reason")}
    return answers


def check_claims(claim_ids: set[str], limit: int | None = None) -> dict[str, dict]:
    """Check the claims not checked before (at most `limit` of them); return the answers for all of `claim_ids`."""
    claims = [claim for line in CLAIMS.open(encoding="utf-8") if line.strip()
              for claim in [json.loads(line)] if claim["claim_id"] in claim_ids]
    answers = load_answers()
    todo = sorted((claim for claim in claims if (claim["claim_id"], claim["claim_text"]) not in answers),
                  key=lambda claim: claim["claim_id"])[:limit]
    print(f"AI-link check ({MODEL}, prompt {PROMPT_VERSION}): {len(claims)} claims, {len(todo)} to check now")
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
                for claim_id, answer in new_answers.items():  # each batch saved as it arrives (lesson 24)
                    out.write(json.dumps({"claim_id": claim_id, "claim_text": texts[claim_id], "model": MODEL,
                                          "prompt_version": PROMPT_VERSION, **answer}, ensure_ascii=False) + "\n")
                    answers[(claim_id, texts[claim_id])] = answer
                out.flush()
        print(f"tokens: {prompt_tokens} prompt, {completion_tokens} completion")
    return {claim["claim_id"]: answers[(claim["claim_id"], claim["claim_text"])] for claim in claims
            if (claim["claim_id"], claim["claim_text"]) in answers}


def relevant_claim_ids() -> set[str]:
    """The claims the relevance check judged relevant for at least one career: only those can be shown."""
    import check_claim_relevance

    return {claim_id for (_, claim_id), relevant in check_claim_relevance.load_answers(check_claim_relevance.MODEL).items()
            if relevant}


def review() -> None:
    """Every verdict and rewrite, for a person to read before the rewrites are shown."""
    claims = {claim["claim_id"]: claim for line in CLAIMS.open(encoding="utf-8") if line.strip()
              for claim in [json.loads(line)]}
    answers = check_claims(relevant_claim_ids(), limit=0)
    REVIEW.parent.mkdir(parents=True, exist_ok=True)
    with REVIEW.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["claim_id", "verdict", "claim_text", "rewrite", "evidence_quote", "title", "reason"])
        for claim_id, answer in sorted(answers.items(), key=lambda item: (VERDICTS.index(item[1]["verdict"]), item[0])):
            claim = claims[claim_id]
            writer.writerow([claim_id, answer["verdict"], claim["claim_text"], answer["rewrite"], claim["evidence_quote"],
                             f"{claim['title']} ({claim['year']})", answer["reason"]])
    counts = {verdict: sum(answer["verdict"] == verdict for answer in answers.values()) for verdict in VERDICTS}
    print(f"wrote {REVIEW.relative_to(PROJECT_ROOT)}: {counts}")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    if "--pilot" in sys.argv:
        check_claims(relevant_claim_ids(), limit=int(sys.argv[sys.argv.index("--pilot") + 1]))
    elif "--review" in sys.argv:
        review()
    else:
        sys.exit(__doc__)

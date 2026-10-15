#!/usr/bin/env python3
"""Translate the career content students see into Turkish, once, at build time (ROADMAP 6.1, D8 = B).

What is translated: each career's title, description and its 6 most important tasks (the ones the
report shows, 6.1a); the skill, knowledge, ability and work-context names; the research claims the
app shows (4.1c). O*NET content is CC BY 4.0, so the Turkish text is marked as an adaptation.

Answers are cached in data/i18n/translation_cache.jsonl by (English text, model, prompt version),
so a rerun only pays for strings it hasn't translated with that model and prompt.

    python scripts/i18n/translate_content.py --pilot 40 --models gpt-4o-mini,gpt-5.4-mini
        writes evaluation/translation_pilot.csv for a blind comparison (6.1b)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import duckdb
from dotenv import load_dotenv
from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from career_rag.config import ENV_PATH, ONET_DUCKDB_PATH, RESEARCH_CLAIMS_PATH  # noqa: E402
from career_rag.ip_ai_impact import TASKS_BY_IMPORTANCE_SQL  # noqa: E402

CACHE = PROJECT_ROOT / "data" / "i18n" / "translation_cache.jsonl"
PILOT = PROJECT_ROOT / "evaluation" / "translation_pilot.csv"
PILOT_KEY = PROJECT_ROOT / "evaluation" / "translation_pilot_key.csv"
BATCH = 20
PROMPT_VERSION = 2  # 1 (pilot, 2026-10-15) wrote tasks as orders, plural titles and kept "AI" in English
SYSTEM_PROMPT = (
    "You translate career information from O*NET, the US occupational database, into Turkish for "
    "Turkish university students. Write natural, clear Turkish as used in Turkey, and keep the meaning "
    "exact: add and drop nothing. Each input is labelled with its kind:\n"
    "- title: an occupation title, singular, as a job title in Turkey (\"Accountants\" -> \"Muhasebeci\"), "
    "only the first letter capitalized unless a word is a proper name.\n"
    "- description, task: say what a person in this job does, in the third-person present tense "
    "(\"Explain procedures to patients.\" -> \"Hastalara işlemleri açıklar.\"), never as an instruction.\n"
    "- element name: a short label for a skill, knowledge area, ability or work condition, as a noun "
    "phrase (\"Spend Time Sitting\" -> \"Oturarak geçen süre\"), only the first letter capitalized.\n"
    "- research claim: a finding from a study, in a neutral report style.\n"
    "Translate \"AI\" as \"yapay zekâ\". Use the established Turkish term for an occupation, skill or field "
    "where one exists. Keep product and software names, abbreviations such as O*NET, and numbers as they are. "
    'Answer in JSON: {"translations": [one Turkish string per input, in the same order]}.'
)
# How many of each kind the pilot draws, so every kind is judged.
PILOT_MIX = {"title": 6, "description": 8, "task": 14, "element name": 6, "research claim": 6}


def collect() -> dict[str, list[str]]:
    """{kind: distinct English strings} the report shows."""
    con = duckdb.connect(str(ONET_DUCKDB_PATH), read_only=True)
    careers = con.execute(
        "SELECT onetsoc_code, title, description FROM occupation_data "
        "WHERE onetsoc_code IN (SELECT DISTINCT onetsoc_code FROM task_statements) ORDER BY onetsoc_code"
    ).fetchall()
    tasks = {task for code, _, _ in careers for _, task, _ in con.execute(TASKS_BY_IMPORTANCE_SQL, [code, 6]).fetchall()}
    elements = con.execute(
        """
        SELECT DISTINCT r.element_name FROM content_model_reference AS r
        WHERE r.element_id IN (SELECT element_id FROM essential_skills UNION SELECT element_id FROM knowledge
                               UNION SELECT element_id FROM abilities UNION SELECT element_id FROM work_context)
        UNION SELECT DISTINCT category_description FROM work_context_categories
        """
    ).fetchall()
    con.close()
    with RESEARCH_CLAIMS_PATH.open(encoding="utf-8", newline="") as handle:
        claims = {row["claim_text"] for row in csv.DictReader(handle)}
    return {
        "title": sorted({title for _, title, _ in careers}),
        "description": sorted({description for _, _, description in careers}),
        "task": sorted(tasks),
        "element name": sorted({name for (name,) in elements if name}),
        "research claim": sorted(claims),
    }


def load_cache() -> dict[tuple[str, str, int], str]:
    cache = {}
    if CACHE.exists():
        for line in CACHE.open(encoding="utf-8"):
            row = json.loads(line)
            cache[(row["english"], row["model"], row["prompt_version"])] = row["turkish"]
    return cache


def translate_batch(client: OpenAI, model: str, items: list[tuple[str, str]]) -> tuple[list[str], int, int]:
    """Translate [(kind, English)] in one call; returns (Turkish strings, prompt tokens, completion tokens)."""
    numbered = "\n".join(f"{n}. [{kind}] {text}" for n, (kind, text) in enumerate(items, start=1))
    settings = {"reasoning_effort": "low"} if model.startswith(("gpt-5", "o")) else {"temperature": 0}
    last_error = None
    for attempt in range(1, 4):
        try:
            response = client.chat.completions.create(
                model=model,
                **settings,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": numbered}],
            )
            translations = json.loads(response.choices[0].message.content)["translations"]
            if len(translations) != len(items) or not all(isinstance(t, str) and t.strip() for t in translations):
                raise ValueError(f"expected {len(items)} translations, got {len(translations)}")
            return [t.strip() for t in translations], response.usage.prompt_tokens, response.usage.completion_tokens
        except Exception as exc:  # network errors and malformed answers are retried alike
            last_error = exc
            time.sleep(1.5 * attempt)
    raise RuntimeError(f"OpenAI call failed after 3 attempts: {last_error}")


def translate(model: str, items: list[tuple[str, str]], cache: dict) -> dict[str, str]:
    """{English: Turkish} for these (kind, English) items, calling the API only for uncached ones."""
    todo = [(kind, text) for kind, text in items if (text, model, PROMPT_VERSION) not in cache]
    if todo:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
        prompt_tokens = completion_tokens = 0
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        with CACHE.open("a", encoding="utf-8") as out, ThreadPoolExecutor(max_workers=8) as pool:
            for batch, (turkish, used_in, used_out) in zip(batches, pool.map(lambda b: translate_batch(client, model, b), batches)):
                prompt_tokens += used_in
                completion_tokens += used_out
                for (_, english), text in zip(batch, turkish):
                    cache[(english, model, PROMPT_VERSION)] = text
                    out.write(json.dumps({"english": english, "model": model, "prompt_version": PROMPT_VERSION,
                                          "turkish": text}, ensure_ascii=False) + "\n")
        print(f"{model}: {len(todo)} strings, tokens {prompt_tokens} prompt, {completion_tokens} completion")
    return {text: cache[(text, model, PROMPT_VERSION)] for _, text in items}


def pilot(size: int, models: list[str]) -> None:
    """A blind side-by-side of two models on the same random strings, for you to judge."""
    if PILOT.exists():
        sys.exit(f"{PILOT.relative_to(PROJECT_ROOT)} exists; delete or rename it to draw a new pilot.")
    strings = collect()
    rng = random.Random(2026)
    scale = size / sum(PILOT_MIX.values())
    items = [(kind, text) for kind, n in PILOT_MIX.items() for text in rng.sample(strings[kind], round(n * scale))]
    cache = load_cache()
    results = {model: translate(model, items, cache) for model in models}
    with PILOT.open("w", encoding="utf-8", newline="") as out, PILOT_KEY.open("w", encoding="utf-8", newline="") as key:
        writer = csv.writer(out)
        writer.writerow(["n", "kind", "english", "translation_1", "translation_2",
                         "better (1, 2 or same)", "1 acceptable (1/0)", "2 acceptable (1/0)", "note"])
        key_writer = csv.writer(key)
        key_writer.writerow(["n", "translation_1", "translation_2"])
        for n, (kind, text) in enumerate(rng.sample(items, len(items)), start=1):
            order = rng.sample(models, 2)  # which model is 1 and 2 is random per row, so you judge blind
            writer.writerow([n, kind, text, results[order[0]][text], results[order[1]][text], "", "", "", ""])
            key_writer.writerow([n, *order])
    print(f"wrote {PILOT.relative_to(PROJECT_ROOT)} ({len(items)} rows) and the model key {PILOT_KEY.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pilot", type=int, help="draw this many strings for a blind comparison of --models")
    parser.add_argument("--models", default="gpt-4o-mini,gpt-5.4-mini")
    args = parser.parse_args()
    load_dotenv(ENV_PATH)
    if args.pilot:
        pilot(args.pilot, args.models.split(","))
    else:
        counts = {kind: len(texts) for kind, texts in collect().items()}
        print(f"strings to translate: {counts}; the full run comes in ROADMAP 6.1c")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

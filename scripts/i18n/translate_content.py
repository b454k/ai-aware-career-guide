#!/usr/bin/env python3
"""Translate the career content students see into Turkish, once, at build time (ROADMAP 6.1, D8 = B).

What is translated: each career's title, description and its 6 most important tasks (the ones the
report shows, 6.1a); the skill, knowledge, ability, work-context and education-level names; the Job
Zone texts; the research claims the app shows (4.1c). O*NET content is CC BY 4.0, so the Turkish
text is marked as an adaptation in the app.

Answers are cached in data/i18n/translation_cache.jsonl by (English text, model, prompt version),
so a rerun only pays for strings it hasn't translated with that model and prompt.

    python scripts/i18n/translate_content.py --pilot 40 --models gpt-4o-mini,gpt-5.4-mini
        writes evaluation/translation_pilot.csv for a blind comparison (6.1b)
    python scripts/i18n/translate_content.py --model gpt-5.4-mini
        translates everything not yet cached and writes data/i18n/content_tr.csv, the table the app
        reads (committed, 6.1c); with everything cached it rebuilds the table without API calls
    python scripts/i18n/translate_content.py --spotcheck 30
        writes evaluation/translation_spotcheck.csv, random rows of the table for you to judge
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import duckdb
from dotenv import load_dotenv
from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from career_rag.config import ENV_PATH, ILO_EXPOSURE_PATH, ONET_DUCKDB_PATH, RESEARCH_CLAIMS_PATH  # noqa: E402
from career_rag.ip_ai_impact import TASKS_BY_IMPORTANCE_SQL  # noqa: E402

CACHE = PROJECT_ROOT / "data" / "i18n" / "translation_cache.jsonl"
PILOT = PROJECT_ROOT / "evaluation" / "translation_pilot.csv"
PILOT_KEY = PROJECT_ROOT / "evaluation" / "translation_pilot_key.csv"
TABLE = PROJECT_ROOT / "data" / "i18n" / "content_tr.csv"  # committed; read by the app (6.1c)
SPOTCHECK = PROJECT_ROOT / "evaluation" / "translation_spotcheck.csv"
CORRECTIONS = PROJECT_ROOT / "data" / "i18n" / "content_tr_corrections.csv"  # committed; checked by hand
BATCH = 20
# 1 (pilot, 2026-10-15) wrote tasks as orders, plural titles and kept "AI" in English; 2 fixed that
# (the blind pilot); 3 added the Job Zone kind; 4 follows your pilot judgments on titles (plural, each
# main word capitalized: preferred in 5 of 6) and answers keyed by input number, because a model that
# translated one title twice shifted every later answer by one (CHANGELOG 046).
PROMPT_VERSION = 4
SYSTEM_PROMPT = (
    "You translate career information from O*NET, the US occupational database, into Turkish for "
    "Turkish university students. Write natural, clear Turkish as used in Turkey, and keep the meaning "
    "exact: add and drop nothing. Each input is labelled with its kind:\n"
    "- title: an occupation title as in a list of careers, plural, each main word capitalized "
    "(\"Accountants\" -> \"Muhasebeciler\").\n"
    "- description, task: say what a person in this job does, in the third-person present tense "
    "(\"Explain procedures to patients.\" -> \"Hastalara işlemleri açıklar.\"), never as an instruction.\n"
    "- element name: a short label for a skill, knowledge area, ability or work condition, as a noun "
    "phrase (\"Spend Time Sitting\" -> \"Oturarak geçen süre\"), only the first letter capitalized.\n"
    "- research claim: a finding from a study, in a neutral report style.\n"
    "- job zone: O*NET's text on how much preparation a group of jobs needs, in a neutral style; keep its "
    "hedges such as \"usually\", \"most\" and \"some do not\" (\"Job Zone\" -> \"İş Bölgesi\").\n"
    "Translate \"AI\" as \"yapay zekâ\". Use the established Turkish term for an occupation, skill or field "
    "where one exists. Keep product and software names, abbreviations such as O*NET, and numbers as they are. "
    'Answer in JSON with exactly one Turkish string per input, keyed by its number: '
    '{"translations": {"1": "...", "2": "..."}}.'
)
# How many of each kind the pilot draws, so every kind is judged.
PILOT_MIX = {"title": 6, "description": 8, "task": 14, "element name": 6, "research claim": 6}

# The checking pass (CHANGELOG 050): a second model fixes clear errors only. Your pilot preferred
# gpt-4o-mini's style, so the checker must not rewrite correct translations to its own taste.
CHECK_CACHE = PROJECT_ROOT / "data" / "i18n" / "check_cache.jsonl"
CHECK_FIXES = PROJECT_ROOT / "evaluation" / "translation_check_fixes.csv"  # every fix, for your review
CHECK_VERSION = 1
CHECK_PROMPT = (
    "You review English-to-Turkish translations of career information for Turkish university students "
    "(O*NET occupation data and research findings). Each numbered item has its kind, the English source "
    "and the Turkish translation. Fix only clear errors:\n"
    "- the meaning changed, or something was added or dropped;\n"
    "- a wrong word or term (a field translated as people, a literal translation of a technical term, "
    "a false friend);\n"
    "- broken or ungrammatical Turkish;\n"
    "- a product, brand or company name translated;\n"
    "- a task or description written as an instruction instead of in the third-person present tense.\n"
    "Do not change a correct translation for style or word preference. Keep these conventions: occupation "
    "titles are plural with each main word capitalized; \"AI\" is \"yapay zekâ\"; \"Job Zone\" is \"İş Bölgesi\". "
    'Answer in JSON keyed by item number: {"checks": {"1": "OK", "2": {"fix": "the corrected Turkish", '
    '"why": "a few words"}}}, with "OK" when the translation has no clear error.'
)


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
        UNION SELECT DISTINCT category_description FROM education_categories
        """
    ).fetchall()
    # The software examples a report shows (ip_final_report._fetch_software: 16 per career, in-demand first).
    # Only generic categories are translated ("Accounts payable software"): gpt-4o-mini translated parts of
    # 1,428 product and company names despite the prompt ("BidMaster" -> "Teklif Master", CHANGELOG 049),
    # so any name with a capital letter after its first word stays as it is, untranslated.
    software = con.execute(
        """
        SELECT workplace_example FROM (
            SELECT workplace_example, row_number() OVER (
                PARTITION BY onetsoc_code
                ORDER BY CASE WHEN UPPER(COALESCE(in_demand, '')) = 'Y' THEN 0 ELSE 1 END, workplace_example
            ) AS n
            FROM (SELECT DISTINCT onetsoc_code, workplace_example, in_demand FROM software_skills
                  WHERE workplace_example IS NOT NULL)
        ) WHERE n <= 16
        """
    ).fetchall()
    job_zones = con.execute("SELECT name, experience, education, job_training FROM job_zone_reference").fetchall()
    con.close()
    with RESEARCH_CLAIMS_PATH.open(encoding="utf-8", newline="") as handle:
        claims = {row["claim_text"] for row in csv.DictReader(handle)}
    with ILO_EXPOSURE_PATH.open(encoding="utf-8", newline="") as handle:  # ISCO-08 group names in the ILO panel
        isco_titles = {row["isco08_title"] for row in csv.DictReader(handle)}
    kinds = {
        "title": {title for _, title, _ in careers} | isco_titles,
        "description": {description for _, _, description in careers},
        "task": tasks,
        "element name": {name for (name,) in elements} | {name for (name,) in software if is_generic(name)},
        "job zone": {text for row in job_zones for text in row},
        "research claim": claims,
    }
    # Whitespace as the app shows it (one space), which is also how career_rag.ui_i18n.content_text looks it up.
    return {kind: sorted({normalize(text) for text in texts if text and normalize(text)}) for kind, texts in kinds.items()}


def is_generic(name: str) -> bool:
    """A software category rather than a product: several words, none after the first capitalized."""
    words = name.split()
    return len(words) > 1 and not any(word[:1].isupper() for word in words[1:])


def normalize(text: str) -> str:
    return " ".join(str(text).split())


def load_cache() -> dict[tuple[str, str, int], str]:
    cache = {}
    if CACHE.exists():
        with CACHE.open(encoding="utf-8") as lines:
            for line in lines:
                row = json.loads(line)
                cache[(row["english"], row["model"], row["prompt_version"])] = row["turkish"]
    return cache


def ask_json(client: OpenAI, model: str, system: str, user: str, key: str, count: int, valid) -> tuple[dict, int, int]:
    """One JSON call whose answers are keyed by item number 1..count; retried 3 times.

    Returns ({"1": answer, ...}, prompt tokens, completion tokens). `valid(answer)` checks each answer.
    """
    settings = {"reasoning_effort": "low"} if model.startswith(("gpt-5", "o")) else {"temperature": 0}
    last_error = None
    for attempt in range(1, 4):
        try:
            response = client.chat.completions.create(
                model=model,
                **settings,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            )
            answers = json.loads(response.choices[0].message.content)[key]
            numbers = [str(n) for n in range(1, count + 1)]
            if sorted(answers, key=int) != numbers or not all(valid(answers[n]) for n in numbers):
                raise ValueError(f"expected answers 1-{count}, got keys {sorted(answers)[:5]}...")
            return answers, response.usage.prompt_tokens, response.usage.completion_tokens
        except Exception as exc:  # network errors and malformed answers are retried alike
            last_error = exc
            time.sleep(1.5 * attempt)
    raise RuntimeError(f"OpenAI call failed after 3 attempts: {last_error}")


def translate_batch(client: OpenAI, model: str, items: list[tuple[str, str]]) -> tuple[list[str], int, int]:
    """Translate [(kind, English)] in one call; returns (Turkish strings, prompt tokens, completion tokens)."""
    numbered = "\n".join(f"{n}. [{kind}] {text}" for n, (kind, text) in enumerate(items, start=1))
    answers, used_in, used_out = ask_json(
        client, model, SYSTEM_PROMPT, numbered, "translations", len(items), lambda a: isinstance(a, str) and a.strip()
    )
    return [answers[str(n)].strip() for n in range(1, len(items) + 1)], used_in, used_out


def check_batch(client: OpenAI, model: str, items: list[tuple[str, str, str]]) -> tuple[list[dict], int, int]:
    """Check [(kind, English, Turkish)] in one call; returns ({"fix": Turkish or None, "why": reason}, ...)."""
    numbered = "\n\n".join(
        f"{n}. [{kind}]\nEnglish: {english}\nTurkish: {turkish}" for n, (kind, english, turkish) in enumerate(items, start=1)
    )

    def valid(answer) -> bool:
        return answer == "OK" or (isinstance(answer, dict) and str(answer.get("fix") or "").strip() != "")

    answers, used_in, used_out = ask_json(client, model, CHECK_PROMPT, numbered, "checks", len(items), valid)
    results = []
    for n in range(1, len(items) + 1):
        answer = answers[str(n)]
        results.append({"fix": None, "why": ""} if answer == "OK" else {"fix": answer["fix"].strip(), "why": str(answer.get("why") or "")})
    return results, used_in, used_out


def run_batches(todo: list, call, record, label: str) -> None:
    """Send `todo` in batches of BATCH through call(batch) -> (results, prompt tokens, completion tokens).

    Each batch's results go to record(batch, results) as soon as they arrive, under a lock (batches finish in
    worker threads), so an interrupted run keeps what it paid for. A batch that keeps failing is split in
    half and retried; a single item that still fails is reported and stops the run at the end (CHANGELOG 046).
    """
    tokens = [0, 0]
    failed: list = []
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=8) as pool:

        def run(batch: list) -> None:
            try:
                results, used_in, used_out = call(batch)
            except RuntimeError:
                if len(batch) == 1:
                    failed.extend(batch)
                    return
                run(batch[: len(batch) // 2])
                run(batch[len(batch) // 2:])
                return
            with lock:
                tokens[0] += used_in
                tokens[1] += used_out
                record(batch, results)

        for future in as_completed([pool.submit(run, todo[i:i + BATCH]) for i in range(0, len(todo), BATCH)]):
            future.result()
    print(f"{label}: {len(todo)} items, tokens {tokens[0]} prompt, {tokens[1]} completion; failed: {len(failed)}")
    if failed:
        sys.exit(f"failed: {[item[1] for item in failed][:5]}")


def translate(model: str, items: list[tuple[str, str]], cache: dict) -> dict[str, str]:
    """{English: Turkish} for these (kind, English) items, calling the API only for uncached ones."""
    # One request per text, even when it appears under two kinds (e.g. a skill and a knowledge area).
    todo = list({text: (kind, text) for kind, text in items if (text, model, PROMPT_VERSION) not in cache}.values())
    if todo:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        with CACHE.open("a", encoding="utf-8") as out:

            def record(batch, turkish):
                for (_, english), text in zip(batch, turkish):
                    cache[(english, model, PROMPT_VERSION)] = text
                    out.write(json.dumps({"english": english, "model": model, "prompt_version": PROMPT_VERSION,
                                          "turkish": text}, ensure_ascii=False) + "\n")
                out.flush()

            run_batches(todo, lambda batch: translate_batch(client, model, batch), record, f"translate with {model}")
    return {text: cache[(text, model, PROMPT_VERSION)] for _, text in items}


def load_checks() -> dict[tuple[str, str, str, int], dict]:
    checks = {}
    if CHECK_CACHE.exists():
        with CHECK_CACHE.open(encoding="utf-8") as lines:
            for line in lines:
                row = json.loads(line)
                checks[(row["english"], row["turkish"], row["model"], row["check_version"])] = {"fix": row["fix"], "why": row["why"]}
    return checks


def check(model: str, items: list[tuple[str, str, str]]) -> dict[tuple[str, str], dict]:
    """{(English, Turkish): {"fix", "why"}} from `model`, checking only pairs it hasn't checked before.

    A pair is checked again when its Turkish changes, so new translations (ROADMAP 8.2) get checked
    and nothing already checked is paid for twice.
    """
    checks = load_checks()
    todo = list({(e, t): (k, e, t) for k, e, t in items if (e, t, model, CHECK_VERSION) not in checks}.values())
    if todo:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        with CHECK_CACHE.open("a", encoding="utf-8") as out:

            def record(batch, results):
                for (_, english, turkish), result in zip(batch, results):
                    checks[(english, turkish, model, CHECK_VERSION)] = result
                    out.write(json.dumps({"english": english, "turkish": turkish, "model": model,
                                          "check_version": CHECK_VERSION, **result}, ensure_ascii=False) + "\n")
                out.flush()

            run_batches(todo, lambda batch: check_batch(client, model, batch), record, f"check with {model}")
    return {(e, t): checks[(e, t, model, CHECK_VERSION)] for _, e, t in items}


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


def full_run(model: str, checker: str | None = None, checker_kinds: set[str] | None = None) -> None:
    """Translate every collected string with `model`, optionally check some with `checker`, and write the table.

    Which text wins: a hand correction, else a checker's fix, else the model's translation. `checker` sends
    the translations of `checker_kinds` (all kinds if None) not checked before to the checker; fixes already
    in the check cache are applied on every run, so a rebuild without --checker keeps them. The table's
    `source` column says which text won; every checker fix is listed in evaluation/translation_check_fixes.csv.
    """
    items = [(kind, text) for kind, texts in collect().items() for text in texts]
    kinds = {text: kind for kind, text in reversed(items)}  # the first kind a text appears under
    turkish = translate(model, items, load_cache())
    source = dict.fromkeys(turkish, model)
    with CORRECTIONS.open(encoding="utf-8", newline="") as handle:
        corrections = {row["english"]: row["turkish"] for row in csv.DictReader(handle)}
    unused = corrections.keys() - kinds.keys()
    if unused:
        sys.exit(f"corrections for text the app no longer shows: {sorted(unused)[:3]}")
    if checker:
        check(checker, [(kinds[e], e, turkish[e]) for e in kinds
                        if e not in corrections and (checker_kinds is None or kinds[e] in checker_kinds)])
    fixes = []
    for (english, before, checked_by, version), result in load_checks().items():
        if (version == CHECK_VERSION and english in kinds and english not in corrections
                and turkish[english] == before and result["fix"] and result["fix"] != before):
            fixes.append((kinds[english], english, before, result["fix"], result["why"]))
            turkish[english], source[english] = result["fix"], f"{model}, fixed by {checked_by}"
    with CHECK_FIXES.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["kind", "english", "before", "after", "why"])
        writer.writerows(sorted(fixes))
    for english, text in corrections.items():  # checked by hand, so they win
        turkish[english], source[english] = text, "hand"
    TABLE.parent.mkdir(parents=True, exist_ok=True)
    with TABLE.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["kind", "english", "turkish", "source"])
        writer.writerows((kind, english, turkish[english], source[english]) for english, kind in kinds.items())
    print(f"wrote {TABLE.relative_to(PROJECT_ROOT)}: {len(kinds)} strings, model {model}, prompt version {PROMPT_VERSION}, "
          f"{len(fixes)} checker fixes, {len(corrections)} hand corrections")


def check_eval(checker: str) -> None:
    """How the checker does on the spot-check you and Claude judged (the model's original translations)."""
    with SPOTCHECK.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    results = check(checker, [(row["kind"], row["english"], row["turkish"]) for row in rows])
    flagged = {row["n"] for row in rows if results[(row["english"], row["turkish"])]["fix"]}
    bad = {row["n"] for row in rows if row["acceptable (1/0)"] == "0"}
    print(f"{checker}: flagged {len(flagged & bad)} of {len(bad)} judged unacceptable, "
          f"{len(flagged - bad)} of {len(rows) - len(bad)} judged acceptable")
    for row in rows:
        result = results[(row["english"], row["turkish"])]
        if result["fix"] or row["n"] in bad:
            print(f"#{row['n']} judged {'0' if row['n'] in bad else '1'} | {'FIX' if result['fix'] else 'ok '} | "
                  f"{row['turkish'][:70]} -> {(result['fix'] or '')[:70]} ({result['why']})")


def spotcheck(size: int) -> None:
    """Random rows of the table for you to judge (ROADMAP 6.1c check), every kind represented."""
    if SPOTCHECK.exists():
        sys.exit(f"{SPOTCHECK.relative_to(PROJECT_ROOT)} exists; delete or rename it to draw a new sample.")
    with TABLE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rng = random.Random(2026)
    kinds = sorted({row["kind"] for row in rows})
    sample = [rng.choice([row for row in rows if row["kind"] == kind]) for kind in kinds]
    sample += rng.sample([row for row in rows if row not in sample], size - len(sample))
    with SPOTCHECK.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["n", "kind", "english", "turkish", "acceptable (1/0)", "better translation", "note"])
        writer.writerows([n, row["kind"], row["english"], row["turkish"], "", "", ""] for n, row in enumerate(sample, 1))
    print(f"wrote {SPOTCHECK.relative_to(PROJECT_ROOT)} ({size} rows)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pilot", type=int, help="draw this many strings for a blind comparison of --models")
    parser.add_argument("--models", default="gpt-4o-mini,gpt-5.4-mini")
    parser.add_argument("--model", help="translate everything with this model and write the app's table")
    parser.add_argument("--spotcheck", type=int, help="draw this many random rows of the table for you to judge")
    parser.add_argument("--checker", help="with --model: check translations not checked before with this model")
    parser.add_argument("--checker-kinds", help="with --checker: only these kinds, comma-separated (e.g. title,description)")
    parser.add_argument("--check-eval", help="run this checker on the judged spot-check and compare")
    args = parser.parse_args()
    load_dotenv(ENV_PATH)
    if args.pilot:
        pilot(args.pilot, args.models.split(","))
    elif args.check_eval:
        check_eval(args.check_eval)
    elif args.model:
        full_run(args.model, args.checker, set(args.checker_kinds.split(",")) if args.checker_kinds else None)
    elif args.spotcheck:
        spotcheck(args.spotcheck)
    else:
        counts = {kind: len(texts) for kind, texts in collect().items()}
        print(f"strings to translate: {counts}; pass --model to translate them")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

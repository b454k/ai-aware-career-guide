#!/usr/bin/env python3
"""Add new research sources to the app, incrementally (ROADMAP 8.2, D18 option 1).

The claims pipeline (collect -> enrich -> chunk -> extract -> postprocess -> match -> relevance check ->
translation) was built to run over all sources at once. This runs it for the URLs in
data/research/source_urls.txt that data/research/research_sources_enriched.csv doesn't list yet:

  collect, enrich, chunk   only the new sources (their per-source functions), appended to the existing files
  extract                  only chunks not extracted before (the extractor resumes; paid)
  postprocess              all claims again (no API; reproduces today's claims exactly, and the extractor only
                           appends, so existing claim IDs never move)
  match                    all claims again (local embeddings, no API)
  relevance check          only (career, claim) pairs not checked before (paid)
  translation and check    only text not translated or checked before (paid)

By default it only lists the new URLs and stops (a dry run): downloading and the paid steps need --run.
A URL in the list is a decision to pay for its extraction, so it is reviewed first (in the monthly run,
it arrives in a pull request you merge). The first version ran straight away and found 7 URLs nobody had
processed, not all of them research (CHANGELOG 056). The files it needs from earlier runs (the claims,
chunks, raw extraction and caches) are the monthly run's state (D19 = C).

    python scripts/research/update_research.py          # list what would be added
    python scripts/research/update_research.py --run    # add it
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESEARCH = PROJECT_ROOT / "data" / "research"
sys.path.insert(0, str(Path(__file__).resolve().parent))

import chunk_research_sources as chunker  # noqa: E402
import collect_research_sources as collector  # noqa: E402
import enrich_research_metadata as enricher  # noqa: E402

URLS = RESEARCH / "source_urls.txt"
ENRICHED = RESEARCH / "research_sources_enriched.csv"


def run(*args: str) -> None:
    print(f"\n$ python {' '.join(args)}", flush=True)
    subprocess.run([sys.executable, *args], cwd=PROJECT_ROOT, check=True)


def main() -> int:
    known = pd.read_csv(ENRICHED, dtype=str, keep_default_na=False)
    new_urls = [url for url in collector.read_urls(URLS) if url not in set(known["url"])]
    print(f"sources known: {len(known)}; new URLs: {len(new_urls)}")
    for url in new_urls:
        print(f"  new: {url}")
    if not new_urls:
        print("Nothing to add; no API calls made.")
        return 0
    if "--run" not in sys.argv[1:]:
        print("Dry run: nothing downloaded, no API calls. Add --run to download and extract these sources.")
        return 0

    # collect: the collector's own source IDs, kept distinct from the existing ones
    used_ids = set(known["source_id"])
    collected = []
    for url in new_urls:
        collected.append(collector.process_source(collector.make_source_id(url, used_ids), url))
        time.sleep(2)

    # enrich, then append to the registry with the same columns
    enriched = pd.DataFrame([enricher.process_row(pd.Series(record)) for record in collected])
    for column in known.columns:
        if column not in enriched.columns:
            enriched[column] = "auto_extracted" if column == "metadata_review_status" else ""
    pd.concat([known, enriched[known.columns].astype(str).replace("nan", "")]).to_csv(ENRICHED, index=False)

    # chunk the new sources only, appended to the chunks and the chunk summary
    new_rows = pd.read_csv(ENRICHED, dtype=str, keep_default_na=False).tail(len(collected))
    chunks, summaries = [], []
    for _, row in new_rows.iterrows():
        rows, summary = chunker.process_source(row)
        chunks.extend(rows)
        summaries.append(summary)
    with chunker.CHUNKS_JSONL.open("a", encoding="utf-8") as out:
        for chunk in chunks:
            out.write(chunker.json.dumps(chunk, ensure_ascii=False) + "\n")
    summary = pd.read_csv(chunker.SUMMARY_CSV, dtype=str, keep_default_na=False)
    pd.concat([summary, pd.DataFrame(summaries, columns=chunker.SUMMARY_FIELDS).astype(str)]).to_csv(
        chunker.SUMMARY_CSV, index=False)
    print(f"collected {len(collected)} sources: {sum(s['processed'] for s in summaries)} processed, {len(chunks)} chunks")

    run("scripts/research/extract_ai_impact_claims.py")
    run("scripts/research/postprocess_ai_impact_claims.py", "--overwrite-clean")
    run("scripts/research/match_claims_to_occupations.py")
    run("scripts/research/check_claim_relevance.py")
    run("scripts/i18n/translate_content.py", "--model", "gpt-4o-mini", "--checker", "gpt-5.4-mini")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

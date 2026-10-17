# Scripts and data files

Reference for the build and analysis scripts, and for the files they produce. Run every script from the project root. The project's overview is in the [main README](../README.md).

## App modules (`career_rag/`)

| File | Purpose |
| --- | --- |
| `interest_profiler_app.py` | Streamlit app: the card test, Job Zones, follow-up questions, the report, the new-title search. |
| `config.py` | Paths (each can be overridden by an environment variable) and the embedding model's name. |
| `artifacts.py` | Checks that the files the app reads exist, and names the missing ones. |
| `interest_profiler_local.py` | Interest Profiler scoring (six RIASEC scores, Holland code) and the profile JSON. |
| `ip_career_matcher.py` | O\*NET's own matching rule over every occupation in a Job Zone. |
| `ip_followup_agent.py` | Follow-up questions and their interpretation (LLM, with a fallback). |
| `ip_refinement_ranker.py` | Reranks careers with the follow-up answers; updates the profile with them. |
| `ip_final_report.py` | Builds the report: O\*NET details, AI evidence, citations, "a day in the life". |
| `ip_ai_impact.py` | A career's AI evidence: Anthropic task coverage, Claude usage, the ILO score, research claims. |
| `ip_report_ui.py` | Renders the report: the careers list beside the selected career, and "About the data". |
| `new_titles.py` | New job titles and their closest O\*NET roles, looked up by career. |
| `departments.py` | Turkish university departments and the O\*NET careers they lead to. |
| `occupation_aliases.py` | Resolves a career title to an O\*NET occupation. |
| `ui_i18n.py` | All user-visible texts in English and Turkish, and the Turkish content lookup. |
| `static/app.css` | The few styles the light theme (`.streamlit/config.toml`) doesn't cover: the activity card. |

## Data files

| Path | Type | Role |
| --- | --- | --- |
| `onet_interest_profiler/interest_profiler_questions.json` | JSON, committed | The 60 Interest Profiler activities (from O\*NET's short form PDF). |
| `data/duckdb/onet.duckdb` | DuckDB, built | O\*NET 31.0, from O\*NET's text files. |
| `data/duckdb/ai_impact.duckdb` | DuckDB, built | Anthropic task coverage, observed exposure, and the 2026 Claude usage (global and Turkey). |
| `data/duckdb/research_claims.duckdb` | DuckDB + NumPy, built | Each career's candidate research claims (embedding match). |
| `data/research/career_research_claims.csv` | CSV, **committed** | The research claims each career shows (at most 3; D16, D17). |
| `data/research/source_urls.txt` | text, **committed** | The research sources; the monthly run adds the new ones. |
| `data/research/claim_corrections.csv` | CSV, **committed** | Hand corrections of shown claims. |
| `data/i18n/content_tr.csv` | CSV, **committed** | O\*NET content and research claims in Turkish (8,795 strings), an adaptation marked in the app. |
| `data/i18n/content_tr_corrections.csv` | CSV, **committed** | Hand corrections of translations; they win over the model and the checker. |
| `data/ilo/ilo_exposure_by_career.csv` | CSV, **committed** | Each career's ISCO-08 group and its ILO exposure score (909 careers). |
| `data/new_titles/new_job_titles.csv` | CSV, **committed** | 29 new job titles with their closest O\*NET roles, reviewed by hand. |
| `data/departments/departments.csv` | CSV, **committed** | 96 Turkish university departments with their US fields of study (CIP 2020), reviewed by hand. |
| `data/departments/department_careers.csv` | CSV, **committed**, built | Each department's O\*NET careers (604 links). |
| `data/departments/department_career_exclusions.csv` | CSV, **committed** | Specialties that came in through catch-all codes and don't fit a department, with reasons. |
| `onet_interest_profiler/ip_profile_result.json`, `ip_final_career_report.*` | JSON / Markdown, local | The user's saved profile and report; not committed. |

The research pipeline's working files (`data/research/*.jsonl`, the caches) are not in git; the monthly run keeps them as the `pipeline-state` release asset (D19).

## Build

| Script | Purpose |
| --- | --- |
| `build_all_artifacts.py` | Downloads the public sources, builds the O\*NET and AI-impact databases, optionally rebuilds the shown research claims (`--with-research-claims`), and runs the smoke test. |
| `download_sources.py` | Downloads the public files (about 315 MB) and checks each one's size and SHA-256; `--only PREFIX` limits it to files under `data/PREFIX`. |
| `onet/build_onet_duckdb.py` | Builds `onet.duckdb` from O\*NET's text release; `--compare` shows the differences between two builds. |
| `ai_impact/build_aei_release.py` | Extracts per-occupation and per-task Claude usage (global and Turkey) from an Anthropic Economic Index release. |
| `ai_impact/build_ai_impact_duckdb.py` | Builds `ai_impact.duckdb`: task coverage (joined to O\*NET tasks by exact text), observed exposure, the usage extract. |
| `ai_impact/extract_ilo_wp140.py` | Reads the ILO's exposure index (WP140, Annex Table A1) from its PDF: 427 ISCO-08 groups, checked by two independent readings. |
| `departments/build_department_careers.py` | Builds each department's careers: CIP → SOC (NCES crosswalk) → O\*NET, minus the reviewed exclusions; flags specialties. |
| `onet/build_onet_isco08.py` | Links each O\*NET career to one ISCO-08 group with O\*NET's ESCO crosswalk (918 of 923). |
| `ai_impact/build_ilo_by_career.py` | Joins the two above into `ilo_exposure_by_career.csv`, which the app reads. |

## Research claims

| Script | Purpose |
| --- | --- |
| `research/collect_research_sources.py` | Downloads the sources in `source_urls.txt` (PDFs or web snapshots). |
| `research/enrich_research_metadata.py` | Fills in titles, authors and years. |
| `research/chunk_research_sources.py` | Splits the sources into chunks for extraction. |
| `research/extract_ai_impact_claims.py` | Extracts AI and work claims from the chunks (OpenAI; paid). |
| `research/postprocess_ai_impact_claims.py` | Checks each claim's quote against the source text, cleans labels, removes duplicates. |
| `research/match_claims_to_occupations.py` | Embeds the claims and each career with BGE and keeps each career's candidates (exact NumPy search; D6). |
| `research/check_claim_relevance.py` | Asks gpt-5.4-mini which candidates are about each career and writes what the app shows (D16); answers are cached, so only new pairs cost. |
| `research/check_claim_standalone.py` | Asks once per claim whether it stands on its own; the ones that don't are not shown (4.2). `--audit` compares it with the audited claims. |
| `research/update_research.py` | Adds the URLs not processed yet, running all the steps above on new material only (dry run unless `--run`; paid). |
| `research/pipeline_state.py` | Packs or unpacks the monthly run's state. |
| `i18n/translate_content.py` | Translates new O\*NET content and shown claims into Turkish and checks them (paid; cached). |

## Checks and analysis

| Script | Purpose |
| --- | --- |
| `check_artifacts.py` | Checks the required files and runs a follow-up ranking smoke test. |
| `make_baseline.py` | Rebuilds the test profiles' reports and compares them with `baseline/` (`--check`). |
| `check_source_updates.py` | Read-only: reports newer or changed public sources (exit 1 when something is new). |
| `analysis/compare_top_match_rankings.py` | Compares the matches with O\*NET's official Interest Profiler (needs `ONET_API_KEY`). |
| `analysis/make_claim_label_set.py` | Draws the claims to label for the evaluation; `--round` adds a later round and keeps the old labels. |
| `analysis/compare_claim_search_backends.py` | Compares exact NumPy search with Chroma's approximate index (D6). |
| `diagnostics/rag_diagnostics.py` | Read-only inspection of the O\*NET database. |
| `../notebooks/run_all.py` | Runs the evaluation notebooks top to bottom before they are committed. |

## Typical rebuilds

```bash
python scripts/onet/build_onet_duckdb.py data/onet/db_31_0/db_31_0_text data/duckdb/onet.duckdb
python scripts/ai_impact/build_aei_release.py release_2026_06_26
python scripts/ai_impact/build_ai_impact_duckdb.py
python scripts/build_all_artifacts.py --with-research-claims
```

# AI Aware Career  Guide

Install dependencies, restore/check local RAG artifacts, and run the Streamlit app from the project root:

```powershell
python -m pip install -r requirements.txt
python scripts\archives\restore_data_archives.py
python scripts\check_artifacts.py
python -m streamlit run interest_profiler_app.py
```

If artifacts are missing and you have raw/local data available, rebuild them:

```powershell
python scripts\build_all_artifacts.py
```

## Project Overview

AI Aware Career Guide is a local career-guidance application built for an Applied NLP workflow. It combines the O*NET Interest Profiler, O*NET occupation data, and AI labor-market evidence to help a user move from interests to grounded career recommendations.

The final app is `interest_profiler_app.py`. It asks the O*NET Interest Profiler short-form questions, computes RIASEC scores, lets the user choose current and future Job Zones, optionally asks follow-up questions, ranks matching careers, and generates a cited final career report. Follow-up ranking and report generation require the local O*NET DuckDB database and the AI-impact evidence file; if they are missing, the app stops and shows rebuild instructions.

The project can run without an OpenAI key for deterministic scoring and template fallback behavior. LLM-powered follow-up interpretation, claim extraction, and richer report text require `OPENAI_API_KEY` in `.env`.

## Quick Start

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python scripts\archives\restore_data_archives.py
python scripts\check_artifacts.py
python -m streamlit run interest_profiler_app.py
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
python scripts/archives/restore_data_archives.py
python -m streamlit run interest_profiler_app.py
```

Keep `.env` local. Do not commit API keys or machine-specific paths.

## Fresh Clone Setup

Windows PowerShell:

```powershell
git clone <repo-url>
cd career-rag
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
python scripts\archives\restore_data_archives.py
python scripts\check_artifacts.py
python -m streamlit run interest_profiler_app.py
```

Fill `HF_TOKEN` in `.env` before rebuilding the research-claims Chroma collection. Fill `OPENAI_API_KEY` only if you want LLM-powered follow-up interpretation or research-claim extraction.

If the split archive bundle is not available, place the raw O*NET SQL dump under `onet_sql/`, place/download research and Anthropic source files under `data/`, then run:

```powershell
python scripts\build_all_artifacts.py
python scripts\check_artifacts.py
```

For a quick path-only check (skips the follow-up ranking smoke test):

```powershell
python scripts\check_artifacts.py --skip-retrieval
```

Expected behavior after a clone is explicit: the app either works with restored artifacts, or it shows `RAG artifacts missing. Please run the setup/build command.` with the exact missing files/folders.

## Artifact Policy

Generated DuckDB files, JSONL documents, Chroma stores, downloaded research files, profile results, final reports, caches, and logs are ignored by git. The `data_archives/` bundle is no longer in the repository (it contained third-party PDFs), so a fresh clone cannot restore data yet; ROADMAP task 3.3 replaces it with a build step that uses only public sources.

Versioned artifact bundle:

```powershell
python scripts\archives\restore_data_archives.py
```

Rebuild from source/local inputs:

```powershell
python scripts\build_all_artifacts.py
```


## Troubleshooting Missing RAG Artifacts

- Missing `data/duckdb/onet.duckdb`: run `python scripts\archives\restore_data_archives.py`, or rebuild with `python scripts\build_all_artifacts.py` after placing O*NET SQL files in `onet_sql/`.
- Missing `data/processed/ai_impact_evidence_deduped.jsonl`: restore archives or run the structured AI-impact build steps.
- `HF_TOKEN is missing`: add it to `.env` before building embeddings.
- Follow-up results look identical to initial matches: open `Debug: RAG artifacts` in the app and run `python scripts\check_artifacts.py`; the app now warns when follow-up answers exist but the refined order does not change.

## What The App Does

The Streamlit app turns an O*NET Interest Profiler session into a cited career report. It does not only rank careers; it also shows the evidence behind the rankings.

The user-facing flow is:

1. Load the local O*NET Interest Profiler short-form questions from `onet_interest_profiler/interest_profiler_questions.json`.
2. Score the six Holland/RIASEC interests: Realistic, Investigative, Artistic, Social, Enterprising, and Conventional.
3. Detect clear, tied, or near-tied interest profiles.
4. Ask current and future Job Zone preferences so recommendations respect education, training, and preparation constraints.
5. Match careers from the local O*NET Interest Profiler career listing JSON.
6. Optionally ask follow-up questions about work setting, people/data/things/ideas, independence, team style, impact, structure, strengths, recognition, concerns, and future vision.
7. Use follow-up answers to refine the profile and rerank candidate careers.
8. Resolve displayed career titles to local O*NET occupations and O*NET-SOC codes.
9. Build a final report with tabs for a summary, **Top Matches**, alternative careers, and cited sources.

| Window | Main purpose | How to read it |
| --- | --- | --- |
| **Top Matches** | Shows the main recommendations selected from the Interest Profiler career-match pipeline. | Treat this as the ranked recommendation list. Each card is a specific resolved occupation with job details, skills, education, day-in-the-life text, and task-level AI-impact notes. |

## How The App Works

`interest_profiler_app.py` is the user-facing Streamlit application. It keeps the current profile, follow-up state, and generated report in Streamlit session state, while also saving durable JSON outputs under `onet_interest_profiler/`.

The app works in four stages:

1. **Interest Profiler scoring**: the app loads `interest_profiler_questions.json`, records checked activities, and uses `career_rag/interest_profiler_local.py` to compute six RIASEC scores and a Holland code.
2. **Career candidate matching**: `career_rag/ip_career_matcher.py` matches the highest RIASEC interests against `ip_career_listings.json`, filtered by current and future O*NET Job Zones.
3. **Optional follow-up refinement**: `career_rag/ip_followup_agent.py` asks open-ended questions, optionally uses OpenAI to interpret answers, and `career_rag/ip_refinement_ranker.py` adjusts the ranked career list using preferences, Job Zones, O*NET occupation details, and follow-up text.
4. **Top Matches report construction**: `career_rag/ip_final_report.py` builds two candidate pools, one for the current Job Zone and one for the future Job Zone. It takes up to five careers from each pool, resolves each title to an O*NET-SOC code, retrieves structured occupation details from DuckDB, attaches exact local AI-impact task evidence when available, and creates the detailed match cards.

The app checks required artifacts before building a report. If the DuckDB database or the AI-impact evidence file is missing, it shows rebuild/restore instructions instead of silently producing weak results.

### How Top Matches Are Built

The **Top Matches** window is candidate-first. It starts from careers that the O*NET Interest Profiler listing already associates with the user's strongest interests and selected Job Zones. If follow-up answers exist, the app uses `final_ranked_matches` or `refined_career_matches`; otherwise it uses the original `career_matches` groups. The report builder then fills each selected career with local evidence.

Top Matches retrieval/enrichment flow:

1. Candidate careers come from `ip_career_listings.json`, grouped by `primary_current_zone`, `primary_future_zone`, `secondary_future_zone`, and `tertiary_future_zone`.
2. `_candidate_groups_from_profile()` creates "Current Job Zone options" and "Future Job Zone options" with a limit of five per group.
3. `resolve_career_alias()` maps each display title to an O*NET occupation title and O*NET-SOC code using the local occupation index.
4. `get_onet_occupation_details()` queries `data/duckdb/onet.duckdb` for description, tasks, skills, knowledge, abilities, education, Job Zone, work context, software, and related occupations.
5. `build_ai_impact_for_occupation()` reads local structured AI-impact JSONL rows and uses exact O*NET-SOC/task matches where possible; if no exact local task row exists, the card labels that as missing evidence instead of treating it as zero impact.
6. `_build_match()` packages the card with fit label, why-it-fits text, O*NET details, key skills, education, day-in-the-life text, and AI-impact breakdown.

## RAG Implementation

The app currently answers everything with exact lookups: O*NET occupation details from DuckDB and AI-impact evidence matched by O*NET-SOC code and task ID. Structured data like this is looked up, not searched by similarity.

Retrieval-augmented generation is being rebuilt where it fits: over the 2,673 quote-validated research claims (unstructured text), shown as a "What research says" section per career (see `docs/ROADMAP.md`, Phase 4). The earlier Semantic Report tab and its O*NET and AI-impact vector indexes were removed on 2026-09-23; the reasons are in `docs/CHANGELOG.md`, entry 009.

### Models, Technologies, Databases, And Data Types

| Part | Model / Technology | Main data types | Used by |
| --- | --- | --- | --- |
| Interest scoring | Deterministic Python scoring | JSON questions, checked activity IDs, integer RIASEC scores, Holland code strings | `interest_profiler_app.py`, `interest_profiler_local.py` |
| Local occupation database | DuckDB | O*NET SQL-imported relational tables, O*NET-SOC codes, task/skill/knowledge rows | `ip_final_report.py`, `ip_refinement_ranker.py`, `occupation_aliases.py` |
| AI-impact evidence | Exact lookups by O*NET-SOC code and task ID | JSONL evidence rows, metric fields, source metadata | `ip_ai_impact.py` |
| LLM follow-up questions and report text | OpenAI chat model, default `gpt-4o-mini` via `OPENAI_MODEL` | Chat messages, JSON outputs, grounded report strings | `ip_followup_agent.py`, parts of `ip_final_report.py` |
| App UI | Streamlit | Session-state dictionaries, forms, tabs, tables, report JSON | `interest_profiler_app.py`, `ip_report_ui.py` |
| Build and diagnostics | Python CLI scripts | DuckDB files, JSONL, CSV, PDF/text source files, Chroma stores, zip archive parts | `scripts/` |

Important persistent artifacts:

| Artifact | Type | Role |
| --- | --- | --- |
| `data/duckdb/onet.duckdb` | DuckDB database | Structured O*NET facts used for occupation details, tasks, aliases, and report grounding. |
| `data/processed/ai_impact_evidence_deduped.jsonl` | JSONL | Structured Anthropic/NBER AI-impact evidence rows. |
| `chroma_research/` | Chroma persistent DB | `research_ai_impact_claims` collection (not used by the app yet; see ROADMAP Phase 4). |
| `onet_interest_profiler/ip_profile_result.json` | JSON | Saved user profile, scores, Job Zones, matches, and follow-up refinement. |
| `onet_interest_profiler/ip_final_career_report.json` | JSON | Structured final report rendered by the Streamlit UI. |
| `onet_interest_profiler/ip_final_career_report.md` | Markdown | Human-readable final report export. |

## Essential Main-Work Files

These are the files that do the core retrieval and inference work:

| File | Why it matters |
| --- | --- |
| `interest_profiler_app.py` | Main app orchestrator: collects inputs, triggers scoring, follow-up refinement, artifact checks, report generation, and report rendering. |
| `career_rag/ip_final_report.py` | Final Interest Profiler report builder. It combines profile data, career matches, DuckDB occupation details, AI-impact evidence, citations, and optional LLM-written narratives. |
| `career_rag/ip_ai_impact.py` | Builds occupation-specific AI-impact sections from local evidence, especially exact O*NET task rows when available. |
| `career_rag/ip_followup_agent.py` | Generates and interprets open-ended follow-up questions, using deterministic fallback logic or OpenAI JSON output. |
| `career_rag/ip_refinement_ranker.py` | Converts follow-up answers into structured preferences and reranks candidate careers using local O*NET evidence. |

For rebuilding the RAG indexes, the most important scripts are:

| Script | Main output |
| --- | --- |
| `scripts/onet/import_onet.py` | `data/duckdb/onet.duckdb` |
| `scripts/ai_impact/merge_ai_impact_evidence.py` | Deduplicated structured AI-impact JSONL |
| `scripts/research/embed_ai_impact_claims.py` | Chroma `research_ai_impact_claims` collection |
| `scripts/build_all_artifacts.py` | End-to-end local artifact rebuild |
| `scripts/check_artifacts.py` | Artifact and follow-up ranking smoke test |

## Compact Structure

```text
career-rag/
  README.md                       Project setup, architecture, scripts, and references
  requirements.txt                Python package dependencies
  .env.example                    Environment variable template
  interest_profiler_app.py        Streamlit entrypoint
  career_rag/                     Runtime package used by the app
  scripts/
    onet/                         O*NET database import
    research/                     Research source and claim-processing utilities
    ai_impact/                    Structured AI-exposure evidence pipeline
    diagnostics/                  Read-only inspection CLI
    archives/                     Data archive restore/package helpers
  onet_interest_profiler/         Local PDF-derived profiler assets and app outputs
  data/                           Ignored generated data restored from archives
  data_archives/                  Split archive bundle for generated data
  onet_sql/                       O*NET SQL source dump location
  chroma_research/                Ignored Chroma store for research evidence
```

## Runtime Package

| File | Purpose |
| --- | --- |
| `interest_profiler_app.py` | Streamlit UI for the local O*NET Interest Profiler and final report workflow. |
| `career_rag/__init__.py` | Package marker. |
| `career_rag/config.py` | Shared project paths, environment loading, and embedding-model configuration. |
| `career_rag/artifacts.py` | Central artifact validation and missing-artifact messages. |
| `career_rag/interest_profiler_local.py` | Local O*NET Interest Profiler scoring, profile JSON creation, and RIASEC helper logic. |
| `career_rag/ip_career_matcher.py` | Local career matching for Interest Profiler scores and Job Zones. |
| `career_rag/ip_followup_agent.py` | Optional follow-up question planning and refinement for ambiguous or personalized profiles. |
| `career_rag/ip_refinement_ranker.py` | Follow-up-aware ranking adjustments for candidate careers. |
| `career_rag/ip_final_report.py` | Builds and saves the final career report JSON/Markdown with citations and local evidence. |
| `career_rag/ip_report_ui.py` | Streamlit rendering helpers for the final report tabs, cards, tables, and sources. |
| `career_rag/ip_ai_impact.py` | AI-impact helpers for final reports, using local structured evidence with labeled fallback rows. |
| `career_rag/occupation_aliases.py` | Resolves user-facing career titles to local O*NET occupations and SOC codes. |
| `career_rag/ai_exposure_utils.py` | Shared normalization, hashing, JSONL, and source-policy helpers for AI-exposure pipelines. |

## Script Groups

Run scripts from the project root.

### O*NET Build Scripts

| Script | Purpose |
| --- | --- |
| `scripts/onet/create_db.py` | Creates or opens `data/duckdb/onet.duckdb`. |
| `scripts/onet/import_onet.py` | Imports all O*NET SQL files from `onet_sql/` into DuckDB in filename order. |
| `scripts/onet/import_missing_onet_tables.py` | Additively imports supplemental O*NET tables into the existing DuckDB database. |

Typical O*NET rebuild:

```powershell
python scripts\onet\import_onet.py
python scripts\onet\import_missing_onet_tables.py
```

### Research Claim Scripts

| Script | Purpose |
| --- | --- |
| `scripts/research/collect_research_sources.py` | Reads `data/research/source_urls.txt`, downloads PDFs or webpage snapshots, and writes a source inventory CSV. |
| `scripts/research/enrich_research_metadata.py` | Inspects collected PDFs/text and enriches missing title, author, and year metadata. |
| `scripts/research/extract_ai_impact_claims.py` | Uses the OpenAI API to extract AI/job-impact claims from prepared research chunks. |
| `scripts/research/postprocess_ai_impact_claims.py` | Cleans labels, validates evidence quotes, deduplicates claims, and writes final claim JSONL/CSV summaries. |
| `scripts/research/embed_ai_impact_claims.py` | Embeds clean AI-impact claims into Chroma collection `research_ai_impact_claims`. |
| `scripts/research/extract_research_chunks.py` | Extracts policy-limited inference chunks from downloaded research-source manifests for the structured AI-impact pipeline. |

### Structured AI-Impact Scripts

| Script | Purpose |
| --- | --- |
| `scripts/ai_impact/download_research_sources.py` | Downloads source URLs and writes a source-policy manifest for AI-exposure work. |
| `scripts/ai_impact/extract_nber_w31222_ai_exposure.py` | Extracts structured AI-exposure evidence from NBER Working Paper 31222. |
| `scripts/ai_impact/build_anthropic_economic_index.py` | Normalizes Anthropic Economic Index data into AI-impact evidence rows. |
| `scripts/ai_impact/merge_ai_impact_evidence.py` | Merges and deduplicates Anthropic and NBER structured evidence. |

Typical structured AI-impact rebuild:

```powershell
python scripts\ai_impact\download_research_sources.py
python scripts\research\extract_research_chunks.py
python scripts\ai_impact\extract_nber_w31222_ai_exposure.py --use-llm
python scripts\ai_impact\build_anthropic_economic_index.py --download-if-missing
python scripts\ai_impact\merge_ai_impact_evidence.py
python scripts\ai_impact\embed_ai_impact_evidence.py
```

If LLM extraction is unavailable, run NBER extraction without `--use-llm`.

### Diagnostics And Archives

| Script | Purpose |
| --- | --- |
| `scripts/diagnostics/rag_diagnostics.py` | Read-only diagnostics for the O*NET DuckDB database. |
| `scripts/check_artifacts.py` | Verifies required paths and runs a follow-up ranking smoke test. |
| `scripts/build_all_artifacts.py` | Runs the O*NET, AI-impact, Chroma, and smoke-test build steps in order. |
| `scripts/archives/restore_data_archives.py` | Restores ignored local runtime data from split zip parts in `data_archives/`. |
| `scripts/archives/package_data_archives.py` | Packages generated local data into GitHub-friendly split zip archives. |

Useful diagnostics:

```powershell
python scripts\diagnostics\rag_diagnostics.py tables
python scripts\diagnostics\rag_diagnostics.py documents
python scripts\check_artifacts.py
```

## Data And Evidence

| Path | Purpose |
| --- | --- |
| `onet_interest_profiler/Interest_Profiler.pdf` | Source PDF for the 60 short-form activities. |
| `onet_interest_profiler/IP_Career_Listings.pdf` | Source PDF for Interest Area and Job Zone career listings. |
| `onet_interest_profiler/interest_profiler_questions.json` | Runtime JSON for the 60 profiler activities. |
| `onet_interest_profiler/ip_career_listings.json` | Runtime JSON for local career matching. |
| `data/duckdb/onet.duckdb` | DuckDB database built from O*NET SQL tables. |
| `data/research/source_urls.txt` | URL input list for research source collection. |
| `data/research/*.jsonl` and `*.csv` | Research-claim extraction, cleanup, and summary outputs. |
| `data/processed/*.jsonl` | Structured AI-impact evidence and method/inference chunks. |
| `chroma_research/` | Research Chroma collections. |
| `data_archives/` | Split archive bundle for sharing ignored generated data. |

All Chroma collections use the embedding model configured in `career_rag/config.py`:

```text
BAAI/bge-small-en-v1.5
```

SentenceTransformer model loading may require `HF_TOKEN` in `.env`.

## Important Implementation Points

- User profile answers are saved as structured JSON, not embedded into Chroma.
- Raw RIASEC scores are preserved separately from follow-up refinements.
- Job Zone constraints are part of matching, so recommendations respect current and future preparation levels.
- O*NET occupation facts come from local DuckDB tables.
- AI-impact rows distinguish observed exposure, task penetration, adoption context, and fallback/inferred explanations.
- Exposure is not treated as job loss; broad labor-market evidence is not converted into task-level automation scores unless the local data supports that level.
- Generated app outputs such as `ip_profile_result.json` and `ip_final_career_report.json` are ignored by git.
- Generated logs, smoke-test outputs, caches, Chroma stores, DuckDB files, downloaded PDFs, and large data files are intentionally excluded from source control.

## Applied NLP Course Summary

Problem addressed: students and career changers need career recommendations that are personalized, explainable, and grounded in trusted occupation data, while also reflecting current uncertainty around AI exposure.

Solution: this project builds a retrieval-augmented career guidance system. It scores user interests with the O*NET Interest Profiler, retrieves relevant local O*NET evidence, adds structured AI-impact evidence, and produces a cited report that explains why each career is recommended.

Core NLP steps:

1. Data collection from O*NET PDFs, O*NET SQL tables, research URLs, NBER evidence, and Anthropic Economic Index data.
2. Text cleaning, metadata enrichment, chunking, and JSONL document construction.
3. Semantic embedding with `BAAI/bge-small-en-v1.5`.
4. Vector indexing and retrieval with ChromaDB.
5. Query/profile structuring from RIASEC scores, Job Zones, and follow-up answers.
6. Retrieval-augmented generation with OpenAI models when keys are available.
7. Citation-aware final reporting with deterministic fallback behavior.

Technologies used: Python, Streamlit, DuckDB, ChromaDB, SentenceTransformers, OpenAI API, pandas, PyMuPDF, BeautifulSoup, requests, and local O*NET/AI-impact data artifacts.

In short, AI Aware Career Guide turns an interest-profile questionnaire into an evidence-grounded career report by combining classic NLP preprocessing, embeddings, vector retrieval, structured occupation databases, and optional LLM generation.

## References

Primary O*NET and Interest Profiler sources:

- O*NET Resource Center: https://www.onetcenter.org/
- O*NET OnLine: https://www.onetonline.org/
- O*NET Database downloads: https://www.onetcenter.org/database.html
- O*NET Interest Profiler resources: https://www.onetcenter.org/IP.html
- O*NET Interest Profiler web app: https://onetinterestprofiler.org/
- My Next Move interest browser: https://www.mynextmove.org/find/interests
- O*NET Interest Profiler Short Form PDF: https://www.onetcenter.org/dl_tools/ipsf/Interest_Profiler.pdf
- O*NET Interest Profiler Career Listings PDF: https://www.onetcenter.org/dl_tools/ipsf/IP_Career_Listings.pdf
- O*NET Interest Profiler Score Report PDF: https://www.onetcenter.org/dl_tools/ipsf/IP_Score_Report.pdf
- O*NET Interest Profiler Score Report Starter PDF: https://www.onetcenter.org/dl_tools/ipsf/IP_Score_Report_Starter.pdf
- O*NET Interest Profiler Short Form psychometric report: https://www.onetcenter.org/reports/IPSF_Psychometric.html

AI-impact and labor-market evidence sources:

- Anthropic Economic Index: https://www.anthropic.com/economic-index
- Anthropic Economic Index dataset on Hugging Face: https://huggingface.co/datasets/Anthropic/EconomicIndex
- Anthropic labor-market impacts of AI: https://www.anthropic.com/research/labor-market-impacts
- NBER Working Paper w32966, "The Rapid Adoption of Generative AI": https://www.nber.org/papers/w32966
- NBER Working Paper w32966 PDF: https://www.nber.org/system/files/working_papers/w32966/w32966.pdf
- NBER Working Paper w31222, "Generative AI and Firm Values": https://www.nber.org/papers/w31222
- NBER Working Paper w31222 PDF: https://www.nber.org/system/files/working_papers/w31222/w31222.pdf

Career-guidance and LLM-related background sources used during development:

- Hua et al. (2024), "The Career Interests of Large Language Models": https://arxiv.org/abs/2407.08564
- Renji et al. (2025), "Steve: LLM Powered ChatBot for Career Progression": https://arxiv.org/abs/2504.03789
- Jeon et al. (2025), "Letters from Future Self": https://arxiv.org/abs/2502.18881

The expanded research corpus used by the collection scripts is listed in `data/research/source_urls.txt`.

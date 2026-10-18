#!/usr/bin/env python3
"""Pack or unpack the monthly run's state (ROADMAP 8.2, D19 = C).

The research update (update_research.py) is incremental: it needs what earlier runs produced, which is not
in git. The monthly GitHub Action downloads this archive from the `pipeline-state` release, unpacks it,
runs, packs it again and uploads it. The archive holds a manifest with each file's SHA-256, checked on unpack.

    python scripts/research/pipeline_state.py pack pipeline-state.tar.gz
    python scripts/research/pipeline_state.py unpack pipeline-state.tar.gz
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_FILES = [  # everything a later run reads that git doesn't hold (D19 table)
    "data/research/research_sources_enriched.csv",   # which sources are done
    "data/research/research_chunks.jsonl",           # their text, for quote validation in postprocess
    "data/research/research_chunk_summary.csv",
    "data/research/ai_impact_claims_raw.jsonl",      # the paid extraction, appended to by each run
    "data/research/ai_impact_claims.jsonl",          # the claims
    "data/research/claim_relevance_checks.jsonl",    # the paid relevance answers
    "data/research/claim_standalone_checks.jsonl",   # the paid stand-alone answers (ROADMAP 4.2)
    "data/research/claim_ai_link_checks.jsonl",      # the paid AI-link answers and rewrites (ROADMAP 10.6)
    "data/research/claim_quote_checks.jsonl",        # the paid quote-support answers and rewrites (ROADMAP 10.13)
    "data/i18n/translation_cache.jsonl",             # the paid translations
    "data/i18n/check_cache.jsonl",                   # the paid checks
]
MANIFEST = "state_manifest.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pack(archive: Path) -> None:
    manifest = {}
    with tarfile.open(archive, "w:gz") as tar:
        for relative in STATE_FILES:
            data = (PROJECT_ROOT / relative).read_bytes()
            manifest[relative] = {"bytes": len(data), "sha256": sha256(data)}
            tar.add(PROJECT_ROOT / relative, arcname=relative)
        body = json.dumps(manifest, indent=1).encode("utf-8")
        info = tarfile.TarInfo(MANIFEST)
        info.size = len(body)
        tar.addfile(info, io.BytesIO(body))
    print(f"packed {len(STATE_FILES)} files ({sum(m['bytes'] for m in manifest.values()):,} bytes) into {archive}")


def unpack(archive: Path) -> None:
    with tarfile.open(archive, "r:gz") as tar:
        manifest = json.load(tar.extractfile(MANIFEST))
        if sorted(manifest) != sorted(STATE_FILES):
            sys.exit(f"the archive holds {sorted(manifest)}, expected {STATE_FILES}")
        for relative, expected in manifest.items():
            data = tar.extractfile(relative).read()
            if sha256(data) != expected["sha256"]:
                sys.exit(f"{relative}: checksum mismatch, archive is damaged")
            target = PROJECT_ROOT / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)  # only the listed paths are written, never a path from inside the archive
    print(f"unpacked {len(manifest)} files from {archive}; all checksums match")


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in ("pack", "unpack"):
        sys.exit(__doc__)
    (pack if sys.argv[1] == "pack" else unpack)(Path(sys.argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

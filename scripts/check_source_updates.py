#!/usr/bin/env python3
"""Report what is new at the public sources the app is built from (ROADMAP 8.1). Read-only: downloads nothing.

Checks, against scripts/download_sources.py's manifest:
  - each Anthropic Economic Index file: changed on Hugging Face? (SHA-256 for large files, git blob id for small ones)
  - newer Anthropic release folders (release_YYYY_MM_DD) than ours, and dataset folders we haven't reviewed yet
  - a newer O*NET database release than ours
  - the other files (ILO paper, O*NET's ESCO crosswalk): a different size on the server

A source update is never applied silently: schemas change between releases (ROADMAP 2.5), so each
finding is reviewed and adopted by hand, with its new checksum in the manifest.
Exit status 1 when anything is new, so the monthly run (8.2) can open an issue.

    python scripts/check_source_updates.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from download_sources import DATA_DIR, HF, SOURCES  # noqa: E402

HF_API = "https://huggingface.co/api/datasets/Anthropic/EconomicIndex/tree/main"
ONET_RELEASES = "https://www.onetcenter.org/db_releases.html"
# Hugging Face folders already reviewed (2026-10-16). A folder not listed here is reported as new.
REVIEWED_HF_FOLDERS = {
    "labor_market_impacts", "release_2025_02_10", "release_2025_03_27", "release_2025_09_15",
    "release_2026_01_15", "release_2026_03_24", "release_2026_06_26",
    "robot_exposure",  # reviewed 2026-10-16 (CHANGELOG 055)
}
HEADERS = {"User-Agent": "career-rag source check (github.com/b454k/ai-aware-career-guide)"}


def fetch(url: str, method: str = "GET") -> urllib.request.addinfourl:
    return urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS, method=method), timeout=60)


def hf_listing(folder: str) -> dict[str, dict]:
    with fetch(f"{HF_API}/{folder}" if folder else HF_API) as response:
        return {item["path"]: item for item in json.load(response)}


def git_blob_id(path: Path) -> str:
    """The id Hugging Face (git) gives a small, non-LFS file: sha1 of "blob <size>\\0" + content."""
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def main() -> int:
    findings: list[str] = []
    listings: dict[str, dict[str, dict]] = {}

    for url, local, size, checksum in SOURCES:
        if url.startswith(HF):
            remote_path = url[len(HF) + 1:]
            folder = remote_path.rsplit("/", 1)[0]
            listing = listings.setdefault(folder, hf_listing(folder))
            item = listing.get(remote_path)
            if item is None:
                findings.append(f"Anthropic: {remote_path} is no longer on Hugging Face")
            elif item.get("lfs"):
                if item["lfs"]["oid"] != checksum:
                    findings.append(f"Anthropic: {remote_path} changed (new SHA-256 {item['lfs']['oid'][:12]}…)")
            elif item["size"] != size or ((DATA_DIR / local).exists() and item["oid"] != git_blob_id(DATA_DIR / local)):
                findings.append(f"Anthropic: {remote_path} changed ({size:,} → {item['size']:,} bytes)")
        else:
            with fetch(url, "HEAD") as response:
                length = response.headers.get("Content-Length")
                modified = response.headers.get("Last-Modified", "?")
            if length is None:
                # O*NET generates the crosswalk on request and sends no size; a change shows up as a checksum
                # failure in download_sources.py whenever it is downloaded fresh (as on the monthly run's runner).
                print(f"note: {url} sends no size, so it can't be compared without downloading")
            elif int(length) != size:
                findings.append(f"{url}: size {size:,} → {int(length):,} bytes (last modified {modified})")

    folders = {path for path, item in hf_listing("").items() if item["type"] == "directory"}
    ours = max(re.findall(r"release_\d{4}_\d{2}_\d{2}", " ".join(url for url, *_ in SOURCES)))
    findings += [f"Anthropic: newer release {folder} (ours: {ours})" for folder in sorted(folders)
                 if folder.startswith("release_") and folder > ours]
    findings += [f"Anthropic: dataset folder not reviewed yet: {folder}/" for folder in sorted(folders - REVIEWED_HF_FOLDERS)
                 if not folder.startswith("release_")]

    with fetch(ONET_RELEASES) as response:
        versions = {tuple(map(int, v)) for v in re.findall(r"db_(\d+)_(\d+)_text\.zip", response.read().decode("utf-8", "replace"))}
    our_onet = max(tuple(map(int, v)) for v in re.findall(r"db_(\d+)_(\d+)_text\.zip", " ".join(url for url, *_ in SOURCES)))
    if max(versions) > our_onet:
        findings.append(f"O*NET: newer database {'.'.join(map(str, max(versions)))} (ours: {'.'.join(map(str, our_onet))})")

    print("\n".join(findings) if findings else "No updates: every source matches the manifest.")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

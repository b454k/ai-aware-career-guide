#!/usr/bin/env python3
"""Download the public source files the app is built from (ROADMAP 3.3).

Each file is checked against the size and SHA-256 recorded below; files already present
and correct are skipped, so this is safe to re-run. About 315 MB in total.

  O*NET 31.0 database, text format (CC BY 4.0) .......... https://www.onetcenter.org/db_releases.html
  Anthropic Economic Index (CC BY) ...................... https://huggingface.co/datasets/Anthropic/EconomicIndex
  ILO Working Paper 140, GenAI exposure index (CC BY 4.0)  https://www.ilo.org/publications/generative-ai-and-jobs-refined-global-index-occupational-exposure
  O*NET's ESCO to O*NET-SOC 2019 crosswalk (CC BY 4.0) ... https://www.onetcenter.org/crosswalks.html

    python scripts/download_sources.py
"""

from __future__ import annotations

import hashlib
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
HF = "https://huggingface.co/datasets/Anthropic/EconomicIndex/resolve/main"

# (url, local path under data/, size in bytes, sha256), recorded 2026-09-23.
SOURCES = [
    (
        "https://www.onetcenter.org/dl_files/database/db_31_0_text.zip",
        "onet/db_31_0_text.zip",
        13_183_034,
        "6883548adf5fde64cf6f801b35d15519c9225f2732c3cab0e281c652d16b23a9",
    ),
    (
        f"{HF}/labor_market_impacts/task_penetration.csv",
        "anthropic_economic_index/labor_market_impacts/task_penetration.csv",
        1_889_822,
        "85bee872db1d55d3e9a7f4e89da5ae4a5d59aa8ec875d728fbf4b7d820984616",
    ),
    (
        f"{HF}/labor_market_impacts/job_exposure.csv",
        "anthropic_economic_index/labor_market_impacts/job_exposure.csv",
        37_176,
        "4f0a3adf5feeb2ec5f5d02ab18cc5e851a2a4b8470bde84c0c9335017be12d68",
    ),
    (
        f"{HF}/release_2026_06_26/data_documentation.md",
        "anthropic_economic_index/release_2026_06_26/data_documentation.md",
        7_397,
        "1a01eeb7d34250b192aa9c906098bea1db971644e6bdb04497d87b7a4ed141a5",
    ),
    (
        f"{HF}/release_2026_06_26/data/aei_claude_ai_2026-06-26.csv",
        "anthropic_economic_index/release_2026_06_26/data/aei_claude_ai_2026-06-26.csv",
        219_174_671,
        "f974b358bce0e5a8417510c61da4342234cd0de9d9d0b62acf4c6dbcf8ec7b68",
    ),
    (
        f"{HF}/release_2026_06_26/data/aei_1p_api_2026-06-26.csv",
        "anthropic_economic_index/release_2026_06_26/data/aei_1p_api_2026-06-26.csv",
        77_282_477,
        "62197f003e001945ad130c2f26f5e07f3fda45ff41644df91444b04fd524a19f",
    ),
    (  # recorded 2026-10-16: Anthropic's robot exposure ("What work can robots do?", 2026-09-30), not used yet
        f"{HF}/robot_exposure/README.md",
        "anthropic_economic_index/robot_exposure/README.md",
        7_769,
        "34cce581f932237800f92494338aaa73f737a1af1e18f46ae6f4fb85e8eba408",
    ),
    (
        f"{HF}/robot_exposure/robot_exposure_occupations.csv",
        "anthropic_economic_index/robot_exposure/robot_exposure_occupations.csv",
        47_761,
        "bdb193200e2cf8f1cf353bbaa6e447ca97da7db2f29c830b0d05601801e7b271",
    ),
    (  # recorded 2026-10-15; scripts/ai_impact/extract_ilo_wp140.py reads its Annex Table A1 (ROADMAP 6.2)
        "https://www.ilo.org/sites/default/files/2025-05/WP140_web.pdf",
        "ilo/WP140_web.pdf",
        4_211_233,
        "9077761c72aabaa3c7ee70999ec5aa46a6afcf943b5fb01baa971f601d363ee9",
    ),
    (  # recorded 2026-10-15; scripts/onet/build_onet_isco08.py links careers to ISCO-08 with it (ROADMAP 6.3)
        "https://www.onetcenter.org/crosswalks/esco/ESCO_to_ONET-SOC.xlsx",
        "onet/crosswalks/ESCO_to_ONET-SOC.xlsx",
        213_061,
        "bf6c854f7ffc935eba67a296d6d7fa4d40b70fb26bcdb5ecb5621374bca6f35b",
    ),
]
ONET_TEXT_DIR = DATA_DIR / "onet" / "db_31_0"  # the zip unpacks to db_31_0/db_31_0_text/


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def is_valid(path: Path, size: int, checksum: str) -> bool:
    return path.is_file() and path.stat().st_size == size and sha256(path) == checksum


def download(url: str, path: Path, size: int, checksum: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part")
    print(f"downloading {path.relative_to(PROJECT_ROOT)} ({size / 1e6:.1f} MB) ...", flush=True)
    with urllib.request.urlopen(url, timeout=60) as response, partial.open("wb") as file:
        shutil.copyfileobj(response, file, length=1 << 20)
    if not is_valid(partial, size, checksum):
        partial.unlink()
        sys.exit(f"Downloaded file does not match the recorded size/checksum: {url}")
    partial.replace(path)


def main() -> int:
    for url, relative, size, checksum in SOURCES:
        path = DATA_DIR / relative
        if is_valid(path, size, checksum):
            print(f"ok          {path.relative_to(PROJECT_ROOT)}")
            continue
        download(url, path, size, checksum)
    if not (ONET_TEXT_DIR / "db_31_0_text").is_dir():
        with zipfile.ZipFile(DATA_DIR / "onet" / "db_31_0_text.zip") as archive:
            archive.extractall(ONET_TEXT_DIR)
        print(f"unzipped    {ONET_TEXT_DIR.relative_to(PROJECT_ROOT)}")
    print("All sources present and verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

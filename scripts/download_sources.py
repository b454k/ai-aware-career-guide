#!/usr/bin/env python3
"""Download the public source files the app is built from (ROADMAP 3.3).

Each file is checked against the size and SHA-256 recorded below; files already present
and correct are skipped, so this is safe to re-run. About 315 MB in total.

  O*NET 31.0 database, text format (CC BY 4.0) .......... https://www.onetcenter.org/db_releases.html
  Anthropic Economic Index (CC BY) ...................... https://huggingface.co/datasets/Anthropic/EconomicIndex
  ILO Working Paper 140, GenAI exposure index (CC BY 4.0)  https://www.ilo.org/publications/generative-ai-and-jobs-refined-global-index-occupational-exposure
  Microsoft, "Working with AI" results (CC BY 4.0) ........ https://github.com/microsoft/working-with-ai
  (BLS's projections can't be downloaded by a script; they are committed under data/bls/, see its README.)
  O*NET's ESCO to O*NET-SOC 2019 crosswalk (CC BY 4.0) ... https://www.onetcenter.org/crosswalks.html
  NCES CIP 2020 to SOC 2018 crosswalk (US government) .... https://nces.ed.gov/ipeds/cipcode/resources.aspx?y=56

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
MS = "https://raw.githubusercontent.com/microsoft/working-with-ai/18ec44905db3383a7fd7fd0c1ff3ab36ad7729db"

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
    (  # recorded 2026-10-18; scripts/ai_impact/build_robot_by_career.py reads it (10.14)
        f"{HF}/robot_exposure/robot_exposure_tasks.csv",
        "anthropic_economic_index/robot_exposure/robot_exposure_tasks.csv",
        99_520_982,
        "28b17551a913fd0d0bad1deb0d1c83584d9a936270e6e545eefb3a8aee081586",
    ),
    *(  # recorded 2026-10-18: Microsoft's "Working with AI" results at commit 18ec449 (v1.1); CC BY 4.0 (10.15)
        (f"{MS}/{name}", f"microsoft_working_with_ai/{name}", size, checksum)
        for name, size, checksum in (
            ("README.md", 11_287, "d252b51f6ae9473dcd2e3e0e4129ad7c320ed898eaf25e19a334541f4288e69c"),
            ("LICENSE.txt", 214, "7482bb7c074d6d966bb94e54f3393f089d576e8be9dc9e92e239a40a56df8a41"),
            ("ai_applicability_scores.csv", 50_018, "204c7e6a5ec704156212f88a6282dba7508c8b90e5df7c0d590088b2b44aa7d2"),
            ("soc_metrics.csv", 183_048, "c452eb71acf0cca7cfd236025a124802d148fed6c31f5e1baa342dd7d1babbfa"),
            ("iwa_metrics.csv", 72_575, "524f718dba31c987f0d04b55d81fac84f95533a143dfb780e04e63fb831abcf2"),
            ("soc_iwa_weights.csv", 1_238_819, "f6467d16e4af622eca06ce07b3d9b12519998ca9504743e7f08c629592771891"),
            ("soc_to_iwas.csv", 301_369, "6b4fb16f36f099bbb4dd3ffb99659bbbf791389ceab4d6b23399c7a263f77246"),
        )
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
    (  # recorded 2026-10-17; NCES's fields of study (CIP 2020) to occupations (SOC 2018), for departments (ROADMAP 9.1)
        "https://nces.ed.gov/ipeds/cipcode/Files/CIP2020_SOC2018_Crosswalk.xlsx",
        "crosswalks/CIP2020_SOC2018_Crosswalk.xlsx",
        428_901,
        "ba3d59a191b9d977a5c457a66b9348c4f2f7963aafacf72c0b80113b46bf0ab8",
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
    # --only PREFIX limits the run to files under data/PREFIX, e.g. "onet/" for the monthly run (ROADMAP 8.2).
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else ""
    for url, relative, size, checksum in SOURCES:
        if not relative.startswith(only):
            continue
        path = DATA_DIR / relative
        if is_valid(path, size, checksum):
            print(f"ok          {path.relative_to(PROJECT_ROOT)}")
            continue
        download(url, path, size, checksum)
    if "onet/db_31_0_text.zip".startswith(only) and not (ONET_TEXT_DIR / "db_31_0_text").is_dir():
        with zipfile.ZipFile(DATA_DIR / "onet" / "db_31_0_text.zip") as archive:
            archive.extractall(ONET_TEXT_DIR)
        print(f"unzipped    {ONET_TEXT_DIR.relative_to(PROJECT_ROOT)}")
    print("All sources present and verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
ml/download_dataset.py
======================
Automated acquisition and integrity verification of the OASIS Longitudinal Dataset.

Sources:
- Open Access Series of Imaging Studies (OASIS-2 / Longitudinal)
- Verified public research mirrors of oasis_longitudinal.csv
"""

from __future__ import annotations

import csv
import os
import sys
import urllib.request

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DATA_FILE = os.path.join(DATA_DIR, "oasis_longitudinal.csv")

# Verified mirrors hosting the exact standard OASIS longitudinal research table
MIRRORS = [
    "https://raw.githubusercontent.com/deepak525/Dementia-Classification-Compare-Classifiers/master/oasis_longitudinal.csv",
    "https://raw.githubusercontent.com/multivacplatform/multivac-dl/master/data/mri-and-alzheimers/oasis_longitudinal.csv",
]

REQUIRED_COLUMNS = [
    "Subject ID", "MRI ID", "Group", "Visit", "M/F", "Age",
    "EDUC", "SES", "MMSE", "CDR", "eTIV", "nWBV", "ASF"
]


def verify_dataset_file(filepath: str) -> bool:
    """Verify that the CSV exists, contains expected columns and rows."""
    if not os.path.exists(filepath):
        return False
    try:
        with open(filepath, mode="r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                return False
            header_clean = [c.strip() for c in header]
            for col in REQUIRED_COLUMNS:
                if col not in header_clean:
                    print(f"[-] Missing required column: {col}")
                    return False
            row_count = sum(1 for _ in reader)
            if row_count < 100:
                print(f"[-] Dataset too small: only {row_count} rows found.")
                return False
            print(f"[+] Dataset verification passed: {row_count} records with all required columns.")
            return True
    except Exception as e:
        print(f"[-] Verification error: {e}")
        return False


def download_dataset() -> bool:
    os.makedirs(DATA_DIR, exist_ok=True)
    if verify_dataset_file(DATA_FILE):
        print(f"[+] Dataset already present at: {DATA_FILE}")
        return True

    print(f"[*] oasis_longitudinal.csv not found locally. Attempting download to {DATA_FILE}...")

    for mirror in MIRRORS:
        try:
            print(f"[*] Trying mirror: {mirror} ...")
            req = urllib.request.Request(
                mirror,
                headers={"User-Agent": "NeuroAid-Research-Setup/1.0"}
            )
            with urllib.request.urlopen(req, timeout=20) as response, open(DATA_FILE, "wb") as out_file:
                out_file.write(response.read())

            if verify_dataset_file(DATA_FILE):
                print(f"[+] Successfully downloaded and verified dataset from {mirror}")
                return True
            else:
                if os.path.exists(DATA_FILE):
                    os.remove(DATA_FILE)
        except Exception as exc:
            print(f"[-] Download from mirror failed: {exc}")

    print("\n[!] Programmatic download was not successful or environment is offline.")
    print("    Please manually place 'oasis_longitudinal.csv' into:")
    print(f"    {DATA_FILE}\n")
    print("    Expected columns include:")
    print("    " + ", ".join(REQUIRED_COLUMNS))
    return False


if __name__ == "__main__":
    success = download_dataset()
    sys.exit(0 if success else 1)

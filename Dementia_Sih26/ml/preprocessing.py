"""
ml/preprocessing.py
===================
Data loading, cleaning, target definition, and leakage-safe preprocessing
for the OASIS longitudinal dataset.

Key Scientific & Leakage Safety Design Decisions:
1. Target Variable Definition:
   - "Nondemented": 0
   - "Demented": 1
   - "Converted": Handled via 'visit_cdr' (default) or 'as_demented' / 'exclude'.
     In 'visit_cdr' mode, converted subjects' visits are assigned 1 if CDR >= 0.5 at that visit,
     and 0 if CDR == 0.0. CDR is strictly used ONLY for ground truth labeling and is NEVER
     included as an input feature in X!
2. Leakage-Safe Feature Set:
   - Input features: Age, EDUC, SES, MMSE, eTIV, nWBV, ASF, sex (M=1, F=0)
   - Excluded: CDR (target leakage), MRI ID, MR Delay, Visit, Hand
3. Subject Identifier for Stratified Group Splitting:
   - 'Subject ID' is preserved to guarantee that all visits from any given subject
     are strictly constrained to either train or test folds (zero cross-visit leakage).
"""

from __future__ import annotations

import os
from typing import Literal, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

CLINICAL_FEATURE_NAMES = [
    "Age",
    "EDUC",
    "SES",
    "MMSE",
    "eTIV",
    "nWBV",
    "ASF",
    "sex",  # 1 for Male, 0 for Female
]


def load_oasis_dataset(filepath: Optional[str] = None) -> pd.DataFrame:
    """Load the raw OASIS longitudinal CSV from default or specified path."""
    if filepath is None:
        filepath = os.path.join(os.path.dirname(__file__), "data", "oasis_longitudinal.csv")
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"OASIS dataset not found at '{filepath}'. "
            f"Please run 'python ml/download_dataset.py' to acquire the dataset."
        )
    df = pd.read_csv(filepath)
    # Strip whitespace from columns
    df.columns = [c.strip() for c in df.columns]
    return df


def prepare_clinical_dataset(
    df: pd.DataFrame,
    handle_converted: Literal["visit_cdr", "as_demented", "exclude"] = "visit_cdr",
) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Clean and structure the OASIS dataset into features X, target y, and grouping groups.

    Parameters:
        df: Raw OASIS dataframe
        handle_converted:
            - 'visit_cdr' (default): For Converted group, label=1 if CDR >= 0.5, label=0 if CDR == 0.
            - 'as_demented': Treat all visits of Converted participants as demented (label=1).
            - 'exclude': Drop Converted subjects entirely.

    Returns:
        X: DataFrame of 8 clinical input features
        y: Series of binary dementia status (1 = demented, 0 = nondemented)
        groups: Series of Subject ID for group-based cross-validation
    """
    df = df.copy()

    # Drop any records with missing Group
    df = df[df["Group"].notna()]

    # Filter or label converted subjects
    if handle_converted == "exclude":
        df = df[df["Group"].str.strip().str.lower() != "converted"]
        df["target"] = (df["Group"].str.strip().str.lower() == "demented").astype(int)
    elif handle_converted == "as_demented":
        group_clean = df["Group"].str.strip().str.lower()
        df["target"] = group_clean.isin(["demented", "converted"]).astype(int)
    elif handle_converted == "visit_cdr":
        # Ground truth label based on clinical status at this visit
        # If CDR is present: CDR >= 0.5 -> 1, CDR == 0.0 -> 0
        def assign_target(row):
            grp = str(row.get("Group", "")).strip().lower()
            if grp == "demented":
                return 1
            elif grp == "nondemented":
                return 0
            elif grp == "converted":
                cdr = row.get("CDR", 0.0)
                return 1 if (pd.notna(cdr) and float(cdr) >= 0.5) else 0
            return 0

        df["target"] = df.apply(assign_target, axis=1)
    else:
        raise ValueError(f"Unknown handle_converted strategy: {handle_converted}")

    # Encode biological sex: M -> 1, F -> 0
    if "M/F" in df.columns:
        df["sex"] = df["M/F"].astype(str).str.strip().str.upper().map({"M": 1.0, "F": 0.0})
    elif "sex" in df.columns:
        df["sex"] = df["sex"].astype(float)
    else:
        df["sex"] = 0.0

    # Ensure all clinical feature columns are numeric
    for col in CLINICAL_FEATURE_NAMES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            raise KeyError(f"Required clinical feature '{col}' missing from OASIS dataset.")

    # Guard: ensure CDR is NEVER in X
    assert "CDR" not in CLINICAL_FEATURE_NAMES, "Fatal: CDR cannot be in feature set X (target leakage)."

    X = df[CLINICAL_FEATURE_NAMES].copy()
    y = df["target"].astype(int).copy()
    groups = df["Subject ID"].astype(str).copy()

    return X, y, groups


def build_preprocessing_pipeline() -> Pipeline:
    """
    Build scikit-learn preprocessing pipeline.
    Uses median imputation for missing SES/MMSE followed by standard scaling.
    """
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

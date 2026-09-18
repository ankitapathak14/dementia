"""
NeuroAid — core/clinical_config.py
====================================
Clinical parameters for V2-sourced 4-layer scoring pipeline.
Merged into V4 (V3 architecture + V2 brain logic + ML).

Layers:
  1. Age-adjusted z-score norms (population-based)
  2. Education correction factors (cognitive reserve)
  3. Medical condition risk multipliers (clinical comorbidities)
  4. Fatigue/temporary factor confidence scoring

Source: Approximate population norms inspired by MMSE/MoCA literature.
This is NOT a diagnostic tool - screening signals only.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Union

# ── Scoring weights (must sum to 1.0) ─────────────────────────────────────────
DOMAIN_WEIGHTS = {
    "speech":    0.25,
    "memory":    0.30,
    "reaction":  0.20,
    "executive": 0.15,
    "motor":     0.10,
}

# ── Risk thresholds (probability scale 0–1) ────────────────────────────────────
THRESHOLDS = {
    "low_max":      0.35,
    "moderate_max": 0.65,
    # > 0.65 → High
}

# ── Age-bracket norms for z-score normalization ────────────────────────────────
AGE_NORMS = {
    "reaction_time": {   # ms — lower is better
        "20-39": {"mean": 280, "std": 45},
        "40-59": {"mean": 330, "std": 55},
        "60-75": {"mean": 400, "std": 70},
        "75+":   {"mean": 480, "std": 90},
    },
    "memory_accuracy": {  # % — higher is better
        "20-39": {"mean": 82, "std": 12},
        "40-59": {"mean": 75, "std": 13},
        "60-75": {"mean": 65, "std": 15},
        "75+":   {"mean": 55, "std": 18},
    },
    "wpm": {              # words per minute — higher is better
        "20-39": {"mean": 145, "std": 30},
        "40-59": {"mean": 135, "std": 30},
        "60-75": {"mean": 120, "std": 32},
        "75+":   {"mean": 105, "std": 35},
    },
}


def get_age_bracket(age: int) -> str:
    if age < 40:   return "20-39"
    elif age < 60: return "40-59"
    elif age < 75: return "60-75"
    else:          return "75+"


def age_z_score(value: float, metric: str, age: int) -> float:
    """Z = (X - μ_age) / σ_age. Positive = above peer mean (better)."""
    bracket = get_age_bracket(age)
    norms = AGE_NORMS.get(metric, {}).get(bracket)
    if not norms:
        return 0.0
    return round((value - norms["mean"]) / norms["std"], 3)


# ── Education correction (cognitive reserve) ───────────────────────────────────
# 1=No formal, 2=Primary, 3=Secondary, 4=Graduate, 5=Postgrad
EDUCATION_CORRECTION = {
    1: +0.05,
    2: +0.03,
    3:  0.00,
    4:  0.00,
    5: -0.02,
}


def get_education_correction(education_level: int) -> float:
    return EDUCATION_CORRECTION.get(education_level, 0.0)


# ── Education mapping to formal years (EDUC for clinical reference) ────────────
# Documented mapping from NeuroAid categories to estimated years of education (EDUC).
EDUCATION_YEARS_MAPPING: dict[Union[int, str], float] = {
    1: 6.0,                      # No formal / incomplete primary
    2: 8.0,                      # Primary education
    3: 12.0,                     # Secondary / High School
    4: 16.0,                     # Graduate / Bachelor's
    5: 18.0,                     # Post-graduate / Master's / Doctoral
    "no formal": 6.0,
    "primary": 8.0,
    "high school": 12.0,
    "some college": 14.0,
    "bachelor's": 16.0,
    "bachelors": 16.0,
    "master's": 18.0,
    "masters": 18.0,
    "doctoral": 20.0,
    "doctorate": 20.0,
    "professional degree": 20.0,
}


def map_education_to_years(education_value: Optional[Union[int, str]]) -> Optional[float]:
    """
    Explicitly map NeuroAid education representation to years of education (EDUC)
    for the OASIS clinical reference model.
    Returns None if the value is invalid or cannot be reliably mapped.
    DO NOT guess or multiply by arbitrary constants.
    """
    if education_value is None:
        return None
    if isinstance(education_value, int):
        return EDUCATION_YEARS_MAPPING.get(education_value)
    if isinstance(education_value, str):
        clean = education_value.strip().lower()
        if clean.isdigit():
            val = int(clean)
            if 1 <= val <= 5:
                return EDUCATION_YEARS_MAPPING.get(val)
            elif 6 <= val <= 25:
                return float(val)
        return EDUCATION_YEARS_MAPPING.get(clean)
    return None


# ── Medical condition risk multipliers (γ coefficients) ───────────────────────
CONDITION_MULTIPLIERS = {
    "diabetes":          0.04,
    "hypertension":      0.05,
    "stroke_history":    0.08,
    "family_alzheimers": 0.06,
    "parkinsons_dx":     0.10,
    "depression":        0.04,
    "thyroid_disorder":  0.03,
}

MAX_RISK_CAP = 0.95


def apply_condition_multipliers(base_risk: float, conditions: dict) -> float:
    """R_final = R × (1 + Σγ) capped at MAX_RISK_CAP."""
    gamma_sum = sum(
        CONDITION_MULTIPLIERS.get(k, 0.0)
        for k, v in conditions.items() if v
    )
    return min(base_risk * (1 + gamma_sum), MAX_RISK_CAP)


# ── Fatigue / temporary factor configuration ───────────────────────────────────
FATIGUE_FACTORS = {
    "tired":          0.10,
    "sleep_deprived": 0.12,
    "sick":           0.08,
    "anxious":        0.06,
}

FATIGUE_CONFIDENCE_THRESHOLD = 0.75


def compute_confidence_score(missing_data_ratio: float, fatigue_flags: dict) -> float:
    """Confidence = 1 - MissingDataRatio - FatiguePenalty. Range [0, 1]."""
    fatigue_penalty = sum(
        FATIGUE_FACTORS.get(k, 0.0)
        for k, v in fatigue_flags.items() if v
    )
    confidence = 1.0 - missing_data_ratio - fatigue_penalty
    return round(max(0.0, min(1.0, confidence)), 3)


# ── Safe output language ───────────────────────────────────────────────────────
SAFE_OUTPUT_LANGUAGE = {
    "disclaimer": (
        "⚠️ This is NOT a diagnosis. This tool identifies cognitive risk indicators only. "
        "Always consult a qualified neurologist or physician for clinical evaluation."
    ),
    "retest_recommendation": (
        "Results may be temporarily affected by fatigue or stress. "
        "Please retest after adequate rest for a more reliable reading."
    ),
}

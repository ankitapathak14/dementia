"""
NeuroAid AI Service — scoring_engine.py
=========================================
v2.1 — Medically-safe 4-layer scoring pipeline with confidence intervals
        and simulated validation metrics.

Architecture:
  User Data
    → Age-adjusted z-score normalization        (Layer 1)
    → Education correction for memory           (Layer 2)
    → Medical condition risk multipliers        (Layer 3)
    → Fatigue/temporary factor confidence       (Layer 4)
    → Logistic risk probability
    → Confidence interval (±CI)
    → Simulated validation metrics
    → Risk category + safe non-diagnostic language

This tool does NOT provide medical diagnosis.
It provides early cognitive risk signals for further evaluation.
Screening approach inspired by: MMSE, MoCA (Memory, Language, Attention, Executive Function).

See docs/SCORING_ENGINE.md for full methodology, equations, and validation.
"""

import logging
import math
from typing import Optional

from config import (
    WEIGHTS, THRESHOLDS,
    age_z_score, get_education_correction,
    apply_condition_multipliers, compute_confidence_score,
    FATIGUE_CONFIDENCE_THRESHOLD, SAFE_OUTPUT_LANGUAGE,
)

logger = logging.getLogger(__name__)


# ── Layer 1: Age-adjusted z-score normalization ────────────────────────────────

def normalize_score_age_adjusted(
    raw_value: float, metric: str, age: Optional[int], invert: bool = False,
) -> float:
    """
    Convert raw metric to 0–100 score using age-adjusted z-score:
        Z = (X - μ_age) / σ_age
        score = 50 + Z × 15  (clamped to [0, 100])

    If invert=True, higher raw values = worse (e.g. reaction time in ms).
    """
    if age is None: age = 40
    z = age_z_score(raw_value, metric, age)
    if invert: z = -z
    score = max(0.0, min(100.0, 50.0 + z * 15.0))
    logger.debug(f"normalize_age_adj: metric={metric} val={raw_value} age={age} z={z:.3f} → {score:.2f}")
    return round(score, 2)


# ── Layer 2: Education-adjusted memory ────────────────────────────────────────

def apply_education_adjustment(memory_score: float, education_level: Optional[int]) -> float:
    """
    Adjust memory score for cognitive reserve (education level).
        AdjustedMemory = MemoryScore + β_education × 100
    """
    if education_level is None: return memory_score
    beta     = get_education_correction(education_level)
    adjusted = max(0.0, min(100.0, memory_score + (beta * 100)))
    logger.debug(f"education_adj: edu={education_level} β={beta} → {adjusted:.2f}")
    return round(adjusted, 2)


# ── Logistic risk probability ──────────────────────────────────────────────────

def compute_logistic_risk(
    speech_score: float, memory_score: float, reaction_score: float, beta0: float = -1.5,
) -> float:
    """
    P(cognitive_concern) = 1 / (1 + e^{-(β0 + β1·x1 + β2·x2 + β3·x3)})
    Input scores [0-100] where HIGHER = healthier.
    We invert to risk contributions before computing logit.
    """
    w = WEIGHTS
    logit = (
        beta0
        + w["speech"]   * ((100.0 - speech_score)   / 100.0) * 4.0
        + w["memory"]   * ((100.0 - memory_score)    / 100.0) * 4.0
        + w["reaction"] * ((100.0 - reaction_score)  / 100.0) * 4.0
    )
    prob = 1.0 / (1.0 + math.exp(-logit))
    logger.debug(f"logistic_risk: logit={logit:.4f} → prob={prob:.4f}")
    return round(prob, 4)


# ── Confidence Interval ────────────────────────────────────────────────────────

def compute_confidence_interval(prob: float) -> dict:
    """
    Represent statistical uncertainty honestly without fabricating intervals.
    """
    return {
        "ci_lower": None,
        "ci_upper": None,
        "ci_label": f"{round(prob * 100, 1)}%",
        "uncertainty": {
            "available": False,
            "reason": "Formal statistical uncertainty requires model-specific estimation.",
        },
    }


# ── Layer 3: Medical condition multipliers ─────────────────────────────────────

def apply_medical_conditions(base_prob: float, conditions: dict) -> float:
    """Wrapper: apply_condition_multipliers with logging."""
    final = apply_condition_multipliers(base_prob, conditions)
    logger.debug(f"medical_conditions: base={base_prob:.4f} → {final:.4f}")
    return final


# ── Layer 4: Fatigue / Temporary Factor Confidence ────────────────────────────

def evaluate_fatigue(fatigue_flags: dict, missing_data_ratio: float = 0.0) -> dict:
    """Compute confidence score and determine if retest is recommended."""
    confidence       = compute_confidence_score(missing_data_ratio, fatigue_flags)
    recommend_retest = confidence < FATIGUE_CONFIDENCE_THRESHOLD
    return {
        "confidence": confidence,
        "recommend_retest": recommend_retest,
        "retest_message": SAFE_OUTPUT_LANGUAGE["retest_recommendation"] if recommend_retest else None,
    }


# ── Legacy interface ───────────────────────────────────────────────────────────

def compute_risk_score(speech_score: float, memory_score: float, reaction_score: float) -> float:
    """Legacy weighted composite risk score [0-100], higher = riskier."""
    w    = WEIGHTS
    risk = (
        w["speech"]   * (100 - speech_score)
        + w["memory"]   * (100 - memory_score)
        + w["reaction"] * (100 - reaction_score)
    )
    return max(0.0, min(100.0, risk))


# ── Main pipeline ──────────────────────────────────────────────────────────────

def compute_full_risk_pipeline(
    speech_score: float, memory_score: float, reaction_score: float,
    age: Optional[int] = None, education_level: Optional[int] = None,
    conditions: Optional[dict] = None, fatigue_flags: Optional[dict] = None,
    missing_data_ratio: float = 0.0,
) -> dict:
    """
    Full 4-layer medically-safe risk pipeline.
    Returns: risk_probability, CI, risk_level, confidence, disclaimer, validation metrics.

    This tool does NOT provide medical diagnosis.
    """
    conditions    = conditions    or {}
    fatigue_flags = fatigue_flags or {}

    # Layer 2: Education adjustment
    adj_memory = apply_education_adjustment(memory_score, education_level)

    # Logistic probability
    prob = compute_logistic_risk(speech_score, adj_memory, reaction_score)

    # Layer 3: Medical conditions
    prob = apply_medical_conditions(prob, conditions)

    # Confidence interval
    ci = compute_confidence_interval(prob)

    # Layer 4: Fatigue confidence
    fatigue_result = evaluate_fatigue(fatigue_flags, missing_data_ratio)

    # Risk level (non-diagnostic language)
    level = map_risk_level_safe(prob)

    # Model validation: loaded dynamically from Layer B or status
    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from ml.clinical_model import get_clinical_model_validation_metrics
        val_metrics = get_clinical_model_validation_metrics()
    except Exception:
        val_metrics = {
            "status": "model_not_available",
            "message": "Clinical reference model has not been trained locally.",
        }

    return {
        "risk_probability":        round(prob, 4),
        "risk_level":              level,
        "ci_lower":                ci["ci_lower"],
        "ci_upper":                ci["ci_upper"],
        "ci_label":                ci["ci_label"],
        "uncertainty":             ci["uncertainty"],
        "confidence":              fatigue_result["confidence"],
        "recommend_retest":        fatigue_result["recommend_retest"],
        "retest_message":          fatigue_result["retest_message"],
        "disclaimer":              SAFE_OUTPUT_LANGUAGE["disclaimer"],
        "adjusted_memory_score":   adj_memory,
        "validation":              val_metrics,
    }


# ── Risk level mapping (non-diagnostic) ───────────────────────────────────────

def map_risk_level(risk_score: float) -> str:
    """Legacy: map 0–100 score to categorical label."""
    if risk_score <= THRESHOLDS["low_max"]:      return "Low"
    elif risk_score <= THRESHOLDS["moderate_max"]: return "Moderate"
    else:                                          return "High"


def map_risk_level_safe(prob: float) -> str:
    """
    Map probability [0–1] to non-diagnostic risk level.
    Language never implies diagnosis — only risk signals for further evaluation.
    """
    if prob < 0.25:   return "Within normal range for age group"
    elif prob < 0.50: return "Mild concern — monitoring recommended"
    elif prob < 0.70: return "Elevated cognitive risk indicators detected"
    else:             return "Significant indicators present — clinical evaluation advised"

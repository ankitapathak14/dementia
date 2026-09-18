"""
NeuroAid — core/behavioral_ml.py
==================================
Layer A: Behavioral Anomaly Detection Engine

Uses scikit-learn's IsolationForest to evaluate deviations across NeuroAid's
canonical 18-feature cognitive behavioral vector.

Safety and Clinical Intent:
- This is a non-diagnostic behavioral screening signal ("Cognitive Performance Deviation").
- Never claims medical diagnosis (e.g., Alzheimer's, Dementia, Parkinson's).
- Requires a longitudinal history of prior sessions (min_history >= 3) to establish
  the patient's personal baseline before declaring an anomaly.
- If insufficient history exists, returns status="insufficient_history" with no fabricated alerts.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

# Canonical 18 behavioral features (strictly preserved, no additions)
FEATURE_NAMES: List[str] = [
    # Speech (5)
    "wpm",
    "speed_deviation",
    "speech_variability",
    "pause_ratio",
    "speech_start_delay",
    # Memory (5)
    "immediate_recall_accuracy",
    "delayed_recall_accuracy",
    "intrusion_count",
    "recall_latency",
    "order_match_ratio",
    # Reaction (5)
    "mean_rt",
    "std_rt",
    "min_rt",
    "reaction_drift",
    "miss_count",
    # Executive (2)
    "stroop_error_rate",
    "stroop_rt",
    # Motor (1)
    "tap_interval_std",
]

# Standard reference scales for normalizing 18 features into roughly comparable magnitudes [0, 1]
# Note: This is an affine scaling for stable numerical conditioning of distance-based estimators.
FEATURE_NORMALIZATION_SCALES: Dict[str, Tuple[float, float]] = {
    "wpm": (0.0, 200.0),
    "speed_deviation": (0.0, 50.0),
    "speech_variability": (0.0, 30.0),
    "pause_ratio": (0.0, 1.0),
    "speech_start_delay": (0.0, 5.0),
    "immediate_recall_accuracy": (0.0, 100.0),
    "delayed_recall_accuracy": (0.0, 100.0),
    "intrusion_count": (0.0, 10.0),
    "recall_latency": (0.0, 15.0),
    "order_match_ratio": (0.0, 1.0),
    "mean_rt": (150.0, 1200.0),
    "std_rt": (0.0, 300.0),
    "min_rt": (100.0, 800.0),
    "reaction_drift": (-100.0, 300.0),
    "miss_count": (0.0, 10.0),
    "stroop_error_rate": (0.0, 1.0),
    "stroop_rt": (300.0, 1500.0),
    "tap_interval_std": (0.0, 200.0),
}


def normalize_feature_vector(raw_features: Union[Dict[str, Any], Any]) -> np.ndarray:
    """
    Extract and scale the 18 canonical features into a 1D numpy array.
    Accepts dict or object with feature attributes.
    Missing features are imputed with domain medians/defaults.
    """
    vector = np.zeros(len(FEATURE_NAMES), dtype=np.float64)
    for idx, name in enumerate(FEATURE_NAMES):
        if isinstance(raw_features, dict):
            val = raw_features.get(name)
        else:
            val = getattr(raw_features, name, None)

        if val is None:
            # Domain sensible median fallbacks if key missing
            min_val, max_val = FEATURE_NORMALIZATION_SCALES[name]
            val = (min_val + max_val) / 2.0

        try:
            val_float = float(val)
        except (ValueError, TypeError):
            min_val, max_val = FEATURE_NORMALIZATION_SCALES[name]
            val_float = (min_val + max_val) / 2.0

        min_val, max_val = FEATURE_NORMALIZATION_SCALES[name]
        denom = max_val - min_val if max_val > min_val else 1.0
        scaled = (val_float - min_val) / denom
        vector[idx] = float(np.clip(scaled, 0.0, 2.0))  # allow mild headroom without unbounded explosion
    return vector


def extract_raw_vector_dict(raw_features: Union[Dict[str, Any], Any]) -> Dict[str, float]:
    """Extract raw 18-feature dictionary with sensible fallbacks for any missing attributes."""
    out: Dict[str, float] = {}
    for name in FEATURE_NAMES:
        if isinstance(raw_features, dict):
            val = raw_features.get(name)
        else:
            val = getattr(raw_features, name, None)

        if val is None:
            min_val, max_val = FEATURE_NORMALIZATION_SCALES[name]
            val = (min_val + max_val) / 2.0
        try:
            out[name] = float(val)
        except (ValueError, TypeError):
            min_val, max_val = FEATURE_NORMALIZATION_SCALES[name]
            out[name] = float((min_val + max_val) / 2.0)
    return out


def evaluate_behavioral_anomaly(
    current_features: Union[Dict[str, Any], Any],
    historical_sessions: List[Union[Dict[str, Any], Any]],
    min_history: int = 3,
) -> Dict[str, Any]:
    """
    Evaluate cognitive performance deviation using IsolationForest on patient history.

    Parameters:
        current_features: 18-feature dictionary or Pydantic model for current session.
        historical_sessions: List of prior feature vectors from the same patient.
        min_history: Minimum number of historical sessions required (default 3).

    Returns:
        status: "sufficient_history" | "insufficient_history"
        anomaly_detected: bool
        severity: "none" | "mild" | "significant" | "severe"
        anomaly_score: float in [0.0, 1.0] (higher = more anomalous) or None
        top_deviating_features: List of {feature, baseline_mean, baseline_std, current_value, z_score, direction}
        baseline_comparison: Dict[feature, {mean, std, current}]
        terminology: "Cognitive Performance Deviation"
    """
    raw_current = extract_raw_vector_dict(current_features)
    norm_current = normalize_feature_vector(current_features)

    # 1. Check history guard
    if len(historical_sessions) < min_history:
        return {
            "status": "insufficient_history",
            "anomaly_detected": False,
            "severity": "none",
            "anomaly_score": None,
            "session_count": len(historical_sessions),
            "min_history_required": min_history,
            "top_deviating_features": [],
            "baseline_comparison": {},
            "terminology": "Cognitive Performance Deviation",
            "message": (
                f"Establishing baseline requires at least {min_history} completed sessions "
                f"({len(historical_sessions)} available). No anomaly evaluation performed."
            ),
        }

    # 2. Extract and normalize historical sessions
    hist_raw_list = [extract_raw_vector_dict(h) for h in historical_sessions]
    hist_norm_matrix = np.array([normalize_feature_vector(h) for h in historical_sessions])

    # 3. Fit IsolationForest on historical data
    from sklearn.ensemble import IsolationForest

    # Use small contamination proportion reflecting screening anomaly assumptions
    iso_forest = IsolationForest(
        n_estimators=100,
        contamination=0.1,
        random_state=42,
    )
    iso_forest.fit(hist_norm_matrix)

    # decision_function: positive = normal, negative = anomaly
    # Lower score means more anomalous
    raw_score = float(iso_forest.decision_function(norm_current.reshape(1, -1))[0])
    is_outlier = bool(iso_forest.predict(norm_current.reshape(1, -1))[0] == -1)

    # Transform decision function to continuous anomaly index in [0, 1]
    # Decision function roughly lies in [-0.5, 0.5]
    # Anomaly index = 1 / (1 + exp(8 * decision_score))
    anomaly_index = float(1.0 / (1.0 + math.exp(6.0 * raw_score)))
    anomaly_index = round(max(0.0, min(1.0, anomaly_index)), 4)

    # 4. Compute personal baseline per feature
    baseline_comp: Dict[str, Dict[str, float]] = {}
    deviations: List[Dict[str, Any]] = []

    for name in FEATURE_NAMES:
        values = [h[name] for h in hist_raw_list]
        b_mean = float(np.mean(values))
        b_std = float(np.std(values))
        # Protect against zero variance in flat history
        effective_std = b_std if b_std > 1e-4 else (0.1 * abs(b_mean) if abs(b_mean) > 1e-4 else 1.0)

        curr_val = raw_current[name]
        z = (curr_val - b_mean) / effective_std

        baseline_comp[name] = {
            "baseline_mean": round(b_mean, 2),
            "baseline_std": round(b_std, 2),
            "current_value": round(curr_val, 2),
            "z_score": round(z, 2),
        }

        # Check if deviation signifies performance decline:
        # For accuracy/wpm: decrease is decline (z < 0)
        # For latency/errors/variability/drift: increase is decline (z > 0)
        is_adverse = False
        if name in ["immediate_recall_accuracy", "delayed_recall_accuracy", "order_match_ratio", "wpm"]:
            if z < -1.0:
                is_adverse = True
        else:
            if z > 1.0:
                is_adverse = True

        deviations.append({
            "feature": name,
            "baseline_mean": round(b_mean, 2),
            "baseline_std": round(b_std, 2),
            "current_value": round(curr_val, 2),
            "z_score": round(z, 2),
            "abs_z": abs(z),
            "direction": "lower" if z < 0 else "higher",
            "is_adverse_deviation": is_adverse,
        })

    # Sort deviations by absolute z-score descending
    deviations.sort(key=lambda x: x["abs_z"], reverse=True)
    top_deviations = [
        {
            "feature": d["feature"],
            "baseline_mean": d["baseline_mean"],
            "baseline_std": d["baseline_std"],
            "current_value": d["current_value"],
            "z_score": d["z_score"],
            "direction": d["direction"],
            "is_adverse": d["is_adverse_deviation"],
        }
        for d in deviations[:5]
    ]

    # 5. Determine severity safely and non-diagnostically
    max_adverse_z = max([d["abs_z"] for d in deviations if d["is_adverse_deviation"]], default=0.0)

    # A cognitive performance deviation requires adverse deviation from baseline.
    # If scores are within normal baseline variation (max_adverse_z < 1.5), it is not an anomaly.
    if max_adverse_z < 1.5 and not (is_outlier and max_adverse_z >= 1.2):
        severity = "none"
        anomaly_detected = False
    elif (is_outlier and anomaly_index >= 0.75) or max_adverse_z >= 3.0:
        severity = "severe"
        anomaly_detected = True
    elif (is_outlier and anomaly_index >= 0.60) or max_adverse_z >= 2.2:
        severity = "significant"
        anomaly_detected = True
    elif max_adverse_z >= 1.5 or (is_outlier and max_adverse_z >= 1.2):
        severity = "mild"
        anomaly_detected = True
    else:
        severity = "none"
        anomaly_detected = False

    return {
        "status": "sufficient_history",
        "anomaly_detected": anomaly_detected,
        "severity": severity,
        "anomaly_score": anomaly_index,
        "raw_decision_score": round(raw_score, 4),
        "session_count": len(historical_sessions),
        "top_deviating_features": top_deviations,
        "baseline_comparison": baseline_comp,
        "terminology": "Cognitive Performance Deviation",
        "message": (
            f"Cognitive performance deviation severity: {severity} "
            f"(evaluated against personal {len(historical_sessions)}-session historical baseline)."
        ),
    }

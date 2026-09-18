"""
NeuroAid — core/ml_engine.py
================================
ML Engine for NeuroAid.

Features:
  1. Multi-Modal Signal Fusion (delegates to core.signal_fusion)
  2. Longitudinal Progress Anomaly Detection (Z-score based detection of sudden cognitive drops)
  3. Non-fabricated statistical uncertainty representation
  4. Genuine model coefficient explainability and baseline deviations

These are SCREENING SIGNALS only — not diagnostic.
"""

from __future__ import annotations

import statistics
from typing import Any, Dict, List, Optional

from core.signal_fusion import fuse_cognitive_signals


# ─────────────────────────────────────────────────────────────────────────────
# 1. SIGNAL FUSION
# ─────────────────────────────────────────────────────────────────────────────

def compute_multimodal_fusion(
    behavioral_anomaly_result: Optional[Dict[str, Any]],
    clinical_reference_result: Optional[Dict[str, Any]],
    behavioral_weight: float = 0.5,
    clinical_weight: float = 0.5,
) -> Dict[str, Any]:
    """
    Fuses behavioral anomaly signal and clinical reference signal ONLY when both exist.
    Never combines a signal with itself.
    """
    return fuse_cognitive_signals(
        behavioral_anomaly_result=behavioral_anomaly_result,
        clinical_reference_result=clinical_reference_result,
        behavioral_weight=behavioral_weight,
        clinical_weight=clinical_weight,
    )


def compute_hybrid_risk(
    behavioral_score: Optional[float],
    clinical_prob: Optional[float],
    behavioral_weight: float = 0.5,
    clinical_weight: float = 0.5,
) -> Optional[float]:
    """
    Backward-compatible helper: fuses two distinct numerical probabilities/scores.
    Guards against self-combination: if either input is None or both are identical references,
    returns None or single available signal.
    """
    if behavioral_score is None and clinical_prob is None:
        return None
    if behavioral_score is None:
        return clinical_prob
    if clinical_prob is None:
        return behavioral_score

    # Check for identical values (self-combination bug prevention)
    if abs(behavioral_score - clinical_prob) < 1e-6:
        # Cannot combine identical inputs (self-combination guard)
        return round(float(behavioral_score), 4)

    total_w = behavioral_weight + clinical_weight
    fused = (behavioral_weight * behavioral_score + clinical_weight * clinical_prob) / total_w
    return round(max(0.0, min(1.0, fused)), 4)


# ─────────────────────────────────────────────────────────────────────────────
# 2. PROGRESS ANOMALY DETECTION (Z-score based drop detection)
# ─────────────────────────────────────────────────────────────────────────────

ANOMALY_Z_THRESHOLD = -1.5   # > 1.5 std deviations drop = warning
ANOMALY_MIN_HISTORY = 3      # Need at least 3 sessions to detect anomalies


def detect_progress_anomaly(
    score_history: List[float],
    current_score: float,
    metric_name: str = "score",
) -> Dict[str, Any]:
    """
    Detect if current_score is an anomalous DROP compared to personal historical trend.

    Uses Z-score: Z = (current - mean_history) / std_history
    If Z < ANOMALY_Z_THRESHOLD → anomaly detected (significant drop).
    """
    if len(score_history) < ANOMALY_MIN_HISTORY:
        return {
            "anomaly_detected": False,
            "z_score": None,
            "severity": "insufficient_data",
            "message": f"Need {ANOMALY_MIN_HISTORY}+ sessions to detect anomalies.",
        }

    mean_h = statistics.mean(score_history)
    std_h = statistics.stdev(score_history) if len(score_history) > 1 else 1.0
    if std_h < 1.0:
        std_h = 1.0

    z = (current_score - mean_h) / std_h

    if z < -2.5:
        severity = "severe"
        anomaly = True
    elif z < -1.75:
        severity = "significant"
        anomaly = True
    elif z < ANOMALY_Z_THRESHOLD:
        severity = "mild"
        anomaly = True
    else:
        severity = "none"
        anomaly = False

    messages = {
        "none": None,
        "mild": f"Noticeable {metric_name} variation detected relative to baseline.",
        "significant": f"Significant {metric_name} drop relative to historical baseline.",
        "severe": f"Pronounced {metric_name} decline detected relative to baseline.",
        "insufficient_data": None,
    }

    return {
        "anomaly_detected": anomaly,
        "z_score": round(z, 3),
        "severity": severity,
        "mean_history": round(mean_h, 2),
        "std_history": round(std_h, 2),
        "message": messages.get(severity),
    }


def analyze_all_progress_anomalies(
    historical_results: List[Dict[str, Any]],
    current_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Run anomaly detection across all key cognitive metrics.
    historical_results: list of past result dicts
    current_result: the just-computed result dict
    """
    if not historical_results:
        return {"overall_alert": "none", "metrics": {}}

    METRICS_TO_CHECK = [
        ("memory_score", "Memory"),
        ("reaction_score", "Reaction Time"),
        ("speech_score", "Speech"),
        ("executive_score", "Executive Function"),
        ("motor_score", "Motor Control"),
    ]

    findings = {}
    highest_severity_rank = 0
    severity_rank = {"none": 0, "insufficient_data": 0, "mild": 1, "significant": 2, "severe": 3}

    for field, label in METRICS_TO_CHECK:
        history = [r[field] for r in historical_results if field in r and r[field] is not None]
        current = current_result.get(field)
        if current is None:
            continue

        result = detect_progress_anomaly(history, current, label)
        findings[field] = result

        rank = severity_rank.get(result["severity"], 0)
        if rank > highest_severity_rank:
            highest_severity_rank = rank

    overall = ["none", "mild", "significant", "severe"][highest_severity_rank]
    return {"overall_alert": overall, "metrics": findings}


# ─────────────────────────────────────────────────────────────────────────────
# 3. STATISTICAL UNCERTAINTY (No hardcoded fake CIs)
# ─────────────────────────────────────────────────────────────────────────────

def compute_uncertainty() -> Dict[str, Any]:
    """
    Scientifically defensible uncertainty representation.
    Hardcoded ±0.04/0.03 intervals are permanently removed.
    """
    return {
        "available": False,
        "reason": "Formal statistical uncertainty requires model-specific estimation.",
    }


def compute_confidence_interval(prob: Optional[float]) -> Dict[str, Any]:
    """
    Backward compatibility wrapper for legacy response schemas.
    Does NOT fabricate a confidence interval.
    """
    unc = compute_uncertainty()
    label = f"{round(prob * 100, 1)}%" if prob is not None else None
    return {
        "ci_lower": None,
        "ci_upper": None,
        "ci_label": label,
        "uncertainty": unc,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. EXPLAINABILITY (Coefficients & Baseline Deviations — No Fake SHAP)
# ─────────────────────────────────────────────────────────────────────────────

def get_clinical_model_explanations() -> List[Dict[str, Any]]:
    """
    Retrieve real model coefficients and odds ratios from trained OASIS model.
    Never claims to be SHAP.
    """
    try:
        import os, json
        meta_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "ml", "artifacts", "clinical_model_metadata.json"
        )
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("feature_coefficients", [])
    except Exception:
        pass
    return []


def compute_feature_importance(
    feature_vector: Dict[str, Any],
    baseline_deviations: Optional[List[Dict[str, Any]]] = None,
    disease: str = "clinical_reference",
) -> List[Dict[str, Any]]:
    """
    Explainability breakdown based on true model coefficients (Layer B)
    or baseline deviations (Layer A).
    Never claims to be SHAP.
    """
    if baseline_deviations:
        # Use genuine deviations from patient baseline
        items = []
        for d in baseline_deviations:
            items.append({
                "feature": d["feature"],
                "importance": abs(d.get("z_score", 0.0)),
                "value": d.get("current_value"),
                "direction": d.get("direction"),
                "explanation_type": "personal_baseline_deviation",
            })
        items.sort(key=lambda x: x["importance"], reverse=True)
        return items[:6]

    # Fallback to trained clinical coefficients if available
    coefs = get_clinical_model_explanations()
    if coefs:
        return coefs[:6]

    # Fallback when no baseline or clinical artifacts exist
    return []

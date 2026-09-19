"""
NeuroAid — core/signal_fusion.py
==================================
Multi-Modal Cognitive Signal Fusion Layer

Combines independent signals ONLY when both modalities are genuinely available:
- Signal 1: Behavioral Anomaly Signal (Layer A, IsolationForest on 18 cognitive features)
- Signal 2: Clinical Reference Signal (Layer B, OASIS-trained Logistic Regression)

Safety & Semantic Principles:
- NEVER interprets behavioral anomaly scores as dementia probabilities.
- NEVER combines a signal with itself.
- If both modalities are available, weighted fusion is retained ONLY as an operational
  heuristic attention indicator ("heuristic_multimodal_attention_score").
- NEVER calls the combined output a "dementia probability", "Alzheimer's probability",
  or "clinical risk probability".
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def fuse_cognitive_signals(
    behavioral_anomaly_result: Optional[Dict[str, Any]],
    clinical_reference_result: Optional[Dict[str, Any]],
    behavioral_weight: float = 0.5,
    clinical_weight: float = 0.5,
) -> Dict[str, Any]:
    """
    Fuses behavioral deviation and clinical reference signals into an operational attention indicator.

    Returns:
        behavioral_deviation:
            score: Optional[float]
            severity: str ("none" | "mild" | "significant" | "severe")
            status: str
            anomaly_detected: bool
            top_deviating_features: list
        clinical_reference:
            probability: Optional[float]
            risk_band: Optional[str] ("Low" | "Moderate" | "High" | None)
            status: str ("available" | "insufficient_input" | "model_not_available")
            missing_features: list
            explanations: list
        overall_attention:
            available: bool
            label: Optional[str]
            method: str
            heuristic_multimodal_attention_score: Optional[float]
    """
    has_behavioral = False
    beh_score: Optional[float] = None
    b_status = "insufficient_history"
    b_severity = "none"
    anomaly_detected = False
    top_deviations = []

    if behavioral_anomaly_result:
        b_status = behavioral_anomaly_result.get("status", "insufficient_history")
        b_severity = behavioral_anomaly_result.get("severity", "none")
        anomaly_detected = behavioral_anomaly_result.get("anomaly_detected", False)
        top_deviations = behavioral_anomaly_result.get("top_deviating_features", [])
        if b_status in ["preliminary_baseline", "longitudinal_baseline"] and behavioral_anomaly_result.get("anomaly_score") is not None:
            has_behavioral = True
            beh_score = float(behavioral_anomaly_result["anomaly_score"])

    behavioral_deviation = {
        "score": beh_score,
        "severity": b_severity,
        "status": b_status,
        "anomaly_detected": anomaly_detected,
        "top_deviating_features": top_deviations,
    }

    has_clinical = False
    clin_prob: Optional[float] = None
    clin_status = "insufficient_input"
    clin_risk_band: Optional[str] = None
    missing_features = []
    provided_features = []
    explanations = []

    if clinical_reference_result:
        clin_status = clinical_reference_result.get("status", "insufficient_input")
        missing_features = clinical_reference_result.get("missing_features", [])
        provided_features = clinical_reference_result.get("provided_features", [])
        explanations = clinical_reference_result.get("explanations", [])
        if clin_status == "available" and clinical_reference_result.get("probability") is not None:
            has_clinical = True
            clin_prob = float(clinical_reference_result["probability"])
            clin_risk_band = clinical_reference_result.get("risk_band")

    clinical_reference = {
        "status": clin_status,
        "probability": clin_prob,
        "risk_band": clin_risk_band,
        "model": "OASIS_LogisticRegression",
        "missing_features": missing_features,
        "provided_features": provided_features,
        "explanations": explanations,
    }

    # Signal fusion: only when BOTH independent modalities are genuinely present
    if has_behavioral and has_clinical and beh_score is not None and clin_prob is not None:
        norm_w_beh = behavioral_weight / (behavioral_weight + clinical_weight)
        norm_w_clin = clinical_weight / (behavioral_weight + clinical_weight)
        attention_score = round((norm_w_beh * beh_score) + (norm_w_clin * clin_prob), 4)

        if attention_score < 0.35:
            label = "Routine Cognitive Monitoring"
        elif attention_score < 0.65:
            label = "Moderate Attention Priority"
        else:
            label = "Elevated Attention Priority"

        overall_attention = {
            "available": True,
            "label": label,
            "method": "heuristic_multimodal_attention_score",
            "heuristic_multimodal_attention_score": attention_score,
            "components": {
                "behavioral_deviation_score": beh_score,
                "clinical_reference_probability": clin_prob,
            },
            "disclaimer": (
                "This heuristic attention score is an operational monitoring metric combining behavioral "
                "performance deviation with clinical reference cohort probability. It is NOT a clinical diagnosis, "
                "dementia probability, Alzheimer's probability, or medical risk probability."
            ),
        }

    elif has_behavioral and beh_score is not None:
        overall_attention = {
            "available": False,
            "label": None,
            "method": "None (Awaiting complete clinical reference feature inputs)",
            "heuristic_multimodal_attention_score": None,
            "components": {
                "behavioral_deviation_score": beh_score,
                "clinical_reference_probability": None,
            },
            "disclaimer": "Behavioral deviation only. Clinical reference inputs incomplete.",
        }

    elif has_clinical and clin_prob is not None:
        overall_attention = {
            "available": False,
            "label": None,
            "method": "None (Awaiting sufficient behavioral baseline history)",
            "heuristic_multimodal_attention_score": None,
            "components": {
                "behavioral_deviation_score": None,
                "clinical_reference_probability": clin_prob,
            },
            "disclaimer": "Clinical reference only. Longitudinal behavioral baseline not established.",
        }

    else:
        overall_attention = {
            "available": False,
            "label": None,
            "method": "None (Insufficient data across both modalities)",
            "heuristic_multimodal_attention_score": None,
            "components": {
                "behavioral_deviation_score": None,
                "clinical_reference_probability": None,
            },
            "disclaimer": "Both behavioral history and clinical reference inputs are incomplete.",
        }

    return {
        # Task 5 canonical semantics
        "behavioral_deviation": behavioral_deviation,
        "clinical_reference": clinical_reference,
        "overall_attention": overall_attention,
        # Backwards-compatible aliases
        "behavioral_signal": behavioral_deviation,
        "clinical_reference_signal": clinical_reference,
        "combined_indicator": {
            "available": overall_attention["available"],
            "value": overall_attention["heuristic_multimodal_attention_score"],
            "label": overall_attention["label"],
            "fusion_method": overall_attention["method"],
            "heuristic_multimodal_attention_score": overall_attention["heuristic_multimodal_attention_score"],
        },
        "fusion_method": overall_attention["method"],
    }

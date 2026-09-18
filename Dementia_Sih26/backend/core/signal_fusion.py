"""
NeuroAid — core/signal_fusion.py
==================================
Multi-Modal Cognitive Signal Fusion Layer

Combines independent signals ONLY when both modalities are available:
- Signal 1: Behavioral Anomaly Signal (Layer A, IsolationForest on 18 cognitive features)
- Signal 2: Clinical Reference Signal (Layer B, OASIS-trained Logistic Regression)

Safety Principles:
- NEVER combines a signal with itself.
- If only behavioral data exists -> returns behavioral results only.
- If only clinical data exists -> returns clinical results only.
- If both exist -> combines via documented weighted linear fusion.
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
    Combines behavioral performance anomaly and clinical reference signals.

    Parameters:
        behavioral_anomaly_result: Output from evaluate_behavioral_anomaly()
        clinical_reference_result: Output from predict_clinical_reference()
        behavioral_weight: Weight assigned to behavioral anomaly score (default 0.5)
        clinical_weight: Weight assigned to clinical reference probability (default 0.5)

    Returns:
        Dict containing:
            behavioral_signal: Optional dict with status, score, severity
            clinical_reference_signal: Optional dict with status, probability, risk_band
            combined_indicator: Dict with available (bool), value (float or None), label, method
            fusion_method: str describing fusion protocol
    """
    has_behavioral = False
    beh_score: Optional[float] = None
    beh_summary = None

    if behavioral_anomaly_result:
        b_status = behavioral_anomaly_result.get("status")
        if b_status == "sufficient_history" and behavioral_anomaly_result.get("anomaly_score") is not None:
            has_behavioral = True
            beh_score = float(behavioral_anomaly_result["anomaly_score"])
        beh_summary = {
            "status": b_status,
            "anomaly_detected": behavioral_anomaly_result.get("anomaly_detected", False),
            "severity": behavioral_anomaly_result.get("severity", "none"),
            "anomaly_score": beh_score,
            "top_deviating_features": behavioral_anomaly_result.get("top_deviating_features", []),
        }

    has_clinical = False
    clin_prob: Optional[float] = None
    clin_summary = None

    if clinical_reference_result:
        c_status = clinical_reference_result.get("status")
        if c_status == "available" and clinical_reference_result.get("probability") is not None:
            has_clinical = True
            clin_prob = float(clinical_reference_result["probability"])
        clin_summary = {
            "status": c_status,
            "model": clinical_reference_result.get("model", "OASIS_LogisticRegression"),
            "probability": clin_prob,
            "risk_band": clinical_reference_result.get("risk_band"),
            "explanations": clinical_reference_result.get("explanations", []),
        }

    # Signal fusion logic
    if has_behavioral and has_clinical and beh_score is not None and clin_prob is not None:
        # Both independent signals are present
        norm_w_beh = behavioral_weight / (behavioral_weight + clinical_weight)
        norm_w_clin = clinical_weight / (behavioral_weight + clinical_weight)
        combined_val = (norm_w_beh * beh_score) + (norm_w_clin * clin_prob)
        combined_val = round(max(0.0, min(1.0, combined_val)), 4)

        if combined_val < 0.35:
            label = "Low Risk Indicator"
        elif combined_val < 0.65:
            label = "Moderate Risk Indicator"
        else:
            label = "Elevated Risk Indicator"

        combined_indicator = {
            "available": True,
            "value": combined_val,
            "label": label,
            "fusion_method": f"WeightedLinearCombination({norm_w_beh:.2f}*Behavioral + {norm_w_clin:.2f}*Clinical)",
            "components": {
                "behavioral_anomaly_score": beh_score,
                "clinical_reference_prob": clin_prob,
            },
        }
        fusion_method = "Multi-Modal Weighted Linear Fusion"

    elif has_behavioral and beh_score is not None:
        # Behavioral only
        combined_indicator = {
            "available": False,
            "value": None,
            "label": None,
            "fusion_method": "None (Awaiting clinical reference inputs for multi-modal fusion)",
            "components": {
                "behavioral_anomaly_score": beh_score,
                "clinical_reference_prob": None,
            },
        }
        fusion_method = "Behavioral Modality Only"

    elif has_clinical and clin_prob is not None:
        # Clinical only
        combined_indicator = {
            "available": False,
            "value": None,
            "label": None,
            "fusion_method": "None (Awaiting sufficient behavioral baseline history for multi-modal fusion)",
            "components": {
                "behavioral_anomaly_score": None,
                "clinical_reference_prob": clin_prob,
            },
        }
        fusion_method = "Clinical Modality Only"

    else:
        # Neither signal available
        combined_indicator = {
            "available": False,
            "value": None,
            "label": None,
            "fusion_method": "None (Insufficient data across both modalities)",
            "components": {
                "behavioral_anomaly_score": None,
                "clinical_reference_prob": None,
            },
        }
        fusion_method = "Insufficient Modalities"

    return {
        "behavioral_signal": beh_summary,
        "clinical_reference_signal": clin_summary,
        "combined_indicator": combined_indicator,
        "fusion_method": fusion_method,
    }

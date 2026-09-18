"""
ml/clinical_model.py
====================
Layer B: Clinical Reference Model Inference and Explainability.

Provides non-diagnostic risk screening based on the OASIS-trained
logistic regression reference model.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

try:
    from ml.preprocessing import CLINICAL_FEATURE_NAMES
except ImportError:
    from preprocessing import CLINICAL_FEATURE_NAMES

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
PIPELINE_PATH = os.path.join(ARTIFACTS_DIR, "clinical_logistic_pipeline.joblib")
METADATA_PATH = os.path.join(ARTIFACTS_DIR, "clinical_model_metadata.json")

_cached_pipeline = None
_cached_metadata = None


def is_model_available() -> bool:
    """Check if trained clinical reference model artifacts exist."""
    return os.path.exists(PIPELINE_PATH) and os.path.exists(METADATA_PATH)


def load_model_artifacts() -> Tuple[Optional[Any], Optional[Dict[str, Any]]]:
    """Load and cache the trained joblib pipeline and metadata JSON."""
    global _cached_pipeline, _cached_metadata
    if _cached_pipeline is not None and _cached_metadata is not None:
        return _cached_pipeline, _cached_metadata

    if not is_model_available():
        return None, None

    import joblib
    try:
        _cached_pipeline = joblib.load(PIPELINE_PATH)
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            _cached_metadata = json.load(f)
        return _cached_pipeline, _cached_metadata
    except Exception as exc:
        print(f"[-] Failed loading clinical model artifacts: {exc}")
        return None, None


def get_clinical_model_validation_metrics() -> Dict[str, Any]:
    """
    Return true cross-validation metrics produced by training on OASIS.
    Returns status='model_not_available' if artifact is missing.
    Zero fabricated numbers.
    """
    _, metadata = load_model_artifacts()
    if not metadata or "metrics" not in metadata:
        return {
            "status": "model_not_available",
            "message": "Clinical reference model has not been trained locally.",
        }

    metrics = metadata["metrics"]
    return {
        "status": "available",
        "dataset": metadata.get("dataset_name", "OASIS Longitudinal"),
        "validation_protocol": metadata.get("validation_protocol", "StratifiedGroupKFold on Subject ID"),
        "training_sample_count": metadata.get("training_sample_count"),
        "subject_count": metadata.get("subject_count"),
        "sensitivity": metrics.get("sensitivity"),
        "specificity": metrics.get("specificity"),
        "auc": metrics.get("roc_auc"),
        "pr_auc": metrics.get("pr_auc"),
        "precision": metrics.get("precision"),
        "f1": metrics.get("f1"),
        "confusion_matrix": metrics.get("confusion_matrix"),
        "note": (
            "Cross-validated out-of-fold empirical metrics on OASIS longitudinal cohort. "
            "Grouped by Subject ID to eliminate longitudinal visit leakage."
        ),
    }


def predict_clinical_reference(clinical_inputs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Run inference on clinical inputs using the OASIS reference model.

    Expected fields in clinical_inputs:
    - Age (e.g. 60-95)
    - EDUC (years of education, e.g. 12-20)
    - SES (socioeconomic status 1-5)
    - MMSE (Mini-Mental State Exam score 0-30)
    - eTIV (Estimated total intracranial volume)
    - nWBV (Normalized whole brain volume)
    - ASF (Atlas scaling factor)
    - sex ('M', 'F', 1, 0)
    """
    if not is_model_available():
        return {
            "status": "model_not_available",
            "message": "Clinical reference model has not been trained locally.",
            "model": "OASIS_LogisticRegression",
            "probability": None,
            "risk_band": None,
            "explanations": [],
        }

    if not clinical_inputs:
        return {
            "status": "insufficient_input",
            "message": "No clinical reference parameters provided.",
            "model": "OASIS_LogisticRegression",
            "probability": None,
            "risk_band": None,
            "explanations": [],
        }

    # At least Age and MMSE or Education must be provided for meaningful inference
    core_keys = ["Age", "MMSE", "EDUC"]
    provided_core = [k for k in core_keys if k in clinical_inputs and clinical_inputs[k] is not None]
    if len(provided_core) == 0:
        return {
            "status": "insufficient_input",
            "message": f"Core clinical features missing. Provided: {list(clinical_inputs.keys())}",
            "model": "OASIS_LogisticRegression",
            "probability": None,
            "risk_band": None,
            "explanations": [],
        }

    pipeline, metadata = load_model_artifacts()
    if pipeline is None:
        return {
            "status": "model_not_available",
            "message": "Unable to load model pipeline.",
            "model": "OASIS_LogisticRegression",
            "probability": None,
            "risk_band": None,
            "explanations": [],
        }

    # Format input DataFrame
    row: Dict[str, Any] = {}
    for feat in CLINICAL_FEATURE_NAMES:
        val = clinical_inputs.get(feat)
        if feat == "sex" and val is not None:
            if isinstance(val, str):
                val = 1.0 if val.strip().upper() == "M" else 0.0
            else:
                val = float(val)
        elif val is not None:
            try:
                val = float(val)
            except (ValueError, TypeError):
                val = np.nan
        else:
            val = np.nan
        row[feat] = val

    df_input = pd.DataFrame([row], columns=CLINICAL_FEATURE_NAMES)

    # Inference
    try:
        prob = float(pipeline.predict_proba(df_input)[0, 1])
        prob = round(prob, 4)
    except Exception as e:
        return {
            "status": "inference_error",
            "message": f"Inference failed: {e}",
            "model": "OASIS_LogisticRegression",
            "probability": None,
            "risk_band": None,
            "explanations": [],
        }

    if prob < 0.35:
        risk_band = "Low"
    elif prob < 0.65:
        risk_band = "Moderate"
    else:
        risk_band = "High"

    # Compute feature contributions using pipeline transform + coefficients
    explanations = []
    try:
        imputer = pipeline.named_steps["imputer"]
        scaler = pipeline.named_steps["scaler"]
        clf = pipeline.named_steps["classifier"]

        X_imp = imputer.transform(df_input)
        X_scaled = scaler.transform(X_imp)[0]
        coefs = clf.coef_[0]

        for feat_name, scaled_val, raw_val, coef in zip(CLINICAL_FEATURE_NAMES, X_scaled, X_imp[0], coefs):
            contrib = float(scaled_val * coef)
            explanations.append({
                "feature": feat_name,
                "raw_value": round(float(raw_val), 2),
                "scaled_value": round(float(scaled_val), 3),
                "coefficient": round(float(coef), 4),
                "contribution_to_logit": round(contrib, 4),
                "direction": "increases_risk" if contrib > 0 else "decreases_risk",
                "importance": round(abs(contrib), 4),
            })
        explanations.sort(key=lambda x: x["importance"], reverse=True)
    except Exception as exc:
        print(f"[-] Warning: Failed computing detailed explanations: {exc}")

    return {
        "status": "available",
        "model": "OASIS_LogisticRegression",
        "probability": prob,
        "risk_band": risk_band,
        "explanations": explanations[:5],
        "research_disclaimer": (
            "This reference probability is estimated by a logistic regression model trained on the OASIS "
            "clinical cohort. It is a research baseline indicator and NOT a clinical diagnosis."
        ),
    }

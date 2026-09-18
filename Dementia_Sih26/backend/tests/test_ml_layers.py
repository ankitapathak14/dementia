"""
backend/tests/test_ml_layers.py
================================
Unit test suite for NeuroAid's two-layer ML architecture:
1. 18-feature vector construction.
2. Missing features handling and default fallbacks.
3. Behavioral model with insufficient history.
4. Behavioral anomaly detection with sufficient history.
5. OASIS preprocessing and leakage safety (no CDR in features).
6. Subject-level train/test separation (zero cross-visit leakage).
7. Logistic model training reproducibility.
8. Model artifact loading from joblib / JSON.
9. Clinical inference and coefficient explainability.
10. No fake / simulated validation metrics.
11. No self-combination in hybrid risk.
12. API backward compatibility with /api/analyze.
"""

from __future__ import annotations

import json
import os
import sys
import numpy as np
import pytest

# Ensure backend and repo root are on path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.behavioral_ml import (
    FEATURE_NAMES,
    evaluate_behavioral_anomaly,
    extract_raw_vector_dict,
    normalize_feature_vector,
)
from core.ml_engine import (
    compute_hybrid_risk,
    compute_uncertainty,
    compute_feature_importance,
)
from core.signal_fusion import fuse_cognitive_signals
from ml.preprocessing import (
    CLINICAL_FEATURE_NAMES,
    load_oasis_dataset,
    prepare_clinical_dataset,
)
from ml.clinical_model import (
    get_clinical_model_validation_metrics,
    is_model_available,
    load_model_artifacts,
    predict_clinical_reference,
)
from services.ai_service import (
    build_feature_vector,
    extract_speech_features,
    extract_memory_features,
    extract_reaction_features,
    extract_executive_features,
    extract_motor_features,
    compute_disease_risks,
)
from models.schemas import (
    FeatureVector,
    SpeechData,
    MemoryData,
    ReactionData,
    StroopData,
    TapData,
    UserProfile,
    AnalyzeRequest,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. 18-Feature Vector Construction
# ─────────────────────────────────────────────────────────────────────────────

def test_feature_vector_construction():
    speech_score, sf = extract_speech_features(speech=SpeechData(wpm=130.0, pause_ratio=0.12, speech_start_delay=0.6))
    memory_score, mf = extract_memory_features({}, memory=MemoryData(word_recall_accuracy=85.0, pattern_accuracy=80.0, delayed_recall_accuracy=75.0, recall_latency_seconds=3.2, order_match_ratio=0.9, intrusion_count=1))
    reaction_score, rf = extract_reaction_features([], reaction=ReactionData(times=[280.0, 310.0, 295.0, 305.0], miss_count=0))
    exec_score, ef = extract_executive_features(StroopData(total_trials=20, error_count=2, mean_rt=580.0))
    motor_score, mof = extract_motor_features(TapData(intervals=[210.0, 215.0, 208.0, 212.0], tap_count=4))

    fv = build_feature_vector(sf, mf, rf, ef, mof)
    assert isinstance(fv, FeatureVector)
    fv_dict = fv.model_dump()
    assert len(fv_dict) == 18
    for name in FEATURE_NAMES:
        assert name in fv_dict
        assert isinstance(fv_dict[name], (int, float))
        assert not np.isnan(fv_dict[name])


# ─────────────────────────────────────────────────────────────────────────────
# 2. Missing Features Handling & Fallbacks
# ─────────────────────────────────────────────────────────────────────────────

def test_missing_features_fallback():
    empty_dict = {}
    extracted = extract_raw_vector_dict(empty_dict)
    assert len(extracted) == 18
    for name in FEATURE_NAMES:
        assert name in extracted
        assert extracted[name] is not None
        assert not np.isnan(extracted[name])

    norm_arr = normalize_feature_vector(empty_dict)
    assert isinstance(norm_arr, np.ndarray)
    assert norm_arr.shape == (18,)
    assert np.all(norm_arr >= 0.0)
    assert np.all(norm_arr <= 2.0)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Behavioral Model with Insufficient History
# ─────────────────────────────────────────────────────────────────────────────

def test_behavioral_model_insufficient_history():
    current_fv = extract_raw_vector_dict({})

    # 0 sessions
    res0 = evaluate_behavioral_anomaly(current_fv, [], min_history=3)
    assert res0["status"] == "insufficient_history"
    assert res0["anomaly_detected"] is False
    assert res0["severity"] == "none"
    assert res0["anomaly_score"] is None
    assert "Establishing baseline requires at least 3 completed sessions" in res0["message"]

    # 1 session
    res1 = evaluate_behavioral_anomaly(current_fv, [current_fv], min_history=3)
    assert res1["status"] == "insufficient_history"
    assert res1["anomaly_detected"] is False

    # 2 sessions
    res2 = evaluate_behavioral_anomaly(current_fv, [current_fv, current_fv], min_history=3)
    assert res2["status"] == "insufficient_history"
    assert res2["anomaly_detected"] is False
    assert res2["anomaly_score"] is None


# ─────────────────────────────────────────────────────────────────────────────
# 4. Behavioral Anomaly Detection with History
# ─────────────────────────────────────────────────────────────────────────────

def test_behavioral_anomaly_detection():
    # Build 5 consistent healthy baseline sessions
    baseline_session = {
        "wpm": 140.0,
        "speed_deviation": 10.0,
        "speech_variability": 8.0,
        "pause_ratio": 0.12,
        "speech_start_delay": 0.7,
        "immediate_recall_accuracy": 90.0,
        "delayed_recall_accuracy": 85.0,
        "intrusion_count": 0.0,
        "recall_latency": 2.5,
        "order_match_ratio": 0.95,
        "mean_rt": 310.0,
        "std_rt": 35.0,
        "min_rt": 260.0,
        "reaction_drift": 10.0,
        "miss_count": 0.0,
        "stroop_error_rate": 0.05,
        "stroop_rt": 520.0,
        "tap_interval_std": 25.0,
    }

    history = []
    for i in range(5):
        session = {k: v + np.random.normal(0, 0.5) for k, v in baseline_session.items()}
        history.append(session)

    # Normal session
    normal_res = evaluate_behavioral_anomaly(baseline_session, history, min_history=3)
    assert normal_res["status"] == "sufficient_history"
    assert normal_res["anomaly_detected"] is False
    assert normal_res["severity"] == "none"
    assert normal_res["anomaly_score"] is not None
    assert 0.0 <= normal_res["anomaly_score"] <= 1.0

    # Degraded anomalous session (sudden cognitive drop)
    anomalous_session = dict(baseline_session)
    anomalous_session["immediate_recall_accuracy"] = 30.0  # huge drop
    anomalous_session["delayed_recall_accuracy"] = 20.0    # severe drop
    anomalous_session["mean_rt"] = 750.0                   # severe slowing
    anomalous_session["miss_count"] = 5.0                  # multiple misses
    anomalous_session["stroop_error_rate"] = 0.50          # severe error spike

    anomaly_res = evaluate_behavioral_anomaly(anomalous_session, history, min_history=3)
    assert anomaly_res["status"] == "sufficient_history"
    assert anomaly_res["anomaly_detected"] is True
    assert anomaly_res["severity"] in ["mild", "significant", "severe"]
    assert len(anomaly_res["top_deviating_features"]) > 0
    deviating_names = [d["feature"] for d in anomaly_res["top_deviating_features"]]
    # At least one of the severely degraded features should be in top deviations
    assert any(f in deviating_names for f in ["delayed_recall_accuracy", "immediate_recall_accuracy", "mean_rt", "miss_count"])


# ─────────────────────────────────────────────────────────────────────────────
# 5. OASIS Preprocessing & Leakage Safety
# ─────────────────────────────────────────────────────────────────────────────

def test_oasis_preprocessing_leakage_safety():
    df = load_oasis_dataset()
    assert len(df) > 100
    X, y, groups = prepare_clinical_dataset(df, handle_converted="visit_cdr")

    # Guard: CDR MUST NOT be in feature set X (target leakage prevention)
    assert "CDR" not in X.columns
    assert "CDR" not in CLINICAL_FEATURE_NAMES
    for col in CLINICAL_FEATURE_NAMES:
        assert col in X.columns

    # Check target
    assert set(y.unique()).issubset({0, 1})
    assert len(X) == len(y) == len(groups)
    assert len(groups.unique()) >= 100  # distinct subjects


# ─────────────────────────────────────────────────────────────────────────────
# 6. Subject-Level Train/Test Separation
# ─────────────────────────────────────────────────────────────────────────────

def test_subject_level_train_test_separation():
    from sklearn.model_selection import StratifiedGroupKFold

    df = load_oasis_dataset()
    X, y, groups = prepare_clinical_dataset(df)

    sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    for fold, (train_idx, val_idx) in enumerate(sgkf.split(X, y, groups=groups), 1):
        train_subjects = set(groups.iloc[train_idx])
        val_subjects = set(groups.iloc[val_idx])
        # Crucial test: zero overlap in subjects between train and validation folds
        overlap = train_subjects.intersection(val_subjects)
        assert len(overlap) == 0, f"Leakage detected in fold {fold}: {overlap}"


# ─────────────────────────────────────────────────────────────────────────────
# 7. Logistic Model Training Reproducibility
# ─────────────────────────────────────────────────────────────────────────────

def test_logistic_model_training():
    from ml.train_clinical_model import train_clinical_model
    metadata = train_clinical_model()

    assert "metrics" in metadata
    metrics = metadata["metrics"]
    assert metrics["roc_auc"] > 0.70
    assert 0.0 <= metrics["sensitivity"] <= 1.0
    assert 0.0 <= metrics["specificity"] <= 1.0
    assert 0.0 <= metrics["precision"] <= 1.0
    assert 0.0 <= metrics["f1"] <= 1.0
    assert len(metrics["fold_roc_aucs"]) == 5


# ─────────────────────────────────────────────────────────────────────────────
# 8. Model Artifact Loading
# ─────────────────────────────────────────────────────────────────────────────

def test_model_artifact_loading():
    assert is_model_available() is True
    pipeline, metadata = load_model_artifacts()
    assert pipeline is not None
    assert metadata is not None
    assert "dataset_name" in metadata
    assert "feature_coefficients" in metadata
    assert len(metadata["feature_coefficients"]) == len(CLINICAL_FEATURE_NAMES)


# ─────────────────────────────────────────────────────────────────────────────
# 9. Clinical Inference & Explainability
# ─────────────────────────────────────────────────────────────────────────────

def test_clinical_inference():
    # Test valid patient query
    patient_input = {
        "Age": 76.0,
        "EDUC": 12.0,
        "SES": 3.0,
        "MMSE": 22.0,
        "eTIV": 1450.0,
        "nWBV": 0.71,
        "ASF": 1.20,
        "sex": "M",
    }
    res = predict_clinical_reference(patient_input)
    assert res["status"] == "available"
    assert res["probability"] is not None
    assert 0.0 <= res["probability"] <= 1.0
    assert res["risk_band"] in ["Low", "Moderate", "High"]
    assert len(res["explanations"]) > 0

    exp0 = res["explanations"][0]
    assert "feature" in exp0
    assert "coefficient" in exp0
    assert "direction" in exp0
    assert "importance" in exp0

    # Test missing input
    empty_res = predict_clinical_reference(None)
    assert empty_res["status"] == "insufficient_input"


# ─────────────────────────────────────────────────────────────────────────────
# 10. No Fake Validation Metrics
# ─────────────────────────────────────────────────────────────────────────────

def test_no_fake_validation_metrics():
    metrics = get_clinical_model_validation_metrics()
    assert metrics["status"] == "available"
    # Verify values are true empirical values, not the old hardcoded 0.82 / 0.78 / 0.85
    assert not (metrics["sensitivity"] == 0.82 and metrics["specificity"] == 0.78 and metrics["auc"] == 0.85)
    assert metrics["auc"] > 0.80
    assert "StratifiedGroupKFold" in metrics["validation_protocol"]


# ─────────────────────────────────────────────────────────────────────────────
# 11. No Self-Combination in Hybrid Risk
# ─────────────────────────────────────────────────────────────────────────────

def test_no_self_combination_in_hybrid_risk():
    # When both signals exist independently
    beh = {"status": "sufficient_history", "anomaly_score": 0.70, "anomaly_detected": True, "severity": "significant"}
    clin = {"status": "available", "probability": 0.40, "risk_band": "Moderate"}
    fused = fuse_cognitive_signals(beh, clin)
    assert fused["combined_indicator"]["available"] is True
    assert fused["combined_indicator"]["value"] == 0.55
    assert "WeightedLinearCombination" in fused["combined_indicator"]["fusion_method"]

    # When only behavioral exists
    fused_beh_only = fuse_cognitive_signals(beh, None)
    assert fused_beh_only["combined_indicator"]["available"] is False
    assert fused_beh_only["combined_indicator"]["value"] is None

    # When only clinical exists
    fused_clin_only = fuse_cognitive_signals(None, clin)
    assert fused_clin_only["combined_indicator"]["available"] is False
    assert fused_clin_only["combined_indicator"]["value"] is None

    # Self combination guard in compute_hybrid_risk helper
    assert compute_hybrid_risk(0.65, 0.65) == 0.65  # returns value directly without false combination


# ─────────────────────────────────────────────────────────────────────────────
# 12. API Backward Compatibility
# ─────────────────────────────────────────────────────────────────────────────

def test_api_backward_compatibility():
    import asyncio
    from routers.analyze_api import analyze
    req = AnalyzeRequest(
        speech=SpeechData(wpm=125.0, pause_ratio=0.14),
        memory=MemoryData(word_recall_accuracy=75.0, pattern_accuracy=70.0),
        reaction=ReactionData(times=[310.0, 320.0, 330.0]),
        stroop=StroopData(total_trials=10, error_count=1, mean_rt=550.0),
        tap=TapData(intervals=[200.0, 205.0, 202.0], tap_count=3),
        profile=UserProfile(age=72, education_level=3),
    )

    response = asyncio.run(analyze(req))

    # Legacy fields preserved for frontend
    assert hasattr(response, "speech_score")
    assert hasattr(response, "memory_score")
    assert hasattr(response, "reaction_score")
    assert hasattr(response, "executive_score")
    assert hasattr(response, "motor_score")
    assert hasattr(response, "composite_risk_score")
    assert hasattr(response, "hybrid_risk")
    assert hasattr(response, "risk_drivers")
    assert hasattr(response, "feature_importance")
    assert hasattr(response, "model_validation")

    # Real validation metrics
    assert response.model_validation["status"] == "available"
    assert response.model_validation["auc"] > 0.80

    # Multi-Modal ML Layers
    assert response.ml_analysis is not None
    assert response.ml_analysis.behavioral.status in ["sufficient_history", "insufficient_history"]
    assert response.ml_analysis.clinical_reference.status in ["available", "insufficient_input"]
    assert response.ml_analysis.combined_indicator is not None

    # Honest uncertainty
    assert response.uncertainty is not None
    assert response.uncertainty["available"] is False

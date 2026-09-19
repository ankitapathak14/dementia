"""
backend/tests/test_data_lineage_semantics.py
============================================
Verification suite for data lineage and user-facing semantics:
1. No frontend disease probability component consumes deprecated disease fields.
2. User Dashboard uses domain scores and ml_analysis.behavioral_deviation.
3. Doctor Dashboard uses ml_analysis.overall_attention and behavioral_deviation.
4. Patient Detail does not label disease probabilities; uses Overall Attention, Behavioral Deviation, and domain scores.
5. Missing OASIS inputs result in insufficient_input with exact statutory research text.
6. Feature provenance correctly distinguishes measured / derived / defaulted across 18 features.
7. Composite score is labeled "Cognitive Performance Index" with required non-diagnostic disclaimer tooltip.
8. Backward compatibility maintained in API response schemas.
"""

from __future__ import annotations

import os
import re
import sys
import pytest

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend", "src")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from ml.clinical_model import predict_clinical_reference
from services.ai_service import compute_feature_provenance
from models.schemas import (
    SpeechData,
    MemoryData,
    ReactionData,
    StroopData,
    TapData,
    AnalyzeResponse,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Frontend: No deprecated disease probability consumption
# ─────────────────────────────────────────────────────────────────────────────

def test_frontend_no_deprecated_disease_fields_consumed():
    """Verify that frontend pages do not consume deprecated disease probability fields."""
    key_pages = [
        os.path.join(FRONTEND_DIR, "pages", "DoctorDashboard.jsx"),
        os.path.join(FRONTEND_DIR, "pages", "DoctorHome.jsx"),
        os.path.join(FRONTEND_DIR, "pages", "PatientDetail.jsx"),
        os.path.join(FRONTEND_DIR, "pages", "UserDashboard.jsx"),
        os.path.join(FRONTEND_DIR, "pages", "ResultsPage.jsx"),
    ]

    deprecated_fields = [
        "alzheimers_risk",
        "dementia_risk",
        "parkinsons_risk",
        "risk_levels",
    ]

    for page_path in key_pages:
        assert os.path.exists(page_path), f"File not found: {page_path}"
        with open(page_path, "r", encoding="utf-8") as f:
            content = f.read()

        for field in deprecated_fields:
            assert field not in content, f"Found deprecated field '{field}' in {os.path.basename(page_path)}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. User Dashboard uses domain scores, not disease proxies
# ─────────────────────────────────────────────────────────────────────────────

def test_user_dashboard_uses_domain_scores():
    """Verify UserDashboard consumes actual domain scores and behavioral deviation."""
    user_dash_path = os.path.join(FRONTEND_DIR, "pages", "UserDashboard.jsx")
    with open(user_dash_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Must consume domain scores
    assert "memory_score" in content
    assert "executive_score" in content
    assert "motor_score" in content

    # Must consume behavioral deviation
    assert "ml_analysis?.behavioral_deviation" in content or "ml_analysis.behavioral_deviation" in content

    # Must NOT use alzheimers_risk as memory proxy
    assert "alzheimers_risk" not in content
    assert "dementia_risk" not in content
    assert "parkinsons_risk" not in content


# ─────────────────────────────────────────────────────────────────────────────
# 3. Doctor Dashboard uses ml_analysis.overall_attention & deviation
# ─────────────────────────────────────────────────────────────────────────────

def test_doctor_dashboard_uses_overall_attention():
    """Verify Doctor Dashboard uses overall_attention and behavioral_deviation."""
    doc_dash_path = os.path.join(FRONTEND_DIR, "pages", "DoctorDashboard.jsx")
    with open(doc_dash_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "overall_attention" in content
    assert "behavioral_deviation" in content
    assert "Elevated" in content
    assert "Moderate" in content
    assert "Routine" in content

    # DoctorHome should also use attention priority
    doc_home_path = os.path.join(FRONTEND_DIR, "pages", "DoctorHome.jsx")
    with open(doc_home_path, "r", encoding="utf-8") as f:
        home_content = f.read()
    assert "overall_attention" in home_content
    assert "behavioral_deviation" in home_content


# ─────────────────────────────────────────────────────────────────────────────
# 4. Patient Detail does not label disease probabilities
# ─────────────────────────────────────────────────────────────────────────────

def test_patient_detail_does_not_label_disease_probabilities():
    """Verify PatientDetail does not display Alzheimer's/Dementia/Parkinson's risk columns or cards."""
    patient_detail_path = os.path.join(FRONTEND_DIR, "pages", "PatientDetail.jsx")
    with open(patient_detail_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Must contain new table headers
    assert "Overall Attention" in content
    assert "Behavioral Deviation" in content

    # Must not contain disease columns in sessions table
    assert '["Date", "Overall Attention", "Behavioral Deviation", "Memory", "Reaction", "Executive", "Speech", "Motor"]' in content
    assert "Alzheimer's" not in content
    assert "alzheimers" not in content


# ─────────────────────────────────────────────────────────────────────────────
# 5. Missing OASIS inputs result in insufficient_input
# ─────────────────────────────────────────────────────────────────────────────

def test_missing_oasis_inputs_insufficient_input():
    """Verify missing research inputs produce insufficient_input without silent imputation."""
    # Only Age and Education supplied (typical NeuroAid user profile)
    res = predict_clinical_reference({"Age": 72, "EDUC": 14})
    assert res["status"] == "insufficient_input"
    assert res["probability"] is None
    assert res["risk_band"] == "unavailable"
    assert "missing_features" in res
    assert len(res["missing_features"]) > 0
    assert "Clinical reference model unavailable for this session because required research-model inputs are incomplete." in res["message"]


# ─────────────────────────────────────────────────────────────────────────────
# 6. Feature provenance correctly distinguishes measured / derived / defaulted
# ─────────────────────────────────────────────────────────────────────────────

def test_feature_provenance_distinction():
    """Verify 18 features are accurately classified as measured, derived, or defaulted."""
    # Scenario A: All inputs provided
    speech = SpeechData(wpm=120.0, pause_ratio=0.15, speech_start_delay=0.5)
    memory = MemoryData(
        word_recall_accuracy=80.0,
        pattern_accuracy=75.0,
        delayed_recall_accuracy=70.0,
        recall_latency_seconds=3.0,
        order_match_ratio=0.85,
        intrusion_count=1
    )
    reaction = ReactionData(times=[280.0, 310.0, 295.0, 320.0], miss_count=0)
    stroop = StroopData(total_trials=20, error_count=1, mean_rt=550.0)
    tap = TapData(intervals=[200.0, 205.0, 198.0, 202.0], tap_count=4)

    prov_a, categorized_a, counts_a = compute_feature_provenance(
        audio_b64=None,
        speech=speech,
        memory_results={},
        memory=memory,
        reaction_times=[280.0, 310.0, 295.0, 320.0],
        reaction=reaction,
        stroop=stroop,
        tap=tap
    )

    assert prov_a["wpm"] == "measured"
    assert prov_a["delayed_recall_accuracy"] == "measured"
    assert prov_a["mean_rt"] == "measured"
    assert prov_a["stroop_rt"] == "measured"
    assert prov_a["tap_interval_std"] == "measured"
    assert len(categorized_a["defaulted"]) == 0
    assert counts_a["defaulted_count"] == 0

    # Scenario B: Delayed recall missing, but immediate and pattern supplied -> derived
    memory_derived = MemoryData(
        word_recall_accuracy=80.0,
        pattern_accuracy=75.0,
        delayed_recall_accuracy=None,
        recall_latency_seconds=3.0,
        order_match_ratio=0.85,
        intrusion_count=1
    )
    prov_b, categorized_b, counts_b = compute_feature_provenance(
        audio_b64=None,
        speech=None,
        memory_results={},
        memory=memory_derived,
        reaction_times=None,
        reaction=None,
        stroop=None,
        tap=None
    )

    assert prov_b["wpm"] == "defaulted"
    assert prov_b["delayed_recall_accuracy"] == "derived"
    assert prov_b["stroop_rt"] == "defaulted"
    assert prov_b["tap_interval_std"] == "defaulted"
    assert "delayed_recall_accuracy" in categorized_b["derived"]
    assert "wpm" in categorized_b["defaulted"]

    # Scenario C: Tap data has only 2 intervals (< 3) -> tap_interval_std is defaulted
    tap_few = TapData(intervals=[200.0, 205.0], tap_count=2)
    prov_c, categorized_c, counts_c = compute_feature_provenance(
        audio_b64=None,
        speech=None,
        memory_results={},
        memory=None,
        reaction_times=None,
        reaction=None,
        stroop=None,
        tap=tap_few
    )
    assert prov_c["tap_interval_std"] == "defaulted"


# ─────────────────────────────────────────────────────────────────────────────
# 7. Composite score is labeled Cognitive Performance Index
# ─────────────────────────────────────────────────────────────────────────────

def test_composite_score_naming_and_tooltip():
    """Verify Cognitive Performance Index labeling and non-diagnostic tooltip in frontend."""
    user_dash_path = os.path.join(FRONTEND_DIR, "pages", "UserDashboard.jsx")
    with open(user_dash_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Cognitive Performance Index" in content
    expected_tooltip = "Composite performance index derived from measured cognitive domains. It is a monitoring metric and not a medical diagnosis."
    assert expected_tooltip in content

    # ProgressPage verification
    prog_path = os.path.join(FRONTEND_DIR, "pages", "ProgressPage.jsx")
    with open(prog_path, "r", encoding="utf-8") as f:
        prog_content = f.read()
    assert "Cognitive Performance Index" in prog_content
    assert expected_tooltip in prog_content

    # Locales verification
    loc_path = os.path.join(FRONTEND_DIR, "i18n", "locales.js")
    with open(loc_path, "r", encoding="utf-8") as f:
        loc_content = f.read()
    assert 'compositeRiskScore: "Cognitive Performance Index"' in loc_content


# ─────────────────────────────────────────────────────────────────────────────
# 8. AnalyzeResponse Schema contains provenance fields
# ─────────────────────────────────────────────────────────────────────────────

def test_analyze_response_schema_provenance():
    """Verify AnalyzeResponse includes feature_provenance and categorized fields."""
    fields = AnalyzeResponse.model_fields
    assert "feature_provenance" in fields
    assert "measured_features" in fields
    assert "derived_features" in fields
    assert "defaulted_features" in fields
    assert "provenance_summary" in fields

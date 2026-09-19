"""
backend/tests/test_ml_end_to_end.py
===================================
End-to-End Behavioral and Clinical Validation Test Suite for NeuroAid ML Pipeline.

ALL DATA IN THIS SUITE ARE DETERMINISTIC SYNTHETIC VALIDATION FIXTURES ONLY.
THEY DO NOT REPRESENT REAL PATIENTS OR CLINICAL OBSERVATIONS.

Scenarios Tested:
- Scenario A: Stable Patient (5 chronological sessions, baseline establishment, non-diagnostic)
- Scenario B: Memory Decline (stable baseline -> memory deterioration, top deviations, non-diagnostic)
- Scenario C: Reaction Decline (stable baseline -> reaction latency/variability jump, top deviations)
- Scenario D: Insufficient History (1 and 2 prior sessions -> status='insufficient_history')
- Scenario E: Missing Test Modalities (deliberate omissions -> feature_provenance breakdown)
- Scenario F: Incomplete OASIS Input (Age + EDUC only -> status='insufficient_input', no probability)
- Scenario G: Complete OASIS Input (All 8 features -> status='available', valid probability, explanations)
- Scenario H: Fusion Semantics (Behavioral only, Clinical only, Both modalities, non-diagnostic labeling)
"""

from __future__ import annotations

import os
import sys
import json
import pytest

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from fastapi.testclient import TestClient
from main import app
from core.behavioral_ml import (
    FEATURE_NAMES,
    evaluate_behavioral_anomaly,
    extract_raw_vector_dict,
)
from core.signal_fusion import fuse_cognitive_signals
from ml.clinical_model import predict_clinical_reference
from services.ai_service import (
    build_feature_vector,
    compute_feature_provenance,
    extract_executive_features,
    extract_memory_features,
    extract_motor_features,
    extract_reaction_features,
    extract_speech_features,
)
from models.schemas import (
    MemoryData,
    ReactionData,
    SpeechData,
    StroopData,
    TapData,
)


@pytest.fixture
def client():
    return TestClient(app)


def _make_synthetic_session_vector(
    wpm: float = 125.0,
    pause_ratio: float = 0.14,
    speech_delay: float = 0.6,
    word_recall: float = 85.0,
    pattern_accuracy: float = 80.0,
    delayed_recall: float = 80.0,
    recall_latency: float = 3.1,
    order_match: float = 0.9,
    intrusions: int = 1,
    mean_rt: float = 295.0,
    miss_count: int = 0,
    stroop_rt: float = 560.0,
    stroop_errors: int = 1,
    tap_intervals: list[float] | None = None,
) -> dict[str, float]:
    """Deterministic synthetic fixture helper constructing a canonical 18-feature vector."""
    if tap_intervals is None:
        tap_intervals = [205.0, 210.0, 202.0, 208.0]

    _, sf = extract_speech_features(speech=SpeechData(wpm=wpm, pause_ratio=pause_ratio, speech_start_delay=speech_delay))
    _, mf = extract_memory_features(
        {},
        memory=MemoryData(
            word_recall_accuracy=word_recall,
            pattern_accuracy=pattern_accuracy,
            delayed_recall_accuracy=delayed_recall,
            recall_latency_seconds=recall_latency,
            order_match_ratio=order_match,
            intrusion_count=intrusions,
        ),
    )
    r_times = [mean_rt - 10.0, mean_rt + 10.0, mean_rt - 5.0, mean_rt + 5.0]
    _, rf = extract_reaction_features(
        r_times,
        reaction=ReactionData(times=r_times, miss_count=miss_count),
    )
    _, ef = extract_executive_features(StroopData(total_trials=20, error_count=stroop_errors, mean_rt=stroop_rt))
    _, mof = extract_motor_features(TapData(intervals=tap_intervals, tap_count=len(tap_intervals)))
    fv = build_feature_vector(sf, mf, rf, ef, mof)
    return extract_raw_vector_dict(fv.model_dump())


# =============================================================================
# STEP 2 — SCENARIO A: STABLE PATIENT
# =============================================================================

def test_scenario_a_stable_patient():
    """
    Scenario A: 5 deterministic synthetic sessions representing a stable patient.
    Run chronologically:
    - First sessions establish baseline.
    - No severe behavioral deviation.
    - No disease diagnosis.
    - No Alzheimer's probability.
    - No dementia probability.
    - Overall attention remains Routine/stable.
    """
    print("\n" + "=" * 60)
    print("SCENARIO A: STABLE PATIENT (5 CHRONOLOGICAL SESSIONS)")
    print("=" * 60)

    # 5 deterministic synthetic sessions with realistic minor variations
    sessions = [
        _make_synthetic_session_vector(wpm=124.0, word_recall=86.0, delayed_recall=82.0, mean_rt=292.0),
        _make_synthetic_session_vector(wpm=126.0, word_recall=84.0, delayed_recall=79.0, mean_rt=297.0),
        _make_synthetic_session_vector(wpm=125.0, word_recall=85.0, delayed_recall=80.0, mean_rt=294.0),
        _make_synthetic_session_vector(wpm=123.0, word_recall=87.0, delayed_recall=81.0, mean_rt=296.0),
        _make_synthetic_session_vector(wpm=125.0, word_recall=85.0, delayed_recall=80.0, mean_rt=295.0),
    ]

    history: list[dict[str, float]] = []
    session_results = []

    for i, current_session in enumerate(sessions, start=1):
        res = evaluate_behavioral_anomaly(
            current_features=current_session,
            historical_sessions=history,
            min_history=3,
        )
        history.append(current_session)
        session_results.append(res)

        print(f"\n[Session {i}/5]")
        print(f"  History count:       {len(history) - 1}")
        print(f"  Status:              {res['status']}")
        print(f"  Anomaly detected:    {res['anomaly_detected']}")
        print(f"  Severity:            {res['severity']}")
        print(f"  Anomaly score:       {res['anomaly_score']}")
        print(f"  Terminology:         {res['terminology']}")
        print(f"  Top deviations:      {[d['feature'] + ': z=' + str(d['z_score']) for d in res.get('top_deviating_features', [])]}")

        # Baseline establishment checks
        if i in (1, 2, 3):
            # Prior sessions count is < min_history (3)
            assert res["status"] == "insufficient_history"
            assert res["anomaly_detected"] is False
            assert res["anomaly_score"] is None
        elif i in (4, 5):
            # Baseline established: preliminary_baseline or longitudinal_baseline
            assert res["status"] in ["preliminary_baseline", "longitudinal_baseline"]
            # No severe behavioral deviation; stable patient remains low-severity / none
            assert res["severity"] in ["none", "mild"], f"Session {i} severity too high: {res['severity']}"
            assert res["anomaly_detected"] is False, f"Session {i} false positive anomaly detected"

        # Output semantics audit: strictly non-diagnostic
        assert "dementia_probability" not in res
        assert "alzheimers_probability" not in res
        assert "diagnosis" not in res
        assert res["terminology"] == "Cognitive Performance Deviation"

    # Multimodal signal fusion with incomplete clinical profile (typical patient)
    last_res = session_results[-1]
    clin_res = predict_clinical_reference({"Age": 68.0, "EDUC": 14.0})
    fusion = fuse_cognitive_signals(last_res, clin_res)
    oa = fusion["overall_attention"]

    print("\n[Scenario A Fusion Result]")
    print(f"  Fusion Available:    {oa['available']}")
    print(f"  Attention Label:     {oa['label']}")
    print(f"  Attention Method:    {oa['method']}")

    if oa["available"] and oa["label"]:
        assert "elevated" not in oa["label"].lower()
        assert "high" not in oa["label"].lower()


# =============================================================================
# STEP 3 — SCENARIO B: MEMORY DECLINE
# =============================================================================

def test_scenario_b_memory_decline():
    """
    Scenario B: 5 synthetic sessions.
    Sessions 1-3: stable baseline memory performance.
    Sessions 4-5: substantial deterioration in memory-related measurements.
    Keep reaction, executive, speech, and motor approximately stable.
    Verify:
    - Behavioral analysis runs.
    - Anomaly/deviation changes relative to baseline.
    - Memory-related features are candidates for top deviations.
    - Output remains non-diagnostic.
    """
    print("\n" + "=" * 60)
    print("SCENARIO B: MEMORY DECLINE (ACUTE MEMORY DETERIORATION)")
    print("=" * 60)

    # Sessions 1-3: stable baseline memory (recall ~85%, delayed ~81%, intrusions 1, latency 3.1s)
    s1 = _make_synthetic_session_vector(word_recall=86.0, delayed_recall=82.0, intrusions=1, recall_latency=3.0)
    s2 = _make_synthetic_session_vector(word_recall=84.0, delayed_recall=80.0, intrusions=1, recall_latency=3.2)
    s3 = _make_synthetic_session_vector(word_recall=85.0, delayed_recall=81.0, intrusions=1, recall_latency=3.1)

    baseline_history = [s1, s2, s3]

    # Session 4: substantial drop in memory (recall 85->35, delayed 80->25, intrusions 1->5, latency 3.1->7.8)
    s4 = _make_synthetic_session_vector(word_recall=35.0, delayed_recall=25.0, intrusions=5, recall_latency=7.8, order_match=0.35)

    # Session 5: continued severe memory deterioration (recall 30->20, delayed 20->15, intrusions 5->7, latency 7.8->8.9)
    s5 = _make_synthetic_session_vector(word_recall=20.0, delayed_recall=15.0, intrusions=7, recall_latency=8.9, order_match=0.25)

    # Evaluate Session 4
    res_4 = evaluate_behavioral_anomaly(current_features=s4, historical_sessions=baseline_history, min_history=3)

    print("\n[Session 4 Result - First Memory Decline]")
    print(f"  Status:              {res_4['status']}")
    print(f"  Anomaly detected:    {res_4['anomaly_detected']}")
    print(f"  Severity:            {res_4['severity']}")
    print(f"  Anomaly score:       {res_4['anomaly_score']}")
    print("  Top deviating features:")
    for f in res_4["top_deviating_features"]:
        print(f"    - {f['feature']}: z={f['z_score']}, dir={f['direction']}, adverse={f['is_adverse']}")

    # Evaluate Session 5 with accumulated history
    history_with_s4 = [s1, s2, s3, s4]
    res_5 = evaluate_behavioral_anomaly(current_features=s5, historical_sessions=history_with_s4, min_history=3)

    print("\n[Session 5 Result - Sustained Memory Decline]")
    print(f"  Status:              {res_5['status']}")
    print(f"  Anomaly detected:    {res_5['anomaly_detected']}")
    print(f"  Severity:            {res_5['severity']}")
    print(f"  Anomaly score:       {res_5['anomaly_score']}")
    print("  Top deviating features:")
    for f in res_5["top_deviating_features"]:
        print(f"    - {f['feature']}: z={f['z_score']}, dir={f['direction']}, adverse={f['is_adverse']}")

    # Verifications
    assert res_4["status"] in ["preliminary_baseline", "longitudinal_baseline"]
    assert res_4["anomaly_detected"] is True
    assert res_4["severity"] in ["significant", "severe"]

    assert res_5["status"] in ["preliminary_baseline", "longitudinal_baseline"]
    assert res_5["anomaly_detected"] is True
    assert res_5["severity"] in ["significant", "severe"]

    # Verify memory features dominate top deviations
    memory_feature_names = {
        "delayed_recall_accuracy",
        "immediate_recall_accuracy",
        "order_match_ratio",
        "intrusion_count",
        "recall_latency",
    }
    top_4 = [d["feature"] for d in res_4["top_deviating_features"]]
    top_5 = [d["feature"] for d in res_5["top_deviating_features"]]

    assert any(feat in memory_feature_names for feat in top_4), f"Memory features missing in {top_4}"
    assert any(feat in memory_feature_names for feat in top_5), f"Memory features missing in {top_5}"

    # Non-diagnostic semantics verification
    for res in (res_4, res_5):
        assert "dementia_probability" not in res
        assert "alzheimers_probability" not in res
        assert "diagnosis" not in res
        assert res["terminology"] == "Cognitive Performance Deviation"


# =============================================================================
# STEP 4 — SCENARIO C: REACTION DECLINE
# =============================================================================

def test_scenario_c_reaction_decline():
    """
    Scenario C: 5 synthetic sessions.
    Sessions 1-3: stable reaction times (~290ms, 0 misses).
    Sessions 4-5: substantially slower and more variable reaction times (>750ms, misses).
    Keep other domains approximately stable.
    Verify:
    - Behavioral analysis runs.
    - Reaction-related features appear among top deviations.
    - No disease diagnosis is produced.
    """
    print("\n" + "=" * 60)
    print("SCENARIO C: REACTION DECLINE (SLOWER RT & ELEVATED VARIABILITY)")
    print("=" * 60)

    # Sessions 1-3: stable baseline reaction times
    s1 = _make_synthetic_session_vector(mean_rt=290.0, miss_count=0)
    s2 = _make_synthetic_session_vector(mean_rt=295.0, miss_count=0)
    s3 = _make_synthetic_session_vector(mean_rt=288.0, miss_count=0)

    baseline_history = [s1, s2, s3]

    # Session 4: substantial slowdown (290ms -> 780ms, 3 misses)
    s4 = _make_synthetic_session_vector(mean_rt=780.0, miss_count=3)
    # Session 5: continued severe reaction slowing (850ms, 4 misses)
    s5 = _make_synthetic_session_vector(mean_rt=850.0, miss_count=4)

    res_4 = evaluate_behavioral_anomaly(current_features=s4, historical_sessions=baseline_history, min_history=3)

    print("\n[Session 4 Result - Reaction Decline]")
    print(f"  Status:              {res_4['status']}")
    print(f"  Anomaly detected:    {res_4['anomaly_detected']}")
    print(f"  Severity:            {res_4['severity']}")
    print(f"  Anomaly score:       {res_4['anomaly_score']}")
    print("  Top deviating features:")
    for f in res_4["top_deviating_features"]:
        print(f"    - {f['feature']}: z={f['z_score']}, dir={f['direction']}, adverse={f['is_adverse']}")

    history_with_s4 = [s1, s2, s3, s4]
    res_5 = evaluate_behavioral_anomaly(current_features=s5, historical_sessions=history_with_s4, min_history=3)

    print("\n[Session 5 Result - Sustained Reaction Decline]")
    print(f"  Status:              {res_5['status']}")
    print(f"  Anomaly detected:    {res_5['anomaly_detected']}")
    print(f"  Severity:            {res_5['severity']}")
    print(f"  Anomaly score:       {res_5['anomaly_score']}")
    print("  Top deviating features:")
    for f in res_5["top_deviating_features"]:
        print(f"    - {f['feature']}: z={f['z_score']}, dir={f['direction']}, adverse={f['is_adverse']}")

    # Verifications
    assert res_4["anomaly_detected"] is True
    assert res_4["severity"] in ["significant", "severe"]
    assert res_5["anomaly_detected"] is True
    assert res_5["severity"] in ["significant", "severe"]

    reaction_features = {"mean_rt", "std_rt", "min_rt", "reaction_drift", "miss_count"}
    top_4 = [d["feature"] for d in res_4["top_deviating_features"]]
    top_5 = [d["feature"] for d in res_5["top_deviating_features"]]

    assert any(feat in reaction_features for feat in top_4), f"Reaction features missing in {top_4}"
    assert any(feat in reaction_features for feat in top_5), f"Reaction features missing in {top_5}"

    # Non-diagnostic semantics verification
    for res in (res_4, res_5):
        assert "dementia_probability" not in res
        assert "alzheimers_probability" not in res
        assert "diagnosis" not in res
        assert res["terminology"] == "Cognitive Performance Deviation"


# =============================================================================
# STEP 5 — SCENARIO D: INSUFFICIENT HISTORY
# =============================================================================

def test_scenario_d_insufficient_history():
    """
    Scenario D: Insufficient History.
    Run behavioral analysis with:
    - 1 historical session (history count = 1)
    - 2 historical sessions (history count = 2)
    Expected:
    - status == "insufficient_history"
    - anomaly_detected == False
    - anomaly_score is None
    """
    print("\n" + "=" * 60)
    print("SCENARIO D: INSUFFICIENT HISTORY (1 AND 2 HISTORICAL SESSIONS)")
    print("=" * 60)

    curr = _make_synthetic_session_vector()
    h1 = _make_synthetic_session_vector(wpm=120.0, word_recall=80.0)
    h2 = _make_synthetic_session_vector(wpm=128.0, word_recall=86.0)

    # 1 historical session
    res_1 = evaluate_behavioral_anomaly(current_features=curr, historical_sessions=[h1], min_history=3)
    print("\n[1 Historical Session Result]")
    print(f"  Status:              {res_1['status']}")
    print(f"  Anomaly detected:    {res_1['anomaly_detected']}")
    print(f"  Severity:            {res_1['severity']}")
    print(f"  Anomaly score:       {res_1['anomaly_score']}")
    print(f"  Session count:       {res_1['session_count']}")
    print(f"  Message:             {res_1['message']}")

    assert res_1["status"] == "insufficient_history"
    assert res_1["anomaly_detected"] is False
    assert res_1["anomaly_score"] is None
    assert res_1["severity"] == "none"
    assert res_1["session_count"] == 1

    # 2 historical sessions
    res_2 = evaluate_behavioral_anomaly(current_features=curr, historical_sessions=[h1, h2], min_history=3)
    print("\n[2 Historical Sessions Result]")
    print(f"  Status:              {res_2['status']}")
    print(f"  Anomaly detected:    {res_2['anomaly_detected']}")
    print(f"  Severity:            {res_2['severity']}")
    print(f"  Anomaly score:       {res_2['anomaly_score']}")
    print(f"  Session count:       {res_2['session_count']}")
    print(f"  Message:             {res_2['message']}")

    assert res_2["status"] == "insufficient_history"
    assert res_2["anomaly_detected"] is False
    assert res_2["anomaly_score"] is None
    assert res_2["severity"] == "none"
    assert res_2["session_count"] == 2


# =============================================================================
# STEP 6 — SCENARIO E: MISSING TEST MODALITIES
# =============================================================================

def test_scenario_e_missing_test_modalities(client):
    """
    Scenario E: Deliberately omitted modalities.
    Supplied: Memory, Reaction.
    Omitted: Speech, Stroop, Motor.
    Inspect:
    - feature_provenance
    - measured_features
    - derived_features
    - defaulted_features
    - provenance_summary
    Verify:
    - all 18 feature keys still have provenance
    - omitted modalities are NOT labelled 'measured'
    - defaulted features are correctly identified
    - measured count + derived count + defaulted count = 18
    """
    print("\n" + "=" * 60)
    print("SCENARIO E: MISSING TEST MODALITIES & FEATURE PROVENANCE")
    print("=" * 60)

    payload = {
        "memory": {
            "word_recall_accuracy": 82.0,
            "pattern_accuracy": 78.0,
            "delayed_recall_accuracy": 75.0,
            "recall_latency_seconds": 3.2,
            "order_match_ratio": 0.88,
            "intrusion_count": 1,
        },
        "reaction": {
            "times": [290.0, 310.0, 295.0, 305.0],
            "miss_count": 0,
        },
        # Speech, Stroop, Motor omitted deliberately
    }

    resp = client.post("/api/analyze", json=payload)
    assert resp.status_code == 200, f"Endpoint error: {resp.text}"
    data = resp.json()

    feature_provenance = data["feature_provenance"]
    measured_features = data["measured_features"]
    derived_features = data["derived_features"]
    defaulted_features = data["defaulted_features"]
    provenance_summary = data["provenance_summary"]

    print("\n[Feature Provenance Summary]")
    print(f"  Measured ({len(measured_features)}):  {measured_features}")
    print(f"  Derived ({len(derived_features)}):   {derived_features}")
    print(f"  Defaulted ({len(defaulted_features)}): {defaulted_features}")
    print(f"  Summary counts:      {provenance_summary}")
    print("\n[All 18 Feature Provenances]")
    for k, v in feature_provenance.items():
        print(f"    {k:26s} -> {v}")

    # 1. All 18 canonical keys must exist in provenance
    assert len(feature_provenance) == 18
    for feat in FEATURE_NAMES:
        assert feat in feature_provenance, f"Missing feature in provenance: {feat}"

    # 2. Omitted modalities (speech, stroop, motor) must NOT be marked "measured"
    omitted_feats = [
        "wpm",
        "speed_deviation",
        "speech_variability",
        "pause_ratio",
        "speech_start_delay",
        "stroop_error_rate",
        "stroop_rt",
        "tap_interval_std",
    ]
    for feat in omitted_feats:
        assert feature_provenance[feat] != "measured", f"Omitted feature {feat} was incorrectly marked measured"
        assert feat not in measured_features, f"Omitted feature {feat} found in measured_features"
        assert feature_provenance[feat] == "defaulted", f"Omitted feature {feat} expected 'defaulted', got {feature_provenance[feat]}"

    # 3. Supplied modalities (memory, reaction) must have measured features
    assert feature_provenance["immediate_recall_accuracy"] == "measured"
    assert feature_provenance["delayed_recall_accuracy"] == "measured"
    assert feature_provenance["mean_rt"] == "measured"
    assert feature_provenance["miss_count"] == "measured"

    # 4. Count invariant: measured + derived + defaulted == 18
    total_count = len(measured_features) + len(derived_features) + len(defaulted_features)
    assert total_count == 18, f"Expected total 18, got {total_count}"
    assert provenance_summary["measured_count"] == len(measured_features)
    assert provenance_summary["derived_count"] == len(derived_features)
    assert provenance_summary["defaulted_count"] == len(defaulted_features)
    assert (
        provenance_summary["measured_count"]
        + provenance_summary["derived_count"]
        + provenance_summary["defaulted_count"]
    ) == 18


# =============================================================================
# STEP 7 — SCENARIO F: INCOMPLETE OASIS INPUT
# =============================================================================

def test_scenario_f_incomplete_oasis_input():
    """
    Scenario F: Clinical reference inference with ONLY Age and EDUC.
    Expected:
    - status == "insufficient_input"
    - probability is None (absent/null)
    - missing_features identifies missing clinical variables (SES, MMSE, eTIV, nWBV, ASF, sex)
    CRITICAL: Age + Education MUST NOT silently produce an OASIS probability.
    """
    print("\n" + "=" * 60)
    print("SCENARIO F: INCOMPLETE OASIS INPUT (AGE + EDUCATION ONLY)")
    print("=" * 60)

    incomplete_input = {"Age": 72.0, "EDUC": 14.0}
    res = predict_clinical_reference(incomplete_input)

    print("\n[Incomplete OASIS Result]")
    print(f"  Status:              {res['status']}")
    print(f"  Probability:         {res['probability']}")
    print(f"  Risk Band:           {res['risk_band']}")
    print(f"  Missing Features:    {res['missing_features']}")
    print(f"  Message:             {res['message']}")

    assert res["status"] == "insufficient_input"
    assert res["probability"] is None
    assert res["risk_band"] == "unavailable"

    # Verify missing features includes required clinical research variables
    expected_missing = {"SES", "MMSE", "eTIV", "nWBV", "ASF", "sex"}
    assert expected_missing.issubset(set(res["missing_features"])), (
        f"Expected {expected_missing} in missing_features, got {res['missing_features']}"
    )

    # Empty inputs test
    res_empty = predict_clinical_reference({})
    assert res_empty["status"] == "insufficient_input"
    assert res_empty["probability"] is None


# =============================================================================
# STEP 8 — SCENARIO G: COMPLETE OASIS INPUT
# =============================================================================

def test_scenario_g_complete_oasis_input():
    """
    Scenario G: Deterministic complete research-model input (fixture only).
    Features: Age, EDUC, SES, MMSE, eTIV, nWBV, ASF, sex.
    Verify:
    - status == "available"
    - model == "OASIS_LogisticRegression"
    - probability is numeric
    - 0 <= probability <= 1
    - risk_band exists
    - explanations exist
    """
    print("\n" + "=" * 60)
    print("SCENARIO G: COMPLETE OASIS INPUT (ALL 8 CLINICAL RESEARCH VARIABLES)")
    print("=" * 60)

    # Deterministic complete research-model input fixture (NOT a real patient)
    complete_input = {
        "Age": 75.0,
        "EDUC": 14.0,
        "SES": 2.0,
        "MMSE": 28.0,
        "eTIV": 1450.0,
        "nWBV": 0.73,
        "ASF": 1.15,
        "sex": "M",
    }
    res = predict_clinical_reference(complete_input)

    print("\n[Complete OASIS Result]")
    print(f"  Status:              {res['status']}")
    print(f"  Model:               {res['model']}")
    print(f"  Probability:         {res['probability']}")
    print(f"  Risk Band:           {res['risk_band']}")
    print(f"  Explanations count:  {len(res['explanations'])}")
    for exp in res["explanations"]:
        print(f"    - {exp['feature']}: raw={exp.get('raw_value')}, contrib={exp.get('contribution_to_logit')}, dir={exp.get('direction')}")

    assert res["status"] == "available"
    assert res["model"] == "OASIS_LogisticRegression"
    assert isinstance(res["probability"], (float, int))
    assert 0.0 <= res["probability"] <= 1.0
    assert res["risk_band"] in ["Low", "Moderate", "High"]
    assert "explanations" in res
    assert len(res["explanations"]) > 0
    assert "research_disclaimer" in res


# =============================================================================
# STEP 9 — SCENARIO H: FUSION SEMANTICS
# =============================================================================

def test_scenario_h_fusion_semantics():
    """
    Scenario H: Signal fusion semantics under 3 conditions:
    A. Behavioral signal only
    B. Clinical signal only
    C. Both signals available
    Verify:
    A: Behavioral available, no fake clinical result.
    B: Clinical available, no fake behavioral result.
    C: Combined result labelled as attention/heuristic indicator;
       NEVER labelled dementia or Alzheimer's probability.
    """
    print("\n" + "=" * 60)
    print("SCENARIO H: MULTI-MODAL SIGNAL FUSION SEMANTICS")
    print("=" * 60)

    # 1. Prepare valid behavioral result (with baseline)
    stable_hist = [
        _make_synthetic_session_vector(wpm=124.0, mean_rt=290.0),
        _make_synthetic_session_vector(wpm=126.0, mean_rt=295.0),
        _make_synthetic_session_vector(wpm=125.0, mean_rt=292.0),
    ]
    curr_vec = _make_synthetic_session_vector(wpm=125.0, mean_rt=293.0)
    behavioral_signal = evaluate_behavioral_anomaly(
        current_features=curr_vec,
        historical_sessions=stable_hist,
        min_history=3,
    )

    # 2. Prepare valid complete clinical result
    complete_clin = {
        "Age": 75.0,
        "EDUC": 14.0,
        "SES": 2.0,
        "MMSE": 28.0,
        "eTIV": 1450.0,
        "nWBV": 0.73,
        "ASF": 1.15,
        "sex": "M",
    }
    clinical_signal = predict_clinical_reference(complete_clin)

    # --- Condition A: Behavioral Signal Only ---
    fusion_a = fuse_cognitive_signals(
        behavioral_anomaly_result=behavioral_signal,
        clinical_reference_result=None,
    )
    print("\n[Condition A: Behavioral Signal Only]")
    print(f"  Behavioral score:    {fusion_a['behavioral_deviation']['score']}")
    print(f"  Behavioral status:   {fusion_a['behavioral_deviation']['status']}")
    print(f"  Clinical status:     {fusion_a['clinical_reference']['status']}")
    print(f"  Clinical prob:       {fusion_a['clinical_reference']['probability']}")
    print(f"  Fusion available:    {fusion_a['overall_attention']['available']}")

    assert fusion_a["behavioral_deviation"]["score"] is not None
    assert fusion_a["behavioral_deviation"]["status"] in ["preliminary_baseline", "longitudinal_baseline"]
    assert fusion_a["clinical_reference"]["probability"] is None
    assert fusion_a["clinical_reference"]["status"] == "insufficient_input"
    assert fusion_a["overall_attention"]["available"] is False
    assert fusion_a["overall_attention"]["heuristic_multimodal_attention_score"] is None

    # --- Condition B: Clinical Signal Only ---
    fusion_b = fuse_cognitive_signals(
        behavioral_anomaly_result=None,
        clinical_reference_result=clinical_signal,
    )
    print("\n[Condition B: Clinical Signal Only]")
    print(f"  Clinical prob:       {fusion_b['clinical_reference']['probability']}")
    print(f"  Clinical status:     {fusion_b['clinical_reference']['status']}")
    print(f"  Behavioral score:    {fusion_b['behavioral_deviation']['score']}")
    print(f"  Behavioral status:   {fusion_b['behavioral_deviation']['status']}")
    print(f"  Fusion available:    {fusion_b['overall_attention']['available']}")

    assert fusion_b["clinical_reference"]["probability"] is not None
    assert fusion_b["clinical_reference"]["status"] == "available"
    assert fusion_b["behavioral_deviation"]["score"] is None
    assert fusion_b["behavioral_deviation"]["status"] == "insufficient_history"
    assert fusion_b["overall_attention"]["available"] is False
    assert fusion_b["overall_attention"]["heuristic_multimodal_attention_score"] is None

    # --- Condition C: Both Signals Available ---
    fusion_c = fuse_cognitive_signals(
        behavioral_anomaly_result=behavioral_signal,
        clinical_reference_result=clinical_signal,
    )
    oa_c = fusion_c["overall_attention"]
    print("\n[Condition C: Both Signals Available]")
    print(f"  Fusion Available:    {oa_c['available']}")
    print(f"  Attention Score:     {oa_c['heuristic_multimodal_attention_score']}")
    print(f"  Attention Label:     {oa_c['label']}")
    print(f"  Attention Method:    {oa_c['method']}")
    print(f"  Disclaimer:          {oa_c['disclaimer']}")

    assert oa_c["available"] is True
    assert isinstance(oa_c["heuristic_multimodal_attention_score"], float)
    assert 0.0 <= oa_c["heuristic_multimodal_attention_score"] <= 1.0
    assert oa_c["method"] == "heuristic_multimodal_attention_score"

    # Strict labeling checks: MUST NOT be called dementia/Alzheimer's probability
    label_lower = oa_c["label"].lower()
    assert "dementia" not in label_lower, f"Prohibited term in label: {oa_c['label']}"
    assert "alzheimer" not in label_lower, f"Prohibited term in label: {oa_c['label']}"
    assert "probability" not in label_lower, f"Prohibited term in label: {oa_c['label']}"

    assert "dementia_probability" not in fusion_c
    assert "alzheimers_probability" not in fusion_c


# =============================================================================
# STEP 10 — RUNTIME API NON-DIAGNOSTIC SEMANTICS AUDIT
# =============================================================================

def test_scenario_non_diagnostic_api_semantics(client):
    """
    Runtime API audit on /api/analyze to ensure no prohibited disease probability
    terminology is returned and legacy deprecated fields do not contain fabricated data.
    """
    print("\n" + "=" * 60)
    print("RUNTIME API AUDIT: NON-DIAGNOSTIC SEMANTICS")
    print("=" * 60)

    payload = {
        "speech": {"wpm": 122.0, "pause_ratio": 0.15, "speech_start_delay": 0.6},
        "memory": {
            "word_recall_accuracy": 82.0,
            "pattern_accuracy": 78.0,
            "delayed_recall_accuracy": 75.0,
            "recall_latency_seconds": 3.2,
            "order_match_ratio": 0.85,
            "intrusion_count": 1,
        },
        "reaction": {"times": [295.0, 310.0, 285.0, 300.0], "miss_count": 0},
        "stroop": {"total_trials": 20, "error_count": 1, "mean_rt": 550.0},
        "tap": {"intervals": [205.0, 210.0, 202.0, 208.0], "tap_count": 4},
        "profile": {"age": 70, "education_level": 3},
    }

    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    ml_analysis = data.get("ml_analysis", {})
    behavioral = ml_analysis.get("behavioral_deviation", {})

    print("\n[API Behavioral Terminology Audit]")
    print(f"  Terminology:         {behavioral.get('terminology')}")
    print(f"  Score description:   {behavioral.get('score_description')}")

    assert behavioral.get("terminology") == "Cognitive Performance Deviation"
    if behavioral.get("score_description"):
        desc = behavioral["score_description"].lower()
        assert "not a dementia" in desc or "not a dementia or alzheimer's" in desc

    oa = ml_analysis.get("overall_attention", {})
    if oa.get("label"):
        oa_lbl = oa["label"].lower()
        assert "alzheimer" not in oa_lbl
        assert "dementia" not in oa_lbl
        assert "diagnosis" not in oa_lbl

    # Deprecated compatibility fields must be None when research inputs are incomplete
    assert data.get("alzheimers_risk") is None
    assert data.get("dementia_risk") is None
    assert data.get("parkinsons_risk") is None


# =============================================================================
# PRELIMINARY BASELINE FALSE-POSITIVE REGRESSION TEST SUITE
# =============================================================================

def test_preliminary_baseline_does_not_false_positive_on_small_variation():
    """
    Regression Test 1:
    Stable patient with low sample variance during preliminary baseline.
    Baseline WPM: 124, 126, 125
    Session 4 WPM: 123
    Expected: NOT significant/severe solely from WPM. Must remain conservative (none or mild).
    """
    print("\n" + "=" * 60)
    print("REGRESSION 1: PRELIMINARY BASELINE LOW-VARIANCE FALSE POSITIVE GUARD")
    print("=" * 60)

    h1 = _make_synthetic_session_vector(wpm=124.0)
    h2 = _make_synthetic_session_vector(wpm=126.0)
    h3 = _make_synthetic_session_vector(wpm=125.0)
    current = _make_synthetic_session_vector(wpm=123.0)

    res = evaluate_behavioral_anomaly(
        current_features=current,
        historical_sessions=[h1, h2, h3],
        min_history=3,
    )

    print("\n[Result for WPM 124/126/125 -> 123]")
    print(f"  Status:              {res['status']}")
    print(f"  Anomaly detected:    {res['anomaly_detected']}")
    print(f"  Severity:            {res['severity']}")
    print(f"  Anomaly score:       {res['anomaly_score']}")
    print(f"  Top deviations:      {[d['feature'] + ': z=' + str(d['z_score']) for d in res.get('top_deviating_features', [])]}")

    assert res["status"] == "preliminary_baseline"
    assert res["anomaly_detected"] is False, f"False positive detected: {res}"
    assert res["severity"] in ["none", "mild"], f"Unexpected high severity: {res['severity']}"
    assert res["severity"] not in ["significant", "severe"], f"Prohibited escalation on minor variation: {res['severity']}"


def test_preliminary_baseline_still_detects_large_change():
    """
    Regression Test 2:
    Preliminary baseline (3 sessions: 125, 124, 126 WPM).
    Session 4: Large genuine deterioration to 80 WPM.
    Expected: Meaningful anomaly remains detectable (anomaly_detected=True, wpm in deviations).
    """
    print("\n" + "=" * 60)
    print("REGRESSION 2: PRELIMINARY BASELINE GENUINE LARGE DETERIORATION")
    print("=" * 60)

    h1 = _make_synthetic_session_vector(wpm=125.0)
    h2 = _make_synthetic_session_vector(wpm=124.0)
    h3 = _make_synthetic_session_vector(wpm=126.0)
    current_degraded = _make_synthetic_session_vector(wpm=80.0)

    res = evaluate_behavioral_anomaly(
        current_features=current_degraded,
        historical_sessions=[h1, h2, h3],
        min_history=3,
    )

    print("\n[Result for WPM 125/124/126 -> 80]")
    print(f"  Status:              {res['status']}")
    print(f"  Anomaly detected:    {res['anomaly_detected']}")
    print(f"  Severity:            {res['severity']}")
    print(f"  Anomaly score:       {res['anomaly_score']}")
    print(f"  Top deviations:      {[d['feature'] + ': z=' + str(d['z_score']) for d in res.get('top_deviating_features', [])]}")

    assert res["status"] == "preliminary_baseline"
    assert res["anomaly_detected"] is True, "Large change was not detected"
    assert res["severity"] in ["mild", "significant", "severe"]
    top_features = [d["feature"] for d in res["top_deviating_features"]]
    assert "wpm" in top_features, f"WPM not found in top deviations: {top_features}"


def test_multi_feature_decline_remains_detectable():
    """
    Regression Test 3:
    Simulate multi-domain deterioration during preliminary baseline:
    Memory drops substantially + Reaction time slows substantially + Speech slows.
    Expected: Significant or severe deviation remains possible.
    """
    print("\n" + "=" * 60)
    print("REGRESSION 3: MULTI-FEATURE / MULTI-DOMAIN DECLINE")
    print("=" * 60)

    h1 = _make_synthetic_session_vector(wpm=125.0, word_recall=85.0, delayed_recall=80.0, mean_rt=290.0)
    h2 = _make_synthetic_session_vector(wpm=124.0, word_recall=84.0, delayed_recall=79.0, mean_rt=295.0)
    h3 = _make_synthetic_session_vector(wpm=126.0, word_recall=86.0, delayed_recall=81.0, mean_rt=292.0)

    # Multi-domain collapse
    current_multi_drop = _make_synthetic_session_vector(
        wpm=85.0,
        word_recall=30.0,
        delayed_recall=20.0,
        intrusions=6,
        recall_latency=8.5,
        mean_rt=750.0,
        miss_count=4,
    )

    res = evaluate_behavioral_anomaly(
        current_features=current_multi_drop,
        historical_sessions=[h1, h2, h3],
        min_history=3,
    )

    print("\n[Result for Multi-Domain Drop (Memory + Reaction + Speech)]")
    print(f"  Status:              {res['status']}")
    print(f"  Anomaly detected:    {res['anomaly_detected']}")
    print(f"  Severity:            {res['severity']}")
    print(f"  Anomaly score:       {res['anomaly_score']}")
    print("  Top deviating features:")
    for f in res["top_deviating_features"]:
        print(f"    - {f['feature']}: z={f['z_score']}, dir={f['direction']}, adverse={f['is_adverse']}")

    assert res["status"] == "preliminary_baseline"
    assert res["anomaly_detected"] is True
    assert res["severity"] in ["significant", "severe"], f"Expected significant or severe, got {res['severity']}"


def test_mature_baseline_retains_sensitivity():
    """
    Regression Test 4:
    Use at least 5 baseline sessions (mature longitudinal baseline).
    Introduce substantial deterioration.
    Expected: Existing longitudinal anomaly detection remains fully sensitive and effective.
    """
    print("\n" + "=" * 60)
    print("REGRESSION 4: MATURE LONGITUDINAL BASELINE SENSITIVITY (5+ SESSIONS)")
    print("=" * 60)

    history_5 = [
        _make_synthetic_session_vector(wpm=125.0, word_recall=85.0, delayed_recall=80.0, mean_rt=290.0),
        _make_synthetic_session_vector(wpm=124.0, word_recall=84.0, delayed_recall=79.0, mean_rt=295.0),
        _make_synthetic_session_vector(wpm=126.0, word_recall=86.0, delayed_recall=81.0, mean_rt=292.0),
        _make_synthetic_session_vector(wpm=125.0, word_recall=85.0, delayed_recall=80.0, mean_rt=294.0),
        _make_synthetic_session_vector(wpm=123.0, word_recall=87.0, delayed_recall=82.0, mean_rt=291.0),
    ]

    # Acute memory drop on mature baseline
    current_drop = _make_synthetic_session_vector(
        wpm=124.0,
        word_recall=35.0,
        delayed_recall=25.0,
        intrusions=5,
        recall_latency=7.5,
        mean_rt=293.0,
    )

    res = evaluate_behavioral_anomaly(
        current_features=current_drop,
        historical_sessions=history_5,
        min_history=3,
    )

    print("\n[Result for Mature Baseline (5 sessions) + Memory Drop]")
    print(f"  Status:              {res['status']}")
    print(f"  Anomaly detected:    {res['anomaly_detected']}")
    print(f"  Severity:            {res['severity']}")
    print(f"  Anomaly score:       {res['anomaly_score']}")
    print("  Top deviating features:")
    for f in res["top_deviating_features"]:
        print(f"    - {f['feature']}: z={f['z_score']}, dir={f['direction']}, adverse={f['is_adverse']}")

    assert res["status"] == "longitudinal_baseline"
    assert res["anomaly_detected"] is True
    assert res["severity"] in ["significant", "severe"]
    top_features = [d["feature"] for d in res["top_deviating_features"]]
    assert any(f in top_features for f in ["immediate_recall_accuracy", "delayed_recall_accuracy", "intrusion_count", "recall_latency"])


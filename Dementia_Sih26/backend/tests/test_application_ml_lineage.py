"""
backend/tests/test_application_ml_lineage.py
============================================
End-to-End Application Data Lineage and Behavioral Validation Test Suite.

Validates the full pipeline flow:
5 Test Modalities (Speech, Memory, Reaction, Stroop, Tap)
-> Raw assessment results
-> Feature extraction (ai_service.py)
-> Canonical 18-feature vector (schemas.py FeatureVector)
-> Feature provenance (compute_feature_provenance)
-> Behavioral ML anomaly detection (core/behavioral_ml.py)
-> Signal fusion (core/signal_fusion.py)
-> API response (AnalyzeResponse)
-> Frontend-consumable data contract (UserDashboard, ResultsPage, DoctorDashboard, etc.)

ALL TEST DATA USE DETERMINISTIC SYNTHETIC APPLICATION FIXTURES ONLY.
THEY DO NOT REPRESENT REAL PATIENTS OR CLINICAL SAMPLES.
"""

from __future__ import annotations

import os
import sys
import json
import pytest

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend", "src")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from fastapi.testclient import TestClient
from main import app
from core.behavioral_ml import (
    FEATURE_NAMES,
    FEATURE_NORMALIZATION_SCALES,
    evaluate_behavioral_anomaly,
    normalize_feature_vector,
    extract_raw_vector_dict,
)
from core.signal_fusion import fuse_cognitive_signals
from services.ai_service import (
    build_feature_vector,
    compute_feature_provenance,
    extract_speech_features,
    extract_memory_features,
    extract_reaction_features,
    extract_executive_features,
    extract_motor_features,
)
from models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    FeatureVector,
)
from tests.fixtures.cognitive_sessions import (
    get_patient_a_stable_sessions,
    get_patient_b_memory_decline_sessions,
    get_patient_c_reaction_decline_sessions,
    get_patient_d_partial_session,
)


@pytest.fixture
def client():
    return TestClient(app)


# =============================================================================
# STEP 1 & 3: FULL 18-FEATURE TRACEABILITY & NORMALIZATION AUDIT
# =============================================================================

def test_trace_all_18_features_lineage():
    """
    Step 1 & Step 3:
    Verify the complete extraction lineage for all 18 features from raw assessment inputs:
    Test Input -> Extractor -> Feature Name -> Normalization Range -> Provenance.
    """
    print("\n" + "=" * 80)
    print("STEP 1 & 3: CANONICAL 18-FEATURE DATA LINEAGE & NORMALIZATION TABLE")
    print("=" * 80)

    # Use a complete stable session fixture
    session = get_patient_a_stable_sessions()[0]

    # 1. Execute individual extractors
    _, speech_f = extract_speech_features(session.speech_audio, session.speech)
    _, memory_f = extract_memory_features(session.memory_results, session.memory)
    _, reaction_f = extract_reaction_features(session.reaction_times, session.reaction)
    _, executive_f = extract_executive_features(session.stroop)
    _, motor_f = extract_motor_features(session.tap)

    # 2. Build 18-feature vector
    fv = build_feature_vector(speech_f, memory_f, reaction_f, executive_f, motor_f)
    raw_dict = fv.model_dump()

    # 3. Compute provenance
    prov, categorized, counts = compute_feature_provenance(
        audio_b64=session.speech_audio,
        speech=session.speech,
        memory_results=session.memory_results,
        memory=session.memory,
        reaction_times=session.reaction_times,
        reaction=session.reaction,
        stroop=session.stroop,
        tap=session.tap,
    )

    # 4. Compute normalized values [0, 1]
    norm_vec = normalize_feature_vector(raw_dict)

    feature_source_map = {
        # Speech
        "wpm": ("Speech Assessment", "speech.wpm"),
        "speed_deviation": ("Speech Assessment", "speech.speed_deviation"),
        "speech_variability": ("Speech Assessment", "speech.speech_speed_variability"),
        "pause_ratio": ("Speech Assessment", "speech.pause_ratio"),
        "speech_start_delay": ("Speech Assessment", "speech.speech_start_delay"),
        # Memory
        "immediate_recall_accuracy": ("Memory Assessment", "memory.word_recall_accuracy"),
        "delayed_recall_accuracy": ("Memory Assessment", "memory.delayed_recall_accuracy"),
        "intrusion_count": ("Memory Assessment", "memory.intrusion_count"),
        "recall_latency": ("Memory Assessment", "memory.recall_latency_seconds"),
        "order_match_ratio": ("Memory Assessment", "memory.order_match_ratio"),
        # Reaction
        "mean_rt": ("Reaction Assessment", "reaction.times (mean)"),
        "std_rt": ("Reaction Assessment", "reaction.times (std)"),
        "min_rt": ("Reaction Assessment", "reaction.times (min)"),
        "reaction_drift": ("Reaction Assessment", "reaction.times (half-diff)"),
        "miss_count": ("Reaction Assessment", "reaction.miss_count"),
        # Executive
        "stroop_error_rate": ("Stroop Assessment", "stroop.error_count / total"),
        "stroop_rt": ("Stroop Assessment", "stroop.mean_rt / incongruent_rt"),
        # Motor
        "tap_interval_std": ("Motor Tap Assessment", "tap.intervals (std)"),
    }

    header = f"{'Feature':<28} | {'Source Assessment':<20} | {'Raw Extracted':<12} | {'Norm [0-1]':<10} | {'Scale Range':<16} | {'Provenance':<10}"
    print(header)
    print("-" * len(header))

    assert len(FEATURE_NAMES) == 18, f"Expected exactly 18 canonical features, got {len(FEATURE_NAMES)}"
    assert len(raw_dict) == 18, f"Feature vector contains {len(raw_dict)} features"

    for idx, name in enumerate(FEATURE_NAMES):
        src_test, _ = feature_source_map[name]
        raw_val = raw_dict[name]
        norm_val = round(float(norm_vec[idx]), 3)
        scale_min, scale_max = FEATURE_NORMALIZATION_SCALES[name]
        scale_str = f"({scale_min}, {scale_max})"
        p_status = prov.get(name, "unknown")

        print(f"{name:<28} | {src_test:<20} | {raw_val:<12} | {norm_val:<10} | {scale_str:<16} | {p_status:<10}")

        # Assertions on feature integrity
        assert name in raw_dict
        assert name in prov
        assert p_status == "measured"
        assert 0.0 <= norm_val <= 2.0


# =============================================================================
# STEP 2: PATIENT A — STABLE APPLICATION SESSIONS
# =============================================================================

def test_patient_a_stable_lineage(client):
    """
    Patient A: 5 realistic application sessions with stable performance.
    Flows through /api/analyze:
    - 18 features generated per session.
    - All test-derived features marked 'measured'.
    - First sessions establish baseline.
    - No severe behavioral deviation.
    - Overall attention remains Routine/stable.
    - No disease probability generated.
    """
    print("\n" + "=" * 80)
    print("STEP 2: PATIENT A — STABLE APPLICATION SESSIONS (CHRONOLOGICAL)")
    print("=" * 80)

    sessions = get_patient_a_stable_sessions()
    assert len(sessions) == 5

    from services import auth_service
    test_user_id = "test_patient_a_lineage"
    users = auth_service.get_users()
    users[test_user_id] = {
        "id": test_user_id,
        "email": "patient_a@test.com",
        "full_name": "Patient A Lineage",
        "role": "patient",
    }
    auth_service.users_store.write(users)

    # Clean prior test results for this user if any
    results = auth_service.results_store.read()
    results[test_user_id] = []
    auth_service.results_store.write(results)

    raw_token = auth_service.create_session_for_user(test_user_id)
    headers = {"Authorization": f"Bearer {raw_token}"}

    for idx, session in enumerate(sessions, start=1):
        # Direct API submission with user auth token to test persistent longitudinal history
        resp = client.post("/api/analyze", json=session.model_dump(), headers=headers)
        assert resp.status_code == 200, f"Analysis failed: {resp.text}"
        data = resp.json()

        # Extract behavioral analysis
        ml_analysis = data["ml_analysis"]
        beh = ml_analysis["behavioral_deviation"]
        oa = ml_analysis["overall_attention"]
        provenance = data["feature_provenance"]
        prov_summary = data["provenance_summary"]

        print(f"\n[Patient A - Session {idx}/5]")
        print(f"  Domain scores:       Speech={data['speech_score']}, Memory={data['memory_score']}, Reaction={data['reaction_score']}, Executive={data['executive_score']}, Motor={data['motor_score']}")
        print(f"  Status:              {beh['status']}")
        print(f"  Anomaly detected:    {beh['anomaly_detected']}")
        print(f"  Severity:            {beh['severity']}")
        print(f"  Anomaly score:       {beh['anomaly_score']}")
        print(f"  Provenance summary:  {prov_summary}")

        # Invariant 1: 18 features generated
        assert len(data["feature_vector"]) == 18

        # Invariant 2: In complete assessment, all features are measured
        assert prov_summary["defaulted_count"] == 0
        assert prov_summary["measured_count"] == 18

        # Invariant 3: History progression & anomaly safety
        if idx in (1, 2, 3):
            assert beh["status"] == "insufficient_history"
            assert beh["anomaly_detected"] is False
        elif idx in (4, 5):
            assert beh["status"] in ["preliminary_baseline", "longitudinal_baseline"]
            # After preliminary baseline fix, stable patient exhibits no false alert
            assert beh["severity"] in ["none", "mild"]
            assert beh["severity"] != "severe"
            assert beh["anomaly_detected"] is False

        # Invariant 4: Overall attention must not be Elevated
        if oa["available"] and oa["label"]:
            assert "elevated" not in oa["label"].lower()
            assert "high" not in oa["label"].lower()

        # Invariant 5: No disease probabilities
        assert data.get("alzheimers_risk") is None
        assert data.get("dementia_risk") is None
        assert data.get("parkinsons_risk") is None
        assert "dementia_probability" not in beh
        assert "alzheimers_probability" not in beh


# =============================================================================
# STEP 2: PATIENT B — MEMORY DECLINE APPLICATION SESSIONS
# =============================================================================

def test_patient_b_memory_decline_lineage():
    """
    Patient B: 5 realistic application sessions.
    Sessions 1-3: Stable memory baseline.
    Sessions 4-5: Substantial deterioration in memory performance.
    Other domains remain approximately stable.
    Verify:
    - Memory-derived behavioral features change appropriately.
    - Behavioral deviation detects longitudinal change.
    - Memory-related features appear among top deviations.
    - Output remains strictly non-diagnostic.
    """
    print("\n" + "=" * 80)
    print("STEP 2: PATIENT B — MEMORY DECLINE APPLICATION LINEAGE")
    print("=" * 80)

    sessions = get_patient_b_memory_decline_sessions()
    assert len(sessions) == 5

    # Extract 18-feature vectors through production extractor
    feature_vectors = []
    for s in sessions:
        _, sf = extract_speech_features(s.speech_audio, s.speech)
        _, mf = extract_memory_features(s.memory_results, s.memory)
        _, rf = extract_reaction_features(s.reaction_times, s.reaction)
        _, ef = extract_executive_features(s.stroop)
        _, mof = extract_motor_features(s.tap)
        fv = build_feature_vector(sf, mf, rf, ef, mof)
        feature_vectors.append(fv.model_dump())

    # Sessions 1-3 establish baseline
    baseline_history = feature_vectors[:3]

    # Evaluate Session 4 (Acute drop)
    res_4 = evaluate_behavioral_anomaly(
        current_features=feature_vectors[3],
        historical_sessions=baseline_history,
        min_history=3,
    )

    print("\n[Patient B - Session 4 (First Memory Drop)]")
    print(f"  Status:              {res_4['status']}")
    print(f"  Anomaly detected:    {res_4['anomaly_detected']}")
    print(f"  Severity:            {res_4['severity']}")
    print(f"  Anomaly score:       {res_4['anomaly_score']}")
    print("  Top deviating features:")
    for f in res_4["top_deviating_features"]:
        print(f"    - {f['feature']}: z={f['z_score']}, dir={f['direction']}, adverse={f['is_adverse']}")

    # Evaluate Session 5 (Sustained severe drop)
    history_with_4 = feature_vectors[:4]
    res_5 = evaluate_behavioral_anomaly(
        current_features=feature_vectors[4],
        historical_sessions=history_with_4,
        min_history=3,
    )

    print("\n[Patient B - Session 5 (Sustained Memory Drop)]")
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

    memory_feature_names = {
        "delayed_recall_accuracy",
        "immediate_recall_accuracy",
        "order_match_ratio",
        "intrusion_count",
        "recall_latency",
    }
    top_4_names = [d["feature"] for d in res_4["top_deviating_features"]]
    top_5_names = [d["feature"] for d in res_5["top_deviating_features"]]

    assert any(f in memory_feature_names for f in top_4_names), f"Memory features missing in {top_4_names}"
    assert any(f in memory_feature_names for f in top_5_names), f"Memory features missing in {top_5_names}"

    # Non-diagnostic verification
    for res in (res_4, res_5):
        assert "dementia_probability" not in res
        assert "alzheimers_probability" not in res
        assert "diagnosis" not in res
        assert res["terminology"] == "Cognitive Performance Deviation"


# =============================================================================
# STEP 2: PATIENT C — REACTION DECLINE APPLICATION SESSIONS
# =============================================================================

def test_patient_c_reaction_decline_lineage():
    """
    Patient C: 5 realistic application sessions.
    Sessions 1-3: Stable reaction latency (~290ms, 0 misses).
    Sessions 4-5: Substantially slower reaction times (>780ms, misses).
    Other domains remain approximately stable.
    Verify:
    - Reaction features change correctly.
    - Behavioral deviation responds to the deterioration.
    - No disease diagnosis is generated.
    """
    print("\n" + "=" * 80)
    print("STEP 2: PATIENT C — REACTION DECLINE APPLICATION LINEAGE")
    print("=" * 80)

    sessions = get_patient_c_reaction_decline_sessions()
    assert len(sessions) == 5

    feature_vectors = []
    for s in sessions:
        _, sf = extract_speech_features(s.speech_audio, s.speech)
        _, mf = extract_memory_features(s.memory_results, s.memory)
        _, rf = extract_reaction_features(s.reaction_times, s.reaction)
        _, ef = extract_executive_features(s.stroop)
        _, mof = extract_motor_features(s.tap)
        fv = build_feature_vector(sf, mf, rf, ef, mof)
        feature_vectors.append(fv.model_dump())

    baseline_history = feature_vectors[:3]

    res_4 = evaluate_behavioral_anomaly(
        current_features=feature_vectors[3],
        historical_sessions=baseline_history,
        min_history=3,
    )

    print("\n[Patient C - Session 4 (Reaction Slowing & Misses)]")
    print(f"  Status:              {res_4['status']}")
    print(f"  Anomaly detected:    {res_4['anomaly_detected']}")
    print(f"  Severity:            {res_4['severity']}")
    print(f"  Anomaly score:       {res_4['anomaly_score']}")
    print("  Top deviating features:")
    for f in res_4["top_deviating_features"]:
        print(f"    - {f['feature']}: z={f['z_score']}, dir={f['direction']}, adverse={f['is_adverse']}")

    history_with_4 = feature_vectors[:4]
    res_5 = evaluate_behavioral_anomaly(
        current_features=feature_vectors[4],
        historical_sessions=history_with_4,
        min_history=3,
    )

    print("\n[Patient C - Session 5 (Sustained Reaction Slowing)]")
    print(f"  Status:              {res_5['status']}")
    print(f"  Anomaly detected:    {res_5['anomaly_detected']}")
    print(f"  Severity:            {res_5['severity']}")
    print(f"  Anomaly score:       {res_5['anomaly_score']}")
    print("  Top deviating features:")
    for f in res_5["top_deviating_features"]:
        print(f"    - {f['feature']}: z={f['z_score']}, dir={f['direction']}, adverse={f['is_adverse']}")

    assert res_4["anomaly_detected"] is True
    assert res_4["severity"] in ["significant", "severe"]
    assert res_5["anomaly_detected"] is True
    assert res_5["severity"] in ["significant", "severe"]

    reaction_features = {"mean_rt", "std_rt", "min_rt", "reaction_drift", "miss_count"}
    top_4_names = [d["feature"] for d in res_4["top_deviating_features"]]
    top_5_names = [d["feature"] for d in res_5["top_deviating_features"]]

    assert any(f in reaction_features for f in top_4_names), f"Reaction features missing in {top_4_names}"
    assert any(f in reaction_features for f in top_5_names), f"Reaction features missing in {top_5_names}"

    for res in (res_4, res_5):
        assert "dementia_probability" not in res
        assert "alzheimers_probability" not in res
        assert "diagnosis" not in res
        assert res["terminology"] == "Cognitive Performance Deviation"


# =============================================================================
# STEP 2: PATIENT D — PARTIAL ASSESSMENT & FEATURE PROVENANCE
# =============================================================================

def test_patient_d_partial_assessment_provenance(client):
    """
    Patient D: Deliberately partial assessment (Memory & Reaction supplied, Speech/Stroop/Tap omitted).
    Flows through /api/analyze:
    - feature_provenance inspected.
    - measured_features, derived_features, defaulted_features verified.
    - Provenance counts verified.
    - CRITICAL: Features originating from omitted tests are NEVER marked 'measured'.
    """
    print("\n" + "=" * 80)
    print("STEP 2: PATIENT D — PARTIAL ASSESSMENT PROVENANCE VERIFICATION")
    print("=" * 80)

    session = get_patient_d_partial_session()
    resp = client.post("/api/analyze", json=session.model_dump())
    assert resp.status_code == 200, f"Analysis failed: {resp.text}"
    data = resp.json()

    feature_provenance = data["feature_provenance"]
    measured_features = data["measured_features"]
    derived_features = data["derived_features"]
    defaulted_features = data["defaulted_features"]
    provenance_summary = data["provenance_summary"]

    print("\n[Patient D Provenance Breakdown]")
    print(f"  Measured ({len(measured_features)}):   {measured_features}")
    print(f"  Derived ({len(derived_features)}):    {derived_features}")
    print(f"  Defaulted ({len(defaulted_features)}):  {defaulted_features}")
    print(f"  Summary counts:       {provenance_summary}")

    # 1. Total features must be exactly 18
    assert len(feature_provenance) == 18
    assert (len(measured_features) + len(derived_features) + len(defaulted_features)) == 18

    # 2. Supplied tests (Memory, Reaction) produce measured features
    expected_measured = [
        "immediate_recall_accuracy",
        "delayed_recall_accuracy",
        "intrusion_count",
        "recall_latency",
        "order_match_ratio",
        "mean_rt",
        "std_rt",
        "min_rt",
        "reaction_drift",
        "miss_count",
    ]
    for feat in expected_measured:
        assert feature_provenance[feat] == "measured", f"Expected {feat} to be measured, got {feature_provenance[feat]}"
        assert feat in measured_features

    # 3. CRITICAL: Omitted tests (Speech, Stroop, Tap) MUST NEVER be labeled 'measured'
    omitted_features = [
        "wpm",
        "speed_deviation",
        "speech_variability",
        "pause_ratio",
        "speech_start_delay",
        "stroop_error_rate",
        "stroop_rt",
        "tap_interval_std",
    ]
    for feat in omitted_features:
        assert feature_provenance[feat] != "measured", f"CRITICAL BUG: Omitted feature {feat} was labeled measured"
        assert feat not in measured_features, f"Omitted feature {feat} found in measured_features list"
        assert feature_provenance[feat] == "defaulted", f"Expected {feat} to be defaulted, got {feature_provenance[feat]}"
        assert feat in defaulted_features


# =============================================================================
# STEP 4: FRONTEND CONTRACT INTEGRITY AUDIT
# =============================================================================

def test_frontend_contract_integrity():
    """
    Step 4: Trace the actual API response consumed by frontend components:
    - UserDashboard
    - ResultsPage
    - ProgressPage
    - DoctorDashboard
    - DoctorHome
    - PatientDetail
    Verify that components consume:
    - ml_analysis
    - overall_attention
    - behavioral_deviation
    - domain performance
    - clinical reference status
    - feature provenance
    And do NOT depend on deprecated disease fields (alzheimers_risk, dementia_risk, parkinsons_risk, risk_levels).
    """
    print("\n" + "=" * 80)
    print("STEP 4: FRONTEND DATA CONTRACT AUDIT")
    print("=" * 80)

    frontend_pages = {
        "UserDashboard": os.path.join(FRONTEND_DIR, "pages", "UserDashboard.jsx"),
        "ResultsPage": os.path.join(FRONTEND_DIR, "pages", "ResultsPage.jsx"),
        "ProgressPage": os.path.join(FRONTEND_DIR, "pages", "ProgressPage.jsx"),
        "DoctorDashboard": os.path.join(FRONTEND_DIR, "pages", "DoctorDashboard.jsx"),
        "DoctorHome": os.path.join(FRONTEND_DIR, "pages", "DoctorHome.jsx"),
        "PatientDetail": os.path.join(FRONTEND_DIR, "pages", "PatientDetail.jsx"),
    }

    deprecated_prohibited_terms = [
        "alzheimers_risk",
        "dementia_risk",
        "parkinsons_risk",
        "risk_levels",
    ]

    for component_name, path in frontend_pages.items():
        assert os.path.exists(path), f"Frontend component file not found: {path}"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Audit prohibited deprecated keys
        for dep in deprecated_prohibited_terms:
            assert dep not in content, f"Deprecated field '{dep}' found in frontend component: {component_name}"

        print(f"  [OK] {component_name:<16} -> Clean of deprecated disease risk fields")

    # Specific component assertions:
    # 1. UserDashboard: uses domain scores + ml_analysis
    with open(frontend_pages["UserDashboard"], "r", encoding="utf-8") as f:
        u_content = f.read()
    assert "memory_score" in u_content
    assert "executive_score" in u_content
    assert "reaction_score" in u_content
    assert "ml_analysis" in u_content
    assert "overall_attention" in u_content

    # 2. ResultsPage: uses domain scores + composite index + feature_vector (and no deprecated disease risks)
    with open(frontend_pages["ResultsPage"], "r", encoding="utf-8") as f:
        r_content = f.read()
    assert "memory_score" in r_content
    assert "reaction_score" in r_content
    assert "composite_risk_score" in r_content
    assert "feature_vector" in r_content

    # 3. ProgressPage: uses longitudinal domain scores + composite_risk_score
    with open(frontend_pages["ProgressPage"], "r", encoding="utf-8") as f:
        pr_content = f.read()
    assert "memory_score" in pr_content
    assert "speech_score" in pr_content
    assert "reaction_score" in pr_content
    assert "composite_risk_score" in pr_content

    # 4. DoctorDashboard & DoctorHome: consume overall_attention and behavioral_deviation
    with open(frontend_pages["DoctorDashboard"], "r", encoding="utf-8") as f:
        d_content = f.read()
    assert "overall_attention" in d_content
    assert "behavioral_deviation" in d_content

    with open(frontend_pages["DoctorHome"], "r", encoding="utf-8") as f:
        dh_content = f.read()
    assert "overall_attention" in dh_content
    assert "behavioral_deviation" in dh_content

    # 5. PatientDetail: displays overall attention, behavioral deviation, and domain scores
    with open(frontend_pages["PatientDetail"], "r", encoding="utf-8") as f:
        p_content = f.read()
    assert "Overall Attention" in p_content
    assert "Behavioral Deviation" in p_content
    assert "ml_analysis" in p_content

    print("  [OK] All 6 frontend components adhere strictly to the non-diagnostic ML data contract.")

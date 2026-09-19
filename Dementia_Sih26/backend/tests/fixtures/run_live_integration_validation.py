"""
run_live_integration_validation.py
==================================
Comprehensive live validation script executing against the running NeuroAid
backend (http://127.0.0.1:8000) and checking database, ML states, and frontend contracts.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.error
from typing import Any, Dict

# Ensure backend and project root are on sys.path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
for p in [BACKEND_DIR, PROJECT_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)

BASE_URL = "http://127.0.0.1:8000/api"
DOCTOR_TOKEN = "sih_demo_doctor_token_deterministic_2026"
CAREGIVER_TOKEN = "sih_demo_caregiver_token_deterministic_2026"

def request_json(path: str, method: str = "GET", body: Any = None, token: str | None = None) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    print("=" * 80)
    print("LIVE APPLICATION VALIDATION SUITE")
    print("=" * 80)

    # 1. Reset and Seed
    print("\n[Step 1 & 2] Triggering POST /demo/reset-and-seed...")
    seed_res = request_json("/demo/reset-and-seed", method="POST")
    print("Seed Status:", seed_res.get("status"))
    personas = seed_res.get("longitudinal_personas", {})
    print(f"Longitudinal Personas seeded: {list(personas.keys())}")

    # 2. Verify Doctor Patients List
    print("\n[Step 3, 4, 5] Verifying GET /auth/patients for demo doctor...")
    doc_res = request_json("/auth/patients", token=DOCTOR_TOKEN)
    patients = doc_res.get("patients", [])
    print(f"Total Enrolled Patients returned: {len(patients)}")

    # Priority mapping matching DoctorDashboard.jsx
    def get_attention_priority(p):
        r = p.get("lastResult")
        bd = r.get("ml_analysis", {}).get("behavioral_deviation", {}) if r else {}
        if not r or p.get("sessionCount", 0) < 3 or bd.get("status") == "insufficient_history":
            return "Pending Assessment"
        oa = r.get("ml_analysis", {}).get("overall_attention", {})
        if oa.get("available") and oa.get("label"):
            lbl = oa["label"].lower()
            if "high" in lbl or "elevated" in lbl:
                return "Elevated Attention"
            if "moderate" in lbl:
                return "Moderate Attention"
            return "Routine Attention"
        sev = bd.get("severity")
        if sev in ("severe", "significant"):
            return "Elevated Attention"
        if sev == "mild":
            return "Moderate Attention"
        if sev == "none":
            return "Routine Attention"
        return "Pending Assessment"

    counts = {
        "Total": len(patients),
        "Elevated Attention": 0,
        "Moderate Attention": 0,
        "Routine Attention": 0,
        "Pending Assessment": 0,
    }

    persona_results = {}

    for p in patients:
        prio = get_attention_priority(p)
        counts[prio] = counts.get(prio, 0) + 1
        pid = p["id"]
        last = p.get("lastResult")
        ml = last.get("ml_analysis", {}) if last else {}
        beh = ml.get("behavioral_deviation", {})
        oa = ml.get("overall_attention", {})
        clin = ml.get("clinical_reference", {})
        
        print(f"\n  Patient: {p['full_name']} ({pid})")
        print(f"    Sessions: {p.get('sessionCount')}")
        print(f"    Derived Priority: {prio}")
        print(f"    Behavioral Status: {beh.get('status')}, Severity: {beh.get('severity')}, Anomaly Detected: {beh.get('anomaly_detected')}")
        print(f"    Clinical Ref Status: {clin.get('status')}, Probability: {clin.get('probability')}")
        if beh.get("top_deviating_features"):
            top_feats = [f"{f['feature']} (z: {f.get('z_score', 0)})" for f in beh.get("top_deviating_features", [])]
            print(f"    Top Deviating Features: {', '.join(top_feats)}")

        for letter in ["A", "B", "C", "D", "E"]:
            if f"patient-{letter.lower()}" in pid:
                persona_results[letter] = {
                    "full_name": p["full_name"],
                    "session_count": p.get("sessionCount"),
                    "priority": prio,
                    "behavioral_severity": beh.get("severity"),
                    "anomaly_detected": beh.get("anomaly_detected"),
                    "clinical_status": clin.get("status"),
                    "top_deviating": [f["feature"] for f in beh.get("top_deviating_features", [])],
                }

    print("\n" + "-" * 40)
    print("DOCTOR DASHBOARD COUNTS (DYNAMIC DERIVATION):")
    print(f"  Total Patients:      {counts['Total']}")
    print(f"  Elevated Attention:  {counts['Elevated Attention']}")
    print(f"  Moderate Attention:  {counts['Moderate Attention']}")
    print(f"  Routine Attention:   {counts['Routine Attention']}")
    print(f"  Pending Assessment:  {counts['Pending Assessment']}")
    print("-" * 40)

    # Invariants for Personas A-E
    assert persona_results["A"]["priority"] == "Routine Attention", f"Patient A expected Routine Attention, got {persona_results['A']['priority']}"
    assert persona_results["A"]["anomaly_detected"] is False, "Patient A should have anomaly_detected=False"
    assert persona_results["A"]["session_count"] == 5, "Patient A must have 5 sessions"

    assert persona_results["B"]["priority"] == "Elevated Attention", f"Patient B expected Elevated Attention, got {persona_results['B']['priority']}"
    assert persona_results["B"]["anomaly_detected"] is True, "Patient B should have anomaly_detected=True"
    assert any("memory" in f or "recall" in f for f in persona_results["B"]["top_deviating"]), "Patient B top deviating must feature memory metrics"

    assert persona_results["C"]["priority"] == "Elevated Attention", f"Patient C expected Elevated Attention, got {persona_results['C']['priority']}"
    assert persona_results["C"]["anomaly_detected"] is True, "Patient C should have anomaly_detected=True"
    assert any("rt" in f or "miss" in f for f in persona_results["C"]["top_deviating"]), "Patient C top deviating must feature reaction metrics"

    assert persona_results["D"]["priority"] == "Elevated Attention", f"Patient D expected Elevated Attention, got {persona_results['D']['priority']}"
    assert persona_results["D"]["anomaly_detected"] is True, "Patient D should have anomaly_detected=True"
    assert len(persona_results["D"]["top_deviating"]) >= 2, "Patient D top deviating should span multiple features"

    assert persona_results["E"]["priority"] == "Pending Assessment", f"Patient E expected Pending Assessment, got {persona_results['E']['priority']}"
    assert persona_results["E"]["session_count"] == 1, "Patient E must have 1 session"

    # Verify PatientDetail endpoint for all personas
    print("\n[Step 7] Verifying PatientDetail endpoint GET /results/patient/{id} for Personas A-E...")
    for letter in ["A", "B", "C", "D", "E"]:
        pid = f"sih-demo-patient-{letter.lower()}"
        res = request_json(f"/results/patient/{pid}", token=DOCTOR_TOKEN)
        sess = res.get("results", [])
        print(f"  Patient {letter} ({pid}): {len(sess)} sessions returned with consent verified.")
        for s in sess:
            assert "ml_analysis" in s, f"Session missing ml_analysis in patient {letter}"
            assert "behavioral_deviation" in s["ml_analysis"]
            assert "overall_attention" in s["ml_analysis"]
            assert "clinical_reference" in s["ml_analysis"]

    # Verify Patient own results endpoint
    print("\n[Step 8] Verifying Patient own results GET /results/my...")
    for letter in ["A", "B", "C", "D", "E"]:
        token = f"sih_demo_token_patient_{letter.lower()}_2026"
        res = request_json("/results/my", token=token)
        my_results = res.get("results", [])
        progress = res.get("progress", {})
        print(f"  Patient {letter}: {len(my_results)} sessions, progress trajectory: {progress.get('overall_trajectory')}")

    # Verify Caregiver Alerts Safety
    print("\n[Step 9] Verifying Caregiver alerts safety...")
    cg_res = request_json(f"/dashboard/patient/sih-demo-patient-001", token=CAREGIVER_TOKEN)
    alerts = cg_res.get("caregiver_alerts", [])
    print(f"  Caregiver alerts count for Biren Das: {len(alerts)}")
    forbidden = ["alzheimer", "dementia", "parkinson", "disease risk", "probability"]
    for a in alerts:
        txt = f"{a.get('title','')} {a.get('message','')} {a.get('recommended_action','')}".lower()
        for f_word in forbidden:
            assert f_word not in txt, f"Forbidden word '{f_word}' in alert: {txt}"

    # Verify OASIS Clinical Reference Safety
    print("\n[Step 10 & 11] Verifying Clinical Reference Model Isolation & Safety...")
    from ml.clinical_model import predict_clinical_reference
    # 1. Normal app inputs without MRI features -> must return insufficient_input without error
    incomplete_res = predict_clinical_reference({"Age": 72.0, "EDUC": 14.0})
    assert incomplete_res["status"] == "insufficient_input"
    assert incomplete_res["probability"] is None
    print("  Incomplete inputs correctly refused -> status: 'insufficient_input', probability: None")

    # 2. Independent research benchmark fixture with valid research inputs (all 8 OASIS features)
    research_fixture = {"Age": 75.0, "EDUC": 16.0, "SES": 2.0, "MMSE": 22.0, "eTIV": 1500.0, "nWBV": 0.71, "ASF": 1.15, "sex": "M"}
    research_res = predict_clinical_reference(research_fixture)
    assert research_res["status"] == "available"
    assert research_res["probability"] is not None
    print(f"  Research benchmark fixture valid -> status: 'available', probability: {research_res['probability']}")

    print("\n" + "=" * 80)
    print("ALL LIVE INTEGRATION VALIDATION CHECKS PASSED PERFECTLY!")
    print("=" * 80)

if __name__ == "__main__":
    main()

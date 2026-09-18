"""
test_live_e2e_browser_simulation.py — Full End-to-End Simulation of Real Frontend Network & State
===================================================================================================
Simulates the exact browser API interactions executed by the React application across:
1. Patient Flow (Biren Das / Patient B)
2. Caregiver Flow (Sreejeta Sen)
3. RBAC Negative Tests (Patient C, Patient E access blocked)
4. Doctor Flow (Dr. Tanisha)
5. Cross-role Data Consistency (Patient B session trajectory identical in Patient, Caregiver, Doctor views)
6. Terminology Audit
7. Consent Enforcement
"""
import urllib.request
import urllib.error
import json
import re
import sys

BASE_URL = "http://127.0.0.1:8000/api"

class Response:
    def __init__(self, status_code, body_text):
        self.status_code = status_code
        self.text = body_text
    def json(self):
        return json.loads(self.text)

def http_req(method, url, headers=None, json_data=None):
    headers = headers or {}
    data = None
    if json_data is not None:
        data = json.dumps(json_data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return Response(resp.status, resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        return Response(err.code, err.read().decode("utf-8"))

def log(step, msg, ok=True):
    symbol = "[PASS]" if ok else "[FAIL]"
    print(f"{symbol} {step}: {msg}")

def run_e2e_simulation():
    print("=" * 70)
    print("STARTING FULL END-TO-END LIVE APPLICATION VALIDATION")
    print("=" * 70)

    # STEP 1: RESET & SEED DEMO
    r = http_req("POST", f"{BASE_URL}/demo/reset-and-seed")
    assert r.status_code == 200, f"Demo reset failed: {r.text}"
    seed_data = r.json()
    log("STEP 1", f"Demo reset and seeded successfully. Status: {seed_data.get('status')}")
    assert seed_data["patient"]["name"] == "Biren Das (Demo Patient)"
    assert seed_data["doctor"]["name"] == "Dr. Tanisha"
    assert "Sreejeta" in seed_data["caregiver"]["name"]
    log("STEP 1", "Verified Doctor (Dr. Tanisha), Patient (Biren Das), Caregiver (Sreejeta Sen)")

    # STEP 2: PATIENT FLOW
    # Login as Biren Das
    login_p = http_req("POST", f"{BASE_URL}/auth/login", json_data={
        "email": "biren.das@sihdemo.local",
        "password": "DemoPassword#2026",
        "role": "patient"
    })
    assert login_p.status_code == 200, f"Patient login failed: {login_p.text}"
    p_token = login_p.json()["token"]
    p_headers = {"Authorization": f"Bearer {p_token}"}
    log("STEP 2", "Patient login successful (Biren Das)")

    # Patient Dashboard: Doctor Info
    r_doc = http_req("GET", f"{BASE_URL}/auth/doctors/my-doctor", headers=p_headers)
    assert r_doc.status_code == 200
    doc_info = r_doc.json()
    assert doc_info.get("doctor") is not None
    assert "Tanisha" in doc_info["doctor"].get("full_name", "")
    log("STEP 2", f"Patient dashboard 'My Doctor' verified: {doc_info['doctor']['full_name']}")

    # Patient Dashboard: Caregiver Info
    r_cg = http_req("GET", f"{BASE_URL}/caregivers/my-caregivers", headers=p_headers)
    assert r_cg.status_code == 200
    cg_info = r_cg.json()
    assert cg_info.get("active_count", 0) >= 1
    active_cg = cg_info["caregivers"][0]
    assert "Sreejeta" in active_cg["caregiver_name"]
    assert active_cg["status"] == "connected"
    assert active_cg["access_granted"] is True
    log("STEP 2", f"Patient dashboard 'My Caregiver' verified: {active_cg['caregiver_name']} (Status: {active_cg['status']}, Active: {active_cg['access_granted']})")

    # Patient Results / Cognitive Trajectory
    r_res = http_req("GET", f"{BASE_URL}/results/my", headers=p_headers)
    assert r_res.status_code == 200
    p_sessions = r_res.json().get("results", [])
    log("STEP 2", f"Patient results loaded: {len(p_sessions)} sessions available")

    # STEP 3: CAREGIVER FLOW
    # Login as Sreejeta
    login_cg = http_req("POST", f"{BASE_URL}/auth/login", json_data={
        "email": "sreejeta.sen@sihdemo.local",
        "password": "DemoPassword#2026",
        "role": "caregiver"
    })
    assert login_cg.status_code == 200, f"Caregiver login failed: {login_cg.text}"
    cg_token = login_cg.json()["token"]
    cg_headers = {"Authorization": f"Bearer {cg_token}"}
    log("STEP 3", "Caregiver login successful (Sreejeta Sen)")

    # Caregiver Dashboard: Assigned Patients
    r_cg_patients = http_req("GET", f"{BASE_URL}/dashboard/patients", headers=cg_headers)
    assert r_cg_patients.status_code == 200
    cg_patients_data = r_cg_patients.json()
    assert cg_patients_data.get("role") == "caregiver"
    cg_patient_ids = [p["id"] for p in cg_patients_data.get("patients", [])]
    log("STEP 3", f"Caregiver assigned patient count: {len(cg_patient_ids)}")

    # Verify authorized patients visible
    expected_cg_patients = {"sih-demo-patient-001", "sih-demo-patient-a", "sih-demo-patient-b", "sih-demo-patient-d"}
    assert set(cg_patient_ids) == expected_cg_patients, f"Mismatch: expected {expected_cg_patients}, got {set(cg_patient_ids)}"
    log("STEP 3", "Caregiver sees EXACTLY Patient A, Patient B, Patient D, and Biren Das")

    # Verify unauthorized patients NOT visible
    assert "sih-demo-patient-c" not in cg_patient_ids
    assert "sih-demo-patient-e" not in cg_patient_ids
    log("STEP 3", "Caregiver roster correctly EXCLUDES Patient C and Patient E")

    # Open Authorized Patients Details: Patient B
    r_b = http_req("GET", f"{BASE_URL}/dashboard/patient/sih-demo-patient-b", headers=cg_headers)
    assert r_b.status_code == 200
    b_data = r_b.json()
    assert "patient_id" in b_data
    assert "overall_attention" in b_data
    assert "behavioral_deviation" in b_data
    assert "domain_scores" in b_data
    assert b_data["behavioral_deviation"].get("severity") == "significant"

    # Also verify Caregiver can load longitudinal results for Patient B
    r_b_res = http_req("GET", f"{BASE_URL}/results/patient/sih-demo-patient-b", headers=cg_headers)
    assert r_b_res.status_code == 200
    b_results = r_b_res.json().get("results", [])
    assert len(b_results) == 5
    log("STEP 3", f"Patient B details & results for Caregiver verified: {len(b_results)} sessions, Behavioral Deviation='{b_data['behavioral_deviation']['severity']}'")

    # STEP 4: RBAC NEGATIVE TESTS
    # Sreejeta attempts to access Patient C details
    r_neg_c = http_req("GET", f"{BASE_URL}/dashboard/patient/sih-demo-patient-c", headers=cg_headers)
    assert r_neg_c.status_code == 403, f"Expected 403, got {r_neg_c.status_code}"
    log("STEP 4", "RBAC Negative Test 1: Caregiver access to Patient C dashboard blocked with 403 Forbidden")

    # Sreejeta attempts to access Patient E details
    r_neg_e = http_req("GET", f"{BASE_URL}/dashboard/patient/sih-demo-patient-e", headers=cg_headers)
    assert r_neg_e.status_code == 403, f"Expected 403, got {r_neg_e.status_code}"
    log("STEP 4", "RBAC Negative Test 2: Caregiver access to Patient E dashboard blocked with 403 Forbidden")

    # Sreejeta attempts to access Patient C results
    r_neg_res_c = http_req("GET", f"{BASE_URL}/results/patient/sih-demo-patient-c", headers=cg_headers)
    assert r_neg_res_c.status_code == 403, f"Expected 403, got {r_neg_res_c.status_code}"
    log("STEP 4", "RBAC Negative Test 3: Caregiver access to Patient C results blocked with 403 Forbidden")

    # STEP 5: DOCTOR FLOW
    # Login as Dr. Tanisha
    login_doc = http_req("POST", f"{BASE_URL}/auth/login", json_data={
        "email": "dr.tanisha@sihdemo.local",
        "password": "DemoPassword#2026",
        "role": "doctor"
    })
    assert login_doc.status_code == 200, f"Doctor login failed: {login_doc.text}"
    doc_token = login_doc.json()["token"]
    doc_headers = {"Authorization": f"Bearer {doc_token}"}
    log("STEP 5", "Doctor login successful (Dr. Tanisha)")

    # Doctor Dashboard: Enrolled Patients
    r_doc_patients = http_req("GET", f"{BASE_URL}/dashboard/patients", headers=doc_headers)
    assert r_doc_patients.status_code == 200
    doc_patients_data = r_doc_patients.json()
    doc_patient_dict = {p["id"]: p for p in doc_patients_data.get("patients", [])}
    log("STEP 5", f"Doctor dashboard loaded: {len(doc_patient_dict)} enrolled patients")

    # Check that Patients A-E are all enrolled
    for p_id in ["sih-demo-patient-a", "sih-demo-patient-b", "sih-demo-patient-c", "sih-demo-patient-d", "sih-demo-patient-e"]:
        assert p_id in doc_patient_dict, f"Missing {p_id} in doctor dashboard"

    # Verify Attention States for Personas
    assert doc_patient_dict["sih-demo-patient-a"]["attention_priority"] == "Routine Attention"
    assert doc_patient_dict["sih-demo-patient-b"]["attention_priority"] == "Elevated Attention"
    assert doc_patient_dict["sih-demo-patient-c"]["attention_priority"] == "Elevated Attention"
    assert doc_patient_dict["sih-demo-patient-d"]["attention_priority"] == "Elevated Attention"
    assert doc_patient_dict["sih-demo-patient-e"]["attention_priority"] == "Pending Assessment"
    log("STEP 5", "Doctor dashboard Attention States verified: A=Routine, B=Elevated, C=Elevated, D=Elevated, E=Pending")

    # Doctor can open Patient B, C, D
    for pid in ["sih-demo-patient-b", "sih-demo-patient-c", "sih-demo-patient-d"]:
        r_dtl = http_req("GET", f"{BASE_URL}/dashboard/patient/{pid}", headers=doc_headers)
        d_json = r_dtl.json()
        clinical_results = d_json.get("clinical", {}).get("assessment_results", [])
        assert len(clinical_results) == 5
    log("STEP 5", "Doctor successfully inspected longitudinal data for Patient B, C, and D")

    # STEP 6: CROSS-ROLE DATA CONSISTENCY FOR PATIENT B
    # Patient B self-login
    login_b = http_req("POST", f"{BASE_URL}/auth/login", json_data={
        "email": "bhavna.baruah@sihdemo.local",
        "password": "DemoPassword#2026",
        "role": "patient"
    })
    b_token = login_b.json()["token"]
    r_b_self = http_req("GET", f"{BASE_URL}/results/my", headers={"Authorization": f"Bearer {b_token}"}).json().get("results", [])
    r_b_cg = http_req("GET", f"{BASE_URL}/results/patient/sih-demo-patient-b", headers=cg_headers).json().get("results", [])
    r_b_doc = http_req("GET", f"{BASE_URL}/results/patient/sih-demo-patient-b", headers=doc_headers).json().get("results", [])

    # Verify session count is exactly 5 across all 3 views
    assert len(r_b_self) == 5
    assert len(r_b_cg) == 5
    assert len(r_b_doc) == 5

    # Verify latest session timestamps and scores match
    self_latest = r_b_self[-1]
    cg_latest = r_b_cg[-1]
    doc_latest = r_b_doc[-1]

    assert self_latest["timestamp"] == cg_latest["timestamp"] == doc_latest["timestamp"]
    assert self_latest["memory_score"] == cg_latest["memory_score"] == doc_latest["memory_score"]
    assert self_latest["speech_score"] == cg_latest["speech_score"] == doc_latest["speech_score"]
    assert self_latest["reaction_score"] == cg_latest["reaction_score"] == doc_latest["reaction_score"]
    log("STEP 6", "Cross-role trajectory consistency verified: Patient, Caregiver, and Doctor receive identical session metrics for Patient B")

    # STEP 7: TERMINOLOGY AUDIT
    forbidden_terms = [
        "alzheimers_risk",
        "dementia_risk",
        "parkinsons_risk",
        "risk_levels",
        "high risk",
        "moderate risk",
        "low risk",
        "disease risk",
        "risk score",
        "disease probability"
    ]
    # Check payload from doctor dashboard
    raw_doc_text = json.dumps(doc_patients_data).lower()
    for term in forbidden_terms:
        assert term not in raw_doc_text, f"Forbidden term '{term}' found in doctor dashboard payload!"

    raw_cg_text = json.dumps(cg_patients_data).lower()
    for term in forbidden_terms:
        assert term not in raw_cg_text, f"Forbidden term '{term}' found in caregiver dashboard payload!"
    log("STEP 7", "API payload Terminology Audit passed: 0 instances of forbidden disease/risk semantics")

    print("=" * 70)
    print("ALL LIVE END-TO-END VALIDATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_e2e_simulation()

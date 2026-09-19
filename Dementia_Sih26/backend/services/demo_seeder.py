"""
backend/services/demo_seeder.py
================================
Controlled, deterministic longitudinal demo dataset seeder for SIH PS 26003.

DISCLAIMER & INTEGRITY NOTICE:
- Development and demonstration fixtures only.
- NOT real patient data and NOT clinical evidence.
- Does NOT manufacture or hardcode ML results.
- Executes the REAL application pipeline:
  patient -> cognitive assessment -> /api/analyze -> feature extraction
  -> 18-feature vector -> behavioral baseline -> longitudinal deviation
  -> overall attention -> results_store persistence -> doctor dashboard.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from core.security import hash_password, hash_token
from core.storage import (
    consent_store,
    patient_caregivers_store,
    results_store,
    sessions_store,
    users_store,
)
from services.audit_service import utcnow_iso
from tests.fixtures.cognitive_sessions import (
    get_patient_a_stable_sessions,
    get_patient_b_memory_decline_sessions,
    get_patient_c_reaction_decline_sessions,
    get_patient_d_multidomain_decline_sessions,
    get_patient_e_insufficient_history_sessions,
)

# Deterministic IDs
DEMO_DOCTOR_ID = "sih-demo-doctor-001"
DEMO_CAREGIVER_ID = "sih-demo-caregiver-001"

DEMO_DOCTOR_TOKEN = "sih_demo_doctor_token_deterministic_2026"
DEMO_CAREGIVER_TOKEN = "sih_demo_caregiver_token_deterministic_2026"

DEMO_PATIENTS = {
    "A": {
        "id": "sih-demo-patient-a",
        "full_name": "Arun Sharma (Patient A - Stable)",
        "email": "arun.sharma@sihdemo.local",
        "age": 72,
        "gender": "Male",
        "location": "Guwahati, Assam",
        "education": "Graduate",
        "occupation": "Retired Accountant",
        "token": "sih_demo_token_patient_a_2026",
        "sessions_factory": get_patient_a_stable_sessions,
        "expected_attention": "Routine",
        "description": "5 longitudinal sessions with stable cognitive performance.",
    },
    "B": {
        "id": "sih-demo-patient-b",
        "full_name": "Bhavna Baruah (Patient B - Memory Change)",
        "email": "bhavna.baruah@sihdemo.local",
        "age": 70,
        "gender": "Female",
        "location": "Jorhat, Assam",
        "education": "High School",
        "occupation": "Retired Librarian",
        "token": "sih_demo_token_patient_b_2026",
        "sessions_factory": get_patient_b_memory_decline_sessions,
        "expected_attention": "Elevated",
        "description": "5 longitudinal sessions: stable baseline (1-3) then substantial memory decline (4-5).",
    },
    "C": {
        "id": "sih-demo-patient-c",
        "full_name": "Chandra Kalita (Patient C - Reaction Change)",
        "email": "chandra.kalita@sihdemo.local",
        "age": 71,
        "gender": "Male",
        "location": "Dibrugarh, Assam",
        "education": "Graduate",
        "occupation": "Retired High School Principal",
        "token": "sih_demo_token_patient_c_2026",
        "sessions_factory": get_patient_c_reaction_decline_sessions,
        "expected_attention": "Elevated",
        "description": "5 longitudinal sessions: stable baseline (1-3) then substantial reaction latency slowing (4-5).",
    },
    "D": {
        "id": "sih-demo-patient-d",
        "full_name": "Deepali Saikia (Patient D - Multi-Domain)",
        "email": "deepali.saikia@sihdemo.local",
        "age": 73,
        "gender": "Female",
        "location": "Silchar, Assam",
        "education": "Graduate",
        "occupation": "Retired Professor",
        "token": "sih_demo_token_patient_d_2026",
        "sessions_factory": get_patient_d_multidomain_decline_sessions,
        "expected_attention": "Elevated",
        "description": "5 longitudinal sessions: controlled multi-domain deterioration across Memory, Reaction, and Speech.",
    },
    "E": {
        "id": "sih-demo-patient-e",
        "full_name": "Emon Hazarika (Patient E - Insufficient History)",
        "email": "emon.hazarika@sihdemo.local",
        "age": 69,
        "gender": "Male",
        "location": "Tezpur, Assam",
        "education": "High School",
        "occupation": "Retired Clerk",
        "token": "sih_demo_token_patient_e_2026",
        "sessions_factory": get_patient_e_insufficient_history_sessions,
        "expected_attention": "Pending Assessment",
        "description": "Only 1 completed intake session; personal baseline pending establishment.",
    },
}


def seed_longitudinal_demo_pipeline() -> Dict[str, Any]:
    """
    Executes real pipeline seeding for Patients A, B, C, D, E.
    Ingests each session through the REAL FastAPI POST /api/analyze route.
    """
    now = utcnow_iso()
    now_dt = datetime.now(timezone.utc)

    # 1. Update/Add Doctor & Caregiver
    users = users_store.read()
    doctor = users.get(DEMO_DOCTOR_ID, {})
    doctor.update({
        "id": DEMO_DOCTOR_ID,
        "full_name": "Dr. Tanisha",
        "email": "dr.tanisha@sihdemo.local",
        "aliases": ["tanisha@gmail.com", "dr.hazarika@sihdemo.local"],
        "password_hash": hash_password("DemoPassword#2026"),
        "role": "doctor",
        "specialization": "Cognitive Neurologist",
        "hospital": "Apollo Hospitals",
        "location": "Kolkata, India",
        "years_experience": 18,
        "consultation_mode": "Both",
        "bio": "Specialist in neurodegenerative screening, MCI longitudinal monitoring, and community cognitive health.",
        "max_patients": 50,
        "created_at": doctor.get("created_at", now),
        "last_login": now,
    })

    # Collect patient IDs for doctor enrollment
    existing_enrolled = set(doctor.get("patient_list", []))
    for p_key, p_info in DEMO_PATIENTS.items():
        existing_enrolled.add(p_info["id"])
    existing_enrolled.add("sih-demo-patient-001")

    doctor["patient_list"] = list(existing_enrolled)
    doctor["current_patients"] = len(doctor["patient_list"])
    users[DEMO_DOCTOR_ID] = doctor

    # Also sync enrollment into any custom doctor accounts for Dr. Tanisha
    for uid, u in users.items():
        if u.get("role") == "doctor" and ("tanisha" in u.get("full_name", "").lower() or "tanisha" in u.get("email", "").lower()):
            u_enrolled = set(u.get("patient_list", []))
            for p_key, p_info in DEMO_PATIENTS.items():
                u_enrolled.add(p_info["id"])
            u_enrolled.add("sih-demo-patient-001")
            u["patient_list"] = list(u_enrolled)
            u["current_patients"] = len(u["patient_list"])

    # Ensure caregiver user record is populated for Sreejeta Sen
    caregiver = users.get(DEMO_CAREGIVER_ID, {})
    caregiver.update({
        "id": DEMO_CAREGIVER_ID,
        "full_name": "Sreejeta Sen (Caregiver)",
        "email": "sreejeta.sen@sihdemo.local",
        "aliases": ["sreejeta@example.com", "sreejeta@demo.com", "ananya.das@sihdemo.local"],
        "password_hash": hash_password("DemoPassword#2026"),
        "role": "caregiver",
        "specialization": "Family Caregiver",
        "hospital": "Home Care Network",
        "location": "Kolkata, India",
        "created_at": caregiver.get("created_at", now),
        "last_login": now,
    })
    users[DEMO_CAREGIVER_ID] = caregiver

    # 2. Register Patient User Records
    for p_key, p_info in DEMO_PATIENTS.items():
        pid = p_info["id"]
        users[pid] = {
            "id": pid,
            "full_name": p_info["full_name"],
            "email": p_info["email"],
            "password_hash": hash_password("DemoPassword#2026"),
            "role": "patient",
            "age": p_info["age"],
            "gender": p_info["gender"],
            "phone": "+91 98640 0000" + str(ord(p_key) - ord("A")),
            "assigned_doctor_id": DEMO_DOCTOR_ID,
            "education": p_info["education"],
            "occupation": p_info["occupation"],
            "location": p_info["location"],
            "created_at": (now_dt - timedelta(days=35)).isoformat(),
            "last_login": now,
        }
    users_store.write(users)

    # 3. Create Sessions (Tokens)
    sessions = sessions_store.read()
    sessions[hash_token(DEMO_DOCTOR_TOKEN)] = {"user_id": DEMO_DOCTOR_ID, "created_at": now, "last_active": now}
    sessions[hash_token(DEMO_CAREGIVER_TOKEN)] = {"user_id": DEMO_CAREGIVER_ID, "created_at": now, "last_active": now}
    for p_info in DEMO_PATIENTS.values():
        sessions[hash_token(p_info["token"])] = {"user_id": p_info["id"], "created_at": now, "last_active": now}
    sessions_store.write(sessions)

    # 4. Set Patient Consents (Doctor access granted)
    consents = consent_store.read()
    for p_info in DEMO_PATIENTS.values():
        consents[p_info["id"]] = {
            "share_with_care_team": True,
            "share_memory_bank": True,
            "share_reminders": True,
            "allow_research_deidentified": True,
            "updated_at": now,
            "policy_version": "2026-v2-sih-demo",
        }
    consent_store.write(consents)

    # 5. Initialize Patient-Caregiver Relationships for Demo Caregiver
    caregiver_user = users.get(DEMO_CAREGIVER_ID, {})
    caregiver_name = caregiver_user.get("full_name", "Sreejeta Sen (Caregiver)")
    caregiver_email = caregiver_user.get("email", "sreejeta.sen@sihdemo.local")

    # Assigned demo patients: Patient A, Patient B, Patient D, and Demo Patient Biren Das
    # Patient C and Patient E remain intentionally unassigned to demonstrate strict RBAC
    assigned_patients_for_caregiver = [
        ("sih-demo-patient-001", "Biren Das (Demo Patient)"),
        ("sih-demo-patient-a", DEMO_PATIENTS["A"]["full_name"]),
        ("sih-demo-patient-b", DEMO_PATIENTS["B"]["full_name"]),
        ("sih-demo-patient-d", DEMO_PATIENTS["D"]["full_name"]),
    ]

    caregiver_relationships = [
        {
            "id": f"rel-demo-cg-{p_id}",
            "patient_id": p_id,
            "patient_name": p_name,
            "caregiver_id": DEMO_CAREGIVER_ID,
            "caregiver_name": caregiver_name,
            "caregiver_email": caregiver_email,
            "status": "connected",
            "access_granted": True,
            "created_at": now,
            "updated_at": now,
        }
        for p_id, p_name in assigned_patients_for_caregiver
    ]
    patient_caregivers_store.write(caregiver_relationships)

    # 6. Clear Prior Results for Personas A-E
    results = results_store.read()
    for p_info in DEMO_PATIENTS.values():
        results[p_info["id"]] = []
    results_store.write(results)

    # 6. Feed Sessions through REAL Production API
    # Lazy import app and TestClient to run in-process through FastAPI
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)

    seeded_summary = {}

    for p_key, p_info in DEMO_PATIENTS.items():
        pid = p_info["id"]
        token = p_info["token"]
        headers = {"Authorization": f"Bearer {token}"}
        session_list = p_info["sessions_factory"]()
        num_sessions = len(session_list)

        # Ingest every session through /api/analyze
        for s_idx, session_req in enumerate(session_list, start=1):
            resp = client.post("/api/analyze", json=session_req.model_dump(), headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Real API pipeline ingestion failed for Patient {p_key} (session {s_idx}): {resp.text}"
                )

        # 7. Post-process timestamps to reflect realistic weekly intervals
        patient_res = results_store.read().get(pid, [])
        if patient_res:
            for s_idx, r in enumerate(patient_res):
                # E.g. for 5 sessions: 28 days ago, 21 days ago, 14 days ago, 7 days ago, today
                weeks_back = max(0, num_sessions - 1 - s_idx)
                session_dt = now_dt - timedelta(days=weeks_back * 7)
                iso_ts = session_dt.isoformat()
                r["timestamp"] = iso_ts
                r["createdAt"] = iso_ts

            # Persist updated chronological timestamps
            all_res = results_store.read()
            all_res[pid] = patient_res
            results_store.write(all_res)

        last_result = patient_res[-1] if patient_res else None
        ml_analysis = last_result.get("ml_analysis", {}) if last_result else {}
        oa = ml_analysis.get("overall_attention", {})
        bd = ml_analysis.get("behavioral_deviation", {})

        seeded_summary[p_key] = {
            "patient_id": pid,
            "full_name": p_info["full_name"],
            "session_count": len(patient_res),
            "last_attention_label": oa.get("label"),
            "behavioral_status": bd.get("status"),
            "behavioral_severity": bd.get("severity"),
            "anomaly_detected": bd.get("anomaly_detected"),
            "top_deviating_features": [f["feature"] for f in bd.get("top_deviating_features", [])],
        }

    return {
        "status": "ok",
        "message": "Real application pipeline seeded successfully for Personas A–E.",
        "seeded_patients": seeded_summary,
    }

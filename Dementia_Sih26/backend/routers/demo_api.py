"""
demo_api.py — Deterministic SIH Demo Mode Seeder and Controller
================================================================
Seeds verified synthetic demo data for Smart India Hackathon (SIH PS 26003) judges.
All data is clearly labelled as synthetic.
Screening output is strictly for early cognitive risk indicators and educational purposes,
never a clinical diagnosis.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from fastapi import APIRouter

from core.security import hash_password, hash_token
from core.storage import (
    caregiver_alerts_store,
    consent_store,
    game_sessions_store,
    memory_bank_store,
    messages_store,
    reminders_store,
    results_store,
    routine_logs_store,
    sessions_store,
    users_store,
)
from services.audit_service import record, utcnow_iso

router = APIRouter(prefix="/demo", tags=["sih-demo"])

DEMO_PATIENT_ID = "sih-demo-patient-001"
DEMO_PATIENT_2_ID = "sih-demo-patient-002"
DEMO_DOCTOR_ID = "sih-demo-doctor-001"
DEMO_CAREGIVER_ID = "sih-demo-caregiver-001"

DEMO_PATIENT_TOKEN = "sih_demo_patient_token_deterministic_2026"
DEMO_DOCTOR_TOKEN = "sih_demo_doctor_token_deterministic_2026"
DEMO_CAREGIVER_TOKEN = "sih_demo_caregiver_token_deterministic_2026"


@router.post("/reset-and-seed")
def reset_and_seed_demo() -> Dict[str, Any]:
    """
    Seed deterministic synthetic demo data for SIH judges.
    Idempotent and resets state to a clean baseline.
    """
    now = utcnow_iso()

    # 1. Synthetic Users
    patient = {
        "id": DEMO_PATIENT_ID,
        "full_name": "Biren Das (Demo Patient)",
        "email": "biren.das@sihdemo.local",
        "password_hash": hash_password("DemoPassword#2026"),
        "role": "patient",
        "age": 68,
        "gender": "Male",
        "phone": "+91 98640 12345",
        "assigned_doctor_id": DEMO_DOCTOR_ID,
        "education": "Graduate",
        "occupation": "Retired High School Teacher (Assam)",
        "location": "Guwahati, Assam",
        "created_at": now,
        "last_login": now,
    }

    doctor = {
        "id": DEMO_DOCTOR_ID,
        "full_name": "Dr. Rupjyoti Hazarika",
        "email": "dr.hazarika@sihdemo.local",
        "password_hash": hash_password("DemoPassword#2026"),
        "role": "doctor",
        "specialization": "Cognitive Neurologist",
        "hospital": "Guwahati Medical College & Hospital (GMCH)",
        "location": "Guwahati, Assam",
        "years_experience": 18,
        "consultation_mode": "Both",
        "bio": "Specialist in neurodegenerative screening, MCI longitudinal monitoring, and community cognitive health.",
        "max_patients": 20,
        "current_patients": 2,
        "patient_list": [DEMO_PATIENT_ID, DEMO_PATIENT_2_ID],
        "pending_requests": [],
        "created_at": now,
        "last_login": now,
    }

    caregiver = {
        "id": DEMO_CAREGIVER_ID,
        "full_name": "Ananya Das (Caregiver)",
        "email": "ananya.das@sihdemo.local",
        "password_hash": hash_password("DemoPassword#2026"),
        "role": "caregiver",
        "specialization": "Family Caregiver",
        "hospital": "Home Care Network, Assam",
        "location": "Guwahati, Assam",
        "patient_list": [DEMO_PATIENT_ID, DEMO_PATIENT_2_ID],
        "created_at": now,
        "last_login": now,
    }

    patient_2 = {
        "id": DEMO_PATIENT_2_ID,
        "full_name": "Pradip Borah (Demo Inactive)",
        "email": "pradip.borah@sihdemo.local",
        "password_hash": hash_password("DemoPassword#2026"),
        "role": "patient",
        "age": 72,
        "gender": "Male",
        "phone": "+91 98640 54321",
        "assigned_doctor_id": DEMO_DOCTOR_ID,
        "education": "High School",
        "occupation": "Retired Postmaster (Tezpur, Assam)",
        "location": "Tezpur, Assam",
        "created_at": now,
        "last_login": now,
    }

    users = users_store.read()
    users[DEMO_PATIENT_ID] = patient
    users[DEMO_PATIENT_2_ID] = patient_2
    users[DEMO_DOCTOR_ID] = doctor
    users[DEMO_CAREGIVER_ID] = caregiver
    users_store.write(users)

    # 2. Synthetic Hashed Sessions
    sessions = sessions_store.read()
    sessions[hash_token(DEMO_PATIENT_TOKEN)] = {"user_id": DEMO_PATIENT_ID, "created_at": now, "last_active": now}
    sessions[hash_token(DEMO_DOCTOR_TOKEN)] = {"user_id": DEMO_DOCTOR_ID, "created_at": now, "last_active": now}
    sessions[hash_token(DEMO_CAREGIVER_TOKEN)] = {"user_id": DEMO_CAREGIVER_ID, "created_at": now, "last_active": now}
    sessions_store.write(sessions)

    # 3. Synthetic Consent
    consents = consent_store.read()
    consents[DEMO_PATIENT_ID] = {
        "share_with_care_team": True,
        "share_memory_bank": True,
        "share_reminders": True,
        "allow_research_deidentified": True,
        "updated_at": now,
        "policy_version": "2026-v2-sih-demo",
    }
    consents[DEMO_PATIENT_2_ID] = {
        "share_with_care_team": True,
        "share_memory_bank": True,
        "share_reminders": True,
        "allow_research_deidentified": True,
        "updated_at": now,
        "policy_version": "2026-v2-sih-demo",
    }
    consent_store.write(consents)

    # 4. Synthetic Personal Memory Bank (Culturally rooted in Assam)
    memories: List[Dict[str, Any]] = [
        {
            "id": "mem-sih-001",
            "user_id": DEMO_PATIENT_ID,
            "category": "person",
            "name": "Aarav (Grandson)",
            "relationship_or_context": "নাতি (Grandson), lives in Guwahati, loves cricket",
            "photo_url": None,
            "image_emoji": "👦",
            "notes": "Always visits on Sunday afternoons. Loves grandma's homemade pitha.",
            "audio_cue": None,
            "added_by": "caregiver",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "mem-sih-002",
            "user_id": DEMO_PATIENT_ID,
            "category": "person",
            "name": "Maya (Daughter)",
            "relationship_or_context": "কন্যা (Daughter), calls every evening at 7:00 PM",
            "photo_url": None,
            "image_emoji": "👩",
            "notes": "Civil engineer in Tezpur. Always asks about medicine routine.",
            "audio_cue": None,
            "added_by": "caregiver",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "mem-sih-003",
            "user_id": DEMO_PATIENT_ID,
            "category": "place",
            "name": "Jorhat Ancestral Tea Garden",
            "relationship_or_context": "পুৰণি চাহ বাগিচা (Ancestral home in Upper Assam)",
            "photo_url": None,
            "image_emoji": "🍵",
            "notes": "Visited every Bihu festival with family.",
            "audio_cue": None,
            "added_by": "patient",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "mem-sih-004",
            "user_id": DEMO_PATIENT_ID,
            "category": "item",
            "name": "Assamese Japi & Gamosa",
            "relationship_or_context": "সাংস্কৃতিক চিন (Traditional gift received upon retirement)",
            "photo_url": None,
            "image_emoji": "👒",
            "notes": "Kept in the study room showcase.",
            "audio_cue": None,
            "added_by": "patient",
            "created_at": now,
            "updated_at": now,
        },
    ]
    # Filter out previous demo memories and re-add
    existing_mem = [m for m in memory_bank_store.read() if m.get("user_id") != DEMO_PATIENT_ID]
    memory_bank_store.write(existing_mem + memories)

    # 5. Synthetic Reminders
    reminders: List[Dict[str, Any]] = [
        {
            "id": "rem-sih-000",
            "user_id": DEMO_PATIENT_ID,
            "category": "daily_activity",
            "title": "Morning Breakfast & Assam Tea",
            "description": "Nutritious morning meal with warm tea",
            "scheduled_time": "08:30",
            "recurrence": "daily",
            "days_of_week": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "dosage": None,
            "instructions": "Completed after wake-up",
            "status": "completed",
            "last_completed_at": now,
            "created_by": "caregiver",
            "created_at": now,
        },
        {
            "id": "rem-sih-001",
            "user_id": DEMO_PATIENT_ID,
            "category": "medicine",
            "title": "Donepezil 5mg (মগজুৰ ঔষধ)",
            "description": "Morning memory maintenance prescribed by Dr. Hazarika",
            "scheduled_time": "08:00",
            "recurrence": "daily",
            "days_of_week": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "dosage": "1 tablet after breakfast",
            "instructions": "Take with warm water",
            "status": "pending",
            "last_completed_at": None,
            "created_by": "caregiver",
            "created_at": now,
        },
        {
            "id": "rem-sih-002",
            "user_id": DEMO_PATIENT_ID,
            "category": "hydration",
            "title": "Drink a Glass of Water (পানী খোৱা)",
            "description": "Hydration reminder to reduce cognitive fatigue",
            "scheduled_time": "11:30",
            "recurrence": "daily",
            "days_of_week": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "dosage": "1 full glass (250ml)",
            "instructions": None,
            "status": "pending",
            "last_completed_at": None,
            "created_by": "patient",
            "created_at": now,
        },
        {
            "id": "rem-sih-003",
            "user_id": DEMO_PATIENT_ID,
            "category": "activity",
            "title": "Evening Walk & Breathing (সন্ধিয়া খোজকঢ়a)",
            "description": "Light walk in the garden",
            "scheduled_time": "17:00",
            "recurrence": "daily",
            "days_of_week": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "dosage": "20 minutes gentle pacing",
            "instructions": "Wear comfortable walking shoes",
            "status": "pending",
            "last_completed_at": None,
            "created_by": "caregiver",
            "created_at": now,
        },
    ]
    existing_rem = [r for r in reminders_store.read() if r.get("user_id") not in (DEMO_PATIENT_ID, DEMO_PATIENT_2_ID)]
    reminders_store.write(existing_rem + reminders)

    # 6. Synthetic 6-Week Longitudinal Assessments & Explainable Alerts
    # Week 1 to Week 6: Speech 78->71, Memory 75->56, Reaction 76->60
    synthetic_results = [
        {
            "timestamp": "2026-01-20T10:00:00Z",
            "createdAt": "2026-01-20T10:00:00Z",
            "speech_score": 82.0,
            "memory_score": 78.0,
            "reaction_score": 80.0,
            "executive_score": 76.0,
            "motor_score": 84.0,
            "composite_risk_score": 20.0,
            "hybrid_risk": 21.5,
            "confidence": 0.88,
            "risk_levels": {"alzheimers": "Low", "dementia": "Low", "parkinsons": "Low"},
            "attention_variability_index": 0.12,
            "anomaly_alert": "none",
            "disclaimer": "Synthetic demonstration data. Screening indicators only, not a clinical diagnosis.",
        },
        {
            "timestamp": "2026-01-27T10:00:00Z",
            "createdAt": "2026-01-27T10:00:00Z",
            "speech_score": 80.0,
            "memory_score": 74.0,
            "reaction_score": 76.0,
            "executive_score": 75.0,
            "motor_score": 82.0,
            "composite_risk_score": 23.5,
            "hybrid_risk": 24.0,
            "confidence": 0.86,
            "risk_levels": {"alzheimers": "Low", "dementia": "Low", "parkinsons": "Low"},
            "attention_variability_index": 0.14,
            "anomaly_alert": "none",
            "disclaimer": "Synthetic demonstration data. Screening indicators only, not a clinical diagnosis.",
        },
        {
            "timestamp": "2026-02-03T10:00:00Z",
            "createdAt": "2026-02-03T10:00:00Z",
            "speech_score": 76.0,
            "memory_score": 68.0,
            "reaction_score": 72.0,
            "executive_score": 72.0,
            "motor_score": 80.0,
            "composite_risk_score": 28.0,
            "hybrid_risk": 29.5,
            "confidence": 0.85,
            "risk_levels": {"alzheimers": "Mild Concern", "dementia": "Low", "parkinsons": "Low"},
            "attention_variability_index": 0.16,
            "anomaly_alert": "none",
            "disclaimer": "Synthetic demonstration data. Screening indicators only, not a clinical diagnosis.",
        },
        {
            "timestamp": "2026-02-10T10:00:00Z",
            "createdAt": "2026-02-10T10:00:00Z",
            "speech_score": 74.0,
            "memory_score": 64.0,
            "reaction_score": 68.0,
            "executive_score": 70.0,
            "motor_score": 78.0,
            "composite_risk_score": 32.0,
            "hybrid_risk": 33.0,
            "confidence": 0.82,
            "risk_levels": {"alzheimers": "Mild Concern", "dementia": "Low", "parkinsons": "Low"},
            "attention_variability_index": 0.18,
            "anomaly_alert": "none",
            "disclaimer": "Synthetic demonstration data. Screening indicators only, not a clinical diagnosis.",
        },
        {
            "timestamp": "2026-02-17T10:00:00Z",
            "createdAt": "2026-02-17T10:00:00Z",
            "speech_score": 71.0,
            "memory_score": 60.0,
            "reaction_score": 64.0,
            "executive_score": 68.0,
            "motor_score": 76.0,
            "composite_risk_score": 36.5,
            "hybrid_risk": 37.0,
            "confidence": 0.80,
            "risk_levels": {"alzheimers": "Moderate", "dementia": "Mild Concern", "parkinsons": "Low"},
            "attention_variability_index": 0.22,
            "anomaly_alert": "mild_variance",
            "disclaimer": "Synthetic demonstration data. Screening indicators only, not a clinical diagnosis.",
        },
        {
            "timestamp": "2026-02-24T10:00:00Z",
            "createdAt": "2026-02-24T10:00:00Z",
            "speech_score": 68.0,
            "memory_score": 56.0,
            "reaction_score": 60.0,
            "executive_score": 66.0,
            "motor_score": 75.0,
            "composite_risk_score": 41.5,
            "hybrid_risk": 43.0,
            "confidence": 0.79,
            "risk_levels": {"alzheimers": "Moderate", "dementia": "Moderate", "parkinsons": "Low"},
            "attention_variability_index": 0.28,
            "anomaly_alert": "significant_drift",
            "anomaly_details": {
                "detected": True,
                "metric": "attention_variability",
                "drift_percentage": "+19.4%",
                "baseline_mean_rt": "285ms",
                "current_mean_rt": "341ms",
                "explanation": "Reaction time variability drifted +19.4% above personal 4-week moving baseline, combined with word-recall latency. Flags candidate for clinician review.",
            },
            "feature_importance": [
                {"feature": "word_recall_accuracy", "importance": 0.38},
                {"feature": "speech_hesitation_ratio", "importance": 0.26},
                {"feature": "reaction_time_variability", "importance": 0.21},
                {"feature": "stroop_interference", "importance": 0.15},
            ],
            "recommend_retest": False,
            "disclaimer": "Synthetic demonstration data. Screening indicators only, not a clinical diagnosis.",
        },
    ]

    all_res = results_store.read()
    all_res[DEMO_PATIENT_ID] = synthetic_results
    results_store.write(all_res)

    # 7. Synthetic Cognitive Game Sessions for SIH PS 26003
    # Memory Match: 3 baseline sessions (avg 81.7%) vs 3 recent sessions (51%, 48%, 46% -> avg 48.3%, drop -33.4%)
    now_dt = datetime.now(timezone.utc)
    synthetic_game_sessions = [
        # Baseline sessions (7, 6, 5 days ago)
        {
            "session_id": "sess-sih-001",
            "user_id": DEMO_PATIENT_ID,
            "game_id": "memory_match",
            "game_title": "Memory Match",
            "cognitive_domain": "Visual Association & Working Memory",
            "domain_label": "Visual Memory",
            "difficulty_level": 1,
            "score": 85,
            "stars": 3,
            "stars_label": "3/3 Stars",
            "performance_level": "Good",
            "feedback_message": "Strong memory performance.",
            "duration_seconds": 45,
            "moves_count": 8,
            "mistakes_count": 1,
            "completed": True,
            "timestamp": (now_dt - timedelta(days=7)).isoformat(),
        },
        {
            "session_id": "sess-sih-002",
            "user_id": DEMO_PATIENT_ID,
            "game_id": "memory_match",
            "game_title": "Memory Match",
            "cognitive_domain": "Visual Association & Working Memory",
            "domain_label": "Visual Memory",
            "difficulty_level": 1,
            "score": 82,
            "stars": 3,
            "stars_label": "3/3 Stars",
            "performance_level": "Good",
            "feedback_message": "Consistent visual recall.",
            "duration_seconds": 48,
            "moves_count": 9,
            "mistakes_count": 1,
            "completed": True,
            "timestamp": (now_dt - timedelta(days=6)).isoformat(),
        },
        {
            "session_id": "sess-sih-003",
            "user_id": DEMO_PATIENT_ID,
            "game_id": "memory_match",
            "game_title": "Memory Match",
            "cognitive_domain": "Visual Association & Working Memory",
            "domain_label": "Visual Memory",
            "difficulty_level": 1,
            "score": 78,
            "stars": 3,
            "stars_label": "3/3 Stars",
            "performance_level": "Good",
            "feedback_message": "Steady pacing.",
            "duration_seconds": 52,
            "moves_count": 10,
            "mistakes_count": 2,
            "completed": True,
            "timestamp": (now_dt - timedelta(days=5)).isoformat(),
        },
        # Recent sessions (2 days ago, yesterday, today) - repeated difficulty and sudden drop
        {
            "session_id": "sess-sih-004",
            "user_id": DEMO_PATIENT_ID,
            "game_id": "memory_match",
            "game_title": "Memory Match",
            "cognitive_domain": "Visual Association & Working Memory",
            "domain_label": "Visual Memory",
            "difficulty_level": 2,
            "score": 51,
            "stars": 1,
            "stars_label": "1/3 Stars",
            "performance_level": "Needs Review",
            "feedback_message": "Elevated hesitation latency.",
            "duration_seconds": 88,
            "moves_count": 16,
            "mistakes_count": 5,
            "completed": True,
            "timestamp": (now_dt - timedelta(days=2)).isoformat(),
        },
        {
            "session_id": "sess-sih-005",
            "user_id": DEMO_PATIENT_ID,
            "game_id": "memory_match",
            "game_title": "Memory Match",
            "cognitive_domain": "Visual Association & Working Memory",
            "domain_label": "Visual Memory",
            "difficulty_level": 2,
            "score": 48,
            "stars": 1,
            "stars_label": "1/3 Stars",
            "performance_level": "Needs Review",
            "feedback_message": "Multiple mis-matches observed.",
            "duration_seconds": 95,
            "moves_count": 18,
            "mistakes_count": 6,
            "completed": True,
            "timestamp": (now_dt - timedelta(days=1)).isoformat(),
        },
        {
            "session_id": "sess-sih-006",
            "user_id": DEMO_PATIENT_ID,
            "game_id": "memory_match",
            "game_title": "Memory Match",
            "cognitive_domain": "Visual Association & Working Memory",
            "domain_label": "Visual Memory",
            "difficulty_level": 2,
            "score": 46,
            "stars": 1,
            "stars_label": "1/3 Stars",
            "performance_level": "Needs Review",
            "feedback_message": "Consider Level 1 pacing.",
            "duration_seconds": 102,
            "moves_count": 20,
            "mistakes_count": 7,
            "completed": True,
            "timestamp": now,
        },
        # Pradip Borah (inactive patient): 1 session 5 days ago, 0 sessions in last 5 days
        {
            "session_id": "sess-sih-007",
            "user_id": DEMO_PATIENT_2_ID,
            "game_id": "memory_match",
            "game_title": "Memory Match",
            "cognitive_domain": "Visual Association & Working Memory",
            "domain_label": "Visual Memory",
            "difficulty_level": 1,
            "score": 68,
            "stars": 2,
            "stars_label": "2/3 Stars",
            "performance_level": "Moderate",
            "feedback_message": "Routine session completed.",
            "duration_seconds": 65,
            "moves_count": 12,
            "mistakes_count": 3,
            "completed": True,
            "timestamp": (now_dt - timedelta(days=5, hours=2)).isoformat(),
        },
    ]
    existing_sessions = [s for s in game_sessions_store.read() if s.get("user_id") not in (DEMO_PATIENT_ID, DEMO_PATIENT_2_ID)]
    game_sessions_store.write(existing_sessions + synthetic_game_sessions)

    # 8. Reset Caregiver Alert Review States for Demo Reset
    alerts_data = caregiver_alerts_store.read()
    alerts_data.pop(DEMO_PATIENT_ID, None)
    alerts_data.pop(DEMO_PATIENT_2_ID, None)
    caregiver_alerts_store.write(alerts_data)

    record(
        event="demo.seeded",
        actor_id="sih_system",
        outcome="success",
        metadata={"patient_id": DEMO_PATIENT_ID, "patient_2_id": DEMO_PATIENT_2_ID, "doctor_id": DEMO_DOCTOR_ID},
    )

    return {
        "status": "ok",
        "message": "SIH deterministic demo data initialized successfully.",
        "patient": {"id": DEMO_PATIENT_ID, "name": patient["full_name"], "token": DEMO_PATIENT_TOKEN},
        "patient_inactive": {"id": DEMO_PATIENT_2_ID, "name": patient_2["full_name"]},
        "doctor": {"id": DEMO_DOCTOR_ID, "name": doctor["full_name"], "token": DEMO_DOCTOR_TOKEN},
        "caregiver": {"id": DEMO_CAREGIVER_ID, "name": caregiver["full_name"], "token": DEMO_CAREGIVER_TOKEN},
    }

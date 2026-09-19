"""
dashboard_api.py — RBAC Care Team Dashboard API
================================================
Aggregated cognitive telemetry, trends, and clinical metrics for clinicians and caregivers.
Enforces patient enrollment relationship, consent checks, and audit logging.
Screening output is never a clinical diagnosis.
"""
from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter, Header, HTTPException

from core.storage import (
    game_sessions_store,
    memory_bank_store,
    reminders_store,
    results_store,
    routine_logs_store,
)
from routers.consent_api import check_patient_consent
from services import audit_service, auth_service, caregiver_alert_service

router = APIRouter(prefix="/dashboard", tags=["dashboards"])


def member(header: str) -> Dict[str, Any]:
    return auth_service.require_care_team(header)


def verify_patient_access(user: Dict[str, Any], patient_id: str) -> None:
    # 1. Enforce independent doctor/caregiver care relationship
    if not auth_service.verify_care_member_patient_access(user, patient_id):
        audit_service.record(
            event="dashboard.access_denied",
            actor_id=user["id"],
            actor_role=user.get("role"),
            subject_id=patient_id,
            outcome="forbidden",
            metadata={"reason": "unassigned_patient"},
        )
        raise HTTPException(status_code=403, detail="This patient is not assigned to your care team.")

    # 2. Enforce consent
    if not check_patient_consent(patient_id, "share_with_care_team"):
        audit_service.record(
            event="dashboard.access_denied",
            actor_id=user["id"],
            actor_role=user.get("role"),
            subject_id=patient_id,
            outcome="forbidden",
            metadata={"reason": "consent_withheld"},
        )
        raise HTTPException(status_code=403, detail="Patient has not granted consent to share data with care team.")


def trend(results: List[Dict[str, Any]]) -> List[float]:
    return [
        round(
            sum(row.get(key, 0) for key in ("speech_score", "memory_score", "reaction_score", "executive_score", "motor_score")) / 5,
            1,
        )
        for row in results
    ]


def signal(latest: Dict[str, Any] | None) -> str:
    if latest and latest.get("anomaly_alert") and latest.get("anomaly_alert") != "none":
        return "Requires professional evaluation"
    if latest:
        return "Screening signal: monitor performance change"
    return "No screening data"


@router.get("/patients")
def overview(authorization: str = Header(...)) -> Dict[str, Any]:
    user = member(authorization)
    if user.get("role") == "caregiver":
        people = auth_service.list_patients_for_caregiver(user["id"])
    else:
        people = auth_service.list_patients_for_doctor(user["id"])

    audit_service.record(
        event="dashboard.overview_read",
        actor_id=user["id"],
        actor_role=user.get("role"),
        outcome="success",
        metadata={"patient_count": len(people)},
    )

    def get_attention_priority(last_res: Dict[str, Any] | None, sess_count: int) -> str:
        if not last_res or sess_count < 3:
            return "Pending Assessment"
        oa = last_res.get("ml_analysis", {}).get("overall_attention", {})
        if oa.get("available") and oa.get("label"):
            lbl = oa["label"].lower()
            if "high" in lbl or "elevated" in lbl:
                return "Elevated Attention"
            if "moderate" in lbl:
                return "Moderate Attention"
            return "Routine Attention"
        bd = last_res.get("ml_analysis", {}).get("behavioral_deviation", {})
        if bd.get("status") == "insufficient_history":
            return "Pending Assessment"
        sev = bd.get("severity")
        if sev in ("severe", "significant"):
            return "Elevated Attention"
        if sev == "mild":
            return "Moderate Attention"
        if sev == "none":
            return "Routine Attention"
        return "Pending Assessment"

    return {
        "role": user["role"],
        "patients": [
            {
                "id": p["id"],
                "name": p["full_name"],
                "sessions": p.get("sessionCount", 0),
                "attention_priority": get_attention_priority(p.get("lastResult"), p.get("sessionCount", 0)),
                "screening_signal": signal(p.get("lastResult")),
                "last_assessment": p.get("lastResult", {}).get("timestamp") if p.get("lastResult") else None,
                "domain_scores": {
                    "speech": round(p.get("lastResult", {}).get("speech_score", 0), 1) if p.get("lastResult") else None,
                    "memory": round(p.get("lastResult", {}).get("memory_score", 0), 1) if p.get("lastResult") else None,
                    "reaction": round(p.get("lastResult", {}).get("reaction_score", 0), 1) if p.get("lastResult") else None,
                    "executive": round(p.get("lastResult", {}).get("executive_score", 0), 1) if p.get("lastResult") else None,
                    "motor": round(p.get("lastResult", {}).get("motor_score", 0), 1) if p.get("lastResult") else None,
                } if p.get("lastResult") else None,
            }
            for p in people
        ],
    }


@router.get("/patient/{patient_id}")
def detail(patient_id: str, authorization: str = Header(...)) -> Dict[str, Any]:
    user = member(authorization)
    verify_patient_access(user, patient_id)

    results = results_store.read().get(patient_id, [])
    latest = results[-1] if results else None
    reminders = [row for row in reminders_store.read() if row.get("user_id") == patient_id]

    caregiver_alerts = caregiver_alert_service.evaluate_caregiver_alerts(patient_id)

    payload: Dict[str, Any] = {
        "patient_id": patient_id,
        "screening_signal": signal(latest),
        "performance_trend": trend(results),
        "game_activity": [row for row in game_sessions_store.read() if row.get("user_id") == patient_id][-10:],
        "medication": reminders,
        "routine": reminders,
        "hydration_glasses": sum(
            row.get("glasses", 0) for row in routine_logs_store.read() if row.get("user_id") == patient_id and row.get("type") == "hydration"
        ),
        "alerts": [signal(latest)] if latest else [],
        "caregiver_alerts": caregiver_alerts,
        "memory_bank": [row for row in memory_bank_store.read() if row.get("user_id") == patient_id],
        "overall_attention": latest.get("ml_analysis", {}).get("overall_attention") if latest else None,
        "behavioral_deviation": latest.get("ml_analysis", {}).get("behavioral_deviation") if latest else None,
        "domain_scores": (
            {key: round(latest.get(key, 0), 1) for key in ("speech_score", "memory_score", "reaction_score", "executive_score", "motor_score")}
            if latest
            else None
        ),
        "latest_session": {
            "timestamp": latest.get("timestamp"),
            "session_count": len(results),
        } if latest else None,
    }

    if user["role"] == "doctor":
        payload["clinical"] = {
            "assessment_results": results,
            "domain_metrics": (
                {key: latest.get(key) for key in ("speech_score", "memory_score", "reaction_score", "executive_score", "motor_score")}
                if latest
                else {}
            ),
            "anomaly_detection": latest.get("anomaly_details") if latest else None,
            "session_quality": (
                {"confidence": latest.get("confidence"), "retest_recommended": latest.get("recommend_retest")}
                if latest
                else {}
            ),
            "feature_importance": latest.get("feature_importance", []),
            "patient_history": results,
        }

    audit_service.record(
        event="dashboard.patient_detail_read",
        actor_id=user["id"],
        actor_role=user.get("role"),
        subject_id=patient_id,
        outcome="success",
    )
    return payload


@router.get("/patient/{patient_id}/alerts")
def get_patient_alerts(patient_id: str, authorization: str = Header(...)) -> Dict[str, Any]:
    """Retrieve evaluated caregiver alerts for a patient."""
    user = member(authorization)
    verify_patient_access(user, patient_id)

    alerts = caregiver_alert_service.evaluate_caregiver_alerts(patient_id)
    audit_service.record(
        event="caregiver_alerts.read",
        actor_id=user["id"],
        actor_role=user.get("role"),
        subject_id=patient_id,
        outcome="success",
        metadata={"count": len(alerts)},
    )
    return {
        "patient_id": patient_id,
        "alerts": alerts,
        "active_count": sum(1 for a in alerts if a.get("status") == "new"),
        "total_count": len(alerts),
    }


@router.post("/patient/{patient_id}/alerts/{alert_id}/review")
def review_alert(
    patient_id: str,
    alert_id: str,
    payload: Optional[Dict[str, Any]] = None,
    authorization: str = Header(...),
) -> Dict[str, Any]:
    """Mark a caregiver alert as reviewed (or toggle back to new)."""
    user = member(authorization)
    verify_patient_access(user, patient_id)

    target_status = "reviewed"
    if payload and "status" in payload:
        target_status = payload["status"]

    updated = caregiver_alert_service.mark_alert_status(
        patient_id=patient_id,
        alert_id=alert_id,
        status=target_status,
        reviewer_id=user["id"],
    )

    audit_service.record(
        event="caregiver_alerts.status_updated",
        actor_id=user["id"],
        actor_role=user.get("role"),
        subject_id=patient_id,
        outcome="success",
        metadata={"alert_id": alert_id, "status": target_status},
    )

    return {
        "patient_id": patient_id,
        "alert_id": alert_id,
        "review_state": updated,
        "message": f"Alert marked as {target_status}.",
    }


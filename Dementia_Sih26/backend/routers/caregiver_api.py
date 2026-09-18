"""
caregiver_api.py — Patient-Caregiver Relationship Management API
=================================================================
Enforces patient autonomy over caregiver appointments, invitations, and revocations.
Strictly separates patient-caregiver relationships from doctor-patient relationships.
Screening output is never a clinical diagnosis.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from services import auth_service
from services.audit_service import record

router = APIRouter(prefix="/caregivers", tags=["caregivers"])


class CaregiverAssignRequest(BaseModel):
    caregiver_identity: str = Field(..., min_length=3, max_length=150, description="Caregiver email address or user ID")


class CaregiverRevokeRequest(BaseModel):
    caregiver_id: str = Field(..., min_length=1, max_length=100, description="Caregiver user ID to revoke access for")


@router.get("/my-caregivers", response_model=Dict[str, Any])
def get_my_caregivers(authorization: str = Header(...)) -> Dict[str, Any]:
    """Retrieve all caregivers associated with the authenticated patient."""
    user = auth_service.require_user(authorization)
    if user.get("role") != "patient":
        raise HTTPException(status_code=403, detail="Only patients can view their assigned caregivers.")

    relationships = auth_service.get_patient_caregiver_relationships(patient_id=user["id"], active_only=False)
    record(
        event="care_team.caregivers_read",
        actor_id=user["id"],
        actor_role=user.get("role"),
        subject_id=user["id"],
        outcome="success",
        metadata={"count": len(relationships)},
    )
    return {
        "patient_id": user["id"],
        "caregivers": relationships,
        "active_count": sum(1 for r in relationships if r.get("status") == "connected" and r.get("access_granted", True)),
    }


@router.post("/assign", response_model=Dict[str, Any])
def assign_caregiver(payload: CaregiverAssignRequest, authorization: str = Header(...)) -> Dict[str, Any]:
    """Patient assigns/invites a caregiver by email or user ID."""
    user = auth_service.require_user(authorization)
    if user.get("role") != "patient":
        raise HTTPException(status_code=403, detail="Only patients can assign caregivers.")

    relationship = auth_service.assign_caregiver_to_patient(user["id"], payload.caregiver_identity)
    return {
        "message": "Caregiver assigned successfully.",
        "relationship": relationship,
    }


@router.post("/revoke", response_model=Dict[str, Any])
def revoke_caregiver(payload: CaregiverRevokeRequest, authorization: str = Header(...)) -> Dict[str, Any]:
    """Patient revokes access for an assigned caregiver."""
    user = auth_service.require_user(authorization)
    if user.get("role") != "patient":
        raise HTTPException(status_code=403, detail="Only patients can revoke caregiver access.")

    result = auth_service.revoke_caregiver_from_patient(user["id"], payload.caregiver_id)
    return result

from __future__ import annotations

import os
import sys
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException

# Ensure root directory is on sys.path for ml module imports
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.behavioral_ml import evaluate_behavioral_anomaly
from core.clinical_config import (
    DOMAIN_WEIGHTS,
    FATIGUE_CONFIDENCE_THRESHOLD,
    SAFE_OUTPUT_LANGUAGE,
    compute_confidence_score,
    get_education_correction,
    map_education_to_years,
)
from core.ml_engine import (
    compute_confidence_interval,
    compute_feature_importance,
    compute_uncertainty,
)
from core.progress_tracker import build_progress_summary
from core.signal_fusion import fuse_cognitive_signals
from core.storage import results_store
from ml.clinical_model import (
    get_clinical_model_validation_metrics,
    predict_clinical_reference,
)
from models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    DiseaseRiskLevels,
    MLAnalysis,
    MLBehavioralAnalysis,
    MLClinicalReference,
    MLCombinedIndicator,
    MLOverallAttention,
)
from services import auth_service
from services.ai_service import (
    _prob_to_level,
    build_feature_vector,
    compute_feature_provenance,
    extract_executive_features,
    extract_memory_features,
    extract_motor_features,
    extract_reaction_features,
    extract_speech_features,
)
from utils.logger import log_info

router = APIRouter(tags=["analysis"])
DISCLAIMER = SAFE_OUTPUT_LANGUAGE["disclaimer"]


def _compute_composite_risk(speech: float, memory: float, reaction: float, executive: float, motor: float) -> float:
    values = {
        "speech": speech,
        "memory": memory,
        "reaction": reaction,
        "executive": executive,
        "motor": motor,
    }
    risk = sum(DOMAIN_WEIGHTS[key] * (100.0 - values[key]) for key in values)
    return round(max(0.0, min(100.0, risk)), 2)


def _compute_risk_drivers(speech: float, memory: float, reaction: float, executive: float, motor: float) -> dict[str, float]:
    contributions = {
        "speech": DOMAIN_WEIGHTS["speech"] * (100.0 - speech),
        "memory": DOMAIN_WEIGHTS["memory"] * (100.0 - memory),
        "reaction": DOMAIN_WEIGHTS["reaction"] * (100.0 - reaction),
        "executive": DOMAIN_WEIGHTS["executive"] * (100.0 - executive),
        "motor": DOMAIN_WEIGHTS["motor"] * (100.0 - motor),
    }
    total = sum(contributions.values()) or 1.0
    percentages = {key: round((value / total) * 100) for key, value in contributions.items()}
    return {
        "memory_recall_contribution_pct": percentages["memory"],
        "executive_function_contribution_pct": percentages["executive"],
        "speech_delay_contribution_pct": percentages["speech"],
        "reaction_time_contribution_pct": percentages["reaction"],
        "motor_consistency_contribution_pct": percentages["motor"],
    }


def _optional_user(authorization: Optional[Any]) -> Optional[dict[str, Any]]:
    if not authorization or not isinstance(authorization, str):
        return None
    token = auth_service.extract_bearer_token(authorization)
    return auth_service.get_user_from_token(token)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(payload: AnalyzeRequest, authorization: Optional[str] = Header(default=None)) -> AnalyzeResponse:
    log_info("analysis request received")
    try:
        speech_score, speech_features = extract_speech_features(payload.speech_audio or None, payload.speech)
        memory_score, memory_features = extract_memory_features(payload.memory_results, payload.memory)
        reaction_score, reaction_features = extract_reaction_features(payload.reaction_times, payload.reaction)
        executive_score, executive_features = extract_executive_features(payload.stroop)
        motor_score, motor_features = extract_motor_features(payload.tap)
        feature_vector = build_feature_vector(
            speech_features,
            memory_features,
            reaction_features,
            executive_features,
            motor_features,
        )
        feature_provenance, categorized_provenance, provenance_counts = compute_feature_provenance(
            audio_b64=payload.speech_audio,
            speech=payload.speech,
            memory_results=payload.memory_results,
            memory=payload.memory,
            reaction_times=payload.reaction_times,
            reaction=payload.reaction,
            stroop=payload.stroop,
            tap=payload.tap,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Processing error: {exc}") from exc

    if payload.profile and payload.profile.education_level:
        memory_score = max(0.0, min(100.0, memory_score + get_education_correction(payload.profile.education_level) * 100))

    fatigue = payload.fatigue.model_dump() if payload.fatigue else {}
    confidence = compute_confidence_score(0.0, fatigue)
    recommend_retest = confidence < FATIGUE_CONFIDENCE_THRESHOLD

    # ── Retrieve patient longitudinal history ───────────────────────────────────
    current_user = _optional_user(authorization)
    hist_feature_vectors = []
    user_id = current_user["id"] if current_user else None

    if user_id:
        results = results_store.read()
        history = results.get(user_id, [])
        for record in history:
            if "feature_vector" in record and record["feature_vector"]:
                hist_feature_vectors.append(record["feature_vector"])
            else:
                hist_feature_vectors.append(record)

    # ── LAYER A: Behavioral Anomaly Detection ──────────────────────────────────
    behavioral_analysis = evaluate_behavioral_anomaly(
        current_features=feature_vector.model_dump(),
        historical_sessions=hist_feature_vectors,
        min_history=3,
    )
    behavioral_analysis["feature_provenance"] = feature_provenance

    # ── LAYER B: Clinical Reference Model ──────────────────────────────────────
    clinical_inputs = None
    if payload.clinical_inputs is not None:
        clinical_inputs = dict(payload.clinical_inputs)
    elif payload.profile and payload.profile.age is not None:
        mapped_educ = map_education_to_years(payload.profile.education_level)
        clinical_inputs = {"Age": float(payload.profile.age)}
        if mapped_educ is not None:
            clinical_inputs["EDUC"] = mapped_educ
    clinical_analysis = predict_clinical_reference(clinical_inputs)

    # ── MULTI-MODAL SIGNAL FUSION ──────────────────────────────────────────────
    fusion_result = fuse_cognitive_signals(
        behavioral_anomaly_result=behavioral_analysis,
        clinical_reference_result=clinical_analysis,
    )

    # ── REAL MODEL VALIDATION METRICS (Zero Fabrication) ──────────────────────
    model_validation = get_clinical_model_validation_metrics()

    # ── EXPLAINABILITY & UNCERTAINTY ───────────────────────────────────────────
    uncertainty = compute_uncertainty()
    clinical_prob = clinical_analysis.get("probability")
    confidence_interval = compute_confidence_interval(clinical_prob)

    composite_risk = _compute_composite_risk(speech_score, memory_score, reaction_score, executive_score, motor_score)
    risk_drivers = _compute_risk_drivers(speech_score, memory_score, reaction_score, executive_score, motor_score)
    feature_importance = compute_feature_importance(
        feature_vector=feature_vector.model_dump(),
        baseline_deviations=behavioral_analysis.get("top_deviating_features"),
    )

    mean_rt = reaction_features.get("mean_rt", 1.0)
    std_rt = reaction_features.get("std_rt", 0.0)
    attention_variability_index = round(std_rt / mean_rt, 4) if mean_rt > 0 else 0.0

    # Structured ML Analysis payload
    behavioral_model = MLBehavioralAnalysis(**behavioral_analysis)
    clinical_model = MLClinicalReference(**clinical_analysis)
    combined_model = MLCombinedIndicator(**fusion_result["combined_indicator"])
    overall_attention_model = MLOverallAttention(**fusion_result["overall_attention"])

    ml_analysis_obj = MLAnalysis(
        behavioral_deviation=behavioral_model,
        clinical_reference=clinical_model,
        overall_attention=overall_attention_model,
        behavioral=behavioral_model,
        combined_indicator=combined_model,
    )

    # ── Result Persistence ─────────────────────────────────────────────────────
    combined_val = fusion_result["combined_indicator"].get("value")
    result_data = {
        "timestamp": auth_service.utcnow_iso(),
        "createdAt": auth_service.utcnow_iso(),
        "speech_score": speech_score,
        "memory_score": memory_score,
        "reaction_score": reaction_score,
        "executive_score": executive_score,
        "motor_score": motor_score,
        "alzheimers_risk": clinical_prob,
        "dementia_risk": clinical_prob,
        "parkinsons_risk": None,
        "composite_risk_score": composite_risk,
        "hybrid_risk": combined_val,
        "confidence": confidence,
        "risk_levels": {
            "alzheimers": _prob_to_level(clinical_prob),
            "dementia": _prob_to_level(clinical_prob),
            "parkinsons": "N/A",
        },
        "attention_variability_index": attention_variability_index,
        "feature_vector": feature_vector.model_dump(),
        "feature_provenance": feature_provenance,
        "provenance_summary": provenance_counts,
        "ml_analysis": ml_analysis_obj.model_dump(),
        "disclaimer": DISCLAIMER,
    }

    if user_id:
        results = results_store.read()
        history = results.get(user_id, [])
        history.append(result_data)
        results[user_id] = history[-20:]
        results_store.write(results)

    anomaly_alert = (
        behavioral_analysis.get("severity", "none")
        if behavioral_analysis.get("anomaly_detected")
        else "none"
    )

    return AnalyzeResponse(
        speech_score=speech_score,
        memory_score=memory_score,
        reaction_score=reaction_score,
        executive_score=executive_score,
        motor_score=motor_score,
        alzheimers_risk=clinical_prob,
        dementia_risk=clinical_prob,
        parkinsons_risk=None,
        risk_levels=DiseaseRiskLevels(
            alzheimers=_prob_to_level(clinical_prob),
            dementia=_prob_to_level(clinical_prob),
            parkinsons="N/A",
        ),
        ml_analysis=ml_analysis_obj,
        uncertainty=uncertainty,
        composite_risk_score=composite_risk,
        hybrid_risk=combined_val,
        confidence=confidence,
        recommend_retest=recommend_retest,
        ci_lower=confidence_interval["ci_lower"],
        ci_upper=confidence_interval["ci_upper"],
        ci_label=confidence_interval["ci_label"],
        logistic_risk_probability=clinical_prob,
        confidence_interval_label=confidence_interval["ci_label"],
        anomaly_alert=anomaly_alert,
        anomaly_details={"behavioral_anomaly": behavioral_analysis} if anomaly_alert != "none" else None,
        risk_drivers=risk_drivers,
        feature_importance=feature_importance,
        model_validation=model_validation,
        feature_vector=feature_vector,
        attention_variability_index=attention_variability_index,
        feature_provenance=feature_provenance,
        measured_features=categorized_provenance["measured"],
        derived_features=categorized_provenance["derived"],
        defaulted_features=categorized_provenance["defaulted"],
        provenance_summary=provenance_counts,
        disclaimer=DISCLAIMER,
    )


@router.get("/results/my")
def get_my_results(authorization: str = Header(...)) -> dict[str, Any]:
    user = auth_service.require_user(authorization)
    results = results_store.read()
    user_results = results.get(user["id"], [])
    from services.audit_service import record
    record(
        event="phi.read_self",
        actor_id=user["id"],
        actor_role=user.get("role"),
        subject_id=user["id"],
        outcome="success",
        metadata={"record_count": len(user_results)},
    )
    return {"results": user_results, "progress": build_progress_summary(user_results)}


@router.get("/results/patient/{patient_id}")
def get_patient_results(patient_id: str, authorization: str = Header(...)) -> dict[str, Any]:
    care_member = auth_service.require_care_team(authorization)
    from services.audit_service import record
    from routers.consent_api import check_patient_consent

    # 1. Enforce doctor/caregiver care relationship
    if not auth_service.verify_care_member_patient_access(care_member, patient_id):
        record(
            event="phi.access_denied",
            actor_id=care_member["id"],
            actor_role=care_member.get("role"),
            subject_id=patient_id,
            outcome="forbidden",
            metadata={"reason": "unassigned_patient", "resource": "cognitive_results"},
        )
        raise HTTPException(status_code=403, detail="This patient is not assigned to your care team.")

    # 2. Enforce patient consent
    if not check_patient_consent(patient_id, "share_with_care_team"):
        record(
            event="phi.access_denied",
            actor_id=care_member["id"],
            actor_role=care_member.get("role"),
            subject_id=patient_id,
            outcome="forbidden",
            metadata={"reason": "consent_withheld", "resource": "cognitive_results"},
        )
        raise HTTPException(status_code=403, detail="Patient has not granted consent to share screening results with care team.")

    results = results_store.read()
    patient_results = results.get(patient_id, [])

    record(
        event="phi.read",
        actor_id=care_member["id"],
        actor_role=care_member.get("role"),
        subject_id=patient_id,
        outcome="success",
        metadata={"record_count": len(patient_results), "resource": "cognitive_results"},
    )
    return {"results": patient_results, "progress": build_progress_summary(patient_results)}

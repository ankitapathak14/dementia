"""
caregiver_alert_service.py — Explainable Caregiver Alerts & Monitoring Service
================================================================================
Evaluates patient activity, medication schedules, and cognitive game records
to generate non-diagnostic, observational alerts for family caregivers and clinicians.

Alert Categories:
1. Missed Medication (unacknowledged medication reminder beyond grace period)
2. Unusual Inactivity (no cognitive activity recorded for threshold days)
3. Sudden Performance Change (decline in cognitive training performance vs baseline)
4. Missed Routine (daily/morning routine incomplete after expected window)
5. Repeated Difficulty (consecutive low-scoring attempts on a cognitive game)

SIH PS 26003: Strictly observational language. Never outputs a clinical diagnosis.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.storage import (
    caregiver_alerts_store,
    game_sessions_store,
    reminders_store,
    results_store,
    routine_logs_store,
)
from services.auth_service import utcnow_iso

# Configurable alert thresholds
DEFAULT_ALERT_THRESHOLDS: Dict[str, Any] = {
    "medication_grace_minutes": 30,
    "inactivity_days_threshold": 3,
    "performance_drop_percentage": 15.0,  # 15 percentage points drop
    "routine_grace_minutes": 60,
    "repeated_difficulty_attempts": 3,
    "repeated_difficulty_score_threshold": 55.0,  # Below 55%
}

STATUTORY_DISCLAIMER = "Activity and performance observation for caregiver review. Not a medical diagnosis."


def _parse_iso(iso_str: str) -> Optional[datetime]:
    if not iso_str:
        return None
    try:
        clean = iso_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean)
    except (ValueError, TypeError):
        return None


def _deterministic_id(patient_id: str, category: str, key_info: str) -> str:
    raw = f"{patient_id}_{category}_{key_info}"
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]
    return f"alert_{category[:4]}_{digest}"


def get_alert_states(patient_id: str) -> Dict[str, Dict[str, Any]]:
    """Retrieve persisted review states for a patient's alerts."""
    all_states = caregiver_alerts_store.read()
    return all_states.get(patient_id, {})


def mark_alert_status(
    patient_id: str,
    alert_id: str,
    status: str = "reviewed",
    reviewer_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Mark an alert as 'reviewed' or 'new' with timestamp and reviewer ID.
    Persists atomically to caregiver_alerts_store.
    """
    now = utcnow_iso()
    record = {
        "status": status,
        "reviewed_at": now if status == "reviewed" else None,
        "reviewed_by": reviewer_id,
        "updated_at": now,
    }

    def _mutator(existing: Dict[str, Any]) -> Dict[str, Any]:
        if patient_id not in existing:
            existing[patient_id] = {}
        existing[patient_id][alert_id] = record
        return existing

    caregiver_alerts_store.update(_mutator)
    return record


def _eval_missed_medication(
    patient_id: str,
    reminders: List[Dict[str, Any]],
    now: datetime,
    thresholds: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Category 1: Missed Medication reminder."""
    alerts = []
    grace_mins = thresholds.get("medication_grace_minutes", 30)

    now_minutes = now.hour * 60 + now.minute

    med_reminders = [
        r for r in reminders
        if r.get("category") == "medicine" and r.get("status") != "completed"
    ]

    for r in med_reminders:
        time_str = r.get("scheduled_time", "")
        if not time_str or ":" not in time_str:
            continue

        try:
            parts = time_str.split(":")
            sched_hour = int(parts[0])
            sched_minute = int(parts[1])
            sched_minutes = sched_hour * 60 + sched_minute
        except (ValueError, IndexError):
            continue

        # Compute elapsed time
        if now_minutes >= sched_minutes + grace_mins:
            elapsed = now_minutes - sched_minutes
        else:
            # Check if overdue from earlier cycle / yesterday if unacknowledged
            elapsed = (24 * 60 - sched_minutes) + now_minutes

        if elapsed >= grace_mins:
            alert_id = _deterministic_id(patient_id, "medication", r.get("id", time_str))
            title = r.get("title", "Medication")
            dosage = r.get("dosage") or ""
            dosage_str = f" ({dosage})" if dosage else ""

            alerts.append({
                "id": alert_id,
                "category": "missed_medication",
                "category_label": "Missed Medication",
                "category_icon": "💊",
                "severity": "high",
                "title": "Medication reminder not acknowledged",
                "message": f"Medication reminder for {title}{dosage_str} due at {time_str} remains unacknowledged ({elapsed} minutes past schedule).",
                "timestamp": now.isoformat(),
                "due_time": time_str,
                "delay_minutes": elapsed,
                "data": {
                    "reminder_id": r.get("id"),
                    "medication_title": title,
                    "scheduled_time": time_str,
                    "dosage": dosage,
                    "instructions": r.get("instructions") or "Take with water.",
                    "status_note": f"Not acknowledged for {elapsed} minutes",
                },
                "recommended_action": "Contact patient or family member to confirm medication intake.",
                "disclaimer": STATUTORY_DISCLAIMER,
            })

    return alerts


def _eval_unusual_inactivity(
    patient_id: str,
    sessions: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
    now: datetime,
    thresholds: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Category 2: Unusual Inactivity."""
    alerts = []
    days_thresh = thresholds.get("inactivity_days_threshold", 3)

    all_timestamps: List[datetime] = []
    for s in sessions:
        ts = _parse_iso(s.get("timestamp"))
        if ts:
            all_timestamps.append(ts)
    for r in results:
        ts = _parse_iso(r.get("timestamp") or r.get("createdAt"))
        if ts:
            all_timestamps.append(ts)

    if not all_timestamps:
        alert_id = _deterministic_id(patient_id, "inactivity", "no_records")
        alerts.append({
            "id": alert_id,
            "category": "unusual_inactivity",
            "category_label": "Unusual Inactivity",
            "category_icon": "⏳",
            "severity": "moderate",
            "title": "No cognitive activity recorded",
            "message": "No cognitive gaming or assessment sessions recorded. Expected activity: 4 sessions/week.",
            "timestamp": now.isoformat(),
            "data": {
                "days_inactive": 5,
                "last_active_date": "None logged",
                "expected_frequency": "4 sessions/week",
            },
            "recommended_action": "Encourage patient to try a gentle Level 1 memory or rhythm game.",
            "disclaimer": STATUTORY_DISCLAIMER,
        })
        return alerts

    all_timestamps.sort()
    latest_ts = all_timestamps[-1]
    diff_days = (now - latest_ts).total_seconds() / 86400.0

    if diff_days >= days_thresh:
        days_int = max(1, int(diff_days))
        alert_id = _deterministic_id(patient_id, "inactivity", latest_ts.strftime("%Y%m%d"))
        alerts.append({
            "id": alert_id,
            "category": "unusual_inactivity",
            "category_label": "Unusual Inactivity",
            "category_icon": "⏳",
            "severity": "moderate",
            "title": f"No cognitive activity recorded for the last {days_int} days",
            "message": f"No cognitive activity recorded for the last {days_int} days (Expected: 4 sessions/week).",
            "timestamp": now.isoformat(),
            "data": {
                "days_inactive": days_int,
                "last_active_date": latest_ts.strftime("%b %d, %Y"),
                "expected_frequency": "4 sessions/week",
            },
            "recommended_action": "Encourage patient to engage in a low-stress cognitive exercise or review daily routine.",
            "disclaimer": STATUTORY_DISCLAIMER,
        })

    return alerts


def _eval_performance_change(
    patient_id: str,
    sessions: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
    now: datetime,
    thresholds: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Category 3: Sudden Performance Change."""
    alerts = []
    drop_thresh = thresholds.get("performance_drop_percentage", 15.0)

    # Group sessions by game_id
    games_map: Dict[str, List[Dict[str, Any]]] = {}
    for s in sessions:
        gid = s.get("game_id")
        if gid:
            games_map.setdefault(gid, []).append(s)

    for gid, g_sessions in games_map.items():
        if len(g_sessions) >= 3:
            g_sessions.sort(key=lambda x: x.get("timestamp", ""))
            split_idx = max(1, len(g_sessions) // 2)
            baseline_sessions = g_sessions[:split_idx]
            recent_sessions = g_sessions[split_idx:]

            base_avg = sum(s.get("score", 0) for s in baseline_sessions) / len(baseline_sessions)
            recent_avg = sum(s.get("score", 0) for s in recent_sessions) / len(recent_sessions)
            drop = base_avg - recent_avg

            if drop >= drop_thresh:
                game_title = g_sessions[-1].get("game_title") or gid.replace("_", " ").title()
                alert_id = _deterministic_id(patient_id, "performance", gid)
                recent_scores = [s.get("score", 0) for s in recent_sessions[-3:]]

                alerts.append({
                    "id": alert_id,
                    "category": "performance_change",
                    "category_label": "Performance Change",
                    "category_icon": "📉",
                    "severity": "moderate",
                    "title": "Recent performance decrease detected",
                    "message": f"Recent performance decrease detected in {game_title} ({round(recent_avg)}% vs baseline {round(base_avg)}%, change: -{round(drop)} percentage points).",
                    "timestamp": now.isoformat(),
                    "data": {
                        "game_id": gid,
                        "game_title": game_title,
                        "previous_average": round(base_avg, 1),
                        "recent_average": round(recent_avg, 1),
                        "percentage_change": -round(drop, 1),
                        "recent_attempts": recent_scores,
                        "status_note": "Performance change detected",
                    },
                    "recommended_action": "Review recent activity with caregiver or clinician. Consider lowering game difficulty.",
                    "disclaimer": STATUTORY_DISCLAIMER,
                })

    # If no game session drops, evaluate longitudinal assessment drift if available
    if not alerts and len(results) >= 2:
        res_scores = [
            sum(r.get(k, 0) for k in ("speech_score", "memory_score", "reaction_score", "executive_score", "motor_score")) / 5.0
            for r in results
        ]
        base_score = res_scores[0]
        curr_score = res_scores[-1]
        drop = base_score - curr_score
        if drop >= drop_thresh:
            alert_id = _deterministic_id(patient_id, "performance", "assessment_composite")
            alerts.append({
                "id": alert_id,
                "category": "performance_change",
                "category_label": "Performance Change",
                "category_icon": "📉",
                "severity": "moderate",
                "title": "Recent performance decrease detected",
                "message": f"Multi-domain assessment composite score dropped from baseline {round(base_score)} to {round(curr_score)} (-{round(drop)} percentage points).",
                "timestamp": now.isoformat(),
                "data": {
                    "game_id": "composite_assessment",
                    "game_title": "Multi-Domain Cognitive Screening",
                    "previous_average": round(base_score, 1),
                    "recent_average": round(curr_score, 1),
                    "percentage_change": -round(drop, 1),
                    "recent_attempts": [round(s, 1) for s in res_scores[-3:]],
                    "status_note": "Performance change detected",
                },
                "recommended_action": "Schedule clinician supervisory review. Non-diagnostic screening indicator.",
                "disclaimer": STATUTORY_DISCLAIMER,
            })

    return alerts


def _eval_missed_routine(
    patient_id: str,
    reminders: List[Dict[str, Any]],
    now: datetime,
    thresholds: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Category 4: Missed Routine."""
    alerts = []
    morning_items = []
    for r in reminders:
        time_str = r.get("scheduled_time", "")
        if ":" in time_str:
            try:
                hour = int(time_str.split(":")[0])
                if hour < 14:
                    morning_items.append(r)
            except ValueError:
                pass

    if morning_items:
        completed = [r.get("title", "Task") for r in morning_items if r.get("status") == "completed"]
        incomplete = [r.get("title", "Task") for r in morning_items if r.get("status") != "completed"]

        if incomplete:
            alert_id = _deterministic_id(patient_id, "routine", "morning_routine")
            alerts.append({
                "id": alert_id,
                "category": "missed_routine",
                "category_label": "Missed Routine",
                "category_icon": "⏰",
                "severity": "moderate",
                "title": "Morning routine is incomplete",
                "message": f"Morning routine is incomplete: {incomplete[0]} has not been acknowledged.",
                "timestamp": now.isoformat(),
                "data": {
                    "routine_name": "Morning Routine",
                    "completed_items": completed,
                    "incomplete_items": incomplete,
                    "total_items": len(morning_items),
                    "adherence_rate": f"{len(completed)}/{len(morning_items)} completed",
                },
                "recommended_action": "Prompt patient or assist in completing remaining morning care activities.",
                "disclaimer": STATUTORY_DISCLAIMER,
            })

    return alerts


def _eval_repeated_difficulty(
    patient_id: str,
    sessions: List[Dict[str, Any]],
    now: datetime,
    thresholds: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Category 5: Repeated Difficulty on a cognitive game."""
    alerts = []
    n_attempts = thresholds.get("repeated_difficulty_attempts", 3)
    score_thresh = thresholds.get("repeated_difficulty_score_threshold", 55.0)

    games_map: Dict[str, List[Dict[str, Any]]] = {}
    for s in sessions:
        gid = s.get("game_id")
        if gid:
            games_map.setdefault(gid, []).append(s)

    for gid, g_sessions in games_map.items():
        if len(g_sessions) >= n_attempts:
            g_sessions.sort(key=lambda x: x.get("timestamp", ""))
            recent_n = g_sessions[-n_attempts:]
            scores = [s.get("score", 0) for s in recent_n]

            if all(sc < score_thresh for sc in scores):
                game_title = recent_n[-1].get("game_title") or gid.replace("_", " ").title()
                alert_id = _deterministic_id(patient_id, "difficulty", gid)
                avg_sc = round(sum(scores) / len(scores), 1)
                curr_level = recent_n[-1].get("difficulty_level", 1)

                alerts.append({
                    "id": alert_id,
                    "category": "repeated_difficulty",
                    "category_label": "Repeated Difficulty",
                    "category_icon": "🎯",
                    "severity": "moderate",
                    "title": f"Repeated low performance detected in {game_title}",
                    "message": f"Repeated low performance detected in {game_title} across the last {n_attempts} attempts ({', '.join(str(s) + '%' for s in scores)}).",
                    "timestamp": now.isoformat(),
                    "data": {
                        "game_id": gid,
                        "game_title": game_title,
                        "recent_attempts": scores,
                        "average_score": avg_sc,
                        "current_difficulty": f"Level {curr_level}",
                    },
                    "recommended_action": f"Consider lowering difficulty to Level {max(1, curr_level - 1)} or encouraging patient with verbal cues.",
                    "disclaimer": STATUTORY_DISCLAIMER,
                })

    return alerts


def evaluate_caregiver_alerts(
    patient_id: str,
    thresholds: Optional[Dict[str, Any]] = None,
    current_time: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Deterministically evaluates all 5 alert categories for the specified patient.
    Attaches persisted review status from caregiver_alerts_store.
    """
    thresh = dict(DEFAULT_ALERT_THRESHOLDS)
    if thresholds:
        thresh.update(thresholds)

    now = current_time or datetime.now(timezone.utc)

    # Read patient data from active stores
    all_reminders = reminders_store.read()
    patient_reminders = [r for r in all_reminders if r.get("user_id") == patient_id]

    all_sessions = game_sessions_store.read()
    patient_sessions = [s for s in all_sessions if s.get("user_id") == patient_id]

    all_results = results_store.read()
    patient_results = all_results.get(patient_id, [])

    # Evaluate 5 categories
    alerts: List[Dict[str, Any]] = []

    # 1. Missed Medication
    alerts.extend(_eval_missed_medication(patient_id, patient_reminders, now, thresh))

    # 2. Unusual Inactivity
    alerts.extend(_eval_unusual_inactivity(patient_id, patient_sessions, patient_results, now, thresh))

    # 3. Sudden Performance Change
    alerts.extend(_eval_performance_change(patient_id, patient_sessions, patient_results, now, thresh))

    # 4. Missed Routine
    alerts.extend(_eval_missed_routine(patient_id, patient_reminders, now, thresh))

    # 5. Repeated Difficulty
    alerts.extend(_eval_repeated_difficulty(patient_id, patient_sessions, now, thresh))

    # Hydrate review state
    states = get_alert_states(patient_id)
    for alert in alerts:
        aid = alert["id"]
        if aid in states:
            saved = states[aid]
            alert["status"] = saved.get("status", "new")
            alert["reviewed_at"] = saved.get("reviewed_at")
            alert["reviewed_by"] = saved.get("reviewed_by")
        else:
            alert["status"] = "new"
            alert["reviewed_at"] = None
            alert["reviewed_by"] = None

    # Sort: 'new' status first, then high severity
    severity_order = {"high": 0, "moderate": 1, "low": 2, "info": 3}
    alerts.sort(
        key=lambda a: (
            0 if a.get("status") == "new" else 1,
            severity_order.get(a.get("severity", "moderate"), 99),
            a.get("title", ""),
        )
    )

    return alerts

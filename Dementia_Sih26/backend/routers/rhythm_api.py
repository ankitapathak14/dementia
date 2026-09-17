"""
rhythm_api.py — Rhythm & Recall Music Engagement API
=====================================================
REST endpoints for the Rhythm & Recall music-based engagement game.
This feature is for enjoyable cognitive stimulation — NOT a diagnostic tool.
All metrics are engagement metrics, never clinical severity scores.
SIH PS 26003 — NeuroAid.
"""
from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException

from core.storage import (
    rhythm_music_store,
    rhythm_sessions_store,
    rhythm_preferences_store,
)
from models.schemas import (
    MusicTrack,
    MusicPreferences,
    RhythmSessionCreate,
    RhythmSessionResponse,
    RhythmRoundData,
    RhythmAnalytics,
)
from services import auth_service

router = APIRouter(prefix="/rhythm", tags=["rhythm-recall"])

# Path to the bundled seed catalogue
_SEED_PATH = Path(__file__).parent.parent / "data" / "rhythm_music_catalogue.json"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _optional_user(authorization: Optional[str]) -> Optional[Dict[str, Any]]:
    if not authorization:
        return None
    token = auth_service.extract_bearer_token(authorization)
    return auth_service.get_user_from_token(token)


def _require_user(authorization: Optional[str]) -> Dict[str, Any]:
    user = _optional_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user


def _get_music_catalogue() -> List[Dict]:
    """Return the live music catalogue, seeding from JSON if empty."""
    tracks = rhythm_music_store.read()
    if not isinstance(tracks, list):
        tracks = []
    if not tracks and _SEED_PATH.exists():
        with _SEED_PATH.open("r", encoding="utf-8") as f:
            seed = json.load(f)
        rhythm_music_store.write(seed)
        tracks = seed
    return [t for t in tracks if t.get("is_active", True)]


def _get_user_preferences(user_id: str) -> Dict:
    prefs = rhythm_preferences_store.read()
    if not isinstance(prefs, dict):
        prefs = {}
    return prefs.get(user_id, {})


def _engagement_label(recognition_pct: Optional[float], tap_count: int, voice: bool) -> str:
    """Generate a positive engagement label — never a clinical diagnosis."""
    parts = []
    if recognition_pct is not None:
        if recognition_pct >= 80:
            parts.append("Excellent song recognition!")
        elif recognition_pct >= 60:
            parts.append("Good song recognition!")
        else:
            parts.append("Enjoyed listening to songs!")
    if tap_count > 5:
        parts.append("Great rhythm participation!")
    if voice:
        parts.append("Wonderful voice participation!")
    return " ".join(parts) if parts else "Wonderful session participation!"


def _encouragement(recognition_pct: Optional[float]) -> str:
    messages = [
        "🌟 Wonderful participation today!",
        "🎵 Music brings joy — great session!",
        "⭐ Every session is a celebration!",
        "🎶 Thank you for sharing this musical moment!",
        "🌸 What a lovely music session!",
    ]
    return random.choice(messages)


def _compute_rhythm_engagement(tap_timestamps: List[float], beat_timestamps: List[float]) -> float:
    """
    Compute rhythm engagement percentage.
    Robust to elderly users with slower motor responses — uses a wide tolerance window.
    Returns a value 0–100 representing PARTICIPATION, not clinical precision.
    """
    if not tap_timestamps:
        return 0.0
    if not beat_timestamps:
        # No beat reference — score based on tap consistency alone
        if len(tap_timestamps) < 2:
            return 50.0
        intervals = [tap_timestamps[i+1] - tap_timestamps[i] for i in range(len(tap_timestamps)-1)]
        avg_interval = sum(intervals) / len(intervals)
        if avg_interval <= 0:
            return 50.0
        deviations = [abs(iv - avg_interval) / avg_interval for iv in intervals]
        consistency = max(0.0, 1.0 - (sum(deviations) / len(deviations)))
        return round(min(100.0, consistency * 100), 1)

    # Match taps to nearest beat with generous ±500ms elderly-friendly tolerance
    TOLERANCE = 0.5
    matched = 0
    for tap in tap_timestamps:
        for beat in beat_timestamps:
            if abs(tap - beat) <= TOLERANCE:
                matched += 1
                break
    ratio = matched / max(len(beat_timestamps), 1)
    # Boost so that partial participation still reads positively
    engagement = min(100.0, (ratio * 70) + (min(len(tap_timestamps), 10) / 10 * 30))
    return round(engagement, 1)


def _trend_note(sessions: List[Dict]) -> str:
    """Generate a neutral trend observation — never a clinical diagnosis."""
    if len(sessions) < 3:
        return "Building a session history — keep enjoying the music!"
    recognition_scores = [
        s.get("recognition_pct") for s in sessions[-6:]
        if s.get("recognition_pct") is not None
    ]
    if len(recognition_scores) < 2:
        return "Great participation across recent sessions."
    diff = recognition_scores[-1] - recognition_scores[0]
    if abs(diff) <= 10:
        return "Song recognition has remained generally consistent across recent sessions."
    elif diff > 10:
        return "A positive change in recent session participation was observed."
    else:
        return "A change in recent session participation was observed. Consider discussing with a healthcare professional if this persists."


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/music", response_model=List[MusicTrack])
def list_music() -> List[MusicTrack]:
    """List all active music tracks in the catalogue."""
    tracks = _get_music_catalogue()
    return [MusicTrack(**t) for t in tracks]


@router.get("/music/personalized")
def get_personalized_music(
    authorization: Optional[str] = Header(default=None),
    count: int = 10,
) -> Dict[str, Any]:
    """
    Return a personalized, preference-weighted music selection for the current user.
    Considers region, language, era, genre, and previous engagement.
    """
    current_user = _optional_user(authorization)
    user_id = current_user["id"] if current_user else "guest"
    prefs = _get_user_preferences(user_id)
    tracks = _get_music_catalogue()

    if not tracks:
        return {"tracks": [], "personalized": False, "note": "Music catalogue is empty. Please add tracks."}

    # Score each track by preference match
    def preference_score(track: Dict) -> float:
        score = 0.0
        if prefs.get("region") and track.get("region", "").lower() == prefs["region"].lower():
            score += 3.0
        if prefs.get("language") and track.get("language", "").lower() == prefs["language"].lower():
            score += 3.0
        genres = [g.lower() for g in prefs.get("favorite_genres", [])]
        if genres and track.get("genre", "").lower() in genres:
            score += 2.0
        if prefs.get("youth_era") and track.get("era"):
            track_era_start = int(track["era"].split("-")[0]) if "-" in track["era"] else 0
            pref_era = prefs.get("youth_era", "")
            if pref_era and str(track_era_start) in pref_era:
                score += 2.0
        if track.get("music_id") in prefs.get("favorite_song_ids", []):
            score += 5.0
        # Add small random jitter to avoid always returning the same set
        score += random.uniform(0, 0.5)
        return score

    # Retrieve past sessions to boost previously engaging songs
    all_sessions = rhythm_sessions_store.read()
    if isinstance(all_sessions, list):
        user_sessions = [s for s in all_sessions if s.get("user_id") == user_id]
        # Recently played music_ids — reduce priority to avoid repetition
        recent_played: set = set()
        for s in user_sessions[-3:]:
            for mid in s.get("music_ids", []):
                recent_played.add(mid)
    else:
        recent_played = set()

    scored = []
    for t in tracks:
        s = preference_score(t)
        # Gently de-prioritize very recently played songs
        if t.get("music_id") in recent_played:
            s -= 1.0
        scored.append((s, t))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [t for _, t in scored[:count]]
    random.shuffle(selected)

    personalized = bool(prefs.get("region") or prefs.get("language") or prefs.get("favorite_genres"))
    return {
        "tracks": [MusicTrack(**t) for t in selected],
        "personalized": personalized,
        "preferences_applied": {
            "region": prefs.get("region"),
            "language": prefs.get("language"),
            "youth_era": prefs.get("youth_era"),
        },
    }


@router.post("/sessions", response_model=RhythmSessionResponse)
def create_session(
    payload: RhythmSessionCreate,
    authorization: Optional[str] = Header(default=None),
) -> RhythmSessionResponse:
    """Save a completed Rhythm & Recall session. Metrics are engagement data only."""
    current_user = _optional_user(authorization)
    user_id = current_user["id"] if current_user else "guest"

    # Idempotency — prevent duplicate saves on browser retry
    sessions = rhythm_sessions_store.read()
    if not isinstance(sessions, list):
        sessions = []
    if payload.client_action_id:
        prior = next(
            (s for s in sessions if s.get("client_action_id") == payload.client_action_id and s.get("user_id") == user_id),
            None,
        )
        if prior:
            return RhythmSessionResponse(**prior)

    recognition_pct = (
        round((payload.recognition_correct / payload.recognition_total) * 100, 1)
        if payload.recognition_total > 0 else None
    )

    session_id = str(uuid.uuid4())
    timestamp = auth_service.utcnow_iso()

    record = {
        "session_id": session_id,
        "client_action_id": payload.client_action_id,
        "user_id": user_id,
        "mode": payload.mode,
        "music_ids": payload.music_ids,
        "duration_seconds": payload.duration_seconds,
        "recognition_correct": payload.recognition_correct,
        "recognition_total": payload.recognition_total,
        "recognition_pct": recognition_pct,
        "tap_count": payload.tap_count,
        "rhythm_engagement_pct": payload.rhythm_engagement_pct,
        "voice_participated": payload.voice_participated,
        "voice_duration_seconds": payload.voice_duration_seconds,
        "memory_responses": payload.memory_responses,
        "mood_responses": payload.mood_responses,
        "rounds": payload.rounds or [],
        "engagement_label": _engagement_label(recognition_pct, payload.tap_count, payload.voice_participated),
        "encouragement": _encouragement(recognition_pct),
        "timestamp": timestamp,
    }

    sessions.append(record)
    # Keep last 1000 rhythm sessions system-wide
    rhythm_sessions_store.write(sessions[-1000:])

    return RhythmSessionResponse(
        session_id=session_id,
        user_id=user_id,
        mode=payload.mode,
        duration_seconds=payload.duration_seconds,
        recognition_correct=payload.recognition_correct,
        recognition_total=payload.recognition_total,
        tap_count=payload.tap_count,
        rhythm_engagement_pct=payload.rhythm_engagement_pct,
        voice_participated=payload.voice_participated,
        memory_responses=payload.memory_responses,
        mood_responses=payload.mood_responses,
        engagement_label=record["engagement_label"],
        encouragement=record["encouragement"],
        timestamp=timestamp,
    )


@router.get("/sessions")
def get_sessions(
    authorization: Optional[str] = Header(default=None),
    limit: int = 20,
) -> Dict[str, Any]:
    """Retrieve the current user's Rhythm & Recall session history."""
    current_user = _require_user(authorization)
    user_id = current_user["id"]

    sessions = rhythm_sessions_store.read()
    if not isinstance(sessions, list):
        sessions = []

    user_sessions = [s for s in sessions if s.get("user_id") == user_id]
    user_sessions = user_sessions[-limit:]
    user_sessions.reverse()  # newest first
    return {"sessions": user_sessions, "total": len(user_sessions)}


@router.post("/sessions/{session_id}/round")
def save_round(
    session_id: str,
    payload: RhythmRoundData,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """
    Save an individual game round's raw data.
    Computes rhythm engagement if beat timestamps are provided.
    Raw tap data is stored for trend analysis — never as a diagnostic metric.
    """
    current_user = _optional_user(authorization)
    user_id = current_user["id"] if current_user else "guest"

    # Compute rhythm engagement if tap data present
    rhythm_engagement = None
    timing_errors = None
    if payload.tap_timestamps:
        rhythm_engagement = _compute_rhythm_engagement(
            payload.tap_timestamps,
            payload.expected_beat_timestamps or [],
        )
        if payload.expected_beat_timestamps:
            timing_errors = []
            for tap in payload.tap_timestamps:
                nearest = min(payload.expected_beat_timestamps, key=lambda b: abs(b - tap))
                timing_errors.append(round(abs(tap - nearest), 3))

    round_record = {
        "session_id": session_id,
        "user_id": user_id,
        "round_number": payload.round_number,
        "song_id": payload.song_id,
        "mode": payload.mode,
        "selected_answer": payload.selected_answer,
        "correct_answer": payload.correct_answer,
        "is_correct": payload.is_correct,
        "response_time_ms": payload.response_time_ms,
        "tap_count": len(payload.tap_timestamps or []),
        "rhythm_engagement_pct": rhythm_engagement,
        "timing_errors": timing_errors,
        "memory_response": payload.memory_response,
        "mood_response": payload.mood_response,
        "timestamp": auth_service.utcnow_iso(),
    }

    # Append round data into the parent session record
    sessions = rhythm_sessions_store.read()
    if isinstance(sessions, list):
        for s in sessions:
            if s.get("session_id") == session_id and s.get("user_id") == user_id:
                if not isinstance(s.get("rounds"), list):
                    s["rounds"] = []
                s["rounds"].append(round_record)
                break
        rhythm_sessions_store.write(sessions)

    return {
        "round_saved": True,
        "rhythm_engagement_pct": rhythm_engagement,
        "engagement_label": "Rhythm Engagement" if rhythm_engagement is not None else "Rhythm Participation",
    }


@router.get("/analytics", response_model=RhythmAnalytics)
def get_analytics(
    authorization: Optional[str] = Header(default=None),
    patient_id: Optional[str] = None,
) -> RhythmAnalytics:
    """
    Longitudinal engagement analytics for Rhythm & Recall.
    Returns trend observations — NOT clinical diagnoses.
    """
    current_user = _require_user(authorization)
    role = current_user.get("role", "patient")

    # Caregivers/doctors can request analytics for a specific patient
    if patient_id and role in ("doctor", "caregiver"):
        target_user_id = patient_id
    else:
        target_user_id = current_user["id"]

    sessions = rhythm_sessions_store.read()
    if not isinstance(sessions, list):
        sessions = []

    user_sessions = [s for s in sessions if s.get("user_id") == target_user_id]
    total = len(user_sessions)

    # Sessions this week
    one_week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    sessions_this_week = sum(
        1 for s in user_sessions
        if s.get("timestamp", "") >= one_week_ago
    )

    avg_duration = (
        round(sum(s.get("duration_seconds", 0) for s in user_sessions) / total / 60, 1)
        if total > 0 else 0.0
    )

    recognition_values = [
        s.get("recognition_pct") for s in user_sessions
        if s.get("recognition_pct") is not None
    ]
    avg_recognition = (
        round(sum(recognition_values) / len(recognition_values), 1)
        if recognition_values else None
    )

    rhythm_values = [
        s.get("rhythm_engagement_pct") for s in user_sessions
        if s.get("rhythm_engagement_pct") is not None
    ]
    avg_rhythm = sum(rhythm_values) / len(rhythm_values) if rhythm_values else None
    if avg_rhythm is None:
        rhythm_label = "No rhythm sessions yet"
    elif avg_rhythm >= 70:
        rhythm_label = "Good"
    elif avg_rhythm >= 45:
        rhythm_label = "Moderate participation"
    else:
        rhythm_label = "Gentle participation"

    voice_sessions = sum(1 for s in user_sessions if s.get("voice_participated"))
    voice_pct = round((voice_sessions / total * 100), 1) if total > 0 else 0.0

    # Collect recent mood responses (last 10 sessions)
    recent_moods: List[str] = []
    for s in user_sessions[-10:]:
        recent_moods.extend(s.get("mood_responses", []))
    recent_moods = recent_moods[-8:]  # cap at 8 for display

    # Total unique songs played
    all_music_ids: set = set()
    for s in user_sessions:
        for mid in s.get("music_ids", []):
            all_music_ids.add(mid)

    return RhythmAnalytics(
        patient_id=target_user_id,
        total_sessions=total,
        avg_duration_minutes=avg_duration,
        avg_recognition_pct=avg_recognition,
        rhythm_participation_label=rhythm_label,
        voice_participation_pct=voice_pct,
        recent_mood_responses=recent_moods,
        trend_note=_trend_note(user_sessions),
        sessions_this_week=sessions_this_week,
        songs_played_total=len(all_music_ids),
    )


@router.post("/preferences")
def save_preferences(
    payload: MusicPreferences,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """Save caregiver-configured music preferences for the patient."""
    current_user = _require_user(authorization)
    user_id = current_user["id"]

    prefs = rhythm_preferences_store.read()
    if not isinstance(prefs, dict):
        prefs = {}

    prefs[user_id] = {
        "region": payload.region,
        "language": payload.language,
        "youth_era": payload.youth_era,
        "favorite_genres": payload.favorite_genres,
        "favorite_artists": payload.favorite_artists,
        "favorite_song_ids": payload.favorite_song_ids,
        "session_duration_minutes": payload.session_duration_minutes,
        "evening_session_enabled": payload.evening_session_enabled,
        "evening_session_time": payload.evening_session_time,
        "updated_at": auth_service.utcnow_iso(),
    }
    rhythm_preferences_store.write(prefs)
    return {"saved": True, "user_id": user_id}


@router.get("/preferences")
def get_preferences(
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """Retrieve music preferences for the current user."""
    current_user = _require_user(authorization)
    user_id = current_user["id"]
    prefs = _get_user_preferences(user_id)
    return {"preferences": prefs, "has_preferences": bool(prefs)}


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """
    Delete a specific session record (caregiver data privacy control).
    Users can only delete their own sessions.
    """
    current_user = _require_user(authorization)
    user_id = current_user["id"]

    sessions = rhythm_sessions_store.read()
    if not isinstance(sessions, list):
        sessions = []

    original_count = len(sessions)
    sessions = [
        s for s in sessions
        if not (s.get("session_id") == session_id and s.get("user_id") == user_id)
    ]
    deleted = original_count - len(sessions)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Session not found or not accessible.")
    rhythm_sessions_store.write(sessions)
    return {"deleted": True, "session_id": session_id}

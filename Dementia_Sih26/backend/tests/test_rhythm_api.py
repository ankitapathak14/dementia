import pytest
from fastapi.testclient import TestClient
from main import app
from services import auth_service

client = TestClient(app)

def test_list_rhythm_music():
    response = client.get("/api/rhythm/music")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "music_id" in data[0]
    assert "title" in data[0]

def test_personalized_music():
    response = client.get("/api/rhythm/music/personalized")
    assert response.status_code == 200
    data = response.json()
    assert "tracks" in data
    assert isinstance(data["tracks"], list)
    assert len(data["tracks"]) > 0

def test_create_and_get_rhythm_session():
    # Register/Get test user
    users = auth_service.get_users()
    test_user_id = "test_rhythm_user"
    if test_user_id not in users:
        users[test_user_id] = {
            "id": test_user_id,
            "email": "rhythm@test.com",
            "full_name": "Test Rhythm Patient",
            "role": "patient",
        }
        auth_service.users_store.write(users)

    raw_token = auth_service.create_session_for_user(test_user_id)
    headers = {"Authorization": f"Bearer {raw_token}"}

    # Create session
    session_payload = {
        "client_action_id": "test-action-123",
        "mode": "recognition",
        "music_ids": ["rr_001", "rr_002"],
        "duration_seconds": 90,
        "recognition_correct": 2,
        "recognition_total": 2,
        "tap_count": 15,
        "rhythm_engagement_pct": 85.0,
        "voice_participated": True,
        "voice_duration_seconds": 12.5,
        "memory_responses": ["Reminds me of my childhood in Assam"],
        "mood_responses": ["Calm", "Joyful"]
    }

    create_resp = client.post("/api/rhythm/sessions", json=session_payload, headers=headers)
    assert create_resp.status_code == 200
    s_data = create_resp.json()
    assert s_data["mode"] == "recognition"
    assert s_data["recognition_correct"] == 2
    assert s_data["engagement_label"] != ""
    assert s_data["encouragement"] != ""

    # Fetch sessions
    get_resp = client.get("/api/rhythm/sessions", headers=headers)
    assert get_resp.status_code == 200
    g_data = get_resp.json()
    assert g_data["total"] >= 1

    # Save round data
    session_id = s_data["session_id"]
    round_payload = {
        "session_id": session_id,
        "round_number": 1,
        "song_id": "rr_001",
        "mode": "rhythm_tap",
        "tap_timestamps": [1.0, 1.5, 2.0, 2.5],
        "expected_beat_timestamps": [1.0, 1.5, 2.0, 2.5]
    }
    round_resp = client.post(f"/api/rhythm/sessions/{session_id}/round", json=round_payload, headers=headers)
    assert round_resp.status_code == 200
    assert round_resp.json()["round_saved"] is True

    # Fetch analytics
    analytics_resp = client.get("/api/rhythm/analytics", headers=headers)
    assert analytics_resp.status_code == 200
    a_data = analytics_resp.json()
    assert a_data["total_sessions"] >= 1
    assert "trend_note" in a_data

    # Save preferences
    pref_payload = {
        "region": "Assam",
        "language": "Assamese",
        "youth_era": "1970s",
        "favorite_genres": ["Folk"],
        "session_duration_minutes": 10
    }
    pref_resp = client.post("/api/rhythm/preferences", json=pref_payload, headers=headers)
    assert pref_resp.status_code == 200
    assert pref_resp.json()["saved"] is True

    # Get preferences
    get_pref_resp = client.get("/api/rhythm/preferences", headers=headers)
    assert get_pref_resp.status_code == 200
    assert get_pref_resp.json()["preferences"]["region"] == "Assam"

    # Delete session
    del_resp = client.delete(f"/api/rhythm/sessions/{session_id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True

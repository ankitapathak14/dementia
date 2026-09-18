"""
test_caregiver_alerts.py — Comprehensive Unit & Integration Tests for Caregiver Alerts
=======================================================================================
Tests all 5 non-diagnostic alert categories, threshold evaluation,
review status workflow, API endpoints, and ethical safety wording.
SIH PS 26003.
"""
from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from main import app
from core.storage import (
    caregiver_alerts_store,
    game_sessions_store,
    reminders_store,
    users_store,
)
from services import caregiver_alert_service
from routers.demo_api import reset_and_seed_demo, DEMO_PATIENT_ID, DEMO_PATIENT_2_ID, DEMO_CAREGIVER_TOKEN


class TestCaregiverAlerts(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.test_patient_id = "test_alert_patient_99"
        self.now = datetime.now(timezone.utc)

    def test_missed_medication_alert(self):
        # Seed test reminders: 1 completed medicine, 1 pending past grace period
        all_rems = reminders_store.read()
        filtered = [r for r in all_rems if r.get("user_id") != self.test_patient_id]

        filtered.extend([
            {
                "id": "test_med_done",
                "user_id": self.test_patient_id,
                "category": "medicine",
                "title": "Amlodipine 5mg",
                "scheduled_time": "08:00",
                "status": "completed",
            },
            {
                "id": "test_med_missed",
                "user_id": self.test_patient_id,
                "category": "medicine",
                "title": "Donepezil 5mg",
                "scheduled_time": "08:00",
                "status": "pending",
                "dosage": "5mg tablet",
            },
        ])
        reminders_store.write(filtered)

        # Evaluate alerts at 09:00 UTC (60 mins after 08:00, grace period is 30m)
        eval_time = self.now.replace(hour=9, minute=0, second=0, microsecond=0)
        alerts = caregiver_alert_service.evaluate_caregiver_alerts(
            self.test_patient_id,
            current_time=eval_time,
        )

        med_alerts = [a for a in alerts if a["category"] == "missed_medication"]
        self.assertEqual(len(med_alerts), 1)
        alert = med_alerts[0]
        self.assertEqual(alert["title"], "Medication reminder not acknowledged")
        self.assertIn("Donepezil 5mg", alert["message"])
        self.assertIn("60 minutes", alert["message"])
        self.assertEqual(alert["severity"], "high")
        self.assertEqual(alert["status"], "new")

    def test_unusual_inactivity_alert(self):
        # Patient with activity 5 days ago and none since
        all_sess = game_sessions_store.read()
        filtered = [s for s in all_sess if s.get("user_id") != self.test_patient_id]
        past_ts = (self.now - timedelta(days=5)).isoformat()
        filtered.append({
            "session_id": "s_old",
            "user_id": self.test_patient_id,
            "game_id": "memory_match",
            "score": 75,
            "timestamp": past_ts,
        })
        game_sessions_store.write(filtered)

        alerts = caregiver_alert_service.evaluate_caregiver_alerts(
            self.test_patient_id,
            current_time=self.now,
        )

        inact_alerts = [a for a in alerts if a["category"] == "unusual_inactivity"]
        self.assertGreaterEqual(len(inact_alerts), 1)
        self.assertIn("No cognitive activity recorded", inact_alerts[0]["title"])
        self.assertIn("5 days", inact_alerts[0]["title"])

    def test_performance_change_alert(self):
        # 3 baseline sessions (avg 85%) and 3 recent sessions (avg 55%) -> 30% drop >= 15% threshold
        all_sess = game_sessions_store.read()
        filtered = [s for s in all_sess if s.get("user_id") != self.test_patient_id]

        for i, sc in enumerate([88, 85, 82]):
            filtered.append({
                "session_id": f"base_{i}",
                "user_id": self.test_patient_id,
                "game_id": "pattern_completion",
                "game_title": "Pattern Completion",
                "score": sc,
                "timestamp": (self.now - timedelta(days=7 - i)).isoformat(),
            })

        for i, sc in enumerate([60, 55, 52]):
            filtered.append({
                "session_id": f"recent_{i}",
                "user_id": self.test_patient_id,
                "game_id": "pattern_completion",
                "game_title": "Pattern Completion",
                "score": sc,
                "timestamp": (self.now - timedelta(days=2 - i)).isoformat(),
            })

        game_sessions_store.write(filtered)

        alerts = caregiver_alert_service.evaluate_caregiver_alerts(
            self.test_patient_id,
            current_time=self.now,
        )

        perf_alerts = [a for a in alerts if a["category"] == "performance_change"]
        self.assertEqual(len(perf_alerts), 1)
        alert = perf_alerts[0]
        self.assertEqual(alert["title"], "Recent performance decrease detected")
        self.assertIn("Pattern Completion", alert["message"])
        self.assertLess(alert["data"]["percentage_change"], -15)

    def test_repeated_difficulty_alert(self):
        # 3 consecutive attempts on same game under 55%
        all_sess = game_sessions_store.read()
        filtered = [s for s in all_sess if s.get("user_id") != self.test_patient_id]

        for i, sc in enumerate([48, 51, 46]):
            filtered.append({
                "session_id": f"diff_{i}",
                "user_id": self.test_patient_id,
                "game_id": "sequence_recall",
                "game_title": "Sequence Recall",
                "score": sc,
                "difficulty_level": 2,
                "timestamp": (self.now - timedelta(hours=3 - i)).isoformat(),
            })

        game_sessions_store.write(filtered)

        alerts = caregiver_alert_service.evaluate_caregiver_alerts(
            self.test_patient_id,
            current_time=self.now,
        )

        diff_alerts = [a for a in alerts if a["category"] == "repeated_difficulty"]
        self.assertEqual(len(diff_alerts), 1)
        alert = diff_alerts[0]
        self.assertIn("Repeated low performance detected in Sequence Recall", alert["title"])
        self.assertEqual(alert["data"]["recent_attempts"], [48, 51, 46])

    def test_missed_routine_alert(self):
        all_rems = reminders_store.read()
        filtered = [r for r in all_rems if r.get("user_id") != self.test_patient_id]

        filtered.extend([
            {
                "id": "r_breakfast",
                "user_id": self.test_patient_id,
                "category": "daily_activity",
                "title": "Morning Breakfast",
                "scheduled_time": "08:00",
                "status": "completed",
            },
            {
                "id": "r_hydration",
                "user_id": self.test_patient_id,
                "category": "hydration",
                "title": "Mid-Morning Water Intake",
                "scheduled_time": "10:30",
                "status": "pending",
            },
        ])
        reminders_store.write(filtered)

        alerts = caregiver_alert_service.evaluate_caregiver_alerts(
            self.test_patient_id,
            current_time=self.now,
        )

        routine_alerts = [a for a in alerts if a["category"] == "missed_routine"]
        self.assertGreaterEqual(len(routine_alerts), 1)
        self.assertEqual(routine_alerts[0]["title"], "Morning routine is incomplete")

    def test_review_status_lifecycle(self):
        # Seed missed medication
        all_rems = reminders_store.read()
        filtered = [r for r in all_rems if r.get("user_id") != self.test_patient_id]
        filtered.append({
            "id": "r_med_toggle",
            "user_id": self.test_patient_id,
            "category": "medicine",
            "title": "Donepezil 5mg",
            "scheduled_time": "08:00",
            "status": "pending",
        })
        reminders_store.write(filtered)

        eval_time = self.now.replace(hour=10, minute=0)
        alerts = caregiver_alert_service.evaluate_caregiver_alerts(
            self.test_patient_id,
            current_time=eval_time,
        )
        self.assertGreaterEqual(len(alerts), 1)
        target_alert = alerts[0]
        self.assertEqual(target_alert["status"], "new")

        # Mark as reviewed
        res = caregiver_alert_service.mark_alert_status(
            patient_id=self.test_patient_id,
            alert_id=target_alert["id"],
            status="reviewed",
            reviewer_id="caregiver_001",
        )
        self.assertEqual(res["status"], "reviewed")
        self.assertIsNotNone(res["reviewed_at"])

        # Re-evaluate and verify it now has reviewed status
        alerts_after = caregiver_alert_service.evaluate_caregiver_alerts(
            self.test_patient_id,
            current_time=eval_time,
        )
        updated = next(a for a in alerts_after if a["id"] == target_alert["id"])
        self.assertEqual(updated["status"], "reviewed")
        self.assertEqual(updated["reviewed_by"], "caregiver_001")

        # Unmark / reopen as new
        caregiver_alert_service.mark_alert_status(
            patient_id=self.test_patient_id,
            alert_id=target_alert["id"],
            status="new",
        )
        alerts_reopened = caregiver_alert_service.evaluate_caregiver_alerts(
            self.test_patient_id,
            current_time=eval_time,
        )
        reopened = next(a for a in alerts_reopened if a["id"] == target_alert["id"])
        self.assertEqual(reopened["status"], "new")

    def test_non_diagnostic_safety_wording(self):
        """Strictly enforce that no alert text makes a clinical diagnosis or uses forbidden terms."""
        forbidden_terms = [
            "dementia is worsening",
            "dementia is getting worse",
            "patient is deteriorating",
            "patient's brain function is declining",
            "patient is becoming more impaired",
            "diagnosed with",
        ]

        # Reset and seed demo
        reset_and_seed_demo()
        alerts = caregiver_alert_service.evaluate_caregiver_alerts(DEMO_PATIENT_ID)
        self.assertGreaterEqual(len(alerts), 1)

        for alert in alerts:
            full_text = f"{alert.get('title', '')} {alert.get('message', '')} {alert.get('recommended_action', '')}".lower()
            for term in forbidden_terms:
                self.assertNotIn(term, full_text, f"Alert contained forbidden diagnostic phrase: '{term}'")

            # Check statutory disclaimer
            self.assertIn("not a medical diagnosis", alert.get("disclaimer", "").lower())

    def test_demo_seeding_triggers_alert_scenarios(self):
        """Verify that SIH demo seeding natively triggers the alert scenarios."""
        reset_res = reset_and_seed_demo()
        self.assertEqual(reset_res["status"], "ok")

        # Patient 1 (Biren Das) should have Missed Medication, Performance Change, Repeated Difficulty, Missed Routine
        biren_alerts = caregiver_alert_service.evaluate_caregiver_alerts(DEMO_PATIENT_ID)
        categories = {a["category"] for a in biren_alerts}

        self.assertIn("missed_medication", categories)
        self.assertIn("performance_change", categories)
        self.assertIn("repeated_difficulty", categories)
        self.assertIn("missed_routine", categories)

        # Patient 2 (Pradip Borah) should have Unusual Inactivity
        pradip_alerts = caregiver_alert_service.evaluate_caregiver_alerts(DEMO_PATIENT_2_ID)
        pradip_categories = {a["category"] for a in pradip_alerts}
        self.assertIn("unusual_inactivity", pradip_categories)

    def test_dashboard_api_endpoints(self):
        """Test API integration: GET /dashboard/patient/{id} and /alerts and review endpoints."""
        reset_and_seed_demo()
        headers = {"Authorization": f"Bearer {DEMO_CAREGIVER_TOKEN}"}

        # 1. GET /dashboard/patient/{DEMO_PATIENT_ID} includes caregiver_alerts
        detail_res = self.client.get(f"/api/dashboard/patient/{DEMO_PATIENT_ID}", headers=headers)
        self.assertEqual(detail_res.status_code, 200)
        data = detail_res.json()
        self.assertIn("caregiver_alerts", data)
        self.assertGreaterEqual(len(data["caregiver_alerts"]), 1)

        # 2. GET /dashboard/patient/{DEMO_PATIENT_ID}/alerts
        alerts_res = self.client.get(f"/api/dashboard/patient/{DEMO_PATIENT_ID}/alerts", headers=headers)
        self.assertEqual(alerts_res.status_code, 200)
        alerts_data = alerts_res.json()
        self.assertIn("alerts", alerts_data)
        self.assertGreater(alerts_data["total_count"], 0)

        # 3. POST /dashboard/patient/{DEMO_PATIENT_ID}/alerts/{alert_id}/review
        first_alert = alerts_data["alerts"][0]
        review_res = self.client.post(
            f"/api/dashboard/patient/{DEMO_PATIENT_ID}/alerts/{first_alert['id']}/review",
            headers=headers,
            json={"status": "reviewed"},
        )
        self.assertEqual(review_res.status_code, 200)
        review_data = review_res.json()
        self.assertEqual(review_data["review_state"]["status"], "reviewed")


if __name__ == "__main__":
    unittest.main()

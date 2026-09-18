"""
test_patient_caregiver_workflow.py — End-to-End Tests for Patient -> Caregiver Authorization
==============================================================================================
Validates the decoupled Patient-Caregiver relationship architecture for SIH PS 26003:
- Strict separation between doctor-patient and patient-caregiver relationships.
- Server-side RBAC and consent validation.
- Non-diagnostic monitoring endpoints.
- Scenarios A through J.
"""
from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timezone
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from main import app
from core.security import hash_password
from core.storage import (
    users_store,
    consent_store,
    patient_caregivers_store,
    sessions_store,
)
from services import auth_service
from services.demo_seeder import (
    seed_longitudinal_demo_pipeline,
    DEMO_DOCTOR_ID,
    DEMO_CAREGIVER_ID,
    DEMO_PATIENTS,
)
from routers.demo_api import (
    reset_and_seed_demo,
    DEMO_PATIENT_ID,
    DEMO_CAREGIVER_TOKEN,
    DEMO_DOCTOR_TOKEN,
)


class TestPatientCaregiverWorkflow(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

        # Helper to create fresh ephemeral test users
        self.patient_1_id = "test_wf_patient_001"
        self.patient_2_id = "test_wf_patient_002"
        self.caregiver_1_id = "test_wf_caregiver_001"
        self.caregiver_2_id = "test_wf_caregiver_002"
        self.doctor_1_id = "test_wf_doctor_001"

        users = users_store.read()
        # Clean up any leftover test users
        for uid in [self.patient_1_id, self.patient_2_id, self.caregiver_1_id, self.caregiver_2_id, self.doctor_1_id]:
            users.pop(uid, None)

        users[self.patient_1_id] = {
            "id": self.patient_1_id,
            "full_name": "Test Patient One",
            "email": "patient1@testwf.local",
            "password_hash": hash_password("Pass#1234"),
            "role": "patient",
            "age": 70,
            "gender": "Female",
            "assigned_doctor_id": self.doctor_1_id,
            "enrolled_doctors": [self.doctor_1_id],
        }
        users[self.patient_2_id] = {
            "id": self.patient_2_id,
            "full_name": "Test Patient Two",
            "email": "patient2@testwf.local",
            "password_hash": hash_password("Pass#1234"),
            "role": "patient",
            "age": 72,
            "gender": "Male",
            "assigned_doctor_id": self.doctor_1_id,
            "enrolled_doctors": [self.doctor_1_id],
        }
        users[self.caregiver_1_id] = {
            "id": self.caregiver_1_id,
            "full_name": "Test Caregiver One",
            "email": "caregiver1@testwf.local",
            "password_hash": hash_password("Pass#1234"),
            "role": "caregiver",
            "specialization": "Caregiver",
            "patient_list": [],
        }
        users[self.caregiver_2_id] = {
            "id": self.caregiver_2_id,
            "full_name": "Test Caregiver Two",
            "email": "caregiver2@testwf.local",
            "password_hash": hash_password("Pass#1234"),
            "role": "caregiver",
            "specialization": "Caregiver",
            "patient_list": [],
        }
        users[self.doctor_1_id] = {
            "id": self.doctor_1_id,
            "full_name": "Test Doctor One",
            "email": "doctor1@testwf.local",
            "password_hash": hash_password("Pass#1234"),
            "role": "doctor",
            "specialization": "Neurology",
            "patient_list": [self.patient_1_id, self.patient_2_id],
        }
        users_store.write(users)

        # Grant consent by default for both patients
        consents = consent_store.read()
        for pid in [self.patient_1_id, self.patient_2_id]:
            consents[pid] = {
                "user_id": pid,
                "data_collection": True,
                "anonymous_research": True,
                "doctor_access": True,
                "consented_at": datetime.now(timezone.utc).isoformat(),
            }
        consent_store.write(consents)

        # Clean existing test relationships from patient_caregivers_store
        rels = patient_caregivers_store.read()
        filtered_rels = [
            r for r in rels
            if r.get("patient_id") not in {self.patient_1_id, self.patient_2_id}
            and r.get("caregiver_id") not in {self.caregiver_1_id, self.caregiver_2_id}
        ]
        patient_caregivers_store.write(filtered_rels)

        # Create session tokens
        self.patient_1_token = auth_service.create_session_for_user(self.patient_1_id)
        self.patient_2_token = auth_service.create_session_for_user(self.patient_2_id)
        self.caregiver_1_token = auth_service.create_session_for_user(self.caregiver_1_id)
        self.caregiver_2_token = auth_service.create_session_for_user(self.caregiver_2_id)
        self.doctor_1_token = auth_service.create_session_for_user(self.doctor_1_id)

    def test_scenario_a_caregiver_zero_assignments(self):
        """Scenario A: Caregiver with 0 assignments returns an empty list (0 patients)."""
        headers = {"Authorization": f"Bearer {self.caregiver_2_token}"}
        res = self.client.get("/api/dashboard/patients", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("patients", data)
        self.assertEqual(len(data["patients"]), 0)

    def test_scenario_b_patient_assigns_caregiver(self):
        """Scenario B: Patient assigns caregiver by email -> patient appears in caregiver's dashboard list."""
        patient_headers = {"Authorization": f"Bearer {self.patient_1_token}"}
        assign_res = self.client.post(
            "/api/caregivers/assign",
            headers=patient_headers,
            json={"caregiver_identity": "caregiver1@testwf.local"},
        )
        self.assertEqual(assign_res.status_code, 200)
        assign_data = assign_res.json()
        self.assertEqual(assign_data["relationship"]["status"], "connected")
        self.assertEqual(assign_data["relationship"]["caregiver_id"], self.caregiver_1_id)

        # Patient can also view their active caregivers
        my_caregivers_res = self.client.get("/api/caregivers/my-caregivers", headers=patient_headers)
        self.assertEqual(my_caregivers_res.status_code, 200)
        cg_list = my_caregivers_res.json()["caregivers"]
        self.assertEqual(len(cg_list), 1)
        self.assertEqual(cg_list[0]["caregiver_id"], self.caregiver_1_id)
        self.assertEqual(cg_list[0]["status"], "connected")

        # Caregiver dashboard now lists this patient
        caregiver_headers = {"Authorization": f"Bearer {self.caregiver_1_token}"}
        dash_res = self.client.get("/api/dashboard/patients", headers=caregiver_headers)
        self.assertEqual(dash_res.status_code, 200)
        patient_ids = [p["id"] for p in dash_res.json()["patients"]]
        self.assertIn(self.patient_1_id, patient_ids)

    def test_scenario_c_multiple_assigned_patients_isolation(self):
        """Scenario C: Caregiver only sees explicitly assigned patients."""
        # Patient 1 assigns Caregiver 1
        self.client.post(
            "/api/caregivers/assign",
            headers={"Authorization": f"Bearer {self.patient_1_token}"},
            json={"caregiver_identity": self.caregiver_1_id},
        )
        # Caregiver 1 should see Patient 1 but NOT Patient 2
        cg1_headers = {"Authorization": f"Bearer {self.caregiver_1_token}"}
        res = self.client.get("/api/dashboard/patients", headers=cg1_headers)
        self.assertEqual(res.status_code, 200)
        patient_ids = [p["id"] for p in res.json()["patients"]]
        self.assertIn(self.patient_1_id, patient_ids)
        self.assertNotIn(self.patient_2_id, patient_ids)

        # Now Patient 2 assigns Caregiver 1
        self.client.post(
            "/api/caregivers/assign",
            headers={"Authorization": f"Bearer {self.patient_2_token}"},
            json={"caregiver_identity": self.caregiver_1_id},
        )
        res2 = self.client.get("/api/dashboard/patients", headers=cg1_headers)
        patient_ids2 = [p["id"] for p in res2.json()["patients"]]
        self.assertIn(self.patient_1_id, patient_ids2)
        self.assertIn(self.patient_2_id, patient_ids2)

    def test_scenario_d_unauthorized_caregiver_dashboard_detail_blocked(self):
        """Scenario D: Unauthorized caregiver cannot call GET /dashboard/patient/{unassigned_id} (403)."""
        cg2_headers = {"Authorization": f"Bearer {self.caregiver_2_token}"}
        res = self.client.get(f"/api/dashboard/patient/{self.patient_1_id}", headers=cg2_headers)
        self.assertEqual(res.status_code, 403)
        self.assertIn("not assigned", res.json()["detail"].lower())

    def test_scenario_e_unauthorized_caregiver_results_blocked(self):
        """Scenario E: Unauthorized caregiver cannot call GET /results/patient/{unassigned_id} (403)."""
        cg2_headers = {"Authorization": f"Bearer {self.caregiver_2_token}"}
        res = self.client.get(f"/api/results/patient/{self.patient_1_id}", headers=cg2_headers)
        self.assertEqual(res.status_code, 403)
        self.assertIn("not assigned", res.json()["detail"].lower())

    def test_scenario_f_patient_revokes_caregiver(self):
        """Scenario F: Patient revokes caregiver -> patient removed from dashboard & detail calls return 403."""
        # 1. Assign Caregiver 1
        p1_headers = {"Authorization": f"Bearer {self.patient_1_token}"}
        self.client.post("/api/caregivers/assign", headers=p1_headers, json={"caregiver_identity": self.caregiver_1_id})

        # Verify Caregiver 1 has access
        cg1_headers = {"Authorization": f"Bearer {self.caregiver_1_token}"}
        detail_res1 = self.client.get(f"/api/dashboard/patient/{self.patient_1_id}", headers=cg1_headers)
        self.assertEqual(detail_res1.status_code, 200)

        # 2. Patient revokes Caregiver 1
        revoke_res = self.client.post(
            "/api/caregivers/revoke",
            headers=p1_headers,
            json={"caregiver_id": self.caregiver_1_id},
        )
        self.assertEqual(revoke_res.status_code, 200)

        # 3. Verify Caregiver 1 dashboard no longer lists Patient 1
        dash_res = self.client.get("/api/dashboard/patients", headers=cg1_headers)
        patient_ids = [p["id"] for p in dash_res.json()["patients"]]
        self.assertNotIn(self.patient_1_id, patient_ids)

        # 4. Detail endpoint now yields 403
        detail_res2 = self.client.get(f"/api/dashboard/patient/{self.patient_1_id}", headers=cg1_headers)
        self.assertEqual(detail_res2.status_code, 403)

    def test_scenario_g_doctor_caregiver_separation(self):
        """Scenario G: Doctor-patient relationship does not grant caregiver access."""
        # Doctor 1 is enrolled with Patient 1 and Patient 2.
        # But Caregiver 1 has NO relationship with Patient 1.
        # Ensure Caregiver 1 is denied access despite sharing the same assigned doctor.
        cg1_headers = {"Authorization": f"Bearer {self.caregiver_1_token}"}
        res = self.client.get(f"/api/dashboard/patient/{self.patient_1_id}", headers=cg1_headers)
        self.assertEqual(res.status_code, 403)

        # Also verify that a caregiver token cannot invoke doctor-only endpoints
        doc_res = self.client.get("/api/auth/doctors/my-doctor", headers=cg1_headers)
        # Even if calling doctor-only routes, role check enforces separation
        doc_enroll_res = self.client.post("/api/auth/doctors/approve", headers=cg1_headers, json={"patient_id": self.patient_1_id})
        self.assertEqual(doc_enroll_res.status_code, 403)

    def test_scenario_h_patient_consent_withheld_blocks_access(self):
        """Scenario H: Patient consent withheld -> caregiver access blocked with 403."""
        # 1. Assign Caregiver 1
        p1_headers = {"Authorization": f"Bearer {self.patient_1_token}"}
        self.client.post("/api/caregivers/assign", headers=p1_headers, json={"caregiver_identity": self.caregiver_1_id})

        # 2. Revoke consent for Patient 1
        consents = consent_store.read()
        consents[self.patient_1_id]["share_with_care_team"] = False
        consents[self.patient_1_id]["doctor_access"] = False
        consent_store.write(consents)

        # 3. Caregiver access is blocked
        cg1_headers = {"Authorization": f"Bearer {self.caregiver_1_token}"}
        res = self.client.get(f"/api/dashboard/patient/{self.patient_1_id}", headers=cg1_headers)
        self.assertEqual(res.status_code, 403)
        self.assertIn("consent", res.json()["detail"].lower())

    def test_scenario_i_demo_seeding_caregiver_assignments(self):
        """Scenario I: Demo seeding verification -> Sreejeta has A, B, D, and Biren Das; C and E are absent."""
        seed_res = seed_longitudinal_demo_pipeline()
        self.assertEqual(seed_res["status"], "ok")

        cg_headers = {"Authorization": f"Bearer {DEMO_CAREGIVER_TOKEN}"}
        dash_res = self.client.get("/api/dashboard/patients", headers=cg_headers)
        self.assertEqual(dash_res.status_code, 200)
        patient_ids = [p["id"] for p in dash_res.json()["patients"]]

        # Sreejeta should have access to A, B, D and Biren Das
        self.assertIn("sih-demo-patient-a", patient_ids)
        self.assertIn("sih-demo-patient-b", patient_ids)
        self.assertIn("sih-demo-patient-d", patient_ids)
        self.assertIn(DEMO_PATIENT_ID, patient_ids)

        # Sreejeta should NOT have access to C or E
        self.assertNotIn("sih-demo-patient-c", patient_ids)
        self.assertNotIn("sih-demo-patient-e", patient_ids)

        # Attempting direct detail access to C or E returns 403
        res_c = self.client.get("/api/dashboard/patient/sih-demo-patient-c", headers=cg_headers)
        self.assertEqual(res_c.status_code, 403)

        res_e = self.client.get("/api/dashboard/patient/sih-demo-patient-e", headers=cg_headers)
        self.assertEqual(res_e.status_code, 403)

    def test_scenario_j_doctor_functionality_unaffected(self):
        """Scenario J: Doctor functionality unaffected -> Doctor can access all enrolled patients regardless of caregiver."""
        seed_longitudinal_demo_pipeline()
        doc_headers = {"Authorization": f"Bearer {DEMO_DOCTOR_TOKEN}"}

        # Doctor can access Persona A, B, C, D, E and Biren Das
        for persona_key in ["a", "b", "c", "d", "e"]:
            pid = f"sih-demo-patient-key" if False else f"sih-demo-patient-{persona_key}"
            res = self.client.get(f"/api/dashboard/patient/{pid}", headers=doc_headers)
            self.assertEqual(res.status_code, 200, f"Doctor should access persona {persona_key}")


if __name__ == "__main__":
    unittest.main()

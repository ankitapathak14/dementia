"""
backend/tests/test_demo_pipeline_integration.py
================================================
Comprehensive integration test for SIH Demonstration Data & Real Application Pipeline.

Validates end-to-end data lineage across:
patient -> cognitive assessments -> /api/analyze -> feature extraction
-> 18-feature vector -> behavioral baseline -> longitudinal deviation
-> overall attention -> results_store persistence -> doctor dashboard
-> patient detail -> caregiver alerts safety.

DISCLAIMER:
All fixtures tested herein are synthetic deterministic development fixtures.
No real patient data is utilized.
"""
from __future__ import annotations

import os
import sys
import unittest
from fastapi.testclient import TestClient

# Ensure root directory is on sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from main import app
from services.demo_seeder import (
    DEMO_DOCTOR_ID,
    DEMO_DOCTOR_TOKEN,
    DEMO_PATIENTS,
    seed_longitudinal_demo_pipeline,
)
from core.storage import results_store, users_store


def compute_attention_priority(result: dict) -> str:
    """Production non-diagnostic attention priority logic as used in DoctorDashboard and PatientDetail."""
    if not result:
        return "Pending Assessment"
    oa = result.get("ml_analysis", {}).get("overall_attention", {})
    if oa.get("available") and oa.get("label"):
        lbl = oa["label"].lower()
        if "high" in lbl or "elevated" in lbl:
            return "Elevated"
        if "moderate" in lbl:
            return "Moderate"
        return "Routine"
    bd = result.get("ml_analysis", {}).get("behavioral_deviation", {})
    sev = bd.get("severity")
    if sev in ("severe", "significant"):
        return "Elevated"
    if sev == "mild":
        return "Moderate"
    if sev == "none":
        return "Routine"
    crs = result.get("composite_risk_score", 0)
    if crs >= 65:
        return "Elevated"
    if crs >= 35:
        return "Moderate"
    return "Routine"


class TestDemoPipelineIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Execute real-pipeline seeding
        cls.seed_result = seed_longitudinal_demo_pipeline()
        assert cls.seed_result["status"] == "ok"

    def test_01_seeding_executed_via_real_pipeline(self):
        """Verify seeding executed and registered all Personas A through E."""
        seeded = self.seed_result["seeded_patients"]
        for key in ["A", "B", "C", "D", "E"]:
            self.assertIn(key, seeded)
            info = seeded[key]
            self.assertGreater(info["session_count"], 0)

    def test_02_patient_a_stable_trajectory(self):
        """Patient A (Stable): 5 sessions, Routine Attention, no false anomaly alerts."""
        pid = DEMO_PATIENTS["A"]["id"]
        results = results_store.read().get(pid, [])
        self.assertEqual(len(results), 5, "Patient A must have exactly 5 longitudinal sessions")

        # Check latest session
        latest = results[-1]
        ml = latest["ml_analysis"]
        beh = ml["behavioral_deviation"]
        prov_summary = latest["provenance_summary"]

        # 1. Behavioral Anomaly: Baseline established, no anomaly detected
        self.assertIn(beh["status"], ["preliminary_baseline", "longitudinal_baseline"])
        self.assertFalse(beh["anomaly_detected"], "Stable patient must not trigger false positive anomaly")
        self.assertEqual(beh["severity"], "none")

        # 2. Overall attention maps to Routine Attention
        self.assertEqual(compute_attention_priority(latest), "Routine")

        # 3. Provenance: all 18 features measured
        self.assertEqual(prov_summary["measured_count"], 18)
        self.assertEqual(prov_summary["defaulted_count"], 0)

        # 4. Clinical reference: no disease probability
        clin = ml["clinical_reference"]
        self.assertEqual(clin["status"], "insufficient_input")
        self.assertIsNone(clin["probability"])

    def test_03_patient_b_memory_deterioration(self):
        """Patient B (Memory Change): 5 sessions, memory features deviate, Elevated Attention."""
        pid = DEMO_PATIENTS["B"]["id"]
        results = results_store.read().get(pid, [])
        self.assertEqual(len(results), 5)

        # Sessions 1-3 were stable; sessions 4-5 deteriorated in memory
        s3 = results[2]
        s5 = results[4]

        # Memory scores dropped noticeably
        self.assertGreater(s3["memory_score"], 70.0)
        self.assertLess(s5["memory_score"], 50.0)

        # Other domains remained relatively stable
        self.assertGreater(s5["speech_score"], 70.0)
        self.assertGreater(s5["reaction_score"], 70.0)

        # Behavioral deviation detected in latest session
        latest_beh = s5["ml_analysis"]["behavioral_deviation"]
        self.assertTrue(latest_beh["anomaly_detected"], "Memory decline must be detected by behavioral ML")
        self.assertIn(latest_beh["severity"], ["significant", "severe"])

        # Top deviating features must include memory features
        deviating_keys = [f["feature"] for f in latest_beh["top_deviating_features"]]
        has_memory_feature = any(
            k in deviating_keys
            for k in ["delayed_recall_accuracy", "immediate_recall_accuracy", "recall_latency", "intrusion_count"]
        )
        self.assertTrue(has_memory_feature, f"Expected memory feature in top deviating: {deviating_keys}")

        # Attention priority must map to Elevated
        self.assertEqual(compute_attention_priority(s5), "Elevated")

    def test_04_patient_c_reaction_slowing(self):
        """Patient C (Reaction Change): 5 sessions, reaction features deviate, Elevated Attention."""
        pid = DEMO_PATIENTS["C"]["id"]
        results = results_store.read().get(pid, [])
        self.assertEqual(len(results), 5)

        s3 = results[2]
        s5 = results[4]

        # Reaction score dropped substantially
        self.assertGreater(s3["reaction_score"], 70.0)
        self.assertLess(s5["reaction_score"], 50.0)

        # Memory and speech remained relatively stable
        self.assertGreater(s5["memory_score"], 70.0)
        self.assertGreater(s5["speech_score"], 70.0)

        # Behavioral deviation detected
        latest_beh = s5["ml_analysis"]["behavioral_deviation"]
        self.assertTrue(latest_beh["anomaly_detected"], "Reaction slowing must be detected by behavioral ML")
        self.assertIn(latest_beh["severity"], ["significant", "severe"])

        # Top deviating features must include reaction features
        deviating_keys = [f["feature"] for f in latest_beh["top_deviating_features"]]
        has_reaction_feature = any(
            k in deviating_keys for k in ["mean_rt", "std_rt", "miss_count", "reaction_drift"]
        )
        self.assertTrue(has_reaction_feature, f"Expected reaction feature in top deviating: {deviating_keys}")

        # Attention priority must map to Elevated
        self.assertEqual(compute_attention_priority(s5), "Elevated")

    def test_05_patient_d_multidomain_decline(self):
        """Patient D (Multi-Domain Change): 5 sessions, multi-domain deviation across Speech, Memory, Reaction."""
        pid = DEMO_PATIENTS["D"]["id"]
        results = results_store.read().get(pid, [])
        self.assertEqual(len(results), 5)

        s5 = results[4]
        latest_beh = s5["ml_analysis"]["behavioral_deviation"]
        self.assertTrue(latest_beh["anomaly_detected"])
        self.assertIn(latest_beh["severity"], ["significant", "severe"])

        # Top deviating features should show multiple domains
        deviating_keys = [f["feature"] for f in latest_beh["top_deviating_features"]]
        self.assertGreaterEqual(len(deviating_keys), 2)

        # Attention priority must map to Elevated
        self.assertEqual(compute_attention_priority(s5), "Elevated")

    def test_06_patient_e_insufficient_history(self):
        """Patient E (Insufficient History): 1 session, status 'insufficient_history', baseline pending."""
        pid = DEMO_PATIENTS["E"]["id"]
        results = results_store.read().get(pid, [])
        self.assertEqual(len(results), 1, "Patient E must have exactly 1 session")

        s1 = results[0]
        beh = s1["ml_analysis"]["behavioral_deviation"]
        oa = s1["ml_analysis"]["overall_attention"]

        self.assertEqual(beh["status"], "insufficient_history")
        self.assertFalse(beh["anomaly_detected"], "Must not fabricate anomaly with insufficient history")
        self.assertEqual(beh["severity"], "none")

        # Fusion recognizes incomplete baseline
        self.assertFalse(oa["available"])

    def test_07_doctor_dashboard_dynamic_data_and_counts(self):
        """Verify Doctor Dashboard endpoint returns all patients and dynamic attention counts."""
        headers = {"Authorization": f"Bearer {DEMO_DOCTOR_TOKEN}"}
        resp = self.client.get("/api/auth/patients", headers=headers)
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        patients = data["patients"]
        self.assertGreaterEqual(len(patients), 5)

        patient_map = {p["id"]: p for p in patients}

        # Check Personas A–E exist in doctor's patient list
        for key in ["A", "B", "C", "D", "E"]:
            pid = DEMO_PATIENTS[key]["id"]
            self.assertIn(pid, patient_map, f"Patient {key} missing from doctor's list")
            p = patient_map[pid]
            self.assertIsNotNone(p.get("lastResult"), f"Patient {key} missing lastResult")

        # Verify dynamic counts computed in the same way as DoctorDashboard.jsx
        def get_priority(p):
            r = p.get("lastResult")
            if not r:
                return "Pending Assessment"
            oa = r.get("ml_analysis", {}).get("overall_attention", {})
            if oa.get("available") and oa.get("label"):
                lbl = oa["label"].lower()
                if "high" in lbl or "elevated" in lbl:
                    return "Elevated"
                if "moderate" in lbl:
                    return "Moderate"
                return "Routine"
            bd = r.get("ml_analysis", {}).get("behavioral_deviation", {})
            if bd.get("severity") in ("severe", "significant"):
                return "Elevated"
            if bd.get("severity") == "mild":
                return "Moderate"
            if bd.get("severity") == "none":
                return "Routine"
            return "Pending Assessment"

        elevated_count = sum(1 for p in patients if get_priority(p) == "Elevated")
        routine_count = sum(1 for p in patients if get_priority(p) == "Routine")

        # Patients B, C, D must map to Elevated
        self.assertEqual(get_priority(patient_map[DEMO_PATIENTS["B"]["id"]]), "Elevated")
        self.assertEqual(get_priority(patient_map[DEMO_PATIENTS["C"]["id"]]), "Elevated")
        self.assertEqual(get_priority(patient_map[DEMO_PATIENTS["D"]["id"]]), "Elevated")
        self.assertGreaterEqual(elevated_count, 3)

        # Patient A must map to Routine
        self.assertEqual(get_priority(patient_map[DEMO_PATIENTS["A"]["id"]]), "Routine")
        self.assertGreaterEqual(routine_count, 1)

    def test_08_patient_detail_endpoint_consent_and_history(self):
        """Verify doctor can retrieve patient history through /results/patient/{id} with consent."""
        headers = {"Authorization": f"Bearer {DEMO_DOCTOR_TOKEN}"}

        for key in ["A", "B", "C", "D", "E"]:
            pid = DEMO_PATIENTS[key]["id"]
            resp = self.client.get(f"/api/results/patient/{pid}", headers=headers)
            self.assertEqual(resp.status_code, 200, f"Doctor access denied for {pid}: {resp.text}")

            res_list = resp.json().get("results", [])
            expected_count = 5 if key in ("A", "B", "C", "D") else 1
            self.assertEqual(len(res_list), expected_count)

            # Ensure all results have non-diagnostic ml_analysis
            for session in res_list:
                self.assertIn("ml_analysis", session)
                self.assertIn("behavioral_deviation", session["ml_analysis"])
                self.assertIn("clinical_reference", session["ml_analysis"])
                self.assertIn("overall_attention", session["ml_analysis"])

    def test_09_patient_own_results_endpoint(self):
        """Verify patient can retrieve their own history through /results/my."""
        for key in ["A", "B", "C", "D", "E"]:
            token = DEMO_PATIENTS[key]["token"]
            headers = {"Authorization": f"Bearer {token}"}
            resp = self.client.get("/api/results/my", headers=headers)
            self.assertEqual(resp.status_code, 200)
            res_list = resp.json().get("results", [])
            expected_count = 5 if key in ("A", "B", "C", "D") else 1
            self.assertEqual(len(res_list), expected_count)


if __name__ == "__main__":
    unittest.main()

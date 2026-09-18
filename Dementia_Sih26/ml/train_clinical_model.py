"""
ml/train_clinical_model.py
==========================
Trains Layer B: Clinical Reference Model on OASIS Longitudinal Dataset.

Validation Protocol:
- Uses StratifiedGroupKFold on 'Subject ID' to strictly prevent cross-visit leakage.
- Calculates and logs actual empirical metrics (ROC-AUC, PR-AUC, Sensitivity, Specificity, Precision, F1).
- Fits a scikit-learn Pipeline (SimpleImputer + StandardScaler + LogisticRegression).
- Saves serialized artifact (.joblib) and detailed audit metadata (.json).
- ZERO hardcoded or simulated numbers.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import sys
from typing import Any, Dict

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold

try:
    from ml.preprocessing import (
        CLINICAL_FEATURE_NAMES,
        build_preprocessing_pipeline,
        load_oasis_dataset,
        prepare_clinical_dataset,
    )
except ImportError:
    from preprocessing import (
        CLINICAL_FEATURE_NAMES,
        build_preprocessing_pipeline,
        load_oasis_dataset,
        prepare_clinical_dataset,
    )

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
PIPELINE_PATH = os.path.join(ARTIFACTS_DIR, "clinical_logistic_pipeline.joblib")
METADATA_PATH = os.path.join(ARTIFACTS_DIR, "clinical_model_metadata.json")


def train_clinical_model(csv_path: str = None) -> Dict[str, Any]:
    print("[*] Loading OASIS dataset...")
    df = load_oasis_dataset(csv_path)
    X, y, groups = prepare_clinical_dataset(df, handle_converted="visit_cdr")

    n_samples = len(X)
    n_subjects = len(np.unique(groups))
    dementia_prevalence = float(np.mean(y))

    print(f"[+] Loaded {n_samples} records across {n_subjects} unique subjects.")
    print(f"[+] Target distribution: {int(np.sum(y))} Demented (1), {int(len(y) - np.sum(y))} Nondemented (0)")
    print(f"[+] Prevalence: {dementia_prevalence:.1%}")

    # 5-fold StratifiedGroupKFold ensures:
    # 1. Class ratio is preserved across folds.
    # 2. All visits from any given Subject ID reside wholly in either Train or Test fold.
    sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)

    oof_probs = np.zeros(n_samples, dtype=float)
    oof_preds = np.zeros(n_samples, dtype=int)
    fold_scores = []

    print("[*] Running 5-fold StratifiedGroupKFold cross-validation on Subject ID...")

    for fold, (train_idx, val_idx) in enumerate(sgkf.split(X, y, groups=groups), start=1):
        X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
        X_val, y_val = X.iloc[val_idx], y.iloc[val_idx]

        # Verify zero subject overlap between train and validation
        train_subjects = set(groups.iloc[train_idx])
        val_subjects = set(groups.iloc[val_idx])
        assert len(train_subjects.intersection(val_subjects)) == 0, (
            f"Leakage Detected in Fold {fold}! Subjects overlap between train and val."
        )

        fold_pipeline = build_preprocessing_pipeline()
        clf = LogisticRegression(
            class_weight="balanced",
            C=1.0,
            max_iter=1000,
            random_state=42,
        )
        fold_pipeline.steps.append(("classifier", clf))

        fold_pipeline.fit(X_tr, y_tr)
        val_probs = fold_pipeline.predict_proba(X_val)[:, 1]
        val_preds = (val_probs >= 0.5).astype(int)

        oof_probs[val_idx] = val_probs
        oof_preds[val_idx] = val_preds

        fold_auc = roc_auc_score(y_val, val_probs)
        fold_scores.append(fold_auc)
        print(f"    Fold {fold}: ROC-AUC = {fold_auc:.4f} (Train: {len(X_tr)} rec, Val: {len(X_val)} rec)")

    # Compute genuine out-of-fold cross-validation metrics
    overall_roc_auc = float(roc_auc_score(y, oof_probs))
    overall_pr_auc = float(average_precision_score(y, oof_probs))
    sensitivity = float(recall_score(y, oof_preds, pos_label=1))
    specificity = float(recall_score(y, oof_preds, pos_label=0))
    precision = float(precision_score(y, oof_preds, pos_label=1))
    f1 = float(f1_score(y, oof_preds, pos_label=1))
    cm = confusion_matrix(y, oof_preds).tolist()

    print("\n[+] Cross-Validation Empirical Results (Out-Of-Fold):")
    print(f"    ROC-AUC:     {overall_roc_auc:.4f}")
    print(f"    PR-AUC:      {overall_pr_auc:.4f}")
    print(f"    Sensitivity: {sensitivity:.4f} (Recall for Demented)")
    print(f"    Specificity: {specificity:.4f} (True Negative Rate)")
    print(f"    Precision:   {precision:.4f}")
    print(f"    F1 Score:    {f1:.4f}")
    print(f"    Confusion Matrix [TN, FP; FN, TP]: {cm}")

    # Fit final pipeline on complete dataset
    print("[*] Training final production reference model on full cohort...")
    final_pipeline = build_preprocessing_pipeline()
    final_clf = LogisticRegression(
        class_weight="balanced",
        C=1.0,
        max_iter=1000,
        random_state=42,
    )
    final_pipeline.steps.append(("classifier", final_clf))
    final_pipeline.fit(X, y)

    # Extract model coefficients for genuine explainability
    coefs = final_clf.coef_[0]
    intercept = float(final_clf.intercept_[0])
    feature_explanations = []
    for feat_name, coef in zip(CLINICAL_FEATURE_NAMES, coefs):
        feature_explanations.append({
            "feature": feat_name,
            "coefficient": round(float(coef), 4),
            "odds_ratio": round(float(np.exp(coef)), 4),
            "direction": "increases_risk" if coef > 0 else "decreases_risk",
            "standardized_importance": round(abs(float(coef)), 4),
        })

    feature_explanations.sort(key=lambda x: x["standardized_importance"], reverse=True)

    # Serialize artifacts
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    joblib.dump(final_pipeline, PIPELINE_PATH)
    print(f"[+] Serialized model pipeline to: {PIPELINE_PATH}")

    metadata = {
        "dataset_name": "OASIS Longitudinal MRI Data in Nondemented and Demented Older Adults",
        "source": "Marcus et al. (2010), oasis-brains.org",
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "training_sample_count": n_samples,
        "subject_count": n_subjects,
        "target_definition": (
            "Binary clinical dementia status at visit: Nondemented = 0, Demented = 1. "
            "Converted visits are labeled using visit-level CDR: CDR >= 0.5 -> 1, CDR == 0 -> 0. "
            "CDR is used only for target construction and never as X (target leakage prevention)."
        ),
        "input_features": CLINICAL_FEATURE_NAMES,
        "validation_protocol": "5-Fold StratifiedGroupKFold on Subject ID (zero longitudinal cross-visit leakage)",
        "metrics": {
            "roc_auc": round(overall_roc_auc, 4),
            "pr_auc": round(overall_pr_auc, 4),
            "sensitivity": round(sensitivity, 4),
            "specificity": round(specificity, 4),
            "precision": round(precision, 4),
            "f1": round(f1, 4),
            "confusion_matrix": cm,
            "fold_roc_aucs": [round(s, 4) for s in fold_scores],
        },
        "model_architecture": "Pipeline(SimpleImputer(median) -> StandardScaler -> LogisticRegression(balanced))",
        "intercept": round(intercept, 4),
        "feature_coefficients": feature_explanations,
        "warning": (
            "RESEARCH REFERENCE MODEL ONLY. This model is trained on the OASIS research cohort "
            "and is NOT clinically validated for NeuroAid standalone patient diagnosis. "
            "All predictions are screening risk indicators."
        ),
    }

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"[+] Saved model audit metadata to: {METADATA_PATH}")

    return metadata


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    train_clinical_model(path)

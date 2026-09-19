# Layer B: Clinical Reference Model

This directory contains the machine learning training pipeline, preprocessing modules, and model artifacts for NeuroAid's **Layer B: Clinical Reference Model**.

---

## 1. Objective & Role in NeuroAid Architecture
NeuroAid separates cognitive signals into two distinct layers:
- **Layer A (Behavioral AI):** Evaluates real-time patient cognitive performance deviations across 18 behavioral features derived from interactive games and speech assessments.
- **Layer B (Clinical Reference Model):** Provides an interpretable, baseline risk context by benchmarking patient clinical and demographic factors against a peer-reviewed clinical research cohort (OASIS Longitudinal).

The two modalities are **never mixed during training**.

---

## 2. Dataset & Provenance
- **Dataset:** Open Access Series of Imaging Studies (OASIS): Longitudinal MRI Data in Nondemented and Demented Older Adults.
- **Citation:** Marcus et al., 2010. *Journal of Cognitive Neuroscience*, 22(12), 2677-2684.
- **Acquisition:** Download via `python ml/download_dataset.py` or place `oasis_longitudinal.csv` in `ml/data/`.
- **Licensing:** Open access research data (CC BY 4.0 / Data Use Agreement).

---

## 3. Leakage Prevention Protocol
- **Target Definition:** Binary classification of dementia status (`demented = 1`, `nondemented = 0`).
- **Target Leakage Safeguard:** `CDR` (Clinical Dementia Rating) is **strictly excluded** from model input features because clinical dementia categories are directly derived from CDR.
- **Subject-Level Split Safeguard:** Because subjects in the OASIS longitudinal study participated in multiple scanning sessions over time (Visits 1, 2, 3+), standard random k-fold would leak visits from the same subject across train and validation sets. We employ **`StratifiedGroupKFold(n_splits=5)`** grouped strictly by `Subject ID`. Zero subjects overlap between train and test folds.

---

## 4. Model Architecture & Pipeline
```
Raw Clinical Inputs (Age, EDUC, SES, MMSE, eTIV, nWBV, ASF, sex)
                      │
                      ▼
      SimpleImputer(strategy='median')
                      │
                      ▼
               StandardScaler()
                      │
                      ▼
   LogisticRegression(class_weight='balanced')
```

---

## 5. How to Train
Run the training script from the repository root:
```bash
python ml/train_clinical_model.py
```
This will:
1. Verify and load `ml/data/oasis_longitudinal.csv`.
2. Execute 5-fold `StratifiedGroupKFold` cross-validation on `Subject ID`.
3. Compute out-of-fold empirical metrics: ROC-AUC, PR-AUC, Sensitivity, Specificity, Precision, F1, and Confusion Matrix.
4. Fit the final pipeline on all records.
5. Save the serialized model to `ml/artifacts/clinical_logistic_pipeline.joblib`.
6. Save the comprehensive model audit log to `ml/artifacts/clinical_model_metadata.json`.

---

## 6. Inference & Explainability
Inference is provided by `ml/clinical_model.py`:
- Checks if model artifacts are available; returns explicit unavailable status otherwise.
- Computes risk probabilities and maps to risk bands (`Low`, `Moderate`, `High`).
- Generates transparent, verifiable explanations using the logistic model's true regression coefficients ($w_i \cdot x_i$), reporting direction and odds ratio.

---

## 7. Research Limitation & Medical Disclaimer
This model is a research benchmark trained on the OASIS longitudinal cohort. It has not undergone prospective clinical trials for standalone medical diagnosis. All outputs are intended solely as early risk screening indicators.

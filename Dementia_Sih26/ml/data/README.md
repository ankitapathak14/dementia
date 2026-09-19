# OASIS Longitudinal Clinical Dataset

This directory holds the clinical reference dataset used for training NeuroAid's Layer B clinical reference model.

## Dataset Information
- **Name:** Open Access Series of Imaging Studies (OASIS): Longitudinal MRI Data in Nondemented and Demented Older Adults
- **Original Source:** [OASIS Brains Project](https://www.oasis-brains.org/)
- **Primary Citation:** 
  > Marcus, D. S., Fotenos, A. F., Csernansky, J. G., Morris, J. C., & Buckner, R. L. (2010). Open Access Series of Imaging Studies: longitudinal MRI data in nondemented and demented older adults. *Journal of Cognitive Neuroscience*, 22(12), 2677-2684.

## Data Use Agreement & Licensing
OASIS data is distributed for open scientific research. Redistribution is subject to attribution requirements and OASIS Data Use agreements. The full dataset is not committed to source control by default to respect data distribution terms and ensure reproducible local setup.

## Expected File
- **Filename:** `oasis_longitudinal.csv`
- **Location:** `ml/data/oasis_longitudinal.csv`

## Expected Columns
The longitudinal dataset contains:
1. `Subject ID`: Unique participant identifier (e.g., OAS2_0001)
2. `MRI ID`: Unique scan session identifier
3. `Group`: Clinical categorization (`Nondemented`, `Demented`, `Converted`)
4. `Visit`: Longitudinal visit number (1, 2, 3, etc.)
5. `MR Delay`: Days elapsed since initial visit
6. `M/F`: Biological sex (`M`, `F`)
7. `Hand`: Handedness (all R)
8. `Age`: Participant age in years
9. `EDUC`: Years of education
10. `SES`: Socioeconomic status (Hollingshead Index, 1–5)
11. `MMSE`: Mini-Mental State Examination score (0–30)
12. `CDR`: Clinical Dementia Rating (0 = normal, 0.5 = very mild, 1 = mild, 2 = moderate)
13. `eTIV`: Estimated Total Intracranial Volume ($mm^3$)
14. `nWBV`: Normalized Whole Brain Volume (proportion)
15. `ASF`: Atlas Scaling Factor

## Clinical Leakage Prevention Guard
`CDR` (Clinical Dementia Rating) is **strictly excluded** from model input features because clinical dementia categories are directly derived from CDR. Using CDR to predict dementia status creates severe target leakage.

Only the non-leaking features (`Age`, `EDUC`, `SES`, `MMSE`, `eTIV`, `nWBV`, `ASF`, and biological sex) are used as inputs.

## Setup Instructions
Run the automated fetch script from the project root:
```bash
python ml/download_dataset.py
```
Or place the verified `oasis_longitudinal.csv` directly into this directory (`ml/data/`).

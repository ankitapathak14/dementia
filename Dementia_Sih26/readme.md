# NeuroAid V4 — Cognitive Risk Assessment & Memory Platform

NeuroAid is an end-to-end cognitive health screening, memory assistance, and clinician workflow web platform designed for early-stage cognitive risk evaluation (Alzheimer's, Dementia, Parkinson's) across five core domains: Speech, Memory, Reaction Time, Executive Function (Stroop), and Motor Coordination.

---

## 🚀 Quick Start Guide

### 1️⃣ Running the Backend Server (FastAPI)

#### Prerequisites
- **Python 3.10+** installed on your system.

#### Setup & Execution Steps

1. **Navigate to the `backend` directory:**
   ```bash
   cd backend
   ```

2. **(Optional but recommended) Create and activate a Virtual Environment:**
   - **Windows (PowerShell):**
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the FastAPI backend server:**
   ```bash
   uvicorn main:app --reload
   ```

> ⚠️ **IMPORTANT NOTE ON COMMAND SYNTAX:**
> Always run `uvicorn main:app --reload` (do **NOT** use `uvicorn app:app`).  
> The entry point file is `main.py` inside the `backend` folder. Running `app:app` will cause an `ERROR: Could not import module "app"`.

5. **Verify the Backend is Running:**
   - **Base URL:** `http://localhost:8000`
   - **Health Check:** `http://localhost:8000/health`
   - **Interactive OpenAPI (Swagger) Docs:** `http://localhost:8000/docs`
   - **ReDoc API Documentation:** `http://localhost:8000/redoc`

---

### 2️⃣ Running the Frontend (React 19 + Vite)

1. Open a new terminal tab/window and navigate to `frontend`:
   ```bash
   cd frontend
   ```

2. Install Node dependencies:
   ```bash
   npm install
   ```

3. Launch the development server:
   ```bash
   npm run dev
   ```

4. Access the web app in your browser at `http://localhost:5173`.

---

### 3️⃣ Running the AI Microservice (Optional RAG & Model Analytics)

1. Open a new terminal tab/window and navigate to `ai-service`:
   ```bash
   cd ai-service
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the AI microservice on Port 8001:
   ```bash
   uvicorn app:app --reload --port 8001
   ```

## 🎮 Cognitive Brain Games & Adaptive Difficulty Engine

NeuroAid features an adaptive, culturally-localized cognitive gaming suite specifically calibrated for elderly individuals with mild cognitive impairment (MCI) and dementia. Games evaluate and stimulate neuroplasticity across 5 clinical domains:

| Game | Cognitive Domain | Accent Color | Mechanics |
|---|---|---|---|
| **Memory Match** | Visuospatial & Memory | Emerald (`#34d399`) | Pair matching traditional North Eastern items (Assam Tea, Japi, Rhino, Dhol, Lotus, etc.) |
| **Sequence Recall** | Working Memory & Concentration | Sky Blue (`#60a5fa`) | Auditory and visual sequence repetition with color frequency chords |
| **Object Recognition** | Semantic & Visual Recognition | Amber (`#f59e0b`) | Cultural artifact identification with hints and voice answer options |
| **Pattern Completion** | Executive Function & Fluid Reasoning | Violet (`#a78bfa`) | Sequence and matrix pattern deduction with missing slot identification |
| **Daily Routine Recall** | Orientation & Procedural Memory | Orange (`#fb923c`) | Chronological ordering of daily activities from morning tea to night rest |

### 5 Difficulty Levels (Easy to Advance)
All games feature **5 Difficulty Levels** accessible via the top-bar level selector or automatically recommended by the AI:
- **Level 1 (Easy)**: Accessible baseline (e.g., 3 pairs / 3 items / 3 rounds) with gentle pacing.
- **Level 2 (Medium)**: Standard challenge (e.g., 4 pairs / 4 items / 4 rounds).
- **Level 3 (Hard)**: Elevated cognitive demand (e.g., 6 pairs / 5 items / 5 rounds).
- **Level 4 (Pro)**: High-performance challenge (e.g., 8 pairs / 6 items / 7 rounds) with accelerated pacing.
- **Level 5 (Advance)**: Master challenge (e.g., 10 pairs / 8 items / 9 rounds) with high-speed response benchmarks.

### 🧠 Deterministic Dynamic Difficulty Adjustment (DDA)
The backend `AdaptiveDifficultyEngine` (`backend/core/adaptive_difficulty.py`) evaluates session telemetry:
- **Accuracy & Error Rate:** Automatic progression if accuracy $\ge 85\%$ and error rate $\le 15\%$; supportive demotion if accuracy $< 60\%$.
- **Latency Drift & Fatigue:** Detects cognitive fatigue if late trial decision latencies slow by $> 30\%$, maintaining level to prevent patient distress.
- **Clinical Explainability:** Returns human-readable rationales and recommended levels to patients and caregivers.

---

## 🧪 Automated Testing

The platform includes comprehensive unit and integration test suites covering the adaptive engine, security hardening, clinical calculations, and REST APIs:

```bash
# Run all backend tests
python -m unittest discover -s backend/tests -p "test_*.py"
```
*Current status: **36/36 tests passing**.*

---

## 🛠️ Environment Configuration

The backend reads settings from `backend/core/settings.py` or environment variables (or `.env` file):

| Variable | Default Value | Description |
|---|---|---|
| `API_HOST` | `127.0.0.1` | Host IP binding |
| `API_PORT` | `8000` | Server listening port |
| `APP_ENV` | `development` | Application environment (`development` / `production`) |
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:3000` | CORS allowed origins |
| `AI_SERVICE_URL` | `http://localhost:8001` | URL of standalone AI microservice |

---

## 🔍 Common Troubleshooting

| Issue / Error | Cause | Solution |
|---|---|---|
| `ERROR: Could not import module "app"` | Ran `uvicorn app:app` instead of `uvicorn main:app` | Run `uvicorn main:app --reload` inside the `backend` directory. |
| `ModuleNotFoundError: No module named 'fastapi'` | Dependencies not installed in active python env | Run `pip install -r requirements.txt`. |
| `Address already in use` | Port 8000 is occupied by another process | Use a custom port: `uvicorn main:app --reload --port 8005` or kill the process on port 8000. |
| `CORS Error in Browser` | Frontend running on custom port not listed in CORS | Add your port to `ALLOWED_ORIGINS` in `.env` or settings. |
| `Memory Match Card Error` | React object child rendering in legacy versions | Resolved: Card labels are safely extracted as localized strings (`card.label[lang] || card.label.en`). |

---

## 📁 Repository Structure

```
HeCodes-main/
├── PRD.md                       # Project Requirements Document
├── Architecture.md              # Technical System Architecture & ML Specs
├── CURRENT_ARCHITECTURE.md      # Detailed Component Audit & Architecture State
├── Design.md                    # Visual Design Tokens & Typography Guidelines
├── IMPLEMENTATION_PLAN.md       # SIH PS 26003 Comprehensive Implementation Plan
├── backend/                     # FastAPI Primary Backend
│   ├── main.py                  # Entry Point (uvicorn main:app)
│   ├── core/                    # Security, Adaptive Engine, Storage, Settings
│   ├── models/                  # Pydantic schemas (schemas.py)
│   ├── routers/                 # API endpoint routers (games_api, auth, caregiver, etc.)
│   ├── services/                # Business services & persistence stores
│   └── tests/                   # 36 automated unit & integration tests
├── frontend/                    # React 19 + Vite Frontend App
│   ├── src/                     # UI components, brain games, pages, i18n, state
│   └── package.json
└── ai-service/                  # Standalone AI/RAG Microservice (Port 8001)
```

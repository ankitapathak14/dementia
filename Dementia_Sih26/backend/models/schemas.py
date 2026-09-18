"""
schemas.py — NeuroAid V4
Extended with all fields required by ResultsPage, ProgressPage, ProfileSetup,
and Cognitive Games Engine (SIH PS 26003).
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


# ── Sub-payloads from frontend ─────────────────────────────────────────────────

class SpeechData(BaseModel):
    audio_b64: Optional[str] = None
    wpm: Optional[float] = None
    speed_deviation: Optional[float] = None
    speech_speed_variability: Optional[float] = None
    pause_ratio: Optional[float] = None
    completion_ratio: Optional[float] = None
    restart_count: Optional[int] = 0
    speech_start_delay: Optional[float] = None

class MemoryData(BaseModel):
    word_recall_accuracy: float = Field(default=50.0, ge=0, le=100)
    pattern_accuracy: float = Field(default=50.0, ge=0, le=100)
    delayed_recall_accuracy: Optional[float] = Field(default=None, ge=0, le=100)
    recall_latency_seconds: Optional[float] = None
    order_match_ratio: Optional[float] = None
    intrusion_count: Optional[int] = 0

class ReactionData(BaseModel):
    times: List[float] = Field(default_factory=list)
    miss_count: Optional[int] = 0
    initiation_delay: Optional[float] = None

class StroopData(BaseModel):
    total_trials: int = 0
    error_count: int = 0
    mean_rt: Optional[float] = None
    incongruent_rt: Optional[float] = None

class TapData(BaseModel):
    intervals: List[float] = Field(default_factory=list)
    tap_count: int = 0

class UserProfile(BaseModel):
    age: Optional[int] = None
    education_level: Optional[int] = None   # 1–5
    sleep_hours: Optional[float] = None

class MedicalConditions(BaseModel):
    diabetes: bool = False
    hypertension: bool = False
    stroke_history: bool = False
    family_alzheimers: bool = False
    parkinsons_dx: bool = False
    depression: bool = False
    thyroid_disorder: bool = False

class FatigueFlags(BaseModel):
    tired: bool = False
    sleep_deprived: bool = False
    sick: bool = False
    anxious: bool = False

# ── Main request ───────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    speech_audio: Optional[str] = None
    memory_results: Dict[str, float] = Field(default_factory=lambda: {"word_recall_accuracy": 50.0, "pattern_accuracy": 50.0})
    reaction_times: List[float] = Field(default_factory=list)
    speech: Optional[SpeechData] = None
    memory: Optional[MemoryData] = None
    reaction: Optional[ReactionData] = None
    stroop: Optional[StroopData] = None
    tap: Optional[TapData] = None
    profile: Optional[UserProfile] = None
    conditions: Optional[MedicalConditions] = None
    fatigue: Optional[FatigueFlags] = None

# ── Feature vector (18 features) ──────────────────────────────────────────────

class FeatureVector(BaseModel):
    wpm: float
    speed_deviation: float
    speech_variability: float
    pause_ratio: float
    speech_start_delay: float
    immediate_recall_accuracy: float
    delayed_recall_accuracy: float
    intrusion_count: float
    recall_latency: float
    order_match_ratio: float
    mean_rt: float
    std_rt: float
    min_rt: float
    reaction_drift: float
    miss_count: float
    stroop_error_rate: float
    stroop_rt: float
    tap_interval_std: float

class DiseaseRiskLevels(BaseModel):
    alzheimers: str
    dementia: str
    parkinsons: str

# ── ML Layer A & B Analysis ───────────────────────────────────────────────────

class MLBehavioralAnalysis(BaseModel):
    status: str
    anomaly_detected: bool = False
    severity: str = "none"
    anomaly_score: Optional[float] = None
    raw_decision_score: Optional[float] = None
    session_count: Optional[int] = None
    min_history_required: Optional[int] = None
    top_deviating_features: List[Dict[str, Any]] = Field(default_factory=list)
    baseline_comparison: Dict[str, Any] = Field(default_factory=dict)
    terminology: str = "Cognitive Performance Deviation"
    message: Optional[str] = None

class MLClinicalReference(BaseModel):
    status: str
    model: str = "OASIS_LogisticRegression"
    probability: Optional[float] = None
    risk_band: Optional[str] = None
    explanations: List[Dict[str, Any]] = Field(default_factory=list)
    message: Optional[str] = None
    research_disclaimer: Optional[str] = None

class MLCombinedIndicator(BaseModel):
    available: bool = False
    value: Optional[float] = None
    label: Optional[str] = None
    fusion_method: Optional[str] = None
    components: Optional[Dict[str, Any]] = None

class MLAnalysis(BaseModel):
    behavioral: MLBehavioralAnalysis
    clinical_reference: MLClinicalReference
    combined_indicator: MLCombinedIndicator

# ── Response (V4 / V5) ────────────────────────────────────────────────────────

class AnalyzeResponse(BaseModel):
    # Domain scores (0–100, higher = healthier)
    speech_score: float
    memory_score: float
    reaction_score: float
    executive_score: float
    motor_score: float

    # Disease-specific probabilities (0–1) - DEPRECATED, kept for frontend compatibility
    alzheimers_risk: Optional[float] = None
    dementia_risk: Optional[float] = None
    parkinsons_risk: Optional[float] = None
    risk_levels: Optional[DiseaseRiskLevels] = None

    # Multi-Modal ML Architecture (Layer A + Layer B + Fusion)
    ml_analysis: Optional[MLAnalysis] = None
    uncertainty: Optional[Dict[str, Any]] = None

    # V4 composite + wellness
    composite_risk_score: Optional[float] = None   # 0–100, higher = more risk

    # V4 hybrid + CI
    hybrid_risk: Optional[float] = None
    confidence: Optional[float] = None
    recommend_retest: Optional[bool] = None
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    ci_label: Optional[str] = None
    logistic_risk_probability: Optional[float] = None
    confidence_interval_label: Optional[str] = None

    # V4 anomaly detection
    anomaly_alert: Optional[str] = None
    anomaly_details: Optional[Dict[str, Any]] = None

    # V4 explainability — risk_drivers (for RiskDriversPanel)
    risk_drivers: Optional[Dict[str, float]] = None

    # V4 feature importance
    feature_importance: Optional[List[Dict]] = None

    # V4 model validation
    model_validation: Optional[Dict[str, Any]] = None

    # Feature transparency
    feature_vector: Optional[FeatureVector] = None
    attention_variability_index: Optional[float] = None

    disclaimer: str = (
        "⚠️ This is a behavioral screening tool only. "
        "It is NOT a medical diagnosis. Always consult a qualified "
        "neurologist or physician for clinical evaluation."
    )


# ── Cognitive Games Schemas (SIH PS 26003) ────────────────────────────────────

class GameCatalogueItem(BaseModel):
    id: str
    title: str
    tagline: str
    description: str
    cognitive_domain: str
    domain_label: str
    icon: str
    accent_color: str
    levels: List[int] = Field(default_factory=lambda: [1, 2, 3])
    instructions: Dict[str, str] = Field(default_factory=dict)


class AdaptiveAdjustment(BaseModel):
    previous_level: int
    new_level: int
    reason: List[str]
    adjustment: str = "maintain"  # "increase" | "decrease" | "maintain"
    metrics_summary: Optional[Dict[str, Any]] = None
    clinical_rationale: Optional[str] = None


class GameRecommendationResponse(BaseModel):
    game_id: str
    recommended_level: int
    previous_level: int
    reason: List[str]
    clinical_rationale: Optional[str] = None


class GameSessionSubmit(BaseModel):
    client_action_id: Optional[str] = Field(default=None, max_length=100)
    game_id: str
    difficulty_level: int = Field(default=1, ge=1, le=3)
    duration_seconds: float = Field(..., ge=0)
    moves_count: int = Field(default=0, ge=0)
    mistakes_count: int = Field(default=0, ge=0)
    score: Optional[float] = Field(default=None, ge=0, le=100)
    completed: bool = True
    accuracy: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    response_time: Optional[float] = Field(default=None, ge=0.0)
    error_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    completion_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    language: str = "en"
    telemetry: Optional[Dict[str, Any]] = None


class GameSessionResponse(BaseModel):
    session_id: str
    game_id: str
    game_title: str
    cognitive_domain: str
    difficulty_level: int
    score: float
    stars: int
    stars_label: str
    feedback_message: str
    performance_level: str
    duration_seconds: float
    moves_count: int
    mistakes_count: int
    timestamp: str
    adaptive_difficulty: Optional[AdaptiveAdjustment] = None


class GameStatsSummary(BaseModel):
    total_games_played: int
    total_stars_earned: int
    current_streak_days: int
    domain_scores: Dict[str, float]
    recent_sessions: List[Dict[str, Any]] = Field(default_factory=list)


# ── Rhythm & Recall Schemas ───────────────────────────────────────────────

class MusicTrack(BaseModel):
    music_id: str
    title: str
    artist: str
    region: str = "pan-india"
    language: str = "hindi"
    genre: str = "folk"
    era: str = "1960-1980"
    audio_url: str
    duration_seconds: int = 180
    is_active: bool = True
    created_at: Optional[str] = None
    # Optional beat metadata (list of expected beat timestamps in seconds)
    beat_timestamps: Optional[List[float]] = None
    description: Optional[str] = None


class RhythmSessionCreate(BaseModel):
    client_action_id: Optional[str] = Field(default=None, max_length=100)
    mode: str  # "recognition" | "rhythm_tap" | "hum_along" | "memory_connection"
    music_ids: List[str] = Field(default_factory=list)
    duration_seconds: float = Field(default=0, ge=0)
    # Mode 1 — Song Recognition
    recognition_correct: int = 0
    recognition_total: int = 0
    # Mode 2 — Rhythm Tap
    tap_count: int = 0
    rhythm_engagement_pct: Optional[float] = None
    # Mode 3 — Hum Along
    voice_participated: bool = False
    voice_duration_seconds: float = 0
    # Mode 4 — Memory Connection
    memory_responses: List[str] = Field(default_factory=list)
    mood_responses: List[str] = Field(default_factory=list)
    # Rounds detail
    rounds: Optional[List[Dict[str, Any]]] = None


class RhythmSessionResponse(BaseModel):
    session_id: str
    user_id: str
    mode: str
    duration_seconds: float
    recognition_correct: int
    recognition_total: int
    tap_count: int
    rhythm_engagement_pct: Optional[float]
    voice_participated: bool
    memory_responses: List[str]
    mood_responses: List[str]
    engagement_label: str
    encouragement: str
    timestamp: str


class RhythmRoundData(BaseModel):
    session_id: str
    round_number: int
    song_id: str
    mode: str
    # Recognition
    selected_answer: Optional[str] = None
    correct_answer: Optional[str] = None
    is_correct: Optional[bool] = None
    response_time_ms: Optional[float] = None
    # Rhythm tap
    tap_timestamps: Optional[List[float]] = None
    expected_beat_timestamps: Optional[List[float]] = None
    timing_errors: Optional[List[float]] = None
    rhythm_accuracy: Optional[float] = None
    # Memory / mood
    memory_response: Optional[str] = None
    mood_response: Optional[str] = None


class MusicPreferences(BaseModel):
    region: Optional[str] = None
    language: Optional[str] = None
    youth_era: Optional[str] = None
    favorite_genres: List[str] = Field(default_factory=list)
    favorite_artists: List[str] = Field(default_factory=list)
    favorite_song_ids: List[str] = Field(default_factory=list)
    session_duration_minutes: int = 10
    evening_session_enabled: bool = False
    evening_session_time: Optional[str] = None  # "HH:MM" format


class RhythmAnalytics(BaseModel):
    patient_id: str
    total_sessions: int
    avg_duration_minutes: float
    avg_recognition_pct: Optional[float]
    rhythm_participation_label: str
    voice_participation_pct: float
    recent_mood_responses: List[str]
    trend_note: str
    sessions_this_week: int
    songs_played_total: int

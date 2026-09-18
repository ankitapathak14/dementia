"""
backend/tests/fixtures/cognitive_sessions.py
============================================
Deterministic synthetic test fixtures for end-to-end cognitive assessment pipeline validation.

DISCLAIMER & INTEGRITY NOTICE:
- These are DETERMINISTIC TEST FIXTURES ONLY.
- They are NOT real patient observations.
- They are NOT machine learning training data.
- They do NOT claim clinical validity.
- They are structured strictly according to NeuroAid's production Pydantic schemas (AnalyzeRequest).

Patients Defined:
- Patient A: Stable performance across all 5 cognitive assessment modalities (5 sessions).
- Patient B: Stable baseline (sessions 1-3) followed by substantial memory decline (sessions 4-5).
- Patient C: Stable baseline (sessions 1-3) followed by substantial reaction latency/variability decline (sessions 4-5).
- Patient D: Partial assessment (Memory & Reaction supplied; Speech, Stroop, Tap omitted).
"""

from __future__ import annotations

from typing import List
from models.schemas import (
    AnalyzeRequest,
    MemoryData,
    ReactionData,
    SpeechData,
    StroopData,
    TapData,
    UserProfile,
)


def get_patient_a_stable_sessions() -> List[AnalyzeRequest]:
    """
    Patient A: 5 realistic, chronological sessions exhibiting stable healthy performance
    across all five cognitive test modules.
    """
    sessions = []
    # Minor realistic test-retest fluctuations across sessions
    variations = [
        {"wpm": 124.0, "word_acc": 86.0, "del_acc": 82.0, "rt": 292.0, "stroop_rt": 535.0},
        {"wpm": 126.0, "word_acc": 84.0, "del_acc": 79.0, "rt": 297.0, "stroop_rt": 545.0},
        {"wpm": 125.0, "word_acc": 85.0, "del_acc": 80.0, "rt": 294.0, "stroop_rt": 540.0},
        {"wpm": 123.0, "word_acc": 87.0, "del_acc": 81.0, "rt": 296.0, "stroop_rt": 538.0},
        {"wpm": 125.0, "word_acc": 85.0, "del_acc": 80.0, "rt": 295.0, "stroop_rt": 542.0},
    ]

    for v in variations:
        rt_base = v["rt"]
        sessions.append(
            AnalyzeRequest(
                speech=SpeechData(
                    wpm=v["wpm"],
                    speed_deviation=12.0,
                    speech_speed_variability=10.0,
                    pause_ratio=0.14,
                    completion_ratio=1.0,
                    restart_count=0,
                    speech_start_delay=0.6,
                ),
                memory=MemoryData(
                    word_recall_accuracy=v["word_acc"],
                    pattern_accuracy=80.0,
                    delayed_recall_accuracy=v["del_acc"],
                    recall_latency_seconds=3.1,
                    order_match_ratio=0.90,
                    intrusion_count=1,
                ),
                reaction=ReactionData(
                    times=[rt_base - 10.0, rt_base + 8.0, rt_base - 5.0, rt_base + 12.0, rt_base - 3.0],
                    miss_count=0,
                    initiation_delay=180.0,
                ),
                stroop=StroopData(
                    total_trials=20,
                    error_count=1,
                    mean_rt=v["stroop_rt"],
                    incongruent_rt=v["stroop_rt"] + 45.0,
                ),
                tap=TapData(
                    intervals=[205.0, 210.0, 202.0, 208.0, 204.0],
                    tap_count=5,
                ),
                profile=UserProfile(age=72, education_level=4, sleep_hours=7.5),
            )
        )
    return sessions


def get_patient_b_memory_decline_sessions() -> List[AnalyzeRequest]:
    """
    Patient B: 5 chronological sessions.
    Sessions 1-3: Stable memory performance.
    Sessions 4-5: Substantial deterioration in memory-related measurements.
    Other domains (speech, reaction, Stroop, tap) remain approximately stable.
    """
    sessions = []

    # Sessions 1-3: Stable baseline
    baseline_variations = [
        {"word_acc": 86.0, "del_acc": 82.0, "intrusions": 1, "latency": 3.0, "order": 0.92},
        {"word_acc": 84.0, "del_acc": 80.0, "intrusions": 1, "latency": 3.2, "order": 0.88},
        {"word_acc": 85.0, "del_acc": 81.0, "intrusions": 1, "latency": 3.1, "order": 0.90},
    ]
    for b in baseline_variations:
        sessions.append(
            AnalyzeRequest(
                speech=SpeechData(
                    wpm=125.0,
                    speed_deviation=12.0,
                    speech_speed_variability=10.0,
                    pause_ratio=0.14,
                    completion_ratio=1.0,
                    restart_count=0,
                    speech_start_delay=0.6,
                ),
                memory=MemoryData(
                    word_recall_accuracy=b["word_acc"],
                    pattern_accuracy=80.0,
                    delayed_recall_accuracy=b["del_acc"],
                    recall_latency_seconds=b["latency"],
                    order_match_ratio=b["order"],
                    intrusion_count=b["intrusions"],
                ),
                reaction=ReactionData(
                    times=[285.0, 305.0, 290.0, 300.0, 295.0],
                    miss_count=0,
                    initiation_delay=180.0,
                ),
                stroop=StroopData(total_trials=20, error_count=1, mean_rt=540.0, incongruent_rt=585.0),
                tap=TapData(intervals=[205.0, 210.0, 202.0, 208.0, 204.0], tap_count=5),
                profile=UserProfile(age=74, education_level=3, sleep_hours=7.0),
            )
        )

    # Session 4: Acute memory drop
    sessions.append(
        AnalyzeRequest(
            speech=SpeechData(wpm=124.0, speed_deviation=12.0, speech_speed_variability=10.0, pause_ratio=0.15, speech_start_delay=0.6),
            memory=MemoryData(
                word_recall_accuracy=35.0,
                pattern_accuracy=40.0,
                delayed_recall_accuracy=25.0,
                recall_latency_seconds=7.8,
                order_match_ratio=0.35,
                intrusion_count=5,
            ),
            reaction=ReactionData(times=[288.0, 302.0, 292.0, 304.0, 298.0], miss_count=0, initiation_delay=180.0),
            stroop=StroopData(total_trials=20, error_count=1, mean_rt=545.0, incongruent_rt=590.0),
            tap=TapData(intervals=[205.0, 210.0, 202.0, 208.0, 204.0], tap_count=5),
            profile=UserProfile(age=74, education_level=3, sleep_hours=7.0),
        )
    )

    # Session 5: Sustained severe memory deterioration
    sessions.append(
        AnalyzeRequest(
            speech=SpeechData(wpm=123.0, speed_deviation=13.0, speech_speed_variability=11.0, pause_ratio=0.15, speech_start_delay=0.7),
            memory=MemoryData(
                word_recall_accuracy=20.0,
                pattern_accuracy=30.0,
                delayed_recall_accuracy=15.0,
                recall_latency_seconds=8.9,
                order_match_ratio=0.25,
                intrusion_count=7,
            ),
            reaction=ReactionData(times=[290.0, 305.0, 295.0, 300.0, 292.0], miss_count=0, initiation_delay=180.0),
            stroop=StroopData(total_trials=20, error_count=2, mean_rt=550.0, incongruent_rt=595.0),
            tap=TapData(intervals=[206.0, 211.0, 203.0, 207.0, 205.0], tap_count=5),
            profile=UserProfile(age=74, education_level=3, sleep_hours=6.5),
        )
    )

    return sessions


def get_patient_c_reaction_decline_sessions() -> List[AnalyzeRequest]:
    """
    Patient C: 5 chronological sessions.
    Sessions 1-3: Stable reaction latency and variability (~290ms, 0 misses).
    Sessions 4-5: Substantially slower and more variable reaction times (>780ms, multiple misses).
    Other domains (speech, memory, Stroop, tap) remain approximately stable.
    """
    sessions = []

    # Sessions 1-3: Stable baseline
    baseline_rts = [
        [285.0, 295.0, 290.0, 300.0, 288.0],
        [290.0, 300.0, 295.0, 305.0, 292.0],
        [288.0, 292.0, 286.0, 298.0, 290.0],
    ]
    for rts in baseline_rts:
        sessions.append(
            AnalyzeRequest(
                speech=SpeechData(wpm=125.0, speed_deviation=12.0, speech_speed_variability=10.0, pause_ratio=0.14, speech_start_delay=0.6),
                memory=MemoryData(
                    word_recall_accuracy=85.0,
                    pattern_accuracy=80.0,
                    delayed_recall_accuracy=80.0,
                    recall_latency_seconds=3.1,
                    order_match_ratio=0.90,
                    intrusion_count=1,
                ),
                reaction=ReactionData(times=rts, miss_count=0, initiation_delay=180.0),
                stroop=StroopData(total_trials=20, error_count=1, mean_rt=540.0, incongruent_rt=580.0),
                tap=TapData(intervals=[205.0, 210.0, 202.0, 208.0, 204.0], tap_count=5),
                profile=UserProfile(age=71, education_level=4, sleep_hours=7.5),
            )
        )

    # Session 4: Acute reaction slowing and misses
    slow_rts_4 = [780.0, 820.0, 750.0, 910.0, 680.0]
    sessions.append(
        AnalyzeRequest(
            speech=SpeechData(wpm=125.0, speed_deviation=12.0, speech_speed_variability=10.0, pause_ratio=0.14, speech_start_delay=0.6),
            memory=MemoryData(
                word_recall_accuracy=85.0,
                pattern_accuracy=80.0,
                delayed_recall_accuracy=80.0,
                recall_latency_seconds=3.1,
                order_match_ratio=0.90,
                intrusion_count=1,
            ),
            reaction=ReactionData(times=slow_rts_4, miss_count=3, initiation_delay=350.0),
            stroop=StroopData(total_trials=20, error_count=1, mean_rt=545.0, incongruent_rt=585.0),
            tap=TapData(intervals=[205.0, 210.0, 202.0, 208.0, 204.0], tap_count=5),
            profile=UserProfile(age=71, education_level=4, sleep_hours=7.0),
        )
    )

    # Session 5: Sustained severe reaction latency & misses
    slow_rts_5 = [850.0, 920.0, 810.0, 1050.0, 790.0]
    sessions.append(
        AnalyzeRequest(
            speech=SpeechData(wpm=124.0, speed_deviation=12.0, speech_speed_variability=10.0, pause_ratio=0.14, speech_start_delay=0.6),
            memory=MemoryData(
                word_recall_accuracy=84.0,
                pattern_accuracy=80.0,
                delayed_recall_accuracy=79.0,
                recall_latency_seconds=3.2,
                order_match_ratio=0.88,
                intrusion_count=1,
            ),
            reaction=ReactionData(times=slow_rts_5, miss_count=4, initiation_delay=400.0),
            stroop=StroopData(total_trials=20, error_count=2, mean_rt=550.0, incongruent_rt=590.0),
            tap=TapData(intervals=[206.0, 211.0, 203.0, 207.0, 205.0], tap_count=5),
            profile=UserProfile(age=71, education_level=4, sleep_hours=7.0),
        )
    )

    return sessions


def get_patient_d_partial_session() -> AnalyzeRequest:
    """
    Patient D: Deliberately partial assessment.
    Supplied:
    - Memory assessment completed.
    - Reaction assessment completed.
    Deliberately Omitted:
    - Speech assessment (speech=None, speech_audio=None).
    - Executive/Stroop assessment (stroop=None).
    - Motor/Tapping assessment (tap=None).
    """
    return AnalyzeRequest(
        speech_audio=None,
        speech=None,
        memory=MemoryData(
            word_recall_accuracy=82.0,
            pattern_accuracy=78.0,
            delayed_recall_accuracy=75.0,
            recall_latency_seconds=3.2,
            order_match_ratio=0.88,
            intrusion_count=1,
        ),
        reaction=ReactionData(
            times=[290.0, 310.0, 295.0, 305.0],
            miss_count=0,
            initiation_delay=185.0,
        ),
        stroop=None,
        tap=None,
        profile=UserProfile(age=69, education_level=4, sleep_hours=8.0),
    )


def get_patient_d_multidomain_decline_sessions() -> List[AnalyzeRequest]:
    """
    Patient D: 5 chronological sessions exhibiting multi-domain cognitive change.
    Sessions 1-3: Stable baseline across Memory, Reaction, and Speech.
    Sessions 4-5: Controlled deterioration across Memory, Reaction, and Speech.
    """
    sessions = []

    # Sessions 1-3: Stable baseline
    baseline_profiles = [
        {"wpm": 125.0, "pause": 0.14, "delay": 0.6, "word_acc": 86.0, "del_acc": 82.0, "rt": 292.0},
        {"wpm": 124.0, "pause": 0.15, "delay": 0.65, "word_acc": 84.0, "del_acc": 80.0, "rt": 298.0},
        {"wpm": 126.0, "pause": 0.14, "delay": 0.6, "word_acc": 85.0, "del_acc": 81.0, "rt": 294.0},
    ]
    for b in baseline_profiles:
        rt_base = b["rt"]
        sessions.append(
            AnalyzeRequest(
                speech=SpeechData(
                    wpm=b["wpm"],
                    speed_deviation=12.0,
                    speech_speed_variability=10.0,
                    pause_ratio=b["pause"],
                    speech_start_delay=b["delay"],
                ),
                memory=MemoryData(
                    word_recall_accuracy=b["word_acc"],
                    pattern_accuracy=80.0,
                    delayed_recall_accuracy=b["del_acc"],
                    recall_latency_seconds=3.1,
                    order_match_ratio=0.90,
                    intrusion_count=1,
                ),
                reaction=ReactionData(
                    times=[rt_base - 8.0, rt_base + 6.0, rt_base - 4.0, rt_base + 10.0, rt_base - 2.0],
                    miss_count=0,
                    initiation_delay=180.0,
                ),
                stroop=StroopData(total_trials=20, error_count=1, mean_rt=540.0, incongruent_rt=580.0),
                tap=TapData(intervals=[205.0, 210.0, 202.0, 208.0, 204.0], tap_count=5),
                profile=UserProfile(age=73, education_level=4, sleep_hours=7.5),
            )
        )

    # Session 4: Controlled multi-domain decline (Memory, Reaction, Speech)
    sessions.append(
        AnalyzeRequest(
            speech=SpeechData(
                wpm=88.0,
                speed_deviation=28.0,
                speech_speed_variability=24.0,
                pause_ratio=0.28,
                speech_start_delay=1.8,
            ),
            memory=MemoryData(
                word_recall_accuracy=48.0,
                pattern_accuracy=55.0,
                delayed_recall_accuracy=38.0,
                recall_latency_seconds=6.5,
                order_match_ratio=0.55,
                intrusion_count=4,
            ),
            reaction=ReactionData(
                times=[720.0, 780.0, 690.0, 810.0, 740.0],
                miss_count=2,
                initiation_delay=320.0,
            ),
            stroop=StroopData(total_trials=20, error_count=3, mean_rt=680.0, incongruent_rt=750.0),
            tap=TapData(intervals=[206.0, 212.0, 204.0, 209.0, 205.0], tap_count=5),
            profile=UserProfile(age=73, education_level=4, sleep_hours=6.5),
        )
    )

    # Session 5: Sustained multi-domain decline
    sessions.append(
        AnalyzeRequest(
            speech=SpeechData(
                wpm=76.0,
                speed_deviation=34.0,
                speech_speed_variability=30.0,
                pause_ratio=0.35,
                speech_start_delay=2.5,
            ),
            memory=MemoryData(
                word_recall_accuracy=36.0,
                pattern_accuracy=45.0,
                delayed_recall_accuracy=26.0,
                recall_latency_seconds=8.2,
                order_match_ratio=0.42,
                intrusion_count=6,
            ),
            reaction=ReactionData(
                times=[840.0, 920.0, 790.0, 980.0, 860.0],
                miss_count=3,
                initiation_delay=380.0,
            ),
            stroop=StroopData(total_trials=20, error_count=4, mean_rt=720.0, incongruent_rt=810.0),
            tap=TapData(intervals=[208.0, 214.0, 205.0, 210.0, 207.0], tap_count=5),
            profile=UserProfile(age=73, education_level=4, sleep_hours=6.0),
        )
    )

    return sessions


def get_patient_e_insufficient_history_sessions() -> List[AnalyzeRequest]:
    """
    Patient E: Deliberately incomplete longitudinal history (only 1 completed session).
    Expected:
    - Status: 'insufficient_history' (requires >= 3 sessions to establish personal baseline).
    - Behavioral anomaly detection does not fabricate alerts.
    - Doctor Dashboard classifies as 'Pending Assessment'.
    """
    return [
        AnalyzeRequest(
            speech=SpeechData(
                wpm=122.0,
                speed_deviation=14.0,
                speech_speed_variability=11.0,
                pause_ratio=0.15,
                speech_start_delay=0.65,
            ),
            memory=MemoryData(
                word_recall_accuracy=84.0,
                pattern_accuracy=78.0,
                delayed_recall_accuracy=80.0,
                recall_latency_seconds=3.2,
                order_match_ratio=0.88,
                intrusion_count=1,
            ),
            reaction=ReactionData(
                times=[295.0, 305.0, 290.0, 310.0, 298.0],
                miss_count=0,
                initiation_delay=185.0,
            ),
            stroop=StroopData(total_trials=20, error_count=1, mean_rt=545.0, incongruent_rt=585.0),
            tap=TapData(intervals=[204.0, 208.0, 201.0, 206.0, 203.0], tap_count=5),
            profile=UserProfile(age=69, education_level=4, sleep_hours=7.5),
        )
    ]


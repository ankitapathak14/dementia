import { useState, useEffect, useRef, useCallback } from "react";
import { useI18n } from "../../i18n/LanguageContext";
import { speak, stopSpeaking, playSelectSound } from "../../utils/voice";
import { registerVoiceContext } from "../../utils/voiceDispatcher";
import { playTapSound, playMatchSound, playGentleMissSound } from "../../utils/gameAudio";
import { getGameRecommendation, submitGameSession } from "../../services/api";
import { getStoriesForLevel } from "../../data/villageContent";

const LIME = "#C8F135";
const EMERALD = "#10B981";

export default function VoiceOfVillageGame({ setPage }) {
  const { language, t } = useI18n();
  const langKey = language || "en-IN";

  // Difficulty level (1 = Easy/Direct, 2 = Medium/Object, 3 = Advanced/Detail)
  const [level, setLevel] = useState(1);
  const [roundIndex, setRoundIndex] = useState(0);
  const [stories, setStories] = useState([]);
  const [currentStory, setCurrentStory] = useState(null);

  // Interaction phase: "intro" | "narrating" | "answering" | "feedback" | "completed"
  const [phase, setPhase] = useState("intro");
  const [selectedOptionId, setSelectedOptionId] = useState(null);
  const [feedbackText, setFeedbackText] = useState("");
  const [isCorrect, setIsCorrect] = useState(null);
  const [isSpeakingNarration, setIsSpeakingNarration] = useState(false);

  // Performance telemetry for AdaptiveDifficultyEngine
  const [sessionMoves, setSessionMoves] = useState(0);
  const [sessionMistakes, setSessionMistakes] = useState(0);
  const [sessionReplays, setSessionReplays] = useState(0);
  const [completionResult, setCompletionResult] = useState(null);

  const startTimeRef = useRef(Date.now());
  const questionShowTimeRef = useRef(Date.now());
  const latenciesRef = useRef([]);
  const isMountedRef = useRef(true);

  // Fetch adaptive difficulty recommendation on mount
  useEffect(() => {
    isMountedRef.current = true;
    getGameRecommendation("voice_village")
      .then((res) => {
        if (res?.recommended_level && [1, 2, 3].includes(res.recommended_level)) {
          setLevel(res.recommended_level);
        }
      })
      .catch(() => {});

    return () => {
      isMountedRef.current = false;
      stopSpeaking();
    };
  }, []);

  // Initialize story set for the selected level
  const initLevel = useCallback((lvl = level) => {
    stopSpeaking();
    const levelPool = getStoriesForLevel(lvl);
    // Shuffle stories gently so each session is fresh
    const shuffled = [...levelPool].sort(() => Math.random() - 0.5).slice(0, 3);
    setStories(shuffled);
    setRoundIndex(0);
    setCurrentStory(shuffled[0] || null);
    setPhase("intro");
    setSelectedOptionId(null);
    setFeedbackText("");
    setIsCorrect(null);
    setSessionMoves(0);
    setSessionMistakes(0);
    setSessionReplays(0);
    setCompletionResult(null);
    startTimeRef.current = Date.now();
    latenciesRef.current = [];
  }, [level]);

  useEffect(() => {
    initLevel(level);
  }, [level, initLevel]);

  // Read localized text helper with fallback
  const getLocText = (obj, fallback = "") => {
    if (!obj) return fallback;
    if (typeof obj === "string") return obj;
    return obj[langKey] || obj["en-IN"] || obj.en || Object.values(obj)[0] || fallback;
  };

  // Play narration for current story
  const narrateStoryAndQuestion = useCallback((storyItem) => {
    if (!storyItem) return;
    stopSpeaking();
    setPhase("narrating");
    setIsSpeakingNarration(true);

    const listenPrompt = t("listenCarefully", "Listen carefully");
    const storyText = getLocText(storyItem.story);
    const questionText = getLocText(storyItem.question);

    // Sequence: Listen prompt -> Story -> Question -> Ready for answer
    speak(listenPrompt, langKey, () => {
      if (!isMountedRef.current) return;
      speak(storyText, langKey, () => {
        if (!isMountedRef.current) return;
        speak(questionText, langKey, () => {
          if (!isMountedRef.current) return;
          setIsSpeakingNarration(false);
          setPhase("answering");
          questionShowTimeRef.current = Date.now();
        });
      });
    });
  }, [langKey, t]);

  // Start round narration whenever currentStory changes
  useEffect(() => {
    if (currentStory && phase === "intro") {
      const timer = setTimeout(() => {
        narrateStoryAndQuestion(currentStory);
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [currentStory, phase, narrateStoryAndQuestion]);

  // Handle "Listen Again" tap / voice command
  const handleListenAgain = useCallback(() => {
    if (!currentStory) return;
    playTapSound();
    setSessionReplays((r) => r + 1);
    narrateStoryAndQuestion(currentStory);
  }, [currentStory, narrateStoryAndQuestion]);

  // Handle answer selection (button tap or voice command)
  const handleSelectAnswer = useCallback((option) => {
    if (phase !== "answering" || !currentStory || !option) return;

    const latency = Math.max(0.4, (Date.now() - questionShowTimeRef.current) / 1000);
    latenciesRef.current.push(latency);

    setSelectedOptionId(option.id);
    setSessionMoves((m) => m + 1);
    setPhase("feedback");

    const correct = Boolean(option.correct);
    setIsCorrect(correct);

    if (correct) {
      playMatchSound();
      const feedbackMsg = t("correctFeedback", "That's right!");
      setFeedbackText(feedbackMsg);
      speak(feedbackMsg, langKey, () => {
        setTimeout(advanceRound, 1200);
      });
    } else {
      playGentleMissSound();
      setSessionMistakes((mis) => mis + 1);
      const feedbackMsg = t("incorrectFeedback", "That's okay. Let's try the next one.");
      setFeedbackText(feedbackMsg);
      speak(feedbackMsg, langKey, () => {
        setTimeout(advanceRound, 1400);
      });
    }
  }, [phase, currentStory, langKey, t]);

  // Advance to next story round or complete session
  const advanceRound = useCallback(() => {
    if (!isMountedRef.current) return;

    const nextIndex = roundIndex + 1;
    if (nextIndex < stories.length) {
      setRoundIndex(nextIndex);
      setCurrentStory(stories[nextIndex]);
      setPhase("intro");
      setSelectedOptionId(null);
      setFeedbackText("");
      setIsCorrect(null);
    } else {
      finishGameSession();
    }
  }, [roundIndex, stories]);

  // Finalize and submit game session to AdaptiveDifficultyEngine
  const finishGameSession = async () => {
    setPhase("completed");
    stopSpeaking();

    const duration = Math.max(1, Math.round((Date.now() - startTimeRef.current) / 1000));
    const totalMoves = Math.max(1, sessionMoves + 1);
    const mistakes = sessionMistakes + (isCorrect === false ? 1 : 0);
    const accuracy = Math.min(1.0, Math.max(0.0, (totalMoves - mistakes) / totalMoves));
    const errorRate = Math.min(1.0, mistakes / totalMoves);
    const avgResponseTime =
      latenciesRef.current.length > 0
        ? latenciesRef.current.reduce((a, b) => a + b, 0) / latenciesRef.current.length
        : duration / totalMoves;

    const sessionPayload = {
      game_id: "voice_village",
      difficulty_level: level,
      duration_seconds: duration,
      moves_count: totalMoves,
      mistakes_count: mistakes,
      completed: true,
      accuracy,
      response_time: avgResponseTime,
      error_rate: errorRate,
      completion_rate: 1.0,
      language: langKey,
      telemetry: {
        action_latencies: latenciesRef.current,
        replays_count: sessionReplays,
      },
    };

    try {
      const res = await submitGameSession(sessionPayload);
      if (isMountedRef.current) {
        setCompletionResult(res);
      }
    } catch (e) {
      // Offline fallback calculation matching backend heuristics
      if (isMountedRef.current) {
        setCompletionResult({
          score: Math.max(50, 100 - mistakes * 12),
          stars: mistakes === 0 ? 3 : mistakes <= 1 ? 2 : 1,
          duration_seconds: duration,
          feedback_message: "Wonderful auditory recall and attentive listening!",
          cognitive_domain: "Auditory Memory & Recall",
          adaptive_difficulty: {
            previous_level: level,
            new_level: mistakes === 0 && level < 3 ? level + 1 : level,
            reason: ["accuracy above target", "patient engaged calmly"],
            adjustment: mistakes === 0 && level < 3 ? "increase" : "maintain",
          },
        });
      }
    }

    const completeMsg = t("completedTodayActivity", "You completed today's activity. Well done!");
    speak(completeMsg, langKey);
  };

  // Register Voice Commands via voiceDispatcher (Optional speech input)
  useEffect(() => {
    if (phase !== "answering" || !currentStory) return;

    const visibleOptions = (currentStory.options || []).map((opt) => ({
      id: opt.id,
      label: getLocText(opt.text),
      optRef: opt,
    }));

    const unregister = registerVoiceContext(
      "voice_of_the_village",
      (rawText, parsed) => {
        const text = (rawText || "").toLowerCase();

        // 1. Voice command: Listen Again / Replay
        if (
          text.includes("listen again") ||
          text.includes("again") ||
          text.includes("repeat") ||
          text.includes("replay") ||
          text.includes("শুনক") ||
          text.includes("सुनें") ||
          parsed.intent === "REPLAY"
        ) {
          handleListenAgain();
          return { handled: true, speakText: t("listenCarefully", "Listen carefully") };
        }

        // 2. Voice command: Answer Option Selection
        if (parsed.intent === "SELECT_OPTION" && parsed.extractedData?.option) {
          const matched = visibleOptions.find(
            (o) => o.id === parsed.extractedData.option.id || o.label.toLowerCase() === parsed.extractedData.option.label?.toLowerCase()
          );
          if (matched) {
            handleSelectAnswer(matched.optRef);
            return { handled: true, speakText: matched.label };
          }
        }

        // Direct phrase matching on choice text
        for (const opt of currentStory.options || []) {
          const optLabel = getLocText(opt.text).toLowerCase();
          if (optLabel && text.includes(optLabel)) {
            handleSelectAnswer(opt);
            return { handled: true, speakText: optLabel };
          }
        }

        return false;
      },
      visibleOptions
    );

    return unregister;
  }, [phase, currentStory, langKey, handleListenAgain, handleSelectAnswer, t]);

  const storyText = currentStory ? getLocText(currentStory.story) : "";
  const questionText = currentStory ? getLocText(currentStory.question) : "";

  return (
    <div style={{ maxWidth: 860, margin: "0 auto", paddingBottom: 40, fontFamily: "'DM Sans', sans-serif" }}>
      {/* ── Top Navigation Bar ── */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 20,
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <button
          onClick={() => {
            playTapSound();
            stopSpeaking();
            if (setPage) setPage("games");
          }}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            padding: "10px 18px",
            borderRadius: 14,
            background: "rgba(255,255,255,0.06)",
            border: "1px solid rgba(255,255,255,0.12)",
            color: "#e5e7eb",
            fontWeight: 700,
            fontSize: 14,
            cursor: "pointer",
            transition: "all 0.15s ease",
          }}
        >
          ← {t("backToGames", "Back to Brain Games")}
        </button>

        {/* Cognitive Domain Tag */}
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            padding: "6px 14px",
            borderRadius: 99,
            background: `${EMERALD}18`,
            border: `1px solid ${EMERALD}44`,
            color: EMERALD,
            fontSize: 12,
            fontWeight: 800,
            letterSpacing: 0.5,
          }}
        >
          <span>🌾</span> Auditory Memory & Recall
        </div>
      </div>

      {/* ── Game Header & Difficulty Select ── */}
      <div
        style={{
          background: "rgba(14,16,12,0.85)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: 22,
          padding: "20px 24px",
          marginBottom: 16,
          boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 16,
          }}
        >
          <div>
            <h1
              style={{
                fontWeight: 900,
                fontSize: "clamp(22px, 3vw, 32px)",
                color: "#fff",
                letterSpacing: "-0.5px",
                margin: "0 0 4px",
                display: "flex",
                alignItems: "center",
                gap: 10,
              }}
            >
              <span>🌾</span> {t("voiceVillageTitle", "Voice of the Village")}
            </h1>
            <p style={{ margin: 0, color: "#9ca3af", fontSize: 14 }}>
              {t("voiceVillageDesc", "Listen to short everyday village stories and recall simple details.")}
            </p>
          </div>

          {/* Difficulty Level Tabs */}
          <div
            style={{
              display: "inline-flex",
              background: "rgba(0,0,0,0.5)",
              padding: 4,
              borderRadius: 14,
              border: "1px solid rgba(255,255,255,0.08)",
              gap: 4,
            }}
          >
            {[
              { lvl: 1, label: "Easy" },
              { lvl: 2, label: "Medium" },
              { lvl: 3, label: "Advance" },
            ].map(({ lvl, label }) => {
              const isActive = level === lvl;
              return (
                <button
                  key={lvl}
                  onClick={() => {
                    playSelectSound();
                    setLevel(lvl);
                  }}
                  style={{
                    padding: "6px 14px",
                    borderRadius: 10,
                    border: "none",
                    background: isActive ? EMERALD : "transparent",
                    color: isActive ? "#080808" : "#9ca3af",
                    fontWeight: isActive ? 800 : 600,
                    fontSize: 12,
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                  }}
                >
                  <span>Lvl {lvl}</span>
                  <span style={{ fontSize: 10, opacity: isActive ? 0.9 : 0.6 }}>({label})</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Round Progress Indicators */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginTop: 16,
            paddingTop: 14,
            borderTop: "1px solid rgba(255,255,255,0.06)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 13, color: "#9ca3af", fontWeight: 700 }}>Story Progress:</span>
            {stories.map((_, i) => (
              <span
                key={i}
                style={{
                  width: 28,
                  height: 8,
                  borderRadius: 99,
                  background:
                    i < roundIndex
                      ? EMERALD
                      : i === roundIndex
                      ? LIME
                      : "rgba(255,255,255,0.12)",
                  transition: "all 0.2s ease",
                }}
              />
            ))}
          </div>
          <span style={{ fontSize: 13, color: "#9ca3af" }}>
            Round <strong>{roundIndex + 1}</strong> of <strong>{stories.length || 3}</strong>
          </span>
        </div>
      </div>

      {/* ── Main Elderly-Friendly Game Board ── */}
      {phase !== "completed" ? (
        <div
          style={{
            background: "rgba(10,12,10,0.92)",
            backdropFilter: "blur(24px)",
            WebkitBackdropFilter: "blur(24px)",
            border: "1px solid rgba(255,255,255,0.09)",
            borderRadius: 24,
            padding: "32px 28px",
            minHeight: 440,
            boxShadow: "0 12px 40px rgba(0,0,0,0.6)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            textAlign: "center",
          }}
        >
          {/* Story Theme Icon */}
          <div
            style={{
              width: 64,
              height: 64,
              borderRadius: 20,
              background: "rgba(16,185,129,0.12)",
              border: `1px solid ${EMERALD}44`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 32,
              marginBottom: 18,
            }}
          >
            {currentStory?.icon || "🌾"}
          </div>

          {/* Voice Prompt Status Banner */}
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "6px 16px",
              borderRadius: 99,
              background: isSpeakingNarration ? "rgba(200,241,53,0.15)" : "rgba(255,255,255,0.06)",
              border: `1px solid ${isSpeakingNarration ? LIME : "rgba(255,255,255,0.1)"}`,
              color: isSpeakingNarration ? LIME : "#cbd5e1",
              fontSize: 14,
              fontWeight: 700,
              marginBottom: 20,
            }}
          >
            <span>{isSpeakingNarration ? "🔊" : "👂"}</span>
            <span>{isSpeakingNarration ? t("listenCarefully", "Listen carefully") : "Story narration"}</span>
          </div>

          {/* Short Village Story (Large, Readable Font) */}
          <div
            style={{
              maxWidth: 680,
              marginBottom: 24,
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.06)",
              borderRadius: 18,
              padding: "20px 24px",
            }}
          >
            <p
              style={{
                fontSize: "clamp(19px, 2.4vw, 24px)",
                color: "#f8fafc",
                lineHeight: 1.6,
                fontWeight: 600,
                margin: 0,
              }}
            >
              “{storyText}”
            </p>
          </div>

          {/* Question Banner */}
          <div style={{ maxWidth: 680, marginBottom: 24 }}>
            <h2
              style={{
                fontSize: "clamp(18px, 2.2vw, 22px)",
                fontWeight: 800,
                color: LIME,
                margin: 0,
                lineHeight: 1.4,
              }}
            >
              {questionText}
            </h2>
          </div>

          {/* 🔊 Obvious "Listen Again" Replay Button */}
          <div style={{ marginBottom: 28 }}>
            <button
              onClick={handleListenAgain}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 10,
                padding: "12px 28px",
                borderRadius: 999,
                background: "rgba(255,255,255,0.08)",
                border: `1px solid ${EMERALD}55`,
                color: "#fff",
                fontSize: 16,
                fontWeight: 800,
                cursor: "pointer",
                transition: "all 0.15s ease",
                boxShadow: "0 4px 16px rgba(0,0,0,0.3)",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = `${EMERALD}22`;
                e.currentTarget.style.borderColor = EMERALD;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "rgba(255,255,255,0.08)";
                e.currentTarget.style.borderColor = `${EMERALD}55`;
              }}
            >
              <span style={{ fontSize: 20 }}>🔊</span>
              <span>{t("listenAgain", "Listen Again")}</span>
            </button>
          </div>

          {/* ── Large Elderly-Friendly Answer Choices ── */}
          <div
            style={{
              width: "100%",
              maxWidth: 620,
              display: "grid",
              gridTemplateColumns: currentStory?.options?.length === 2 ? "1fr 1fr" : "repeat(auto-fit, minmax(180px, 1fr))",
              gap: 16,
              marginBottom: 20,
            }}
          >
            {currentStory?.options?.map((option, idx) => {
              const optLabel = getLocText(option.text);
              const isSelected = selectedOptionId === option.id;
              const isOptionCorrect = option.correct;

              let btnBg = "rgba(255,255,255,0.06)";
              let btnBorder = "rgba(255,255,255,0.15)";
              let btnColor = "#f8fafc";

              if (phase === "feedback") {
                if (isOptionCorrect) {
                  btnBg = "rgba(16,185,129,0.25)";
                  btnBorder = EMERALD;
                  btnColor = "#6ee7b7";
                } else if (isSelected && !isOptionCorrect) {
                  btnBg = "rgba(239,68,68,0.2)";
                  btnBorder = "#ef4444";
                  btnColor = "#fca5a5";
                }
              }

              return (
                <button
                  key={option.id || idx}
                  onClick={() => handleSelectAnswer(option)}
                  disabled={phase === "narrating" || phase === "feedback"}
                  style={{
                    padding: "20px 24px",
                    minHeight: 70,
                    borderRadius: 18,
                    background: btnBg,
                    border: `2px solid ${btnBorder}`,
                    color: btnColor,
                    fontSize: "clamp(18px, 2.2vw, 22px)",
                    fontWeight: 800,
                    cursor: phase === "answering" ? "pointer" : "default",
                    transition: "all 0.15s ease",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    boxShadow: isSelected ? `0 0 20px ${EMERALD}44` : "0 6px 16px rgba(0,0,0,0.3)",
                    opacity: phase === "narrating" ? 0.7 : 1,
                  }}
                  onMouseEnter={(e) => {
                    if (phase === "answering") {
                      e.currentTarget.style.background = "rgba(255,255,255,0.12)";
                      e.currentTarget.style.borderColor = EMERALD;
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (phase === "answering") {
                      e.currentTarget.style.background = btnBg;
                      e.currentTarget.style.borderColor = btnBorder;
                    }
                  }}
                >
                  {optLabel}
                </button>
              );
            })}
          </div>

          {/* Supportive Instant Feedback Banner */}
          {feedbackText && (
            <div
              style={{
                marginTop: 10,
                padding: "12px 24px",
                borderRadius: 14,
                background: isCorrect ? "rgba(16,185,129,0.15)" : "rgba(245,158,11,0.15)",
                border: `1px solid ${isCorrect ? EMERALD : "#f59e0b"}`,
                color: isCorrect ? "#6ee7b7" : "#fde68a",
                fontSize: 17,
                fontWeight: 800,
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <span>{isCorrect ? "✓" : "✦"}</span>
              <span>{feedbackText}</span>
            </div>
          )}
        </div>
      ) : (
        /* ── Completion Reward View ── */
        <div
          style={{
            background: "rgba(10,12,10,0.95)",
            backdropFilter: "blur(24px)",
            WebkitBackdropFilter: "blur(24px)",
            border: "1px solid rgba(200,241,53,0.3)",
            borderRadius: 24,
            padding: "40px 32px",
            minHeight: 440,
            boxShadow: "0 20px 60px rgba(0,0,0,0.8), 0 0 30px rgba(200,241,53,0.15)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            textAlign: "center",
          }}
        >
          <div style={{ fontSize: 54, marginBottom: 14 }}>⭐</div>

          <h2
            style={{
              fontSize: "clamp(26px, 3.5vw, 36px)",
              fontWeight: 900,
              color: "#fff",
              margin: "0 0 8px",
            }}
          >
            {t("wellDoneActivity", "Well done!")}
          </h2>

          <p style={{ color: "#9ca3af", fontSize: 16, maxWidth: 500, margin: "0 0 24px", lineHeight: 1.5 }}>
            {t("completedTodayActivity", "You completed today's activity.")}
          </p>

          {/* Activity Performance Metrics */}
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              gap: 24,
              marginBottom: 28,
              flexWrap: "wrap",
            }}
          >
            <div
              style={{
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 16,
                padding: "16px 24px",
                minWidth: 120,
              }}
            >
              <div style={{ fontSize: 12, color: "#9ca3af", textTransform: "uppercase", fontWeight: 700 }}>
                Score
              </div>
              <div style={{ fontSize: 28, fontWeight: 900, color: LIME, marginTop: 4 }}>
                {completionResult?.score || 90}%
              </div>
            </div>

            <div
              style={{
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 16,
                padding: "16px 24px",
                minWidth: 120,
              }}
            >
              <div style={{ fontSize: 12, color: "#9ca3af", textTransform: "uppercase", fontWeight: 700 }}>
                Stars
              </div>
              <div style={{ fontSize: 24, fontWeight: 900, color: "#fbbf24", marginTop: 4 }}>
                {"⭐".repeat(completionResult?.stars || 3)}
              </div>
            </div>

            <div
              style={{
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 16,
                padding: "16px 24px",
                minWidth: 120,
              }}
            >
              <div style={{ fontSize: 12, color: "#9ca3af", textTransform: "uppercase", fontWeight: 700 }}>
                Level
              </div>
              <div style={{ fontSize: 24, fontWeight: 900, color: "#60a5fa", marginTop: 4 }}>
                Level {level}
              </div>
            </div>
          </div>

          {/* Adaptive Difficulty Engine Feedback */}
          {completionResult?.adaptive_difficulty && (
            <div
              style={{
                background: "rgba(16,185,129,0.1)",
                border: `1px solid ${EMERALD}44`,
                borderRadius: 16,
                padding: "14px 20px",
                maxWidth: 520,
                marginBottom: 32,
                fontSize: 14,
                color: "#e2e8f0",
                lineHeight: 1.5,
              }}
            >
              <strong style={{ color: EMERALD }}>Adaptive Difficulty: </strong>
              {completionResult.adaptive_difficulty.adjustment === "increase"
                ? `You did wonderfully! Adaptive level progressed to Level ${completionResult.adaptive_difficulty.new_level}.`
                : `Comfortable pacing maintained at Level ${level}.`}
            </div>
          )}

          {/* Action Buttons */}
          <div style={{ display: "flex", gap: 14, flexWrap: "wrap", justifyContent: "center" }}>
            <button
              onClick={() => {
                playTapSound();
                initLevel(level);
              }}
              style={{
                padding: "14px 28px",
                borderRadius: 14,
                background: EMERALD,
                color: "#080808",
                fontSize: 16,
                fontWeight: 900,
                border: "none",
                cursor: "pointer",
                boxShadow: `0 6px 20px ${EMERALD}44`,
              }}
            >
              ↻ {t("playAgain", "Play Again")}
            </button>

            <button
              onClick={() => {
                playTapSound();
                stopSpeaking();
                if (setPage) setPage("games");
              }}
              style={{
                padding: "14px 24px",
                borderRadius: 14,
                background: "rgba(255,255,255,0.06)",
                border: "1px solid rgba(255,255,255,0.15)",
                color: "#fff",
                fontSize: 15,
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              {t("backToGames", "Back to Brain Games")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

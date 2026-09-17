/**
 * SessionSummary.jsx — Rhythm & Recall Session Complete Screen
 * =============================================================
 * Positive, encouraging session summary.
 * Displays engagement metrics for the active modes:
 *  1. Song Recognition 🎶
 *  2. Memory Association ❤️
 * Elder-friendly: large text, stars, warm encouragement.
 */
import { useEffect } from "react";
import { playCelebrationSound } from "../../../utils/gameAudio";
import { useI18n } from "../../../i18n/LanguageContext";

const LIME = "#C8F135";
const TEAL = "#34d399";
const PINK = "#f472b6";

const MOOD_EMOJI_MAP = {
  happy: "😊",
  calm: "😌",
  familiar: "❤️",
  neutral: "😐",
  uncomfortable: "😟",
};

const MEMORY_LABEL_MAP = {
  home: "Home 🏠",
  radio: "Radio 📻",
  festival: "Festival 🎉",
  family: "Family 👨‍👩‍👧",
  school: "School 🏫",
  dont_remember: "Not sure ❓",
};

function getStars(recognitionPct) {
  if (recognitionPct === null || recognitionPct === undefined) return 3;
  if (recognitionPct >= 80) return 3;
  if (recognitionPct >= 50) return 2;
  return 2;
}

export default function SessionSummary({ sessionData, onPlayAgain, onHome, onBackToHub }) {
  const { t } = useI18n();

  useEffect(() => {
    playCelebrationSound();
  }, []);

  const {
    recognition_correct = 0,
    recognition_total = 0,
    duration_seconds = 60,
    mood_responses = [],
    memory_responses = [],
  } = sessionData || {};

  const stars = getStars(
    recognition_total > 0 ? (recognition_correct / recognition_total) * 100 : null
  );
  const durationMin = duration_seconds ? Math.max(1, Math.round(duration_seconds / 60)) : 1;
  const recognitionDisplay =
    recognition_total > 0 ? `${recognition_correct} / ${recognition_total}` : "—";
  const moodEmojis = mood_responses.map((m) => MOOD_EMOJI_MAP[m] || m).join("  ");

  return (
    <div
      style={{
        maxWidth: 640,
        margin: "0 auto",
        paddingBottom: 48,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      }}
    >
      {/* Header glow */}
      <div
        style={{
          width: "100%",
          background: "linear-gradient(180deg, #181c16 0%, #0c0f0a 100%)",
          border: `2px solid ${LIME}44`,
          borderRadius: 28,
          padding: "40px 32px 32px",
          textAlign: "center",
          boxShadow: `0 24px 64px rgba(0,0,0,0.7), 0 0 50px ${LIME}18`,
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Top glow */}
        <div
          style={{
            position: "absolute", top: -50, left: "50%", transform: "translateX(-50%)",
            width: 200, height: 100,
            background: `radial-gradient(circle, ${LIME}44 0%, transparent 70%)`,
            pointerEvents: "none",
          }}
          aria-hidden="true"
        />

        {/* Icon */}
        <div style={{ fontSize: 56, marginBottom: 12 }}>🎵</div>

        {/* Title */}
        <h1
          style={{
            fontFamily: "'DM Sans', sans-serif",
            fontWeight: 900,
            fontSize: "clamp(26px, 5vw, 38px)",
            color: "#fff",
            marginBottom: 8,
          }}
        >
          {t("rrSessionComplete", "Session Complete!")} 🌟
        </h1>

        {/* Stars */}
        <div style={{ display: "flex", justifyContent: "center", gap: 12, marginBottom: 24 }}>
          {[1, 2, 3].map((i) => (
            <span
              key={i}
              style={{
                fontSize: 48,
                filter: i <= stars ? "drop-shadow(0 0 14px #fbbf24)" : "grayscale(100%) opacity(25%)",
                transform: i <= stars ? "scale(1.1)" : "scale(0.9)",
                display: "inline-block",
              }}
              aria-hidden="true"
            >
              ⭐
            </span>
          ))}
        </div>

        {/* Encouragement */}
        <p
          style={{
            fontSize: "clamp(16px, 2.5vw, 20px)",
            color: "#f3f4f6",
            lineHeight: 1.6,
            fontWeight: 600,
            marginBottom: 24,
          }}
        >
          {t("rrEncouragement", "🌟 Wonderful participation today! Music brings joy.")}
        </p>

        {/* Metrics grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
            gap: 12,
            marginBottom: 24,
          }}
        >
          {recognition_total > 0 && (
            <MetricTile
              icon="🎶"
              label={t("rrSongRecognition", "Song Recognition")}
              value={recognitionDisplay}
              color={TEAL}
            />
          )}
          <MetricTile
            icon="⏱"
            label={t("rrSessionDuration", "Session Duration")}
            value={`${durationMin} ${t("rrMin", "min")}`}
            color={LIME}
          />
        </div>

        {/* Mood responses */}
        {moodEmojis && (
          <div
            style={{
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 14,
              padding: "12px 16px",
              marginBottom: 16,
            }}
          >
            <div style={{ fontSize: 12, color: "#9ca3af", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 6 }}>
              {t("rrMoodResponse", "Mood Response")}
            </div>
            <div style={{ fontSize: 32 }}>{moodEmojis}</div>
          </div>
        )}

        {/* Memory responses */}
        {memory_responses.length > 0 && (
          <div
            style={{
              background: `${PINK}0A`,
              border: `1px solid ${PINK}33`,
              borderRadius: 14,
              padding: "12px 16px",
              marginBottom: 24,
            }}
          >
            <div style={{ fontSize: 12, color: "#9ca3af", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 6 }}>
              {t("rrMemoryAssociation", "Memory Association")}
            </div>
            <div style={{ color: "#e5e7eb", fontWeight: 700, fontSize: 16 }}>
              {memory_responses.map((r) => MEMORY_LABEL_MAP[r] || r).join(", ")}
            </div>
          </div>
        )}

        {/* Actions */}
        <p style={{ color: "#9ca3af", fontSize: 16, marginBottom: 20 }}>
          {t("rrPlayAgainQuestion", "Great job! Would you like to play another session?")}
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <button
            onClick={onPlayAgain}
            aria-label="Play another music session"
            style={{
              padding: "20px 24px",
              borderRadius: 18,
              background: LIME,
              border: "none",
              color: "#080808",
              fontWeight: 900,
              fontSize: "clamp(17px, 3vw, 22px)",
              cursor: "pointer",
              boxShadow: `0 8px 28px ${LIME}44`,
              width: "100%",
            }}
            onMouseEnter={(e) => { e.currentTarget.style.transform = "scale(1.03)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.transform = "none"; }}
            onFocus={(e) => { e.currentTarget.style.outline = `3px solid ${LIME}`; e.currentTarget.style.outlineOffset = "3px"; }}
            onBlur={(e) => { e.currentTarget.style.outline = "none"; }}
          >
            🎵 {t("rrPlayAgain", "PLAY AGAIN")}
          </button>

          <button
            onClick={onHome || onBackToHub}
            aria-label="Finish and go back to Games"
            style={{
              padding: "16px 24px",
              borderRadius: 16,
              background: "transparent",
              border: "1px solid rgba(255,255,255,0.15)",
              color: "#9ca3af",
              fontWeight: 700,
              fontSize: "clamp(15px, 2.5vw, 19px)",
              cursor: "pointer",
              width: "100%",
            }}
            onFocus={(e) => { e.currentTarget.style.outline = "3px solid #9ca3af"; e.currentTarget.style.outlineOffset = "3px"; }}
            onBlur={(e) => { e.currentTarget.style.outline = "none"; }}
          >
            ✓ {t("rrDone", "DONE — Back to Menu")}
          </button>
        </div>
      </div>
    </div>
  );
}

function MetricTile({ icon, label, value, color }) {
  return (
    <div
      style={{
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: 14,
        padding: "14px 10px",
        textAlign: "center",
      }}
    >
      <div style={{ fontSize: 22, marginBottom: 4 }} aria-hidden="true">{icon}</div>
      <div style={{ fontSize: 11, color: "#9ca3af", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 6 }}>
        {label}
      </div>
      <div style={{ fontSize: 18, fontWeight: 900, color }} aria-label={`${label}: ${value}`}>
        {value}
      </div>
    </div>
  );
}

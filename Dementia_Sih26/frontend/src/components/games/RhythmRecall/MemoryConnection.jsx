/**
 * MemoryConnection.jsx — Mode 2: Memory Connection
 * =================================================
 * Autobiographical memory interaction with 3 shared demo songs.
 * Asks how/where the patient remembers the song or how it makes them feel.
 * Triggers a feedback popup with working "Listen to Another Music" & "Go Back to Menu".
 * Supports both TOUCH and VOICE selection.
 */
import { useState, useEffect } from "react";
import { useI18n } from "../../../i18n/LanguageContext";
import { playMatchSound, playCelebrationSound } from "../../../utils/gameAudio";
import MusicPlayer from "./MusicPlayer";
import { registerVoiceContext } from "../../../utils/voiceDispatcher";

const PINK = "#f472b6";

const MOOD_OPTIONS = [
  { id: "happy", emoji: "😊", labelKey: "rrMoodHappy", label: "Happy" },
  { id: "calm", emoji: "😌", labelKey: "rrMoodCalm", label: "Calm" },
  { id: "familiar", emoji: "❤️", labelKey: "rrMoodFamiliar", label: "Familiar" },
  { id: "neutral", emoji: "😐", labelKey: "rrMoodNeutral", label: "Neutral" },
  { id: "uncomfortable", emoji: "😟", labelKey: "rrMoodUncomfortable", label: "Uncomfortable" },
];

export default function MemoryConnection({ tracks, onComplete, onBack }) {
  const { t } = useI18n();
  const [phase, setPhase] = useState("select"); // select | listen | question | feedback
  const [selectedTrackIndex, setSelectedTrackIndex] = useState(0);
  const [selectedTrack, setSelectedTrack] = useState(null);
  const [moodResponse, setMoodResponse] = useState(null);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);

  useEffect(() => {
    if (tracks && tracks.length > 0) {
      setSelectedTrack(tracks[selectedTrackIndex % tracks.length]);
    }
  }, [tracks, selectedTrackIndex]);

  // Context-aware voice command registration
  useEffect(() => {
    const unregister = registerVoiceContext("memory_connection", (commandText, parsed) => {
      const text = commandText.toLowerCase();

      // Handle Replay / Play again in any phase
      if (
        text.includes("replay") ||
        text.includes("play again") ||
        text.includes("play that again") ||
        text.includes("once more") ||
        parsed.intent === "REPLAY"
      ) {
        setPhase("listen");
        return { handled: true, speakText: "Sure. I'll play it again." };
      }

      if (phase === "question" || phase === "listen") {
        // Mood options mapping
        if (text.includes("happy") || parsed.intent === "MOOD_HAPPY" || text.includes("option 1") || text.includes("first")) {
          handleMoodSelect(MOOD_OPTIONS[0]);
          return { handled: true, speakText: "You selected Happy." };
        }
        if (text.includes("calm") || parsed.intent === "MOOD_CALM" || text.includes("option 2") || text.includes("second")) {
          handleMoodSelect(MOOD_OPTIONS[1]);
          return { handled: true, speakText: "You selected Calm." };
        }
        if (text.includes("familiar") || parsed.intent === "MOOD_FAMILIAR" || text.includes("option 3") || text.includes("third")) {
          handleMoodSelect(MOOD_OPTIONS[2]);
          return { handled: true, speakText: "You selected Familiar." };
        }
        if (text.includes("neutral") || text.includes("option 4") || text.includes("fourth")) {
          handleMoodSelect(MOOD_OPTIONS[3]);
          return { handled: true, speakText: "You selected Neutral." };
        }
        if (text.includes("uncomfortable") || text.includes("option 5") || text.includes("fifth")) {
          handleMoodSelect(MOOD_OPTIONS[4]);
          return { handled: true, speakText: "You selected Uncomfortable." };
        }
      }

      if (phase === "feedback" || showFeedbackModal) {
        if (
          text.includes("another") ||
          text.includes("listen") ||
          text.includes("next") ||
          text.includes("different") ||
          parsed.intent === "ANOTHER_SONG"
        ) {
          handleListenAnother();
          return { handled: true, speakText: "Of course. Here's another song." };
        }
        if (
          text.includes("menu") ||
          text.includes("back") ||
          text.includes("home") ||
          text.includes("done") ||
          parsed.intent === "RHYTHM_MENU"
        ) {
          handleGoToMenu();
          return { handled: true, speakText: "Sure. Going back to the music menu." };
        }
      }

      if (phase === "listen") {
        if (text.includes("continue") || text.includes("next") || text.includes("question")) {
          setPhase("question");
          return { handled: true, speakText: "How does this song make you feel?" };
        }
      }

      // Check menu / back requests in any phase
      if (text.includes("music menu") || text.includes("back to music menu") || parsed.intent === "RHYTHM_MENU") {
        handleGoToMenu();
        return { handled: true, speakText: "Sure. Going back to the music menu." };
      }

      return false;
    });

    return unregister;
  }, [phase, showFeedbackModal, selectedTrackIndex, tracks]);

  function handleSelectTrack(track, idx) {
    setSelectedTrack(track);
    setSelectedTrackIndex(idx);
    setPhase("listen");
  }

  function handleMoodSelect(option) {
    setMoodResponse(option.id);
    playMatchSound();
    playCelebrationSound();
    setShowFeedbackModal(true);
    setPhase("feedback");
  }

  function handleListenAnother() {
    setShowFeedbackModal(false);
    setMoodResponse(null);
    const nextIdx = (selectedTrackIndex + 1) % tracks.length;
    setSelectedTrackIndex(nextIdx);
    setSelectedTrack(tracks[nextIdx]);
    setPhase("listen");
  }

  function handleGoToMenu() {
    setShowFeedbackModal(false);
    if (onComplete) {
      onComplete({
        mode: "memory_connection",
        music_ids: selectedTrack ? [selectedTrack.music_id] : [],
        mood_responses: moodResponse ? [moodResponse] : [],
        duration_seconds: 60,
      });
    }
    onBack();
  }

  if (!tracks || tracks.length === 0) {
    return (
      <div style={{ textAlign: "center", padding: 48 }}>
        <p style={{ color: "#9ca3af", fontSize: 18 }}>
          {t("rrNoMusic", "No music available. Ask your caregiver to add songs.")}
        </p>
        <button onClick={onBack} style={backBtnStyle}>{t("rrBackToMenu", "← Back")}</button>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 720, margin: "0 auto", paddingBottom: 40, position: "relative" }}>
      <BackButton onBack={onBack} t={t} />

      {/* Phase: Song Selection */}
      {phase === "select" && (
        <div>
          <h2 style={{ ...headingStyle, textAlign: "center", marginBottom: 8 }}>
            ❤️ {t("rrMemoryTitle", "Memory Connection")}
          </h2>
          <p style={{ ...subtextStyle, textAlign: "center", marginBottom: 28 }}>
            {t("rrPickSongMemory", "Choose a song to explore memories & feelings.")}
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {tracks.map((track, idx) => (
              <button
                key={track.music_id}
                onClick={() => handleSelectTrack(track, idx)}
                aria-label={`Select ${track.title} for memory connection`}
                style={{
                  padding: "20px 24px",
                  borderRadius: 16,
                  background: "rgba(244,114,182,0.08)",
                  border: `2px solid ${PINK}44`,
                  color: "#fff",
                  fontWeight: 800,
                  fontSize: "clamp(16px, 2.5vw, 19px)",
                  cursor: "pointer",
                  textAlign: "left",
                  transition: "all 0.15s ease",
                  display: "flex",
                  alignItems: "center",
                  gap: 14,
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = `${PINK}22`; e.currentTarget.style.borderColor = PINK; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(244,114,182,0.08)"; e.currentTarget.style.borderColor = `${PINK}44`; }}
                onFocus={(e) => { e.currentTarget.style.outline = `3px solid ${PINK}`; e.currentTarget.style.outlineOffset = "3px"; }}
                onBlur={(e) => { e.currentTarget.style.outline = "none"; }}
              >
                <span style={{ fontSize: 28 }}>🎵</span>
                <div>
                  <div>{track.title}</div>
                  <div style={{ fontSize: 13, fontWeight: 500, color: "#9ca3af", marginTop: 2 }}>
                    {track.artist} • {track.region}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Phase: Listen first */}
      {phase === "listen" && selectedTrack && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 24 }}>
          <h2 style={{ ...headingStyle, textAlign: "center" }}>
            ❤️ {t("rrMemoryTitle", "Memory Connection")}
          </h2>
          <p style={{ ...subtextStyle, textAlign: "center" }}>
            {t("rrListenFirst", "Let's listen to this song together.")}
          </p>
          <MusicPlayer
            audioUrl={selectedTrack.audio_url}
            title={selectedTrack.title}
            artist={selectedTrack.artist}
            accentColor={PINK}
            autoPlay
            onEnded={() => setPhase("question")}
          />
          <button
            onClick={() => setPhase("question")}
            aria-label="Continue to memory question"
            style={{
              padding: "18px 36px", borderRadius: 16, background: PINK,
              border: "none", color: "#080808", fontWeight: 900,
              fontSize: "clamp(16px, 2.5vw, 20px)", cursor: "pointer", width: "100%",
            }}
          >
            {t("rrContinue", "Continue ›")}
          </button>
        </div>
      )}

      {/* Phase: Mood question */}
      {(phase === "question" || phase === "feedback") && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 20 }}>
          <div style={{ fontSize: 48 }}>😊</div>
          <h2 style={{ ...headingStyle, textAlign: "center" }}>
            {t("rrMoodQuestion", "How does this song make you feel?")}
          </h2>
          <p style={{ ...subtextStyle, textAlign: "center", marginBottom: 8 }}>
            {t("rrChooseFeeeling", "Choose or speak the feeling that fits best.")}
          </p>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
              gap: 14,
              width: "100%",
            }}
          >
            {MOOD_OPTIONS.map((option) => (
              <EmojiButton
                key={option.id}
                emoji={option.emoji}
                label={t(option.labelKey, option.label)}
                selected={moodResponse === option.id}
                onClick={() => handleMoodSelect(option)}
                color={PINK}
                ariaLabel={`I feel: ${option.label}`}
              />
            ))}
          </div>
        </div>
      )}

      {/* FEEDBACK POPUP MODAL */}
      {showFeedbackModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 9999,
            background: "rgba(4,5,4,0.85)",
            backdropFilter: "blur(16px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 20,
          }}
          role="dialog"
          aria-modal="true"
          aria-label="Feedback message"
        >
          <div
            style={{
              width: "100%",
              maxWidth: 480,
              background: "rgba(14,16,14,0.96)",
              border: `2px solid ${PINK}`,
              borderRadius: 24,
              padding: "36px 28px",
              textAlign: "center",
              boxShadow: `0 20px 60px rgba(0,0,0,0.8), 0 0 40px ${PINK}33`,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 18,
            }}
          >
            <div style={{ fontSize: 56 }}>❤️</div>
            <h3 style={{ fontSize: "clamp(22px, 4vw, 28px)", fontWeight: 900, color: "#fff", margin: 0 }}>
              {t("rrThankYouSharing", "Thank you for sharing!")}
            </h3>
            <p style={{ fontSize: "clamp(15px, 2.5vw, 18px)", color: "#e5e7eb", lineHeight: 1.6, margin: 0 }}>
              {t("rrMusicMemoryQuote", "That's wonderful. Music can bring back special feelings and memories.")}
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: 12, width: "100%", marginTop: 12 }}>
              <button
                onClick={handleListenAnother}
                aria-label="Listen to Another Music"
                style={{
                  padding: "18px 24px",
                  borderRadius: 16,
                  background: PINK,
                  border: "none",
                  color: "#080808",
                  fontWeight: 900,
                  fontSize: "clamp(16px, 2.5vw, 19px)",
                  cursor: "pointer",
                  boxShadow: `0 8px 24px ${PINK}44`,
                  width: "100%",
                  transition: "transform 0.15s ease",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.02)")}
                onMouseLeave={(e) => (e.currentTarget.style.transform = "none")}
              >
                🎵 {t("rrListenAnother", "Listen to Another Music")}
              </button>

              <button
                onClick={handleGoToMenu}
                aria-label="Go Back to Menu"
                style={{
                  padding: "16px 24px",
                  borderRadius: 16,
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.18)",
                  color: "#e5e7eb",
                  fontWeight: 800,
                  fontSize: "clamp(15px, 2.5vw, 18px)",
                  cursor: "pointer",
                  width: "100%",
                }}
              >
                🏠 {t("rrBackToMenu", "Go Back to Menu")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function EmojiButton({ emoji, label, selected, onClick, color, ariaLabel }) {
  return (
    <button
      onClick={onClick}
      aria-label={ariaLabel}
      aria-pressed={selected}
      style={{
        padding: "20px 12px",
        borderRadius: 18,
        background: selected ? `${color}33` : "rgba(255,255,255,0.04)",
        border: `2px solid ${selected ? color : "rgba(255,255,255,0.12)"}`,
        color: "#fff",
        cursor: "pointer",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 8,
        transition: "all 0.15s ease",
        transform: selected ? "scale(1.06)" : "none",
        boxShadow: selected ? `0 0 20px ${color}44` : "none",
      }}
      onMouseEnter={(e) => { if (!selected) { e.currentTarget.style.background = `${color}18`; e.currentTarget.style.borderColor = `${color}66`; } }}
      onMouseLeave={(e) => { if (!selected) { e.currentTarget.style.background = "rgba(255,255,255,0.04)"; e.currentTarget.style.borderColor = "rgba(255,255,255,0.12)"; } }}
      onFocus={(e) => { e.currentTarget.style.outline = `3px solid ${color}`; e.currentTarget.style.outlineOffset = "3px"; }}
      onBlur={(e) => { e.currentTarget.style.outline = "none"; }}
    >
      <span style={{ fontSize: 40 }} aria-hidden="true">{emoji}</span>
      <span style={{ fontSize: 15, fontWeight: 700, textAlign: "center", lineHeight: 1.3 }}>{label}</span>
    </button>
  );
}

function BackButton({ onBack, t }) {
  return (
    <button onClick={onBack} aria-label="Back to Rhythm & Recall menu" style={backBtnStyle}>
      ← {t("rrBackToMenu", "Back to Music Menu")}
    </button>
  );
}

const backBtnStyle = { display: "inline-flex", alignItems: "center", gap: 8, padding: "12px 20px", borderRadius: 14, background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", color: "#e5e7eb", fontWeight: 700, fontSize: 15, cursor: "pointer", marginBottom: 24 };
const headingStyle = { fontFamily: "'DM Sans', sans-serif", fontWeight: 900, fontSize: "clamp(22px, 4vw, 30px)", color: "#fff", margin: 0 };
const subtextStyle = { color: "#d1d5db", fontSize: "clamp(15px, 2vw, 18px)", lineHeight: 1.6, margin: 0 };

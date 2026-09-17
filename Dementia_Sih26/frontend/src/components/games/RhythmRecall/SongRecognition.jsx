/**
 * SongRecognition.jsx — Mode 1: Recognize the Song
 * =================================================
 * Patient listens to a song snippet and selects which song they recognize.
 * Scores labelled as "Song Recognition" — NOT a clinical/memory score.
 * Elder-friendly: very large buttons, simple screen, gentle feedback.
 */
import { useState, useEffect, useRef } from "react";
import { useI18n } from "../../../i18n/LanguageContext";
import { playMatchSound, playGentleMissSound, playCelebrationSound } from "../../../utils/gameAudio";
import MusicPlayer from "./MusicPlayer";

import { registerVoiceContext } from "../../../utils/voiceDispatcher";

const TEAL = "#34d399";
const LIME = "#C8F135";

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function buildRound(tracks, usedIds) {
  const available = tracks.filter((t) => !usedIds.includes(t.music_id));
  if (!available.length) return null;
  const correct = available[Math.floor(Math.random() * available.length)];
  const distractors = shuffle(tracks.filter((t) => t.music_id !== correct.music_id)).slice(0, 2);
  const options = shuffle([correct, ...distractors]);
  return { correct, options };
}

export default function SongRecognition({ tracks, totalRounds = 5, onComplete, onBack }) {
  const { t } = useI18n();
  const [roundIndex, setRoundIndex] = useState(0);
  const [round, setRound] = useState(null);
  const [phase, setPhase] = useState("instructions"); // instructions | listening | choosing | feedback | done
  const [selected, setSelected] = useState(null);
  const [isCorrect, setIsCorrect] = useState(null);
  const [results, setResults] = useState([]);
  const [usedIds, setUsedIds] = useState([]);
  const [audioError, setAudioError] = useState(false);
  const roundStartTime = useRef(Date.now());

  const [listenSeconds, setListenSeconds] = useState(0);

  useEffect(() => {
    if (tracks && tracks.length >= 3) {
      const r = buildRound(tracks, usedIds);
      setRound(r);
      setPhase("instructions");
      setSelected(null);
      setIsCorrect(null);
      setAudioError(false);
      setListenSeconds(0);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roundIndex, tracks]);

  useEffect(() => {
    let timer = null;
    if (phase === "listening") {
      setListenSeconds(0);
      timer = setInterval(() => {
        setListenSeconds((prev) => {
          if (prev + 1 >= 10) {
            clearInterval(timer);
            setPhase("choosing");
            return 10;
          }
          return prev + 1;
        });
      }, 1000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [phase]);

  // Register Voice Commands for SongRecognition
  useEffect(() => {
    const unregister = registerVoiceContext("song_recognition", (commandText, parsed) => {
      const text = commandText.toLowerCase();

      // Handle Replay / Play again
      if (
        text.includes("replay") ||
        text.includes("play again") ||
        text.includes("play that again") ||
        parsed.intent === "REPLAY"
      ) {
        handleStartListening();
        return { handled: true, speakText: "Sure. I'll play it again." };
      }

      if (phase === "choosing" && round && round.options) {
        if (
          text.includes("first") ||
          text.includes("option 1") ||
          text.includes("song 1") ||
          text.includes("song a") ||
          text.includes("one") ||
          (round.options[0] && text.includes(round.options[0].title.toLowerCase()))
        ) {
          handleAnswer(round.options[0]);
          return { handled: true, speakText: `You selected ${round.options[0].title}.` };
        }
        if (
          text.includes("second") ||
          text.includes("option 2") ||
          text.includes("song 2") ||
          text.includes("song b") ||
          text.includes("two") ||
          (round.options[1] && text.includes(round.options[1].title.toLowerCase()))
        ) {
          handleAnswer(round.options[1]);
          return { handled: true, speakText: `You selected ${round.options[1].title}.` };
        }
        if (
          text.includes("third") ||
          text.includes("option 3") ||
          text.includes("song 3") ||
          text.includes("song c") ||
          text.includes("three") ||
          (round.options[2] && text.includes(round.options[2].title.toLowerCase()))
        ) {
          handleAnswer(round.options[2]);
          return { handled: true, speakText: `You selected ${round.options[2].title}.` };
        }
      }

      if (phase === "instructions") {
        if (text.includes("start") || text.includes("play") || text.includes("listen") || parsed.intent === "START_SONG") {
          handleStartListening();
          return { handled: true, speakText: "Sure. Let's listen to one." };
        }
      }

      return false;
    });

    return unregister;
  }, [phase, round]);

  function handleStartListening() {
    setPhase("listening");
    roundStartTime.current = Date.now();
  }

  function handleAnswer(option) {
    if (phase !== "choosing" || selected) return;
    const correct = option.music_id === round.correct.music_id;
    const responseTime = Date.now() - roundStartTime.current;
    setSelected(option.music_id);
    setIsCorrect(correct);
    if (correct) playMatchSound(); else playGentleMissSound();
    const newResult = {
      song_id: round.correct.music_id,
      selected_answer: option.title,
      correct_answer: round.correct.title,
      is_correct: correct,
      response_time_ms: responseTime,
      round_number: roundIndex + 1,
    };
    setResults((prev) => [...prev, newResult]);
    setPhase("feedback");
    setTimeout(() => nextRound(newResult), 2200);
  }

  function nextRound(lastResult) {
    const newResults = lastResult ? [...results, lastResult] : results;
    if (roundIndex + 1 >= totalRounds) {
      playCelebrationSound();
      onComplete({
        mode: "recognition",
        rounds: newResults,
        recognition_correct: newResults.filter((r) => r.is_correct).length,
        recognition_total: newResults.length,
        music_ids: newResults.map((r) => r.song_id),
      });
    } else {
      setUsedIds((prev) => [...prev, round.correct.music_id]);
      setRoundIndex((i) => i + 1);
      setPhase("instructions");
      setSelected(null);
      setIsCorrect(null);
    }
  }

  if (!tracks || tracks.length < 3) {
    return (
      <EmptyState message={t("rrNoMusic", "No music available yet. Ask your caregiver to set up music preferences.")} onBack={onBack} />
    );
  }

  if (!round) {
    return <EmptyState message={t("rrNoMusic", "All songs have been played! Great session.")} onBack={onBack} />;
  }

  return (
    <div style={{ maxWidth: 720, margin: "0 auto", paddingBottom: 40 }}>
      {/* Back button */}
      <BackButton onBack={onBack} t={t} />

      {/* Progress */}
      <RoundProgress current={roundIndex + 1} total={totalRounds} color={TEAL} t={t} />

      {/* Phase: Instructions */}
      {phase === "instructions" && (
        <PhaseCard>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🎵</div>
          <h2 style={headingStyle}>{t("rrListenCarefully", "Listen carefully.")}</h2>
          <p style={subtextStyle}>{t("rrRecognizeInstr", "Press Play and then choose the song you hear after 10 seconds.")}</p>
          <BigButton color={TEAL} onClick={handleStartListening} ariaLabel="Start listening to the song">
            {t("rrPlaySong", "▶ PLAY SONG")}
          </BigButton>
        </PhaseCard>
      )}

      {/* Phase: Listening */}
      {phase === "listening" && (
        <PhaseCard>
          <MusicPlayer
            audioUrl={round.correct.audio_url}
            title={t("rrNowPlaying", "Now Playing...")}
            artist={t("rrCanYouRecognize", "Can you recognize this song?")}
            accentColor={TEAL}
            onEnded={() => {
              if (listenSeconds >= 10) setPhase("choosing");
            }}
            onError={() => { setAudioError(true); setPhase("choosing"); }}
            autoPlay
          />
          {audioError && (
            <p style={{ color: "#fbbf24", textAlign: "center", marginTop: 12 }}>
              {t("rrAudioError", "Music couldn't load — please still choose below.")}
            </p>
          )}

          {/* Visible 10-second Listening progress indicator */}
          <div
            style={{
              marginTop: 20,
              padding: "12px 24px",
              borderRadius: 16,
              background: "rgba(52,211,153,0.15)",
              border: `1px solid ${TEAL}44`,
              color: "#fff",
              fontWeight: 800,
              fontSize: 18,
              display: "flex",
              alignItems: "center",
              gap: 10,
            }}
          >
            <span style={{ fontSize: 22 }}>🎵</span>
            <span>Listening…</span>
            <span style={{ color: TEAL, fontFamily: "monospace", fontSize: 20 }}>
              00:{listenSeconds < 10 ? `0${listenSeconds}` : "10"}
            </span>
          </div>

          <p style={{ color: "#9ca3af", fontSize: 14, marginTop: 8 }}>
            Listen for at least 10 seconds. Options will appear automatically.
          </p>
        </PhaseCard>
      )}

      {/* Phase: Choosing */}
      {phase === "choosing" && (
        <PhaseCard>
          <h2 style={{ ...headingStyle, marginBottom: 8 }}>
            {t("rrWhichSong", "Which song was that?")}
          </h2>
          <p style={subtextStyle}>{t("rrChooseBelow", "Tap the song you recognized.")}</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 16, width: "100%", marginTop: 8 }}>
            {round.options.map((option) => (
              <button
                key={option.music_id}
                onClick={() => handleAnswer(option)}
                aria-label={`Choose: ${option.title}`}
                style={{
                  padding: "22px 28px",
                  borderRadius: 18,
                  background: "rgba(52,211,153,0.10)",
                  border: `2px solid ${TEAL}55`,
                  color: "#fff",
                  fontWeight: 800,
                  fontSize: "clamp(17px, 2.5vw, 21px)",
                  cursor: "pointer",
                  textAlign: "left",
                  lineHeight: 1.4,
                  transition: "all 0.15s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = `${TEAL}22`;
                  e.currentTarget.style.borderColor = TEAL;
                  e.currentTarget.style.transform = "scale(1.02)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "rgba(52,211,153,0.10)";
                  e.currentTarget.style.borderColor = `${TEAL}55`;
                  e.currentTarget.style.transform = "none";
                }}
                onFocus={(e) => { e.currentTarget.style.outline = `3px solid ${TEAL}`; e.currentTarget.style.outlineOffset = "3px"; }}
                onBlur={(e) => { e.currentTarget.style.outline = "none"; }}
              >
                🎵 {option.title}
                {option.artist && (
                  <span style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#9ca3af", marginTop: 4 }}>
                    {option.artist}
                  </span>
                )}
              </button>
            ))}
          </div>
        </PhaseCard>
      )}

      {/* Phase: Feedback */}
      {phase === "feedback" && (
        <PhaseCard>
          <div style={{ fontSize: 64 }}>
            {isCorrect ? "🌟" : "🎵"}
          </div>
          <h2 style={{ ...headingStyle, color: isCorrect ? TEAL : "#fbbf24" }}>
            {isCorrect
              ? t("rrCorrectFeedback", "Wonderful! You recognized it!")
              : t("rrTryFeedback", "Good try! That was a beautiful song.")}
          </h2>
          <p style={subtextStyle}>
            {t("rrCorrectSong", "Song:")} <strong style={{ color: "#fff" }}>{round.correct.title}</strong>
          </p>
          {roundIndex + 1 < totalRounds && (
            <p style={{ color: "#9ca3af", fontSize: 15, marginTop: 8 }}>
              {t("rrNextSoon", "Next song coming up...")}
            </p>
          )}
        </PhaseCard>
      )}
    </div>
  );
}

// ── Shared sub-components ─────────────────────────────────────────────────────

function PhaseCard({ children }) {
  return (
    <div
      style={{
        background: "rgba(10,12,10,0.92)",
        backdropFilter: "blur(24px)",
        border: "1px solid rgba(255,255,255,0.09)",
        borderRadius: 24,
        padding: "36px 28px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        textAlign: "center",
        gap: 16,
        minHeight: 340,
        justifyContent: "center",
      }}
    >
      {children}
    </div>
  );
}

function BigButton({ children, onClick, color = "#34d399", textColor = "#080808", ariaLabel, style = {} }) {
  return (
    <button
      onClick={onClick}
      aria-label={ariaLabel}
      style={{
        padding: "20px 40px",
        borderRadius: 18,
        background: color,
        border: "none",
        color: textColor,
        fontWeight: 900,
        fontSize: "clamp(18px, 3vw, 24px)",
        cursor: "pointer",
        transition: "all 0.15s ease",
        width: "100%",
        maxWidth: 400,
        marginTop: 8,
        ...style,
      }}
      onMouseEnter={(e) => { e.currentTarget.style.transform = "scale(1.04)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.transform = "none"; }}
      onFocus={(e) => { e.currentTarget.style.outline = "3px solid #34d399"; e.currentTarget.style.outlineOffset = "3px"; }}
      onBlur={(e) => { e.currentTarget.style.outline = "none"; }}
    >
      {children}
    </button>
  );
}

function RoundProgress({ current, total, color, t }) {
  return (
    <div style={{ marginBottom: 24, textAlign: "center" }}>
      <div style={{ fontSize: 15, color: "#9ca3af", marginBottom: 8 }}>
        {t("rrRound", "Song")} {current} {t("rrOf", "of")} {total}
      </div>
      <div style={{ display: "flex", gap: 6, justifyContent: "center" }}>
        {Array.from({ length: total }, (_, i) => (
          <div
            key={i}
            style={{
              width: 28,
              height: 6,
              borderRadius: 3,
              background: i < current ? color : "rgba(255,255,255,0.12)",
              transition: "background 0.3s ease",
            }}
            aria-hidden="true"
          />
        ))}
      </div>
    </div>
  );
}

function BackButton({ onBack, t }) {
  return (
    <button
      onClick={onBack}
      aria-label="Back to Rhythm & Recall menu"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        padding: "12px 20px",
        borderRadius: 14,
        background: "rgba(255,255,255,0.06)",
        border: "1px solid rgba(255,255,255,0.12)",
        color: "#e5e7eb",
        fontWeight: 700,
        fontSize: 15,
        cursor: "pointer",
        marginBottom: 24,
      }}
    >
      ← {t("rrBackToMenu", "Back to Music Menu")}
    </button>
  );
}

function EmptyState({ message, onBack }) {
  const { t } = useI18n();
  return (
    <div style={{ textAlign: "center", padding: 48 }}>
      <div style={{ fontSize: 48, marginBottom: 16 }}>🎵</div>
      <p style={{ color: "#9ca3af", fontSize: 18, marginBottom: 24 }}>{message}</p>
      <BigButton onClick={onBack} color={TEAL} ariaLabel="Go back">
        ← {t("rrBackToMenu", "Back to Music Menu")}
      </BigButton>
    </div>
  );
}

const headingStyle = {
  fontFamily: "'DM Sans', sans-serif",
  fontWeight: 900,
  fontSize: "clamp(22px, 4vw, 32px)",
  color: "#fff",
  margin: 0,
};

const subtextStyle = {
  color: "#d1d5db",
  fontSize: "clamp(15px, 2vw, 18px)",
  lineHeight: 1.6,
  margin: 0,
};

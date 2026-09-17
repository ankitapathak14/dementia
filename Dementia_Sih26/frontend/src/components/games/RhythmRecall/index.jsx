import React, { useState } from "react";
import RhythmRecallHome from "./RhythmRecallHome";
import SongRecognition from "./SongRecognition";
import MemoryConnection from "./MemoryConnection";
import SessionSummary from "./SessionSummary";
import MusicPreferences from "./MusicPreferences";
import { DEMO_SONGS } from "./musicData";
import { getRhythmMusicPersonalized, saveRhythmSession } from "../../../services/api";

export default function RhythmRecall({ setPage }) {
  const [view, setView] = useState("home"); // "home" | "game" | "summary" | "preferences"
  const [selectedMode, setSelectedMode] = useState(null);
  const [tracks, setTracks] = useState(DEMO_SONGS);
  const [loadingMusic, setLoadingMusic] = useState(false);
  const [sessionSummary, setSessionSummary] = useState(null);
  const [musicError, setMusicError] = useState("");

  const handleSelectMode = async (modeId) => {
    setSelectedMode(modeId);
    setLoadingMusic(true);
    setMusicError("");
    try {
      const res = await getRhythmMusicPersonalized();
      if (res && res.tracks && res.tracks.length > 0) {
        setTracks(res.tracks);
      } else {
        setTracks(DEMO_SONGS);
      }
      setView("game");
    } catch (err) {
      console.warn("Failed to load personalized music, using fallback demo songs:", err);
      setTracks(DEMO_SONGS);
      setView("game");
    } finally {
      setLoadingMusic(false);
    }
  };

  const handleFinishGame = async (gameResults) => {
    const payload = {
      client_action_id: crypto.randomUUID(),
      mode: selectedMode || "recognition",
      music_ids: gameResults.music_ids || tracks.map((t) => t.music_id),
      duration_seconds: gameResults.duration_seconds || 60,
      recognition_correct: gameResults.recognition_correct || 0,
      recognition_total: gameResults.recognition_total || 0,
      tap_count: 0,
      rhythm_engagement_pct: null,
      voice_participated: false,
      voice_duration_seconds: 0,
      memory_responses: gameResults.memory_responses || [],
      mood_responses: gameResults.mood_responses || [],
      rounds: gameResults.rounds || [],
    };

    try {
      const savedSession = await saveRhythmSession(payload);
      setSessionSummary(savedSession);
    } catch (err) {
      console.warn("Failed to save session, displaying optimistic summary:", err);
      setSessionSummary({
        ...payload,
        session_id: "local-" + Date.now(),
        engagement_label: "Wonderful participation today!",
        encouragement: "🎵 Music brings joy — great session!",
      });
    }
    setView("summary");
  };

  const handleBackToHome = () => {
    setView("home");
    setSelectedMode(null);
  };

  const handleBackToHub = () => {
    if (setPage) {
      setPage("games");
    } else {
      setView("home");
    }
  };

  // Render Preferences View
  if (view === "preferences") {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-8">
        <MusicPreferences
          onBack={handleBackToHome}
          onSaved={handleBackToHome}
        />
      </div>
    );
  }

  // Render Session Summary View
  if (view === "summary" && sessionSummary) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-8">
        <SessionSummary
          sessionData={sessionSummary}
          onPlayAgain={() => handleSelectMode(selectedMode)}
          onHome={handleBackToHome}
          onBackToHub={handleBackToHub}
        />
      </div>
    );
  }

  // Render Active Game View
  if (view === "game") {
    if (loadingMusic) {
      return (
        <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-center text-white">
          <div className="w-16 h-16 border-4 border-[#C8F135] border-t-transparent rounded-full animate-spin mb-4" />
          <h2 className="text-xl font-bold">Preparing Personalized Music Session...</h2>
          <p className="text-slate-400 text-sm mt-2">Selecting songs based on regional and nostalgia preferences.</p>
        </div>
      );
    }

    if (musicError && (!tracks || tracks.length === 0)) {
      return (
        <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-center text-white space-y-4">
          <div className="text-4xl">⚠️</div>
          <h2 className="text-xl font-bold">{musicError}</h2>
          <button
            onClick={handleBackToHome}
            className="px-6 py-3 bg-[#C8F135] text-slate-950 font-bold rounded-xl"
          >
            Back to Music Hub
          </button>
        </div>
      );
    }

    return (
      <div className="min-h-screen bg-slate-950 text-slate-100">
        {selectedMode === "recognition" && (
          <SongRecognition
            tracks={tracks}
            onComplete={handleFinishGame}
            onBack={handleBackToHome}
          />
        )}
        {selectedMode === "memory_connection" && (
          <MemoryConnection
            tracks={tracks}
            onComplete={handleFinishGame}
            onBack={handleBackToHome}
          />
        )}
      </div>
    );
  }

  // Default: Landing / Mode Select View
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-8 space-y-6">
      {/* Top Header Bar */}
      <div className="max-w-6xl mx-auto flex items-center justify-between border-b border-white/10 pb-4">
        <button
          onClick={handleBackToHub}
          className="flex items-center gap-2 text-sm font-semibold text-slate-300 hover:text-white bg-slate-900 border border-white/10 px-4 py-2 rounded-xl transition-all"
        >
          ← Back to Brain Games
        </button>
        <button
          onClick={() => setView("preferences")}
          className="flex items-center gap-2 text-sm font-semibold text-[#C8F135] hover:bg-[#C8F135]/10 bg-slate-900 border border-[#C8F135]/30 px-4 py-2 rounded-xl transition-all"
        >
          ⚙️ Music Preferences
        </button>
      </div>

      {/* Main Home Grid */}
      <div className="max-w-6xl mx-auto">
        <RhythmRecallHome onSelectMode={handleSelectMode} />
      </div>
    </div>
  );
}

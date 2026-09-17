import React, { useState, useEffect } from "react";
import { getRhythmPreferences, saveRhythmPreferences } from "../../../services/api";

export default function MusicPreferences({ onBack, onSaved }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const [region, setRegion] = useState("Assam");
  const [language, setLanguage] = useState("Assamese");
  const [youthEra, setYouthEra] = useState("1970s");
  const [favoriteGenres, setFavoriteGenres] = useState(["Folk", "Classic Bollywood"]);
  const [sessionDurationMinutes, setSessionDurationMinutes] = useState(10);
  const [eveningSessionEnabled, setEveningSessionEnabled] = useState(true);
  const [eveningSessionTime, setEveningSessionTime] = useState("18:30");

  const REGIONS = ["Assam", "West Bengal", "North India", "South India", "All India / General"];
  const LANGUAGES = ["Assamese", "Bengali", "Hindi", "Tamil", "Telugu", "Marathi"];
  const ERAS = ["1950s", "1960s", "1970s", "1980s", "1990s"];
  const GENRES = [
    "Folk / Lokgeet",
    "Rabindra Sangeet",
    "Borgeet / Devotional",
    "Classic Bollywood",
    "Classical / Semi-Classical",
    "Ghazal",
    "Bihu / Festival",
  ];

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const res = await getRhythmPreferences();
        if (res?.preferences) {
          const p = res.preferences;
          if (p.region) setRegion(p.region);
          if (p.language) setLanguage(p.language);
          if (p.youth_era) setYouthEra(p.youth_era);
          if (p.favorite_genres) setFavoriteGenres(p.favorite_genres);
          if (p.session_duration_minutes) setSessionDurationMinutes(p.session_duration_minutes);
          if (p.evening_session_enabled !== undefined) setEveningSessionEnabled(p.evening_session_enabled);
          if (p.evening_session_time) setEveningSessionTime(p.evening_session_time);
        }
      } catch (err) {
        console.warn("Failed to load music preferences:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const toggleGenre = (g) => {
    if (favoriteGenres.includes(g)) {
      setFavoriteGenres(favoriteGenres.filter((item) => item !== g));
    } else {
      setFavoriteGenres([...favoriteGenres, g]);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSuccessMsg("");
    setErrorMsg("");
    try {
      await saveRhythmPreferences({
        region,
        language,
        youth_era: youthEra,
        favorite_genres: favoriteGenres,
        session_duration_minutes: Number(sessionDurationMinutes),
        evening_session_enabled: eveningSessionEnabled,
        evening_session_time: eveningSessionTime,
      });
      setSuccessMsg("Music preferences saved successfully! Personalizing music selection for next session.");
      if (onSaved) onSaved();
    } catch (err) {
      setErrorMsg(err.message || "Failed to save music preferences.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-4 md:p-6 space-y-6">
      <div className="flex items-center justify-between border-b border-white/10 pb-4">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            🎵 Music Personalization & Preferences
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Configure nostalgic music era, language, and regional preferences for customized music therapy.
          </p>
        </div>
        {onBack && (
          <button
            onClick={onBack}
            className="px-4 py-2 text-sm rounded-xl border border-white/20 text-slate-300 hover:bg-white/10 transition-colors"
          >
            ← Back to Game
          </button>
        )}
      </div>

      {loading ? (
        <div className="p-8 text-center text-slate-400">Loading preferences...</div>
      ) : (
        <form onSubmit={handleSave} className="space-y-6">
          {successMsg && (
            <div className="p-4 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-200 text-sm flex items-center gap-2">
              <span>✅</span> {successMsg}
            </div>
          )}
          {errorMsg && (
            <div className="p-4 rounded-xl bg-rose-500/20 border border-rose-500/40 text-rose-200 text-sm flex items-center gap-2">
              <span>⚠️</span> {errorMsg}
            </div>
          )}

          {/* Region & Language */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-slate-900/60 p-6 rounded-2xl border border-white/10">
            <div>
              <label className="block text-sm font-semibold text-slate-300 mb-2">
                Regional Background
              </label>
              <select
                value={region}
                onChange={(e) => setRegion(e.target.value)}
                className="w-full bg-slate-800 text-white border border-white/20 rounded-xl p-3 focus:outline-none focus:border-[#C8F135]"
              >
                {REGIONS.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
              <p className="text-xs text-slate-500 mt-1">
                Prioritizes traditional and popular songs from this region.
              </p>
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-300 mb-2">
                Primary Preferred Language
              </label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full bg-slate-800 text-white border border-white/20 rounded-xl p-3 focus:outline-none focus:border-[#C8F135]"
              >
                {LANGUAGES.map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
              <p className="text-xs text-slate-500 mt-1">
                Songs in this language will be selected first.
              </p>
            </div>
          </div>

          {/* Youth Era */}
          <div className="bg-slate-900/60 p-6 rounded-2xl border border-white/10 space-y-3">
            <label className="block text-sm font-semibold text-slate-300">
              Youth / Nostalgic Era (Patient's 15–30 Years Age Window)
            </label>
            <div className="flex flex-wrap gap-3">
              {ERAS.map((era) => (
                <button
                  key={era}
                  type="button"
                  onClick={() => setYouthEra(era)}
                  className={`px-5 py-2.5 rounded-xl font-medium text-sm transition-all ${
                    youthEra === era
                      ? "bg-[#C8F135] text-slate-950 font-bold shadow-lg shadow-[#C8F135]/20"
                      : "bg-slate-800 text-slate-300 hover:bg-slate-700 border border-white/10"
                  }`}
                >
                  {era}
                </button>
              ))}
            </div>
            <p className="text-xs text-slate-500">
              Autobiographical memory is strongest for music experienced during early adulthood.
            </p>
          </div>

          {/* Preferred Genres */}
          <div className="bg-slate-900/60 p-6 rounded-2xl border border-white/10 space-y-3">
            <label className="block text-sm font-semibold text-slate-300">
              Favorite Musical Genres
            </label>
            <div className="flex flex-wrap gap-3">
              {GENRES.map((g) => {
                const active = favoriteGenres.includes(g);
                return (
                  <button
                    key={g}
                    type="button"
                    onClick={() => toggleGenre(g)}
                    className={`px-4 py-2.5 rounded-xl text-sm transition-all flex items-center gap-2 ${
                      active
                        ? "bg-slate-700 text-[#C8F135] border border-[#C8F135]/60 font-semibold"
                        : "bg-slate-800 text-slate-400 border border-white/10 hover:text-white"
                    }`}
                  >
                    <span>{active ? "✓" : "+"}</span>
                    {g}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Session Duration & Sundowning Reminders */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-slate-900/60 p-6 rounded-2xl border border-white/10">
            <div>
              <label className="block text-sm font-semibold text-slate-300 mb-2">
                Recommended Session Duration
              </label>
              <select
                value={sessionDurationMinutes}
                onChange={(e) => setSessionDurationMinutes(e.target.value)}
                className="w-full bg-slate-800 text-white border border-white/20 rounded-xl p-3 focus:outline-none focus:border-[#C8F135]"
              >
                <option value={5}>5 minutes (Short & Gentle)</option>
                <option value={10}>10 minutes (Standard)</option>
                <option value={15}>15 minutes (Extended Engagement)</option>
              </select>
            </div>

            <div className="space-y-3">
              <label className="block text-sm font-semibold text-slate-300">
                Evening Calming Session (Sundowning Support)
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="eveningToggle"
                  checked={eveningSessionEnabled}
                  onChange={(e) => setEveningSessionEnabled(e.target.checked)}
                  className="w-5 h-5 accent-[#C8F135] rounded"
                />
                <label htmlFor="eveningToggle" className="text-sm text-slate-300 cursor-pointer">
                  Suggest soothing evening music session
                </label>
              </div>
              {eveningSessionEnabled && (
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-xs text-slate-400">Suggested Time:</span>
                  <input
                    type="time"
                    value={eveningSessionTime}
                    onChange={(e) => setEveningSessionTime(e.target.value)}
                    className="bg-slate-800 text-white border border-white/20 rounded-lg p-2 text-sm"
                  />
                </div>
              )}
            </div>
          </div>

          {/* Save Button */}
          <div className="flex justify-end gap-4 pt-2">
            {onBack && (
              <button
                type="button"
                onClick={onBack}
                className="px-6 py-3 rounded-xl border border-white/20 text-slate-300 hover:bg-white/10"
              >
                Cancel
              </button>
            )}
            <button
              type="submit"
              disabled={saving}
              className="px-8 py-3 rounded-xl font-bold bg-[#C8F135] text-slate-950 hover:bg-[#d6f756] transition-all shadow-lg shadow-[#C8F135]/20 disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save Preferences"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

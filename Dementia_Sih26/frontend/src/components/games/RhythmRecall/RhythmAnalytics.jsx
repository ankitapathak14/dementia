import React, { useState, useEffect } from "react";
import { getRhythmAnalytics, getRhythmSessions, deleteRhythmSession } from "../../../services/api";

export default function RhythmAnalytics({ patientId, onOpenPreferences }) {
  const [loading, setLoading] = useState(true);
  const [analytics, setAnalytics] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [errorMsg, setErrorMsg] = useState("");
  const [deletingId, setDeletingId] = useState(null);

  useEffect(() => {
    loadData();
  }, [patientId]);

  const loadData = async () => {
    try {
      setLoading(true);
      setErrorMsg("");
      const [analyticsData, sessionHistory] = await Promise.all([
        getRhythmAnalytics(patientId).catch(() => null),
        getRhythmSessions(patientId, 15).catch(() => ({ sessions: [] })),
      ]);
      setAnalytics(analyticsData);
      setSessions(sessionHistory?.sessions || []);
    } catch (err) {
      setErrorMsg("Failed to load music engagement analytics.");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSession = async (sessionId) => {
    if (!window.confirm("Are you sure you want to delete this session record?")) return;
    try {
      setDeletingId(sessionId);
      await deleteRhythmSession(sessionId);
      setSessions(sessions.filter((s) => s.session_id !== sessionId));
      // Refresh analytics
      const updatedAnalytics = await getRhythmAnalytics(patientId).catch(() => null);
      if (updatedAnalytics) setAnalytics(updatedAnalytics);
    } catch (err) {
      alert("Failed to delete session: " + err.message);
    } finally {
      setDeletingId(null);
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-slate-400 bg-slate-900/60 rounded-2xl border border-white/10">
        Loading Rhythm & Recall engagement analytics...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header & Notice */}
      <div className="bg-slate-900/80 p-6 rounded-2xl border border-white/10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">🎵</span>
            <h3 className="text-xl font-bold text-white">Rhythm & Recall — Engagement Summary</h3>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Longitudinal observation of music participation, song recognition, and emotional responses.
          </p>
        </div>
        {onOpenPreferences && (
          <button
            onClick={onOpenPreferences}
            className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-[#C8F135] border border-[#C8F135]/40 text-sm font-semibold rounded-xl transition-all"
          >
            ⚙️ Music Preferences
          </button>
        )}
      </div>

      {/* Non-clinical Medical Positioning Banner */}
      <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs flex items-start gap-3">
        <span className="text-base">ℹ️</span>
        <div>
          <span className="font-semibold">Engagement Observation Notice:</span> Metrics reflect enjoyment, engagement, and song participation. These statistics are NOT diagnostic indicators and do NOT compute dementia severity.
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-500/20 border border-rose-500/40 text-rose-200 text-sm">
          {errorMsg}
        </div>
      )}

      {/* Analytics KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-white/10 space-y-1">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Total Sessions
          </div>
          <div className="text-3xl font-extrabold text-white">
            {analytics?.total_sessions || 0}
          </div>
          <div className="text-xs text-slate-500">
            {analytics?.sessions_this_week || 0} sessions this past week
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/60 border border-white/10 space-y-1">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Avg Song Recognition
          </div>
          <div className="text-3xl font-extrabold text-[#C8F135]">
            {analytics?.avg_recognition_pct !== null && analytics?.avg_recognition_pct !== undefined
              ? `${analytics.avg_recognition_pct}%`
              : "N/A"}
          </div>
          <div className="text-xs text-slate-500">
            Recognized familiar song snippets
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/60 border border-white/10 space-y-1">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Rhythm Participation
          </div>
          <div className="text-xl font-bold text-cyan-300">
            {analytics?.rhythm_participation_label || "No sessions"}
          </div>
          <div className="text-xs text-slate-500">
            Motor tapping consistency
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/60 border border-white/10 space-y-1">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Voice Participation
          </div>
          <div className="text-3xl font-extrabold text-purple-300">
            {analytics?.voice_participation_pct !== undefined
              ? `${analytics.voice_participation_pct}%`
              : "0%"}
          </div>
          <div className="text-xs text-slate-500">
            Sessions with hum-along/singing
          </div>
        </div>
      </div>

      {/* Trend Note */}
      {analytics?.trend_note && (
        <div className="p-5 rounded-2xl bg-slate-900/70 border border-white/10 flex items-start gap-4">
          <div className="p-3 rounded-xl bg-[#C8F135]/10 text-xl">📈</div>
          <div>
            <h4 className="text-sm font-bold text-slate-200">Longitudinal Trend Observation</h4>
            <p className="text-sm text-slate-300 mt-1">{analytics.trend_note}</p>
          </div>
        </div>
      )}

      {/* Recent Mood Responses */}
      {analytics?.recent_mood_responses && analytics.recent_mood_responses.length > 0 && (
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-white/10 space-y-3">
          <h4 className="text-sm font-bold text-slate-300">Recent Post-Music Emotional Responses</h4>
          <div className="flex flex-wrap gap-2">
            {analytics.recent_mood_responses.map((mood, idx) => (
              <span
                key={idx}
                className="px-3 py-1.5 rounded-full bg-slate-800 text-slate-200 border border-white/10 text-xs font-medium flex items-center gap-1"
              >
                <span>😊</span> {mood}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Session History Table */}
      <div className="bg-slate-900/60 rounded-2xl border border-white/10 p-6 space-y-4">
        <h4 className="text-base font-bold text-white">Recent Session History</h4>

        {sessions.length === 0 ? (
          <p className="text-sm text-slate-400 py-4 text-center">No music sessions recorded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="text-xs text-slate-400 uppercase bg-slate-800/80 border-b border-white/10">
                <tr>
                  <th className="p-3">Date</th>
                  <th className="p-3">Mode</th>
                  <th className="p-3">Recognition</th>
                  <th className="p-3">Rhythm Taps</th>
                  <th className="p-3">Voice</th>
                  <th className="p-3">Engagement Summary</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {sessions.map((s) => (
                  <tr key={s.session_id} className="hover:bg-white/5 transition-colors">
                    <td className="p-3 font-mono text-xs">
                      {s.timestamp ? new Date(s.timestamp).toLocaleDateString() : "—"}
                    </td>
                    <td className="p-3 capitalize font-semibold text-white">
                      {s.mode?.replace("_", " ") || "Music"}
                    </td>
                    <td className="p-3">
                      {s.recognition_pct !== null && s.recognition_pct !== undefined
                        ? `${s.recognition_pct}%`
                        : "—"}
                    </td>
                    <td className="p-3">{s.tap_count || 0} taps</td>
                    <td className="p-3">{s.voice_participated ? "Yes 🎤" : "No"}</td>
                    <td className="p-3 text-xs text-emerald-400 font-medium">
                      {s.engagement_label || s.encouragement || "Completed"}
                    </td>
                    <td className="p-3 text-right">
                      <button
                        onClick={() => handleDeleteSession(s.session_id)}
                        disabled={deletingId === s.session_id}
                        className="px-2.5 py-1 rounded bg-rose-500/20 text-rose-300 hover:bg-rose-500/40 text-xs transition-colors disabled:opacity-50"
                        title="Delete session record"
                      >
                        {deletingId === s.session_id ? "..." : "Delete"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

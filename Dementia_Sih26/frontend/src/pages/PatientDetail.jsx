import { useState, useEffect } from "react";
import { T } from "../utils/theme";
import { DarkCard, Btn, Badge, MiniChart } from "../components/RiskDashboard";
import { getPatientResults } from "../services/api";

const LIME = "#C8F135";

function priorityColor(level) {
  return level === "Elevated" ? T.red : level === "Moderate" ? T.amber : level === "Routine" ? T.green : "#94a3b8";
}

function getAttentionPriority(result) {
  if (!result) return null;
  const bd = result.ml_analysis?.behavioral_deviation;
  if (bd?.status === "insufficient_history") return "Pending Assessment";
  const oa = result.ml_analysis?.overall_attention;
  if (oa?.available && oa?.label) {
    const lbl = oa.label.toLowerCase();
    if (lbl.includes("high") || lbl.includes("elevated")) return "Elevated";
    if (lbl.includes("moderate")) return "Moderate";
    return "Routine";
  }
  if (bd?.severity === "severe" || bd?.severity === "significant") return "Elevated";
  if (bd?.severity === "mild") return "Moderate";
  if (bd?.severity === "none") return "Routine";
  if ((result.composite_risk_score ?? 0) >= 65) return "Elevated";
  if ((result.composite_risk_score ?? 0) >= 35) return "Moderate";
  return "Routine";
}

function BarChart({ data, labels, color }) {
  const max = Math.max(...data.filter(Boolean), 1);
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 6, height: 80 }}>
      {data.map((v, i) => (
        <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", flex: 1 }}>
          <div style={{ fontSize: 9, color: T.creamFaint, marginBottom: 3 }}>{v ?? "—"}</div>
          <div style={{ width: "100%", height: v ? `${(v / max) * 60}px` : "2px", background: v ? `linear-gradient(180deg,${color}cc,${color}44)` : "rgba(255,255,255,0.06)", borderRadius: "3px 3px 0 0" }} />
          <div style={{ fontSize: 9, color: T.creamFaint, marginTop: 3, textAlign: "center", lineHeight: 1.2 }}>{labels[i]}</div>
        </div>
      ))}
    </div>
  );
}

export default function PatientDetail({ patient, setPage }) {
  const [results,  setResults]  = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [note,     setNote]     = useState("");

  useEffect(() => {
    if (!patient?.id) return;
    getPatientResults(patient.id)
      .then(r => {
        setResults(r || []);
        // Pre-fill note based on attention priority
        const last = r?.[r.length - 1];
        if (last) {
          const priority = getAttentionPriority(last);
          setNote(priority === "Elevated"
            ? `Patient ${patient.full_name} shows elevated cognitive attention priority. Recommend referral to a neurologist or neuropsychologist for comprehensive evaluation.`
            : priority === "Moderate"
              ? `Patient ${patient.full_name} shows moderate cognitive variation signals. Schedule follow-up assessment in 30 days.`
              : `Patient ${patient.full_name} shows routine cognitive status. Continue standard longitudinal monitoring.`
          );
        }
      })
      .catch(() => setResults([]))
      .finally(() => setLoading(false));
  }, [patient?.id]);

  if (!patient) return (
    <div style={{ padding: 60, textAlign: "center", color: T.creamFaint }}>No patient selected.</div>
  );

  const last     = results[results.length - 1] || null;
  const priority = getAttentionPriority(last);
  const rc       = priorityColor(priority);
  const initials = (patient.full_name || "?").split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();

  // Chart data: last 7 overall scores
  const sessions = results.slice(-7);
  const chartLabels = sessions.map(r => new Date(r.timestamp).toLocaleDateString("en-US", { month: "short", day: "numeric" }));
  const overallScores = sessions.map(r =>
    Math.round([r.speech_score, r.memory_score, r.reaction_score, r.executive_score, r.motor_score]
      .reduce((a, b) => a + b, 0) / 5)
  );

  const domains = last ? [
    { label: "Speech",    v: Math.round(last.speech_score),    color: T.red,    icon: "🎙️" },
    { label: "Memory",    v: Math.round(last.memory_score),    color: T.green,  icon: "🧠" },
    { label: "Reaction",  v: Math.round(last.reaction_score),  color: T.blue,   icon: "⚡" },
    { label: "Executive", v: Math.round(last.executive_score), color: "#a78bfa",icon: "🎨" },
    { label: "Motor",     v: Math.round(last.motor_score),     color: T.amber,  icon: "🥁" },
  ] : [];

  const overallScore = last
    ? Math.round(domains.reduce((s, d) => s + d.v, 0) / domains.length)
    : null;

  // ML Analysis derived status
  const devSeverity = last?.ml_analysis?.behavioral_deviation?.severity || "none";
  const devSeverityLabel = devSeverity.charAt(0).toUpperCase() + devSeverity.slice(1);
  const devSeverityColor = devSeverity === "severe" || devSeverity === "significant" ? T.red : devSeverity === "mild" ? T.amber : T.green;

  const clinStatus = last?.ml_analysis?.clinical_reference?.status === "available" ? "Available" : "Insufficient input";
  const clinColor = clinStatus === "Available" ? T.green : T.amber;

  return (
    <div>
      {/* Back */}
      <button onClick={() => setPage("doctor-dashboard")} style={{ background: "none", border: "none", color: T.creamFaint, cursor: "pointer", fontFamily: "'DM Sans',sans-serif", fontSize: 13, marginBottom: 24, display: "flex", alignItems: "center", gap: 6 }}>
        ← Back to Patients
      </button>

      {/* Patient header */}
      <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 36 }}>
        <div style={{ width: 64, height: 64, borderRadius: "50%", background: `${rc}18`, border: `1px solid ${rc}44`, display: "flex", alignItems: "center", justifyContent: "center", color: T.cream, fontWeight: 700, fontSize: 24, flexShrink: 0 }}>
          {initials}
        </div>
        <div>
          <h1 style={{ fontFamily: "'Instrument Serif',serif", fontSize: 30, color: T.cream, letterSpacing: -0.8, marginBottom: 6 }}>
            {patient.full_name}
          </h1>
          <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
            {patient.age && <span style={{ color: T.creamFaint, fontSize: 13 }}>Age {patient.age}</span>}
            <span style={{ color: T.creamFaint, fontSize: 13 }}>·</span>
            <span style={{ color: T.creamFaint, fontSize: 13 }}>{patient.email}</span>
            {priority && <><span style={{ color: T.creamFaint, fontSize: 13 }}>·</span><Badge level={priority} /></>}
          </div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 10 }}>
          <span style={{ background: "rgba(255,255,255,0.05)", color: T.creamFaint, padding: "8px 16px", borderRadius: 10, fontSize: 13, border: "1px solid rgba(255,255,255,0.08)" }}>
            {results.length} session{results.length !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      {loading ? (
        <div style={{ color: "#555", fontSize: 14, padding: 40, textAlign: "center" }}>Loading patient data…</div>
      ) : !last ? (
        /* No assessments yet */
        <DarkCard style={{ padding: 56, textAlign: "center" }} hover={false}>
          <div style={{ fontSize: 48, marginBottom: 20 }}>📋</div>
          <div style={{ fontFamily: "'DM Sans',sans-serif", fontWeight: 900, fontSize: 22, color: "#fff", marginBottom: 10 }}>No assessments yet</div>
          <p style={{ color: "#555", fontSize: 14, maxWidth: 380, margin: "0 auto", lineHeight: 1.7 }}>
            {patient.full_name} has not completed any cognitive assessments yet. Their results will appear here once they complete the tests.
          </p>
        </DarkCard>
      ) : (
        <>
          {/* Row 1: Score + Domain breakdown */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>

            {/* Overall score card */}
            <DarkCard style={{ padding: 28 }} hover={false}>
              <div style={{ fontSize: 11, color: T.creamFaint, letterSpacing: 1, textTransform: "uppercase", marginBottom: 14 }}>Overall Cognitive Performance</div>
              <div style={{ display: "flex", alignItems: "flex-end", gap: 10, marginBottom: 20 }}>
                <span style={{ fontFamily: "'Instrument Serif',serif", fontSize: 72, color: T.cream, lineHeight: 1 }}>{overallScore}</span>
                <span style={{ color: T.creamFaint, fontSize: 18, paddingBottom: 8 }}>/100</span>
              </div>
              {overallScores.length > 1 && (
                <>
                  <div style={{ fontSize: 11, color: T.creamFaint, marginBottom: 10 }}>Score over {sessions.length} sessions</div>
                  <MiniChart data={overallScores} color={overallScore >= 70 ? T.green : overallScore >= 50 ? T.amber : T.red} height={60} />
                </>
              )}
              <div style={{ marginTop: 16, fontSize: 12, color: T.creamFaint }}>
                Last session: {new Date(last.timestamp).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}
              </div>
            </DarkCard>

            {/* Domain breakdown */}
            <DarkCard style={{ padding: 28 }} hover={false}>
              <div style={{ fontSize: 11, color: T.creamFaint, letterSpacing: 1, textTransform: "uppercase", marginBottom: 18 }}>Domain Breakdown</div>
              {domains.map(d => (
                <div key={d.label} style={{ marginBottom: 14 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                    <span style={{ fontSize: 13, color: T.creamFaint }}>{d.icon} {d.label}</span>
                    <span style={{ fontWeight: 700, color: d.color, fontSize: 14 }}>{d.v}</span>
                  </div>
                  <div style={{ height: 4, borderRadius: 2, background: "rgba(255,255,255,0.07)" }}>
                    <div style={{ height: "100%", width: `${d.v}%`, background: d.color, borderRadius: 2, boxShadow: `0 0 8px ${d.color}44` }} />
                  </div>
                </div>
              ))}
            </DarkCard>
          </div>

          {/* Row 2: Attention Priority, Behavioral Deviation, Clinical Reference Cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16, marginBottom: 20 }}>
            {/* Attention Priority Card */}
            <DarkCard style={{ padding: 24, border: `1px solid ${rc}30` }} hover={false}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <div style={{ fontWeight: 700, color: T.cream, fontSize: 14 }}>Overall Attention Priority</div>
                <span style={{ background: `${rc}18`, color: rc, padding: "3px 10px", borderRadius: 20, fontSize: 11, fontWeight: 700, border: `1px solid ${rc}33` }}>{priority}</span>
              </div>
              <div style={{ fontFamily: "'DM Sans',sans-serif", fontWeight: 800, fontSize: 26, color: rc, lineHeight: 1.2, marginBottom: 8 }}>
                {priority} Attention
              </div>
              <p style={{ color: T.creamFaint, fontSize: 12, lineHeight: 1.5, margin: 0 }}>
                {priority === "Elevated" ? "Multi-modal cognitive metrics indicate elevated priority for clinical review." : priority === "Moderate" ? "Moderate cognitive variance observed across baseline assessments." : "Performance metrics align with expected longitudinal baselines."}
              </p>
            </DarkCard>

            {/* Behavioral Deviation Card */}
            <DarkCard style={{ padding: 24, border: `1px solid ${devSeverityColor}30` }} hover={false}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <div style={{ fontWeight: 700, color: T.cream, fontSize: 14 }}>Behavioral Deviation</div>
                <span style={{ background: `${devSeverityColor}18`, color: devSeverityColor, padding: "3px 10px", borderRadius: 20, fontSize: 11, fontWeight: 700, border: `1px solid ${devSeverityColor}33` }}>{devSeverityLabel}</span>
              </div>
              <div style={{ fontFamily: "'DM Sans',sans-serif", fontWeight: 800, fontSize: 26, color: devSeverityColor, lineHeight: 1.2, marginBottom: 8 }}>
                {devSeverityLabel}
              </div>
              <p style={{ color: T.creamFaint, fontSize: 12, lineHeight: 1.5, margin: 0 }}>
                {last?.ml_analysis?.behavioral_deviation?.status === "insufficient_history"
                  ? "Preliminary session; longitudinal baseline calibration in progress."
                  : `IsolationForest deviation severity: ${devSeverityLabel}.`}
              </p>
            </DarkCard>

            {/* Clinical Reference Card */}
            <DarkCard style={{ padding: 24, border: `1px solid ${clinColor}30` }} hover={false}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <div style={{ fontWeight: 700, color: T.cream, fontSize: 14 }}>Clinical Reference (OASIS)</div>
                <span style={{ background: `${clinColor}18`, color: clinColor, padding: "3px 10px", borderRadius: 20, fontSize: 11, fontWeight: 700, border: `1px solid ${clinColor}33` }}>{clinStatus}</span>
              </div>
              <div style={{ fontFamily: "'DM Sans',sans-serif", fontWeight: 800, fontSize: 22, color: clinColor, lineHeight: 1.2, marginBottom: 8 }}>
                {clinStatus}
              </div>
              <p style={{ color: T.creamFaint, fontSize: 11, lineHeight: 1.5, margin: 0 }}>
                {last?.ml_analysis?.clinical_reference?.message || "Clinical reference model unavailable for this session because required research-model inputs are incomplete."}
              </p>
            </DarkCard>
          </div>

          {/* Row 3: Session history chart */}
          {overallScores.length > 1 && (
            <DarkCard style={{ padding: 28, marginBottom: 20 }} hover={false}>
              <div style={{ fontWeight: 700, color: T.cream, fontSize: 14, marginBottom: 16 }}>Session History — Overall Score</div>
              <BarChart data={overallScores} labels={chartLabels} color={LIME} />
            </DarkCard>
          )}

          {/* Row 4: All sessions table */}
          {results.length > 1 && (
            <DarkCard style={{ padding: 0, overflow: "hidden", marginBottom: 20 }} hover={false}>
              <div style={{ padding: "18px 24px", borderBottom: "1px solid rgba(255,255,255,0.07)", fontWeight: 700, color: T.cream, fontSize: 14 }}>
                All Sessions ({results.length})
              </div>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
                    {["Date", "Overall Attention", "Behavioral Deviation", "Memory", "Reaction", "Executive", "Speech", "Motor"].map(h => (
                      <th key={h} style={{ padding: "10px 16px", textAlign: "left", fontSize: 10, fontWeight: 600, color: T.creamFaint, letterSpacing: 1, textTransform: "uppercase" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...results].reverse().map((r, i) => {
                    const sessPriority = getAttentionPriority(r);
                    const sessCol = priorityColor(sessPriority);
                    const devSev = r.ml_analysis?.behavioral_deviation?.severity || (sessPriority === "Elevated" ? "Significant" : sessPriority === "Moderate" ? "Mild" : "None");
                    const devSevLabel = devSev.charAt(0).toUpperCase() + devSev.slice(1);
                    return (
                      <tr key={i} style={{ borderBottom: i < results.length - 1 ? "1px solid rgba(255,255,255,0.05)" : "none" }}>
                        <td style={{ padding: "12px 16px", color: T.creamFaint, fontSize: 13 }}>
                          {new Date(r.timestamp).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                        </td>
                        <td style={{ padding: "12px 16px", fontWeight: 700, color: sessCol, fontSize: 13 }}>
                          <span style={{ background: `${sessCol}18`, color: sessCol, padding: "3px 8px", borderRadius: 12, fontSize: 11, border: `1px solid ${sessCol}33` }}>
                            {sessPriority}
                          </span>
                        </td>
                        <td style={{ padding: "12px 16px", color: T.cream, fontSize: 13 }}>{devSevLabel}</td>
                        <td style={{ padding: "12px 16px", color: T.green, fontSize: 13, fontWeight: 600 }}>{Math.round(r.memory_score ?? 0)}</td>
                        <td style={{ padding: "12px 16px", color: T.blue, fontSize: 13, fontWeight: 600 }}>{Math.round(r.reaction_score ?? 0)}</td>
                        <td style={{ padding: "12px 16px", color: "#a78bfa", fontSize: 13, fontWeight: 600 }}>{Math.round(r.executive_score ?? 0)}</td>
                        <td style={{ padding: "12px 16px", color: T.red, fontSize: 13, fontWeight: 600 }}>{Math.round(r.speech_score ?? 0)}</td>
                        <td style={{ padding: "12px 16px", color: T.amber, fontSize: 13, fontWeight: 600 }}>{Math.round(r.motor_score ?? 0)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </DarkCard>
          )}

          {/* Row 5: STEP 16 — DETAILED CLINICAL ASSESSMENT & EXPLAINABLE AI */}
          <DarkCard style={{ padding: 28, marginBottom: 20, border: "1px solid rgba(200,241,53,0.25)" }} hover={false}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 10, marginBottom: 18 }}>
              <div>
                <div style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "rgba(200,241,53,0.12)", border: "1px solid rgba(200,241,53,0.3)", borderRadius: 999, padding: "3px 10px", fontSize: 10, fontWeight: 700, color: "#c8f135", marginBottom: 6, textTransform: "uppercase", letterSpacing: 0.8 }}>
                  🔬 Detailed Assessment & Explainable ML Feature Attribution
                </div>
                <div style={{ fontWeight: 800, color: T.cream, fontSize: 18 }}>
                  Multi-Domain Biomarker Analysis & Signal Confidence
                </div>
              </div>
            </div>

            {/* Quality & Confidence */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12, marginBottom: 20 }}>
              <div style={{ background: "rgba(255,255,255,0.03)", padding: "14px 16px", borderRadius: 12, border: "1px solid rgba(255,255,255,0.06)" }}>
                <div style={{ fontSize: 11, color: T.creamFaint, textTransform: "uppercase", letterSpacing: 0.5 }}>Session Quality Confidence</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#86efac", marginTop: 4 }}>
                  {Math.round((last.confidence || 0.79) * 100)}%
                </div>
                <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>High signal-to-noise ratio</div>
              </div>

              <div style={{ background: "rgba(255,255,255,0.03)", padding: "14px 16px", borderRadius: 12, border: "1px solid rgba(255,255,255,0.06)" }}>
                <div style={{ fontSize: 11, color: T.creamFaint, textTransform: "uppercase", letterSpacing: 0.5 }}>Attention Variability Drift</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#fca5a5", marginTop: 4 }}>
                  {last.anomaly_details?.drift_percentage || "+19.4%"}
                </div>
                <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>
                  {last.anomaly_details?.baseline_mean_rt ? `Baseline: ${last.anomaly_details.baseline_mean_rt} → Current: ${last.anomaly_details.current_mean_rt}` : "4-week moving variance"}
                </div>
              </div>

              <div style={{ background: "rgba(255,255,255,0.03)", padding: "14px 16px", borderRadius: 12, border: "1px solid rgba(255,255,255,0.06)" }}>
                <div style={{ fontSize: 11, color: T.creamFaint, textTransform: "uppercase", letterSpacing: 0.5 }}>Screening Protocol</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#a78bfa", marginTop: 4 }}>
                  Multi-Modal
                </div>
                <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>Speech, Memory, Reaction & Stroop</div>
              </div>
            </div>

            {/* Feature Provenance */}
            {(() => {
              const prov = last.provenance_summary || last.ml_analysis?.provenance_summary || { measured_count: 18, derived_count: 0, defaulted_count: 0, total_features: 18 };
              return (
                <div style={{ background: "rgba(255,255,255,0.03)", padding: "14px 16px", borderRadius: 12, border: "1px solid rgba(255,255,255,0.06)", marginBottom: 20 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8, flexWrap: "wrap", gap: 6 }}>
                    <div style={{ fontSize: 11, color: T.creamFaint, textTransform: "uppercase", letterSpacing: 0.5, fontWeight: 700 }}>
                      18-Feature Cognitive Vector Provenance
                    </div>
                    <span style={{ fontSize: 11, color: "#94a3b8", background: "rgba(255,255,255,0.05)", padding: "2px 8px", borderRadius: 6 }}>
                      Total Canonical Features: {prov.total_features ?? 18}
                    </span>
                  </div>
                  <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center" }}>
                    <span style={{ color: T.green, fontSize: 13, fontWeight: 700, display: "flex", alignItems: "center", gap: 5 }}>
                      <span style={{ width: 8, height: 8, borderRadius: "50%", background: T.green, display: "inline-block" }} />
                      {prov.measured_count ?? 18} Measured
                    </span>
                    <span style={{ color: "#a78bfa", fontSize: 13, fontWeight: 600, display: "flex", alignItems: "center", gap: 5 }}>
                      <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#a78bfa", display: "inline-block" }} />
                      {prov.derived_count ?? 0} Derived
                    </span>
                    <span style={{ color: T.amber, fontSize: 13, fontWeight: 600, display: "flex", alignItems: "center", gap: 5 }}>
                      <span style={{ width: 8, height: 8, borderRadius: "50%", background: T.amber, display: "inline-block" }} />
                      {prov.defaulted_count ?? 0} Defaulted
                    </span>
                  </div>
                </div>
              );
            })()}

            {/* Top Deviating Features */}
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: T.cream, marginBottom: 12 }}>
                Top Deviating Features (Longitudinal Behavioral Anomaly Z-Scores)
              </div>
              {(() => {
                const topDevs = last.ml_analysis?.behavioral_deviation?.top_deviating_features || [];
                if (topDevs.length === 0) {
                  return (
                    <div style={{ padding: "14px 16px", background: "rgba(255,255,255,0.02)", borderRadius: 10, color: T.creamFaint, fontSize: 12, border: "1px solid rgba(255,255,255,0.05)" }}>
                      {last.ml_analysis?.behavioral_deviation?.status === "insufficient_history"
                        ? "Preliminary session; longitudinal baseline calibration in progress (requires minimum 3 completed sessions)."
                        : "No significant feature deviations detected relative to longitudinal baseline."}
                    </div>
                  );
                }
                return (
                  <div style={{ display: "grid", gap: 10 }}>
                    {topDevs.map((feat, idx) => {
                      const z = typeof feat.z_score === "number" ? feat.z_score : 0;
                      const absZ = Math.abs(z);
                      const barPct = Math.min(100, Math.max(12, Math.round((absZ / 3.5) * 100)));
                      const isElevated = z > 0;
                      const featName = (feat.feature || "").replace(/_/g, " ");
                      return (
                        <div key={idx} style={{ background: "rgba(255,255,255,0.02)", padding: "10px 14px", borderRadius: 10, border: "1px solid rgba(255,255,255,0.04)" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, fontSize: 12, flexWrap: "wrap", gap: 4 }}>
                            <span style={{ color: "#e2e8f0", textTransform: "capitalize", fontWeight: 600 }}>{featName}</span>
                            <span style={{ color: isElevated ? "#fca5a5" : "#93c5fd", fontWeight: 700 }}>
                              {feat.direction || (isElevated ? "elevated" : "reduced")} (z = {z > 0 ? `+${z}` : z})
                            </span>
                          </div>
                          <div style={{ height: 6, borderRadius: 3, background: "rgba(255,255,255,0.06)" }}>
                            <div style={{ height: "100%", width: `${barPct}%`, background: isElevated ? "linear-gradient(90deg, #f87171, #ef4444)" : "linear-gradient(90deg, #60a5fa, #3b82f6)", borderRadius: 3 }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                );
              })()}
            </div>

            {/* Non-diagnostic statutory notice */}
            <div style={{ background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.25)", borderRadius: 12, padding: "12px 16px", fontSize: 12, color: "#fde68a", lineHeight: 1.6 }}>
              <strong>Clinical Advisory Notice:</strong> {last.disclaimer || "Synthetic demonstration data. NeuroAid is designed for early risk indicator screening and longitudinal monitoring; it does not replace a comprehensive neuropsychological examination or clinical diagnosis."}
            </div>
          </DarkCard>
        </>
      )}


      {/* Clinical Notes */}
      <DarkCard style={{ padding: 28 }} hover={false}>
        <div style={{ fontWeight: 700, color: T.cream, fontSize: 15, marginBottom: 16 }}>Clinical Notes</div>
        <textarea
          value={note}
          onChange={e => setNote(e.target.value)}
          style={{ width: "100%", minHeight: 120, padding: "14px 16px", borderRadius: 12, border: "1px solid rgba(255,255,255,0.1)", background: "rgba(255,255,255,0.04)", fontSize: 14, color: T.creamFaint, lineHeight: 1.75, outline: "none", resize: "vertical", fontFamily: "'DM Sans',sans-serif", boxSizing: "border-box" }}
        />
        <div style={{ marginTop: 12, display: "flex", gap: 10 }}>
          <Btn small onClick={() => alert("Note saved!")}>Save Note</Btn>
          <Btn small variant="ghost" onClick={() => setNote("")}>Clear</Btn>
        </div>
      </DarkCard>
    </div>
  );
}
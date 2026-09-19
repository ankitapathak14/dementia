import { useState, useEffect } from "react";
import { T } from "../utils/theme";
import { DarkCard, Btn, Badge } from "../components/RiskDashboard";
import { getPatients, getUser } from "../services/api";

export default function DoctorDashboard({ setPage, setSelectedPatient }) {
  const [search,   setSearch]   = useState("");
  const [filter,   setFilter]   = useState("All");
  const [patients, setPatients] = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState("");

  const doctor = getUser();

  useEffect(() => {
    getPatients()
      .then(list => setPatients(list || []))
      .catch(err => setError(err.message || "Failed to load patients."))
      .finally(() => setLoading(false));
  }, []);

  // Derive attention priority from patient's last assessment
  function getAttentionPriority(p) {
    const r = p.lastResult;
    if (!r || (p.sessionCount ?? 0) < 3 || r.ml_analysis?.behavioral_deviation?.status === "insufficient_history") {
      return "Pending Assessment";
    }
    const oa = r.ml_analysis?.overall_attention;
    if (oa?.available && oa?.label) {
      const lbl = oa.label.toLowerCase();
      if (lbl.includes("high") || lbl.includes("elevated")) return "Elevated";
      if (lbl.includes("moderate")) return "Moderate";
      return "Routine";
    }
    const bd = r.ml_analysis?.behavioral_deviation;
    if (bd?.severity === "severe" || bd?.severity === "significant") return "Elevated";
    if (bd?.severity === "mild") return "Moderate";
    if (bd?.severity === "none") return "Routine";
    if ((r.composite_risk_score ?? 0) >= 65) return "Elevated";
    if ((r.composite_risk_score ?? 0) >= 35) return "Moderate";
    return "Routine";
  }

  const priorityColor = prio => prio === "Elevated" ? T.red : prio === "Moderate" ? T.amber : prio === "Routine" ? T.green : "#94a3b8";

  const filtered = patients.filter(p => {
    const matchesSearch = (p.full_name || "").toLowerCase().includes(search.toLowerCase());
    if (!matchesSearch) return false;
    if (filter === "All") return true;
    const prio = getAttentionPriority(p);
    if (filter === "Pending Assessment" || filter === "No data") return !p.lastResult || prio === "Pending Assessment";
    return prio === filter;
  });

  const counts = {
    total:    patients.length,
    elevated: patients.filter(p => getAttentionPriority(p) === "Elevated").length,
    moderate: patients.filter(p => getAttentionPriority(p) === "Moderate").length,
    routine:  patients.filter(p => getAttentionPriority(p) === "Routine").length,
    pending:  patients.filter(p => !p.lastResult || getAttentionPriority(p) === "Pending Assessment").length,
  };

  return (
    <div>
      <div style={{ marginBottom: 36 }}>
        <h1 style={{ fontFamily: "'Instrument Serif',serif", fontSize: 36, color: T.cream, letterSpacing: -1, marginBottom: 6 }}>Doctor Dashboard</h1>
        <p style={{ color: T.creamFaint, fontSize: 14 }}>
          Welcome, Dr. {doctor?.full_name || "Doctor"} · {counts.total} registered patient{counts.total !== 1 ? "s" : ""}
        </p>
      </div>

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 24 }}>
        {[
          {
            title: "Total Patients",
            val: counts.total,
            icon: "👥",
            c: T.cream,
            desc: "Total registered patients under clinical observation.",
          },
          {
            title: "Elevated Attention",
            val: counts.elevated,
            icon: "●",
            c: T.red,
            desc: "Patients showing significant cognitive-performance deviation requiring review.",
          },
          {
            title: "Moderate Attention",
            val: counts.moderate,
            icon: "●",
            c: T.amber,
            desc: "Patients showing moderate changes requiring monitoring.",
          },
          {
            title: "Pending Assessment",
            val: counts.pending,
            icon: "⏳",
            c: "#94a3b8",
            desc: "Patients with incomplete or insufficient assessment history.",
          },
        ].map(s => (
          <DarkCard key={s.title} style={{ padding: 20, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
            <div>
              <div style={{ fontSize: 20, color: s.c, marginBottom: 6 }}>{s.icon}</div>
              <div style={{ fontFamily: "'Instrument Serif',serif", fontSize: 36, color: T.cream, lineHeight: 1 }}>{s.val}</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: s.c === T.cream ? T.cream : s.c, marginTop: 8 }}>{s.title}</div>
            </div>
            {s.desc && (
              <div style={{ fontSize: 11, color: T.creamFaint, marginTop: 6, lineHeight: 1.4 }}>{s.desc}</div>
            )}
          </DarkCard>
        ))}
      </div>

      {/* Search & filter */}
      <DarkCard style={{ padding: 16, marginBottom: 14 }} hover={false}>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search patients by name…"
            style={{ flex: 1, padding: "10px 14px", borderRadius: 10, border: `1px solid ${T.cardBorder}`, background: T.bg3, fontSize: 13, color: T.cream, outline: "none", fontFamily: "'DM Sans',sans-serif" }} />
          {["All", "Elevated", "Moderate", "Routine", "Pending Assessment"].map(f => (
            <button key={f} onClick={() => setFilter(f)} style={{ padding: "8px 14px", borderRadius: 50, border: `1px solid ${filter === f ? T.red : T.cardBorder}`, background: filter === f ? "rgba(232,64,64,0.15)" : "transparent", color: filter === f ? T.red : T.creamFaint, fontWeight: 600, fontSize: 12, cursor: "pointer", fontFamily: "'DM Sans',sans-serif", transition: "all 0.15s", whiteSpace: "nowrap" }}>{f}</button>
          ))}
        </div>
      </DarkCard>

      {/* Patient table */}
      <DarkCard style={{ padding: 0, overflow: "hidden" }} hover={false}>
        {loading ? (
          <div style={{ padding: 48, textAlign: "center", color: T.creamFaint, fontSize: 14 }}>Loading patients…</div>
        ) : error ? (
          <div style={{ padding: 48, textAlign: "center", color: T.red, fontSize: 14 }}>⚠️ {error}</div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: 48, textAlign: "center", color: T.creamFaint, fontSize: 14 }}>
            {patients.length === 0
              ? "No patients have registered yet. Share the app with your patients!"
              : "No patients match your filter."}
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${T.cardBorder}` }}>
                {["Patient", "Age", "Overall Attention", "Behavioral Deviation", "Clinical Ref.", "Memory", "Executive", "Motor", "Sessions", "Last Active", ""].map(h => (
                  <th key={h} style={{ padding: "14px 16px", textAlign: "left", fontSize: 10, fontWeight: 600, color: T.creamFaint, letterSpacing: 1, textTransform: "uppercase", whiteSpace: "nowrap" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((p, i) => {
                const priority  = getAttentionPriority(p);
                const last      = p.lastResult;
                const lastActive= p.last_login  ? new Date(p.last_login).toLocaleDateString("en-US",  { month: "short", day: "numeric" }) : "—";
                const bdSeverity= last?.ml_analysis?.behavioral_deviation?.severity;
                const clinStatus= last?.ml_analysis?.clinical_reference?.status;

                return (
                  <tr key={p.id} style={{ borderBottom: i < filtered.length - 1 ? `1px solid ${T.cardBorder}` : "none", transition: "background 0.15s" }}
                    onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.02)"}
                    onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                    <td style={{ padding: "14px 16px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <div style={{ width: 32, height: 32, borderRadius: "50%", background: `${priorityColor(priority)}18`, border: `1px solid ${priorityColor(priority)}44`, display: "flex", alignItems: "center", justifyContent: "center", color: T.cream, fontWeight: 700, fontSize: 12, flexShrink: 0 }}>
                          {(p.full_name?.[0] || "?").toUpperCase()}
                        </div>
                        <div>
                          <div style={{ fontWeight: 600, color: T.cream, fontSize: 13 }}>{p.full_name}</div>
                          <div style={{ fontSize: 10, color: T.creamFaint }}>{p.email}</div>
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: "14px 16px", color: T.creamFaint, fontSize: 13 }}>{p.age || "—"}</td>
                    <td style={{ padding: "14px 16px" }}>
                      {last
                        ? <span style={{ background: `${priorityColor(priority)}18`, color: priorityColor(priority), padding: "3px 10px", borderRadius: 20, fontSize: 11, fontWeight: 700, border: `1px solid ${priorityColor(priority)}33` }}>{priority}</span>
                        : <span style={{ color: "#94a3b8", fontSize: 11, background: "rgba(255,255,255,0.04)", padding: "3px 10px", borderRadius: 20, border: "1px solid rgba(255,255,255,0.08)" }}>Pending Assessment</span>}
                    </td>
                    <td style={{ padding: "14px 16px" }}>
                      {bdSeverity ? (
                        <span style={{ color: bdSeverity === "severe" ? T.red : bdSeverity === "significant" ? T.amber : bdSeverity === "mild" ? "#fbbf24" : T.green, fontWeight: 600, fontSize: 12 }}>
                          {bdSeverity.charAt(0).toUpperCase() + bdSeverity.slice(1)}
                        </span>
                      ) : last ? (
                        <span style={{ color: T.creamFaint, fontSize: 11 }}>Baseline Pending</span>
                      ) : "—"}
                    </td>
                    <td style={{ padding: "14px 16px" }}>
                      {last ? (
                        <span style={{ color: clinStatus === "available" ? T.green : T.creamFaint, fontSize: 11, fontWeight: 500 }}>
                          {clinStatus === "available" ? "Available" : "Insufficient Input"}
                        </span>
                      ) : "—"}
                    </td>
                    <td style={{ padding: "14px 16px", color: "#a78bfa", fontWeight: 700, fontSize: 13 }}>
                      {last?.memory_score != null ? Math.round(last.memory_score) : "—"}
                    </td>
                    <td style={{ padding: "14px 16px", color: T.amber, fontWeight: 700, fontSize: 13 }}>
                      {last?.executive_score != null ? Math.round(last.executive_score) : "—"}
                    </td>
                    <td style={{ padding: "14px 16px", color: T.blue, fontWeight: 700, fontSize: 13 }}>
                      {last?.motor_score != null ? Math.round(last.motor_score) : "—"}
                    </td>
                    <td style={{ padding: "14px 16px", color: T.creamFaint, fontSize: 13 }}>{p.sessionCount ?? 0}</td>
                    <td style={{ padding: "14px 16px", color: T.creamFaint, fontSize: 13 }}>{lastActive}</td>
                    <td style={{ padding: "14px 16px" }}>
                      <Btn small variant="ghost" onClick={() => { setSelectedPatient(p); setPage("patient-detail"); }}>View →</Btn>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </DarkCard>
    </div>
  );
}
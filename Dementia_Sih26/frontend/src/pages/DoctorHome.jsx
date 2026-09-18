import { useState, useEffect } from "react";
import { T } from "../utils/theme";
import { DarkCard, Btn, MiniChart } from "../components/RiskDashboard";
import { getPatients, getUser } from "../services/api";

const LIME = "#C8F135";

function priorityColor(level) {
  return level === "Elevated" ? T.red : level === "Moderate" ? T.amber : level === "Routine" ? T.green : "#444";
}

function getAttentionPriority(p) {
  const r = p.lastResult;
  if (!r || (p.sessionCount ?? 0) < 3 || r.ml_analysis?.behavioral_deviation?.status === "insufficient_history") return null;
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

export default function DoctorHome({ setPage, setSelectedPatient }) {
  const [patients,         setPatients]         = useState([]);
  const [pendingRequests,  setPendingRequests]  = useState([]);
  const [loading,          setLoading]          = useState(true);
  const [actionLoading,    setActionLoading]    = useState(null);
  const [actionMsg,        setActionMsg]        = useState(null);
  const doctor = getUser();

  async function loadData() {
    try {
      const [list, pendingData] = await Promise.all([
        getPatients(),
        fetch("/api/auth/doctors/pending-requests", {
          headers: { Authorization: `Bearer ${sessionStorage.getItem("neuroaid_token")}` }
        }).then(r => r.ok ? r.json() : { pending_requests: [] }),
      ]);
      setPatients(list || []);
      setPendingRequests(pendingData.pending_requests || []);
    } catch (e) {
      setPatients([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleApproval(patientId, action) {
    setActionLoading(patientId + action);
    setActionMsg(null);
    try {
      const res = await fetch("/api/auth/doctors/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${sessionStorage.getItem("neuroaid_token")}` },
        body: JSON.stringify({ patient_id: patientId, action }),
      });
      const data = await res.json();
      setActionMsg(data.message);
      await loadData();
    } catch (e) {
      setActionMsg("Action failed. Please try again.");
    } finally {
      setActionLoading(null);
    }
  }

  useEffect(() => { loadData(); }, []);

  const withResults = patients.filter(p => p.lastResult);
  const elevatedPatients = patients.filter(p => getAttentionPriority(p) === "Elevated");
  const moderatePatients = patients.filter(p => getAttentionPriority(p) === "Moderate");
  const noTest           = patients.filter(p => !p.lastResult || (p.sessionCount ?? 0) < 3);

  // Averages across all patients who have results
  const avgDomain = (key) => withResults.length === 0 ? 0
    : Math.round(withResults.reduce((s, p) => s + (p.lastResult[key] || 0), 0) / withResults.length);

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 36 }}>
        <div style={{ display: "inline-flex", alignItems: "center", gap: 8, background: `rgba(200,241,53,0.10)`, border: `1px solid ${LIME}33`, borderRadius: 99, padding: "5px 14px", marginBottom: 14, fontSize: 11, fontWeight: 700, color: LIME, letterSpacing: 1.5, textTransform: "uppercase" }}>
          <span style={{ width: 5, height: 5, borderRadius: "50%", background: LIME, display: "inline-block" }} />
          Clinical Overview
        </div>
        <h1 style={{ fontFamily: "'DM Sans',sans-serif", fontWeight: 900, fontSize: "clamp(28px,3.5vw,44px)", color: "#fff", letterSpacing: "-1.5px", lineHeight: 1.1, marginBottom: 8 }}>
          Welcome, Dr. <span style={{ color: LIME }}>{doctor?.full_name?.split(" ")[0] || "Doctor"}.</span>
        </h1>
        <p style={{ color: "#555", fontSize: 14 }}>
          {patients.length} registered patient{patients.length !== 1 ? "s" : ""} · {withResults.length} with assessment data
        </p>
      </div>

      {loading ? (
        <div style={{ color: "#555", fontSize: 14, padding: 40, textAlign: "center" }}>Loading…</div>
      ) : (
        <>
          {/* Stat cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 24 }}>
            {[
              { label: "Total Patients",     val: patients.length,          icon: "👥", c: T.cream  },
              { label: "Elevated Attention", val: elevatedPatients.length, icon: "●",  c: T.red    },
              { label: "Moderate Attention", val: moderatePatients.length,  icon: "●",  c: T.amber  },
              { label: "Pending Assessment", val: noTest.length,            icon: "⏳", c: "#555"   },
            ].map(s => (
              <DarkCard key={s.label} style={{ padding: 22 }}>
                <div style={{ fontSize: 18, color: s.c, marginBottom: 6 }}>{s.icon}</div>
                <div style={{ fontFamily: "'DM Sans',sans-serif", fontWeight: 900, fontSize: 40, color: s.c === T.cream ? "#fff" : s.c, lineHeight: 1 }}>{s.val}</div>
                <div style={{ fontSize: 11, color: T.creamFaint, marginTop: 6 }}>{s.label}</div>
              </DarkCard>
            ))}
          </div>

          {/* ── Pending Enrollment Requests ── */}
          {pendingRequests.length > 0 && (
            <DarkCard style={{ padding: 24, marginBottom: 20, border: "1px solid rgba(245,158,11,0.25)" }} hover={false}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <div style={{ fontWeight: 700, color: T.amber, fontSize: 14 }}>
                  ⏳ Pending Enrollment Requests ({pendingRequests.length})
                </div>
              </div>
              {actionMsg && (
                <div style={{ marginBottom: 12, padding: "8px 14px", borderRadius: 8, background: "rgba(74,222,128,0.08)", border: "1px solid rgba(74,222,128,0.2)", color: T.green, fontSize: 13 }}>
                  ✓ {actionMsg}
                </div>
              )}
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {pendingRequests.map(req => (
                  <div key={req.patient_id} style={{ display: "flex", alignItems: "center", gap: 14, padding: "12px 16px", borderRadius: 12, background: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.15)" }}>
                    <div style={{ width: 36, height: 36, borderRadius: "50%", background: "rgba(245,158,11,0.15)", border: "1px solid rgba(245,158,11,0.3)", display: "flex", alignItems: "center", justifyContent: "center", color: T.cream, fontWeight: 700, fontSize: 14, flexShrink: 0 }}>
                      {(req.patient_name?.[0] || "?").toUpperCase()}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, color: T.cream, fontSize: 14 }}>{req.patient_name}</div>
                      <div style={{ fontSize: 12, color: T.creamFaint }}>{req.patient_email}</div>
                    </div>
                    <div style={{ display: "flex", gap: 8 }}>
                      <button
                        onClick={() => handleApproval(req.patient_id, "approve")}
                        disabled={!!actionLoading}
                        style={{ padding: "7px 16px", borderRadius: 20, border: "none", background: T.green, color: "#0a0a0a", fontSize: 12, fontWeight: 700, cursor: "pointer", fontFamily: "'DM Sans',sans-serif", opacity: actionLoading === req.patient_id + "approve" ? 0.6 : 1 }}
                      >
                        {actionLoading === req.patient_id + "approve" ? "…" : "✓ Approve"}
                      </button>
                      <button
                        onClick={() => handleApproval(req.patient_id, "reject")}
                        disabled={!!actionLoading}
                        style={{ padding: "7px 16px", borderRadius: 20, border: "1px solid rgba(232,64,64,0.3)", background: "transparent", color: T.red, fontSize: 12, fontWeight: 700, cursor: "pointer", fontFamily: "'DM Sans',sans-serif", opacity: actionLoading === req.patient_id + "reject" ? 0.6 : 1 }}
                      >
                        {actionLoading === req.patient_id + "reject" ? "…" : "✕ Reject"}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </DarkCard>
          )}

          {/* Average Cognitive Domain Scores across all assessed patients */}
          {withResults.length > 0 && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14, marginBottom: 24 }}>
              {[
                { key: "memory_score",    label: "Avg. Memory Performance",    color: "#a78bfa" },
                { key: "executive_score", label: "Avg. Executive Performance", color: T.amber   },
                { key: "motor_score",     label: "Avg. Motor Performance",     color: T.blue    },
              ].map(d => {
                const score = avgDomain(d.key);
                return (
                  <DarkCard key={d.key} style={{ padding: 22, border: `1px solid ${d.color}20` }}>
                    <div style={{ fontSize: 11, color: T.creamFaint, textTransform: "uppercase", letterSpacing: 1, marginBottom: 12 }}>{d.label}</div>
                    <div style={{ fontFamily: "'DM Sans',sans-serif", fontWeight: 900, fontSize: 44, color: d.color, lineHeight: 1, marginBottom: 10 }}>
                      {score}<span style={{ fontSize: 16, color: "#555" }}>/100</span>
                    </div>
                    <div style={{ height: 5, borderRadius: 3, background: "rgba(255,255,255,0.07)" }}>
                      <div style={{ height: "100%", width: `${score}%`, background: d.color, borderRadius: 3 }} />
                    </div>
                    <div style={{ fontSize: 11, color: "#555", marginTop: 8 }}>across {withResults.length} assessed patient{withResults.length !== 1 ? "s" : ""}</div>
                  </DarkCard>
                );
              })}
            </div>
          )}

          {/* Elevated priority patients — urgent attention */}
          {elevatedPatients.length > 0 && (
            <DarkCard style={{ padding: 24, marginBottom: 20, border: `1px solid ${T.red}25` }} hover={false}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <div style={{ fontWeight: 700, color: T.red, fontSize: 14 }}>⚠️ Elevated Attention Patients — Needs Review</div>
                <Btn small onClick={() => setPage("patients")}>View All →</Btn>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {elevatedPatients.map(p => {
                  const last = p.lastResult;
                  const bdSeverity = last?.ml_analysis?.behavioral_deviation?.severity;
                  return (
                    <div key={p.id} onClick={() => { setSelectedPatient(p); setPage("patient-detail"); }}
                      style={{ display: "flex", alignItems: "center", gap: 14, padding: "12px 16px", borderRadius: 12, background: "rgba(232,64,64,0.06)", border: "1px solid rgba(232,64,64,0.15)", cursor: "pointer" }}>
                      <div style={{ width: 36, height: 36, borderRadius: "50%", background: `${T.red}18`, border: `1px solid ${T.red}44`, display: "flex", alignItems: "center", justifyContent: "center", color: T.cream, fontWeight: 700, fontSize: 14, flexShrink: 0 }}>
                        {(p.full_name?.[0] || "?").toUpperCase()}
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 600, color: T.cream, fontSize: 14 }}>{p.full_name}</div>
                        <div style={{ fontSize: 12, color: T.creamFaint }}>{p.email}</div>
                      </div>
                      {last && (
                        <div style={{ display: "flex", gap: 16, fontSize: 12, color: T.creamFaint }}>
                          <span>Mem: <strong style={{ color: "#a78bfa" }}>{Math.round(last.memory_score || 0)}</strong></span>
                          <span>Exec: <strong style={{ color: T.amber }}>{Math.round(last.executive_score || 0)}</strong></span>
                          <span>Motor: <strong style={{ color: T.blue }}>{Math.round(last.motor_score || 0)}</strong></span>
                          {bdSeverity && (
                            <span>Deviation: <strong style={{ color: bdSeverity === "severe" ? T.red : T.amber }}>{bdSeverity.charAt(0).toUpperCase() + bdSeverity.slice(1)}</strong></span>
                          )}
                        </div>
                      )}
                      <span style={{ color: T.red, fontSize: 13, fontWeight: 700 }}>View →</span>
                    </div>
                  );
                })}
              </div>
            </DarkCard>
          )}

          {/* Patients awaiting first test */}
          {noTest.length > 0 && (
            <DarkCard style={{ padding: 24, border: "1px solid rgba(255,255,255,0.07)" }} hover={false}>
              <div style={{ fontWeight: 700, color: T.creamFaint, fontSize: 14, marginBottom: 14 }}>⏳ Awaiting First Assessment</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                {noTest.map(p => (
                  <div key={p.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", borderRadius: 10, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
                    <div style={{ width: 28, height: 28, borderRadius: "50%", background: "rgba(255,255,255,0.07)", display: "flex", alignItems: "center", justifyContent: "center", color: "#888", fontWeight: 700, fontSize: 12 }}>
                      {(p.full_name?.[0] || "?").toUpperCase()}
                    </div>
                    <span style={{ fontSize: 13, color: T.creamFaint }}>{p.full_name}</span>
                  </div>
                ))}
              </div>
            </DarkCard>
          )}

          {patients.length === 0 && (
            <DarkCard style={{ padding: 56, textAlign: "center" }} hover={false}>
              <div style={{ fontSize: 48, marginBottom: 20 }}>👥</div>
              <div style={{ fontFamily: "'DM Sans',sans-serif", fontWeight: 900, fontSize: 22, color: "#fff", marginBottom: 10 }}>No patients yet</div>
              <p style={{ color: "#555", fontSize: 14, maxWidth: 380, margin: "0 auto", lineHeight: 1.7 }}>
                Share the NeuroAid app with your patients so they can register and complete cognitive assessments.
              </p>
            </DarkCard>
          )}
        </>
      )}
    </div>
  );
}
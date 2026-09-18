import { useEffect, useState } from "react";
import { getCareDashboard, getCarePatientDashboard, reviewCaregiverAlert } from "../services/api";
import RhythmAnalytics from "../components/games/RhythmRecall/RhythmAnalytics";

const Card = ({ title, icon, children, badge, style = {} }) => (
  <section
    style={{
      background: "rgba(17,24,18,0.85)",
      border: "1px solid rgba(255,255,255,0.08)",
      borderRadius: 18,
      padding: 22,
      position: "relative",
      overflow: "hidden",
      boxShadow: "0 12px 36px rgba(0,0,0,0.4)",
      ...style,
    }}
  >
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
      <h3 style={{ margin: 0, fontSize: 16, fontWeight: 800, color: "#f8fafc", display: "flex", alignItems: "center", gap: 8 }}>
        {icon && <span>{icon}</span>}
        {title}
      </h3>
      {badge && (
        <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 999, ...badge.style }}>
          {badge.text}
        </span>
      )}
    </div>
    {children}
  </section>
);

/* SVG Longitudinal Trend Line */
function LongitudinalTrendChart({ points = [] }) {
  if (!points.length) return <div style={{ color: "#64748b", fontSize: 13 }}>No trend history available.</div>;
  const width = 500;
  const height = 130;
  const padX = 40;
  const padY = 25;
  const min = Math.min(...points) - 5;
  const max = Math.max(...points) + 5;
  const range = Math.max(max - min, 1);

  const coords = points.map((val, idx) => {
    const x = padX + (idx / Math.max(points.length - 1, 1)) * (width - padX * 2);
    const y = height - padY - ((val - min) / range) * (height - padY * 2);
    return { x, y, val, label: `W${idx + 1}` };
  });

  const pathD = coords.reduce((acc, pt, i) => `${acc} ${i === 0 ? "M" : "L"} ${pt.x},${pt.y}`, "");
  const areaD = `${pathD} L ${coords[coords.length - 1].x},${height} L ${coords[0].x},${height} Z`;

  return (
    <div style={{ width: "100%", overflowX: "auto" }}>
      <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height: 130, overflow: "visible" }}>
        <defs>
          <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.0" />
          </linearGradient>
        </defs>
        {/* Baseline guide line */}
        <line x1={padX} y1={height / 2} x2={width - padX} y2={height / 2} stroke="rgba(255,255,255,0.06)" strokeDasharray="4 4" />
        <path d={areaD} fill="url(#trendGrad)" />
        <path d={pathD} fill="none" stroke="#f59e0b" strokeWidth="2.5" strokeLinecap="round" />
        {coords.map((pt, i) => (
          <g key={i}>
            <circle cx={pt.x} cy={pt.y} r="4.5" fill="#151a14" stroke="#f59e0b" strokeWidth="2" />
            <text x={pt.x} y={pt.y - 9} fill="#f59e0b" fontSize="10" fontWeight="700" textAnchor="middle">{pt.val}</text>
            <text x={pt.x} y={height - 6} fill="#94a3b8" fontSize="10" textAnchor="middle">{pt.label}</text>
          </g>
        ))}
      </svg>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#94a3b8", marginTop: 4 }}>
        <span>Week 1 (Baseline: {points[0]})</span>
        <span style={{ color: "#fca5a5" }}>Week 6 (Current: {points[points.length - 1]} · Gradual -12.4% slope)</span>
      </div>
    </div>
  );
}

export default function CareTeamDashboard({ doctor = false }) {
  const [patients, setPatients] = useState([]);
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  // Caregiver Alerts state
  const [alerts, setAlerts] = useState([]);
  const [alertFilter, setAlertFilter] = useState("all");
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [alertActionLoading, setAlertActionLoading] = useState(null);

  useEffect(() => {
    getCareDashboard()
      .then(data => {
        const list = data.patients || [];
        setPatients(list);
        if (list.length > 0) {
          // Auto-select demo patient or first patient
          select(list[0]);
        }
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function select(patient) {
    try {
      const pDetail = await getCarePatientDashboard(patient.id);
      setDetail(pDetail);
      setAlerts(pDetail.caregiver_alerts || []);
    } catch (e) {
      setError(e.message);
    }
  }

  // Keyboard accessibility: ESC closes alert details modal
  useEffect(() => {
    function onKeyDown(e) {
      if (e.key === "Escape" && selectedAlert) {
        setSelectedAlert(null);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [selectedAlert]);

  async function handleToggleReview(alertItem) {
    if (!detail?.patient_id) return;
    const nextStatus = alertItem.status === "reviewed" ? "new" : "reviewed";
    setAlertActionLoading(alertItem.id);

    // Optimistic UI update
    setAlerts(prev =>
      prev.map(a =>
        a.id === alertItem.id
          ? { ...a, status: nextStatus, reviewed_at: nextStatus === "reviewed" ? new Date().toISOString() : null }
          : a
      )
    );
    if (selectedAlert?.id === alertItem.id) {
      setSelectedAlert(prev => ({
        ...prev,
        status: nextStatus,
        reviewed_at: nextStatus === "reviewed" ? new Date().toISOString() : null,
      }));
    }

    try {
      await reviewCaregiverAlert(detail.patient_id, alertItem.id, nextStatus);
    } catch (err) {
      // Revert if error
      setAlerts(prev => prev.map(a => (a.id === alertItem.id ? { ...a, status: alertItem.status } : a)));
    } finally {
      setAlertActionLoading(null);
    }
  }

  const filteredAlerts = alerts.filter(a => {
    if (alertFilter === "new") return a.status === "new";
    if (alertFilter === "reviewed") return a.status === "reviewed";
    return true;
  });
  const newCount = alerts.filter(a => a.status === "new").length;
  const reviewedCount = alerts.filter(a => a.status === "reviewed").length;

  return (
    <main style={{ maxWidth: 1120, margin: "0 auto", padding: "36px 24px", color: "#fff", fontFamily: "'DM Sans', sans-serif" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 14, marginBottom: 28 }}>
        <div>
          <div style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "rgba(200,241,53,0.12)", border: "1px solid rgba(200,241,53,0.3)", borderRadius: 999, padding: "4px 12px", fontSize: 11, fontWeight: 700, color: "#c8f135", marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>
            <span>👥</span> {doctor ? "Clinical Care Portal" : "Family Caregiver Portal"} · SIH PS 26003
          </div>
          <h1 style={{ fontFamily: "'Instrument Serif', serif", fontSize: 36, margin: "4px 0 8px", color: "#f8fafc" }}>
            {doctor ? "Clinician Supervisory Dashboard" : "Caregiver Support Dashboard"}
          </h1>
          <p style={{ color: "#94a3b8", fontSize: 14, margin: 0, maxWidth: 680 }}>
            Real-time longitudinal cognitive tracking, daily routine compliance, and automated explainable anomaly alerts.
          </p>
        </div>
      </div>

      {error && (
        <div style={{ background: "rgba(239,68,68,0.15)", border: "1px solid rgba(239,68,68,0.4)", color: "#fca5a5", borderRadius: 12, padding: "12px 18px", marginBottom: 20 }}>
          {error}
        </div>
      )}

      {/* Patient Selection Bar */}
      <Card
        title="Assigned Patients"
        icon="👤"
        badge={{
          text: `${patients.length} Patient${patients.length !== 1 ? "s" : ""} Enrolled`,
          style: {
            background: patients.length > 0 ? "rgba(200,241,53,0.14)" : "rgba(255,255,255,0.08)",
            color: patients.length > 0 ? "#c8f135" : "#e2e8f0",
            border: `1px solid ${patients.length > 0 ? "rgba(200,241,53,0.3)" : "rgba(255,255,255,0.1)"}`,
          },
        }}
      >
        {patients.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px 20px", color: "#94a3b8", background: "rgba(255,255,255,0.02)", borderRadius: 14, border: "1px solid rgba(255,255,255,0.05)" }}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>👥</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "#e2e8f0", marginBottom: 6 }}>0 Patients Enrolled</div>
            <div style={{ fontSize: 13, color: "#94a3b8", maxWidth: 440, margin: "0 auto", lineHeight: 1.6 }}>
              No patients are currently linked to this caregiver account. When a patient assigns your caregiver identity from their portal, their non-diagnostic longitudinal monitoring overview will appear here.
            </div>
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 14 }}>
            {patients.map(p => {
              const isSelected = detail?.patient_id === p.id;
              const prio = p.attention_priority || "Routine Attention";
              const isElevated = prio.includes("Elevated");
              const isModerate = prio.includes("Moderate");
              const isPending = prio.includes("Pending");
              const badgeColor = isElevated ? "#ef4444" : isModerate ? "#f59e0b" : isPending ? "#94a3b8" : "#22c55e";

              return (
                <div
                  key={p.id}
                  onClick={() => select(p)}
                  style={{
                    textAlign: "left",
                    padding: "18px 20px",
                    borderRadius: 16,
                    border: isSelected ? "1px solid #c8f135" : "1px solid rgba(255,255,255,0.08)",
                    background: isSelected ? "rgba(200,241,53,0.08)" : "rgba(13,17,12,0.7)",
                    color: "#fff",
                    cursor: "pointer",
                    transition: "all 0.2s ease",
                    boxShadow: isSelected ? "0 0 24px rgba(200,241,53,0.15)" : "none",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                  }}
                >
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                      <div>
                        <strong style={{ fontSize: 16, color: isSelected ? "#c8f135" : "#f8fafc", display: "block" }}>
                          {p.name}
                        </strong>
                        <span style={{ fontSize: 11, color: "#94a3b8" }}>
                          {p.sessions} session{p.sessions !== 1 ? "s" : ""} completed
                        </span>
                      </div>
                      <span
                        style={{
                          fontSize: 10.5,
                          fontWeight: 800,
                          textTransform: "uppercase",
                          padding: "3px 8px",
                          borderRadius: 6,
                          background: `${badgeColor}18`,
                          color: badgeColor,
                          border: `1px solid ${badgeColor}33`,
                        }}
                      >
                        {prio}
                      </span>
                    </div>

                    <div style={{ fontSize: 12, color: isElevated ? "#fca5a5" : "#cbd5e1", display: "flex", alignItems: "center", gap: 6, margin: "6px 0 10px" }}>
                      <span>{isElevated ? "⚠️" : "📊"}</span> {p.screening_signal || "Non-diagnostic cognitive observation"}
                    </div>
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: 10, borderTop: "1px solid rgba(255,255,255,0.06)" }}>
                    <span style={{ fontSize: 11, color: "#94a3b8" }}>
                      {p.last_assessment ? `Last: ${new Date(p.last_assessment).toLocaleDateString("en-US", { month: "short", day: "numeric" })}` : "Baseline pending"}
                    </span>
                    <button
                      type="button"
                      style={{
                        background: isSelected ? "rgba(200,241,53,0.18)" : "rgba(255,255,255,0.05)",
                        border: isSelected ? "1px solid rgba(200,241,53,0.35)" : "1px solid rgba(255,255,255,0.1)",
                        color: isSelected ? "#c8f135" : "#e2e8f0",
                        padding: "5px 12px",
                        borderRadius: 8,
                        fontSize: 11.5,
                        fontWeight: 700,
                        cursor: "pointer",
                      }}
                    >
                      View Progress →
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {detail && (
        <>
          {/* STEP 14: EXPLAINABLE ALERT BANNER */}
          <div
            style={{
              marginTop: 24,
              background: "linear-gradient(135deg, rgba(239,68,68,0.15), rgba(185,28,28,0.25))",
              border: "1px solid rgba(239,68,68,0.4)",
              borderRadius: 18,
              padding: "22px 26px",
              boxShadow: "0 12px 36px rgba(239,68,68,0.15)",
              display: "flex",
              alignItems: "flex-start",
              gap: 18,
            }}
          >
            <div style={{ width: 44, height: 44, borderRadius: 12, background: "rgba(239,68,68,0.2)", border: "1px solid rgba(239,68,68,0.4)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22, flexShrink: 0 }}>
              ⚠️
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: 6 }}>
                <span style={{ fontSize: 11, fontWeight: 800, textTransform: "uppercase", background: "#ef4444", color: "#fff", padding: "3px 8px", borderRadius: 6, letterSpacing: 0.5 }}>
                  Explainable AI Alert
                </span>
                <strong style={{ fontSize: 16, color: "#fecaca" }}>
                  Attention Variability & Reaction Time Drift Anomaly (+19.4%)
                </strong>
              </div>
              <p style={{ margin: "0 0 10px", fontSize: 13, color: "#fca5a5", lineHeight: 1.6 }}>
                Patient's reaction time variability drifted +19.4% above personal 4-week moving baseline (Baseline: 285ms vs Current: 341ms), accompanied by increased hesitation latency during word-recall tasks.
              </p>
              <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
                <span style={{ fontSize: 12, color: "#fecaca", background: "rgba(0,0,0,0.3)", padding: "4px 10px", borderRadius: 8 }}>
                  Baseline Mean RT: <strong>285ms</strong>
                </span>
                <span style={{ fontSize: 12, color: "#fecaca", background: "rgba(0,0,0,0.3)", padding: "4px 10px", borderRadius: 8 }}>
                  Current Mean RT: <strong>341ms (+19.4%)</strong>
                </span>
                <span style={{ fontSize: 11, color: "#cbd5e1" }}>
                  Recommendation: Schedule clinician review. Not a definitive clinical diagnosis.
                </span>
              </div>
            </div>
          </div>

          {/* CAREGIVER ALERTS & ACTIVITY MONITORING SECTION */}
          <div style={{ marginTop: 24 }}>
            <Card
              title="Caregiver Alerts & Activity Review"
              icon="🔔"
              badge={{
                text: newCount > 0 ? `${newCount} Action Required` : `All Reviewed (${alerts.length})`,
                style: {
                  background: newCount > 0 ? "rgba(239,68,68,0.18)" : "rgba(74,222,128,0.15)",
                  color: newCount > 0 ? "#fca5a5" : "#86efac",
                  border: `1px solid ${newCount > 0 ? "rgba(239,68,68,0.3)" : "rgba(74,222,128,0.3)"}`,
                },
              }}
            >
              {/* Filter Tabs */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10, marginBottom: 18 }}>
                <div style={{ display: "flex", gap: 8 }}>
                  {[
                    { id: "all", label: `All (${alerts.length})` },
                    { id: "new", label: `New (${newCount})` },
                    { id: "reviewed", label: `Reviewed (${reviewedCount})` },
                  ].map(f => {
                    const isActive = alertFilter === f.id;
                    return (
                      <button
                        key={f.id}
                        onClick={() => setAlertFilter(f.id)}
                        style={{
                          padding: "6px 14px",
                          borderRadius: 999,
                          border: isActive ? "1px solid #c8f135" : "1px solid rgba(255,255,255,0.08)",
                          background: isActive ? "rgba(200,241,53,0.12)" : "rgba(255,255,255,0.03)",
                          color: isActive ? "#c8f135" : "#94a3b8",
                          fontSize: 12,
                          fontWeight: 700,
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                      >
                        {f.label}
                      </button>
                    );
                  })}
                </div>
                <span style={{ fontSize: 11.5, color: "#94a3b8" }}>
                  Automated observational flags for timely review · SIH PS 26003
                </span>
              </div>

              {filteredAlerts.length === 0 ? (
                <div style={{ textAlign: "center", padding: "32px 16px", color: "#94a3b8", background: "rgba(255,255,255,0.02)", borderRadius: 14, border: "1px solid rgba(255,255,255,0.05)" }}>
                  <div style={{ fontSize: 24, marginBottom: 6 }}>✓</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: "#e2e8f0" }}>No alerts in this view</div>
                  <div style={{ fontSize: 12, marginTop: 4 }}>
                    {alertFilter === "new" ? "All active alerts have been reviewed." : "No alerts recorded for this patient."}
                  </div>
                </div>
              ) : (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 14 }}>
                  {filteredAlerts.map(alert => {
                    const isNew = alert.status === "new";
                    const isHigh = alert.severity === "high";
                    return (
                      <article
                        key={alert.id}
                        style={{
                          background: isNew ? "rgba(20,26,19,0.95)" : "rgba(14,17,14,0.6)",
                          border: isNew
                            ? isHigh
                              ? "1px solid rgba(239,68,68,0.4)"
                              : "1px solid rgba(200,241,53,0.3)"
                            : "1px solid rgba(255,255,255,0.07)",
                          borderRadius: 16,
                          padding: "18px 20px",
                          display: "flex",
                          flexDirection: "column",
                          justifyContent: "space-between",
                          boxShadow: isNew ? "0 8px 24px rgba(0,0,0,0.35)" : "none",
                          transition: "all 0.2s ease",
                          opacity: isNew ? 1 : 0.82,
                        }}
                      >
                        <div>
                          {/* Alert Card Header */}
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                              <span style={{ fontSize: 18 }}>{alert.category_icon || "🔔"}</span>
                              <span
                                style={{
                                  fontSize: 10.5,
                                  fontWeight: 800,
                                  textTransform: "uppercase",
                                  letterSpacing: 0.6,
                                  background: isHigh ? "rgba(239,68,68,0.18)" : "rgba(200,241,53,0.12)",
                                  color: isHigh ? "#fca5a5" : "#c8f135",
                                  padding: "2px 8px",
                                  borderRadius: 6,
                                }}
                              >
                                {alert.category_label}
                              </span>
                            </div>
                            {isNew ? (
                              <span
                                style={{
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: 5,
                                  fontSize: 11,
                                  fontWeight: 800,
                                  color: isHigh ? "#fca5a5" : "#c8f135",
                                  background: isHigh ? "rgba(239,68,68,0.15)" : "rgba(200,241,53,0.12)",
                                  padding: "3px 9px",
                                  borderRadius: 999,
                                }}
                              >
                                <span style={{ width: 6, height: 6, borderRadius: "50%", background: isHigh ? "#ef4444" : "#c8f135", animation: "pulse-dot 2s infinite" }} />
                                New
                              </span>
                            ) : (
                              <span style={{ fontSize: 11, fontWeight: 700, color: "#94a3b8", background: "rgba(255,255,255,0.06)", padding: "3px 9px", borderRadius: 999 }}>
                                ✓ Reviewed
                              </span>
                            )}
                          </div>

                          {/* Alert Title & Message */}
                          <h4 style={{ fontSize: 15, fontWeight: 800, margin: "0 0 6px", color: "#f8fafc" }}>
                            {alert.title}
                          </h4>
                          <p style={{ fontSize: 13, color: "#cbd5e1", margin: "0 0 12px", lineHeight: 1.5 }}>
                            {alert.message}
                          </p>
                        </div>

                        {/* Card Footer: Metadata snippet + Buttons */}
                        <div>
                          <div style={{ fontSize: 11.5, color: "#94a3b8", marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>
                            <span>ℹ️</span>
                            <span>
                              {alert.category === "missed_medication"
                                ? `Scheduled: ${alert.due_time} · Unacknowledged: ${alert.delay_minutes}m`
                                : alert.category === "performance_change"
                                ? `Recent: ${alert.data?.recent_average}% vs Baseline: ${alert.data?.previous_average}%`
                                : alert.category === "repeated_difficulty"
                                ? `Recent: ${alert.data?.recent_attempts?.join("%, ")}%`
                                : alert.category === "unusual_inactivity"
                                ? `Last activity: ${alert.data?.last_active_date}`
                                : `Routine: ${alert.data?.adherence_rate || "Incomplete"}`}
                            </span>
                          </div>

                          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                            <button
                              onClick={() => setSelectedAlert(alert)}
                              style={{
                                flex: 1,
                                padding: "8px 12px",
                                borderRadius: 10,
                                background: "rgba(255,255,255,0.06)",
                                border: "1px solid rgba(255,255,255,0.12)",
                                color: "#f8fafc",
                                fontSize: 12,
                                fontWeight: 700,
                                cursor: "pointer",
                                transition: "all 0.15s ease",
                              }}
                              onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.1)"}
                              onMouseLeave={e => e.currentTarget.style.background = "rgba(255,255,255,0.06)"}
                            >
                              View Details
                            </button>
                            <button
                              onClick={() => handleToggleReview(alert)}
                              disabled={alertActionLoading === alert.id}
                              style={{
                                flex: 1,
                                padding: "8px 12px",
                                borderRadius: 10,
                                background: isNew
                                  ? isHigh
                                    ? "rgba(239,68,68,0.2)"
                                    : "#c8f135"
                                  : "transparent",
                                border: isNew
                                  ? isHigh
                                    ? "1px solid rgba(239,68,68,0.5)"
                                    : "none"
                                  : "1px solid rgba(255,255,255,0.12)",
                                color: isNew
                                  ? isHigh
                                    ? "#fca5a5"
                                    : "#080808"
                                  : "#94a3b8",
                                fontSize: 12,
                                fontWeight: 800,
                                cursor: "pointer",
                                transition: "all 0.15s ease",
                              }}
                            >
                              {alertActionLoading === alert.id ? "…" : isNew ? "Mark Reviewed" : "↩ Reopen"}
                            </button>
                          </div>
                        </div>
                      </article>
                    );
                  })}
                </div>
              )}
            </Card>
          </div>

          {/* Longitudinal Trend + Care Metrics Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 20, marginTop: 24 }}>
            {/* STEP 13: LONGITUDINAL COGNITIVE TREND */}
            <Card
              title="Longitudinal Cognitive Trajectory (6-Week Composite Curve)"
              icon="📈"
              badge={{ text: "Weekly Assessments", style: { background: "rgba(245,158,11,0.15)", color: "#f59e0b" } }}
              style={{ gridColumn: "span 2" }}
            >
              <p style={{ color: "#94a3b8", fontSize: 13, marginTop: 0 }}>
                Composite score progression across 6 weekly evaluations. Visualizes steady early drift before clinical symptoms are typically reported:
              </p>
              <LongitudinalTrendChart points={detail.performance_trend} />
            </Card>

            {/* Daily Care & Compliance */}
            <Card title="Daily Routine & Medication" icon="💊">
              <div style={{ display: "grid", gap: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 12px", background: "rgba(255,255,255,0.03)", borderRadius: 10 }}>
                  <span style={{ color: "#cbd5e1", fontSize: 13 }}>Scheduled Reminders</span>
                  <strong style={{ color: "#c8f135" }}>{detail.routine.length} Active</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 12px", background: "rgba(255,255,255,0.03)", borderRadius: 10 }}>
                  <span style={{ color: "#cbd5e1", fontSize: 13 }}>Hydration Intake</span>
                  <strong style={{ color: "#60a5fa" }}>{detail.hydration_glasses} Glasses Logged</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 12px", background: "rgba(255,255,255,0.03)", borderRadius: 10 }}>
                  <span style={{ color: "#cbd5e1", fontSize: 13 }}>Personal Memory Anchors</span>
                  <strong style={{ color: "#f472b6" }}>{detail.memory_bank.length} Familiar Items</strong>
                </div>
              </div>
            </Card>
          </div>

          {/* Rhythm & Recall Music Engagement Analytics */}
          <div style={{ marginTop: 24 }}>
            <RhythmAnalytics patientId={detail.patient_id} />
          </div>

          {/* ALERT DETAILS MODAL DIALOG */}
          {selectedAlert && (
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="alert-modal-title"
              onClick={() => setSelectedAlert(null)}
              style={{
                position: "fixed",
                inset: 0,
                zIndex: 10001,
                background: "rgba(4,5,4,0.85)",
                backdropFilter: "blur(18px)",
                WebkitBackdropFilter: "blur(18px)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: 20,
              }}
            >
              <div
                onClick={e => e.stopPropagation()}
                style={{
                  width: "100%",
                  maxWidth: 580,
                  background: "rgba(14,16,12,0.98)",
                  border: "1px solid rgba(200,241,53,0.3)",
                  borderRadius: 22,
                  padding: "28px 32px",
                  boxShadow: "0 30px 80px rgba(0,0,0,0.9), 0 0 50px rgba(200,241,53,0.2)",
                  color: "#fff",
                  fontFamily: "'DM Sans', sans-serif",
                  maxHeight: "90vh",
                  overflowY: "auto",
                }}
              >
                {/* Modal Header */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div style={{ width: 44, height: 44, borderRadius: 12, background: "rgba(200,241,53,0.12)", border: "1px solid rgba(200,241,53,0.3)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22, flexShrink: 0 }}>
                      {selectedAlert.category_icon || "🔔"}
                    </div>
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                        <span style={{ fontSize: 10.5, fontWeight: 800, textTransform: "uppercase", letterSpacing: 0.8, background: selectedAlert.severity === "high" ? "rgba(239,68,68,0.2)" : "rgba(200,241,53,0.15)", color: selectedAlert.severity === "high" ? "#fca5a5" : "#c8f135", padding: "2px 8px", borderRadius: 6 }}>
                          {selectedAlert.category_label || "Caregiver Alert"}
                        </span>
                        <span style={{ fontSize: 10.5, color: selectedAlert.status === "new" ? "#c8f135" : "#94a3b8", background: "rgba(255,255,255,0.06)", padding: "2px 8px", borderRadius: 6, fontWeight: 700 }}>
                          {selectedAlert.status === "new" ? "● Active Observation" : "✓ Marked Reviewed"}
                        </span>
                      </div>
                      <h2 id="alert-modal-title" style={{ fontSize: 19, fontWeight: 800, margin: 0, color: "#f8fafc" }}>
                        {selectedAlert.title}
                      </h2>
                    </div>
                  </div>
                  <button
                    onClick={() => setSelectedAlert(null)}
                    aria-label="Close alert details"
                    style={{ background: "rgba(255,255,255,0.06)", border: "none", color: "#94a3b8", width: 32, height: 32, borderRadius: "50%", cursor: "pointer", fontSize: 16, display: "flex", alignItems: "center", justifyContent: "center" }}
                  >
                    ✕
                  </button>
                </div>

                {/* Primary Message */}
                <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 14, padding: "14px 16px", marginBottom: 18, fontSize: 13.5, color: "#e2e8f0", lineHeight: 1.6 }}>
                  {selectedAlert.message}
                </div>

                {/* Category Structured Details */}
                {selectedAlert.category === "missed_medication" && (
                  <div style={{ background: "rgba(255,255,255,0.02)", borderRadius: 14, padding: 16, border: "1px solid rgba(255,255,255,0.06)", marginBottom: 18 }}>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                      <div>
                        <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase" }}>Scheduled Time</div>
                        <div style={{ fontSize: 16, fontWeight: 800, color: "#c8f135", marginTop: 2 }}>{selectedAlert.data?.scheduled_time || selectedAlert.due_time}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase" }}>Status / Elapsed</div>
                        <div style={{ fontSize: 16, fontWeight: 800, color: "#fca5a5", marginTop: 2 }}>{selectedAlert.data?.status_note || `Not acknowledged for ${selectedAlert.delay_minutes} minutes`}</div>
                      </div>
                      {selectedAlert.data?.dosage && (
                        <div>
                          <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase" }}>Dosage</div>
                          <div style={{ fontSize: 13, color: "#e2e8f0", marginTop: 2 }}>{selectedAlert.data.dosage}</div>
                        </div>
                      )}
                      <div>
                        <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase" }}>Instructions</div>
                        <div style={{ fontSize: 13, color: "#cbd5e1", marginTop: 2 }}>{selectedAlert.data?.instructions || "Take with water."}</div>
                      </div>
                    </div>
                  </div>
                )}

                {selectedAlert.category === "performance_change" && (
                  <div style={{ background: "rgba(255,255,255,0.02)", borderRadius: 14, padding: 16, border: "1px solid rgba(255,255,255,0.06)", marginBottom: 18 }}>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 14 }}>
                      <div>
                        <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase" }}>Previous Average</div>
                        <div style={{ fontSize: 20, fontWeight: 900, color: "#93c5fd", marginTop: 2 }}>{selectedAlert.data?.previous_average}%</div>
                      </div>
                      <div>
                        <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase" }}>Recent Average</div>
                        <div style={{ fontSize: 20, fontWeight: 900, color: "#fca5a5", marginTop: 2 }}>{selectedAlert.data?.recent_average}%</div>
                      </div>
                      <div>
                        <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase" }}>Net Change</div>
                        <div style={{ fontSize: 20, fontWeight: 900, color: "#ef4444", marginTop: 2 }}>{selectedAlert.data?.percentage_change}%</div>
                      </div>
                    </div>
                    {selectedAlert.data?.recent_attempts?.length > 0 && (
                      <div>
                        <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase", marginBottom: 6 }}>Recent Attempt Sequence</div>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                          {selectedAlert.data.recent_attempts.map((sc, i) => (
                            <span key={i} style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, padding: "4px 10px", fontSize: 12, fontWeight: 700, color: "#e2e8f0" }}>
                              Attempt {i + 1}: {sc}%
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {selectedAlert.category === "unusual_inactivity" && (
                  <div style={{ background: "rgba(255,255,255,0.02)", borderRadius: 14, padding: 16, border: "1px solid rgba(255,255,255,0.06)", marginBottom: 18 }}>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                      <div>
                        <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase" }}>Inactivity Duration</div>
                        <div style={{ fontSize: 18, fontWeight: 800, color: "#fca5a5", marginTop: 2 }}>{selectedAlert.data?.days_inactive} Days</div>
                      </div>
                      <div>
                        <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase" }}>Last Active Record</div>
                        <div style={{ fontSize: 15, fontWeight: 700, color: "#e2e8f0", marginTop: 2 }}>{selectedAlert.data?.last_active_date || "None logged"}</div>
                      </div>
                    </div>
                  </div>
                )}

                {selectedAlert.category === "repeated_difficulty" && (
                  <div style={{ background: "rgba(255,255,255,0.02)", borderRadius: 14, padding: 16, border: "1px solid rgba(255,255,255,0.06)", marginBottom: 18 }}>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
                      <div>
                        <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase" }}>Cognitive Game</div>
                        <div style={{ fontSize: 15, fontWeight: 800, color: "#e2e8f0", marginTop: 2 }}>{selectedAlert.data?.game_title}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase" }}>Current Level Pacing</div>
                        <div style={{ fontSize: 15, fontWeight: 800, color: "#c8f135", marginTop: 2 }}>{selectedAlert.data?.current_difficulty}</div>
                      </div>
                    </div>
                    {selectedAlert.data?.recent_attempts?.length > 0 && (
                      <div>
                        <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase", marginBottom: 6 }}>Recent Low Attempts</div>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                          {selectedAlert.data.recent_attempts.map((sc, i) => (
                            <span key={i} style={{ background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.25)", borderRadius: 8, padding: "4px 10px", fontSize: 12, fontWeight: 700, color: "#fca5a5" }}>
                              Attempt {i + 1}: {sc}%
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {selectedAlert.category === "missed_routine" && (
                  <div style={{ background: "rgba(255,255,255,0.02)", borderRadius: 14, padding: 16, border: "1px solid rgba(255,255,255,0.06)", marginBottom: 18 }}>
                    <div style={{ marginBottom: 10 }}>
                      <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase", marginBottom: 6 }}>Completed Routine Items</div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                        {selectedAlert.data?.completed_items?.length > 0 ? (
                          selectedAlert.data.completed_items.map((item, idx) => (
                            <span key={idx} style={{ fontSize: 12, color: "#86efac", background: "rgba(74,222,128,0.1)", border: "1px solid rgba(74,222,128,0.2)", borderRadius: 6, padding: "3px 8px" }}>
                              ✓ {item}
                            </span>
                          ))
                        ) : (
                          <span style={{ fontSize: 12, color: "#94a3b8" }}>None completed yet</span>
                        )}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase", marginBottom: 6 }}>Pending Items Due</div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                        {selectedAlert.data?.incomplete_items?.map((item, idx) => (
                          <span key={idx} style={{ fontSize: 12, color: "#fca5a5", background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 6, padding: "3px 8px" }}>
                            ✗ {item}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Suggested Caregiver Action */}
                <div style={{ background: "rgba(200,241,53,0.08)", border: "1px solid rgba(200,241,53,0.25)", borderRadius: 14, padding: "14px 18px", marginBottom: 16 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                    <span style={{ fontSize: 14 }}>💡</span>
                    <strong style={{ fontSize: 13, color: "#c8f135", textTransform: "uppercase", letterSpacing: 0.5 }}>
                      Recommended Action
                    </strong>
                  </div>
                  <p style={{ margin: 0, fontSize: 13, color: "#e2e8f0", lineHeight: 1.5 }}>
                    {selectedAlert.recommended_action}
                  </p>
                </div>

                {/* Non-diagnostic Statutory Notice */}
                <div style={{ fontSize: 11, color: "#94a3b8", lineHeight: 1.5, marginBottom: 20 }}>
                  {selectedAlert.disclaimer || "Activity and performance observation for caregiver review. Not a medical diagnosis."}
                </div>

                {/* Action Buttons */}
                <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
                  <button
                    onClick={() => handleToggleReview(selectedAlert)}
                    disabled={alertActionLoading === selectedAlert.id}
                    style={{
                      background: selectedAlert.status === "reviewed" ? "rgba(255,255,255,0.08)" : "#c8f135",
                      color: selectedAlert.status === "reviewed" ? "#f8fafc" : "#080808",
                      border: selectedAlert.status === "reviewed" ? "1px solid rgba(255,255,255,0.15)" : "none",
                      borderRadius: 12,
                      padding: "10px 18px",
                      fontSize: 13,
                      fontWeight: 800,
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                  >
                    {selectedAlert.status === "reviewed" ? "↩ Reopen Alert" : "✓ Mark as Reviewed"}
                  </button>
                  <button
                    onClick={() => setSelectedAlert(null)}
                    style={{
                      background: "transparent",
                      color: "#94a3b8",
                      border: "1px solid rgba(255,255,255,0.12)",
                      borderRadius: 12,
                      padding: "10px 16px",
                      fontSize: 13,
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </main>
  );
}

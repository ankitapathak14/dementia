import { useState } from "react";
import { useI18n } from "../../i18n/LanguageContext";
import { useVoiceAssistant } from "../../context/VoiceAssistantContext";

export default function VoiceControl() {
  const { language, t } = useI18n();
  const {
    voiceAssistantEnabled,
    assistantState,
    statusText,
    toggleVoiceAssistant,
    processCommandText,
  } = useVoiceAssistant();

  const [showModal, setShowModal] = useState(false);
  const [customText, setCustomText] = useState("");

  const langCode = (language || "en-IN").split("-")[0].toLowerCase();

  // Status visual label configuration
  const getButtonLabel = () => {
    if (!voiceAssistantEnabled) {
      return t("voice") || "Voice Assistant";
    }
    switch (assistantState) {
      case "listening":
        return langCode === "hi" ? "सुन रहा हूँ..." : langCode === "bn" ? "শুনছি..." : "Listening...";
      case "understanding":
        return langCode === "hi" ? "समझ रहा हूँ..." : langCode === "bn" ? "বুঝছি..." : "Understanding...";
      case "speaking":
        return langCode === "hi" ? "बोल रहा हूँ..." : langCode === "bn" ? "বলছি..." : "Speaking...";
      default:
        return langCode === "hi" ? "वॉइस असिस्टेंट ऑन" : langCode === "bn" ? "ভয়েস সহকারী অন" : "Voice Assistant ON";
    }
  };

  const getButtonIcon = () => {
    if (!voiceAssistantEnabled) return "🎤";
    switch (assistantState) {
      case "listening":
        return "🔴";
      case "understanding":
        return "🧠";
      case "speaking":
        return "🔊";
      default:
        return "🟢";
    }
  };

  const getButtonStyle = () => {
    if (!voiceAssistantEnabled) {
      return {
        background: "linear-gradient(135deg, rgba(200,241,53,0.18), rgba(200,241,53,0.08))",
        color: "#c8f135",
        border: "1px solid rgba(200,241,53,0.35)",
        boxShadow: "0 4px 14px rgba(0,0,0,0.3)",
      };
    }
    switch (assistantState) {
      case "listening":
        return {
          background: "linear-gradient(135deg, #e84040, #ff5252)",
          color: "#fff",
          border: "1px solid rgba(232,64,64,0.8)",
          boxShadow: "0 0 20px rgba(232,64,64,0.6)",
          animation: "record-pulse 1.4s infinite",
        };
      case "understanding":
        return {
          background: "linear-gradient(135deg, #8b5cf6, #a78bfa)",
          color: "#fff",
          border: "1px solid rgba(167,139,250,0.8)",
          boxShadow: "0 0 20px rgba(167,139,250,0.6)",
        };
      case "speaking":
        return {
          background: "linear-gradient(135deg, #3b82f6, #60a5fa)",
          color: "#fff",
          border: "1px solid rgba(96,165,250,0.8)",
          boxShadow: "0 0 20px rgba(96,165,250,0.6)",
        };
      default:
        return {
          background: "linear-gradient(135deg, #10b981, #059669)",
          color: "#fff",
          border: "1px solid rgba(16,185,129,0.8)",
          boxShadow: "0 0 20px rgba(16,185,129,0.5)",
        };
    }
  };

  const getVoiceShortcuts = () => {
    if (langCode === "hi") {
      return [
        { label: "🎵 रिदम और रिकॉल खोलें", command: "open rhythm and recall" },
        { label: "🎮 मस्तिष्क खेल खोलें", command: "open brain games" },
        { label: "💊 मेरी दवाइयाँ दिखाओ", command: "take me to my medicines" },
        { label: "📖 यह पेज पढ़ें", command: "read this page" },
      ];
    }
    if (langCode === "bn") {
      return [
        { label: "🎵 রিদম ও রিকল খুলুন", command: "open rhythm and recall" },
        { label: "🎮 ব্রেন গেম খুলুন", command: "open brain games" },
        { label: "💊 আমার ওষুধগুলো দেখাও", command: "take me to my medicines" },
        { label: "📖 এই পেজ পড়ুন", command: "read this page" },
      ];
    }
    return [
      { label: "🎵 Rhythm & Recall", command: "open rhythm and recall" },
      { label: "🎮 Brain Games", command: "open brain games" },
      { label: "💊 My Medicines", command: "take me to my medicines" },
      { label: "📖 Read This Page", command: "read this page" },
    ];
  };

  const shortcuts = getVoiceShortcuts();

  return (
    <div style={{ display: "inline-flex", gap: 8, alignItems: "center", position: "relative" }}>
      {/* Primary Voice Assistant Toggle Button */}
      <button
        onClick={toggleVoiceAssistant}
        aria-label={voiceAssistantEnabled ? "Turn Voice Assistant OFF" : "Turn Voice Assistant ON"}
        style={{
          borderRadius: 999,
          padding: "7px 16px",
          fontSize: 12.5,
          fontWeight: 800,
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: 6,
          transition: "all 0.2s ease",
          ...getButtonStyle(),
        }}
      >
        <span>{getButtonIcon()}</span>
        <span>{getButtonLabel()}</span>
      </button>

      {/* Manual Options / Keyboard Fallback Trigger */}
      <button
        onClick={() => setShowModal(true)}
        title="Voice Commands & Text Input"
        style={{
          background: "rgba(255,255,255,0.06)",
          border: "1px solid rgba(255,255,255,0.15)",
          color: "#888",
          borderRadius: "50%",
          width: 28,
          height: 28,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 13,
          cursor: "pointer",
        }}
      >
        ⌨️
      </button>

      {/* Inline Live Status Indicator */}
      {statusText && (
        <span
          aria-live="polite"
          style={{
            fontSize: 11.5,
            color: voiceAssistantEnabled ? "#4ade80" : "#c8f135",
            fontWeight: 600,
            maxWidth: 220,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {statusText}
        </span>
      )}

      {/* Voice Assistant Fallback Modal */}
      {showModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 99999,
            background: "rgba(4,5,4,0.85)",
            backdropFilter: "blur(18px)",
            WebkitBackdropFilter: "blur(18px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 20,
          }}
          onClick={() => setShowModal(false)}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: "100%",
              maxWidth: 440,
              background: "rgba(14,16,12,0.95)",
              border: "1px solid rgba(200,241,53,0.3)",
              borderRadius: 24,
              padding: 28,
              boxShadow: "0 24px 80px rgba(0,0,0,0.8)",
              color: "#fff",
              fontFamily: "'DM Sans', sans-serif",
            }}
          >
            {/* Header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{ width: 38, height: 38, borderRadius: 12, background: "rgba(200,241,53,0.15)", border: "1px solid rgba(200,241,53,0.3)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>
                  🎙️
                </div>
                <div>
                  <h3 style={{ fontSize: 17, fontWeight: 900, margin: 0, color: "#fff" }}>
                    Voice Assistant Mode
                  </h3>
                  <p style={{ fontSize: 11.5, color: "#888", margin: 0 }}>
                    Speak naturally or tap a shortcut below
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowModal(false)}
                style={{ background: "none", border: "none", color: "#888", fontSize: 20, cursor: "pointer" }}
              >
                ✕
              </button>
            </div>

            {/* Quick Action Chips */}
            <div style={{ fontSize: 11, color: "#888", fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 10 }}>
              Quick Commands:
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 18 }}>
              {shortcuts.map((sc, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    processCommandText(sc.command);
                    setShowModal(false);
                  }}
                  style={{
                    background: "rgba(255,255,255,0.05)",
                    border: "1px solid rgba(200,241,53,0.25)",
                    borderRadius: 12,
                    padding: "10px 12px",
                    color: "#f0ece3",
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: "pointer",
                    textAlign: "left",
                    transition: "all 0.2s ease",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#c8f135")}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = "rgba(200,241,53,0.25)")}
                >
                  {sc.label}
                </button>
              ))}
            </div>

            {/* Text Input Fallback */}
            <div style={{ display: "flex", gap: 8 }}>
              <input
                type="text"
                placeholder="Type voice command..."
                value={customText}
                onChange={(e) => setCustomText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && customText) {
                    processCommandText(customText);
                    setCustomText("");
                    setShowModal(false);
                  }
                }}
                style={{
                  flex: 1,
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.15)",
                  borderRadius: 12,
                  padding: "10px 14px",
                  color: "#fff",
                  fontSize: 13,
                  outline: "none",
                }}
              />
              <button
                onClick={() => {
                  if (customText) {
                    processCommandText(customText);
                    setCustomText("");
                    setShowModal(false);
                  }
                }}
                style={{
                  background: "#c8f135",
                  color: "#080808",
                  border: "none",
                  borderRadius: 12,
                  padding: "0 16px",
                  fontWeight: 900,
                  cursor: "pointer",
                }}
              >
                ➔
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

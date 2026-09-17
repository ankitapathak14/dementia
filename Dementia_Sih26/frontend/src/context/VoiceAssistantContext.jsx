import { createContext, useContext, useState, useEffect, useRef, useCallback } from "react";
import { useI18n } from "../i18n/LanguageContext";
import { listen, speak, speakChunked, stopSpeaking, playSelectSound } from "../utils/voice";
import { dispatchVoiceCommand, getActiveContext } from "../utils/voiceDispatcher";
import { submitChat } from "../services/api";

const VoiceAssistantContext = createContext(null);

// ── Context-aware silence hints per language ──────────────────────────────
function getSilenceHint(language, silenceCount) {
  const isHi = language.startsWith("hi");
  const isBn = language.startsWith("bn");

  if (silenceCount === 1) {
    return isHi
      ? "मैं यहाँ हूँ। जब भी तैयार हों, बोलिए।"
      : isBn
      ? "আমি এখানে আছি। যখন প্রস্তুত হবেন, বলুন।"
      : "I'm here whenever you're ready. Just speak.";
  }

  // On 2nd+ silence, give a helpful prompt with available options
  const ctx = getActiveContext();
  if (ctx && ctx.options && ctx.options.length > 0) {
    const optionNames = ctx.options
      .slice(0, 3)
      .map(o => o.label || o.title || o.id)
      .filter(Boolean)
      .join(", ");
    return isHi
      ? `आप "${optionNames}" जैसा कुछ कह सकते हैं। या कहें: "घर चलो" या "मेरी दवाइयाँ दिखाओ"।`
      : isBn
      ? `আপনি "${optionNames}" বলতে পারেন। বা বলুন: "হোম পেজ" বা "আমার ওষুধ দেখাও"।`
      : `You can say things like: "${optionNames}". Or try: "Go home" or "Open brain games".`;
  }

  return isHi
    ? "आप कह सकते हैं: \"खेल खोलें\", \"दवाइयाँ दिखाओ\", या \"घर चलो\"।"
    : isBn
    ? "আপনি বলতে পারেন: \"গেম খুলুন\", \"ওষুধ দেখাও\", বা \"হোম পেজে যাও\"।"
    : "You can say: \"Open brain games\", \"Show my medicines\", or \"Go home\".";
}

export function VoiceAssistantProvider({ children, setPage }) {
  const i18n = useI18n();
  const language = i18n?.language || "en-IN";
  const t = i18n?.t || ((k, d) => d);

  const [voiceAssistantEnabled, setVoiceAssistantEnabled] = useState(false);
  const [assistantState, setAssistantState] = useState("off"); // off | idle | listening | understanding | speaking
  const [statusText, setStatusText] = useState("");
  const [transcript, setTranscript] = useState("");
  const [lastSpokeText, setLastSpokeText] = useState("");
  const [error, setError] = useState(null);

  const activeRecRef = useRef(null);
  const isSpeakingRef = useRef(false);
  const silenceCountRef = useRef(0);
  const enabledRef = useRef(false);

  // Sync ref with state to prevent stale closure bugs in async speech callbacks
  useEffect(() => {
    enabledRef.current = voiceAssistantEnabled;
  }, [voiceAssistantEnabled]);

  // Stop active speech recognition safely
  const abortListening = useCallback(() => {
    if (activeRecRef.current) {
      try {
        activeRecRef.current.onresult = null;
        activeRecRef.current.onerror = null;
        activeRecRef.current.onend = null;
        activeRecRef.current.stop();
      } catch (e) {
        // Ignore stop errors
      }
      activeRecRef.current = null;
    }
  }, []);

  // Safe wrapper around Text-to-Speech that ensures STT is OFF while speaking
  const speakResponse = useCallback((text, onEndCallback = null) => {
    if (!text) {
      onEndCallback?.();
      return;
    }

    // CRITICAL: Disable microphone recognition while assistant speaks
    abortListening();
    isSpeakingRef.current = true;
    setAssistantState("speaking");
    setLastSpokeText(text);
    setStatusText(text);

    speak(text, language, () => {
      isSpeakingRef.current = false;
      onEndCallback?.();
    });
  }, [language, abortListening]);

  // Chunked multi-sentence speech (for proactive announcements)
  const speakResponseChunked = useCallback((sentences, onEndCallback = null) => {
    if (!sentences || sentences.length === 0) {
      onEndCallback?.();
      return;
    }

    abortListening();
    isSpeakingRef.current = true;
    setAssistantState("speaking");
    const firstSentence = sentences[0] || "";
    setLastSpokeText(firstSentence);
    setStatusText(firstSentence);

    speakChunked(sentences, language, () => {
      isSpeakingRef.current = false;
      onEndCallback?.();
    });
  }, [language, abortListening]);

  // Main Listening Loop Window
  const startListeningWindow = useCallback(() => {
    if (!enabledRef.current || isSpeakingRef.current) return;

    abortListening();
    setError(null);
    setAssistantState("listening");
    setStatusText("Listening...");

    const recognitionInstance = listen(
      language,
      // 1. On speech transcript recognized
      (userText) => {
        if (!enabledRef.current) return;
        abortListening();
        silenceCountRef.current = 0;
        setTranscript(userText);
        setAssistantState("understanding");
        setStatusText(`Understanding: "${userText}"`);

        // Dispatch command to NLU & UI context
        setTimeout(async () => {
          if (!enabledRef.current) return;
          const result = dispatchVoiceCommand(userText, setPage, t);

          let replyText = "";
          if (result.handled) {
            replyText = result.speakText || result.label || "Done.";
          } else {
            // HELP fallback — describe available commands if intent unknown
            const lowerText = userText.toLowerCase();
            if (/help|what can|assist|what do i|what should|सहायता|সাহায্য/.test(lowerText)) {
              const ctx = getActiveContext();
              if (ctx?.options?.length > 0) {
                const names = ctx.options.map(o => o.label || o.title || o.id).filter(Boolean);
                replyText = `On this screen you can say: ${names.join(", ")}. Or say "go home" or "open brain games".`;
              } else {
                replyText = "You can say: Open brain games, Show my medicines, Open messages, or Go home.";
              }
            } else if (result.suggestedFallback) {
              // Use dispatcher's suggested fallback before trying AI
              replyText = result.suggestedFallback;
            } else {
              // Conversational fallback to NeuroBot AI
              try {
                const res = await submitChat(userText);
                replyText = res.answer || "I didn't quite catch that. You can say: go home, open brain games, or show medicines.";
              } catch (err) {
                replyText = `I didn't quite catch that. You can try saying: go home, open brain games, or show my medicines.`;
              }
            }
          }

          // Speak response, then reopen listening window when speech finishes!
          speakResponse(replyText, () => {
            if (enabledRef.current) {
              setTimeout(() => startListeningWindow(), 400);
            } else {
              setAssistantState("off");
            }
          });
        }, 150);
      },
      // 2. On speech recognition error or silence timeout
      (err) => {
        if (!enabledRef.current) return;
        abortListening();

        if (err && err.type === "NO_SPEECH") {
          silenceCountRef.current += 1;

          if (silenceCountRef.current <= 3) {
            // Give a context-aware hint prompt, then keep listening
            const hint = getSilenceHint(language, silenceCountRef.current);
            speakResponse(hint, () => {
              if (enabledRef.current) {
                setTimeout(() => startListeningWindow(), 400);
              }
            });
          } else {
            // After 4 silences, go idle (session still ON, mic off until next input)
            setAssistantState("idle");
            setStatusText(
              language.startsWith("hi")
                ? "🟢 वॉइस असिस्टेंट ऑन"
                : language.startsWith("bn")
                ? "🟢 ভয়েস সহকারী অন"
                : "🟢 Voice Assistant ON"
            );
            // Wake back up after 12 seconds of idle — check if user wants to continue
            setTimeout(() => {
              if (enabledRef.current && !isSpeakingRef.current) {
                silenceCountRef.current = 0;
                startListeningWindow();
              }
            }, 12000);
          }
        } else if (err && err.type === "NOT_ALLOWED") {
          setError(err);
          const deniedMsg = "I can't access the microphone right now. You can continue using the buttons.";
          speakResponse(deniedMsg, () => setAssistantState("idle"));
        } else {
          // Other transient errors — just reopen window
          setAssistantState("idle");
          setTimeout(() => {
            if (enabledRef.current && !isSpeakingRef.current) {
              startListeningWindow();
            }
          }, 800);
        }
      }
    );

    activeRecRef.current = recognitionInstance;
  }, [language, setPage, t, abortListening, speakResponse]);

  /**
   * Proactive page announcement — called by pages on mount.
   * Queues a contextual announcement after a short delay, then resumes listening.
   * Safe: no-op if voice is disabled. Cancels if user speaks first.
   */
  const announcePageContext = useCallback((text, sentences = null) => {
    if (!enabledRef.current) return;

    // Small mount delay — avoids clashing with ongoing speech from navigation
    setTimeout(() => {
      if (!enabledRef.current || isSpeakingRef.current) return;

      const done = () => {
        if (enabledRef.current) {
          setTimeout(() => startListeningWindow(), 400);
        }
      };

      if (sentences && sentences.length > 0) {
        speakResponseChunked(sentences, done);
      } else if (text) {
        speakResponse(text, done);
      }
    }, 700);
  }, [speakResponse, speakResponseChunked, startListeningWindow]);

  // Turn Voice Assistant ON
  const enableVoiceAssistant = useCallback(() => {
    playSelectSound();
    setVoiceAssistantEnabled(true);
    enabledRef.current = true;
    silenceCountRef.current = 0;

    const greetingMsg = language.startsWith("hi")
      ? "मैं यहाँ हूँ। मैं आपकी क्या मदद कर सकता हूँ?"
      : language.startsWith("bn")
      ? "আমি আছি। আমি আপনাকে কীভাবে সাহায্য করতে পারি?"
      : "I'm here! How can I help you today?";

    speakResponse(greetingMsg, () => {
      if (enabledRef.current) {
        setTimeout(() => startListeningWindow(), 300);
      }
    });
  }, [language, speakResponse, startListeningWindow]);

  // Turn Voice Assistant OFF
  const disableVoiceAssistant = useCallback(() => {
    playSelectSound();
    setVoiceAssistantEnabled(false);
    enabledRef.current = false;
    isSpeakingRef.current = false;
    silenceCountRef.current = 0;

    abortListening();
    stopSpeaking();
    setAssistantState("off");
    setStatusText("");
    setTranscript("");
  }, [abortListening]);

  // Toggle Voice Assistant ON/OFF
  const toggleVoiceAssistant = useCallback(() => {
    if (voiceAssistantEnabled) {
      disableVoiceAssistant();
    } else {
      enableVoiceAssistant();
    }
  }, [voiceAssistantEnabled, enableVoiceAssistant, disableVoiceAssistant]);

  // Process text manually (e.g. from input field or shortcut chip)
  const processCommandText = useCallback((rawText) => {
    if (!rawText) return;
    silenceCountRef.current = 0;
    setTranscript(rawText);
    setAssistantState("understanding");
    setStatusText(`Understanding: "${rawText}"`);

    setTimeout(async () => {
      const result = dispatchVoiceCommand(rawText, setPage, t);
      let replyText = "";
      if (result.handled) {
        replyText = result.speakText || result.label || "Done.";
      } else {
        try {
          const res = await submitChat(rawText);
          replyText = res.answer || "I didn't quite catch that. Try: go home, open brain games, or show medicines.";
        } catch (err) {
          replyText = `I didn't quite catch that. Try: go home, open brain games, or show medicines.`;
        }
      }

      speakResponse(replyText, () => {
        if (enabledRef.current) {
          setTimeout(() => startListeningWindow(), 400);
        }
      });
    }, 150);
  }, [setPage, t, speakResponse, startListeningWindow]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortListening();
      stopSpeaking();
    };
  }, [abortListening]);

  const value = {
    voiceAssistantEnabled,
    assistantState,
    statusText,
    transcript,
    lastSpokeText,
    error,
    toggleVoiceAssistant,
    enableVoiceAssistant,
    disableVoiceAssistant,
    processCommandText,
    speakResponse,
    speakResponseChunked,
    announcePageContext,
    startListeningWindow,
  };

  return (
    <VoiceAssistantContext.Provider value={value}>
      {children}
    </VoiceAssistantContext.Provider>
  );
}

export function useVoiceAssistant() {
  const context = useContext(VoiceAssistantContext);
  if (!context) {
    throw new Error("useVoiceAssistant must be used within a VoiceAssistantProvider");
  }
  return context;
}

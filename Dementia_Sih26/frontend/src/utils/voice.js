// Pre-warm SpeechSynthesis Voices cache
let cachedVoices = [];
function updateVoices() {
  if (typeof window !== "undefined" && "speechSynthesis" in window) {
    cachedVoices = window.speechSynthesis.getVoices() || [];
  }
}

if (typeof window !== "undefined" && "speechSynthesis" in window) {
  updateVoices();
  window.speechSynthesis.onvoiceschanged = updateVoices;
}

// ── Preferred neural/Google voice name patterns (priority order) ─────────
const PREFERRED_EN_VOICE_PATTERNS = [
  /google.*us.*english/i,
  /google.*uk.*english/i,
  /google.*en/i,
  /samantha/i,      // macOS natural voice
  /karen/i,         // macOS AU
  /victoria/i,      // macOS
  /daniel/i,        // macOS UK
  /google/i,        // any Google voice as fallback
];

function selectBestVoice(voices, langCode) {
  if (langCode === "hi") {
    return voices.find(v => v.lang.toLowerCase().includes("hi") || v.name.includes("हिन्दी") || v.name.includes("Hindi")) || null;
  }
  if (langCode === "bn" || langCode === "as") {
    return voices.find(v => v.lang.toLowerCase().includes("bn") || v.name.includes("বাংলা") || v.name.includes("Bengali"))
      || voices.find(v => v.lang.toLowerCase().includes("as"))
      || voices.find(v => v.lang.toLowerCase().includes("hi") || v.name.includes("Hindi"))
      || null;
  }
  if (langCode === "mni") {
    return voices.find(v => v.lang.toLowerCase().includes("hi") || v.name.includes("Hindi"))
      || voices.find(v => v.lang.toLowerCase().includes("bn") || v.name.includes("Bengali"))
      || null;
  }
  // English — prefer neural/Google voices, then regional English, then anything
  for (const pattern of PREFERRED_EN_VOICE_PATTERNS) {
    const found = voices.find(v => pattern.test(v.name));
    if (found) return found;
  }
  return voices.find(v => v.lang.toLowerCase().startsWith("en-in"))
    || voices.find(v => v.lang.toLowerCase().startsWith("en"))
    || voices[0]
    || null;
}

// ── Web Audio Chime Sound Effect ─────────────────────────────────────
export function playSelectSound() {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    if (ctx.state === "suspended") ctx.resume();

    const now = ctx.currentTime;
    
    // Tone 1: Warm D5 note
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = "sine";
    osc1.frequency.setValueAtTime(587.33, now);
    gain1.gain.setValueAtTime(0.12, now);
    gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
    osc1.connect(gain1);
    gain1.connect(ctx.destination);
    osc1.start(now);
    osc1.stop(now + 0.25);

    // Tone 2: Crisp A5 harmonic chime
    const osc2 = ctx.createOscillator();
    const gain2 = ctx.createGain();
    osc2.type = "sine";
    osc2.frequency.setValueAtTime(880.00, now + 0.07);
    gain2.gain.setValueAtTime(0.15, now + 0.07);
    gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.40);
    osc2.connect(gain2);
    gain2.connect(ctx.destination);
    osc2.start(now + 0.07);
    osc2.stop(now + 0.40);
  } catch (e) {
    // Fallback for restricted audio contexts
  }
}

// ── Robust SpeechSynthesis Vocalizer (Hindi, Assamese, Bengali, Meitei, English) ──
let speakTimer = null;

export function stopSpeaking() {
  if (speakTimer) {
    clearTimeout(speakTimer);
    speakTimer = null;
  }
  if (typeof window !== "undefined" && "speechSynthesis" in window) {
    try {
      window.speechSynthesis.cancel();
    } catch (e) {
      console.error("Error stopping speech:", e);
    }
  }
}

export function speak(text, language = "en-IN", onEnd = null) {
  if (!text || typeof text !== "string") {
    onEnd?.();
    return false;
  }
  const cleanText = text.trim();
  if (!cleanText) {
    onEnd?.();
    return false;
  }

  if (typeof window === "undefined" || !("speechSynthesis" in window)) {
    onEnd?.();
    return false;
  }

  try {
    // If speech engine is currently active, cancel previous speech
    if (speakTimer) {
      clearTimeout(speakTimer);
      speakTimer = null;
    }
    if (window.speechSynthesis.speaking || window.speechSynthesis.pending) {
      window.speechSynthesis.cancel();
    }

    // 40ms timeout ensures cancel() completes cleanly without triggering blinking/stuttering
    speakTimer = setTimeout(() => {
      try {
        const utterance = new SpeechSynthesisUtterance(cleanText);
        // Warm, natural pace — 0.97 sounds conversational without being too fast for elderly
        utterance.rate = 0.97;
        // Slightly higher pitch (1.05) gives a friendlier, warmer tone
        utterance.pitch = 1.05;
        utterance.volume = 1.0;

        const langCode = (language || "en-IN").split("-")[0].toLowerCase();
        const voices = cachedVoices.length > 0 ? cachedVoices : window.speechSynthesis.getVoices();

        const matchedVoice = selectBestVoice(voices, langCode);
        const fallbackLangMap = { hi: "hi-IN", bn: "bn-IN", as: "as-IN", mni: "hi-IN" };
        const effectiveLangTag = matchedVoice
          ? matchedVoice.lang
          : (fallbackLangMap[langCode] || "en-IN");

        // CRITICAL: utterance.lang MUST match matchedVoice.lang to prevent Chrome abort
        utterance.lang = effectiveLangTag;
        if (matchedVoice) {
          utterance.voice = matchedVoice;
        }

        let hasFinished = false;
        const finishSpeech = () => {
          if (!hasFinished) {
            hasFinished = true;
            onEnd?.();
          }
        };

        utterance.onend = () => finishSpeech();
        utterance.onerror = (e) => {
          console.warn("SpeechSynthesis utterance error:", e);
          finishSpeech();
        };

        window.speechSynthesis.speak(utterance);
      } catch (innerErr) {
        console.error("Inner speak error:", innerErr);
        onEnd?.();
      } finally {
        speakTimer = null;
      }
    }, 40);

    return true;
  } catch (err) {
    console.error("Outer speak error:", err);
    onEnd?.();
    return false;
  }
}

// ── Chunked Speech — speaks sentences with natural pauses between them ───
// Accepts an array of strings. Plays them sequentially with a 220ms gap.
// Cancellable via stopSpeaking(). Calls onEnd when all sentences finish.
export function speakChunked(sentences, language = "en-IN", onEnd = null) {
  if (!sentences || sentences.length === 0) {
    onEnd?.();
    return;
  }

  const remaining = [...sentences.filter(Boolean)];

  function playNext() {
    if (remaining.length === 0) {
      onEnd?.();
      return;
    }
    const sentence = remaining.shift();
    speak(sentence, language, () => {
      if (remaining.length > 0) {
        // Natural inter-sentence pause
        setTimeout(playNext, 220);
      } else {
        onEnd?.();
      }
    });
  }

  playNext();
}

// ── Multi-Stage Web Speech Recognition with Language Fallback ──────
export function listen(language, onText, onError) {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!Recognition) {
    onError?.({ type: "UNSUPPORTED", message: "Browser speech recognition API is unsupported." });
    return null;
  }

  let recognition = new Recognition();
  let primaryLang = language || "en-IN";
  let fallbackLangs = ["bn-IN", "hi-IN", "en-IN", "en-US"];
  let triedLangs = [primaryLang];

  function startRecognition(langToUse) {
    try {
      recognition.lang = langToUse;
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;

      recognition.onresult = (event) => {
        if (event.results && event.results[0] && event.results[0][0]) {
          const transcript = event.results[0][0].transcript;
          onText?.(transcript);
        }
      };

      recognition.onerror = (event) => {
        console.warn(`Speech recognition notice on ${langToUse}:`, event.error);
        
        // On language-not-supported or network issue, attempt regional language fallback
        if ((event.error === "language-not-supported" || event.error === "network") && fallbackLangs.length > 0) {
          const nextLang = fallbackLangs.shift();
          if (!triedLangs.includes(nextLang)) {
            triedLangs.push(nextLang);
            try { recognition.stop(); } catch (e) {}
            recognition = new Recognition();
            startRecognition(nextLang);
            return;
          }
        }

        if (event.error === "no-speech") {
          onError?.({ type: "NO_SPEECH", message: "No speech detected." });
        } else if (event.error === "not-allowed") {
          onError?.({ type: "NOT_ALLOWED", message: "Microphone permission denied." });
        } else {
          onError?.({ type: event.error, message: `Voice notice: ${event.error}` });
        }
      };

      recognition.start();
    } catch (err) {
      onError?.({ type: "EXCEPTION", message: err.message });
    }
  }

  startRecognition(primaryLang);
  return recognition;
}

// ── Multi-lingual Voice Intent Recognition Engine ───────────────────────
export function detectIntent(text) {
  const value = (text || "").toLowerCase();
  
  // Games & Brain Training
  if (/start|play|game|खेल|खेलক|শুরু|আৰম্ভ|শান্নব/.test(value)) {
    return { type: "START_GAME", text: value };
  }
  // Repeat instructions
  if (/repeat|again|instruction|दोहर|আকৌ|পুনৰ|তাকপা/.test(value)) {
    return { type: "REPEAT_INSTRUCTION" };
  }
  // Hydration & Water
  if (/water|hydration|drink|पानी|পানী|জল|ঈশিং/.test(value)) {
    return { type: "HYDRATION" };
  }
  // Daily routine / Reminders
  if (/routine|schedule|care|meds|medicine|दिनचर्या|ৰুটিন|যত্ন/.test(value)) {
    return { type: "ROUTINE" };
  }
  // Task completion mark
  if (/done|complete|taken|पूरा|সম্পূৰ্ণ|লোইরে/.test(value)) {
    return { type: "REMINDER_ACK" };
  }

  return { type: "OBJECT_ANSWER", answer: value };
}

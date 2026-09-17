/**
 * voiceDispatcher.js — Global Context-Aware Voice Command Dispatcher
 * ===================================================================
 * Bridges Natural Language Understanding (NLU), active UI context,
 * page reading, and global React Router navigation.
 */
import { parseNaturalIntent } from "./nluEngine";
import { extractPageSummary } from "./pageReader";

let activeContext = {
  name: "global",
  handler: null,
  options: [],
};

/**
 * Active screen/component registers its voice context & visible options
 */
export function registerVoiceContext(name, handler, options = []) {
  activeContext = { name, handler, options };
  return () => {
    if (activeContext.name === name) {
      activeContext = { name: "global", handler: null, options: [] };
    }
  };
}

export function getActiveContext() {
  return activeContext;
}

/**
 * Dispatch spoken transcript text through NLU engine to local UI actions or global router
 */
export function dispatchVoiceCommand(rawText, setPage, t = (k, d) => d) {
  if (!rawText || typeof rawText !== "string") {
    return { handled: false, message: "Empty command" };
  }

  const parsed = parseNaturalIntent(rawText, activeContext);

  // 1. Try local component handler with parsed intent first
  if (activeContext.handler) {
    const handledLocally = activeContext.handler(rawText, parsed);
    if (handledLocally) {
      let localSpeakText = "Done.";
      if (typeof handledLocally === "object" && handledLocally.speakText) {
        localSpeakText = handledLocally.speakText;
      } else if (parsed.intent === "REPLAY") {
        localSpeakText = "Sure. I'll play it again.";
      } else if (parsed.intent === "ANOTHER_SONG") {
        localSpeakText = "Of course. Here's another song.";
      } else if (parsed.intent === "SELECT_OPTION" && parsed.extractedData?.option) {
        const optLabel = parsed.extractedData.option.label || parsed.extractedData.option.id || "";
        localSpeakText = `You selected ${optLabel}.`;
      } else if (parsed.intent === "MOOD_HAPPY") {
        localSpeakText = "That's nice. I've selected Happy.";
      } else if (parsed.intent === "MOOD_CALM") {
        localSpeakText = "You selected Calm.";
      } else if (parsed.intent === "MOOD_FAMILIAR") {
        localSpeakText = "You selected Familiar.";
      } else if (parsed.intent === "RHYTHM_MENU") {
        localSpeakText = "Sure. Going back to the music menu.";
      }

      return {
        handled: true,
        context: activeContext.name,
        intent: parsed.intent,
        extractedData: parsed.extractedData,
        speakText: localSpeakText,
        label: localSpeakText,
      };
    }
  }

  // 2. READ PAGE intent
  if (parsed.intent === "READ_PAGE") {
    const pageSummary = extractPageSummary();
    return {
      handled: true,
      action: "READ_PAGE",
      speakText: pageSummary,
      label: pageSummary,
    };
  }

  // 3. HELP intent — read available options for the active screen
  if (parsed.intent === "HELP") {
    let helpText = "";
    if (activeContext.options && activeContext.options.length > 0) {
      const names = activeContext.options
        .map(o => o.label || o.title || o.id)
        .filter(Boolean)
        .join(", ");
      helpText = `On this screen you can say: ${names}. You can also say: go home, open brain games, or show my medicines.`;
    } else {
      helpText = "You can say things like: Open brain games, Show my medicines, Open messages, Read this page, or Go home. Just speak naturally.";
    }
    return { handled: true, action: "HELP", speakText: helpText, label: helpText };
  }

  // 3. Global Navigation Intent Mapping
  switch (parsed.intent) {
    case "MEDICINES":
      if (setPage) setPage("daily-care");
      return {
        handled: true,
        action: "NAVIGATE",
        page: "daily-care",
        speakText: "Of course. I'll take you to your medicines.",
        label: "Of course. I'll take you to your medicines.",
      };

    case "APPOINTMENTS":
      if (setPage) setPage("doctors");
      return {
        handled: true,
        action: "NAVIGATE",
        page: "doctors",
        speakText: "Of course. Here are your appointments.",
        label: "Of course. Here are your appointments.",
      };

    case "GAMES":
      if (setPage) setPage("games");
      return {
        handled: true,
        action: "NAVIGATE",
        page: "games",
        speakText: "Opening brain games for you.",
        label: "Opening brain games for you.",
      };

    case "RHYTHM_RECALL":
    case "START_SONG":
      if (setPage) setPage("game-rhythm-recall");
      return {
        handled: true,
        action: "NAVIGATE",
        page: "game-rhythm-recall",
        speakText: "Of course. Let's open Rhythm and Recall.",
        label: "Of course. Let's open Rhythm and Recall.",
      };

    case "GO_HOME":
      if (setPage) setPage("dashboard");
      return {
        handled: true,
        action: "NAVIGATE",
        page: "dashboard",
        speakText: "Of course. Going home.",
        label: "Of course. Going home.",
      };

    case "MESSAGES":
      if (setPage) setPage("messages");
      return {
        handled: true,
        action: "NAVIGATE",
        page: "messages",
        speakText: "Opening your messages.",
        label: "Opening your messages.",
      };

    case "ASSESSMENTS":
      if (setPage) setPage("assessments");
      return {
        handled: true,
        action: "NAVIGATE",
        page: "assessments",
        speakText: "Opening your health assessments.",
        label: "Opening your health assessments.",
      };

    case "RESULTS":
      if (setPage) setPage("results");
      return {
        handled: true,
        action: "NAVIGATE",
        page: "results",
        speakText: "Opening your results.",
        label: "Opening your results.",
      };

    case "GO_BACK":
      window.dispatchEvent(new CustomEvent("neuroaid:go-back"));
      return {
        handled: true,
        action: "GO_BACK",
        speakText: "Sure. Going back.",
        label: "Sure. Going back.",
      };

    case "AMBIGUOUS_NAV":
      return {
        handled: true,
        action: "CLARIFY",
        speakText: "Would you like Medicines, Appointments, or Brain Games?",
        label: "Would you like Medicines, Appointments, or Brain Games?",
      };

    default:
      // Broadcast fallback event for custom page handlers
      window.dispatchEvent(new CustomEvent("neuroaid:voice-command", { detail: { text: rawText, parsed } }));
      return {
        handled: false,
        parsed,
        // Suggest the fallback message so VoiceAssistantContext can use it
        suggestedFallback: "I didn't quite catch that. You can say: go home, open brain games, or show my medicines.",
      };
  }
}

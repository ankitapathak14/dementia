/**
 * nluEngine.js — Natural Language Understanding Engine for NeuroAid
 * =================================================================
 * Parses natural conversational phrasing in English, Hindi, Bengali,
 * and Assamese into structured intents, confidence scores, and entities.
 * Understands what the user MEANS, not merely exact string matching.
 */

export function parseNaturalIntent(rawText, currentContext = {}) {
  if (!rawText || typeof rawText !== "string") {
    return { intent: "UNKNOWN", confidence: 0.0, rawText: "" };
  }

  const text = rawText.trim().toLowerCase();

  // 1. Check current screen visible options & relative position references first
  if (currentContext.options && currentContext.options.length > 0) {
    const matchedOption = matchOptionFromContext(text, currentContext.options);
    if (matchedOption) {
      return {
        intent: "SELECT_OPTION",
        confidence: 0.95,
        extractedData: { option: matchedOption },
        rawText,
      };
    }
  }

  // 2. Relative & Numeric Option Selection
  const ordinalMatch = matchOrdinalOption(text, currentContext.options || []);
  if (ordinalMatch) {
    return {
      intent: "SELECT_OPTION",
      confidence: 0.92,
      extractedData: { option: ordinalMatch },
      rawText,
    };
  }

  // 3. READ PAGE / Read Screen
  if (
    /read (this|the) (page|screen)|read for me|tell me what|what is (on|this)|what's on (this|the)|পঢ়ক|পড়ে শোনাও|पढ़कर सुनाओ/.test(text)
  ) {
    return { intent: "READ_PAGE", confidence: 0.95, rawText };
  }

  // 4. MUSIC REPLAY / Play Again / Listen Again
  if (
    /replay|play.*again|hear.*again|listen.*again|repeat|once more|one more time|play that again|can you play that again|story again|কাহিনী আকৌ|আবার গল্প|আবার বাজাও|फिर से कहानी|फिर से बजाओ/.test(text) &&
    !text.includes("game")
  ) {
    return { intent: "REPLAY", confidence: 0.94, extractedData: { target: "current_item" }, rawText };
  }

  // 5. ANOTHER SONG / Next Song
  if (
    /another (song|music|tune|one)|next (song|tune|one)|try another|different song|something else|hear another|অন্য গান|दूसरा गाना/.test(text)
  ) {
    return { intent: "ANOTHER_SONG", confidence: 0.94, extractedData: { target: "next_song" }, rawText };
  }

  // 6. RHYTHM & RECALL MENU / Exit Session / Back to Music Menu
  if (
    /music menu|rhythm menu|back to.*menu|music hub|done with music|exit music|মেইন মেনু|music main menu/.test(text)
  ) {
    return { intent: "RHYTHM_MENU", confidence: 0.93, rawText };
  }

  // 7. GO BACK
  if (
    /go back|take me back|previous (page|screen)|return|i'd like to go back|পিছলৈ|ফিরে যাও|पीछे जाओ/.test(text) &&
    !text.includes("menu")
  ) {
    return { intent: "GO_BACK", confidence: 0.95, rawText };
  }

  // 8. GO HOME / Dashboard
  if (
    /take me home|go home|home (page|screen)|main dashboard|going home|ঘৰলৈ|হোম পেজ|घर चलो/.test(text)
  ) {
    return { intent: "GO_HOME", confidence: 0.96, rawText };
  }

  // 9. MEDICINES / Daily Routine
  if (
    /medicine|medication|pill|dosage|routine|daily care|check my medicine|need to take|ঔষধ|ওষুধ|দবা|दवा|दिनचर्या/.test(text)
  ) {
    return { intent: "MEDICINES", confidence: 0.92, rawText };
  }

  // 10. APPOINTMENTS / Doctors / Schedule
  if (
    /appointment|doctor|physician|consultation|schedule|anything scheduled|where i need to go|হস্পিতাল|ডাক্তৰ|डॉक्टर|अस्पताल|नियुक्ति/.test(text)
  ) {
    return { intent: "APPOINTMENTS", confidence: 0.93, rawText };
  }

  // 11. GAMES / Brain Games / Rhythm & Recall / Voice of the Village
  if (
    /game|play|something to play|rhythm and recall|brain training|music game|voice of the village|village|গাঁৱৰ|গাँव|খেল|গেম|खेल/.test(text)
  ) {
    if (text.includes("village") || text.includes("গাঁৱৰ") || text.includes("গাँव") || text.includes("খুঙ্গং")) {
      return { intent: "VOICE_VILLAGE", confidence: 0.96, rawText };
    }
    if (text.includes("rhythm") || text.includes("recall") || text.includes("music")) {
      return { intent: "RHYTHM_RECALL", confidence: 0.95, rawText };
    }
    return { intent: "GAMES", confidence: 0.92, rawText };
  }

  // 12. PLAY A SONG / Start Song
  if (
    /play a song|listen to (a|some) song|listen to music|play music| गाना सुनाओ|গান শোনাও/.test(text)
  ) {
    return { intent: "START_SONG", confidence: 0.94, rawText };
  }

  // 13. MESSAGES / Caregiver
  if (
    /message|chat|talk to caregiver|talk to doctor|কথা পাতক|কথা বলো|बात करो/.test(text)
  ) {
    return { intent: "MESSAGES", confidence: 0.91, rawText };
  }

  // 14. RESULTS / Progress
  if (
    /result|score|progress|how am i doing|ফলাফল|রিপোর্ট/.test(text)
  ) {
    return { intent: "RESULTS", confidence: 0.90, rawText };
  }

  // 15. PLAYBACK CONTROLS
  if (/pause|रुक|থামাও/.test(text)) {
    return { intent: "PAUSE", confidence: 0.90, rawText };
  }
  if (/resume|continue|चालu|जारी रखो/.test(text)) {
    return { intent: "RESUME", confidence: 0.90, rawText };
  }
  if (/stop|बंद/.test(text)) {
    return { intent: "STOP", confidence: 0.90, rawText };
  }

  // 16. CONFIRMATIONS
  if (/yes|sure|okay|yep|do it|হব|হ্যাঁ|हाँ/.test(text)) {
    return { intent: "CONFIRM_YES", confidence: 0.95, rawText };
  }
  if (/no|cancel|never mind|don't|নাহ|না|नहीं/.test(text)) {
    return { intent: "CONFIRM_NO", confidence: 0.95, rawText };
  }

  // 17. HELP
  if (/help|what can i do|assist|सहायता|সাহায্য/.test(text)) {
    return { intent: "HELP", confidence: 0.95, rawText };
  }

  // Mood selections when mentioned directly
  if (/happy|joy|cheerful|ভাল|খুশি|खुश/.test(text)) {
    return { intent: "MOOD_HAPPY", confidence: 0.92, rawText };
  }
  if (/calm|relax|peace|শান্ত|शान्त/.test(text)) {
    return { intent: "MOOD_CALM", confidence: 0.92, rawText };
  }
  if (/familiar|known|remember|পৰিচিত|পরিচিত|जाना पहचाना/.test(text)) {
    return { intent: "MOOD_FAMILIAR", confidence: 0.92, rawText };
  }

  // Ambiguous query needing clarification
  if (text.length > 3 && (/show|open|take me|where|can I|i want/.test(text))) {
    return { intent: "AMBIGUOUS_NAV", confidence: 0.45, rawText };
  }

  return { intent: "UNKNOWN", confidence: 0.20, rawText };
}

/**
 * Match semantic option labels against visible option objects
 */
function matchOptionFromContext(text, options) {
  for (const opt of options) {
    const label = (opt.label || opt.title || opt.id || "").toLowerCase();
    const id = (opt.id || "").toLowerCase();

    if (label && text.includes(label)) return opt;
    if (id && text.includes(id)) return opt;

    // Semantic synonym matching for mood options
    if (id === "happy" && (/happy|joy|cheerful|ভাল|খুশি|खुश/.test(text))) return opt;
    if (id === "calm" && (/calm|relax|peace|শান্ত|शान्त/.test(text))) return opt;
    if (id === "familiar" && (/familiar|known|remember|পৰিচিত|পরিচিত|जाना पहचाना/.test(text))) return opt;
    if (id === "neutral" && (/neutral|okay|normal|স্বাভাবিক|सामान्य/.test(text))) return opt;
    if (id === "uncomfortable" && (/uncomfortable|sad|bad|অস্বস্তি|असहज/.test(text))) return opt;
  }
  return null;
}

/**
 * Match ordinal references ("first one", "second option", "middle one", "last one")
 */
function matchOrdinalOption(text, options) {
  if (!options || options.length === 0) return null;

  if (/first|1st|option 1|number 1|one|প্ৰথম|প্রথম|पहला/.test(text)) {
    return options[0] || null;
  }
  if (/second|2nd|option 2|number 2|two|দ্বিতীয়|दूसरा/.test(text)) {
    return options[1] || null;
  }
  if (/third|3rd|option 3|number 3|three|তৃতীয়|तीसरा/.test(text)) {
    return options[2] || null;
  }
  if (/fourth|4th|option 4|number 4|four|চতুৰ্থ|चौथा/.test(text)) {
    return options[3] || null;
  }
  if (/fifth|5th|option 5|number 5|five|পঞ্চম|पांचवां/.test(text)) {
    return options[4] || null;
  }
  if (/middle|center|মাজৰ|মাঝের|बीच वाला/.test(text)) {
    const midIdx = Math.floor(options.length / 2);
    return options[midIdx] || null;
  }
  if (/last|final|শেহৰ|শেষের|आखिरी/.test(text)) {
    return options[options.length - 1] || null;
  }

  return null;
}

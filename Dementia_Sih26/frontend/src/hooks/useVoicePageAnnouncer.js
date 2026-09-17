/**
 * useVoicePageAnnouncer — Proactive Page Announcement Hook
 * =========================================================
 * Drop this hook into any page/component to have the voice assistant
 * automatically announce contextual information when a new screen opens.
 *
 * Usage:
 *   // Single sentence:
 *   useVoicePageAnnouncer("Welcome to Brain Games! Say a game name to begin.");
 *
 *   // Multiple sentences (delivered with natural pauses):
 *   useVoicePageAnnouncer(null, [
 *     "Rhythm and Recall is open.",
 *     "Option one is Recognize the Song.",
 *     "Option two is Memory Connection.",
 *     "Which would you like?",
 *   ]);
 *
 * Rules:
 * - No-op if voice assistant is OFF.
 * - Single-fire per mount. Automatically cancelled on unmount.
 * - Waits 700ms before speaking (avoids clashing with ongoing navigation speech).
 * - Does NOT interrupt ongoing speech — queues via announcePageContext() which
 *   checks isSpeakingRef internally.
 */
import { useEffect, useRef } from "react";
import { useVoiceAssistant } from "../context/VoiceAssistantContext";

/**
 * @param {string|null} text - Single announcement text (or null if using sentences[])
 * @param {string[]|null} sentences - Array of sentences for chunked delivery
 */
export function useVoicePageAnnouncer(text, sentences = null) {
  const { voiceAssistantEnabled, announcePageContext } = useVoiceAssistant();
  const firedRef = useRef(false);

  useEffect(() => {
    // Only announce once per mount; only when assistant is on
    if (!voiceAssistantEnabled || firedRef.current) return;
    if (!text && (!sentences || sentences.length === 0)) return;

    firedRef.current = true;

    // announcePageContext handles the 700ms delay and isSpeaking guard internally
    announcePageContext(text, sentences);

    return () => {
      // Cleanup: if unmounted before the timeout fires, mark as not fired
      // so the next mount can announce correctly
      firedRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [voiceAssistantEnabled]);
  // Note: intentionally only re-runs on voiceAssistantEnabled change, not on text change.
  // Page announcements should be stable strings, not dynamic.
}

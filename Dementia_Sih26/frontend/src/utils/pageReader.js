/**
 * pageReader.js — Onscreen Content Extractor for Accessibility
 * ============================================================
 * Extracts key visible headers, subtext, instructions, and cards from the DOM
 * to format concise, spoken text for elderly users when "Read this page" is invoked.
 */

export function extractPageSummary() {
  if (typeof document === "undefined") return "Onscreen content unavailable.";

  const elements = [];

  // 1. Main Page Title (H1 / H2)
  const mainTitle = document.querySelector("h1, h2");
  if (mainTitle && mainTitle.textContent) {
    const titleText = mainTitle.textContent.trim();
    if (titleText) elements.push(`Page: ${titleText}`);
  }

  // 2. Onscreen Instructions or Subtext
  const subtext = document.querySelector("p");
  if (subtext && subtext.textContent) {
    const pText = subtext.textContent.trim();
    if (pText && pText.length < 150) elements.push(pText);
  }

  // 3. Visible Question / Card Prompts
  const questionEl = document.querySelector("[role='dialog'] h3, [role='status'], .font-bold");
  if (questionEl && questionEl.textContent) {
    const qText = questionEl.textContent.trim();
    if (qText && !elements.includes(qText) && qText.length < 120) {
      elements.push(qText);
    }
  }

  // 4. Visible Active Buttons or Options
  const optionButtons = Array.from(document.querySelectorAll("button"))
    .map(btn => btn.textContent ? btn.textContent.trim() : "")
    .filter(txt => txt && txt.length > 2 && txt.length < 35 && !txt.includes("Back") && !txt.includes("✕"))
    .slice(0, 5);

  if (optionButtons.length > 0) {
    elements.push(`Available options are: ${optionButtons.join(", ")}.`);
  }

  if (elements.length === 0) {
    return "This screen contains NeuroAid navigation tools and interactive features.";
  }

  return elements.join(". ");
}

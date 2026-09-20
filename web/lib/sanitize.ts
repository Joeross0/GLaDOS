export function sanitizeSpokenText(text: string): string {
  if (!text.trim()) return "";
  let cleaned = collapseSpacedLetters(text);
  cleaned = cleaned.replace(/[\n\r]+/g, " ");
  cleaned = cleaned.replace(/\s*[—–−\-]{1,3}\s*/g, ", ");
  cleaned = cleaned.replace(/\s*;\s*/g, ". ");
  cleaned = cleaned.replace(/\s*:\s*/g, ", ");
  cleaned = cleaned.replace(/\s+([,.!?])/g, "$1");
  cleaned = cleaned.replace(/([.!?])([A-Za-z])/g, "$1 $2");
  cleaned = cleaned.replace(/,+/g, ",").replace(/\s+/g, " ").trim();
  const contractions: [RegExp, string][] = [
    [/\bdont\b/gi, "don't"],
    [/\bwont\b/gi, "won't"],
    [/\bcant\b/gi, "can't"],
    [/\bim\b/gi, "I'm"],
    [/\bwhats\b/gi, "what's"],
    [/\bthats\b/gi, "that's"],
  ];
  for (const [pattern, replacement] of contractions) {
    cleaned = cleaned.replace(pattern, replacement);
  }
  cleaned = cleaned.replace(/\bi\b/g, "I");
  return capitalizeSentences(cleaned);
}

function collapseSpacedLetters(text: string): string {
  return text.replace(
    /(?<![A-Za-z])(?:[A-Za-z](?:[\s.\-]+)){2,}[A-Za-z](?![A-Za-z])/g,
    (match) => match.replace(/[^A-Za-z]/g, ""),
  );
}

function capitalizeSentences(text: string): string {
  return text
    .split(/(?<=[.!?])\s+/)
    .map((piece) => {
      const trimmed = piece.trim();
      if (!trimmed) return "";
      return trimmed[0].toUpperCase() + trimmed.slice(1);
    })
    .filter(Boolean)
    .join(" ");
}

export function sanitizeSpokenText(text: string): string {
  if (!text.trim()) return "";
  let cleaned = collapseSpacedLetters(text);
  cleaned = collapseSingleLetterRun(cleaned);
  cleaned = cleaned.replace(/[\n\r]+/g, " ");
  cleaned = cleaned.replace(/\s*[—–−\-]{1,3}\s*/g, ", ");
  cleaned = cleaned.replace(/\s*;\s*/g, ". ");
  cleaned = cleaned.replace(/\s*:\s*/g, ", ");
  cleaned = insertClauseCommas(cleaned);
  cleaned = cleaned.replace(/\s+([,.!?])/g, "$1");
  cleaned = cleaned.replace(/([.!?])([A-Za-z])/g, "$1 $2");
  cleaned = cleaned.replace(/,+/g, ",").replace(/\s+/g, " ").trim();
  const contractions: [RegExp, string][] = [
    [/\bdont\b/gi, "don't"],
    [/\bwont\b/gi, "won't"],
    [/\bcant\b/gi, "can't"],
    [/\bim\b/gi, "I'm"],
    [/\bive\b/gi, "I've"],
    [/\bill\b/gi, "I'll"],
    [/\byoure\b/gi, "you're"],
    [/\btheyre\b/gi, "they're"],
    [/\bwhats\b/gi, "what's"],
    [/\bthats\b/gi, "that's"],
    [/\bheres\b/gi, "here's"],
    [/\bhows\b/gi, "how's"],
    [/\bwheres\b/gi, "where's"],
  ];
  for (const [pattern, replacement] of contractions) {
    cleaned = cleaned.replace(pattern, replacement);
  }
  cleaned = cleaned.replace(/\bi\b/g, "I");
  cleaned = capitalizeSentences(cleaned);
  if (looksLikeKeysmash(cleaned)) return "";
  return cleaned;
}

export function chunkSpokenText(raw: string, alreadySpoken: string[] = []): string[] {
  let sentence = raw.replace(/\*.*?\*|\(.*?\)/g, "");
  sentence = sanitizeSpokenText(sentence);
  sentence = sentence.replace(/:/g, ".");
  const spoken: string[] = [];
  for (const piece of splitSpokenSentences(sentence)) {
    if (/^[A-Za-z][.!?]?$/.test(piece)) continue;
    if (isSilenceReply(piece)) break;
    if (isGluedNonsense(piece)) continue;
    if (isRepetitive(piece, [...alreadySpoken, ...spoken])) continue;
    if (spoken.length >= 12) break;
    spoken.push(piece);
  }
  return spoken;
}

function collapseSpacedLetters(text: string): string {
  return text.replace(
    /(?<![A-Za-z])(?:[A-Za-z](?:[\s.\-]+)){2,}[A-Za-z](?![A-Za-z])/g,
    (match) => match.replace(/[^A-Za-z]/g, ""),
  );
}

function collapseSingleLetterRun(text: string): string {
  return text.replace(/(?<![A-Za-z])(?:[A-Za-z]\s+){2,}[A-Za-z](?![A-Za-z])/g, (match) => match.replace(/\s+/g, ""));
}

function insertClauseCommas(text: string): string {
  return text
    .split(/(?<=[.!?])\s+/)
    .map((sentence) => {
      if (sentence.includes(",") || sentence.split(/\s+/).length < 10) return sentence;
      return sentence.replace(
        /^((?:\S+\s+){4,}\S+)\s+(and|but|so|because|though|which|while)\b/i,
        "$1, $2",
      );
    })
    .join(" ");
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

function splitSpokenSentences(sentence: string): string[] {
  if (!sentence || sentence === ".") return [];
  const pieces = sentence.split(/(?<=[.!?])\s+/);
  const broken: string[] = [];
  for (const piece of pieces) {
    const words = piece.split(/\s+/);
    if (piece.includes(",") && words.length >= 10) {
      broken.push(...piece.split(/(?<=,)\s+/).map((part) => part.trim()).filter(Boolean));
    } else {
      broken.push(piece);
    }
  }
  return broken.map((piece) => piece.trim()).filter((piece) => piece && piece !== ".");
}

function isSilenceReply(sentence: string): boolean {
  const normalized = sentence.toLowerCase().replace(/[^a-z]+/g, " ").trim();
  return ["silence", "do nothing", "do nothing tool", "nothing", "no action", "pass"].includes(normalized);
}

function isGluedNonsense(sentence: string): boolean {
  const letters = [...sentence].filter((char) => /[A-Za-z]/.test(char)).length;
  const spaces = sentence.split(" ").length - 1;
  if (letters >= 28 && spaces < Math.max(2, Math.floor(letters / 14))) return true;
  const lower = sentence.toLowerCase();
  return [
    "wheatley",
    "end credits",
    "i am really sorry",
    "uservoice",
    "assistantvoice",
    "i mean",
    "wouldn't that",
    "connecting you to",
    "bunch of cameras",
    "okay?",
  ].some((mark) => lower.includes(mark));
}

function isRepetitive(sentence: string, recent: string[]): boolean {
  const norm = sentence.toLowerCase().replace(/[^a-z]+/g, " ").trim();
  return recent.some((previous) => previous.toLowerCase().replace(/[^a-z]+/g, " ").trim() === norm);
}

function looksLikeKeysmash(text: string): boolean {
  const letters = text.replace(/[^a-zA-Z]/g, "");
  const spaces = (text.match(/ /g) || []).length;
  if (letters.length >= 40 && spaces < 3) return true;
  const words = text.match(/[A-Za-z]+/g) || [];
  if (words.length >= 8) {
    const vowels = [...letters].filter((ch) => "aeiouAEIOU".includes(ch)).length / Math.max(letters.length, 1);
    if (vowels < 0.22) return true;
  }
  return false;
}

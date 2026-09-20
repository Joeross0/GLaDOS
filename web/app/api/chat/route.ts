import { NextResponse } from "next/server";
import { completeOnRunPod } from "@/lib/runpod";
import { chunkSpokenText, sanitizeSpokenText } from "@/lib/sanitize";

export const maxDuration = 60;

const SYSTEM =
  "You are GLaDOS only. Not Wheatley. Write normal English with a space between every word. " +
  "Never spell a word as separate letters. Six to twelve complete sentences. Stay on the last remark. " +
  "Calm facility PA, then a petty scientific insult. Do not say I mean, okay, or mate. " +
  "Do not apologize. Do not glue words together. This web session is separate from any desktop session.";

type ChatTurn = { role?: string; content?: string };

export async function POST(request: Request) {
  const body = (await request.json()) as {
    message?: string;
    vision?: string;
    history?: ChatTurn[];
    camera?: boolean;
  };

  const message = (body.message || "").trim();
  if (!message) {
    return NextResponse.json({ error: "Say something." }, { status: 400 });
  }

  const history = (body.history || [])
    .filter((turn) => (turn.role === "user" || turn.role === "assistant") && turn.content)
    .slice(-12)
    .map((turn) => ({ role: turn.role as string, content: String(turn.content).slice(0, 900) }));

  let system = SYSTEM;
  if (body.camera) {
    system += " This is a camera update. Four to eight sentences about the real scene. Do not reply SILENCE.";
  }
  if (body.vision) {
    system += ` [vision] ${body.vision.slice(0, 400)}`;
  }

  try {
    const raw = await completeOnRunPod([{ role: "system", content: system }, ...history, { role: "user", content: message.slice(0, 800) }]);
    const already = history.filter((turn) => turn.role === "assistant").map((turn) => turn.content);
    const chunks = chunkSpokenText(raw, already);
    const text = chunks.join(" ") || sanitizeSpokenText(raw) || raw.trim();
    if (!text) {
      return NextResponse.json({ error: "Empty model reply. Is the RunPod serve running?" }, { status: 502 });
    }
    return NextResponse.json({ text, chunks });
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Request failed.";
    return NextResponse.json({ error: detail }, { status: 502 });
  }
}

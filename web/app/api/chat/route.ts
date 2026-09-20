import { NextResponse } from "next/server";
import { sanitizeSpokenText } from "@/lib/sanitize";

export const maxDuration = 60;

const SYSTEM =
  "You are GLaDOS only. Not Wheatley. Write normal English with a space between every word. " +
  "Never spell a word as separate letters. Six to twelve complete sentences. Stay on the last remark. " +
    "Calm facility PA, then a petty scientific insult. Do not say I mean, okay, or mate. " +
  "Do not apologize. Do not glue words together.";

export async function POST(request: Request) {
  const completionUrl = process.env.GLADOS_COMPLETION_URL;
  const apiKey = process.env.GLADOS_API_KEY;
  if (!completionUrl) {
    return NextResponse.json({ error: "GLADOS_COMPLETION_URL is not set on Vercel." }, { status: 500 });
  }

  const body = (await request.json()) as { message?: string };
  const message = (body.message || "").trim();
  if (!message) {
    return NextResponse.json({ error: "Say something." }, { status: 400 });
  }

  const response = await fetch(completionUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
    },
    body: JSON.stringify({
      model: "glados-lora",
      stream: false,
      max_tokens: 280,
      messages: [
        { role: "system", content: SYSTEM },
        { role: "user", content: message },
      ],
    }),
  });

  if (!response.ok) {
    const detail = await response.text();
    return NextResponse.json(
      { error: `RunPod refused the request (${response.status}).`, detail: detail.slice(0, 400) },
      { status: 502 },
    );
  }

  const payload = (await response.json()) as {
    choices?: { message?: { content?: string }; delta?: { content?: string } }[];
  };
  const raw = payload.choices?.[0]?.message?.content || payload.choices?.[0]?.delta?.content || "";
  const text = sanitizeSpokenText(raw) || raw.trim();
  return NextResponse.json({ text });
}

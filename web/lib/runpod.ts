export async function completeOnRunPod(messages: { role: string; content: string }[]): Promise<string> {
  const completionUrl = process.env.GLADOS_COMPLETION_URL;
  const apiKey = process.env.GLADOS_API_KEY;
  if (!completionUrl) {
    throw new Error("GLADOS_COMPLETION_URL is not set on Vercel.");
  }

  const response = await fetch(completionUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
    },
    body: JSON.stringify({
      model: "glados-lora",
      stream: true,
      max_tokens: 280,
      messages,
    }),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`RunPod refused the request (${response.status}): ${detail.slice(0, 240)}`);
  }

  const raw = await response.text();
  if (!raw.trim()) {
    throw new Error("RunPod sent an empty reply. The pod may be stopped.");
  }

  const streamed = parseSseContent(raw);
  if (streamed) return streamed;

  try {
    const payload = JSON.parse(raw) as {
      choices?: { message?: { content?: string }; delta?: { content?: string } }[];
    };
    return payload.choices?.[0]?.message?.content || payload.choices?.[0]?.delta?.content || "";
  } catch {
    return raw.trim();
  }
}

function parseSseContent(raw: string): string {
  const parts: string[] = [];
  for (const line of raw.split(/\r?\n/)) {
    if (!line.startsWith("data:")) continue;
    const data = line.slice(5).trim();
    if (!data || data === "[DONE]") continue;
    try {
      const payload = JSON.parse(data) as {
        choices?: { delta?: { content?: string }; message?: { content?: string } }[];
      };
      const piece = payload.choices?.[0]?.delta?.content || payload.choices?.[0]?.message?.content || "";
      if (piece) parts.push(piece);
    } catch {
      parts.push(data);
    }
  }
  return parts.join("");
}

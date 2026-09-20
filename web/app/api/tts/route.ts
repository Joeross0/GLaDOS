export const maxDuration = 60;

export async function POST(request: Request) {
  const completionUrl = process.env.GLADOS_COMPLETION_URL;
  const apiKey = process.env.GLADOS_API_KEY;
  if (!completionUrl) {
    return Response.json({ error: "GLADOS_COMPLETION_URL is not set." }, { status: 500 });
  }

  const body = (await request.json()) as { text?: string };
  const text = (body.text || "").trim();
  if (!text) {
    return Response.json({ error: "Nothing to speak." }, { status: 400 });
  }

  const ttsUrl = completionUrl.replace(/\/v1\/chat\/completions\/?$/, "/v1/audio/speech");
  const response = await fetch(ttsUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
    },
    body: JSON.stringify({ text }),
  });

  if (!response.ok) {
    const detail = await response.text();
    return Response.json(
      { error: `GLaDOS voice failed (${response.status}). On the pod run: python -m pip install onnxruntime`, detail: detail.slice(0, 240) },
      { status: 502 },
    );
  }

  return new Response(response.body, {
    headers: {
      "Content-Type": response.headers.get("Content-Type") || "audio/wav",
      "Cache-Control": "no-store",
    },
  });
}

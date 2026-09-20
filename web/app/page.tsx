"use client";

import { FormEvent, useRef, useState } from "react";

type Line = { role: "you" | "glados" | "system"; text: string };

export default function Page() {
  const [lines, setLines] = useState<Line[]>([
    { role: "system", text: "All neural network modules are now loaded. System operational." },
  ]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const message = text.trim();
    if (!message || busy) return;
    setText("");
    setLines((current) => [...current, { role: "you", text: message }]);
    setBusy(true);
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      const payload = (await response.json()) as { text?: string; error?: string };
      const reply = payload.text || payload.error || "No response.";
      setLines((current) => [...current, { role: "glados", text: reply }]);
    } catch (error) {
      setLines((current) => [
        ...current,
        { role: "system", text: error instanceof Error ? error.message : "Request failed." },
      ]);
    } finally {
      setBusy(false);
      requestAnimationFrame(() => {
        logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
      });
    }
  }

  return (
    <main>
      <h1>GLaDOS // enrichment center terminal</h1>
      <div className="log" ref={logRef}>
        {lines.map((line, index) => (
          <p key={`${line.role}-${index}`} className={`line ${line.role === "you" ? "you" : ""}`}>
            {line.role === "you" ? "You" : line.role === "glados" ? "GLaDOS" : "System"}: {line.text}
          </p>
        ))}
      </div>
      <form onSubmit={onSubmit}>
        <input
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={busy ? "Thinking..." : "Type a message"}
          disabled={busy}
          autoFocus
        />
        <button type="submit" disabled={busy}>
          Send
        </button>
      </form>
      <p className="note">Text only. Voice and camera stay on your PC. The model is whatever RunPod URL is set on Vercel.</p>
    </main>
  );
}

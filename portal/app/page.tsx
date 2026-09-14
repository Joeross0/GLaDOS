"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

type EventRow = {
  timestamp: number;
  source: string;
  kind: string;
  message: string;
};

const STORAGE_KEY = "glados-portal";

export default function HomePage() {
  const [coreUrl, setCoreUrl] = useState("http://127.0.0.1:9119");
  const [pin, setPin] = useState("9119");
  const [unlocked, setUnlocked] = useState(false);
  const [error, setError] = useState("");
  const [text, setText] = useState("");
  const [scene, setScene] = useState("No vision snapshot yet.");
  const [events, setEvents] = useState<EventRow[]>([]);
  const [since, setSince] = useState(0);

  useEffect(() => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return;
    }
    try {
      const saved = JSON.parse(raw) as { coreUrl?: string; pin?: string };
      if (saved.coreUrl) {
        setCoreUrl(saved.coreUrl);
      }
      if (saved.pin) {
        setPin(saved.pin);
      }
    } catch {
      /* ignore */
    }
  }, []);

  const headers = useMemo(
    () => ({
      "Content-Type": "application/json",
      "X-GLaDOS-Pin": pin,
    }),
    [pin],
  );

  async function api(path: string, init?: RequestInit) {
    const response = await fetch(`${coreUrl.replace(/\/$/, "")}${path}`, {
      ...init,
      headers: { ...headers, ...(init?.headers || {}) },
    });
    const data = (await response.json()) as { ok?: boolean; error?: string };
    if (!response.ok || data.ok === false) {
      throw new Error(data.error || `HTTP ${response.status}`);
    }
    return data;
  }

  async function unlock(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api("/api/status");
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ coreUrl, pin }));
      setUnlocked(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Access denied");
    }
  }

  useEffect(() => {
    if (!unlocked) {
      return;
    }
    let cancelled = false;
    const tick = async () => {
      try {
        const status = (await api("/api/status")) as { scene?: string | null };
        const feed = (await api(`/api/events?since=${since}`)) as { events?: EventRow[] };
        if (cancelled) {
          return;
        }
        if (status.scene) {
          setScene(status.scene);
        }
        if (feed.events?.length) {
          setEvents((current) => [...current, ...feed.events!]);
          setSince(feed.events[feed.events.length - 1].timestamp);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Core unreachable");
        }
      }
    };
    void tick();
    const id = window.setInterval(() => void tick(), 2000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [unlocked, coreUrl, pin, since, headers]);

  async function send(event: FormEvent) {
    event.preventDefault();
    const message = text.trim();
    if (!message) {
      return;
    }
    setText("");
    setError("");
    try {
      await api("/api/chat", { method: "POST", body: JSON.stringify({ text: message }) });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Send failed");
    }
  }

  if (!unlocked) {
    return (
      <main className="shell">
        <form className="gate" onSubmit={unlock}>
          <h1>APERTURE REMOTE ACCESS</h1>
          <p className="sub">Enter the facility PIN and the local core URL.</p>
          <label>Core URL</label>
          <input value={coreUrl} onChange={(event) => setCoreUrl(event.target.value)} />
          <label>PIN</label>
          <input value={pin} onChange={(event) => setPin(event.target.value)} type="password" />
          <div className="row">
            <button type="submit">Unlock</button>
          </div>
          {error ? <p className="error">{error}</p> : null}
        </form>
      </main>
    );
  }

  return (
    <main className="shell">
      <section className="console">
        <h1>GLaDOS CORE</h1>
        <p className="sub">Linked to {coreUrl}</p>
        <div className="scene">{scene}</div>
        <div className="feed">
          {events.map((event) => {
            const role =
              event.source === "tts" ? "glados" : event.source === "vision" ? "vision" : "you";
            const label = role === "glados" ? "GLaDOS" : role === "vision" ? "Vision" : "You";
            return (
              <div key={`${event.timestamp}-${event.message}`} className={`line ${role}`}>
                {label}: {event.message}
              </div>
            );
          })}
        </div>
        <form onSubmit={send}>
          <label>Message</label>
          <input value={text} onChange={(event) => setText(event.target.value)} placeholder="Type a test subject inquiry..." />
          <div className="row">
            <button type="submit">Send</button>
            <button type="button" onClick={() => setUnlocked(false)}>
              Lock
            </button>
          </div>
        </form>
        {error ? <p className="error">{error}</p> : null}
      </section>
    </main>
  );
}

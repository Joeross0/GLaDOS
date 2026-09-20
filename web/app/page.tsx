"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { chunkSpokenText } from "@/lib/sanitize";

type Line = { role: "you" | "glados" | "system"; text: string };
type Detector = { detect: (video: HTMLVideoElement) => Promise<{ class: string; score: number }[]> };

const SESSION_KEY = "glados-web-session";
const SILENT_WAV =
  "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAA=";

function isAutoplayBlock(error: unknown): boolean {
  const message = error instanceof Error ? error.message : String(error);
  return /not allowed by the user agent|NotAllowedError|play\(\)/i.test(message);
}

function sessionId(): string {
  const existing = sessionStorage.getItem(SESSION_KEY);
  if (existing) return existing;
  const created = crypto.randomUUID();
  sessionStorage.setItem(SESSION_KEY, created);
  return created;
}

export default function Page() {
  const [lines, setLines] = useState<Line[]>([
    { role: "system", text: "All neural network modules are now loaded. System operational." },
  ]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [listening, setListening] = useState(false);
  const [cameraOn, setCameraOn] = useState(false);
  const [interruptible, setInterruptible] = useState(false);
  const [scene, setScene] = useState("camera off");
  const [sid, setSid] = useState("");
  const logRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const wantListenRef = useRef(false);
  const detectorRef = useRef<Detector | null>(null);
  const lastSceneRef = useRef("");
  const busyRef = useRef(false);
  const interruptibleRef = useRef(false);
  const turnRef = useRef(0);
  const linesRef = useRef(lines);

  useEffect(() => {
    linesRef.current = lines;
  }, [lines]);
  useEffect(() => {
    busyRef.current = busy;
  }, [busy]);
  useEffect(() => {
    interruptibleRef.current = interruptible;
  }, [interruptible]);

  useEffect(() => {
    setSid(sessionId());
    const saved = sessionStorage.getItem("glados-web-lines");
    if (saved) {
      try {
        setLines(JSON.parse(saved) as Line[]);
      } catch {
        /* keep default */
      }
    }
    setInterruptible(sessionStorage.getItem("glados-web-interrupt") === "1");
  }, []);

  useEffect(() => {
    if (!sid) return;
    sessionStorage.setItem("glados-web-lines", JSON.stringify(lines));
  }, [lines, sid]);

  const audioRef = useRef<HTMLAudioElement | null>(null);

  function ensurePlayer(): HTMLAudioElement {
    if (!audioRef.current) {
      audioRef.current = new Audio();
      audioRef.current.preload = "auto";
    }
    return audioRef.current;
  }

  function unlockAudio() {
    const player = ensurePlayer();
    player.muted = true;
    player.src = SILENT_WAV;
    void player
      .play()
      .then(() => {
        player.pause();
        player.muted = false;
      })
      .catch(() => {
        player.muted = false;
      });
  }

  function stopSpeech() {
    turnRef.current += 1;
    const player = audioRef.current;
    player?.pause();
    if (player?.src.startsWith("blob:")) URL.revokeObjectURL(player.src);
    setThinking(false);
  }

  const speakChunk = useCallback(async (piece: string, turn: number): Promise<boolean> => {
    if (turn !== turnRef.current) return false;
    const response = await fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: piece }),
    });
    if (!response.ok || turn !== turnRef.current) return false;
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const player = ensurePlayer();
    if (player.src.startsWith("blob:")) URL.revokeObjectURL(player.src);
    player.src = url;
    player.muted = false;
    try {
      await player.play();
    } catch {
      return turn === turnRef.current;
    }
    await new Promise<void>((resolve) => {
      const finish = () => {
        window.clearInterval(tick);
        resolve();
      };
      player.onended = finish;
      player.onerror = finish;
      const tick = window.setInterval(() => {
        if (turn !== turnRef.current) {
          player.pause();
          finish();
        }
      }, 80);
    });
    return turn === turnRef.current;
  }, []);

  const ask = useCallback(
    async (message: string, camera = false, vision = "") => {
      if (!message) return;
      if (busyRef.current && !interruptibleRef.current) return;
      if (busyRef.current && interruptibleRef.current) stopSpeech();
      const turn = (turnRef.current += 1);
      setBusy(true);
      setThinking(true);
      if (!camera) {
        setLines((current) => [...current, { role: "you", text: message }]);
      } else {
        setLines((current) => [...current, { role: "system", text: `Camera: ${vision || message}` }]);
      }
      try {
        const history = linesRef.current
          .filter((line) => line.role === "you" || line.role === "glados")
          .map((line) => ({
            role: line.role === "you" ? "user" : "assistant",
            content: line.text,
          }));
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message, history, vision, camera, sessionId: sessionStorage.getItem(SESSION_KEY) }),
        });
        const raw = await response.text();
        let payload: { text?: string; error?: string; chunks?: string[] } = {};
        try {
          payload = raw ? (JSON.parse(raw) as { text?: string; error?: string; chunks?: string[] }) : {};
        } catch {
          payload = { error: raw.slice(0, 200) || "Empty reply from the web API." };
        }
        if (turn !== turnRef.current) return;
        if (payload.error && !payload.text && !payload.chunks?.length) {
          setThinking(false);
          setLines((current) => [...current, { role: "system", text: payload.error || "No response." }]);
          return;
        }
        const already = linesRef.current.filter((line) => line.role === "glados").map((line) => line.text);
        const chunks = (payload.chunks?.length ? payload.chunks : chunkSpokenText(payload.text || "", already)).slice(0, 12);
        if (!chunks.length) {
          setThinking(false);
          return;
        }
        for (const piece of chunks) {
          if (turn !== turnRef.current) return;
          const heard = await speakChunk(piece, turn);
          setThinking(false);
          setLines((current) => [...current, { role: "glados", text: piece }]);
          requestAnimationFrame(() => {
            logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
          });
          if (!heard) {
            const rest = chunks.slice(chunks.indexOf(piece) + 1);
            if (rest.length) {
              setLines((current) => [...current, ...rest.map((text) => ({ role: "glados" as const, text }))]);
            }
            break;
          }
        }
      } catch (error) {
        if (!isAutoplayBlock(error)) {
          setLines((current) => [
            ...current,
            { role: "system", text: error instanceof Error ? error.message : "Request failed." },
          ]);
        }
      } finally {
        if (turn === turnRef.current) {
          setBusy(false);
          setThinking(false);
        }
        requestAnimationFrame(() => {
          logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
        });
      }
    },
    [speakChunk],
  );

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const message = text.trim();
    if (!message) return;
    unlockAudio();
    setText("");
    await ask(message, false, scene);
  }

  function stopMic() {
    wantListenRef.current = false;
    (window as unknown as { _gladosRec?: BrowserSpeech })._gladosRec?.stop();
    micStreamRef.current?.getTracks().forEach((track) => track.stop());
    micStreamRef.current = null;
    setListening(false);
  }

  async function toggleListen() {
    if (listening) {
      stopMic();
      return;
    }
    const Speech = (
      window as typeof window & {
        SpeechRecognition?: new () => BrowserSpeech;
        webkitSpeechRecognition?: new () => BrowserSpeech;
      }
    ).SpeechRecognition ||
      (
        window as typeof window & {
          webkitSpeechRecognition?: new () => BrowserSpeech;
        }
      ).webkitSpeechRecognition;
    if (!Speech) {
      setLines((current) => [
        ...current,
        {
          role: "system",
          text: "This phone browser cannot do speech recognition. Open the site in Chrome on Android, or type.",
        },
      ]);
      return;
    }
    try {
      micStreamRef.current = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    } catch (error) {
      setLines((current) => [
        ...current,
        {
          role: "system",
          text:
            error instanceof Error
              ? `Mic blocked: ${error.message}. Allow the microphone for this site, or type.`
              : "Mic blocked. Allow the microphone for this site, or type.",
        },
      ]);
      return;
    }
    const mobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
    const recognition = new Speech();
    recognition.continuous = !mobile;
    recognition.interimResults = false;
    recognition.lang = "en-US";
    recognition.onresult = (event: BrowserSpeechEvent) => {
      const transcript = Array.from(event.results)
        .slice(event.resultIndex)
        .map((result) => result[0].transcript)
        .join(" ")
        .trim();
      if (transcript) void ask(transcript, false, scene);
    };
    recognition.onerror = (event?: { error?: string }) => {
      if (event?.error === "aborted" || event?.error === "no-speech") return;
      stopMic();
    };
    recognition.onend = () => {
      if (wantListenRef.current && mobile && !busyRef.current) {
        try {
          recognition.start();
        } catch {
          wantListenRef.current = false;
          setListening(false);
        }
        return;
      }
      if (!wantListenRef.current) stopMic();
    };
    try {
      unlockAudio();
      wantListenRef.current = true;
      recognition.start();
      setListening(true);
      (window as unknown as { _gladosRec?: BrowserSpeech })._gladosRec = recognition;
    } catch {
      stopMic();
    }
  }

  useEffect(() => {
    return () => {
      stopMic();
      streamRef.current?.getTracks().forEach((track) => track.stop());
      audioRef.current?.pause();
    };
  }, []);

  async function loadDetector(): Promise<Detector> {
    if (detectorRef.current) return detectorRef.current;
    await loadScript("https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.22.0/dist/tf.min.js");
    await loadScript("https://cdn.jsdelivr.net/npm/@tensorflow-models/coco-ssd@2.2.3/dist/coco-ssd.min.js");
    const coco = (window as unknown as { cocoSsd: { load: () => Promise<Detector> } }).cocoSsd;
    detectorRef.current = await coco.load();
    return detectorRef.current;
  }

  async function toggleCamera() {
    if (cameraOn) {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      setCameraOn(false);
      setScene("camera off");
      return;
    }
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    } catch (error) {
      setLines((current) => [
        ...current,
        {
          role: "system",
          text:
            error instanceof Error
              ? `Camera blocked: ${error.message}`
              : "Camera blocked by the browser.",
        },
      ]);
      return;
    }
    streamRef.current = stream;
    if (videoRef.current) {
      videoRef.current.srcObject = stream;
      await videoRef.current.play();
    }
    setCameraOn(true);
    try {
      await loadDetector();
    } catch {
      setLines((current) => [...current, { role: "system", text: "Camera is on. Object labels failed to load." }]);
    }
  }

  useEffect(() => {
    if (!cameraOn) return;
    const timer = window.setInterval(async () => {
      const video = videoRef.current;
      const detector = detectorRef.current;
      if (!video || video.readyState < 2) return;
      let labels = "live camera feed";
      if (detector) {
        const hits = await detector.detect(video);
        labels =
          hits
            .filter((hit) => hit.score > 0.45)
            .map((hit) => hit.class)
            .slice(0, 6)
            .join(", ") || "empty room";
      }
      setScene(labels);
      if (labels !== lastSceneRef.current && !busyRef.current) {
        lastSceneRef.current = labels;
        void ask(`Camera update. I see: ${labels}`, true, labels);
      }
    }, 8000);
    return () => window.clearInterval(timer);
  }, [ask, cameraOn]);

  function newSession() {
    sessionStorage.removeItem(SESSION_KEY);
    sessionStorage.removeItem("glados-web-lines");
    window.location.reload();
  }

  return (
    <main>
      <header>
        <h1>GLaDOS // enrichment center terminal</h1>
        <p className="note">Session {sid.slice(0, 8) || "..."} — separate from the desktop TUI</p>
      </header>
      <div className="stage">
        <aside>
          <video ref={videoRef} muted playsInline />
          <p className="note">{scene}</p>
          <div className="toolbar">
            <button type="button" onClick={() => void toggleCamera()}>
              {cameraOn ? "Camera off" : "Camera on"}
            </button>
            <button type="button" onClick={() => void toggleListen()}>
              {listening ? "Mic off" : "Mic on"}
            </button>
            <button
              type="button"
              onClick={() => {
                setInterruptible((current) => {
                  const next = !current;
                  sessionStorage.setItem("glados-web-interrupt", next ? "1" : "0");
                  return next;
                });
              }}
            >
              Interrupt {interruptible ? "on" : "off"}
            </button>
            <button type="button" onClick={newSession}>
              New session
            </button>
          </div>
        </aside>
        <div className="log" ref={logRef}>
          {lines.map((line, index) => (
            <p key={`${line.role}-${index}`} className={`line ${line.role === "you" ? "you" : ""}`}>
              {line.role === "you" ? "You" : line.role === "glados" ? "GLaDOS" : "System"}: {line.text}
            </p>
          ))}
          {thinking ? <p className="line thinking">GLaDOS: Thinking</p> : null}
        </div>
      </div>
      <form onSubmit={(event) => void onSubmit(event)}>
        <input
          value={text}
          onChange={(event) => setText(event.target.value)}
            placeholder={
            thinking ? "Thinking..." : interruptible || !busy ? "Speak, test subject" : "Wait, or turn Interrupt on"
          }
          disabled={busy && !interruptible}
          autoFocus
        />
        <button type="submit" disabled={busy && !interruptible}>
          Send
        </button>
      </form>
      <p className="note">
        Voice is the same glados.onnx model the desktop app uses, served from RunPod. Restart that serve after this
        update. Use web-henna-pi-82, not the empty second Vercel project.
      </p>
    </main>
  );
}

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const found = document.querySelector(`script[src="${src}"]`);
    if (found) {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`Failed to load ${src}`));
    document.head.appendChild(script);
  });
}

type BrowserSpeech = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: BrowserSpeechEvent) => void) | null;
  onerror: ((event?: { error?: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
};

type BrowserSpeechEvent = {
  resultIndex: number;
  results: { 0: { transcript: string } }[];
};

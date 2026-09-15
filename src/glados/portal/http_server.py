from __future__ import annotations

import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from mimetypes import guess_type
from pathlib import Path
import threading
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlparse

from loguru import logger

from .config import PortalConfig
from .media_bridge import MediaBridge

if TYPE_CHECKING:
    from ..core.engine import Glados

STATIC_DIR = Path(__file__).resolve().parent / "static"
API_INDEX = {
    "ok": True,
    "service": "glados-portal",
    "endpoints": {
        "GET /api": "This catalog",
        "GET /api/status": "Core, autonomy, vision, speaking state",
        "GET /api/vision": "Latest camera description",
        "GET /api/events": "Dialog and vision events (?since=unix)",
        "POST /api/chat": "Send a text message {text}",
        "POST /api/audio": "Raw float32 PCM microphone chunks (X-Sample-Rate header)",
        "POST /api/camera": "JPEG frame from the browser camera",
        "GET /health": "Liveness probe",
    },
}


def _pins_match(left: str, right: str) -> bool:
    if len(left) != len(right):
        return False
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def start_portal_server(engine: Glados, config: PortalConfig) -> ThreadingHTTPServer:
    """Start the portal HTTP server in a daemon thread."""

    media = MediaBridge(engine)

    class PortalHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            logger.debug("Portal: " + format, *args)

        def _pin_ok(self) -> bool:
            provided = (
                self.headers.get("X-GLaDOS-Pin")
                or self.headers.get("x-glados-pin")
                or parse_qs(urlparse(self.path).query).get("pin", [""])[0]
            )
            return _pins_match(provided, config.pin)

        def _cors(self) -> None:
            origin = self.headers.get("Origin", "*")
            self.send_header("Access-Control-Allow-Origin", origin or "*")
            self.send_header(
                "Access-Control-Allow-Headers",
                "Content-Type, X-GLaDOS-Pin, X-Sample-Rate, ngrok-skip-browser-warning",
            )
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Credentials", "true")

        def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
            self.send_response(status)
            self._cors()
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, payload: dict[str, Any], status: int = 200) -> None:
            self._send(json.dumps(payload).encode("utf-8"), "application/json", status)

        def _static(self, relative: str) -> bool:
            target = (STATIC_DIR / relative.lstrip("/")).resolve()
            if STATIC_DIR not in target.parents and target != STATIC_DIR:
                return False
            if not target.is_file():
                return False
            content_type = guess_type(target.name)[0] or "application/octet-stream"
            self._send(target.read_bytes(), content_type)
            return True

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self._cors()
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path in {"/", "/index.html"}:
                if self._static("index.html"):
                    return
                self._json({"ok": False, "error": "ui missing"}, 500)
                return
            if path == "/health":
                self._json({"ok": True, "service": "glados-portal"})
                return
            if path.startswith("/static/"):
                if self._static(path.removeprefix("/static/")):
                    return
                self._json({"ok": False, "error": "not found"}, 404)
                return
            if not path.startswith("/api"):
                self._json({"ok": False, "error": "not found"}, 404)
                return
            if not self._pin_ok():
                self._json({"ok": False, "error": "invalid pin"}, 401)
                return
            if path == "/api":
                self._json(API_INDEX)
                return
            if path == "/api/status":
                vision = None
                updated_at = None
                change_score = None
                if engine.vision_state:
                    vision, change_score, updated_at = engine.vision_state.details()
                self._json(
                    {
                        "ok": True,
                        "model": engine.llm_model,
                        "autonomy": engine.autonomy_config.enabled,
                        "vision": engine.vision_config is not None,
                        "speaking": engine.currently_speaking_event.is_set(),
                        "asr_muted": engine.asr_muted_event.is_set(),
                        "tts_muted": engine.tts_muted_event.is_set(),
                        "scene": vision,
                        "scene_updated_at": updated_at,
                        "scene_change_score": change_score,
                    }
                )
                return
            if path == "/api/vision":
                if not engine.vision_state:
                    self._json({"ok": False, "error": "vision disabled"}, 404)
                    return
                description, change_score, updated_at = engine.vision_state.details()
                self._json(
                    {
                        "ok": True,
                        "description": description,
                        "change_score": change_score,
                        "updated_at": updated_at,
                    }
                )
                return
            if path == "/api/events":
                query = parse_qs(urlparse(self.path).query)
                since = float(query.get("since", ["0"])[0] or 0)
                events = [
                    {
                        "timestamp": event.timestamp,
                        "source": event.source,
                        "kind": event.kind,
                        "message": event.message,
                        "level": event.level,
                    }
                    for event in engine.observability_bus.snapshot(limit=200)
                    if event.timestamp > since
                    and (
                        (event.kind == "user_input" and event.source in {"asr", "text", "portal"})
                        or (event.source == "tts" and event.kind == "play")
                        or (event.source == "vision" and event.kind == "update")
                    )
                ]
                self._json({"ok": True, "events": events})
                return
            self._json({"ok": False, "error": "not found"}, 404)

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if not path.startswith("/api"):
                self._json({"ok": False, "error": "not found"}, 404)
                return
            if not self._pin_ok():
                self._json({"ok": False, "error": "invalid pin"}, 401)
                return
            length = int(self.headers.get("Content-Length", "0") or 0)
            raw = self.rfile.read(length) if length else b""
            if path == "/api/audio":
                sample_rate = int(self.headers.get("X-Sample-Rate", "16000") or 16000)
                queued = media.ingest_audio(raw, sample_rate)
                self._json({"ok": True, "chunks": queued})
                return
            if path == "/api/camera":
                accepted = media.ingest_jpeg(raw)
                self._json({"ok": accepted, "accepted": accepted}, 200 if accepted else 400)
                return
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._json({"ok": False, "error": "invalid json"}, 400)
                return
            if path == "/api/chat":
                text = str(payload.get("text") or payload.get("message") or "").strip()
                if not text:
                    self._json({"ok": False, "error": "empty message"}, 400)
                    return
                accepted = engine.submit_text_input(text, source="portal")
                self._json({"ok": accepted, "accepted": accepted})
                return
            self._json({"ok": False, "error": "not found"}, 404)

    server = ThreadingHTTPServer((config.host, config.port), PortalHandler)
    thread = threading.Thread(target=server.serve_forever, name="PortalHTTP", daemon=True)
    thread.start()
    logger.success(f"Portal UI + API listening on http://{config.host}:{config.port}")
    return server

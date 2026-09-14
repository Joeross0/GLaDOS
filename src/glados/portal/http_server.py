from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlparse

from loguru import logger

from .config import PortalConfig

if TYPE_CHECKING:
    from ..core.engine import Glados


def start_portal_server(engine: Glados, config: PortalConfig) -> ThreadingHTTPServer:
    """Start the portal HTTP server in a daemon thread."""

    class PortalHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            logger.debug("Portal: " + format, *args)

        def _pin_ok(self) -> bool:
            provided = (
                self.headers.get("X-GLaDOS-Pin")
                or self.headers.get("x-glados-pin")
                or parse_qs(urlparse(self.path).query).get("pin", [""])[0]
            )
            return hmac_compare(provided, config.pin)

        def _cors(self) -> None:
            origin = self.headers.get("Origin", "*")
            self.send_header("Access-Control-Allow-Origin", origin or "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-GLaDOS-Pin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Credentials", "true")

        def _json(self, payload: dict[str, Any], status: int = 200) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self._cors()
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path in {"/", "/health"}:
                self._json({"ok": True, "service": "glados-portal"})
                return
            if not self._pin_ok():
                self._json({"ok": False, "error": "invalid pin"}, 401)
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
            if not self._pin_ok():
                self._json({"ok": False, "error": "invalid pin"}, 401)
                return
            length = int(self.headers.get("Content-Length", "0") or 0)
            raw = self.rfile.read(length) if length else b"{}"
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

    def hmac_compare(left: str, right: str) -> bool:
        import hmac

        if len(left) != len(right):
            return False
        return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))

    server = ThreadingHTTPServer((config.host, config.port), PortalHandler)
    thread = threading.Thread(target=server.serve_forever, name="PortalHTTP", daemon=True)
    thread.start()
    logger.success(f"Portal listening on http://{config.host}:{config.port} (PIN required)")
    return server

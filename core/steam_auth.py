"""
Steam OpenID 2.0 — authentification publique, aucune clé secrète requise.
Même pattern que Twitch OAuth : ouvre le navigateur, callback local, SteamID récupéré.
"""

import re
import socket
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlencode, urlparse, parse_qs

from PyQt6.QtCore import QTimer

from core.config import Config
import core.logger as _log_mod

log = _log_mod.get("steam_auth")

_STEAM_OPENID = "https://steamcommunity.com/openid/login"

_SUCCESS_HTML = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"/>
<style>
  body{margin:0;display:flex;align-items:center;justify-content:center;
       min-height:100vh;background:#0e0e1a;font-family:'Segoe UI',sans-serif;color:#fff;}
  .box{text-align:center;padding:48px;}
  h2{font-size:28px;font-weight:700;margin-bottom:12px;color:#4ade80;}
  p{color:rgba(255,255,255,.6);font-size:15px;}
  .check{font-size:56px;margin-bottom:24px;}
</style></head><body>
<div class="box">
  <div class="check">✅</div>
  <h2>Connecté à Steam !</h2>
  <p>Tu peux fermer cette fenêtre et revenir dans GamePill.</p>
</div></body></html>"""

_ERROR_HTML = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"/>
<style>
  body{margin:0;display:flex;align-items:center;justify-content:center;
       min-height:100vh;background:#0e0e1a;font-family:'Segoe UI',sans-serif;color:#fff;}
  .box{text-align:center;padding:48px;}
  h2{font-size:28px;font-weight:700;margin-bottom:12px;color:#f87171;}
  p{color:rgba(255,255,255,.6);font-size:15px;}
</style></head><body>
<div class="box">
  <h2>Connexion échouée</h2>
  <p>Réessaie depuis GamePill.</p>
</div></body></html>"""


class _Handler(BaseHTTPRequestHandler):
    auth_ref = None   # SteamAuth instance

    def do_GET(self):
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/callback"):
            self.send_response(404); self.end_headers(); return

        params      = parse_qs(parsed.query)
        claimed_id  = params.get("openid.claimed_id", [""])[0]
        match       = re.search(r"/id/(\d+)$", claimed_id)

        if match and self.auth_ref:
            steam_id = match.group(1)
            log.info("Steam OpenID — SteamID64 : %s", steam_id)
            self.auth_ref._handle_success(steam_id)
            html = _SUCCESS_HTML
        else:
            log.warning("Steam OpenID — callback sans SteamID")
            if self.auth_ref:
                self.auth_ref._handle_failure()
            html = _ERROR_HTML

        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


def _find_port() -> int:
    for port in range(7355, 7400):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", port))
            return port
        except OSError:
            continue
        finally:
            s.close()
    return 7355


class SteamAuth:
    def __init__(self, config: Config):
        self._config     = config
        self._server     = None
        self._on_success = None
        self._on_failure = None

    # ── État ─────────────────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return bool(self._config.get("steam_id"))

    @property
    def steam_id(self) -> str:
        return self._config.get("steam_id", "")

    @property
    def username(self) -> str:
        return self._config.get("steam_username", "")

    # ── OAuth ─────────────────────────────────────────────────────────

    def start_oauth(self, on_success=None, on_failure=None):
        self._on_success = on_success
        self._on_failure = on_failure

        port = _find_port()
        callback = f"http://localhost:{port}/callback"

        _Handler.auth_ref = self
        self._server = HTTPServer(("127.0.0.1", port), _Handler)
        threading.Thread(target=self._server.serve_forever,
                         daemon=True, name="steam-oauth").start()

        params = {
            "openid.ns":         "http://specs.openid.net/auth/2.0",
            "openid.mode":       "checkid_setup",
            "openid.return_to":  callback,
            "openid.realm":      f"http://localhost:{port}",
            "openid.identity":   "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
        }
        webbrowser.open(_STEAM_OPENID + "?" + urlencode(params))
        log.info("Steam OpenID — navigateur ouvert, port %d", port)

    def disconnect(self):
        self._config.set("steam_id",       None)
        self._config.set("steam_username",  None)
        log.info("Steam déconnecté")

    # ── Callbacks internes ────────────────────────────────────────────

    def _handle_success(self, steam_id: str):
        self._config.set("steam_id", steam_id)
        self._shutdown_server()
        if self._on_success:
            QTimer.singleShot(500, self._on_success)

    def _handle_failure(self):
        self._shutdown_server()
        if self._on_failure:
            QTimer.singleShot(0, self._on_failure)

    def _shutdown_server(self):
        if self._server:
            threading.Thread(target=self._server.shutdown, daemon=True).start()
            self._server = None

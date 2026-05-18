"""
Twitch OAuth 2.0 — Authorization Code + PKCE
Client ID embarqué (approche OBS/Streamlabs).
"""

import base64
import hashlib
import os
import secrets
import socket
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from cryptography.fernet import Fernet

from core.config import Config
from core.constants import TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET
import core.logger as _log_mod

log = _log_mod.get("auth")

SCOPES   = "channel:read:subscriptions moderator:read:followers user:read:email"
AUTH_URL = "https://id.twitch.tv/oauth2/authorize"
TOKEN_URL= "https://id.twitch.tv/oauth2/token"
API_URL  = "https://api.twitch.tv/helix"

_OAUTH_PORTS = list(range(3000, 3010))


class _ReuseHTTPServer(HTTPServer):
    """HTTPServer avec SO_REUSEADDR pour éviter les erreurs de rebind sur Windows."""
    allow_reuse_address = True

_CALLBACK_HTML = (
    "<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'>"
    "<title>GamePill — Connecté !</title>"
    "<link rel='preconnect' href='https://fonts.googleapis.com'>"
    "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap' rel='stylesheet'>"
    "<style>"
    "*{margin:0;padding:0;box-sizing:border-box}"
    "body{background:#08080f;font-family:'Inter',system-ui,sans-serif;"
    "display:flex;align-items:center;justify-content:center;min-height:100vh;color:#fff;"
    "-webkit-font-smoothing:antialiased;}"
    ".bg{position:fixed;inset:0;z-index:0;"
    "background:radial-gradient(ellipse 60% 50% at 50% -10%,rgba(145,70,255,.25) 0%,transparent 65%),"
    "radial-gradient(ellipse 40% 30% at 80% 90%,rgba(212,175,55,.06) 0%,transparent 60%);}"
    ".grid{position:fixed;inset:0;z-index:0;"
    "background-image:linear-gradient(rgba(145,70,255,.04) 1px,transparent 1px),"
    "linear-gradient(90deg,rgba(145,70,255,.04) 1px,transparent 1px);"
    "background-size:64px 64px;}"
    ".card{position:relative;z-index:1;text-align:center;padding:56px 64px;"
    "max-width:460px;width:90%;background:rgba(16,16,28,.7);"
    "border:1px solid rgba(145,70,255,.18);border-radius:24px;"
    "backdrop-filter:blur(20px);"
    "box-shadow:0 0 80px rgba(145,70,255,.12),0 30px 60px rgba(0,0,0,.5);}"
    ".badge{display:inline-flex;align-items:center;gap:8px;"
    "background:rgba(145,70,255,.12);border:1px solid rgba(145,70,255,.3);"
    "border-radius:999px;padding:7px 18px;font-size:11px;font-weight:700;"
    "letter-spacing:1.5px;color:rgba(200,160,255,.9);text-transform:uppercase;margin-bottom:36px;}"
    ".dot{width:7px;height:7px;border-radius:50%;background:#ff3b30;"
    "animation:pulse 1.6s ease-in-out infinite;}"
    "@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.2;transform:scale(.8)}}"
    ".check{width:72px;height:72px;margin:0 auto 28px;"
    "background:linear-gradient(135deg,rgba(145,70,255,.2),rgba(145,70,255,.05));"
    "border:1px solid rgba(145,70,255,.3);border-radius:50%;"
    "display:flex;align-items:center;justify-content:center;font-size:32px;}"
    "h1{font-size:32px;font-weight:800;letter-spacing:-1px;margin-bottom:14px;line-height:1.1;}"
    "h1 .purple{color:#9146FF}h1 .gold{color:#D4AF37}"
    "p{font-size:14px;color:rgba(255,255,255,.55);line-height:1.7;margin-bottom:36px;}"
    ".cta{display:inline-block;background:linear-gradient(135deg,#9146FF,#7B2FBE);"
    "color:#fff;padding:13px 32px;border-radius:999px;font-size:14px;font-weight:700;"
    "text-decoration:none;letter-spacing:.3px;border:1px solid rgba(212,175,55,.25);"
    "transition:opacity .2s,transform .15s;}"
    ".cta:hover{opacity:.88;transform:translateY(-1px)}"
    ".hint{margin-top:20px;font-size:12px;color:rgba(255,255,255,.25);}"
    "</style></head><body>"
    "<div class='bg'></div><div class='grid'></div>"
    "<div class='card'>"
    "<div class='badge'><div class='dot'></div>LIVE</div>"
    "<div class='check'>✓</div>"
    "<h1>Connecté à <span class='purple'>Twitch</span> <span class='gold'>!</span></h1>"
    "<p>GamePill est maintenant lié à ton compte Twitch.<br>"
    "Tes stats et viewers s'affichent en temps réel.</p>"
    "<a class='cta' href='javascript:window.close()'>🎮 Retourne dans le jeu !</a>"
    "<p class='hint'>Tu peux fermer cet onglet.</p>"
    "</div></body></html>"
)


class TwitchAuth:
    def __init__(self, config: Config):
        self._config = config
        self._fernet = self._make_fernet()

    # ── Chiffrement machine-local ─────────────────────────────────────

    @staticmethod
    def _make_fernet() -> Fernet:
        key_path = Path(os.environ.get("APPDATA", Path.home())) / "GamePill" / "keystore.key"
        key_path.parent.mkdir(parents=True, exist_ok=True)
        if key_path.exists():
            key = key_path.read_bytes()
            if len(key) == 44:  # clé Fernet base64 valide
                return Fernet(key)
        key = Fernet.generate_key()
        key_path.write_bytes(key)
        return Fernet(key)

    def _enc(self, v: str) -> str:
        return self._fernet.encrypt(v.encode()).decode()

    def _dec(self, v: str) -> str | None:
        try:
            return self._fernet.decrypt(v.encode()).decode()
        except Exception as e:
            log.warning("Déchiffrement échoué (%s) — tokens invalidés", type(e).__name__)
            return None

    # ── Propriétés ───────────────────────────────────────────────────

    @property
    def client_id(self) -> str:
        return TWITCH_CLIENT_ID

    @property
    def is_connected(self) -> bool:
        return bool(self._load("access"))

    # ── PKCE ─────────────────────────────────────────────────────────

    @staticmethod
    def _pkce() -> tuple[str, str]:
        verifier  = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).rstrip(b"=").decode()
        return verifier, challenge

    # ── Flow OAuth (non-bloquant) ─────────────────────────────────────

    def start_oauth(self, on_success, on_failure):
        """Lance le navigateur + attend le callback dans un thread."""
        threading.Thread(
            target=self._oauth_worker,
            args=(on_success, on_failure),
            daemon=True,
        ).start()

    def _oauth_worker(self, on_success, on_failure):
        from PyQt6.QtCore import QTimer
        try:
            log.info("Démarrage flow OAuth")
            ok = self._do_oauth()
            log.info("Flow OAuth terminé → %s", "succès" if ok else "échec")
            QTimer.singleShot(0, on_success if ok else on_failure)
        except Exception as e:
            log.error("Erreur OAuth : %s", e)
            QTimer.singleShot(0, on_failure)

    def _do_oauth(self) -> bool:
        verifier, challenge = self._pkce()
        state = secrets.token_urlsafe(16)
        use_pkce = not bool(TWITCH_CLIENT_SECRET)

        # Trouve un port libre via socket simple (évite le rebind Windows)
        port = None
        for p in _OAUTH_PORTS:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind(("localhost", p))
                port = p
                break
            except OSError:
                continue

        if port is None:
            log.error("Aucun port disponible pour le callback OAuth")
            return False

        redirect_uri = f"http://localhost:{port}/callback"

        auth_params: dict = {
            "client_id":     self.client_id,
            "redirect_uri":  redirect_uri,
            "response_type": "code",
            "scope":         SCOPES,
            "state":         state,
        }
        if use_pkce:
            auth_params["code_challenge"]        = challenge
            auth_params["code_challenge_method"] = "S256"

        params = urlencode(auth_params)
        url = f"{AUTH_URL}?{params}"

        code_box:  list[str | None] = [None]
        error_box: list[str | None] = [None]

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed  = urlparse(self.path)
                qparams = parse_qs(parsed.query)

                # Ignore favicon et autres requêtes hors /callback
                if parsed.path != "/callback":
                    self.send_response(204)
                    self.end_headers()
                    return

                # Vérification du state pour prévenir les attaques CSRF
                received_state = qparams.get("state", [""])[0]
                if received_state != state:
                    log.warning("State OAuth invalide — requête ignorée")
                    self.send_response(400)
                    self.end_headers()
                    return

                if "error" in qparams:
                    error_box[0] = qparams["error"][0]
                elif "code" in qparams:
                    code_box[0] = qparams["code"][0]

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(_CALLBACK_HTML.encode("utf-8"))

            def log_message(self, *args):
                pass

        srv = _ReuseHTTPServer(("localhost", port), _Handler)
        srv.timeout = 180
        webbrowser.open(url)

        for _ in range(10):
            srv.handle_request()
            if code_box[0] or error_box[0]:
                break

        srv.server_close()

        if error_box[0]:
            log.warning("Accès refusé par l'utilisateur : %s", error_box[0])
            return False
        if not code_box[0]:
            log.warning("Aucun code reçu après timeout")
            return False
        return self._exchange(code_box[0], verifier if use_pkce else None, redirect_uri)

    def _exchange(self, code: str, verifier: str | None, redirect_uri: str) -> bool:
        try:
            payload: dict = {
                "client_id":    self.client_id,
                "code":         code,
                "grant_type":   "authorization_code",
                "redirect_uri": redirect_uri,
            }
            if TWITCH_CLIENT_SECRET:
                payload["client_secret"] = TWITCH_CLIENT_SECRET
            elif verifier:
                payload["code_verifier"] = verifier
            r = httpx.post(TOKEN_URL, data=payload, timeout=10, verify=False)
            if r.status_code != 200:
                log.error("Échange token échoué : HTTP %d — %s", r.status_code, r.text[:300])
                return False
            d = r.json()
            if "access_token" not in d:
                log.error("Pas de access_token dans la réponse Twitch")
                return False
            self._save(d["access_token"], d.get("refresh_token", ""))
            self._fetch_and_save_username(d["access_token"])
            return True
        except Exception as e:
            log.error("Échange token échoué : %s", e)
            return False

    def _fetch_and_save_username(self, access_token: str):
        try:
            r = httpx.get(f"{API_URL}/users", headers={
                "Authorization": f"Bearer {access_token}",
                "Client-Id":     self.client_id,
            }, timeout=5, verify=False)
            if r.status_code == 200:
                data = r.json().get("data", [])
                if data:
                    self._config.set("twitch_username",      data[0]["login"])
                    self._config.set("twitch_display_name",  data[0]["display_name"])
        except Exception as e:
            log.warning("Impossible de récupérer le username : %s", e)

    # ── Refresh ───────────────────────────────────────────────────────

    def refresh(self) -> bool:
        rt = self._load("refresh")
        if not rt:
            return False
        try:
            refresh_payload: dict = {
                "client_id":     self.client_id,
                "refresh_token": rt,
                "grant_type":    "refresh_token",
            }
            if TWITCH_CLIENT_SECRET:
                refresh_payload["client_secret"] = TWITCH_CLIENT_SECRET
            r = httpx.post(TOKEN_URL, data=refresh_payload, timeout=10, verify=False)
            r.raise_for_status()
            d = r.json()
            self._save(d["access_token"], d.get("refresh_token", rt))
            return True
        except Exception:
            return False

    # ── Tokens ────────────────────────────────────────────────────────

    def get_access_token(self) -> str | None:
        return self._load("access")

    def ensure_valid(self) -> bool:
        token = self._load("access")
        if not token:
            return False
        try:
            r = httpx.get(f"{API_URL}/users", headers={
                "Authorization": f"Bearer {token}",
                "Client-Id":     self.client_id,
            }, timeout=5, verify=False)
            if r.status_code == 200:
                return True
            if r.status_code == 401:
                return self.refresh()
            return False
        except Exception:
            return True  # réseau indisponible — on conserve les tokens

    def disconnect(self):
        self._config.set("twitch_access_token",  None)
        self._config.set("twitch_refresh_token",  None)
        self._config.set("twitch_username",       None)
        self._config.set("twitch_display_name",   None)

    def _save(self, access: str, refresh: str):
        self._config.set("twitch_access_token", self._enc(access))
        if refresh:
            self._config.set("twitch_refresh_token", self._enc(refresh))

    def _load(self, kind: str) -> str | None:
        raw = self._config.get(f"twitch_{kind}_token")
        if not raw:
            return None
        result = self._dec(raw)
        if result is None:
            # Token illisible (clé changée) — on purge pour éviter le spam
            self._config.set(f"twitch_{kind}_token", None)
        return result

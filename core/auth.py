"""
Twitch OAuth 2.0 — Authorization Code + PKCE
Client ID embarqué (approche OBS/Streamlabs).
Pas de Client Secret requis.
"""

import base64
import hashlib
import secrets
import threading
import uuid
import warnings
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import httpx

# Réseau d'entreprise avec inspection SSL — on désactive les warnings
warnings.filterwarnings("ignore", message=".*Unverified HTTPS.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="httpx")
from cryptography.fernet import Fernet

from core.config import Config
from core.constants import TWITCH_CLIENT_ID

REDIRECT_URI = "http://localhost:3000/callback"
SCOPES       = "channel:read:subscriptions moderator:read:followers user:read:email"
AUTH_URL     = "https://id.twitch.tv/oauth2/authorize"
TOKEN_URL    = "https://id.twitch.tv/oauth2/token"
API_URL      = "https://api.twitch.tv/helix"


class TwitchAuth:
    def __init__(self, config: Config):
        self._config = config
        self._fernet = self._make_fernet()

    # ── Chiffrement machine-local ─────────────────────────────────────

    @staticmethod
    def _make_fernet() -> Fernet:
        key = base64.urlsafe_b64encode(
            hashlib.sha256(str(uuid.getnode()).encode()).digest()
        )
        return Fernet(key)

    def _enc(self, v: str) -> str:
        return self._fernet.encrypt(v.encode()).decode()

    def _dec(self, v: str) -> str | None:
        try:
            return self._fernet.decrypt(v.encode()).decode()
        except Exception as e:
            print(f"[Auth] Déchiffrement échoué ({type(e).__name__}) — tokens invalidés")
            return None

    # ── Propriétés ───────────────────────────────────────────────────

    @property
    def client_id(self) -> str:
        return TWITCH_CLIENT_ID

    @property
    def is_connected(self) -> bool:
        result = bool(self._load("access"))
        print(f"[Auth] is_connected → {result}")
        return result

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
            ok = self._do_oauth()
            print(f"[Auth] _do_oauth() → {'succès' if ok else 'échec'}")
            QTimer.singleShot(0, on_success if ok else on_failure)
        except Exception as e:
            print(f"[Auth] Erreur OAuth : {e}")
            QTimer.singleShot(0, on_failure)

    def _do_oauth(self) -> bool:
        verifier, challenge = self._pkce()
        state = secrets.token_urlsafe(16)

        url = (
            f"{AUTH_URL}?client_id={self.client_id}"
            f"&redirect_uri={REDIRECT_URI}"
            f"&response_type=code"
            f"&scope={SCOPES.replace(' ', '+')}"
            f"&code_challenge={challenge}"
            f"&code_challenge_method=S256"
            f"&state={state}"
            f"&force_verify=true"
        )

        code_box: list[str | None] = [None]

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                params = parse_qs(urlparse(self.path).query)
                if "code" in params:
                    code_box[0] = params["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    b"<html><body style='font-family:sans-serif;text-align:center;margin-top:80px'>"
                    b"<h2>\xe2\x9c\x85 GamePill connect\xc3\xa9 !</h2>"
                    b"<p>Tu peux fermer cet onglet et retourner dans le jeu.</p>"
                    b"</body></html>"
                )

            def log_message(self, *args):
                pass

        webbrowser.open(url)
        srv = HTTPServer(("localhost", 3000), _Handler)
        srv.timeout = 180
        srv.handle_request()
        srv.server_close()

        if not code_box[0]:
            return False
        return self._exchange(code_box[0], verifier)

    def _exchange(self, code: str, verifier: str) -> bool:
        try:
            print(f"[Auth] Échange du code contre un token…")
            r = httpx.post(TOKEN_URL, data={
                "client_id":     self.client_id,
                "code":          code,
                "code_verifier": verifier,
                "grant_type":    "authorization_code",
                "redirect_uri":  REDIRECT_URI,
            }, timeout=10, verify=False)
            print(f"[Auth] Réponse Twitch : HTTP {r.status_code}")
            r.raise_for_status()
            d = r.json()
            if "access_token" not in d:
                print(f"[Auth] Pas de access_token dans la réponse : {d}")
                return False
            self._save(d["access_token"], d.get("refresh_token", ""))
            self._fetch_and_save_username(d["access_token"])
            return True
        except Exception as e:
            print(f"[Auth] Échange token échoué : {e}")
            return False

    def _fetch_and_save_username(self, access_token: str):
        """Récupère le login Twitch via l'API et le stocke en config."""
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
            print(f"[Auth] Impossible de récupérer le username : {e}")

    # ── Refresh ───────────────────────────────────────────────────────

    def refresh(self) -> bool:
        rt = self._load("refresh")
        if not rt:
            return False
        try:
            r = httpx.post(TOKEN_URL, data={
                "client_id":     self.client_id,
                "refresh_token": rt,
                "grant_type":    "refresh_token",
            }, timeout=10, verify=False)
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
        """
        Vérifie que le token est encore valide auprès de Twitch.
        Si expiré (401), tente un refresh automatique.
        Appelé au démarrage pour restaurer la session sans re-login.
        """
        token = self._load("access")
        if not token:
            print("[Auth] Aucun token stocké — pas de session à restaurer")
            return False
        try:
            r = httpx.get(f"{API_URL}/users", headers={
                "Authorization": f"Bearer {token}",
                "Client-Id":     self.client_id,
            }, timeout=5, verify=False)
            if r.status_code == 200:
                print("[Auth] Token valide, session restaurée")
                return True
            if r.status_code == 401:
                print("[Auth] Token expiré, tentative de refresh…")
                ok = self.refresh()
                print(f"[Auth] Refresh {'réussi' if ok else 'échoué'}")
                return ok
            print(f"[Auth] Statut inattendu {r.status_code}")
            return False
        except Exception as e:
            print(f"[Auth] Validation impossible (réseau?) : {e}")
            # On garde les tokens — peut-être juste offline
            return True

    def disconnect(self):
        self._config.set("twitch_access_token",  None)
        self._config.set("twitch_refresh_token",  None)
        self._config.set("twitch_username",       None)
        self._config.set("twitch_display_name",   None)

    def _save(self, access: str, refresh: str):
        enc_access = self._enc(access)
        self._config.set("twitch_access_token", enc_access)
        print(f"[Auth] Token sauvegardé (longueur chiffrée : {len(enc_access)})")
        if refresh:
            self._config.set("twitch_refresh_token", self._enc(refresh))
        # Vérification immédiate
        check = self._load("access")
        print(f"[Auth] Vérification post-save : {'OK ✓' if check else 'ECHEC ✗'}")

    def _load(self, kind: str) -> str | None:
        raw = self._config.get(f"twitch_{kind}_token")
        if not raw:
            print(f"[Auth] _load({kind}) : aucune valeur en config")
            return None
        result = self._dec(raw)
        if not result:
            print(f"[Auth] _load({kind}) : déchiffrement échoué")
        return result

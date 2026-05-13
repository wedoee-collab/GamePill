"""
Twitch Helix API — polling toutes les 5s en background thread.
Données : viewers, uptime, dernier follower.
"""

import threading
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

warnings.filterwarnings("ignore", message=".*Unverified HTTPS.*")
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from core.auth import TwitchAuth
from core.config import Config
from core.constants import TWITCH_CLIENT_ID

API = "https://api.twitch.tv/helix"


@dataclass
class TwitchData:
    is_live:       bool = False
    viewers:       int  = 0
    game_name:     str  = ""
    uptime_sec:    int  = 0
    last_follower: str  = ""
    broadcaster_id: str = ""
    username:      str  = ""

    def viewers_fmt(self) -> str:
        """1247 → '1 247'"""
        return f"{self.viewers:,}".replace(",", " ")

    def uptime_fmt(self) -> str:
        if not self.uptime_sec:
            return "--"
        h, r = divmod(self.uptime_sec, 3600)
        m = r // 60
        return f"{h}h {m:02d}m" if h else f"{m}m"


class TwitchService(QObject):
    data_updated    = pyqtSignal(object)   # émet un TwitchData
    connection_lost = pyqtSignal()

    POLL_MS = 5_000

    def __init__(self, auth: TwitchAuth, config: Config, parent=None):
        super().__init__(parent)
        self._auth   = auth
        self._config = config
        self._data   = TwitchData()
        self._lock   = threading.Lock()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)

    @property
    def username(self) -> str:
        return self._config.get("twitch_username", "")

    def start(self):
        self._poll()
        self._timer.start(self.POLL_MS)

    def stop(self):
        self._timer.stop()

    @property
    def data(self) -> TwitchData:
        with self._lock:
            return TwitchData(**vars(self._data))

    # ── Polling ───────────────────────────────────────────────────────

    def _poll(self):
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            self._fetch()
            self.data_updated.emit(self.data)
        except Exception as e:
            print(f"[Twitch] Erreur poll : {e}")
            # On émet quand même pour garder l'UI cohérente
            self.data_updated.emit(self.data)

    # ── Requêtes HTTP ─────────────────────────────────────────────────

    def _headers(self) -> dict | None:
        token = self._auth.get_access_token()
        if not token:
            return None
        return {
            "Authorization": f"Bearer {token}",
            "Client-Id":     self._auth.client_id,
        }

    def _get(self, path: str, params: dict, headers: dict) -> dict | None:
        try:
            r = httpx.get(f"{API}{path}", params=params, headers=headers, timeout=5, verify=False)
            if r.status_code == 401:
                if self._auth.refresh():
                    h2 = self._headers()
                    if h2:
                        r = httpx.get(f"{API}{path}", params=params, headers=h2, timeout=5, verify=False)
                    else:
                        self.connection_lost.emit()
                        return None
                else:
                    self.connection_lost.emit()
                    return None
            return r.json() if r.status_code == 200 else None
        except httpx.TimeoutException:
            print(f"[Twitch] Timeout sur {path}")
            return None
        except Exception as e:
            print(f"[Twitch] Erreur HTTP {path} : {e}")
            return None

    def _fetch(self):
        headers = self._headers()
        if not headers or not self.username:
            return

        # ── Stream ────────────────────────────────────────────────────
        resp = self._get("/streams", {"user_login": self.username}, headers)
        if resp is None:
            return

        streams = resp.get("data", [])
        with self._lock:
            if not streams:
                self._data.is_live   = False
                self._data.viewers   = 0
                self._data.uptime_sec = 0
                return

            s = streams[0]
            self._data.is_live        = True
            self._data.viewers        = s.get("viewer_count", 0)
            self._data.game_name      = s.get("game_name", "")
            self._data.broadcaster_id = s.get("user_id", "")
            self._data.username       = s.get("user_login", self.username)

            started = s.get("started_at", "")
            if started:
                try:
                    dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                    self._data.uptime_sec = int(
                        (datetime.now(timezone.utc) - dt).total_seconds()
                    )
                except Exception:
                    pass

        # ── Dernier follower ──────────────────────────────────────────
        bid = self._data.broadcaster_id
        if not bid:
            return
        h2 = self._headers()
        if not h2:
            return
        resp2 = self._get("/channels/followers",
                          {"broadcaster_id": bid, "first": 1}, h2)
        if resp2:
            fdata = resp2.get("data", [])
            with self._lock:
                self._data.last_follower = fdata[0]["user_name"] if fdata else ""

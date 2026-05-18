"""
Twitch Helix API — polling toutes les 5s.
Données : viewers, peak, uptime, session counters (follows/subs/raids).
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from core.auth import TwitchAuth
from core.config import Config
import core.logger as _log_mod

log = _log_mod.get("twitch")

API = "https://api.twitch.tv/helix"


@dataclass
class TwitchData:
    is_live:         bool = False
    viewers:         int  = 0
    peak_viewers:    int  = 0
    game_name:       str  = ""
    uptime_sec:      int  = 0
    last_follower:   str  = ""
    broadcaster_id:  str  = ""
    username:        str  = ""
    session_follows: int  = 0
    session_subs:    int  = 0
    session_raids:   int  = 0
    session_start:   str  = ""   # ISO — détecte les redémarrages de stream

    def viewers_fmt(self) -> str:
        v = self.viewers
        if v >= 1_000_000:
            return f"{v/1_000_000:.1f}M"
        if v >= 1_000:
            return f"{v/1_000:.1f}k"
        return str(v)

    def peak_fmt(self) -> str:
        v = self.peak_viewers
        if v >= 1_000_000:
            return f"{v/1_000_000:.1f}M"
        if v >= 1_000:
            return f"{v/1_000:.1f}k"
        return str(v)

    def uptime_fmt(self) -> str:
        if not self.uptime_sec:
            return "--"
        h, r = divmod(self.uptime_sec, 3600)
        m = r // 60
        return f"{h}h {m:02d}m" if h else f"{m}m"


class TwitchService(QObject):
    data_updated    = pyqtSignal(object)
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

    # ── EventSub callbacks (appelés depuis TwitchEventSub) ───────────

    def add_follow(self, username: str):
        with self._lock:
            self._data.session_follows += 1
            self._data.last_follower    = username
        snapshot = self.data
        QTimer.singleShot(0, lambda: self.data_updated.emit(snapshot))

    def add_sub(self, username: str, is_gift: bool = False):
        with self._lock:
            self._data.session_subs += 1
        snapshot = self.data
        QTimer.singleShot(0, lambda: self.data_updated.emit(snapshot))

    def add_raid(self, from_name: str, viewers: int):
        with self._lock:
            self._data.session_raids += 1
        snapshot = self.data
        QTimer.singleShot(0, lambda: self.data_updated.emit(snapshot))

    # ── Polling ───────────────────────────────────────────────────────

    def _poll(self):
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            self._fetch()
        except Exception as e:
            log.error("Erreur poll : %s", e)
        snapshot = self.data
        QTimer.singleShot(0, lambda: self.data_updated.emit(snapshot))

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
            r = httpx.get(f"{API}{path}", params=params, headers=headers,
                          timeout=5)
            if r.status_code == 401:
                if self._auth.refresh():
                    h2 = self._headers()
                    if h2:
                        r = httpx.get(f"{API}{path}", params=params, headers=h2,
                                      timeout=5)
                    else:
                        QTimer.singleShot(0, self.connection_lost.emit)
                        return None
                else:
                    QTimer.singleShot(0, self.connection_lost.emit)
                    return None
            return r.json() if r.status_code == 200 else None
        except httpx.TimeoutException:
            return None
        except Exception as e:
            log.error("HTTP %s : %s", path, e)
            return None

    def _fetch(self):
        headers = self._headers()
        if not headers or not self.username:
            return

        resp = self._get("/streams", {"user_login": self.username}, headers)
        if resp is None:
            return

        streams = resp.get("data", [])
        with self._lock:
            if not streams:
                self._data.is_live    = False
                self._data.viewers    = 0
                self._data.uptime_sec = 0
                return

            s = streams[0]
            viewers       = s.get("viewer_count", 0)
            started       = s.get("started_at", "")
            broadcaster   = s.get("user_id", "")

            # Reset session counters si nouveau stream
            if started and started != self._data.session_start:
                self._data.session_start   = started
                self._data.session_follows = 0
                self._data.session_subs    = 0
                self._data.session_raids   = 0
                self._data.peak_viewers    = 0

            # Peak viewers
            if viewers > self._data.peak_viewers:
                self._data.peak_viewers = viewers

            self._data.is_live        = True
            self._data.viewers        = viewers
            self._data.game_name      = s.get("game_name", "")
            self._data.broadcaster_id = broadcaster
            self._data.username       = s.get("user_login", self.username)

            # Sauvegarder broadcaster_id pour EventSub (disponible même hors live)
            if broadcaster:
                self._config.set("twitch_broadcaster_id", broadcaster)

            if started:
                try:
                    dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                    self._data.uptime_sec = int(
                        (datetime.now(timezone.utc) - dt).total_seconds()
                    )
                except Exception:
                    pass

        bid = self._data.broadcaster_id
        if not bid:
            return
        h2 = self._headers()
        if not h2:
            return
        resp2 = self._get("/channels/followers", {"broadcaster_id": bid, "first": 1}, h2)
        if resp2:
            fdata = resp2.get("data", [])
            with self._lock:
                if fdata and not self._data.session_follows:
                    self._data.last_follower = fdata[0]["user_name"]

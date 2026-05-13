"""
Kick — API publique REST.
Polling toutes les 60 s (rate-limit conservateur).
"""

import threading
from dataclasses import dataclass

import httpx
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from core.config import Config
import core.logger as _log_mod

log = _log_mod.get("kick")

API      = "https://kick.com/api/v1/channels"
POLL_MS  = 60_000
HEADERS  = {
    "Accept":     "application/json",
    "User-Agent": "GamePill/1.0",
}


@dataclass
class KickData:
    is_live:   bool = False
    viewers:   int  = 0
    title:     str  = ""
    game_name: str  = ""
    slug:      str  = ""

    def viewers_fmt(self) -> str:
        v = self.viewers
        if v >= 1_000_000:
            return f"{v / 1_000_000:.1f}M"
        if v >= 1_000:
            return f"{v / 1_000:.1f}k"
        return str(v)


class KickService(QObject):
    data_updated    = pyqtSignal(object)   # KickData
    connection_lost = pyqtSignal()

    _BACKOFF = [5, 10, 30, 60]   # secondes entre les tentatives de reconnexion

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self._config     = config
        self._data       = KickData()
        self._lock       = threading.Lock()
        self._failures   = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)

    # ── API publique ──────────────────────────────────────────────────

    @property
    def slug(self) -> str:
        return self._config.get("kick_slug", "")

    @property
    def data(self) -> KickData:
        with self._lock:
            return KickData(**vars(self._data))

    def is_configured(self) -> bool:
        return bool(self.slug)

    def start(self):
        if not self.is_configured():
            log.debug("Kick : pas de slug configuré")
            return
        self._failures = 0
        self._poll()
        self._timer.start(POLL_MS)
        log.info("Kick service démarré pour : %s", self.slug)

    def stop(self):
        self._timer.stop()
        log.info("Kick service arrêté")

    # ── Polling ───────────────────────────────────────────────────────

    def _poll(self):
        threading.Thread(target=self._worker, daemon=True, name="kick-poll").start()

    def _worker(self):
        slug = self.slug
        if not slug:
            return
        try:
            r = httpx.get(f"{API}/{slug}", headers=HEADERS, timeout=8)
            if r.status_code == 404:
                log.warning("Kick : channel '%s' introuvable (404)", slug)
                self._failures += 1
                QTimer.singleShot(0, self.connection_lost.emit)
                return
            if r.status_code != 200:
                log.warning("Kick HTTP %d pour '%s'", r.status_code, slug)
                self._failures += 1
                return

            self._failures = 0
            channel     = r.json()
            livestream  = channel.get("livestream") or {}

            with self._lock:
                self._data.slug      = slug
                self._data.is_live   = bool(livestream)
                self._data.viewers   = livestream.get("viewer_count", 0) if livestream else 0
                self._data.title     = livestream.get("session_title", "") if livestream else ""
                cats = livestream.get("categories", []) if livestream else []
                self._data.game_name = cats[0].get("name", "") if cats else ""

            snapshot = self.data
            log.debug("Kick '%s' — live=%s viewers=%d", slug, snapshot.is_live, snapshot.viewers)
            QTimer.singleShot(0, lambda: self.data_updated.emit(snapshot))

        except httpx.TimeoutException:
            log.warning("Kick : timeout pour '%s'", slug)
            self._failures += 1
        except Exception as e:
            log.error("Kick erreur : %s", e)
            self._failures += 1

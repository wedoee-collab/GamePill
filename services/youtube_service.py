"""
YouTube Data API v3 — clé API simple, pas d'OAuth.
Données publiques : stream live, viewers, uptime.

Setup utilisateur :
  1. console.cloud.google.com → Activer YouTube Data API v3
  2. Credentials → Créer une clé API → copier dans constants.py
  3. Entrer son @handle dans le menu GamePill
"""

import threading
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from core.config import Config
from core.constants import YOUTUBE_API_KEY
import core.logger as _log_mod

log = _log_mod.get("youtube")

API = "https://www.googleapis.com/youtube/v3"


@dataclass
class YouTubeData:
    is_live:      bool = False
    viewers:      int  = 0
    title:        str  = ""
    video_id:     str  = ""
    uptime_sec:   int  = 0
    display_name: str  = ""
    channel_id:   str  = ""

    def viewers_fmt(self) -> str:
        v = self.viewers
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


def resolve_channel(handle: str) -> tuple[str, str] | None:
    """
    Résout un @handle, username ou channel ID en (channel_id, display_name).
    Essaie plusieurs méthodes pour maximiser les chances.
    """
    if not YOUTUBE_API_KEY:
        log.warning("Pas de clé API YouTube")
        return None

    handle = handle.strip().lstrip("@")
    log.info("Résolution YouTube : '%s'", handle)

    # Essai 1 : c'est déjà un channel ID (UCxxxxxxxxxxxxxxxxxxxxxxxxx)
    if handle.startswith("UC") and len(handle) == 24:
        try:
            r = httpx.get(f"{API}/channels", params={
                "part": "snippet", "id": handle, "key": YOUTUBE_API_KEY,
            }, timeout=8)
            log.debug("channelId → HTTP %d", r.status_code)
            if r.status_code == 200:
                items = r.json().get("items", [])
                if items:
                    return items[0]["id"], items[0]["snippet"]["title"]
        except Exception as e:
            log.debug("channelId erreur : %s", e)

    # Essai 2 : forHandle (handles modernes @xxx)
    try:
        r = httpx.get(f"{API}/channels", params={
            "part": "snippet", "forHandle": handle, "key": YOUTUBE_API_KEY,
        }, timeout=8)
        log.debug("forHandle → HTTP %d", r.status_code)
        if r.status_code == 200:
            items = r.json().get("items", [])
            if items:
                return items[0]["id"], items[0]["snippet"]["title"]
    except Exception as e:
        log.debug("forHandle erreur : %s", e)

    # Essai 3 : forUsername (anciens comptes YouTube)
    try:
        r = httpx.get(f"{API}/channels", params={
            "part": "snippet", "forUsername": handle, "key": YOUTUBE_API_KEY,
        }, timeout=8)
        log.debug("forUsername → HTTP %d", r.status_code)
        if r.status_code == 200:
            items = r.json().get("items", [])
            if items:
                return items[0]["id"], items[0]["snippet"]["title"]
    except Exception as e:
        log.debug("forUsername erreur : %s", e)

    # Essai 4 : recherche textuelle (coûte 100 unités mais marche toujours)
    try:
        r = httpx.get(f"{API}/search", params={
            "part": "snippet", "q": handle, "type": "channel",
            "maxResults": 1, "key": YOUTUBE_API_KEY,
        }, timeout=8)
        log.debug("search → HTTP %d", r.status_code)
        if r.status_code == 200:
            items = r.json().get("items", [])
            if items:
                channel_id = items[0]["snippet"]["channelId"]
                name       = items[0]["snippet"]["channelTitle"]
                return channel_id, name
    except Exception as e:
        log.debug("search erreur : %s", e)

    log.warning("YouTube : aucune méthode n'a trouvé '%s'", handle)
    return None


class YouTubeService(QObject):
    data_updated    = pyqtSignal(object)   # YouTubeData
    connection_lost = pyqtSignal()

    # Search coûte 100 unités → poll toutes les 3 min (quota ~480/j sur 10 000/j)
    # Viewers (1 unité) → poll toutes les 30 s quand live
    SEARCH_MS  = 180_000   # 3 min
    VIEWERS_MS = 30_000    # 30 s

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self._config   = config
        self._data     = YouTubeData()
        self._lock     = threading.Lock()

        self._search_timer  = QTimer(self)
        self._viewers_timer = QTimer(self)
        self._search_timer.timeout.connect(self._poll_search)
        self._viewers_timer.timeout.connect(self._poll_viewers)

    @property
    def data(self) -> YouTubeData:
        with self._lock:
            return YouTubeData(**vars(self._data))

    @property
    def channel_id(self) -> str:
        return self._config.get("youtube_channel_id", "")

    @property
    def display_name(self) -> str:
        return self._config.get("youtube_display_name", "")

    def is_configured(self) -> bool:
        return bool(YOUTUBE_API_KEY and self.channel_id)

    def start(self):
        if not self.is_configured():
            log.warning("YouTube : pas de clé API ou channel ID — service non démarré")
            return
        self._poll_search()
        self._search_timer.start(self.SEARCH_MS)

    def stop(self):
        self._search_timer.stop()
        self._viewers_timer.stop()

    # ── Recherche live (toutes les 3 min) ────────────────────────────

    def _poll_search(self):
        threading.Thread(target=self._worker_search, daemon=True).start()

    def _worker_search(self):
        try:
            r = httpx.get(f"{API}/search", params={
                "part":        "snippet",
                "channelId":   self.channel_id,
                "type":        "video",
                "eventType":   "live",
                "maxResults":  1,
                "key":         YOUTUBE_API_KEY,
            }, timeout=8)

            if r.status_code == 403:
                log.error("YouTube : clé API invalide ou quota dépassé")
                self.connection_lost.emit()
                return

            items = r.json().get("items", []) if r.status_code == 200 else []

            if not items:
                # Pas en live
                with self._lock:
                    self._data.is_live      = False
                    self._data.viewers      = 0
                    self._data.uptime_sec   = 0
                    self._data.display_name = self.display_name
                    self._data.channel_id   = self.channel_id
                snapshot = self.data
                # Retour au thread principal pour toute opération Qt
                QTimer.singleShot(0, self._viewers_timer.stop)
                QTimer.singleShot(0, lambda: self.data_updated.emit(snapshot))
                return

            video_id = items[0]["id"]["videoId"]
            title    = items[0]["snippet"].get("title", "")

            with self._lock:
                self._data.is_live      = True
                self._data.video_id     = video_id
                self._data.title        = title
                self._data.display_name = self.display_name
                self._data.channel_id   = self.channel_id

            QTimer.singleShot(0, self._start_viewers_timer)
            self._poll_viewers_now(video_id)

        except Exception as e:
            log.error("Erreur search : %s", e)

    def _start_viewers_timer(self):
        if not self._viewers_timer.isActive():
            self._viewers_timer.start(self.VIEWERS_MS)

    # ── Viewers (toutes les 30 s quand live) ─────────────────────────

    def _poll_viewers(self):
        vid = self._data.video_id
        if vid:
            threading.Thread(target=self._poll_viewers_now,
                             args=(vid,), daemon=True).start()

    def _poll_viewers_now(self, video_id: str):
        try:
            r = httpx.get(f"{API}/videos", params={
                "part": "liveStreamingDetails",
                "id":   video_id,
                "key":  YOUTUBE_API_KEY,
            }, timeout=8)

            if r.status_code != 200:
                return

            items = r.json().get("items", [])
            if not items:
                return

            details = items[0].get("liveStreamingDetails", {})
            try:
                viewers = int(details.get("concurrentViewers", 0))
            except (ValueError, TypeError):
                viewers = 0

            started_str = details.get("actualStartTime", "")
            uptime = 0
            if started_str:
                try:
                    dt     = datetime.fromisoformat(started_str.replace("Z", "+00:00"))
                    uptime = int((datetime.now(timezone.utc) - dt).total_seconds())
                except Exception:
                    pass

            with self._lock:
                self._data.viewers    = viewers
                self._data.uptime_sec = uptime

            snapshot = self.data
            QTimer.singleShot(0, lambda: self.data_updated.emit(snapshot))

        except Exception as e:
            log.error("Erreur viewers : %s", e)

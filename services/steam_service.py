"""
Steam Web API — stats CS2 à vie (K/D, wins, HS%) depuis le profil Steam.
Nécessite une Steam API Key (steamcommunity.com/dev/apikey) et le SteamID64.
"""

import threading
from dataclasses import dataclass, field

import httpx
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from core.config import Config
from core.constants import STEAM_API_KEY
import core.logger as _log_mod

log = _log_mod.get("steam_service")

_CS2_APP_ID = 730
_API_BASE   = "https://api.steampowered.com"


@dataclass
class SteamData:
    steam_id:    str   = ""
    persona:     str   = ""
    kills:       int   = 0
    deaths:      int   = 0
    wins:        int   = 0   # matchs gagnés
    hs_kills:    int   = 0
    shots_hit:   int   = 0
    shots_fired: int   = 0
    # NB : l'API Steam GetUserStatsForGame n'expose pas les assists pour CS2.

    def kd_fmt(self) -> str:
        if not self.deaths:
            return "-.--"
        return f"{self.kills / self.deaths:.2f}"

    def hs_pct(self) -> str:
        if not self.kills:
            return "--%"
        pct = self.hs_kills / self.kills * 100
        return f"{pct:.0f}%"

    def acc_pct(self) -> str:
        if not self.shots_fired:
            return "--%"
        pct = self.shots_hit / self.shots_fired * 100
        return f"{pct:.1f}%"


class SteamService(QObject):
    data_updated = pyqtSignal(object)   # SteamData

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self._config = config
        self._data   = SteamData()

    @property
    def steam_id(self) -> str:
        return self._config.get("steam_id", "")

    @property
    def data(self) -> SteamData:
        return SteamData(**vars(self._data))

    def is_configured(self) -> bool:
        return bool(STEAM_API_KEY and self.steam_id)

    def fetch(self):
        if not self.is_configured():
            log.warning("Steam : clé API ou SteamID manquant")
            return
        threading.Thread(target=self._worker, daemon=True).start()

    # ── Worker ────────────────────────────────────────────────────────

    def _worker(self):
        steam_id = self.steam_id
        try:
            r = httpx.get(f"{_API_BASE}/ISteamUserStats/GetUserStatsForGame/v2/", params={
                "appid":   _CS2_APP_ID,
                "key":     STEAM_API_KEY,
                "steamid": steam_id,
            }, timeout=10)

            if r.status_code == 403:
                log.warning("Steam : profil privé ou clé invalide (HTTP 403)")
                return
            if r.status_code != 200:
                log.warning("Steam : HTTP %d", r.status_code)
                return

            stats_list = r.json().get("playerstats", {}).get("stats", [])
            stats = {s["name"]: s["value"] for s in stats_list}

            d = SteamData(steam_id=steam_id)
            d.kills       = stats.get("total_kills",           0)
            d.deaths      = stats.get("total_deaths",          0)
            d.wins        = stats.get("total_matches_won",     0)
            d.hs_kills    = stats.get("total_kills_headshot",  0)
            d.shots_hit   = stats.get("total_shots_hit",       0)
            d.shots_fired = stats.get("total_shots_fired",     0)

            self._data = d
            log.info("Steam stats — K:%d D:%d KD:%s HS:%s",
                     d.kills, d.deaths, d.kd_fmt(), d.hs_pct())

            snapshot = self.data
            QTimer.singleShot(0, lambda: self.data_updated.emit(snapshot))

        except Exception as e:
            log.error("Steam stats erreur : %s", e)

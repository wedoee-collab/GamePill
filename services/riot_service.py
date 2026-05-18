"""
Riot Games API — Valorant & League of Legends.
Clé personnelle (developer.riotgames.com) — se renouvelle toutes les 24h.
Polling toutes les 2 min (limite : 100 req/2min sur clé perso).
"""

import threading
from datetime import datetime, timezone

import httpx
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from core.config import Config
from core.constants import RIOT_API_KEY
import core.logger as _log_mod

log = _log_mod.get("riot")

# Jeux supportés par ce service
SUPPORTED_GAMES = {"valorant", "league"}

# Mapping région → URL régionale (account, match history)
_REGIONAL = {
    "EUW": "europe", "EUNE": "europe", "TR": "europe", "RU": "europe",
    "NA":  "americas", "BR": "americas", "LAN": "americas", "LAS": "americas",
    "KR":  "asia", "JP": "asia",
    "OCE": "sea",
}

# Mapping région → plateforme (summoner, ranked)
_PLATFORM = {
    "EUW": "euw1", "EUNE": "eun1", "TR": "tr1", "RU": "ru",
    "NA":  "na1",  "BR":  "br1",  "LAN": "la1", "LAS": "la2",
    "KR":  "kr",   "JP":  "jp1",
    "OCE": "oc1",
}

# Tiers Valorant (competitive_tier → display)
_VAL_TIERS = {
    0: "Non classé", 3: "Iron I", 4: "Iron II", 5: "Iron III",
    6: "Bronze I",   7: "Bronze II",   8: "Bronze III",
    9: "Silver I",   10: "Silver II",  11: "Silver III",
    12: "Gold I",    13: "Gold II",    14: "Gold III",
    15: "Plat I",    16: "Plat II",    17: "Plat III",
    18: "Diamond I", 19: "Diamond II", 20: "Diamond III",
    21: "Asc I",     22: "Asc II",     23: "Asc III",
    24: "Immortal I",25: "Immortal II",26: "Immortal III",
    27: "Radiant",
}

# Tiers LoL
_LOL_TIERS = {
    "IRON": "Iron", "BRONZE": "Bronze", "SILVER": "Silver",
    "GOLD": "Gold", "PLATINUM": "Platinum", "EMERALD": "Emerald",
    "DIAMOND": "Diamond", "MASTER": "Master",
    "GRANDMASTER": "Grandmaster", "CHALLENGER": "Challenger",
}
_LOL_RANKS = {"I": "I", "II": "II", "III": "III", "IV": "IV"}


class RiotService(QObject):
    data_updated = pyqtSignal(str, dict, list)  # (game_key, kda_dict, history_list)

    POLL_MS = 120_000   # 2 min

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self._config       = config
        self._current_game: str | None = None
        self._puuid_cache: dict[str, str] = {}   # game_key → puuid

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)

    # ── API publique ──────────────────────────────────────────────────

    def is_configured(self) -> bool:
        return bool(
            RIOT_API_KEY
            and self._config.get("riot_game_name")
            and self._config.get("riot_tag_line")
        )

    def on_game_changed(self, game_key: str):
        """Branché sur GameDetector.game_changed."""
        new_game = game_key if game_key in SUPPORTED_GAMES else None
        if new_game != self._current_game:
            self._current_game = new_game
            if new_game:
                self._poll()
                self._timer.start(self.POLL_MS)
            else:
                self._timer.stop()

    def start(self):
        if self.is_configured() and self._current_game:
            self._poll()
            self._timer.start(self.POLL_MS)

    def stop(self):
        self._timer.stop()

    # ── Polling ───────────────────────────────────────────────────────

    def _poll(self):
        if self._current_game and self.is_configured():
            threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        game = self._current_game
        if not game:
            return
        try:
            result = self._fetch_valorant() if game == "valorant" else self._fetch_league()
            if result:
                kda, history = result
                QTimer.singleShot(0, lambda: self.data_updated.emit(game, kda, history))
        except Exception as e:
            log.error("Erreur fetch %s : %s", game, e)

    # ── PUUID (partagé Valorant + LoL) ───────────────────────────────

    def _get_puuid(self, game_key: str) -> str | None:
        if game_key in self._puuid_cache:
            return self._puuid_cache[game_key]

        name   = self._config.get("riot_game_name", "")
        tag    = self._config.get("riot_tag_line", "")
        region = self._config.get("riot_region", "EUW")
        regional = _REGIONAL.get(region, "europe")

        try:
            r = httpx.get(
                f"https://{regional}.api.riotgames.com"
                f"/riot/account/v1/accounts/by-riot-id/{name}/{tag}",
                headers={"X-Riot-Token": RIOT_API_KEY},
                timeout=8,
            )
            if r.status_code == 200:
                puuid = r.json().get("puuid", "")
                if puuid:
                    self._puuid_cache[game_key] = puuid
                    return puuid
            else:
                log.warning("PUUID HTTP %d : %s", r.status_code, r.text[:150])
        except Exception as e:
            log.error("PUUID erreur : %s", e)
        return None

    def _headers(self) -> dict:
        return {"X-Riot-Token": RIOT_API_KEY}

    def _get(self, url: str, params: dict | None = None) -> dict | None:
        try:
            r = httpx.get(url, params=params, headers=self._headers(),
                          timeout=8)
            return r.json() if r.status_code == 200 else None
        except Exception as e:
            log.error("HTTP erreur %s : %s", url, e)
            return None

    # ── Valorant ──────────────────────────────────────────────────────

    def _fetch_valorant(self) -> tuple[dict, list] | None:
        puuid    = self._get_puuid("valorant")
        if not puuid:
            return None

        region   = self._config.get("riot_region", "EUW")
        regional = _REGIONAL.get(region, "europe")

        # Dernières parties
        ml = self._get(
            f"https://{regional}.api.riotgames.com/val/match/v1/matchlists/by-puuid/{puuid}"
        )
        if not ml:
            return None

        match_ids = [h["matchId"] for h in ml.get("history", [])[:5]]
        if not match_ids:
            return None

        kda_list = []
        last_rank = ""
        last_agent = ""

        for mid in match_ids:
            m = self._get(
                f"https://{regional}.api.riotgames.com/val/match/v1/matches/{mid}"
            )
            if not m:
                continue
            players = m.get("players", {}).get("allPlayers", [])
            me = next((p for p in players if p.get("puuid") == puuid), None)
            if not me:
                continue
            stats = me.get("stats", {})
            kda_list.append({
                "k": stats.get("kills", 0),
                "d": stats.get("deaths", 0),
                "a": stats.get("assists", 0),
                "win": me.get("teamId", "").lower() == (
                    m.get("teams", {}).get("red", {}).get("won") and "red" or "blue"
                ),
            })
            if not last_rank:
                tier = me.get("competitiveTier", 0)
                last_rank  = _VAL_TIERS.get(tier, "")
                last_agent = me.get("characterId", "")[:4].upper() or "—"

        if not kda_list:
            return None

        # KDA moyen sur les 5 dernières parties
        avg_k = round(sum(g["k"] for g in kda_list) / len(kda_list), 1)
        avg_d = round(sum(g["d"] for g in kda_list) / len(kda_list), 1)
        avg_a = round(sum(g["a"] for g in kda_list) / len(kda_list), 1)

        kda = {
            "k":     avg_k,
            "d":     avg_d,
            "a":     avg_a,
            "agent": last_agent,
            "rank":  last_rank,
        }
        return kda, kda_list[:5]

    # ── League of Legends ─────────────────────────────────────────────

    def _fetch_league(self) -> tuple[dict, list] | None:
        puuid    = self._get_puuid("league")
        if not puuid:
            return None

        region   = self._config.get("riot_region", "EUW")
        platform = _PLATFORM.get(region, "euw1")
        regional = _REGIONAL.get(region, "europe")

        # Summoner
        summoner = self._get(
            f"https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        )
        if not summoner:
            return None
        summoner_id = summoner.get("id", "")

        # Ranked
        rank_str = ""
        entries = self._get(
            f"https://{platform}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
        )
        if entries:
            solo = next((e for e in entries if e.get("queueType") == "RANKED_SOLO_5x5"), None)
            if solo:
                tier = _LOL_TIERS.get(solo.get("tier", ""), solo.get("tier", ""))
                rank = solo.get("rank", "")
                lp   = solo.get("leaguePoints", 0)
                rank_str = f"{tier} {rank} · {lp} LP"

        # 5 dernières parties classées
        match_ids_resp = self._get(
            f"https://{regional}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids",
            params={"count": 5, "type": "ranked"},
        )
        match_ids = match_ids_resp if isinstance(match_ids_resp, list) else []

        kda_list = []
        last_champ = ""

        for mid in match_ids:
            m = self._get(
                f"https://{regional}.api.riotgames.com/lol/match/v5/matches/{mid}"
            )
            if not m:
                continue
            participants = m.get("info", {}).get("participants", [])
            me = next((p for p in participants if p.get("puuid") == puuid), None)
            if not me:
                continue

            kda_list.append({
                "k":   me.get("kills", 0),
                "d":   me.get("deaths", 0),
                "a":   me.get("assists", 0),
                "win": me.get("win", False),
            })
            if not last_champ:
                last_champ = me.get("championName", "—")

        if not kda_list:
            # Pas de ranked récent — on renvoie juste le rang
            return {"k": "--", "d": "--", "a": "--",
                    "agent": last_champ or "—", "rank": rank_str}, []

        avg_k = round(sum(g["k"] for g in kda_list) / len(kda_list), 1)
        avg_d = round(sum(g["d"] for g in kda_list) / len(kda_list), 1)
        avg_a = round(sum(g["a"] for g in kda_list) / len(kda_list), 1)

        kda = {
            "k":     avg_k,
            "d":     avg_d,
            "a":     avg_a,
            "agent": last_champ,
            "rank":  rank_str,
        }
        return kda, kda_list[:5]

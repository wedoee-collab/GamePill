import psutil
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from core.themes import THEMES, GameTheme

PROCESS_MAP: dict[str, str] = {
    "VALORANT.exe":                          "valorant",
    "LeagueOfLegends.exe":                   "league",
    "cs2.exe":                               "cs2",
    "FortniteClient-Win64-Shipping.exe":     "fortnite",
    "r5apex.exe":                            "apex",
    "GTA5.exe":                              "gta",
    "Overwatch.exe":                         "overwatch",
    "dota2.exe":                             "dota2",
    "RocketLeague.exe":                      "rocket_league",
    "ModernWarfare.exe":                     "cod",
    "cod.exe":                               "cod",
    "DeadByDaylight-Win64-Shipping.exe":     "dbd",
    "Hearthstone.exe":                       "hearthstone",
    "TslGame.exe":                           "pubg",
    "Minecraft.Windows.exe":                 "minecraft",
}

# Stats vides : affichées tant qu'aucun service réel (Riot, CS2 GSI,
# Steam) n'a fourni de vraies données. Aucune stat fictive.
_EMPTY_KDA: dict = {"k": "--", "d": "--", "a": "--", "agent": "", "rank": ""}


class GameDetector(QObject):
    game_changed = pyqtSignal(str, object)  # (game_key, GameTheme)

    def __init__(self, config=None, parent=None):
        super().__init__(parent)
        self._config = config
        self._current_key: str | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._scan)
        self._timer.start(10_000)

    def start(self):
        self._scan()

    def rescan(self):
        """Relance une détection immédiate (après un changement de réglages)."""
        self._scan()

    def current_kda(self) -> dict:
        # Pas de stats fictives : les vraies viennent des services API.
        return dict(_EMPTY_KDA)

    def current_history(self) -> list:
        return []

    def current_theme(self) -> GameTheme:
        return THEMES.get(self._current_key or "default", THEMES["default"])

    def _scan(self):
        detected: str | None = None
        try:
            for proc in psutil.process_iter(["name"]):
                try:
                    name = proc.info.get("name", "") or ""
                    if name in PROCESS_MAP:
                        detected = PROCESS_MAP[name]
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception:
            pass  # psutil itself failed — keep previous state

        # Jeux désactivés par l'utilisateur dans les réglages → ignorés
        if detected and self._config:
            disabled = self._config.get("games_disabled", []) or []
            if detected in disabled:
                detected = None

        if detected != self._current_key:
            self._current_key = detected
            key = detected or "default"
            try:
                self.game_changed.emit(key, THEMES[key])
            except Exception:
                pass

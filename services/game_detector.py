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

MOCK_KDA: dict[str, dict] = {
    "valorant":     {"k": 8,  "d": 2, "a": 5,  "agent": "Jett",    "rank": "Diamond II"},
    "league":       {"k": 12, "d": 4, "a": 18, "agent": "Jinx",    "rank": "Platinum I"},
    "cs2":          {"k": 24, "d": 10,"a": 0,  "agent": "CT",      "rank": "MG1"},
    "fortnite":     {"k": 6,  "d": 1, "a": 0,  "agent": "Jonesy",  "rank": "Champion"},
    "apex":         {"k": 9,  "d": 1, "a": 4,  "agent": "Wraith",  "rank": "Diamond"},
    "gta":          {"k": 0,  "d": 0, "a": 0,  "agent": "",        "rank": "Online"},
    "overwatch":    {"k": 28, "d": 7, "a": 0,  "agent": "Tracer",  "rank": "Master"},
    "dota2":        {"k": 14, "d": 5, "a": 22, "agent": "Pudge",   "rank": "Ancient 3"},
    "rocket_league":{"k": 3,  "d": 2, "a": 1,  "agent": "",        "rank": "Diamond III"},
    "cod":          {"k": 18, "d": 8, "a": 0,  "agent": "",        "rank": "Top 250"},
    "dbd":          {"k": 4,  "d": 0, "a": 0,  "agent": "Trapper", "rank": "Iri I"},
    "hearthstone":  {"k": 0,  "d": 0, "a": 0,  "agent": "Warrior", "rank": "Legend"},
    "pubg":         {"k": 5,  "d": 1, "a": 0,  "agent": "",        "rank": "Top 100"},
    "minecraft":    {"k": 0,  "d": 2, "a": 0,  "agent": "Survival","rank": ""},
    "default":      {"k": 0,  "d": 0, "a": 0,  "agent": "",        "rank": ""},
}

MOCK_HISTORY: dict[str, list] = {
    "valorant":  [
        {"k": 12,"d": 3, "a": 7,  "win": True},
        {"k": 5, "d": 8, "a": 2,  "win": False},
        {"k": 18,"d": 1, "a": 10, "win": True},
        {"k": 8, "d": 6, "a": 4,  "win": True},
        {"k": 3, "d": 9, "a": 1,  "win": False},
    ],
    "default": [
        {"k": 8, "d": 4, "a": 6,  "win": True},
        {"k": 6, "d": 7, "a": 3,  "win": False},
        {"k": 14,"d": 2, "a": 8,  "win": True},
        {"k": 5, "d": 8, "a": 1,  "win": False},
        {"k": 10,"d": 3, "a": 5,  "win": True},
    ],
}


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
        if not self._current_key:
            # Aucun jeu détecté — on affiche rien
            return {"k": "--", "d": "--", "a": "--", "agent": "", "rank": ""}
        return MOCK_KDA.get(self._current_key, MOCK_KDA["default"])

    def current_history(self) -> list:
        if not self._current_key:
            return []
        return MOCK_HISTORY.get(self._current_key, MOCK_HISTORY["default"])

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

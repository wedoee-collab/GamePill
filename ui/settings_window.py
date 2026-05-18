"""
Fenêtre de réglages GamePill.
Pilote les plateformes, les jeux détectés, l'affichage de la pill et les alertes.
S'ouvre au double-clic sur l'icône du tray.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QCheckBox, QScrollArea, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.themes import THEMES
from core.version import APP_VERSION
import core.autostart as autostart


_PLATFORMS = [
    ("twitch",  "Twitch",  "#9146FF"),
    ("youtube", "YouTube", "#FF0000"),
    ("kick",    "Kick",    "#53FC18"),
]

_DISPLAY = [
    ("show_viewers", "Viewers"),
    ("show_peak",    "Pic de viewers"),
    ("show_game",    "Nom du jeu"),
    ("show_kda",     "KDA"),
]

_QSS = """
QWidget {
    background: #0c0c14;
    color: #e8e8f0;
    font-family: 'Segoe UI';
    font-size: 10pt;
}
QLabel#header {
    background: #12121e;
    color: #ffffff;
    font-size: 15pt;
    font-weight: 700;
    border-bottom: 1px solid rgba(145,70,255,0.28);
    padding-left: 20px;
}
QFrame#card {
    background: #15151f;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
}
QLabel#sectionTitle {
    color: #D4AF37;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 2px;
}
QLabel#hint { color: rgba(255,255,255,0.40); font-size: 9pt; }
QLabel#rowName { font-weight: 600; }
QCheckBox { spacing: 8px; padding: 3px; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border-radius: 4px;
    border: 1px solid rgba(255,255,255,0.25);
    background: rgba(255,255,255,0.05);
}
QCheckBox::indicator:checked {
    background: #9146FF;
    border: 1px solid #9146FF;
}
QCheckBox:disabled { color: rgba(255,255,255,0.30); }
QPushButton#smallBtn {
    background: rgba(145,70,255,0.18);
    border: 1px solid rgba(145,70,255,0.40);
    border-radius: 8px;
    padding: 5px 14px;
    color: #ffffff;
    font-size: 9pt;
}
QPushButton#smallBtn:hover  { background: rgba(145,70,255,0.30); }
QPushButton#smallBtn:pressed{ background: rgba(145,70,255,0.12); }
QScrollArea { border: none; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }
QScrollBar::handle:vertical {
    background: rgba(145,70,255,0.40); border-radius: 4px; min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
"""


class SettingsWindow(QWidget):
    platform_connect    = pyqtSignal(str)
    platform_disconnect = pyqtSignal(str)
    settings_changed    = pyqtSignal()
    check_updates       = pyqtSignal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config  = config
        self._loading = False
        self._pf      = {}
        self._games   = {}
        self._disp    = {}
        self.setWindowTitle("Réglages GamePill")
        self.setFixedSize(560, 740)
        self.setStyleSheet(_QSS)
        self._build()
        self.refresh()

    # ── Construction ──────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QLabel("Réglages")
        header.setObjectName("header")
        header.setFixedHeight(54)
        root.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        col = QVBoxLayout(content)
        col.setContentsMargins(20, 18, 20, 24)
        col.setSpacing(16)
        col.addWidget(self._build_platforms())
        col.addWidget(self._build_games())
        col.addWidget(self._build_display())
        col.addWidget(self._build_alerts())
        col.addWidget(self._build_general())
        col.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll, 1)

    def _card(self, title: str):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 14, 18, 16)
        lay.setSpacing(10)
        lbl = QLabel(title.upper())
        lbl.setObjectName("sectionTitle")
        lay.addWidget(lbl)
        return card, lay

    def _build_platforms(self):
        card, lay = self._card("Plateformes")
        hint = QLabel("Décoche une plateforme pour la masquer sans te déconnecter.")
        hint.setObjectName("hint")
        lay.addWidget(hint)
        for key, name, color in _PLATFORMS:
            row = QHBoxLayout()
            row.setSpacing(10)

            dot = QLabel("●")
            dot.setStyleSheet(f"color:{color}; font-size:13px;")

            nm = QLabel(name)
            nm.setObjectName("rowName")
            nm.setFixedWidth(64)

            status = QLabel("…")
            status.setFixedWidth(110)

            btn = QPushButton("…")
            btn.setObjectName("smallBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self._on_platform_btn(k))

            active = QCheckBox("Actif")
            active.toggled.connect(self._on_platform_active)

            row.addWidget(dot)
            row.addWidget(nm)
            row.addWidget(status)
            row.addStretch()
            row.addWidget(btn)
            row.addWidget(active)
            lay.addLayout(row)
            self._pf[key] = {"status": status, "btn": btn, "active": active}
        return card

    def _build_games(self):
        card, lay = self._card("Jeux détectés")
        hint = QLabel("Décoche les jeux que GamePill doit ignorer.")
        hint.setObjectName("hint")
        lay.addWidget(hint)
        grid = QGridLayout()
        grid.setSpacing(6)
        games = [(k, t.name) for k, t in THEMES.items() if k != "default"]
        for i, (key, name) in enumerate(games):
            cb = QCheckBox(name)
            cb.toggled.connect(self._on_game_toggled)
            grid.addWidget(cb, i // 2, i % 2)
            self._games[key] = cb
        lay.addLayout(grid)
        return card

    def _build_display(self):
        card, lay = self._card("Affichage de la pill")
        hint = QLabel("Choisis ce qui apparaît dans la barre.")
        hint.setObjectName("hint")
        lay.addWidget(hint)
        grid = QGridLayout()
        grid.setSpacing(6)
        for i, (key, label) in enumerate(_DISPLAY):
            cb = QCheckBox(label)
            cb.toggled.connect(self._on_display_toggled)
            grid.addWidget(cb, i // 2, i % 2)
            self._disp[key] = cb
        lay.addLayout(grid)
        return card

    def _build_alerts(self):
        card, lay = self._card("Alertes")
        self._alerts_cb = QCheckBox("Alertes follow / sub / raid (animation et notification)")
        self._alerts_cb.toggled.connect(self._on_alerts_toggled)
        lay.addWidget(self._alerts_cb)
        return card

    def _build_general(self):
        card, lay = self._card("Général")
        self._autostart_cb = QCheckBox("Démarrer GamePill avec Windows")
        self._autostart_cb.toggled.connect(self._on_autostart)
        lay.addWidget(self._autostart_cb)

        row = QHBoxLayout()
        upd = QPushButton("Vérifier les mises à jour")
        upd.setObjectName("smallBtn")
        upd.setCursor(Qt.CursorShape.PointingHandCursor)
        upd.clicked.connect(self.check_updates.emit)
        row.addWidget(upd)
        row.addStretch()
        ver = QLabel(f"version {APP_VERSION}")
        ver.setObjectName("hint")
        row.addWidget(ver)
        lay.addLayout(row)
        return card

    # ── État ──────────────────────────────────────────────────────────

    def _is_connected(self, key: str) -> bool:
        return {
            "twitch":  bool(self._config.get("twitch_access_token")),
            "youtube": bool(self._config.get("youtube_channel_id")),
            "kick":    bool(self._config.get("kick_slug")),
        }.get(key, False)

    def refresh(self):
        """Resynchronise tous les contrôles depuis la config."""
        self._loading = True

        pf_disabled = self._config.get("platforms_disabled", []) or []
        for key, w in self._pf.items():
            conn = self._is_connected(key)
            w["status"].setText("Connecté" if conn else "Non connecté")
            w["status"].setStyleSheet(
                "color:#4ade80;" if conn else "color:rgba(255,255,255,0.40);"
            )
            w["btn"].setText("Déconnecter" if conn else "Connecter")
            w["active"].setEnabled(conn)
            w["active"].setChecked(conn and key not in pf_disabled)

        g_disabled = self._config.get("games_disabled", []) or []
        for key, cb in self._games.items():
            cb.setChecked(key not in g_disabled)

        for key, cb in self._disp.items():
            cb.setChecked(bool(self._config.get(key, True)))

        self._alerts_cb.setChecked(bool(self._config.get("alerts_enabled", True)))
        self._autostart_cb.setChecked(autostart.is_enabled())

        self._loading = False

    # ── Handlers ──────────────────────────────────────────────────────

    def _on_platform_btn(self, key: str):
        if self._is_connected(key):
            self.platform_disconnect.emit(key)
        else:
            self.platform_connect.emit(key)

    def _on_platform_active(self):
        if self._loading:
            return
        disabled = [k for k, w in self._pf.items() if not w["active"].isChecked()]
        self._config.set("platforms_disabled", disabled)
        self.settings_changed.emit()

    def _on_game_toggled(self):
        if self._loading:
            return
        disabled = [k for k, cb in self._games.items() if not cb.isChecked()]
        self._config.set("games_disabled", disabled)
        self.settings_changed.emit()

    def _on_display_toggled(self):
        if self._loading:
            return
        for key, cb in self._disp.items():
            self._config.set(key, cb.isChecked())
        self.settings_changed.emit()

    def _on_alerts_toggled(self, checked: bool):
        if self._loading:
            return
        self._config.set("alerts_enabled", checked)
        self.settings_changed.emit()

    def _on_autostart(self, checked: bool):
        if self._loading:
            return
        if checked:
            autostart.enable()
        else:
            autostart.disable()

    # Fermer = masquer (la fenêtre est réutilisée)
    def closeEvent(self, event):
        event.ignore()
        self.hide()

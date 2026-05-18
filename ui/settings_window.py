"""
Fenêtre de réglages GamePill.
Pilote les plateformes, les jeux détectés, l'affichage de la pill et les alertes.
S'ouvre au double-clic sur l'icône du tray.

Style : épuré, inspiré de macOS System Settings.
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
    background: #0a0a11;
    color: #ececf2;
    font-family: 'Segoe UI';
    font-size: 10pt;
}
QLabel#title {
    color: #ffffff;
    font-size: 19pt;
    font-weight: 800;
    letter-spacing: -0.5px;
}
QLabel#subtitle {
    color: rgba(236,236,242,0.45);
    font-size: 9.5pt;
}
QFrame#card {
    background: #14141d;
    border: 1px solid rgba(255,255,255,0.055);
    border-radius: 16px;
}
QLabel#sectionTitle {
    color: rgba(236,236,242,0.45);
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 2.5px;
}
QLabel#hint   { color: rgba(236,236,242,0.38); font-size: 9pt; }
QLabel#rowName{ font-size: 10.5pt; font-weight: 600; color: #f3f3f7; }
QLabel#ver    { color: rgba(236,236,242,0.30); font-size: 9pt; }
QLabel#hair   { background: rgba(255,255,255,0.06); }

QCheckBox { spacing: 9px; padding: 4px 2px; color: #dcdce4; }
QCheckBox::indicator {
    width: 19px; height: 19px;
    border-radius: 6px;
    border: 1px solid rgba(255,255,255,0.22);
    background: rgba(255,255,255,0.045);
}
QCheckBox::indicator:hover { border-color: rgba(145,70,255,0.6); }
QCheckBox::indicator:checked {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #a45dff, stop:1 #7d2fd6);
    border: 1px solid #9146FF;
}
QCheckBox:disabled { color: rgba(236,236,242,0.25); }
QCheckBox::indicator:disabled {
    border-color: rgba(255,255,255,0.10);
    background: rgba(255,255,255,0.02);
}

QPushButton#btn {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 9px;
    padding: 6px 16px;
    color: #f3f3f7;
    font-size: 9pt;
    font-weight: 600;
}
QPushButton#btn:hover   { background: rgba(255,255,255,0.12); }
QPushButton#btn:pressed { background: rgba(255,255,255,0.05); }

QPushButton#btnAccent {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #9146FF, stop:1 #7d2fd6);
    border: 1px solid rgba(212,175,55,0.30);
    border-radius: 9px;
    padding: 6px 16px;
    color: #ffffff;
    font-size: 9pt;
    font-weight: 700;
}
QPushButton#btnAccent:hover   { background: #a45dff; }
QPushButton#btnAccent:pressed { background: #7d2fd6; }

QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 4px 2px; }
QScrollBar::handle:vertical {
    background: rgba(255,255,255,0.14); border-radius: 4px; min-height: 36px;
}
QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.22); }
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
        self.setFixedSize(560, 760)
        self.setStyleSheet(_QSS)
        self._build()
        self.refresh()

    # ── Construction ──────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # En-tête
        header = QWidget()
        header.setFixedHeight(96)
        header.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 #16111f, stop:1 #0a0a11);"
        )
        hl = QVBoxLayout(header)
        hl.setContentsMargins(28, 22, 28, 0)
        hl.setSpacing(2)
        title = QLabel("Réglages")
        title.setObjectName("title")
        subtitle = QLabel("Personnalise ce que GamePill affiche et surveille.")
        subtitle.setObjectName("subtitle")
        hl.addWidget(title)
        hl.addWidget(subtitle)
        root.addWidget(header)

        accent = QFrame()
        accent.setFixedHeight(2)
        accent.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 rgba(212,175,55,0.7), stop:0.35 rgba(145,70,255,0.5),"
            "stop:1 rgba(145,70,255,0));"
        )
        root.addWidget(accent)

        # Contenu défilant
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        col = QVBoxLayout(content)
        col.setContentsMargins(22, 22, 22, 26)
        col.setSpacing(18)
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
        lay.setContentsMargins(22, 18, 22, 20)
        lay.setSpacing(12)
        lbl = QLabel(title.upper())
        lbl.setObjectName("sectionTitle")
        lay.addWidget(lbl)
        return card, lay

    def _hair(self) -> QFrame:
        line = QFrame()
        line.setObjectName("hair")
        line.setFixedHeight(1)
        return line

    def _build_platforms(self):
        card, lay = self._card("Plateformes")
        hint = QLabel("Décoche une plateforme pour la masquer sans te déconnecter.")
        hint.setObjectName("hint")
        lay.addWidget(hint)

        for idx, (key, name, color) in enumerate(_PLATFORMS):
            if idx:
                lay.addWidget(self._hair())
            row = QHBoxLayout()
            row.setContentsMargins(0, 4, 0, 4)
            row.setSpacing(11)

            dot = QLabel("●")
            dot.setStyleSheet(f"color:{color}; font-size:13px;")

            nm = QLabel(name)
            nm.setObjectName("rowName")
            nm.setFixedWidth(62)

            status = QLabel("…")
            status.setMinimumWidth(106)
            status.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn = QPushButton("…")
            btn.setObjectName("btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedWidth(108)
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
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(3)
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
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(3)
        for i, (key, label) in enumerate(_DISPLAY):
            cb = QCheckBox(label)
            cb.toggled.connect(self._on_display_toggled)
            grid.addWidget(cb, i // 2, i % 2)
            self._disp[key] = cb
        lay.addLayout(grid)
        return card

    def _build_alerts(self):
        card, lay = self._card("Alertes")
        self._alerts_cb = QCheckBox("Alertes follow / sub / raid  (animation et notification)")
        self._alerts_cb.toggled.connect(self._on_alerts_toggled)
        lay.addWidget(self._alerts_cb)
        return card

    def _build_general(self):
        card, lay = self._card("Général")
        self._autostart_cb = QCheckBox("Démarrer GamePill avec Windows")
        self._autostart_cb.toggled.connect(self._on_autostart)
        lay.addWidget(self._autostart_cb)
        lay.addWidget(self._hair())

        row = QHBoxLayout()
        row.setContentsMargins(0, 2, 0, 0)
        upd = QPushButton("Vérifier les mises à jour")
        upd.setObjectName("btn")
        upd.setCursor(Qt.CursorShape.PointingHandCursor)
        upd.clicked.connect(self.check_updates.emit)
        row.addWidget(upd)
        row.addStretch()
        ver = QLabel(f"GamePill {APP_VERSION}")
        ver.setObjectName("ver")
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
            if conn:
                w["status"].setText("Connecté")
                w["status"].setStyleSheet(
                    "color:#5fd98a; background:rgba(95,217,138,0.12);"
                    "border-radius:9px; padding:3px 12px; font-size:8.5pt; font-weight:600;"
                )
            else:
                w["status"].setText("Non connecté")
                w["status"].setStyleSheet(
                    "color:rgba(236,236,242,0.40); background:rgba(255,255,255,0.05);"
                    "border-radius:9px; padding:3px 12px; font-size:8.5pt;"
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

import math

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
)
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QPainterPath, QLinearGradient, QBrush,
)

from core.themes import GameTheme, THEMES


def _sf(size: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    return QFont("Segoe UI", size, int(weight))


def _hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


class StatCard(QWidget):
    def __init__(self, label: str, value, color: str):
        super().__init__()
        self._color = color
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            "StatCard { background-color: rgba(255,255,255,9);"
            " border: 1px solid rgba(255,255,255,14); border-radius: 13px; }"
        )
        self.setMinimumHeight(60)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setSpacing(3)

        self._val_lbl = QLabel(str(value))
        self._val_lbl.setFont(_sf(20, QFont.Weight.Bold))
        self._val_lbl.setStyleSheet(f"color: {color}; background: transparent;")
        self._val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._key_lbl = QLabel(label.upper())
        self._key_lbl.setFont(_sf(7, QFont.Weight.Medium))
        self._key_lbl.setStyleSheet(
            "color: rgba(255,255,255,70); background: transparent; letter-spacing: 1.5px;"
        )
        self._key_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self._val_lbl)
        layout.addWidget(self._key_lbl)

    def set_value(self, value):
        self._val_lbl.setText(str(value))

    def set_color(self, color: str):
        self._val_lbl.setStyleSheet(f"color: {color}; background: transparent;")


class ExpandedContent(QWidget):
    def __init__(self, theme: GameTheme = None, kda: dict = None, history: list = None):
        super().__init__()
        self._theme = theme or THEMES["default"]
        self._kda = kda or {}
        self._history = history or []
        self._pulse_phase = 0.0
        self._build_ui()
        self._start_pulse()

    def _build_ui(self):
        d = self._kda
        t = self._theme

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 14)
        layout.setSpacing(10)

        # ── Header : nom du jeu + rang ────────────────────────────────
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)

        self._game_title = QLabel("En attente d'un jeu…")
        self._game_title.setFont(_sf(13, QFont.Weight.Bold))
        self._game_title.setStyleSheet("color: white; background: transparent;")

        rank = d.get("rank", "")
        self._rank_lbl = QLabel(rank if rank else "")
        self._rank_lbl.setFont(_sf(10))
        self._rank_lbl.setStyleSheet("color: rgba(255,255,255,100); background: transparent;")
        self._rank_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        hdr.addWidget(self._game_title)
        hdr.addStretch()
        hdr.addWidget(self._rank_lbl)
        layout.addLayout(hdr)

        # ── Accent line ───────────────────────────────────────────────
        self._accent_line = QFrame()
        self._accent_line.setFixedHeight(1)
        self._update_accent(t.primary)
        layout.addWidget(self._accent_line)

        # ── Stats grid 3×2 — valeurs vides par défaut ─────────────────
        grid = QGridLayout()
        grid.setSpacing(6)
        grid.setContentsMargins(0, 0, 0, 0)

        self._cards: dict[str, StatCard] = {}
        stats = [
            ("Kills",   d.get("k", "--"), "#34c759"),
            ("Deaths",  d.get("d", "--"), "#ff3b30"),
            ("Assists", d.get("a", "--"), t.secondary),
            ("Score",   "--",             "rgba(255,255,255,180)"),
            ("HS rate", "--",             "#ff9f0a"),
            ("Agent",   d.get("agent") or "—", t.primary),
        ]
        for i, (label, val, color) in enumerate(stats):
            card = StatCard(label, val, color)
            self._cards[label] = card
            grid.addWidget(card, i // 3, i % 3)

        layout.addLayout(grid)

        # ── Séparateur ────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: rgba(255,255,255,20); border: none;")
        layout.addWidget(sep)

        # ── Stream row ────────────────────────────────────────────────
        stream_row = QHBoxLayout()
        stream_row.setContentsMargins(0, 0, 0, 0)
        stream_row.setSpacing(8)

        self._sdot = QLabel("●")
        self._sdot.setFont(_sf(10))
        self._sdot.setStyleSheet("color: #ff3b30; background: transparent;")

        self._viewers_lbl = QLabel("-- viewers")
        self._viewers_lbl.setFont(_sf(11, QFont.Weight.DemiBold))
        self._viewers_lbl.setStyleSheet("color: rgba(255,255,255,180); background: transparent;")

        self._dur_lbl = QLabel("--")
        self._dur_lbl.setFont(_sf(11))
        self._dur_lbl.setStyleSheet("color: rgba(255,255,255,80); background: transparent;")

        stream_row.addWidget(self._sdot)
        stream_row.addWidget(self._viewers_lbl)
        stream_row.addStretch()
        stream_row.addWidget(self._dur_lbl)
        layout.addLayout(stream_row)

        # ── Compteurs session ─────────────────────────────────────────
        self._session_lbl = QLabel("")
        self._session_lbl.setFont(_sf(9))
        self._session_lbl.setStyleSheet(
            "color: rgba(255,255,255,110); background: transparent; "
            "padding-left: 16px;"
        )
        self._session_lbl.setVisible(False)
        layout.addWidget(self._session_lbl)

        # ── Banner follow/sub — caché par défaut ──────────────────────
        self._banner = QWidget()
        self._banner.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._banner.setStyleSheet(
            "QWidget { background-color: rgba(48,209,88,20);"
            " border-radius: 8px; border: 1px solid rgba(48,209,88,50); }"
        )
        b_layout = QHBoxLayout(self._banner)
        b_layout.setContentsMargins(10, 6, 10, 6)
        b_layout.setSpacing(8)

        star = QLabel("★")
        star.setFont(_sf(12))
        star.setStyleSheet("color: #30d158; background: transparent; border: none;")

        self._banner_text = QLabel("")
        self._banner_text.setFont(_sf(10, QFont.Weight.DemiBold))
        self._banner_text.setStyleSheet("color: #30d158; background: transparent; border: none;")

        b_layout.addWidget(star)
        b_layout.addWidget(self._banner_text)
        b_layout.addStretch()
        layout.addWidget(self._banner)
        self._banner.setVisible(False)

    # ── Helpers ───────────────────────────────────────────────────────

    def _update_accent(self, primary: str):
        r, g, b = _hex_rgb(primary)
        self._accent_line.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 rgba({r},{g},{b},180), stop:0.5 rgba({r},{g},{b},50),"
            f"stop:1 rgba({r},{g},{b},0)); border: none;"
        )

    def _start_pulse(self):
        t = QTimer(self)
        t.timeout.connect(self._tick_pulse)
        t.start(30)

    def _tick_pulse(self):
        self._pulse_phase = (self._pulse_phase + 0.1257) % (2 * math.pi)
        a = int((0.4 + 0.6 * (math.sin(self._pulse_phase) * 0.5 + 0.5)) * 255)
        self._sdot.setStyleSheet(f"color: rgba(255,59,48,{a}); background: transparent;")

    # ── API publique ──────────────────────────────────────────────────

    def apply_theme(self, theme: GameTheme, kda: dict, history: list):
        self._theme = theme
        self._kda = kda

        has_game = theme is not THEMES["default"]

        # Titre du jeu
        if has_game:
            self._game_title.setText(theme.name)
            r, g, b = _hex_rgb(theme.primary)
            self._game_title.setStyleSheet(f"color: rgba({r},{g},{b},230); background: transparent;")
        else:
            self._game_title.setText("En attente d'un jeu…")
            self._game_title.setStyleSheet("color: rgba(255,255,255,120); background: transparent;")

        # Rang
        rank = kda.get("rank", "")
        self._rank_lbl.setText(rank)

        # Accent line
        self._update_accent(theme.primary)

        # Stats
        self._cards["Kills"].set_value(kda.get("k", "--"))
        self._cards["Deaths"].set_value(kda.get("d", "--"))
        self._cards["Assists"].set_value(kda.get("a", "--"))
        self._cards["Agent"].set_value(kda.get("agent") or "—")
        self._cards["Score"].set_value(kda.get("score", "--"))
        self._cards["HS rate"].set_value(kda.get("hs", "--"))

        # Couleurs dynamiques
        self._cards["Assists"].set_color(theme.secondary)
        self._cards["Agent"].set_color(theme.primary)

    def update_stream_data(self, viewers: str, duration: str,
                           last_event: str, is_live: bool,
                           session: dict | None = None):
        self._viewers_lbl.setText(f"{viewers} viewers" if is_live else "Offline")
        self._dur_lbl.setText(duration if is_live else "")

        # Compteurs de session
        s = session or {}
        follows = s.get("follows", 0)
        subs    = s.get("subs", 0)
        raids   = s.get("raids", 0)
        if is_live and (follows or subs or raids):
            parts = []
            if follows: parts.append(f"+{follows} follows")
            if subs:    parts.append(f"+{subs} subs")
            if raids:   parts.append(f"+{raids} raids")
            self._session_lbl.setText("  ·  ".join(parts))
            self._session_lbl.setVisible(True)
        else:
            self._session_lbl.setVisible(False)

        if last_event:
            self._banner_text.setText(f"Nouveau follow — {last_event}")
            self._banner.setVisible(True)
        else:
            self._banner.setVisible(False)

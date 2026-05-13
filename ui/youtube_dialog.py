"""
Dialog de connexion YouTube — saisie du @handle, pas d'OAuth.
Branding YouTube rouge/sombre.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QWidget, QFrame,
)
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPainterPath, QLinearGradient,
    QBrush, QPen, QRadialGradient,
)

BLACK  = "#08080f"
DARK   = "#10101c"
RED    = "#FF0000"
RED2   = "#CC0000"
GOLD   = "#D4AF37"
MUTED  = "rgba(255,255,255,0.6)"
DIM    = "rgba(255,255,255,0.35)"


def _font(size: int, weight: int = 400) -> QFont:
    f = QFont("Segoe UI", size)
    f.setWeight(QFont.Weight(weight))
    return f


class _PulseDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(8, 8)
        self._alpha = 255
        self._growing = False
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(25)

    def _tick(self):
        self._alpha += -5 if not self._growing else 5
        if self._alpha <= 50:  self._growing = True
        if self._alpha >= 255: self._growing = False
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        c = QColor(RED)
        c.setAlpha(self._alpha)
        p.setBrush(c)
        p.drawEllipse(1, 1, 6, 6)


class _HeaderWidget(QWidget):
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        g = QLinearGradient(0, 0, w, h)
        g.setColorAt(0, QColor(50, 5, 5))
        g.setColorAt(0.6, QColor(20, 5, 5))
        g.setColorAt(1, QColor(8, 8, 15))
        p.fillRect(self.rect(), QBrush(g))
        rg = QRadialGradient(w * 0.2, 0, w * 0.7)
        rg.setColorAt(0, QColor(255, 0, 0, 45))
        rg.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), QBrush(rg))
        pen = QPen(QColor(255, 0, 0, 10))
        pen.setWidthF(0.5)
        p.setPen(pen)
        for x in range(0, w, 32):
            p.drawLine(x, 0, x, h)
        for y in range(0, h, 32):
            p.drawLine(0, y, w, y)


class _GoldLine(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)

    def paintEvent(self, _):
        p = QPainter(self)
        g = QLinearGradient(0, 0, self.width(), 0)
        g.setColorAt(0,   QColor(255, 0, 0, 160))
        g.setColorAt(0.4, QColor(212, 175, 55, 50))
        g.setColorAt(1,   QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), QBrush(g))


class YouTubeConnectDialog(QDialog):
    """
    Retourne accepted si l'utilisateur valide un @handle.
    Accéder au handle saisi via .handle_value après exec().
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GamePill — Connexion YouTube")
        self.setFixedSize(460, 440)
        self.setModal(True)
        self.setStyleSheet(f"QDialog {{ background: {BLACK}; }} QLabel {{ background: transparent; }}")
        self.handle_value = ""
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────
        header = _HeaderWidget()
        header.setFixedHeight(140)
        hl = QVBoxLayout(header)
        hl.setContentsMargins(30, 22, 30, 22)
        hl.setSpacing(10)

        badge_row = QHBoxLayout()
        badge_row.setSpacing(10)

        dot = _PulseDot()
        badge_row.addWidget(dot, 0, Qt.AlignmentFlag.AlignVCenter)
        live_lbl = QLabel("LIVE")
        live_lbl.setFont(_font(8, 700))
        live_lbl.setStyleSheet(f"color: {RED}; letter-spacing: 2px;")
        badge_row.addWidget(live_lbl)
        badge_row.addSpacing(10)

        yt_badge = QLabel("  YOUTUBE  ")
        yt_badge.setFont(_font(8, 700))
        yt_badge.setStyleSheet(f"color: white; background: {RED}; border-radius: 5px; padding: 4px 6px; letter-spacing: 1px;")
        badge_row.addWidget(yt_badge)
        badge_row.addStretch()
        hl.addLayout(badge_row)

        title = QLabel("Connecte ta chaîne YouTube")
        title.setFont(_font(19, 700))
        title.setStyleSheet("color: white;")
        hl.addWidget(title)

        sub = QLabel("Sans compte Google — juste ton @handle.")
        sub.setFont(_font(10))
        sub.setStyleSheet(f"color: {MUTED};")
        hl.addWidget(sub)

        root.addWidget(header)
        root.addWidget(_GoldLine())

        # ── Corps ─────────────────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet(f"background: {DARK};")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(30, 28, 30, 30)
        bl.setSpacing(0)

        lbl = QLabel("TON HANDLE YOUTUBE")
        lbl.setFont(_font(8, 700))
        lbl.setStyleSheet(f"color: {GOLD}; letter-spacing: 3px;")
        bl.addWidget(lbl)
        bl.addSpacing(12)

        # Input handle
        self._input = QLineEdit()
        self._input.setPlaceholderText("@sm0ke  ou  sm0ke")
        self._input.setFont(_font(13))
        self._input.setFixedHeight(48)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(255,255,255,0.05);
                color: white;
                border: 1px solid rgba(255,0,0,0.3);
                border-radius: 12px;
                padding: 0 16px;
                selection-background-color: rgba(255,0,0,0.3);
            }}
            QLineEdit:focus {{
                border-color: rgba(255,0,0,0.65);
                background: rgba(255,255,255,0.07);
            }}
        """)
        bl.addWidget(self._input)
        bl.addSpacing(10)

        # Message d'erreur (caché par défaut)
        self._err = QLabel("")
        self._err.setFont(_font(9))
        self._err.setStyleSheet("color: #ff5555;")
        self._err.setVisible(False)
        bl.addWidget(self._err)

        bl.addSpacing(14)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,0,0,0.1); border: none;")
        bl.addWidget(sep)
        bl.addSpacing(14)

        hint = QLabel("🔑  Nécessite YOUTUBE_API_KEY dans constants.py\n"
                       "🔒  Lecture seule sur données publiques · Aucun login")
        hint.setFont(_font(9))
        hint.setStyleSheet(f"color: {DIM}; line-height: 1.6;")
        bl.addWidget(hint)

        bl.addStretch()
        bl.addSpacing(20)

        # ── Boutons ───────────────────────────────────────────────────
        btns = QHBoxLayout()
        btns.setSpacing(12)

        cancel = QPushButton("Annuler")
        cancel.setFixedHeight(48)
        cancel.setFont(_font(10))
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.05);
                color: {MUTED};
                border-radius: 24px;
                border: 1px solid rgba(255,255,255,0.1);
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.09); color: white; }}
            QPushButton:pressed {{ background: rgba(255,255,255,0.03); }}
        """)
        cancel.clicked.connect(self.reject)

        confirm = QPushButton("Connecter  →")
        confirm.setFixedHeight(48)
        confirm.setFont(_font(11, 700))
        confirm.setDefault(True)
        confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {RED}, stop:1 {RED2});
                color: white;
                border-radius: 24px;
                border: 1px solid rgba(212,175,55,0.25);
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #ff5555, stop:1 {RED});
            }}
            QPushButton:pressed {{ background: {RED2}; }}
        """)
        confirm.clicked.connect(self._on_confirm)

        btns.addWidget(cancel, 1)
        btns.addWidget(confirm, 2)
        bl.addLayout(btns)

        root.addWidget(body, 1)

        self._input.returnPressed.connect(self._on_confirm)

    def _on_confirm(self):
        handle = self._input.text().strip().lstrip("@")
        if not handle:
            self._err.setText("Entre ton handle YouTube (ex: @sm0ke)")
            self._err.setVisible(True)
            return
        self.handle_value = handle
        self.accept()

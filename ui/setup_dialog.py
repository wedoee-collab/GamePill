"""
Dialog de connexion Twitch — noir / violet / or, cohérent avec le site GamePill.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QWidget,
)
from PyQt6.QtCore import Qt, QRectF, QTimer
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPainterPath, QLinearGradient,
    QBrush, QPen,
)


PURPLE      = "#9146FF"
PURPLE_DARK = "#7B2FBE"
GOLD        = "#D4AF37"
BLACK       = "#16162a"
CARD        = "#1e1e32"
RED_LIVE    = "#ff3b30"


def _sf(size: int, bold: bool = False) -> QFont:
    f = QFont("Segoe UI", size)
    if bold:
        f.setWeight(QFont.Weight.Bold)
    return f


class _AnimDot(QWidget):
    """Petit point rouge qui pulse comme dans la pill."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(8, 8)
        self._alpha = 255
        self._growing = False
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(30)

    def _tick(self):
        self._alpha += -6 if not self._growing else 6
        if self._alpha <= 60:  self._growing = True
        if self._alpha >= 255: self._growing = False
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        c = QColor(RED_LIVE)
        c.setAlpha(self._alpha)
        p.setBrush(c)
        p.drawEllipse(0, 0, 8, 8)


class _GoldSep(QFrame):
    """Séparateur fin dégradé or → transparent."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)

    def paintEvent(self, _):
        p = QPainter(self)
        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(0,   QColor(212, 175, 55, 200))
        grad.setColorAt(0.5, QColor(145,  70, 255, 80))
        grad.setColorAt(1,   QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), QBrush(grad))


class TwitchConnectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GamePill — Connexion Twitch")
        self.setFixedSize(440, 500)
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog {{
                background: {BLACK};
            }}
            QLabel {{ background: transparent; }}
        """)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header dégradé ───────────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(130)
        header.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #2d1060, stop:0.6 #1e0a40, stop:1 {BLACK});
        """)

        hl = QVBoxLayout(header)
        hl.setContentsMargins(28, 20, 28, 18)
        hl.setSpacing(8)

        # LIVE badge row
        badge_row = QHBoxLayout()
        badge_row.setSpacing(8)

        dot = _AnimDot()
        badge_row.addWidget(dot, 0, Qt.AlignmentFlag.AlignVCenter)

        live_lbl = QLabel("LIVE")
        live_lbl.setFont(_sf(8, bold=True))
        live_lbl.setStyleSheet(f"color: {RED_LIVE}; letter-spacing: 2px;")
        badge_row.addWidget(live_lbl)

        badge_row.addSpacing(12)

        twitch_badge = QLabel("  TWITCH  ")
        twitch_badge.setFont(_sf(8, bold=True))
        twitch_badge.setStyleSheet(f"""
            color: white;
            background: {PURPLE};
            border-radius: 4px;
            padding: 3px 4px;
            letter-spacing: 1px;
        """)
        badge_row.addWidget(twitch_badge)
        badge_row.addStretch()

        hl.addLayout(badge_row)

        title = QLabel("Connexion à ton compte")
        title.setFont(_sf(18, bold=True))
        title.setStyleSheet("color: white;")
        hl.addWidget(title)

        sub = QLabel("GamePill accède à tes stats en lecture seule.")
        sub.setFont(_sf(10))
        sub.setStyleSheet("color: rgba(255,255,255,0.7);")
        hl.addWidget(sub)

        layout.addWidget(header)

        # Séparateur or
        layout.addWidget(_GoldSep())

        # ── Corps ─────────────────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet(f"background: {CARD};")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(28, 24, 28, 28)
        bl.setSpacing(0)

        # Titre section
        acc_title = QLabel("ACCÈS DEMANDÉS")
        acc_title.setFont(_sf(8, bold=True))
        acc_title.setStyleSheet(f"color: {GOLD}; letter-spacing: 3px;")
        bl.addWidget(acc_title)
        bl.addSpacing(16)

        # Permissions
        perms = [
            ("👁",  "Nombre de viewers en direct"),
            ("🔔",  "Nouveaux follows et abonnés"),
            ("⚡",  "Pseudo récupéré automatiquement"),
        ]
        for icon, text in perms:
            row = QHBoxLayout()
            row.setSpacing(12)
            row.setContentsMargins(0, 0, 0, 0)

            ic = QLabel(icon)
            ic.setFont(_sf(15))
            ic.setFixedWidth(28)
            ic.setAlignment(Qt.AlignmentFlag.AlignCenter)

            tx = QLabel(text)
            tx.setFont(_sf(10))
            tx.setStyleSheet("color: rgba(255,255,255,0.88);")

            row.addWidget(ic)
            row.addWidget(tx)
            row.addStretch()
            bl.addLayout(row)
            bl.addSpacing(12)

        bl.addSpacing(8)

        # Séparateur fin
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("background: rgba(255,255,255,0.08); border: none;")
        sep2.setFixedHeight(1)
        bl.addWidget(sep2)
        bl.addSpacing(16)

        # Vie privée
        priv = QLabel("🔒  Données 100% locales · Aucun serveur externe")
        priv.setFont(_sf(9))
        priv.setStyleSheet("color: rgba(255,255,255,0.5);")
        bl.addWidget(priv)

        bl.addStretch()
        bl.addSpacing(24)

        # ── Boutons ───────────────────────────────────────────────────
        btns = QHBoxLayout()
        btns.setSpacing(12)

        cancel = QPushButton("Annuler")
        cancel.setFixedHeight(46)
        cancel.setFont(_sf(10))
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.06);
                color: rgba(255,255,255,0.5);
                border-radius: 23px;
                border: 1px solid rgba(255,255,255,0.1);
                padding: 0 20px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.1); color: white; }
            QPushButton:pressed { background: rgba(255,255,255,0.04); }
        """)
        cancel.clicked.connect(self.reject)

        connect = QPushButton("  Connecter avec Twitch  →")
        connect.setFixedHeight(46)
        connect.setFont(_sf(11, bold=True))
        connect.setDefault(True)
        connect.setCursor(Qt.CursorShape.PointingHandCursor)
        connect.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {PURPLE}, stop:1 {PURPLE_DARK});
                color: white;
                border-radius: 23px;
                border: 1px solid rgba(212,175,55,0.25);
                padding: 0 24px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #a855ff, stop:1 {PURPLE});
                border-color: rgba(212,175,55,0.5);
            }}
            QPushButton:pressed {{
                background: {PURPLE_DARK};
            }}
        """)
        connect.clicked.connect(self.accept)

        btns.addWidget(cancel, 1)
        btns.addWidget(connect, 2)
        bl.addLayout(btns)

        layout.addWidget(body, 1)

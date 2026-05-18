"""
Dialog de connexion Kick — saisie du slug, branding vert Kick.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QWidget, QFrame,
)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QLinearGradient, QBrush, QPen, QRadialGradient,
)

BLACK = "#08080f"
DARK  = "#10101c"
GREEN = "#53FC18"
GREEN2= "#35c010"
GOLD  = "#D4AF37"
MUTED = "rgba(255,255,255,0.6)"
DIM   = "rgba(255,255,255,0.35)"


def _font(size: int, weight: int = 400) -> QFont:
    f = QFont("Segoe UI", size)
    f.setWeight(QFont.Weight(weight))
    return f


class _HeaderWidget(QWidget):
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        g = QLinearGradient(0, 0, w, h)
        g.setColorAt(0, QColor(5, 30, 5))
        g.setColorAt(0.6, QColor(5, 15, 5))
        g.setColorAt(1, QColor(8, 8, 15))
        p.fillRect(self.rect(), QBrush(g))
        rg = QRadialGradient(w * 0.2, 0, w * 0.7)
        rg.setColorAt(0, QColor(83, 252, 24, 40))
        rg.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), QBrush(rg))
        pen = QPen(QColor(83, 252, 24, 10))
        pen.setWidthF(0.5)
        p.setPen(pen)
        for x in range(0, w, 32):
            p.drawLine(x, 0, x, h)
        for y in range(0, h, 32):
            p.drawLine(0, y, w, y)


class _GreenLine(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)

    def paintEvent(self, _):
        p = QPainter(self)
        g = QLinearGradient(0, 0, self.width(), 0)
        g.setColorAt(0,   QColor(83, 252, 24, 180))
        g.setColorAt(0.4, QColor(212, 175, 55, 50))
        g.setColorAt(1,   QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), QBrush(g))


class KickConnectDialog(QDialog):
    def __init__(self, current_slug: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("GamePill — Connexion Kick")
        self.setFixedSize(460, 400)
        self.setModal(True)
        self.setStyleSheet(f"QDialog {{ background: {BLACK}; }} QLabel {{ background: transparent; }}")
        self.slug_value = ""
        self._build(current_slug)

    def _build(self, current_slug: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = _HeaderWidget()
        header.setFixedHeight(140)
        hl = QVBoxLayout(header)
        hl.setContentsMargins(30, 22, 30, 22)
        hl.setSpacing(10)

        badge_row = QHBoxLayout()
        kick_badge = QLabel("  KICK  ")
        kick_badge.setFont(_font(8, 700))
        kick_badge.setStyleSheet(f"""
            color: black;
            background: {GREEN};
            border-radius: 5px;
            padding: 4px 6px;
            letter-spacing: 1px;
        """)
        badge_row.addWidget(kick_badge)
        badge_row.addStretch()
        hl.addLayout(badge_row)

        title = QLabel("Connecte ta chaîne Kick")
        title.setFont(_font(19, 700))
        title.setStyleSheet("color: white;")
        hl.addWidget(title)

        sub = QLabel("Sans connexion requise — juste ton slug de chaîne.")
        sub.setFont(_font(10))
        sub.setStyleSheet(f"color: {MUTED};")
        hl.addWidget(sub)

        root.addWidget(header)
        root.addWidget(_GreenLine())

        # Body
        body = QWidget()
        body.setStyleSheet(f"background: {DARK};")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(30, 28, 30, 30)
        bl.setSpacing(0)

        lbl = QLabel("TON SLUG KICK")
        lbl.setFont(_font(8, 700))
        lbl.setStyleSheet(f"color: {GOLD}; letter-spacing: 3px;")
        bl.addWidget(lbl)
        bl.addSpacing(12)

        self._input = QLineEdit(current_slug)
        self._input.setPlaceholderText("sm0ke")
        self._input.setFont(_font(13))
        self._input.setFixedHeight(48)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(255,255,255,0.05);
                color: white;
                border: 1px solid rgba(83,252,24,0.3);
                border-radius: 12px;
                padding: 0 16px;
            }}
            QLineEdit:focus {{
                border-color: rgba(83,252,24,0.65);
                background: rgba(255,255,255,0.07);
            }}
        """)
        bl.addWidget(self._input)
        bl.addSpacing(8)

        hint_url = QLabel("kick.com/<b>sm0ke</b>  →  entre  <b>sm0ke</b>")
        hint_url.setFont(_font(9))
        hint_url.setStyleSheet(f"color: {DIM};")
        bl.addWidget(hint_url)

        self._err = QLabel("")
        self._err.setFont(_font(9))
        self._err.setStyleSheet("color: #ff5555;")
        self._err.setVisible(False)
        bl.addWidget(self._err)

        bl.addSpacing(16)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: rgba(83,252,24,0.1); border: none;")
        bl.addWidget(sep)
        bl.addSpacing(14)

        note = QLabel("🔒  Données publiques · Aucun compte requis")
        note.setFont(_font(9))
        note.setStyleSheet(f"color: {DIM};")
        bl.addWidget(note)

        bl.addStretch()
        bl.addSpacing(20)

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
                    stop:0 {GREEN}, stop:1 {GREEN2});
                color: black;
                border-radius: 24px;
                border: 1px solid rgba(212,175,55,0.25);
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #7fff50, stop:1 {GREEN});
            }}
            QPushButton:pressed {{ background: {GREEN2}; }}
        """)
        confirm.clicked.connect(self._on_confirm)

        btns.addWidget(cancel, 1)
        btns.addWidget(confirm, 2)
        bl.addLayout(btns)

        root.addWidget(body, 1)
        self._input.returnPressed.connect(self._on_confirm)

    def _on_confirm(self):
        slug = self._input.text().strip().lower()
        if not slug:
            self._err.setText("Entre le slug de ta chaîne (ex: sm0ke)")
            self._err.setVisible(True)
            return
        self.slug_value = slug
        self.accept()

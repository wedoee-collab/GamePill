"""
Dialog de connexion Riot Games — style GamePill.
Collecte Riot ID (name#tag) + région, ouvre account.riotgames.com si besoin.
"""

import webbrowser

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFrame, QWidget,
)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPainterPath, QLinearGradient,
    QBrush, QPen, QRadialGradient,
)

BLACK  = "#08080f"
DARK   = "#10101c"
GOLD   = "#C89B3C"
GOLD2  = "#F0D060"
RED_R  = "#D13639"   # Riot red
MUTED  = "rgba(255,255,255,0.6)"
DIM    = "rgba(255,255,255,0.35)"
PURPLE = "#9146FF"

REGIONS = ["EUW", "EUNE", "NA", "KR", "BR", "TR", "RU", "JP", "OCE"]


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
        g.setColorAt(0, QColor(60, 10, 10))
        g.setColorAt(0.6, QColor(30, 8, 8))
        g.setColorAt(1, QColor(8, 8, 15))
        p.fillRect(self.rect(), QBrush(g))

        rg = QRadialGradient(w * 0.2, 0, w * 0.7)
        rg.setColorAt(0, QColor(209, 54, 57, 50))
        rg.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), QBrush(rg))

        pen = QPen(QColor(200, 155, 60, 12))
        pen.setWidthF(0.5)
        p.setPen(pen)
        step = 32
        for x in range(0, w, step):
            p.drawLine(x, 0, x, h)
        for y in range(0, h, step):
            p.drawLine(0, y, w, y)


class _GoldLine(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)

    def paintEvent(self, _):
        p = QPainter(self)
        g = QLinearGradient(0, 0, self.width(), 0)
        g.setColorAt(0,   QColor(200, 155, 60, 220))
        g.setColorAt(0.4, QColor(209, 54, 57, 80))
        g.setColorAt(1,   QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), QBrush(g))


_INPUT_STYLE = """
QLineEdit {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(200,155,60,0.35);
    border-radius: 10px;
    color: white;
    padding: 0 14px;
    font-family: 'Segoe UI';
    font-size: 11pt;
}
QLineEdit:focus {
    border-color: rgba(200,155,60,0.75);
    background: rgba(255,255,255,0.09);
}
QLineEdit::placeholder {
    color: rgba(255,255,255,0.3);
}
"""

_COMBO_STYLE = """
QComboBox {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(200,155,60,0.35);
    border-radius: 10px;
    color: white;
    padding: 0 14px;
    font-family: 'Segoe UI';
    font-size: 11pt;
}
QComboBox:focus { border-color: rgba(200,155,60,0.75); }
QComboBox::drop-down { border: none; width: 30px; }
QComboBox::down-arrow {
    width: 10px; height: 10px;
    border-right: 2px solid rgba(200,155,60,0.7);
    border-bottom: 2px solid rgba(200,155,60,0.7);
    margin-right: 10px;
    transform: rotate(45deg);
}
QComboBox QAbstractItemView {
    background: #1a1020;
    color: white;
    border: 1px solid rgba(200,155,60,0.4);
    selection-background-color: rgba(200,155,60,0.25);
}
"""


class RiotDialog(QDialog):
    def __init__(self, game_name: str = "", tag_line: str = "",
                 region: str = "EUW", parent=None):
        super().__init__(parent)
        self.setWindowTitle("GamePill — Connexion Riot Games")
        self.setFixedSize(460, 520)
        self.setModal(True)
        self.setStyleSheet(f"QDialog {{ background: {BLACK}; }} QLabel {{ background: transparent; }}")
        self._build(game_name, tag_line, region)

    # ── Public ────────────────────────────────────────────────────────

    @property
    def game_name(self) -> str:
        return self._name_input.text().strip()

    @property
    def tag_line(self) -> str:
        return self._tag_input.text().strip().lstrip("#")

    @property
    def region(self) -> str:
        return self._region_combo.currentText()

    # ── Build UI ──────────────────────────────────────────────────────

    def _build(self, game_name: str, tag_line: str, region: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = _HeaderWidget()
        header.setFixedHeight(150)
        hl = QVBoxLayout(header)
        hl.setContentsMargins(30, 22, 30, 22)
        hl.setSpacing(10)

        badge_row = QHBoxLayout()
        badge_row.setSpacing(10)

        riot_badge = QLabel("  RIOT GAMES  ")
        riot_badge.setFont(_font(8, 700))
        riot_badge.setStyleSheet(f"""
            color: white;
            background: {RED_R};
            border-radius: 5px;
            padding: 4px 6px;
            letter-spacing: 1px;
        """)
        badge_row.addWidget(riot_badge)
        badge_row.addStretch()
        hl.addLayout(badge_row)

        title = QLabel("Connexion à ton compte Riot")
        title.setFont(_font(20, 700))
        title.setStyleSheet("color: white;")
        hl.addWidget(title)

        sub = QLabel("GamePill récupère tes stats en lecture seule.")
        sub.setFont(_font(10))
        sub.setStyleSheet(f"color: {MUTED};")
        hl.addWidget(sub)

        root.addWidget(header)
        root.addWidget(_GoldLine())

        # Body
        body = QWidget()
        body.setStyleSheet(f"background: {DARK};")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(30, 26, 30, 30)
        bl.setSpacing(0)

        sec = QLabel("TON RIOT ID")
        sec.setFont(_font(8, 700))
        sec.setStyleSheet(f"color: {GOLD}; letter-spacing: 3px;")
        bl.addWidget(sec)
        bl.addSpacing(12)

        # Name + tag fields
        fields_row = QHBoxLayout()
        fields_row.setSpacing(8)

        self._name_input = QLineEdit(game_name)
        self._name_input.setFixedHeight(46)
        self._name_input.setPlaceholderText("NomJoueur")
        self._name_input.setStyleSheet(_INPUT_STYLE)
        fields_row.addWidget(self._name_input, 3)

        sep_lbl = QLabel("#")
        sep_lbl.setFont(_font(16, 700))
        sep_lbl.setStyleSheet(f"color: {MUTED}; background: transparent;")
        sep_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fields_row.addWidget(sep_lbl)

        self._tag_input = QLineEdit(tag_line)
        self._tag_input.setFixedHeight(46)
        self._tag_input.setPlaceholderText("TAG")
        self._tag_input.setMaxLength(5)
        self._tag_input.setStyleSheet(_INPUT_STYLE)
        fields_row.addWidget(self._tag_input, 1)

        bl.addLayout(fields_row)
        bl.addSpacing(6)

        hint = QLabel("Ex :  sm0ke  #  EUW1")
        hint.setFont(_font(9))
        hint.setStyleSheet(f"color: {DIM};")
        bl.addWidget(hint)

        bl.addSpacing(18)

        region_lbl = QLabel("RÉGION")
        region_lbl.setFont(_font(8, 700))
        region_lbl.setStyleSheet(f"color: {GOLD}; letter-spacing: 3px;")
        bl.addWidget(region_lbl)
        bl.addSpacing(10)

        self._region_combo = QComboBox()
        self._region_combo.setFixedHeight(46)
        self._region_combo.addItems(REGIONS)
        if region in REGIONS:
            self._region_combo.setCurrentIndex(REGIONS.index(region))
        self._region_combo.setStyleSheet(_COMBO_STYLE)
        bl.addWidget(self._region_combo)

        bl.addSpacing(14)

        # "Trouver mon Riot ID" link button
        find_btn = QPushButton("Trouver mon Riot ID  ↗")
        find_btn.setFixedHeight(36)
        find_btn.setFont(_font(9))
        find_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        find_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {GOLD};
                border: 1px solid rgba(200,155,60,0.35);
                border-radius: 18px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background: rgba(200,155,60,0.1);
                border-color: rgba(200,155,60,0.6);
            }}
            QPushButton:pressed {{ background: rgba(200,155,60,0.05); }}
        """)
        find_btn.clicked.connect(lambda: webbrowser.open("https://account.riotgames.com"))
        bl.addWidget(find_btn)

        bl.addSpacing(8)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(200,155,60,0.15); border: none;")
        bl.addWidget(sep)
        bl.addSpacing(12)

        priv = QLabel("🔒  Données 100% locales · Aucun serveur externe")
        priv.setFont(_font(9))
        priv.setStyleSheet(f"color: {DIM};")
        bl.addWidget(priv)

        bl.addStretch()
        bl.addSpacing(16)

        # Buttons
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
                padding: 0 20px;
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.09);
                color: white;
                border-color: rgba(255,255,255,0.2);
            }}
            QPushButton:pressed {{ background: rgba(255,255,255,0.03); }}
        """)
        cancel.clicked.connect(self.reject)

        confirm = QPushButton("Confirmer  →")
        confirm.setFixedHeight(48)
        confirm.setFont(_font(11, 700))
        confirm.setDefault(True)
        confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {RED_R}, stop:1 #a0282a);
                color: white;
                border-radius: 24px;
                border: 1px solid rgba(200,155,60,0.3);
                padding: 0 26px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #e03d40, stop:1 {RED_R});
                border-color: rgba(200,155,60,0.55);
            }}
            QPushButton:pressed {{ background: #a0282a; }}
        """)
        confirm.clicked.connect(self._validate)

        btns.addWidget(cancel, 1)
        btns.addWidget(confirm, 2)
        bl.addLayout(btns)

        root.addWidget(body, 1)

    def _validate(self):
        name = self._name_input.text().strip()
        tag  = self._tag_input.text().strip().lstrip("#")
        if not name or not tag:
            self._name_input.setStyleSheet(
                _INPUT_STYLE + "QLineEdit { border-color: #D13639; }" if not name else _INPUT_STYLE
            )
            self._tag_input.setStyleSheet(
                _INPUT_STYLE + "QLineEdit { border-color: #D13639; }" if not tag else _INPUT_STYLE
            )
            return
        self.accept()

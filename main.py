import sys
import ctypes
import os
import threading

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PyQt6.QtGui import QPainter, QPixmap, QColor, QIcon, QFont, QAction, QPen, QPainterPath
from PyQt6.QtCore import Qt, QTimer, QRectF

from ui.pill_widget import PillWidget, PLATFORM_TWITCH, PLATFORM_NONE
from ui.setup_dialog import TwitchConnectDialog
from services.game_detector import GameDetector
from services.twitch_service import TwitchService
from core.auth import TwitchAuth
from core.config import Config
from core.themes import THEMES


def _make_tray_icon() -> QIcon:
    """Pill noire avec un point rouge LIVE — comme le widget."""
    px = QPixmap(32, 16)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Fond pill
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 1, 32, 14), 7, 7)
    p.fillPath(path, QColor(10, 10, 12, 240))
    pen = QPen(QColor(145, 70, 255, 120))
    pen.setWidthF(1.0)
    p.setPen(pen)
    p.drawPath(path)

    # Point rouge
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#ff3b30"))
    p.drawEllipse(5, 5, 6, 6)

    # "GP" en blanc
    p.setPen(QColor(255, 255, 255, 200))
    f = QFont("Segoe UI", 6, int(QFont.Weight.Bold))
    p.setFont(f)
    p.drawText(14, 12, "GP")

    p.end()
    return QIcon(px)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setFont(QFont("Segoe UI", 10))

    config   = Config()
    auth     = TwitchAuth(config)
    twitch   = TwitchService(auth, config)
    detector = GameDetector()

    pill = PillWidget(THEMES["default"])

    # ── Game detector → thème ────────────────────────────────────────
    def on_game_changed(key: str, theme):
        kda     = detector.current_kda()
        history = detector.current_history()
        pill.apply_theme(theme, kda, history)

    detector.game_changed.connect(on_game_changed)

    # ── Systray ──────────────────────────────────────────────────────
    tray = QSystemTrayIcon(_make_tray_icon(), app)
    tray.setToolTip("GamePill")
    menu = QMenu()

    # Status en haut du menu — créé en premier pour être accessible partout
    status_action = QAction("❌ Non connecté à Twitch", app)
    status_action.setEnabled(False)
    menu.addAction(status_action)
    menu.addSeparator()

    twitch_menu = menu.addMenu("Twitch")

    menu.addSeparator()
    menu.addAction("Demo alerte sub").triggered.connect(lambda: pill.trigger_alert())
    menu.addSeparator()
    menu.addAction("Quitter").triggered.connect(app.quit)

    # ── Fonction centrale de mise à jour du statut ───────────────────
    def _refresh_status():
        """Met à jour le label de statut dans le menu systray."""
        try:
            if auth.is_connected:
                name = config.get("twitch_display_name") or config.get("twitch_username") or "Twitch"
                td = twitch.data
                if td.is_live:
                    label = f"🟢 {name}  —  {td.viewers_fmt()} viewers  ({td.uptime_fmt()})"
                else:
                    label = f"⚫ {name}  —  Pas en live"
            else:
                label = "❌ Non connecté à Twitch"
            status_action.setText(label)
            tray.setToolTip(f"GamePill  |  {label}")
        except Exception as e:
            print(f"[Main] _refresh_status erreur : {e}")

    # ── Twitch live → pill ───────────────────────────────────────────
    def on_twitch_data(data):
        pill.update_live_data(data)
        pill.set_platform(PLATFORM_TWITCH)
        _refresh_status()   # met à jour viewers/uptime dans le menu

    def on_connection_lost():
        print("[Main] Connexion Twitch perdue.")
        pill.set_platform(PLATFORM_NONE)
        _refresh_status()

    twitch.data_updated.connect(on_twitch_data)
    twitch.connection_lost.connect(on_connection_lost)

    # Refresh aussi à l'ouverture du menu (fallback)
    menu.aboutToShow.connect(_refresh_status)

    # ── Actions Twitch ───────────────────────────────────────────────
    def connect_twitch():
        dlg = TwitchConnectDialog()
        if dlg.exec() != TwitchConnectDialog.DialogCode.Accepted:
            return

        def _on_success():
            name = config.get("twitch_display_name") or config.get("twitch_username") or "Twitch"
            tray.showMessage(
                "GamePill",
                f"✅ Connecté en tant que {name} !",
                QSystemTrayIcon.MessageIcon.Information, 3000
            )
            pill.set_platform(PLATFORM_TWITCH)
            twitch.start()
            _refresh_status()   # ← mise à jour immédiate du menu

        def _on_failure():
            QMessageBox.warning(
                None, "GamePill",
                "Connexion Twitch échouée.\nRéessaie dans quelques secondes."
            )
            _refresh_status()

        auth.start_oauth(on_success=_on_success, on_failure=_on_failure)
        tray.showMessage(
            "GamePill",
            "Navigateur ouvert — autorise l'accès sur Twitch.",
            QSystemTrayIcon.MessageIcon.Information, 5000
        )

    def disconnect_twitch():
        twitch.stop()
        auth.disconnect()
        pill.set_platform(PLATFORM_NONE)
        pill.reset_live_data()
        _refresh_status()   # ← mise à jour immédiate du menu
        tray.showMessage("GamePill", "Twitch déconnecté.", QSystemTrayIcon.MessageIcon.Information, 2000)

    twitch_menu.addAction("Connecter Twitch").triggered.connect(connect_twitch)
    twitch_menu.addAction("Déconnecter").triggered.connect(disconnect_twitch)

    # ── Démarrage ────────────────────────────────────────────────────
    pill.show()
    detector.start()

    # Restauration de session si tokens sauvegardés
    if auth.is_connected:
        pill.set_platform(PLATFORM_TWITCH)
        _refresh_status()   # affiche déjà "⚫ Nom — Pas en live" pendant la validation

        def _restore_session():
            valid = auth.ensure_valid()
            if valid:
                QTimer.singleShot(0, twitch.start)
                QTimer.singleShot(0, _refresh_status)
            else:
                QTimer.singleShot(0, lambda: pill.set_platform(PLATFORM_NONE))
                QTimer.singleShot(0, _refresh_status)

        threading.Thread(target=_restore_session, daemon=True).start()

    tray.setContextMenu(menu)
    tray.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

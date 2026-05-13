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
from PyQt6.QtGui import QPainter, QPixmap, QColor, QIcon, QFont
from PyQt6.QtCore import Qt

from ui.pill_widget import PillWidget, PLATFORM_TWITCH, PLATFORM_NONE
from ui.setup_dialog import TwitchConnectDialog
from services.game_detector import GameDetector
from services.twitch_service import TwitchService
from core.auth import TwitchAuth
from core.config import Config
from core.themes import THEMES


def _make_tray_icon() -> QIcon:
    px = QPixmap(16, 16)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#9146FF"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(2, 2, 12, 12)
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

    # Pill démarre en état "en attente" — aucune fausse donnée
    pill = PillWidget(THEMES["default"])

    # ── Game detector → thème ────────────────────────────────────────
    def on_game_changed(key: str, theme):
        kda     = detector.current_kda()
        history = detector.current_history()
        pill.apply_theme(theme, kda, history)

    detector.game_changed.connect(on_game_changed)

    # ── Twitch live → pill ───────────────────────────────────────────
    def on_twitch_data(data):
        pill.update_live_data(data)
        pill.set_platform(PLATFORM_TWITCH)

    def on_connection_lost():
        print("[Main] Connexion Twitch perdue.")
        pill.set_platform(PLATFORM_NONE)

    twitch.data_updated.connect(on_twitch_data)
    twitch.connection_lost.connect(on_connection_lost)

    # ── Démarrage ────────────────────────────────────────────────────
    pill.show()
    detector.start()

    # Si déjà connecté à Twitch (tokens sauvegardés), on restaure la session
    if auth.is_connected:
        pill.set_platform(PLATFORM_TWITCH)

        def _restore_session():
            """Valide + rafraîchit le token en arrière-plan, puis lance le polling."""
            from PyQt6.QtCore import QTimer
            valid = auth.ensure_valid()
            if valid:
                QTimer.singleShot(0, twitch.start)
            else:
                QTimer.singleShot(0, lambda: pill.set_platform(PLATFORM_NONE))

        threading.Thread(target=_restore_session, daemon=True).start()

    # ── Systray ──────────────────────────────────────────────────────
    tray = QSystemTrayIcon(_make_tray_icon(), app)
    tray.setToolTip("GamePill")
    menu = QMenu()

    twitch_menu = menu.addMenu("Twitch")

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

        def _on_failure():
            QMessageBox.warning(
                None, "GamePill",
                "Connexion Twitch échouée.\nRéessaie dans quelques secondes."
            )

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
        tray.showMessage("GamePill", "Twitch déconnecté.", QSystemTrayIcon.MessageIcon.Information, 2000)

    twitch_menu.addAction("Connecter Twitch").triggered.connect(connect_twitch)
    twitch_menu.addAction("Déconnecter").triggered.connect(disconnect_twitch)

    menu.addSeparator()
    menu.addAction("Demo alerte sub").triggered.connect(pill.trigger_alert)
    menu.addSeparator()
    menu.addAction("Quitter").triggered.connect(app.quit)

    # ── Status Twitch en haut du menu (mis à jour dynamiquement) ────
    from PyQt6.QtGui import QAction
    status_action = QAction("❌ Non connecté à Twitch", app)
    status_action.setEnabled(False)           # affiché en grisé = info
    menu.insertAction(twitch_menu.menuAction(), status_action)
    menu.insertSeparator(twitch_menu.menuAction())

    def _update_menu():
        if auth.is_connected:
            name = config.get("twitch_display_name") or config.get("twitch_username") or "Twitch"
            td = twitch.data
            if td.is_live:
                viewers = td.viewers_fmt()
                uptime  = td.uptime_fmt()
                label = f"🟢 {name}  —  {viewers} viewers  ({uptime})"
            else:
                label = f"⚫ {name}  —  Pas en live"
        else:
            label = "❌ Non connecté à Twitch"
        status_action.setText(label)

    menu.aboutToShow.connect(_update_menu)

    tray.setContextMenu(menu)
    tray.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

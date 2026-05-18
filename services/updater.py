"""
Auto-updater — vérifie les releases GitHub et remplace le .exe.

Au démarrage, l'app interroge l'API GitHub pour la dernière release.
Si une version plus récente existe, l'utilisateur peut la télécharger :
le nouveau .exe est récupéré à côté de l'ancien, puis un petit script
batch attend la fermeture de l'app, échange les fichiers et relance.
"""

import os
import sys
import subprocess
import tempfile
import threading

import httpx
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from core.version import APP_VERSION
import core.logger as _log_mod

log = _log_mod.get("updater")

GITHUB_REPO  = "wedoee-collab/GamePill"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
ASSET_NAME   = "GamePill.exe"

_CREATE_NO_WINDOW = 0x08000000


def _parse_version(tag: str) -> tuple:
    """'v1.2.3' → (1, 2, 3). Robuste aux suffixes non numériques."""
    parts = tag.strip().lstrip("vV").split(".")
    out = []
    for p in parts:
        num = ""
        for ch in p:
            if ch.isdigit():
                num += ch
            else:
                break
        out.append(int(num) if num else 0)
    return tuple(out) or (0,)


class Updater(QObject):
    update_available = pyqtSignal(str, str)   # (version, download_url)
    no_update        = pyqtSignal()
    check_failed     = pyqtSignal(str)        # message

    # ── Vérification ──────────────────────────────────────────────────

    def check(self):
        threading.Thread(target=self._worker_check, daemon=True).start()

    def _worker_check(self):
        try:
            r = httpx.get(RELEASES_API, timeout=10, follow_redirects=True,
                          headers={"Accept": "application/vnd.github+json"})

            # Aucune release publiée → on considère qu'on est à jour
            if r.status_code == 404:
                log.info("Updater : aucune release publiée")
                QTimer.singleShot(0, self.no_update.emit)
                return
            if r.status_code != 200:
                log.warning("Updater : HTTP %d", r.status_code)
                QTimer.singleShot(0, lambda: self.check_failed.emit(f"HTTP {r.status_code}"))
                return

            data    = r.json()
            tag     = data.get("tag_name", "")
            assets  = data.get("assets", [])

            url = ""
            for a in assets:
                if a.get("name", "").lower() == ASSET_NAME.lower():
                    url = a.get("browser_download_url", "")
                    break

            latest  = _parse_version(tag)
            current = _parse_version(APP_VERSION)

            if latest > current and url:
                log.info("Updater : version %s disponible (actuelle %s)", tag, APP_VERSION)
                QTimer.singleShot(0, lambda: self.update_available.emit(tag, url))
            else:
                log.info("Updater : à jour (%s)", APP_VERSION)
                QTimer.singleShot(0, self.no_update.emit)

        except Exception as e:
            log.error("Updater : échec de la vérification — %s", e)
            QTimer.singleShot(0, lambda: self.check_failed.emit(str(e)))

    # ── Téléchargement + remplacement ─────────────────────────────────

    def download_and_apply(self, url: str, on_done=None, on_error=None):
        threading.Thread(
            target=self._worker_download,
            args=(url, on_done, on_error),
            daemon=True,
        ).start()

    def _worker_download(self, url, on_done, on_error):
        def _fail(msg):
            log.error("Updater : %s", msg)
            QTimer.singleShot(0, lambda: on_error(msg) if on_error else None)

        # En mode développement (python main.py) il n'y a pas de .exe
        if not getattr(sys, "frozen", False):
            _fail("Mode développement — l'auto-update ne s'applique qu'au .exe")
            return

        current_exe = sys.executable
        new_exe     = current_exe + ".new"

        try:
            with httpx.stream("GET", url, timeout=120, follow_redirects=True) as resp:
                resp.raise_for_status()
                with open(new_exe, "wb") as f:
                    for chunk in resp.iter_bytes(65536):
                        f.write(chunk)
        except Exception as e:
            _fail(f"Téléchargement échoué : {e}")
            return

        if os.path.getsize(new_exe) < 100_000:
            _fail("Fichier téléchargé invalide (trop petit)")
            try:
                os.remove(new_exe)
            except OSError:
                pass
            return

        try:
            self._spawn_swap(current_exe, new_exe)
        except Exception as e:
            _fail(f"Impossible de lancer le script de mise à jour : {e}")
            return

        log.info("Updater : nouvelle version prête, redémarrage…")
        QTimer.singleShot(0, lambda: on_done() if on_done else None)

    def _spawn_swap(self, current_exe: str, new_exe: str):
        """Script batch : attend la fermeture, échange les .exe, relance."""
        bat = os.path.join(tempfile.gettempdir(), "gamepill_update.bat")
        script = (
            "@echo off\r\n"
            "timeout /t 2 /nobreak >nul\r\n"
            ":wait\r\n"
            f'del "{current_exe}" >nul 2>&1\r\n'
            f'if exist "{current_exe}" (timeout /t 1 /nobreak >nul & goto wait)\r\n'
            f'move /y "{new_exe}" "{current_exe}" >nul\r\n'
            f'start "" "{current_exe}"\r\n'
            'del "%~f0" >nul 2>&1\r\n'
        )
        with open(bat, "w", encoding="utf-8") as f:
            f.write(script)
        subprocess.Popen(["cmd", "/c", bat], creationflags=_CREATE_NO_WINDOW)

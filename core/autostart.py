r"""
Gestion du démarrage automatique avec Windows via le registre.
Clé : HKCU\Software\Microsoft\Windows\CurrentVersion\Run
"""

import os
import sys
import winreg

import core.logger as _log_mod

log = _log_mod.get("autostart")

APP_NAME = "GamePill"


def _app_command() -> str:
    """Commande a enregistrer. Le drapeau --autostart signale a GamePill
    qu'il est lance par Windows (pour ne pas afficher l'ecran de bienvenue)."""
    if getattr(sys, "frozen", False):
        # Mode package PyInstaller : sys.executable est le .exe
        return f'"{sys.executable}" --autostart'
    else:
        # Mode dev : python.exe + chemin absolu de main.py
        main_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "main.py")
        )
        return f'"{sys.executable}" "{main_path}" --autostart'


def _open_run_key(write: bool = False):
    access = winreg.KEY_READ | (winreg.KEY_SET_VALUE if write else 0)
    return winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0, access,
    )


def is_enabled() -> bool:
    try:
        with _open_run_key() as key:
            winreg.QueryValueEx(key, APP_NAME)
        return True
    except (FileNotFoundError, OSError):
        return False


def enable():
    try:
        with _open_run_key(write=True) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _app_command())
        log.info("Autostart activé → %s", _app_command())
    except Exception as e:
        log.error("Impossible d'activer l'autostart : %s", e)


def disable():
    try:
        with _open_run_key(write=True) as key:
            winreg.DeleteValue(key, APP_NAME)
        log.info("Autostart désactivé")
    except FileNotFoundError:
        pass
    except Exception as e:
        log.error("Impossible de désactiver l'autostart : %s", e)


def toggle() -> bool:
    """Active ou désactive selon l'état actuel. Retourne le nouvel état."""
    if is_enabled():
        disable()
        return False
    else:
        enable()
        return True


def sync():
    """Réaligne la commande enregistrée sur la commande actuelle.
    Sert à intégrer le drapeau --autostart aux entrées créées avant."""
    if not is_enabled():
        return
    try:
        with _open_run_key() as key:
            current, _ = winreg.QueryValueEx(key, APP_NAME)
        if current != _app_command():
            enable()
    except Exception as e:
        log.warning("Autostart sync échoué : %s", e)

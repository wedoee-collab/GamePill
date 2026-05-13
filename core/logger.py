"""Logging centralisé — fichier tournant dans %APPDATA%/GamePill/."""

import logging
import os
from logging.handlers import RotatingFileHandler

_LOG_DIR  = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "GamePill")
_LOG_FILE = os.path.join(_LOG_DIR, "gamepill.log")

_initialized = False


def setup() -> logging.Logger:
    global _initialized
    if _initialized:
        return logging.getLogger("gamepill")

    os.makedirs(_LOG_DIR, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)-20s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    fh = RotatingFileHandler(_LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3,
                             encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    _initialized = True
    log = logging.getLogger("gamepill")
    log.info("=== GamePill démarré ===  log : %s", _LOG_FILE)
    return log


def get(name: str) -> logging.Logger:
    return logging.getLogger(name)

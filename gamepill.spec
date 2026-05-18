# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — GamePill
# Usage : pyinstaller gamepill.spec

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[str(Path(".").resolve())],
    binaries=[],
    datas=[
        ("assets/gamepill.ico", "assets"),
    ],
    hiddenimports=[
        # PyQt6 plugins
        "PyQt6.QtWidgets",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtNetwork",
        "PyQt6.sip",
        # Services
        "services.twitch_service",
        "services.twitch_eventsub",
        "services.youtube_service",
        "services.kick_service",
        "services.riot_service",
        "services.cs2_service",
        "services.steam_service",
        "services.game_detector",
        "services.updater",
        # Core
        "core.auth",
        "core.steam_auth",
        "core.config",
        "core.constants",
        "core.themes",
        "core.autostart",
        "core.logger",
        "core.version",
        # UI
        "ui.pill_widget",
        "ui.expanded_widget",
        "ui.setup_dialog",
        "ui.youtube_dialog",
        "ui.riot_dialog",
        "ui.kick_dialog",
        "ui.settings_window",
        "ui.onboarding",
        # Deps
        "httpx",
        "truststore",
        "websocket",
        "websocket._exceptions",
        "psutil",
        "cryptography",
        "cryptography.fernet",
        "cryptography.hazmat.primitives.kdf.pbkdf2",
        "cryptography.hazmat.backends.openssl",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # http.server / email / html sont requis par auth, steam_auth,
        # cs2_service et httpx — ne PAS les exclure.
        "tkinter",
        "unittest",
        "xmlrpc",
        "pydoc",
        "doctest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="GamePill",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # pas de fenêtre console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/gamepill.ico",
    version_file=None,
)

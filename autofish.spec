# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['autofish.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resume_game.png', '.'),
        ('ok_button.png', '.'),
        ('set_hook.png', '.')
    ],
    hiddenimports=[
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'keyboard',
        'cv2',
        'numpy',
        'pyautogui',
        'pygetwindow',
        'pytesseract'  # If you used pytesseract before switching
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='autofish',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to True if you want to see console output
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='autofish',
)

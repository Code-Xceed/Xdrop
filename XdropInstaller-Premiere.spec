# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['src/tools/installer_premiere.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/desktop-service/xdrop', 'xdrop'),
        ('src/resolve-plugin/dist', 'dist'),
        ('src/premiere-plugin', 'premiere-plugin'),
        ('src/assets', 'src/assets'),
        ('src/tools/assets', 'src/tools/assets'),
    ],
    hiddenimports=['tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.filedialog', 'PIL', 'PIL.Image', 'PIL.ImageTk'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='XdropInstaller-Premiere',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['src/assets/logo.ico'],
)

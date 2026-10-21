# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['src/tools/installer_resolve.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/desktop-service/xdrop', 'xdrop'),
        ('src/resolve-plugin/dist', 'dist'),
        ('src/resolve-plugin/Xdrop.lua', 'resolve-plugin'),
        ('src/resolve-plugin/Xdrop - Starter Bin.drb', 'resolve-plugin'),
        ('src/resolve-plugin/XdropLogo.png', 'resolve-plugin'),
        ('src/resolve-workflow-integration', 'resolve-workflow-integration'),
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
    name='XdropInstaller-Resolve',
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

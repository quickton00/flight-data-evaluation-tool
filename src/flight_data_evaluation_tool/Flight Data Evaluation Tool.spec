# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all numpy, scipy, and sklearn submodules
numpy_hiddenimports = collect_submodules('numpy')
scipy_hiddenimports = collect_submodules('scipy')
sklearn_hiddenimports = collect_submodules('sklearn')

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('icon.ico', '.'),
        ('results_template.json', '.'),
        ('database/*.json', 'database'),
        ('globals.py', '.'),
        ('plot.py', '.'),
        ('evaluation.py', '.'),
        ('datastructuring.py', '.'),
        ('grading.py', '.'),
        ('gui/*.py', 'gui'),
        ] + collect_data_files('numpy') + collect_data_files('scipy') + collect_data_files('sklearn'),
    hiddenimports=[
        "CTkTable",
        "sklearn.preprocessing",
        "sklearn.utils._typedefs",
        "sklearn.utils._heap",
        "sklearn.utils._sorting",
        "sklearn.utils._vector_sentinel",
        "sklearn.neighbors._partition_nodes",
        "sklearn.externals.array_api_compat.numpy",
        "sklearn.externals.array_api_compat.numpy.fft",
        "crispyn",
        "scipy._lib.messagestream",
        "scipy._cyutility",
        "scipy.signal",
        "scipy.signal.windows",
        "scipy.linalg",
        "scipy.linalg._cythonized_array_utils",
        ] + numpy_hiddenimports + scipy_hiddenimports + sklearn_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy.distutils', 'numpy.f2py'],
    noarchive=False,
    optimize=0,
)

# Remove duplicate entries
a.datas = list({tuple(d) for d in a.datas})
a.binaries = list({tuple(b) for b in a.binaries})

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Flight Data Evaluation Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)

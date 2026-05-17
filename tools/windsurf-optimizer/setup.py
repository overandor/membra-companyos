"""
setup.py for py2app — bundles WindsurfOptimizer.py into a native .app
Usage:
    python3 setup.py py2app
"""
from setuptools import setup

APP = ["WindsurfOptimizer.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "Windsurf Optimizer",
        "CFBundleShortVersionString": "2.0.0",
        "CFBundleVersion": "2.0.0",
        "CFBundleIdentifier": "com.membra.windsurf-optimizer",
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
        "LSBackgroundOnly": False,
    },
    "packages": ["rumps", "psutil", "AppKit", "Foundation"],
    "includes": ["subprocess", "time", "shutil", "platform", "pathlib", "gc", "json", "requests"],
    "strip": True,
    "optimize": 2,
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)

#!/bin/bash
set -e
set -o pipefail

cd "$(dirname "$0")"

echo "========================================"
echo " Windsurf Optimizer — Build & DMG"
echo "========================================"

# 1. Ensure venv exists and is activated
if [ ! -d "venv" ]; then
    echo "[*] Creating Python virtual environment…"
    python3 -m venv venv
fi

source venv/bin/activate

# 2. Install / upgrade deps
echo "[*] Installing dependencies…"
pip install --upgrade pip
pip install -r requirements.txt

# 3. Clean previous build artifacts
echo "[*] Cleaning old build artifacts…"
rm -rf build dist WindsurfOptimizer.spec

# 4. Build .app with py2app
echo "[*] Building macOS .app bundle with py2app…"
python3 setup.py py2app

# 5. Verify bundle exists
APP_PATH="dist/Windsurf Optimizer.app"
if [ ! -d "$APP_PATH" ]; then
    echo "[✗] Build failed — app bundle not found at $APP_PATH"
    exit 1
fi

echo "[✓] App bundle created: $APP_PATH"

# 6. Create DMG
echo "[*] Creating DMG installer…"
DMG_NAME="Windsurf-Optimizer-2.0.0.dmg"
VOLUME_NAME="Windsurf Optimizer Installer"
MOUNT_DIR="/Volumes/$VOLUME_NAME"

# Remove old DMG if it exists
rm -f "$DMG_NAME"

# Build via a temp staging folder so we control layout
STAGE="$(mktemp -d)"
cp -a "$APP_PATH" "$STAGE/"
ln -sf /Applications "$STAGE/Applications"

# Create compressed DMG directly from staging folder
hdiutil create -srcfolder "$STAGE" -volname "$VOLUME_NAME" -fs HFS+ \
    -format UDZO -imagekey zlib-level=9 -o "$DMG_NAME"

rm -rf "$STAGE"

# Optional: set DMG layout via AppleScript (open, arrange, close)
# We skip Finder layout automation to keep the build headless and reliable

echo "========================================"
echo "[✓] DMG ready: $(pwd)/$DMG_NAME"
echo "========================================"

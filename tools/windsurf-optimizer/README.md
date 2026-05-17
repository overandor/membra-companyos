# Windsurf Optimizer

A lightweight **macOS menu bar utility** that decompresses RAM, CPU, and GPU pressure, and keeps the Windsurf IDE running at peak performance. Press the disk icon in your menu bar and the system gets looser, faster, refreshed.

## What It Does

| Feature | Action |
|---|---|
| **Decompress RAM** | Runs `purge`, flushes DNS caches, clears stale user caches, triggers GC |
| **Decompress CPU** | Renices Windsurf processes to higher priority, kills stale heavy helpers, disables App Nap |
| **Decompress GPU** | Flushes QuickLook + CoreAnimation + font caches; relieves unified-memory pressure |
| **Optimize Windsurf** | Clears WS `Cache`, `GPUCache`, `CachedData`, extension caches; boosts process priority |
| **Full Optimize** | Runs all four optimizations in one shot |
| **Auto-Optimize** | Optional 5-minute timer that refreshes the system automatically |

## Quick Start

### Option A — Run from source (developer mode)

```bash
cd tools/windsurf-optimizer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 WindsurfOptimizer.py
```

The disk icon 💿 appears in your menu bar.

### Option B — Build native .app + DMG (end-user installer)

```bash
cd tools/windsurf-optimizer
chmod +x build_dmg.sh
./build_dmg.sh
```

When the script finishes you will have:
- `dist/Windsurf Optimizer.app` — the raw app bundle
- `Windsurf-Optimizer-1.0.0.dmg` — a drag-and-drop installer DMG

Double-click the DMG, drag **Windsurf Optimizer** into **Applications**, and launch it from Launchpad or Finder.

## Menu Bar Controls

- **Click the disk icon** to open the menu
- **Refresh Stats** — updates RAM / CPU / GPU pressure readings
- **Auto-Optimize Every 5m** — toggles background automatic refresh
- **Full System Optimize** — one-click total system relief

## Architecture

- `WindsurfOptimizer.py` — main `rumps` app (menu bar UI + optimization logic)
- `setup.py` — `py2app` configuration (bundles Python into a native `.app`)
- `build_dmg.sh` — one-shot build script (venv → deps → py2app → DMG)

## Notes

- Some optimizations use `sudo` internally via AppleScript; macOS will prompt for your admin password the first time.
- The app is a **LSUIElement** (menu-bar-only) — it does not appear in the Dock.
- GPU decompression on Apple Silicon / Intel macOS works through unified-memory pressure relief; discrete GPU support is limited by macOS sandboxing.

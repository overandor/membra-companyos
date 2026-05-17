#!/usr/bin/env python3
"""Windsurf Optimizer — macOS menu-bar app. PyObjC NSPanel, no tkinter."""
import gc, json, os, shutil, subprocess, sys, threading, time
from pathlib import Path
import psutil, rumps, requests
from AppKit import (NSButton, NSTextView, NSScrollView, NSColor, NSFont,
    NSMakeRect, NSMakeSize, NSVisualEffectView, NSFloatingWindowLevel,
    NSBackingStoreBuffered, NSBezelStyleRounded, NSTitledWindowMask,
    NSClosableWindowMask, NSResizableWindowMask, NSTextField, NSPanel,
    NSFullSizeContentViewWindowMask, NSWindowTitleHidden,
    NSVisualEffectBlendingModeBehindWindow, NSVisualEffectMaterialDark,
    NSVisualEffectStateActive, NSRoundedBezelStyle, NSTextAlignmentCenter,
    NSApplication, NSView, NSShadow)
from Foundation import NSMakeRange

APP_NAME = "Windsurf Optimizer"
ICON_DISK = "\U0001f4bf"
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
WINDSURF_NAMES = {"Windsurf", "windsurf", "Code Helper",
                  "Code-Helper", "Electron", "windsurf Helper"}
CARD_COLOR = NSColor.colorWithRed_green_blue_alpha_(0.10, 0.10, 0.18, 0.90)
TEXT_COLOR = NSColor.colorWithRed_green_blue_alpha_(0.88, 0.90, 0.93, 1.0)
DIM_COLOR = NSColor.colorWithRed_green_blue_alpha_(0.53, 0.57, 0.69, 1.0)
GREEN_COLOR = NSColor.colorWithRed_green_blue_alpha_(0.20, 0.84, 0.40, 1.0)
RED_COLOR = NSColor.colorWithRed_green_blue_alpha_(0.94, 0.27, 0.35, 1.0)
GLASS_BG = NSColor.colorWithRed_green_blue_alpha_(0.08, 0.08, 0.16, 0.55)
GLASS_BORDER = NSColor.colorWithWhite_alpha_(1.0, 0.06)
GLASS_HIGHLIGHT = NSColor.colorWithWhite_alpha_(1.0, 0.04)
GLASS_SHADOW = NSColor.colorWithWhite_alpha_(0.0, 0.4)
CARD_RAISED = NSColor.colorWithRed_green_blue_alpha_(0.10, 0.10, 0.20, 0.65)
CARD_PRESSED = NSColor.colorWithRed_green_blue_alpha_(0.05, 0.05, 0.12, 0.75)


def _run(cmd, sudo=False, timeout=30):
    try:
        if sudo:
            cmd = f"osascript -e 'do shell script \"{cmd}\" with administrator privileges'"
        r = subprocess.run(cmd, shell=True, capture_output=True,
                          text=True, timeout=timeout)
        return r.returncode == 0, r.stdout.strip()
    except Exception as e:
        return False, str(e)


def _sysctl(name):
    try:
        return subprocess.run(["sysctl", "-n", name],
                             capture_output=True, text=True, timeout=2).stdout.strip()
    except Exception:
        return ""


class SystemInfo:
    @staticmethod
    def ram():
        vm = psutil.virtual_memory()
        return {"pct": vm.percent, "used": round(vm.used/1024**3, 1),
                "total": round(vm.total/1024**3, 1)}

    @staticmethod
    def cpu():
        return {"pct": psutil.cpu_percent(interval=0.2),
                "cores": psutil.cpu_count(logical=True)}

    @staticmethod
    def gpu():
        try:
            r = subprocess.run(
                ["ioreg", "-c", "IOAccelerator", "-r", "-d", "1"],
                capture_output=True, text=True, timeout=3)
            for line in r.stdout.split("\n"):
                if '"Device Utilization %"' in line:
                    try:
                        pct = float(line.split("=")[-1].strip().rstrip("%"))
                        return {"pct": round(pct, 1)}
                    except Exception:
                        pass
                    break
        except Exception:
            pass
        return {"pct": 0.0}

    @staticmethod
    def is_as():
        return _sysctl("hw.optional.arm64") == "1"

    @staticmethod
    def chip():
        return _sysctl("machdep.cpu.brand_string")


class Optimizer:
    def __init__(self, log_cb=None):
        self.log = log_cb or (lambda m: None)
        self.is_as = SystemInfo.is_as()

    def _size_mb(self, path):
        try:
            total = 0
            for f in path.rglob("*"):
                if f.is_file():
                    try: total += f.stat().st_size
                    except Exception: pass
            return round(total / 1024**2, 1)
        except Exception:
            return 0

    def _clear_dir(self, path):
        if not path.exists(): return 0
        before = self._size_mb(path)
        try:
            shutil.rmtree(path, ignore_errors=True)
            path.mkdir(parents=True, exist_ok=True)
        except Exception:
            for f in path.glob("*"):
                try:
                    if f.is_file(): f.unlink()
                    elif f.is_dir(): shutil.rmtree(f, ignore_errors=True)
                except Exception: pass
        after = self._size_mb(path)
        return before - after

    def ram(self):
        out = []
        before = SystemInfo.ram()
        total_freed = 0

        # Aggressive user cache clearing (no sudo needed)
        cache_dirs = [
            Path.home()/"Library"/"Caches",
            Path.home()/"Library"/"Caches"/"com.apple.WebKit.Networking",
            Path.home()/"Library"/"Caches"/"com.apple.WebKit.WebContent",
            Path.home()/"Library"/"Caches"/"com.apple.Safari",
            Path.home()/"Library"/"Caches"/"Google"/"Chrome",
            Path.home()/"Library"/"Caches"/"com.google.Chrome",
            Path.home()/"Library"/"Caches"/"BraveSoftware"/"Brave-Browser",
            Path.home()/"Library"/"Caches"/"com.microsoft.edgemac",
            Path.home()/"Library"/"Caches"/"com.apple.dt.Xcode",
            Path.home()/"Library"/"Caches"/"pip",
            Path.home()/".npm"/"_cacache",
            Path.home()/"Library"/"Caches"/"yarn",
            Path.home()/"Library"/"Caches"/"com.apple.helpd",
            Path.home()/"Library"/"Caches"/"com.apple.nsurlsessiond",
            Path.home()/"Library"/"Caches"/"com.apple.Spotlight",
            Path.home()/"Library"/"Caches"/"com.apple.coresymbolicationd",
        ]
        for d in cache_dirs:
            freed = self._clear_dir(d)
            if freed > 1:
                total_freed += freed
                out.append(f"freed {freed:.0f}MB from {d.name}")

        # Clear /tmp user files
        tmp = Path("/tmp")
        try:
            for f in tmp.glob("*"):
                try:
                    if f.owner() == os.getlogin():
                        if f.is_file(): f.unlink()
                        elif f.is_dir(): shutil.rmtree(f, ignore_errors=True)
                except Exception: pass
        except Exception: pass

        # Clear system logs (user-readable)
        log_dirs = [Path.home()/"Library"/"Logs"]
        for d in log_dirs:
            freed = self._clear_dir(d)
            if freed > 1:
                total_freed += freed
                out.append(f"freed {freed:.0f}MB from logs")

        # sync + purge (sudo)
        _run("sync")
        ok, msg = _run("purge", sudo=True)
        out.append(f"purge: {'ok' if ok else 'skipped (sudo needed)'}")

        gc.collect()
        after = SystemInfo.ram()
        delta = before["pct"] - after["pct"]
        out.append(f"RAM: {before['pct']:.0f}% → {after['pct']:.0f}% ({delta:+.0f}%)")
        if total_freed > 0:
            out.append(f"Total freed: {total_freed:.0f}MB disk cache")
        return out

    def cpu(self):
        out = []
        before = SystemInfo.cpu()["pct"]
        boosted = 0
        throttled = 0

        for p in psutil.process_iter(["pid","name","cpu_percent","create_time"]):
            try:
                n = p.info["name"] or ""
                pid = p.info["pid"]
                cpu = p.info.get("cpu_percent") or 0
                born = p.info.get("create_time") or time.time()
                age = time.time() - born

                # Boost Windsurf main processes
                if any(t in n for t in WINDSURF_NAMES) and "Helper" not in n:
                    _run(f"renice -n -5 -p {pid}")
                    if self.is_as:
                        _run(f"taskpolicy -d user_interactive -p {pid}")
                    boosted += 1

                # Throttle heavy background helpers
                elif "Helper" in n and any(w in n for w in ["Windsurf","Code","Electron"]):
                    if cpu > 30 and age > 60:
                        if self.is_as:
                            _run(f"taskpolicy -b -p {pid}")
                        throttled += 1

                # Throttle any CPU-hogging user process (non-system)
                elif cpu > 80 and age > 30 and pid > 100:
                    try:
                        proc = psutil.Process(pid)
                        if proc.username() == os.getlogin():
                            if self.is_as:
                                _run(f"taskpolicy -b -p {pid}")
                            throttled += 1
                            out.append(f"throttled CPU hog: {n}({pid}) at {cpu:.0f}%")
                    except Exception: pass
            except (psutil.NoSuchProcess, psutil.AccessDenied): pass

        if boosted:
            out.append(f"boosted {boosted} Windsurf processes")
        if throttled:
            out.append(f"throttled {throttled} background processes")

        _run("defaults write com.exafunction.windsurf NSAppSleepDisabled -bool true")
        out.append("AppNap disabled")

        after = SystemInfo.cpu()["pct"]
        delta = before - after
        out.append(f"CPU: {before:.0f}% → {after:.0f}% ({delta:+.0f}%)")
        return out

    def gpu(self):
        out = []
        before = SystemInfo.gpu()["pct"]

        # Clear GPU-related caches
        gpu_caches = [
            Path.home()/"Library"/"Caches"/"com.apple.coreanimation",
            Path.home()/"Library"/"Caches"/"com.apple.Metal",
            Path.home()/"Library"/"Caches"/"com.apple.gpuswitching",
        ]
        for d in gpu_caches:
            freed = self._clear_dir(d)
            if freed > 0.5:
                out.append(f"freed {freed:.0f}MB GPU cache")

        _run("qlmanage -r cache >/dev/null 2>&1")
        out.append("QuickLook flushed")

        # Reduce transparency for GPU relief
        _run("defaults write com.apple.universalaccess reduceTransparency -bool true")
        out.append("transparency reduced")

        after = SystemInfo.gpu()["pct"]
        delta = before - after
        out.append(f"GPU: {before:.0f}% → {after:.0f}% ({delta:+.0f}%)")
        return out

    def windsurf(self):
        out = []
        total_freed = 0
        ws_dirs = [
            Path.home()/"Library"/"Application Support"/"Windsurf"/"Cache",
            Path.home()/"Library"/"Application Support"/"Windsurf"/"CachedData",
            Path.home()/"Library"/"Application Support"/"Windsurf"/"Code Cache",
            Path.home()/"Library"/"Application Support"/"Windsurf"/"GPUCache",
            Path.home()/"Library"/"Caches"/"Windsurf",
            Path.home()/"Library"/"Application Support"/"Windsurf"/"CachedExtensionVSIXs",
            Path.home()/"Library"/"Application Support"/"Windsurf"/"Cache"/"Cache_Data",
            Path.home()/"Library"/"Application Support"/"Windsurf"/"Service Worker",
            Path.home()/"Library"/"Application Support"/"Windsurf"/"Local Storage",
            Path.home()/"Library"/"Application Support"/"Windsurf"/"Session Storage",
        ]
        for d in ws_dirs:
            freed = self._clear_dir(d)
            if freed > 0.5:
                total_freed += freed
                out.append(f"freed {freed:.0f}MB: {d.name}")

        # Boost Windsurf processes
        boosted = 0
        for p in psutil.process_iter(["pid","name"]):
            try:
                n = p.info["name"] or ""
                if any(t in n for t in WINDSURF_NAMES):
                    pid = p.info["pid"]
                    _run(f"renice -n -5 -p {pid}")
                    if self.is_as:
                        _run(f"taskpolicy -d user_interactive -p {pid}")
                    boosted += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied): pass

        if boosted:
            out.append(f"boosted {boosted} Windsurf processes")
        if total_freed > 0:
            out.append(f"Total freed: {total_freed:.0f}MB Windsurf cache")

        _run('defaults write com.exafunction.windsurf "crashes.reportUnhandledExceptions" -bool false')
        return out

    def full(self):
        return self.ram() + self.cpu() + self.gpu() + self.windsurf()

    def deep_ram(self):
        out = []
        before = SystemInfo.ram()
        # Swap management
        ok, swap = _run("sysctl vm.swapusage")
        if ok: out.append(f"swap: {swap}")
        # Memory compression mode
        _run("sysctl -w vm.compressor_mode=4", sudo=True)
        out.append("compressor: VM (mode 4)")
        # Purge disk cache
        ok, _ = _run("purge", sudo=True)
        out.append(f"purge: {'ok' if ok else 'skipped'}")
        # Clear unified buffer cache
        _run("sync")
        after = SystemInfo.ram()
        delta = before["pct"] - after["pct"]
        out.append(f"Deep RAM: {before['pct']:.0f}% → {after['pct']:.0f}% ({delta:+.0f}%)")
        return out

    def deep_cpu(self):
        out = []
        before = SystemInfo.cpu()["pct"]
        # QoS for Windsurf
        for p in psutil.process_iter(["pid","name"]):
            try:
                n = p.info["name"] or ""
                if any(t in n for t in WINDSURF_NAMES):
                    pid = p.info["pid"]
                    _run(f"renice -n -10 -p {pid}", sudo=True)
                    if self.is_as:
                        _run(f"taskpolicy -d user_interactive -p {pid}")
            except Exception: pass
        out.append("Windsurf QoS: user_interactive")
        # Thermal throttling relief
        if self.is_as:
            _run("pmset -a thermalspeed 0", sudo=True)
            out.append("thermal throttle: relaxed")
        # I/O priority for Windsurf
        _run("defaults write com.exafunction.windsurf NSAppSleepDisabled -bool true")
        out.append("I/O priority: high")
        after = SystemInfo.cpu()["pct"]
        delta = before - after
        out.append(f"Deep CPU: {before:.0f}% → {after:.0f}% ({delta:+.0f}%)")
        return out

    def deep_gpu(self):
        out = []
        before = SystemInfo.gpu()["pct"]
        # Metal shader cache
        for d in (Path.home()/"Library"/"Caches"/"com.apple.Metal",
                  Path.home()/"Library"/"Caches"/"com.apple.metal",
                  Path("/private/var/folders")):
            if d.exists():
                freed = self._clear_dir(d)
                if freed > 0.5:
                    out.append(f"freed {freed:.0f}MB Metal cache")
        # Display power management
        _run("pmset -a gpuswitch 0", sudo=True)
        out.append("GPU: performance mode")
        # WindowServer optimization
        _run("defaults write com.apple.WindowServer GLCompositorUseDisplayLink -bool false")
        out.append("WindowServer: optimized")
        after = SystemInfo.gpu()["pct"]
        delta = before - after
        out.append(f"Deep GPU: {before:.0f}% → {after:.0f}% ({delta:+.0f}%)")
        return out

    def deep_system(self):
        out = []
        # Power management
        _run("pmset -a powermode 2", sudo=True)
        out.append("power: high performance")
        # Disk I/O
        _run("sysctl -w kern.maxvnodes=600000", sudo=True)
        out.append("vnode cache: expanded")
        # Network
        _run("sysctl -w net.inet.tcp.delayed_ack=0", sudo=True)
        out.append("TCP: low latency")
        # Kernel
        _run("sysctl -w kern.ipc.maxsockbuf=8388608", sudo=True)
        out.append("socket buffer: 8MB")
        # Disable swap encryption
        _run("sysctl -w vm.swap_encryption=0", sudo=True)
        out.append("swap encryption: off")
        return out

    def deep_full(self):
        return self.deep_ram() + self.deep_cpu() + self.deep_gpu() + self.deep_system()


class OllamaClient:
    def __init__(self, host=OLLAMA_HOST):
        self.host = host.rstrip("/")

    def is_running(self):
        try:
            return requests.get(f"{self.host}/api/tags", timeout=2).status_code == 200
        except Exception:
            return False

    def list_models(self):
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=5)
            return [m["name"] for m in r.json().get("models", [])]
        except Exception:
            return []

    def chat(self, model, prompt, on_chunk):
        try:
            with requests.post(f"{self.host}/api/generate",
                              json={"model": model, "prompt": prompt, "stream": True},
                              stream=True, timeout=60) as r:
                for line in r.iter_lines():
                    if not line: continue
                    try:
                        obj = json.loads(line.decode())
                        if "response" in obj: on_chunk(obj["response"])
                        if obj.get("done"): break
                    except Exception: pass
        except Exception as e:
            on_chunk(f"\n[Error: {e}]")


class SmartOptimizer:
    """LLM-driven optimizer — analyzes system state and decides what to compress."""
    def __init__(self, ollama, optimizer, log_cb=None):
        self.ollama = ollama
        self.opt = optimizer
        self.log = log_cb or (lambda m: None)

    def analyze_and_optimize(self, model):
        snapshot = self._snapshot()
        prompt = self._build_prompt(snapshot)
        self.log("Asking LLM to analyze system…")
        response = []
        self.ollama.chat(model, prompt, lambda c: response.append(c))
        plan = "".join(response).strip()
        self.log(f"LLM plan: {plan[:200]}…" if len(plan) > 200 else f"LLM plan: {plan}")
        return self._execute_plan(plan)

    def _snapshot(self):
        ram = SystemInfo.ram()
        cpu = SystemInfo.cpu()
        gpu = SystemInfo.gpu()
        top = []
        for p in psutil.process_iter(["pid","name","cpu_percent","memory_percent"]):
            try:
                n = p.info["name"] or ""
                cpu_p = p.info.get("cpu_percent") or 0
                mem_p = p.info.get("memory_percent") or 0
                if cpu_p > 5 or mem_p > 5:
                    top.append((n, round(cpu_p, 1), round(mem_p, 1)))
            except Exception: pass
        top.sort(key=lambda x: x[1] + x[2], reverse=True)
        return {
            "ram_pct": ram["pct"], "ram_used_gb": ram["used"], "ram_total_gb": ram["total"],
            "cpu_pct": cpu["pct"], "cpu_cores": cpu["cores"],
            "gpu_pct": gpu["pct"],
            "is_apple_silicon": self.opt.is_as,
            "top_processes": top[:8]
        }

    def _build_prompt(self, s):
        procs = "\n".join(f"  {n}: CPU {c}% MEM {m}%" for n, c, m in s["top_processes"])
        return f"""You are a macOS system optimizer for Apple Silicon. Analyze this system state and decide EXACTLY which optimizations to run.

Current state:
- RAM: {s['ram_pct']:.0f}% ({s['ram_used_gb']}GB / {s['ram_total_gb']}GB)
- CPU: {s['cpu_pct']:.0f}% ({s['cpu_cores']} cores)
- GPU: {s['gpu_pct']:.0f}%
- Apple Silicon: {s['is_apple_silicon']}

Top processes by CPU/MEM:
{procs}

Available actions:
- ram: clear caches, purge memory, flush DNS
- cpu: boost Windsurf, throttle helpers, disable AppNap
- gpu: clear GPU caches, reduce transparency
- windsurf: clear Windsurf caches, boost processes
- deep_ram: swap management, memory compression, purge
- deep_cpu: QoS, thermal throttle relief, I/O priority
- deep_gpu: Metal cache, display power, WindowServer
- deep_system: power mode, vnode cache, TCP, socket buffer
- full: run all standard optimizations
- deep_full: run all deep optimizations

Respond with ONLY a comma-separated list of actions to run, e.g.: "ram, cpu, deep_gpu"
Choose actions based on what's most needed. If RAM > 70%, include ram or deep_ram. If CPU > 50%, include cpu or deep_cpu. If GPU > 30%, include gpu or deep_gpu."""

    def _execute_plan(self, plan):
        results = []
        actions = [a.strip() for a in plan.replace("\n", "").split(",")]
        valid = {"ram", "cpu", "gpu", "windsurf", "full",
                 "deep_ram", "deep_cpu", "deep_gpu", "deep_system", "deep_full"}
        for action in actions:
            if action not in valid:
                self.log(f"Unknown action: {action}, skipping")
                continue
            self.log(f"Executing: {action}")
            try:
                fn = getattr(self.opt, action)
                for line in fn():
                    self.log(f"  {line}")
                    results.append((action, line))
            except Exception as e:
                self.log(f"Error in {action}: {e}")
        return results


class Verifier:
    """Self-diagnostics — verify app integrity and system readiness."""
    def __init__(self, log_cb=None):
        self.log = log_cb or (lambda m: None)
        self.results = []

    def run_all(self):
        self.results = []
        self._check("Python 3.11", sys.version_info[:2] == (3, 11))
        self._check("psutil", self._test_psutil())
        self._check("requests", self._test_requests())
        self._check("AppKit", self._test_appkit())
        self._check("Apple Silicon", SystemInfo.is_as())
        self._check("sudo access", self._test_sudo())
        self._check("Ollama reachable", OllamaClient().is_running())
        self._check("Windsurf running", self._test_windsurf())
        self._check("purge available", self._test_purge())
        self._check("taskpolicy", self._test_taskpolicy())
        return self.results

    def _check(self, name, ok):
        icon = "✓" if ok else "✗"
        self.results.append((name, ok, icon))
        self.log(f"{icon} {name}: {'OK' if ok else 'FAIL'}")

    def _test_psutil(self):
        try:
            psutil.virtual_memory()
            return True
        except Exception:
            return False

    def _test_requests(self):
        try:
            requests.get(f"{OLLAMA_HOST}/api/tags", timeout=1)
            return True
        except Exception:
            return False

    def _test_appkit(self):
        try:
            from AppKit import NSColor
            _ = NSColor.clearColor()
            return True
        except Exception:
            return False

    def _test_sudo(self):
        ok, _ = _run("echo ok", sudo=True)
        return ok

    def _test_windsurf(self):
        for p in psutil.process_iter(["name"]):
            try:
                if any(t in (p.info["name"] or "") for t in WINDSURF_NAMES):
                    return True
            except Exception:
                pass
        return False

    def _test_purge(self):
        ok, _ = _run("which purge")
        return ok

    def _test_taskpolicy(self):
        ok, _ = _run("which taskpolicy")
        return ok


class NeomorphicPanel:
    def __init__(self, app):
        self.app = app
        self.opt = Optimizer(log_cb=self._log)
        self.ollama = OllamaClient()
        self.models = []
        self._build()

    def _build(self):
        frame = NSMakeRect(100, 100, 420, 600)
        mask = (NSTitledWindowMask | NSClosableWindowMask |
                NSResizableWindowMask | NSFullSizeContentViewWindowMask)
        self.win = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            frame, mask, NSBackingStoreBuffered, False)
        self.win.setTitle_(APP_NAME)
        self.win.setTitlebarAppearsTransparent_(True)
        self.win.setTitleVisibility_(NSWindowTitleHidden)
        self.win.setMovableByWindowBackground_(True)
        self.win.setLevel_(NSFloatingWindowLevel)
        self.win.setBackgroundColor_(NSColor.clearColor())
        self.win.setOpaque_(False)
        self.win.setHasShadow_(True)

        # Vibrancy background
        self.effect = NSVisualEffectView.alloc().initWithFrame_(self.win.contentView().bounds())
        self.effect.setAutoresizingMask_(18)  # NSViewWidthSizable | NSViewHeightSizable
        self.effect.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
        self.effect.setMaterial_(NSVisualEffectMaterialDark)
        self.effect.setState_(NSVisualEffectStateActive)
        self.effect.setWantsLayer_(True)
        self.effect.layer().setCornerRadius_(20)
        self.effect.layer().setBorderWidth_(0.5)
        self.effect.layer().setBorderColor_(
            NSColor.colorWithWhite_alpha_(1.0, 0.08).CGColor())
        self.effect.layer().setMasksToBounds_(True)
        self.win.contentView().addSubview_(self.effect)

        self._add_glass_cards()
        self._add_stats()
        self._add_buttons()
        self._add_log()
        self._add_ollama()
        self._start_poll()

    def _mk_label(self, text, frame, font_size=10, color=DIM_COLOR, bold=False):
        f = NSFont.systemFontOfSize_weight_(font_size,
            0.4 if bold else 0.3)  # NSFontWeightMedium / Regular
        tf = NSTextField.alloc().initWithFrame_(frame)
        tf.setStringValue_(text)
        tf.setFont_(f)
        tf.setTextColor_(color)
        tf.setBezeled_(False)
        tf.setDrawsBackground_(False)
        tf.setEditable_(False)
        tf.setSelectable_(False)
        tf.setAlignment_(NSTextAlignmentCenter)
        return tf

    def _add_glass_cards(self):
        positions = [(10, 490, 120, 70), (145, 490, 120, 70), (280, 490, 120, 70)]
        for x, y, w, h in positions:
            card = NSView.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
            card.setWantsLayer_(True)
            card.layer().setBackgroundColor_(CARD_RAISED.CGColor())
            card.layer().setCornerRadius_(16)
            card.layer().setBorderWidth_(0.5)
            card.layer().setBorderColor_(GLASS_BORDER.CGColor())
            card.layer().setShadowOpacity_(0.4)
            card.layer().setShadowRadius_(10)
            card.layer().setShadowOffset_(NSMakeSize(0, -3))
            card.layer().setShadowColor_(GLASS_SHADOW.CGColor())
            card.layer().setMasksToBounds_(False)
            inner = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, w, h))
            inner.setWantsLayer_(True)
            inner.layer().setBackgroundColor_(GLASS_HIGHLIGHT.CGColor())
            inner.layer().setCornerRadius_(16)
            inner.layer().setMasksToBounds_(True)
            card.addSubview_(inner)
            self.effect.addSubview_(card)

    def _add_stats(self):
        labels = [("RAM", 10), ("CPU", 145), ("GPU", 280)]
        self.stat_fields = {}
        for name, x in labels:
            self.effect.addSubview_(self._mk_label(name, NSMakeRect(x, 540, 120, 16), 9, DIM_COLOR))
            tf = self._mk_label("—", NSMakeRect(x, 500, 120, 32), 20, TEXT_COLOR, True)
            self.effect.addSubview_(tf)
            self.stat_fields[name] = tf
        chip = SystemInfo.chip()
        if chip:
            self.effect.addSubview_(self._mk_label(chip, NSMakeRect(10, 482, 400, 14), 8, DIM_COLOR))

    def _add_buttons(self):
        actions = [("RAM", 10), ("CPU", 112), ("GPU", 214), ("WS", 316)]
        for label, x in actions:
            btn = NSButton.alloc().initWithFrame_(NSMakeRect(x, 440, 90, 28))
            btn.setTitle_(label)
            btn.setBezelStyle_(NSBezelStyleRounded)
            btn.setFont_(NSFont.systemFontOfSize_weight_(10, 0.4))
            btn.setTarget_(self)
            btn.setAction_(f"opt_{label.lower()}:")
            btn.setWantsLayer_(True)
            btn.layer().setCornerRadius_(8)
            self.effect.addSubview_(btn)
        smart = NSButton.alloc().initWithFrame_(NSMakeRect(10, 400, 400, 32))
        smart.setTitle_("SMART OPTIMIZE (LLM)")
        smart.setBezelStyle_(NSBezelStyleRounded)
        smart.setFont_(NSFont.systemFontOfSize_weight_(11, 0.5))
        smart.setTarget_(self)
        smart.setAction_("smart_optimize:")
        smart.setWantsLayer_(True)
        smart.layer().setCornerRadius_(8)
        self.effect.addSubview_(smart)
        full = NSButton.alloc().initWithFrame_(NSMakeRect(10, 362, 400, 32))
        full.setTitle_("FULL OPTIMIZE")
        full.setBezelStyle_(NSBezelStyleRounded)
        full.setFont_(NSFont.systemFontOfSize_weight_(11, 0.5))
        full.setTarget_(self)
        full.setAction_("opt_full:")
        full.setWantsLayer_(True)
        full.layer().setCornerRadius_(8)
        self.effect.addSubview_(full)
        verify = NSButton.alloc().initWithFrame_(NSMakeRect(10, 324, 400, 32))
        verify.setTitle_("Verify System")
        verify.setBezelStyle_(NSBezelStyleRounded)
        verify.setFont_(NSFont.systemFontOfSize_weight_(11, 0.4))
        verify.setTarget_(self)
        verify.setAction_("run_verify:")
        verify.setWantsLayer_(True)
        verify.layer().setCornerRadius_(8)
        self.effect.addSubview_(verify)

    def _add_log(self):
        scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(10, 170, 400, 145))
        scroll.setHasVerticalScroller_(True)
        scroll.setBorderType_(0)
        self.log_view = NSTextView.alloc().initWithFrame_(scroll.contentView().bounds())
        self.log_view.setEditable_(False)
        self.log_view.setFont_(NSFont.systemFontOfSize_(10))
        self.log_view.setTextColor_(TEXT_COLOR)
        self.log_view.setBackgroundColor_(NSColor.clearColor())
        self.log_view.setDrawsBackground_(False)
        scroll.setDocumentView_(self.log_view)
        self.effect.addSubview_(scroll)

    def _add_ollama(self):
        self.ollama_status = self._mk_label("●", NSMakeRect(10, 148, 20, 16), 8, DIM_COLOR)
        self.effect.addSubview_(self.ollama_status)
        self.effect.addSubview_(self._mk_label("Ollama", NSMakeRect(28, 150, 380, 14), 9, DIM_COLOR))
        self.model_btn = NSButton.alloc().initWithFrame_(NSMakeRect(10, 122, 180, 22))
        self.model_btn.setTitle_("Loading models…")
        self.model_btn.setBezelStyle_(NSBezelStyleRounded)
        self.model_btn.setFont_(NSFont.systemFontOfSize_(9))
        self.model_btn.setTarget_(self)
        self.model_btn.setAction_("cycle_model:")
        self.effect.addSubview_(self.model_btn)

        scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(10, 55, 400, 60))
        scroll.setHasVerticalScroller_(True)
        scroll.setBorderType_(0)
        self.chat_view = NSTextView.alloc().initWithFrame_(scroll.contentView().bounds())
        self.chat_view.setEditable_(False)
        self.chat_view.setFont_(NSFont.systemFontOfSize_(10))
        self.chat_view.setTextColor_(TEXT_COLOR)
        self.chat_view.setBackgroundColor_(NSColor.clearColor())
        self.chat_view.setDrawsBackground_(False)
        scroll.setDocumentView_(self.chat_view)
        self.effect.addSubview_(scroll)

        self.entry = NSTextField.alloc().initWithFrame_(NSMakeRect(10, 22, 310, 24))
        self.entry.setFont_(NSFont.systemFontOfSize_(10))
        self.entry.setTextColor_(TEXT_COLOR)
        self.entry.setBackgroundColor_(CARD_COLOR)
        self.entry.setBezeled_(True)
        self.entry.setBezelStyle_(NSRoundedBezelStyle)
        self.entry.setTarget_(self)
        self.entry.setAction_("send_chat:")
        self.effect.addSubview_(self.entry)

        send = NSButton.alloc().initWithFrame_(NSMakeRect(328, 20, 80, 26))
        send.setTitle_("Send")
        send.setBezelStyle_(NSBezelStyleRounded)
        send.setFont_(NSFont.systemFontOfSize_weight_(10, 0.4))
        send.setTarget_(self)
        send.setAction_("send_chat:")
        self.effect.addSubview_(send)

    def _start_poll(self):
        def poll():
            while True:
                try:
                    ram = SystemInfo.ram()
                    cpu = SystemInfo.cpu()
                    gpu = SystemInfo.gpu()
                    self.stat_fields["RAM"].setStringValue_(f"{ram['pct']:.0f}%")
                    self.stat_fields["CPU"].setStringValue_(f"{cpu['pct']:.0f}%")
                    self.stat_fields["GPU"].setStringValue_(f"{gpu['pct']:.0f}%")
                    online = self.ollama.is_running()
                    self.ollama_status.setStringValue_("●")
                    self.ollama_status.setTextColor_(GREEN_COLOR if online else RED_COLOR)
                except Exception: pass
                time.sleep(2)
        threading.Thread(target=poll, daemon=True).start()
        threading.Thread(target=self._load_models, daemon=True).start()

    def _load_models(self):
        self.models = self.ollama.list_models()
        if self.models:
            self.model_btn.setTitle_(self.models[0])
        else:
            self.model_btn.setTitle_("No models")

    def _log(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.log_view.textStorage().appendAttributedString_(
            NSAttributedString.alloc().initWithString_attributes_(
                f"[{ts}] {msg}\n", {NSFontAttributeName: NSFont.systemFontOfSize_(10),
                 NSForegroundColorAttributeName: TEXT_COLOR}))
        self.log_view.scrollToEndOfDocument_(None)

    def _run_opt(self, mode):
        def task():
            self._log(f"Starting {mode}…")
            try:
                fn = getattr(self.opt, mode)
                for line in fn(): self._log(f"  {line}")
                self._log(f"Done: {mode}")
            except Exception as e:
                self._log(f"Error: {e}")
        threading.Thread(target=task, daemon=True).start()

    def run_verify(self, _):
        def task():
            self._log("Running diagnostics…")
            v = Verifier(log_cb=self._log)
            results = v.run_all()
            passed = sum(1 for _, ok, _ in results if ok)
            total = len(results)
            self._log(f"Results: {passed}/{total} passed")
        threading.Thread(target=task, daemon=True).start()

    def smart_optimize(self, _):
        model = self.model_btn.title()
        if model in ("Loading models…", "No models"):
            self._log("No Ollama model available for Smart Optimize")
            return
        def task():
            self._log("Smart Optimize: analyzing system…")
            smart = SmartOptimizer(self.ollama, self.opt, log_cb=self._log)
            smart.analyze_and_optimize(model)
            self._log("Smart Optimize: complete")
        threading.Thread(target=task, daemon=True).start()

    def opt_ram(self, _): self._run_opt("ram")
    def opt_cpu(self, _): self._run_opt("cpu")
    def opt_gpu(self, _): self._run_opt("gpu")
    def opt_ws(self, _): self._run_opt("windsurf")
    def opt_full(self, _): self._run_opt("full")

    def cycle_model(self, _):
        if not self.models: return
        cur = self.model_btn.title()
        try:
            idx = self.models.index(cur)
            nxt = self.models[(idx + 1) % len(self.models)]
        except ValueError:
            nxt = self.models[0]
        self.model_btn.setTitle_(nxt)

    def send_chat(self, _):
        model = self.model_btn.title()
        if model in ("Loading models…", "No models"):
            self._log("No Ollama model available")
            return
        text = self.entry.stringValue().strip()
        if not text: return
        self.entry.setStringValue_("")
        self._append_chat(f"You: {text}\n")
        self._append_chat("AI: …", pending=True)

        def stream():
            full = ""
            def on_chunk(c):
                nonlocal full; full += c
                self._update_pending(f"AI: {full}")
            self.ollama.chat(model, text, on_chunk)
            self._finalize_pending()
        threading.Thread(target=stream, daemon=True).start()

    def _append_chat(self, text, pending=False):
        color = DIM_COLOR if pending else TEXT_COLOR
        self.chat_view.textStorage().appendAttributedString_(
            NSAttributedString.alloc().initWithString_attributes_(
                text + "\n", {NSFontAttributeName: NSFont.systemFontOfSize_(10),
                 NSForegroundColorAttributeName: color}))
        self.chat_view.scrollToEndOfDocument_(None)

    def _update_pending(self, text):
        store = self.chat_view.textStorage()
        s = store.string()
        last_nl = s.rfind("\n")
        if last_nl >= 0:
            prev_nl = s.rfind("\n", 0, last_nl)
            start = (prev_nl + 1) if prev_nl >= 0 else 0
            rng = NSMakeRange(start, len(s) - start)
            store.replaceCharactersInRange_withString_(rng, text)
        else:
            store.setAttributedString_(
                NSAttributedString.alloc().initWithString_attributes_(
                    text, {NSFontAttributeName: NSFont.systemFontOfSize_(10),
                     NSForegroundColorAttributeName: TEXT_COLOR}))
        self.chat_view.scrollToEndOfDocument_(None)

    def _finalize_pending(self):
        pass  # pending text is already final

    def show(self):
        self.win.makeKeyAndOrderFront_(None)
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    def hide(self):
        self.win.orderOut_(None)


class WindsurfOptimizerApp(rumps.App):
    def __init__(self):
        super().__init__(name=APP_NAME, title=ICON_DISK, quit_button="Quit")
        self.panel = None
        self._auto_timer = None
        self._auto_on = False
        self.menu = [
            rumps.MenuItem("Open Panel", callback=self._open),
            None,
            rumps.MenuItem("Full Optimize", callback=self._menu_full),
            rumps.MenuItem("RAM", callback=self._menu_ram),
            rumps.MenuItem("CPU", callback=self._menu_cpu),
            rumps.MenuItem("GPU", callback=self._menu_gpu),
            rumps.MenuItem("Windsurf", callback=self._menu_ws),
            None,
            rumps.MenuItem("Auto 5m", callback=self._menu_auto),
        ]

    def _ensure(self):
        if not self.panel:
            self.panel = NeomorphicPanel(self)
        return self.panel

    def _open(self, _): self._ensure().show()
    def _menu_full(self, _): self._ensure().opt_full(None); self._ensure().show()
    def _menu_ram(self, _): self._ensure().opt_ram(None)
    def _menu_cpu(self, _): self._ensure().opt_cpu(None)
    def _menu_gpu(self, _): self._ensure().opt_gpu(None)
    def _menu_ws(self, _): self._ensure().opt_ws(None)

    def _menu_auto(self, sender):
        self._auto_on = not self._auto_on
        sender.state = self._auto_on
        if self._auto_on:
            self._auto_timer = rumps.Timer(lambda _: self._ensure().opt_full(None), 300)
            self._auto_timer.start()
        elif self._auto_timer:
            self._auto_timer.stop()


if __name__ == "__main__":
    WindsurfOptimizerApp().run()

#!/usr/bin/env python3
"""Windsurf Optimizer — macOS menu-bar app. PyObjC NSPanel, no tkinter."""
import gc, json, os, shutil, subprocess, sys, threading, time
from pathlib import Path
import psutil, rumps, requests
from AppKit import (NSWindow, NSView, NSButton, NSTextView, NSScrollView,
    NSColor, NSFont, NSMakeRect, NSVisualEffectView, NSBorderlessWindowMask,
    NSFloatingWindowLevel, NSBackingStoreBuffered, NSBezelStyleRounded,
    NSMomentaryLightButton, NSMakeSize, NSZeroRect, NSTitledWindowMask,
    NSClosableWindowMask, NSResizableWindowMask, NSTextField, NSPanel,
    NSUtilityWindowMask, NSHUDWindowMask, NSFullSizeContentViewWindowMask,
    NSWindowTitleHidden, NSVisualEffectBlendingModeBehindWindow,
    NSVisualEffectMaterialDark, NSVisualEffectStateActive,
    NSBezelStyleRegularSquare, NSControlStateValueOn, NSControlStateValueOff,
    NSOnState, NSOffState, NSRoundedBezelStyle, NSSmallControlSize,
    NSRegularControlSize, NSTextAlignmentCenter, NSTextAlignmentLeft,
    NSLineBreakByWordWrapping, NSLineBreakByClipping)

APP_NAME = "Windsurf Optimizer"
ICON_DISK = "\U0001f4bf"
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
WINDSURF_NAMES = {"Windsurf", "windsurf", "Code Helper",
                  "Code-Helper", "Electron", "windsurf Helper"}
BG_DARK = NSColor.colorWithRed_green_blue_alpha_(0.06, 0.06, 0.12, 0.95)
CARD_COLOR = NSColor.colorWithRed_green_blue_alpha_(0.10, 0.10, 0.18, 0.90)
ACCENT = NSColor.colorWithRed_green_blue_alpha_(0.91, 0.27, 0.39, 1.0)
TEXT_COLOR = NSColor.colorWithRed_green_blue_alpha_(0.88, 0.90, 0.93, 1.0)
DIM_COLOR = NSColor.colorWithRed_green_blue_alpha_(0.53, 0.57, 0.69, 1.0)


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
        return {"pressure": psutil.virtual_memory().percent}

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

    def ram(self):
        out = []
        ok, msg = _run("purge", sudo=True)
        out.append(f"purge: {'ok' if ok else msg}")
        _run("dscacheutil -flushcache; killall -HUP mDNSResponder", sudo=True)
        out.append("DNS flushed")
        cutoff = time.time() - 300
        for d in (Path.home()/"Library"/"Caches",
                  Path.home()/"Library"/"Caches"/"com.apple.WebKit.Networking"):
            if not d.exists(): continue
            for f in d.rglob("*"):
                try:
                    if f.is_file() and f.stat().st_atime < cutoff: f.unlink()
                except Exception: pass
        out.append("caches cleared")
        gc.collect()
        return out

    def cpu(self):
        out = []
        ws, heavy = [], []
        for p in psutil.process_iter(["pid","name","cpu_percent","create_time"]):
            try:
                n = p.info["name"] or ""
                pid = p.info["pid"]
                if any(t in n for t in WINDSURF_NAMES):
                    ws.append((pid, n))
                elif self.is_as and "Helper" in n and any(w in n for w in ["Windsurf","Code","Electron"]):
                    cpu = p.info.get("cpu_percent") or 0
                    born = p.info.get("create_time") or time.time()
                    if cpu > 50 and (time.time()-born) > 120: heavy.append((pid, n))
            except (psutil.NoSuchProcess, psutil.AccessDenied): pass
        for pid, n in ws:
            os.system(f"renice -n -10 -p {pid} >/dev/null 2>&1")
            out.append(f"boosted {n}({pid})")
        if self.is_as:
            for pid, n in heavy:
                os.system(f"taskpolicy -b -p {pid} >/dev/null 2>&1")
                out.append(f"throttled {n}({pid})")
        _run("defaults write com.exafunction.windsurf NSAppSleepDisabled -bool true")
        out.append("AppNap off")
        return out

    def gpu(self):
        out = []
        _run("qlmanage -r >/dev/null 2>&1; qlmanage -r cache >/dev/null 2>&1")
        out.append("QuickLook flushed")
        _run("atsutil databases -removeUser")
        out.append("font cache flushed")
        ca = Path.home()/"Library"/"Caches"/"com.apple.coreanimation"
        if ca.exists(): shutil.rmtree(ca, ignore_errors=True)
        out.append("CoreAnimation cleared")
        _run("purge", sudo=True)
        return out

    def windsurf(self):
        out = []
        for d in (Path.home()/"Library"/"Application Support"/"Windsurf"/"Cache",
                  Path.home()/"Library"/"Application Support"/"Windsurf"/"CachedData",
                  Path.home()/"Library"/"Application Support"/"Windsurf"/"Code Cache",
                  Path.home()/"Library"/"Application Support"/"Windsurf"/"GPUCache",
                  Path.home()/"Library"/"Caches"/"Windsurf",
                  Path.home()/"Library"/"Application Support"/"Windsurf"/"CachedExtensionVSIXs"):
            if d.exists(): shutil.rmtree(d, ignore_errors=True); out.append(f"cleared {d.name}")
        for p in psutil.process_iter(["pid","name"]):
            try:
                n = p.info["name"] or ""
                if any(t in n for t in WINDSURF_NAMES):
                    pid = p.info["pid"]
                    os.system(f"renice -n -10 -p {pid} >/dev/null 2>&1")
                    if self.is_as: os.system(f"taskpolicy -d user_interactive -p {pid} >/dev/null 2>&1")
                    out.append(f"boosted {n}({pid})")
            except (psutil.NoSuchProcess, psutil.AccessDenied): pass
        _run('defaults write com.exafunction.windsurf "crashes.reportUnhandledExceptions" -bool false')
        return out

    def full(self):
        return self.ram() + self.cpu() + self.gpu() + self.windsurf()


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


class NeomorphicPanel:
    def __init__(self, app):
        self.app = app
        self.opt = Optimizer(log_cb=self._log)
        self.ollama = OllamaClient()
        self.models = []
        self._build()

    def _build(self):
        frame = NSMakeRect(100, 100, 560, 780)
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
        self.effect.layer().setCornerRadius_(16)
        self.effect.layer().setMasksToBounds_(True)
        self.win.contentView().addSubview_(self.effect)

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

    def _add_stats(self):
        labels = [("RAM", 20), ("CPU", 200), ("GPU", 380)]
        self.stat_fields = {}
        for name, x in labels:
            self.effect.addSubview_(self._mk_label(name, NSMakeRect(x, 710, 160, 20), 10, DIM_COLOR))
            tf = self._mk_label("—", NSMakeRect(x, 670, 160, 36), 22, TEXT_COLOR, True)
            self.effect.addSubview_(tf)
            self.stat_fields[name] = tf
        chip = SystemInfo.chip()
        if chip:
            self.effect.addSubview_(self._mk_label(chip, NSMakeRect(20, 650, 520, 16), 9, DIM_COLOR))

    def _add_buttons(self):
        actions = [("RAM", 20), ("CPU", 148), ("GPU", 276), ("WS", 404)]
        for label, x in actions:
            btn = NSButton.alloc().initWithFrame_(NSMakeRect(x, 590, 115, 36))
            btn.setTitle_(label)
            btn.setBezelStyle_(NSBezelStyleRounded)
            btn.setFont_(NSFont.systemFontOfSize_weight_(11, 0.4))
            btn.setTarget_(self)
            btn.setAction_(f"opt_{label.lower()}:")
            self.effect.addSubview_(btn)
        full = NSButton.alloc().initWithFrame_(NSMakeRect(20, 540, 500, 42))
        full.setTitle_("FULL SYSTEM OPTIMIZE")
        full.setBezelStyle_(NSBezelStyleRounded)
        full.setFont_(NSFont.systemFontOfSize_weight_(12, 0.5))
        full.setTarget_(self)
        full.setAction_("opt_full:")
        self.effect.addSubview_(full)

    def _add_log(self):
        scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(20, 310, 520, 220))
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
        self.effect.addSubview_(self._mk_label("Ollama LLM", NSMakeRect(20, 280, 520, 16), 10, DIM_COLOR))
        self.model_btn = NSButton.alloc().initWithFrame_(NSMakeRect(20, 245, 200, 26))
        self.model_btn.setTitle_("Loading models…")
        self.model_btn.setBezelStyle_(NSBezelStyleRounded)
        self.model_btn.setFont_(NSFont.systemFontOfSize_(10))
        self.model_btn.setTarget_(self)
        self.model_btn.setAction_("cycle_model:")
        self.effect.addSubview_(self.model_btn)

        scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(20, 80, 520, 155))
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

        self.entry = NSTextField.alloc().initWithFrame_(NSMakeRect(20, 40, 420, 28))
        self.entry.setFont_(NSFont.systemFontOfSize_(11))
        self.entry.setTextColor_(TEXT_COLOR)
        self.entry.setBackgroundColor_(CARD_COLOR)
        self.entry.setBezeled_(True)
        self.entry.setBezelStyle_(NSRoundedBezelStyle)
        self.entry.setTarget_(self)
        self.entry.setAction_("send_chat:")
        self.effect.addSubview_(self.entry)

        send = NSButton.alloc().initWithFrame_(NSMakeRect(450, 38, 90, 30))
        send.setTitle_("Send")
        send.setBezelStyle_(NSBezelStyleRounded)
        send.setFont_(NSFont.systemFontOfSize_weight_(11, 0.4))
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
                    self.stat_fields["GPU"].setStringValue_(f"{gpu['pressure']:.0f}%")
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
        lines = s.split("\n")
        # Remove last line (the pending one) and append new
        new = "\n".join(lines[:-2]) + "\n" + text if len(lines) >= 2 else text
        store.setAttributedString_(
            NSAttributedString.alloc().initWithString_attributes_(
                new, {NSFontAttributeName: NSFont.systemFontOfSize_(10),
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

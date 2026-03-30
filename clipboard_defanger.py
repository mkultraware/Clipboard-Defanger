import re
import json
import threading
import tkinter as tk
import winreg
import logging
import os
import sys
import ctypes
import ctypes.wintypes
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import win32clipboard
import win32con
import win32gui
import win32api
import pystray
from PIL import Image, ImageDraw

APP_NAME    = "Sekura PasteGuard"
LOG_FILE    = os.path.join(os.path.expanduser("~"), "pasteguard.log")
CONFIG_FILE = os.path.join(os.path.expanduser("~"), "pasteguard.json")

DEFAULT_STATE = {
    "silent_mode": False,
    "notifications": True,
    "stats": {"blocked": 0, "cleaned": 0},
}

# --- Persistence ---

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            saved = json.load(f)
        config = DEFAULT_STATE.copy()
        config["silent_mode"]      = saved.get("silent_mode", DEFAULT_STATE["silent_mode"])
        config["notifications"]    = saved.get("notifications", DEFAULT_STATE["notifications"])
        config["stats"]["blocked"] = saved.get("stats", {}).get("blocked", 0)
        config["stats"]["cleaned"] = saved.get("stats", {}).get("cleaned", 0)
        return config
    except Exception:
        return DEFAULT_STATE.copy()

def save_config():
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump({
                "silent_mode":   state["silent_mode"],
                "notifications": state["notifications"],
                "stats":         state["stats"],
            }, f, indent=2)
    except Exception as e:
        log(f"Config save failed: {e}", "warning")

_saved = load_config()
state = {
    **_saved,
    "recent_value": "",
    "icon":         None,
    "whitelist":    set(),  # session-only, cleared on restart
}

# --- Logging ---

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def log(msg, level="info"):
    print(msg)
    getattr(logging, level)(msg)

# --- Tracking params ---

TRACKING_PARAMS_SET = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "dclid", "gbraid", "wbraid",
    "ttclid", "igshid", "twclid", "msclkid", "yclid",
    "li_fat_id", "trk", "lipi", "mc_eid", "_ga",
    "si", "ref", "ref_",
}

# --- Detection ---
#
# Tier 1: structurally unambiguous patterns, fire standalone.
# Tier 2: tool name + shell signal required, prevents false positives
#         when tool names appear in prose or documentation.

TIER1_PATTERNS = [
    (r"cmd(?:\.exe)?\s*/[cCkK]",                                "CMD /c"),
    (r"powershell(?:\.exe)?\s+-\w",                             "PowerShell"),
    (r"-enc(?:odedcommand)?\s+[A-Za-z0-9+/=]{20,}",            "Encoded PowerShell command"),
    (r"Invoke-WebRequest|iwr\s+https?://",                      "Invoke-WebRequest"),
    (r"Invoke-RestMethod|irm\s+https?://",                      "Invoke-RestMethod"),
    (r"\biex\b|Invoke-Expression",                              "Invoke-Expression"),
    (r"DownloadString|DownloadFile",                            "WebClient download"),
    (r"&\s*\(\s*\$",                                            "Dynamic invocation"),
    (r"curl\s+https?://",                                       "curl download"),
    (r"reg\s+add\s+HKEY",                                       "Registry write"),
    (r"bash\s+-c\s+[\"'$\{]",                                   "Bash (WSL)"),
    (r"(?:powershell|mshta|cmd|wscript|cscript|rundll32)[^\n]{0,60}[A-Za-z0-9+/]{60,}={0,2}",
                                                                "Base64 payload"),
]

_SHELL_TOOLS = r"(?:mshta|msiexec|rundll32|certutil|wscript|cscript|wmic|regsvr32|bitsadmin|schtasks|powershell|cmd)"
_SHELL_SIGNAL = (
    r"(?:"
    r"\s*[|&;]\s*"
    r"|\s+https?://"
    r"|\s+-\w"
    r"|\s+//?\w"
    r"|\s+\$\w"
    r"|\s+vbscript:"
    r"|\s+javascript:"
    r"|\s+\S+\.(?:dll|vbs|js|hta|bat|ps1|cmd|exe)\b"
    r")"
)

COMPILED_TIER1 = [(re.compile(p, re.IGNORECASE), l) for p, l in TIER1_PATTERNS]
COMPILED_TIER2 = re.compile(_SHELL_TOOLS + r"(?:\.exe)?" + _SHELL_SIGNAL, re.IGNORECASE)

def detect_command(text):
    for pattern, label in COMPILED_TIER1:
        if pattern.search(text):
            return True, label
    m = COMPILED_TIER2.search(text)
    if m:
        return True, f"Shell command ({m.group(0).strip()[:40]})"
    return False, None

# --- URL cleaning ---

def clean_url(text):
    text = text.strip()
    if not (text.startswith("http://") or text.startswith("https://")):
        return None
    try:
        parsed = urlparse(text)
        params = parse_qs(parsed.query, keep_blank_values=True)
        cleaned_params = {k: v for k, v in params.items() if k not in TRACKING_PARAMS_SET}
        new_query = urlencode(cleaned_params, doseq=True)
        cleaned = urlunparse(parsed._replace(query=new_query))
        return cleaned if cleaned != text else None
    except Exception:
        return None

# --- Notifications ---

def notify_tray(title, message):
    if not state["notifications"]:
        return
    try:
        if state["icon"]:
            state["icon"].notify(message, title)
    except Exception:
        log(f"[NOTIFY] {title}: {message}")

# --- System theme ---

def is_dark_mode():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return value == 0
    except Exception:
        return True  # default to dark

# --- Windows 11 rounded corners ---

def apply_rounded_corners(hwnd):
    try:
        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        DWMWCP_ROUND = 2
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(ctypes.c_int(DWMWCP_ROUND)),
            ctypes.sizeof(ctypes.c_int)
        )
    except Exception:
        pass

# --- Warning dialog ---

def show_warning_dialog(payload_text, trigger_label):
    """Returns: 'cancel' | 'keep' | 'whitelist'"""
    dark = is_dark_mode()

    # Colors based on system theme
    if dark:
        bg          = "#1c1c1e"
        surface     = "#2c2c2e"
        text_pri    = "#ffffff"
        text_sec    = "#ababab"
        text_dim    = "#636366"
        accent      = "#f0a500"
        btn_cancel  = "#3a3a3c"
        btn_cancel_fg = "#ffffff"
        btn_keep    = "#2c2c2e"
        btn_keep_fg = "#ababab"
        btn_trust   = "#1c3a1c"
        btn_trust_fg = "#4cd964"
        border      = "#3a3a3c"
    else:
        bg          = "#f2f2f7"
        surface     = "#ffffff"
        text_pri    = "#000000"
        text_sec    = "#3c3c43"
        text_dim    = "#8e8e93"
        accent      = "#c07800"
        btn_cancel  = "#e5e5ea"
        btn_cancel_fg = "#000000"
        btn_keep    = "#e5e5ea"
        btn_keep_fg = "#3c3c43"
        btn_trust   = "#d4edda"
        btn_trust_fg = "#1a7a2e"
        border      = "#d1d1d6"

    # Flash fix: invisible root, never shown
    root = tk.Tk()
    root.geometry("0x0+0+0")
    root.attributes("-alpha", 0)
    root.withdraw()

    dialog = tk.Toplevel(root)
    dialog.title("")
    dialog.geometry("480x310")
    dialog.resizable(False, False)
    dialog.attributes("-topmost", True)
    dialog.configure(bg=bg)
    dialog.overrideredirect(False)

    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth()  // 2) - 240
    y = (dialog.winfo_screenheight() // 2) - 155
    dialog.geometry(f"+{x}+{y}")

    # Apply Windows 11 rounded corners
    dialog.update()
    hwnd = ctypes.windll.user32.GetParent(dialog.winfo_id())
    if hwnd == 0:
        hwnd = dialog.winfo_id()
    apply_rounded_corners(hwnd)

    result = {"action": "cancel"}

    # App label
    tk.Label(dialog, text="Sekura PasteGuard",
             font=("Segoe UI", 9), fg=text_dim, bg=bg).pack(pady=(20, 0))

    # Title
    tk.Label(dialog, text="Suspicious command detected",
             font=("Segoe UI", 14, "bold"), fg=text_pri, bg=bg).pack(pady=(4, 0))

    # Trigger label
    tk.Label(dialog, text=f"Triggered by: {trigger_label}",
             font=("Segoe UI", 9), fg=accent, bg=bg).pack(pady=(4, 0))

    # Divider
    tk.Frame(dialog, height=1, bg=border).pack(fill="x", padx=24, pady=(12, 0))

    # Snippet
    snippet = payload_text[:120].replace("\n", " ").replace("\r", "")
    if len(payload_text) > 120:
        snippet += "..."
    tk.Label(dialog, text=snippet,
             font=("Cascadia Code", 8) if True else ("Courier New", 8),
             fg=text_sec, bg=surface,
             wraplength=420, justify="left", anchor="w",
             padx=12, pady=8).pack(fill="x", padx=24, pady=(12, 0))

    # Subtext
    tk.Label(dialog,
             text="Only proceed if you know exactly what this command does.",
             font=("Segoe UI", 8), fg=text_dim, bg=bg,
             wraplength=420).pack(pady=(10, 0))

    # Divider
    tk.Frame(dialog, height=1, bg=border).pack(fill="x", padx=24, pady=(12, 0))

    # Buttons
    btn_frame = tk.Frame(dialog, bg=bg)
    btn_frame.pack(pady=(10, 0))

    def on_cancel():
        result["action"] = "cancel"
        dialog.destroy()
        root.destroy()

    def on_keep():
        result["action"] = "keep"
        dialog.destroy()
        root.destroy()

    def on_whitelist():
        result["action"] = "whitelist"
        dialog.destroy()
        root.destroy()

    btn_cfg = {"relief": "flat", "padx": 16, "pady": 6, "cursor": "hand2", "bd": 0}

    tk.Button(btn_frame, text="Clear Clipboard", command=on_cancel,
              font=("Segoe UI", 9, "bold"),
              bg="#c0392b", fg="#ffffff",
              activebackground="#a93226", activeforeground="#ffffff",
              **btn_cfg).pack(side="left", padx=(0, 8))

    tk.Button(btn_frame, text="Copy Anyway", command=on_keep,
              font=("Segoe UI", 9),
              bg=btn_keep, fg=btn_keep_fg,
              activebackground=border, activeforeground=text_pri,
              **btn_cfg).pack(side="left", padx=(0, 8))

    tk.Button(btn_frame, text="Trust This Session", command=on_whitelist,
              font=("Segoe UI", 9),
              bg=btn_trust, fg=btn_trust_fg,
              activebackground=btn_trust, activeforeground=btn_trust_fg,
              **btn_cfg).pack(side="left")

    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    dialog.grab_set()
    root.wait_window(dialog)

    return result["action"]

# --- Clipboard I/O ---

def get_clipboard_text():
    try:
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        elif win32clipboard.IsClipboardFormatAvailable(win32con.CF_TEXT):
            data = win32clipboard.GetClipboardData(win32con.CF_TEXT).decode("utf-8", errors="replace")
        else:
            data = None
        win32clipboard.CloseClipboard()
        return data
    except Exception:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass
        return None

def clear_clipboard():
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.CloseClipboard()
    except Exception:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass

def set_clipboard_text(text):
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
        win32clipboard.CloseClipboard()
    except Exception:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass

# --- Clipboard processing ---

def process_clipboard(text):
    if text == state["recent_value"]:
        return
    state["recent_value"] = text

    is_cmd, label = detect_command(text)

    if is_cmd:
        if label in state["whitelist"]:
            log(f"Whitelisted pattern skipped [{label}]")
            return

        log(f"Command detected [{label}]: {text[:100]!r}")

        if state["silent_mode"]:
            clear_clipboard()
            state["recent_value"] = ""
            state["stats"]["blocked"] += 1
            save_config()
            update_tray_menu()
            log("Silently cleared.")
        else:
            action = show_warning_dialog(text, label)
            if action == "cancel":
                clear_clipboard()
                state["recent_value"] = ""
                state["stats"]["blocked"] += 1
                save_config()
                update_tray_menu()
                log("User cancelled. Clipboard cleared.")
            elif action == "whitelist":
                state["whitelist"].add(label)
                log(f"Pattern whitelisted for session: {label}")
            else:
                log("User chose to keep command in clipboard.")
    else:
        cleaned = clean_url(text)
        if cleaned:
            set_clipboard_text(cleaned)
            state["recent_value"] = cleaned
            state["stats"]["cleaned"] += 1
            save_config()
            update_tray_menu()
            log(f"URL cleaned -> {cleaned}")
            notify_tray("URL Cleaned", "Tracking parameters removed.")

# --- Clipboard listener (event-driven via WM_CLIPBOARDUPDATE) ---

WM_CLIPBOARDUPDATE = 0x031D

def clipboard_wnd_proc(hwnd, msg, wparam, lparam):
    if msg == WM_CLIPBOARDUPDATE:
        text = get_clipboard_text()
        if text:
            threading.Thread(target=process_clipboard, args=(text,), daemon=True).start()
    elif msg == win32con.WM_DESTROY:
        win32gui.PostQuitMessage(0)
    return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

def run_clipboard_listener():
    wc = win32gui.WNDCLASS()
    wc.lpfnWndProc   = clipboard_wnd_proc
    wc.lpszClassName = "PasteGuardListener"
    wc.hInstance     = win32api.GetModuleHandle(None)
    win32gui.RegisterClass(wc)

    hwnd = win32gui.CreateWindow(
        wc.lpszClassName, "PasteGuard Listener",
        0, 0, 0, 0, 0, win32con.HWND_MESSAGE, 0, wc.hInstance, None
    )

    ctypes.windll.user32.AddClipboardFormatListener(hwnd)
    log("Clipboard listener active.")
    win32gui.PumpMessages()

# --- Tray ---

def resource_path(filename):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, filename)

def create_icon_image():
    try:
        return Image.open(resource_path("clipboard-x.512.ico"))
    except Exception:
        img = Image.new("RGB", (64, 64), "#1a1a2e")
        dc  = ImageDraw.Draw(img)
        dc.rectangle((16, 16, 48, 48), fill="#f0a500")
        return img

def toggle_silent_mode(icon, item):
    state["silent_mode"] = not state["silent_mode"]
    save_config()
    log(f"Silent mode: {'ON' if state['silent_mode'] else 'OFF'}")
    icon.update_menu()

def toggle_notifications(icon, item):
    state["notifications"] = not state["notifications"]
    save_config()
    log(f"Notifications: {'ON' if state['notifications'] else 'OFF'}")
    icon.update_menu()

def open_log(icon, item):
    os.startfile(LOG_FILE)

def on_quit(icon, item):
    save_config()
    icon.stop()

def build_menu():
    blocked = state["stats"]["blocked"]
    cleaned = state["stats"]["cleaned"]
    return pystray.Menu(
        pystray.MenuItem(f"🛡 Blocked: {blocked}   🔗 Cleaned: {cleaned}", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            lambda item: f"Silent Mode: {'ON' if state['silent_mode'] else 'OFF'}",
            toggle_silent_mode
        ),
        pystray.MenuItem(
            lambda item: f"Notifications: {'ON' if state['notifications'] else 'OFF'}",
            toggle_notifications
        ),
        pystray.MenuItem("View Log", open_log),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", on_quit),
    )

def update_tray_menu():
    if state["icon"]:
        state["icon"].menu = build_menu()
        state["icon"].update_menu()

def main():
    icon_image    = create_icon_image()
    icon          = pystray.Icon(APP_NAME, icon_image, APP_NAME, build_menu())
    state["icon"] = icon

    threading.Thread(target=run_clipboard_listener, daemon=True).start()
    icon.run()

if __name__ == "__main__":
    main()

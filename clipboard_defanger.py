import re
import threading
import tkinter as tk
import logging
import os
import ctypes
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import win32clipboard
import win32con
import win32gui
import win32api
import pystray
from PIL import Image, ImageDraw

# ==========================================
# CONFIGURATION
# ==========================================
APP_NAME = "Sekura PasteGuard"
LOG_FILE = os.path.join(os.path.expanduser("~"), "pasteguard.log")

state = {
    "silent_mode": False,
    "notifications": True,
    "recent_value": "",
    "icon": None,
}

# ==========================================
# LOGGING
# ==========================================
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def log(msg, level="info"):
    print(msg)
    getattr(logging, level)(msg)

# ==========================================
# TRACKING PARAMS
# ==========================================
TRACKING_PARAMS_SET = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "dclid", "gbraid", "wbraid",
    "ttclid", "igshid", "twclid", "msclkid", "yclid",
    "li_fat_id", "trk", "lipi",
    "mc_eid", "_ga",
    "si", "ref", "ref_"
}

# ==========================================
# COMMAND PATTERNS
# Each tuple: (regex, human-readable label)
# ==========================================
COMMAND_PATTERNS = [
    (r"powershell(?:\.exe)?",                                   "PowerShell"),
    (r"-enc(?:odedcommand)?\s+[A-Za-z0-9+/=]{20,}",            "Encoded PowerShell command"),
    (r"cmd(?:\.exe)?\s*/[cCkK]",                                "CMD /c"),
    (r"mshta(?:\.exe)?",                                        "MSHTA"),
    (r"msiexec(?:\.exe)?",                                      "MSIExec"),
    (r"rundll32(?:\.exe)?",                                     "RunDLL32"),
    (r"certutil(?:\.exe)?",                                     "CertUtil"),
    (r"wscript(?:\.exe)?",                                      "WScript"),
    (r"cscript(?:\.exe)?",                                      "CScript"),
    (r"wmic(?:\.exe)?",                                         "WMIC"),
    (r"regsvr32(?:\.exe)?",                                     "RegSvr32"),
    (r"bitsadmin(?:\.exe)?",                                    "BITSAdmin"),
    (r"schtasks(?:\.exe)?",                                     "SchTasks"),
    (r"reg\s+add",                                              "Registry write"),
    (r"curl\s+https?://",                                       "curl download"),
    (r"Invoke-WebRequest|iwr\s+https?://",                      "Invoke-WebRequest"),
    (r"Invoke-RestMethod|irm\s+https?://",                      "Invoke-RestMethod"),
    (r"Start-Process",                                          "Start-Process"),
    (r"DownloadString|DownloadFile",                            "WebClient download"),
    (r"bash\s+-c\b",                                            "Bash (WSL)"),
    # Context-aware base64: only flags when adjacent to a known executor
    (r"(?:powershell|mshta|cmd|wscript|cscript|rundll32)"
     r"[^\n]{0,60}[A-Za-z0-9+/]{60,}={0,2}",                   "Base64 payload"),
]

COMPILED_PATTERNS = [
    (re.compile(pattern, re.IGNORECASE), label)
    for pattern, label in COMMAND_PATTERNS
]

# ==========================================
# DETECTION
# ==========================================

def detect_command(text):
    for pattern, label in COMPILED_PATTERNS:
        if pattern.search(text):
            return True, label
    return False, None

# ==========================================
# URL CLEANING
# ==========================================

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

# ==========================================
# TRAY NOTIFICATION
# ==========================================

def notify_tray(title, message):
    if not state["notifications"]:
        return
    try:
        if state["icon"]:
            state["icon"].notify(message, title)
    except Exception:
        log(f"[NOTIFY] {title}: {message}")

# ==========================================
# WARNING DIALOG
# ==========================================

def show_warning_dialog(payload_text, trigger_label):
    root = tk.Tk()
    root.withdraw()

    dialog = tk.Toplevel(root)
    dialog.title("PasteGuard Warning")
    dialog.geometry("520x300")
    dialog.resizable(False, False)
    dialog.attributes("-topmost", True)
    dialog.configure(bg="#1a1a1a")

    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - 260
    y = (dialog.winfo_screenheight() // 2) - 150
    dialog.geometry(f"+{x}+{y}")

    result = {"keep": False}

    tk.Label(
        dialog,
        text="⚠  Windows Command Detected",
        font=("Segoe UI", 13, "bold"),
        fg="#f0a500",
        bg="#1a1a1a"
    ).pack(pady=(18, 4))

    tk.Label(
        dialog,
        text=(
            "You have copied what appears to be a Windows command.\n"
            "Many sites use this as a fake CAPTCHA to deliver malware.\n\n"
            "Only proceed if you know exactly what this command does."
        ),
        font=("Segoe UI", 9),
        fg="#cccccc",
        bg="#1a1a1a",
        justify="center",
        wraplength=480
    ).pack(pady=(0, 6))

    tk.Label(
        dialog,
        text=f"Triggered by: {trigger_label}",
        font=("Segoe UI", 9, "italic"),
        fg="#f0a500",
        bg="#1a1a1a"
    ).pack(pady=(0, 6))

    snippet = payload_text[:140].replace("\n", " ").replace("\r", "")
    if len(payload_text) > 140:
        snippet += "..."
    tk.Label(
        dialog,
        text=snippet,
        font=("Courier New", 8),
        fg="#777777",
        bg="#111111",
        wraplength=480,
        justify="left",
        anchor="w",
        padx=8,
        pady=6
    ).pack(fill="x", padx=16, pady=(0, 14))

    btn_frame = tk.Frame(dialog, bg="#1a1a1a")
    btn_frame.pack()

    def on_cancel():
        result["keep"] = False
        dialog.destroy()
        root.destroy()

    def on_keep():
        result["keep"] = True
        dialog.destroy()
        root.destroy()

    tk.Button(
        btn_frame,
        text="Cancel (Clear Clipboard)",
        command=on_cancel,
        font=("Segoe UI", 9, "bold"),
        bg="#c0392b",
        fg="white",
        relief="flat",
        padx=14,
        pady=6,
        cursor="hand2"
    ).pack(side="left", padx=(0, 10))

    tk.Button(
        btn_frame,
        text="Copy Anyway",
        command=on_keep,
        font=("Segoe UI", 9),
        bg="#2d2d2d",
        fg="#aaaaaa",
        relief="flat",
        padx=14,
        pady=6,
        cursor="hand2"
    ).pack(side="left")

    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    dialog.grab_set()
    root.wait_window(dialog)

    return result["keep"]

# ==========================================
# CLIPBOARD READ/WRITE
# ==========================================

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

# ==========================================
# CLIPBOARD PROCESSING
# ==========================================

def process_clipboard(text):
    if text == state["recent_value"]:
        return
    state["recent_value"] = text

    is_cmd, label = detect_command(text)

    if is_cmd:
        log(f"Command detected [{label}]: {text[:100]!r}")
        if state["silent_mode"]:
            clear_clipboard()
            state["recent_value"] = ""
            log("Silently cleared.")
        else:
            keep = show_warning_dialog(text, label)
            if not keep:
                clear_clipboard()
                state["recent_value"] = ""
                log("User cancelled. Clipboard cleared.")
            else:
                log("User chose to keep command in clipboard.")
    else:
        cleaned = clean_url(text)
        if cleaned:
            set_clipboard_text(cleaned)
            state["recent_value"] = cleaned
            log(f"URL cleaned -> {cleaned}")
            notify_tray("URL Cleaned", "Tracking parameters removed.")

# ==========================================
# EVENT-DRIVEN CLIPBOARD LISTENER
# ==========================================

WM_CLIPBOARDUPDATE = 0x031D

def clipboard_wnd_proc(hwnd, msg, wparam, lparam):
    if msg == WM_CLIPBOARDUPDATE:
        text = get_clipboard_text()
        if text:
            threading.Thread(
                target=process_clipboard,
                args=(text,),
                daemon=True
            ).start()
    elif msg == win32con.WM_DESTROY:
        win32gui.PostQuitMessage(0)
    return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

def run_clipboard_listener():
    wc = win32gui.WNDCLASS()
    wc.lpfnWndProc = clipboard_wnd_proc
    wc.lpszClassName = "PasteGuardListener"
    wc.hInstance = win32api.GetModuleHandle(None)
    win32gui.RegisterClass(wc)

    hwnd = win32gui.CreateWindow(
        wc.lpszClassName,
        "PasteGuard Listener",
        0, 0, 0, 0, 0,
        win32con.HWND_MESSAGE,
        0, wc.hInstance, None
    )

    ctypes.windll.user32.AddClipboardFormatListener(hwnd)
    log("Event-driven clipboard listener active.")
    win32gui.PumpMessages()

# ==========================================
# TRAY ICON
# ==========================================

def resource_path(filename):
    """Get path to resource, works for both script and PyInstaller bundle."""
    import sys
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, filename)

def create_icon_image():
    try:
        return Image.open(resource_path("clipboard-x.512.ico"))
    except Exception:
        image = Image.new("RGB", (64, 64), "#1a1a2e")
        dc = ImageDraw.Draw(image)
        dc.rectangle((16, 16, 48, 48), fill="#f0a500")
        return image

def toggle_silent_mode(icon, item):
    state["silent_mode"] = not state["silent_mode"]
    log(f"Silent mode: {'ON' if state['silent_mode'] else 'OFF'}")
    icon.update_menu()

def toggle_notifications(icon, item):
    state["notifications"] = not state["notifications"]
    log(f"Notifications: {'ON' if state['notifications'] else 'OFF'}")
    icon.update_menu()

def open_log(icon, item):
    os.startfile(LOG_FILE)

def on_quit(icon, item):
    icon.stop()

def build_menu():
    return pystray.Menu(
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

def main():
    icon_image = create_icon_image()
    icon = pystray.Icon(APP_NAME, icon_image, APP_NAME, build_menu())
    state["icon"] = icon

    listener_thread = threading.Thread(target=run_clipboard_listener, daemon=True)
    listener_thread.start()

    icon.run()

if __name__ == "__main__":
    main()

import time
import re
import threading
import tkinter as tk
from tkinter import messagebox
import pyperclip
import pystray
from PIL import Image, ImageDraw

# ==========================================
# CONFIGURATION
# ==========================================
APP_NAME = "Sekura PasteGuard"
CHECK_INTERVAL = 0.5

# Set to True to silently kill commands instead of warning
SILENT_MODE = False

TRACKING_PARAMS = [
    # UTM standard
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    # Social platforms
    "fbclid",       # Facebook
    "gclid",        # Google Ads
    "dclid",        # DoubleClick / Google Display
    "gbraid",       # Google (iOS privacy)
    "wbraid",       # Google (iOS privacy)
    "ttclid",       # TikTok
    "igshid",       # Instagram
    "twclid",       # Twitter/X
    "msclkid",      # Microsoft / Bing Ads
    "yclid",        # Yandex
    # LinkedIn
    "li_fat_id",
    "trk",
    "lipi",
    # Email
    "mc_eid",       # Mailchimp
    # Google Analytics
    "_ga",
    # Generic
    "si", "ref", "ref_"
]

# Patterns that indicate a shell command payload
# Covers all documented ClickFix / paste-and-run vectors as of 2026
COMMAND_PATTERNS = [
    r"powershell",
    r"powershell\.exe",
    r"-enc\s+[A-Za-z0-9+/=]{20,}",       # Base64 encoded PS command
    r"-encodedcommand",
    r"cmd\s*/c",
    r"cmd\.exe",
    r"mshta",
    r"msiexec",
    r"rundll32",
    r"certutil",
    r"wscript",
    r"cscript",
    r"reg\s+add",
    r"curl\s+http",
    r"Invoke-WebRequest",
    r"iwr\s+http",
    r"Start-Process",
    r"DownloadString",
    r"DownloadFile",
    r"[A-Za-z0-9+/]{100,}={0,2}",        # Raw base64 blob (100+ chars)
]

COMPILED_COMMAND_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in COMMAND_PATTERNS
]

# ==========================================
# LOGIC
# ==========================================

def is_command_payload(text):
    for pattern in COMPILED_COMMAND_PATTERNS:
        if pattern.search(text):
            return True
    return False

def clean_url(text):
    if not (text.startswith("http://") or text.startswith("https://")):
        return None

    original_text = text

    for param in TRACKING_PARAMS:
        pattern = r"[\?&]" + param + r"=[^&\s]*"
        text = re.sub(pattern, "", text)

    text = text.rstrip("?&")

    if text != original_text:
        return text
    return None

def show_warning_dialog(payload_text):
    """
    Shows a warning dialog when a command is detected in clipboard.
    Returns True if user chose to keep it, False if they cancelled.
    """
    root = tk.Tk()
    root.withdraw()  # Hide the root window

    # Custom dialog
    dialog = tk.Toplevel(root)
    dialog.title("⚠ Clipboard Defanger Warning")
    dialog.geometry("480x220")
    dialog.resizable(False, False)
    dialog.attributes("-topmost", True)
    dialog.configure(bg="#1a1a1a")

    # Center on screen
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - 240
    y = (dialog.winfo_screenheight() // 2) - 110
    dialog.geometry(f"+{x}+{y}")

    result = {"keep": False}

    # Warning icon + title
    tk.Label(
        dialog,
        text="⚠  Windows Command Detected",
        font=("Segoe UI", 13, "bold"),
        fg="#f0a500",
        bg="#1a1a1a"
    ).pack(pady=(18, 4))

    # Message
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
        wraplength=440
    ).pack(pady=(0, 16))

    # Buttons
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

def clipboard_monitor():
    recent_value = ""
    print("--- MONITOR ACTIVE: Waiting for clipboard changes... ---")

    while True:
        try:
            current_value = pyperclip.paste()

            if current_value != recent_value:
                recent_value = current_value

                # Check for command payload first
                if is_command_payload(current_value):
                    if SILENT_MODE:
                        print("Command payload detected. Clearing clipboard silently.")
                        pyperclip.copy("")
                        recent_value = ""
                    else:
                        print("Command payload detected. Showing warning...")
                        keep = show_warning_dialog(current_value)
                        if not keep:
                            print("User cancelled. Clipboard cleared.")
                            pyperclip.copy("")
                            recent_value = ""
                        else:
                            print("User chose to keep command in clipboard.")

                # Otherwise check for tracking URLs
                else:
                    cleaned = clean_url(current_value)
                    if cleaned:
                        print(f"Cleaning URL...")
                        pyperclip.copy(cleaned)
                        recent_value = cleaned
                        print(f"SUCCESS -> {cleaned}")

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(CHECK_INTERVAL)

# ==========================================
# GUI
# ==========================================

def create_icon_image():
    try:
        return Image.open("clipboard-x.512.ico")
    except Exception:
        # Fallback if icon file is missing
        image = Image.new('RGB', (64, 64), "green")
        dc = ImageDraw.Draw(image)
        dc.rectangle((16, 16, 48, 48), fill="white")
        return image

def on_quit(icon, item):
    icon.stop()

def main():
    icon_image = create_icon_image()
    menu = pystray.Menu(pystray.MenuItem("Quit", on_quit))
    icon = pystray.Icon(APP_NAME, icon_image, APP_NAME, menu)

    monitor_thread = threading.Thread(target=clipboard_monitor)
    monitor_thread.daemon = True
    monitor_thread.start()

    icon.run()

if __name__ == "__main__":
    main()

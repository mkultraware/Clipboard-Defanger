import time
import re
import threading
import pyperclip
import pystray
from PIL import Image, ImageDraw

# ==========================================
# CONFIGURATION
# ==========================================
APP_NAME = "Clipboard Defanger"
CHECK_INTERVAL = 0.5  # Faster check (0.5s) for better responsiveness

TRACKING_PARAMS = [
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "si", "ref", "ref_"
]

# ==========================================
# LOGIC
# ==========================================

def clean_url(text):
    if not (text.startswith("http://") or text.startswith("https://")):
        return None

    original_text = text
    
    for param in TRACKING_PARAMS:
        # Regex: Look for ?param=... or &param=...
        pattern = r"[\?&]" + param + r"=[^&\s]*"
        text = re.sub(pattern, "", text)

    text = text.rstrip("?&")
    
    if text != original_text:
        return text
    return None

def clipboard_monitor():
    """
    Runs forever in the background.
    """
    recent_value = ""
    print("--- MONITOR ACTIVE: Waiting for links... ---")
    
    # CHANGED: Comments removed by author
    # Comments removed by author
    while True:
        try:
            current_value = pyperclip.paste()
            
            if current_value != recent_value:
                recent_value = current_value # Update memory immediately
                
                cleaned = clean_url(current_value)
                
                if cleaned:
                    print(f"Cleaning URL...")
                    pyperclip.copy(cleaned)
                    recent_value = cleaned # Update memory to match new clean version
                    print(f"SUCCESS -> {cleaned}")
            
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(CHECK_INTERVAL)

# ==========================================
# GUI
# ==========================================

def create_icon_image():
    # 64x64 Green Square
    width = 64
    height = 64
    color = "green"
    image = Image.new('RGB', (width, height), color)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 4, height // 4, width * 3 // 4, height * 3 // 4), fill="white")
    return image

def on_quit(icon, item):
    icon.stop()

def main():
    icon_image = create_icon_image()
    menu = pystray.Menu(pystray.MenuItem("Quit", on_quit))
    
    icon = pystray.Icon(APP_NAME, icon_image, APP_NAME, menu)
    
    # Run monitor in background
    monitor_thread = threading.Thread(target=clipboard_monitor)
    monitor_thread.daemon = True # This kills the thread when the main program exits
    monitor_thread.start()
    
    # Run icon (this blocks the script from closing)
    icon.run()

if __name__ == "__main__":
    main()
# Sekura PasteGuard 🛡️
A lightweight Windows utility that protects you from clipboard-based attacks and tracking.

## What is it?
PasteGuard runs silently in your system tray and monitors your clipboard in real time.

It does two things:

**1. ClickFix Protection**
Attackers use fake CAPTCHAs and error pages to trick you into copying and running malicious commands. The moment PasteGuard detects a shell command in your clipboard, it warns you before you can paste and run it.

**2. Tracking Parameter Removal**
When you copy a link from Amazon, Facebook, TikTok, LinkedIn, and others, they attach tracking parameters to spy on your clicks. PasteGuard strips them instantly so you always paste a clean URL.

## Download
[**Download the latest installer here**](https://github.com/mkultraware/Clipboard-Defanger/releases)

## ✨ Features
- **ClickFix Detection:** Warns you when a Windows shell command is copied, with Clear Clipboard, Copy Anyway, and Trust This Session options
- **Session Whitelist:** Trust a pattern for the current session — no more repeated warnings for the same trigger
- **Silent Mode:** Kills command payloads instantly without prompting — toggle from the tray, no source editing required
- **Notifications:** Tray notifications on URL cleans, toggleable from the tray menu
- **Tracking Removal:** Strips 20+ tracking parameters including UTM, fbclid, ttclid, LinkedIn trk, msclkid, and more
- **Stats:** Blocked threats and cleaned URLs shown in the tray menu, persisted across restarts
- **Persistent Settings:** Silent Mode and notification preferences survive restarts
- **System Theme:** Dialog follows Windows light/dark mode automatically
- **Zero-Click:** Works automatically in the background
- **Lightweight:** Uses minimal RAM (<20MB)
- **Auto-Start:** Runs on Windows startup via the installer

## 🔍 What Commands Does It Detect?
PasteGuard uses a two-tier detection engine to catch real payloads while ignoring tool names in normal text.

**Tier 1 — unambiguous patterns (fire standalone):**
`powershell -flag`, `cmd /c`, `Invoke-WebRequest`, `Invoke-RestMethod`, `iex`, `Invoke-Expression`, `DownloadString`, `DownloadFile`, `curl https://`, `reg add HKEY`, `bash -c "..."`, base64 payloads adjacent to known executors, dynamic invocation `& ($var)`

**Tier 2 — tool name + shell signal required:**
`mshta`, `msiexec`, `rundll32`, `certutil`, `wscript`, `cscript`, `wmic`, `regsvr32`, `bitsadmin`, `schtasks` — only trigger when followed by a flag, URL, operator, variable, or payload file extension.

## 🛠️ How to Run from Source (Python)
1. Clone the repo
2. Install dependencies:
```
pip install pywin32 pystray Pillow
```
3. Run:
```
python clipboard_defanger.py
```

## ⚙️ Tray Menu
Right-click the tray icon to access:
- **Stats** — threats blocked and URLs cleaned since install
- **Silent Mode** — toggle payload killing without a dialog
- **Notifications** — toggle tray notifications on URL cleans
- **View Log** — opens `~/pasteguard.log` directly
- **Quit**

## License & Pricing
**Personal Use:** Free for personal, non-commercial use on your own devices.

**Commercial Use:** Use in a commercial environment (business, enterprise, or government) requires a paid license.
📧 [Contact us for a quote](mailto:founder@sekura.se)

**Redistribution:** You may not sell or repackage this software without explicit permission.

---
*A [Sekura](https://sekura.se) product.*

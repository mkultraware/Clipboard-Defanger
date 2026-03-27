# Sekura PasteGuard 🛡️
A lightweight Windows utility that protects you from clipboard-based attacks and tracking.

## What is it?

PasteGuard runs silently in your system tray and monitors your clipboard in real time.

It does two things:

**1. ClickFix Protection**
Attackers use fake CAPTCHAs and error pages to trick you into copying and running malicious commands. The moment PasteGuard detects a shell command in your clipboard (PowerShell, CMD, curl, mshta, etc.), it warns you before you can paste and run it.

**2. Tracking Parameter Removal**
When you copy a link from Amazon, Facebook, TikTok, LinkedIn, and others, they attach tracking parameters to spy on your clicks. PasteGuard strips them instantly so you always paste a clean URL.

## Download
[**Download the latest installer here**](https://github.com/mkultraware/Clipboard-Defanger/releases)

## ✨ Features

- **ClickFix Detection:** Warns you when a Windows shell command is copied to clipboard, with Cancel and Copy Anyway options
- **Silent Mode:** Optional mode that kills command payloads instantly without prompting
- **Tracking Removal:** Strips 20+ tracking parameters including UTM, fbclid, ttclid, LinkedIn trk, msclkid, and more
- **Zero-Click:** Works automatically in the background
- **Lightweight:** Uses minimal RAM (<20MB)
- **Auto-Start:** Runs on Windows startup via the installer

## 🔍 What Commands Does It Detect?

PasteGuard detects all known [ClickFix](https://www.proofpoint.com/us/blog/threat-insight/clipboard-hijacking) attack patterns including:

`powershell`, `cmd /c`, `mshta`, `msiexec`, `rundll32`, `certutil`, `wscript`, `cscript`, `reg add`, `curl`, `Invoke-WebRequest`, `DownloadString`, base64 encoded payloads, and more.

## 🛠️ How to Run from Source (Python)

1. Clone the repo
2. Install dependencies:
```
pip install -r requirements.txt
```
3. Run:
```
python clipboard_defanger.py
```

## ⚙️ Silent Mode

To silently kill command payloads without showing a warning dialog, open `clipboard_defanger.py` and set:
```python
SILENT_MODE = True
```

## License & Pricing

**Personal Use:** Free for personal, non-commercial use on your own devices.

**Commercial Use:** Use in a commercial environment (business, enterprise, or government) requires a paid license.

📧 [Contact us for a quote](mailto:founder@sekura.se)

**Redistribution:** You may not sell or repackage this software without explicit permission.

---

*A [Sekura](https://sekura.se) product.*

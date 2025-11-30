# Clipboard Defanger 🛡️

A lightweight Windows utility that acts as a "digital hand sanitizer" for your links.

## What is it?
When you copy a link from sites like Amazon, Facebook, or YouTube, they attach "tracking parameters" (garbage text used to spy on your clicks). 

**Clipboard Defanger** runs silently in your system tray. It monitors your clipboard, and the moment you copy a "dirty" link, it instantly strips the tracking tags (`utm_source`, `fbclid`, etc.) so you paste a clean, private URL.

## Download
[**Download the latest Installer here**](https://github.com/mkultraware/Clipboard-Defanger/releases)

## ✨ Features
* **Zero-Click:** Just copy and paste. It happens automatically.
* **Privacy First:** Removes 10+ common tracking parameters.
* **Lightweight:** Uses minimal RAM (<20MB).
* **Auto-Start:** Includes an installer to run on startup.

## 🛠️ How to Run from Source (Python)
If you prefer not to use the EXE, you can run the script directly:

1.  Clone the repo.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the script:
    ```bash
    python clipboard_defanger.py
    ```


##  License & Pricing

**Personal Use:** This software is free for personal, non-commercial use. You can download and use it on your personal devices without charge.

**Commercial Use:** Use in a commercial environment (business, enterprise, or for-profit organization) requires a license fee. The installer will guide you to the payment page, or you can [pay for a commercial license here](https://paypal.me/mkultraware).

**Redistribution:** You may not sell this software or repackage it for sale without explicit permission.

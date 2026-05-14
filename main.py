"""
main.py - Entry Point
Smart Price Tracker & Intelligent Web Scraper
=============================================

Run this file to launch the application:
    python main.py

Requirements (install via pip):
    pip install requests beautifulsoup4 pandas matplotlib python-dateutil
    (sqlite3 and tkinter are part of Python standard library)
"""

import sys
import tkinter as tk
from tkinter import messagebox


# ── Dependency check ──────────────────────────────────────────────────────────

REQUIRED_PACKAGES = {
    "requests":         "requests",
    "bs4":              "beautifulsoup4",
    "pandas":           "pandas",
    "matplotlib":       "matplotlib",
    "dateutil":         "python-dateutil",
}

missing = []
for module, pkg in REQUIRED_PACKAGES.items():
    try:
        __import__(module)
    except ImportError:
        missing.append(pkg)

if missing:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "Missing Dependencies",
        "Please install the following packages and restart:\n\n"
        + "\n".join(f"  pip install {p}" for p in missing)
        + "\n\nOr run:  pip install -r requirements.txt"
    )
    sys.exit(1)


# ── Launch ────────────────────────────────────────────────────────────────────

from ui import SmartPriceTrackerApp


def main():
    root = tk.Tk()

    # High-DPI awareness on Windows
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = SmartPriceTrackerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

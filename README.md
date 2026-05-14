# ⚡ Smart Price Tracker & Intelligent Web Scraper

> A Python desktop application to compare, track, and analyze product prices across multiple e-commerce platforms in real time.

---

## 📌 Project Overview

Smart Price Tracker is a full-featured desktop application built with **Python 3** and **Tkinter**. It allows users to:

- Search for any product and instantly compare prices across Amazon, Flipkart, Croma, Reliance Digital, and Tata CLiQ
- Identify the **cheapest deal** with a single click
- **Track products** over time in a local SQLite database
- View **price history graphs** using Matplotlib
- Set **target price alerts** — get notified when the price drops to your goal
- **Auto-refresh** prices in the background using threading
- Switch between **Dark and Light mode**
- **Export data** to CSV for spreadsheet analysis

---

## 🗂 File Structure

```
SmartPriceTracker/
│
├── main.py          ← Entry point; checks dependencies, launches app
├── ui.py            ← Complete Tkinter GUI (dark/light, tables, graphs)
├── scraper.py       ← Web scraping engine with smart mock fallback
├── database.py      ← SQLite database operations (CRUD + export)
├── tracker.py       ← Price tracking, alert engine, auto-refresh
├── requirements.txt ← Python package dependencies
└── README.md        ← This file
```

---

## ⚙ Installation & Setup

### 1. Prerequisites
- Python 3.10 or higher
- pip (Python package manager)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install requests beautifulsoup4 pandas matplotlib python-dateutil
```

> **Note:** `tkinter` and `sqlite3` are included in Python's standard library.

### 3. Run the Application
```bash
python main.py
```

---

## 🚀 How to Use

| Step | Action |
|------|--------|
| 1 | Type a product name (e.g., *iPhone 15, Samsung TV*) in the search bar |
| 2 | Click **Search** or press Enter |
| 3 | View results — cheapest is highlighted in green with 🏆 |
| 4 | Select a row → click **📌 Track** to save to database |
| 5 | In the right panel, select a tracked item → click **📈 Graph** |
| 6 | Use **🎯 Set Target** to get a popup alert when price drops |
| 7 | Click **▶ Auto-Refresh** to enable background price updates |
| 8 | Use **⬇ Export CSV** to download all tracked data |
| 9 | Toggle **☀ Light Mode** / **🌙 Dark Mode** in the top-right corner |

---

## 🔍 Scraping Strategy

The app uses a two-tier approach:

1. **Real HTTP Scraping**: Attempts to scrape live data from Amazon India and Flipkart using `requests` + `BeautifulSoup4`
2. **Intelligent Mock Fallback**: If a site blocks the request (common due to bot detection), a realistic price generator kicks in. It uses product-category-specific base prices and per-site variance to simulate real market data

This ensures the app **always shows results**, even in offline or restricted lab environments.

---

## 🗄 Database Schema

### `products` table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment ID |
| query | TEXT | Search term used |
| name | TEXT | Product name |
| website | TEXT | Source site |
| url | TEXT | Product link |
| target_price | REAL | Alert threshold |
| added_at | TEXT | Timestamp added |

### `price_history` table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| product_id | INTEGER FK | References products |
| price | REAL | Price at this time |
| recorded_at | TEXT | Timestamp |

---

## 🧪 Technologies Used

| Library | Purpose |
|---------|---------|
| `tkinter` / `ttk` | Desktop GUI framework |
| `requests` | HTTP requests for scraping |
| `BeautifulSoup4` | HTML parsing |
| `sqlite3` | Local database (built-in) |
| `matplotlib` | Price trend graphs |
| `pandas` | (Available for data processing) |
| `threading` | Background auto-refresh |
| `dataclasses` | Clean Product data model |

---

## ❓ Viva Questions & Answers

### Q1. What is web scraping and how is it implemented in this project?

**Answer:** Web scraping is the automated extraction of data from websites using HTTP requests and HTML parsing. In this project, the `PriceScraper` class in `scraper.py` sends HTTP GET requests to Amazon and Flipkart with browser-like headers to avoid bot detection. The response HTML is parsed using `BeautifulSoup4` to locate product names and prices via CSS selectors. If the request is blocked (common on e-commerce sites), an intelligent mock data generator provides realistic price data based on product category, ensuring the app always has results to display.

---

### Q2. Why is SQLite used instead of a server-based database like MySQL?

**Answer:** SQLite is a **serverless, file-based** relational database that requires zero configuration and comes bundled with Python's standard library. For a desktop application like a price tracker, SQLite is ideal because: (1) it stores all data in a single `.db` file that travels with the app, (2) it supports full SQL queries for complex data retrieval, (3) it handles concurrent reads well, and (4) there's no need to install or run a database server. MySQL or PostgreSQL would be overkill for single-user desktop use.

---

### Q3. How does the threading module prevent UI freezing during scraping?

**Answer:** Tkinter runs on a **single main thread** — if a slow operation (like an HTTP request that takes 5–10 seconds) runs on this thread, the entire UI freezes. The app solves this with Python's `threading` module: when the user clicks Search, a new **daemon thread** is spawned that runs the scraping function in the background. The main thread continues running the UI event loop. When scraping completes, `root.after(0, callback)` safely schedules the UI update back on the main thread (Tkinter is not thread-safe, so we never update widgets directly from worker threads).

---

### Q4. Explain OOP design in this project. What classes are used?

**Answer:** The project uses Object-Oriented Programming throughout:
- **`Product` (dataclass)** — Models a scraped product with name, price, website, URL, rating fields and a `to_dict()` method
- **`PriceScraper`** — Encapsulates all scraping logic; exposes a clean `search()` method; internally delegates to site-specific private methods
- **`DatabaseManager`** — Wraps all SQLite operations; hides SQL queries behind semantic methods like `upsert_product()`, `get_price_history()`
- **`PriceTracker`** — Composes the DB and Scraper to implement tracking, alert detection, and auto-refresh via threading
- **`PriceAlert`** — Models an alert event with computed properties (`drop_percent`, `is_target_hit`)
- **`SmartPriceTrackerApp`** — The main UI class; manages all Tkinter widgets, user events, and coordinates all other classes

---

### Q5. How does the price-drop alert system work?

**Answer:** The alert system works across three layers: (1) **Storage** — each product has an optional `target_price` column in the database; (2) **Detection** — during every auto-refresh cycle, `PriceTracker.refresh_all()` fetches the new price and compares it to the previous price using `get_previous_price(product_id)`; if `new_price < prev_price`, a `PriceAlert` object is created containing the drop amount and percentage; (3) **Dispatch** — the alert is passed to a registered callback function via `set_alert_callback()`. The callback uses `root.after(0, ...)` to safely schedule a Tkinter `messagebox` popup on the main thread. If the new price also falls at or below `target_price`, the alert message includes a special "Target Price Reached!" notification.

---

## 👨‍💻 Author Notes

- Mock data is used to ensure the app works in offline/lab environments where real scraping is blocked
- All prices are normalised using regex to strip ₹, commas, and whitespace before storing as float
- The app avoids duplicate database entries using `INSERT OR IGNORE` with a `UNIQUE(name, website)` constraint
- Dark mode uses a navy/crimson palette; Light mode uses a clean white/blue scheme
- The `PanedWindow` layout allows resizing the results and tracked panels

---

## 📜 License

This project is created for academic/educational purposes as part of a Software Lab course.

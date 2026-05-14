"""
database.py - SQLite Database Operations
Smart Price Tracker & Intelligent Web Scraper
Handles all database interactions: create, read, write, update
"""

import sqlite3
import os
from datetime import datetime


DB_PATH = "price_tracker.db"


class DatabaseManager:
    """Manages all SQLite database operations for the price tracker."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.initialize_db()

    # ──────────────────────────────────────────────
    # Setup
    # ──────────────────────────────────────────────

    def initialize_db(self):
        """Create tables if they don't exist."""
        with self._connect() as conn:
            cursor = conn.cursor()

            # Products table – stores each tracked product
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    query       TEXT NOT NULL,
                    name        TEXT NOT NULL,
                    website     TEXT NOT NULL,
                    url         TEXT,
                    target_price REAL DEFAULT NULL,
                    added_at    TEXT NOT NULL,
                    UNIQUE(name, website)
                )
            """)

            # Price history table – time-series data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id  INTEGER NOT NULL,
                    price       REAL NOT NULL,
                    recorded_at TEXT NOT NULL,
                    FOREIGN KEY (product_id) REFERENCES products(id)
                )
            """)

            conn.commit()

    def _connect(self):
        """Return a new SQLite connection."""
        return sqlite3.connect(self.db_path)

    # ──────────────────────────────────────────────
    # Products
    # ──────────────────────────────────────────────

    def upsert_product(self, query: str, name: str, website: str,
                       url: str, price: float) -> int:
        """
        Insert product if it doesn't exist; return its ID.
        Also records the current price in price_history.
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            cursor = conn.cursor()

            # Try insert; ignore if duplicate
            cursor.execute("""
                INSERT OR IGNORE INTO products (query, name, website, url, added_at)
                VALUES (?, ?, ?, ?, ?)
            """, (query, name, website, url, now))
            conn.commit()

            # Fetch the ID
            cursor.execute("""
                SELECT id FROM products WHERE name = ? AND website = ?
            """, (name, website))
            row = cursor.fetchone()
            product_id = row[0] if row else None

            if product_id:
                # Record price history
                cursor.execute("""
                    INSERT INTO price_history (product_id, price, recorded_at)
                    VALUES (?, ?, ?)
                """, (product_id, price, now))
                conn.commit()

        return product_id

    def get_all_tracked_products(self) -> list:
        """Return all tracked products with their latest price."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.id, p.query, p.name, p.website, p.url,
                       p.target_price, p.added_at,
                       ph.price AS latest_price
                FROM products p
                LEFT JOIN price_history ph ON ph.id = (
                    SELECT id FROM price_history
                    WHERE product_id = p.id
                    ORDER BY recorded_at DESC
                    LIMIT 1
                )
                ORDER BY p.added_at DESC
            """)
            rows = cursor.fetchall()
        return rows

    def set_target_price(self, product_id: int, target: float):
        """Set a price-drop alert target for a product."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE products SET target_price = ? WHERE id = ?
            """, (target, product_id))
            conn.commit()

    def delete_product(self, product_id: int):
        """Remove a product and its history from the database."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM price_history WHERE product_id = ?", (product_id,))
            cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
            conn.commit()

    # ──────────────────────────────────────────────
    # Price History
    # ──────────────────────────────────────────────

    def get_price_history(self, product_id: int) -> list:
        """Return full price history for a product, oldest first."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT price, recorded_at
                FROM price_history
                WHERE product_id = ?
                ORDER BY recorded_at ASC
            """, (product_id,))
            rows = cursor.fetchall()
        return rows

    def get_latest_price(self, product_id: int) -> float | None:
        """Return the most recent price for a product."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT price FROM price_history
                WHERE product_id = ?
                ORDER BY recorded_at DESC
                LIMIT 1
            """, (product_id,))
            row = cursor.fetchone()
        return row[0] if row else None

    def get_previous_price(self, product_id: int) -> float | None:
        """Return the second-most-recent price (for drop detection)."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT price FROM price_history
                WHERE product_id = ?
                ORDER BY recorded_at DESC
                LIMIT 2
            """, (product_id,))
            rows = cursor.fetchall()
        return rows[1][0] if len(rows) >= 2 else None

    # ──────────────────────────────────────────────
    # Export
    # ──────────────────────────────────────────────

    def export_to_csv(self, filepath: str):
        """Export all tracked products + latest prices to CSV."""
        import csv
        rows = self.get_all_tracked_products()
        headers = ["ID", "Query", "Product Name", "Website", "URL",
                   "Target Price", "Added At", "Latest Price"]
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)

    def export_history_to_csv(self, product_id: int, filepath: str):
        """Export price history for a single product to CSV."""
        import csv
        rows = self.get_price_history(product_id)
        headers = ["Price (₹)", "Recorded At"]
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)

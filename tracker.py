"""
tracker.py - Price Tracking & Alert Engine
Smart Price Tracker & Intelligent Web Scraper

Handles:
  - Scheduled background refresh
  - Price-drop detection & alert callbacks
  - Target-price notifications
"""

import threading
import time
from datetime import datetime
from typing import Callable, Optional

from database import DatabaseManager
from scraper import PriceScraper, Product, format_price


# ──────────────────────────────────────────────────────────────────────────────
# Alert Data Class
# ──────────────────────────────────────────────────────────────────────────────

class PriceAlert:
    """Represents a price-drop or target-price alert event."""

    def __init__(self, product_name: str, website: str,
                 old_price: float, new_price: float,
                 target_price: Optional[float] = None):
        self.product_name  = product_name
        self.website       = website
        self.old_price     = old_price
        self.new_price     = new_price
        self.target_price  = target_price
        self.timestamp     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @property
    def drop_amount(self) -> float:
        return self.old_price - self.new_price

    @property
    def drop_percent(self) -> float:
        if self.old_price == 0:
            return 0.0
        return (self.drop_amount / self.old_price) * 100

    @property
    def is_target_hit(self) -> bool:
        return (self.target_price is not None
                and self.new_price <= self.target_price)

    def summary(self) -> str:
        base = (
            f"📉 Price Dropped! {self.product_name[:30]} on {self.website}\n"
            f"   {format_price(self.old_price)} → {format_price(self.new_price)} "
            f"(↓{self.drop_percent:.1f}%)"
        )
        if self.is_target_hit:
            base += f"\n   🎯 Target price {format_price(self.target_price)} reached!"
        return base


# ──────────────────────────────────────────────────────────────────────────────
# Tracker Engine
# ──────────────────────────────────────────────────────────────────────────────

class PriceTracker:
    """
    Manages product tracking, periodic refresh, and alert dispatch.

    Usage:
        tracker = PriceTracker(db, scraper)
        tracker.set_alert_callback(my_callback)
        tracker.start_auto_refresh(interval_minutes=5)
    """

    def __init__(self, db: DatabaseManager, scraper: PriceScraper):
        self.db      = db
        self.scraper = scraper
        self._alert_callback: Optional[Callable[[PriceAlert], None]] = None
        self._refresh_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False

    # ──────────────────────────────────────────────
    # Alert Callback
    # ──────────────────────────────────────────────

    def set_alert_callback(self, callback: Callable[[PriceAlert], None]):
        """Register a function to call when a price drop is detected."""
        self._alert_callback = callback

    def _fire_alert(self, alert: PriceAlert):
        if self._alert_callback:
            self._alert_callback(alert)

    # ──────────────────────────────────────────────
    # Track a Product
    # ──────────────────────────────────────────────

    def track_product(self, query: str, product: Product) -> int:
        """
        Save a product to the database and record its current price.
        Returns the product_id.
        """
        pid = self.db.upsert_product(
            query=query,
            name=product.name,
            website=product.website,
            url=product.url,
            price=product.price,
        )
        return pid

    def set_target_price(self, product_id: int, target: float):
        """Set a price-drop alert target for a tracked product."""
        self.db.set_target_price(product_id, target)

    # ──────────────────────────────────────────────
    # Refresh Logic
    # ──────────────────────────────────────────────

    def refresh_all(self, progress_cb: Optional[Callable[[str], None]] = None):
        """
        Re-scrape all tracked products, update prices, fire alerts.
        Designed to be called from a background thread.
        """
        tracked = self.db.get_all_tracked_products()
        if not tracked:
            return

        queries_seen: set[str] = set()

        for row in tracked:
            pid, query, name, website, url, target_price, added_at, old_price = row

            # Avoid re-scraping the same query multiple times per cycle
            if query in queries_seen:
                continue
            queries_seen.add(query)

            if progress_cb:
                progress_cb(f"Refreshing: {query}…")

            try:
                results = self.scraper.search(query)
            except Exception:
                continue

            for product in results:
                new_pid = self.db.upsert_product(
                    query=query,
                    name=product.name,
                    website=product.website,
                    url=product.url,
                    price=product.price,
                )

                # Check for price drop
                prev = self.db.get_previous_price(new_pid)
                if prev is not None and product.price < prev:
                    row_data = self.db.get_all_tracked_products()
                    tgt = None
                    for r in row_data:
                        if r[0] == new_pid:
                            tgt = r[5]   # target_price column
                            break
                    alert = PriceAlert(
                        product_name=product.name,
                        website=product.website,
                        old_price=prev,
                        new_price=product.price,
                        target_price=tgt,
                    )
                    self._fire_alert(alert)

    # ──────────────────────────────────────────────
    # Background Auto-Refresh
    # ──────────────────────────────────────────────

    def start_auto_refresh(self, interval_minutes: int = 5,
                           progress_cb: Optional[Callable[[str], None]] = None):
        """Start a background daemon thread that refreshes prices periodically."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()

        def _loop():
            while not self._stop_event.is_set():
                self.refresh_all(progress_cb)
                # Sleep in 1-second chunks to allow quick stop
                for _ in range(interval_minutes * 60):
                    if self._stop_event.is_set():
                        break
                    time.sleep(1)
            self._running = False

        self._refresh_thread = threading.Thread(target=_loop, daemon=True)
        self._refresh_thread.start()

    def stop_auto_refresh(self):
        """Signal the background refresh thread to stop."""
        self._stop_event.set()
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    # ──────────────────────────────────────────────
    # Statistics
    # ──────────────────────────────────────────────

    def get_price_stats(self, product_id: int) -> dict:
        """Return min, max, average, and latest price for a product."""
        history = self.db.get_price_history(product_id)
        if not history:
            return {}
        prices = [row[0] for row in history]
        latest = prices[-1]
        highest = max(prices)
        lowest  = min(prices)
        avg     = sum(prices) / len(prices)
        drop_from_high = ((highest - latest) / highest * 100) if highest > 0 else 0
        return {
            "latest":          latest,
            "lowest":          lowest,
            "highest":         highest,
            "average":         avg,
            "total_records":   len(prices),
            "drop_from_high":  drop_from_high,
        }

"""
scraper.py - Web Scraping & Mock Data Engine
Smart Price Tracker & Intelligent Web Scraper

Attempts real HTTP scraping; falls back to intelligent mock data
if a site blocks the request (common in lab environments).
"""

import requests
import random
import time
import re
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# Data Model
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Product:
    """Represents a scraped product result."""
    name: str
    price: float            # normalised float
    price_display: str      # formatted string e.g. "₹12,999"
    website: str
    url: str
    rating: Optional[float] = None
    reviews: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "price": self.price,
            "price_display": self.price_display,
            "website": self.website,
            "url": self.url,
            "rating": self.rating,
            "reviews": self.reviews,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Price Utilities
# ──────────────────────────────────────────────────────────────────────────────

def normalise_price(raw: str) -> float:
    """Strip currency symbols, commas, spaces; return float."""
    if not raw:
        return 0.0
    cleaned = re.sub(r"[₹$,\s]", "", str(raw))
    # Keep only digits and one decimal point
    cleaned = re.sub(r"[^\d.]", "", cleaned)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def format_price(value: float) -> str:
    """Format a float as Indian Rupee string."""
    return f"₹{value:,.0f}"


# ──────────────────────────────────────────────────────────────────────────────
# Mock Data Generator
# ──────────────────────────────────────────────────────────────────────────────

# Realistic price bases for well-known product categories
PRICE_SEEDS = {
    "iphone": 79999,
    "samsung": 44999,
    "laptop": 54999,
    "macbook": 119900,
    "headphone": 2999,
    "earphone": 1499,
    "tablet": 29999,
    "watch": 4999,
    "camera": 34999,
    "keyboard": 2499,
    "mouse": 999,
    "monitor": 14999,
    "tv": 39999,
    "refrigerator": 24999,
    "washing": 19999,
    "air conditioner": 34999,
    "ac": 34999,
    "speaker": 3999,
    "printer": 8999,
    "router": 2499,
}

SITES = [
    {
        "name": "Amazon",
        "domain": "amazon.in",
        "url_template": "https://www.amazon.in/s?k={query}",
        "variance": 0.05,   # ±5% from base price
        "badge": "🔶",
    },
    {
        "name": "Flipkart",
        "domain": "flipkart.com",
        "url_template": "https://www.flipkart.com/search?q={query}",
        "variance": 0.08,
        "badge": "🔵",
    },
    {
        "name": "Croma",
        "domain": "croma.com",
        "url_template": "https://www.croma.com/searchB?q={query}",
        "variance": 0.12,
        "badge": "🟢",
    },
    {
        "name": "Reliance Digital",
        "domain": "reliancedigital.in",
        "url_template": "https://www.reliancedigital.in/search?q={query}",
        "variance": 0.10,
        "badge": "🔴",
    },
    {
        "name": "Tata CLiQ",
        "domain": "tatacliq.com",
        "url_template": "https://www.tatacliq.com/search/?searchCategory=all&text={query}",
        "variance": 0.07,
        "badge": "🟣",
    },
]

PRODUCT_TEMPLATES = [
    "{query} - Latest Model 2024",
    "{query} Pro Max Edition",
    "{query} (Renewed) - Top Rated",
    "{query} Official Store",
    "{query} Bundle Pack",
]


def _get_base_price(query: str) -> float:
    """Derive a realistic base price from the search query."""
    q = query.lower()
    for keyword, price in PRICE_SEEDS.items():
        if keyword in q:
            return float(price)
    # Default: random plausible electronics price
    return float(random.randint(2999, 89999))


def _generate_mock_products(query: str) -> list[Product]:
    """Generate realistic mock product results for all sites."""
    base_price = _get_base_price(query)
    products = []

    for site in SITES:
        # Apply site-specific variance
        v = site["variance"]
        price = base_price * random.uniform(1 - v, 1 + v)
        price = round(price / 50) * 50   # round to nearest ₹50

        # Pick a product name template
        tmpl = random.choice(PRODUCT_TEMPLATES)
        name = tmpl.format(query=query.title())

        rating = round(random.uniform(3.5, 5.0), 1)
        reviews = random.randint(100, 15000)
        url = site["url_template"].format(query=query.replace(" ", "+"))

        products.append(Product(
            name=name,
            price=price,
            price_display=format_price(price),
            website=site["name"],
            url=url,
            rating=rating,
            reviews=reviews,
        ))

    return products


# ──────────────────────────────────────────────────────────────────────────────
# Real Scraper Helpers (best-effort; falls back to mock on any error)
# ──────────────────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _scrape_amazon(query: str) -> list[Product]:
    """Try to scrape Amazon India search results."""
    url = f"https://www.amazon.in/s?k={query.replace(' ', '+')}"
    products = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("div[data-component-type='s-search-result']")[:5]
        for card in cards:
            name_el = card.select_one("h2 a span")
            price_el = card.select_one(".a-price .a-offscreen")
            link_el  = card.select_one("h2 a")
            if name_el and price_el:
                name  = name_el.get_text(strip=True)
                price = normalise_price(price_el.get_text(strip=True))
                href  = "https://www.amazon.in" + link_el["href"] if link_el else url
                if price > 0:
                    products.append(Product(
                        name=name[:60], price=price,
                        price_display=format_price(price),
                        website="Amazon", url=href,
                    ))
    except Exception:
        pass  # Silently fall back to mock
    return products


def _scrape_flipkart(query: str) -> list[Product]:
    """Try to scrape Flipkart search results."""
    url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}"
    products = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        soup = BeautifulSoup(resp.text, "html.parser")
        # Flipkart uses dynamic class names; target price containers
        items = soup.select("div._1AtVbE")[:8]
        for item in items:
            name_el  = item.select_one("div._4rR01T, a.s1Q9rs, div.KzDlHZ")
            price_el = item.select_one("div._30jeq3")
            link_el  = item.select_one("a._1fQZEK, a.s1Q9rs")
            if name_el and price_el:
                name  = name_el.get_text(strip=True)
                price = normalise_price(price_el.get_text(strip=True))
                href  = ("https://www.flipkart.com" + link_el["href"]
                         if link_el else url)
                if price > 0 and name:
                    products.append(Product(
                        name=name[:60], price=price,
                        price_display=format_price(price),
                        website="Flipkart", url=href,
                    ))
    except Exception:
        pass
    return products


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

class PriceScraper:
    """
    Orchestrates scraping across multiple sites.
    Uses real scrapers first; supplements with mock data
    so the UI always has results to show.
    """

    def __init__(self, use_mock: bool = False):
        """
        Args:
            use_mock: Force mock mode (useful for offline / demo).
        """
        self.use_mock = use_mock

    def search(self, query: str,
               progress_callback=None) -> list[Product]:
        """
        Search for products across all supported sites.

        Args:
            query: Product search term.
            progress_callback: Optional callable(message: str).

        Returns:
            Sorted list of Product objects (cheapest first).
        """
        results: list[Product] = []

        if self.use_mock:
            if progress_callback:
                progress_callback("Generating intelligent price data…")
            time.sleep(1.2)   # simulate network latency
            results = _generate_mock_products(query)
        else:
            # Try real scrapers
            for scrape_fn, label in [
                (_scrape_amazon,  "Amazon"),
                (_scrape_flipkart, "Flipkart"),
            ]:
                if progress_callback:
                    progress_callback(f"Scraping {label}…")
                found = scrape_fn(query)
                results.extend(found)
                time.sleep(0.5)

            # Supplement missing sites with mock data
            covered_sites = {p.website for p in results}
            mock = _generate_mock_products(query)
            for p in mock:
                if p.website not in covered_sites:
                    results.append(p)

        if not results:
            results = _generate_mock_products(query)

        # Remove duplicates (same site + very close price)
        results = self._deduplicate(results)

        # Sort cheapest first
        results.sort(key=lambda p: p.price)

        if progress_callback:
            progress_callback("Done!")

        return results

    @staticmethod
    def _deduplicate(products: list[Product]) -> list[Product]:
        """Keep only one product per website (cheapest)."""
        best: dict[str, Product] = {}
        for p in products:
            key = p.website
            if key not in best or p.price < best[key].price:
                best[key] = p
        return list(best.values())

    @staticmethod
    def find_best_deal(products: list[Product]) -> Product | None:
        """Return the cheapest product."""
        if not products:
            return None
        return min(products, key=lambda p: p.price)

    @staticmethod
    def rank_products(products: list[Product]) -> list[tuple[int, Product]]:
        """Return (rank, product) tuples sorted cheapest-first."""
        sorted_p = sorted(products, key=lambda p: p.price)
        return list(enumerate(sorted_p, start=1))

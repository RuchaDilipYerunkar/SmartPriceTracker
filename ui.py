"""
ui.py - Modern Tkinter GUI
Smart Price Tracker & Intelligent Web Scraper

Implements a dark/light-mode desktop app with:
  - Product search bar
  - Results table with cheapest highlight
  - Track / History / Export controls
  - Inline status bar
  - Matplotlib price history window
  - Alert toasts
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import threading
import webbrowser
from datetime import datetime

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from scraper import PriceScraper, Product
from database import DatabaseManager
from tracker import PriceTracker, PriceAlert


# ──────────────────────────────────────────────────────────────────────────────
# Colour Palettes
# ──────────────────────────────────────────────────────────────────────────────

DARK = {
    "bg":           "#0f0f17",
    "surface":      "#1a1a2e",
    "surface2":     "#16213e",
    "accent":       "#e94560",
    "accent2":      "#0f3460",
    "text":         "#eaeaea",
    "text_dim":     "#8892a4",
    "green":        "#00d4aa",
    "yellow":       "#ffd700",
    "red":          "#ff4757",
    "border":       "#2d2d4e",
    "row_alt":      "#1e1e32",
    "row_best":     "#1a3a2a",
    "header_bg":    "#0a0a14",
}

LIGHT = {
    "bg":           "#f0f2f5",
    "surface":      "#ffffff",
    "surface2":     "#e8eaf0",
    "accent":       "#c0392b",
    "accent2":      "#2980b9",
    "text":         "#1a1a2e",
    "text_dim":     "#666688",
    "green":        "#00a878",
    "yellow":       "#e67e22",
    "red":          "#e74c3c",
    "border":       "#d0d4e0",
    "row_alt":      "#f7f8fc",
    "row_best":     "#d5f5e3",
    "header_bg":    "#1a1a2e",
}


# ──────────────────────────────────────────────────────────────────────────────
# Main Application Window
# ──────────────────────────────────────────────────────────────────────────────

class SmartPriceTrackerApp:
    """Main application class – builds and manages the full UI."""

    APP_TITLE   = "Smart Price Tracker"
    APP_VERSION = "v2.0"
    MIN_W, MIN_H = 1050, 680

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{self.APP_TITLE}  {self.APP_VERSION}")
        self.root.minsize(self.MIN_W, self.MIN_H)
        self.root.geometry("1150x720")

        # State
        self._dark_mode  = True
        self._theme      = DARK
        self._results: list[Product] = []
        self._auto_refresh_on = False
        self._refresh_interval = 5   # minutes

        # Core modules
        self.db      = DatabaseManager()
        self.scraper = PriceScraper(use_mock=False)
        self.tracker = PriceTracker(self.db, self.scraper)
        self.tracker.set_alert_callback(self._on_price_alert)

        self._build_ui()
        self._apply_theme()

        # Window close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ──────────────────────────────────────────────
    # UI Construction
    # ──────────────────────────────────────────────

    def _build_ui(self):
        """Assemble all UI components."""
        self._build_header()
        self._build_search_bar()
        self._build_results_area()
        self._build_status_bar()

    def _build_header(self):
        """Top banner with title, subtitle, and theme toggle."""
        self.header_frame = tk.Frame(self.root, height=64)
        self.header_frame.pack(fill="x", side="top")
        self.header_frame.pack_propagate(False)

        # Left: icon + title
        left = tk.Frame(self.header_frame)
        left.pack(side="left", padx=18, pady=10)

        self.lbl_icon = tk.Label(left, text="⚡", font=("Segoe UI Emoji", 22))
        self.lbl_icon.pack(side="left", padx=(0, 8))

        title_block = tk.Frame(left)
        title_block.pack(side="left")
        self.lbl_title = tk.Label(title_block, text=self.APP_TITLE,
                                   font=("Segoe UI", 16, "bold"))
        self.lbl_title.pack(anchor="w")
        self.lbl_sub = tk.Label(title_block,
                                 text="Compare prices · Track deals · Save money",
                                 font=("Segoe UI", 9))
        self.lbl_sub.pack(anchor="w")

        # Right: toggle + version
        right = tk.Frame(self.header_frame)
        right.pack(side="right", padx=18)

        self.btn_theme = tk.Button(right, text="☀  Light Mode",
                                    font=("Segoe UI", 9, "bold"),
                                    relief="flat", bd=0, padx=10, pady=5,
                                    cursor="hand2",
                                    command=self._toggle_theme)
        self.btn_theme.pack(side="right", padx=(8, 0))

        self.lbl_version = tk.Label(right, text=self.APP_VERSION,
                                     font=("Segoe UI", 8))
        self.lbl_version.pack(side="right")

    def _build_search_bar(self):
        """Search input + action buttons row."""
        self.search_frame = tk.Frame(self.root, pady=14)
        self.search_frame.pack(fill="x", padx=20)

        # Search entry
        entry_wrap = tk.Frame(self.search_frame, bd=2, relief="flat")
        entry_wrap.pack(side="left", fill="x", expand=True, ipady=4)

        self.lbl_search_icon = tk.Label(entry_wrap, text="🔍",
                                         font=("Segoe UI Emoji", 13))
        self.lbl_search_icon.pack(side="left", padx=(10, 4))

        self.search_var = tk.StringVar()
        self.entry_search = tk.Entry(entry_wrap, textvariable=self.search_var,
                                      font=("Segoe UI", 13), relief="flat",
                                      bd=0, width=40)
        self.entry_search.pack(side="left", fill="x", expand=True, ipady=6)
        self.entry_search.insert(0, "e.g. iPhone 15, Samsung TV, Laptop…")
        self.entry_search.bind("<FocusIn>",  self._clear_placeholder)
        self.entry_search.bind("<FocusOut>", self._restore_placeholder)
        self.entry_search.bind("<Return>", lambda e: self._do_search())

        # Buttons
        btn_cfg = dict(font=("Segoe UI", 10, "bold"), relief="flat",
                        bd=0, padx=14, pady=8, cursor="hand2")

        self.btn_search = tk.Button(self.search_frame, text="  Search  ",
                                     **btn_cfg, command=self._do_search)
        self.btn_search.pack(side="left", padx=(10, 4))

        self.btn_track = tk.Button(self.search_frame, text="📌 Track",
                                    **btn_cfg, command=self._track_selected)
        self.btn_track.pack(side="left", padx=4)

        self.btn_history = tk.Button(self.search_frame, text="📈 History",
                                      **btn_cfg, command=self._show_history_dialog)
        self.btn_history.pack(side="left", padx=4)

        self.btn_export = tk.Button(self.search_frame, text="⬇ Export CSV",
                                     **btn_cfg, command=self._export_csv)
        self.btn_export.pack(side="left", padx=4)

        self.btn_auto = tk.Button(self.search_frame, text="▶ Auto-Refresh",
                                   **btn_cfg, command=self._toggle_auto_refresh)
        self.btn_auto.pack(side="left", padx=(4, 0))

    def _build_results_area(self):
        """Main area: best deal banner + results table + tracked panel."""
        self.main_pane = tk.PanedWindow(self.root, orient="horizontal",
                                         sashwidth=6, sashrelief="flat")
        self.main_pane.pack(fill="both", expand=True, padx=20, pady=(0, 4))

        # ── Left Panel: search results ──────────────────────────
        left_panel = tk.Frame(self.main_pane)
        self.main_pane.add(left_panel, minsize=600)

        # Best Deal Banner
        self.banner_frame = tk.Frame(left_panel, pady=8, padx=14)
        self.banner_frame.pack(fill="x")

        self.lbl_best = tk.Label(self.banner_frame, text="",
                                  font=("Segoe UI", 12, "bold"), anchor="w")
        self.lbl_best.pack(side="left")

        self.lbl_drop_pct = tk.Label(self.banner_frame, text="",
                                      font=("Segoe UI", 10), anchor="e")
        self.lbl_drop_pct.pack(side="right")

        # Column headers label
        self.lbl_results_hdr = tk.Label(left_panel,
                                         text="SEARCH RESULTS",
                                         font=("Segoe UI", 9, "bold"),
                                         anchor="w", padx=4)
        self.lbl_results_hdr.pack(fill="x", padx=4, pady=(4, 2))

        # Results table
        tbl_frame = tk.Frame(left_panel)
        tbl_frame.pack(fill="both", expand=True)

        cols = ("rank", "product", "website", "price", "rating", "url")
        self.tree = ttk.Treeview(tbl_frame, columns=cols,
                                  show="headings", selectmode="browse")

        col_widths = {"rank": 45, "product": 280, "website": 110,
                       "price": 95, "rating": 70, "url": 0}
        col_titles = {"rank": "#", "product": "Product Name",
                       "website": "Website", "price": "Price",
                       "rating": "Rating", "url": "URL"}

        for c in cols:
            self.tree.heading(c, text=col_titles[c],
                               command=lambda _c=c: self._sort_by(_c))
            self.tree.column(c, width=col_widths[c], stretch=(c == "product"),
                              anchor="center" if c in ("rank","price","rating") else "w")

        vsb = ttk.Scrollbar(tbl_frame, orient="vertical",
                             command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self._open_url)

        # Filter bar
        filter_frame = tk.Frame(left_panel)
        filter_frame.pack(fill="x", pady=(6, 0))

        tk.Label(filter_frame, text="Filter by site:",
                  font=("Segoe UI", 9)).pack(side="left", padx=(4, 4))

        self.filter_var = tk.StringVar(value="All")
        self.filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_var,
                                          width=14, state="readonly",
                                          font=("Segoe UI", 9))
        self.filter_combo.pack(side="left")
        self.filter_combo.bind("<<ComboboxSelected>>", self._apply_filter)

        tk.Label(filter_frame, text="  Sort:",
                  font=("Segoe UI", 9)).pack(side="left", padx=(10, 4))
        self.sort_var = tk.StringVar(value="Price ↑")
        sort_combo = ttk.Combobox(filter_frame, textvariable=self.sort_var,
                                   values=["Price ↑", "Price ↓", "Rating ↓"],
                                   width=10, state="readonly", font=("Segoe UI", 9))
        sort_combo.pack(side="left")
        sort_combo.bind("<<ComboboxSelected>>", self._apply_filter)

        # Loading indicator
        self.progress = ttk.Progressbar(left_panel, mode="indeterminate",
                                          length=200)
        self.lbl_loading = tk.Label(left_panel, text="",
                                     font=("Segoe UI", 9, "italic"))

        # ── Right Panel: tracked products ─────────────────────
        right_panel = tk.Frame(self.main_pane)
        self.main_pane.add(right_panel, minsize=280)

        tk.Label(right_panel, text="📌  TRACKED PRODUCTS",
                  font=("Segoe UI", 9, "bold"),
                  anchor="w", padx=4).pack(fill="x", padx=4, pady=(4, 2))

        track_frame = tk.Frame(right_panel)
        track_frame.pack(fill="both", expand=True)

        t_cols = ("name", "site", "price")
        self.track_tree = ttk.Treeview(track_frame, columns=t_cols,
                                        show="headings", selectmode="browse",
                                        height=16)
        self.track_tree.heading("name",  text="Product")
        self.track_tree.heading("site",  text="Site")
        self.track_tree.heading("price", text="Latest ₹")
        self.track_tree.column("name",  width=140, stretch=True)
        self.track_tree.column("site",  width=80)
        self.track_tree.column("price", width=70, anchor="e")

        vsb2 = ttk.Scrollbar(track_frame, orient="vertical",
                               command=self.track_tree.yview)
        self.track_tree.configure(yscrollcommand=vsb2.set)
        self.track_tree.pack(side="left", fill="both", expand=True)
        vsb2.pack(side="right", fill="y")

        # Tracked panel buttons
        tb = tk.Frame(right_panel)
        tb.pack(fill="x", pady=6)
        btn_s = dict(font=("Segoe UI", 9, "bold"), relief="flat",
                      bd=0, padx=10, pady=5, cursor="hand2")

        tk.Button(tb, text="📈 Graph", **btn_s,
                   command=self._show_history_for_selected).pack(side="left", padx=4)
        tk.Button(tb, text="🎯 Set Target", **btn_s,
                   command=self._set_target_price).pack(side="left", padx=4)
        tk.Button(tb, text="🗑 Remove", **btn_s,
                   command=self._remove_tracked).pack(side="left", padx=4)

        # Refresh tracked list
        self._refresh_tracked_panel()

    def _build_status_bar(self):
        """Bottom status bar."""
        self.status_frame = tk.Frame(self.root, height=26)
        self.status_frame.pack(fill="x", side="bottom")
        self.status_frame.pack_propagate(False)

        self.lbl_status = tk.Label(self.status_frame, text="Ready  ·  Enter a product name to search",
                                    font=("Segoe UI", 9), anchor="w")
        self.lbl_status.pack(side="left", padx=12)

        self.lbl_time = tk.Label(self.status_frame, font=("Segoe UI", 9), anchor="e")
        self.lbl_time.pack(side="right", padx=12)
        self._tick_clock()

    # ──────────────────────────────────────────────
    # Theme
    # ──────────────────────────────────────────────

    def _toggle_theme(self):
        self._dark_mode = not self._dark_mode
        self._theme = DARK if self._dark_mode else LIGHT
        self._apply_theme()
        self.btn_theme.config(text="☀  Light Mode" if self._dark_mode else "🌙  Dark Mode")

    def _apply_theme(self):
        t = self._theme
        self.root.config(bg=t["bg"])

        # Configure ttk style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                         background=t["surface"],
                         foreground=t["text"],
                         fieldbackground=t["surface"],
                         rowheight=28,
                         font=("Segoe UI", 10),
                         borderwidth=0)
        style.configure("Treeview.Heading",
                         background=t["header_bg"],
                         foreground="#ffffff",
                         font=("Segoe UI", 9, "bold"),
                         relief="flat")
        style.map("Treeview",
                   background=[("selected", t["accent2"])],
                   foreground=[("selected", "#ffffff")])
        style.configure("TScrollbar",
                         background=t["surface2"], troughcolor=t["bg"],
                         borderwidth=0, arrowsize=12)
        style.configure("TCombobox",
                         fieldbackground=t["surface"],
                         background=t["surface"],
                         foreground=t["text"],
                         arrowcolor=t["text"])
        style.configure("TProgressbar",
                         troughcolor=t["surface2"],
                         background=t["accent"],
                         borderwidth=0)

        def recolor(widget):
            cls = widget.winfo_class()
            try:
                if cls in ("Frame", "PanedWindow"):
                    widget.config(bg=t["bg"])
                elif cls == "Label":
                    widget.config(bg=t["bg"], fg=t["text"])
                elif cls == "Entry":
                    widget.config(bg=t["surface"], fg=t["text"],
                                   insertbackground=t["text"],
                                   disabledbackground=t["surface2"])
                elif cls == "Button":
                    widget.config(bg=t["accent2"], fg="#ffffff",
                                   activebackground=t["accent"],
                                   activeforeground="#ffffff")
            except tk.TclError:
                pass
            for child in widget.winfo_children():
                recolor(child)

        recolor(self.root)

        # Special overrides
        self.header_frame.config(bg=t["header_bg"])
        for w in self.header_frame.winfo_children():
            try:
                w.config(bg=t["header_bg"], fg="#ffffff")
            except Exception:
                pass
            for c in w.winfo_children():
                try:
                    c.config(bg=t["header_bg"], fg="#ffffff")
                except Exception:
                    pass

        self.lbl_best.config(bg=t["bg"], fg=t["green"])
        self.lbl_drop_pct.config(bg=t["bg"], fg=t["yellow"])
        self.status_frame.config(bg=t["surface2"])
        self.lbl_status.config(bg=t["surface2"], fg=t["text_dim"])
        self.lbl_time.config(bg=t["surface2"], fg=t["text_dim"])

        self.btn_search.config(bg=t["accent"], fg="#ffffff",
                                activebackground="#c0392b")
        self.btn_track.config(bg=t["accent2"])
        self.btn_auto.config(bg="#006644" if self._auto_refresh_on else t["accent2"])

        # Tag colours for table rows
        self.tree.tag_configure("best",    background=t["row_best"],  foreground=t["green"])
        self.tree.tag_configure("alt",     background=t["row_alt"])
        self.tree.tag_configure("normal",  background=t["surface"])

        self.banner_frame.config(bg=t["bg"])
        self.search_frame.config(bg=t["bg"])

    # ──────────────────────────────────────────────
    # Search
    # ──────────────────────────────────────────────

    def _do_search(self):
        query = self.search_var.get().strip()
        if not query or query.startswith("e.g."):
            messagebox.showwarning("Empty Search", "Please enter a product name.")
            return

        self._set_status(f"Searching for '{query}'…")
        self._show_loading(True)
        self._clear_results()

        def worker():
            try:
                results = self.scraper.search(
                    query, progress_callback=self._set_status)
                self.root.after(0, lambda: self._display_results(results, query))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(
                    "Search Error", str(e)))
            finally:
                self.root.after(0, lambda: self._show_loading(False))

        threading.Thread(target=worker, daemon=True).start()

    def _display_results(self, results: list[Product], query: str):
        self._results = results
        self._current_query = query

        # Update filter combo
        sites = ["All"] + sorted({p.website for p in results})
        self.filter_combo["values"] = sites
        self.filter_var.set("All")

        self._populate_table(results)
        self._set_status(
            f"Found {len(results)} result(s) for '{query}'  ·  Double-click to open URL")

    def _populate_table(self, products: list[Product]):
        self._clear_results()
        if not products:
            return

        # Apply sort
        sort = self.sort_var.get()
        if sort == "Price ↑":
            products = sorted(products, key=lambda p: p.price)
        elif sort == "Price ↓":
            products = sorted(products, key=lambda p: p.price, reverse=True)
        elif sort == "Rating ↓":
            products = sorted(products, key=lambda p: p.rating or 0, reverse=True)

        best = products[0] if sort.startswith("Price ↑") else \
               min(products, key=lambda p: p.price)

        for i, p in enumerate(products):
            is_best = (p.website == best.website and p.price == best.price)
            tag = "best" if is_best else ("alt" if i % 2 else "normal")
            star = "⭐" if is_best else ""
            rating_str = f"{p.rating}★" if p.rating else "—"
            self.tree.insert("", "end",
                              values=(f"{i+1}{'  '+star if is_best else ''}",
                                      p.name[:52],
                                      p.website,
                                      p.price_display,
                                      rating_str,
                                      p.url),
                              tags=(tag,))

        # Update best-deal banner
        self.lbl_best.config(
            text=f"🏆  Best Deal: {best.price_display}  on  {best.website}")

        if len(products) > 1:
            prices = sorted(p.price for p in products)
            diff = prices[-1] - prices[0]
            pct  = diff / prices[-1] * 100 if prices[-1] > 0 else 0
            self.lbl_drop_pct.config(
                text=f"You save {pct:.0f}% vs highest price")

    def _apply_filter(self, *_):
        site  = self.filter_var.get()
        items = self._results if site == "All" else \
                [p for p in self._results if p.website == site]
        self._populate_table(items)

    def _sort_by(self, col: str):
        """Sort table when clicking a column header."""
        if col == "price":
            self.sort_var.set("Price ↑")
        elif col == "rating":
            self.sort_var.set("Rating ↓")
        self._apply_filter()

    def _clear_results(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.lbl_best.config(text="")
        self.lbl_drop_pct.config(text="")

    def _open_url(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        url = self.tree.item(sel[0])["values"][5]
        if url and url.startswith("http"):
            webbrowser.open(url)

    # ──────────────────────────────────────────────
    # Tracking
    # ──────────────────────────────────────────────

    def _track_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a product row first.")
            return
        vals  = self.tree.item(sel[0])["values"]
        name  = str(vals[1])
        site  = str(vals[2])
        price_str = str(vals[3])
        url   = str(vals[5])

        # Find matching Product object
        product = next((p for p in self._results
                        if p.website == site), None)
        if not product:
            messagebox.showerror("Error", "Could not find product details.")
            return

        query = getattr(self, "_current_query", name)
        pid = self.tracker.track_product(query, product)
        self._refresh_tracked_panel()
        messagebox.showinfo("Tracked!",
                             f"'{name[:40]}' is now being tracked.\n"
                             f"Use '🎯 Set Target' to get price-drop alerts!")

    def _refresh_tracked_panel(self):
        for item in self.track_tree.get_children():
            self.track_tree.delete(item)
        rows = self.db.get_all_tracked_products()
        for row in rows:
            pid, query, name, website, url, target, added, latest = row
            price_str = f"₹{latest:,.0f}" if latest else "—"
            self.track_tree.insert("", "end",
                                    iid=str(pid),
                                    values=(name[:28], website, price_str))

    def _set_target_price(self):
        sel = self.track_tree.selection()
        if not sel:
            messagebox.showinfo("No Selection",
                                 "Select a tracked product first.")
            return
        pid = int(sel[0])
        latest = self.db.get_latest_price(pid)
        hint   = f"Current price: ₹{latest:,.0f}\n" if latest else ""
        target = simpledialog.askfloat(
            "Set Target Price",
            f"{hint}Enter your target price (₹):",
            minvalue=1, parent=self.root)
        if target:
            self.tracker.set_target_price(pid, target)
            messagebox.showinfo("Target Set",
                                 f"Alert set! You'll be notified if price drops to ₹{target:,.0f}.")

    def _remove_tracked(self):
        sel = self.track_tree.selection()
        if not sel:
            return
        pid = int(sel[0])
        if messagebox.askyesno("Remove", "Remove this product from tracking?"):
            self.db.delete_product(pid)
            self._refresh_tracked_panel()

    # ──────────────────────────────────────────────
    # Price History Graph
    # ──────────────────────────────────────────────

    def _show_history_dialog(self):
        """Show history for the first tracked product (general button)."""
        rows = self.db.get_all_tracked_products()
        if not rows:
            messagebox.showinfo("No Data",
                                 "No tracked products yet. Track a product first!")
            return
        # Show picker if multiple
        if len(rows) == 1:
            self._draw_history_graph(rows[0][0], rows[0][2])
        else:
            self._show_history_picker(rows)

    def _show_history_for_selected(self):
        """Show history for the selected tracked item."""
        sel = self.track_tree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a tracked product first.")
            return
        pid  = int(sel[0])
        name = self.track_tree.item(sel[0])["values"][0]
        self._draw_history_graph(pid, name)

    def _show_history_picker(self, rows):
        """Simple dialog to pick which product to graph."""
        win = tk.Toplevel(self.root)
        win.title("Select Product")
        win.geometry("360x240")
        win.config(bg=self._theme["bg"])

        tk.Label(win, text="Select a tracked product:",
                  font=("Segoe UI", 11, "bold"),
                  bg=self._theme["bg"], fg=self._theme["text"]).pack(pady=12)

        lb = tk.Listbox(win, font=("Segoe UI", 10),
                         bg=self._theme["surface"], fg=self._theme["text"],
                         selectbackground=self._theme["accent"],
                         relief="flat", bd=0, height=8)
        lb.pack(fill="both", expand=True, padx=16)
        for row in rows:
            lb.insert("end", f"{row[2][:30]}  —  {row[3]}")

        def _select():
            if not lb.curselection():
                return
            idx = lb.curselection()[0]
            pid  = rows[idx][0]
            name = rows[idx][2]
            win.destroy()
            self._draw_history_graph(pid, name)

        tk.Button(win, text="Show Graph", font=("Segoe UI", 10, "bold"),
                   bg=self._theme["accent"], fg="#fff", relief="flat",
                   bd=0, padx=12, pady=6, cursor="hand2",
                   command=_select).pack(pady=10)

    def _draw_history_graph(self, product_id: int, name: str):
        """Open a matplotlib window showing price-over-time chart."""
        history = self.db.get_price_history(product_id)
        stats   = self.tracker.get_price_stats(product_id)

        if not history or len(history) < 1:
            messagebox.showinfo("No History",
                                 "No price history yet for this product.\n"
                                 "Track it and wait for auto-refresh, or search again.")
            return

        from dateutil import parser as dp
        dates  = []
        prices = []
        for price, ts in history:
            try:
                dates.append(dp.parse(ts))
            except Exception:
                dates.append(datetime.now())
            prices.append(price)

        # Create popup window
        win = tk.Toplevel(self.root)
        win.title(f"Price History — {name[:40]}")
        win.geometry("820x500")
        win.config(bg=self._theme["bg"])

        is_dark = self._dark_mode
        bg_col  = "#0f0f17" if is_dark else "#f0f2f5"
        fg_col  = "#eaeaea" if is_dark else "#1a1a2e"
        grid_c  = "#2d2d4e" if is_dark else "#d0d4e0"
        line_c  = "#e94560" if is_dark else "#c0392b"
        fill_c  = "#e9456030" if is_dark else "#c0392b20"
        point_c = "#ffd700" if is_dark else "#e67e22"

        fig, ax = plt.subplots(figsize=(9, 4.2))
        fig.patch.set_facecolor(bg_col)
        ax.set_facecolor(bg_col)

        ax.plot(dates, prices, color=line_c, linewidth=2.5,
                 marker="o", markersize=6, markerfacecolor=point_c,
                 markeredgewidth=0, zorder=3)
        ax.fill_between(dates, prices, alpha=0.15, color=line_c)

        # Annotations
        if len(prices) >= 2:
            ax.axhline(min(prices), color="#00d4aa", linewidth=1,
                        linestyle="--", alpha=0.7, label=f"Lowest: ₹{min(prices):,.0f}")
            ax.axhline(max(prices), color="#ff4757", linewidth=1,
                        linestyle="--", alpha=0.7, label=f"Highest: ₹{max(prices):,.0f}")
            ax.legend(facecolor=bg_col, edgecolor=grid_c,
                       labelcolor=fg_col, fontsize=9)

        ax.set_title(f"Price History: {name[:45]}", color=fg_col,
                      fontsize=12, fontweight="bold", pad=12)
        ax.set_xlabel("Date / Time", color=fg_col, fontsize=9)
        ax.set_ylabel("Price (₹)", color=fg_col, fontsize=9)
        ax.tick_params(colors=fg_col, labelsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b %H:%M"))
        fig.autofmt_xdate(rotation=30)
        for spine in ax.spines.values():
            spine.set_edgecolor(grid_c)
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda x, _: f"₹{x:,.0f}"))
        ax.grid(color=grid_c, linewidth=0.5, alpha=0.6)

        # Stats sidebar
        if stats:
            info = (
                f"Latest:   ₹{stats['latest']:,.0f}\n"
                f"Lowest:   ₹{stats['lowest']:,.0f}\n"
                f"Highest:  ₹{stats['highest']:,.0f}\n"
                f"Average:  ₹{stats['average']:,.0f}\n"
                f"Records:  {stats['total_records']}\n"
                f"↓ From High: {stats['drop_from_high']:.1f}%"
            )
            ax.text(0.02, 0.98, info, transform=ax.transAxes,
                     fontsize=8.5, verticalalignment="top",
                     color=fg_col,
                     bbox=dict(boxstyle="round,pad=0.4",
                                facecolor=bg_col, edgecolor=grid_c, alpha=0.85))

        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        # Export button
        def _export_graph():
            path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG Image", "*.png")],
                initialfile=f"price_history_{product_id}.png")
            if path:
                fig.savefig(path, dpi=150, facecolor=bg_col)
                messagebox.showinfo("Saved", f"Graph saved to:\n{path}")

        tk.Button(win, text="💾 Save Graph as PNG",
                   font=("Segoe UI", 9, "bold"),
                   bg=self._theme["accent2"], fg="#fff",
                   relief="flat", bd=0, padx=12, pady=6, cursor="hand2",
                   command=_export_graph).pack(pady=(0, 10))

    # ──────────────────────────────────────────────
    # Export
    # ──────────────────────────────────────────────

    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV File", "*.csv")],
            initialfile="tracked_products.csv")
        if path:
            self.db.export_to_csv(path)
            messagebox.showinfo("Exported", f"Data exported to:\n{path}")

    # ──────────────────────────────────────────────
    # Auto-Refresh
    # ──────────────────────────────────────────────

    def _toggle_auto_refresh(self):
        if self._auto_refresh_on:
            self.tracker.stop_auto_refresh()
            self._auto_refresh_on = False
            self.btn_auto.config(text="▶ Auto-Refresh",
                                  bg=self._theme["accent2"])
            self._set_status("Auto-refresh stopped.")
        else:
            interval = simpledialog.askinteger(
                "Auto-Refresh Interval",
                "Refresh every how many minutes?",
                initialvalue=5, minvalue=1, maxvalue=60,
                parent=self.root)
            if not interval:
                return
            self._refresh_interval = interval
            self.tracker.start_auto_refresh(
                interval_minutes=interval,
                progress_cb=self._set_status)
            self._auto_refresh_on = True
            self.btn_auto.config(text=f"⏸ Auto ({interval}m)",
                                  bg="#006644")
            self._set_status(
                f"Auto-refresh active — every {interval} min.")

    # ──────────────────────────────────────────────
    # Alerts
    # ──────────────────────────────────────────────

    def _on_price_alert(self, alert: PriceAlert):
        """Called from tracker thread; schedule UI update on main thread."""
        self.root.after(0, lambda: self._show_alert_toast(alert))
        self.root.after(100, self._refresh_tracked_panel)

    def _show_alert_toast(self, alert: PriceAlert):
        """Display a modal alert for price drops."""
        icon  = "🎯" if alert.is_target_hit else "📉"
        title = "Target Price Reached!" if alert.is_target_hit else "Price Dropped!"
        msg   = alert.summary()
        messagebox.showinfo(f"{icon} {title}", msg)

    # ──────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────

    def _set_status(self, msg: str):
        self.root.after(0, lambda: self.lbl_status.config(text=msg))

    def _show_loading(self, show: bool):
        if show:
            self.progress.pack(after=self.lbl_loading, pady=4)
            self.lbl_loading.config(text="Fetching prices…")
            self.lbl_loading.pack()
            self.progress.start(10)
            self.btn_search.config(state="disabled")
        else:
            self.progress.stop()
            self.progress.pack_forget()
            self.lbl_loading.pack_forget()
            self.btn_search.config(state="normal")

    def _clear_placeholder(self, event):
        if self.search_var.get().startswith("e.g."):
            self.entry_search.delete(0, "end")

    def _restore_placeholder(self, event):
        if not self.search_var.get().strip():
            self.entry_search.insert(0, "e.g. iPhone 15, Samsung TV, Laptop…")

    def _tick_clock(self):
        now = datetime.now().strftime("%a %d %b %Y  %H:%M:%S")
        self.lbl_time.config(text=now)
        self.root.after(1000, self._tick_clock)

    def _on_close(self):
        self.tracker.stop_auto_refresh()
        self.root.destroy()

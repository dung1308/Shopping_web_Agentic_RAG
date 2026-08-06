import tkinter as tk
from tkinter import ttk, messagebox

class ScraperPipelineApp(tk.Frame):
    def __init__(self, parent=None):
        super().__init__(parent, bg="#0b0f19")
        self.parent = parent

        # Hook Agency 2026 Color Scheme
        self.bg_dark = "#0b0f19"
        self.card_bg = "#151d2a"
        self.accent_coral = "#f04b4c"
        self.accent_teal = "#7acfd6"
        self.accent_gold = "#ad974f"
        self.text_white = "#f8fafc"
        self.text_muted = "#94a3b8"

        self._build_header()
        self._build_content()

    def _build_header(self):
        header = tk.Frame(self, bg=self.bg_dark, pady=15, padx=20)
        header.pack(fill="x")

        tk.Label(header, text="🕷️ Playwright Scraping & Validation Pipeline", bg=self.bg_dark, fg=self.text_white, font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(header, text="Robots.txt compliance, Pydantic AI strict price checks & AuditFlag inspector (2026 Palette)", bg=self.bg_dark, fg=self.text_muted, font=("Segoe UI", 9)).pack(anchor="w")

    def _build_content(self):
        body = tk.Frame(self, bg=self.bg_dark, padx=20, pady=10)
        body.pack(fill="both", expand=True)

        cfg_panel = tk.Frame(body, bg=self.card_bg, highlightbackground="#1e293b", highlightthickness=1, padx=15, pady=15, width=340)
        cfg_panel.pack(side="left", fill="y", padx=(0, 10))
        cfg_panel.pack_propagate(False)

        tk.Label(cfg_panel, text="⚙️ Crawler Settings", bg=self.card_bg, fg=self.text_white, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 12))

        fields = [
            ("Target URL", "https://zara.com/vn/en/category/woman-bags"),
            ("Max Depth", "3 levels"),
            ("Concurrency Limit", "5 workers"),
            ("Min Price Bound", "50,000 VND"),
            ("Max Price Bound", "15,000,000 VND"),
        ]

        for label, default_val in fields:
            lbl = tk.Label(cfg_panel, text=label, bg=self.card_bg, fg=self.text_muted, font=("Segoe UI", 8, "bold"))
            lbl.pack(anchor="w", pady=(6, 2))
            ent = tk.Entry(cfg_panel, bg="#080d16", fg="#ffffff", font=("Segoe UI", 9), relief="flat", insertbackground="white")
            ent.insert(0, default_val)
            ent.pack(fill="x", ipady=4)

        tk.Label(cfg_panel, text="Governance Rules:", bg=self.card_bg, fg=self.text_muted, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(12, 4))
        
        c1 = tk.Checkbutton(cfg_panel, text="Enforce robots.txt strict compliance", bg=self.card_bg, fg=self.text_white, selectcolor=self.bg_dark, activebackground=self.card_bg)
        c1.select()
        c1.pack(anchor="w")

        c2 = tk.Checkbutton(cfg_panel, text="Reject expired promo dates (>365d)", bg=self.card_bg, fg=self.text_white, selectcolor=self.bg_dark, activebackground=self.card_bg)
        c2.select()
        c2.pack(anchor="w")

        tk.Button(cfg_panel, text="🚀 Launch Scraping Job", bg=self.accent_coral, fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", pady=6, command=self._launch_job).pack(fill="x", pady=(20, 5))
        tk.Button(cfg_panel, text="🧹 Clear Redis Cache", bg="#334155", fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", pady=5).pack(fill="x")

        right_panel = tk.Frame(body, bg=self.card_bg, highlightbackground="#1e293b", highlightthickness=1, padx=15, pady=15)
        right_panel.pack(side="right", fill="both", expand=True)

        tk.Label(right_panel, text="🚩 Pydantic AI Flagged Audit Violations", bg=self.card_bg, fg=self.text_white, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 10))

        columns = ("id", "store", "product", "rule", "found_val", "expected", "action")
        tree = ttk.Treeview(right_panel, columns=columns, show="headings", height=14)

        tree.heading("id", text="Flag ID")
        tree.heading("store", text="Store")
        tree.heading("product", text="Product Title")
        tree.heading("rule", text="Violated Rule")
        tree.heading("found_val", text="Scraped Data")
        tree.heading("expected", text="Valid Bound")
        tree.heading("action", text="Status")

        tree.column("id", width=70, anchor="center")
        tree.column("store", width=90)
        tree.column("product", width=160)
        tree.column("rule", width=130)
        tree.column("found_val", width=100, anchor="center")
        tree.column("expected", width=100, anchor="center")
        tree.column("action", width=80, anchor="center")

        sample_flags = [
            ("FLG-102", "Zara VN", "Leather Jacket XL", "MAX_PRICE_BOUND", "22,500,000", "< 15,000,000", "FLAGGED"),
            ("FLG-103", "Uniqlo", "Graphic Tee Sale", "INVALID_DATE_RANGE", "2024-01-01 -> 2028-01-01", "Max 1 Year", "FLAGGED"),
            ("FLG-104", "Nike Mall", "Air Jordan 1 Retro", "NULL_MANDATORY_FIELD", "image_url = None", "Required String", "OVERRIDDEN"),
            ("FLG-105", "Adidas", "UltraBoost 22", "PRICE_CORRUPTED", "-500 VND", "> 0 VND", "REJECTED"),
        ]

        for item in sample_flags:
            tree.insert("", "end", values=item)

        tree.pack(fill="both", expand=True, pady=(0, 10))

        detail_box = tk.Frame(right_panel, bg="#080d16", padx=10, pady=8)
        detail_box.pack(fill="x")
        tk.Label(detail_box, text="Selected Flag Details: FLG-102 (Zara VN)", bg="#080d16", fg=self.accent_teal, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(detail_box, text="Reason: Product price 22,500,000 VND exceeds maximum threshold configured for category 'Fashion'. Requires admin manual override approval before indexer step.", bg="#080d16", fg=self.text_muted, font=("Segoe UI", 8)).pack(anchor="w")

    def _launch_job(self):
        messagebox.showinfo("Job Queued", "Playwright scraping worker has been queued for execution.")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Playwright Ingestion Scraper Inspector")
    root.geometry("1100x720")
    app = ScraperPipelineApp(root)
    app.pack(fill="both", expand=True)
    root.mainloop()

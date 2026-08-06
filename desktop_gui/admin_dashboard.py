import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import time

class MallAdminDashboard(tk.Frame):
    def __init__(self, parent=None):
        super().__init__(parent, bg="#0f172a")
        self.parent = parent
        
        # 2026 Hook Agency Palette Tokens
        self.bg_dark = "#0f172a"
        self.card_bg = "#1e293b"
        self.accent_coral = "#f04b4c"    # Hook Agency Coral Red
        self.accent_teal = "#7acfd6"     # Hook Agency Blue Beans Teal
        self.accent_gold = "#ad974f"     # Hook Agency Luxury Gold
        self.accent_green = "#10b981"    # Mint Success Green
        self.text_white = "#f8fafc"
        self.text_muted = "#94a3b8"

        self._build_header()
        self._build_metrics()
        self._build_main_content()
        self._build_footer()

    def _build_header(self):
        header_frame = tk.Frame(self, bg=self.bg_dark, pady=15, padx=20)
        header_frame.pack(fill="x")

        left_hdr = tk.Frame(header_frame, bg=self.bg_dark)
        left_hdr.pack(side="left")

        title = tk.Label(left_hdr, text="🛒 Mall RAG Governance Dashboard", font=("Segoe UI", 16, "bold"), bg=self.bg_dark, fg=self.text_white)
        title.pack(anchor="w")
        sub = tk.Label(left_hdr, text="Real-time Scrape Pipeline, Audit Flags & Vector Store Status", font=("Segoe UI", 9), bg=self.bg_dark, fg=self.text_muted)
        sub.pack(anchor="w")

        badge_frame = tk.Frame(header_frame, bg=self.bg_dark)
        badge_frame.pack(side="right")

        services = [("FastAPI", self.accent_green), ("ChromaDB", self.accent_teal), ("Neon DB", self.accent_gold), ("Redis", self.accent_coral)]
        for name, color in services:
            b = tk.Label(badge_frame, text=f"● {name}", bg=self.card_bg, fg=color, font=("Segoe UI", 9, "bold"), padx=10, pady=4)
            b.pack(side="left", padx=4)

    def _build_metrics(self):
        metrics_frame = tk.Frame(self, bg=self.bg_dark, padx=20, pady=5)
        metrics_frame.pack(fill="x")

        metrics_data = [
            ("Total Products", "14,280", "+128 today", self.accent_teal),
            ("Active Audit Flags", "24 Items", "3 Critical Price Violations", self.accent_coral),
            ("Scrape Job Rate", "45 URLs/min", "Playwright Playback Active", self.accent_gold),
            ("Vector Index Health", "99.8%", "1024-dim bge-m3 dense", self.accent_green),
        ]

        for i, (title, val, sub, color) in enumerate(metrics_data):
            card = tk.Frame(metrics_frame, bg=self.card_bg, highlightbackground="#334155", highlightthickness=1, padx=15, pady=12)
            card.pack(side="left", fill="both", expand=True, padx=5 if i > 0 else 0)

            stripe = tk.Frame(card, bg=color, width=4)
            stripe.pack(side="left", fill="y", padx=(0, 10))

            info_f = tk.Frame(card, bg=self.card_bg)
            info_f.pack(side="left", fill="both", expand=True)

            lbl_t = tk.Label(info_f, text=title, bg=self.card_bg, fg=self.text_muted, font=("Segoe UI", 9))
            lbl_t.pack(anchor="w")
            lbl_v = tk.Label(info_f, text=val, bg=self.card_bg, fg=self.text_white, font=("Segoe UI", 16, "bold"))
            lbl_v.pack(anchor="w")
            lbl_s = tk.Label(info_f, text=sub, bg=self.card_bg, fg=color, font=("Segoe UI", 8))
            lbl_s.pack(anchor="w")

    def _build_main_content(self):
        content = tk.Frame(self, bg=self.bg_dark, padx=20, pady=15)
        content.pack(fill="both", expand=True)

        left_pan = tk.Frame(content, bg=self.card_bg, highlightbackground="#334155", highlightthickness=1, padx=12, pady=12)
        left_pan.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tbl_hdr = tk.Frame(left_pan, bg=self.card_bg)
        tbl_hdr.pack(fill="x", pady=(0, 8))
        tk.Label(tbl_hdr, text="⚡ Active Scraping & Ingestion Pipeline", bg=self.card_bg, fg=self.text_white, font=("Segoe UI", 11, "bold")).pack(side="left")

        btn_f = tk.Frame(tbl_hdr, bg=self.card_bg)
        btn_f.pack(side="right")
        tk.Button(btn_f, text="▶ Start Crawl", bg=self.accent_green, fg="#000", font=("Segoe UI", 8, "bold"), relief="flat", command=self._trigger_crawl, padx=8, pady=2).pack(side="left", padx=2)
        tk.Button(btn_f, text="⏹ Stop All", bg=self.accent_coral, fg="#fff", font=("Segoe UI", 8, "bold"), relief="flat", command=self._stop_crawl, padx=8, pady=2).pack(side="left", padx=2)

        tree_scroll = ttk.Scrollbar(left_pan)
        tree_scroll.pack(side="right", fill="y")

        self.tree = ttk.Treeview(left_pan, columns=("job_id", "domain", "status", "scraped", "flags"), show="headings", yscrollcommand=tree_scroll.set, height=12)
        tree_scroll.config(command=self.tree.yview)

        self.tree.heading("job_id", text="Job ID")
        self.tree.heading("domain", text="Store Domain")
        self.tree.heading("status", text="Status")
        self.tree.heading("scraped", text="Products")
        self.tree.heading("flags", text="Audit Flags")

        self.tree.column("job_id", width=80, anchor="center")
        self.tree.column("domain", width=160, anchor="w")
        self.tree.column("status", width=100, anchor="center")
        self.tree.column("scraped", width=80, anchor="center")
        self.tree.column("flags", width=90, anchor="center")

        sample_jobs = [
            ("JOB-9012", "zara.com.vn", "RUNNING", "1,240", "2 Price Warn"),
            ("JOB-9013", "uniqlo.com/vn", "INDEXING", "890", "1 Date Err"),
            ("JOB-9014", "nike.com.vn", "COMPLETED", "430", "0 Clean"),
            ("JOB-9015", "adidas.com.vn", "QUEUED", "0", "0 Pending"),
            ("JOB-9016", "sephora.vn", "FAILED", "42", "4 Invalid URL"),
        ]

        for item in sample_jobs:
            self.tree.insert("", "end", values=item)

        self.tree.pack(fill="both", expand=True)

        right_pan = tk.Frame(content, bg=self.card_bg, highlightbackground="#334155", highlightthickness=1, padx=12, pady=12)
        right_pan.pack(side="right", fill="both", expand=True)

        tk.Label(right_pan, text="📜 Live Ingestion Audit Logs", bg=self.card_bg, fg=self.text_white, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 8))

        self.log_area = scrolledtext.ScrolledText(right_pan, bg="#0d1424", fg=self.accent_teal, font=("Consolas", 9), relief="flat", insertbackground="white")
        self.log_area.pack(fill="both", expand=True)

        initial_logs = (
            "[2026-08-01 22:23:01] INFO [Scraper] Initiated Playwright Chromium headless task...\n"
            "[2026-08-01 22:23:03] INFO [Validator] Validating Pydantic schema for 'Fashion' category...\n"
            "[2026-08-01 22:23:05] WARN [AuditFlag] Store 'zara.com.vn' product #8911 price bound check failed: 15,000,000 VND > 10,000,000 VND cap!\n"
            "[2026-08-01 22:23:07] INFO [Indexer] ChromaDB upsert batch: 128 vectors (1024-dim) inserted successfully.\n"
            "[2026-08-01 22:23:10] INFO [Redis] Invalidating session cache key `mall_products_floor2`...\n"
        )
        self.log_area.insert("end", initial_logs)

    def _build_footer(self):
        footer = tk.Frame(self, bg="#080c16", padx=20, pady=6)
        footer.pack(fill="x", side="bottom")

        tk.Label(footer, text="Dual-View Agentic RAG System • Environment: Production • Port: 8000", bg="#080c16", fg=self.text_muted, font=("Segoe UI", 8)).pack(side="left")
        tk.Label(footer, text="System Time: 2026-08-01 22:23:00", bg="#080c16", fg=self.accent_coral, font=("Segoe UI", 8, "bold")).pack(side="right")

    def _trigger_crawl(self):
        self.log_area.insert("end", f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] INFO [ManualTrigger] Admin triggered full mall catalog re-crawl.\n")
        self.log_area.see("end")
        messagebox.showinfo("Crawl Started", "Scraper job queued successfully across 5 mall tenant domains.")

    def _stop_crawl(self):
        self.log_area.insert("end", f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] WARN [ManualTrigger] Admin issued EMERGENCY STOP signal to scraper worker pool.\n")
        self.log_area.see("end")
        messagebox.showwarning("Crawl Stopped", "Scraper worker tasks terminated.")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Shopping Mall AI — Admin Governance Dashboard")
    root.geometry("1100x720")
    app = MallAdminDashboard(root)
    app.pack(fill="both", expand=True)
    root.mainloop()

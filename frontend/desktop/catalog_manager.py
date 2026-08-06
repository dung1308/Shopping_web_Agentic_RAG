import tkinter as tk
from tkinter import ttk, messagebox

class CatalogManagerApp(tk.Frame):
    def __init__(self, parent=None):
        super().__init__(parent, bg="#0b0f19")
        self.parent = parent

        # 2026 Hook Agency Color Tokens
        self.bg_dark = "#0b0f19"
        self.card_bg = "#151d2a"
        self.accent_coral = "#f04b4c"
        self.accent_teal = "#7acfd6"
        self.accent_gold = "#ad974f"
        self.text_white = "#f8fafc"
        self.text_muted = "#94a3b8"

        self._build_header()
        self._build_tabs()

    def _build_header(self):
        header = tk.Frame(self, bg=self.bg_dark, pady=15, padx=20)
        header.pack(fill="x")

        tk.Label(header, text="📦 Store Inventory & Audit Override Management", bg=self.bg_dark, fg=self.text_white, font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(header, text="Review catalog compliance, force manual overrides, configure category price limits (2026 Theme)", bg=self.bg_dark, fg=self.text_muted, font=("Segoe UI", 9)).pack(anchor="w")

    def _build_tabs(self):
        body = tk.Frame(self, bg=self.bg_dark, padx=20, pady=10)
        body.pack(fill="both", expand=True)

        notebook = ttk.Notebook(body)
        notebook.pack(fill="both", expand=True)

        t1 = tk.Frame(notebook, bg=self.card_bg, padx=15, pady=15)
        notebook.add(t1, text="  🏬 Products Directory  ")
        self._build_tab1(t1)

        t2 = tk.Frame(notebook, bg=self.card_bg, padx=15, pady=15)
        notebook.add(t2, text="  ⚖️ Category Price Bounds  ")
        self._build_tab2(t2)

        t3 = tk.Frame(notebook, bg=self.card_bg, padx=15, pady=15)
        notebook.add(t3, text="  ✍️ Admin Overrides  ")
        self._build_tab3(t3)

    def _build_tab1(self, parent):
        top_bar = tk.Frame(parent, bg=self.card_bg)
        top_bar.pack(fill="x", pady=(0, 10))

        tk.Label(top_bar, text="Filter by Store:", bg=self.card_bg, fg=self.text_white, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))
        cbox = ttk.Combobox(top_bar, values=["All Stores (14,280 items)", "Zara (1,240 items)", "Uniqlo (890 items)", "Nike (430 items)"])
        cbox.current(0)
        cbox.pack(side="left", padx=(0, 15))

        tk.Button(top_bar, text="✏️ Edit Selected Item", bg="#3b82f6", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=10, pady=3, command=self._edit_item).pack(side="left")
        tk.Button(top_bar, text="✅ Batch Approve Compliant", bg=self.accent_coral, fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=10, pady=3).pack(side="right")

        cols = ("sku", "title", "category", "price", "discount", "floor", "status")
        tree = ttk.Treeview(parent, columns=cols, show="headings", height=14)

        tree.heading("sku", text="SKU Code")
        tree.heading("title", text="Product Title")
        tree.heading("category", text="Category")
        tree.heading("price", text="Price (VND)")
        tree.heading("discount", text="Discount Tag")
        tree.heading("floor", text="Floor Location")
        tree.heading("status", text="Audit Status")

        tree.column("sku", width=90, anchor="center")
        tree.column("title", width=180)
        tree.column("category", width=100, anchor="center")
        tree.column("price", width=110, anchor="e")
        tree.column("discount", width=100, anchor="center")
        tree.column("floor", width=90, anchor="center")
        tree.column("status", width=110, anchor="center")

        sample_products = [
            ("SKU-9901", "Zara Basic Cotton T-Shirt", "Fashion", "399,000", "None", "Floor 2", "COMPLIANT"),
            ("SKU-9902", "Uniqlo Ultra Light Down", "Fashion", "1,490,000", "10% OFF", "Floor 2", "COMPLIANT"),
            ("SKU-9903", "Nike Air Force 1 '07", "Footwear", "2,929,000", "None", "Floor 1", "COMPLIANT"),
            ("SKU-9904", "Sony WH-1000XM5 Headphone", "Electronics", "8,490,000", "SALE", "Floor 3", "PRICE_FLAGGED"),
            ("SKU-9905", "Starbucks Reserve Tumbler", "Food & Bev", "650,000", "5% OFF", "Floor 1", "COMPLIANT"),
        ]

        for item in sample_products:
            tree.insert("", "end", values=item)

        tree.pack(fill="both", expand=True)

    def _build_tab2(self, parent):
        tk.Label(parent, text="Category Minimum & Maximum Price Bounds (VND)", bg=self.card_bg, fg=self.text_white, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 10))

        rules = [
            ("Fashion & Apparel", "50,000 VND", "15,000,000 VND"),
            ("Footwear & Shoes", "100,000 VND", "25,000,000 VND"),
            ("Electronics & Gadgets", "100,000 VND", "100,000,000 VND"),
            ("Food & Beverage", "10,000 VND", "5,000,000 VND"),
            ("Jewelry & Luxury", "500,000 VND", "500,000,000 VND"),
        ]

        for cat, min_p, max_p in rules:
            r = tk.Frame(parent, bg="#080d16", padx=12, pady=10)
            r.pack(fill="x", pady=4)
            tk.Label(r, text=f"🏷️ {cat}", bg="#080d16", fg=self.text_white, font=("Segoe UI", 9, "bold"), width=25, anchor="w").pack(side="left")
            tk.Label(r, text=f"Min: {min_p}", bg="#080d16", fg=self.accent_teal, font=("Segoe UI", 9)).pack(side="left", padx=20)
            tk.Label(r, text=f"Max: {max_p}", bg="#080d16", fg=self.accent_coral, font=("Segoe UI", 9)).pack(side="left", padx=20)
            tk.Button(r, text="Configure", bg="#334155", fg="white", font=("Segoe UI", 8), relief="flat", padx=8).pack(side="right")

    def _build_tab3(self, parent):
        tk.Label(parent, text="Recent Admin Manual Overrides & Audit Log", bg=self.card_bg, fg=self.text_white, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 10))
        
        txt = tk.Text(parent, bg="#080d16", fg="#e2e8f0", font=("Consolas", 9), relief="flat")
        txt.pack(fill="both", expand=True)
        txt.insert("end", "[2026-08-01 22:23:12] ADMIN 'admin_user1' OVERRODE Flag FLG-099 on SKU-9904 (Sony XM5): Reason 'Confirmed luxury electronics exception with tenant manager'. Status changed FLAGGED -> APPROVED.\n")

    def _edit_item(self):
        messagebox.showinfo("Edit Item", "Product parameters modal opened for item SKU-9904.")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Store Inventory & Audit Override Management")
    root.geometry("1100x720")
    app = CatalogManagerApp(root)
    app.pack(fill="both", expand=True)
    root.mainloop()

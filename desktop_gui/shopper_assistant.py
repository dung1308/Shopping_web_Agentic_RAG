import tkinter as tk
from tkinter import ttk, scrolledtext

class ShopperAssistantApp(tk.Frame):
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
        self._build_main_split()

    def _build_header(self):
        header = tk.Frame(self, bg=self.bg_dark, pady=15, padx=20)
        header.pack(fill="x")

        title_frame = tk.Frame(header, bg=self.bg_dark)
        title_frame.pack(side="left")
        
        tk.Label(title_frame, text="✨ Mall Concierge AI (2026 Hook Agency Palette)", bg=self.bg_dark, fg=self.text_white, font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(title_frame, text="Ask anything about stores, products, locations & promotions in VinMall", bg=self.bg_dark, fg=self.text_muted, font=("Segoe UI", 9)).pack(anchor="w")

        tk.Label(header, text="📍 Location: Floor 2 (Central Atrium)", bg="#25161c", fg=self.accent_coral, font=("Segoe UI", 9, "bold"), padx=12, pady=6).pack(side="right")

    def _build_main_split(self):
        body = tk.Frame(self, bg=self.bg_dark, padx=20, pady=10)
        body.pack(fill="both", expand=True)

        chat_col = tk.Frame(body, bg=self.card_bg, highlightbackground="#1e293b", highlightthickness=1, padx=12, pady=12)
        chat_col.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(chat_col, text="💬 Conversational Search", bg=self.card_bg, fg=self.text_white, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 8))

        self.chat_display = scrolledtext.ScrolledText(chat_col, bg="#080d16", fg="#e2e8f0", font=("Segoe UI", 10), relief="flat", wrap="word")
        self.chat_display.pack(fill="both", expand=True, pady=(0, 10))

        self.chat_display.insert("end", "🤖 Mall AI: Hello! Welcome to VinMall. What are you looking for today?\n\n")
        self.chat_display.insert("end", "👤 You: Where can I find a leather bag under 800k on Floor 2?\n\n")
        self.chat_display.insert("end", "🤖 Mall AI: I found 3 great matching items at Pedro (Floor 2, Unit 204) and Charles & Keith (Floor 2, Unit 210)! Check out the product cards on the right. 👇\n\n")

        input_frame = tk.Frame(chat_col, bg=self.card_bg)
        input_frame.pack(fill="x")

        self.input_entry = tk.Entry(input_frame, bg="#1e293b", fg="#ffffff", font=("Segoe UI", 10), relief="flat", insertbackground="white")
        self.input_entry.pack(side="left", fill="x", expand=True, ipady=7, padx=5)
        self.input_entry.insert(0, "Search discount shoes on Floor 1...")

        send_btn = tk.Button(input_frame, text="Send ➔", bg=self.accent_coral, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=5, command=self._send_message)
        send_btn.pack(side="right", padx=(5, 0))

        cards_col = tk.Frame(body, bg=self.card_bg, highlightbackground="#1e293b", highlightthickness=1, padx=12, pady=12)
        cards_col.pack(side="right", fill="both", expand=True)

        filter_bar = tk.Frame(cards_col, bg=self.card_bg)
        filter_bar.pack(fill="x", pady=(0, 12))

        tk.Label(filter_bar, text="Filters:", bg=self.card_bg, fg=self.text_muted, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))
        for tag in ["All Floors", "Floor 2 Only", "< 800k VND", "Fashion & Bags", "On Sale 🔥"]:
            btn = tk.Label(filter_bar, text=tag, bg="#1e293b", fg="#cbd5e1", font=("Segoe UI", 8, "bold"), padx=8, pady=3)
            btn.pack(side="left", padx=3)

        grid_container = tk.Frame(cards_col, bg=self.card_bg)
        grid_container.pack(fill="both", expand=True)

        products = [
            ("Pedro Elegant Tote Bag", "790,000 VND", "Pedro Store", "Floor 2 • Unit 204", "15% OFF", self.accent_coral),
            ("Charles & Keith Clutch", "750,000 VND", "C&K Boutique", "Floor 2 • Unit 210", "BEST SELLER", self.accent_teal),
            ("Vascara Leather Crossbody", "680,000 VND", "Vascara", "Floor 2 • Unit 218", "20% OFF", self.accent_gold),
            ("LYN Modern Shoulder Bag", "820,000 VND", "LYN Vietnam", "Floor 2 • Unit 202", "NEW", "#10b981"),
        ]

        for idx, (title, price, store, unit, badge, bcolor) in enumerate(products):
            row = idx // 2
            col = idx % 2

            card = tk.Frame(grid_container, bg="#080d16", highlightbackground="#334155", highlightthickness=1, padx=10, pady=10)
            card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
            grid_container.grid_columnconfigure(col, weight=1)
            grid_container.grid_rowconfigure(row, weight=1)

            top_f = tk.Frame(card, bg="#080d16")
            top_f.pack(fill="x")
            tk.Label(top_f, text=badge, bg=bcolor, fg="#000000", font=("Segoe UI", 7, "bold"), padx=6, pady=1).pack(side="left")
            tk.Label(top_f, text=unit, bg="#080d16", fg=self.text_muted, font=("Segoe UI", 8)).pack(side="right")

            tk.Label(card, text=title, bg="#080d16", fg=self.text_white, font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x", pady=(6, 2))
            tk.Label(card, text=f"🏷️ {price}", bg="#080d16", fg=self.accent_teal, font=("Segoe UI", 11, "bold"), anchor="w").pack(fill="x")
            tk.Label(card, text=f"🏬 {store}", bg="#080d16", fg=self.text_muted, font=("Segoe UI", 8), anchor="w").pack(fill="x", pady=(0, 6))

            tk.Button(card, text="📍 Directions to Store", bg="#1e293b", fg="#ffffff", font=("Segoe UI", 8, "bold"), relief="flat", padx=6, pady=3).pack(fill="x")

    def _send_message(self):
        msg = self.input_entry.get()
        if msg:
            self.chat_display.insert("end", f"👤 You: {msg}\n\n")
            self.chat_display.insert("end", "🤖 Mall AI: Searching vector store for relevant matching items...\n\n")
            self.chat_display.see("end")
            self.input_entry.delete(0, "end")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Shopping Mall Assistant — Desktop Shopper Hub")
    root.geometry("1100x720")
    app = ShopperAssistantApp(root)
    app.pack(fill="both", expand=True)
    root.mainloop()

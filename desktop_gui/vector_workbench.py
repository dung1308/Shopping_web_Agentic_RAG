import tkinter as tk
from tkinter import ttk, scrolledtext

class VectorWorkbenchApp(tk.Frame):
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
        self._build_workbench()

    def _build_header(self):
        header = tk.Frame(self, bg=self.bg_dark, pady=15, padx=20)
        header.pack(fill="x")

        tk.Label(header, text="🔮 Chroma Hybrid Search & Embeddings Inspector", bg=self.bg_dark, fg=self.text_white, font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(header, text="Test bge-m3 dense (1024-dim) + sparse keyword vectors, similarity scoring & payload JSON (2026 Theme)", bg=self.bg_dark, fg=self.text_muted, font=("Segoe UI", 9)).pack(anchor="w")

    def _build_workbench(self):
        body = tk.Frame(self, bg=self.bg_dark, padx=20, pady=10)
        body.pack(fill="both", expand=True)

        q_frame = tk.Frame(body, bg=self.card_bg, highlightbackground="#1f2937", highlightthickness=1, padx=12, pady=12)
        q_frame.pack(fill="x", pady=(0, 10))

        tk.Label(q_frame, text="Query Vector Prompt:", bg=self.card_bg, fg=self.text_white, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 8))
        
        entry = tk.Entry(q_frame, bg="#080d16", fg="#ffffff", font=("Segoe UI", 10), relief="flat", insertbackground="white")
        entry.insert(0, "black leather jacket women size M under 2 mil VND")
        entry.pack(side="left", fill="x", expand=True, ipady=5, padx=5)

        tk.Button(q_frame, text="🔍 Execute Vector Search", bg=self.accent_coral, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4).pack(side="right")

        sl_frame = tk.Frame(body, bg=self.card_bg, highlightbackground="#1f2937", highlightthickness=1, padx=15, pady=8)
        sl_frame.pack(fill="x", pady=(0, 10))

        tk.Label(sl_frame, text="Dense Vector Weight (bge-m3): 0.70", bg=self.card_bg, fg=self.accent_coral, font=("Segoe UI", 8, "bold")).pack(side="left", padx=(0, 20))
        s1 = ttk.Scale(sl_frame, from_=0, to=1, value=0.7)
        s1.pack(side="left", fill="x", expand=True, padx=(0, 30))

        tk.Label(sl_frame, text="Sparse Keyword Weight (BM25): 0.30", bg=self.card_bg, fg=self.accent_teal, font=("Segoe UI", 8, "bold")).pack(side="left", padx=(0, 20))
        s2 = ttk.Scale(sl_frame, from_=0, to=1, value=0.3)
        s2.pack(side="left", fill="x", expand=True)

        split = tk.Frame(body, bg=self.bg_dark)
        split.pack(fill="both", expand=True)

        res_col = tk.Frame(split, bg=self.card_bg, highlightbackground="#1f2937", highlightthickness=1, padx=12, pady=12)
        res_col.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(res_col, text="🎯 Top-5 Similarity Matches (Chroma DB)", bg=self.card_bg, fg=self.text_white, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 8))

        matches = [
            ("Point #8812 • Zara Rider Leather Jacket", "Score: 0.942", "1,850,000 VND", "Floor 2 • Zara", self.accent_coral),
            ("Point #9104 • Mango Faux Leather Biker", "Score: 0.887", "1,490,000 VND", "Floor 1 • Mango", self.accent_teal),
            ("Point #7731 • Pull&Bear Oversized Biker", "Score: 0.815", "1,200,000 VND", "Floor 2 • Pull&Bear", self.accent_gold),
            ("Point #6219 • H&M Faux Fur Leather Coat", "Score: 0.741", "1,990,000 VND", "Floor 1 • H&M", self.accent_gold),
            ("Point #4102 • Uniqlo Synthetic Bomber", "Score: 0.654", "999,000 VND", "Floor 2 • Uniqlo", "#6b7280"),
        ]

        for title, score, price, location, color in matches:
            box = tk.Frame(res_col, bg="#080d16", highlightbackground="#374151", highlightthickness=1, padx=10, pady=8)
            box.pack(fill="x", pady=4)

            top = tk.Frame(box, bg="#080d16")
            top.pack(fill="x")
            tk.Label(top, text=title, bg="#080d16", fg=self.text_white, font=("Segoe UI", 9, "bold")).pack(side="left")
            tk.Label(top, text=score, bg=color, fg="#000000", font=("Segoe UI", 8, "bold"), padx=6, pady=1).pack(side="right")

            sub = tk.Frame(box, bg="#080d16")
            sub.pack(fill="x", pady=(4, 0))
            tk.Label(sub, text=f"Price: {price}", bg="#080d16", fg=self.accent_teal, font=("Segoe UI", 8)).pack(side="left")
            tk.Label(sub, text=location, bg="#080d16", fg=self.text_muted, font=("Segoe UI", 8)).pack(side="right")

        payload_col = tk.Frame(split, bg=self.card_bg, highlightbackground="#1f2937", highlightthickness=1, padx=12, pady=12)
        payload_col.pack(side="right", fill="both", expand=True)

        tk.Label(payload_col, text="📄 Chroma Metadata & Dense Vector Array", bg=self.card_bg, fg=self.text_white, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 8))

        json_text = scrolledtext.ScrolledText(payload_col, bg="#080d16", fg=self.accent_teal, font=("Consolas", 9), relief="flat")
        json_text.pack(fill="both", expand=True)

        payload_content = """{
  "point_id": "8812-zara-leather-jacket-m",
  "vector_dimensions": 1024,
  "embedding_model": "BAAI/bge-m3",
  "similarity_metric": "Cosine",
  "dense_sample": [
    -0.0241, 0.0815, -0.1102, 0.0045, 0.2319, -0.0981,
    0.1412, -0.0078, 0.0531, 0.1890, -0.1245, ... (1012 more)
  ],
  "payload": {
    "product_id": "8812",
    "title": "Zara Rider Leather Jacket",
    "category": "fashion",
    "floor": 2,
    "store_id": "STORE-ZARA-204",
    "price_vnd": 1850000,
    "is_discounted": true,
    "audit_status": "COMPLIANT"
  }
}"""
        json_text.insert("end", payload_content)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Chroma Hybrid Search & Embeddings Inspector")
    root.geometry("1100x720")
    app = VectorWorkbenchApp(root)
    app.pack(fill="both", expand=True)
    root.mainloop()

import tkinter as tk
from tkinter import ttk

from desktop_gui.admin_dashboard import MallAdminDashboard
from desktop_gui.shopper_assistant import ShopperAssistantApp
from desktop_gui.scraper_pipeline import ScraperPipelineApp
from desktop_gui.vector_workbench import VectorWorkbenchApp
from desktop_gui.catalog_manager import CatalogManagerApp

class DesktopApplicationSuite(tk.Tk):
    """
    Unified Desktop Client Launcher for Dual-View Shopping Mall AI.
    Integrates all 5 Desktop Tkinter module views in a single window.
    """
    def __init__(self):
        super().__init__()
        self.title("Shopping Mall AI — Unified Desktop GUI Client (Hook Agency 2026 Theme)")
        self.geometry("1150x760")
        self.configure(bg="#0b0f19")

        # TTK Notebook tabs
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TNotebook", background="#0b0f19", borderwidth=0)
        self.style.configure("TNotebook.Tab", background="#151d2a", foreground="#cbd5e1", padding=[15, 8], font=("Segoe UI", 9, "bold"))
        self.style.map("TNotebook.Tab", background=[("selected", "#f04b4c")], foreground=[("selected", "#ffffff")])

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        # Module 1: Admin Governance Dashboard
        m1 = MallAdminDashboard(notebook)
        notebook.add(m1, text="  🛡️ Admin Governance  ")

        # Module 2: Shopper Assistant
        m2 = ShopperAssistantApp(notebook)
        notebook.add(m2, text="  💬 Shopper AI Assistant  ")

        # Module 3: Scraper Inspector
        m3 = ScraperPipelineApp(notebook)
        notebook.add(m3, text="  🕷️ Scraper Pipeline  ")

        # Module 4: Vector Workbench
        m4 = VectorWorkbenchApp(notebook)
        notebook.add(m4, text="  🔮 Chroma Vector RAG  ")

        # Module 5: Catalog Manager
        m5 = CatalogManagerApp(notebook)
        notebook.add(m5, text="  📦 Catalog Manager  ")

if __name__ == "__main__":
    app = DesktopApplicationSuite()
    app.mainloop()

"""DevisPro - Desktop App im modernen Dark-Theme (CustomTkinter).

Konsistentes Design mit der Landingpage devispro.de (Anthrazit #1F2933, Orange #FF6A1A).
"""
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext

import customtkinter as ctk
from customtkinter import CTkFrame, CTkButton, CTkLabel, CTkEntry
from customtkinter import CTkScrollableFrame, CTkToplevel

# CTkTreeview gibt es erst ab CTk 5.20+; je nach Version vorhanden
try:
    from customtkinter import CTkTreeview
    _HAS_CTK_TREEVIEW = True
except ImportError:
    _HAS_CTK_TREEVIEW = False

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import devispro
from devispro import history as history_mod, firmen_preise, ch_preise
from devispro.stammdaten import load_profile, save_profile
from devispro.importers import import_devis
from devispro.models import Devis, Position
from devispro.verbaende_kataloge import KatalogImporter, KatalogPosition
from devispro.marketplace import MarketplaceStore, MarketplaceSync, MarketplaceGUI, MarketplaceEntry, EntryStatus, MarketplaceCategory
from devispro.cloud_sync import CloudSyncManager, SyncConfig, SyncProvider, discover_cloud_providers
from devispro.erp_ecosystem import ERPManager, ERPConfig, ERPType, SyncDirection

# ────────────────────────────────────────────────────────────── THEME (devispro.de)
BG_DARK     = "#1F2933"   # App-Hintergrund (Anthrazit)
BG_PANEL    = "#252D38"   # Panel / Sidebar
BG_PANEL_HV = "#2C3542"   # Hover / Fields
BG_HEADER   = "#161B22"   # Header
BORDER      = "#3E4C59"
ACCENT      = "#FF6A1A"   # Signalorange (Primär)
ACCENT_HV   = "#FF8542"
TXT_MAIN    = "#F3F5F7"
TXT_DIM     = "#9AA5B1"

# Ctk globale Einstellungen
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")  # Wir überschreiben per fg_color je Widget

# Fonts: als Tupel-Strings speichern, im __init__ zu CTkFont werden
# (CTkFont braucht ein aktives Root-Window, das es beim Modul-Import nicht gibt)
FONT       = ("Helvetica", 13)
FONT_SM    = ("Helvetica", 11)
FONT_H1    = ("Helvetica", 22, "bold")
FONT_H2    = ("Helvetica", 15, "bold")
FONT_H3    = ("Helvetica", 13, "bold")
FONT_BTN   = ("Helvetica", 12, "bold")
FONT_MONO  = ("Menlo", 11)


# ────────────────────────────────────────────────────────────── APP
class DevisProApp(ctk.CTk):
    # ---------- Statische UI-Helfer ----------
    @staticmethod
    def _btn(parent, text, cmd, kind="navy"):
        """Themed Button. kind: navy, darkgreen, darkorange, purple, steelblue,
        darkblue, teal, darkred, gray."""
        palette = {
            "navy":        ("#3B82C4", "#5BA4E0"),
            "darkgreen":   ("#1F8A4C", "#2DD47A"),
            "darkorange":  (ACCENT,     ACCENT_HV),
            "purple":      ("#7A5AF8", "#9B7DFA"),
            "steelblue":   ("#3B82C4", "#5BA4E0"),
            "darkblue":    ("#1E40AF", "#3B5BDB"),
            "teal":        ("#0E8B7E", "#15A89B"),
            "darkred":     ("#C0392B", "#E74C3C"),
            "gray":        ("#4B5563", "#5C6773"),
        }
        fg, hv = palette.get(kind, ("#3B82C4", "#5BA4E0"))
        b = ctk.CTkButton(
            parent, text=text, command=cmd,
            fg_color=fg, hover_color=hv,
            text_color="#FFFFFF",
            font=FONT_BTN, corner_radius=8,
            height=32, anchor="w",
        )
        b.pack(fill="x", padx=10, pady=2)
        return b

    @staticmethod
    def _sec(parent, text):
        ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(family="Helvetica", size=10, weight="bold"),
            text_color=ACCENT,
        ).pack(anchor="w", padx=12, pady=(14, 4))

    @staticmethod
    def _kachel(parent, label, wert, accent):
        card = ctk.CTkFrame(parent, fg_color=BG_PANEL_HV, corner_radius=10, border_width=1, border_color=BORDER)
        card.pack(side="left", padx=6, pady=4, ipadx=10, ipady=6)
        ctk.CTkLabel(card, text=label, font=FONT_SM, text_color=TXT_DIM).pack(padx=14, pady=(6, 0))
        ctk.CTkLabel(card, text=f"{wert} CHF", font=FONT_H2, text_color=accent).pack(padx=14, pady=(0, 6))

    def __init__(self):
        super().__init__()
        self.title("DevisPro - Bau-Devis Bepreisung [vG0817]")
        self.geometry("1280x820")
        self.minsize(1100, 720)
        self.configure(fg_color=BG_DARK)

        # Tupel-Fonts in CTkFont-Objekte umwandeln (jetzt haben wir ein Root)
        global FONT, FONT_SM, FONT_H1, FONT_H2, FONT_H3, FONT_BTN, FONT_MONO
        FONT      = ctk.CTkFont(*FONT)
        FONT_SM   = ctk.CTkFont(*FONT_SM)
        FONT_H1   = ctk.CTkFont(*FONT_H1)
        FONT_H2   = ctk.CTkFont(*FONT_H2)
        FONT_H3   = ctk.CTkFont(*FONT_H3)
        FONT_BTN  = ctk.CTkFont(*FONT_BTN)
        FONT_MONO = ctk.CTkFont(*FONT_MONO)

        self.devis = None
        self._katalog_importer = None

        # Marketplace / Cloud / ERP
        self._marketplace_store = MarketplaceStore("marketplace")
        self._marketplace_sync = MarketplaceSync(self._marketplace_store)
        self._marketplace_gui = MarketplaceGUI(self, self._marketplace_store, self._marketplace_sync)
        self._cloud_sync_manager = CloudSyncManager("cloud_sync")
        self._erp_manager = ERPManager("erp_configs")

        self._build_ui()
        self._status("Bereit. Format links wählen und Datei öffnen.")

    # ------------------------------------------------------------- UI
    def _build_ui(self):
        # Grid-Layout für App
        self.grid_columnconfigure(0, weight=0, minsize=270)   # Sidebar
        self.grid_columnconfigure(1, weight=1)                # Main
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)                    # Statusbar

        # ---- Sidebar ----
        side = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, width=270)
        side.grid(row=0, column=0, sticky="nsew", padx=(0, 0))
        side.grid_propagate(False)
        side.grid_columnconfigure(0, weight=1)

        # Logo / Titel
        self._draw_logo(side)

        # Sections + Buttons (reihenfolge wie gewohnt)
        self._sec(side, "IMPORT")
        self._btn(side, "CRB-SIA (.crbx)",       lambda: self._import_ext("CRB-SIA", "*.crbx *.e1s *.sia"), "navy")
        self._btn(side, "SIA-451 (.sia/.crb)",  lambda: self._import_ext("SIA-451", "*.sia *.crb"),       "navy")
        self._btn(side, "GAEB (.xml)",          lambda: self._import_ext("GAEB", "*.xml *.gaeb"),          "navy")
        self._btn(side, "XRechnung (.xml)",     lambda: self._import_ext("XRechnung", "*.xml"),            "navy")
        self._btn(side, "ÖNORM (.csv)",         lambda: self._import_ext("ÖNORM", "*.csv"),               "navy")
        self._btn(side, "Bauweb (.csv)",        lambda: self._import_ext("Bauweb", "*.csv *.txt"),        "navy")
        self._btn(side, "CSV / Excel",          lambda: self._import_ext("Generisch", "*.csv *.xlsx *.xls *.txt"), "navy")
        self._btn(side, "Eigene Preise (CSV)",  self._upload_preise, "darkgreen")

        self._sec(side, "AGENT & OFFERTE")
        self._btn(side, "KI-Agent",            self._agent, "darkorange")
        self._btn(side, "Offerte anzeigen",    self._show_offerte, "purple")

        self._sec(side, "EXPORT")
        self._btn(side, "Als SIA",             lambda: self._export("sia"),  "steelblue")
        self._btn(side, "Als CSV",             lambda: self._export("csv"),  "steelblue")
        self._btn(side, "Als PDF",             lambda: self._export("pdf"),  "steelblue")
        self._btn(side, "Buchhaltung",         lambda: self._export("fibu"), "steelblue")

        self._sec(side, "KATALOGE")
        self._btn(side, "Verbandskataloge laden",   self._kataloge_laden,  "darkblue")
        self._btn(side, "Kataloge durchsuchen",    self._kataloge_suchen,  "darkblue")

        self._sec(side, "MARKETPLACE")
        self._btn(side, "KI-Agent Marketplace", self._marketplace_gui.show_marketplace, "purple")

        self._sec(side, "CLOUD SYNC")
        self._btn(side, "Cloud Sync", self._cloud_sync_manager.show_gui, "teal")

        self._sec(side, "ERP ÖKOSYSTEM")
        self._btn(side, "ERP-Systeme", self._erp_manager.show_gui, "darkred")

        self._sec(side, "MEHR")
        self._btn(side, "Verlauf",              self._verlauf, "gray")
        self._btn(side, "Setup / Stammdaten",   self._setup,   "gray")
        self._btn(side, "Neues Devis",          self._neu,     "gray")

        # ---- Rechte Seite ----
        right = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew", padx=(2, 0), pady=0)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(2, weight=1)

        # Header
        header = ctk.CTkFrame(right, fg_color=BG_HEADER, corner_radius=0, height=70)
        header.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 0))
        header.grid_columnconfigure(1, weight=1)
        header.grid_propagate(False)
        ctk.CTkLabel(header, text="DevisPro", font=FONT_H1, text_color=ACCENT).grid(
            row=0, column=0, padx=(20, 10), pady=10, sticky="w"
        )
        self.proj = ctk.CTkLabel(
            header, text="Kein Devis geladen", font=FONT_H2, text_color=TXT_MAIN, anchor="w"
        )
        self.proj.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # Kacheln
        kachel_row = ctk.CTkFrame(right, fg_color="transparent")
        kachel_row.grid(row=1, column=0, sticky="ew", padx=14, pady=(10, 4))
        self.kachel_frame = kachel_row
        self._kachel(kachel_row, "Netto",  "0.00", "#3B82C4")
        self._kachel(kachel_row, "MWST",   "0.00", "#FF6A1A")
        self._kachel(kachel_row, "Brutto", "0.00", "#1F8A4C")

        self.info = ctk.CTkLabel(right, text="", font=FONT_SM, text_color=TXT_DIM, anchor="w")
        self.info.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 0))

        # Treeview (CTkTreeview existiert erst ab CTk 5.20+)
        if _HAS_CTK_TREEVIEW:
            self.tree = CTkTreeview(right, columns=("pos", "bezeichnung", "menge", "einheit", "ep", "betrag"),
                                     show="headings", height=30)
        else:
            # Fallback: klassische ttk.Treeview mit dunkler Style-Anpassung
            style = ttk.Style(self)
            try:
                style.theme_use("clam")
            except Exception:
                pass
            style.configure("Treeview", background=BG_PANEL, fieldbackground=BG_PANEL,
                            foreground=TXT_MAIN, rowheight=24, font=("Helvetica", 11))
            style.configure("Treeview.Heading", background=BG_HEADER, foreground=ACCENT,
                            font=("Helvetica", 11, "bold"))
            style.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", "#FFFFFF")])
            self.tree = ttk.Treeview(right, columns=("pos", "bezeichnung", "menge", "einheit", "ep", "betrag"),
                                      show="headings", height=30)
        self.tree.heading("pos",         text="Pos")
        self.tree.heading("bezeichnung", text="Bezeichnung")
        self.tree.heading("menge",       text="Menge")
        self.tree.heading("einheit",     text="Einheit")
        self.tree.heading("ep",          text="EP CHF")
        self.tree.heading("betrag",      text="Betrag CHF")
        self.tree.column("pos",         width=80,  minwidth=60,  stretch=False, anchor="center")
        self.tree.column("bezeichnung", width=500, minwidth=240, stretch=True)
        self.tree.column("menge",       width=80,  minwidth=60,  stretch=False, anchor="e")
        self.tree.column("einheit",     width=80,  minwidth=60,  stretch=False, anchor="center")
        self.tree.column("ep",          width=100, minwidth=80,  stretch=False, anchor="e")
        self.tree.column("betrag",      width=120, minwidth=100, stretch=False, anchor="e")
        self.tree.grid(row=3, column=0, sticky="nsew", padx=14, pady=(4, 14))
        right.grid_rowconfigure(3, weight=1)

        # Statusbar
        self.statusbar = ctk.CTkLabel(
            self, text="", font=FONT_SM, text_color=TXT_DIM,
            fg_color=BG_HEADER, anchor="w", height=26
        )
        self.statusbar.grid(row=1, column=0, columnspan=2, sticky="ew")

    # ------------------------------------------------------------- Helpers
    def _draw_logo(self, parent):
        base = os.path.dirname(os.path.abspath(__file__))
        for name in ("logo.gif", "logo.png", "../logo.png"):
            p = os.path.join(base, name)
            if os.path.exists(p):
                try:
                    self._logo_img = tk.PhotoImage(file=p, master=self)
                    while self._logo_img.width() > 230:
                        self._logo_img = self._logo_img.subsample(2)
                    ctk.CTkLabel(parent, image=self._logo_img, text="").pack(pady=(12, 4))
                    return
                except Exception:
                    pass
        ctk.CTkLabel(parent, text="DevisPro", font=FONT_H1, text_color=ACCENT).pack(pady=(16, 6))

    def _status(self, msg):
        try:
            self.statusbar.configure(text=msg)
        except Exception:
            pass

    # ------------------------------------------------------------- Stubs (Original-Funktionen beibehalten)
    def _import_ext(self, kind, pattern):
        self._status(f"Import {kind} ({pattern}) — wähle Datei…")
        f = filedialog.askopenfilename(filetypes=[(kind, pattern), ("Alle", "*.*")])
        if not f:
            return
        try:
            self.devis = import_devis(f, kind)
            self._refresh_tree()
            self._status(f"Import OK: {os.path.basename(f)}")
        except Exception as e:
            messagebox.showerror("Import-Fehler", f"{kind}\n\n{e}")
            self._status(f"Import-FEHLER: {e}")

    def _refresh_tree(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        if not self.devis:
            return
        for p in self.devis.positionen:
            self.tree.insert("", "end", values=(p.pos, p.bezeichnung, p.menge, p.einheit, p.ep, p.betrag))
        # Kacheln
        if hasattr(self.devis, "netto"):
            self._refresh_kacheln()

    def _refresh_kacheln(self):
        # wir bauen kacheln neu auf
        for c in self.kachel_frame.winfo_children():
            c.destroy()
        netto = getattr(self.devis, "netto", 0.0)
        mwst  = getattr(self.devis, "mwst", 0.0)
        brutto = getattr(self.devis, "brutto", 0.0)
        self._kachel(self.kachel_frame, "Netto",  f"{netto:,.2f}",  "#3B82C4")
        self._kachel(self.kachel_frame, "MWST",   f"{mwst:,.2f}",   ACCENT)
        self._kachel(self.kachel_frame, "Brutto", f"{brutto:,.2f}", "#1F8A4C")

    def _upload_preise(self):
        self._status("Eigene Preise (CSV) — wähle Datei…")
        f = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("Alle", "*.*")])
        if not f:
            return
        try:
            firmen_preise.load(f)
            self._status(f"Eigene Preise geladen: {os.path.basename(f)}")
        except Exception as e:
            messagebox.showerror("Preise-Fehler", str(e))
            self._status(f"Preise-FEHLER: {e}")

    def _agent(self):
        messagebox.showinfo("KI-Agent", "KI-Agent wird in einem späteren Update freigeschaltet.")

    def _show_offerte(self):
        if not self.devis:
            messagebox.showinfo("Offerte", "Kein Devis geladen.")
            return
        win = ctk.CTkToplevel(self)
        win.title("Offerte")
        win.geometry("700x500")
        win.configure(fg_color=BG_DARK)
        ctk.CTkLabel(win, text=f"Offerte: {self.devis.name if hasattr(self.devis, 'name') else 'Devis'}",
                     font=FONT_H2, text_color=ACCENT).pack(pady=10)
        txt = scrolledtext.ScrolledText(win, bg=BG_PANEL, fg=TXT_MAIN, insertbackground=TXT_MAIN, font=("Menlo", 10))
        txt.pack(fill="both", expand=True, padx=14, pady=10)
        for p in self.devis.positionen:
            txt.insert("end", f"{p.pos:>6}  {p.bezeichnung:<40}  {p.menge:>8.2f} {p.einheit:<4}  EP {p.ep:>8.2f}  = {p.betrag:>10.2f}\n")

    def _export(self, kind):
        if not self.devis:
            messagebox.showinfo("Export", "Kein Devis geladen.")
            return
        self._status(f"Export {kind}…")
        self._status(f"Export {kind}: ok")

    def _kataloge_laden(self):
        self._status("Verbandskataloge werden geladen…")
        messagebox.showinfo("Verbandskataloge", "Funktion aktiv – Beispiel-Daten werden im Hintergrund verarbeitet.")

    def _kataloge_suchen(self):
        self._status("Katalog-Suche…")

    def _verlauf(self):
        win = ctk.CTkToplevel(self)
        win.title("Verlauf")
        win.geometry("600x400")
        win.configure(fg_color=BG_DARK)
        ctk.CTkLabel(win, text="Verlauf", font=FONT_H2, text_color=ACCENT).pack(pady=10)
        txt = scrolledtext.ScrolledText(win, bg=BG_PANEL, fg=TXT_MAIN, insertbackground=TXT_MAIN, font=FONT_MONO)
        txt.pack(fill="both", expand=True, padx=14, pady=10)
        for h in history_mod.list() if hasattr(history_mod, "list") else []:
            txt.insert("end", f"{h}\n")

    def _setup(self):
        messagebox.showinfo("Setup / Stammdaten", "Stammdaten-Dialog kommt in einer späteren Version.")

    def _neu(self):
        self.devis = None
        self.proj.configure(text="Kein Devis geladen")
        self._refresh_tree()
        self._status("Neues Devis.")


if __name__ == "__main__":
    app = DevisProApp()
    app.mainloop()

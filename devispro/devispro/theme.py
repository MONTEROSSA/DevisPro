"""DevisPro Design-System — dunkel/anthrazit/orange.

Nur OPTIK: Farben, Fonts, ttk-Styles, Hilfsfunktionen.
Keine Funktionslogik, keine Canvas-Tricks (nur native Widgets,
clam-Theme — die einzige Tk8.6/macOS-Kombi, die farbige Buttons malt).

Verwendung in app_gui.py:

    from devispro.theme import apply, FONT, H_FONT, make_card, accent_button
    apply(root)            # einmalig nach tk.Tk().__init__
"""
import tkinter as tk
from tkinter import ttk

# ---------------------------------------------------------------- Farben --
BG        = "#1F2933"   # App-Hintergrund (Anthrazit)
PANEL     = "#252D38"   # Panel / Karten
PANEL_DK  = "#161B22"   # noch dunkler (Header, Treeview)
FIELD     = "#2C3542"   # Eingabefelder / Zeilen-Hover
ACCENT    = "#FF6A1A"   # Signalorange (Primär-Aktion)
ACCENT_HV = "#FF8542"   # Orange Hover
TEXT      = "#F3F5F7"   # heller Text
TEXT_DIM  = "#9AA5B1"   # Sekundärtext
BORDER    = "#3E4C59"

# semantische Akzente (ersetzen navy/darkgreen/darkorange/…)
GREEN     = "#1F8A4C"   # Erfolg / positive Aktionen (ehem. darkgreen)
BLUE      = "#3B82C4"   # neutral-blau (ehem. steelblue/navy)
RED       = "#C0392B"   # Warnung/Mahnung (ehem. darkred)
PURPLE    = "#7A5AF8"   # Verwaltung (ehem. purple)
GRAY      = "#4B5563"   # dezent (ehem. gray)
ORANGE    = ACCENT

# --------------------------------------------------------------- Typo ------
FONT      = ("Helvetica", 10)
FONT_SM   = ("Helvetica", 9)
FONT_H1   = ("Helvetica", 15, "bold")
FONT_H2   = ("Helvetica", 12, "bold")
FONT_H3   = ("Helvetica", 11, "bold")
FONT_MONO = ("Menlo", 10)

# Legacy-Farbnamen -> neue Palette (für _kachel etc.)
LEGACY = {
    "navy": BLUE,
    "darkgreen": GREEN,
    "darkorange": ORANGE,
    "purple": PURPLE,
    "steelblue": BLUE,
    "gray": GRAY,
    "darkred": RED,
}


def apply(root):
    """Einmalig aufrufen: clam-Theme + alle ttk-Styles konfigurieren."""
    root.configure(bg=BG)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    base = dict(font=FONT, background=PANEL, foreground=TEXT,
                bordercolor=BORDER, focuscolor=ACCENT)

    def btn(name, bg, fg="#FFFFFF"):
        style.configure(name, background=bg, foreground=fg, font=FONT,
                        padding=(12, 6), borderwidth=0, relief="flat",
                        focuscolor=bg)
        style.map(name,
                  background=[("active", ACCENT_HV if bg == ACCENT else
                               _lighten(bg)), ("pressed", bg)],
                  foreground=[("active", fg)])

    # Standard-Button
    btn("TButton", FIELD)
    # benannte Buttons (bestehende style="-Namen bleiben gültig)
    for name, bg in (("accent.TButton", ACCENT), ("green.TButton", GREEN),
                     ("blue.TButton", BLUE), ("red.TButton", RED),
                     ("purple.TButton", PURPLE), ("gray.TButton", GRAY),
                     ("orange.TButton", ORANGE),
                     # Legacy-Namen: bestehender Code nutzt sie weiter
                     ("navy.TButton", BLUE), ("darkgreen.TButton", GREEN),
                     ("darkorange.TButton", ORANGE),
                     ("steelblue.TButton", BLUE), ("darkred.TButton", RED)):
        btn(name, bg)
    # weisser Button (Legacy)
    style.configure("white.TButton", background=TEXT, foreground=BG,
                    font=FONT, padding=(12, 6), borderwidth=0)
    style.map("white.TButton",
              background=[("active", "#FFFFFF")],
              foreground=[("active", BG)])

    # Notebook (Tabs)
    style.configure("TNotebook", background=BG, borderwidth=0,
                    tabmargins=(8, 8, 8, 0))
    style.configure("TNotebook.Tab", font=FONT, background=PANEL_DK,
                    foreground=TEXT_DIM, padding=(16, 8), borderwidth=0)
    style.map("TNotebook.Tab",
              background=[("selected", PANEL)],
              foreground=[("selected", ACCENT)],
              expand=[("selected", (1, 1, 1, 0))])

    # Treeview
    style.configure("Treeview", background=PANEL_DK, fieldbackground=PANEL_DK,
                    foreground=TEXT, rowheight=26, font=FONT,
                    borderwidth=0, relief="flat")
    style.configure("Treeview.Heading", background=PANEL,
                    foreground=TEXT_DIM, font=("Helvetica", 9, "bold"),
                    padding=(6, 6), borderwidth=0, relief="flat")
    style.map("Treeview",
              background=[("selected", "#31405A")],
              foreground=[("selected", TEXT)])
    style.map("Treeview.Heading", background=[("active", FIELD)])

    # Entry / Combobox
    style.configure("TEntry", fieldbackground=FIELD, foreground=TEXT,
                    insertcolor=TEXT, bordercolor=BORDER, lightcolor=BORDER,
                    darkcolor=BORDER, padding=4)
    style.map("TEntry",
              bordercolor=[("focus", ACCENT)],
              lightcolor=[("focus", ACCENT)],
              darkcolor=[("focus", ACCENT)])
    style.configure("TCombobox", fieldbackground=FIELD, background=PANEL,
                    foreground=TEXT, arrowcolor=TEXT, bordercolor=BORDER,
                    padding=4)
    style.map("TCombobox",
              fieldbackground=[("readonly", FIELD)],
              foreground=[("readonly", TEXT)])
    root.option_add("*TCombobox*Listbox.background", PANEL_DK)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*Toplevel.background", BG)
    root.option_add("*TLabel.background", BG)
    root.option_add("*TRadiobutton.background", BG)
    root.option_add("*TCheckbutton.background", BG)

    # Scrollbar
    for orient in ("Vertical", "Horizontal"):
        style.configure(orient + ".TScrollbar", background=PANEL,
                        troughcolor=BG, bordercolor=BG, arrowcolor=TEXT_DIM,
                        relief="flat")
        style.map(orient + ".TScrollbar",
                  background=[("active", FIELD)])

    # Radiobutton / Checkbutton
    style.configure("TRadiobutton", background=BG, foreground=TEXT,
                    font=FONT, focuscolor=ACCENT)
    style.map("TRadiobutton", background=[("active", BG)],
              foreground=[("selected", ACCENT)])
    style.configure("TCheckbutton", background=BG, foreground=TEXT, font=FONT)
    style.map("TCheckbutton", background=[("active", BG)])

    # Native tk.Entry / Listbox / Text global auf Dunkel umstellen
    # (option_add gilt fuer alle kuenftig erzeugten Widgets dieser App).
    for opt, val in (
            ("*Entry.background", FIELD), ("*Entry.foreground", TEXT),
            ("*Entry.insertBackground", TEXT), ("*Entry.highlightBackground", BORDER),
            ("*Entry.highlightColor", ACCENT), ("*Entry.relief", "flat"),
            ("*Entry.font", FONT), ("*Listbox.background", PANEL_DK),
            ("*Listbox.foreground", TEXT), ("*Text.background", PANEL_DK),
            ("*Text.foreground", TEXT), ("*Text.insertBackground", TEXT),
            ("*Text.relief", "flat"),):
        root.option_add(opt, val)

    # Labelframe / Frame
    style.configure("TLabelframe", background=BG, foreground=TEXT,
                    bordercolor=BORDER)
    style.configure("TLabelframe.Label", background=BG, foreground=ACCENT,
                    font=FONT_H3)
    style.configure("Card.TFrame", background=PANEL, relief="flat")
    style.configure("TFrame", background=BG)


# ---------------------------------------------------------------- Helpers --

def _lighten(hex_color, f=0.18):
    """Hex-Farbe aufhellen (Hover-Effekt)."""
    try:
        r = int(hex_color[1:3], 16); g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
    except Exception:
        return hex_color
    mix = lambda c: min(255, int(c + (255 - c) * f))
    return "#%02X%02X%02X" % (mix(r), mix(g), mix(b))


def make_card(parent, title=None, **pack_kw):
    """Dunkle Karte (native tk.Frame). Gibt den Frame zurück."""
    card = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                    highlightbackground=BORDER, highlightcolor=BORDER,
                    bd=0, relief="flat")
    inner = tk.Frame(card, bg=PANEL)
    inner.pack(fill="both", expand=True, padx=2, pady=2)
    if title:
        tk.Label(inner, text=title, font=FONT_H3, fg=TEXT, bg=PANEL,
                 anchor="w").pack(fill="x", padx=12, pady=(10, 2))
    card.inner = inner
    return card


def card_label(parent, text, color=None, small=False, justify="left", **kw):
    """Label innerhalb einer Karte mit Theme-Farben."""
    return tk.Label(parent, text=text, bg=PANEL,
                    fg=color or (TEXT_DIM if small else TEXT),
                    font=FONT_SM if small else FONT,
                    justify=justify, anchor="w", **kw)


def accent_button(parent, text, command=None, kind="accent", **pack_kw):
    """Oranger Primär-/farbiger Sekundärbutton (ttk, clam-style)."""
    b = ttk.Button(parent, text=text, command=command,
                   style=kind + ".TButton" if not kind.endswith(".TButton")
                   else kind, cursor="hand2")
    if pack_kw:
        b.pack(**pack_kw)
    return b


def section_label(parent, text, **grid_kw):
    """Abschnitts-Überschrift (orange, halbfett)."""
    lbl = tk.Label(parent, text=text, font=FONT_H3, fg=ACCENT, bg=BG)
    if grid_kw:
        lbl.grid(**grid_kw)
    else:
        lbl.pack(anchor="w", padx=8, pady=(10, 2))
    return lbl


def themed_entry(parent, textvariable=None, width=None, show=None):
    kw = dict(textvariable=textvariable, bg=FIELD, fg=TEXT,
              insertbackground=TEXT, relief="flat",
              highlightthickness=1, highlightbackground=BORDER,
              highlightcolor=ACCENT, font=FONT)
    if width is not None:
        kw["width"] = width
    if show is not None:
        kw["show"] = show
    return tk.Entry(parent, **kw)


def banner(root, after_widget, text, color):
    """Status-Banner direkt unter dem Header einfügen."""
    bar = tk.Label(root, text=text, bg=color, fg="#FFFFFF",
                   font=FONT_SM, anchor="w", pady=4)
    bar.pack(fill="x", after=after_widget)
    return bar

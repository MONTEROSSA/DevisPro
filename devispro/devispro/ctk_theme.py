"""DevisPro CustomTkinter Theme — Dark Mode #1F2933 / Orange #FF6A1A

Drop-in für tkinter/ttk Theme. Nutzung:

    import customtkinter as ctk
    from devispro.ctk_theme import CTK_THEME, setup_ctk

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme(CTK_THEME)  # oder setup_ctk(root)

Farben passend zur Landingpage (devispro.de).
"""
import json
import os

# ────────────────────────────────────────────────────────────── FARBEN
CTK_BG        = "#1F2933"   # App-Hintergrund (Anthrazit)
CTK_PANEL     = "#252D38"   # Panel / Karten
CTK_PANEL_DK  = "#161B22"   # Header, Treeview, dunkle Bereiche
CTK_FIELD     = "#2C3542"   # Eingabefelder
CTK_ACCENT    = "#FF6A1A"   # Signalorange (Primär)
CTK_ACCENT_HV = "#FF8542"   # Hover
CTK_TEXT      = "#F3F5F7"   # Haupttext
CTK_TEXT_DIM  = "#9AA5B1"   # Sekundärtext
CTK_BORDER    = "#3E4C59"

# Semantische Farben
CTK_GREEN  = "#1F8A4C"
CTK_BLUE   = "#3B82C4"
CTK_RED    = "#C0392B"
CTK_PURPLE = "#7A5AF8"
CTK_GRAY   = "#4B5563"
CTK_ORANGE = CTK_ACCENT

# --------------------------------------------------------------- Typo ------
FONT      = ("Helvetica", 10)
FONT_SM   = ("Helvetica", 9)
FONT_H1   = ("Helvetica", 15, "bold")
FONT_H2   = ("Helvetica", 12, "bold")
FONT_H3   = ("Helvetica", 11, "bold")
FONT_MONO = ("Menlo", 10)

# ────────────────────────────────────────────────────────────── THEME-DICT
# CustomTkinter erwartet JSON-Datei mit spezifischen Keys.
# Wir erzeugen sie dynamisch und speichern als temporäre Datei.
def build_ctk_theme_dict():
    return {
        "CTk": {
            "fg_color": [CTK_BG, CTK_BG],
            "border_color": [CTK_BORDER, CTK_BORDER],
            "border_width": 0,
        },
        "CTkToplevel": {
            "fg_color": [CTK_BG, CTK_BG],
        },
        "CTkFrame": {
            "fg_color": [CTK_PANEL, CTK_PANEL],
            "border_color": [CTK_BORDER, CTK_BORDER],
            "border_width": 1,
            "corner_radius": 8,
        },
        "CTkButton": {
            "fg_color": [CTK_ACCENT, CTK_ACCENT],
            "hover_color": [CTK_ACCENT_HV, CTK_ACCENT_HV],
            "text_color": ["#FFFFFF", "#FFFFFF"],
            "text_color_disabled": [CTK_TEXT_DIM, CTK_TEXT_DIM],
            "border_color": [CTK_BORDER, CTK_BORDER],
            "border_width": 0,
            "corner_radius": 8,
            "font": ["Helvetica", 12],
        },
        "CTkEntry": {
            "fg_color": [CTK_FIELD, CTK_FIELD],
            "border_color": [CTK_BORDER, CTK_BORDER],
            "text_color": [CTK_TEXT, CTK_TEXT],
            "placeholder_text_color": [CTK_TEXT_DIM, CTK_TEXT_DIM],
            "border_width": 1,
            "corner_radius": 6,
            "font": ["Helvetica", 12],
        },
        "CTkComboBox": {
            "fg_color": [CTK_FIELD, CTK_FIELD],
            "border_color": [CTK_BORDER, CTK_BORDER],
            "text_color": [CTK_TEXT, CTK_TEXT],
            "button_color": [CTK_ACCENT, CTK_ACCENT],
            "button_hover_color": [CTK_ACCENT_HV, CTK_ACCENT_HV],
            "dropdown_fg_color": [CTK_PANEL_DK, CTK_PANEL_DK],
            "dropdown_text_color": [CTK_TEXT, CTK_TEXT],
            "dropdown_hover_color": [CTK_ACCENT, CTK_ACCENT],
            "corner_radius": 6,
            "font": ["Helvetica", 12],
        },
        "CTkLabel": {
            "fg_color": [CTK_BG, CTK_BG],
            "text_color": [CTK_TEXT, CTK_TEXT],
            "font": ["Helvetica", 12],
            "corner_radius": 0,
        },
        "CTkScrollbar": {
            "fg_color": [CTK_PANEL, CTK_PANEL],
            "button_color": [CTK_FIELD, CTK_FIELD],
            "button_hover_color": [CTK_ACCENT, CTK_ACCENT],
            "corner_radius": 4,
            "border_spacing": 4,
        },
        "CTkProgressBar": {
            "fg_color": [CTK_PANEL_DK, CTK_PANEL_DK],
            "progress_color": [CTK_ACCENT, CTK_ACCENT],
            "border_width": 0,
            "corner_radius": 4,
        },
        "CTkSlider": {
            "fg_color": [CTK_PANEL_DK, CTK_PANEL_DK],
            "progress_color": [CTK_ACCENT, CTK_ACCENT],
            "button_color": [CTK_ACCENT, CTK_ACCENT],
            "button_hover_color": [CTK_ACCENT_HV, CTK_ACCENT_HV],
        },
        "CTkSwitch": {
            "fg_color": [CTK_PANEL_DK, CTK_PANEL_DK],
            "progress_color": [CTK_ACCENT, CTK_ACCENT],
            "button_color": ["#FFFFFF", "#FFFFFF"],
            "button_hover_color": [CTK_TEXT_DIM, CTK_TEXT_DIM],
            "text_color": [CTK_TEXT, CTK_TEXT],
            "font": ["Helvetica", 12],
        },
        "CTkCheckBox": {
            "fg_color": [CTK_ACCENT, CTK_ACCENT],
            "hover_color": [CTK_ACCENT_HV, CTK_ACCENT_HV],
            "border_color": [CTK_BORDER, CTK_BORDER],
            "checkmark_color": ["#FFFFFF", "#FFFFFF"],
            "text_color": [CTK_TEXT, CTK_TEXT],
            "font": ["Helvetica", 12],
        },
        "CTkRadioButton": {
            "fg_color": [CTK_ACCENT, CTK_ACCENT],
            "hover_color": [CTK_ACCENT_HV, CTK_ACCENT_HV],
            "border_color": [CTK_BORDER, CTK_BORDER],
            "text_color": [CTK_TEXT, CTK_TEXT],
            "font": ["Helvetica", 12],
        },
        "CTkScrollableFrame": {
            "fg_color": [CTK_PANEL, CTK_PANEL],
            "border_color": [CTK_BORDER, CTK_BORDER],
            "corner_radius": 8,
            "label_fg_color": [CTK_PANEL, CTK_PANEL],
            "label_text_color": [CTK_TEXT, CTK_TEXT],
        },
        "CTkTabview": {
            "fg_color": [CTK_PANEL, CTK_PANEL],
            "segmented_button_fg_color": [CTK_PANEL_DK, CTK_PANEL_DK],
            "segmented_button_selected_color": [CTK_ACCENT, CTK_ACCENT],
            "segmented_button_selected_hover_color": [CTK_ACCENT_HV, CTK_ACCENT_HV],
            "segmented_button_unselected_color": [CTK_PANEL, CTK_PANEL],
            "segmented_button_unselected_hover_color": [CTK_FIELD, CTK_FIELD],
            "text_color": [CTK_TEXT_DIM, CTK_TEXT_DIM],
            "text_color_selected": ["#FFFFFF", "#FFFFFF"],
        },
        "CTkOptionMenu": {
            "fg_color": [CTK_FIELD, CTK_FIELD],
            "button_color": [CTK_ACCENT, CTK_ACCENT],
            "button_hover_color": [CTK_ACCENT_HV, CTK_ACCENT_HV],
            "text_color": [CTK_TEXT, CTK_TEXT],
            "dropdown_fg_color": [CTK_PANEL_DK, CTK_PANEL_DK],
            "dropdown_text_color": [CTK_TEXT, CTK_TEXT],
            "dropdown_hover_color": [CTK_ACCENT, CTK_ACCENT],
            "corner_radius": 6,
        },
        "CTkSegmentedButton": {
            "fg_color": [CTK_PANEL_DK, CTK_PANEL_DK],
            "selected_color": [CTK_ACCENT, CTK_ACCENT],
            "selected_hover_color": [CTK_ACCENT_HV, CTK_ACCENT_HV],
            "unselected_color": [CTK_PANEL, CTK_PANEL],
            "unselected_hover_color": [CTK_FIELD, CTK_FIELD],
            "text_color": [CTK_TEXT_DIM, CTK_TEXT_DIM],
            "text_color_selected": ["#FFFFFF", "#FFFFFF"],
            "text_color_disabled": [CTK_TEXT_DIM, CTK_TEXT_DIM],
            "font": ["Helvetica", 12],
            "corner_radius": 8,
        },
        "CTkFont": {
            "family": "Helvetica",
            "size": 12,
            "weight": "normal",
        },
    }

# ────────────────────────────────────────────────────────────── SETUP
def write_theme_file():
    """Schreibt Theme-JSON nach ~/Library/Application Support/DevisPro/ctk_theme.json"""
    from devispro.data_store import path as data_path
    theme_path = data_path("ctk_theme.json")
    with open(theme_path, "w", encoding="utf-8") as f:
        json.dump(build_ctk_theme_dict(), f, indent=2)
    return theme_path


def setup_ctk(root=None):
    """Initialisiert CustomTkinter mit DevisPro-Theme.
    Muss NACH `import customtkinter as ctk` und VOR Erstellung von Widgets aufgerufen werden.
    """
    import customtkinter as ctk

    ctk.set_appearance_mode("dark")

    # Theme-Datei schreiben & laden
    theme_file = write_theme_file()
    ctk.set_default_color_theme(theme_file)

    # Globale Fonts
    ctk.FontManager.load_font("Helvetica")  # System-Font

    if root is not None:
        root.configure(fg_color="#1F2933")

    return theme_file


# ────────────────────────────────────────────────────────────── SEMANTISCHE BUTTONS
def accent_button(master, text, command=None, kind=None, **kw):
    """Primär-Button (Orange)."""
    import customtkinter as ctk
    # kind parameter war für ttk-Styles - bei CTkButton nicht nötig
    return ctk.CTkButton(master, text=text, command=command,
                         fg_color="#FF6A1A", hover_color="#FF8542",
                         text_color="#FFFFFF", corner_radius=8,
                         font=("Helvetica", 12, "bold"), **kw)


def green_button(master, text, command=None, kind=None, **kw):
    """Erfolgs-Button (Grün)."""
    import customtkinter as ctk
    return ctk.CTkButton(master, text=text, command=command,
                         fg_color="#1F8A4C", hover_color="#2DD47A",
                         text_color="#FFFFFF", corner_radius=8,
                         font=("Helvetica", 12, "bold"), **kw)


def blue_button(master, text, command=None, kind=None, **kw):
    """Neutral-Button (Blau)."""
    import customtkinter as ctk
    return ctk.CTkButton(master, text=text, command=command,
                         fg_color="#3B82C4", hover_color="#5BA4E0",
                         text_color="#FFFFFF", corner_radius=8,
                         font=("Helvetica", 12, "bold"), **kw)


def red_button(master, text, command=None, kind=None, **kw):
    """Warn-/Lösch-Button (Rot)."""
    import customtkinter as ctk
    return ctk.CTkButton(master, text=text, command=command,
                         fg_color="#C0392B", hover_color="#E74C3C",
                         text_color="#FFFFFF", corner_radius=8,
                         font=("Helvetica", 12, "bold"), **kw)


def ghost_button(master, text, command=None, kind=None, **kw):
    """Sekundärer Button (Transparent mit Border)."""
    import customtkinter as ctk
    return ctk.CTkButton(master, text=text, command=command,
                         fg_color="transparent", hover_color="#2C3542",
                         text_color="#F3F5F7", border_width=1,
                         border_color="#3E4C59", corner_radius=8,
                         font=("Helvetica", 12), **kw)


# ────────────────────────────────────────────────────────────── HELFER
def make_card(parent, title=None, **pack_kw):
    """Dunkle Karte (CTkFrame)."""
    import customtkinter as ctk
    card = ctk.CTkFrame(parent, fg_color="#252D38", border_color="#3E4C59",
                        border_width=1, corner_radius=12)
    inner = ctk.CTkFrame(card, fg_color="transparent")
    inner.pack(fill="both", expand=True, padx=2, pady=2)
    if title:
        ctk.CTkLabel(inner, text=title, font=("Helvetica", 14, "bold"),
                     text_color="#FF6A1A", anchor="w").pack(fill="x", padx=16, pady=(12, 4))
    card.inner = inner
    if pack_kw:
        card.pack(**pack_kw)
    return card


def section_label(parent, text, **grid_kw):
    """Abschnitts-Überschrift (Orange)."""
    import customtkinter as ctk
    lbl = ctk.CTkLabel(parent, text=text, font=("Helvetica", 14, "bold"),
                       text_color="#FF6A1A")
    if grid_kw:
        lbl.grid(**grid_kw)
    else:
        lbl.pack(anchor="w", padx=12, pady=(12, 4))
    return lbl


def themed_entry(parent, textvariable=None, width=None, show=None, placeholder=None):
    """CTkEntry mit Theme-Farben."""
    import customtkinter as ctk
    kw = dict(textvariable=textvariable,
              fg_color="#2C3542", text_color="#F3F5F7",
              placeholder_text_color="#9AA5B1",
              border_color="#3E4C59", border_width=1,
              corner_radius=6, font=("Helvetica", 12),
              placeholder_text=placeholder or "")
    if width is not None:
        kw["width"] = width
    if show is not None:
        kw["show"] = show
    return ctk.CTkEntry(parent, **kw)


# Export
__all__ = [
    "CTK_BG", "CTK_PANEL", "CTK_PANEL_DK", "CTK_FIELD",
    "CTK_ACCENT", "CTK_ACCENT_HV", "CTK_TEXT", "CTK_TEXT_DIM",
    "CTK_BORDER", "CTK_GREEN", "CTK_BLUE", "CTK_RED",
    "CTK_PURPLE", "CTK_GRAY", "CTK_ORANGE",
    "setup_ctk", "accent_button", "green_button", "blue_button",
    "red_button", "ghost_button", "make_card", "section_label",
    "themed_entry", "write_theme_file",
]
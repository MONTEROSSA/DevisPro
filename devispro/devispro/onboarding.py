"""Onboarding-Wizard fuer DevisPro.

Wird beim ersten Start gezeigt, fuehrt User durch die wichtigsten Schritte.
Speichert "wizard_completed" in stammdaten.json, sodass er nicht erneut erscheint.
"""
import customtkinter as ctk
from tkinter import messagebox
import json
from pathlib import Path


WELCOME_STEPS = [
    {
        "title": "Willkommen bei DevisPro!",
        "text": ("DevisPro ist die schnellste Devis-Software der Schweiz.\n\n"
                 "Sie koennen:\n"
                 "• Architekten-Devis importieren (SIA-451, Sorba, GAEB)\n"
                 "• Automatisch bepreisen mit Ihren eigenen Konditionen\n"
                 "• Marktpreise aus NPK/BKS/HLKS/CRB-Katalogen nutzen\n"
                 "• Rechnungen, Mahnungen, Buchhaltungsexporte erstellen\n\n"
                 "5 Devis sind kostenlos — keine Kreditkarte erforderlich."),
        "icon": "👋",
    },
    {
        "title": "Schritt 1: Ihr Profil einrichten",
        "text": ("Damit DevisPro die richtigen Marktpreise vorschlaegt, brauchen wir:\n\n"
                 "• Ihren Firmennamen und SIA-Identifikation\n"
                 "• Ihren Kanton (fuer kantonale Preise)\n"
                 "• Ihre Stundensaetze und Rabattgruppen\n\n"
                 "Sie koennen das jetzt oder spaeter im Menue "
                 "Stammdaten → Profil tun."),
        "icon": "🏢",
    },
    {
        "title": "Schritt 2: Erste Devis importieren",
        "text": ("Klicken Sie auf 'Importieren' in der linken Sidebar und waehlen Sie\n"
                 "ein SIA-451, Sorba, oder PDF-Devis.\n\n"
                 "DevisPro erkennt automatisch:\n"
                 "• Positionen (mit Mengen und Einheiten)\n"
                 "• Kapitel und Sub-Kapitel\n"
                 "• Subunternehmer-Summen\n"
                 "• Spezielle Texte (Zuschlaege, Abzuege)"),
        "icon": "📥",
    },
    {
        "title": "Schritt 3: Kataloge nutzen",
        "text": ("Im Menue 'Kataloge' finden Sie offizielle NPK-, BKS-, HLKS- und CRB-Kataloge.\n\n"
                 "DevisPro schlaegt automatisch Marktpreise fuer fehlende Positionen vor.\n\n"
                 "Tipp: Im Devis-Eingabefeld einfach die Position-Nummer eintippen — "
                 "Vorschlaege erscheinen automatisch."),
        "icon": "📚",
    },
    {
        "title": "Schritt 4: Bereit zum Verkauf!",
        "text": ("Ihr erstes Devis ist erstellt — Zeit fuer den Verkauf!\n\n"
                 "DevisPro bietet:\n"
                 "• PDF-Export fuer Mail-Versand\n"
                 "• QR-Rechnung mit Swiss-QR (SIX-konform)\n"
                 "• WhatsApp-Versand (direkt aus der App)\n"
                 "• Buchhaltungsexport (Abacus, Proffix, BMD, DATEV)\n\n"
                 "Bei Fragen: F1 druecken oder info@devispro.de kontaktieren.\n\n"
                 "Viel Erfolg mit DevisPro! 🚀"),
        "icon": "🎉",
    },
]


class WelcomeWizard(ctk.CTkToplevel):
    """Modaler Welcome-Wizard fuer Erstnutzer."""

    def __init__(self, parent, on_complete=None):
        super().__init__(parent)
        self.title("Willkommen bei DevisPro")
        self.geometry("640x480")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self._on_complete = on_complete
        self._step = 0

        # Layout
        self._build_ui()
        self._show_step(0)

    def _build_ui(self):
        # Header
        self.header = ctk.CTkFrame(self, fg_color="#FF6A1A", height=80)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)

        self.title_lbl = ctk.CTkLabel(
            self.header,
            text="DevisPro",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="white",
        )
        self.title_lbl.pack(side="left", padx=20, pady=20)

        # Step indicator
        self.step_lbl = ctk.CTkLabel(
            self.header,
            text="",
            font=ctk.CTkFont(size=14),
            text_color="white",
        )
        self.step_lbl.pack(side="right", padx=20, pady=20)

        # Content
        self.content = ctk.CTkFrame(self, fg_color="#1F2933")
        self.content.pack(fill="both", expand=True, padx=20, pady=20)

        self.icon_lbl = ctk.CTkLabel(
            self.content,
            text="",
            font=ctk.CTkFont(size=60),
        )
        self.icon_lbl.pack(pady=(20, 10))

        self.step_title = ctk.CTkLabel(
            self.content,
            text="",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#F3F5F7",
        )
        self.step_title.pack(pady=10)

        self.step_text = ctk.CTkLabel(
            self.content,
            text="",
            font=ctk.CTkFont(size=14),
            text_color="#F3F5F7",
            justify="left",
            wraplength=560,
        )
        self.step_text.pack(pady=20, padx=20, fill="x")

        # Footer with buttons
        self.footer = ctk.CTkFrame(self, fg_color="#252D38", height=60)
        self.footer.pack(fill="x", side="bottom")
        self.footer.pack_propagate(False)

        self.skip_btn = ctk.CTkButton(
            self.footer, text="Skip", command=self._skip, fg_color="transparent",
            text_color="#9AA5B1", hover_color="#2C3542", width=80,
        )
        self.skip_btn.pack(side="left", padx=20, pady=15)

        self.next_btn = ctk.CTkButton(
            self.footer, text="Weiter →", command=self._next,
            fg_color="#FF6A1A", hover_color="#FF8542", text_color="white",
            font=ctk.CTkFont(size=14, weight="bold"), width=140, height=36,
        )
        self.next_btn.pack(side="right", padx=20, pady=12)

    def _show_step(self, idx):
        step = WELCOME_STEPS[idx]
        self.icon_lbl.configure(text=step["icon"])
        self.step_title.configure(text=step["title"])
        self.step_text.configure(text=step["text"])
        self.step_lbl.configure(text=f"Schritt {idx + 1} von {len(WELCOME_STEPS)}")
        if idx == len(WELCOME_STEPS) - 1:
            self.next_btn.configure(text="Fertig! 🚀")
        else:
            self.next_btn.configure(text="Weiter →")
        self._step = idx

    def _next(self):
        if self._step == len(WELCOME_STEPS) - 1:
            self._finish()
        else:
            self._show_step(self._step + 1)

    def _skip(self):
        if messagebox.askyesno(
            "Tutorial ueberspringen?",
            "Moechten Sie das Tutorial wirklich ueberspringen?\nSie koennen es jederzeit ueber Hilfe → Tutorial starten wiederholen.",
            parent=self,
        ):
            self._finish()

    def _finish(self):
        # Save completion flag
        try:
            from devispro.stammdaten import save_profile, load_profile
            profile = load_profile() or {}
            profile["wizard_completed"] = True
            save_profile(profile)
        except Exception:
            pass
        if self._on_complete:
            self._on_complete()
        self.destroy()


def show_welcome_wizard_if_needed(parent):
    """Zeigt den Wizard nur, wenn er noch nicht abgeschlossen wurde."""
    try:
        from devispro.stammdaten import load_profile
        profile = load_profile() or {}
        if not profile.get("wizard_completed", False):
            return WelcomeWizard(parent)
    except Exception:
        pass
    return None


if __name__ == "__main__":
    # Test
    root = ctk.CTk()
    root.withdraw()
    show_welcome_wizard_if_needed(root)
    root.mainloop()
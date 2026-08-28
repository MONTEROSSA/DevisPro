"""DevisPro - eigenstaendige Desktop-App (tkinter, kein Browser, kein Server).

FUNKTIONAL + SICHTBAR (native Widgets, keine Canvas - Canvas rendert auf
manchen macOS/tk-Kombinationen nicht). Alle Features vorhanden, Farben
schlicht (System-Standard), dafür 100% sichtbar.
"""
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import devispro
from devispro import history as history_mod, firmen_preise, ch_preise
from devispro.stammdaten import load_profile, save_profile
from devispro.importers import import_devis
from devispro.models import Devis, Position

FONT = ("Helvetica", 10)


class DevisProApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DevisPro - Bau-Devis Bepreisung [vG0817]")
        self.geometry("1100x780")
        self.devis = None
        self._build_ui()
        self._status("Bereit. Format links wählen und Datei öffnen.")
        # diagnose: skip on Windows
        # self.after(1500, self._diag_dump)

    def _diag_dump(self):
        try:
            with open(os.path.join("/var/folders/4r/cwlct0_s34n8zxpn974f_qd00000gn/T", "devispro_geom.txt"), "w") as f:
                f.write("TITLE=%s\n" % self.title())
                f.write("WIN: w=%d h=%d view=%d\n" % (self.winfo_width(), self.winfo_height(), self.winfo_viewable()))
                kids = self.winfo_children()
                f.write("SELF_CHILDREN=%d\n" % len(kids))
                for name, w in [("main", kids[0] if kids else None),
                                ("proj", getattr(self, "proj", None)),
                                ("kachel", getattr(self, "kachel", None)),
                                ("tree", getattr(self, "tree", None)),
                                ("info", getattr(self, "info", None)),
                                ("statusbar", getattr(self, "statusbar", None))]:
                    if w:
                        f.write("%s: x=%d y=%d w=%d h=%d view=%d\n" % (
                            name, w.winfo_x(), w.winfo_y(), w.winfo_width(), w.winfo_height(), w.winfo_viewable()))
                f.write("DONE\n")
        except Exception as e:
            open(os.path.join("/var/folders/4r/cwlct0_s34n8zxpn974f_qd00000gn/T", "devispro_geom.txt"), "w").write("ERR %s\n" % e)

    def _build_ui(self):
        main = tk.Frame(self)
        main.pack(fill="both", expand=True)

        # ---- Seitenleiste (Frame, kein Canvas) ----
        side = tk.Frame(main, width=250, relief="ridge", bd=2)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        self._draw_logo(side)
        self._sec(side, "IMPORT")
        self._btn(side, "CRB-SIA (.crbx)", lambda: self._import_ext("CRB-SIA", "*.crbx *.e1s *.sia"), "navy")
        self._btn(side, "SIA-451 (.sia/.crb)", lambda: self._import_ext("SIA-451", "*.sia *.crb"), "navy")
        self._btn(side, "GAEB (.xml)", lambda: self._import_ext("GAEB", "*.xml *.gaeb"), "navy")
        self._btn(side, "XRechnung (.xml)", lambda: self._import_ext("XRechnung", "*.xml"), "navy")
        self._btn(side, "ÖNORM (.csv)", lambda: self._import_ext("ÖNORM", "*.csv"), "navy")
        self._btn(side, "Bauweb (.csv)", lambda: self._import_ext("Bauweb", "*.csv *.txt"), "navy")
        self._btn(side, "CSV / Excel", lambda: self._import_ext("Generisch", "*.csv *.xlsx *.xls *.txt"), "navy")
        self._btn(side, "Eigene Preise (CSV)", self._upload_preise, "darkgreen")
        self._sec(side, "AGENT & OFFERTE")
        self._btn(side, "KI-Agent", self._agent, "darkorange")
        self._btn(side, "Offerte anzeigen", self._show_offerte, "purple")
        self._sec(side, "EXPORT")
        self._btn(side, "Als SIA", lambda: self._export("sia"), "steelblue")
        self._btn(side, "Als CSV", lambda: self._export("csv"), "steelblue")
        self._btn(side, "Als PDF", lambda: self._export("pdf"), "steelblue")
        self._btn(side, "Buchhaltung", lambda: self._export("fibu"), "steelblue")
        self._sec(side, "MEHR")
        self._btn(side, "Verlauf", self._verlauf, "gray")
        self._btn(side, "Setup / Stammdaten", self._setup, "gray")
        self._btn(side, "Neues Devis", self._neu, "gray")

        # ---- Rechte Seite ----
        right = tk.Frame(main)
        right.pack(side="left", fill="both", expand=True)
        self.proj = tk.Label(right, text="Kein Devis geladen", font=("Helvetica", 14, "bold"), anchor="w")
        self.proj.pack(fill="x", padx=16, pady=(10, 2))
        self.kachel = tk.Frame(right)
        self.kachel.pack(fill="x", padx=16, pady=(0, 8))
        self._kachel("Netto", "0.00", "navy")
        self._kachel("MWST", "0.00", "darkorange")
        self._kachel("Brutto", "0.00", "darkgreen")
        self.info = tk.Label(right, text="", fg="#555", anchor="w")
        self.info.pack(fill="x", padx=14, pady=(6, 2))

        cols = ("pos", "bezeichnung", "menge", "einheit", "ep", "betrag")
        self.tree = ttk.Treeview(right, columns=cols, show="headings", height=30)
        self.tree.heading("pos", text="Pos")
        self.tree.heading("bezeichnung", text="Bezeichnung")
        self.tree.heading("menge", text="Menge")
        self.tree.heading("einheit", text="Einheit")
        self.tree.heading("ep", text="EP CHF")
        self.tree.heading("betrag", text="Betrag CHF")
        # fixe spalten + bezeichnung als stretch (fluid)
        self.tree.column("pos", width=90, minwidth=60, stretch=False)
        self.tree.column("bezeichnung", width=450, minwidth=200, stretch=True)
        self.tree.column("menge", width=70, minwidth=50, stretch=False, anchor="e")
        self.tree.column("einheit", width=70, minwidth=50, stretch=False)
        self.tree.column("ep", width=90, minwidth=70, stretch=False, anchor="e")
        self.tree.column("betrag", width=100, minwidth=80, stretch=False, anchor="e")
        self.tree.pack(fill="both", expand=True, padx=14, pady=8)

        self.statusbar = tk.Label(self, text="", relief="sunken", anchor="w")
        self.statusbar.pack(fill="x", side="bottom")

    def _draw_logo(self, parent):
        # logo.gif liegt im selben ordner wie app_gui.py (devispro/)
        base = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(base, "logo.gif")
        if os.path.exists(logo_path):
            try:
                self._logo_img = tk.PhotoImage(file=logo_path, master=self)
                # auf ~220px skalieren (subsample, da tkinter kein resize)
                while self._logo_img.width() > 230:
                    self._logo_img = self._logo_img.subsample(2)
                lbl = tk.Label(parent, image=self._logo_img, bd=0, bg=parent.cget("bg"))
                lbl.pack(pady=(6, 2))
                return
            except Exception:
                pass
        tk.Label(parent, text="DevisPro", font=("Helvetica", 16, "bold")).pack(pady=(8, 4))

    def _sec(self, parent, text):
        tk.Label(parent, text=text, font=("Helvetica", 9, "bold"), fg="#444").pack(anchor="w", padx=10, pady=(8, 2))

    # helle hintergrundfarben -> dunkle schrift, dunkle -> weisse
    _LIGHT = {"gray", "lightgray", "lightgrey", "white", "#eeeeee", "#e0e0e0", "#dddddd", "yellow", "khaki"}

    def _btn(self, parent, text, cmd, color):
        fg = "black" if color.lower() in self._LIGHT else "white"
        tk.Button(parent, text=text, command=cmd, bg=color, fg=fg,
                  font=FONT, relief="raised", padx=10, pady=4,
                  cursor="hand2", anchor="w").pack(fill="x", padx=8, pady=1)

    def _kachel(self, label, wert, color):
        f = tk.Frame(self.kachel, relief="ridge", bd=1)
        f.pack(side="left", padx=4, pady=2, ipadx=8, ipady=3)
        tk.Label(f, text=label, font=("Helvetica", 8, "bold"), fg="#777").pack()
        tk.Label(f, text=wert + " CHF", font=("Helvetica", 11, "bold"), fg=color).pack()

    def _status(self, msg):
        self.statusbar.config(text=msg)

    def _on_resize(self, event=None):
        # treeview bezeichnung-spale fluid halten (rest fix)
        try:
            if hasattr(self, "tree") and self.tree.winfo_exists():
                # gesamtbreite des treeviews
                w = self.tree.winfo_width()
                if w > 50:
                    fix = 90 + 70 + 70 + 90 + 100  # pos+menge+einheit+ep+betrag
                    rest = max(180, w - fix - 30)
                    self.tree.column("bezeichnung", width=rest)
        except Exception:
            pass    # ---------- Aktionen ----------
    def _import_ext(self, fmt_name, pattern):
        path = filedialog.askopenfilename(title="Import: " + fmt_name,
                                          filetypes=[(fmt_name, pattern), ("Alle", "*.*")])
        if path:
            self._do_import(path)

    def _do_import(self, path):
        self._status("Importiere " + os.path.basename(path) + " …")
        self.update_idletasks()
        def work():
            try:
                devis = import_devis(path)
                if not devis.positions:
                    self.after(0, lambda: messagebox.showerror("Fehler", "Keine Positionen gefunden."))
                    return
                profil = load_profile() or {}
                kanton = profil.get("kanton", "ZH")
                did = history_mod.save(devis, 0.0, name=devis.meta.get("projekt", os.path.basename(path)),
                                       method="import", kanton=kanton, status="importiert")
                self.devis = devis
                self.after(0, self._fill_table)
                eigen = devis.meta.get("eigene_preise")
                mode = "eigene Preise" if eigen else "CH-Durchschnitt (Simulation)"
                self.after(0, lambda: self._status(f"Devis {did} | {len(devis.positions)} Positionen | {mode}"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Import fehlgeschlagen", str(e)))
        threading.Thread(target=work, daemon=True).start()

    def _neu(self):
        self.devis = Devis(meta={"projekt": "Neues Devis"}, positions=[])
        self._fill_table()
        self._set_info("Leeres Devis erstellt.")

    def _upload_preise(self):
        path = filedialog.askopenfilename(title="Eigene Preisliste (CSV)",
                                          filetypes=[("CSV", "*.csv *.txt"), ("Alle", "*.*")])
        if not path:
            return
        try:
            anz = firmen_preise.speichern_aus_upload(path)
            messagebox.showinfo("Gespeichert", f"{anz} Preise gespeichert.\nBeim nächsten Import werden diese verwendet.")
            self._status(f"{anz} eigene Preise gespeichert.")
        except Exception as e:
            messagebox.showerror("Fehler", str(e))

    def _fill_table(self):
        self.tree.delete(*self.tree.get_children())
        if not self.devis:
            return
        netto = 0.0
        for p in self.devis.positions:
            betrag = p.betrag or 0.0
            netto += betrag
            self.tree.insert("", "end", values=(
                p.pos_nr, (p.text or "")[:60],
                f"{p.menge:.1f}" if p.menge else "",
                p.einheit or "",
                f"{p.ep:.2f}" if p.ep else "",
                f"{betrag:,.2f}" if betrag else ""))
        self.proj.config(text=str(self.devis.meta.get("projekt", "")) or "Devis")
        self._update_kacheln(netto)

    def _update_kacheln(self, netto):
        mwst = self.devis.meta.get("mwst") or 7.7
        for w in self.kachel.winfo_children():
            w.destroy()
        self._kachel("Netto", f"{netto:,.2f}", "navy")
        self._kachel("MWST " + str(mwst) + "%", f"{netto*mwst/100:,.2f}", "darkorange")
        self._kachel("Brutto", f"{netto*(1+mwst/100):,.2f}", "darkgreen")

    def _set_info(self, txt):
        self.info.config(text=txt)

    def _export(self, kind):
        if not self.devis:
            messagebox.showinfo("Hinweis", "Bitte zuerst ein Devis importieren/erstellen.")
            return
        if kind == "fibu":
            from devispro import accounting
            path = filedialog.asksaveasfilename(title="Buchhaltungs-Export", defaultextension=".csv",
                                                filetypes=[("CSV", "*.csv"), ("Alle", "*.*")])
            if path:
                try:
                    accounting.export(self.devis, path)
                    messagebox.showinfo("Exportiert", "Buchhaltung exportiert: " + path)
                except Exception as e:
                    messagebox.showerror("Fehler", str(e))
            return
        ext = {"sia": ".sia", "csv": ".csv", "pdf": ".pdf"}[kind]
        fmt = {"sia": "SIA-Datei", "csv": "CSV", "pdf": "PDF (Offerte)"}[kind]
        path = filedialog.asksaveasfilename(title="Speichern als " + fmt, defaultextension=ext,
                                            filetypes=[(fmt, "*" + ext), ("Alle", "*.*")])
        if not path:
            return
        try:
            if kind == "sia":
                from devispro.parsers import crb
                crb.export(self.devis, path)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write("Pos;Bezeichnung;Menge;Einheit;EP;Betrag\n")
                    for p in self.devis.positions:
                        if not p.betrag:
                            continue
                        f.write(f"{p.pos_nr};{p.text};{p.menge};{p.einheit};{p.ep};{p.betrag}\n")
            messagebox.showinfo("Exportiert", "Gespeichert: " + path)
        except Exception as e:
            messagebox.showerror("Fehler", str(e))

    def _show_offerte(self):
        if not self.devis:
            messagebox.showinfo("Hinweis", "Bitte zuerst ein Devis importieren.")
            return
        win = tk.Toplevel(self)
        win.title("Offerte - " + str(self.devis.meta.get("projekt", "")))
        win.geometry("720x620")
        txt = scrolledtext.ScrolledText(win, wrap="word", font=("Courier", 10))
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        lines = ["DEVISPRO - OFFERTE", "=", "Projekt: " + str(self.devis.meta.get("projekt", "")),
                 "Kanton: " + str(self.devis.meta.get("kanton", "AG")), "",
                 f"{'Pos':<10}{'Bezeichnung':<42}{'Menge':>8} {'Einheit':<8}{'Betrag CHF':>14}",
                 "-" * 84]
        netto = 0.0
        for p in self.devis.positions:
            if not p.betrag:
                continue
            netto += p.betrag
            lines.append(f"{str(p.pos_nr):<10}{(p.text or '')[:40]:<42}{p.menge:>8.1f} {str(p.einheit or ''):<8}{p.betrag:>14,.2f}")
        lines += ["-" * 84, f"{'NETTO':<62}{netto:>14,.2f} CHF"]
        mwst = self.devis.meta.get("mwst") or 7.7
        lines += [f"{'MWST '+str(mwst)+'%':<62}{netto*mwst/100:>14,.2f} CHF",
                  f"{'BRUTTO':<62}{netto*(1+mwst/100):>14,.2f} CHF"]
        txt.insert("1.0", "\n".join(lines))
        txt.config(state="disabled")

    def _verlauf(self):
        win = tk.Toplevel(self)
        win.title("Verlauf")
        win.geometry("600x400")
        items = history_mod.list_all()
        txt = scrolledtext.ScrolledText(win, wrap="word", font=("Courier", 10))
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        if not items:
            txt.insert("1.0", "Kein Verlauf vorhanden.")
        else:
            for d in items:
                txt.insert("end", f"{d['id']}  {d.get('name','')}  {d.get('status','')}  {d.get('created','')}\n")
        txt.config(state="disabled")

    def _setup(self):
        profil = load_profile() or {}
        win = tk.Toplevel(self)
        win.title("Setup / Stammdaten")
        win.geometry("460x360")
        tk.Label(win, text="Firma:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        e_betrieb = tk.Entry(win, width=40); e_betrieb.grid(row=0, column=1, padx=8)
        e_betrieb.insert(0, profil.get("betrieb", ""))
        tk.Label(win, text="Kanton (AG/ZH/BE…):").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        e_kanton = tk.Entry(win, width=10); e_kanton.grid(row=1, column=1, sticky="w", padx=8)
        e_kanton.insert(0, profil.get("kanton", "AG"))
        tk.Label(win, text="MWST %:").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        e_mwst = tk.Entry(win, width=10); e_mwst.grid(row=2, column=1, sticky="w", padx=8)
        e_mwst.insert(0, str(profil.get("mwst", 7.7)))
        def save():
            p = {"betrieb": e_betrieb.get(), "kanton": e_kanton.get().upper(),
                 "mwst": float(e_mwst.get() or 7.7)}
            save_profile(p)
            messagebox.showinfo("Gespeichert", "Stammdaten gespeichert.")
            win.destroy()
        tk.Button(win, text="Speichern", command=save, bg="darkgreen", fg="white").grid(row=3, column=1, sticky="w", padx=8, pady=10)

    def _agent(self):
        win = tk.Toplevel(self)
        win.title("KI-Agent")
        win.geometry("640x520")
        txt = scrolledtext.ScrolledText(win, wrap="word", font=("Helvetica", 10))
        txt.pack(fill="both", expand=True, padx=8, pady=6)
        txt.insert("1.0", "KI-Agent bereit. Befehle z.B.:\n"
                          "- 'wechsle auf Kanton Aargau'\n"
                          "- 'exportiere nach Abacus'\n"
                          "- 'bepreise das Devis'\n")
        entry = tk.Entry(win)
        entry.pack(fill="x", padx=8, pady=6)
        def send():
            cmd = entry.get().strip()
            if not cmd:
                return
            entry.delete(0, "end")
            txt.insert("end", f"\nDu: {cmd}\n")
            try:
                from devispro import bridge_agent as agent
                antw = agent.chat(cmd)
                txt.insert("end", f"Agent: {antw}\n")
            except Exception as e:
                txt.insert("end", f"Fehler: {e}\n")
            txt.see("end")
        tk.Button(win, text="Senden", command=send, bg="darkorange", fg="white").pack(padx=8, pady=4)


def main():
    app = DevisProApp()
    app.mainloop()


if __name__ == "__main__":
    main()

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


def chf(value):
    """Schweizer Zahlenformat: Tausender mit ', Dezimal mit '.'."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{v:,.2f}".replace(",", "'")


class DevisProApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DevisPro - Bau-Devis Bepreisung [vG0817]")
        self.geometry("1100x780")
        self.devis = None
        self._pos_by_iid = {}
        self._build_ui()

    def _build_ui(self):
        # clam-theme: einzige tk-kombi unter macOS/Tk8.6 die button-background farbig malt
        try:
            self._style = ttk.Style()
            self._style.theme_use("clam")
        except Exception:
            self._style = ttk.Style()
        # pro farbe ein style anlegen (fg je nach hell/dunkel)
        for color, light in (("navy", False), ("darkgreen", False), ("darkorange", False),
                             ("purple", False), ("steelblue", False), ("gray", False),
                             ("white", True)):
            fg = "black" if light else "white"
            name = color.lower() + ".TButton"
            self._style.configure(name, background=color, foreground=fg,
                                  font=FONT, padding=(10, 5))
            # hover (active): tk/clam macht bg hellgrau -> schrift MUSS schwarz sein, sonst unlesbar
            hover_bg = color if light else "#dddddd"
            self._style.map(name,
                            foreground=[("active", "black")],
                            background=[("active", hover_bg)])
        main = tk.Frame(self)
        main.pack(fill="both", expand=True)

        # ---- Seitenleiste ----
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
        self.right = right
        self.proj = tk.Label(right, text="Kein Devis geladen", font=("Helvetica", 14, "bold"), anchor="w")
        self.proj.pack(fill="x", padx=16, pady=(10, 2))
        self.kachel = tk.Frame(right)
        self.kachel.pack(fill="x", padx=16, pady=(0, 8))
        self._kachel("Netto", "0.00", "navy")
        self._kachel("MWST", "0.00", "darkorange")
        self._kachel("Brutto", "0.00", "darkgreen")
        self.info = tk.Label(right, text="", fg="#555", anchor="w")
        self.info.pack(fill="x", padx=14, pady=(6, 2))

        # ---- Rabatt (global, %), live anwendbar ----
        self.rabatt = 0.0
        rframe = tk.Frame(right)
        rframe.pack(fill="x", padx=14, pady=(2, 6))
        tk.Label(rframe, text="Rabatt %:", anchor="w").pack(side="left")
        self.rabatt_var = tk.StringVar(value="0")
        self.rabatt_entry = tk.Entry(rframe, textvariable=self.rabatt_var, width=8)
        self.rabatt_entry.pack(side="left", padx=(4, 8))
        ttk.Button(rframe, text="Anwenden", style="steelblue.TButton",
                   command=self._apply_rabatt, cursor="hand2").pack(side="left")

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
        self.tree.bind("<Double-1>", lambda e: self._edit_pos())

        # ---- Aktionsleiste fuer Positionen ----
        pbar = tk.Frame(right)
        pbar.pack(fill="x", padx=14, pady=(0, 6))
        ttk.Button(pbar, text="+ Position", style="darkgreen.TButton",
                   command=self._add_pos, cursor="hand2").pack(side="left", padx=(0, 6))
        ttk.Button(pbar, text="Bearbeiten", style="steelblue.TButton",
                   command=self._edit_pos, cursor="hand2").pack(side="left", padx=(0, 6))
        ttk.Button(pbar, text="Löschen", style="darkorange.TButton",
                   command=self._del_pos, cursor="hand2").pack(side="left", padx=(0, 6))

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
    _LIGHT = {"white", "#eeeeee", "#e0e0e0", "#dddddd", "yellow", "khaki"}

    def _btn(self, parent, text, cmd, color):
        ttk.Button(parent, text=text, command=cmd, style=color.lower() + ".TButton",
                   cursor="hand2").pack(fill="x", padx=8, pady=2)

    def _kachel(self, label, wert, color):
        f = tk.Frame(self.kachel, relief="ridge", bd=1, bg="#ffffff")
        f.pack(side="left", padx=4, pady=2, ipadx=8, ipady=3)
        tk.Label(f, text=label, font=("Helvetica", 8, "bold"), fg="#777", bg="#ffffff").pack()
        tk.Label(f, text=wert + " CHF", font=("Helvetica", 11, "bold"), fg=color, bg="#ffffff").pack()

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
                self.rabatt = 0.0
                self.after(0, self._fill_table)
                eigen = devis.meta.get("eigene_preise")
                mode = "eigene Preise" if eigen else "CH-Durchschnitt (Simulation)"
                self.after(0, lambda: self._status(f"Devis {did} | {len(devis.positions)} Positionen | {mode}"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Import fehlgeschlagen", str(e)))
        threading.Thread(target=work, daemon=True).start()

    def _neu(self):
        self.devis = Devis(meta={"projekt": "Neues Devis"}, positions=[])
        self.rabatt = 0.0
        self.rabatt_var.set("0")
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
        self._pos_by_iid = {}
        if not self.devis:
            return
        netto = 0.0
        for idx, p in enumerate(self.devis.positions):
            betrag = p.betrag or 0.0
            netto += betrag
            iid = self.tree.insert("", "end", values=(
                p.pos_nr, (p.text or "")[:60],
                f"{p.menge:.1f}" if p.menge else "",
                p.einheit or "",
                chf(p.ep) if p.ep else "",
                chf(betrag) if betrag else ""))
            self._pos_by_iid[iid] = idx
        self.proj.config(text=str(self.devis.meta.get("projekt", "")) or "Devis")
        self._update_kacheln(netto)

    def _sel_index(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return self._pos_by_iid.get(sel[0])

    def _add_pos(self):
        if not self.devis:
            messagebox.showinfo("Hinweis", "Bitte zuerst ein Devis importieren oder 'Neues Devis' wählen.")
            return
        self._pos_dialog(None)

    def _edit_pos(self):
        idx = self._sel_index()
        if idx is None:
            messagebox.showinfo("Hinweis", "Bitte zuerst eine Position in der Tabelle auswählen.")
            return
        self._pos_dialog(idx)

    def _del_pos(self):
        idx = self._sel_index()
        if idx is None:
            messagebox.showinfo("Hinweis", "Bitte zuerst eine Position in der Tabelle auswählen.")
            return
        if not messagebox.askyesno("Löschen", "Position wirklich löschen?"):
            return
        del self.devis.positions[idx]
        self._fill_table()
        self._status("Position gelöscht.")
        self._set_info("Position entfernt. Kacheln aktualisiert.")

    def _pos_dialog(self, idx):
        """Dialog zum Anlegen (idx=None) oder Bearbeiten (idx>=0) einer Position.
        Betrag wird aus EP x Menge neu berechnet."""
        editing = idx is not None
        p = self.devis.positions[idx] if editing else Position("", "", 0.0, "")

        win = tk.Toplevel(self)
        win.title("Position bearbeiten" if editing else "Neue Position")
        win.geometry("520x370")
        win.transient(self)
        win.grab_set()

        def mk(row, label, textvar):
            tk.Label(win, text=label).grid(row=row, column=0, sticky="w", padx=10, pady=5)
            e = tk.Entry(win, textvariable=textvar, width=44)
            e.grid(row=row, column=1, padx=10, pady=5)
            return e

        v_pos = tk.StringVar(value=p.pos_nr)
        v_text = tk.StringVar(value=p.text or "")
        v_menge = tk.StringVar(value=f"{p.menge:.1f}" if p.menge else "")
        v_einh = tk.StringVar(value=p.einheit or "")
        v_ep = tk.StringVar(value=f"{p.ep:.2f}" if p.ep is not None else "")

        mk(0, "Pos-Nr. (z.B. 0901):", v_pos)
        mk(1, "Bezeichnung:", v_text)
        mk(2, "Menge:", v_menge)
        mk(3, "Einheit (St./m2/h):", v_einh)
        mk(4, "Einheitspreis CHF:", v_ep)

        # live-vorschau betrag
        v_info = tk.StringVar(value="")
        tk.Label(win, textvariable=v_info, fg="#555").grid(row=5, column=1, sticky="w", padx=10, pady=2)

        def calc_preview():
            try:
                m = float(v_menge.get().replace(",", ".") or 0)
                ep = float(v_ep.get().replace(",", ".") or 0)
                v_info.set(f"Betrag = {chf(m * ep)} CHF  (Menge x EP)")
            except ValueError:
                v_info.set("")

        for v in (v_menge, v_ep):
            v.trace_add("write", lambda *a: calc_preview())
        calc_preview()

        def save():
            try:
                menge = float(v_menge.get().replace(",", ".") or 0)
                ep = float(v_ep.get().replace(",", ".") or 0) if v_ep.get().strip() else None
            except ValueError:
                messagebox.showerror("Fehler", "Menge und Einheitspreis müssen Zahlen sein.")
                return
            pos = Position(
                pos_nr=v_pos.get().strip() or "(neu)",
                text=v_text.get().strip(),
                menge=menge,
                einheit=v_einh.get().strip(),
                ep=ep,
            )
            pos.fill()  # betrag = menge x ep
            if editing:
                self.devis.positions[idx] = pos
            else:
                self.devis.positions.append(pos)
            self._fill_table()
            win.destroy()
            self._status("Position gespeichert.")
            self._set_info("Position aktualisiert – Betrag aus Menge × EP berechnet.")

        self._dlg_btn(win, "Speichern", save, "darkgreen").grid(row=6, column=1, sticky="e", padx=10, pady=12)
        win.columnconfigure(1, weight=1)

    def _update_kacheln(self, netto):
        rabatt = getattr(self, "rabatt", 0.0) or 0.0
        netto_rab = netto * (1 - rabatt / 100.0)
        mwst = self.devis.meta.get("mwst") or 7.7
        for w in self.kachel.winfo_children():
            w.destroy()
        if rabatt:
            self._kachel("Netto", chf(netto), "navy")
            self._kachel("Rabatt " + str(rabatt) + "%", "-" + chf(netto * rabatt / 100.0), "darkorange")
            self._kachel("MWST " + str(mwst) + "%", chf(netto_rab * mwst / 100.0), "darkorange")
            self._kachel("Brutto", chf(netto_rab * (1 + mwst / 100.0)), "darkgreen")
        else:
            self._kachel("Netto", chf(netto), "navy")
            self._kachel("MWST " + str(mwst) + "%", chf(netto * mwst / 100.0), "darkorange")
            self._kachel("Brutto", chf(netto * (1 + mwst / 100.0)), "darkgreen")

    def _apply_rabatt(self):
        try:
            val = float(str(self.rabatt_var.get()).replace(",", ".").strip() or "0")
        except ValueError:
            messagebox.showerror("Rabatt", "Bitte eine Zahl eingeben (z.B. 5 fuer 5 %).")
            return
        if val < 0 or val >= 100:
            messagebox.showerror("Rabatt", "Rabatt muss zwischen 0 und 100 % liegen.")
            return
        self.rabatt = val
        # netto aus positionen neu summieren und kacheln aktualisieren
        netto = sum((p.betrag or 0.0) for p in (self.devis.positions if self.devis else []))
        self._update_kacheln(netto)
        self._set_info(f"Rabatt von {val:g} % angewendet.")

    def _set_info(self, txt):
        self.info.config(text=txt)

    def _export(self, kind):
        if not self.devis:
            messagebox.showinfo("Hinweis", "Bitte zuerst ein Devis importieren/erstellen.")
            return
        if kind == "fibu":
            self._export_fibu()
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
            elif kind == "pdf":
                from devispro import pdf_export
                rabatt = getattr(self, "rabatt", 0.0) or 0.0
                pdf_export.write_pdf(self.devis, path, rabatt)
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

    def _export_fibu(self):
        if not self.devis:
            messagebox.showinfo("Hinweis", "Bitte zuerst ein Devis importieren/erstellen.")
            return
        from devispro import accounting
        try:
            systeme = accounting.liste()
        except Exception:
            systeme = [{"id": "csv", "name": "Generisches CSV"}]

        win = tk.Toplevel(self)
        win.title("Buchhaltungs-Export")
        win.geometry("440x280")
        win.transient(self)
        win.grab_set()

        tk.Label(win, text="Zielsystem:").grid(row=0, column=0, sticky="w", padx=10, pady=6)
        sys_ids = [s["id"] for s in systeme]
        sys_names = [f"{s['name']} ({s.get('land','')})" for s in systeme]
        v_sys = tk.StringVar(value=sys_ids[0] if sys_ids else "csv")
        cb = ttk.Combobox(win, textvariable=v_sys, values=sys_names, state="readonly", width=30)
        cb.grid(row=0, column=1, padx=10, pady=6)
        cb.current(0)

        tk.Label(win, text="Beleg-Nr.:").grid(row=1, column=0, sticky="w", padx=10, pady=6)
        v_beleg = tk.StringVar(value="OFFERTe1")
        tk.Entry(win, textvariable=v_beleg, width=20).grid(row=1, column=1, padx=10, pady=6)

        tk.Label(win, text="Datum (JJJJMMTT):").grid(row=2, column=0, sticky="w", padx=10, pady=6)
        v_datum = tk.StringVar(value="20260818")
        tk.Entry(win, textvariable=v_datum, width=20).grid(row=2, column=1, padx=10, pady=6)

        from devispro.stammdaten import load_profile
        profil = load_profile() or {}
        if "mwst_pct" not in profil:
            profil["mwst_pct"] = self.devis.meta.get("mwst") or 7.7

        def do_export():
            sys_id = sys_ids[cb.current()] if cb.current() >= 0 else v_sys.get()
            beleg = v_beleg.get().strip() or "OFFERTe1"
            datum = v_datum.get().strip() or "20260818"
            path = filedialog.asksaveasfilename(
                title="Buchhaltungs-Export speichern",
                defaultextension=".csv",
                initialfile=f"{beleg}_{sys_id}.csv",
                filetypes=[("CSV", "*.csv"), ("Alle", "*.*")])
            if not path:
                return
            try:
                data = accounting.export(sys_id, self.devis, profil, beleg, datum)
                with open(path, "wb") as f:
                    f.write(data)
                win.destroy()
                messagebox.showinfo("Exportiert", f"Buchhaltung ({sys_id}) gespeichert:\n{path}")
            except Exception as e:
                messagebox.showerror("Fehler", str(e))

        self._dlg_btn(win, "Exportieren", do_export, "steelblue").grid(row=3, column=1, sticky="e", padx=10, pady=14)
        win.columnconfigure(1, weight=1)
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
            lines.append(f"{str(p.pos_nr):<10}{(p.text or '')[:40]:<42}{p.menge:>8.1f} {str(p.einheit or ''):<8}{chf(p.betrag):>16}")
        lines += ["-" * 84, f"{'NETTO':<62}{chf(netto):>16} CHF"]
        mwst = self.devis.meta.get("mwst") or 7.7
        rabatt = getattr(self, "rabatt", 0.0) or 0.0
        if rabatt:
            netto_rab = netto * (1 - rabatt / 100.0)
            lines += [f"{'RABATT '+str(rabatt)+'%':<62}{'-'+chf(netto*rabatt/100.0):>16} CHF",
                      f"{'MWST '+str(mwst)+'%':<62}{chf(netto_rab*mwst/100.0):>16} CHF",
                      f"{'BRUTTO':<62}{chf(netto_rab*(1+mwst/100.0)):>16} CHF"]
        else:
            lines += [f"{'MWST '+str(mwst)+'%':<62}{chf(netto*mwst/100.0):>16} CHF",
                      f"{'BRUTTO':<62}{chf(netto*(1+mwst/100.0)):>16} CHF"]
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
        self._dlg_btn(win, "Speichern", save, "darkgreen").grid(row=3, column=1, sticky="w", padx=8, pady=10)

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
        self._dlg_btn(win, "Senden", send, "darkorange").pack(padx=8, pady=4)

    def _dlg_btn(self, parent, text, cmd, color):
        # ttk.Button mit clam-style (farbig + klickbar unter macOS/Tk8.6)
        return ttk.Button(parent, text=text, command=cmd,
                          style=color.lower() + ".TButton", cursor="hand2")


def main():
    app = DevisProApp()
    app.mainloop()


if __name__ == "__main__":
    main()

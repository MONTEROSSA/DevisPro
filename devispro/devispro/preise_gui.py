"""Profi-Preislisten-Manager (GUI).

Komfortabler Tabellen-Editor fuer die eigenen Leistungspreise:
  bkp | bezeichnung | einheit | ep_chf | stundensatz | kosten | kategorie
Mit Hinzufuegen / Bearbeiten / Loeschen / Suchen und CSV-Import.
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import firmen_preise as fp
from . import data_store as ds
from . import preise_import as pi

COLS = [
    ("bkp", "BKP/NPK", 90),
    ("bezeichnung", "Bezeichnung", 320),
    ("einheit", "Einheit", 70),
    ("ep_chf", "EP CHF", 90),
    ("stundensatz_chf", "Std-Lohn", 90),
    ("kosten_chf", "Kosten", 90),
    ("kategorie", "Kategorie", 120),
]


class PreislistenManager(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Preisliste pflegen - DevisPro")
        self.geometry("900x560")
        self._build()

    def _build(self):
        # Suchleiste
        bar = tk.Frame(self)
        bar.pack(fill="x", padx=10, pady=6)
        tk.Label(bar, text="Suche:").pack(side="left")
        self.suche = tk.StringVar()
        e = tk.Entry(bar, textvariable=self.suche, width=30)
        e.pack(side="left", padx=(4, 8))
        e.bind("<KeyRelease>", lambda ev: self._refresh())
        ttk.Button(bar, text="+ Neu", command=self._neu, cursor="hand2").pack(side="left", padx=4)
        ttk.Button(bar, text="Bearbeiten", command=self._bearbeiten, cursor="hand2").pack(side="left", padx=4)
        ttk.Button(bar, text="Löschen", command=self._loeschen, cursor="hand2").pack(side="left", padx=4)
        ttk.Button(bar, text="CSV importieren", command=self._import, cursor="hand2").pack(side="left", padx=4)
        ttk.Button(bar, text="Excel importieren", command=self._import_xlsx, cursor="hand2").pack(side="left", padx=4)
        ttk.Button(bar, text="PDF importieren", command=self._import_pdf, cursor="hand2").pack(side="left", padx=4)
        ttk.Button(bar, text="CSV exportieren", command=self._export, cursor="hand2").pack(side="left", padx=4)

        # Tabelle
        f = tk.Frame(self)
        f.pack(fill="both", expand=True, padx=10, pady=6)
        self.tree = ttk.Treeview(f, columns=[c[0] for c in COLS], show="headings", height=20)
        for key, label, w in COLS:
            self.tree.heading(key, text=label)
            self.tree.column(key, width=w, minwidth=60, stretch=(key == "bezeichnung"))
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(f, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)

        self._refresh()
        self.status = tk.Label(self, text="", fg="#555", anchor="w")
        self.status.pack(fill="x", padx=10, pady=4)
        self._set_status()

    def _rows(self):
        zeilen = fp.alle_zeilen()
        q = self.suche.get().strip().lower()
        if q:
            zeilen = [z for z in zeilen if q in str(z.get("bezeichnung", "")).lower()
                      or q in str(z.get("bkp", "")).lower()
                      or q in str(z.get("kategorie", "")).lower()]
        return zeilen

    def _refresh(self):
        for it in self.tree.get_children():
            self.tree.delete(it)
        for z in self._rows():
            self.tree.insert("", "end", values=(
                z.get("bkp", ""), z.get("bezeichnung", ""), z.get("einheit", ""),
                z.get("ep_chf", ""), z.get("stundensatz_chf", ""), z.get("kosten_chf", ""),
                z.get("kategorie", "")))
        self._set_status()

    def _set_status(self):
        n = len(self._rows())
        self.status.config(text=f"{n} Preise erfasst  |  gespeichert in {ds.PREISE_PATH}")

    def _selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Hinweis", "Bitte zuerst eine Zeile auswählen.")
            return None
        idx = self.tree.index(sel[0])
        return self._rows()[idx]

    def _neu(self):
        self._editor({}, neu=True)

    def _bearbeiten(self):
        z = self._selected()
        if z is not None:
            self._editor(z, neu=False)

    def _editor(self, zeile, neu):
        win = tk.Toplevel(self)
        win.title("Preis erfassen" if neu else "Preis bearbeiten")
        win.geometry("520x320")
        vars_ = {}
        for i, (key, label, _) in enumerate(COLS):
            tk.Label(win, text=label + ":").grid(row=i, column=0, sticky="w", padx=10, pady=4)
            v = tk.StringVar(value=str(zeile.get(key, "")))
            vars_[key] = v
            tk.Entry(win, textvariable=v, width=40).grid(row=i, column=1, padx=10, pady=4)

        def save():
            neue = {k: vars_[k].get().strip() for k in vars_}
            # numerisch bereinigen
            for fld in ("ep_chf", "stundensatz_chf", "kosten_chf"):
                if neue[fld] == "":
                    neue[fld] = ""
            fp.zeile_speichern(neue)
            win.destroy()
            self._refresh()
            messagebox.showinfo("Gespeichert", "Preis gespeichert.")

        ttk.Button(win, text="Speichern", command=save, cursor="hand2").grid(row=len(COLS), column=1, sticky="w", padx=10, pady=12)

    def _loeschen(self):
        z = self._selected()
        if z is None:
            return
        if not messagebox.askyesno("Löschen", f"Preis '{z.get('bezeichnung','')}' wirklich löschen?"):
            return
        zeilen = fp.alle_zeilen()
        q = (z.get("bkp", "").strip().lower(), z.get("bezeichnung", "").strip().lower())
        for i, x in enumerate(zeilen):
            xk = (x.get("bkp", "").strip().lower(), x.get("bezeichnung", "").strip().lower())
            if xk == q:
                fp.zeile_loeschen(i)
                break
        self._refresh()

    def _import(self):
        pf = filedialog.askopenfilename(title="Preisliste (CSV)",
                                        filetypes=[("CSV", "*.csv *.txt"), ("Alle", "*.*")])
        if not pf:
            return
        try:
            n = fp.speichern_aus_upload(pf)
            self._refresh()
            messagebox.showinfo("Importiert", f"{n} Preise aus {os.path.basename(pf)} übernommen.")
        except Exception as e:
            messagebox.showerror("Fehler", str(e))

    def _import_xlsx(self):
        pf = filedialog.askopenfilename(title="Preisliste (Excel)",
                                        filetypes=[("Excel", "*.xlsx *.xls"), ("Alle", "*.*")])
        if not pf:
            return
        try:
            n = pi.import_xlsx(pf)
            self._refresh()
            messagebox.showinfo("Importiert", f"{n} Preise aus {os.path.basename(pf)} übernommen.")
        except Exception as e:
            messagebox.showerror("Excel-Import fehlgeschlagen", str(e))

    def _import_pdf(self):
        pf = filedialog.askopenfilename(title="Preisliste (PDF)",
                                        filetypes=[("PDF", "*.pdf"), ("Alle", "*.*")])
        if not pf:
            return
        try:
            n = pi.import_pdf(pf)
            self._refresh()
            messagebox.showinfo("Importiert", f"{n} Preise aus {os.path.basename(pf)} übernommen.")
        except Exception as e:
            messagebox.showerror("PDF-Import fehlgeschlagen", str(e))

    def _export(self):
        pf = filedialog.asksaveasfilename(title="Preisliste exportieren (CSV)",
                                          defaultextension=".csv",
                                          filetypes=[("CSV", "*.csv")])
        if not pf:
            return
        try:
            import shutil
            shutil.copyfile(ds.PREISE_PATH, pf)
            messagebox.showinfo("Exportiert", f"Preisliste nach {pf} kopiert.")
        except Exception as e:
            messagebox.showerror("Fehler", str(e))

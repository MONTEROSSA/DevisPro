#!/usr/bin/env python3
"""Rewrite _build_analysen method completely with correct indentation."""

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'r') as f:
    content = f.read()

lines = content.splitlines(keepends=True)

# Find the start and end of _build_analysen
start_idx = None
end_idx = None

for i, line in enumerate(lines):
    stripped = line.lstrip()
    if stripped.startswith('def _build_analysen') and i > 500:
        start_idx = i
        break

# Find next class method after _build_analysen
if start_idx is not None:
    for i in range(start_idx + 1, len(lines)):
        stripped = lines[i].lstrip()
        if stripped.startswith('def ') and lines[i].startswith('    ') and not lines[i].startswith(' ' * 8):
            end_idx = i
            break
    if end_idx is None:
        end_idx = len(lines)

print(f"_build_analysen: lines {start_idx+1} to {end_idx}")

# New _build_analysen method with correct indentation
new_method = '''    def _build_analysen(self, parent):
        info = ctk.CTkFrame(parent, fg_color=CTK_PANEL)
        info.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(info,
                     text="BEREICH 5 \\u2014 ANALYSEN-BIBLIOTHEK\\n"
                          "Verwalten Sie Kalkulations-Analysen mit Zuschl\\u00e4gen (Lohn, Material, Ger\\u00e4t, AGK, GAV, Wagnis, Gewinn).\\n"
                          "Drag & Drop eine Analyse auf eine Devis-Position, um die Zuschl\\u00e4ge anzuwenden.",
                     font=FONT, fg_color=CTK_PANEL, text_color=CTK_TEXT_DIM, justify="left",
                     anchor="w").pack(fill="x", padx=12, pady=8)

        # Toolbar
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.pack(fill="x", padx=10, pady=4)
        accent_button(bar, text="Neue Analyse", command=self._analysen_neu, kind="accent").pack(side="left", padx=(0, 6))
        blue_button(bar, text="Aus Template", command=self._analysen_aus_template, kind="blue").pack(side="left", padx=(0, 6))
        ghost_button(bar, text="Import JSON", command=self._analysen_import, kind="ghost").pack(side="left", padx=(0, 6))
        ghost_button(bar, text="Team Export (ZIP)", command=self._analysen_team_export, kind="ghost").pack(side="left", padx=(0, 6))
        ghost_button(bar, text="Team Import (ZIP)", command=self._analysen_team_import, kind="ghost").pack(side="left", padx=(0, 6))

        # Liste der Analysen (Sidebar links)
        left = ctk.CTkFrame(parent, fg_color=CTK_PANEL_DK, border_color=CTK_BORDER, border_width=1, corner_radius=8)
        left.pack(side="left", fill="y", padx=(10, 5), pady=8, ipadx=5, ipady=5)
        left.configure(width=300)
        left.pack_propagate(False)

        ctk.CTkLabel(left, text="\\U0001f4c1 Analysen", font=FONT_H3, text_color=CTK_ACCENT).pack(anchor="w", padx=10, pady=(10, 5))

        self.analysen_listbox = tk.Listbox(left, font=("Helvetica", 11), bg=CTK_PANEL_DK, fg=CTK_TEXT,
             selectbackground=CTK_ACCENT, selectforeground="white",
             borderwidth=0, highlightthickness=0, activestyle="none")
        self.analysen_listbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.analysen_listbox.bind("<<ListboxSelect>>", self._analysen_on_select)
        self.analysen_listbox.bind("<Double-Button-1>", lambda e: self._analysen_bearbeiten())
        self.analysen_listbox.bind("<Delete>", lambda e: self._analysen_loeschen())

        # Details / Editor (rechts)
        right = ctk.CTkFrame(parent, fg_color=CTK_PANEL_DK, border_color=CTK_BORDER, border_width=1, corner_radius=8)
        right.pack(side="left", fill="both", expand=True, padx=(5, 10), pady=8)

        self.analysen_detail_frame = right
        self._analysen_liste_aktualisieren()
        self._analysen_zeige_leer()

    def _analysen_liste_aktualisieren(self):
        self.analysen_listbox.delete(0, tk.END)
        self._analysen_cache = anabib.liste_analysen()
        for a in self._analysen_cache:
            quelle_icon = "\\U0001f4dd" if a["quelle"] == "benutzer" else "\\U0001f4cb"
            summe = a["zuschlaege_summe"]
            self.analysen_listbox.insert(tk.END, f"{quelle_icon} {a['name']} v{a['version']} ({summe:.1f}%)")

    def _analysen_on_select(self, event):
        sel = self.analysen_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < len(self._analysen_cache):
            a = self._analysen_cache[idx]
            self._analysen_zeige_detail(a)

    def _analysen_zeige_leer(self):
        for w in self.analysen_detail_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.analysen_detail_frame, text="W\\u00e4hlen Sie eine Analyse links aus,\\noder erstellen Sie eine neue.",
                     font=FONT, text_color=CTK_TEXT_DIM, fg_color=CTK_PANEL_DK).pack(expand=True)

    def _analysen_zeige_detail(self, a_data: dict):
        for w in self.analysen_detail_frame.winfo_children():
            w.destroy()

        # Header
        hdr = ctk.CTkFrame(self.analysen_detail_frame, fg_color=CTK_PANEL)
        hdr.pack(fill="x", padx=12, pady=10)
        quelle_txt = "Benutzerdefiniert" if a_data["quelle"] == "benutzer" else "Template (schreibgesch\\u00fctzt)"
        ctk.CTkLabel(hdr, text=f"{a_data['name']} v{a_data['version']}", font=FONT_H2, text_color=CTK_TEXT).pack(anchor="w")
        ctk.CTkLabel(hdr, text=f"{quelle_txt} \\u00b7 Summe Zuschl\\u00e4ge: {a_data['zuschlaege_summe']:.1f}%", font=FONT_SM, text_color=CTK_TEXT_DIM).pack(anchor="w")
        if a_data.get("beschreibung"):
            ctk.CTkLabel(hdr, text=a_data["beschreibung"], font=FONT_SM, text_color=CTK_TEXT_DIM, wraplength=500, justify="left").pack(anchor="w", pady=(4, 0))

        # Zuschl\\u00e4ge anzeigen/bearbeiten
        analyse = anabib.lade_analyse(a_data["name"], a_data["version"])
        if not analyse:
            ctk.CTkLabel(self.analysen_detail_frame, text="Fehler beim Laden.", text_color=CTK_RED).pack(pady=20)
            return

        z = analyse.zuschlaege.to_dict()
        felder = [
            ("lohn", "Lohnzuschlag %"),
            ("material", "Materialzuschlag %"),
            ("geraet", "Ger\\u00e4tezuschlag %"),
            ("agk", "AGK (Allg. Gesch\\u00e4ftskosten) %"),
            ("gav", "GAV / Sozialleistungen %"),
            ("wagnis", "Wagnis / Risiko %"),
            ("gewinn", "Gewinn / Marge %"),
        ]

        self._analysen_vars = {}
        grid = ctk.CTkFrame(self.analysen_detail_frame, fg_color="transparent")
        grid.pack(fill="x", padx=12, pady=8)
        for i, (key, label) in enumerate(felder):
            r = i // 2
            c = (i % 2) * 2
            ctk.CTkLabel(grid, text=label + ":").grid(row=r, column=c, sticky="w", padx=8, pady=4)
            v = tk.StringVar(value=str(z.get(key, 0.0)))
            self._analysen_vars[key] = v
            ctk.CTkEntry(grid, textvariable=v, width=10).grid(row=r, column=c+1, padx=8, pady=4)

        # Summe live
        self._analysen_summe_var = tk.StringVar(value=f"Summe: {sum(z.values()):.1f}%")
        ctk.CTkLabel(self.analysen_detail_frame, textvariable=self._analysen_summe_var, font=("Helvetica", 11, "bold"), text_color=CTK_ACCENT).pack(anchor="w", padx=12, pady=(4, 8))

        def update_summe(*_):
            try:
                s = sum(float(v.get() or 0) for v in self._analysen_vars.values())
                self._analysen_summe_var.set(f"Summe: {s:.1f}%")
            except Exception:
                pass
        for v in self._analysen_vars.values():
            v.trace_add("write", update_summe)

        # Buttons
        btn_frame = ctk.CTkFrame(self.analysen_detail_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=10)

        if a_data["quelle"] == "benutzer":
            accent_button(btn_frame, text="Speichern", command=lambda: self._analysen_speichern(a_data["name"], a_data["version"]), kind="accent").pack(side="left", padx=(0, 6))
            red_button(btn_frame, text="L\\u00f6schen", command=self._analysen_loeschen, kind="red").pack(side="left", padx=(0, 6))
        else:
            ghost_button(btn_frame, text="Als Kopie speichern", command=lambda: self._analysen_als_kopie_speichern(a_data["name"]), kind="ghost").pack(side="left", padx=(0, 6))

        blue_button(btn_frame, text="Auf Position anwenden", command=self._analysen_auf_position_anwenden, kind="blue").pack(side="left", padx=(0, 6))
        ghost_button(btn_frame, text="Export JSON", command=lambda: self._analysen_export_json(a_data["name"], a_data["version"]), kind="ghost").pack(side="left")

        # Drag & Drop Hinweis
        hint = ctk.CTkLabel(self.analysen_detail_frame,
            text="\\U0001f4cb Tipp: Ziehen Sie den Analyse-Namen aus der Liste per Drag & Drop\\nauf eine Position in Bereich 2, um die Zuschl\\u00e4ge zu \\u00fcbernehmen.",
            font=FONT_SM, text_color=CTK_TEXT_DIM, fg_color=CTK_PANEL_DK, justify="left")
        hint.pack(fill="x", padx=12, pady=(20, 10))

        # Drag & Drop Binding auf Listbox
        self._analysen_drag_bind()

    def _analysen_drag_bind(self):
        """Drag & Drop von der Listbox auf die Treeview in Bereich 2."""
        def on_drag_start(event):
            sel = self.analysen_listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            if idx < len(self._analysen_cache):
                a = self._analysen_cache[idx]
                # Daten f\\u00fcr Drag speichern
                self._drag_analyse = a
                self.analysen_listbox.config(cursor="hand2")

        def on_drag_motion(event):
            pass

        def on_drag_end(event):
            self.analysen_listbox.config(cursor="")

        self.analysen_listbox.bind("<ButtonPress-1>", on_drag_start)
        self.analysen_listbox.bind("<B1-Motion>", on_drag_motion)
        self.analysen_listbox.bind("<ButtonRelease-1>", on_drag_end)

        # Drop-Ziel: Treeview in Bereich 2 vorbereiten
        if hasattr(self, "tree"):
            self.tree.drop_target_register(tk.DND_FILES)  # placeholder, wir nutzen eigenes DnD
            # Wir implementieren DnD \\u00fcber Bindings auf der Treeview
            self.tree.bind("<ButtonRelease-1>", self._analysen_drop_on_tree, add="+")

    def _analysen_drop_on_tree(self, event):
        """Wird aufgerufen wenn Maus auf Treeview losgelassen wird w\\u00e4hrend Drag aktiv."""
        if not hasattr(self, "_drag_analyse") or not self._drag_analyse:
            return
        # Pr\\u00fcfen ob Maus \\u00fcber Treeview ist
        x, y = event.x_root, event.y_root
        widget_under = self.winfo_containing(x, y)
        if widget_under != self.tree and not str(widget_under).startswith(str(self.tree)):
            self._drag_analyse = None
            return

        # Position unter Maus finden
        try:
            row_id = self.tree.identify_row(y - self.tree.winfo_rooty())
            if not row_id:
                self._drag_analyse = None
                return
            idx = self._pos_by_iid.get(row_id)
            if idx is None:
                self._drag_analyse = None
                return
            # Zuschl\\u00e4ge anwenden
            self._analysen_anwenden_auf_position_idx(idx, self._drag_analyse)
            self._drag_analyse = None
        except Exception:
            self._drag_analyse = None

    def _analysen_anwenden_auf_position_idx(self, idx: int, a_data: dict):
        """Wendet die Zuschl\\u00e4ge der Analyse auf die Position an.'''

# Replace the broken method
if start_idx is not None and end_idx is not None:
    new_lines = lines[:start_idx] + [new_method] + lines[end_idx:]
    with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'w') as f:
        f.write(''.join(new_lines))
    print("SUCCESS: Replaced _build_analysen method")
else:
    print("ERROR: Could not find method boundaries")
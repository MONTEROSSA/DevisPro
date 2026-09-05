#!/usr/bin/env python3
"""
KI-Agent Marketplace für DevisPro
Community-Plattform für geteilte Prompts, Analysen und Agent-Konfigurationen.
Offline-First: Lokaler Cache + optionaler Sync via Shared Folder (NAS/iCloud/OneDrive).
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
import json
import os
import hashlib
import threading
import time


class MarketplaceCategory(Enum):
    """Kategorien für Marketplace-Einträge"""
    PREISBERECHNUNG = "Preisberechnung"
    ANALYSE = "Analyse"
    EXPORT = "Export"
    IMPORT = "Import"
    KALKULATION = "Kalkulation"
    NACHWERK = "Nachwerk"
    SONSTIGES = "Sonstiges"


class EntryStatus(Enum):
    """Status eines Marketplace-Eintrags"""
    DRAFT = "Entwurf"
    PUBLISHED = "Veröffentlicht"
    ARCHIVED = "Archiviert"
    FLAGGED = "Gemeldet"


@dataclass
class MarketplaceEntry:
    """Ein Marketplace-Eintrag (Prompt, Analyse, Agent-Config)"""
    id: str                          # Eindeutige ID (SHA256 von content + author)
    title: str                       # Titel
    description: str                 # Beschreibung
    category: str                    # Kategorie
    author: str                      # Autor (Name/Email)
    author_id: str                   # Autor-ID (Hash)
    content: str                     # Der eigentliche Prompt/Code/Config
    content_type: str                # "prompt", "python", "json", "yaml", "agent_config"
    tags: List[str] = field(default_factory=list)
    version: str = "1.0"
    status: str = EntryStatus.DRAFT.value
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    downloads: int = 0
    rating: float = 0.0
    rating_count: int = 0
    rating_sum: int = 0
    metadata: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generiert deterministische ID aus Content + Autor"""
        data = f"{self.content}{self.author}{self.created_at}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def add_rating(self, score: int):
        """Fügt Bewertung hinzu (1-5 Sterne)"""
        if 1 <= score <= 5:
            self.rating_sum += score
            self.rating_count += 1
            self.rating = round(self.rating_sum / self.rating_count, 1)
            self.updated_at = datetime.now().isoformat()
    
    def increment_downloads(self):
        self.downloads += 1
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MarketplaceEntry':
        return cls(**data)


class MarketplaceStore:
    """Lokaler Marketplace-Store mit File-System Backend"""
    
    def __init__(self, store_dir: str = "marketplace"):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(exist_ok=True)
        self.entries_file = self.store_dir / "entries.json"
        self.index_file = self.store_dir / "index.json"
        self.entries: Dict[str, MarketplaceEntry] = {}
        self._load()
    
    def _load(self):
        """Lädt alle Einträge"""
        if self.entries_file.exists():
            try:
                with open(self.entries_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for entry_data in data.get('entries', []):
                        entry = MarketplaceEntry.from_dict(entry_data)
                        self.entries[entry.id] = entry
            except Exception:
                pass
    
    def _save(self):
        """Speichert alle Einträge"""
        data = {
            'version': '1.0',
            'updated_at': datetime.now().isoformat(),
            'entries': [e.to_dict() for e in self.entries.values()]
        }
        with open(self.entries_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Index für schnelle Suche
        index = {}
        for entry in self.entries.values():
            index[entry.id] = {
                'title': entry.title,
                'category': entry.category,
                'author': entry.author,
                'tags': entry.tags,
                'status': entry.status,
                'rating': entry.rating,
                'downloads': entry.downloads
            }
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    
    def add(self, entry: MarketplaceEntry) -> str:
        """Fügt Eintrag hinzu"""
        self.entries[entry.id] = entry
        self._save()
        return entry.id
    
    def get(self, entry_id: str) -> Optional[MarketplaceEntry]:
        return self.entries.get(entry_id)
    
    def update(self, entry: MarketplaceEntry):
        entry.updated_at = datetime.now().isoformat()
        self.entries[entry.id] = entry
        self._save()
    
    def delete(self, entry_id: str) -> bool:
        if entry_id in self.entries:
            del self.entries[entry_id]
            self._save()
            return True
        return False
    
    def list_all(self, status: Optional[str] = None, category: Optional[str] = None, 
                 author: Optional[str] = None, tags: Optional[List[str]] = None) -> List[MarketplaceEntry]:
        """Listet Einträge mit Filtern"""
        results = []
        for entry in self.entries.values():
            if status and entry.status != status:
                continue
            if category and entry.category != category:
                continue
            if author and entry.author != author:
                continue
            if tags and not all(tag in entry.tags for tag in tags):
                continue
            results.append(entry)
        
        # Sortierung: veröffentlicht zuerst, dann nach Rating, dann neueste
        results.sort(key=lambda e: (
            e.status != EntryStatus.PUBLISHED.value,
            -e.rating,
            -e.downloads,
            e.created_at
        ))
        return results
    
    def search(self, query: str, limit: int = 50) -> List[MarketplaceEntry]:
        """Volltextsuche in Titel, Beschreibung, Content, Tags"""
        query_lower = query.lower()
        results = []
        for entry in self.entries.values():
            if entry.status != EntryStatus.PUBLISHED.value:
                continue
            searchable = f"{entry.title} {entry.description} {entry.content} {' '.join(entry.tags)}".lower()
            if query_lower in searchable:
                results.append(entry)
                if len(results) >= limit:
                    break
        return results
    
    def get_categories(self) -> List[str]:
        return list(set(e.category for e in self.entries.values() if e.status == EntryStatus.PUBLISHED.value))
    
    def get_authors(self) -> List[str]:
        return list(set(e.author for e in self.entries.values() if e.status == EntryStatus.PUBLISHED.value))


class MarketplaceSync:
    """Synchronisation via Shared Folder (NAS/iCloud/OneDrive)"""
    
    def __init__(self, store: MarketplaceStore, sync_dir: str = None):
        self.store = store
        self.sync_dir = Path(sync_dir) if sync_dir else None
        self._running = False
        self._thread = None
    
    def set_sync_dir(self, sync_dir: str):
        self.sync_dir = Path(sync_dir)
        self.sync_dir.mkdir(parents=True, exist_ok=True)
    
    def push(self) -> Dict:
        """Lokale Änderungen in Sync-Ordner hochladen"""
        if not self.sync_dir:
            return {'success': False, 'error': 'Kein Sync-Ordner konfiguriert'}
        
        try:
            # Entries exportieren
            export_file = self.sync_dir / "marketplace_entries.json"
            data = {
                'version': '1.0',
                'synced_at': datetime.now().isoformat(),
                'source': 'local',
                'entries': [e.to_dict() for e in self.store.entries.values() 
                           if e.status == EntryStatus.PUBLISHED.value]
            }
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return {'success': True, 'exported': len(data['entries'])}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def pull(self) -> Dict:
        """Änderungen aus Sync-Ordner herunterladen"""
        if not self.sync_dir:
            return {'success': False, 'error': 'Kein Sync-Ordner konfiguriert'}
        
        import_file = self.sync_dir / "marketplace_entries.json"
        if not import_file.exists():
            return {'success': True, 'imported': 0, 'message': 'Keine Remote-Daten'}
        
        try:
            with open(import_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            imported = 0
            updated = 0
            for entry_data in data.get('entries', []):
                entry = MarketplaceEntry.from_dict(entry_data)
                existing = self.store.get(entry.id)
                
                if not existing:
                    self.store.add(entry)
                    imported += 1
                elif entry.updated_at > existing.updated_at:
                    self.store.update(entry)
                    updated += 1
            
            return {'success': True, 'imported': imported, 'updated': updated}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def sync(self) -> Dict:
        """Vollständiger Sync (Pull + Push)"""
        pull_result = self.pull()
        push_result = self.push()
        return {
            'pull': pull_result,
            'push': push_result,
            'synced_at': datetime.now().isoformat()
        }
    
    def start_auto_sync(self, interval_minutes: int = 30):
        """Startet automatische Synchronisation"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._auto_sync_loop, 
                                        args=(interval_minutes,), daemon=True)
        self._thread.start()
    
    def stop_auto_sync(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def _auto_sync_loop(self, interval_minutes: int):
        while self._running:
            try:
                self.sync()
            except Exception:
                pass
            time.sleep(interval_minutes * 60)


class MarketplaceGUI:
    """GUI-Integration für Marketplace (für tkinter App)"""
    
    def __init__(self, parent_app, store: MarketplaceStore, sync: Optional[MarketplaceSync] = None):
        self.parent = parent_app
        self.store = store
        self.sync = sync
    
    def show_marketplace(self):
        """Zeigt Marketplace-Hauptfenster"""
        import tkinter as tk
        from tkinter import ttk, scrolledtext, messagebox, filedialog
        
        win = tk.Toplevel(self.parent)
        win.title("KI-Agent Marketplace")
        win.geometry("1100x700")
        
        # Toolbar
        toolbar = tk.Frame(win)
        toolbar.pack(fill="x", padx=8, pady=8)
        
        tk.Button(toolbar, text="Neu erstellen", command=self._create_entry, 
                  bg="darkgreen", fg="white").pack(side="left", padx=4)
        tk.Button(toolbar, text="Meine Einträge", command=self._show_my_entries, 
                  bg="darkblue", fg="white").pack(side="left", padx=4)
        tk.Button(toolbar, text="Sync", command=self._do_sync, 
                  bg="darkorange", fg="white").pack(side="left", padx=4)
        tk.Button(toolbar, text="Einstellungen", command=self._show_settings, 
                  bg="gray").pack(side="left", padx=4)
        
        # Such-Leiste
        search_frame = tk.Frame(win)
        search_frame.pack(fill="x", padx=8, pady=(0, 8))
        
        tk.Label(search_frame, text="Suche:").pack(side="left")
        search_entry = tk.Entry(search_frame, width=40)
        search_entry.pack(side="left", padx=4)
        
        tk.Label(search_frame, text="Kategorie:").pack(side="left", padx=(16, 4))
        cat_var = tk.StringVar(value="Alle")
        cat_combo = ttk.Combobox(search_frame, textvariable=cat_var, 
                                 values=["Alle"] + self.store.get_categories(), 
                                 width=15, state="readonly")
        cat_combo.pack(side="left")
        
        # Treeview
        cols = ("title", "category", "author", "rating", "downloads", "status")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=25)
        tree.heading("title", text="Titel")
        tree.heading("category", text="Kategorie")
        tree.heading("author", text="Autor")
        tree.heading("rating", text="⭐")
        tree.heading("downloads", text="⬇")
        tree.heading("status", text="Status")
        tree.column("title", width=350, stretch=True)
        tree.column("category", width=120, stretch=False)
        tree.column("author", width=150, stretch=False)
        tree.column("rating", width=50, stretch=False, anchor="center")
        tree.column("downloads", width=60, stretch=False, anchor="center")
        tree.column("status", width=100, stretch=False, anchor="center")
        tree.pack(fill="both", expand=True, padx=8, pady=8)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=8)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Detail-Anzeige
        detail_frame = tk.LabelFrame(win, text="Details")
        detail_frame.pack(fill="x", padx=8, pady=8)
        
        detail_text = scrolledtext.ScrolledText(detail_frame, height=8, wrap="word", 
                                                font=("Courier", 9))
        detail_text.pack(fill="x", padx=4, pady=4)
        detail_text.config(state="disabled")
        
        def refresh_tree():
            query = search_entry.get().strip()
            cat = cat_var.get() if cat_var.get() != "Alle" else None
            
            if query:
                entries = self.store.search(query)
            else:
                entries = self.store.list_all(status=EntryStatus.PUBLISHED.value, 
                                             category=cat if cat else None)
            
            tree.delete(*tree.get_children())
            for entry in entries:
                tree.insert("", "end", values=(
                    entry.title[:50],
                    entry.category,
                    entry.author,
                    f"{entry.rating:.1f}" if entry.rating > 0 else "-",
                    entry.downloads,
                    entry.status
                ), tags=(entry.id,))
        
        def on_select(event):
            selection = tree.selection()
            if selection:
                item_id = tree.item(selection[0])['tags'][0]
                entry = self.store.get(item_id)
                if entry:
                    detail_text.config(state="normal")
                    detail_text.delete("1.0", "end")
                    detail_text.insert("1.0", 
                        f"Titel: {entry.title}\n"
                        f"Kategorie: {entry.category}\n"
                        f"Autor: {entry.author}\n"
                        f"Version: {entry.version}\n"
                        f"Status: {entry.status}\n"
                        f"Rating: {entry.rating:.1f} ({entry.rating_count} Bewertungen)\n"
                        f"Downloads: {entry.downloads}\n"
                        f"Tags: {', '.join(entry.tags)}\n"
                        f"\nBeschreibung:\n{entry.description}\n"
                        f"\nContent:\n{entry.content[:500]}..."
                    )
                    detail_text.config(state="disabled")
        
        def on_double_click(event):
            selection = tree.selection()
            if selection:
                item_id = tree.item(selection[0])['tags'][0]
                entry = self.store.get(item_id)
                if entry:
                    self._use_entry(entry)
        
        def do_search():
            refresh_tree()
        
        search_entry.bind("<Return>", lambda e: do_search())
        tk.Button(search_frame, text="Suchen", command=do_search).pack(side="left", padx=8)
        cat_combo.bind("<<ComboboxSelected>>", lambda e: refresh_tree())
        
        tree.bind("<<TreeviewSelect>>", on_select)
        tree.bind("<Double-1>", on_double_click)
        
        # Initial laden
        refresh_tree()
    
    def _create_entry(self):
        """Erstellt neuen Marketplace-Eintrag"""
        import tkinter as tk
        from tkinter import messagebox
        
        win = tk.Toplevel(self.parent)
        win.title("Neuen Marketplace-Eintrag erstellen")
        win.geometry("700x600")
        
        # Formular
        fields = {}
        
        tk.Label(win, text="Titel:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        fields['title'] = tk.Entry(win, width=60)
        fields['title'].grid(row=0, column=1, padx=8, pady=4, sticky="ew")
        
        tk.Label(win, text="Kategorie:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        fields['category'] = ttk.Combobox(win, values=[c.value for c in MarketplaceCategory], 
                                           width=30, state="readonly")
        fields['category'].grid(row=1, column=1, padx=8, pady=4, sticky="w")
        fields['category'].set(MarketplaceCategory.ANALYSE.value)
        
        tk.Label(win, text="Content-Type:").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        fields['content_type'] = ttk.Combobox(win, 
            values=["prompt", "python", "json", "yaml", "agent_config"], 
            width=30, state="readonly")
        fields['content_type'].grid(row=2, column=1, padx=8, pady=4, sticky="w")
        fields['content_type'].set("prompt")
        
        tk.Label(win, text="Tags (kommasepariert):").grid(row=3, column=0, sticky="w", padx=8, pady=4)
        fields['tags'] = tk.Entry(win, width=60)
        fields['tags'].grid(row=3, column=1, padx=8, pady=4, sticky="ew")
        
        tk.Label(win, text="Beschreibung:").grid(row=4, column=0, sticky="nw", padx=8, pady=4)
        fields['description'] = tk.Text(win, height=4, width=60)
        fields['description'].grid(row=4, column=1, padx=8, pady=4, sticky="ew")
        
        tk.Label(win, text="Content (Prompt/Code/Config):").grid(row=5, column=0, sticky="nw", padx=8, pady=4)
        fields['content'] = tk.Text(win, height=15, width=60, font=("Courier", 9))
        fields['content'].grid(row=5, column=1, padx=8, pady=4, sticky="ew")
        
        win.columnconfigure(1, weight=1)
        
        def save_draft():
            entry = MarketplaceEntry(
                id="",
                title=fields['title'].get(),
                description=fields['description'].get("1.0", "end-1c"),
                category=fields['category'].get(),
                author=self._get_current_user(),
                author_id=self._get_user_id(),
                content=fields['content'].get("1.0", "end-1c"),
                content_type=fields['content_type'].get(),
                tags=[t.strip() for t in fields['tags'].get().split(",") if t.strip()],
                status=EntryStatus.DRAFT.value
            )
            self.store.add(entry)
            messagebox.showinfo("Gespeichert", "Entwurf gespeichert.")
            win.destroy()
        
        def publish():
            entry = MarketplaceEntry(
                id="",
                title=fields['title'].get(),
                description=fields['description'].get("1.0", "end-1c"),
                category=fields['category'].get(),
                author=self._get_current_user(),
                author_id=self._get_user_id(),
                content=fields['content'].get("1.0", "end-1c"),
                content_type=fields['content_type'].get(),
                tags=[t.strip() for t in fields['tags'].get().split(",") if t.strip()],
                status=EntryStatus.PUBLISHED.value
            )
            self.store.add(entry)
            messagebox.showinfo("Veröffentlicht", "Eintrag veröffentlicht!")
            win.destroy()
        
        btn_frame = tk.Frame(win)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=16)
        tk.Button(btn_frame, text="Als Entwurf speichern", command=save_draft, 
                  bg="gray").pack(side="left", padx=8)
        tk.Button(btn_frame, text="Veröffentlichen", command=publish, 
                  bg="darkgreen", fg="white").pack(side="left", padx=8)
    
    def _show_my_entries(self):
        """Zeigt nur eigene Einträge"""
        import tkinter as tk
        from tkinter import ttk
        
        win = tk.Toplevel(self.parent)
        win.title("Meine Marketplace-Einträge")
        win.geometry("900x500")
        
        cols = ("title", "category", "status", "rating", "downloads", "created")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=20)
        for col in cols:
            tree.heading(col, text=col.capitalize())
        tree.column("title", width=300)
        tree.column("category", width=120)
        tree.column("status", width=100)
        tree.column("rating", width=60, anchor="center")
        tree.column("downloads", width=80, anchor="center")
        tree.column("created", width=150)
        tree.pack(fill="both", expand=True, padx=8, pady=8)
        
        user_id = self._get_user_id()
        for entry in self.store.list_all(author=self._get_current_user()):
            tree.insert("", "end", values=(
                entry.title[:40],
                entry.category,
                entry.status,
                f"{entry.rating:.1f}" if entry.rating > 0 else "-",
                entry.downloads,
                entry.created_at[:10]
            ), tags=(entry.id,))
        
        def on_double_click(event):
            selection = tree.selection()
            if selection:
                item_id = tree.item(selection[0])['tags'][0]
                entry = self.store.get(item_id)
                if entry:
                    self._edit_entry(entry)
        
        tree.bind("<Double-1>", on_double_click)
    
    def _edit_entry(self, entry: MarketplaceEntry):
        """Bearbeitet eigenen Eintrag"""
        import tkinter as tk
        from tkinter import messagebox
        
        win = tk.Toplevel(self.parent)
        win.title(f"Bearbeiten: {entry.title}")
        win.geometry("700x600")
        
        fields = {}
        
        tk.Label(win, text="Titel:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        fields['title'] = tk.Entry(win, width=60)
        fields['title'].grid(row=0, column=1, padx=8, pady=4, sticky="ew")
        fields['title'].insert(0, entry.title)
        
        tk.Label(win, text="Kategorie:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        fields['category'] = ttk.Combobox(win, values=[c.value for c in MarketplaceCategory], 
                                           width=30, state="readonly")
        fields['category'].grid(row=1, column=1, padx=8, pady=4, sticky="w")
        fields['category'].set(entry.category)
        
        tk.Label(win, text="Content-Type:").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        fields['content_type'] = ttk.Combobox(win, 
            values=["prompt", "python", "json", "yaml", "agent_config"], 
            width=30, state="readonly")
        fields['content_type'].grid(row=2, column=1, padx=8, pady=4, sticky="w")
        fields['content_type'].set(entry.content_type)
        
        tk.Label(win, text="Tags:").grid(row=3, column=0, sticky="w", padx=8, pady=4)
        fields['tags'] = tk.Entry(win, width=60)
        fields['tags'].grid(row=3, column=1, padx=8, pady=4, sticky="ew")
        fields['tags'].insert(0, ", ".join(entry.tags))
        
        tk.Label(win, text="Beschreibung:").grid(row=4, column=0, sticky="nw", padx=8, pady=4)
        fields['description'] = tk.Text(win, height=4, width=60)
        fields['description'].grid(row=4, column=1, padx=8, pady=4, sticky="ew")
        fields['description'].insert("1.0", entry.description)
        
        tk.Label(win, text="Content:").grid(row=5, column=0, sticky="nw", padx=8, pady=4)
        fields['content'] = tk.Text(win, height=15, width=60, font=("Courier", 9))
        fields['content'].grid(row=5, column=1, padx=8, pady=4, sticky="ew")
        fields['content'].insert("1.0", entry.content)
        
        # Status
        tk.Label(win, text="Status:").grid(row=6, column=0, sticky="w", padx=8, pady=4)
        fields['status'] = ttk.Combobox(win, 
            values=[s.value for s in EntryStatus], width=15, state="readonly")
        fields['status'].grid(row=6, column=1, padx=8, pady=4, sticky="w")
        fields['status'].set(entry.status)
        
        win.columnconfigure(1, weight=1)
        
        def save():
            entry.title = fields['title'].get()
            entry.description = fields['description'].get("1.0", "end-1c")
            entry.category = fields['category'].get()
            entry.content_type = fields['content_type'].get()
            entry.tags = [t.strip() for t in fields['tags'].get().split(",") if t.strip()]
            entry.content = fields['content'].get("1.0", "end-1c")
            entry.status = fields['status'].get()
            entry.updated_at = datetime.now().isoformat()
            
            self.store.update(entry)
            messagebox.showinfo("Gespeichert", "Eintrag aktualisiert.")
            win.destroy()
        
        btn_frame = tk.Frame(win)
        btn_frame.grid(row=7, column=0, columnspan=2, pady=16)
        tk.Button(btn_frame, text="Speichern", command=save, 
                  bg="darkblue", fg="white").pack(side="left", padx=8)
        tk.Button(btn_frame, text="Löschen", command=lambda: self._delete_entry(entry, win), 
                  bg="darkred", fg="white").pack(side="left", padx=8)
    
    def _delete_entry(self, entry: MarketplaceEntry, parent_win):
        import tkinter as tk
        from tkinter import messagebox
        if messagebox.askyesno("Löschen", f"Eintrag '{entry.title}' wirklich löschen?"):
            self.store.delete(entry.id)
            parent_win.destroy()
            messagebox.showinfo("Gelöscht", "Eintrag gelöscht.")
    
    def _use_entry(self, entry: MarketplaceEntry):
        """Verwendet Eintrag in der App (kopiert Content, öffnet Agent, etc.)"""
        import tkinter as tk
        from tkinter import messagebox
        
        entry.increment_downloads()
        self.store.update(entry)
        
        # Je nach Content-Type unterschiedliche Aktion
        if entry.content_type == "prompt":
            # In Agent-Fenster kopieren
            self._open_in_agent(entry.content)
        elif entry.content_type in ("python", "json", "yaml", "agent_config"):
            # Als Datei speichern oder in Editor öffnen
            self._save_as_file(entry)
        else:
            messagebox.showinfo("Verwendet", f"Content von '{entry.title}' kopiert.")
            self.parent.clipboard_clear()
            self.parent.clipboard_append(entry.content)
    
    def _open_in_agent(self, prompt: str):
        """Öffnet Prompt im KI-Agent Fenster"""
        # Nutzt existierende _agent Methode der Haupt-App
        if hasattr(self.parent, '_agent'):
            self.parent._agent()
            # TODO: Prompt in Agent-Eingabe einfügen
        else:
            import tkinter.messagebox as messagebox
            messagebox.showinfo("Prompt", f"Prompt kopiert:\n{prompt[:200]}...")
            self.parent.clipboard_clear()
            self.parent.clipboard_append(prompt)
    
    def _save_as_file(self, entry: MarketplaceEntry):
        """Speichert Content als Datei"""
        import tkinter as tk
        from tkinter import filedialog, messagebox
        
        ext_map = {"python": ".py", "json": ".json", "yaml": ".yaml", "agent_config": ".json"}
        ext = ext_map.get(entry.content_type, ".txt")
        
        path = filedialog.asksaveasfilename(
            title=f"Speichern: {entry.title}",
            defaultextension=ext,
            filetypes=[(f"{entry.content_type.upper()}", f"*{ext}"), ("Alle", "*.*")]
        )
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(entry.content)
            messagebox.showinfo("Gespeichert", f"Datei gespeichert: {path}")
    
    def _do_sync(self):
        """Führt Marketplace-Sync durch"""
        if not self.sync or not self.sync.sync_dir:
            import tkinter.messagebox as messagebox
            messagebox.showinfo("Sync", "Kein Sync-Ordner konfiguriert. Bitte in Einstellungen setzen.")
            self._show_settings()
            return
        
        result = self.sync.sync()
        import tkinter.messagebox as messagebox
        if result['pull']['success'] and result['push']['success']:
            msg = f"Sync abgeschlossen:\n"
            msg += f"  Importiert: {result['pull'].get('imported', 0)}\n"
            msg += f"  Aktualisiert: {result['pull'].get('updated', 0)}\n"
            msg += f"  Exportiert: {result['push'].get('exported', 0)}"
            messagebox.showinfo("Sync", msg)
        else:
            messagebox.showerror("Sync-Fehler", 
                f"Pull: {result['pull'].get('error', 'OK')}\n"
                f"Push: {result['push'].get('error', 'OK')}")
    
    def _show_settings(self):
        """Marketplace-Einstellungen"""
        import tkinter as tk
        from tkinter import messagebox, filedialog
        
        win = tk.Toplevel(self.parent)
        win.title("Marketplace Einstellungen")
        win.geometry("500x300")
        
        tk.Label(win, text="Autor-Name:").grid(row=0, column=0, sticky="w", padx=8, pady=8)
        author_entry = tk.Entry(win, width=40)
        author_entry.grid(row=0, column=1, padx=8, pady=8)
        author_entry.insert(0, self._get_current_user())
        
        tk.Label(win, text="Autor-ID:").grid(row=1, column=0, sticky="w", padx=8, pady=8)
        author_id_entry = tk.Entry(win, width=40)
        author_id_entry.grid(row=1, column=1, padx=8, pady=8)
        author_id_entry.insert(0, self._get_user_id())
        author_id_entry.config(state="readonly")
        
        tk.Label(win, text="Sync-Ordner (NAS/iCloud/OneDrive):").grid(row=2, column=0, sticky="nw", padx=8, pady=8)
        sync_frame = tk.Frame(win)
        sync_frame.grid(row=2, column=1, padx=8, pady=8, sticky="ew")
        sync_path_entry = tk.Entry(sync_frame, width=30)
        sync_path_entry.pack(side="left", fill="x", expand=True)
        if self.sync and self.sync.sync_dir:
            sync_path_entry.insert(0, str(self.sync.sync_dir))
        
        def browse_sync():
            path = filedialog.askdirectory(title="Sync-Ordner wählen")
            if path:
                sync_path_entry.delete(0, "end")
                sync_path_entry.insert(0, path)
        
        tk.Button(sync_frame, text="Durchsuchen", command=browse_sync).pack(side="left", padx=4)
        
        def save_settings():
            # Autor speichern
            # Sync-Ordner setzen
            if self.sync:
                sync_path = sync_path_entry.get().strip()
                if sync_path:
                    self.sync.set_sync_dir(sync_path)
            messagebox.showinfo("Gespeichert", "Einstellungen gespeichert.")
            win.destroy()
        
        tk.Button(win, text="Speichern", command=save_settings, 
                  bg="darkgreen", fg="white").grid(row=3, column=1, sticky="e", padx=8, pady=16)
    
    def _get_current_user(self) -> str:
        """Holt aktuellen User aus Profil"""
        try:
            from devispro.stammdaten import load_profile
            profile = load_profile() or {}
            return profile.get("betrieb", "Anonym")
        except:
            return "Anonym"
    
    def _get_user_id(self) -> str:
        """Generiert User-ID"""
        import hashlib
        user = self._get_current_user()
        return hashlib.sha256(user.encode()).hexdigest()[:12]


# Demo / Test
if __name__ == "__main__":
    # Store initialisieren
    store = MarketplaceStore("test_marketplace")
    
    # Beispiel-Einträge erstellen
    entries = [
        MarketplaceEntry(
            id="",
            title="Beton C25/30 Preisberechnung",
            description="Berechnet Betonpreis basierend auf Kanton und Menge",
            category=MarketplaceCategory.PREISBERECHNUNG.value,
            author="DevisPro Team",
            author_id="team001",
            content="Berechne den Preis für Beton C25/30 in Kanton {kanton} für {menge} m3. Berücksichtige Zuschläge für Pumpe, Zusatzmittel und Entsorgung.",
            content_type="prompt",
            tags=["beton", "preis", "kanton", "c25"],
            status=EntryStatus.PUBLISHED.value
        ),
        MarketplaceEntry(
            id="",
            title="Mauerwerk KS-Preisanalyse",
            description="Analysiert Kalksandstein-Preise aus NPK/BKS/CRB",
            category=MarketplaceCategory.ANALYSE.value,
            author="Max Mustermann",
            author_id="user123",
            content="import pandas as pd\nimport numpy as np\n\ndef analyse_ks_preise(katalog='NPK', jahr=2024):\n    \"\"\"Analysiert KS-Preise über alle Kataloge\"\"\"\n    # Lade Katalogdaten\n    # Vergleiche Preise pro m2\n    # Erkenne Ausreisser\n    pass",
            content_type="python",
            tags=["mauerwerk", "kalksandstein", "analyse", "npk", "bks"],
            status=EntryStatus.PUBLISHED.value
        ),
        MarketplaceEntry(
            id="",
            title="SIA-451 Export Konfiguration",
            description="Standard-Export-Config für SIA-451 Roundtrip",
            category=MarketplaceCategory.EXPORT.value,
            author="DevisPro Team",
            author_id="team001",
            content='{\n  "format": "sia451",\n  "version": "1.0",\n  "include_positions": true,\n  "include_kennwerte": true,\n  "kanton_mapping": {\n    "ZH": "260",\n    "BE": "261",\n    "AG": "262"\n  },\n  "rundung": 2\n}',
            content_type="json",
            tags=["sia451", "export", "config", "roundtrip"],
            status=EntryStatus.PUBLISHED.value
        )
    ]
    
    for entry in entries:
        store.add(entry)
    
    print(f"Marketplace initialisiert mit {len(store.entries)} Einträgen")
    print(f"Kategorien: {store.get_categories()}")
    
    # Suche testen
    results = store.search("Beton")
    print(f"\nSuche 'Beton': {len(results)} Treffer")
    for r in results:
        print(f"  {r.title} ({r.category}) - {r.rating}⭐")
#!/usr/bin/env python3
"""
Offline-First Cloud Sync für DevisPro
Unterstützt: iCloud Drive, NAS (SMB/AFP), OneDrive, Google Drive, Dropbox, lokales Verzeichnis
Basiert auf dem bestehenden team_sync.py (CRDT, Locks, Presence)
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
import os
import json
import hashlib
import threading
import time
import shutil
import platform

# watchdog optional
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    Observer = None
    class FileSystemEventHandler:
        pass
    WATCHDOG_AVAILABLE = False


class SyncProvider(Enum):
    """Unterstützte Sync-Provider"""
    ICLOUD = "iCloud Drive"
    ONEDRIVE = "OneDrive"
    GOOGLE_DRIVE = "Google Drive"
    DROPBOX = "Dropbox"
    NAS_SMB = "NAS (SMB/CIFS)"
    NAS_AFP = "NAS (AFP)"
    LOCAL = "Lokales Verzeichnis"
    CUSTOM = "Benutzerdefiniert"


class SyncStatus(Enum):
    IDLE = "Bereit"
    SYNCING = "Synchronisiere..."
    CONFLICT = "Konflikt"
    ERROR = "Fehler"
    OFFLINE = "Offline"


@dataclass
class SyncConfig:
    """Konfiguration für einen Sync-Provider"""
    provider: str
    name: str
    local_path: str
    remote_path: str
    enabled: bool = True
    auto_sync: bool = True
    interval_minutes: int = 15
    conflict_strategy: str = "newer_wins"  # newer_wins, local_wins, remote_wins, manual
    ignore_patterns: List[str] = field(default_factory=lambda: [
        "*.tmp", "*.temp", "*.lock", ".DS_Store", "Thumbs.db", 
        "__pycache__", "*.pyc", ".git", ".svn", "*.log"
    ])
    max_file_size_mb: int = 100
    metadata: Dict = field(default_factory=dict)


@dataclass
class SyncFile:
    """Metadaten einer synchronisierten Datei"""
    relative_path: str
    local_hash: str
    remote_hash: str
    local_mtime: float
    remote_mtime: float
    size: int
    last_synced: str
    conflict: bool = False


class CloudSyncProvider:
    """Basis-Klasse für Cloud-Sync-Provider"""
    
    def __init__(self, config: SyncConfig):
        self.config = config
        self.local_root = Path(config.local_path).expanduser().resolve()
        self.remote_root = Path(config.remote_path).expanduser().resolve()
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        self.local_root.mkdir(parents=True, exist_ok=True)
        self.remote_root.mkdir(parents=True, exist_ok=True)
    
    def is_available(self) -> bool:
        """Prüft ob Remote verfügbar ist"""
        return self.remote_root.exists()
    
    def list_remote(self) -> Dict[str, Dict]:
        """Listet alle Dateien im Remote mit Metadaten"""
        files = {}
        if not self.is_available():
            return files
        
        for file_path in self.remote_root.rglob("*"):
            if file_path.is_file():
                if self._should_ignore(file_path):
                    continue
                rel_path = file_path.relative_to(self.remote_root)
                stat = file_path.stat()
                files[str(rel_path)] = {
                    'hash': self._file_hash(file_path),
                    'mtime': stat.st_mtime,
                    'size': stat.st_size
                }
        return files
    
    def list_local(self) -> Dict[str, Dict]:
        """Listet alle lokalen Dateien mit Metadaten"""
        files = {}
        for file_path in self.local_root.rglob("*"):
            if file_path.is_file():
                if self._should_ignore(file_path):
                    continue
            rel_path = file_path.relative_to(self.local_root)
            stat = file_path.stat()
            files[str(rel_path)] = {
                'hash': self._file_hash(file_path),
                'mtime': stat.st_mtime,
                'size': stat.st_size
            }
        return files
    
    def _should_ignore(self, file_path: Path) -> bool:
        import fnmatch
        name = file_path.name
        for pattern in self.config.ignore_patterns:
            if fnmatch.fnmatch(name, pattern):
                return True
        return False
    
    def _file_hash(self, file_path: Path) -> str:
        """Berechnet SHA256 Hash einer Datei"""
        if file_path.stat().st_size > self.config.max_file_size_mb * 1024 * 1024:
            return f"large:{file_path.stat().st_size}"
        hasher = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
        except Exception:
            return "error"
        return hasher.hexdigest()
    
    def pull(self, files: List[str]) -> Dict[str, bool]:
        """Lädt Dateien von Remote nach Local"""
        results = {}
        for rel_path in files:
            try:
                src = self.remote_root / rel_path
                dst = self.local_root / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                results[rel_path] = True
            except Exception:
                results[rel_path] = False
        return results
    
    def push(self, files: List[str]) -> Dict[str, bool]:
        """Lädt Dateien von Local nach Remote"""
        results = {}
        for rel_path in files:
            try:
                src = self.local_root / rel_path
                dst = self.remote_root / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                results[rel_path] = True
            except Exception:
                results[rel_path] = False
        return results
    
    def delete_remote(self, files: List[str]) -> Dict[str, bool]:
        """Löscht Dateien auf Remote"""
        results = {}
        for rel_path in files:
            try:
                (self.remote_root / rel_path).unlink(missing_ok=True)
                results[rel_path] = True
            except Exception:
                results[rel_path] = False
        return results
    
    def delete_local(self, files: List[str]) -> Dict[str, bool]:
        """Löscht Dateien lokal"""
        results = {}
        for rel_path in files:
            try:
                (self.local_root / rel_path).unlink(missing_ok=True)
                results[rel_path] = True
            except Exception:
                results[rel_path] = False
        return results


class iCloudProvider(CloudSyncProvider):
    """iCloud Drive Provider (macOS)"""
    
    def __init__(self, config: SyncConfig):
        # iCloud Pfad auf macOS
        icloud_base = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs"
        if not config.remote_path:
            config.remote_path = str(icloud_base / "DevisPro")
        super().__init__(config)
    
    def is_available(self) -> bool:
        if platform.system() != "Darwin":
            return False
        return super().is_available()


class OneDriveProvider(CloudSyncProvider):
    """OneDrive Provider"""
    
    def __init__(self, config: SyncConfig):
        # OneDrive Pfad Erkennung
        if not config.remote_path:
            # Typische OneDrive Pfade
            candidates = [
                Path.home() / "OneDrive",
                Path.home() / "OneDrive - Personal",
                Path.home() / "OneDrive - Business",
            ]
            for c in candidates:
                if c.exists():
                    config.remote_path = str(c / "DevisPro")
                    break
        super().__init__(config)


class GoogleDriveProvider(CloudSyncProvider):
    """Google Drive Provider (via File Stream / Drive for Desktop)"""
    
    def __init__(self, config: SyncConfig):
        if not config.remote_path:
            candidates = [
                Path.home() / "Google Drive",
                Path.home() / "Drive",
            ]
            for c in candidates:
                if c.exists():
                    config.remote_path = str(c / "DevisPro")
                    break
        super().__init__(config)


class DropboxProvider(CloudSyncProvider):
    """Dropbox Provider"""
    
    def __init__(self, config: SyncConfig):
        if not config.remote_path:
            candidates = [
                Path.home() / "Dropbox",
            ]
            for c in candidates:
                if c.exists():
                    config.remote_path = str(c / "DevisPro")
                    break
        super().__init__(config)


class NASProvider(CloudSyncProvider):
    """NAS Provider (SMB/CIFS oder AFP mount)"""
    
    def __init__(self, config: SyncConfig):
        # Erwartet gemountetes Volume
        super().__init__(config)
    
    def is_available(self) -> bool:
        # Prüft ob Mount-Point erreichbar
        return self.remote_root.exists() and os.access(self.remote_root, os.R_OK | os.W_OK)


class CloudSyncManager:
    """Zentrale Sync-Verwaltung"""
    
    def __init__(self, config_dir: str = "cloud_sync"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.providers: Dict[str, CloudSyncProvider] = {}
        self.configs: Dict[str, SyncConfig] = {}
        self.status = SyncStatus.IDLE
        self.last_sync: Dict[str, datetime] = {}
        self.sync_state_file = self.config_dir / "sync_state.json"
        self._load_configs()
        self._running = False
        self._thread = None
        self._callbacks: List[Callable] = []
    
    def _load_configs(self):
        config_file = self.config_dir / "configs.json"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for name, cfg_data in data.get('configs', {}).items():
                    config = SyncConfig(**cfg_data)
                    self.configs[name] = config
                    self._create_provider(name, config)
    
    def _save_configs(self):
        config_file = self.config_dir / "configs.json"
        # Konvertiere Enums zu Strings für JSON-Serialisierung
        def _serialize(cfg):
            d = asdict(cfg)
            if isinstance(d.get('provider'), SyncProvider):
                d['provider'] = d['provider'].value
            if isinstance(d.get('conflict_strategy'), str):
                pass  # bereits str
            return d
        data = {
            'configs': {name: _serialize(cfg) for name, cfg in self.configs.items()}
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _create_provider(self, name: str, config: SyncConfig):
        provider_map = {
            SyncProvider.ICLOUD.value: iCloudProvider,
            SyncProvider.ONEDRIVE.value: OneDriveProvider,
            SyncProvider.GOOGLE_DRIVE.value: GoogleDriveProvider,
            SyncProvider.DROPBOX.value: DropboxProvider,
            SyncProvider.NAS_SMB.value: NASProvider,
            SyncProvider.NAS_AFP.value: NASProvider,
            SyncProvider.LOCAL.value: CloudSyncProvider,
            SyncProvider.CUSTOM.value: CloudSyncProvider,
        }
        provider_class = provider_map.get(config.provider, CloudSyncProvider)
        self.providers[name] = provider_class(config)
    
    def add_provider(self, name: str, config: SyncConfig):
        self.configs[name] = config
        self._create_provider(name, config)
        self._save_configs()
    
    def remove_provider(self, name: str):
        if name in self.providers:
            del self.providers[name]
        if name in self.configs:
            del self.configs[name]
        self._save_configs()
    
    def get_available_providers(self) -> List[str]:
        """Gibt Liste der verfügbaren (erreichbaren) Provider"""
        return [name for name, provider in self.providers.items() 
                if provider.is_available()]

    def show_gui(self):
        """Zeigt Cloud Sync GUI"""
        import tkinter as tk
        from tkinter import ttk, messagebox, filedialog, scrolledtext
        
        win = tk.Toplevel()
        win.title("Cloud Sync")
        win.geometry("800x600")
        
        # Toolbar
        toolbar = tk.Frame(win)
        toolbar.pack(fill="x", padx=8, pady=8)
        
        tk.Button(toolbar, text="Alle synchronisieren", command=self._sync_all_gui, 
                  bg="darkgreen", fg="white").pack(side="left", padx=4)
        tk.Button(toolbar, text="Provider hinzufügen", command=self._add_provider_gui, 
                  bg="darkblue", fg="white").pack(side="left", padx=4)
        tk.Button(toolbar, text="Auto-Sync starten", command=self._toggle_auto_sync, 
                  bg="darkorange", fg="white").pack(side="left", padx=4)
        tk.Button(toolbar, text="Provider verwalten", command=self._manage_providers_gui, 
                  bg="gray").pack(side="left", padx=4)
        
        # Status
        status_frame = tk.Frame(win)
        status_frame.pack(fill="x", padx=8, pady=8)
        self._status_label = tk.Label(status_frame, text="Status: Bereit", anchor="w")
        self._status_label.pack(side="left", fill="x", expand=True)
        
        # Provider Treeview
        cols = ("name", "provider", "available", "enabled", "auto_sync", "last_sync", "local", "remote")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=15)
        tree.heading("name", text="Name")
        tree.heading("provider", text="Provider")
        tree.heading("available", text="Verfügbar")
        tree.heading("enabled", text="Aktiv")
        tree.heading("auto_sync", text="Auto")
        tree.heading("last_sync", text="Letzter Sync")
        tree.heading("local", text="Lokaler Pfad")
        tree.heading("remote", text="Remote Pfad")
        tree.column("name", width=150)
        tree.column("provider", width=120)
        tree.column("available", width=70, anchor="center")
        tree.column("enabled", width=60, anchor="center")
        tree.column("auto_sync", width=50, anchor="center")
        tree.column("last_sync", width=150)
        tree.column("local", width=200)
        tree.column("remote", width=200)
        tree.pack(fill="both", expand=True, padx=8, pady=8)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=8)
        tree.configure(yscrollcommand=scrollbar.set)
        
        def refresh_tree():
            tree.delete(*tree.get_children())
            for name, config in self.configs.items():
                provider = self.providers.get(name)
                available = provider.is_available() if provider else False
                last_sync = self.last_sync.get(name)
                last_sync_str = last_sync.strftime("%d.%m.%Y %H:%M") if last_sync else "Nie"
                tree.insert("", "end", values=(
                    name,
                    config.provider,
                    "✓" if available else "✗",
                    "✓" if config.enabled else "✗",
                    "✓" if config.auto_sync else "✗",
                    last_sync_str,
                    config.local_path,
                    config.remote_path
                ), tags=(name,))
        
        def on_double_click(event):
            selection = tree.selection()
            if selection:
                name = tree.item(selection[0])['tags'][0]
                self._edit_provider_gui(name)
        
        def sync_selected():
            selection = tree.selection()
            if selection:
                name = tree.item(selection[0])['tags'][0]
                self._sync_provider_gui(name)
        
        # Buttons unter Treeview
        btn_frame = tk.Frame(win)
        btn_frame.pack(fill="x", padx=8, pady=8)
        tk.Button(btn_frame, text="Ausgewählten syncen", command=sync_selected, 
                  bg="darkblue", fg="white").pack(side="left", padx=4)
        tk.Button(btn_frame, text="Aktualisieren", command=refresh_tree).pack(side="left", padx=4)
        
        tree.bind("<Double-1>", on_double_click)
        
        # Initial laden
        refresh_tree()
        
        # Store tree reference for refresh
        self._gui_tree = tree
        self._gui_refresh = refresh_tree
    
    def _sync_all_gui(self):
        import tkinter as tk
        from tkinter import messagebox
        import threading
        
        def work():
            self._set_status(SyncStatus.SYNCING)
            results = self.sync_all()
            self._set_status(SyncStatus.IDLE)
            
            msg = "Sync aller Provider:\n"
            for name, result in results.items():
                if result.get('success'):
                    msg += f"  {name}: ✓ ({result.get('pulled',0)} gezogen, {result.get('pushed',0)} geschoben)\n"
                else:
                    msg += f"  {name}: ✗ ({result.get('error', 'Fehler')})\n"
            
            def show_result():
                messagebox.showinfo("Sync abgeschlossen", msg)
            
            # Thread-sicher
            import tkinter as tk
            try:
                self._gui_refresh()
            except:
                pass
            # Nach kurzer Verzögerung Messagebox zeigen
            import time
            time.sleep(0.5)
            messagebox.showinfo("Sync abgeschlossen", msg)
        
        threading.Thread(target=work, daemon=True).start()
    
    def _sync_provider_gui(self, name: str):
        import tkinter as tk
        from tkinter import messagebox
        import threading
        
        def work():
            self._set_status(SyncStatus.SYNCING)
            result = self.sync_provider(name)
            self._set_status(SyncStatus.IDLE)
            
            if result.get('success'):
                msg = f"Sync {name}:\n"
                msg += f"  Gezogen: {result.get('pulled', 0)}\n"
                msg += f"  Geschoben: {result.get('pushed', 0)}\n"
                msg += f"  Gelöscht lokal: {result.get('deleted_local', 0)}\n"
                msg += f"  Gelöscht remote: {result.get('deleted_remote', 0)}\n"
                msg += f"  Konflikte: {result.get('conflicts', 0)}"
            else:
                msg = f"Fehler bei {name}: {result.get('error', 'Unbekannt')}"
            
            try:
                self._gui_refresh()
            except:
                pass
            import time
            time.sleep(0.5)
            messagebox.showinfo("Sync", msg)
        
        threading.Thread(target=work, daemon=True).start()
    
    def _edit_provider_gui(self, name: str):
        import tkinter as tk
        from tkinter import ttk, messagebox, filedialog
        
        config = self.configs.get(name)
        if not config:
            return
        
        win = tk.Toplevel()
        win.title(f"Provider bearbeiten: {name}")
        win.geometry("600x500")
        
        fields = {}
        
        tk.Label(win, text="Name:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        fields['name'] = tk.Entry(win, width=50)
        fields['name'].grid(row=0, column=1, padx=8, pady=4, sticky="ew")
        fields['name'].insert(0, name)
        fields['name'].config(state="readonly")
        
        tk.Label(win, text="Provider:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        fields['provider'] = ttk.Combobox(win, 
            values=[p.value for p in SyncProvider], width=30, state="readonly")
        fields['provider'].grid(row=1, column=1, padx=8, pady=4, sticky="w")
        fields['provider'].set(config.provider)
        
        tk.Label(win, text="Lokaler Pfad:").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        local_frame = tk.Frame(win)
        local_frame.grid(row=2, column=1, padx=8, pady=4, sticky="ew")
        fields['local_path'] = tk.Entry(local_frame, width=40)
        fields['local_path'].pack(side="left", fill="x", expand=True)
        fields['local_path'].insert(0, config.local_path)
        tk.Button(local_frame, text="...", command=lambda: self._browse_local(fields['local_path'])).pack(side="left", padx=4)
        
        tk.Label(win, text="Remote Pfad:").grid(row=3, column=0, sticky="w", padx=8, pady=4)
        remote_frame = tk.Frame(win)
        remote_frame.grid(row=3, column=1, padx=8, pady=4, sticky="ew")
        fields['remote_path'] = tk.Entry(remote_frame, width=40)
        fields['remote_path'].pack(side="left", fill="x", expand=True)
        fields['remote_path'].insert(0, config.remote_path)
        tk.Button(remote_frame, text="...", command=lambda: self._browse_remote(fields['remote_path'])).pack(side="left", padx=4)
        
        tk.Label(win, text="Aktiv:").grid(row=4, column=0, sticky="w", padx=8, pady=4)
        fields['enabled'] = tk.BooleanVar(value=config.enabled)
        tk.Checkbutton(win, variable=fields['enabled']).grid(row=4, column=1, sticky="w", padx=8)
        
        tk.Label(win, text="Auto-Sync:").grid(row=5, column=0, sticky="w", padx=8, pady=4)
        fields['auto_sync'] = tk.BooleanVar(value=config.auto_sync)
        tk.Checkbutton(win, variable=fields['auto_sync']).grid(row=5, column=1, sticky="w", padx=8)
        
        tk.Label(win, text="Intervall (Minuten):").grid(row=6, column=0, sticky="w", padx=8, pady=4)
        fields['interval'] = tk.Entry(win, width=10)
        fields['interval'].grid(row=6, column=1, sticky="w", padx=8)
        fields['interval'].insert(0, str(config.interval_minutes))
        
        tk.Label(win, text="Konflikt-Strategie:").grid(row=7, column=0, sticky="w", padx=8, pady=4)
        fields['conflict'] = ttk.Combobox(win, 
            values=["newer_wins", "local_wins", "remote_wins", "manual"], 
            width=15, state="readonly")
        fields['conflict'].grid(row=7, column=1, sticky="w", padx=8)
        fields['conflict'].set(config.conflict_strategy)
        
        tk.Label(win, text="Max. Dateigröße (MB):").grid(row=8, column=0, sticky="w", padx=8, pady=4)
        fields['max_size'] = tk.Entry(win, width=10)
        fields['max_size'].grid(row=8, column=1, sticky="w", padx=8)
        fields['max_size'].insert(0, str(config.max_file_size_mb))
        
        win.columnconfigure(1, weight=1)
        
        def save():
            config.provider = fields['provider'].get()
            config.local_path = fields['local_path'].get()
            config.remote_path = fields['remote_path'].get()
            config.enabled = fields['enabled'].get()
            config.auto_sync = fields['auto_sync'].get()
            config.interval_minutes = int(fields['interval'].get() or 15)
            config.conflict_strategy = fields['conflict'].get()
            config.max_file_size_mb = int(fields['max_size'].get() or 100)
            
            # Provider neu erstellen
            from .cloud_sync import CloudSyncManager, SyncConfig, SyncProvider
            # Provider neu erstellen in self.providers
            self._create_provider(name, config)
            self._save_configs()
            
            # Tree aktualisieren
            try:
                self._gui_refresh()
            except:
                pass
            
            from tkinter import messagebox
            messagebox.showinfo("Gespeichert", "Provider-Konfiguration gespeichert.")
            win.destroy()
        
        btn_frame = tk.Frame(win)
        btn_frame.grid(row=9, column=0, columnspan=2, pady=16)
        tk.Button(btn_frame, text="Speichern", command=save, 
                  bg="darkblue", fg="white").pack(side="left", padx=8)
        tk.Button(btn_frame, text="Löschen", command=lambda: self._delete_provider_gui(name, win), 
                  bg="darkred", fg="white").pack(side="left", padx=8)
    
    def _delete_provider_gui(self, name: str, parent_win):
        import tkinter as tk
        from tkinter import messagebox
        if messagebox.askyesno("Löschen", f"Provider '{name}' wirklich löschen?"):
            self.remove_provider(name)
            try:
                self._gui_refresh()
            except:
                pass
            parent_win.destroy()
            messagebox.showinfo("Gelöscht", "Provider gelöscht.")
    
    def _browse_local(self, entry_widget):
        import tkinter as tk
        from tkinter import filedialog
        path = filedialog.askdirectory(title="Lokalen Pfad wählen")
        if path:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, path)
    
    def _browse_remote(self, entry_widget):
        import tkinter as tk
        from tkinter import filedialog
        path = filedialog.askdirectory(title="Remote Pfad wählen")
        if path:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, path)
    
    def _add_provider_gui(self):
        import tkinter as tk
        from tkinter import ttk, messagebox, filedialog
        
        win = tk.Toplevel()
        win.title("Neuen Cloud-Provider hinzufügen")
        win.geometry("600x500")
        
        # Auto-discovered Provider anzeigen
        tk.Label(win, text="Gefundene Cloud-Dienste:").pack(anchor="w", padx=8, pady=8)
        
        discovered = discover_cloud_providers()
        for i, cfg in enumerate(discovered):
            frame = tk.Frame(win, relief="ridge", bd=1)
            frame.pack(fill="x", padx=8, pady=4)
            tk.Label(frame, text=f"{cfg.name} ({cfg.provider})").pack(side="left", padx=8)
            tk.Label(frame, text=f"→ {cfg.remote_path}").pack(side="left", padx=8)
            tk.Button(frame, text="Hinzufügen", 
                     command=lambda c=cfg: self._add_discovered_provider(c, win),
                     bg="darkgreen", fg="white").pack(side="right", padx=8)
        
        if not discovered:
            tk.Label(win, text="Keine Cloud-Dienste automatisch gefunden.", fg="gray").pack(padx=8, pady=8)
        
        # Manueller Eintrag
        tk.Label(win, text="--- Oder manuell ---").pack(pady=8)
        
        fields = {}
        
        tk.Label(win, text="Name:").grid(row=10, column=0, sticky="w", padx=8, pady=4)
        fields['name'] = tk.Entry(win, width=40)
        fields['name'].grid(row=10, column=1, padx=8, pady=4, sticky="ew")
        
        tk.Label(win, text="Provider:").grid(row=11, column=0, sticky="w", padx=8, pady=4)
        fields['provider'] = ttk.Combobox(win, 
            values=[p.value for p in SyncProvider], width=30, state="readonly")
        fields['provider'].grid(row=11, column=1, padx=8, pady=4, sticky="w")
        
        tk.Label(win, text="Lokaler Pfad:").grid(row=12, column=0, sticky="w", padx=8, pady=4)
        local_frame = tk.Frame(win)
        local_frame.grid(row=12, column=1, padx=8, pady=4, sticky="ew")
        fields['local_path'] = tk.Entry(local_frame, width=30)
        fields['local_path'].pack(side="left", fill="x", expand=True)
        fields['local_path'].insert(0, str(Path.home() / "DevisPro_Sync"))
        tk.Button(local_frame, text="...", command=lambda: self._browse_local(fields['local_path'])).pack(side="left", padx=4)
        
        tk.Label(win, text="Remote Pfad:").grid(row=13, column=0, sticky="w", padx=8, pady=4)
        remote_frame = tk.Frame(win)
        remote_frame.grid(row=13, column=1, padx=8, pady=4, sticky="ew")
        fields['remote_path'] = tk.Entry(remote_frame, width=30)
        fields['remote_path'].pack(side="left", fill="x", expand=True)
        tk.Button(remote_frame, text="...", command=lambda: self._browse_remote(fields['remote_path'])).pack(side="left", padx=4)
        
        win.columnconfigure(1, weight=1)
        
        def save():
            name = fields['name'].get().strip()
            if not name:
                messagebox.showerror("Fehler", "Name ist erforderlich.")
                return
            
            config = SyncConfig(
                provider=fields['provider'].get(),
                name=name,
                local_path=fields['local_path'].get(),
                remote_path=fields['remote_path'].get(),
                enabled=True,
                auto_sync=True,
                interval_minutes=15
            )
            self.add_provider(name, config)
            messagebox.showinfo("Hinzugefügt", f"Provider '{name}' hinzugefügt.")
            try:
                self._gui_refresh()
            except:
                pass
            win.destroy()
        
        tk.Button(win, text="Hinzufügen", command=save, 
                  bg="darkgreen", fg="white").pack(pady=16)
    
    def _add_discovered_provider(self, config: SyncConfig, parent_win):
        self.add_provider(config.name, config)
        parent_win.destroy()
        try:
            self._gui_refresh()
        except:
            pass
        import tkinter.messagebox as messagebox
        messagebox.showinfo("Hinzugefügt", f"Provider '{config.name}' hinzugefügt.")
    
    def _manage_providers_gui(self):
        import tkinter as tk
        from tkinter import messagebox
        win = tk.Toplevel()
        win.title("Provider verwalten")
        win.geometry("400x300")
        
        for name in self.configs:
            frame = tk.Frame(win)
            frame.pack(fill="x", padx=8, pady=4)
            config = self.configs[name]
            provider = self.providers.get(name)
            available = provider.is_available() if provider else False
            status = "✓" if available else "✗"
            tk.Label(frame, text=f"{name} ({config.provider}) {status}").pack(side="left", padx=8)
            tk.Button(frame, text="Testen", 
                     command=lambda n=name: self._test_provider_gui(n)).pack(side="right", padx=4)
        
        if not self.configs:
            tk.Label(win, text="Keine Provider konfiguriert.", fg="gray").pack(pady=20)
    
    def _test_provider_gui(self, name: str):
        import tkinter as tk
        from tkinter import messagebox
        provider = self.providers.get(name)
        if provider:
            available = provider.is_available()
            if available:
                # Test: Dateien listen
                try:
                    files = provider.list_remote()
                    messagebox.showinfo("Test", f"Provider '{name}' erreichbar.\n{len(files)} Dateien auf Remote.")
                except Exception as e:
                    messagebox.showerror("Test", f"Provider '{name}' Fehler: {e}")
            else:
                messagebox.showwarning("Test", f"Provider '{name}' nicht erreichbar.")
        else:
            messagebox.showerror("Test", f"Provider '{name}' nicht gefunden.")
    
    def _toggle_auto_sync(self):
        import tkinter as tk
        from tkinter import messagebox
        # TODO: Auto-Sync Toggle implementieren
        messagebox.showinfo("Info", "Auto-Sync Toggle: Noch nicht implementiert.\nAktiviert in Provider-Einstellungen.")
    
    def _browse_local(self, entry_widget):
        import tkinter as tk
        from tkinter import filedialog
        path = filedialog.askdirectory(title="Lokalen Pfad wählen")
        if path:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, path)
    
    def _browse_remote(self, entry_widget):
        import tkinter as tk
        from tkinter import filedialog
        path = filedialog.askdirectory(title="Remote Pfad wählen")
        if path:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, path)
    
    def sync_provider(self, name: str) -> Dict:
        """Synchronisiert einen Provider"""
        if name not in self.providers:
            return {'success': False, 'error': 'Provider nicht gefunden'}
        
        provider = self.providers[name]
        if not provider.is_available():
            return {'success': False, 'error': 'Remote nicht erreichbar'}
        
        self._set_status(SyncStatus.SYNCING)
        try:
            local_files = provider.list_local()
            remote_files = provider.list_remote()
            
            # Sync-Plan erstellen
            plan = self._create_sync_plan(local_files, remote_files, provider.config.conflict_strategy)
            
            # Ausführen
            results = {
                'pulled': 0,
                'pushed': 0,
                'deleted_local': 0,
                'deleted_remote': 0,
                'conflicts': 0,
                'errors': []
            }
            
            # Pull (Remote -> Local)
            if plan['pull']:
                pull_results = provider.pull(plan['pull'])
                results['pulled'] = sum(1 for v in pull_results.values() if v)
                results['errors'].extend([f"Pull {k}: {v}" for k, v in pull_results.items() if not v])
            
            # Push (Local -> Remote)
            if plan['push']:
                push_results = provider.push(plan['push'])
                results['pushed'] = sum(1 for v in push_results.values() if v)
                results['errors'].extend([f"Push {k}: {v}" for k, v in push_results.items() if not v])
            
            # Delete Local
            if plan['delete_local']:
                del_results = provider.delete_local(plan['delete_local'])
                results['deleted_local'] = sum(1 for v in del_results.values() if v)
            
            # Delete Remote
            if plan['delete_remote']:
                del_results = provider.delete_remote(plan['delete_remote'])
                results['deleted_remote'] = sum(1 for v in del_results.values() if v)
            
            results['conflicts'] = len(plan['conflicts'])
            self.last_sync[name] = datetime.now()
            self._save_sync_state()
            self._set_status(SyncStatus.IDLE)
            self._notify_callbacks(name, results)
            
            return {'success': True, **results}
            
        except Exception as e:
            self._set_status(SyncStatus.ERROR)
            return {'success': False, 'error': str(e)}
    
    def _create_sync_plan(self, local: Dict, remote: Dict, strategy: str) -> Dict:
        """Erstellt Sync-Plan basierend auf Strategie"""
        all_paths = set(local.keys()) | set(remote.keys())
        
        pull = []      # Remote -> Local
        push = []      # Local -> Remote
        delete_local = []
        delete_remote = []
        conflicts = []
        
        for path in all_paths:
            local_info = local.get(path)
            remote_info = remote.get(path)
            
            if local_info and not remote_info:
                # Nur lokal -> Push
                push.append(path)
            elif remote_info and not local_info:
                # Nur remote -> Pull
                pull.append(path)
            elif local_info and remote_info:
                # Beide vorhanden
                if local_info['hash'] == remote_info['hash']:
                    continue  # Identisch
                
                # Konflikt
                if strategy == "newer_wins":
                    if local_info['mtime'] > remote_info['mtime']:
                        push.append(path)
                    else:
                        pull.append(path)
                elif strategy == "local_wins":
                    push.append(path)
                elif strategy == "remote_wins":
                    pull.append(path)
                else:  # manual
                    conflicts.append(path)
        
        return {
            'pull': pull,
            'push': push,
            'delete_local': delete_local,
            'delete_remote': delete_remote,
            'conflicts': conflicts
        }
    
    def sync_all(self) -> Dict:
        """Synchronisiert alle aktivierten Provider"""
        results = {}
        for name, config in self.configs.items():
            if config.enabled and config.auto_sync:
                results[name] = self.sync_provider(name)
        return results
    
    def _set_status(self, status: SyncStatus):
        self.status = status
        self._notify_callbacks('status', status.value)
    
    def _notify_callbacks(self, event: str, data: Any):
        for cb in self._callbacks:
            try:
                cb(event, data)
            except Exception:
                pass
    
    def register_callback(self, callback: Callable):
        self._callbacks.append(callback)
    
    def _save_sync_state(self):
        state = {
            'last_sync': {k: v.isoformat() for k, v in self.last_sync.items()}
        }
        with open(self.sync_state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    
    def _load_sync_state(self):
        if self.sync_state_file.exists():
            with open(self.sync_state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for k, v in data.get('last_sync', {}).items():
                    self.last_sync[k] = datetime.fromisoformat(v)
    
    def start_auto_sync(self):
        """Startet automatische Synchronisation"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._auto_sync_loop, daemon=True)
        self._thread.start()
    
    def stop_auto_sync(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def _auto_sync_loop(self):
        while self._running:
            try:
                self.sync_all()
            except Exception:
                pass
            # Schlaf mit kürzeren Intervallen für Responsiveness
            for _ in range(60):  # 60 Sekunden = 1 Minute Checks
                if not self._running:
                    break
                time.sleep(1)
            # Dann warten bis nächstes Intervall
            time.sleep(59 * 60)  # Restliche 59 Minuten


class FileWatcher(FileSystemEventHandler):
    """Datei-Überwachung für sofortigen Sync"""
    
    def __init__(self, sync_manager: CloudSyncManager, provider_name: str, debounce_seconds: float = 2.0):
        self.sync_manager = sync_manager
        self.provider_name = provider_name
        self.debounce_seconds = debounce_seconds
        self._last_event = {}
        self._timer = None
    
    def on_modified(self, event):
        if event.is_directory:
            return
        self._debounce_sync(event.src_path)
    
    def on_created(self, event):
        if event.is_directory:
            return
        self._debounce_sync(event.src_path)
    
    def on_deleted(self, event):
        if event.is_directory:
            return
        self._debounce_sync(event.src_path)
    
    def _debounce_sync(self, file_path: str):
        now = time.time()
        self._last_event[file_path] = now
        
        if self._timer:
            self._timer.cancel()
        
        self._timer = threading.Timer(self.debounce_seconds, self._do_sync)
        self._timer.start()
    
    def _do_sync(self):
        # Sammle alle Events innerhalb Debounce-Zeit
        now = time.time()
        recent_files = [
            f for f, t in self._last_event.items() 
            if now - t <= self.debounce_seconds
        ]
        if recent_files:
            self.sync_manager.sync_provider(self.provider_name)


# Auto-Discovery für bekannte Cloud-Ordner
def discover_cloud_providers() -> List[SyncConfig]:
    """Erkennt automatisch konfigurierte Cloud-Ordner"""
    home = Path.home()
    discovered = []
    
    # iCloud
    icloud = home / "Library" / "Mobile Documents" / "com~apple~CloudDocs"
    if icloud.exists():
        discovered.append(SyncConfig(
            provider=SyncProvider.ICLOUD.value,
            name="iCloud Drive",
            local_path=str(Path.home() / "DevisPro_Sync"),
            remote_path=str(icloud / "DevisPro"),
            enabled=True
        ))
    
    # OneDrive
    for od_name in ["OneDrive", "OneDrive - Personal", "OneDrive - Business"]:
        od_path = home / od_name
        if od_path.exists():
            discovered.append(SyncConfig(
                provider=SyncProvider.ONEDRIVE.value,
                name=f"OneDrive ({od_name})",
                local_path=str(Path.home() / "DevisPro_Sync"),
                remote_path=str(od_path / "DevisPro"),
                enabled=True
            ))
    
    # Google Drive
    for gd_name in ["Google Drive", "Drive"]:
        gd_path = home / gd_name
        if gd_path.exists():
            discovered.append(SyncConfig(
                provider=SyncProvider.GOOGLE_DRIVE.value,
                name=f"Google Drive ({gd_name})",
                local_path=str(Path.home() / "DevisPro_Sync"),
                remote_path=str(gd_path / "DevisPro"),
                enabled=True
            ))
    
    # Dropbox
    db_path = home / "Dropbox"
    if db_path.exists():
        discovered.append(SyncConfig(
            provider=SyncProvider.DROPBOX.value,
            name="Dropbox",
            local_path=str(Path.home() / "DevisPro_Sync"),
            remote_path=str(db_path / "DevisPro"),
            enabled=True
        ))
    
    return discovered


# Integration in bestehende team_sync.py
class UnifiedSyncManager:
    """Vereinheitlicht Team-Sync (CRDT) + Cloud-Sync"""
    
    def __init__(self, project_dir: str, cloud_config_dir: str = "cloud_sync"):
        self.project_dir = Path(project_dir)
        self.cloud_manager = CloudSyncManager(cloud_config_dir)
        self._setup_default_provider()
    
    def _setup_default_provider(self):
        """Richtet Standard-Provider ein falls keiner existiert"""
        if not self.cloud_manager.configs:
            discovered = discover_cloud_providers()
            for config in discovered:
                self.cloud_manager.add_provider(config.name, config)
    
    def sync_project(self, provider_name: str = None) -> Dict:
        """Synct Projekt-Daten"""
        if provider_name:
            return self.cloud_manager.sync_provider(provider_name)
        return self.cloud_manager.sync_all()
    
    def get_status(self) -> Dict:
        return {
            'status': self.cloud_manager.status.value,
            'providers': {
                name: {
                    'available': provider.is_available(),
                    'enabled': config.enabled,
                    'last_sync': self.cloud_manager.last_sync.get(name)
                }
                for name, (provider, config) in zip(
                    self.cloud_manager.providers.keys(),
                    zip(self.cloud_manager.providers.values(), self.cloud_manager.configs.values())
                )
            }
        }


# Demo / Test
if __name__ == "__main__":
    # Cloud Sync Manager erstellen
    manager = CloudSyncManager("test_cloud_sync")
    
    # Auto-Discovery
    discovered = discover_cloud_providers()
    print(f"Gefundene Cloud-Provider: {len(discovered)}")
    for cfg in discovered:
        print(f"  - {cfg.name} ({cfg.provider})")
        print(f"    Local: {cfg.local_path}")
        print(f"    Remote: {cfg.remote_path}")
    
    # Provider hinzufügen
    for cfg in discovered:
        manager.add_provider(cfg.name, cfg)
    
    print(f"\nRegistrierte Provider: {list(manager.providers.keys())}")
    print(f"Verfügbar: {manager.get_available_providers()}")
    
    # Test Sync (falls verfügbar)
    for name in manager.get_available_providers():
        print(f"\nTeste Sync für {name}...")
        result = manager.sync_provider(name)
        print(f"  Ergebnis: {result}")
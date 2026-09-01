"""Persistente Stammdaten eines Betriebs (Profi-Umfang).

Einmal eingeben -> bleibt ausserhalb des Bundles gespeichert (data_store)
und wird fuer jedes neue Devis automatisch verwendet.
"""
# data_store als direkter import (kein relativer Import, vermeidet Circular)
import data_store as ds


def default_profile() -> dict:
    return {
        # --- Betrieb (LEER bei Erststart: KMU gibt eigene Daten ein;
        #     die GUI zeigt Platzhalter-Hinweise statt Muster-Namen) ---
        "betrieb": "",
        "strasse": "",
        "plz": "",
        "ort": "",
        "telefon": "",
        "email": "",
        "web": "",
        "mwst_nr": "",            # UID-Nummer CH
        # --- Gewerk / Ansaetze ---
        "gewerk": "Maler",
        "stundenlohn_chf": 82.0,        # Lohn + Lohnnebenkosten (Markt CH)
        "monteur_stundenlohn_chf": 75.0,
        "material_aufschlag_pct": 12.0,
        "gemeinkosten_pct": 10.0,
        "gewinn_pct": 8.0,
        # --- Steuern / Rabatt ---
        "mwst_pct": 8.1,          # Default-Normalsatz
        "mwst_ansaetze": {        # mehrere Saetze wie in der Offerte ueblich
            "normal": 8.1,
            "reduziert": 2.6,
            "frei": 0.0,
        },
        "rabatt_pct": 0.0,
        "kanton": "ZH",
        # --- Bank / Zahlung ---
        "bank_name": "",
        "iban": "",
        "konto_post": "",
        "zahlungsziel_tage": 30,
        # --- Logo ---
        "logo_path": "",
    }


def save_profile(profile: dict) -> None:
    ds._write_json(ds.PROFILE_PATH, profile)


def load_profile() -> dict:
    p = ds._read_json(ds.PROFILE_PATH, None)
    if p is None:
        return default_profile()
    # fehlende schluessel mit default ergaenzen (forward-compat)
    d = default_profile()
    d.update(p)
    return d


def save_prices_csv(content: str) -> None:
    with open(ds.PREISE_PATH, "w", encoding="utf-8") as f:
        f.write(content)


def load_prices_csv() -> str:
    if os_path_exists(ds.PREISE_PATH):
        with open(ds.PREISE_PATH, encoding="utf-8") as f:
            return f.read()
    return ""


def prices_exist() -> bool:
    import os
    return os.path.exists(ds.PREISE_PATH) and os.path.getsize(ds.PREISE_PATH) > 0


def save_logo(src_path: str) -> str:
    """Kopiert ein Logo in den Datenordner, gibt den Zielpfad zurueck."""
    import shutil
    os.makedirs(ds.app_support_dir(), exist_ok=True)
    dst = ds.LOGO_PATH
    shutil.copyfile(src_path, dst)
    p = load_profile()
    p["logo_path"] = dst
    save_profile(p)
    return dst


# --- Kundenstamm ----------------------------------------------------------
def load_kunden() -> list:
    return ds._read_json(ds.KUNDEN_PATH, [])


def save_kunden(liste: list) -> None:
    ds._write_json(ds.KUNDEN_PATH, liste)


# --- Verlauf --------------------------------------------------------------
def load_verlauf() -> list:
    return ds._read_json(ds.VERLAUF_PATH, [])


def save_verlauf(liste: list) -> None:
    ds._write_json(ds.VERLAUF_PATH, liste)


def os_path_exists(p):
    import os
    return os.path.exists(p)

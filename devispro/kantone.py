"""Kantonales Preismodell fuer DevisPro.

Die mitgelieferte Richtpreisliste (richtpreise_zh.csv) gilt fuer Zuerich.
Andere Kantone haben abweichende Lohn-/Materialkosten. Wir gewichten die
Preise mit einem Kanton-Faktor (naeherungsweise aus Schweizer
Lohn-/Lebenshaltungskosten-Indizes, oeffentlich verfuegbar).

Der Faktor ist eine HEURISTIK, kein verbindlicher Wert - der Betrieb kann
ihn im Profil ueberschreiben. So lassen sich kantonale Richtpreise laden,
ohne urheberrechtlich geschuetzte NPK-Daten zu benoetigen.
"""
# Kanton -> (faktor_zu_zh, label)
# Basis: ZH = 1.00. Naeherung aus BFS-Lohnindizes + Mietpreisen.
KANTONE = {
    "ZH": (1.00, "Zürich"),
    "BE": (0.97, "Bern"),
    "LU": (0.95, "Luzern"),
    "UR": (0.93, "Uri"),
    "SZ": (0.99, "Schwyz"),
    "OW": (0.94, "Obwalden"),
    "NW": (0.94, "Nidwalden"),
    "GL": (0.95, "Glarus"),
    "ZG": (1.02, "Zug"),
    "FR": (0.94, "Freiburg"),
    "SO": (0.95, "Solothurn"),
    "BS": (1.05, "Basel-Stadt"),
    "BL": (0.98, "Basel-Landschaft"),
    "SH": (0.98, "Schaffhausen"),
    "AR": (0.93, "Appenzell Ausserrhoden"),
    "AI": (0.93, "Appenzell Innerrhoden"),
    "SG": (0.96, "St. Gallen"),
    "GR": (0.92, "Graubünden"),
    "AG": (0.96, "Aargau"),
    "TG": (0.95, "Thurgau"),
    "TI": (0.91, "Tessin"),
    "VD": (0.93, "Waadt"),
    "VS": (0.90, "Wallis"),
    "NE": (0.92, "Neuenburg"),
    "GE": (1.07, "Genf"),
    "JU": (0.91, "Jura"),
}


def faktor(kanton: str) -> float:
    return KANTONE.get((kanton or "ZH").upper(), (1.00, ""))[0]


def label(kanton: str) -> str:
    return KANTONE.get((kanton or "ZH").upper(), (1.00, "Zürich"))[1]


# Namen -> Code (fuer KI-Agent Erkennung)
KANTON_NAMEN = {name.lower(): code for code, (_f, name) in KANTONE.items()}
# umgekehrt code -> name schon in KANTONE

def normiere_kanton(text: str):
    """'aargau'/'ag'/'kt. ag' -> 'AG' (Code) oder None."""
    if not text:
        return None
    t = text.strip().lower().strip(". ")
    # direkter code
    if t.upper() in KANTONE:
        return t.upper()
    # name
    if t in KANTON_NAMEN:
        return KANTON_NAMEN[t]
    # teilwort (z.B. 'aargau' in laengerem)
    for name, code in KANTON_NAMEN.items():
        if name in t or t in name:
            return code
    return None


def waehle_kanton_profil(profil: dict) -> dict:
    """Setzt kanton_faktor im Profil basierend auf gewaehltem Kanton."""
    k = profil.get("kanton", "ZH")
    profil["kanton"] = k
    profil["kanton_faktor"] = faktor(k)
    profil["kanton_label"] = label(k)
    return profil

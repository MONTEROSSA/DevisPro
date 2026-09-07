"""DevisPro ERP - voll funktionsfaehiges, lokal arbeitendes ERP (Tarif 'erp').

Konkurrenzfaehig zu Abacus/Proffix (KMU-Bau): Artikel & Lager (mit Stuecklisten),
Kunden & Lieferanten, Einkauf (Bestellung + Wareneingang + Disposition),
Verkauf (Offerte->Auftrag->Rechnung, Teilzahlungen, MWST), Buchhaltung
(Journal, Kontenrahmen KMU, Debitoren/Kreditoren, Salden, MWST-Abrechnung),
Mahnwesen (3 Stufen), Projekte, Dashboard. Kein externer Dienst, reiner Python.
"""

import os
import json
import datetime as dt
from dataclasses import dataclass, field, asdict
from typing import Optional, List

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")

MWST_SAETZE = {"normale": 8.1, "reduziert": 2.6, "sondersatz": 3.8, "frei": 0.0}
KONTO_RAHMEN = {
    "1000": "Flüssige Mittel (Bank)",
    "1200": "Debitoren (Kunden)",
    "2000": "Kreditoren (Lieferanten)",
    "2200": "Darlehen",
    "3000": "Eigenkapital",
    "3200": "Jahresgewinn",
    "4000": "Umsatzerlöse (Leistungen)",
    "4200": "Umsatzerlöse (Waren)",
    "5000": "Material/Wareneinkauf",
    "6000": "Personalaufwand",
    "7000": "Betriebsaufwand",
    "1170": "MWST geschuldet",
    "2201": "MWST abziehbar (Vorsteuer)",
}


@dataclass
class Artikel:
    nr: str
    bezeichnung: str
    einheit: str = "Stk"
    ek_preis: float = 0.0
    vk_preis: float = 0.0
    bestand: float = 0.0
    mindestbestand: float = 0.0
    lagerort: str = ""
    typ: str = "einfach"          # 'einfach' | 'stueckliste'
    stueckliste: List[dict] = field(default_factory=list)  # [{artikel_nr, menge}]

    def lagerwert(self) -> float:
        return round(self.bestand * self.ek_preis, 2)

    def soll_nachbestellt_werden(self) -> bool:
        return self.bestand <= self.mindestbestand


@dataclass
class Partner:
    nr: str
    name: str
    typ: str = "kunde"            # 'kunde' | 'lieferant'
    strasse: str = ""
    plz_ort: str = ""
    mwst_nr: str = ""
    mail: str = ""
    offen: float = 0.0
    land: str = "CH"
    kreditlimit: float = 0.0


@dataclass
class BelegPosition:
    artikel_nr: str = ""
    bezeichnung: str = ""
    menge: float = 0.0
    einheit: str = "Stk"
    ep: float = 0.0
    rabatt_pct: float = 0.0
    mwst_satz: str = "normale"
    betrag: float = 0.0

    def __post_init__(self):
        if self.betrag == 0.0 and self.ep is not None:
            netto = self.menge * self.ep * (1 - self.rabatt_pct / 100.0)
            self.betrag = round(netto, 2)


@dataclass
class Zahlung:
    datum: str
    betrag: float
    art: str = "eingang"          # 'eingang' | 'ausgang'


@dataclass
class Beleg:
    nr: str
    typ: str                     # angeb/angebot | auftrag | rechnung | gutschrift |
                                # bestellung | wareneingang | lieferschein
    partner_nr: str
    partner_name: str
    datum: str
    faellig: str = ""
    positionen: List[BelegPosition] = field(default_factory=list)
    zahlungen: List[Zahlung] = field(default_factory=list)
    bezahlt: bool = False
    projekt: str = ""
    notiz: str = ""
    status: str = ""

    def netto(self) -> float:
        return round(sum(p.betrag for p in self.positionen), 2)

    def mwst_betrag(self) -> float:
        total = 0.0
        for p in self.positionen:
            satz = MWST_SAETZE.get(p.mwst_satz, 0.0)
            total += p.betrag * satz / 100.0
        return round(total, 2)

    def brutto(self) -> float:
        return round(self.netto() + self.mwst_betrag(), 2)

    def offen(self) -> float:
        gezahlt = sum(z.betrag for z in self.zahlungen)
        return round(self.brutto() - gezahlt, 2)

    def mahnstufe(self) -> int:
        if self.bezahlt or self.offen() <= 0:
            return 0
        tage = (dt.date.today() - dt.date.fromisoformat(self.faellig or self.datum)).days
        if tage > 30:
            return 3
        if tage > 20:
            return 2
        if tage > 10:
            return 1
        return 0


@dataclass
class Buchung:
    nr: str
    datum: str
    konto: str
    gegenkonto: str
    betrag: float
    text: str
    beleg_nr: str = ""
    mwst: float = 0.0


class _Store:
    def __init__(self, name, factory):
        self.pfad = os.path.join(DATA, name)
        self.factory = factory
        self._daten = None

    def laden(self):
        if self._daten is not None:
            return self._daten
        if os.path.exists(self.pfad):
            try:
                with open(self.pfad, encoding="utf-8") as f:
                    self._daten = json.load(f)
                return self._daten
            except Exception:
                pass
        self._daten = self.factory()
        return self._daten

    def speichern(self):
        os.makedirs(DATA, exist_ok=True)
        with open(self.pfad, "w", encoding="utf-8") as f:
            json.dump(self._daten, f, indent=2, ensure_ascii=False)

    def reset(self):
        self._daten = self.factory()
        self.speichern()


_artikel = _Store("erp_artikel.json", lambda: [])
_partner = _Store("erp_partner.json", lambda: [])
_belege = _Store("erp_belege.json", lambda: [])
_buchungen = _Store("erp_buchungen.json", lambda: [])
_projekte = _Store("erp_projekte.json", lambda: [])


def _naechste_nr(prefix, liste, feld="nr"):
    z = 0
    for e in liste:
        n = str(e.get(feld) if isinstance(e, dict) else getattr(e, feld)).split("-")[-1]
        try:
            z = max(z, int(n))
        except Exception:
            pass
    return f"{prefix}-{z+1:05d}"


# --- Artikel / Lager -------------------------------------------------------
def artikel_liste() -> List[Artikel]:
    return [Artikel(**a) for a in _artikel.laden()]

def artikel_ergaenzen(nr, bez, einheit="Stk", ek=0.0, vk=0.0, bestand=0.0,
                      mindest=0.0, lagerort="", typ="einfach", stueckliste=None) -> Artikel:
    a = Artikel(nr, bez, einheit, float(ek), float(vk), float(bestand),
                float(mindest), lagerort, typ, stueckliste or [])
    _artikel.laden().append(asdict(a))
    _artikel.speichern()
    return a

def artikel_wareneingang(nr, menge, ek_preis=None, lagerort=None) -> bool:
    for a in _artikel.laden():
        if a["nr"] == nr:
            a["bestand"] = round(a["bestand"] + float(menge), 3)
            if ek_preis is not None:
                a["ek_preis"] = float(ek_preis)
            if lagerort:
                a["lagerort"] = lagerort
            _artikel.speichern()
            lager_bewegung_erfassen(nr, "wareneingang", menge)
            return True
    return False

def artikel_ausschluss(nr, menge) -> bool:
    for a in _artikel.laden():
        if a["nr"] == nr:
            a["bestand"] = round(a["bestand"] - float(menge), 3)
            _artikel.speichern()
            lager_bewegung_erfassen(nr, "ausschluss", -float(menge))
            return True
    return False

def lagerwert_gesamt() -> float:
    return round(sum(a.lagerwert() for a in artikel_liste()), 2)

def nachbestellliste() -> List[str]:
    return [a.nr for a in artikel_liste() if a.soll_nachbestellt_werden()]


# --- Partner --------------------------------------------------------------
def partner_liste(typ=None) -> List[Partner]:
    ps = [Partner(**p) for p in _partner.laden()]
    return [p for p in ps if typ is None or p.typ == typ]

def partner_ergaenzen(nr, name, typ="kunde", strasse="", plz_ort="",
                      mwst_nr="", mail="", land="CH") -> Partner:
    p = Partner(nr, name, typ, strasse, plz_ort, mwst_nr, mail, land=land)
    _partner.laden().append(asdict(p))
    _partner.speichern()
    return p


# --- Belege / Verkauf / Einkauf ------------------------------------------
def beleg_erstellen(typ, partner_nr, partner_name, positionen, faellig="",
                    projekt="", notiz="") -> Beleg:
    b = Beleg(_naechste_nr(typ[:4].upper(), _belege.laden()),
              typ, partner_nr, partner_name, dt.date.today().isoformat(),
              faellig=faellig or (dt.date.today() + dt.timedelta(days=30)).isoformat(),
              positionen=[BelegPosition(**p) for p in positionen],
              projekt=projekt, notiz=notiz)
    _belege.laden().append(asdict(b))
    _belege.speichern()
    _buchen_aus_beleg(b)
    return b

def beleg_from_dict(b: dict) -> Beleg:
    return Beleg(
        nr=b.get("nr", ""), typ=b.get("typ", ""), partner_nr=b.get("partner_nr", ""),
        partner_name=b.get("partner_name", ""), datum=b.get("datum", ""),
        faellig=b.get("faellig", ""),
        positionen=[BelegPosition(**p) for p in b.get("positionen", [])],
        zahlungen=[Zahlung(**z) for z in b.get("zahlungen", [])],
        bezahlt=b.get("bezahlt", False), projekt=b.get("projekt", ""),
        notiz=b.get("notiz", ""), status=b.get("status", ""))


def beleg_liste(typ=None) -> List[Beleg]:
    return [beleg_from_dict(b) for b in _belege.laden()
            if typ is None or b.get("typ") == typ]

def beleg_zahlung(nr, betrag, datum=None, art="eingang") -> bool:
    for b in _belege.laden():
        if b["nr"] == nr:
            b["zahlungen"].append(asdict(Zahlung(datum or dt.date.today().isoformat(),
                                                  float(betrag), art)))
            # offen direkt aus gespeicherten Feldern berechnen (keine Rekonstruktion)
            netto = round(sum(p.get("betrag", 0.0) for p in b["positionen"]), 2)
            mwst = round(sum(p.get("betrag", 0.0) * MWST_SAETZE.get(p.get("mwst_satz", "normale"), 0.0) / 100.0
                             for p in b["positionen"]), 2)
            offen = round(netto + mwst - sum(z.get("betrag", 0.0) for z in b["zahlungen"]), 2)
            if offen <= 0.001:
                b["bezahlt"] = True
            _belege.speichern()
            return True
    return False

def _buchen_aus_beleg(b: Beleg):
    if b.typ in ("rechnung", "angebot", "auftrag", "gutschrift"):
        _buchen("1200", "4000", b.netto(), f"{b.typ} {b.nr}", b.nr, b.mwst_betrag())
        _partner_saldo(b.partner_nr, b.brutto())
    elif b.typ in ("bestellung", "wareneingang"):
        _buchen("5000", "2000", b.netto(), f"{b.typ} {b.nr}", b.nr, b.mwst_betrag())
        _partner_saldo(b.partner_nr, -b.brutto())

def _buchen(konto, gegen, betrag, text, beleg_nr="", mwst=0.0):
    nr = _naechste_nr("BH", _buchungen.laden())
    _buchungen.laden().append(asdict(Buchung(nr, dt.date.today().isoformat(),
                                             konto, gegen, round(float(betrag), 2), text,
                                             beleg_nr, round(float(mwst), 2))))
    _buchungen.speichern()

def _partner_saldo(nr, delta):
    for p in _partner.laden():
        if p["nr"] == nr:
            p["offen"] = round(p["offen"] + delta, 2)
            _partner.speichern()
            return


# --- Mahnwesen ----------------------------------------------------------
def offene_posten_liste() -> List[dict]:
    out = []
    for b in beleg_liste("rechnung"):
        if b.offen() > 0.001 and not b.bezahlt:
            out.append({"nr": b.nr, "partner": b.partner_name, "faellig": b.faellig,
                        "offen": b.offen(), "stufe": b.mahnstufe()})
    return out

def mahnstufe_max() -> int:
    return max([b.mahnstufe() for b in beleg_liste("rechnung")] + [0])

def offene_posten_summe() -> float:
    return round(sum(b.offen() for b in beleg_liste("rechnung") if not b.bezahlt), 2)


# --- Buchhaltung ---------------------------------------------------------
def buchungen_liste() -> List[Buchung]:
    return [Buchung(**b) for b in _buchungen.laden()]

def kontosaldo(konto: str) -> float:
    s = 0.0
    for b in buchungen_liste():
        if b.konto == konto:
            s += b.betrag
        if b.gegenkonto == konto:
            s -= b.betrag
    return round(s, 2)

def umsatz_jahr(jahr=None) -> float:
    jahr = str(jahr or dt.date.today().year)
    return round(sum(b.betrag for b in buchungen_liste()
                      if b.datum.startswith(jahr) and b.konto == "1200" and b.betrag > 0), 2)

def mwst_abrechnung(jahr=None) -> dict:
    jahr = str(jahr or dt.date.today().year)
    geschuldet = round(sum(b.mwst for b in buchungen_liste()
                           if b.datum.startswith(jahr) and b.konto == "4000" and b.mwst > 0), 2)
    vorsteuer = round(sum(b.mwst for b in buchungen_liste()
                          if b.datum.startswith(jahr) and b.konto == "5000" and b.mwst > 0), 2)
    return {"jahr": jahr, "mwst_geschuldet": geschuldet,
            "vorsteuer": vorsteuer, "saldo_zahlbar": round(geschuldet - vorsteuer, 2)}


# --- Projekte ------------------------------------------------------------
def projekt_liste() -> list:
    return _projekte.laden()

def projekt_anlegen(nr, name, kunde_nr="", kunde_name=""):
    p = {"nr": nr, "name": name, "kunde_nr": kunde_nr, "kunde_name": kunde_name,
         "belege": []}
    _projekte.laden().append(p)
    _projekte.speichern()
    return p

def projekt_beleg_hinzufuegen(projekt_nr, beleg_nr):
    for p in _projekte.laden():
        if p["nr"] == projekt_nr and beleg_nr not in p["belege"]:
            p["belege"].append(beleg_nr)
            _projekte.speichern()
            return True
    return False


# --- Dashboard ------------------------------------------------------------
def dashboard() -> dict:
    return {
        "umsatz_jahr": umsatz_jahr(),
        "offene_posten": offene_posten_summe(),
        "lagerwert": lagerwert_gesamt(),
        "artikel": len(artikel_liste()),
        "kunden": len(partner_liste("kunde")),
        "lieferanten": len(partner_liste("lieferant")),
        "rechnungen_offen": len(offene_posten_liste()),
        "mahnstufe_max": mahnstufe_max(),
        "nachbestellung": nachbestellliste(),
        "mwst": mwst_abrechnung(),
    }

def zuruecksetzen():
    for s in (_artikel, _partner, _belege, _buchungen, _projekte, _bewegungen):
        s.reset()


# --- Lager-Bewegungshistorie ---------------------------------------------
_bewegungen = _Store("erp_bewegungen.json", lambda: [])

def lager_bewegung_erfassen(artikel_nr, typ, menge, ref="", notiz=""):
    _bewegungen.laden().append({
        "datum": dt.date.today().isoformat(),
        "artikel_nr": artikel_nr, "typ": typ,
        "menge": round(float(menge), 3), "ref": ref, "notiz": notiz,
    })
    _bewegungen.speichern()

def lager_bewegung_liste(artikel_nr=None):
    bs = _bewegungen.laden()
    if artikel_nr:
        bs = [b for b in bs if b["artikel_nr"] == artikel_nr]
    return bs

# --- Inventur / Zaehlung -------------------------------------------------
def inventur_erfassen(artikel_nr, gezaehlt, notiz=""):
    a = None
    for x in _artikel.laden():
        if x["nr"] == artikel_nr:
            a = x; break
    if a is None:
        return None
    diff = round(float(gezaehlt) - a["bestand"], 3)
    lager_bewegung_erfassen(artikel_nr, "inventur", diff, notiz="Inventur Korrektur")
    a["bestand"] = round(float(gezaehlt), 3)
    _artikel.speichern()
    return diff

# --- Kreditlimit / Debitoren-Warnung ------------------------------------
def kreditlimit_setzen(partner_nr, limit):
    for p in _partner.laden():
        if p["nr"] == partner_nr:
            p["kreditlimit"] = round(float(limit), 2)
            _partner.speichern(); return True
    return False

def kreditlimit_ueberschritten(partner_nr):
    p = next((x for x in _partner.laden() if x["nr"] == partner_nr), None)
    if not p:
        return False
    limit = p.get("kreditlimit", 0.0)
    if not limit:
        return False
    return round(p.get("offen", 0.0), 2) > limit

def debitoren_warnungen():
    return [{"nr": p["nr"], "name": p.get("name",""), "offen": round(p.get("offen",0.0),2),
             "limit": p.get("kreditlimit", 0.0)}
            for p in _partner.laden()
            if p.get("typ") == "kunde" and kreditlimit_ueberschritten(p["nr"])]

# --- Verkaufs-Statuskette: Angebot -> Auftrag -> Rechnung ---------------
def beleg_status_setzen(nr, status):
    for b in _belege.laden():
        if b["nr"] == nr:
            b["status"] = status
            _belege.speichern(); return True
    return False

def beleg_kopie_als(nr, neu_typ):
    for b in _belege.laden():
        if b["nr"] == nr:
            neu = dict(b)
            neu["nr"] = _naechste_nr(neu_typ[:4].upper(), _belege.laden())
            neu["typ"] = neu_typ
            neu["status"] = "neu"
            neu["zahlungen"] = []
            neu["bezahlt"] = False
            _belege.laden().append(neu)
            _belege.speichern()
            return neu["nr"]
    return None

# --- ERP -> Buchhaltungs-Export (13 Formate ueber accounting.py) --------
def export_buchhaltung(beleg_nr, system="csv", profil=None):
    """Exportiert einen Verkaufs-/Einkaufsbeleg ins Buchhaltungsformat.

    Nutzt devispro.accounting (Abacus, Proffix, BMD, Banana, DATEV, SAP,
    Lexoffice, SevDesk, XRechnung, generisches CSV ...).
    """
    b = next((x for x in _belege.laden() if x["nr"] == beleg_nr), None)
    if not b:
        raise ValueError("Beleg nicht gefunden: " + str(beleg_nr))
    from devispro import accounting as acc
    profil = profil or {"mwst_pct": 8.1, "betrieb": "KMU", "iban": ""}

    class _Pos:
        def __init__(self, p):
            self.text = p.get("bezeichnung", "")
            self.menge = p.get("menge", 0.0)
            self.einheit = p.get("einheit", "Stk")
            self.ep = p.get("ep", 0.0)
            self.betrag = p.get("betrag", 0.0)
            self.mwst_pct = MWST_SAETZE.get(p.get("mwst_satz", "normale"), 8.1)

    class _Dev:
        def __init__(self, b):
            self.positions = [_Pos(p) for p in b.get("positionen", [])]

    return acc.export(system_id=system, devis=_Dev(b), profil=profil,
                     beleg=beleg_nr, datum=b.get("datum", dt.date.today().isoformat()))

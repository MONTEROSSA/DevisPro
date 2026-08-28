"""Realistisches Zürcher Bauprojekt als Beispiel-Devis.

Szenario: Teil-Sanierung eines Mehrfamilienhauses in Zürich-Wiedikon
(Ausschreibung durch Architekturbüro, 29 Positionen über alle Gewerke).
pos_nr im echten SIA-451-Format: NPK ohne Punkt, 12-stellig (0-padding).
Texte <= 40 Zeichen (Fixed-Width text-Block).
"""
from .models import Devis, Position


def build_realistic_devis() -> Devis:
    meta = {
        "version": "SIA451",
        "currency": "CHF",
        "date": "20260312",
        "project_id": "WDK2026",
        "project_name": "Sanierung MFH Wiedikon ZH",
        "devis_nr": "2026-014",
    }
    addresses = [
        {"role": "Bauherrschaft", "name": "Stiftung Wohnen Zuerich", "street": "Wiedikerstrasse 123", "city": "8003 Zuerich"},
        {"role": "Planung", "name": "Architektur Blatt & Stein AG", "street": "Foerrlibuckstrasse 45", "city": "8005 Zuerich"},
    ]
    chapters = [
        ("1", "241", "Baumeisterarbeiten"),
        ("1", "242", "Maurerarbeiten"),
        ("1", "243", "Putzerarbeiten"),
        ("1", "244", "Bodenbelagsarbeiten"),
        ("1", "251", "Zimmereiarbeiten"),
        ("1", "252", "Dachdeckerarbeiten"),
        ("1", "255", "Schreinerarbeiten"),
        ("1", "261", "Elektroinstallationen"),
        ("1", "263", "Sanitaere Arbeiten"),
        ("1", "271", "Anstricharbeiten"),
    ]

    pos = [
        # 241 Baumeister
        Position("241111000000", "Abbruch unbewehrter Beton bis 20 cm", 18.5, "m3"),
        Position("241211000000", "Erstellen von Beton C25/30 Ortbeton", 96.0, "m2"),
        Position("241712000000", "Erdaushub Bodenklasse 3 mittels Bagger", 64.0, "m3"),
        # 242 Maurer
        Position("242101000000", "Mauerwerk Kalksandstein 24 cm MG II", 142.0, "m2"),
        Position("242401000000", "Wand aus Hochlochziegel 11.5 cm verputzt", 38.0, "m2"),
        # 243 Putz
        Position("243101000000", "Aussenputz Mineralputz Koernung 2 mm", 210.0, "m2"),
        Position("243201000000", "Innenputz Kalkputz einlagig", 340.0, "m2"),
        # 244 Bodenbelag
        Position("244101000000", "Bodenbelag Keramik 30x30 cm verlegt", 185.0, "m2"),
        Position("244301000000", "Trennlage Entkopplung Boden", 185.0, "m2"),
        # 251 Zimmerei
        Position("251201000000", "Unterlagsboden Holzwerkstoff 22 mm", 165.0, "m2"),
        Position("251501000000", "Holzstaenderwand beidseitig beplankt", 72.0, "m2"),
        # 252 Dach
        Position("252401000000", "Dacheindeckung Ziegeldach neu verlegen", 240.0, "m2"),
        Position("252101000000", "Dachabdichtung Bitumen 2-lagig", 95.0, "m2"),
        # 255 Schreiner
        Position("255101000000", "Innentuer BLT Massivholz 2-fluegelig", 12.0, "Stk"),
        Position("255301000000", "Fenster Kunststoff 3-fach Verglasung", 28.0, "Stk"),
        Position("255601000000", "Einbauschrank nach Mass furniert", 9.0, "m2"),
        # 261 Elektro
        Position("261101000000", "Elektro Grundausbau pro WE", 14.0, "Stk"),
        Position("261501000000", "Steckdose Unterputz installiert", 120.0, "Stk"),
        Position("261521000000", "Lichtschalter Unterputz installiert", 64.0, "Stk"),
        Position("261601000000", "LED-Deckenleuchte inkl Montage", 48.0, "Stk"),
        # 263 Sanitaer
        Position("263101000000", "Sanitaer Grundausbau pro WE", 14.0, "Stk"),
        Position("263201000000", "Wandtiefspueler WC komplett montiert", 18.0, "Stk"),
        Position("263301000000", "Waschtisch 60 cm mit Armatur", 22.0, "Stk"),
        Position("263401000000", "Dusche bodengleich inkl Ablauf", 16.0, "Stk"),
        # 271 Anstrich
        Position("271101000000", "Innenanstrich Wand 2x Dispersion", 520.0, "m2"),
        Position("271201000000", "Aussenanstrich Fassade 2 Anstriche", 210.0, "m2"),
        Position("271501000000", "Anstrich Holzbauteile lasierend", 60.0, "m2"),
        # ABSICHTLICH AMBIG: kein exakter NPK-Treffer in Liste -> requires_review
        Position("288900000000", "Photovoltaikanlage 8 kWp auf Flachdach", 1.0, "Stk"),
        Position("299100000000", "Baustellenbewachung mit Webcam", 1.0, "Pauschal"),
    ]

    return Devis(meta=meta, addresses=addresses, chapters=chapters, positions=pos)

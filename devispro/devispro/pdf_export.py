"""PDF-Export der Offerte ueber fpdf2 (battle-tested, Preview-kompatibel).

Fallback-Logik:
- Versucht zuerst fpdf2 (sauberes, valides PDF, das jeder Reader oeffnet).
- Falls fpdf2 nicht verfuegbar, wird ein minimales Stdlib-PDF erzeugt.
"""

import os


def _chf(value):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{v:,.2f}".replace(",", "'")


def _row_text(p):
    pos = (str(p.pos_nr) or "")[:7]
    bez = (p.text or "")[:34]
    menge = f"{p.menge:.1f}" if p.menge else ""
    einh = str(p.einheit or "")
    betr = _chf(p.betrag) if p.betrag else ""
    return f"{pos:<7} {bez:<34} {menge:>6}  {einh:<7} {betr:>14}"


def _clean(s):
    """Alle Nicht-Latin-1-Zeichen (en/em dash, typografische Anfuehrungs-
    zeichen, €, § etc.) auf ASCII-Aequivalente reduzieren, damit fpdf2
    (Standard-Helvetica = Latin-1) keinen UnicodeEncodeError wirft."""
    if s is None:
        return ""
    s = str(s)
    repl = {
        "\u2013": "-", "\u2014": "-", "\u2012": "-", "\u2015": "-",
        "\u2018": "'", "\u2019": "'", "\u201a": "'",
        "\u201c": '"', "\u201d": '"', "\u201e": '"',
        "\u2026": "...", "\u2022": "-", "\u00ab": '"', "\u00bb": '"',
        "\u20ac": "CHF", "\u00a7": "S", "\u00b0": " Grad", "\u00ad": "-",
        "\u00a0": " ", "\u2009": " ",
    }
    for k, v in repl.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")


WATERMARK_TEXT = "DevisPro Pay-per-Devis — Rechnung folgt"


def watermark_aktiv() -> bool:
    """PREISMODELL v3, Entscheidung 4: dezente Fusszeile nur auf UNBEZAHLTEN
    Exporten — Ehrenwort-PPD mit offener Sammelrechnung bzw. ueberzogenes
    Prepaid-Guthaben. Bezahlte/licensierte Exporte sind wasserzeichenfrei."""
    try:
        from devispro import license as liz
        s = liz.status()
        return s.get("zustand") == "ppd_ueberzogen"
    except Exception:
        return False


def _watermark_stdlib_lines() -> list:
    """Fusszeilen-Zeile fuer den Stdlib-Pfad (kind 'footer')."""
    return [("footer", [(40, WATERMARK_TEXT)])]


def write_pdf(devis, path, rabatt=0.0):
    try:
        from fpdf import FPDF
    except Exception:
        return _write_pdf_stdlib(devis, path, rabatt)

    projekt = _clean(devis.meta.get("projekt", "") or "Devis")
    kanton = _clean(devis.meta.get("kanton", "AG"))
    mwst = devis.meta.get("mwst") or 8.1
    wm = watermark_aktiv()

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, _clean("DEVISPRO - OFFERTE"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, _clean("Projekt: " + projekt), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, _clean("Kanton: " + kanton), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # --- Tabellen-Spalten mit FIXEN x-Koordinaten (proportionale Schrift!) ---
    x_pos = pdf.l_margin + 2
    x_bez = x_pos + 16
    x_menge = x_bez + 95
    x_einh = x_menge + 22
    x_betr = pdf.w - pdf.r_margin - 30  # rechtsbuendig beginnend

    def _row(y, pos, bez, menge, einh, betr, font=("", 9),
             a_pos="L", a_bez="L", a_menge="R", a_einh="R", a_betr="R"):
        pdf.set_xy(x_pos, y)
        pdf.set_font("Helvetica", font[0], font[1])
        pdf.cell(15, 6, _clean(pos), new_x="RIGHT", new_y="TOP", align=a_pos)
        pdf.set_xy(x_bez, y)
        pdf.cell(x_menge - x_bez - 2, 6, _clean(bez), new_x="RIGHT", new_y="TOP", align=a_bez)
        pdf.set_xy(x_menge, y)
        pdf.cell(x_einh - x_menge - 2, 6, _clean(menge), new_x="RIGHT", new_y="TOP", align=a_menge)
        pdf.set_xy(x_einh, y)
        pdf.cell(x_betr - x_einh - 2, 6, _clean(einh), new_x="RIGHT", new_y="TOP", align=a_einh)
        pdf.set_xy(x_betr, y)
        pdf.cell(30, 6, _clean(betr), new_x="RIGHT", new_y="TOP", align=a_betr)

    pdf.set_font("Helvetica", "B", 9)
    y = pdf.get_y()
    # header als einzelne zellen mit korrekter ausrichtung (rechtsbuendig fuer zahlen)
    pdf.set_xy(x_pos, y)
    pdf.cell(15, 6, "Pos", new_x="RIGHT", new_y="TOP", align="L")
    pdf.set_xy(x_bez, y)
    pdf.cell(x_menge - x_bez - 2, 6, "Bezeichnung", new_x="RIGHT", new_y="TOP", align="L")
    pdf.set_xy(x_menge, y)
    pdf.cell(x_einh - x_menge - 2, 6, "Menge", new_x="RIGHT", new_y="TOP", align="R")
    pdf.set_xy(x_einh, y)
    pdf.cell(x_betr - x_einh - 2, 6, "Einheit", new_x="RIGHT", new_y="TOP", align="R")
    pdf.set_xy(x_betr, y)
    pdf.cell(30, 6, "Betrag CHF", new_x="RIGHT", new_y="TOP", align="R")
    pdf.set_draw_color(180, 180, 180)
    pdf.line(pdf.l_margin, pdf.get_y() + 6, pdf.w - pdf.r_margin, pdf.get_y() + 6)
    # y manuell verfolgen (robust gegen auto-page-break)
    y = pdf.get_y() + 8

    netto = 0.0
    row_h = 6
    bottom = pdf.h - pdf.b_margin
    for p in devis.positions:
        if not p.betrag:
            continue
        netto += p.betrag
        bez = (p.text or "")[:52]
        menge = f"{p.menge:.1f}" if p.menge else ""
        einh = str(p.einheit or "")
        betr = _chf(p.betrag)
        # seitenumbruch pruefen
        if y + row_h > bottom:
            pdf.add_page()
            y = pdf.t_margin + 4
        _row(y, str(p.pos_nr)[:10], bez, menge, einh, betr)
        y += row_h

    y += 2
    if y > bottom:
        pdf.add_page()
        y = pdf.t_margin + 4
    pdf.set_draw_color(180, 180, 180)
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    y += 2

    def _sum(yy, label, value):
        pdf.set_xy(x_pos, yy)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(x_betr - x_pos - 4, 7, _clean(label), new_x="RIGHT", new_y="TOP")
        pdf.set_xy(x_betr, yy)
        pdf.cell(30, 7, _clean(value), new_x="RIGHT", new_y="TOP", align="R")
        return yy + 7

    _sum(y, "NETTO", _chf(netto))
    y += 7
    if rabatt:
        netto_rab = netto * (1 - rabatt / 100.0)
        _sum(y, f"RABATT {rabatt:g} %", "-" + _chf(netto * rabatt / 100.0))
        y += 7
        _sum(y, f"MWST {mwst:g} %", _chf(netto_rab * mwst / 100.0))
        y += 7
        _sum(y, "BRUTTO", _chf(netto_rab * (1 + mwst / 100.0)))
    else:
        _sum(y, f"MWST {mwst:g} %", _chf(netto * mwst / 100.0))
        y += 7
        _sum(y, "BRUTTO", _chf(netto * (1 + mwst / 100.0)))
    y += 2

    # PREISMODELL v3: dezente Fusszeile auf unbezahlten PPD-Exporten (B.4)
    if wm:
        pdf.set_y(-12)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(130, 130, 130)
        pdf.cell(0, 6, _clean(WATERMARK_TEXT), align="C")
        pdf.set_text_color(0, 0, 0)

    pdf.output(path)
    return path


def build_pdf(devis, rabatt=0.0):
    import tempfile, os
    fd, p = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        write_pdf(devis, p, rabatt)
        with open(p, "rb") as f:
            return f.read()
    finally:
        try:
            os.remove(p)
        except OSError:
            pass


def _write_pdf_stdlib(devis, path, rabatt=0.0):
    projekt = str(devis.meta.get("projekt", "") or "Devis")
    kanton = str(devis.meta.get("kanton", "AG"))
    mwst = devis.meta.get("mwst") or 8.1
    # Stammdaten des KMU einbinden (falls gepflegt)
    profil = {}
    try:
        from devispro import stammdaten as sd
        profil = sd.load_profile()
    except Exception:
        profil = {}
    # --- Layout: feste Spalten-x (proportionale Schrift!) ---
    X = {"pos": 40, "bez": 75, "menge": 360, "einh": 415, "betr": 520}
    LINES = []  # (kind, [ (x, text), ... ])  -- mehrere spalten pro zeile

    # Standard-Helvetica-Zeichenbreiten (1/1000 em) fuer exakte rechtsbuendigkeit
    HELV_W = {' ':278,'!':278,'"':355,'#':556,'$':556,'%':889,'&':667,"'":191,'(':333,')':333,
              '*':389,'+':584,',':278,'-':333,'.':278,'/':278,'0':556,'1':556,'2':556,'3':556,
              '4':556,'5':556,'6':556,'7':556,'8':556,'9':556,':':278,';':278,'<':584,'=':584,
              '>':584,'?':556,'@':1015,'A':667,'B':667,'C':722,'D':722,'E':667,'F':611,'G':778,
              'H':722,'I':278,'J':500,'K':667,'L':556,'M':833,'N':722,'O':778,'P':667,'Q':778,
              'R':722,'S':667,'T':611,'U':722,'V':667,'W':944,'X':667,'Y':667,'Z':611,'[':278,
              '\\':278,']':278,'^':469,'_':556,'`':333,'a':556,'b':556,'c':500,'d':556,'e':556,
              'f':278,'g':556,'h':556,'i':222,'j':222,'k':500,'l':222,'m':833,'n':556,'o':556,
              'p':556,'q':556,'r':333,'s':500,'t':278,'u':556,'v':500,'w':722,'x':500,'y':500,
              'z':500,'{':334,'|':260,'}':334,'~':584}
    def _tw(s, size):
        return sum(HELV_W.get(c, 556) for c in s) * size / 1000.0

    def add(kind, cells):
        LINES.append((kind, cells))

    firma = profil.get("betrieb", "")
    if firma:
        add("title", [(40, str(firma))])
        adr = " ".join(x for x in [profil.get("strasse", ""), profil.get("plz", ""), profil.get("ort", "")] if x)
        if adr:
            add("sub", [(40, adr)])
        if profil.get("iban"):
            add("sub", [(40, "IBAN: " + str(profil.get("iban")))])
        add("sub", [(40, "")])
    add("title2", [(40, "OFFERTE")])
    add("sub", [(40, "Projekt: " + projekt)])
    add("sub", [(40, "Kanton: " + kanton)])
    add("sub", [(40, "")])
    # Tabellenkopf (fett)
    add("head", [(X["pos"], "Pos"), (X["bez"], "Bezeichnung"),
                 (X["menge"], "Menge"), (X["einh"], "Einheit"), (X["betr"], "Betrag CHF")])
    add("rule", [(40, "")])
    netto = 0.0
    for p in devis.positions:
        if not p.betrag:
            continue
        netto += p.betrag
        pos = (str(p.pos_nr) or "")[:7]
        bez = (p.text or "")[:40]
        menge = f"{p.menge:.1f}" if p.menge else ""
        einh = str(p.einheit or "")
        betr = _chf(p.betrag)
        add("row", [(X["pos"], pos), (X["bez"], bez),
                    (X["menge"], menge), (X["einh"], einh), (X["betr"], betr)])
    add("rule", [(40, "")])
    add("sum", [(40, "NETTO"), (X["betr"], _chf(netto) + " CHF")])
    if rabatt:
        netto_rab = netto * (1 - rabatt / 100.0)
        add("sum", [(40, "RABATT %g %%" % rabatt), (X["betr"], "-" + _chf(netto * rabatt / 100.0) + " CHF")])
        add("sum", [(40, "MWST %g %%" % mwst), (X["betr"], _chf(netto_rab * mwst / 100.0) + " CHF")])
        add("rule", [(40, "")])
        add("sumbold", [(40, "BRUTTO"), (X["betr"], _chf(netto_rab * (1 + mwst / 100.0)) + " CHF")])
    else:
        add("sum", [(40, "MWST %g %%" % mwst), (X["betr"], _chf(netto * mwst / 100.0) + " CHF")])
        add("rule", [(40, "")])
        add("sumbold", [(40, "BRUTTO"), (X["betr"], _chf(netto * (1 + mwst / 100.0)) + " CHF")])

    # PREISMODELL v3: dezente Fusszeile auf unbezahlten PPD-Exporten (B.4)
    try:
        if watermark_aktiv():
            add("footer", [(40, WATERMARK_TEXT)])
    except Exception:
        pass

    _SIZES = {"title": 18, "title2": 14, "sub": 11, "head": 10, "row": 9,
              "sum": 10, "sumbold": 11, "rule": 9, "footer": 8}
    _LEAD = {"title": 26, "title2": 18, "sub": 15, "head": 24, "row": 24,
             "sum": 24, "sumbold": 24, "rule": 24, "footer": 20}
    parts = []
    y = 800
    prev_kind = None
    for kind, cells in LINES:
        size = _SIZES.get(kind, 9)
        font = 2 if kind in ("title", "head", "sumbold") else 1
        for x, text in cells:
            t = _clean(text)
            # rechtsbuendig ausrichten: betrag- & summen-spalte (x >= X["betr"]) an rechte kante 555
            if x >= X["betr"]:
                draw_x = 555 - _tw(t, size)
            else:
                draw_x = x
            tb = t.encode("latin-1", "replace")
            parts.append(b"BT")
            parts.append(("/F%d %d Tf" % (font, size)).encode("latin-1"))
            parts.append(("1 0 0 1 %d %d Tm" % (draw_x, y)).encode("latin-1"))
            parts.append(b"(%s) Tj" % tb)
            parts.append(b"ET")
        lead = _LEAD.get(kind, 12)
        if kind == "rule":
            # linie mittig in die 24pt-luecke (12pt unter kopf-baseline, 12pt ueber daten-baseline)
            yline = y - 12
            # brutto-trennung (regel direkt nach einer sum-zeile) dicker, kopf-trennung duenner
            w = 1.0 if prev_kind == "sum" else 0.6
            parts.append(("%s w 0.3 0.3 0.3 RG %s G 40 %d m 555 %d l S" % (
                ("1.0" if w == 1.0 else "0.6"),
                ("0.3" if w == 1.0 else "0.7"),
                yline, yline)).encode("latin-1"))
        prev_kind = kind
        y -= lead
    stream = b"\n".join(parts)
    objects = []
    objects.append((3, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"))
    objects.append((4, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"))
    # Objekt 5 = Content-Stream (MUSS stream/endstream + /Length haben!)
    stream_obj = b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
    objects.append((5, stream_obj))
    objects.append((6, b"<< /Type /Page /Parent 7 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents 5 0 R >>"))
    objects.append((7, b"<< /Type /Pages /Count 1 /Kids [ 6 0 R ] >>"))
    objects.append((8, b"<< /Type /Catalog /Pages 7 0 R >>"))
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    for num, data in objects:
        offsets[num] = len(out)
        out += ("%d 0 obj\n" % num).encode("latin-1")
        out += data
        out += b"\nendobj\n"
    xref_pos = len(out)
    max_obj = max(offsets)
    out += ("xref\n0 %d\n" % (max_obj + 1)).encode("latin-1")
    out += b"0000000000 65535 f \n"
    for i in range(1, max_obj + 1):
        if i in offsets:
            out += ("%010d 00000 n \n" % offsets[i]).encode("latin-1")
        else:
            out += b"0000000000 65535 f \n"
    out += ("trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (max_obj + 1, 8, xref_pos)).encode("latin-1")
    with open(path, "wb") as f:
        f.write(bytes(out))
    return path

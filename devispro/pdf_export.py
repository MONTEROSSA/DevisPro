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


def write_pdf(devis, path, rabatt=0.0):
    try:
        from fpdf import FPDF
    except Exception:
        return _write_pdf_stdlib(devis, path, rabatt)

    projekt = _clean(devis.meta.get("projekt", "") or "Devis")
    kanton = _clean(devis.meta.get("kanton", "AG"))
    mwst = devis.meta.get("mwst") or 7.7

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
    lines = []
    projekt = str(devis.meta.get("projekt", "") or "Devis")
    kanton = str(devis.meta.get("kanton", "AG"))
    mwst = devis.meta.get("mwst") or 7.7
    lines.append(("title", "DEVISPRO - OFFERTE"))
    lines.append(("sub", "Projekt: " + projekt))
    lines.append(("sub", "Kanton: " + kanton))
    lines.append(("sub", ""))
    lines.append(("head", "Pos      Bezeichnung                         Menge  Einheit       Betrag CHF"))
    lines.append(("rule", ""))
    netto = 0.0
    for p in devis.positions:
        if not p.betrag:
            continue
        netto += p.betrag
        pos = (str(p.pos_nr) or "")[:7]
        bez = (p.text or "")[:34]
        menge = f"{p.menge:.1f}" if p.menge else ""
        einh = str(p.einheit or "")
        betr = _chf(p.betrag)
        lines.append(("row", f"{pos:<7} {bez:<34} {menge:>6}  {einh:<7} {betr:>14}"))
    lines.append(("rule", ""))
    lines.append(("sum", f"{'NETTO':<54}{_chf(netto):>16}"))
    if rabatt:
        netto_rab = netto * (1 - rabatt / 100.0)
        lines.append(("sum", f"{'RABATT ' + str(rabatt) + ' %':<54}{'-' + _chf(netto * rabatt / 100.0):>16}"))
        lines.append(("sum", f"{'MWST ' + str(mwst) + ' %':<54}{_chf(netto_rab * mwst / 100.0):>16}"))
        lines.append(("sum", f"{'BRUTTO':<54}{_chf(netto_rab * (1 + mwst / 100.0)):>16}"))
    else:
        lines.append(("sum", f"{'MWST ' + str(mwst) + ' %':<54}{_chf(netto * mwst / 100.0):>16}"))
        lines.append(("sum", f"{'BRUTTO':<54}{_chf(netto * (1 + mwst / 100.0)):>16}"))

    _SIZES = {"title": 18, "sub": 11, "head": 10, "row": 9, "sum": 10, "rule": 9}
    _LEAD = {"title": 26, "sub": 15, "head": 14, "row": 12, "sum": 14, "rule": 6}
    parts = []
    y = 800
    for kind, text in lines:
        size = _SIZES.get(kind, 9)
        font = 2 if kind in ("title", "head") else 1
        t = text.encode("latin-1", "replace")
        parts.append(b"BT")
        parts.append(("/F%d %d Tf" % (font, size)).encode("latin-1"))
        parts.append(("1 0 0 1 40 %d Tm" % y).encode("latin-1"))
        parts.append(b"(%s) Tj" % t)
        parts.append(b"ET")
        y -= _LEAD.get(kind, 12)
    stream = b"\n".join(parts)
    objects = []
    objects.append((3, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"))
    objects.append((4, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"))
    objects.append((5, stream))
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

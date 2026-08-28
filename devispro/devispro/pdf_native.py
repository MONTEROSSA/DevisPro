"""Dependency-freier PDF-Generator (reine Stdlib, KEIN wkhtmltopdf).

Erzeugt gueltige A4-PDFs mit Ueberschriften, Schluesseltabelle, Positions-
tabellen, Summen und Unterschriftenblock. Verwendet die Standard-PDF-Fonts
Helvetica/Helvetica-Bold (WinAnsiEncoding) – Nicht-WinAnsi-Zeichen werden
auf ASCII-Ersatz gemappt (Emojis entfernt, –/·/✓ ersetzt).

Nutzung:
    pdf = PDF()
    pdf.heading("Werkvertrag")
    pdf.kv([("Auftraggeber","..."), ("Objekt","...")])
    pdf.table(["Nr","Bezeichnung","..."],[[...],...], widths=[60,300,80])
    pdf.text("Hinweis: ...")
    pdf.sign(["Unternehmer","Besteller"])
    data = pdf.build()   # bytes, beginnend mit b"%PDF"
"""
import re
import zlib

# ---- A4 in Punkten (1pt = 1/72 inch) ----
PAGE_W = 595.28
PAGE_H = 841.89
MARGIN_L = 56.0
MARGIN_R = 56.0
MARGIN_T = 56.0
MARGIN_B = 56.0
GREEN = "0.08 0.32 0.18"


def _sanitize(s):
    if s is None:
        return ""
    s = str(s)
    repl = {
        "\u2013": "-", "\u2014": "-", "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u00b7": "-",
        "\u2713": "x", "\u2717": "x", "\u2192": "->", "\u00a0": " ",
        "\u2022": "-", "\u20ac": "CHF ", "\u00d7": "x",
    }
    for k, v in repl.items():
        s = s.replace(k, v)
    out = []
    for ch in s:
        if ord(ch) < 0x2500:           # keine Emojis / Box-Zeichen
            out.append(ch)
    s = "".join(out)
    return s.encode("latin-1", "replace").decode("latin-1")


def _esc(s):
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


_HELV_W = {
    ' ': 278, '!': 278, '"': 355, '#': 556, '$': 556, '%': 889, '&': 667,
    "'": 191, '(': 333, ')': 333, '*': 389, '+': 584, ',': 278, '-': 333,
    '.': 278, '/': 278, '0': 556, '1': 556, '2': 556, '3': 556, '4': 556,
    '5': 556, '6': 556, '7': 556, '8': 556, '9': 556, ':': 278, ';': 278,
    '<': 584, '=': 584, '>': 584, '?': 556, '@': 1015, 'A': 667, 'B': 667,
    'C': 722, 'D': 722, 'E': 667, 'F': 611, 'G': 778, 'H': 722, 'I': 278,
    'J': 500, 'K': 667, 'L': 556, 'M': 833, 'N': 722, 'O': 778, 'P': 667,
    'Q': 778, 'R': 722, 'S': 667, 'T': 611, 'U': 722, 'V': 667, 'W': 944,
    'X': 667, 'Y': 667, 'Z': 611, '[': 278, '\\': 278, ']': 278, '^': 469,
    '_': 556, '`': 333, 'a': 556, 'b': 556, 'c': 500, 'd': 556, 'e': 556,
    'f': 278, 'g': 556, 'h': 556, 'i': 222, 'j': 222, 'k': 500, 'l': 222,
    'm': 833, 'n': 556, 'o': 556, 'p': 556, 'q': 556, 'r': 333, 's': 500,
    't': 278, 'u': 556, 'v': 500, 'w': 722, 'x': 500, 'y': 500, 'z': 500,
    '{': 334, '|': 260, '}': 334, '~': 584,
}


def _width(text, size):
    total = 0
    for ch in _sanitize(text):
        total += _HELV_W.get(ch, 556)
    return total / 1000.0 * size


def _wrap(text, size, max_w):
    words = _sanitize(text).split(" ")
    lines = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if _width(trial, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


class PDF:
    def __init__(self):
        self.ops = []       # (y, x, text, font, size, color)
        self.lines = []     # (x1,y1,x2,y2,w,color)
        self.rects = []     # (x1,y2bottom,x2,y1top,color) pro Seite
        self.pages = []       # (ops, lines, rects)
        self.y = PAGE_H - MARGIN_T
        self._footer_text = ""
        self._footer_size = 8
        self._images = []     # (img_id, w, h, comp_bytes)
        self._image_ops = []  # (x, y, w, h, img_id)

    # ---- interne Helfer ----
    def _ensure(self, need=20):
        if self.y - need < MARGIN_B:
            self._flush_page()

    def _flush_page(self):
        rects = list(self.rects)
        self.pages.append((list(self.ops), list(self.lines), rects))
        self.ops = []
        self.lines = []
        self.rects = []
        self.y = PAGE_H - MARGIN_T

    # ---- oeffentliche API ----
    def heading(self, text, size=16):
        self._ensure(40)
        self.y -= size + 6
        self.ops.append((self.y, MARGIN_L, text, "F2", size, GREEN))
        self.y -= 6
        self.lines.append((MARGIN_L, self.y, PAGE_W - MARGIN_R, self.y, 1.2, GREEN))
        self.y -= 14

    def subtitle(self, text, size=10):
        self._ensure(20)
        self.y -= size + 4
        self.ops.append((self.y, MARGIN_L, text, "F1", size, "0 0 0"))
        self.y -= 8

    def kv(self, pairs, size=10):
        label_w = 150.0
        for k, v in pairs:
            self._ensure(size + 8)
            self.y -= size + 6
            self.ops.append((self.y, MARGIN_L, k, "F2", size, "0 0 0"))
            for i, line in enumerate(_wrap(v, size, PAGE_W - MARGIN_R - MARGIN_L - label_w)):
                if i > 0:
                    self._ensure(size + 6)
                    self.y -= size + 6
                self.ops.append((self.y, MARGIN_L + label_w, line, "F1", size, "0 0 0"))
        self.y -= 6

    def table(self, headers, rows, widths, size=9, zebra=True):
        total_w = sum(widths)
        x0 = MARGIN_L
        self._ensure(size + 12)
        self.y -= size + 6
        hx = x0
        for h, w in zip(headers, widths):
            self.ops.append((self.y, hx + 3, h, "F2", size, "0 0 0"))
            hx += w
        self.y -= 4
        self.lines.append((x0, self.y, x0 + total_w, self.y, 0.8, "0.4 0.4 0.4"))
        self.y -= 4
        for ri, row in enumerate(rows):
            cell_lines = [_wrap(str(val), size, w - 6) for val, w in zip(row, widths)]
            n = max(len(c) for c in cell_lines)
            row_h = n * (size + 4) + 4
            if self.y - row_h < MARGIN_B:
                self._flush_page()
                self.y -= size + 6
                hx = x0
                for h, w in zip(headers, widths):
                    self.ops.append((self.y, hx + 3, h, "F2", size, "0 0 0"))
                    hx += w
                self.y -= 4
                self.lines.append((x0, self.y, x0 + total_w, self.y, 0.8, "0.4 0.4 0.4"))
                self.y -= 4
            if zebra and ri % 2 == 1:
                self.rects.append((x0, self.y - row_h, x0 + total_w, self.y, "0.95 0.97 0.95"))
            cx = x0
            top = self.y
            for ci, (val, w) in enumerate(zip(row, widths)):
                ty = top
                for ln in cell_lines[ci]:
                    ty -= size + 4
                    self.ops.append((ty, cx + 3, ln, "F1", size, "0 0 0"))
                cx += w
            self.y -= row_h
            self.lines.append((x0, self.y, x0 + total_w, self.y, 0.4, "0.8 0.8 0.8"))
        self.y -= 8

    def summary(self, rows, size=10):
        label_w = 240.0
        x0 = PAGE_W - MARGIN_R - label_w - 120
        for i, (k, v, bold) in enumerate(rows):
            self._ensure(size + 8)
            self.y -= size + 6
            self.ops.append((self.y, x0, k, "F2" if bold else "F1", size, "0 0 0"))
            self.ops.append((self.y, PAGE_W - MARGIN_R - 120, v, "F2" if bold else "F1", size, "0 0 0"))
            if bold:
                self.lines.append((x0, self.y - 2, PAGE_W - MARGIN_R, self.y - 2, 1.0, GREEN))

    def text(self, text, size=10, color=None):
        for ln in _wrap(text, size, PAGE_W - MARGIN_R - MARGIN_L):
            self._ensure(size + 6)
            self.y -= size + 6
            self.ops.append((self.y, MARGIN_L, ln, "F1", size, color or "0 0 0"))

    def spacer(self, h=10):
        self._ensure(h)
        self.y -= h

    def sign(self, labels, size=10):
        self._ensure(60)
        self.y -= 50
        n = len(labels)
        gap = 40
        slot = (PAGE_W - MARGIN_L - MARGIN_R - gap * (n - 1)) / n
        x = MARGIN_L
        for lab in labels:
            self.lines.append((x, self.y, x + slot, self.y, 0.6, "0.3 0.3 0.3"))
            self.ops.append((self.y - 14, x, lab, "F1", size, "0 0 0"))
            x += slot + gap

    def note(self, text, size=9):
        self._ensure(30)
        self.y -= 8
        self.lines.append((MARGIN_L, self.y, PAGE_W - MARGIN_R, self.y, 0.6, "0.95 0.6 0.1"))
        self.y -= 6
        for ln in _wrap(text, size, PAGE_W - MARGIN_R - MARGIN_L - 12):
            self._ensure(size + 6)
            self.y -= size + 6
            self.ops.append((self.y, MARGIN_L + 6, ln, "F1", size, "0.6 0.2 0.1"))
        self.y -= 6

    def footer(self, text, size=8):
        self._footer_text = text
        self._footer_size = size

    def image(self, matrix, x, y, size, quiet=4):
        """Bettet ein QR-Symbol (bool-Matrix) als FlateDecode-Grayscale-Bild ein.

        matrix: list[list[int]] (1=dunk, 0=hell) ODER Tuple (matrix, n).
        size: Kantenlaenge in pt.
        """
        if isinstance(matrix, tuple):
            matrix = matrix[0]
        n = len(matrix)
        dim = n + 2 * quiet
        raw = bytearray()
        for r in range(dim):
            raw.append(0)  # filter type 0 pro Zeile
            for c in range(dim):
                v = 0 if (quiet <= r < quiet + n and quiet <= c < quiet + n and matrix[r - quiet][c - quiet]) else 255
                raw.append(v)
        comp = zlib.compress(bytes(raw), 9)
        img_id = self._next_img_id()
        self._images.append((img_id, dim, dim, comp))
        # Bild als XObject referenzieren (in Content als Do)
        self._image_ops.append((x, y, size, size, img_id))

    def _next_img_id(self):
        if not hasattr(self, "_img_counter"):
            self._img_counter = 1000
        self._img_counter += 1
        return self._img_counter

    def build(self):
        self._flush_page()
        if not hasattr(self, "_images"):
            self._images = []
        if not hasattr(self, "_image_ops"):
            self._image_ops = []
        # Footer an jede Seite anhaengen
        if self._footer_text:
            for pg in self.pages:
                pg[0].append((MARGIN_B - 12, MARGIN_L, self._footer_text, "F1", self._footer_size, "0.5 0.5 0.5"))
        body = []
        catalog_id, pages_id, f1_id, f2_id = 1, 2, 3, 4
        next_id = 5
        body.append((catalog_id, b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id))
        body.append((pages_id, None))
        body.append((f1_id, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"))
        body.append((f2_id, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"))
        # Bild-XObjects (QR-Codes) registrieren
        img_obj_ids = {}
        img_names = {}
        k = 0
        for (img_id, w, h, comp) in self._images:
            k += 1
            cid = next_id; next_id += 1
            name = "Im%d" % k
            img_obj_ids[img_id] = cid
            img_names[img_id] = name
            body.append((cid, (b"<< /Type /XObject /Subtype /Image /Width %d /Height %d "
                               b"/ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /FlateDecode "
                               b"/Length %d >>\nstream\n%s\nendstream" % (w, h, len(comp), comp))))
        page_ids = []
        for idx, (ops, lns, rects) in enumerate(self.pages):
            img_for_page = img_names if (idx == len(self.pages) - 1) else None
            content = self._render_content(ops, lns, rects, img_for_page)
            cid = next_id; next_id += 1
            pid = next_id; next_id += 1
            body.append((cid, b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content)))
            page_ids.append(pid)
            xobj_res = ""
            if self._image_ops and img_obj_ids:
                parts = " ".join("/%s %d 0 R" % (img_names[iid], img_obj_ids[iid]) for (_, _, _, _, iid) in self._image_ops if iid in img_obj_ids)
                xobj_res = " /XObject << " + parts + " >>"
            body.append((pid, ("<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.2f %.2f] "
                             "/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >>%s >> "
                             "/Contents %d 0 R >>" % (pages_id, PAGE_W, PAGE_H, f1_id, f2_id, xobj_res, cid)).encode("latin-1")))
        kids = " ".join("%d 0 R" % p for p in page_ids)
        body[pages_id - 1] = (pages_id, b"<< /Type /Pages /Count %d /Kids [%s] >>" % (len(page_ids), kids.encode()))
        out = bytearray()
        out += b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
        offsets = {1: len(out)}
        for oid, val in body:
            offsets[oid] = len(out)
            out += ("%d 0 obj\n" % oid).encode("latin-1")
            out += val
            out += b"\nendobj\n"
        xref_pos = len(out)
        max_id = max(offsets)
        out += ("xref\n0 %d\n" % (max_id + 1)).encode("latin-1")
        out += b"0000000000 65535 f \n"
        for i in range(1, max_id + 1):
            out += ("%010d 00000 n \n" % offsets.get(i, 0)).encode("latin-1")
        out += b"trailer\n"
        out += ("<< /Size %d /Root %d 0 R >>\n" % (max_id + 1, catalog_id)).encode("latin-1")
        out += b"startxref\n%d\n%%%%EOF" % xref_pos
        return bytes(out)

    def _render_content(self, ops, lns, rects, img_names=None):
        s = []
        if img_names and self._image_ops:
            for (x, y, w, h, iid) in self._image_ops:
                if iid in img_names:
                    s.append("q")
                    s.append("%.2f 0 0 %.2f %.2f %.2f cm" % (w, h, x, y))
                    s.append("/%s Do" % img_names[iid])
                    s.append("Q")
        for (x1, y2b, x2, y1t, color) in rects:
            s.append("%s rg" % color)
            s.append("%.2f %.2f %.2f %.2f re f" % (x1, y2b, x2 - x1, y1t - y2b))
            s.append("0 0 0 rg")
        for (x1, y1, x2, y2, w, color) in lns:
            s.append("%s RG" % color)
            s.append("%.2f w" % w)
            s.append("%.2f %.2f m %.2f %.2f l S" % (x1, y1, x2, y2))
        for (y, x, text, font, size, color) in sorted(ops, key=lambda o: -o[0]):
            t = _esc(_sanitize(text))
            s.append("%s rg" % color)
            s.append("BT /%s %.2f Tf %.2f %.2f Td (%s) Tj ET" % (font, size, x, y, t))
        return "\n".join(s).encode("latin-1")

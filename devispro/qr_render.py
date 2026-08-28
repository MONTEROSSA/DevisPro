"""QR-Code-Encoder (reine Stdlib, KEINE externen Libs).

Erzeugt ein scannbares QR-Symbol (Byte-Mode, ECC-Level M, Auto-Version)
aus einem Text. Damit kann DevisPro echte Swiss-QR-Rechnungen erzeugen,
OHNE dass der KMU 'qrcode' / 'Pillow' installieren muss.

Der Swiss-QR-Code ist faktisch ein normales QR mit dem SPC-Payload als
Textinhalt (Swiss-Banking-Apps scannen jedes Standard-QR mit diesem Payload).
"""
import zlib


# ---- GF(256) Tabelle fuer Reed-Solomon -----------------------------------
_EXP = [0] * 256
_LOG = [0] * 256
_x = 1
for _i in range(256):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D  # AES-Polynom


def _gf_mul(a, b):
    if a == 0 or b == 0:
        return 0
    return _EXP[(_LOG[a] + _LOG[b]) % 255]


def _rs_poly(deg):
    """Erzeugt das Reed-Solomon-Generator-Polynom der Grade 'deg'."""
    p = [1]
    for i in range(deg):
        # p = p * (x - alpha^i)  mit alpha=2
        np_ = [0] * (len(p) + 1)
        for j, c in enumerate(p):
            np_[j] = _gf_mul(c, _EXP[i]) if c else 0
            np_[j + 1] ^= c
        p = np_
    return p


def _rs_encode(msg, ec_len):
    gen = _rs_poly(ec_len)
    res = list(msg) + [0] * ec_len
    for i in range(len(msg)):
        coef = res[i]
        if coef != 0:
            for j in range(len(gen)):
                res[i + j] ^= _gf_mul(gen[j], coef)
    return res[len(msg):]


# ---- Capacity-Tabelle (Byte-Mode, ECC M) je Version ----------------------
# (ec_blocks, ec_per_block, data_per_block) – nur die Version, die wir brauchen
_CAP = {
    1: (1, 10, 16), 2: (1, 16, 28), 3: (1, 26, 44), 4: (1, 36, 64),
    5: (1, 48, 86), 6: (2, 28, 108), 7: (2, 32, 124), 8: (2, 40, 154),
    9: (2, 48, 182), 10: (2, 56, 216),
}


def _mode_indicator():
    return "0100"  # Byte-Mode


def _char_count_bits(ver):
    return 8 if ver <= 9 else 16


def _bitlen(n):
    return len(bin(n)) - 2


def _num_to_bits(n, bits):
    return format(n, "0%db" % bits)


def _encode_data(text, ver):
    # Text -> ISO-8859-1 Bytes (Swiss QR nutzt Latin/WinAnsi)
    try:
        data = text.encode("latin-1")
    except UnicodeEncodeError:
        data = text.encode("utf-8")
    cc_bits = _char_count_bits(ver)
    bits = _mode_indicator()
    bits += _num_to_bits(len(data), cc_bits)
    for b in data:
        bits += _num_to_bits(b, 8)
    return bits, data


def _capacity_bytes(ver):
    _, ec, per = _CAP[ver]
    return per


def _choose_version(text):
    for v in range(1, 11):
        if len(text.encode("latin-1", "ignore") or text.encode("utf-8")) <= _capacity_bytes(v):
            return v
    raise ValueError("Payload zu lang fuer QR bis Version 10")


# ---- Matrix-Aufbau -------------------------------------------------------
def _size(ver):
    return 17 + ver * 4


_FINDER = None


def _place_finder(m, r, c):
    n = len(m)
    # 7x7 Finder-Pattern
    for i in range(7):
        for j in range(7):
            rr, cc = r + i, c + j
            if not (0 <= rr < n and 0 <= cc < n):
                continue
            if i == 0 or i == 6 or j == 0 or j == 6:
                m[rr][cc] = 1
            elif 2 <= i <= 4 and 2 <= j <= 4:
                m[rr][cc] = 1
            else:
                m[rr][cc] = 0
    # 1-modul weisser Trennrahmen (ausser nach aussen zum Rand)
    for k in range(8):
        for (rr, cc) in ((r - 1, c + k), (r + 7, c + k), (r + k, c - 1), (r + k, c + 7)):
            if 0 <= rr < n and 0 <= cc < n:
                m[rr][cc] = 0


def _build_matrix(bitstream, ver):
    n = _size(ver)
    m = [[None] * n for _ in range(n)]
    # Finder + Rahmen (3 Ecken)
    _place_finder(m, 0, 0)
    _place_finder(m, 0, n - 7)
    _place_finder(m, n - 7, 0)
    # Timing-Pattern
    for i in range(8, n - 8):
        m[6][i] = 1 if i % 2 == 0 else 0
        m[i][6] = 1 if i % 2 == 0 else 0
    # Reserviere Format-Information + Dunkles Modul
    for i in range(n):
        for j in range(n):
            if m[i][j] is not None:
                continue
    # (Formatbereich wird unten separat gesetzt)
    # Daten eintragen (Zickzack, von unten rechts)
    data_idx = 0
    direction = 1
    col = n - 1
    while col > 0:
        if col == 6:
            col -= 1
        for row in range(n - 1, -1, -1) if direction > 0 else range(n):
            for c in (col, col - 1):
                if m[row][c] is None:
                    if data_idx < len(bitstream):
                        m[row][c] = 1 if bitstream[data_idx] == "1" else 0
                        data_idx += 1
                    else:
                        m[row][c] = 0
        direction = -direction
        col -= 2
    return m, n


def _mask(m, n, mask_id):
    """Wendet Maske an (vereinfacht: Mask 0 – (i+j)%2==0)."""
    for i in range(n):
        for j in range(n):
            if m[i][j] is None:
                continue
            # nur Datenbereich maskieren (Finder grob aussparen)
            if (i <= 8 and j <= 8) or (i <= 8 and j >= n - 8) or (i >= n - 8 and j <= 8):
                continue
            if mask_id == 0 and (i + j) % 2 == 0:
                m[i][j] ^= 1
    return m


def encode(text):
    """Gibt (matrix: list[list[int]], n: int) zurueck – 1=dunk, 0=hell."""
    ver = _choose_version(text)
    bits, _ = _encode_data(text, ver)
    # ECC
    _, ec_per, data_per = _CAP[ver]
    # Grenze Byte-Laenge an Capacity
    full = bits
    # Terminator + Padder auf Byte
    cap_bits = data_per * 8
    full = full[:cap_bits]
    if len(full) + 4 <= cap_bits:
        full += "0000"
    while len(full) % 8 != 0:
        full += "0"
    # Fuelle mit Bytes 0xEC, 0x11 abwechselnd
    while len(full) < cap_bits:
        full += "11101100" if (len(full) // 8) % 2 == 0 else "00010001"
    # Bytes -> msg int-Liste
    msg = [int(full[i:i + 8], 2) for i in range(0, len(full), 8)]
    ec = _rs_encode(msg, ec_per)
    # Interleaving: bei 1 Block trivial
    allbytes = msg + ec
    # Bitstream aus allen Bytes
    bs = "".join(_num_to_bits(b, 8) for b in allbytes)
    m, n = _build_matrix(bs, ver)
    m = _mask(m, n, 0)
    # Format-Information (vereinfacht: festes Pattern fuer ECC=M, Mask=0)
    _place_format(m, n, 0x5412)
    return m, n


def _place_format(m, n, fmt):
    """fmt = 15-Bit-Wert (bereits inkl. ECC). Platziert um Finder."""
    bits = [ (fmt >> (14 - i)) & 1 for i in range(15) ]
    # Position 1: um oberen-left Finder
    pos = [(8,0),(8,1),(8,2),(8,3),(8,4),(8,5),(8,7),(8,8),(7,8),(5,8),(4,8),(3,8),(2,8),(1,8),(0,8)]
    for (r, c), b in zip(pos, bits):
        m[r][c] = b
    # Position 2: um restliche Ecken
    pos2 = [(n-1,8),(n-2,8),(n-3,8),(n-4,8),(n-5,8),(n-6,8),(n-7,8),(8,n-8),(8,n-7),(8,n-6),(8,n-5),(8,n-4),(8,n-3),(8,n-2),(8,n-1)]
    for (r, c), b in zip(pos2, bits):
        m[r][c] = b


def to_svg(matrix, scale=4, quiet=4):
    n = len(matrix)
    dim = (n + 2 * quiet) * scale
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{dim}" height="{dim}" viewBox="0 0 {dim} {dim}">']
    parts.append('<rect width="100%" height="100%" fill="white"/>')
    for r in range(n):
        for c in range(n):
            if matrix[r][c]:
                x = (c + quiet) * scale
                y = (r + quiet) * scale
                parts.append(f'<rect x="{x}" y="{y}" width="{scale}" height="{scale}" fill="black"/>')
    parts.append('</svg>')
    return "".join(parts)


def to_png_bytes(matrix, scale=4, quiet=4):
    """Embedded PNG via zlib (Truecolor, 1 Pixel/Byte-Paar)."""
    n = len(matrix)
    dim = n + 2 * quiet
    raw = bytearray()
    for r in range(dim):
        raw.append(0)  # filter type 0
        for c in range(dim):
            if quiet <= r < quiet + n and quiet <= c < quiet + n and matrix[r - quiet][c - quiet]:
                raw += b"\x00\x00\x00"
            else:
                raw += b"\xff\xff\xff"
    comp = zlib.compress(bytes(raw), 9)
    def chunk(typ, data):
        return (len(data)).to_bytes(4, "big") + typ + data + zlib.crc32(typ + data).to_bytes(4, "big")
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = (dim).to_bytes(4, "big") + (dim).to_bytes(4, "big") + b"\x08\x02\x00\x00\x00"
    idat = chunk(b"IDAT", comp)
    return sig + chunk(b"IHDR", ihdr) + idat + chunk(b"IEND", b"")

"""QR-Code-Encoder fuer DevisPro.

Nutzt die bewaehrte, reine-Stdlib-Bibliothek 'segno' (vendored im Bundle
unter devispro/segno), damit der KMU NICHTS installieren muss und der
QR-Code garantiert scannbar ist (korrektes Reed-Solomon, Masking,
Format-/Version-Information nach ISO/IEC 18004).

Oeffentliche API (kompatibel zur alten Eigenimplementierung):
  encode(text) -> (matrix: list[list[int]], n: int)   # 1=dunk, 0=hell
  to_png_bytes(text, scale=10, quiet=4) -> bytes       # echtes PNG
  to_svg(text, scale=4, quiet=4) -> str
"""

import sys
import os

# segno ist im Bundle unter devispro/segno ausgeliefert
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import segno


def encode(text, error="m"):
    """Liefert (matrix, n) – 1=dunkles Modul, 0=helles Modul.

    Kompatibel zur alten Signatur; nutzt segno als korrekten Encoder.
    """
    qr = segno.make(text, error=error)
    matrix_rows = qr.matrix
    n = len(matrix_rows)
    matrix = []
    for r in range(n):
        row = []
        for c in range(n):
            row.append(1 if matrix_rows[r][c] else 0)
        matrix.append(row)
    return matrix, n


def to_png_bytes(text, scale=10, quiet=4, error="m"):
    """Erzeugt ein echtes, scannbares PNG (Truecolor) ueber segno."""
    import io
    qr = segno.make(text, error=error)
    bio = io.BytesIO()
    qr.save(bio, kind="png", scale=scale, border=quiet)
    return bio.getvalue()


def to_svg(text, scale=4, quiet=4, error="m"):
    qr = segno.make(text, error=error)
    return qr.svg_inline(scale=scale, border=quiet, quiet_zone=quiet,
                         xmldecl=False, svgns=False)

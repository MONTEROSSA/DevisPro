"""RSA in reinem Python (nur Stdlib) - keine C-Bindings noetig.

Verwendung fuer Lizenz-Signatur:
  - Anbieter hat PRIVATE Key -> signiert kunde_id|gueltig_bis
  - KMU hat PUBLIC Key (in App einkompiliert) -> verifiziert die Signatur
  - Private Key verlaesst nie den Anbieter

Schluessellaenge 1024 Bit (ausreichend fuer Lizenz-Codes; reine Python-
Generierung in ~20s, Verifikation via pow() in Mikrosekunden).

WICHTIG: Dies ist KEINE Hochsicherheits-Verschluesselung, sondern verhindert,
dass ein KMU ohne den (geheimen) Private Key gueltige Codes faelschen kann.
"""
import secrets
import hashlib


def _is_prime(n, k=12):
    if n < 2:
        return False
    for p in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]:
        if n % p == 0:
            return n == p
    d = n - 1
    r = 0
    while d % 2 == 0:
        d //= 2
        r += 1
    for _ in range(k):
        a = secrets.randbelow(n - 3) + 2
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def _gen_prime(bits):
    while True:
        cand = secrets.randbits(bits) | (1 << (bits - 1)) | 1
        if _is_prime(cand):
            return cand


def _egcd(a, b):
    if b == 0:
        return a, 1, 0
    g, y, x = _egcd(b, a % b)
    return g, x, y - (a // b) * x


def _modinv(a, m):
    g, x, _ = _egcd(a % m, m)
    if g != 1:
        raise ValueError("Kein modulares Inverses")
    return x % m


def generate_keypair(bits=1024):
    """Erzeugt (public, private) als Tupel von (n, e) bzw (n, d)."""
    p = _gen_prime(bits // 2)
    q = _gen_prime(bits // 2)
    while q == p:
        q = _gen_prime(bits // 2)
    n = p * q
    phi = (p - 1) * (q - 1)
    e = 65537
    while _egcd(e, phi)[0] != 1:
        e += 2
    d = _modinv(e, phi)
    return (n, e), (n, d)


def _hash_int(msg: str) -> int:
    h = hashlib.sha256(msg.encode("utf-8")).digest()
    return int.from_bytes(h, "big")


def sign(private_key, msg: str) -> str:
    """Signiert msg; Rueckgabe hex-String der Signatur."""
    n, d = private_key
    z = _hash_int(msg) % n
    s = pow(z, d, n)
    return format(s, "x").zfill((n.bit_length() + 3) // 4)


def verify(public_key, msg: str, sig_hex: str) -> bool:
    """Verifiziert Signatur; True/False."""
    try:
        n, e = public_key
        s = int(sig_hex, 16) % n
        z = pow(s, e, n)
        return z == (_hash_int(msg) % n)
    except Exception:
        return False


def key_to_str(key) -> str:
    return f"{key[0]}:{key[1]}"


def key_from_str(s: str):
    n, v = s.split(":")
    return (int(n), int(v))

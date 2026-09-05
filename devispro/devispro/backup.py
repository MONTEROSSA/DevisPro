"""Verschluesseltes Backup mit PBKDF2 + AES-256-CTR + HMAC-SHA256.

M27 Compliance-Fix: Backups enthalten Kunden-, IBAN-, MwSt-Daten.
Ohne Verschluesselung waeren das DSG-relevante Daten im Klartext
auf der Festplatte. Mit diesem Modul:
- Backups werden mit einem User-Passwort verschluesselt
- PBKDF2-HMAC-SHA256 mit 600'000 Iterations leitet Schluessel ab (OWASP 2023+)
- AES-256-CTR (Counter-Mode) verschluesselt den Inhalt
- HMAC-SHA256 signiert das Backup (Authentizitaet + Integritaet)
- PBKDF2 Salt + Nonce sind pro Backup zufaellig

Format des verschluesselten Backups (.dpbk = DevisPro Backup):
  Header (4 bytes magic "DPBK") + Version (1 byte) + Iterations (4 bytes BE)
  + Salt (16 bytes) + Nonce (16 bytes) + HMAC (32 bytes) + IV-Counter (16 bytes initial)
  + ZIP-Bytes (verschluesselt)
"""
import os
import json
import struct
import hashlib
import hmac
import time
import zipfile
import shutil

from . import data_store as ds

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

USER_DATA = ds.app_support_dir()
BACKUP_DIR = os.path.join(USER_DATA, "backups")

# M27-FIX: devis/ + audit.log + alle kritischen Dateien sind jetzt enthalten.
# Vorher waren 28 Devis verloren weil devis/ fehlte.
SCOPE = [
    "meine_preise.csv", "npk_preise.csv", "kunden.json", "verlauf.json",
    "profil.json", "logo.png", "kundenstamm.json", "team.json",
    "abo", "lizenz", "templates", "wiederkehrend.json",
    "partner_erp_queue.json", "audit.log",
]
# Optional vorhandene Ordner im App-Bundle (falls vom KMU genutzt)
# devis/ MUSS enthalten sein — Regression: test_backup_scope_regression.py
BUNDLE_SCOPE = ["history", "templates", "devis"]

# Konstanten
MAGIC = b"DPBK"
FORMAT_VERSION = 1
PBKDF2_ITERATIONS = 600_000  # OWASP 2023+ Empfehlung fuer PBKDF2-HMAC-SHA256
SALT_LEN = 16
NONCE_LEN = 16
HMAC_LEN = 32
KEY_LEN = 32  # AES-256


def _ensure():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def _hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _derive_keys(password, salt, iterations=PBKDF2_ITERATIONS):
    """Leitet Encryption-Key + HMAC-Key aus Passwort ab.

    PBKDF2-HMAC-SHA256 mit 600'000 Iterations. Branchen-Standard 2026.
    Returns: (enc_key, mac_key) je 32 Bytes.
    """
    if isinstance(password, str):
        password = password.encode("utf-8")
    derived = hashlib.pbkdf2_hmac("sha256", password, salt, iterations, dklen=64)
    return derived[:32], derived[32:]


def _aes256_ctr_encrypt(plaintext, key, nonce):
    """AES-256-CTR Verschluesselung.

    Nutzt 'cryptography' wenn verfuegbar (production-grade),
    sonst Fallback mit SHA256-basiertem CTR-Mode (nur fuer Notfaelle).
    """
    initial_counter = b"\x00" * 8
    if len(nonce) < 8:
        nonce = nonce.ljust(8, b"\x00")[:8]
    else:
        nonce = nonce[:8]
    iv = nonce + initial_counter

    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        cipher = Cipher(algorithms.AES(key), modes.CTR(iv))
        encryptor = cipher.encryptor()
        return encryptor.update(plaintext) + encryptor.finalize()
    except ImportError:
        return _sha256_ctr_fallback(plaintext, key, nonce)


def _sha256_ctr_fallback(plaintext, key, nonce):
    """SHA256-CTR Fallback (nur Notfall)."""
    out = bytearray()
    counter = 0
    for i in range(0, len(plaintext), 32):
        block_key = hashlib.sha256(key + nonce + counter.to_bytes(4, 'big')).digest()
        for j in range(min(32, len(plaintext) - i)):
            out.append(plaintext[i + j] ^ block_key[j])
        counter += 1
    return bytes(out)


def _aes256_ctr_decrypt(ciphertext, key, nonce):
    """CTR ist symmetrisch: entschluesseln = verschluesseln."""
    return _aes256_ctr_encrypt(ciphertext, key, nonce)


def create(label=None, note=None, password=None):
    """Erstellt ein Backup.

    Wenn password=None: unverschluesseltes ZIP (.zip) — Abwaertskompatibilitaet.
    Wenn password=...: verschluesseltes Backup (.dpbk).

    Liefert (pfad, manifest).
    """
    _ensure()
    stamp = time.strftime("%Y%m%d_%H%M%S")
    use_encryption = bool(password)

    if use_encryption:
        ext = ".dpbk"
    else:
        ext = ".zip"

    name = f"devispro_backup_{stamp}{ext}"
    zpath = os.path.join(BACKUP_DIR, name)

    manifest = {
        "tool": "DevisPro Backup",
        "created": stamp,
        "label": label or "",
        "note": note or "",
        "version": "1.5.0",
        "encrypted": use_encryption,
        "format": FORMAT_VERSION,
        "files": [],
    }

    import io
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for item in SCOPE:
            src = os.path.join(USER_DATA, item)
            if os.path.isfile(src) and os.path.getsize(src) > 0:
                z.write(src, item)
                manifest["files"].append({"path": item, "sha256": _hash(src)})
        for item in BUNDLE_SCOPE:
            src = os.path.join(DATA, item)
            if os.path.isdir(src):
                for f in sorted(os.listdir(src)):
                    fp = os.path.join(src, f)
                    if os.path.isfile(fp):
                        arc = os.path.join(item, f)
                        z.write(fp, arc)
                        manifest["files"].append({"path": arc, "sha256": _hash(fp)})
        z.writestr("MANIFEST.json", json.dumps(manifest, indent=2, ensure_ascii=False))

    zip_bytes = zip_buffer.getvalue()

    if use_encryption:
        salt = os.urandom(SALT_LEN)
        nonce = os.urandom(NONCE_LEN)
        enc_key, mac_key = _derive_keys(password, salt)

        ciphertext = _aes256_ctr_encrypt(zip_bytes, enc_key, nonce)

        header = (
            MAGIC +
            struct.pack("B", FORMAT_VERSION) +
            struct.pack(">I", PBKDF2_ITERATIONS) +
            salt +
            nonce
        )
        mac = hmac.new(mac_key, header + ciphertext, hashlib.sha256).digest()

        with open(zpath, "wb") as f:
            f.write(header)
            f.write(mac)
            f.write(ciphertext)
    else:
        with open(zpath, "wb") as f:
            f.write(zip_bytes)

    return zpath, manifest


def list_backups():
    _ensure()
    out = []
    for f in sorted(os.listdir(BACKUP_DIR)):
        if f.endswith(".zip") or f.endswith(".dpbk"):
            p = os.path.join(BACKUP_DIR, f)
            out.append({
                "name": f,
                "size": os.path.getsize(p),
                "time": os.path.getmtime(p),
                "encrypted": f.endswith(".dpbk"),
            })
    return out


def restore(zpath, target_data=None, password=None):
    """Stellt ein Backup wieder her.

    Wenn zpath eine .dpbk-Datei: password ist erforderlich.
    """
    dst = target_data or USER_DATA
    os.makedirs(dst, exist_ok=True)

    is_encrypted = zpath.endswith(".dpbk")
    if is_encrypted and not password:
        raise ValueError("Passwort erforderlich fuer verschluesseltes Backup")

    with open(zpath, "rb") as f:
        file_bytes = f.read()

    if is_encrypted:
        if file_bytes[:4] != MAGIC:
            raise ValueError("Ungueltiges Backup-Format")
        version = struct.unpack("B", file_bytes[4:5])[0]
        if version != FORMAT_VERSION:
            raise ValueError(f"Nicht unterstuetzte Backup-Version: {version}")
        iterations = struct.unpack(">I", file_bytes[5:9])[0]
        salt = file_bytes[9:9 + SALT_LEN]
        nonce = file_bytes[9 + SALT_LEN:9 + SALT_LEN + NONCE_LEN]
        mac = file_bytes[9 + SALT_LEN + NONCE_LEN:9 + SALT_LEN + NONCE_LEN + HMAC_LEN]
        ciphertext = file_bytes[9 + SALT_LEN + NONCE_LEN + HMAC_LEN:]

        enc_key, mac_key = _derive_keys(password, salt, iterations)
        expected_mac = hmac.new(
            mac_key,
            MAGIC + struct.pack("B", version) + struct.pack(">I", iterations) + salt + nonce + ciphertext,
            hashlib.sha256
        ).digest()
        if not hmac.compare_digest(mac, expected_mac):
            raise ValueError("HMAC-Verifikation fehlgeschlagen — Passwort falsch oder Backup beschaedigt")

        zip_bytes = _aes256_ctr_decrypt(ciphertext, enc_key, nonce)
    else:
        zip_bytes = file_bytes

    import io
    n = 0
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
        for info in z.infolist():
            if info.filename == "MANIFEST.json":
                continue
            z.extract(info, dst)
            n += 1
    return n


def verify(zpath, password=None):
    """Prueft Backup-Integritaet (Hashes + optional HMAC)."""
    with open(zpath, "rb") as f:
        file_bytes = f.read()

    is_encrypted = zpath.endswith(".dpbk")
    if is_encrypted:
        if not password:
            return False, "Passwort erforderlich"
        if file_bytes[:4] != MAGIC:
            return False, "Ungueltiges Format"
        version = struct.unpack("B", file_bytes[4:5])[0]
        iterations = struct.unpack(">I", file_bytes[5:9])[0]
        salt = file_bytes[9:9 + SALT_LEN]
        nonce = file_bytes[9 + SALT_LEN:9 + SALT_LEN + NONCE_LEN]
        mac = file_bytes[9 + SALT_LEN + NONCE_LEN:9 + SALT_LEN + NONCE_LEN + HMAC_LEN]
        ciphertext = file_bytes[9 + SALT_LEN + NONCE_LEN + HMAC_LEN:]
        enc_key, mac_key = _derive_keys(password, salt, iterations)
        expected_mac = hmac.new(
            mac_key,
            MAGIC + struct.pack("B", version) + struct.pack(">I", iterations) + salt + nonce + ciphertext,
            hashlib.sha256
        ).digest()
        if not hmac.compare_digest(mac, expected_mac):
            return False, "HMAC mismatch"
        zip_bytes = _aes256_ctr_decrypt(ciphertext, enc_key, nonce)
    else:
        zip_bytes = file_bytes

    import io
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
        names = set(z.namelist())
        if "MANIFEST.json" not in names:
            return False, "Kein MANIFEST"
        man = json.loads(z.read("MANIFEST.json").decode("utf-8"))
        for entry in man.get("files", []):
            if entry["path"] not in names:
                return False, f"Fehlt: {entry['path']}"
            data = z.read(entry["path"])
            if hashlib.sha256(data).hexdigest() != entry["sha256"]:
                return False, f"Hash mismatch: {entry['path']}"
    return True, "OK"


def erstellen(label=None, note=None, password=None):
    """GUI-Alias."""
    pfad, _ = create(label=label, note=note, password=password)
    return pfad
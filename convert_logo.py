import os, subprocess
p = "/Users/ferdinandrothlisberger/Downloads/IMG_3220 2.JPG"
print("Datei existiert:", os.path.exists(p))
if os.path.exists(p):
    print("Groesse:", os.path.getsize(p), "bytes")
    # versuche mit sips (macos built-in) nach png zu konvertieren
    out = "/Users/ferdinandrothlisberger/devis-auto/devispro/logo.png"
    r = subprocess.run(["sips","-s","format","png",p,"--out",out], capture_output=True, text=True, timeout=30)
    print("sips rc:", r.returncode)
    if r.returncode == 0 and os.path.exists(out):
        print("PNG erstellt:", os.path.getsize(out), "bytes")
    else:
        print("sips fehler:", r.stderr[:200])

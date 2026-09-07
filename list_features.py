import os, re
ROOT="/Users/ferdinandrothlisberger/devis-auto/devispro"
# alle .py in devispro rekursiv, suche export/chat/agent funktionen
for dp,_,fs in os.walk(ROOT):
    for f in fs:
        if not f.endswith(".py"): continue
        p=os.path.join(dp,f)
        try:
            t=open(p,encoding="utf-8",errors="ignore").read()
        except Exception:
            continue
        for m in re.finditer(r"^(def|class)\s+([A-Za-z_][A-Za-z0-9_]*).*", t, re.M):
            name=m.group(2)
            if any(k in name.lower() for k in ["export","chat","agent","fibu","buchhalt","setup","offer","bepreis","save","load","list"]):
                rel=os.path.relpath(p,ROOT)
                print(f"{rel}: {name}")

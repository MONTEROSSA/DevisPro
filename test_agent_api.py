import re
t = open("/Users/ferdinandrothlisberger/devis-auto/devispro/agent.py", encoding="utf-8").read()
for m in re.finditer(r"^(def|class)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\):", t, re.M):
    print(f"{m.group(1)} {m.group(2)}({m.group(3)})")
# wie wird devis gesetzt?
for m in re.finditer(r"set_devis|self\.devis\s*=|def chat", t):
    s = max(0, m.start()-40)
    print("...", t[s:m.end()+60].replace("\n"," "))

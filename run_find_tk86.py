import subprocess
code = open("/Users/ferdinandrothlisberger/devis-auto/find_tk86.py").read()
r = subprocess.run(["python3","-c",code], capture_output=True, text=True, timeout=90, cwd="/Users/ferdinandrothlisberger/devis-auto")
print(r.stdout.strip())
print("ERR:", r.stderr.strip()[:200])

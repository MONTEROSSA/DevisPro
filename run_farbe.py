import subprocess, os
r = subprocess.run(["python3","test_farbe2.py"], cwd="/Users/ferdinandrothlisberger/devis-auto",
                   capture_output=True, text=True, timeout=15)
print("STDOUT:", r.stdout.strip())
print("RC:", r.returncode)

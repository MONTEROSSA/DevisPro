import subprocess, sys, time, os, shutil

# debug app von SHGN7 bundle starten (gleicher code, mit prints)
RES = "/Volumes/SHGN7/DevisPro.app/Contents/Resources"
# kopie der app_gui nach /tmp mit prints
import shutil
src = os.path.join(RES, "devispro", "app_gui.py")
dbg = "/tmp/app_gui_debug_run.py"
shutil.copy(src, dbg)

p = subprocess.Popen([sys.executable, "-u", dbg], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
lines = []
start = time.time()
while time.time() - start < 5:
    line = p.stdout.readline()
    if line:
        lines.append(line.rstrip())
    if len(lines) > 20:
        break
p.terminate()
print("=== DEBUG OUTPUT ===")
for l in lines:
    print(l)
if not lines:
    print("(keine ausgabe - app crasht vor erstem print oder blockiert)")

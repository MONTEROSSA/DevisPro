import subprocess, sys, time

LAUNCH = "/Volumes/SHGN7/DevisPro.app/Contents/MacOS/DevisPro"
# wir kopieren erst den neuen launcher auf shgn7
import shutil
src = "/Users/ferdinandrothlisberger/devis-auto/DevisPro.app/Contents/MacOS/DevisPro"
dst = "/Volumes/SHGN7/DevisPro.app/Contents/MacOS/DevisPro"
shutil.copy(src, dst)
print("Launcher auf SHGN7 kopiert")

p = subprocess.Popen([dst], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
time.sleep(6)
alive = p.poll() is None
print("Lebt:", alive)
if alive:
    # fenster ueber osascript (window server)
    try:
        wid = subprocess.run(["osascript","-e",'tell application "System Events" to get id of first window of (first process whose name is "Python")'],
            capture_output=True, text=True, timeout=8).stdout.strip()
        print("Fenster-ID (window server):", wid or "(KEIN FENSTER)")
        title = subprocess.run(["osascript","-e",'tell application "System Events" to get title of first window of (first process whose name is "Python")'],
            capture_output=True, text=True, timeout=8).stdout.strip()
        print("Fenster-Titel:", title or "(keiner)")
    except Exception as e:
        print("osascript fehler:", e)
    p.terminate()
else:
    out, err = p.communicate(timeout=4)
    print("CRASH:", err[:2000])

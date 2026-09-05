import os, subprocess
uv_py = "/Users/ferdinandrothlisberger/.local/share/uv/python/cpython-3.11.15-macos-aarch64-none/bin/python3"
print("uv python existiert:", os.path.exists(uv_py))
# groesse des uv python verzeichnisses
base = "/Users/ferdinandrothlisberger/.local/share/uv/python/cpython-3.11.15-macos-aarch64-none"
r = subprocess.run(["du","-sh",base], capture_output=True, text=True)
print("uv python groesse:", r.stdout.strip())
# tk version
try:
    v = subprocess.run([uv_py,"-c","import tkinter as tk; r=tk.Tk(); print(r.tk.call('info','patchlevel')); r.destroy()"],
                       capture_output=True, text=True, timeout=10).stdout.strip()
    print("uv python tk:", v)
except Exception as e:
    print("fehler:", e)
# tcl/tk libs vorhanden?
tcl = os.path.join(base, "lib", "tcl9.0")
tk = os.path.join(base, "lib", "tk9.0")
print("tcl9.0 dir:", os.path.isdir(tcl))
print("tk9.0 dir:", os.path.isdir(tk))

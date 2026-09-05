import os, subprocess
venv = "/Users/ferdinandrothlisberger/.hermes/hermes-agent/venv"
py = os.path.join(venv, "bin", "python3")
print("venv python:", py, "existiert:", os.path.exists(py))
# tk _tk.so location
r = subprocess.run([py,"-c","import tkinter, _tkinter; print(_tkinter.__file__)"],
                  capture_output=True, text=True)
print("tk .so:", r.stdout.strip() or r.stderr.strip())
# tcl/tk framework
r2 = subprocess.run([py,"-c","import tkinter; r=tkinter.Tk(); print(r.tk.eval('info library')); r.destroy()"],
                   capture_output=True, text=True)
print("tcl library:", r2.stdout.strip())
# groesse des venv
r3 = subprocess.run(["du","-sh",venv], capture_output=True, text=True)
print("venv groesse:", r3.stdout.strip())

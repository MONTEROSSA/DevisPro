try:
    import tkinter
    print("tkinter OK", tkinter.TkVersion)
except Exception as e:
    print("tkinter FEHLT:", e)
import sys
print("python", sys.version)

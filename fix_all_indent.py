# Vollständige Indentation-Reparatur für app_gui.py
# Führt alle Fixes in EINEM Durchgang aus

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'r') as f:
    lines = f.readlines()

def fix_line(idx, target_spaces):
    """Setzt führende Leerzeichen auf target_spaces."""
    if idx < len(lines):
        lines[idx] = ' ' * target_spaces + lines[idx].lstrip()

# ===== _build_mehr METHOD BODY (sollte 12 spaces = 3 tabs) =====
# card calls at line 538, 541, 544 (1-indexed)
fix_line(537, 12)   # line 538: card(2, 2, "Team & Sync"
fix_line(540, 12)   # line 541: card(3, 0, "Anbieter-Konsole"
fix_line(543, 12)   # line 544: card(3, 1, "Anleitung"

# Continuation lines (21 spaces)
for i in [538, 539, 541, 542, 544, 545]:
    fix_line(i, 21)

# ===== CLASS LEVEL (8 spaces = 2 tabs) =====
# Comment block lines 548-550
fix_line(547, 8)    # line 548: # ---
fix_line(548, 8)    # line 549: # BEREICH 5
fix_line(549, 8)    # line 550: # ---

# Method definition _build_analysen (class method = 8 spaces)
fix_line(550, 8)    # line 551: def _build_analysen

# Method body (12 spaces = 3 tabs)
fix_line(551, 12)   # line 552: info = ctk.CTkFrame
fix_line(552, 12)   # line 553: info.pack
fix_line(553, 12)   # line 554: ctk.CTkLabel
fix_line(554, 21)   # line 555: text=...
fix_line(555, 21)   # line 556: "Verwalten Sie...
fix_line(556, 21)   # line 557: "Drag & Drop...
fix_line(557, 21)   # line 558: font=FONT...
fix_line(558, 21)   # line 559: anchor="w"...

# Rest der Methode: alle body-lines auf 12, continuations auf 21
# Wir fixen systematisch: jede Zeile die mit ctk. oder ctk.CTkLabel etc. beginnt
for i in range(559, min(580, len(lines))):
    stripped = lines[i].lstrip()
    if stripped.startswith(('ctk.', 'ctk.CTk', 'accent_button', 'blue_button', 'ghost_button', 
                           'red_button', 'btn_frame', 'left.', 'right.', 'self.', '#', 
                           'c =', 'r =', 'v =', 'if ', 'else:', 'for ', 'def ', 'return')):
        # Prüfen ob continuation (lange Zeile mit .pack, .grid, etc. am Ende vorher)
        prev = lines[i-1].rstrip() if i > 0 else ''
        if prev.endswith(('(', ',', '\\', '+')):
            fix_line(i, 21)
        else:
            fix_line(i, 12)

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'w') as f:
    f.writelines(lines)

print("✅ Indentation fix complete - running syntax check...")
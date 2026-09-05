with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'r') as f:
    lines = f.readlines()

# Fix lines 544-546 (0-indexed: 543, 544, 545)
# They currently have 29 leading spaces, should have 12
# Line 544:         card(3, 1, "\U0001f4d6 Anleitung",
# Line 545:                              "Vollst\u00e4ndige Bedienungsanleitung (Preise, Devis, Rechnung, ERP) im Browser.",
# Line 546:                              self._anleitung_ui, "steelblue.TButton")

# Fix them to have 12 spaces (inside _build_mehr method)
if len(lines) > 545:
    # Line 544 (index 543)
    lines[543] = '            ' + lines[543].lstrip() + '\n'
    # Line 545 (index 544)
    lines[544] = '            ' + lines[544].lstrip() + '\n'
    # Line 546 (index 545)
    lines[545] = '            ' + lines[545].lstrip() + '\n'
    
    with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'w') as f:
        f.writelines(lines)
    print("Fixed indentation lines 544-546")
else:
    print("File too short")
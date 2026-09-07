import re

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'r') as f:
    content = f.read()

# Fix the indentation issue: lines 544-546 have wrong indentation (29 spaces instead of 12)
# Pattern: the card(3,1) call and its continuation lines
content = re.sub(
    r'^        card\(3, 1, \"\\\\U0001f4d6 Anleitung\",\n\s+\"Vollst\\\\u00e4ndige Bedienungsanleitung \(Preise, Devis, Rechnung, ERP\) im Browser\.\",\n\s+self\._anleitung_ui, \"steelblue\.TButton\"\)',
    '            card(3, 1, "\\U0001f4d6 Anleitung",\n                     "Vollst\u00e4ndige Bedienungsanleitung (Preise, Devis, Rechnung, ERP) im Browser.",\n                     self._anleitung_ui, "steelblue.TButton")',
    content,
    flags=re.MULTILINE
)

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'w') as f:
    f.write(content)

print("Fixed indentation")
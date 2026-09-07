with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'r') as f:
    lines = f.readlines()

# Fix multiple indentation issues at once
# Index: line number - 1

# Line 538 (idx 537): '        card(2, 2' - 8 spaces -> needs 12
lines[537] = '    ' + lines[537]

# Line 541 (idx 540): '               card(3, 0' - 15 spaces -> needs 12 (remove 3)
lines[540] = lines[540][3:]

# Line 544 (idx 543): '           card(3, 1' - 11 spaces -> needs 12 (add 1)
lines[543] = ' ' + lines[543]

# Line 553 (idx 552): '                info.pack' - 16 spaces -> needs 12 (remove 4)
lines[552] = lines[552][4:]

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'w') as f:
    f.writelines(lines)
print("Fixed indentation lines 538, 541, 544, 553")
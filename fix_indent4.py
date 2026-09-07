with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'r') as f:
    lines = f.readlines()

# Fix lines 540-552 (0-indexed 540-551)
# Current state:
# 540: '        card(2, 2' - 8 spaces (inside _build_mehr) - WRONG, should be 12
# 541: '            card(3, 0' - 11 spaces - should be 12
# 542: '                    ' - 20 spaces - OK
# 543: '                    ' - 20 spaces - OK
# 544: '            card(3, 1' - 11 spaces - should be 12
# 545: '                    ' - 20 spaces - OK
# 546: '                    ' - 20 spaces - OK
# 547: empty
# 548: '        # comment' - 8 spaces - CORRECT (class level)
# 549: '        # comment' - 8 spaces - CORRECT
# 550: '        # comment' - 8 spaces - CORRECT
# 551: '        def _build_analysen' - 8 spaces - CORRECT (class method)
# 552: '                info = ' - 16 spaces - WRONG, should be 12 (method body)

# The issue: _build_mehr method body should be 12 spaces, but line 540 has 8 spaces
# And _build_analysen body should be 12 spaces, but line 552 has 16

# Fix:
# Line 540 (idx 540): card(2,2) - add 4 spaces to make 12
lines[540] = '    ' + lines[540]  # 8+4=12
# Line 541 (idx 541): card(3,0) - add 1 space to make 12
lines[541] = ' ' + lines[541]  # 11+1=12
# Line 544 (idx 544): card(3,1) - add 1 space to make 12
lines[544] = ' ' + lines[544]  # 11+1=12
# Line 552 (idx 551): method body - remove 4 spaces to make 12
lines[551] = lines[551][4:]  # 16-4=12

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'w') as f:
    f.writelines(lines)
print("Fixed indentation")
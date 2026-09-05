with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'r') as f:
    lines = f.readlines()

# Fix lines 541-550 (0-indexed 540-549)
# The structure should be:
# Line 541:         card(3, 0, ...) - 12 spaces
# Line 542:                     ... - 21 spaces (continuation)
# Line 543:                     ... - 21 spaces
# Line 544:         card(3, 1, ...) - 12 spaces
# Line 545:                     ... - 21 spaces
# Line 546:                     ... - 21 spaces
# Line 547: (empty)
# Line 548:             # comment - 12 spaces
# Line 549:             # comment - 12 spaces
# Line 550:             # comment - 12 spaces
# Line 551:             def _build_analysen - 12 spaces (but this is a CLASS METHOD, should be 8 spaces!)

# The issue: _build_analysen is a CLASS METHOD, not inside _build_mehr!
# It should be at 8 spaces (one level in class), not 12.

# Let me check the class structure first - find where _build_mehr ends
# _build_mehr starts around line 487, ends before _build_analysen

# Actually, looking at the pattern, _build_mehr is one method, _build_analysen is another method at class level.
# So _build_analysen should have 8 spaces (4 for class + 4 for method).

# Fix lines 540-551:
# 540:        card(2, 2, ... - 12 spaces (inside _build_mehr)
# 541:        card(3, 0, ... - 12 spaces (inside _build_mehr)
# 542:                    ... - 21 spaces
# 543:                    ... - 21 spaces
# 544:        card(3, 1, ... - 12 spaces (inside _build_mehr)
# 545:                    ... - 21 spaces
# 546:                    ... - 21 spaces
# 547: (empty)
# 548:            # comment - 12 spaces (but this is OUTSIDE _build_mehr!)
# 549:            # comment - 12 spaces
# 550:            # comment - 12 spaces
# 551:            def _build_analysen - 12 spaces (WRONG! should be 8 spaces for class method)

# The problem: the comment block and _build_analysen are at wrong indentation.
# They should be at CLASS LEVEL (8 spaces), not inside _build_mehr (12 spaces).

# Let me find where _build_mehr actually ends. It should end before the comment block.
# Looking at the code, _build_mehr builds a grid of cards. The last card is card(3,1).
# Then _build_mehr should end, and _build_analysen starts at class level.

# Current state:
# Line 541 (index 540): 8 spaces + 'card(3, 0' - WRONG, should be 12
# Line 542 (index 541): 21 spaces continuation
# Line 543 (index 542): 21 spaces continuation
# Line 544 (index 543): 16 spaces + 'card(3, 1' - WRONG, should be 12
# Line 545 (index 544): 21 spaces
# Line 546 (index 545): 21 spaces
# Line 547 (index 546): empty
# Line 548 (index 547): 12 spaces comment - should be 8
# Line 549 (index 548): 12 spaces comment - should be 8
# Line 550 (index 549): 12 spaces comment - should be 8
# Line 551 (index 550): 12 spaces def - should be 8

# The fix: 
# - Lines 541-546: inside _build_mehr, 12 spaces for card calls, 21 for continuations
# - Lines 548-551: at class level, 8 spaces

# Let me count actual spaces in current file:
# Line 541 (idx 540): '        card(3, 0' = 8 spaces - NEEDS 12
# Line 542 (idx 541): '                    ' = 20 spaces - OK for continuation
# Line 543 (idx 542): '                    ' = 20 spaces - OK
# Line 544 (idx 543): '                card(3, 1' = 16 spaces - NEEDS 12
# Line 545 (idx 544): '                    ' = 20 spaces - OK
# Line 546 (idx 545): '                    ' = 20 spaces - OK
# Line 548 (idx 547): '            # ' = 12 spaces - NEEDS 8
# Line 549 (idx 548): '            # ' = 12 spaces - NEEDS 8
# Line 550 (idx 549): '            # ' = 12 spaces - NEEDS 8
# Line 551 (idx 550): '            def _build_analysen' = 12 spaces - NEEDS 8

# Fix:
lines[540] = '            ' + lines[540].lstrip()  # 12 spaces
lines[543] = '            ' + lines[543].lstrip()  # 12 spaces
lines[547] = '        ' + lines[547].lstrip()      # 8 spaces
lines[548] = '        ' + lines[548].lstrip()      # 8 spaces
lines[549] = '        ' + lines[549].lstrip()      # 8 spaces
lines[550] = '        ' + lines[550].lstrip()      # 8 spaces

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'w') as f:
    f.writelines(lines)
print("Fixed indentation for _build_mehr end and _build_analysen start")
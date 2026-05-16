#!/usr/bin/env python3
"""Find unclosed docstrings by counting triple quotes."""

import re

file_path = r'd:\repos\ITL.ControlPanel.SDK\src\itl_controlplane_sdk\providers\base\provider.py'

with open(file_path, 'r') as f:
    lines = f.readlines()

triple_quote_lines = []
open_count = 0
current_block_start = None

for i, line in enumerate(lines, 1):
    matches = len(re.findall(r'"""', line))
    
    if matches > 0:
        triple_quote_lines.append((i, line.strip(), matches))
        open_count += matches
        
        if open_count % 2 == 1:  # Opening
            if current_block_start is None:
                current_block_start = i
        else:  # Closing
            current_block_start = None

print("Triple-quoted strings found:")
for line_num, content, count in triple_quote_lines[-30:]:  # Last 30
    print(f"  Line {line_num:4d} ({count}x): {content[:60]}")

if open_count % 2 == 1:
    print(f"\n⚠️  Found unclosed docstring!")
    print(f"  Open count: {open_count} (should be even)")
    
    # Find where it started
    for i in range(len(triple_quote_lines)-1, -1, -1):
        _sum = sum(c for _, _, c in triple_quote_lines[:i+1])
        if _sum % 2 == 1:
            print(f"  Last unclosed block started at line {triple_quote_lines[i][0]}")
            break
else:
    print("\n✓ All docstrings are properly closed")

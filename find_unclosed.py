#!/usr/bin/env python3
"""Find the exact unclosed docstring."""

import re

file_path = r'd:\repos\ITL.ControlPanel.SDK\src\itl_controlplane_sdk\providers\base\provider.py'

with open(file_path, 'r') as f:
    lines = f.readlines()

in_docstring = False
docstring_start = None

for i, line in enumerate(lines, 1):
    matches = re.findall(r'"""', line)
    
    for match in matches:
        if not in_docstring:
            in_docstring = True
            docstring_start = i
            print(f"Line {i:4d}: Opening docstring")
        else:
            in_docstring = False
            print(f"Line {i:4d}: Closing docstring (started at {docstring_start})")

if in_docstring:
    print(f"\n❌ Unclosed docstring starting at line {docstring_start}")
else:
    print("\n✓ All docstrings properly closed")

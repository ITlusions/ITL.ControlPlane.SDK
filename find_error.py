#!/usr/bin/env python3
"""Find the line with the unclosed docstring."""

import ast
import sys

file_path = r'd:\repos\ITL.ControlPanel.SDK\src\itl_controlplane_sdk\providers\base\provider.py'

try:
    with open(file_path, 'r') as f:
        code = f.read()
    
    ast.parse(code)
    print("✓ File parses successfully")
    
except SyntaxError as e:
    print(f"❌ Syntax Error: {e}")
    print(f"\nFile: {e.filename}")
    print(f"Line {e.lineno}: {e.text}")
    print(f"Offset: {' ' * (e.offset - 1) if e.offset else ''}^")
    print(f"\nProblem: {e.msg}")
    
    # Print context around the error
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    start = max(0, e.lineno - 10)
    end = min(len(lines), e.lineno + 5)
    
    print(f"\n--- Context (lines {start+1}-{end}) ---")
    for i in range(start, end):
        marker = ">>>" if i == e.lineno - 1 else "   "
        print(f"{marker} {i+1:4d}: {lines[i]}", end='')

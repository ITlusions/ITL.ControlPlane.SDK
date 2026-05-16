#!/usr/bin/env python3
"""Debug the docstring structure around the error."""

file_path = r'd:\repos\ITL.ControlPanel.SDK\src\itl_controlplane_sdk\providers\base\provider.py'

with open(file_path, 'rb') as f:
    content = f.read()

# Find the last 200 bytes
last_200 = content[-200:]
print("Last 200 bytes (hex):")
print(last_200.hex())
print("\nLast 200 bytes (as text with repr):")
print(repr(last_200.decode('utf-8')))

# Count triple quotes in last 500 bytes
last_500 = content[-500:].decode('utf-8')
count = last_500.count('"""')
print(f"\nTriple quotes in last 500 bytes: {count}")

# Show last 30 lines with line numbers
lines = content.decode('utf-8').split('\n')
print(f"\nTotal lines: {len(lines)}")
print("\nLast 30 lines:")
start = max(0, len(lines) - 30)
for i in range(start, len(lines)):
    line = lines[i]
    print(f"{i+1:4d}: {repr(line[:80])}")

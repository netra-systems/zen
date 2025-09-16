#!/usr/bin/env python3
"""Test script to reproduce infrastructure.vpc_connectivity_fix ImportError"""

import sys
import traceback

print("=== Python Environment Analysis ===")
print(f"Python version: {sys.version}")
print(f"Current working directory: {sys.path[0] if sys.path else 'N/A'}")
print("\nPython path:")
for i, path in enumerate(sys.path):
    print(f"  {i}: {path}")

print("\n=== Testing Import ===")
try:
    import infrastructure.vpc_connectivity_fix
    print("SUCCESS: infrastructure.vpc_connectivity_fix imported successfully")
except ImportError as e:
    print(f"IMPORT ERROR: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
except Exception as e:
    print(f"OTHER ERROR: {e}")
    print("\nFull traceback:")
    traceback.print_exc()

print("\n=== Directory Structure Check ===")
import os
if os.path.exists("infrastructure"):
    print("infrastructure/ directory exists")
    if os.path.exists("infrastructure/__init__.py"):
        print("infrastructure/__init__.py exists")
    else:
        print("infrastructure/__init__.py MISSING")

    if os.path.exists("infrastructure/vpc_connectivity_fix.py"):
        print("infrastructure/vpc_connectivity_fix.py exists")
        # Check if file is readable
        try:
            with open("infrastructure/vpc_connectivity_fix.py", 'r') as f:
                first_line = f.readline().strip()
                print(f"First line: {first_line}")
        except Exception as e:
            print(f"Cannot read file: {e}")
    else:
        print("infrastructure/vpc_connectivity_fix.py MISSING")
else:
    print("infrastructure/ directory does NOT exist")
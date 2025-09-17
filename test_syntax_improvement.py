#!/usr/bin/env python3
"""Test syntax improvement across critical test directories"""

import os
import subprocess
from pathlib import Path

def check_syntax(file_path):
    """Check if a file has valid Python syntax"""
    try:
        result = subprocess.run(
            ['python', '-m', 'py_compile', str(file_path)],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False

def main():
    critical_dirs = [
        "C:/netra-apex/tests/mission_critical",
        "C:/netra-apex/tests/e2e",
        "C:/netra-apex/test_framework/ssot"
    ]

    total_files = 0
    valid_files = 0
    invalid_files = []

    for directory in critical_dirs:
        if os.path.exists(directory):
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        total_files += 1

                        if check_syntax(file_path):
                            valid_files += 1
                        else:
                            invalid_files.append(file_path)

    print(f"SYNTAX CHECK RESULTS:")
    print(f"Total Python files checked: {total_files}")
    if total_files > 0: print(f"Valid syntax: {valid_files} ({valid_files/total_files*100:.1f}%)"); else: print("No files found")
    print(f"Invalid syntax: {len(invalid_files)} ({len(invalid_files)/total_files*100:.1f}%)")

    if invalid_files and len(invalid_files) <= 20:
        print(f"\nFirst {min(20, len(invalid_files))} files with syntax errors:")
        for file_path in invalid_files[:20]:
            rel_path = file_path.replace("C:/netra-apex/", "")
            print(f"  - {rel_path}")

    return valid_files, total_files

if __name__ == "__main__":
    main()
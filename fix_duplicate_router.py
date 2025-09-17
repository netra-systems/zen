#!/usr/bin/env python3
"""
Script to fix MessageRouter SSOT violation by removing duplicate CanonicalMessageRouter from handlers.py
"""

def fix_duplicate_canonical_message_router():
    """Remove duplicate CanonicalMessageRouter from handlers.py and fix SSOT violation."""

    file_path = 'netra_backend/app/websocket_core/handlers.py'

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find the start and end of the duplicate CanonicalMessageRouter class
    start_line = None
    end_line = None

    for i, line in enumerate(lines):
        if line.strip() == 'class CanonicalMessageRouter:':
            start_line = i
            print(f"Found duplicate CanonicalMessageRouter at line {i + 1}")
        elif start_line is not None and line.strip().startswith('# === SSOT CONSOLIDATED MESSAGE ROUTER ==='):
            end_line = i
            print(f"Found end of duplicate class at line {i + 1}")
            break

    if start_line is None or end_line is None:
        print(f"Could not locate duplicate class boundaries. start_line={start_line}, end_line={end_line}")
        return False

    print(f"Removing lines {start_line + 1} to {end_line}")

    # Remove the duplicate class and replace with import comment
    new_lines = (
        lines[:start_line] +
        [
            "# === SSOT CONSOLIDATED MESSAGE ROUTER ===\n",
            "# Import the CANONICAL CanonicalMessageRouter that serves as the SSOT\n",
            "# This replaces the duplicate implementation that was previously defined here\n",
            "\n"
        ] +
        lines[end_line:]
    )

    # Write the modified file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"Successfully removed duplicate CanonicalMessageRouter from {file_path}")
    print(f"Removed {end_line - start_line} lines")
    return True

if __name__ == '__main__':
    fix_duplicate_canonical_message_router()
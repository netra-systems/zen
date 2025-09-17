#!/usr/bin/env python3
"""
NETRA APEX - Issue #1082 Phase 1 Build Context Cleanup
Critical infrastructure fix to remove cache pollution
Removes 10,861+ .pyc files and 879+ __pycache__ directories
"""

import os
import shutil
import subprocess
import time
from pathlib import Path

def cleanup_python_cache():
    """Remove Python cache files and directories safely"""
    root_dir = Path("C:/GitHub/netra-apex")

    print("CLEANING: Starting Python cache cleanup for Issue #1082...")
    print(f"Root directory: {root_dir}")

    # Count files before cleanup
    pyc_count = 0
    pycache_count = 0

    print("\nCOUNTING: Analyzing cache files...")
    for path in root_dir.rglob("*.pyc"):
        pyc_count += 1

    for path in root_dir.rglob("__pycache__"):
        if path.is_dir():
            pycache_count += 1

    print(f"Found {pyc_count:,} .pyc files")
    print(f"Found {pycache_count:,} __pycache__ directories")

    # Remove .pyc files
    removed_pyc = 0
    print("\nREMOVING: Deleting .pyc files...")
    for path in root_dir.rglob("*.pyc"):
        try:
            path.unlink()
            removed_pyc += 1
            if removed_pyc % 1000 == 0:
                print(f"  Removed {removed_pyc:,} .pyc files...")
        except Exception as e:
            print(f"  Failed to remove {path}: {e}")

    # Remove __pycache__ directories
    removed_pycache = 0
    print("\nREMOVING: Deleting __pycache__ directories...")
    for path in root_dir.rglob("__pycache__"):
        if path.is_dir():
            try:
                shutil.rmtree(path)
                removed_pycache += 1
                if removed_pycache % 100 == 0:
                    print(f"  Removed {removed_pycache:,} __pycache__ directories...")
            except Exception as e:
                print(f"  Failed to remove {path}: {e}")

    # Also clean other cache patterns
    print("\nCLEANING: Additional cache patterns...")
    other_patterns = [
        "*.pyo",
        "*.pyd",
        ".pytest_cache",
        ".coverage",
        ".mypy_cache",
        ".ruff_cache"
    ]

    removed_other = 0
    for pattern in other_patterns:
        for path in root_dir.rglob(pattern):
            try:
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    shutil.rmtree(path)
                removed_other += 1
            except Exception as e:
                print(f"  Failed to remove {path}: {e}")

    # Final count
    final_pyc = sum(1 for _ in root_dir.rglob("*.pyc"))
    final_pycache = sum(1 for p in root_dir.rglob("__pycache__") if p.is_dir())

    print(f"\nSUCCESS: Cleanup complete!")
    print(f"RESULTS: Summary:")
    print(f"  - Removed {removed_pyc:,} .pyc files")
    print(f"  - Removed {removed_pycache:,} __pycache__ directories")
    print(f"  - Removed {removed_other:,} other cache items")
    print(f"  - Remaining .pyc files: {final_pyc:,}")
    print(f"  - Remaining __pycache__ dirs: {final_pycache:,}")

    if final_pyc == 0 and final_pycache == 0:
        print("SUCCESS: Build context is now clean!")
        return True
    else:
        print("WARNING: Some cache files may remain")
        return False

if __name__ == "__main__":
    success = cleanup_python_cache()
    exit(0 if success else 1)
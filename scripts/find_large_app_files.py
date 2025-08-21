#!/usr/bin/env python3
"""Find largest Python files in app/ directory (excluding tests)"""

import glob
import os


def count_lines(file_path):
    """Count lines in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except:
        return 0

def find_large_files():
    """Find Python files in app/ directory over 300 lines (excluding tests)"""
    app_files = []
    
    # Get all Python files in app directory
    pattern = "app/**/*.py"
    for file_path in glob.glob(pattern, recursive=True):
        # Skip test files, backup files, and __pycache__
        if ('test_' in file_path or '/tests/' in file_path or 
            '_backup' in file_path or '_test.' in file_path or 
            '__pycache__' in file_path):
            continue
            
        line_count = count_lines(file_path)
        if line_count > 300:
            app_files.append((line_count, file_path))
    
    # Sort by line count (descending)
    app_files.sort(reverse=True)
    
    print("TOP LARGE APP FILES (>300 lines, excluding tests):")
    print("=" * 60)
    for i, (lines, file_path) in enumerate(app_files[:10]):
        print(f"{i+1:2d}. {lines:4d} lines: {file_path}")
    
    return app_files[:5]  # Return top 5

if __name__ == "__main__":
    find_large_files()
#!/usr/bin/env python3
"""
Quick script to verify that test scanning is excluding site-packages and virtual environments
"""

import sys
from pathlib import Path


def check_test_file_locations():
    """Check if any test files are being counted from excluded directories"""
    
    from scripts.business_value_test_index import BusinessValueTestIndexer
    
    indexer = BusinessValueTestIndexer(project_root)
    indexer.scan_tests()
    
    # Check for files from excluded directories (checking directory names, not file names)
    excluded_indicators = [
        'site-packages', 'dist-packages', '__pycache__', 
        'venv', '.venv', 'node_modules',
        'Lib', 'Scripts', 'Include',  # Windows Python dirs
    ]
    
    problematic_files = []
    for test in indexer.tests:
        path_parts = Path(test.file_path).parts
        for indicator in excluded_indicators:
            # Check if the indicator appears as a directory in the path, not in filename
            if indicator.lower() in [p.lower() for p in path_parts[:-1]]:  # Exclude the filename
                problematic_files.append((test.file_path, indicator))
                break
    
    print(f"Total tests scanned: {len(indexer.tests)}")
    print(f"Tests in excluded directories: {len(problematic_files)}")
    
    if problematic_files:
        print("\nProblematic files found in excluded directories:")
        for file_path, indicator in problematic_files[:10]:  # Show first 10
            print(f"  - {file_path} (matched: {indicator})")
    else:
        print("\nSUCCESS: No tests found in excluded directories (site-packages, venv, etc.)")
    
    # Check test distribution
    test_dirs = {}
    for test in indexer.tests:
        parts = test.file_path.split('/')
        if not parts:
            parts = test.file_path.split('\\')
        
        if parts:
            top_dir = parts[0]
            test_dirs[top_dir] = test_dirs.get(top_dir, 0) + 1
    
    print("\nTest distribution by top-level directory:")
    for dir_name, count in sorted(test_dirs.items(), key=lambda x: x[1], reverse=True):
        print(f"  {dir_name}: {count} tests")

if __name__ == "__main__":
    check_test_file_locations()
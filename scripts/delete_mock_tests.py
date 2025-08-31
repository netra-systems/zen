#!/usr/bin/env python3
"""Delete mock-only integration tests that provide no real integration value."""

import os
import re
from pathlib import Path
from typing import List

def get_mock_only_tests() -> List[Path]:
    """Get list of mock-only test files to delete."""
    
    # Read the audit report
    mock_tests = []
    
    with open('integration_test_audit.txt', 'r') as f:
        lines = f.readlines()
    
    in_mock_section = False
    for line in lines:
        if "MOCK-ONLY TESTS" in line:
            in_mock_section = True
            continue
        elif "MIXED TESTS" in line:
            in_mock_section = False
            break
        
        if in_mock_section and line.strip() and not line.startswith("  "):
            # This is a file path
            file_path = line.strip()
            if file_path and os.path.exists(file_path):
                mock_tests.append(Path(file_path))
    
    return mock_tests

def main():
    """Main function to delete mock-only tests."""
    
    mock_tests = get_mock_only_tests()
    
    print(f"Found {len(mock_tests)} mock-only integration tests to delete")
    print()
    
    # Show first 10 for confirmation
    print("Files to delete (first 10):")
    for path in mock_tests[:10]:
        print(f"  - {path}")
    
    if len(mock_tests) > 10:
        print(f"  ... and {len(mock_tests) - 10} more")
    
    print()
    response = input("Delete these mock-only tests? (y/n): ")
    
    if response.lower() == 'y':
        deleted_count = 0
        errors = []
        
        for path in mock_tests:
            try:
                os.remove(path)
                deleted_count += 1
                print(f"Deleted: {path}")
            except Exception as e:
                errors.append((path, str(e)))
        
        print()
        print(f"Successfully deleted {deleted_count} files")
        
        if errors:
            print(f"Errors deleting {len(errors)} files:")
            for path, error in errors[:5]:
                print(f"  {path}: {error}")
    else:
        print("Deletion cancelled")

if __name__ == "__main__":
    main()
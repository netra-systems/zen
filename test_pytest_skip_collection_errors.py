#!/usr/bin/env python3
"""
Test script to demonstrate pytest.skip collection errors in Issue #636.

This script identifies all pytest.skip calls that lack allow_module_level=True
and demonstrates the collection errors they cause.
"""

import subprocess
import sys
import os
import re
from pathlib import Path

def find_problematic_pytest_skip_calls():
    """Find all pytest.skip calls without allow_module_level=True parameter."""
    print("🔍 Scanning for problematic pytest.skip calls...")
    
    # Search pattern for pytest.skip calls without allow_module_level=True
    test_dir = Path("netra_backend/tests/unit")
    problematic_files = []
    
    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return []
    
    # Use grep to find the pattern
    try:
        result = subprocess.run([
            "grep", "-r", "-n", "--include=*.py",
            r"^[^#]*pytest\.skip\([^,]*\)$",
            str(test_dir)
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line:
                    file_path, line_num, content = line.split(':', 2)
                    problematic_files.append({
                        'file': file_path,
                        'line': int(line_num),
                        'content': content.strip()
                    })
    except Exception as e:
        print(f"❌ Error searching for pytest.skip patterns: {e}")
        return []
    
    return problematic_files

def test_collection_for_file(file_path):
    """Test if a specific file can be collected by pytest."""
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", "--collect-only", file_path
        ], capture_output=True, text=True, cwd=".")
        
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    except Exception as e:
        return {
            'success': False,
            'stdout': '',
            'stderr': f"Exception: {e}"
        }

def main():
    """Main test execution."""
    print("=" * 80)
    print("🧪 PYTEST.SKIP COLLECTION ERROR REPRODUCTION TEST - Issue #636")
    print("=" * 80)
    
    # Find all problematic pytest.skip calls
    problematic_files = find_problematic_pytest_skip_calls()
    
    if not problematic_files:
        print("✅ No problematic pytest.skip calls found!")
        return 0
    
    print(f"\n📊 Found {len(problematic_files)} problematic pytest.skip calls:")
    print("-" * 60)
    
    collection_errors = []
    
    for item in problematic_files:
        print(f"\n📁 File: {item['file']} (line {item['line']})")
        print(f"📝 Content: {item['content']}")
        
        # Test collection for this file
        collection_result = test_collection_for_file(item['file'])
        
        if not collection_result['success']:
            collection_errors.append({
                'file': item['file'],
                'error': collection_result['stderr']
            })
            print(f"❌ Collection FAILED")
            if "allow_module_level" in collection_result['stderr']:
                print(f"🎯 CONFIRMED: Missing allow_module_level=True parameter")
        else:
            print(f"✅ Collection OK (may be in try/except block)")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 COLLECTION ERROR SUMMARY")
    print("=" * 80)
    print(f"Total problematic pytest.skip calls: {len(problematic_files)}")
    print(f"Files with collection errors: {len(collection_errors)}")
    
    if collection_errors:
        print("\n🚨 FILES WITH COLLECTION ERRORS:")
        for error in collection_errors:
            print(f"  ❌ {error['file']}")
            # Show relevant error lines
            error_lines = [line for line in error['error'].split('\n') 
                          if 'allow_module_level' in line or 'pytest.skip' in line]
            for line in error_lines[:2]:  # Show first 2 relevant lines
                print(f"     {line.strip()}")
        
        print(f"\n🎯 REPRODUCTION CONFIRMED: {len(collection_errors)} files have pytest.skip collection errors")
        return 1
    else:
        print("\n✅ All files collect successfully (pytest.skip calls may be in try/except blocks)")
        return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
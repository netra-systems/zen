#!/usr/bin/env python3
"""
Comprehensive fix script for pytest.skip collection errors in Issue #636.

This script automatically adds allow_module_level=True to all pytest.skip calls
that lack this parameter, ensuring proper test collection behavior.
"""

import re
import os
from pathlib import Path
import subprocess

def find_files_with_pytest_skip():
    """Find all files containing pytest.skip calls without allow_module_level=True."""
    print("🔍 Finding files with pytest.skip calls...")
    
    test_dir = Path("netra_backend/tests/unit")
    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return []
    
    try:
        # Find files with pytest.skip calls that don't have allow_module_level=True
        result = subprocess.run([
            "grep", "-r", "-l", "--include=*.py",
            r"pytest\.skip\(",
            str(test_dir)
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
            
            # Filter to only files that have pytest.skip without allow_module_level=True
            problematic_files = []
            for file_path in files:
                if has_problematic_pytest_skip(file_path):
                    problematic_files.append(file_path)
            
            return problematic_files
        
    except Exception as e:
        print(f"❌ Error searching for files: {e}")
    
    return []

def has_problematic_pytest_skip(file_path):
    """Check if a file has pytest.skip calls without allow_module_level=True."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for pytest.skip patterns that don't have allow_module_level=True
        skip_pattern = r'pytest\.skip\s*\([^)]*\)'
        matches = re.findall(skip_pattern, content)
        
        for match in matches:
            if 'allow_module_level=True' not in match:
                return True
        
        return False
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return False

def fix_pytest_skip_in_file(file_path):
    """Fix pytest.skip calls in a specific file by adding allow_module_level=True."""
    print(f"🔧 Fixing {file_path}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to match pytest.skip calls without allow_module_level=True
        # This pattern captures the pytest.skip call and its parameters
        pattern = r'(pytest\.skip\s*\(\s*(?:[^,)]+(?:\s*,\s*[^,)]+)*)\s*\))'
        
        def replace_skip_call(match):
            original_call = match.group(1)
            
            # Skip if already has allow_module_level
            if 'allow_module_level' in original_call:
                return original_call
            
            # Add allow_module_level=True parameter
            # Find the closing parenthesis and insert the parameter before it
            if original_call.endswith(')'):
                # Remove the closing parenthesis
                without_closing = original_call[:-1]
                
                # Check if there are existing parameters (look for content after opening parenthesis)
                paren_content = without_closing[without_closing.find('(') + 1:].strip()
                
                if paren_content:
                    # There are existing parameters, add a comma
                    return without_closing + ', allow_module_level=True)'
                else:
                    # No existing parameters, add directly
                    return without_closing + 'allow_module_level=True)'
            
            return original_call
        
        # Apply the fix
        new_content = re.sub(pattern, replace_skip_call, content)
        
        # Check if any changes were made
        if new_content != content:
            # Write the fixed content back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"  ✅ Fixed pytest.skip calls in {file_path}")
            return True
        else:
            print(f"  ℹ️  No changes needed in {file_path}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error fixing {file_path}: {e}")
        return False

def validate_fix(file_path):
    """Validate that the fix was applied correctly."""
    try:
        result = subprocess.run([
            "python3", "-m", "pytest", "--collect-only", file_path
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            print(f"  ✅ Collection test passed for {file_path}")
            return True
        else:
            if "allow_module_level" in result.stderr:
                print(f"  ❌ Still has allow_module_level issue: {file_path}")
            else:
                print(f"  ⚠️  Other collection issue in {file_path}: {result.stderr[:100]}...")
            return False
            
    except Exception as e:
        print(f"  ❌ Error validating {file_path}: {e}")
        return False

def main():
    """Main remediation execution."""
    print("=" * 80)
    print("🔧 PYTEST.SKIP COLLECTION ERROR REMEDIATION - Issue #636")
    print("=" * 80)
    
    # Find all files with problematic pytest.skip calls
    problematic_files = find_files_with_pytest_skip()
    
    if not problematic_files:
        print("✅ No files with problematic pytest.skip calls found!")
        return 0
    
    print(f"\n📊 Found {len(problematic_files)} files to fix:")
    for file_path in problematic_files:
        print(f"  📁 {file_path}")
    
    print("\n" + "=" * 80)
    print("🔧 APPLYING FIXES")
    print("=" * 80)
    
    fixed_files = []
    failed_files = []
    
    for file_path in problematic_files:
        if fix_pytest_skip_in_file(file_path):
            fixed_files.append(file_path)
        else:
            failed_files.append(file_path)
    
    print("\n" + "=" * 80)
    print("🧪 VALIDATING FIXES")
    print("=" * 80)
    
    validation_passed = []
    validation_failed = []
    
    for file_path in fixed_files:
        if validate_fix(file_path):
            validation_passed.append(file_path)
        else:
            validation_failed.append(file_path)
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 REMEDIATION SUMMARY")
    print("=" * 80)
    print(f"Files found with issues: {len(problematic_files)}")
    print(f"Files successfully fixed: {len(fixed_files)}")
    print(f"Files failed to fix: {len(failed_files)}")
    print(f"Validation passed: {len(validation_passed)}")
    print(f"Validation failed: {len(validation_failed)}")
    
    if failed_files:
        print("\n🚨 FAILED TO FIX:")
        for file_path in failed_files:
            print(f"  ❌ {file_path}")
    
    if validation_failed:
        print("\n⚠️ VALIDATION FAILED:")
        for file_path in validation_failed:
            print(f"  ❌ {file_path}")
    
    if len(validation_passed) == len(problematic_files):
        print("\n🎉 ALL FIXES SUCCESSFUL AND VALIDATED!")
        return 0
    else:
        print(f"\n⚠️ {len(problematic_files) - len(validation_passed)} files still have issues")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
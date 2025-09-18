#!/usr/bin/env python3
"""
Emergency syntax error fix script for Docker Infrastructure Crisis Issue #979
Fixes common syntax errors preventing test collection and execution
"""

import os
import sys
import re
import ast
from pathlib import Path
from typing import List, Tuple, Dict

def check_syntax(file_path: str) -> Tuple[bool, str]:
    """Check if a Python file has valid syntax."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True, ""
    except SyntaxError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Error reading file: {e}"

def fix_decimal_literal_errors(content: str) -> str:
    """Fix invalid decimal literal errors caused by unquoted $ in comments."""
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Fix lines that start with Business Value:, BVJ:, etc. and contain $ amounts
        if re.match(r'^(Business Value|BVJ|Revenue Impact|Strategic Impact|Value Impact):', line.strip()):
            if not line.strip().startswith('"""') and not line.strip().startswith('#'):
                line = '# ' + line.strip()
        
        # Fix lines with unmatched quotes at the start
        if line.strip().startswith('"') and not line.strip().endswith('"') and '"""' not in line:
            line = '# ' + line.strip()
            
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

def fix_unmatched_quotes(content: str) -> str:
    """Fix unmatched quotes and docstring issues."""
    # Fix common patterns of broken docstrings
    content = re.sub(r'^"([^"]+)"\s*$', r'"""\1"""', content, flags=re.MULTILINE)
    
    # Fix broken triple quotes
    content = re.sub(r'"""\s*\n([^"]*)\n""$', r'"""\n\1\n"""', content, flags=re.MULTILINE)
    
    return content

def fix_unmatched_brackets(content: str) -> str:
    """Remove obvious unmatched brackets/parentheses at end of files."""
    lines = content.split('\n')
    
    # Remove lines that are just unmatched brackets/parentheses
    fixed_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped in [')', ')))', '))))))', ']]', '}}}}', ')' * 10, ')' * 20, ')' * 50]:
            continue  # Skip these lines
        if re.match(r'^\)+$', stripped) and len(stripped) > 5:
            continue  # Skip lines with just many closing parentheses
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

def fix_specific_syntax_issues(content: str) -> str:
    """Fix specific syntax issues found in the codebase."""
    
    # Fix __main__ syntax errors
    content = re.sub(r'if __name__ == __main__":"', 'if __name__ == "__main__":', content)
    
    # Fix quote syntax in assert statements
    content = re.sub(r'assert ([^"]+)"([^"]+)"([^,]+)', r'assert \1"\2"\3', content)
    
    # Fix bracket syntax in array access
    content = re.sub(r'\["([^"]+)"\]\[([^\]]+)\]\[([^\]]+)\]', r'["\1"][\2][\3]', content)
    
    # Fix malformed string literals  
    content = re.sub(r'"([^"]*)\]([^"]*)"', r'"\1][\2"', content)
    
    return content

def emergency_fix_file(file_path: str) -> bool:
    """Emergency fix for a single file with syntax errors."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Apply fixes in order
        content = fix_decimal_literal_errors(original_content)
        content = fix_unmatched_quotes(content)
        content = fix_unmatched_brackets(content)
        content = fix_specific_syntax_issues(content)
        
        # Verify fix worked
        try:
            ast.parse(content)
            
            # Write fixed content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ FIXED: {file_path}")
            return True
            
        except SyntaxError as e:
            print(f"❌ STILL BROKEN: {file_path} - {e}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR FIXING: {file_path} - {e}")
        return False

def main():
    """Main function to fix syntax errors in test files."""
    
    project_root = Path(__file__).parent
    test_dirs = [
        project_root / "tests",
        project_root / "netra_backend" / "tests",
        project_root / "auth_service" / "tests", 
        project_root / "frontend" / "test"
    ]
    
    all_files = []
    for test_dir in test_dirs:
        if test_dir.exists():
            all_files.extend(test_dir.rglob("*.py"))
    
    print(f"🔍 Checking {len(all_files)} test files for syntax errors...")
    
    broken_files = []
    for file_path in all_files:
        is_valid, error = check_syntax(str(file_path))
        if not is_valid:
            broken_files.append((str(file_path), error))
    
    print(f"❌ Found {len(broken_files)} files with syntax errors")
    
    if not broken_files:
        print("✅ No syntax errors found!")
        return 0
    
    # Show first 10 errors for context
    print("\n📋 Sample syntax errors:")
    for file_path, error in broken_files[:10]:
        print(f"  {file_path}: {error}")
    
    if len(broken_files) > 10:
        print(f"  ... and {len(broken_files) - 10} more")
    
    # Ask for confirmation to fix
    print(f"\n🛠️  Attempting to fix {len(broken_files)} files...")
    
    fixed_count = 0
    for file_path, error in broken_files:
        if emergency_fix_file(file_path):
            fixed_count += 1
    
    print(f"\n📊 Results: {fixed_count}/{len(broken_files)} files fixed")
    
    if fixed_count == len(broken_files):
        print("✅ ALL SYNTAX ERRORS FIXED!")
        return 0
    else:
        print(f"⚠️  {len(broken_files) - fixed_count} files still need manual review")
        return 1

if __name__ == "__main__":
    sys.exit(main())
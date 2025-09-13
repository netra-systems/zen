#!/usr/bin/env python3
"""Check Python test files for common formatting issues that cause collection/import problems."""

import os
import glob
import ast
import sys

def check_syntax_errors(filepath):
    """Check if Python file has syntax errors."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        ast.parse(source)
        return None
    except SyntaxError as e:
        return f"Syntax error: {e}"
    except UnicodeDecodeError as e:
        return f"Encoding error: {e}"
    except Exception as e:
        return f"Parse error: {e}"

def check_encoding_issues(filepath):
    """Check for common encoding issues."""
    try:
        # Try to read with UTF-8
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for BOM
        if content.startswith('\ufeff'):
            return "BOM (Byte Order Mark) detected"
        
        # Check for mixed line endings
        if '\r\n' in content and '\n' in content.replace('\r\n', ''):
            return "Mixed line endings detected"
            
        return None
    except UnicodeDecodeError:
        return "UTF-8 encoding issue"
    except Exception as e:
        return f"File reading error: {e}"

def check_trailing_whitespace(filepath):
    """Check for excessive trailing whitespace."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        trailing_whitespace_lines = []
        for i, line in enumerate(lines, 1):
            if line.rstrip() != line.rstrip('\n\r'):
                trailing_whitespace_lines.append(i)
        
        if len(trailing_whitespace_lines) > 10:  # More than 10 lines with trailing whitespace
            return f"Excessive trailing whitespace on {len(trailing_whitespace_lines)} lines"
        
        return None
    except Exception as e:
        return f"Error checking whitespace: {e}"

def check_import_issues(filepath):
    """Check for common import issues that cause collection failures."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = []
        
        # Check for relative imports that might be problematic
        if 'from .' in content and 'import' in content:
            relative_imports = content.count('from .')
            if relative_imports > 5:  # Arbitrary threshold
                issues.append(f"{relative_imports} relative imports (potential path issues)")
        
        # Check for circular import patterns (basic check)
        if filepath.endswith('__init__.py') and 'import' in content:
            if content.count('import') > 20:  # Heavy init file
                issues.append("Heavy __init__.py file (potential circular imports)")
        
        return '; '.join(issues) if issues else None
        
    except Exception as e:
        return f"Import check error: {e}"

def scan_test_files():
    """Scan all test files for formatting issues."""
    test_files = glob.glob('/Users/anthony/Desktop/netra-apex/tests/**/*.py', recursive=True)
    
    issues = {
        'syntax_errors': [],
        'encoding_issues': [],
        'trailing_whitespace': [],
        'import_issues': []
    }
    
    print(f"Scanning {len(test_files)} Python test files...")
    
    for i, filepath in enumerate(test_files):
        if i % 500 == 0:
            print(f"Scanned {i}/{len(test_files)} files...")
        
        # Check syntax
        syntax_issue = check_syntax_errors(filepath)
        if syntax_issue:
            issues['syntax_errors'].append((filepath, syntax_issue))
        
        # Check encoding
        encoding_issue = check_encoding_issues(filepath)
        if encoding_issue:
            issues['encoding_issues'].append((filepath, encoding_issue))
        
        # Check trailing whitespace
        whitespace_issue = check_trailing_whitespace(filepath)
        if whitespace_issue:
            issues['trailing_whitespace'].append((filepath, whitespace_issue))
        
        # Check imports
        import_issue = check_import_issues(filepath)
        if import_issue:
            issues['import_issues'].append((filepath, import_issue))
    
    return issues

if __name__ == "__main__":
    issues = scan_test_files()
    
    print("\n" + "="*80)
    print("FILE FORMAT ISSUES SUMMARY")
    print("="*80)
    
    total_issues = sum(len(category_issues) for category_issues in issues.values())
    
    for category, file_issues in issues.items():
        print(f"\n{category.upper().replace('_', ' ')}: {len(file_issues)} files")
        if file_issues:
            for filepath, issue in file_issues[:10]:  # Show first 10
                rel_path = filepath.replace('/Users/anthony/Desktop/netra-apex/', '')
                print(f"  {rel_path}: {issue}")
            if len(file_issues) > 10:
                print(f"  ... and {len(file_issues) - 10} more files")
    
    print(f"\nTOTAL ISSUES FOUND: {total_issues} files with formatting problems")
    
    if total_issues == 0:
        print("✅ No formatting issues found that would cause test collection problems!")
    else:
        print("⚠️  Found formatting issues that may affect test collection.")
#!/usr/bin/env python3
"""
Syntax Error Detection and Analysis Tool
Identifies Python syntax errors in test files to enable systematic fixing.
"""

import ast
import os
import sys
from pathlib import Path
from collections import defaultdict
import re

def check_syntax(filepath):
    """Check syntax of a Python file and return detailed error info."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return None
    except SyntaxError as e:
        return {
            'file': filepath,
            'line': e.lineno,
            'column': e.offset,
            'message': e.msg,
            'text': e.text.strip() if e.text else '',
            'error_type': classify_error(e.msg)
        }
    except UnicodeDecodeError as e:
        return {
            'file': filepath,
            'line': 0,
            'column': 0,
            'message': f'Unicode decode error: {e}',
            'text': '',
            'error_type': 'encoding'
        }
    except Exception as e:
        return {
            'file': filepath,
            'line': 0,
            'column': 0,
            'message': f'Unexpected error: {e}',
            'text': '',
            'error_type': 'other'
        }

def classify_error(msg):
    """Classify syntax error by type for pattern analysis."""
    msg_lower = msg.lower()
    
    if 'indent' in msg_lower:
        return 'indentation'
    elif 'bracket' in msg_lower or 'parenthes' in msg_lower:
        return 'brackets'
    elif 'colon' in msg_lower:
        return 'colon'
    elif 'quote' in msg_lower or 'string' in msg_lower:
        return 'quotes'
    elif 'eof' in msg_lower:
        return 'eof'
    elif 'import' in msg_lower:
        return 'import'
    elif 'async' in msg_lower or 'await' in msg_lower:
        return 'async'
    else:
        return 'other'

def find_test_files():
    """Find all Python test files in the project."""
    test_files = []
    
    # Common test directories and patterns
    test_patterns = [
        'test*.py',
        '*test*.py',
        '*_test.py'
    ]
    
    test_dirs = [
        'tests',
        'test',
        'netra_backend/tests',
        'auth_service/tests',
        'frontend/tests',
        'test_framework'
    ]
    
    # Find files in test directories
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            for root, dirs, files in os.walk(test_dir):
                for file in files:
                    if file.endswith('.py'):
                        test_files.append(os.path.join(root, file))
    
    # Find test files in other directories
    for root, dirs, files in os.walk('.'):
        # Skip common non-source directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', 'env']]
        
        for file in files:
            if file.endswith('.py') and any(pattern.replace('*', '') in file.lower() for pattern in ['test', '_test']):
                filepath = os.path.join(root, file)
                if filepath not in test_files:
                    test_files.append(filepath)
    
    return sorted(set(test_files))

def analyze_errors(errors):
    """Analyze error patterns for systematic fixing."""
    error_types = defaultdict(list)
    error_messages = defaultdict(int)
    
    for error in errors:
        error_types[error['error_type']].append(error)
        error_messages[error['message']] += 1
    
    return error_types, error_messages

def main():
    print("🔍 Scanning for Python test files with syntax errors...")
    
    # Find all test files
    test_files = find_test_files()
    print(f"Found {len(test_files)} test files to check")
    
    # Check syntax
    errors = []
    checked = 0
    
    for filepath in test_files:
        checked += 1
        if checked % 50 == 0:
            print(f"Checked {checked}/{len(test_files)} files...")
        
        error = check_syntax(filepath)
        if error:
            errors.append(error)
    
    print(f"\n🚨 SYNTAX ERROR ANALYSIS RESULTS:")
    print(f"Total files checked: {len(test_files)}")
    print(f"Files with syntax errors: {len(errors)}")
    print(f"Clean files: {len(test_files) - len(errors)}")
    
    if not errors:
        print("✅ No syntax errors found!")
        return
    
    # Analyze error patterns
    error_types, error_messages = analyze_errors(errors)
    
    print(f"\n📊 ERROR BREAKDOWN BY TYPE:")
    for error_type, type_errors in sorted(error_types.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {error_type}: {len(type_errors)} files")
    
    print(f"\n📋 TOP 10 MOST COMMON ERROR MESSAGES:")
    for msg, count in sorted(error_messages.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {count}x: {msg}")
    
    print(f"\n🔍 FIRST 20 SYNTAX ERRORS (detailed):")
    for i, error in enumerate(errors[:20]):
        print(f"\n{i+1}. {error['file']}:{error['line']}")
        print(f"   Type: {error['error_type']}")
        print(f"   Error: {error['message']}")
        if error['text']:
            print(f"   Line: {error['text']}")
    
    # Save detailed report
    report_file = 'syntax_errors_report.txt'
    with open(report_file, 'w') as f:
        f.write("SYNTAX ERROR DETAILED REPORT\n")
        f.write("=" * 50 + "\n\n")
        
        f.write(f"Total files checked: {len(test_files)}\n")
        f.write(f"Files with syntax errors: {len(errors)}\n")
        f.write(f"Clean files: {len(test_files) - len(errors)}\n\n")
        
        f.write("ERROR BREAKDOWN BY TYPE:\n")
        for error_type, type_errors in sorted(error_types.items(), key=lambda x: len(x[1]), reverse=True):
            f.write(f"  {error_type}: {len(type_errors)} files\n")
        
        f.write("\nALL SYNTAX ERRORS:\n")
        for error in errors:
            f.write(f"\n{error['file']}:{error['line']}\n")
            f.write(f"  Type: {error['error_type']}\n")
            f.write(f"  Error: {error['message']}\n")
            if error['text']:
                f.write(f"  Line: {error['text']}\n")
    
    print(f"\n📄 Detailed report saved to: {report_file}")
    
    # Show fixable patterns
    print(f"\n🛠️  RECOMMENDED FIXING ORDER:")
    print("1. Fix indentation errors (usually systematic)")
    print("2. Fix bracket/parentheses mismatches")
    print("3. Fix import statement issues")
    print("4. Fix string/quote issues")
    print("5. Fix other specific errors")

if __name__ == "__main__":
    main()
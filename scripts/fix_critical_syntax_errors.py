#!/usr/bin/env python3
"""
Quick fix for the most common critical syntax errors in e2e tests.
"""

import ast
import re
from pathlib import Path
from typing import List


def read_file(file_path: Path) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ""


def write_file(file_path: Path, content: str) -> bool:
    try:
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            f.write(content)
        return True
    except Exception:
        return False


def fix_common_issues(content: str) -> str:
    """Fix the most common syntax issues found."""
    
    # Fix missing closing parentheses in function calls
    # Pattern: function_call(\n    "arg1",\n    "arg2"\n without closing )
    content = re.sub(
        r'(send_agent_request\(\s*\n\s*"[^"]+",\s*\n\s*"[^"]+"\s*)\n(\s+)',
        r'\1\n)\n\2',
        content,
        flags=re.MULTILINE
    )
    
    # Fix missing closing parentheses in function calls with context
    content = re.sub(
        r'(send_agent_request\(\s*\n\s*"[^"]+",\s*\n\s*"[^"]+",\s*\n\s*[^)]+)\n(\s+)',
        r'\1\n)\n\2',
        content,
        flags=re.MULTILINE
    )
    
    # Remove misplaced "pass" statements after try:
    content = re.sub(r'try:\s*\n\s+pass\s*\n(\s+)', r'try:\n\1', content, flags=re.MULTILINE)
    
    # Fix incomplete import statements - remove orphaned import lines
    lines = content.split('\n')
    cleaned_lines = []
    
    for i, line in enumerate(lines):
        # Skip lines that are just import continuation without proper structure
        stripped = line.strip()
        
        # Skip orphaned import items
        if (stripped and 
            not stripped.startswith(('#', 'from ', 'import ', 'class ', 'def ', 'async def ', '@')) and
            not stripped.endswith(':') and
            stripped in ['ConcurrentUserMetrics,', 'UserSession,', 'MockServiceManager,', 'MockWebSocketClient,', 'IsolationValidator']):
            continue
            
        # Skip standalone closing parentheses that don't belong
        if stripped == ')' and i > 0:
            prev_line = lines[i-1].strip() if i > 0 else ""
            # Only keep ) if previous line suggests it belongs there
            if not (prev_line.endswith(',') or '(' in prev_line):
                continue
        
        # Skip duplicate import lines
        if line.strip() == 'from typing import Dict, List, Any, Optional' and cleaned_lines:
            # Check if we already have this import
            if any('from typing import Dict, List, Any, Optional' in prev for prev in cleaned_lines[-10:]):
                continue
        
        cleaned_lines.append(line)
    
    content = '\n'.join(cleaned_lines)
    
    # Add missing indentation after try, if, etc
    content = re.sub(r'(try|if [^:]*|for [^:]*|while [^:]*|with [^:]*|async def [^:]*|def [^:]*):$\n([^\s])', 
                    r'\1:\n    \2', content, flags=re.MULTILINE)
    
    return content


def get_files_with_syntax_errors(directory: Path) -> List[Path]:
    """Get list of Python files with syntax errors."""
    files_with_errors = []
    
    if not directory.exists():
        return files_with_errors
    
    python_files = list(directory.rglob("*.py"))
    
    for file_path in python_files[:10]:  # Limit to first 10 for quick fix
        try:
            content = read_file(file_path)
            if content:
                ast.parse(content, filename=str(file_path))
        except SyntaxError:
            files_with_errors.append(file_path)
        except Exception:
            pass
    
    return files_with_errors


def main():
    """Main execution function."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    e2e_tests_dir = project_root / "tests" / "e2e"
    
    print(f"Quick fix for critical syntax errors in: {e2e_tests_dir}")
    print("=" * 60)
    
    # Get first batch of files with syntax errors
    error_files = get_files_with_syntax_errors(e2e_tests_dir)
    print(f"Found {len(error_files)} files with syntax errors (processing first 10)")
    
    fixed_count = 0
    
    for file_path in error_files:
        print(f"Fixing: {file_path}")
        
        content = read_file(file_path)
        if not content:
            continue
            
        fixed_content = fix_common_issues(content)
        
        if fixed_content != content:
            if write_file(file_path, fixed_content):
                print(f"  Fixed successfully")
                fixed_count += 1
            else:
                print(f"  Failed to write")
        else:
            print(f"  No changes needed")
    
    print(f"\nFixed {fixed_count} files")


if __name__ == "__main__":
    main()
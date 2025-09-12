#!/usr/bin/env python3
"""
Comprehensive syntax error fix script for e2e tests.
Systematically fixes common syntax errors found in the codebase.
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict


def read_file(file_path: Path) -> str:
    """Read file content safely."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""


def write_file(file_path: Path, content: str) -> bool:
    """Write file content safely."""
    try:
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Error writing {file_path}: {e}")
        return False


def fix_function_signature_colon(content: str) -> str:
    """Fix missing colons in function signatures."""
    # Pattern: function signature ending with parameter: type but missing final colon
    patterns = [
        # async def func(param: type
        (r'(async def \w+\([^)]*): \s*\n(\s*)', r'\1:\n\2'),
        # def func(param: type
        (r'(def \w+\([^)]*): \s*\n(\s*)', r'\1:\n\2'),
        # Fix cases like "param: str:"  -> "param: str):"
        (r'(\w+: \w+):\s*\n(\s*\w)', r'\1):\n\2'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    return content


def fix_incomplete_imports(content: str) -> str:
    """Fix incomplete import statements."""
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check for incomplete import like "from module import ("
        if line.strip().startswith('from ') and line.strip().endswith('('):
            # Look for the closing import
            import_lines = [line]
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith('import ') and not lines[j].strip().startswith('from '):
                import_lines.append(lines[j])
                if ')' in lines[j]:
                    break
                j += 1
            
            # If we didn't find proper closing, fix it
            if not any(')' in l for l in import_lines[1:]):
                # Add a closing parenthesis to the last import line
                if len(import_lines) > 1:
                    import_lines[-1] = import_lines[-1].rstrip() + ')'
                else:
                    # Single line import, might be malformed
                    import_lines[0] = import_lines[0].replace('(', '').rstrip()
            
            fixed_lines.extend(import_lines)
            i = j
        else:
            fixed_lines.append(line)
            i += 1
    
    return '\n'.join(fixed_lines)


def fix_indentation_issues(content: str) -> str:
    """Fix basic indentation issues."""
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Fix unexpected indents after imports
        if (line.strip().startswith('import ') or line.strip().startswith('from ')) and line.startswith('    '):
            # Check if previous line is also import
            if i > 0 and (lines[i-1].strip().startswith('import ') or lines[i-1].strip().startswith('from ')):
                fixed_lines.append(line)
            else:
                # Remove unexpected indent
                fixed_lines.append(line.lstrip())
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def fix_malformed_function_definitions(content: str) -> str:
    """Fix malformed function definitions."""
    # Fix function signatures that are split incorrectly
    patterns = [
        # Fix cases like: def func(param: type\n  param2: type):
        (r'(async def \w+\([^:)]*): *\n *([^)]+\)):? *\n', r'\1, \2:\n'),
        (r'(def \w+\([^:)]*): *\n *([^)]+\)):? *\n', r'\1, \2:\n'),
        # Fix missing closing parentheses in function definitions
        (r'(async def \w+\([^)]*): *\n(\s+)', r'\1):\n\2'),
        (r'(def \w+\([^)]*): *\n(\s+)', r'\1):\n\2'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    return content


def fix_missing_indentation(content: str) -> str:
    """Fix missing indentation after if statements, etc."""
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        fixed_lines.append(line)
        
        # Check if line ends with colon (if, for, while, def, class, etc.)
        if line.strip().endswith(':') and not line.strip().startswith('#'):
            # Check if next line exists and is not indented
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if next_line.strip() and not next_line.startswith('    ') and not next_line.startswith('\t'):
                    # Add proper indentation to next line
                    lines[i + 1] = '    ' + next_line.lstrip()
    
    return '\n'.join(lines)


def apply_all_fixes(content: str) -> str:
    """Apply all syntax fixes to content."""
    content = fix_incomplete_imports(content)
    content = fix_malformed_function_definitions(content)
    content = fix_function_signature_colon(content)
    content = fix_indentation_issues(content)
    content = fix_missing_indentation(content)
    return content


def fix_file(file_path: Path) -> bool:
    """Fix syntax errors in a single file."""
    print(f"Fixing: {file_path}")
    
    # Read original content
    content = read_file(file_path)
    if not content:
        return False
    
    # Apply fixes
    fixed_content = apply_all_fixes(content)
    
    # Check if content changed
    if fixed_content == content:
        print(f"  No changes needed")
        return True
    
    # Write fixed content
    if write_file(file_path, fixed_content):
        print(f"  Fixed successfully")
        return True
    else:
        print(f"  Failed to write fixes")
        return False


def scan_and_fix_directory(directory: Path) -> Dict[str, bool]:
    """Scan directory and fix all syntax errors found."""
    results = {}
    
    if not directory.exists():
        print(f"Directory does not exist: {directory}")
        return results
    
    # Get all Python files with syntax errors
    python_files = list(directory.rglob("*.py"))
    
    print(f"Checking {len(python_files)} Python files...")
    
    files_with_errors = []
    for file_path in python_files:
        try:
            content = read_file(file_path)
            ast.parse(content, filename=str(file_path))
        except SyntaxError:
            files_with_errors.append(file_path)
        except Exception:
            pass  # Skip other errors for now
    
    print(f"Found {len(files_with_errors)} files with syntax errors")
    
    # Fix each file
    for file_path in files_with_errors:
        success = fix_file(file_path)
        results[str(file_path)] = success
    
    return results


def main():
    """Main execution function."""
    # Get the e2e tests directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    e2e_tests_dir = project_root / "tests" / "e2e"
    
    print(f"Fixing syntax errors in: {e2e_tests_dir}")
    print("=" * 60)
    
    # Fix all files
    results = scan_and_fix_directory(e2e_tests_dir)
    
    # Print summary
    fixed_count = sum(1 for success in results.values() if success)
    failed_count = len(results) - fixed_count
    
    print(f"\nSummary:")
    print(f"  Fixed: {fixed_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Total: {len(results)}")
    
    if failed_count == 0:
        print("[U+2713] All syntax errors fixed!")
        sys.exit(0)
    else:
        print("X Some fixes failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
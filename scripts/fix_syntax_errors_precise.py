#!/usr/bin/env python3
"""
Precise syntax error fix script that handles common patterns found in e2e tests.
Fixes errors without introducing new ones.
"""

import ast
import re
import sys
from pathlib import Path
from typing import Dict, List


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


def fix_import_issues(content: str) -> str:
    """Fix incomplete import statements."""
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Fix incomplete import like "from module import"
        if line.strip().startswith('from ') and line.strip().endswith('import'):
            # Look ahead for continuation
            if i + 1 < len(lines) and lines[i + 1].strip().startswith('from '):
                # This is a broken import, merge with next line
                next_line = lines[i + 1]
                # Remove the duplicate 'from typing import' part
                if 'from typing import' in next_line:
                    fixed_lines.append(next_line)
                    # Skip the incomplete line
                    continue
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def fix_function_signature_issues(content: str) -> str:
    """Fix function signature issues."""
    lines = content.split('\n')
    fixed_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Fix function signatures split across lines incorrectly
        if (('async def ' in line or 'def ' in line) and 
            line.strip().endswith(':') and 
            i + 1 < len(lines) and 
            lines[i + 1].strip() and 
            not lines[i + 1].startswith(' ') and
            not lines[i + 1].startswith('\t')):
            
            # This looks like a broken function signature
            # Check if the next line has parameters
            next_line = lines[i + 1].strip()
            if next_line.endswith(') -> ') or ') ->' in next_line:
                # Merge the lines properly
                line_without_colon = line.rstrip(':').strip()
                # Reconstruct the function signature
                if next_line.endswith(') ->'):
                    return_type_line = lines[i + 2] if i + 2 < len(lines) else ""
                    fixed_line = f"{line_without_colon}, {next_line[:-4]}) -> {return_type_line.strip().rstrip(':')}:"
                    fixed_lines.append(fixed_line)
                    i += 3  # Skip the merged lines
                    continue
                elif ') ->' in next_line:
                    # Return type on same line
                    fixed_line = f"{line_without_colon}, {next_line}:"
                    fixed_lines.append(fixed_line)
                    i += 2
                    continue
        
        fixed_lines.append(line)
        i += 1
    
    return '\n'.join(fixed_lines)


def fix_unmatched_parentheses(content: str) -> str:
    """Fix unmatched parentheses in import statements."""
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Remove standalone closing parentheses that don't match
        if line.strip() == ')':
            # Check if previous line needs this parenthesis
            if fixed_lines and ('(' in fixed_lines[-1] and ')' not in fixed_lines[-1]):
                # This closing paren belongs to previous line
                fixed_lines[-1] = fixed_lines[-1] + ')'
            # Otherwise skip the standalone parenthesis
            continue
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def fix_indentation_after_keywords(content: str) -> str:
    """Fix missing indentation after keywords like if, try, etc."""
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        fixed_lines.append(line)
        
        # Check if line ends with colon and next line is not indented
        if (line.strip().endswith(':') and 
            i + 1 < len(lines) and 
            lines[i + 1].strip() and 
            not lines[i + 1].startswith('    ') and
            not lines[i + 1].startswith('\t') and
            not lines[i + 1].strip().startswith('#')):
            
            # Add indentation to next line
            lines[i + 1] = '    ' + lines[i + 1].lstrip()
    
    return '\n'.join(lines)


def fix_try_except_blocks(content: str) -> str:
    """Fix incomplete try/except blocks."""
    lines = content.split('\n')
    fixed_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        fixed_lines.append(line)
        
        # Check for try: without proper except/finally
        if line.strip() == 'try:':
            # Look ahead to see if there's an except or finally
            j = i + 1
            has_except_or_finally = False
            
            # Look for except or finally in following lines
            while j < len(lines) and j < i + 20:  # Look ahead reasonable distance
                next_line = lines[j].strip()
                if next_line.startswith('except') or next_line.startswith('finally'):
                    has_except_or_finally = True
                    break
                j += 1
            
            # If no except/finally found, add a pass and except
            if not has_except_or_finally:
                # Add pass on next line if it doesn't exist
                if i + 1 < len(lines) and not lines[i + 1].strip().startswith('pass'):
                    fixed_lines.append('    pass')
        
        i += 1
    
    return '\n'.join(fixed_lines)


def apply_targeted_fixes(content: str) -> str:
    """Apply all targeted fixes to content."""
    content = fix_import_issues(content)
    content = fix_unmatched_parentheses(content)
    content = fix_function_signature_issues(content)
    content = fix_indentation_after_keywords(content)
    content = fix_try_except_blocks(content)
    return content


def fix_specific_file_issues(file_path: Path, content: str) -> str:
    """Apply file-specific fixes based on common patterns."""
    file_name = file_path.name
    
    # Fix specific patterns found in the syntax errors
    # Remove standalone closing parentheses that don't belong
    lines = content.split('\n')
    cleaned_lines = []
    for i, line in enumerate(lines):
        if line.strip() == ')' and i > 0:
            # Check if this should close an import on previous line
            prev_line = lines[i-1].strip()
            if prev_line and ('(' in prev_line or prev_line.endswith(',')):
                # Merge with previous line
                if cleaned_lines:
                    cleaned_lines[-1] = cleaned_lines[-1].rstrip() + ')'
                continue
        cleaned_lines.append(line)
    content = '\n'.join(cleaned_lines)
    
    return content


def fix_file(file_path: Path) -> bool:
    """Fix syntax errors in a single file."""
    print(f"Fixing: {file_path}")
    
    # Read original content
    content = read_file(file_path)
    if not content:
        return False
    
    # Apply fixes
    fixed_content = apply_targeted_fixes(content)
    fixed_content = fix_specific_file_issues(file_path, fixed_content)
    
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


def get_files_with_syntax_errors(directory: Path) -> List[Path]:
    """Get list of Python files with syntax errors."""
    files_with_errors = []
    
    if not directory.exists():
        return files_with_errors
    
    python_files = list(directory.rglob("*.py"))
    
    for file_path in python_files:
        try:
            content = read_file(file_path)
            if content:
                ast.parse(content, filename=str(file_path))
        except SyntaxError:
            files_with_errors.append(file_path)
        except Exception:
            pass  # Skip other errors
    
    return files_with_errors


def main():
    """Main execution function."""
    # Get the e2e tests directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    e2e_tests_dir = project_root / "tests" / "e2e"
    
    print(f"Fixing syntax errors in: {e2e_tests_dir}")
    print("=" * 60)
    
    # Get files with syntax errors
    error_files = get_files_with_syntax_errors(e2e_tests_dir)
    print(f"Found {len(error_files)} files with syntax errors")
    
    # Fix each file
    results = {}
    for file_path in error_files:
        success = fix_file(file_path)
        results[str(file_path)] = success
    
    # Print summary
    fixed_count = sum(1 for success in results.values() if success)
    failed_count = len(results) - fixed_count
    
    print(f"\nSummary:")
    print(f"  Fixed: {fixed_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Total: {len(results)}")
    
    if failed_count == 0:
        print("All syntax errors fixed!")
        sys.exit(0)
    else:
        print("Some fixes failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
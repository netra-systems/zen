#!/usr/bin/env python3
"""
Aggressive syntax error fixer for Python files.
Handles common syntax issues found in the codebase.
"""

import ast
import re
import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict


def fix_mismatched_brackets(content: str) -> str:
    """Fix mismatched brackets by balancing them."""
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        # Fix common bracket mismatches
        if "closing parenthesis ')' does not match opening parenthesis '{'" in str(line):
            # Look for { ... ) patterns and fix them
            lines[i] = re.sub(r'\{([^}]*)\)', r'{\1}', line)
        
        if "closing parenthesis ']' does not match opening parenthesis '{'" in str(line):
            # Look for { ... ] patterns and fix them
            lines[i] = re.sub(r'\{([^\]]*)\]', r'{\1}', line)
    
    return '\n'.join(lines)


def fix_unclosed_parentheses(content: str) -> str:
    """Fix unclosed parentheses by adding missing closing ones."""
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        if "'(' was never closed" in str(line):
            # Count open and close parens
            open_count = line.count('(')
            close_count = line.count(')')
            if open_count > close_count:
                lines[i] = line + ')' * (open_count - close_count)
    
    return '\n'.join(lines)


def fix_unterminated_strings(content: str) -> str:
    """Fix unterminated triple-quoted strings."""
    # Fix unterminated triple quotes
    if content.count('"""') % 2 == 1:
        content += '\n"""'
    if content.count("'''") % 2 == 1:
        content += "\n'''"
    
    return content


def fix_unexpected_indent(content: str) -> str:
    """Fix unexpected indentation issues."""
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # If line starts with unexpected whitespace and previous line doesn't need continuation
        if i > 0 and line.startswith('    ') and not lines[i-1].rstrip().endswith((':', '\\', ',')):
            # Check if this looks like orphaned code
            stripped = line.strip()
            if stripped.startswith(('import ', 'from ', 'def ', 'class ', 'async def')):
                # Remove indentation for top-level statements
                fixed_lines.append(stripped)
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def fix_empty_blocks(content: str) -> str:
    """Add pass statements to empty blocks."""
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        fixed_lines.append(line)
        
        # If this line ends with : and next line is not indented or is empty/comment
        if line.strip().endswith(':') and i < len(lines) - 1:
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            
            # Check if we need to add pass
            if (not next_line.strip() or 
                not next_line.startswith('    ') or 
                next_line.strip().startswith('#')):
                # Add pass statement
                indent = len(line) - len(line.lstrip()) + 4
                fixed_lines.append(' ' * indent + 'pass')
    
    return '\n'.join(fixed_lines)


def fix_syntax_errors(content: str) -> str:
    """Apply multiple syntax fixes."""
    # Apply fixes in order
    content = fix_unexpected_indent(content)
    content = fix_mismatched_brackets(content)
    content = fix_unclosed_parentheses(content)
    content = fix_unterminated_strings(content)
    content = fix_empty_blocks(content)
    
    # Remove orphaned import lines that are malformed
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Skip malformed import lines
        if line.strip().startswith(('from .', 'from ..')) and 'import' not in line:
            continue
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def validate_syntax(file_path: str) -> Tuple[bool, str]:
    """Validate Python syntax using ast.parse."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast.parse(content)
        return True, ""
    except SyntaxError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Error reading file: {e}"


def fix_file(file_path: str) -> bool:
    """Fix syntax errors in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Apply fixes
        fixed_content = fix_syntax_errors(original_content)
        
        # Write back if changed
        if fixed_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            # Validate the fix
            is_valid, error = validate_syntax(file_path)
            if is_valid:
                print(f"[FIXED] {file_path}")
                return True
            else:
                # Restore original if fix didn't work
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                print(f"[FAILED] {file_path} - {error}")
                return False
        else:
            print(f"[UNCHANGED] {file_path}")
            return True
            
    except Exception as e:
        print(f"[ERROR] {file_path}: {e}")
        return False


def main():
    """Main function to fix syntax errors."""
    if len(sys.argv) != 2:
        print("Usage: python aggressive_syntax_fixer.py <directory>")
        sys.exit(1)
    
    directory = Path(sys.argv[1])
    if not directory.exists():
        print(f"Directory not found: {directory}")
        sys.exit(1)
    
    # Get all Python files with syntax errors
    python_files = list(directory.rglob("*.py"))
    
    syntax_error_files = []
    for file_path in python_files:
        is_valid, error = validate_syntax(str(file_path))
        if not is_valid:
            syntax_error_files.append(str(file_path))
    
    if not syntax_error_files:
        print("No syntax errors found!")
        return
    
    print(f"Found {len(syntax_error_files)} files with syntax errors")
    print("Attempting to fix...")
    
    fixed_count = 0
    for file_path in syntax_error_files:
        if fix_file(file_path):
            fixed_count += 1
    
    print(f"\nResults:")
    print(f"Fixed: {fixed_count}/{len(syntax_error_files)} files")
    
    if fixed_count < len(syntax_error_files):
        print(f"Still have {len(syntax_error_files) - fixed_count} files with syntax errors")


if __name__ == "__main__":
    main()
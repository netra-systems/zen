#!/usr/bin/env python3
"""
Verify all functions in reliability.py are  <= 8 lines.
"""

import ast
import re


def count_function_lines(file_path: str):
    """Count lines for each function in the file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    violations = []
    
    # Find function definitions using regex for precise line counting
    pattern = r'^(\s*)def\s+(\w+)\s*\([^)]*\).*?:'
    
    i = 0
    while i < len(lines):
        line = lines[i]
        match = re.match(pattern, line)
        
        if match:
            func_name = match.group(2)
            start_line = i + 1  # Line numbers start at 1
            indent_level = len(match.group(1))
            
            # Count lines until we find the end of the function
            j = i + 1
            func_lines = 1  # Count the def line
            
            # Skip docstring if present
            if j < len(lines) and '"""' in lines[j]:
                if lines[j].count('"""') == 1:  # Multi-line docstring
                    j += 1
                    while j < len(lines) and '"""' not in lines[j]:
                        j += 1
                    j += 1  # Skip closing """
                else:  # Single-line docstring
                    j += 1
            
            # Count function body lines
            while j < len(lines):
                current_line = lines[j]
                
                # Empty line - count it
                if not current_line.strip():
                    func_lines += 1
                    j += 1
                    continue
                
                # Calculate current indentation
                current_indent = len(current_line) - len(current_line.lstrip())
                
                # If we're back to the same or less indentation and not a continuation
                if current_indent <= indent_level and current_line.strip():
                    break
                
                func_lines += 1
                j += 1
            
            print(f"Function '{func_name}' (lines {start_line}-{start_line + func_lines - 1}): {func_lines} lines")
            
            if func_lines > 8:
                violations.append((func_name, func_lines, start_line))
        
        i += 1
    
    return violations

def main():
    file_path = "app/core/reliability.py"
    print(f"Analyzing functions in {file_path}")
    print("=" * 50)
    
    violations = count_function_lines(file_path)
    
    print("\n" + "=" * 50)
    if violations:
        print(f" FAIL:  Found {len(violations)} violations (functions > 8 lines):")
        for func_name, line_count, start_line in violations:
            print(f"  - {func_name}: {line_count} lines (starts at line {start_line})")
    else:
        print(" PASS:  All functions are  <= 8 lines! No violations found.")
    
    return len(violations) == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
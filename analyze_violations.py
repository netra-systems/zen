#!/usr/bin/env python3
"""
Script to analyze function violations in app/agents/
Finds functions that exceed 8 lines and files with most violations.
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

def count_function_lines(file_path: str) -> List[Tuple[str, int, int]]:
    """Count lines for each function in a file."""
    violations = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception:
        return violations
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Find function definitions
        match = re.match(r'^(async\s+)?def\s+(\w+)\s*\(', line)
        if match:
            func_name = match.group(2)
            start_line = i + 1  # 1-based line numbering
            
            # Count lines until next function or class or end of indentation
            func_lines = 1
            i += 1
            
            # Skip function signature if it spans multiple lines
            while i < len(lines) and lines[i].strip().endswith('):') == False and '(' in lines[start_line-1]:
                if ')' in lines[i]:
                    break
                i += 1
                func_lines += 1
            
            # Count function body lines
            if i < len(lines):
                base_indent = len(lines[i]) - len(lines[i].lstrip())
                i += 1
                func_lines += 1
                
                while i < len(lines):
                    line = lines[i]
                    
                    # Empty line
                    if not line.strip():
                        i += 1
                        func_lines += 1
                        continue
                    
                    current_indent = len(line) - len(line.lstrip())
                    
                    # If we've gone back to base level or less, function is done
                    if current_indent <= base_indent and line.strip():
                        # Check if it's another def/class/decorator
                        if (re.match(r'^(async\s+)?def\s+', line.strip()) or 
                            re.match(r'^class\s+', line.strip()) or
                            line.strip().startswith('@')):
                            break
                    
                    i += 1
                    func_lines += 1
            
            # Count as violation if > 8 lines
            if func_lines > 8:
                violations.append((func_name, start_line, func_lines))
        else:
            i += 1
    
    return violations

def analyze_agents_directory():
    """Analyze all Python files in app/agents/ directory."""
    agents_path = Path("app/agents")
    file_violations = {}
    
    for py_file in agents_path.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
            
        violations = count_function_lines(str(py_file))
        if violations:
            file_violations[str(py_file)] = violations
    
    return file_violations

def main():
    """Main analysis function."""
    print("ANALYZING function violations in app/agents/...")
    print("=" * 60)
    
    violations = analyze_agents_directory()
    
    if not violations:
        print("No violations found!")
        return
    
    # Sort files by number of violations
    sorted_files = sorted(violations.items(), key=lambda x: len(x[1]), reverse=True)
    
    print(f"\nTOP 10 FILES WITH MOST VIOLATIONS:")
    print("=" * 60)
    
    total_violations = 0
    for i, (file_path, file_violations) in enumerate(sorted_files[:10]):
        violation_count = len(file_violations)
        total_violations += violation_count
        
        print(f"\n{i+1}. {file_path}")
        print(f"   Violations: {violation_count}")
        
        # Show top 3 worst functions in each file
        sorted_funcs = sorted(file_violations, key=lambda x: x[2], reverse=True)
        for func_name, line_num, line_count in sorted_funcs[:3]:
            print(f"   - {func_name}() at line {line_num}: {line_count} lines (violation: +{line_count-8})")
    
    print(f"\nSUMMARY:")
    print(f"   Total files with violations: {len(violations)}")
    print(f"   Total function violations: {total_violations}")
    print(f"   Files analyzed: {len(list(Path('app/agents').rglob('*.py')))}")

if __name__ == "__main__":
    main()

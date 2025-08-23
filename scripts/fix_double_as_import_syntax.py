#!/usr/bin/env python3
"""
Fix double 'as' import syntax errors in Python files.
This script fixes invalid syntax like:
from module import Class as Name2
to:
from module import Class as Name2
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

def find_double_as_imports(file_path: Path) -> List[Tuple[int, str, str]]:
    """
    Find lines with double 'as' import syntax.
    Returns list of (line_number, original_line, fixed_line) tuples.
    """
    fixes = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines, 1):
            # Pattern to match "from X import Y as Z2"
            pattern = r'(from\s+\S+\s+import\s+\S+\s+as\s+\S+)\s+as\s+(\S+)'
            match = re.search(pattern, line)
            
            if match:
                # Extract the second alias (the one we want to keep)
                second_alias = match.group(2)
                
                # Reconstruct with only the second alias
                # First get the base import part
                base_pattern = r'(from\s+\S+\s+import\s+\S+)\s+as\s+\S+\s+as\s+\S+'
                base_match = re.search(base_pattern, line)
                
                if base_match:
                    base_import = base_match.group(1)
                    fixed_line = line.replace(match.group(0), f"{base_import} as {second_alias}")
                    fixes.append((i, line.rstrip(), fixed_line.rstrip()))
    
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []
    
    return fixes

def apply_fixes(file_path: Path, fixes: List[Tuple[int, str, str]]) -> bool:
    """Apply the fixes to the file."""
    if not fixes:
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Apply fixes in reverse order to preserve line numbers
        for line_num, original, fixed in reversed(fixes):
            content = content.replace(original, fixed, 1)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
    
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def find_python_files(root_dir: Path) -> List[Path]:
    """Find all Python files in the directory tree."""
    python_files = []
    
    # Skip these directories
    skip_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', 'venv', '.venv'}
    
    for root, dirs, files in os.walk(root_dir):
        # Remove skip directories from dirs list to prevent os.walk from entering them
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    
    return python_files

def main():
    """Main function to fix double 'as' import syntax errors."""
    # Get the root directory (where this script is located)
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent
    
    print(f"Scanning for double 'as' import syntax errors in: {root_dir}")
    
    # Find all Python files
    python_files = find_python_files(root_dir)
    print(f"Found {len(python_files)} Python files to check")
    
    total_fixes = 0
    fixed_files = 0
    
    # Process each file
    for file_path in python_files:
        fixes = find_double_as_imports(file_path)
        
        if fixes:
            print(f"\nFixing {file_path}:")
            for line_num, original, fixed in fixes:
                print(f"  Line {line_num}:")
                print(f"    OLD: {original}")
                print(f"    NEW: {fixed}")
            
            if apply_fixes(file_path, fixes):
                fixed_files += 1
                total_fixes += len(fixes)
                print(f"  OK Applied {len(fixes)} fixes")
            else:
                print(f"  ERROR Failed to apply fixes")
    
    print(f"\n=== SUMMARY ===")
    print(f"Files scanned: {len(python_files)}")
    print(f"Files fixed: {fixed_files}")
    print(f"Total fixes applied: {total_fixes}")
    
    if total_fixes > 0:
        print("\nOK All double 'as' import syntax errors have been fixed!")
        
        # Verify fixes by testing a few critical files
        critical_files = [
            "netra_backend/tests/integration/critical_paths/test_high_performance_websocket_stress.py",
            "netra_backend/tests/integration/critical_paths/test_websocket_concurrency.py",
            "netra_backend/tests/e2e/test_cost_optimization_workflows.py"
        ]
        
        print("\nVerifying critical files...")
        for file_rel_path in critical_files:
            file_path = root_dir / file_rel_path
            if file_path.exists():
                try:
                    # Try to compile the file to check for syntax errors
                    with open(file_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                    compile(code, str(file_path), 'exec')
                    print(f"  OK {file_rel_path} - syntax OK")
                except SyntaxError as e:
                    print(f"  ERROR {file_rel_path} - syntax error: {e}")
                except Exception as e:
                    print(f"  ? {file_rel_path} - check failed: {e}")
    else:
        print("No double 'as' import syntax errors found.")

if __name__ == "__main__":
    main()
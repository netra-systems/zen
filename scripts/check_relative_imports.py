#!/usr/bin/env python3
"""
Pre-commit hook to prevent relative imports in Python files.
Enforces absolute imports only as per CLAUDE.md guidelines.
"""

import ast
import sys
from pathlib import Path
from typing import List, Tuple


def check_relative_imports(file_path: Path) -> List[Tuple[int, str]]:
    """
    Check a Python file for relative imports.
    
    Returns a list of (line_number, import_statement) tuples for any relative imports found.
    """
    violations = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return violations
    
    # Quick check to avoid parsing if no relative imports
    if 'from .' not in content and 'from ..' not in content:
        return violations
    
    try:
        tree = ast.parse(content, filename=str(file_path))
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}")
        return violations
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level > 0:  # Relative import detected
                # Get the actual import statement from the source
                lines = content.split('\n')
                if hasattr(node, 'lineno') and 0 < node.lineno <= len(lines):
                    import_line = lines[node.lineno - 1].strip()
                    violations.append((node.lineno, import_line))
    
    return violations


def main():
    """Main entry point for the pre-commit hook."""
    if len(sys.argv) < 2:
        print("Usage: check_relative_imports.py <file1> [file2] ...")
        sys.exit(1)
    
    total_violations = 0
    files_with_violations = []
    
    for file_arg in sys.argv[1:]:
        file_path = Path(file_arg)
        
        # Skip non-Python files
        if not file_path.suffix == '.py':
            continue
        
        violations = check_relative_imports(file_path)
        
        if violations:
            total_violations += len(violations)
            files_with_violations.append(file_path)
            
            print(f"\n FAIL:  RELATIVE IMPORTS DETECTED in {file_path}:")
            print("=" * 60)
            for line_num, import_stmt in violations:
                print(f"  Line {line_num}: {import_stmt}")
            
            # Suggest the fix
            print(f"\n   IDEA:  Fix suggestion:")
            print(f"     Run: python scripts/fix_all_import_issues.py --absolute-only")
            print(f"     Or manually convert to absolute imports")
    
    if total_violations > 0:
        print("\n" + "=" * 80)
        print(f" FAIL:  COMMIT BLOCKED: Found {total_violations} relative import(s) in {len(files_with_violations)} file(s)")
        print("=" * 80)
        print("\n[U+1F4CB] IMPORT RULES (from CLAUDE.md):")
        print("  [U+2022] ALL Python files MUST use absolute imports")
        print("  [U+2022] NEVER use relative imports (. or ..)")
        print("  [U+2022] This rule overrides any existing patterns")
        print("\n PASS:  CORRECT EXAMPLE:")
        print("  from netra_backend.app.services.user_service import UserService")
        print("\n FAIL:  INCORRECT EXAMPLE:")
        print("  from ..services.user_service import UserService")
        print("\n[U+1F527] TO FIX:")
        print("  1. Run: python scripts/fix_all_import_issues.py --absolute-only")
        print("  2. Review and commit the changes")
        print("  3. Try your commit again")
        
        sys.exit(1)
    
    # No violations found
    sys.exit(0)


if __name__ == '__main__':
    main()
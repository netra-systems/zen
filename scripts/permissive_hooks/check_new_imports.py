#!/usr/bin/env python3
"""
Permissive hook to check for relative imports in new/modified files.
Only flags new relative imports in modified files.
"""

import ast
import sys
import subprocess
from pathlib import Path
from typing import Set, List, Tuple


def get_git_diff_lines(file_path: str) -> Set[int]:
    """Get line numbers that were added/modified in the file."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--unified=0", file_path],
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            errors='replace'
        )
        
        if not result.stdout:
            return set()
            
        modified_lines = set()
        for line in result.stdout.split('\n'):
            if line.startswith('@@'):
                # Parse the @@ -old_start,old_count +new_start,new_count @@ format
                try:
                    parts = line.split('+')[1].split('@@')[0].strip()
                    if ',' in parts:
                        start, count = map(int, parts.split(','))
                        modified_lines.update(range(start, start + count))
                    else:
                        # Single line change
                        modified_lines.add(int(parts))
                except (IndexError, ValueError):
                    continue
        
        return modified_lines
    except (subprocess.CalledProcessError, ValueError):
        # If we can't get diff, assume entire file is new
        return set()


def check_relative_imports(file_path: str, modified_lines: Set[int]) -> List[Tuple[int, str]]:
    """Check for relative imports in the specified lines."""
    violations = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content, filename=file_path)
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.ImportFrom,)) and node.level > 0:
                # This is a relative import
                line_no = node.lineno
                
                # Only flag if it's in a modified line
                if not modified_lines or line_no in modified_lines:
                    module = node.module or ''
                    level = '.' * node.level
                    import_str = f"from {level}{module} import ..."
                    violations.append((line_no, import_str))
    
    except (SyntaxError, FileNotFoundError):
        # Skip files with syntax errors or that don't exist
        pass
    
    return violations


def main():
    """Main entry point for the hook."""
    files = sys.argv[1:]
    python_files = [f for f in files if f.endswith('.py')]
    
    if not python_files:
        sys.exit(0)
    
    all_violations = []
    
    for file_path in python_files:
        # Check if file is new
        try:
            subprocess.run(
                ["git", "diff", "--cached", "--name-status"],
                capture_output=True,
                text=True,
                check=True
            )
            result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard", file_path],
                capture_output=True,
                text=True,
                check=True
            )
            is_new_file = bool(result.stdout.strip())
        except subprocess.CalledProcessError:
            is_new_file = False
        
        if is_new_file:
            # For new files, check all lines
            violations = check_relative_imports(file_path, set())
        else:
            # For existing files, only check modified lines
            modified_lines = get_git_diff_lines(file_path)
            if not modified_lines:
                continue
            violations = check_relative_imports(file_path, modified_lines)
        
        for line_no, import_str in violations:
            all_violations.append(f"{file_path}:{line_no}: {import_str}")
    
    if all_violations:
        print("Found relative imports in new/modified code:")
        for violation in all_violations:
            print(f"  {violation}")
        print("\nPlease use absolute imports instead.")
        print("Example: from netra_backend.app.services.foo import Bar")
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
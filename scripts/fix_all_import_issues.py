#!/usr/bin/env python3
"""
Comprehensive script to fix all import issues in the codebase.
Converts relative imports to absolute imports and removes sys.path manipulations.
"""

import argparse
import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class ImportFixer(ast.NodeTransformer):
    """AST transformer to convert relative imports to absolute imports."""
    
    def __init__(self, module_path: str, package_root: str):
        self.module_path = module_path
        self.package_root = package_root
        self.changes = []
        
    def visit_ImportFrom(self, node):
        """Transform relative imports to absolute imports."""
        if node.level > 0:  # Relative import
            # Calculate the absolute module path
            parts = self.module_path.split('.')
            
            # Go up 'level' directories
            if node.level <= len(parts):
                base_parts = parts[:-node.level]
                
                # Add the module if specified
                if node.module:
                    base_parts.append(node.module)
                
                # Create absolute import
                absolute_module = '.'.join(base_parts) if base_parts else None
                
                if absolute_module:
                    old_import = self._format_import(node)
                    node.level = 0
                    node.module = absolute_module
                    new_import = self._format_import(node)
                    self.changes.append((old_import, new_import))
        
        return node
    
    def _format_import(self, node):
        """Format an import node as a string."""
        if node.level > 0:
            dots = '.' * node.level
            module = node.module if node.module else ''
            return f"from {dots}{module} import ..."
        else:
            return f"from {node.module} import ..."


def get_module_path(file_path: Path, root_path: Path) -> str:
    """Get the module path for a Python file."""
    try:
        rel_path = file_path.relative_to(root_path)
        parts = list(rel_path.parts[:-1])  # Remove the file name
        parts.append(rel_path.stem)  # Add the module name without .py
        return '.'.join(parts)
    except ValueError:
        return ''


def fix_imports_in_file(file_path: Path, root_path: Path, dry_run: bool = False) -> List[str]:
    """Fix imports in a single file."""
    changes = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return [f"Error reading {file_path}: {e}"]
    
    # Check for relative imports
    if 'from .' not in content and 'from ..' not in content:
        return []
    
    # Parse the AST
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        return [f"Syntax error in {file_path}: {e}"]
    
    # Get module path
    module_path = get_module_path(file_path, root_path)
    
    # Transform the AST
    fixer = ImportFixer(module_path, str(root_path))
    fixer.visit(tree)
    
    if not fixer.changes:
        return []
    
    # Apply changes to the content
    new_content = content
    for old_import, new_import in fixer.changes:
        # Use regex to replace the actual import statements
        old_pattern = re.escape(old_import.replace('...', '.*'))
        old_pattern = old_pattern.replace(r'\.\*', r'[^)]+')
        
        # Find the actual import statement
        import_pattern = r'from\s+\.+(?:\w+(?:\.\w+)*)?\s+import\s+[^(\n]+(?:\([^)]+\))?'
        for match in re.finditer(import_pattern, content):
            matched_text = match.group()
            if matched_text.startswith('from .'):
                # Extract the imports part
                import_parts = matched_text.split(' import ', 1)
                if len(import_parts) == 2:
                    from_part, imports = import_parts
                    
                    # Count dots
                    dots = len(from_part.split()[1]) - len(from_part.split()[1].lstrip('.'))
                    
                    # Build the new import statement
                    if '.' * dots in from_part:
                        # Calculate absolute path
                        parts = module_path.split('.')
                        if dots <= len(parts):
                            base_parts = parts[:-dots]
                            
                            # Get the module part after dots
                            module_after_dots = from_part.split()[1][dots:]
                            if module_after_dots:
                                base_parts.append(module_after_dots)
                            
                            if base_parts:
                                new_from = f"from {'.'.join(base_parts)}"
                                new_statement = f"{new_from} import {imports}"
                                new_content = new_content.replace(matched_text, new_statement)
                                changes.append(f"{file_path}: {matched_text} -> {new_statement}")
    
    if not dry_run and new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
    
    return changes


def remove_sys_path_manipulation(file_path: Path, dry_run: bool = False) -> List[str]:
    """Remove sys.path manipulations from files."""
    changes = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        return [f"Error reading {file_path}: {e}"]
    
    new_lines = []
    skip_next = 0
    removed_lines = []
    in_path_block = False
    
    for i, line in enumerate(lines):
        if skip_next > 0:
            skip_next -= 1
            removed_lines.append(line.rstrip())
            continue
        
        # Check for start of path manipulation block
            # Look ahead to see if this is part of sys.path manipulation
            if i + 1 < len(lines) and 'sys.path' in lines[i + 1]:
                in_path_block = True
                removed_lines.append(line.rstrip())
                continue
            elif i + 2 < len(lines) and 'sys.path' in lines[i + 2]:
                in_path_block = True
                removed_lines.append(line.rstrip())
                continue
        
        # Check for sys.path manipulations
            removed_lines.append(line.rstrip())
            in_path_block = False
            
            # Check if it's part of a multi-line statement
            if line.rstrip().endswith('\\') or '(' in line and ')' not in line:
                # Find the end of the statement
                for j in range(i + 1, len(lines)):
                    removed_lines.append(lines[j].rstrip())
                    skip_next += 1
                    if ')' in lines[j] or not lines[j].rstrip().endswith('\\'):
                        break
            continue
        
        # Check for path checking conditions
        if in_path_block and ('not in sys.path' in line or 'in sys.path' in line):
            removed_lines.append(line.rstrip())
            in_path_block = False
            continue
        
        # Keep the line
        new_lines.append(line)
        in_path_block = False
    
    if removed_lines:
        for line in removed_lines:
            changes.append(f"  - {line}")
        
        if not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
    
    return changes


def fix_pytest_config(dry_run: bool = False) -> List[str]:
    """Fix pytest configuration files to remove relative path support."""
    changes = []
    
    pytest_files = [
        'pytest.ini',
        'netra_backend/pytest.ini',
        'auth_service/pytest.ini',
    ]
    
    for pytest_file in pytest_files:
        if not os.path.exists(pytest_file):
            continue
            
        with open(pytest_file, 'r') as f:
            lines = f.readlines()
        
        new_lines = []
        for line in lines:
            # Remove pythonpath configuration that enables relative imports
            if line.strip().startswith('pythonpath'):
                changes.append(f"{pytest_file}: Removed line: {line.strip()}")
                continue
            new_lines.append(line)
        
        if new_lines != lines and not dry_run:
            with open(pytest_file, 'w') as f:
                f.writelines(new_lines)
    
    return changes


def main():
    parser = argparse.ArgumentParser(description='Fix import issues in the codebase')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without modifying files')
    parser.add_argument('--absolute-only', action='store_true', help='Only fix relative imports, keep sys.path for compatibility')
    parser.add_argument('--verify', action='store_true', help='Verify all imports after fixing')
    parser.add_argument('--path', default='.', help='Path to scan (default: current directory)')
    
    args = parser.parse_args()
    
    root_path = Path(args.path).resolve()
    all_changes = []
    
    print("=" * 80)
    print("Import Issue Fixer")
    print("=" * 80)
    
    # Step 1: Fix pytest configuration
    if not args.absolute_only:
        print("\n1. Fixing pytest configuration files...")
        changes = fix_pytest_config(args.dry_run)
        all_changes.extend(changes)
        print(f"   Fixed {len(changes)} configuration issues")
    
    # Step 2: Find all Python files
    print("\n2. Scanning for Python files...")
    python_files = []
    for root, dirs, files in os.walk(root_path):
        # Skip virtual environments and other non-code directories
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'venv', '.venv', 'node_modules', '.pytest_cache'}]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    
    print(f"   Found {len(python_files)} Python files")
    
    # Step 3: Fix relative imports
    print("\n3. Fixing relative imports...")
    import_changes = []
    for file_path in python_files:
        changes = fix_imports_in_file(file_path, root_path, args.dry_run)
        import_changes.extend(changes)
    
    all_changes.extend(import_changes)
    print(f"   Fixed {len(import_changes)} import issues")
    
    # Step 4: Remove sys.path manipulations (optional)
    if not args.absolute_only:
        print("\n4. Removing sys.path manipulations...")
        sys_path_changes = []
        for file_path in python_files:
            # Process ALL Python files for atomic remediation
            changes = remove_sys_path_manipulation(file_path, args.dry_run)
            sys_path_changes.extend(changes)
        
        all_changes.extend(sys_path_changes)
        print(f"   Removed {len(sys_path_changes)} sys.path manipulations")
    
    # Step 5: Summary
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    
    if all_changes:
        print(f"\nTotal changes: {len(all_changes)}")
        if args.dry_run:
            print("\nChanges that would be made:")
            for change in all_changes[:20]:  # Show first 20 changes
                print(f"  {change}")
            if len(all_changes) > 20:
                print(f"  ... and {len(all_changes) - 20} more")
            print("\nRun without --dry-run to apply these changes")
        else:
            print("\nAll changes have been applied successfully!")
            print("Next steps:")
            print("1. Run tests to verify everything still works:")
            print("   python unified_test_runner.py --level integration --no-coverage --fast-fail")
            print("2. Commit the changes")
    else:
        print("\nNo changes needed - all imports are already absolute!")
    
    # Step 6: Verification (optional)
    if args.verify and not args.dry_run:
        print("\n" + "=" * 80)
        print("Verification")
        print("=" * 80)
        
        print("\nChecking for remaining relative imports...")
        remaining = 0
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'from .' in content or 'from ..' in content:
                        # Check if it's in a string or comment
                        for line in content.split('\n'):
                            stripped = line.strip()
                            if stripped.startswith('#'):
                                continue
                            if 'from .' in line or 'from ..' in line:
                                if '"' not in line and "'" not in line:  # Not in a string
                                    print(f"  WARNING: {file_path} still has relative imports")
                                    remaining += 1
                                    break
            except:
                pass
        
        if remaining == 0:
            print("  [U+2713] All relative imports have been successfully converted!")
        else:
            print(f"  [U+2717] {remaining} files still have relative imports")
            print("    These may need manual intervention")


if __name__ == '__main__':
    main()
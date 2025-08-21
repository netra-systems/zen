#!/usr/bin/env python3
"""
Import Fix Tool for Netra Apex
Automatically fixes import issues, especially converting relative to absolute imports.
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
import argparse
import shutil
from collections import defaultdict

class ImportFixer:
    def __init__(self, root_path: Path, dry_run: bool = False):
        self.root_path = root_path
        self.dry_run = dry_run
        self.module_map = {}
        self.fixed_files = []
        self.error_files = []
        
        # Build module map
        self._build_module_map()
        
    def _build_module_map(self):
        """Build a map of all available modules in the project."""
        for py_file in self.root_path.rglob('*.py'):
            if '__pycache__' in str(py_file):
                continue
                
            # Get module path
            try:
                rel_path = py_file.relative_to(self.root_path)
                parts = list(rel_path.parts)
                
                # Handle __init__.py files
                if parts[-1] == '__init__.py':
                    parts = parts[:-1]
                else:
                    # Remove .py extension
                    parts[-1] = parts[-1][:-3]
                    
                if parts:
                    module_path = '.'.join(parts)
                    self.module_map[module_path] = py_file
                    
            except Exception:
                continue
    
    def _resolve_relative_import(self, file_path: Path, module: str, level: int, 
                                 import_items: List[str]) -> Optional[str]:
        """Resolve a relative import to an absolute import."""
        try:
            # Get the current module's path
            rel_path = file_path.relative_to(self.root_path)
            parts = list(rel_path.parts)
            
            # Remove the file name
            if parts[-1].endswith('.py'):
                if parts[-1] == '__init__.py':
                    parts = parts[:-1]
                else:
                    parts[-1] = parts[-1][:-3]
            
            # Go up 'level' directories for relative imports
            if level > 0:
                if level > len(parts):
                    return None
                parts = parts[:-level]
            
            # Add the module parts if specified
            if module:
                parts.extend(module.split('.'))
            
            # Create the absolute module path
            absolute_module = '.'.join(parts)
            
            # Verify the module exists
            if absolute_module in self.module_map:
                return absolute_module
            
            # Check if we're importing from a package
            package_path = '.'.join(parts)
            if package_path in self.module_map:
                return package_path
                
            # Check if any of the import items exist as submodules
            for item in import_items:
                test_module = f"{absolute_module}.{item}" if absolute_module else item
                if test_module in self.module_map:
                    return absolute_module if absolute_module else None
                    
            # For test files, try common patterns
            if 'tests' in parts or 'test' in parts[0]:
                # Try without the tests prefix
                if parts and parts[0] in ['tests', 'test']:
                    alt_parts = parts[1:]
                    if alt_parts:
                        alt_module = '.'.join(alt_parts)
                        if alt_module in self.module_map:
                            return alt_module
                            
            return absolute_module if absolute_module else None
            
        except Exception as e:
            print(f"Error resolving import in {file_path}: {e}")
            return None
    
    def fix_file(self, file_path: Path) -> bool:
        """Fix imports in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                original_content = content
            
            # Parse the AST
            tree = ast.parse(content, filename=str(file_path))
            
            # Track changes
            changes = []
            lines = content.splitlines()
            
            # Find and fix imports
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level > 0:
                    # This is a relative import
                    import_items = [alias.name for alias in node.names]
                    resolved = self._resolve_relative_import(
                        file_path, node.module, node.level, import_items
                    )
                    
                    if resolved is not None:
                        # Build the new import statement
                        if node.names[0].name == '*':
                            new_import = f"from {resolved} import *"
                        else:
                            items = ', '.join(
                                f"{alias.name} as {alias.asname}" if alias.asname 
                                else alias.name 
                                for alias in node.names
                            )
                            new_import = f"from {resolved} import {items}"
                        
                        # Record the change
                        line_num = node.lineno - 1
                        if line_num < len(lines):
                            old_line = lines[line_num]
                            changes.append((line_num, old_line, new_import))
            
            # Apply changes if any
            if changes:
                # Sort changes by line number in reverse order
                changes.sort(key=lambda x: x[0], reverse=True)
                
                for line_num, old_line, new_line in changes:
                    # Preserve indentation
                    indent = len(old_line) - len(old_line.lstrip())
                    new_line = ' ' * indent + new_line
                    lines[line_num] = new_line
                
                new_content = '\n'.join(lines)
                if lines and not new_content.endswith('\n'):
                    new_content += '\n'
                
                # Save the file
                if not self.dry_run:
                    # Create backup
                    backup_path = file_path.with_suffix('.py.bak')
                    shutil.copy2(file_path, backup_path)
                    
                    # Write fixed content
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    # Remove backup if successful
                    backup_path.unlink()
                
                self.fixed_files.append((file_path, len(changes)))
                
                if self.dry_run:
                    print(f"Would fix {len(changes)} imports in {file_path}")
                    for line_num, old_line, new_line in changes:
                        print(f"  Line {line_num + 1}:")
                        print(f"    - {old_line.strip()}")
                        print(f"    + {new_line.strip()}")
                else:
                    print(f"Fixed {len(changes)} imports in {file_path}")
                
                return True
            
            return False
            
        except SyntaxError as e:
            self.error_files.append((file_path, f"Syntax error: {e}"))
            return False
        except Exception as e:
            self.error_files.append((file_path, str(e)))
            return False
    
    def fix_duplicate_imports(self, file_path: Path) -> bool:
        """Remove duplicate import statements from a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            seen_imports = set()
            new_lines = []
            removed_count = 0
            
            for line in lines:
                # Simple check for import statements
                stripped = line.strip()
                if stripped.startswith(('import ', 'from ')):
                    # Normalize the import statement
                    import_key = ' '.join(stripped.split())
                    if import_key in seen_imports:
                        removed_count += 1
                        continue  # Skip duplicate
                    seen_imports.add(import_key)
                
                new_lines.append(line)
            
            if removed_count > 0:
                if not self.dry_run:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(new_lines)
                print(f"Removed {removed_count} duplicate imports from {file_path}")
                return True
                
            return False
            
        except Exception as e:
            self.error_files.append((file_path, f"Error fixing duplicates: {e}"))
            return False
    
    def fix_directory(self, directory: Path, pattern: str = "*.py", 
                     fix_duplicates: bool = True) -> Dict[str, int]:
        """Fix all Python files in a directory."""
        stats = {
            'files_processed': 0,
            'files_fixed': 0,
            'imports_fixed': 0,
            'duplicates_removed': 0,
            'errors': 0
        }
        
        py_files = list(directory.rglob(pattern))
        total_files = len(py_files)
        
        print(f"Processing {total_files} Python files...")
        
        for i, file_path in enumerate(py_files, 1):
            # Skip __pycache__ and backup files
            if '__pycache__' in str(file_path) or file_path.suffix == '.bak':
                continue
            
            if i % 100 == 0:
                print(f"Progress: {i}/{total_files} files...")
            
            stats['files_processed'] += 1
            
            # Fix relative imports
            if self.fix_file(file_path):
                stats['files_fixed'] += 1
            
            # Fix duplicate imports if requested
            if fix_duplicates:
                if self.fix_duplicate_imports(file_path):
                    stats['duplicates_removed'] += 1
        
        # Count total imports fixed
        stats['imports_fixed'] = sum(count for _, count in self.fixed_files)
        stats['errors'] = len(self.error_files)
        
        return stats
    
    def generate_report(self) -> str:
        """Generate a report of fixes made."""
        report = []
        report.append("=" * 80)
        report.append("IMPORT FIX REPORT")
        report.append("=" * 80)
        report.append("")
        
        if self.fixed_files:
            report.append(f"Files with fixed imports: {len(self.fixed_files)}")
            report.append("-" * 40)
            for file_path, count in self.fixed_files[:20]:
                rel_path = file_path.relative_to(self.root_path)
                report.append(f"  {rel_path}: {count} imports fixed")
            if len(self.fixed_files) > 20:
                report.append(f"  ... and {len(self.fixed_files) - 20} more files")
            report.append("")
        
        if self.error_files:
            report.append(f"Files with errors: {len(self.error_files)}")
            report.append("-" * 40)
            for file_path, error in self.error_files[:10]:
                rel_path = file_path.relative_to(self.root_path)
                report.append(f"  {rel_path}: {error}")
            if len(self.error_files) > 10:
                report.append(f"  ... and {len(self.error_files) - 10} more files")
            report.append("")
        
        return '\n'.join(report)

def main():
    parser = argparse.ArgumentParser(description='Fix Python import issues')
    parser.add_argument('path', nargs='?', default='.',
                       help='Path to fix (default: current directory)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be fixed without making changes')
    parser.add_argument('--no-duplicates', action='store_true',
                       help='Do not fix duplicate imports')
    parser.add_argument('--focus', choices=['tests', 'backend', 'all'], default='all',
                       help='Focus on specific part of codebase')
    
    args = parser.parse_args()
    
    # Setup paths
    root_path = Path(args.path).resolve()
    
    # Add project root to Python path
    if str(root_path) not in sys.path:
        sys.path.insert(0, str(root_path))
    
    # Initialize fixer
    fixer = ImportFixer(root_path, dry_run=args.dry_run)
    
    # Determine what to fix
    if args.focus == 'tests':
        fix_paths = [root_path / 'tests']
    elif args.focus == 'backend':
        fix_paths = [root_path / 'netra_backend']
    else:
        fix_paths = [root_path]
    
    # Fix imports
    total_stats = {
        'files_processed': 0,
        'files_fixed': 0,
        'imports_fixed': 0,
        'duplicates_removed': 0,
        'errors': 0
    }
    
    for path in fix_paths:
        if path.exists():
            print(f"\nFixing imports in {path}...")
            stats = fixer.fix_directory(
                path, 
                fix_duplicates=not args.no_duplicates
            )
            
            # Aggregate stats
            for key in total_stats:
                total_stats[key] += stats[key]
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Files processed: {total_stats['files_processed']}")
    print(f"Files fixed: {total_stats['files_fixed']}")
    print(f"Imports fixed: {total_stats['imports_fixed']}")
    if not args.no_duplicates:
        print(f"Duplicate imports removed: {total_stats['duplicates_removed']}")
    print(f"Errors encountered: {total_stats['errors']}")
    
    # Print detailed report
    if fixer.fixed_files or fixer.error_files:
        print("\n" + fixer.generate_report())
    
    # Return exit code
    return 0 if total_stats['errors'] == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
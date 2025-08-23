#!/usr/bin/env python3
"""
Fix import paths in E2E tests to use proper absolute imports

This script fixes imports in E2E tests that incorrectly import from tests.* 
instead of tests.e2e.* (for files in the E2E directory)
"""
import os
import re
from pathlib import Path

def fix_import_paths_in_file(file_path: Path) -> bool:
    """Fix import paths in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern to find imports like: from tests.module_name import ...
        # But NOT tests.e2e.* (which are correct) or tests.* within comments
        lines = content.split('\n')
        modified_lines = []
        
        for line in lines:
            # Skip commented lines
            if line.strip().startswith('#'):
                modified_lines.append(line)
                continue
            
            # Pattern to match: from tests.something import ... (but not tests.e2e.*)
            if re.match(r'^\s*from\s+tests\.(?!e2e)[a-zA-Z_][a-zA-Z0-9_]*', line):
                # This is a problematic import - check what it's trying to import
                match = re.match(r'^(\s*from\s+tests\.)([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)', line)
                if match:
                    prefix = match.group(1)  # "from tests."
                    module_path = match.group(2)  # "module_name" or "submodule.name"
                    
                    # Check if this might be referring to something in the e2e directory
                    potential_e2e_path = Path(file_path).parent.parent / 'e2e' / (module_path.replace('.', '/') + '.py')
                    potential_e2e_init = Path(file_path).parent.parent / 'e2e' / module_path.replace('.', '/') / '__init__.py'
                    
                    # Also check for just the first part of the module path
                    first_module = module_path.split('.')[0]
                    potential_first_module = Path(file_path).parent.parent / 'e2e' / (first_module + '.py')
                    
                    if (potential_e2e_path.exists() or 
                        potential_e2e_init.exists() or 
                        potential_first_module.exists()):
                        # Replace with tests.e2e.* import
                        new_line = line.replace(f'from tests.{module_path}', f'from tests.e2e.{module_path}')
                        print(f"  Fixed import: {line.strip()} -> {new_line.strip()}")
                        line = new_line
            
            modified_lines.append(line)
        
        content = '\n'.join(modified_lines)
        
        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix import paths in all E2E test files."""
    project_root = Path(__file__).parent
    e2e_dir = project_root / 'tests' / 'e2e'
    
    files_changed = []
    files_processed = 0
    
    # Find all Python files in the E2E directory
    for py_file in e2e_dir.rglob('*.py'):
        if '__pycache__' in str(py_file):
            continue
        
        files_processed += 1
        
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for problematic import patterns
            if re.search(r'^\s*from\s+tests\.(?!e2e)[a-zA-Z_]', content, re.MULTILINE):
                print(f"Processing: {py_file.relative_to(project_root)}")
                if fix_import_paths_in_file(py_file):
                    files_changed.append(py_file.relative_to(project_root))
                    print(f"  ✓ Fixed import paths")
                else:
                    print(f"  - No changes needed")
        except Exception as e:
            print(f"Error reading {py_file}: {e}")
    
    print(f"\nProcessed {files_processed} files")
    print(f"Modified {len(files_changed)} files")
    
    if files_changed:
        print("\nModified files:")
        for file_path in files_changed:
            print(f"  - {file_path}")

if __name__ == '__main__':
    main()
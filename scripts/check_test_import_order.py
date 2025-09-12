"""Check that setup_test_path() is called before any netra_backend imports in test files."""

import ast
import sys
from pathlib import Path


def check_import_order(file_path):
    """Check if setup_test_path() is called before netra_backend imports."""
    with open(file_path, 'r', encoding='utf-8') as f:
        source = f.read()
    
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None, "Failed to parse file"
    
    setup_line = None
    first_netra_import_line = None
    has_setup_import = False
    
    for node in ast.walk(tree):
        # Check for setup_test_path import
        if isinstance(node, ast.ImportFrom):
            if node.module == 'netra_backend.tests.test_utils':
                for alias in node.names:
                    if alias.name == 'setup_test_path':
                        has_setup_import = True
                        break
        
        # Check for setup_test_path() call
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Name) and node.value.func.id == 'setup_test_path':
                setup_line = node.lineno
        
        # Check for netra_backend imports (excluding test_utils)
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith('netra_backend') and 'test_utils' not in node.module:
                    if first_netra_import_line is None:
                        first_netra_import_line = node.lineno
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith('netra_backend'):
                        if first_netra_import_line is None:
                            first_netra_import_line = node.lineno
    
    if not has_setup_import:
        return None, "No setup_test_path import found"
    
    if setup_line is None:
        return None, "setup_test_path() not called"
    
    if first_netra_import_line is None:
        return True, "No netra_backend imports found"
    
    if setup_line < first_netra_import_line:
        return True, f"OK: setup_test_path() at line {setup_line}, first import at line {first_netra_import_line}"
    else:
        return False, f"ERROR: setup_test_path() at line {setup_line} comes AFTER first import at line {first_netra_import_line}"

def main():
    # Find all test files
    test_dir = Path('netra_backend/tests')
    test_files = list(test_dir.rglob('test_*.py'))
    
    issues = []
    ok_count = 0
    skip_count = 0
    
    for test_file in test_files:
        result, message = check_import_order(test_file)
        
        if result is None:
            # File doesn't use setup_test_path, that's fine
            skip_count += 1
        elif result:
            ok_count += 1
        else:
            issues.append((test_file, message))
    
    print(f"Checked {len(test_files)} test files:")
    print(f"  - {ok_count} files have correct import order")
    print(f"  - {skip_count} files don't use setup_test_path")
    print(f"  - {len(issues)} files have import order issues")
    
    if issues:
        print("\nFiles with import order issues:")
        for file_path, message in issues[:10]:  # Show first 10 issues
            print(f"  {file_path}: {message}")
        
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more files")
        
        return 1
    else:
        print("\n[U+2713] All files have correct import order!")
        return 0

if __name__ == '__main__':
    sys.exit(main())
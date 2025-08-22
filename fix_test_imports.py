#!/usr/bin/env python
"""
Fix incorrect test imports in netra_backend test files.
This script fixes imports that incorrectly use absolute imports for test modules
when they should use relative imports.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

def fix_test_imports(file_path: Path) -> Tuple[bool, List[str]]:
    """
    Fix test imports in a single file.
    Returns (modified, changes_made).
    """
    changes = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            original_content = content
    except Exception as e:
        return False, [f"Error reading file: {e}"]
    
    # Pattern to match imports from netra_backend.tests
    pattern = r'^from netra_backend\.tests\.([a-z_]+)\.([a-z_]+) import'
    
    lines = content.split('\n')
    modified_lines = []
    modified = False
    
    for line in lines:
        original_line = line
        
        # Check if this is a test-to-test import that should be relative
        match = re.match(pattern, line)
        if match:
            # Get the current file's directory relative to tests/
            file_dir = file_path.parent
            tests_dir = Path('netra_backend/tests')
            
            # If the file is in netra_backend/tests, convert to relative import
            if 'netra_backend\\tests' in str(file_path):
                import_path = match.group(1)
                module_name = match.group(2)
                
                # Get the relative path from current file to target
                current_subdir = file_dir.name
                
                if import_path == current_subdir:
                    # Same directory - use relative import
                    new_line = re.sub(
                        r'^from netra_backend\.tests\.[a-z_]+\.',
                        'from .',
                        line
                    )
                    if new_line != line:
                        modified = True
                        changes.append(f"Line {lines.index(original_line) + 1}: {line} -> {new_line}")
                        line = new_line
        
        modified_lines.append(line)
    
    if modified:
        new_content = '\n'.join(modified_lines)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True, changes
        except Exception as e:
            return False, [f"Error writing file: {e}"]
    
    return False, []


def main():
    """Main function to fix all test imports."""
    project_root = Path(__file__).parent
    tests_dir = project_root / 'netra_backend' / 'tests'
    
    if not tests_dir.exists():
        print(f"Tests directory not found: {tests_dir}")
        return
    
    # Collect all Python test files
    test_files = list(tests_dir.rglob('test_*.py'))
    
    print(f"Found {len(test_files)} test files to check")
    
    total_modified = 0
    all_changes = []
    
    for test_file in test_files:
        modified, changes = fix_test_imports(test_file)
        if modified:
            total_modified += 1
            all_changes.append({
                'file': str(test_file.relative_to(project_root)),
                'changes': changes
            })
            print(f"[FIXED] {test_file.relative_to(project_root)}")
    
    # Write report
    report_path = project_root / 'test_import_fixes_report.json'
    import json
    
    report = {
        'total_files_checked': len(test_files),
        'total_files_modified': total_modified,
        'files_modified': all_changes
    }
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nSummary:")
    print(f"  - Files checked: {len(test_files)}")
    print(f"  - Files modified: {total_modified}")
    print(f"  - Report saved to: {report_path}")
    
    # Additional check for the specific issue mentioned
    parameterized_file = project_root / 'netra_backend' / 'tests' / 'agents' / 'test_example_prompts_parameterized.py'
    if parameterized_file.exists():
        print(f"\nChecking specific file: test_example_prompts_parameterized.py")
        with open(parameterized_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'from netra_backend.tests.agents' in content:
                print("  [WARNING] Still contains absolute test imports")
            else:
                print("  [OK] No absolute test imports found")


if __name__ == '__main__':
    main()
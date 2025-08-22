#!/usr/bin/env python
"""
Fix all incorrect test imports in netra_backend test files.
This includes:
1. from netra_backend.tests.* -> relative imports
2. from tests.* -> relative imports
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
    
    lines = content.split('\n')
    modified_lines = []
    modified = False
    
    for i, line in enumerate(lines):
        original_line = line
        
        # Pattern 1: from netra_backend.tests.X.Y import
        match1 = re.match(r'^from netra_backend\.tests\.([a-z_]+)\.([a-z_]+) import', line)
        if match1:
            # Convert to relative import
            new_line = re.sub(
                r'^from netra_backend\.tests\.[a-z_]+\.',
                'from .',
                line
            )
            if new_line != line:
                modified = True
                changes.append(f"Line {i + 1}: {line} -> {new_line}")
                line = new_line
        
        # Pattern 2: from tests.X.Y import (without netra_backend prefix)
        match2 = re.match(r'^from tests\.([a-z_]+)\.([a-z_]+) import', line)
        if match2:
            # Convert to relative import
            import_path = match2.group(1)
            module_name = match2.group(2)
            
            # Get the current file's directory
            file_dir = file_path.parent.name
            
            if import_path == file_dir:
                # Same directory - use relative import
                new_line = re.sub(
                    r'^from tests\.[a-z_]+\.',
                    'from .',
                    line
                )
            else:
                # Different directory - use relative parent import
                new_line = re.sub(
                    r'^from tests\.',
                    'from ..',
                    line
                )
            
            if new_line != line:
                modified = True
                changes.append(f"Line {i + 1}: {line} -> {new_line}")
                line = new_line
        
        # Pattern 3: from tests.X import (without subdirectory)
        match3 = re.match(r'^from tests\.([a-z_]+) import', line)
        if match3 and '.' not in match3.group(1):
            # This is importing from tests directory directly
            new_line = re.sub(
                r'^from tests\.',
                'from ..',
                line
            )
            if new_line != line:
                modified = True
                changes.append(f"Line {i + 1}: {line} -> {new_line}")
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
    test_files = list(tests_dir.rglob('*.py'))
    
    print(f"Found {len(test_files)} Python files to check")
    
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
    report_path = project_root / 'all_test_import_fixes_report.json'
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


if __name__ == '__main__':
    main()
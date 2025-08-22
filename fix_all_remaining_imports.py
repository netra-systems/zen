#!/usr/bin/env python
"""
Fix ALL remaining import issues in test files.
"""

import re
from pathlib import Path
from typing import List, Tuple

def fix_imports_in_file(file_path: Path) -> Tuple[bool, List[str]]:
    """Fix all import issues in a single file."""
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
        
        # Fix netra_backend.tests.X imports
        if 'from netra_backend.tests.' in line:
            # Extract what's being imported from
            match = re.match(r'^from netra_backend\.tests\.([a-zA-Z_]+)', line)
            if match:
                module = match.group(1)
                # Convert to relative import
                if module in ['test_fixtures', 'test_helpers', 'test_database', 'conftest', 'test_utils']:
                    new_line = line.replace('from netra_backend.tests.', 'from ..')
                else:
                    # For subdirectories
                    new_line = line.replace('from netra_backend.tests.', 'from .')
                
                if new_line != line:
                    modified = True
                    changes.append(f"Line {i + 1}: {line} -> {new_line}")
                    line = new_line
        
        # Fix tests.X imports (without netra_backend prefix)
        elif line.startswith('from tests.'):
            # Determine relative path
            file_dir = file_path.parent
            tests_dir = Path('netra_backend/tests')
            
            # Extract what's being imported from
            match = re.match(r'^from tests\.([a-zA-Z_]+)', line)
            if match:
                module = match.group(1)
                
                # Check if it's a direct test module or subdirectory
                if module in ['test_fixtures', 'test_helpers', 'test_database', 'conftest', 'test_utils']:
                    # Root level test modules
                    new_line = line.replace('from tests.', 'from ..')
                elif '.' in line[11:]:  # Has subdirectory
                    # Subdirectory imports
                    parts = line[11:].split('.')
                    if file_dir.name == parts[0]:
                        # Same directory
                        new_line = 'from .' + line[11 + len(parts[0]):]
                    else:
                        # Different directory
                        new_line = line.replace('from tests.', 'from ..')
                else:
                    # Direct import from tests
                    new_line = line.replace('from tests.', 'from ..')
                
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
    """Main function to fix all import issues."""
    project_root = Path(__file__).parent
    tests_dir = project_root / 'netra_backend' / 'tests'
    
    if not tests_dir.exists():
        print(f"Tests directory not found: {tests_dir}")
        return
    
    # Collect all Python files in tests
    test_files = list(tests_dir.rglob('*.py'))
    
    print(f"Checking {len(test_files)} Python files for import issues...")
    
    total_modified = 0
    all_changes = []
    
    for test_file in test_files:
        modified, changes = fix_imports_in_file(test_file)
        if modified:
            total_modified += 1
            all_changes.append({
                'file': str(test_file.relative_to(project_root)),
                'changes': changes
            })
            print(f"[FIXED] {test_file.relative_to(project_root)}")
    
    # Write report
    report_path = project_root / 'final_import_fixes_report.json'
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
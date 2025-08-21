"""Remove duplicate test setup code from all test files.

This script finds and removes the duplicate sys.path manipulation code
that appears in hundreds of test files, ensuring only the centralized
setup_test_path() function is used.
"""

import re
from pathlib import Path


def remove_duplicate_setup(file_path):
    """Remove duplicate PROJECT_ROOT setup code from a test file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match the duplicate block (with optional comment)
    # This matches the block with or without the "Add project root to path" comment
    pattern = r'(?:# Add project root to path\n)?import sys\nfrom pathlib import Path\nPROJECT_ROOT = Path\(__file__\)\.parent\.parent\.parent\nif str\(PROJECT_ROOT\) not in sys\.path:\n    sys\.path\.insert\(0, str\(PROJECT_ROOT\)\)\n\n?\n?'
    
    # Check if file has the duplicate pattern
    if re.search(pattern, content):
        # Remove the duplicate block
        new_content = re.sub(pattern, '', content)
        
        # Only write if content actually changed
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
    return False


def main():
    """Main function to process all test files."""
    project_root = Path(__file__).parent.parent
    test_dirs = [
        project_root / 'netra_backend' / 'tests',
        project_root / 'auth_service' / 'tests'
    ]
    
    total_files = 0
    modified_files = 0
    
    for test_dir in test_dirs:
        if not test_dir.exists():
            print(f"Directory not found: {test_dir}")
            continue
            
        # Find all Python test files
        test_files = list(test_dir.rglob('test_*.py'))
        
        for file_path in test_files:
            # Skip test_utils.py as it contains the implementation
            if file_path.name == 'test_utils.py':
                continue
                
            total_files += 1
            if remove_duplicate_setup(file_path):
                modified_files += 1
                print(f"Fixed: {file_path.relative_to(project_root)}")
    
    print(f"\nProcessed {total_files} files, modified {modified_files} files")
    print("Duplicate test setup code has been removed.")


if __name__ == '__main__':
    main()
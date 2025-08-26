#!/usr/bin/env python3
"""
Add pytest markers to test files based on their directory location.
This ensures proper test categorization for compliance and test runner.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Test infrastructure compliance and reporting accuracy
- Value Impact: Enables accurate test metrics and compliance scoring
- Strategic Impact: Improves development velocity through proper test organization
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Test category mappings based on directory structure
CATEGORY_MAPPINGS = {
    'tests/e2e': 'e2e',
    'tests/integration': 'integration', 
    'tests/unit': 'unit',
    'tests/smoke': 'smoke',
    'tests/performance': 'performance',
    'tests/websocket': 'websocket',
    'tests/api': 'api',
    'tests/frontend': 'frontend',
    'tests/database': 'database',
    'tests/e2e/integration': 'e2e',  # Subdirectories inherit parent category
    'tests/e2e/journeys': 'e2e',
    'tests/e2e/performance': 'e2e',
    'tests/e2e/resilience': 'e2e',
    'tests/e2e/websocket': 'e2e',
    'tests/e2e/rapid_message': 'e2e',
    'tests/e2e/resource_isolation': 'e2e',
    'tests/e2e/agent_isolation': 'e2e'
}


def needs_pytest_marker(content: str, marker: str) -> bool:
    """Check if file already has the specified pytest marker."""
    # Check for existing marker
    marker_pattern = rf'@pytest\.mark\.{marker}'
    if re.search(marker_pattern, content):
        return False
    
    # Check if file has test functions/classes
    has_tests = bool(
        re.search(r'^def test_', content, re.MULTILINE) or
        re.search(r'^class Test', content, re.MULTILINE) or
        re.search(r'^async def test_', content, re.MULTILINE)
    )
    
    return has_tests


def add_pytest_import(content: str) -> str:
    """Add pytest import if not present."""
    if 'import pytest' not in content:
        # Check if there are any imports
        import_match = re.search(r'^(import |from .+ import)', content, re.MULTILINE)
        if import_match:
            # Add after first import block
            insert_pos = import_match.end()
            while insert_pos < len(content) and content[insert_pos] in '\n':
                insert_pos += 1
            insert_pos = content.rfind('\n', 0, insert_pos) + 1
            return content[:insert_pos] + 'import pytest\n' + content[insert_pos:]
        else:
            # Add at beginning with module docstring handling
            if content.startswith('"""'):
                end_docstring = content.find('"""', 3) + 3
                return content[:end_docstring] + '\n\nimport pytest\n' + content[end_docstring:].lstrip()
            else:
                return 'import pytest\n\n' + content
    return content


def add_marker_to_test(content: str, marker: str) -> str:
    """Add pytest marker to all test functions and classes."""
    lines = content.split('\n')
    modified_lines = []
    
    for i, line in enumerate(lines):
        modified_lines.append(line)
        
        # Check if this is a test function or class definition
        if (line.startswith('def test_') or 
            line.startswith('async def test_') or 
            line.startswith('class Test')):
            
            # Check if previous line already has a marker
            if i > 0 and '@pytest.mark.' in lines[i-1]:
                continue
                
            # Find the indentation of the current line
            indent = len(line) - len(line.lstrip())
            marker_line = ' ' * indent + f'@pytest.mark.{marker}'
            
            # Insert marker before the function/class definition
            modified_lines.insert(-1, marker_line)
    
    return '\n'.join(modified_lines)


def process_file(file_path: Path, marker: str) -> Tuple[bool, str]:
    """Process a single test file to add pytest markers."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not needs_pytest_marker(content, marker):
            return False, f"Already has @pytest.mark.{marker} or no tests"
        
        # Add pytest import if needed
        content = add_pytest_import(content)
        
        # Add markers to test functions/classes
        modified_content = add_marker_to_test(content, marker)
        
        # Write back only if content changed
        if modified_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            return True, f"Added @pytest.mark.{marker}"
        
        return False, "No changes needed"
        
    except Exception as e:
        return False, f"Error: {e}"


def process_directory(directory: Path, marker: str) -> Tuple[int, int, List[str]]:
    """Process all test files in a directory."""
    processed = 0
    modified = 0
    errors = []
    
    # Find all test_*.py files
    test_files = list(directory.rglob('test_*.py'))
    
    for test_file in test_files:
        # Skip __pycache__ directories
        if '__pycache__' in str(test_file):
            continue
            
        processed += 1
        success, message = process_file(test_file, marker)
        
        if success:
            modified += 1
            print(f"[OK] {test_file.relative_to(directory.parent.parent)}: {message}")
        elif "Error" in message:
            errors.append(f"{test_file}: {message}")
        else:
            print(f"[--] {test_file.relative_to(directory.parent.parent)}: {message}")
    
    return processed, modified, errors


def main():
    """Main entry point."""
    # Get project root
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent
    
    print("=" * 80)
    print("PYTEST MARKER ADDITION TOOL")
    print("=" * 80)
    print()
    
    total_processed = 0
    total_modified = 0
    all_errors = []
    
    # Process each test directory
    for dir_pattern, marker in CATEGORY_MAPPINGS.items():
        test_dir = project_root / dir_pattern
        
        if test_dir.exists() and test_dir.is_dir():
            print(f"\nProcessing {dir_pattern} -> @pytest.mark.{marker}")
            print("-" * 40)
            
            processed, modified, errors = process_directory(test_dir, marker)
            total_processed += processed
            total_modified += modified
            all_errors.extend(errors)
            
            print(f"Processed: {processed}, Modified: {modified}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total files processed: {total_processed}")
    print(f"Total files modified: {total_modified}")
    
    if all_errors:
        print(f"\nErrors encountered: {len(all_errors)}")
        for error in all_errors:
            print(f"  [ERROR] {error}")
        return 1
    else:
        print("\n[SUCCESS] All files processed successfully")
        
        # Provide next steps
        print("\n" + "=" * 80)
        print("NEXT STEPS")
        print("=" * 80)
        print("1. Run tests to verify markers work correctly:")
        print("   python unified_test_runner.py --category e2e --list-tests")
        print("\n2. Check compliance improvement:")
        print("   python scripts/check_architecture_compliance.py")
        print("\n3. Commit changes:")
        print("   git add -A && git commit -m \"feat: add pytest markers to all test files for proper categorization\"")
        
        return 0


if __name__ == "__main__":
    sys.exit(main())
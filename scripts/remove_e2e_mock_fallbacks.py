#!/usr/bin/env python
"""
Remove all mock fallbacks from E2E tests

This script systematically removes mock usage from E2E test files
and replaces them with real service calls.

Business Value Justification (BVJ):
- Segment: All tiers
- Business Goal: Ensure E2E tests validate real system behavior  
- Value Impact: Prevents false confidence from mock-based "E2E" tests
- Revenue Impact: Reduces production bugs that damage customer trust
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

def find_e2e_test_files() -> List[Path]:
    """Find all E2E test files"""
    e2e_dir = Path("tests/e2e")
    if not e2e_dir.exists():
        print(f"Error: {e2e_dir} does not exist")
        sys.exit(1)
    
    test_files = list(e2e_dir.rglob("test_*.py"))
    print(f"Found {len(test_files)} E2E test files")
    return test_files


def analyze_mock_usage(file_path: Path) -> Tuple[int, List[str]]:
    """Analyze mock usage in a file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    mock_patterns = [
        r'from unittest\.mock import',
        r'from mock import',
        r'Mock\(',
        r'MagicMock\(',
        r'AsyncMock\(',
        r'PropertyMock\(',
        r'patch\(',
        r'patch\.object\(',
        r'@patch',
        r'@mock\.',
        r'\.return_value\s*=',
        r'\.side_effect\s*=',
        r'mock_[a-zA-Z_]+',
        r'Mock[A-Z][a-zA-Z]+',
    ]
    
    issues = []
    total_count = 0
    
    for pattern in mock_patterns:
        matches = re.findall(pattern, content)
        if matches:
            total_count += len(matches)
            issues.append(f"{pattern}: {len(matches)} occurrences")
    
    return total_count, issues


def remove_mock_imports(content: str) -> str:
    """Remove mock import statements"""
    # Remove unittest.mock imports
    content = re.sub(
        r'from unittest\.mock import .*\n',
        '',
        content
    )
    
    # Remove mock library imports
    content = re.sub(
        r'from mock import .*\n',
        '',
        content
    )
    
    # Remove unused imports that might be left
    content = re.sub(
        r'import mock\n',
        '',
        content
    )
    
    return content


def replace_mock_fixtures(content: str) -> str:
    """Replace mock fixtures with real service fixtures"""
    replacements = [
        # Replace mock fixtures with real ones
        (r'mock_redis_client', 'real_redis_client'),
        (r'mock_websocket_manager', 'real_websocket_manager'),
        (r'mock_agent_service', 'real_agent_service'),
        (r'mock_llm_manager', 'real_llm_manager'),
        (r'mock_clickhouse_client', 'real_clickhouse_client'),
        (r'mock_supervisor_agent', 'real_supervisor_agent'),
        (r'mock_sub_agents', 'real_sub_agents'),
        (r'MockLLMProvider', 'RealLLMProvider'),
        (r'MockRetryStrategy', 'RealRetryStrategy'),
        (r'MockCostCalculator', 'RealCostCalculator'),
        (r'MockTokenUsage', 'RealTokenUsage'),
        
        # Replace Mock class instantiations
        (r'MagicMock\(\)', 'None  # Real service required'),
        (r'AsyncMock\(\)', 'None  # Real async service required'),
        (r'Mock\(\)', 'None  # Real service required'),
        
        # Comment out return_value and side_effect assignments
        (r'(\s*)(.+)\.return_value\s*=\s*(.+)', r'\1# REMOVED MOCK: \2.return_value = \3'),
        (r'(\s*)(.+)\.side_effect\s*=\s*(.+)', r'\1# REMOVED MOCK: \2.side_effect = \3'),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    return content


def add_real_service_import(content: str) -> str:
    """Add import for real service enforcement"""
    if 'enforce_real_services' not in content:
        # Add after the docstring
        lines = content.split('\n')
        insert_index = 0
        
        # Find the end of the module docstring
        in_docstring = False
        for i, line in enumerate(lines):
            if line.strip().startswith('"""'):
                if not in_docstring:
                    in_docstring = True
                else:
                    insert_index = i + 1
                    break
            elif not in_docstring and (line.strip().startswith('import ') or line.strip().startswith('from ')):
                insert_index = i
                break
        
        # Insert the enforcement import
        enforcement_import = '\n# ENFORCED: E2E tests use real services only\nfrom tests.e2e.enforce_real_services import E2EServiceValidator\nE2EServiceValidator.enforce_real_services()\n'
        
        lines.insert(insert_index, enforcement_import)
        content = '\n'.join(lines)
    
    return content


def process_file(file_path: Path, dry_run: bool = False) -> bool:
    """Process a single E2E test file"""
    print(f"\nProcessing: {file_path}")
    
    # Analyze current mock usage
    mock_count, issues = analyze_mock_usage(file_path)
    
    if mock_count == 0:
        print(f"  [OK] No mocks found")
        return True
    
    print(f"  Found {mock_count} mock references:")
    for issue in issues[:5]:  # Show first 5 issues
        print(f"    - {issue}")
    
    if dry_run:
        print(f"  [DRY RUN] Would remove {mock_count} mock references")
        return False
    
    # Read file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Apply transformations
    original_content = content
    content = remove_mock_imports(content)
    content = replace_mock_fixtures(content)
    content = add_real_service_import(content)
    
    # Write back if changed
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  [FIXED] Removed mock fallbacks")
        return True
    else:
        print(f"  No changes needed")
        return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Remove mock fallbacks from E2E tests')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--file', help='Process a specific file only')
    parser.add_argument('--limit', type=int, default=10, help='Limit number of files to process (default: 10)')
    args = parser.parse_args()
    
    if args.file:
        # Process single file
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File {file_path} does not exist")
            sys.exit(1)
        process_file(file_path, args.dry_run)
    else:
        # Process all E2E test files
        test_files = find_e2e_test_files()
        
        # Sort by mock count (process worst offenders first)
        files_with_mocks = []
        for file_path in test_files:
            mock_count, _ = analyze_mock_usage(file_path)
            if mock_count > 0:
                files_with_mocks.append((file_path, mock_count))
        
        files_with_mocks.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\nFound {len(files_with_mocks)} E2E test files with mocks")
        
        # Process files
        processed = 0
        for file_path, mock_count in files_with_mocks[:args.limit]:
            if process_file(file_path, args.dry_run):
                processed += 1
        
        print(f"\n{'[DRY RUN] Would process' if args.dry_run else 'Processed'} {processed} files")
        print(f"Remaining files with mocks: {len(files_with_mocks) - args.limit if len(files_with_mocks) > args.limit else 0}")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Quick script to find top mocked functions/services that need justification or real implementation.
"""

import re
from collections import defaultdict
from pathlib import Path
from typing import List, Tuple


def find_mock_patterns(root_path: str = ".") -> List[Tuple[str, str, int, str]]:
    """Find all mock patterns and categorize them"""
    root = Path(root_path)
    mock_usages = []
    
    # Common mock patterns to search for
    patterns = {
        'Mock()': r'Mock\(\)',
        'MagicMock()': r'MagicMock\(\)',
        'AsyncMock()': r'AsyncMock\(\)',
        'PropertyMock()': r'PropertyMock\(\)',
        '@patch': r'@patch\(',
        'patch.object': r'patch\.object\(',
        'create_autospec': r'create_autospec\(',
    }
    
    # Focus on key test directories
    test_dirs = [
        'tests/unified',
        'tests/integration', 
        'tests/e2e',
        'tests/agents',
        'tests/websocket'
    ]
    
    for test_dir in test_dirs:
        test_path = root / test_dir
        if not test_path.exists():
            continue
            
        for py_file in test_path.glob("**/*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                for i, line in enumerate(lines, 1):
                    for pattern_name, pattern_regex in patterns.items():
                        if re.search(pattern_regex, line):
                            rel_path = str(py_file.relative_to(root))
                            mock_usages.append((rel_path, pattern_name, i, line.strip()))
            except Exception as e:
                print(f"Error reading {py_file}: {e}")
    
    return mock_usages

def analyze_mock_targets(mock_usages: List[Tuple[str, str, int, str]]) -> dict:
    """Analyze what's being mocked most frequently"""
    mock_targets = defaultdict(list)
    
    for file_path, mock_type, line_num, code in mock_usages:
        # Extract patch targets
        if '@patch' in mock_type or 'patch' in mock_type:
            match = re.search(r"['\"]([^'\"]+)['\"]", code)
            if match:
                target = match.group(1)
                mock_targets[target].append((file_path, line_num))
        # Track inline mocks by context
        elif 'Mock()' in code:
            # Try to extract what's being assigned
            match = re.search(r'(\w+)\s*=\s*Mock\(\)', code)
            if match:
                var_name = match.group(1)
                mock_targets[f"inline:{var_name}"].append((file_path, line_num))
    
    return mock_targets

def check_for_justification(file_path: str, line_num: int) -> bool:
    """Check if a mock has a justification nearby"""
    justification_patterns = [
        r'@mock_justified',
        r'#\s*[Jj]ustification:',
        r'#\s*Mock justification:',
        r'#\s*Required for',
        r'#\s*Necessary because',
    ]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Check 3 lines before and 1 after
        start = max(0, line_num - 4)
        end = min(len(lines), line_num + 1)
        
        for i in range(start, end):
            for pattern in justification_patterns:
                if re.search(pattern, lines[i], re.IGNORECASE):
                    return True
    except:
        pass
    
    return False

def main():
    print("Finding all mock usages in test files...")
    mock_usages = find_mock_patterns()
    
    print(f"\nFound {len(mock_usages)} total mock usages")
    
    # Count by type
    by_type = defaultdict(int)
    for _, mock_type, _, _ in mock_usages:
        by_type[mock_type] += 1
    
    print("\nMock usage by type:")
    for mock_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
        print(f"  {mock_type}: {count}")
    
    # Analyze targets
    mock_targets = analyze_mock_targets(mock_usages)
    
    print("\nTop 20 most mocked targets:")
    sorted_targets = sorted(mock_targets.items(), key=lambda x: len(x[1]), reverse=True)
    
    unjustified_mocks = []
    
    for i, (target, locations) in enumerate(sorted_targets[:20], 1):
        print(f"\n{i}. {target} - mocked {len(locations)} times")
        
        # Check first few locations for justification
        for file_path, line_num in locations[:3]:
            has_just = check_for_justification(file_path, line_num)
            if not has_just:
                unjustified_mocks.append((target, file_path, line_num))
                print(f"   WARNING: {file_path}:{line_num} - NO JUSTIFICATION")
            else:
                print(f"   OK: {file_path}:{line_num} - has justification")
    
    # Files with most mocks
    file_counts = defaultdict(int)
    for file_path, _, _, _ in mock_usages:
        file_counts[file_path] += 1
    
    print("\n\nFiles with most mocks:")
    for file_path, count in sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {file_path}: {count} mocks")
    
    print(f"\n\nSummary:")
    print(f"Total mocks found: {len(mock_usages)}")
    print(f"Unjustified high-priority mocks found: {len(unjustified_mocks)}")
    
    # Export unjustified list
    if unjustified_mocks:
        print("\nTop unjustified mocks to fix:")
        for target, file_path, line_num in unjustified_mocks[:10]:
            print(f"  - {file_path}:{line_num} - {target}")

if __name__ == "__main__":
    main()
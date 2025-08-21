#!/usr/bin/env python3
"""
Test Compliance Checker
Ensures test files follow the same quality standards as production code:
- Maximum 300 lines per file
- Maximum 8 lines per function
- No mock component implementations inside test files
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def check_file_length(filepath: Path) -> Tuple[bool, int]:
    """Check if file exceeds 300 lines"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    return len(lines) <= 300, len(lines)

def check_function_lengths(filepath: Path) -> List[Dict]:
    """Find functions exceeding 8 lines"""
    violations = []
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Patterns for function detection
    patterns = [
        r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)',
        r'^\s*(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\()',
        r'^\s*(\w+)\s*:\s*(?:async\s+)?(?:function|\()',
        r'^\s*(?:it|test|describe)\s*\([\'"`]([^\'"`]+)'
    ]
    
    current_func = None
    func_start = 0
    brace_count = 0
    
    for i, line in enumerate(lines):
        # Check for function start
        if not current_func:
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    current_func = match.group(1) if match.lastindex else 'anonymous'
                    func_start = i + 1
                    brace_count = line.count('{') - line.count('}')
                    break
        else:
            # Track braces to find function end
            brace_count += line.count('{') - line.count('}')
            if brace_count <= 0:
                func_length = i - func_start + 1
                if func_length > 8:
                    violations.append({
                        'function': current_func,
                        'start_line': func_start,
                        'end_line': i + 1,
                        'length': func_length
                    })
                current_func = None
    
    return violations

def check_mock_components(filepath: Path) -> List[str]:
    """Check for mock component implementations in test files"""
    mock_patterns = []
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Look for mock component patterns
    patterns = [
        r'const\s+Mock\w+\s*=.*?return\s*<',
        r'const\s+\w+Form\s*=.*?return\s*<div',
        r'jest\.mock\([\'"`][^\'"`]+[\'"`],\s*\(\)\s*=>\s*\(\{[\s\S]+?return\s*<div'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
        mock_patterns.extend(matches[:3])  # Limit to first 3 matches per pattern
    
    return mock_patterns

def scan_test_files(root_dir: Path) -> Dict:
    """Scan all test files for compliance violations"""
    results = {
        'total_files': 0,
        'files_over_300': [],
        'functions_over_8': [],
        'mock_components': [],
        'summary': {}
    }
    
    test_patterns = ['*.test.tsx', '*.test.ts', '*.spec.tsx', '*.spec.ts']
    
    for pattern in test_patterns:
        for filepath in root_dir.rglob(pattern):
            # Skip node_modules
            if 'node_modules' in str(filepath):
                continue
            
            results['total_files'] += 1
            
            # Check file length
            compliant, line_count = check_file_length(filepath)
            if not compliant:
                results['files_over_300'].append({
                    'file': str(filepath.relative_to(root_dir)),
                    'lines': line_count
                })
            
            # Check function lengths
            violations = check_function_lengths(filepath)
            if violations:
                results['functions_over_8'].append({
                    'file': str(filepath.relative_to(root_dir)),
                    'violations': violations
                })
            
            # Check for mock components
            mocks = check_mock_components(filepath)
            if mocks:
                results['mock_components'].append({
                    'file': str(filepath.relative_to(root_dir)),
                    'mock_count': len(mocks)
                })
    
    # Generate summary
    results['summary'] = {
        'total_test_files': results['total_files'],
        'files_exceeding_300_lines': len(results['files_over_300']),
        'files_with_long_functions': len(results['functions_over_8']),
        'files_with_mock_components': len(results['mock_components']),
        'compliance_rate': calculate_compliance_rate(results)
    }
    
    return results

def calculate_compliance_rate(results: Dict) -> float:
    """Calculate overall compliance rate"""
    if results['total_files'] == 0:
        return 100.0
    
    violations = (
        len(results['files_over_300']) +
        len(results['functions_over_8']) +
        len(results['mock_components'])
    )
    
    return round((1 - violations / (results['total_files'] * 3)) * 100, 2)

def print_report(results: Dict):
    """Print compliance report"""
    print("\n" + "="*60)
    print("TEST COMPLIANCE REPORT")
    print("="*60)
    
    print(f"\nTotal test files scanned: {results['summary']['total_test_files']}")
    print(f"Overall compliance rate: {results['summary']['compliance_rate']}%")
    
    # Files over 300 lines
    if results['files_over_300']:
        print(f"\n[X] FILES EXCEEDING 300 LINES ({len(results['files_over_300'])} files):")
        for item in results['files_over_300'][:5]:
            print(f"  - {item['file']}: {item['lines']} lines")
        if len(results['files_over_300']) > 5:
            print(f"  ... and {len(results['files_over_300']) - 5} more")
    
    # Functions over 8 lines
    if results['functions_over_8']:
        print(f"\n[X] FILES WITH FUNCTIONS > 8 LINES ({len(results['functions_over_8'])} files):")
        for item in results['functions_over_8'][:5]:
            print(f"  - {item['file']}: {len(item['violations'])} violations")
            for v in item['violations'][:2]:
                print(f"    * {v['function']}: {v['length']} lines")
        if len(results['functions_over_8']) > 5:
            print(f"  ... and {len(results['functions_over_8']) - 5} more files")
    
    # Mock components
    if results['mock_components']:
        print(f"\n[X] FILES WITH MOCK COMPONENTS ({len(results['mock_components'])} files):")
        for item in results['mock_components'][:5]:
            print(f"  - {item['file']}: {item['mock_count']} mock patterns found")
        if len(results['mock_components']) > 5:
            print(f"  ... and {len(results['mock_components']) - 5} more")
    
    if results['summary']['compliance_rate'] == 100:
        print("\n[OK] All test files are compliant!")
    else:
        print("\n[!] Action Required: Fix violations to improve test quality")
    
    print("\n" + "="*60)

def main():
    """Main entry point"""
    # Check if we're in the frontend directory
    current_dir = Path.cwd()
    if current_dir.name == 'frontend':
        root_dir = current_dir
    else:
        root_dir = current_dir / 'frontend'
    
    if not root_dir.exists():
        print(f"Error: Frontend directory not found at {root_dir}")
        sys.exit(1)
    
    print(f"Scanning test files in: {root_dir}")
    results = scan_test_files(root_dir)
    print_report(results)
    
    # Return non-zero exit code if violations found
    if results['summary']['compliance_rate'] < 100:
        sys.exit(1)
    
    return 0

if __name__ == "__main__":
    main()
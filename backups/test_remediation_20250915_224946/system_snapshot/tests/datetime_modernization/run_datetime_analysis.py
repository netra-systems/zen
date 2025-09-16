#!/usr/bin/env python3
"""
Direct execution of datetime.utcnow() analysis for Issue #826

This script runs the core datetime detection and analysis functionality
without the test framework dependencies.
"""

import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Tuple


def scan_for_datetime_utcnow(project_root: Path) -> Dict[str, List[Tuple[int, str]]]:
    """Scan codebase for datetime.utcnow() usage patterns."""
    patterns = {}
    excluded_dirs = {'__pycache__', '.git', 'node_modules', '.pytest_cache', 'venv', 'env', '.tox'}
    
    for root, dirs, files in os.walk(project_root):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in excluded_dirs]
        
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    file_patterns = []
                    for line_num, line in enumerate(lines, 1):
                        if 'datetime.utcnow()' in line:
                            file_patterns.append((line_num, line))
                    
                    if file_patterns:
                        rel_path = os.path.relpath(file_path, project_root)
                        patterns[rel_path] = file_patterns
                        
                except Exception as e:
                    print(f"Warning: Could not scan {file_path}: {e}")
    
    return patterns


def categorize_usage(line_content: str) -> str:
    """Categorize the type of datetime.utcnow() usage."""
    line_lower = line_content.lower().strip()
    
    if any(op in line_content for op in ['=', 'return']):
        if any(fmt in line_content for fmt in ['.isoformat()', '.strftime(']):
            return 'formatting'
        return 'assignments'
    elif any(op in line_content for op in ['<', '>', '<=', '>=', '==', '!=']):
        return 'comparisons'
    elif any(op in line_content for op in ['+', '-', 'timedelta']):
        return 'arithmetic'
    elif any(fmt in line_content for fmt in ['.isoformat()', '.strftime(', '.timestamp()']):
        return 'formatting'
    else:
        return 'other'


def assess_risk_level(line_content: str) -> str:
    """Assess the risk level of a datetime usage pattern."""
    high_risk_patterns = [
        r'\.timestamp\(\)',
        r'fromtimestamp',
        r'strftime',
        r'\.isoformat\(\)',
        r'<|>|<=|>=',
    ]
    
    medium_risk_patterns = [
        r'\+|\-',
        r'timedelta',
        r'\.total_seconds\(\)',
    ]
    
    for pattern in high_risk_patterns:
        if re.search(pattern, line_content):
            return 'high'
    
    for pattern in medium_risk_patterns:
        if re.search(pattern, line_content):
            return 'medium'
    
    return 'low'


def identify_component(file_path: str) -> str:
    """Identify which component a file belongs to."""
    path_parts = file_path.split('/')
    
    if 'netra_backend' in path_parts:
        return 'backend'
    elif 'auth_service' in path_parts:
        return 'auth_service'
    elif 'analytics_service' in path_parts:
        return 'analytics_service'
    elif 'frontend' in path_parts:
        return 'frontend'
    elif 'shared' in path_parts:
        return 'shared'
    elif 'tests' in path_parts:
        return 'tests'
    elif 'scripts' in path_parts:
        return 'scripts'
    else:
        return 'other'


def test_modernization_compatibility():
    """Test that datetime.now(datetime.UTC) produces compatible results."""
    print("\n=== MODERNIZATION COMPATIBILITY TEST ===")
    
    # Test basic equivalence
    legacy_dt = datetime.utcnow()
    modern_dt = datetime.now(timezone.utc)
    
    print(f"Legacy datetime.utcnow(): {legacy_dt} (tzinfo: {legacy_dt.tzinfo})")
    print(f"Modern datetime.now(UTC): {modern_dt} (tzinfo: {modern_dt.tzinfo})")
    
    # Test formatting compatibility
    test_cases = [
        ('Basic ISO format', 
         lambda dt: dt.isoformat(),
         'Modernized version includes timezone info'),
        
        ('Timestamp conversion',
         lambda dt: dt.timestamp(),
         'Both should produce equivalent unix timestamps'),
        
        ('String representation',
         lambda dt: str(dt),
         'Modern version includes timezone info')
    ]
    
    print("\nCOMPATIBILITY ANALYSIS:")
    for test_name, test_func, note in test_cases:
        try:
            legacy_result = test_func(legacy_dt)
            modern_result = test_func(modern_dt)
            
            print(f"\n{test_name}:")
            print(f"  Legacy: {legacy_result}")
            print(f"  Modern: {modern_result}")
            print(f"  Note: {note}")
            
            # For timestamps, check they're reasonably close (within a few seconds)
            if test_name == 'Timestamp conversion':
                diff = abs(legacy_result - modern_result)
                print(f"  Timestamp difference: {diff:.3f} seconds")
                compatible = diff < 5.0
                print(f"  Compatible: {compatible}")
            
        except Exception as e:
            print(f"  Error in {test_name}: {e}")
    
    return True


def main():
    """Run datetime modernization analysis."""
    print("=== DATETIME MODERNIZATION ANALYSIS FOR ISSUE #826 ===")
    
    project_root = Path(__file__).parent.parent.parent
    print(f"Scanning project root: {project_root}")
    
    # 1. Detection Test
    print("\n=== DETECTING DATETIME.UTCNOW() USAGE PATTERNS ===")
    
    utcnow_patterns = scan_for_datetime_utcnow(project_root)
    
    total_files = len(utcnow_patterns)
    total_occurrences = sum(len(occurrences) for occurrences in utcnow_patterns.values())
    
    print(f"Found {total_occurrences} datetime.utcnow() usage patterns in {total_files} files")
    
    # Show some examples
    print("\nSAMPLE OCCURRENCES:")
    count = 0
    for file_path, occurrences in utcnow_patterns.items():
        if count >= 10:  # Show first 10 files
            break
        print(f"\n{file_path}:")
        for line_num, line_content in occurrences[:3]:  # Show first 3 lines per file
            print(f"  Line {line_num}: {line_content.strip()}")
        if len(occurrences) > 3:
            print(f"  ... and {len(occurrences) - 3} more occurrences")
        count += 1
    
    if total_files > 10:
        print(f"\n... and {total_files - 10} more files with datetime.utcnow() usage")
    
    # 2. Categorization Analysis
    print("\n=== USAGE PATTERN CATEGORIZATION ===")
    
    categories = {
        'timestamp_creation': 0,
        'comparisons': 0,
        'arithmetic': 0,
        'formatting': 0,
        'assignments': 0,
        'other': 0
    }
    
    risk_levels = {
        'high': 0,
        'medium': 0,
        'low': 0
    }
    
    component_breakdown = {}
    
    for file_path, occurrences in utcnow_patterns.items():
        component = identify_component(file_path)
        if component not in component_breakdown:
            component_breakdown[component] = 0
        component_breakdown[component] += len(occurrences)
        
        for line_num, line_content in occurrences:
            category = categorize_usage(line_content)
            categories[category] += 1
            
            risk = assess_risk_level(line_content)
            risk_levels[risk] += 1
    
    print("Usage categories:")
    for category, count in categories.items():
        print(f"  {category}: {count}")
    
    print("\nRisk levels:")
    for risk, count in risk_levels.items():
        print(f"  {risk}: {count}")
    
    print("\nComponent breakdown:")
    for component, count in sorted(component_breakdown.items()):
        print(f"  {component}: {count}")
    
    # 3. Scope Estimation
    print("\n=== MODERNIZATION SCOPE ESTIMATION ===")
    
    effort_hours = (
        risk_levels['low'] * 0.1 +
        risk_levels['medium'] * 0.5 +
        risk_levels['high'] * 2.0
    )
    
    print(f"Estimated effort: {effort_hours:.1f} hours")
    print(f"High-risk patterns requiring careful analysis: {risk_levels['high']}")
    print(f"Medium-risk patterns requiring testing: {risk_levels['medium']}")
    print(f"Low-risk patterns (simple replacements): {risk_levels['low']}")
    
    # 4. Compatibility Testing
    test_modernization_compatibility()
    
    # 5. Recommendations
    print("\n=== RECOMMENDATIONS ===")
    
    if total_occurrences > 0:
        print("✅ PROCEED WITH MODERNIZATION:")
        print("  - Found deprecated datetime.utcnow() usage that should be modernized")
        print(f"  - {total_occurrences} occurrences across {total_files} files need updating")
        print(f"  - Estimated effort: {effort_hours:.1f} hours")
        print("  - Modern approach provides better timezone handling")
        
        print(f"\nPRIORITIZE HIGH-RISK PATTERNS ({risk_levels['high']} occurrences):")
        print("  - These require careful testing and validation")
        print("  - Focus on timestamp conversions, formatting, and comparisons")
        
        print(f"\nCOMPONENT FOCUS:")
        sorted_components = sorted(component_breakdown.items(), key=lambda x: x[1], reverse=True)
        for component, count in sorted_components[:3]:
            print(f"  - {component}: {count} occurrences (high impact)")
        
    else:
        print("ℹ️  NO MODERNIZATION NEEDED:")
        print("  - No datetime.utcnow() usage found in Python source files")
        print("  - System already uses modern datetime patterns")
    
    return {
        'total_files': total_files,
        'total_occurrences': total_occurrences,
        'categories': categories,
        'risk_levels': risk_levels,
        'component_breakdown': component_breakdown,
        'estimated_effort_hours': effort_hours,
        'recommendation': 'proceed' if total_occurrences > 0 else 'not_needed'
    }


if __name__ == '__main__':
    results = main()

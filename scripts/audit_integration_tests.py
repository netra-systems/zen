#!/usr/bin/env python3
"""Audit integration tests to identify which are legacy/mocked vs real tests."""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

def analyze_test_file(file_path: Path) -> Dict[str, any]:
    """Analyze a test file for mock usage and real service indicators."""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for various indicators
    indicators = {
        'uses_mocks': bool(re.search(r'from unittest\.mock import|Mock\(|MagicMock\(|AsyncMock\(|@patch|@mock', content)),
        'uses_real_websocket': bool(re.search(r'websockets\.connect|TestClient.*websocket', content)),
        'uses_real_db': bool(re.search(r'create_all|async_sessionmaker|get_database_session', content)),
        'uses_docker': bool(re.search(r'docker|container|compose', content, re.IGNORECASE)),
        'uses_real_redis': bool(re.search(r'redis\.Redis|aioredis|redis_client', content)) and not bool(re.search(r'mock.*redis|redis.*mock', content, re.IGNORECASE)),
        'uses_real_llm': bool(re.search(r'real_llm|REAL_LLM|openai\.ChatCompletion|anthropic', content)),
        'has_bvj': bool(re.search(r'Business Value Justification|BVJ:', content)),
        'l3_test': bool(re.search(r'L3|L3IntegrationTest|Level 3', content)),
        'marked_skip': bool(re.search(r'@pytest\.mark\.skip|pytest\.skip', content)),
        'marked_xfail': bool(re.search(r'@pytest\.mark\.xfail', content)),
    }
    
    # Count test methods
    test_methods = re.findall(r'def (test_\w+)', content)
    indicators['num_tests'] = len(test_methods)
    
    # Check if it's a fixture/helper file
    indicators['is_helper'] = bool(re.search(r'fixture|helper|base|mock|util', str(file_path.name), re.IGNORECASE))
    
    # Calculate a "realness score"
    real_indicators = ['uses_real_websocket', 'uses_real_db', 'uses_docker', 'uses_real_redis', 'uses_real_llm', 'l3_test']
    fake_indicators = ['uses_mocks']
    
    real_score = sum(1 for ind in real_indicators if indicators.get(ind, False))
    fake_score = sum(1 for ind in fake_indicators if indicators.get(ind, False))
    
    indicators['real_score'] = real_score
    indicators['fake_score'] = fake_score
    indicators['likely_real'] = real_score > fake_score
    
    return indicators

def main():
    """Main audit function."""
    
    # Find all integration test files
    integration_dirs = [
        Path('netra_backend/tests/integration'),
        Path('analytics_service/tests/integration'),
        Path('auth_service/tests/integration'),
    ]
    
    results = {}
    
    for base_dir in integration_dirs:
        if not base_dir.exists():
            continue
            
        for test_file in base_dir.rglob('test_*.py'):
            relative_path = test_file.relative_to(Path('.'))
            results[str(relative_path)] = analyze_test_file(test_file)
    
    # Categorize tests
    real_tests = []
    mock_tests = []
    mixed_tests = []
    helper_files = []
    skip_tests = []
    
    for file_path, analysis in results.items():
        if analysis['is_helper']:
            helper_files.append(file_path)
        elif analysis['marked_skip'] or analysis['marked_xfail']:
            skip_tests.append(file_path)
        elif analysis['real_score'] > 0 and analysis['fake_score'] == 0:
            real_tests.append((file_path, analysis))
        elif analysis['fake_score'] > 0 and analysis['real_score'] == 0:
            mock_tests.append((file_path, analysis))
        else:
            mixed_tests.append((file_path, analysis))
    
    # Print report
    print("=" * 80)
    print("INTEGRATION TEST AUDIT REPORT")
    print("=" * 80)
    print()
    
    print(f"Total test files analyzed: {len(results)}")
    print(f"Helper/fixture files: {len(helper_files)}")
    print(f"Skipped/xfail tests: {len(skip_tests)}")
    print()
    
    print(f"REAL TESTS (no mocks, use real services): {len(real_tests)}")
    if real_tests:
        for path, analysis in real_tests[:10]:  # Show first 10
            print(f"  [REAL] {path} (score: {analysis['real_score']})")
        if len(real_tests) > 10:
            print(f"  ... and {len(real_tests) - 10} more")
    print()
    
    print(f"MOCK TESTS (only mocks, no real services): {len(mock_tests)}")
    if mock_tests:
        for path, analysis in mock_tests[:10]:  # Show first 10
            print(f"  [MOCK] {path} (tests: {analysis['num_tests']})")
        if len(mock_tests) > 10:
            print(f"  ... and {len(mock_tests) - 10} more")
    print()
    
    print(f"MIXED TESTS (both mocks and real services): {len(mixed_tests)}")
    if mixed_tests:
        for path, analysis in mixed_tests[:10]:  # Show first 10
            print(f"  [MIXED] {path} (real: {analysis['real_score']}, fake: {analysis['fake_score']})")
        if len(mixed_tests) > 10:
            print(f"  ... and {len(mixed_tests) - 10} more")
    print()
    
    # Summary recommendations
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    total_actionable = len(mock_tests) + len(mixed_tests)
    print(f"Tests needing review/update: {total_actionable}")
    print(f"Tests that appear valid: {len(real_tests)}")
    print()
    
    if mock_tests:
        print("Priority 1: Convert pure mock tests to real integration tests")
        print("  These provide little value as integration tests")
        print()
    
    if mixed_tests:
        print("Priority 2: Review mixed tests")
        print("  Determine if mocks are justified or should use real services")
        print()
    
    # Write detailed report to file
    with open('integration_test_audit.txt', 'w') as f:
        f.write("DETAILED INTEGRATION TEST AUDIT\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("MOCK-ONLY TESTS (candidates for deletion or conversion):\n")
        for path, analysis in mock_tests:
            f.write(f"\n{path}\n")
            f.write(f"  Tests: {analysis['num_tests']}\n")
            f.write(f"  Has BVJ: {analysis['has_bvj']}\n")
        
        f.write("\n\nMIXED TESTS (need review):\n")
        for path, analysis in mixed_tests:
            f.write(f"\n{path}\n")
            f.write(f"  Real score: {analysis['real_score']}\n")
            f.write(f"  Mock score: {analysis['fake_score']}\n")
            f.write(f"  Tests: {analysis['num_tests']}\n")
        
        f.write("\n\nREAL TESTS (keep as-is):\n")
        for path, analysis in real_tests:
            f.write(f"\n{path}\n")
            f.write(f"  Real score: {analysis['real_score']}\n")
            f.write(f"  Tests: {analysis['num_tests']}\n")
    
    print(f"Detailed report written to: integration_test_audit.txt")

if __name__ == "__main__":
    main()
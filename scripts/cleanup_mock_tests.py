#!/usr/bin/env python3
"""Clean up mock-only integration tests that provide no real integration value."""

import os
import re
from pathlib import Path
from typing import List, Dict, Any

def analyze_test_file(file_path: Path) -> Dict[str, Any]:
    """Analyze a test file for mock usage and real service indicators."""
    
    if not file_path.exists():
        return None
        
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
    indicators['is_mock_only'] = fake_score > 0 and real_score == 0
    
    return indicators

def main():
    """Main function to delete mock-only tests."""
    
    # Find all integration test files
    integration_dirs = [
        Path('netra_backend/tests/integration'),
        Path('analytics_service/tests/integration'),
        Path('auth_service/tests/integration'),
    ]
    
    mock_only_tests = []
    
    for base_dir in integration_dirs:
        if not base_dir.exists():
            continue
            
        for test_file in base_dir.rglob('test_*.py'):
            analysis = analyze_test_file(test_file)
            if analysis and analysis['is_mock_only'] and not analysis['is_helper']:
                mock_only_tests.append(test_file)
    
    print(f"Found {len(mock_only_tests)} mock-only integration tests")
    
    # Delete them
    deleted = []
    errors = []
    
    for test_file in mock_only_tests:
        try:
            print(f"Deleting: {test_file}")
            os.remove(test_file)
            deleted.append(test_file)
        except Exception as e:
            errors.append((test_file, str(e)))
    
    print()
    print("=" * 80)
    print(f"Successfully deleted {len(deleted)} mock-only integration tests")
    
    if errors:
        print(f"\nErrors deleting {len(errors)} files:")
        for path, error in errors[:10]:
            print(f"  {path}: {error}")
    
    # Write summary
    with open('deleted_mock_tests.txt', 'w') as f:
        f.write("DELETED MOCK-ONLY INTEGRATION TESTS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total deleted: {len(deleted)}\n\n")
        for path in deleted:
            f.write(f"{path}\n")
    
    print(f"\nSummary written to: deleted_mock_tests.txt")

if __name__ == "__main__":
    main()
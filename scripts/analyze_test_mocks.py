#!/usr/bin/env python3
"""
Analyze test mocks in the codebase to identify unjustified mocks.
Based on testing.xml spectrum levels (L0-L5).
"""

import os
import re
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

# Categories of mocks based on testing.xml spectrum levels
MOCK_CATEGORIES = {
    'database': {'level': 'L3', 'priority': 1},  # Should use real DB containers
    'llm_services': {'level': 'L3', 'priority': 1},  # Should use real LLM for critical paths
    'auth_services': {'level': 'L3', 'priority': 1},  # Should use real auth service
    'websocket': {'level': 'L3', 'priority': 2},  # Should use real websocket connections
    'redis': {'level': 'L3', 'priority': 2},  # Should use real Redis container
    'http_client': {'level': 'L2', 'priority': 3},  # Could use real HTTP calls
    'time_utilities': {'level': 'L1', 'priority': 4},  # Justified for deterministic tests
    'file_system': {'level': 'L1', 'priority': 4},  # May be justified for isolation
    'other': {'level': 'L1', 'priority': 5}
}


def categorize_mock(target: str) -> str:
    """Categorize mock based on what it's mocking."""
    if not target:
        return 'other'
    
    target_lower = target.lower()
    
    # Database mocks
    if any(x in target_lower for x in ['database', 'session', 'repository', 'sqlalchemy', 'postgres', 'clickhouse']):
        return 'database'
    
    # LLM service mocks
    if any(x in target_lower for x in ['llm', 'openai', 'anthropic', 'gemini', 'completion', 'agent']):
        return 'llm_services'
    
    # Auth service mocks
    if any(x in target_lower for x in ['auth', 'jwt', 'oauth', 'token', 'permission']):
        return 'auth_services'
    
    # WebSocket mocks
    if any(x in target_lower for x in ['websocket', 'ws', 'socket']):
        return 'websocket'
    
    # Redis mocks
    if any(x in target_lower for x in ['redis', 'cache']):
        return 'redis'
    
    # HTTP client mocks
    if any(x in target_lower for x in ['httpx', 'requests', 'client.get', 'client.post']):
        return 'http_client'
    
    # Time utilities
    if any(x in target_lower for x in ['time.time', 'datetime', 'sleep']):
        return 'time_utilities'
    
    # File system
    if any(x in target_lower for x in ['open', 'file', 'path.exists']):
        return 'file_system'
    
    return 'other'


def find_mock_justification(content: str, line_no: int) -> bool:
    """Check if mock has a justification comment or decorator."""
    lines = content.split('\n')
    
    # Check surrounding lines for justification
    start = max(0, line_no - 5)
    end = min(len(lines), line_no + 2)
    
    for i in range(start, end):
        if i < len(lines):
            line = lines[i]
            if '@mock_justified' in line or '# Mock justified' in line or '# Justified:' in line:
                return True
    
    return False


def analyze_file_for_mocks(filepath: str) -> List[Dict]:
    """Analyze a single file for mock usage."""
    mocks = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Find @patch decorators
        patch_pattern = r'@patch\([\'"]([^\'"]*)[\'"].*?\)'
        for match in re.finditer(patch_pattern, content, re.DOTALL):
            target = match.group(1)
            line_no = content[:match.start()].count('\n') + 1
            has_justification = find_mock_justification(content, line_no)
            category = categorize_mock(target)
            
            mocks.append({
                'type': 'patch',
                'target': target,
                'line': line_no,
                'justified': has_justification,
                'category': category,
                'priority': MOCK_CATEGORIES[category]['priority']
            })
        
        # Find Mock/MagicMock/AsyncMock usage
        mock_pattern = r'\b(Mock|MagicMock|AsyncMock)\(.*?\)'
        for match in re.finditer(mock_pattern, content):
            line_no = content[:match.start()].count('\n') + 1
            has_justification = find_mock_justification(content, line_no)
            
            # Try to determine what's being mocked from context
            start_line = max(0, line_no - 3)
            end_line = min(len(content.split('\n')), line_no + 2)
            context = '\n'.join(content.split('\n')[start_line:end_line])
            category = categorize_mock(context)
            
            mocks.append({
                'type': match.group(1),
                'target': '',
                'line': line_no,
                'justified': has_justification,
                'category': category,
                'priority': MOCK_CATEGORIES[category]['priority']
            })
    
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
    
    return mocks


def main():
    """Main function to analyze mocks."""
    # Scan all test files
    all_mocks = []
    test_dirs = ['netra_backend/tests', 'tests/e2e', 'auth_service/tests']
    
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            for root, dirs, files in os.walk(test_dir):
                for file in files:
                    if file.endswith('.py') and 'test' in file:
                        filepath = os.path.join(root, file)
                        mocks = analyze_file_for_mocks(filepath)
                        
                        for mock in mocks:
                            mock['file'] = filepath
                            all_mocks.append(mock)
    
    # Filter unjustified mocks and sort by priority
    unjustified_mocks = [m for m in all_mocks if not m['justified']]
    unjustified_mocks.sort(key=lambda x: (x['priority'], -len(x['target'])))
    
    # Group by category for summary
    category_summary = defaultdict(int)
    for mock in unjustified_mocks:
        category_summary[mock['category']] += 1
    
    print('=== Mock Analysis Summary ===')
    print(f'Total mocks found: {len(all_mocks)}')
    print(f'Unjustified mocks: {len(unjustified_mocks)}')
    print('\nUnjustified mocks by category:')
    for category, count in sorted(category_summary.items(), key=lambda x: MOCK_CATEGORIES[x[0]]['priority']):
        level = MOCK_CATEGORIES[category]['level']
        print(f'  {category}: {count} mocks (should be {level})')
    
    print('\n=== Top 10 Unjustified Mocks to Fix ===')
    base_path = os.getcwd()
    for i, mock in enumerate(unjustified_mocks[:10], 1):
        file_short = os.path.relpath(mock['file'], base_path)
        print(f'{i}. {file_short}:{mock["line"]}')
        print(f'   Category: {mock["category"]} (Priority: {mock["priority"]})')
        print(f'   Type: {mock["type"]}')
        if mock['target']:
            print(f'   Target: {mock["target"]}')
    
    # Save full analysis for processing
    with open('mock_analysis.json', 'w') as f:
        # Make paths relative for JSON
        for mock in unjustified_mocks[:100]:
            mock['file'] = os.path.relpath(mock['file'], base_path)
        
        json.dump({
            'summary': dict(category_summary),
            'top_100': unjustified_mocks[:100]
        }, f, indent=2)
    
    print('\nFull analysis saved to mock_analysis.json')
    return unjustified_mocks[:100]


if __name__ == '__main__':
    main()
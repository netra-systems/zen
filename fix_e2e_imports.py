#!/usr/bin/env python3
"""
Fix E2E test import issues across the codebase.
This script identifies and fixes common import problems in E2E tests.
"""

import os
import re
import sys
from pathlib import Path


def find_test_files():
    """Find all test files in E2E directories."""
    test_files = []
    
    # Find files in netra_backend/tests/e2e
    for root, dirs, files in os.walk('netra_backend/tests/e2e'):
        for file in files:
            if file.endswith('.py'):
                test_files.append(os.path.join(root, file))
    
    # Find files in tests/e2e
    for root, dirs, files in os.walk('tests/e2e'):
        for file in files:
            if file.endswith('.py'):
                test_files.append(os.path.join(root, file))
    
    return test_files


def fix_import_issues():
    """Fix common import issues in test files."""
    test_files = find_test_files()
    fixed_count = 0
    
    # Common import fixes
    import_fixes = [
        # Fix relative imports to absolute
        (r'from \.\.\.', 'from netra_backend.'),
        (r'from \.\.', 'from netra_backend.'),
        (r'from \.', 'from netra_backend.tests.e2e.'),
        
        # Fix common missing module paths
        (r'from netra_backend\.tests\.model_effectiveness_tests', 'from netra_backend.tests.e2e.model_effectiveness_tests'),
        (r'from netra_backend\.tests\.([^\.]+)\.([^\.]+)$', r'from netra_backend.tests.e2e.\1.\2'),
        
        # Fix missing test framework imports
        (r'from tests\.e2e\.', 'from tests.e2e.'),
        
        # Fix websocket manager imports
        (r'from netra_backend\.app\.core\.websocket\.manager import WebSocketManager', 
         'from netra_backend.app.websocket.unified.manager import WebSocketManager'),
         
        # Fix agent imports that may have moved
        (r'from netra_backend\.app\.agents\.supervisor\.execution_context',
         'from netra_backend.app.agents.base.execution_context'),
    ]
    
    for filepath in test_files:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            original_content = content
            
            # Apply fixes
            for pattern, replacement in import_fixes:
                content = re.sub(pattern, replacement, content)
            
            # Fix specific import patterns
            if 'from netra_backend.tests.' in content and 'e2e' not in content:
                content = content.replace('from netra_backend.tests.', 'from netra_backend.tests.e2e.')
            
            # Write back if changed
            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Fixed imports in: {filepath}")
                fixed_count += 1
                
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
    
    return fixed_count


def check_missing_fixtures():
    """Check for missing fixture files and create basic ones."""
    fixture_files = [
        'netra_backend/tests/e2e/conftest.py',
        'tests/e2e/conftest.py',
    ]
    
    created_count = 0
    
    for fixture_path in fixture_files:
        if not os.path.exists(fixture_path):
            # Create basic conftest.py
            conftest_content = '''"""E2E test fixtures and configuration."""

import pytest
import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

# Basic test setup fixtures
@pytest.fixture
async def mock_agent_service():
    """Mock agent service for E2E tests."""
    mock_service = AsyncMock()
    mock_service.process_message.return_value = {
        "response": "Test response",
        "metadata": {"test": True}
    }
    return mock_service

@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager for E2E tests."""
    mock_manager = MagicMock()
    mock_manager.send_message = AsyncMock()
    mock_manager.broadcast = AsyncMock()
    return mock_manager

@pytest.fixture
def model_selection_setup():
    """Basic setup for model selection tests."""
    return {
        "mock_llm_service": AsyncMock(),
        "mock_database": AsyncMock(),
        "test_config": {"environment": "test"}
    }

# Real LLM testing configuration
@pytest.fixture
def real_llm_config():
    """Configuration for real LLM testing."""
    return {
        "enabled": False,  # Default to disabled
        "timeout": 30.0,
        "max_retries": 3
    }
'''
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(fixture_path), exist_ok=True)
            
            with open(fixture_path, 'w', encoding='utf-8') as f:
                f.write(conftest_content)
            
            print(f"Created fixture file: {fixture_path}")
            created_count += 1
    
    return created_count


def fix_async_test_functions():
    """Fix async test function definitions that are missing test_ prefix."""
    test_files = find_test_files()
    fixed_count = 0
    
    for filepath in test_files:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            modified = False
            new_lines = []
            
            for line in lines:
                # Skip helper functions and fixtures
                if ('async def _' in line or 
                    '@pytest.fixture' in line or
                    'async def create_' in line or
                    'async def setup_' in line):
                    new_lines.append(line)
                    continue
                
                # Fix async test functions without test_ prefix
                if 'async def ' in line and 'test_' in line:
                    # Check if it should be a test function
                    if ('async def test_' not in line and 
                        'def test_' not in line and
                        line.strip().startswith('async def ')):
                        # This might be a misnamed test function
                        function_name = line.split('async def ')[1].split('(')[0].strip()
                        if not function_name.startswith('_') and not function_name.startswith('test_'):
                            # Likely should be a test function
                            new_line = line.replace(f'async def {function_name}', f'async def test_{function_name}')
                            new_lines.append(new_line)
                            modified = True
                            continue
                
                new_lines.append(line)
            
            if modified:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                print(f"Fixed async test functions in: {filepath}")
                fixed_count += 1
                
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
    
    return fixed_count


def main():
    """Main fix function."""
    print("Fixing E2E test import issues...")
    
    if not os.path.exists('netra_backend') and not os.path.exists('tests'):
        print("Error: Run this script from the project root directory")
        sys.exit(1)
    
    # Fix import issues
    fixed_imports = fix_import_issues()
    print(f"Fixed imports in {fixed_imports} files")
    
    # Create missing fixture files
    created_fixtures = check_missing_fixtures()
    print(f"Created {created_fixtures} fixture files")
    
    # Fix async test function names
    fixed_functions = fix_async_test_functions()
    print(f"Fixed async test functions in {fixed_functions} files")
    
    print("E2E import fixes completed!")
    
    # Test a few files to verify
    print("\nTesting fixed files...")
    test_files = [
        'netra_backend/tests/e2e/chat_optimization_tests.py',
        'netra_backend/tests/e2e/model_effectiveness_tests.py'
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"Testing collection of {test_file}...")
            result = os.system(f'python -m pytest --collect-only {test_file} > /dev/null 2>&1')
            if result == 0:
                print(f"✓ {test_file} - OK")
            else:
                print(f"✗ {test_file} - Still has issues")


if __name__ == '__main__':
    main()
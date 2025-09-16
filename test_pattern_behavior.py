#!/usr/bin/env python3
"""
Test script to check current pattern filtering behavior for Issue #1270
"""

import sys
sys.path.insert(0, '.')
from tests.unified_test_runner import UnifiedTestRunner
from unittest.mock import Mock

def test_pattern_behavior():
    # Create a test runner instance
    runner = UnifiedTestRunner()

    # Mock args with pattern
    mock_args = Mock()
    mock_args.pattern = 'agent'
    mock_args.no_coverage = True
    mock_args.parallel = False
    mock_args.verbose = False
    mock_args.fast_fail = False
    mock_args.env = 'staging'

    # Test database category command generation
    try:
        cmd = runner._build_pytest_command('backend', 'database', mock_args)
        print('DATABASE CATEGORY COMMAND:')
        print(cmd)
        print()

        # Check if pattern is in command
        if '-k' in cmd and 'agent' in cmd:
            print('ISSUE #1270 NOT FIXED: Pattern IS applied to database category')
            print('This is the BUG - database tests will be filtered when they should not be')
        else:
            print('ISSUE #1270 FIXED: Pattern is NOT applied to database category')
        print()

        # Test e2e category for comparison
        cmd2 = runner._build_pytest_command('backend', 'e2e', mock_args)
        print('E2E CATEGORY COMMAND:')
        print(cmd2)
        print()

        if '-k' in cmd2 and 'agent' in cmd2:
            print('EXPECTED: Pattern IS applied to e2e category')
        else:
            print('UNEXPECTED: Pattern is NOT applied to e2e category')

        # Test unit category (should NOT have pattern)
        cmd3 = runner._build_pytest_command('backend', 'unit', mock_args)
        print('UNIT CATEGORY COMMAND:')
        print(cmd3)
        print()

        if '-k' in cmd3 and 'agent' in cmd3:
            print('ISSUE #1270 NOT FIXED: Pattern IS applied to unit category (should not be)')
        else:
            print('CORRECT: Pattern is NOT applied to unit category')

    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_pattern_behavior()
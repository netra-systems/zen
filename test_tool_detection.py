#!/usr/bin/env python3
"""
Test script for tool detection patterns
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from zen_orchestrator import ClaudeInstanceOrchestrator

def test_tool_detection():
    """Test the enhanced tool detection patterns"""
    orchestrator = ClaudeInstanceOrchestrator('.')

    # Test cases based on actual log data
    test_cases = [
        # Case 1: File path result (tool_ngW9xHGt)
        {
            'content': 'zen/zen_orchestrator.py',
            'expected': 'Glob',
            'description': 'Single file path result'
        },

        # Case 2: Git commit success (tool_1aNZHJXb)
        {
            'content': '[develop-long-lived 1b8d034e6] feat(zen): enhance budget tracking and tool detection\n 1 file changed, 50 insertions(+), 9 deletions(-)',
            'expected': 'Bash',
            'description': 'Git commit success output'
        },

        # Case 3: Empty result (tool_8YKJFaqd)
        {
            'content': '',
            'expected': 'Bash',
            'description': 'Empty command result'
        },

        # Case 4: Regular git status (should still work)
        {
            'content': 'On branch develop-long-lived\nYour branch and \'origin/develop-long-lived\' have diverged',
            'expected': 'Bash',
            'description': 'Git status output'
        },

        # Case 5: Directory read error (tool_DPLTmvTM, tool_kJub1RTK)
        {
            'content': 'EISDIR: illegal operation on a directory, read',
            'expected': 'Read',
            'description': 'Read tool directory error'
        },

        # Case 6: Command approval error (tool_BCwLTXMy type scenarios)
        {
            'content': 'This command requires approval',
            'expected': 'Bash',
            'description': 'Command requires approval error'
        },

        # Case 7: File size limit error
        {
            'content': 'File content (30686 tokens) exceeds maximum allowed tokens (25000). Please use offset and limit parameters to read specific portions of the file',
            'expected': 'Read',
            'description': 'File size limit exceeded error'
        },

        # Case 8: MCP permission error
        {
            'content': 'Claude requested permissions to use mcp__serena__list_dir, but you haven\'t granted it yet.',
            'expected': 'permission_request',
            'description': 'MCP tool permission request'
        }
    ]

    print("Testing enhanced tool detection patterns...")
    print("=" * 50)

    for i, test in enumerate(test_cases, 1):
        tool_result = {'content': test['content']}
        tool_use_id = f'test_tool_{i}'

        detected = orchestrator._extract_tool_name_from_result(tool_result, tool_use_id)

        status = "✅ PASS" if detected == test['expected'] else "❌ FAIL"
        print(f"{status} Test {i}: {test['description']}")
        print(f"  Content: {repr(test['content'][:50])}{'...' if len(test['content']) > 50 else ''}")
        print(f"  Expected: {test['expected']}, Got: {detected}")
        print()

        if detected != test['expected']:
            return False

    print("🎉 All tool detection tests passed!")
    return True

if __name__ == '__main__':
    success = test_tool_detection()
    sys.exit(0 if success else 1)
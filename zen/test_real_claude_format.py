#!/usr/bin/env python3
"""Test with real Claude API stream format to identify parsing issues."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from claude_instance_orchestrator import ClaudeInstanceOrchestrator, InstanceStatus

def test_real_format_parsing():
    """Test the exact format that Claude Code outputs."""
    print("=" * 80)
    print("TESTING REAL CLAUDE STREAM FORMAT PARSING ISSUES")
    print("=" * 80)

    workspace = Path.cwd()
    orchestrator = ClaudeInstanceOrchestrator(workspace)

    status = InstanceStatus("test")

    # This is the actual problem: the parser doesn't handle delta.usage structure
    real_claude_line = '{"type":"message_delta","delta":{"stop_reason":"end_turn","usage":{"input_tokens":45,"output_tokens":12,"total_tokens":57}}}'

    print(f"Testing real Claude output line:")
    print(f"  {real_claude_line}")
    print(f"Initial status: total={status.total_tokens}")

    # This should work but currently doesn't
    result = orchestrator._try_parse_json_token_usage(real_claude_line, status)

    print(f"Parse result: {result}")
    print(f"Status after parsing: input={status.input_tokens}, output={status.output_tokens}, total={status.total_tokens}")

    if status.total_tokens == 0:
        print("❌ PROBLEM IDENTIFIED: Real Claude format not parsed correctly!")

        # Let's manually fix the parsing logic and test
        print("\n--- Testing manual fix ---")
        json_data = json.loads(real_claude_line)

        # Check for delta.usage structure (THIS IS MISSING FROM CURRENT CODE)
        if 'delta' in json_data and isinstance(json_data['delta'], dict) and 'usage' in json_data['delta']:
            usage_data = json_data['delta']['usage']
            print(f"Found usage data in delta: {usage_data}")

            # Apply the usage
            if 'input_tokens' in usage_data:
                status.input_tokens = max(status.input_tokens, int(usage_data['input_tokens']))
            if 'output_tokens' in usage_data:
                status.output_tokens = max(status.output_tokens, int(usage_data['output_tokens']))
            if 'total_tokens' in usage_data:
                status.total_tokens = max(status.total_tokens, int(usage_data['total_tokens']))

            print(f"After manual fix: input={status.input_tokens}, output={status.output_tokens}, total={status.total_tokens}")

def test_max_vs_add_issue():
    """Test the max() vs += issue causing cumulative token problems."""
    print("\n" + "=" * 80)
    print("TESTING MAX() VS += ACCUMULATION ISSUE")
    print("=" * 80)

    workspace = Path.cwd()
    orchestrator = ClaudeInstanceOrchestrator(workspace)

    status = InstanceStatus("test")

    # Test progressive token usage (multiple API calls in same session)
    test_messages = [
        '{"id": "msg_001", "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}}',
        '{"id": "msg_002", "usage": {"input_tokens": 50, "output_tokens": 25, "total_tokens": 75}}',
        '{"id": "msg_003", "usage": {"input_tokens": 80, "output_tokens": 40, "total_tokens": 120}}',
    ]

    print("Processing multiple messages sequentially (simulating progressive token usage):")

    total_expected_input = 0
    total_expected_output = 0
    total_expected_total = 0

    for i, msg in enumerate(test_messages):
        print(f"\nMessage {i+1}: {msg}")

        # Parse expected values
        data = json.loads(msg)
        expected_input = data['usage']['input_tokens']
        expected_output = data['usage']['output_tokens']
        expected_total = data['usage']['total_tokens']

        total_expected_input += expected_input
        total_expected_output += expected_output
        total_expected_total += expected_total

        # Process with orchestrator
        orchestrator._try_parse_json_token_usage(msg, status)

        print(f"  Expected cumulative: input={total_expected_input}, output={total_expected_output}, total={total_expected_total}")
        print(f"  Actual after parsing: input={status.input_tokens}, output={status.output_tokens}, total={status.total_tokens}")

        # Check if we're losing data due to max()
        if status.total_tokens < total_expected_total:
            print(f"  ❌ PROBLEM: Using max() instead of += loses cumulative token data!")

def test_tool_counting_issue():
    """Test tool counting issues."""
    print("\n" + "=" * 80)
    print("TESTING TOOL COUNTING ISSUES")
    print("=" * 80)

    workspace = Path.cwd()
    orchestrator = ClaudeInstanceOrchestrator(workspace)

    status = InstanceStatus("test")

    tool_messages = [
        '{"type": "tool_use", "id": "tool_1", "name": "bash"}',  # Should increment
        '{"type": "tool_call", "id": "tool_2", "name": "read"}',  # Should increment
        '{"id": "msg_1", "type": "tool_use", "name": "edit"}',    # Should increment (with message ID)
        '{"id": "msg_1", "type": "tool_use", "name": "edit"}',    # Duplicate message ID - should NOT increment again
    ]

    print("Processing tool usage messages:")

    for i, msg in enumerate(tool_messages):
        print(f"\nTool message {i+1}: {msg}")
        print(f"  Tool calls before: {status.tool_calls}")

        orchestrator._try_parse_json_token_usage(msg, status)

        print(f"  Tool calls after: {status.tool_calls}")

    expected_tools = 3  # First 3 should count, 4th is duplicate
    if status.tool_calls != expected_tools:
        print(f"❌ TOOL COUNTING ISSUE: Expected {expected_tools}, got {status.tool_calls}")

def test_status_report_display():
    """Test if status reports show token information correctly."""
    print("\n" + "=" * 80)
    print("TESTING STATUS REPORT DISPLAY")
    print("=" * 80)

    workspace = Path.cwd()
    orchestrator = ClaudeInstanceOrchestrator(
        workspace,
        overall_token_budget=1000,
        enable_budget_visuals=True
    )

    # Create a fake instance with token usage
    from claude_instance_orchestrator import InstanceConfig
    config = InstanceConfig(command="/test", name="test_instance")
    orchestrator.add_instance(config)

    # Manually set some token usage to test display
    status = orchestrator.statuses["test_instance"]
    status.total_tokens = 450
    status.input_tokens = 300
    status.output_tokens = 150
    status.cached_tokens = 50
    status.tool_calls = 5

    # Record this in the budget manager
    orchestrator.budget_manager.record_usage("/test", 450)

    print("Testing status report with token data:")
    print("Status data:")
    print(f"  Total tokens: {status.total_tokens}")
    print(f"  Input tokens: {status.input_tokens}")
    print(f"  Output tokens: {status.output_tokens}")
    print(f"  Cached tokens: {status.cached_tokens}")
    print(f"  Tool calls: {status.tool_calls}")

    print("\nGenerated status report:")
    import asyncio
    try:
        # This might fail without running instances, but let's try
        asyncio.run(orchestrator._print_status_report(final=True))
    except Exception as e:
        print(f"Status report error (expected): {e}")
        # Manually show what would be displayed
        print("Manual status display:")
        token_info = orchestrator._format_tokens(status.total_tokens)
        cache_info = orchestrator._format_tokens(status.cached_tokens)
        print(f"  Token display: {token_info}")
        print(f"  Cache display: {cache_info}")

if __name__ == "__main__":
    print("COMPREHENSIVE ANALYSIS: Why User Reports 'Tokens Remain 0'")

    test_real_format_parsing()
    test_max_vs_add_issue()
    test_tool_counting_issue()
    test_status_report_display()

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("Key Issues Found:")
    print("1. Real Claude delta.usage format not parsed")
    print("2. max() vs += causing cumulative token loss")
    print("3. Tool counting may have message ID deduplication issues")
    print("4. Status reporting needs verification")
    print("=" * 80)
#!/usr/bin/env python3
"""Debug token parsing to understand why tokens might remain at 0."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from claude_instance_orchestrator import ClaudeInstanceOrchestrator, InstanceStatus

def test_json_parsing():
    """Test JSON parsing with various realistic Claude outputs."""
    print("=" * 80)
    print("TESTING JSON TOKEN PARSING")
    print("=" * 80)

    workspace = Path.cwd()
    orchestrator = ClaudeInstanceOrchestrator(workspace)

    status = InstanceStatus("test")

    # Test various JSON formats that Claude might output
    test_cases = [
        # Standard usage format
        '{"usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}}',

        # Message with usage
        '{"message": {"usage": {"input_tokens": 200, "output_tokens": 75, "total_tokens": 275}}}',

        # Direct token fields
        '{"input_tokens": 50, "output_tokens": 25, "total_tokens": 75}',

        # Tool usage
        '{"type": "tool_use", "name": "bash", "id": "tool_1"}',

        # Cached tokens
        '{"usage": {"input_tokens": 100, "output_tokens": 50, "cache_read_input_tokens": 25, "total_tokens": 175}}',

        # Alternative format
        '{"tokens": {"input": 80, "output": 40, "total": 120}}',
    ]

    print(f"Initial status: input={status.input_tokens}, output={status.output_tokens}, total={status.total_tokens}, tools={status.tool_calls}")

    for i, json_line in enumerate(test_cases):
        print(f"\nTest case {i+1}: {json_line}")

        # Test the JSON parsing
        result = orchestrator._try_parse_json_token_usage(json_line, status)

        print(f"  Parse result: {result}")
        print(f"  Status after: input={status.input_tokens}, output={status.output_tokens}, total={status.total_tokens}, tools={status.tool_calls}")

def test_fallback_parsing():
    """Test fallback regex parsing."""
    print("\n" + "=" * 80)
    print("TESTING FALLBACK REGEX PARSING")
    print("=" * 80)

    workspace = Path.cwd()
    orchestrator = ClaudeInstanceOrchestrator(workspace)

    status = InstanceStatus("test")

    # Test various text formats that might contain token info
    text_cases = [
        "Used 150 tokens",
        "150 tokens used",
        "Input: 100 tokens, Output: 50 tokens",
        "Total: 200 tokens",
        "Cached: 25 tokens",
        "Tool execution completed",
        "Executing tool bash",
        "Input tokens: 80, Output tokens: 40, Total tokens: 120",
        "Cache hit: 30 tokens"
    ]

    print(f"Initial status: input={status.input_tokens}, output={status.output_tokens}, total={status.total_tokens}, tools={status.tool_calls}")

    for i, text_line in enumerate(text_cases):
        print(f"\nTest case {i+1}: '{text_line}'")

        # Test the fallback parsing
        orchestrator._parse_token_usage_fallback(text_line, status)

        print(f"  Status after: input={status.input_tokens}, output={status.output_tokens}, total={status.total_tokens}, tools={status.tool_calls}")

def test_message_id_deduplication():
    """Test message ID deduplication to see if this causes issues."""
    print("\n" + "=" * 80)
    print("TESTING MESSAGE ID DEDUPLICATION")
    print("=" * 80)

    workspace = Path.cwd()
    orchestrator = ClaudeInstanceOrchestrator(workspace)

    status = InstanceStatus("test")

    # Test same message ID being processed multiple times (should not duplicate)
    duplicate_messages = [
        '{"id": "msg_123", "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}}',
        '{"id": "msg_123", "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}}',  # Duplicate
        '{"id": "msg_124", "usage": {"input_tokens": 50, "output_tokens": 25, "total_tokens": 75}}',   # New message
    ]

    print(f"Initial status: total={status.total_tokens}")

    for i, json_line in enumerate(duplicate_messages):
        print(f"\nProcessing message {i+1}: {json_line}")

        result = orchestrator._try_parse_json_token_usage(json_line, status)

        print(f"  Parse result: {result}")
        print(f"  Status after: total={status.total_tokens}")
        print(f"  Processed message IDs: {status.processed_message_ids}")

def test_real_claude_output_simulation():
    """Test with simulated real Claude output."""
    print("\n" + "=" * 80)
    print("TESTING SIMULATED REAL CLAUDE OUTPUT")
    print("=" * 80)

    # Simulate what a real Claude Code session might output
    simulated_output = '''
{"type":"message_start","message":{"id":"msg_01ABC123","type":"message","role":"assistant"}}
{"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}
{"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"I'll help you with that task."}}
{"type":"content_block_stop","index":0}
{"type":"message_delta","delta":{"stop_reason":"end_turn","usage":{"input_tokens":45,"output_tokens":12,"total_tokens":57}}}
{"type":"message_stop"}
    '''.strip()

    workspace = Path.cwd()
    orchestrator = ClaudeInstanceOrchestrator(workspace)

    status = InstanceStatus("test_real")

    print(f"Initial status: input={status.input_tokens}, output={status.output_tokens}, total={status.total_tokens}")

    lines = simulated_output.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        if line:
            print(f"\nProcessing line {i+1}: {line}")
            orchestrator._parse_token_usage(line, status, "test_real")
            print(f"  Status after: input={status.input_tokens}, output={status.output_tokens}, total={status.total_tokens}")

if __name__ == "__main__":
    print("DEBUGGING TOKEN PARSING - WHY TOKENS MIGHT STAY AT 0")

    test_json_parsing()
    test_fallback_parsing()
    test_message_id_deduplication()
    test_real_claude_output_simulation()

    print("\n" + "=" * 80)
    print("DEBUGGING COMPLETE")
    print("=" * 80)
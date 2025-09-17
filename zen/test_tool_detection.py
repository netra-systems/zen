#!/usr/bin/env python3
"""
Test script to verify tool detection improvements
"""

import json
import tempfile
import logging
from claude_instance_orchestrator import ClaudeInstanceOrchestrator, InstanceStatus

# Set up debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_tool_detection():
    """Test tool detection with sample Claude Code output"""
    orchestrator = ClaudeInstanceOrchestrator(
        config_path="minimal_config.json",
        max_console_lines=10
    )

    # Create a test instance status
    status = InstanceStatus(name="test", pid=12345, status="running")

    # Sample JSON lines that should contain tool usage (from actual Claude Code output)
    test_lines = [
        # Claude Code tool_use format
        '{"type":"assistant","message":{"id":"msg_01DS2yqzfsa5xnz2R61zSUve","type":"message","role":"assistant","model":"claude-sonnet-4-20250514","content":[{"type":"tool_use","id":"toolu_012HQ7HEagRQagFAuhGic75q","name":"Task","input":{"subagent_type":"git-commit-gardener","description":"Analyze and organize git commits","prompt":"You are the git commit gardener agent..."}}],"stop_reason":null,"stop_sequence":null,"usage":{"input_tokens":4,"cache_creation_input_tokens":31740,"cache_read_input_tokens":8843,"cache_creation":{"ephemeral_5m_input_tokens":31740,"ephemeral_1h_input_tokens":0},"output_tokens":3,"service_tier":"standard"}},"parent_tool_use_id":null,"session_id":"19c70f2c-ff69-45e8-a5ee-fabf6e72701f","uuid":"4173460e-0ee6-43fd-b75d-fa24abbfbb5d"}',

        # Direct tool_use format
        '{"type":"tool_use","id":"toolu_018vGJBa7XHoBMeSCCSmgVAz","name":"Bash","input":{"command":"git status","description":"Check current git status"}}',

        # Tool result format
        '{"type":"user","message":{"role":"user","content":[{"type":"tool_result","content":"On branch develop-long-lived...","is_error":false,"tool_use_id":"toolu_018vGJBa7XHoBMeSCCSmgVAz"}]},"parent_tool_use_id":"toolu_016b4hCKritHgbXH2EVw1vLB","session_id":"19c70f2c-ff69-45e8-a5ee-fabf6e72701f","uuid":"c17cdd23-cdc3-425e-8194-ea2a8980dd7e"}'
    ]

    print("Testing tool detection...")
    print(f"Initial state: tool_details={status.tool_details}, tool_tokens={status.tool_tokens}, tool_calls={status.tool_calls}")

    for i, line in enumerate(test_lines):
        print(f"\n--- Testing line {i+1} ---")
        print(f"Line preview: {line[:100]}...")

        # Test the parsing method
        result = orchestrator._try_parse_json_token_usage(line, status)
        print(f"Parse result: {result}")
        print(f"After parsing: tool_details={status.tool_details}, tool_tokens={status.tool_tokens}, tool_calls={status.tool_calls}")

    print(f"\nFinal results:")
    print(f"- tool_details: {status.tool_details}")
    print(f"- tool_tokens: {status.tool_tokens}")
    print(f"- tool_calls: {status.tool_calls}")

    # Test table display condition
    all_tools = {}
    for tool_name, count in status.tool_details.items():
        if tool_name not in all_tools:
            all_tools[tool_name] = {"count": 0, "tokens": 0, "instances": []}
        all_tools[tool_name]["count"] += count
        all_tools[tool_name]["tokens"] += status.tool_tokens.get(tool_name, 0)

    print(f"\nTable display check:")
    print(f"- all_tools: {all_tools}")
    print(f"- Would table display? {bool(all_tools)}")

if __name__ == "__main__":
    test_tool_detection()
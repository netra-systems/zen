#!/usr/bin/env python3
"""
Quick test to verify Issue #973 fix for WebSocket event structure validation
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from netra_backend.app.websocket_core.unified_manager import _serialize_message_safely

def test_event_structure_fix():
    """Test that WebSocket events preserve business data structure at top level."""
    
    print("Testing Issue #973 fix - WebSocket event structure validation")
    print("=" * 60)
    
    # Test agent_started event
    agent_started_data = {
        "type": "agent_started",
        "user_id": "test_user_123",
        "thread_id": "thread_456", 
        "agent_name": "DataHelperAgent",
        "task_description": "Analyze user request",
        "timestamp": 1234567890.0
    }
    
    print("\n1. Testing agent_started event structure:")
    print(f"   Input: {agent_started_data}")
    
    wrapped_event = _serialize_message_safely(agent_started_data)
    print(f"   Output: {wrapped_event}")
    
    # Validate critical fields at top level
    assert "user_id" in wrapped_event, f"user_id missing from wrapped event. Got: {wrapped_event}"
    assert wrapped_event["user_id"] == "test_user_123", f"user_id value incorrect"
    assert "thread_id" in wrapped_event, f"thread_id missing from wrapped event. Got: {wrapped_event}"
    assert wrapped_event["thread_id"] == "thread_456", f"thread_id value incorrect"
    assert "agent_name" in wrapped_event, f"agent_name missing from wrapped event. Got: {wrapped_event}"
    assert wrapped_event["agent_name"] == "DataHelperAgent", f"agent_name value incorrect"
    assert wrapped_event["type"] == "agent_started", f"event type incorrect"
    
    print("   ✅ PASS: agent_started event structure preserved")
    
    # Test tool_executing event
    tool_executing_data = {
        "type": "tool_executing",
        "tool_name": "search_analyzer",
        "tool_args": {"query": "test search"},
        "execution_id": "exec_123",
        "timestamp": 1234567890.0,
        "user_id": "test_user_456"
    }
    
    print("\n2. Testing tool_executing event structure:")
    print(f"   Input: {tool_executing_data}")
    
    wrapped_event = _serialize_message_safely(tool_executing_data)
    print(f"   Output: {wrapped_event}")
    
    assert "tool_name" in wrapped_event, f"tool_name missing from wrapped event. Got: {wrapped_event}"
    assert wrapped_event["tool_name"] == "search_analyzer", f"tool_name value incorrect"
    assert "tool_args" in wrapped_event, f"tool_args missing from wrapped event. Got: {wrapped_event}"
    assert isinstance(wrapped_event["tool_args"], dict), f"tool_args not dict type"
    assert "execution_id" in wrapped_event, f"execution_id missing from wrapped event. Got: {wrapped_event}"
    assert wrapped_event["type"] == "tool_executing", f"Event type incorrect"
    
    print("   ✅ PASS: tool_executing event structure preserved")
    
    # Test agent_thinking event
    agent_thinking_data = {
        "type": "agent_thinking",
        "reasoning": "I need to analyze the user's request for data patterns...",
        "agent_name": "DataHelperAgent",
        "step_number": 2,
        "user_id": "test_user_123",
        "timestamp": 1234567890.0
    }
    
    print("\n3. Testing agent_thinking event structure:")
    print(f"   Input: {agent_thinking_data}")
    
    wrapped_event = _serialize_message_safely(agent_thinking_data)
    print(f"   Output: {wrapped_event}")
    
    assert "reasoning" in wrapped_event, f"reasoning missing. Got: {wrapped_event}"
    assert "agent_name" in wrapped_event, f"agent_name missing. Got: {wrapped_event}"
    assert "step_number" in wrapped_event, f"step_number missing. Got: {wrapped_event}"
    assert wrapped_event["reasoning"] == "I need to analyze the user's request for data patterns..."
    assert wrapped_event["agent_name"] == "DataHelperAgent"
    assert wrapped_event["step_number"] == 2
    assert wrapped_event["type"] == "agent_thinking"
    
    print("   ✅ PASS: agent_thinking event structure preserved")
    
    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED - Issue #973 fix verified!")
    print("WebSocket events now preserve business data at top level")
    return True

if __name__ == "__main__":
    try:
        test_event_structure_fix()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
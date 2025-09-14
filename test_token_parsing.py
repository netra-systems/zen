#!/usr/bin/env python3
"""
Test script to verify the token parsing fix works correctly
"""

import json
import sys
import os

# Add the scripts directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

# Import after path is set
try:
    exec(open('scripts/claude-instance-orchestrator.py').read())
    # The classes will now be available in the current namespace
except Exception as e:
    print(f"Error loading orchestrator: {e}")
    sys.exit(1)
from pathlib import Path

def test_token_parsing():
    """Test token parsing with real JSON data from Claude Code"""
    
    # Create a test instance status
    status = InstanceStatus(name="test")
    
    # Create orchestrator just for the parsing methods
    orchestrator = ClaudeInstanceOrchestrator(Path.cwd())
    
    # Test JSON with cache_creation_input_tokens (from real Claude Code output)
    test_json = """{"type":"assistant","message":{"id":"msg_01N6TtnurjB7M1d7Rs4MUUcF","type":"message","role":"assistant","model":"claude-sonnet-4-20250514","usage":{"input_tokens":10,"cache_creation_input_tokens":23762,"cache_read_input_tokens":11357,"cache_creation":{"ephemeral_5m_input_tokens":23762,"ephemeral_1h_input_tokens":0},"output_tokens":2,"service_tier":"standard"}}}"""
    
    print("Testing token parsing with real Claude Code JSON...")
    print(f"Before parsing: total={status.total_tokens}, input={status.input_tokens}, output={status.output_tokens}, cached={status.cached_tokens}")
    
    # Parse the JSON
    orchestrator._parse_token_usage(test_json, status)
    
    print(f"After parsing: total={status.total_tokens}, input={status.input_tokens}, output={status.output_tokens}, cached={status.cached_tokens}")
    
    # Expected values:
    # input_tokens: 10
    # output_tokens: 2  
    # cached_tokens: 23762 (cache_creation) + 11357 (cache_read) = 35119
    # total_tokens: 10 + 2 + 23762 + 11357 = 35131
    
    expected_input = 10
    expected_output = 2
    expected_cached = 23762 + 11357  # 35119
    expected_total = 10 + 2 + 23762 + 11357  # 35131
    
    print(f"Expected: total={expected_total}, input={expected_input}, output={expected_output}, cached={expected_cached}")
    
    # Verify results
    success = True
    if status.input_tokens != expected_input:
        print(f"❌ Input tokens mismatch: got {status.input_tokens}, expected {expected_input}")
        success = False
    
    if status.output_tokens != expected_output:
        print(f"❌ Output tokens mismatch: got {status.output_tokens}, expected {expected_output}")
        success = False
    
    if status.cached_tokens != expected_cached:
        print(f"❌ Cached tokens mismatch: got {status.cached_tokens}, expected {expected_cached}")
        success = False
    
    if status.total_tokens != expected_total:
        print(f"❌ Total tokens mismatch: got {status.total_tokens}, expected {expected_total}")
        success = False
    
    if success:
        print("✅ All token parsing tests passed!")
        return True
    else:
        print("❌ Token parsing tests failed!")
        return False

if __name__ == "__main__":
    success = test_token_parsing()
    sys.exit(0 if success else 1)
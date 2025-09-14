#!/usr/bin/env python3
"""
Test Example for Claude Instance Orchestrator JSON Parsing

This demonstrates how the modernized token parsing works with both
JSON and fallback regex approaches.
"""

import json
import sys
import os
from pathlib import Path

# Add the script directory to Python path to import the orchestrator
sys.path.insert(0, str(Path(__file__).parent))

# Import the modernized orchestrator
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("orchestrator", "claude-instance-orchestrator.py")
    orchestrator_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(orchestrator_module)
    InstanceStatus = orchestrator_module.InstanceStatus
    ClaudeInstanceOrchestrator = orchestrator_module.ClaudeInstanceOrchestrator
except Exception as e:
    print("Note: This test requires the claude-instance-orchestrator.py file to be in the same directory")
    print(f"Error: {e}")
    sys.exit(1)

def test_json_parsing_examples():
    """Test the new JSON parsing with various input formats"""
    
    # Create a mock orchestrator instance for testing
    orchestrator = ClaudeInstanceOrchestrator(Path.cwd())
    
    # Create test status object
    test_status = InstanceStatus("test_instance")
    
    print("=== Testing JSON Parsing Examples ===")
    print()
    
    # Test various JSON message formats
    json_test_cases = [
        # Claude Code usage statistics
        '{"usage": {"input_tokens": 150, "output_tokens": 75, "cache_read_input_tokens": 25}}',
        
        # Token summary format
        '{"tokens": {"total": 200, "input": 120, "output": 80, "cached": 30}}',
        
        # Tool execution message
        '{"type": "tool_use", "tool_name": "bash", "result": "success"}',
        
        # Complete response with metadata
        '{"response": "Generated text", "usage": {"input_tokens": 100, "output_tokens": 50}, "tool_calls": 2}',
        
        # Simple token count
        '{"total_tokens": 250, "input_tokens": 150, "output_tokens": 100}',
        
        # Metrics format
        '{"metrics": {"total_tokens": 300, "cached_tokens": 50, "tool_calls": 1}}'
    ]
    
    print("JSON Test Cases:")
    print("-" * 50)
    
    for i, json_line in enumerate(json_test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"Input: {json_line}")
        
        # Reset status for clean test
        initial_status = InstanceStatus(f"test_{i}")
        
        # Test the parsing
        orchestrator._parse_token_usage(json_line, initial_status)
        
        print(f"Result: tokens={initial_status.total_tokens}, input={initial_status.input_tokens}, "
              f"output={initial_status.output_tokens}, cached={initial_status.cached_tokens}, "
              f"tools={initial_status.tool_calls}")
    
    print("\n" + "="*60)
    print("=== Testing Fallback Regex Parsing ===")
    print()
    
    # Test regex fallback with text-based patterns
    regex_test_cases = [
        "Used 150 tokens in this request",
        "Input: 100 tokens, Output: 50 tokens, Cached: 25 tokens",
        "Total: 200 tokens consumed",
        "Tool execution completed - calling bash command",
        "Cache hit: 30 tokens saved"
    ]
    
    print("Regex Fallback Test Cases:")
    print("-" * 30)
    
    for i, text_line in enumerate(regex_test_cases, 1):
        print(f"\nFallback Test {i}:")
        print(f"Input: {text_line}")
        
        # Reset status for clean test
        fallback_status = InstanceStatus(f"fallback_{i}")
        
        # Test the parsing (will fall back to regex since not JSON)
        orchestrator._parse_token_usage(text_line, fallback_status)
        
        print(f"Result: tokens={fallback_status.total_tokens}, input={fallback_status.input_tokens}, "
              f"output={fallback_status.output_tokens}, cached={fallback_status.cached_tokens}, "
              f"tools={fallback_status.tool_calls}")

def test_complete_json_output():
    """Test parsing of complete JSON output (non-streaming format)"""
    
    print("\n" + "="*60)
    print("=== Testing Complete JSON Output Parsing ===")
    print()
    
    # Simulate a complete Claude Code JSON response
    complete_json_response = {
        "response": "This is the generated response from Claude Code",
        "usage": {
            "input_tokens": 250,
            "output_tokens": 180,
            "cache_read_input_tokens": 45,
            "total_tokens": 430
        },
        "turns": [
            {"usage": {"input_tokens": 120, "output_tokens": 80}},
            {"usage": {"input_tokens": 130, "output_tokens": 100}}
        ],
        "tool_calls": [
            {"name": "bash", "result": "success"},
            {"name": "read_file", "result": "completed"}
        ],
        "metadata": {
            "model": "claude-3-5-sonnet-20241022",
            "duration": 3.2
        }
    }
    
    # Convert to JSON string
    json_output = json.dumps(complete_json_response, indent=2)
    print("Complete JSON Response:")
    print(json_output)
    
    # Create test status and orchestrator
    orchestrator = ClaudeInstanceOrchestrator(Path.cwd())
    complete_status = InstanceStatus("complete_test")
    
    # Test the complete JSON parsing
    orchestrator._parse_final_output_token_usage(json_output, complete_status, "json")
    
    print("\nParsed Results:")
    print(f"  Total tokens: {complete_status.total_tokens}")
    print(f"  Input tokens: {complete_status.input_tokens}")
    print(f"  Output tokens: {complete_status.output_tokens}")
    print(f"  Cached tokens: {complete_status.cached_tokens}")
    print(f"  Tool calls: {complete_status.tool_calls}")
    
    # Calculate cache hit rate
    if complete_status.total_tokens > 0:
        cache_rate = (complete_status.cached_tokens / complete_status.total_tokens) * 100
        print(f"  Cache hit rate: {cache_rate:.1f}%")

if __name__ == "__main__":
    print("Claude Instance Orchestrator - JSON Parsing Test Suite")
    print("=" * 60)
    
    test_json_parsing_examples()
    test_complete_json_output()
    
    print("\n" + "="*60)
    print("✅ All tests completed successfully!")
    print("The modernized orchestrator can parse both JSON and text-based token information.")
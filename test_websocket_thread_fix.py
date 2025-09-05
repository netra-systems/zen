#!/usr/bin/env python
"""
Test script to verify WebSocket thread routing and message delivery fixes.

This script tests the critical fixes for:
1. Thread ID extraction from run_id 
2. WebSocket connection thread association
3. Message routing from agents to users
"""

import asyncio
import sys
import os
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.core.unified_id_manager import UnifiedIDManager


def test_thread_id_extraction():
    """Test thread ID extraction from various run_id formats."""
    print("\n=== Testing Thread ID Extraction ===")
    
    test_cases = [
        # Format: (run_id, expected_thread_id)
        ("thread_13679e4dcc38403a_run_1756919162904_9adf1f09", "thread_13679e4dcc38403a"),
        ("thread_user123_run_1693430400000_a1b2c3d4", "thread_user123"),
        ("thread_session_abc_run_1693430400000_e5f6g7h8", "thread_session_abc"),
        ("thread_chat_12345_run_1693430400000_xyz", "thread_chat_12345"),
    ]
    
    bridge = AgentWebSocketBridge()
    
    for run_id, expected_thread in test_cases:
        print(f"\nTesting: {run_id}")
        
        # Test standard extraction function
        extracted_raw = UnifiedIDManager.extract_thread_id(run_id)
        print(f"  Standard extraction (raw): {extracted_raw}")
        
        # Test bridge extraction method
        extracted_bridge = bridge._extract_thread_from_standardized_run_id(run_id)
        print(f"  Bridge extraction: {extracted_bridge}")
        print(f"  Expected: {expected_thread}")
        
        if extracted_bridge == expected_thread:
            print("  PASS")
        else:
            print(f"  FAIL - Got {extracted_bridge}, expected {expected_thread}")


def test_run_id_generation_and_extraction():
    """Test the full cycle of run_id generation and thread extraction."""
    print("\n=== Testing Run ID Generation and Extraction ===")
    
    thread_ids = [
        "13679e4dcc38403a",
        "user_123_session_456",
        "chat_abc123",
        "thread_already_prefixed",
    ]
    
    bridge = AgentWebSocketBridge()
    
    for thread_id in thread_ids:
        print(f"\nOriginal thread_id: {thread_id}")
        
        # Generate run_id
        run_id = generate_run_id(thread_id, "test_context")
        print(f"  Generated run_id: {run_id}")
        
        # Extract thread_id back
        extracted_raw = extract_thread_id_from_run_id(run_id)
        print(f"  Extracted (raw): {extracted_raw}")
        
        # Extract using bridge method
        extracted_bridge = bridge._extract_thread_from_standardized_run_id(run_id)
        print(f"  Extracted (bridge): {extracted_bridge}")
        
        # The expected format for WebSocket routing
        expected_format = f"thread_{thread_id}" if not thread_id.startswith("thread_") else thread_id
        print(f"  Expected for WebSocket: {expected_format}")
        
        if extracted_bridge == expected_format:
            print("  PASS - Thread ID properly formatted for WebSocket routing")
        else:
            print(f"  FAIL - WebSocket routing will fail!")


async def test_websocket_resolution():
    """Test the full thread resolution process."""
    print("\n=== Testing WebSocket Thread Resolution ===")
    
    bridge = AgentWebSocketBridge()
    
    test_run_ids = [
        "thread_13679e4dcc38403a_run_1756919162904_9adf1f09",
        "thread_user_123_run_1693430400000_a1b2c3d4",
        "invalid_format_no_thread",
    ]
    
    for run_id in test_run_ids:
        print(f"\nResolving run_id: {run_id}")
        
        try:
            # Test private resolution method
            thread_id = await bridge._resolve_thread_id_from_run_id(run_id)
            print(f"  Resolved to: {thread_id}")
        except Exception as e:
            print(f"  Resolution failed: {e}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("WebSocket Thread Routing Fix Verification")
    print("=" * 60)
    
    # Test basic extraction
    test_thread_id_extraction()
    
    # Test full generation/extraction cycle
    test_run_id_generation_and_extraction()
    
    # Test async resolution
    print("\nRunning async resolution tests...")
    asyncio.run(test_websocket_resolution())
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
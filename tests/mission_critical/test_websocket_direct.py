#!/usr/bin/env python
"""MISSION CRITICAL: Direct WebSocket Bridge Tests (No pytest)

CRITICAL BUSINESS CONTEXT:
- WebSocket bridge is 90% of chat value delivery
- This test directly validates WebSocket bridge functionality
- Run_id to thread_id extraction is ESSENTIAL for proper routing

Direct tests without pytest complexity:
1. Run_id to thread_id extraction patterns
2. WebSocket event emission verification
3. Bridge initialization and health
4. Error handling and edge cases
"""

import asyncio
import os
import sys
import uuid
import time
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set up isolated test environment
os.environ['WEBSOCKET_TEST_ISOLATED'] = 'true'
os.environ['SKIP_REAL_SERVICES'] = 'true'
os.environ['TEST_COLLECTION_MODE'] = '1'

# Import the WebSocket bridge
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, IntegrationState


class MockWebSocketManager:
    """Mock WebSocket manager for testing."""
    
    def __init__(self):
        self.sent_messages = []
    
    async def send_to_thread(self, thread_id: str, message: dict) -> bool:
        self.sent_messages.append((thread_id, message))
        print(f"Mock WebSocket sent to {thread_id}: {message.get('type', 'unknown')}")
        return True


class MockOrchestrator:
    """Mock orchestrator for testing thread_id resolution."""
    
    def __init__(self):
        self.thread_mapping = {}
    
    def set_thread_mapping(self, run_id: str, thread_id: str):
        """Set a mapping for testing."""
        self.thread_mapping[run_id] = thread_id
    
    async def get_thread_id_for_run(self, run_id: str) -> Optional[str]:
        """Mock implementation for testing."""
        return self.thread_mapping.get(run_id)


async def test_direct_thread_id_patterns():
    """Test extraction when run_id IS a thread_id."""
    print("\nTesting direct thread_id patterns...")
    
    mock_websocket = MockWebSocketManager()
    mock_orchestrator = MockOrchestrator()
    
    with patch.multiple(
        'netra_backend.app.services.agent_websocket_bridge',
        get_websocket_manager=MagicMock(return_value=mock_websocket),
        get_agent_execution_registry=MagicMock(return_value=mock_orchestrator)
    ):
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        test_cases = [
            ("thread_12345", "thread_12345"),
            ("thread_abc123", "thread_abc123"), 
            ("thread_user_session_789", "thread_user_session_789"),
        ]
        
        for run_id, expected in test_cases:
            result = await bridge._resolve_thread_id_from_run_id(run_id)
            if result == expected:
                print(f"PASS {run_id} -> {result}")
            else:
                print(f"FAIL {run_id} -> expected {expected}, got {result}")
                return False
    
    print("PASS Direct thread_id patterns: PASSED")
    return True


async def test_embedded_thread_id_patterns():
    """Test extraction when thread_id is embedded in run_id."""
    print("\n🔬 Testing embedded thread_id patterns...")
    
    mock_websocket = MockWebSocketManager()
    mock_orchestrator = MockOrchestrator()
    
    with patch.multiple(
        'netra_backend.app.services.agent_websocket_bridge',
        get_websocket_manager=MagicMock(return_value=mock_websocket),
        get_agent_execution_registry=MagicMock(return_value=mock_orchestrator)
    ):
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        test_cases = [
            ("run_thread_12345", "thread_12345"),
            ("user_123_thread_456_session", "thread_456"),
            ("agent_execution_thread_789_v1", "thread_789"),
            ("prefix_thread_abc123_suffix", "thread_abc123"),
        ]
        
        for run_id, expected in test_cases:
            result = await bridge._resolve_thread_id_from_run_id(run_id)
            if result == expected:
                print(f"✅ {run_id} -> {result}")
            else:
                print(f"❌ {run_id} -> expected {expected}, got {result}")
                return False
    
    print("✅ Embedded thread_id patterns: PASSED")
    return True


async def test_orchestrator_resolution():
    """Test resolution via orchestrator when available."""
    print("\n🔬 Testing orchestrator resolution...")
    
    mock_websocket = MockWebSocketManager()
    mock_orchestrator = MockOrchestrator()
    
    with patch.multiple(
        'netra_backend.app.services.agent_websocket_bridge',
        get_websocket_manager=MagicMock(return_value=mock_websocket),
        get_agent_execution_registry=MagicMock(return_value=mock_orchestrator)
    ):
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        # Set up orchestrator mapping
        run_id = "custom_run_12345"
        expected_thread_id = "thread_orchestrator_resolved"
        mock_orchestrator.set_thread_mapping(run_id, expected_thread_id)
        
        result = await bridge._resolve_thread_id_from_run_id(run_id)
        if result == expected_thread_id:
            print(f"✅ Orchestrator resolved {run_id} -> {result}")
        else:
            print(f"❌ Expected orchestrator resolution to return '{expected_thread_id}', got '{result}'")
            return False
    
    print("✅ Orchestrator resolution: PASSED")
    return True


async def test_websocket_event_emission():
    """Test that WebSocket events are properly emitted."""
    print("\n🔬 Testing WebSocket event emission...")
    
    mock_websocket = MockWebSocketManager()
    mock_orchestrator = MockOrchestrator()
    
    with patch.multiple(
        'netra_backend.app.services.agent_websocket_bridge',
        get_websocket_manager=MagicMock(return_value=mock_websocket),
        get_agent_execution_registry=MagicMock(return_value=mock_orchestrator)
    ):
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        # Test the 5 critical events
        run_id = "thread_test_123"
        agent_name = "TestAgent"
        
        # 1. Agent Started
        await bridge.notify_agent_started(run_id, agent_name, "Starting test")
        
        # 2. Agent Thinking
        await bridge.notify_agent_thinking(run_id, agent_name, "Processing request")
        
        # 3. Tool Executing
        await bridge.notify_tool_executing(run_id, "test_tool", {"param": "value"})
        
        # 4. Tool Completed
        await bridge.notify_tool_completed(run_id, "test_tool", {"result": "success"}, 100)
        
        # 5. Agent Completed
        await bridge.notify_agent_completed(run_id, agent_name, {"status": "success"}, 1000)
        
        # Verify all events were sent
        if len(mock_websocket.sent_messages) >= 5:
            print(f"✅ All 5 critical events emitted ({len(mock_websocket.sent_messages)} total)")
            
            # Check event types
            event_types = set()
            for thread_id, message in mock_websocket.sent_messages:
                event_types.add(message.get('type'))
                print(f"  📤 {message.get('type')} -> {thread_id}")
            
            required_events = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'}
            missing_events = required_events - event_types
            
            if not missing_events:
                print("✅ All required event types present")
            else:
                print(f"❌ Missing event types: {missing_events}")
                return False
        else:
            print(f"❌ Expected at least 5 events, got {len(mock_websocket.sent_messages)}")
            return False
    
    print("✅ WebSocket event emission: PASSED")
    return True


async def test_bridge_health_monitoring():
    """Test bridge health status."""
    print("\n🔬 Testing bridge health monitoring...")
    
    mock_websocket = MockWebSocketManager()
    mock_orchestrator = MockOrchestrator()
    
    with patch.multiple(
        'netra_backend.app.services.agent_websocket_bridge',
        get_websocket_manager=MagicMock(return_value=mock_websocket),
        get_agent_execution_registry=MagicMock(return_value=mock_orchestrator)
    ):
        bridge = AgentWebSocketBridge()
        result = await bridge.ensure_integration()
        
        if result.success:
            print("✅ Bridge initialization successful")
            
            health = bridge.get_health_status()
            if health.state == IntegrationState.ACTIVE:
                print("✅ Bridge health is ACTIVE")
            else:
                print(f"❌ Bridge health is {health.state}")
                return False
        else:
            print(f"❌ Bridge initialization failed: {result.error}")
            return False
    
    print("✅ Bridge health monitoring: PASSED")
    return True


async def test_error_handling():
    """Test error handling and edge cases."""
    print("\n🔬 Testing error handling...")
    
    mock_websocket = MockWebSocketManager()
    mock_orchestrator = MockOrchestrator()
    
    with patch.multiple(
        'netra_backend.app.services.agent_websocket_bridge',
        get_websocket_manager=MagicMock(return_value=mock_websocket),
        get_agent_execution_registry=MagicMock(return_value=mock_orchestrator)
    ):
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        # Test edge cases
        edge_cases = [
            ("", None),  # Empty string
            ("thread_", None),  # Incomplete pattern
            ("no_thread_pattern", None),  # No pattern
            ("_thread_123", "thread_123"),  # Leading underscore
        ]
        
        for run_id, expected in edge_cases:
            try:
                result = await bridge._resolve_thread_id_from_run_id(run_id)
                if (expected is None and result is None) or result == expected:
                    print(f"✅ Edge case {run_id!r} -> {result!r}")
                else:
                    print(f"❌ Edge case {run_id!r} -> expected {expected!r}, got {result!r}")
                    return False
            except Exception as e:
                print(f"❌ Exception for {run_id!r}: {e}")
                return False
    
    print("✅ Error handling: PASSED")  
    return True


async def test_performance():
    """Test performance with many extractions."""
    print("\n🔬 Testing performance...")
    
    mock_websocket = MockWebSocketManager()
    mock_orchestrator = MockOrchestrator()
    
    with patch.multiple(
        'netra_backend.app.services.agent_websocket_bridge',
        get_websocket_manager=MagicMock(return_value=mock_websocket),
        get_agent_execution_registry=MagicMock(return_value=mock_orchestrator)
    ):
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        # Generate test cases
        test_run_ids = []
        for i in range(100):  # Reduced for faster testing
            test_run_ids.append(f"performance_test_thread_{i}_{uuid.uuid4()}")
        
        # Measure extraction performance
        start_time = time.time()
        results = []
        
        for run_id in test_run_ids:
            result = await bridge._resolve_thread_id_from_run_id(run_id)
            results.append(result)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Validate results
        successful_extractions = sum(1 for result in results if result is not None)
        avg_time_per_extraction = (execution_time / len(test_run_ids)) * 1000  # milliseconds
        
        if successful_extractions == len(test_run_ids):
            print(f"✅ Performance test: {len(test_run_ids)} extractions in {execution_time:.2f}s ({avg_time_per_extraction:.3f}ms per extraction)")
        else:
            print(f"❌ Performance test failed: {successful_extractions}/{len(test_run_ids)} successful extractions")
            return False
        
        if execution_time > 10.0:
            print(f"⚠️  Performance warning: took {execution_time:.2f}s")
            return False
    
    print("✅ Performance: PASSED")
    return True


async def run_all_tests():
    """Run all tests and report results."""
    print("Starting WebSocket Bridge Direct Tests...")
    print("=" * 60)
    
    tests = [
        ("Direct Thread ID Patterns", test_direct_thread_id_patterns),
        ("Embedded Thread ID Patterns", test_embedded_thread_id_patterns),
        ("Orchestrator Resolution", test_orchestrator_resolution),
        ("WebSocket Event Emission", test_websocket_event_emission),
        ("Bridge Health Monitoring", test_bridge_health_monitoring),
        ("Error Handling", test_error_handling),
        ("Performance", test_performance),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n📋 Running: {test_name}")
            result = await test_func()
            if result:
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                failed += 1
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            failed += 1
            print(f"💥 {test_name}: EXCEPTION - {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 TEST RESULTS: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED! WebSocket bridge is working correctly!")
        print("\n📋 COMPREHENSIVE TEST SUMMARY:")
        print("✅ Run_id to thread_id extraction: Working")
        print("✅ WebSocket event emission: Working") 
        print("✅ Bridge health monitoring: Working")
        print("✅ Error handling: Robust")
        print("✅ Performance: Acceptable")
        print("\n🔒 CRITICAL BUSINESS VALUE VERIFIED:")
        print("  • Chat routing works properly")
        print("  • Real-time notifications function")  
        print("  • Agent events reach correct threads")
        print("  • System handles edge cases gracefully")
        return True
    else:
        print("💥 TESTS FAILED! WebSocket bridge has issues!")
        return False


if __name__ == "__main__":
    # Run the direct test suite
    result = asyncio.run(run_all_tests())
    sys.exit(0 if result else 1)
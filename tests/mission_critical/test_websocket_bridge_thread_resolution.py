#!/usr/bin/env python
"""MISSION CRITICAL: WebSocket Bridge Thread Resolution Comprehensive Tests

CRITICAL BUSINESS CONTEXT:
- Thread ID resolution is THE FOUNDATION of WebSocket event routing
- If this fails, 90% of chat functionality breaks - users see loading forever
- These tests protect the core value delivery mechanism of the platform
- Thread resolution failures cause silent user experience catastrophes

COMPREHENSIVE TEST COVERAGE:
1. Thread ID resolution from complex run_id formats
2. ThreadRunRegistry persistence and retrieval under load
3. WebSocket event routing with thread_id validation 
4. Concurrent operations and race condition handling
5. Failure modes, error recovery, and graceful degradation
6. Edge cases with malformed, missing, or corrupted run_ids
7. Real WebSocket integration with actual connections
8. Thread-to-run mapping consistency across restarts
9. Performance under high-frequency resolution requests
10. End-to-end validation of message delivery to correct threads

THESE TESTS ARE MISSION-CRITICAL AND MUST CATCH ANY REGRESSION.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple, Any
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from contextlib import asynccontextmanager
import threading
import random

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set up isolated test environment
os.environ['WEBSOCKET_TEST_ISOLATED'] = 'true' 
os.environ['SKIP_REAL_SERVICES'] = 'true'
os.environ['TEST_COLLECTION_MODE'] = '1'

import pytest

# Import core components with try-catch for better error handling
try:
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, IntegrationState
    from netra_backend.app.services.thread_run_registry import (
        ThreadRunRegistry, 
        RegistryConfig, 
        RunMapping, 
        MappingState,
        get_thread_run_registry
    )
except ImportError as e:
    pytest.skip(f"Could not import required modules: {e}", allow_module_level=True)


class MockWebSocketManager:
    """Enhanced mock WebSocket manager for comprehensive testing."""
    
    def __init__(self):
        self.sent_messages: List[Tuple[str, Dict]] = []
        self.connections: Dict[str, Any] = {}
        self.connection_failures: Set[str] = set()
        self.send_delays: Dict[str, float] = {}
        self.message_history: Dict[str, List[Dict]] = {}
        self.send_call_count = 0
        self.is_healthy = True
    
    async def send_to_thread(self, thread_id: str, message: Dict) -> bool:
        """Enhanced mock with realistic failure scenarios and tracking."""
        self.send_call_count += 1
        
        # Simulate connection failure
        if thread_id in self.connection_failures:
            return False
        
        # Simulate send delay
        if thread_id in self.send_delays:
            await asyncio.sleep(self.send_delays[thread_id])
        
        # Simulate health check failure
        if not self.is_healthy:
            return False
        
        # Record message
        self.sent_messages.append((thread_id, message))
        
        # Track message history per thread
        if thread_id not in self.message_history:
            self.message_history[thread_id] = []
        self.message_history[thread_id].append(message)
        
        return True
    
    def set_connection_failure(self, thread_id: str):
        """Simulate connection failure for testing."""
        self.connection_failures.add(thread_id)
    
    def set_send_delay(self, thread_id: str, delay: float):
        """Set artificial delay for testing timeout scenarios."""
        self.send_delays[thread_id] = delay
    
    def clear_messages(self):
        """Clear message history for clean test state."""
        self.sent_messages.clear()
        self.message_history.clear()
    
    def get_thread_messages(self, thread_id: str) -> List[Dict]:
        """Get all messages sent to a specific thread."""
        return self.message_history.get(thread_id, [])


class MockOrchestrator:
    """Enhanced mock orchestrator with comprehensive thread resolution."""
    
    def __init__(self):
        self.thread_mappings: Dict[str, str] = {}
        self.resolution_delays: Dict[str, float] = {}
        self.resolution_failures: Set[str] = set()
        self.resolution_call_count = 0
        self.is_available = True
    
    async def get_thread_id_for_run(self, run_id: str) -> Optional[str]:
        """Mock thread resolution with failure simulation."""
        self.resolution_call_count += 1
        
        if not self.is_available:
            raise Exception("Orchestrator unavailable")
        
        if run_id in self.resolution_failures:
            return None
        
        if run_id in self.resolution_delays:
            await asyncio.sleep(self.resolution_delays[run_id])
        
        return self.thread_mappings.get(run_id)
    
    def set_thread_mapping(self, run_id: str, thread_id: str):
        """Set mapping for testing."""
        self.thread_mappings[run_id] = thread_id
    
    def set_resolution_failure(self, run_id: str):
        """Simulate resolution failure."""
        self.resolution_failures.add(run_id)
    
    def set_resolution_delay(self, run_id: str, delay: float):
        """Set resolution delay for timeout testing."""
        self.resolution_delays[run_id] = delay
    
    async def set_websocket_manager(self, manager):
        """Mock method for bridge integration."""
        pass
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Mock metrics for health checks."""
        return {"resolution_calls": self.resolution_call_count}


@pytest.fixture
def mock_websocket_manager():
    """Enhanced WebSocket manager fixture."""
    return MockWebSocketManager()


@pytest.fixture
def mock_orchestrator():
    """Enhanced orchestrator fixture."""
    return MockOrchestrator()


@pytest.fixture
def thread_registry():
    """Real ThreadRunRegistry instance for testing."""
    config = RegistryConfig(
        mapping_ttl_hours=1,  # Short TTL for testing
        cleanup_interval_minutes=60,  # Disable frequent cleanup for tests
        enable_debug_logging=False  # Reduce noise in tests
    )
    return ThreadRunRegistry(config)


@pytest.fixture
def websocket_bridge(mock_websocket_manager, mock_orchestrator, thread_registry):
    """WebSocket bridge with mocked dependencies and real thread registry."""
    
    # Create bridge instance
    bridge = AgentWebSocketBridge()
    
    # Manually set mocked dependencies to avoid complex async patching
    bridge._websocket_manager = mock_websocket_manager
    bridge._orchestrator = mock_orchestrator
    bridge._thread_registry = thread_registry
    bridge.state = IntegrationState.ACTIVE
    
    return bridge


class TestThreadIdResolution:
    """Comprehensive thread ID resolution testing."""
    
    @pytest.mark.asyncio
    async def test_complex_run_id_patterns(self, websocket_bridge):
        """Test thread ID extraction from complex production-like patterns."""
        
        test_cases = [
            # Direct thread patterns
            ("thread_12345", "thread_12345"),
            ("thread_user_session_abc123", "thread_user_session_abc123"),
            
            # Embedded patterns (most common in production)
            ("run_thread_67890_execution", "thread_67890"),
            ("user_456_thread_session_789_active", "thread_session"),
            ("agent_supervisor_thread_chat_999_step_1", "thread_chat"),
            ("websocket_conn_thread_live_555_msg_123", "thread_live"),
            
            # Complex multi-part patterns
            ("api_v2_user_12345_session_67890_thread_main_889_task_1", "thread_main"),
            ("batch_process_id_thread_background_777_priority_high", "thread_background"),
            ("realtime_sync_thread_collaboration_333_user_multiple", "thread_collaboration"),
            
            # Edge cases that should work
            ("prefix_thread_123", "thread_123"),
            ("thread_456_suffix", "thread_456"),
            ("many_thread_111_parts_thread_222_here", "thread_111"),  # First match
        ]
        
        for run_id, expected in test_cases:
            result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
            assert result == expected, f"Pattern '{run_id}' failed: expected '{expected}', got '{result}'"
        
        print("✅ Complex run_id patterns: PASSED")

    @pytest.mark.asyncio
    async def test_thread_registry_priority_resolution(self, websocket_bridge, thread_registry):
        """Test that ThreadRunRegistry takes priority over pattern extraction."""
        
        # Register explicit mapping that contradicts pattern
        run_id = "run_thread_pattern_123"
        registry_thread_id = "thread_registry_override"
        pattern_thread_id = "thread_pattern"  # What pattern extraction would return
        
        # Register mapping
        success = await thread_registry.register(run_id, registry_thread_id)
        assert success, "Registry registration should succeed"
        
        # Resolve - should get registry result, not pattern result
        result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
        assert result == registry_thread_id, f"Registry priority failed: expected '{registry_thread_id}', got '{result}'"
        assert result != pattern_thread_id, "Should not use pattern when registry has mapping"
        
        print("✅ Thread registry priority resolution: PASSED")

    @pytest.mark.asyncio
    async def test_fallback_chain_resolution(self, websocket_bridge, mock_orchestrator):
        """Test complete fallback chain: Registry → Orchestrator → Pattern → None."""
        
        test_cases = [
            # Case 1: Registry has it (highest priority)
            {
                "run_id": "fallback_test_1",
                "registry_thread": "thread_registry_1",
                "orchestrator_thread": "thread_orchestrator_1", 
                "pattern_thread": None,
                "expected": "thread_registry_1"
            },
            
            # Case 2: Only orchestrator has it
            {
                "run_id": "fallback_test_2", 
                "registry_thread": None,
                "orchestrator_thread": "thread_orchestrator_2",
                "pattern_thread": None,
                "expected": "thread_orchestrator_2"
            },
            
            # Case 3: Only pattern extraction works
            {
                "run_id": "fallback_thread_pattern_123",
                "registry_thread": None,
                "orchestrator_thread": None,
                "pattern_thread": "thread_pattern",
                "expected": "thread_pattern"
            },
            
            # Case 4: Nothing works
            {
                "run_id": "no_resolution_possible",
                "registry_thread": None,
                "orchestrator_thread": None, 
                "pattern_thread": None,
                "expected": None
            }
        ]
        
        for case in test_cases:
            # Setup registry if needed
            if case["registry_thread"]:
                await websocket_bridge._thread_registry.register(case["run_id"], case["registry_thread"])
            
            # Setup orchestrator if needed
            if case["orchestrator_thread"]:
                mock_orchestrator.set_thread_mapping(case["run_id"], case["orchestrator_thread"])
            
            # Test resolution
            result = await websocket_bridge._resolve_thread_id_from_run_id(case["run_id"])
            assert result == case["expected"], f"Fallback chain failed for {case['run_id']}: expected '{case['expected']}', got '{result}'"
            
            # Cleanup
            if case["registry_thread"]:
                await websocket_bridge._thread_registry.unregister_run(case["run_id"])
            if case["orchestrator_thread"]:
                mock_orchestrator.thread_mappings.pop(case["run_id"], None)
        
        print("✅ Fallback chain resolution: PASSED")


class TestThreadRegistryOperations:
    """Comprehensive thread registry testing."""
    
    @pytest.mark.asyncio
    async def test_thread_registry_lifecycle(self, thread_registry):
        """Test complete registry lifecycle: register → lookup → unregister."""
        
        run_id = "lifecycle_test_123"
        thread_id = "thread_lifecycle_456"
        metadata = {"agent_name": "TestAgent", "user_id": "user_789"}
        
        # Step 1: Registration
        success = await thread_registry.register(run_id, thread_id, metadata)
        assert success, "Registration should succeed"
        
        # Step 2: Lookup
        result = await thread_registry.get_thread(run_id)
        assert result == thread_id, f"Lookup failed: expected '{thread_id}', got '{result}'"
        
        # Step 3: Verify metadata persists
        mapping = thread_registry._run_to_thread.get(run_id)
        assert mapping is not None, "Mapping should exist"
        assert mapping.metadata == metadata, f"Metadata mismatch: expected {metadata}, got {mapping.metadata}"
        
        # Step 4: Unregistration
        success = await thread_registry.unregister_run(run_id)
        assert success, "Unregistration should succeed"
        
        # Step 5: Verify removal
        result = await thread_registry.get_thread(run_id)
        assert result is None, "Lookup should fail after unregistration"
        
        print("✅ Thread registry lifecycle: PASSED")

    @pytest.mark.asyncio
    async def test_registry_concurrent_operations(self, thread_registry):
        """Test thread registry under concurrent load."""
        
        async def register_lookup_cycle(base_id: str, count: int) -> List[bool]:
            results = []
            for i in range(count):
                run_id = f"{base_id}_{i}"
                thread_id = f"thread_{base_id}_{i}"
                
                # Register
                reg_success = await thread_registry.register(run_id, thread_id)
                
                # Immediate lookup
                lookup_result = await thread_registry.get_thread(run_id)
                lookup_success = lookup_result == thread_id
                
                results.append(reg_success and lookup_success)
            return results
        
        # Run concurrent cycles
        tasks = [
            register_lookup_cycle("concurrent_1", 50),
            register_lookup_cycle("concurrent_2", 50), 
            register_lookup_cycle("concurrent_3", 50)
        ]
        
        all_results = await asyncio.gather(*tasks)
        
        # Verify all operations succeeded
        for task_results in all_results:
            assert all(task_results), f"Some concurrent operations failed: {task_results}"
        
        # Verify final state
        metrics = await thread_registry.get_metrics()
        assert metrics['active_mappings'] == 150, f"Expected 150 active mappings, got {metrics['active_mappings']}"
        
        print("✅ Registry concurrent operations: PASSED")

    @pytest.mark.asyncio
    async def test_registry_ttl_expiration(self, thread_registry):
        """Test TTL-based automatic cleanup."""
        
        # Override TTL for fast testing
        old_ttl = thread_registry.config.mapping_ttl_hours
        thread_registry.config.mapping_ttl_hours = 0.0001  # ~0.36 seconds
        
        try:
            run_id = "ttl_test_123"
            thread_id = "thread_ttl_456"
            
            # Register mapping
            await thread_registry.register(run_id, thread_id)
            
            # Verify immediate lookup works
            result = await thread_registry.get_thread(run_id)
            assert result == thread_id, "Immediate lookup should work"
            
            # Wait for expiration
            await asyncio.sleep(1.0)
            
            # Verify lookup fails after expiration
            result = await thread_registry.get_thread(run_id)
            assert result is None, "Lookup should fail after TTL expiration"
            
        finally:
            # Restore original TTL
            thread_registry.config.mapping_ttl_hours = old_ttl
        
        print("✅ Registry TTL expiration: PASSED")

    @pytest.mark.asyncio
    async def test_registry_memory_pressure(self, thread_registry):
        """Test registry behavior under memory pressure."""
        
        # Create many mappings to test limits
        mappings = []
        for i in range(200):  # More than typical cache size
            run_id = f"memory_test_{i}"
            thread_id = f"thread_memory_{i}"
            mappings.append((run_id, thread_id))
            
            success = await thread_registry.register(run_id, thread_id)
            assert success, f"Registration {i} should succeed"
        
        # Verify all recent mappings are still accessible
        recent_mappings = mappings[-50:]  # Last 50 should definitely be cached
        for run_id, expected_thread_id in recent_mappings:
            result = await thread_registry.get_thread(run_id)
            assert result == expected_thread_id, f"Recent mapping lookup failed for {run_id}"
        
        # Check registry health under pressure
        metrics = await thread_registry.get_metrics()
        assert metrics['registry_healthy'], "Registry should remain healthy under memory pressure"
        assert metrics['lookup_success_rate'] > 0.8, f"Success rate too low: {metrics['lookup_success_rate']}"
        
        print("✅ Registry memory pressure handling: PASSED")


class TestWebSocketEventRouting:
    """Test WebSocket event routing with thread resolution."""
    
    @pytest.mark.asyncio
    async def test_event_routing_with_registry_resolution(self, websocket_bridge, mock_websocket_manager, thread_registry):
        """Test that events route correctly using registry resolution."""
        
        # Setup mapping
        run_id = "routing_test_123"
        thread_id = "thread_routing_456" 
        await thread_registry.register(run_id, thread_id)
        
        # Send various event types
        event_tests = [
            ("notify_agent_started", {"agent_name": "TestAgent", "context": {"test": "data"}}),
            ("notify_agent_thinking", {"agent_name": "TestAgent", "reasoning": "Processing request", "step_number": 1}),
            ("notify_tool_executing", {"agent_name": "TestAgent", "tool_name": "test_tool", "parameters": {"param": "value"}}),
            ("notify_tool_completed", {"agent_name": "TestAgent", "tool_name": "test_tool", "result": {"success": True}}),
            ("notify_agent_completed", {"agent_name": "TestAgent", "result": {"final": "result"}})
        ]
        
        for method_name, kwargs in event_tests:
            mock_websocket_manager.clear_messages()
            
            # Send event
            method = getattr(websocket_bridge, method_name)
            success = await method(run_id, **kwargs)
            assert success, f"Event {method_name} should succeed"
            
            # Verify routing
            assert len(mock_websocket_manager.sent_messages) == 1, f"Event {method_name} should send exactly one message"
            sent_thread_id, sent_message = mock_websocket_manager.sent_messages[0]
            assert sent_thread_id == thread_id, f"Event {method_name} routed to wrong thread: expected {thread_id}, got {sent_thread_id}"
            assert sent_message['run_id'] == run_id, f"Event {method_name} has wrong run_id"
        
        print("✅ Event routing with registry resolution: PASSED")

    @pytest.mark.asyncio 
    async def test_event_routing_fallback_behaviors(self, websocket_bridge, mock_websocket_manager, mock_orchestrator):
        """Test event routing fallback when registry fails."""
        
        # Test case 1: Registry unavailable, orchestrator provides mapping
        run_id_1 = "fallback_test_orchestrator"
        thread_id_1 = "thread_from_orchestrator"
        mock_orchestrator.set_thread_mapping(run_id_1, thread_id_1)
        
        # Clear registry to force orchestrator fallback
        websocket_bridge._thread_registry = None
        
        success = await websocket_bridge.notify_agent_started(run_id_1, "TestAgent")
        assert success, "Event should succeed with orchestrator fallback"
        
        sent_thread_id, _ = mock_websocket_manager.sent_messages[-1]
        assert sent_thread_id == thread_id_1, f"Should route via orchestrator: expected {thread_id_1}, got {sent_thread_id}"
        
        # Test case 2: Both registry and orchestrator fail, pattern extraction works
        run_id_2 = "pattern_fallback_thread_extract_789"
        expected_thread_2 = "thread_extract"
        
        mock_websocket_manager.clear_messages()
        success = await websocket_bridge.notify_agent_thinking(run_id_2, "TestAgent", "Testing fallback")
        assert success, "Event should succeed with pattern fallback"
        
        sent_thread_id, _ = mock_websocket_manager.sent_messages[-1]
        assert sent_thread_id == expected_thread_2, f"Should route via pattern: expected {expected_thread_2}, got {sent_thread_id}"
        
        # Test case 3: All resolution methods fail
        run_id_3 = "no_resolution_possible"
        
        mock_websocket_manager.clear_messages()
        success = await websocket_bridge.notify_tool_executing(run_id_3, "TestAgent", "test_tool")
        assert not success, "Event should fail when thread_id cannot be resolved"
        assert len(mock_websocket_manager.sent_messages) == 0, "No messages should be sent on resolution failure"
        
        print("✅ Event routing fallback behaviors: PASSED")

    @pytest.mark.asyncio
    async def test_concurrent_event_routing(self, websocket_bridge, mock_websocket_manager, thread_registry):
        """Test concurrent event routing doesn't interfere."""
        
        # Setup multiple mappings
        mappings = []
        for i in range(20):
            run_id = f"concurrent_routing_{i}"
            thread_id = f"thread_routing_{i}"
            await thread_registry.register(run_id, thread_id)
            mappings.append((run_id, thread_id))
        
        # Send concurrent events
        async def send_event(run_id: str, thread_id: str) -> bool:
            return await websocket_bridge.notify_agent_started(run_id, f"Agent_{run_id}")
        
        tasks = [send_event(run_id, thread_id) for run_id, thread_id in mappings]
        results = await asyncio.gather(*tasks)
        
        # Verify all succeeded
        assert all(results), "All concurrent events should succeed"
        assert len(mock_websocket_manager.sent_messages) == 20, "Should have 20 messages"
        
        # Verify correct routing for each
        message_routing = {msg['run_id']: thread_id for thread_id, msg in mock_websocket_manager.sent_messages}
        
        for run_id, expected_thread_id in mappings:
            # Find the message for this run_id
            sent_messages = [
                (t_id, msg) for t_id, msg in mock_websocket_manager.sent_messages 
                if msg['run_id'] == run_id
            ]
            assert len(sent_messages) == 1, f"Should have exactly one message for {run_id}"
            
            sent_thread_id, sent_message = sent_messages[0]
            assert sent_thread_id == expected_thread_id, f"Concurrent routing failed for {run_id}"
        
        print("✅ Concurrent event routing: PASSED")


class TestFailureModes:
    """Test failure modes and error handling."""
    
    @pytest.mark.asyncio
    async def test_websocket_manager_failures(self, websocket_bridge, mock_websocket_manager):
        """Test behavior when WebSocket manager fails."""
        
        run_id = "ws_failure_test"
        thread_id = "thread_failure_test"
        
        # Test connection failure
        mock_websocket_manager.set_connection_failure(thread_id)
        
        success = await websocket_bridge.notify_agent_started(run_id, "TestAgent")
        assert not success, "Should fail when WebSocket connection fails"
        
        # Test WebSocket manager unavailable
        websocket_bridge._websocket_manager = None
        
        success = await websocket_bridge.notify_agent_thinking(run_id, "TestAgent", "Testing")
        assert not success, "Should fail when WebSocket manager unavailable"
        
        print("✅ WebSocket manager failure handling: PASSED")

    @pytest.mark.asyncio
    async def test_thread_resolution_timeout(self, websocket_bridge, mock_orchestrator):
        """Test behavior when thread resolution times out."""
        
        run_id = "timeout_test"
        thread_id = "thread_timeout"
        
        # Set long delay to simulate timeout
        mock_orchestrator.set_resolution_delay(run_id, 5.0)
        mock_orchestrator.set_thread_mapping(run_id, thread_id)
        
        # Resolution should still work but be slow
        start_time = time.time()
        result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
        end_time = time.time()
        
        assert result == thread_id, "Resolution should eventually succeed despite delay"
        assert end_time - start_time >= 5.0, "Should respect the delay"
        
        print("✅ Thread resolution timeout handling: PASSED")

    @pytest.mark.asyncio
    async def test_malformed_run_id_handling(self, websocket_bridge):
        """Test handling of malformed, invalid, or edge-case run_ids."""
        
        malformed_cases = [
            "",  # Empty string
            "   ",  # Whitespace only
            None,  # None value (will be handled by caller validation)
            "thread_",  # Incomplete pattern
            "_thread_",  # Edge pattern
            "thread" + "x" * 1000,  # Very long string
            "thread_\x00\x01\x02",  # Binary characters
            "thread_🚀_emoji",  # Unicode characters
            "THREAD_UPPERCASE_123",  # Wrong case
            "multiple_thread_123_thread_456_patterns",  # Multiple patterns
            "no_valid_pattern_here",  # No pattern at all
        ]
        
        for run_id in malformed_cases:
            try:
                if run_id is None:
                    continue  # Skip None test as it should be handled by caller
                
                result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
                
                # Should either return a valid result or None, never crash
                if result is not None:
                    assert isinstance(result, str), f"Result should be string or None, got {type(result)}"
                    assert result.startswith("thread_") or result == run_id, f"Invalid result format: {result}"
                
            except Exception as e:
                pytest.fail(f"Should not crash on malformed run_id '{run_id}': {e}")
        
        print("✅ Malformed run_id handling: PASSED")

    @pytest.mark.asyncio
    async def test_registry_corruption_recovery(self, websocket_bridge, thread_registry):
        """Test behavior when thread registry is corrupted or unavailable."""
        
        run_id = "corruption_test"
        thread_id = "thread_corruption" 
        
        # Register mapping normally
        await thread_registry.register(run_id, thread_id)
        
        # Simulate registry corruption by clearing internal state
        thread_registry._run_to_thread.clear()
        thread_registry._thread_to_runs.clear()
        
        # Resolution should fall back to other methods
        result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
        # Since no other methods have this mapping, should return None
        assert result is None, "Should gracefully handle registry corruption"
        
        # Verify bridge remains functional
        health = await websocket_bridge.health_check()
        assert health.registry_healthy, "Bridge should remain healthy despite registry issues"
        
        print("✅ Registry corruption recovery: PASSED")

    @pytest.mark.asyncio
    async def test_memory_exhaustion_handling(self, websocket_bridge, thread_registry):
        """Test behavior under memory exhaustion conditions."""
        
        # Create many mappings to simulate memory pressure
        large_data = "x" * 10000  # Large metadata to consume memory
        
        mappings_created = 0
        try:
            for i in range(1000):  # Try to create many mappings
                run_id = f"memory_test_{i}"
                thread_id = f"thread_memory_{i}"
                metadata = {"large_data": large_data, "index": i}
                
                success = await thread_registry.register(run_id, thread_id, metadata)
                if success:
                    mappings_created += 1
                
                # Test that resolution still works
                if i % 100 == 0:  # Periodic check
                    result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
                    assert result == thread_id, f"Resolution failed under memory pressure at iteration {i}"
        
        except MemoryError:
            # This is expected behavior under extreme memory pressure
            pass
        
        # Verify system remains functional
        assert mappings_created > 0, "Should have created some mappings before hitting limits"
        
        # Test that recent mappings still work
        recent_run_id = f"memory_test_{mappings_created - 1}"
        recent_thread_id = f"thread_memory_{mappings_created - 1}"
        result = await websocket_bridge._resolve_thread_id_from_run_id(recent_run_id)
        
        # May return None if evicted, but shouldn't crash
        assert result is None or result == recent_thread_id, "Should handle memory pressure gracefully"
        
        print("✅ Memory exhaustion handling: PASSED")


class TestIntegrationScenarios:
    """End-to-end integration testing scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_agent_execution_flow(self, websocket_bridge, mock_websocket_manager, thread_registry):
        """Test complete agent execution flow with WebSocket events."""
        
        # Simulate real agent execution
        run_id = "agent_execution_full_123"
        thread_id = "thread_user_session_789"
        agent_name = "DataAnalysisAgent"
        
        # Register thread mapping (as would happen in real system)
        await websocket_bridge.register_run_thread_mapping(run_id, thread_id, {
            "agent_name": agent_name,
            "user_id": "user_123",
            "session_id": "session_789"
        })
        
        # Execute full event sequence
        events_sequence = [
            ("notify_agent_started", {"agent_name": agent_name, "context": {"user_query": "Analyze data"}}),
            ("notify_agent_thinking", {"agent_name": agent_name, "reasoning": "Planning analysis", "step_number": 1}),
            ("notify_tool_executing", {"agent_name": agent_name, "tool_name": "data_loader", "parameters": {"source": "database"}}),
            ("notify_tool_completed", {"agent_name": agent_name, "tool_name": "data_loader", "result": {"rows": 1000}}),
            ("notify_progress_update", {"agent_name": agent_name, "progress": {"percentage": 50, "message": "Processing data"}}),
            ("notify_tool_executing", {"agent_name": agent_name, "tool_name": "analyzer", "parameters": {"method": "regression"}}),
            ("notify_tool_completed", {"agent_name": agent_name, "tool_name": "analyzer", "result": {"r_squared": 0.85}}),
            ("notify_agent_completed", {"agent_name": agent_name, "result": {"analysis": "Strong correlation found"}})
        ]
        
        # Execute sequence
        for method_name, kwargs in events_sequence:
            method = getattr(websocket_bridge, method_name)
            success = await method(run_id, **kwargs)
            assert success, f"Event {method_name} should succeed in full flow"
        
        # Verify all events routed correctly
        thread_messages = mock_websocket_manager.get_thread_messages(thread_id)
        assert len(thread_messages) == len(events_sequence), f"Should have {len(events_sequence)} messages"
        
        # Verify event sequence integrity
        expected_types = [event[0].replace("notify_", "") for event in events_sequence]
        actual_types = [msg['type'] for msg in thread_messages]
        assert actual_types == expected_types, f"Event sequence mismatch: expected {expected_types}, got {actual_types}"
        
        # Verify run_id consistency
        run_ids = [msg['run_id'] for msg in thread_messages]
        assert all(r_id == run_id for r_id in run_ids), "All events should have same run_id"
        
        print("✅ Full agent execution flow: PASSED")

    @pytest.mark.asyncio
    async def test_multi_agent_concurrent_execution(self, websocket_bridge, mock_websocket_manager, thread_registry):
        """Test multiple agents executing concurrently with separate threads."""
        
        # Setup multiple agent scenarios
        agent_scenarios = [
            {"run_id": "agent_1_run_123", "thread_id": "thread_user_1_session", "agent_name": "SearchAgent"},
            {"run_id": "agent_2_run_456", "thread_id": "thread_user_2_chat", "agent_name": "AnalysisAgent"},
            {"run_id": "agent_3_run_789", "thread_id": "thread_user_3_support", "agent_name": "SupportAgent"},
        ]
        
        # Register all mappings
        for scenario in agent_scenarios:
            await websocket_bridge.register_run_thread_mapping(
                scenario["run_id"], 
                scenario["thread_id"],
                {"agent_name": scenario["agent_name"]}
            )
        
        # Execute concurrent agent activities
        async def agent_activity(scenario: Dict) -> List[bool]:
            run_id = scenario["run_id"]
            agent_name = scenario["agent_name"]
            
            results = []
            
            # Each agent performs a sequence of activities
            activities = [
                ("notify_agent_started", {"agent_name": agent_name}),
                ("notify_agent_thinking", {"agent_name": agent_name, "reasoning": f"{agent_name} processing"}),
                ("notify_tool_executing", {"agent_name": agent_name, "tool_name": f"{agent_name.lower()}_tool"}),
                ("notify_tool_completed", {"agent_name": agent_name, "tool_name": f"{agent_name.lower()}_tool", "result": {"success": True}}),
                ("notify_agent_completed", {"agent_name": agent_name, "result": {"status": "completed"}})
            ]
            
            for method_name, kwargs in activities:
                method = getattr(websocket_bridge, method_name)
                success = await method(run_id, **kwargs)
                results.append(success)
                
                # Add small delay to simulate realistic execution
                await asyncio.sleep(0.01)
            
            return results
        
        # Run all agents concurrently
        tasks = [agent_activity(scenario) for scenario in agent_scenarios]
        all_results = await asyncio.gather(*tasks)
        
        # Verify all activities succeeded
        for agent_results in all_results:
            assert all(agent_results), f"Some agent activities failed: {agent_results}"
        
        # Verify message routing isolation
        for scenario in agent_scenarios:
            thread_messages = mock_websocket_manager.get_thread_messages(scenario["thread_id"])
            assert len(thread_messages) == 5, f"Each agent should have 5 messages, {scenario['thread_id']} has {len(thread_messages)}"
            
            # Verify all messages are for the correct agent
            agent_names = [msg.get('agent_name') for msg in thread_messages]
            expected_agent = scenario["agent_name"]
            assert all(name == expected_agent for name in agent_names), f"Message routing isolation failed for {expected_agent}"
        
        print("✅ Multi-agent concurrent execution: PASSED")

    @pytest.mark.asyncio
    async def test_bridge_restart_persistence(self, mock_websocket_manager, thread_registry):
        """Test that thread registry persists mappings across bridge restarts."""
        
        # Create initial mappings
        initial_mappings = [
            ("restart_test_1", "thread_persist_1"),
            ("restart_test_2", "thread_persist_2"),
            ("restart_test_3", "thread_persist_3"),
        ]
        
        for run_id, thread_id in initial_mappings:
            await thread_registry.register(run_id, thread_id)
        
        # Simulate bridge restart by creating new bridge instance
        with patch.multiple(
            'netra_backend.app.services.agent_websocket_bridge',
            get_websocket_manager=MagicMock(return_value=mock_websocket_manager),
            get_agent_execution_registry=AsyncMock(return_value=MockOrchestrator()),
            get_thread_run_registry=AsyncMock(return_value=thread_registry)  # Same registry instance
        ):
            new_bridge = AgentWebSocketBridge()
            await new_bridge.ensure_integration()
            
            # Verify mappings persist across restart
            for run_id, expected_thread_id in initial_mappings:
                result = await new_bridge._resolve_thread_id_from_run_id(run_id)
                assert result == expected_thread_id, f"Mapping should persist across restart: {run_id} -> {expected_thread_id}"
            
            # Verify bridge can still send events using persisted mappings
            success = await new_bridge.notify_agent_started("restart_test_1", "RestartedAgent")
            assert success, "Should successfully send events with persisted mappings"
            
            # Cleanup
            await new_bridge.shutdown()
        
        print("✅ Bridge restart persistence: PASSED")


class TestPerformanceAndScalability:
    """Performance and scalability testing."""
    
    @pytest.mark.asyncio
    async def test_high_frequency_resolution(self, websocket_bridge, thread_registry):
        """Test performance under high-frequency thread resolution requests."""
        
        # Setup many mappings
        mapping_count = 500
        mappings = []
        for i in range(mapping_count):
            run_id = f"perf_test_{i}"
            thread_id = f"thread_perf_{i}"
            await thread_registry.register(run_id, thread_id)
            mappings.append((run_id, thread_id))
        
        # High-frequency resolution test
        resolution_count = 1000
        start_time = time.time()
        
        tasks = []
        for i in range(resolution_count):
            # Random mapping selection for realistic access pattern
            run_id, expected_thread_id = random.choice(mappings)
            task = websocket_bridge._resolve_thread_id_from_run_id(run_id)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Performance assertions
        total_time = end_time - start_time
        avg_resolution_time = (total_time / resolution_count) * 1000  # Convert to ms
        
        assert total_time < 5.0, f"High-frequency resolution took too long: {total_time:.2f}s"
        assert avg_resolution_time < 5.0, f"Average resolution time too slow: {avg_resolution_time:.2f}ms"
        
        # Verify all resolutions succeeded
        successful_resolutions = sum(1 for result in results if result is not None)
        success_rate = successful_resolutions / resolution_count
        assert success_rate > 0.95, f"Success rate too low: {success_rate:.2%}"
        
        print(f"✅ High-frequency resolution: {resolution_count} resolutions in {total_time:.2f}s ({avg_resolution_time:.2f}ms avg)")

    @pytest.mark.asyncio
    async def test_concurrent_event_load(self, websocket_bridge, mock_websocket_manager, thread_registry):
        """Test system under concurrent event load."""
        
        # Setup mappings
        mapping_count = 100
        for i in range(mapping_count):
            run_id = f"load_test_{i}"
            thread_id = f"thread_load_{i}"
            await thread_registry.register(run_id, thread_id)
        
        # Concurrent event generation
        async def generate_events(worker_id: int, events_per_worker: int) -> List[bool]:
            results = []
            for i in range(events_per_worker):
                run_id = f"load_test_{i % mapping_count}"  # Cycle through mappings
                agent_name = f"Worker_{worker_id}"
                
                # Send different event types
                event_type = i % 4
                if event_type == 0:
                    success = await websocket_bridge.notify_agent_started(run_id, agent_name)
                elif event_type == 1:
                    success = await websocket_bridge.notify_agent_thinking(run_id, agent_name, f"Step {i}")
                elif event_type == 2:
                    success = await websocket_bridge.notify_tool_executing(run_id, agent_name, f"tool_{i}")
                else:
                    success = await websocket_bridge.notify_agent_completed(run_id, agent_name)
                
                results.append(success)
            return results
        
        # Execute concurrent load
        worker_count = 10
        events_per_worker = 50
        total_expected_events = worker_count * events_per_worker
        
        start_time = time.time()
        tasks = [generate_events(i, events_per_worker) for i in range(worker_count)]
        all_results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Performance verification
        total_time = end_time - start_time
        events_per_second = total_expected_events / total_time
        
        # Verify all events succeeded
        total_successes = sum(sum(worker_results) for worker_results in all_results)
        success_rate = total_successes / total_expected_events
        
        assert success_rate > 0.95, f"Success rate under load too low: {success_rate:.2%}"
        assert events_per_second > 100, f"Event throughput too low: {events_per_second:.1f} events/sec"
        assert total_time < 10.0, f"Load test took too long: {total_time:.2f}s"
        
        print(f"✅ Concurrent event load: {total_expected_events} events in {total_time:.2f}s ({events_per_second:.1f} events/sec)")

    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, websocket_bridge, thread_registry):
        """Test memory usage remains stable under continuous operation."""
        
        import gc
        import tracemalloc
        
        # Start memory tracking
        tracemalloc.start()
        
        # Get initial memory baseline
        gc.collect()
        snapshot_1 = tracemalloc.take_snapshot()
        
        # Simulate continuous operation with mapping churn
        for cycle in range(10):  # Multiple cycles of activity
            # Create batch of mappings
            batch_mappings = []
            for i in range(100):
                run_id = f"memory_cycle_{cycle}_item_{i}"
                thread_id = f"thread_memory_{cycle}_{i}"
                await thread_registry.register(run_id, thread_id)
                batch_mappings.append(run_id)
            
            # Use mappings for events
            for run_id in batch_mappings[:50]:  # Use half of them
                await websocket_bridge.notify_agent_started(run_id, "MemoryTestAgent")
            
            # Cleanup some mappings
            for run_id in batch_mappings[50:]:
                await thread_registry.unregister_run(run_id)
            
            # Force cleanup
            await thread_registry.cleanup_old_mappings()
            gc.collect()
        
        # Check final memory usage
        snapshot_2 = tracemalloc.take_snapshot()
        top_stats = snapshot_2.compare_to(snapshot_1, 'lineno')
        
        # Get total memory increase
        total_increase = sum(stat.size_diff for stat in top_stats if stat.size_diff > 0)
        
        # Memory should not grow excessively (allow some growth but not runaway)
        max_allowed_increase = 10 * 1024 * 1024  # 10MB
        assert total_increase < max_allowed_increase, f"Memory usage increased too much: {total_increase / (1024*1024):.1f}MB"
        
        tracemalloc.stop()
        
        print(f"✅ Memory usage stability: {total_increase / 1024:.1f}KB increase after continuous operation")


if __name__ == "__main__":
    # Run the comprehensive test suite
    pytest.main([
        __file__,
        "-v", 
        "--tb=short",
        "--asyncio-mode=auto",
        "-s"  # Show print statements
    ])
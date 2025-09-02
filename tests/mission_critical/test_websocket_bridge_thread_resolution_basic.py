from shared.isolated_environment import get_env
#!/usr/bin/env python
"""MISSION CRITICAL: Basic WebSocket Bridge Thread Resolution Tests

CRITICAL BUSINESS CONTEXT:
- Thread ID resolution is THE FOUNDATION of WebSocket event routing
- If this fails, 90% of chat functionality breaks - users see loading forever
- These tests protect the core value delivery mechanism of the platform

Basic test coverage to validate the system works correctly.
"""

import asyncio
import os
import sys
import uuid
import time
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set up isolated test environment
os.environ['WEBSOCKET_TEST_ISOLATED'] = 'true' 
os.environ['SKIP_REAL_SERVICES'] = 'true'
os.environ['TEST_COLLECTION_MODE'] = '1'

import pytest

# Import core components
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, IntegrationState
from netra_backend.app.services.thread_run_registry import ThreadRunRegistry, RegistryConfig


class MockWebSocketManager:
    """Simple mock WebSocket manager."""
    
    def __init__(self):
        self.sent_messages = []
        self.is_healthy = True
    
    async def send_to_thread(self, thread_id: str, message: dict) -> bool:
        if not self.is_healthy:
            return False
        self.sent_messages.append((thread_id, message))
        return True
    
    def clear_messages(self):
        self.sent_messages.clear()


class MockOrchestrator:
    """Simple mock orchestrator."""
    
    def __init__(self):
        self.thread_mappings = {}
        self.is_available = True
    
    async def get_thread_id_for_run(self, run_id: str):
        if not self.is_available:
            return None
        return self.thread_mappings.get(run_id)
    
    def set_thread_mapping(self, run_id: str, thread_id: str):
        self.thread_mappings[run_id] = thread_id
    
    async def set_websocket_manager(self, manager):
        pass
    
    async def get_metrics(self):
        return {"test": "metrics"}


@pytest.fixture
def mock_websocket_manager():
    return MockWebSocketManager()


@pytest.fixture
def mock_orchestrator():
    return MockOrchestrator()


@pytest.fixture
def thread_registry():
    config = RegistryConfig(
        mapping_ttl_hours=1,
        cleanup_interval_minutes=60,
        enable_debug_logging=False
    )
    registry = ThreadRunRegistry(config)
    # Cancel cleanup task to avoid async issues in tests
    if hasattr(registry, '_cleanup_task') and registry._cleanup_task:
        registry._cleanup_task.cancel()
        registry._cleanup_task = None
    return registry


@pytest.fixture
def websocket_bridge(mock_websocket_manager, mock_orchestrator, thread_registry):
    """WebSocket bridge with mocked dependencies."""
    bridge = AgentWebSocketBridge()
    
    # Manually inject dependencies
    bridge._websocket_manager = mock_websocket_manager
    bridge._orchestrator = mock_orchestrator
    bridge._thread_registry = thread_registry
    bridge.state = IntegrationState.ACTIVE
    
    return bridge


class TestBasicThreadResolution:
    """Basic thread ID resolution tests."""
    
    @pytest.mark.asyncio
    async def test_direct_thread_id_patterns(self, websocket_bridge):
        """Test extraction when run_id IS a thread_id."""
        
        test_cases = [
            ("thread_12345", "thread_12345"),
            ("thread_abc123", "thread_abc123"),
            ("thread_user_session_789", "thread_user_session_789"),
        ]
        
        for run_id, expected in test_cases:
            result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
            assert result == expected, f"Expected '{expected}' for run_id '{run_id}', got '{result}'"
    
    @pytest.mark.asyncio
    async def test_embedded_thread_id_patterns(self, websocket_bridge):
        """Test extraction when thread_id is embedded in run_id."""
        
        test_cases = [
            ("run_thread_12345", "thread_12345"),
            ("user_123_thread_456_session", "thread_456"),
            ("agent_execution_thread_789_v1", "thread_789"),
        ]
        
        for run_id, expected in test_cases:
            result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
            assert result == expected, f"Expected '{expected}' for run_id '{run_id}', got '{result}'"
    
    @pytest.mark.asyncio
    async def test_registry_resolution(self, websocket_bridge, thread_registry):
        """Test resolution via thread registry."""
        
        run_id = "registry_test_123"
        thread_id = "thread_registry_456"
        
        # Register mapping
        success = await thread_registry.register(run_id, thread_id)
        assert success, "Registry registration should succeed"
        
        # Resolve
        result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
        assert result == thread_id, f"Expected registry resolution to return '{thread_id}', got '{result}'"
    
    @pytest.mark.asyncio
    async def test_orchestrator_fallback(self, websocket_bridge, mock_orchestrator):
        """Test fallback to orchestrator when registry fails."""
        
        run_id = "orchestrator_test_123"
        thread_id = "thread_orchestrator_456"
        
        # Clear registry to force orchestrator fallback
        websocket_bridge._thread_registry = None
        
        # Set orchestrator mapping
        mock_orchestrator.set_thread_mapping(run_id, thread_id)
        
        result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
        assert result == thread_id, f"Expected orchestrator resolution to return '{thread_id}', got '{result}'"
    
    @pytest.mark.asyncio
    async def test_pattern_fallback(self, websocket_bridge):
        """Test fallback to pattern extraction."""
        
        # Clear both registry and orchestrator
        websocket_bridge._thread_registry = None
        websocket_bridge._orchestrator = None
        
        run_id = "pattern_thread_123"
        expected = "thread_123"
        
        result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
        assert result == expected, f"Expected pattern fallback to return '{expected}', got '{result}'"
    
    @pytest.mark.asyncio
    async def test_resolution_failure(self, websocket_bridge):
        """Test behavior when no resolution method works."""
        
        # Clear all resolution methods
        websocket_bridge._thread_registry = None
        websocket_bridge._orchestrator = None
        
        run_id = "no_pattern_here"
        
        result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
        assert result is None, "Should return None when no resolution method works"


class TestBasicEventRouting:
    """Basic event routing tests."""
    
    @pytest.mark.asyncio
    async def test_successful_event_routing(self, websocket_bridge, mock_websocket_manager, thread_registry):
        """Test that events route correctly to the right thread."""
        
        run_id = "event_test_123"
        thread_id = "thread_event_456"
        
        # Register mapping
        await thread_registry.register(run_id, thread_id)
        
        # Send event
        success = await websocket_bridge.notify_agent_started(run_id, "TestAgent")
        assert success, "Event should be sent successfully"
        
        # Verify routing
        assert len(mock_websocket_manager.sent_messages) == 1, "Should have sent one message"
        sent_thread_id, sent_message = mock_websocket_manager.sent_messages[0]
        assert sent_thread_id == thread_id, f"Should route to correct thread: expected {thread_id}, got {sent_thread_id}"
        assert sent_message['run_id'] == run_id, "Message should have correct run_id"
    
    @pytest.mark.asyncio
    async def test_event_routing_failure(self, websocket_bridge, mock_websocket_manager):
        """Test event routing failure when thread_id cannot be resolved."""
        
        run_id = "unresolvable_run_id"
        
        # Clear all resolution methods
        websocket_bridge._thread_registry = None
        websocket_bridge._orchestrator = None
        
        # Send event
        success = await websocket_bridge.notify_agent_started(run_id, "TestAgent")
        assert not success, "Event should fail when thread_id cannot be resolved"
        assert len(mock_websocket_manager.sent_messages) == 0, "No messages should be sent"
    
    @pytest.mark.asyncio
    async def test_websocket_manager_failure(self, websocket_bridge, mock_websocket_manager, thread_registry):
        """Test behavior when WebSocket manager fails."""
        
        run_id = "ws_failure_test"
        thread_id = "thread_failure"
        
        # Register mapping
        await thread_registry.register(run_id, thread_id)
        
        # Make WebSocket manager fail
        mock_websocket_manager.is_healthy = False
        
        # Send event
        success = await websocket_bridge.notify_agent_started(run_id, "TestAgent")
        assert not success, "Event should fail when WebSocket manager is unhealthy"


class TestRegistryOperations:
    """Basic registry operations tests."""
    
    @pytest.mark.asyncio
    async def test_registry_lifecycle(self, thread_registry):
        """Test basic registry operations: register, lookup, unregister."""
        
        run_id = "lifecycle_test"
        thread_id = "thread_lifecycle"
        
        # Register
        success = await thread_registry.register(run_id, thread_id)
        assert success, "Registration should succeed"
        
        # Lookup
        result = await thread_registry.get_thread(run_id)
        assert result == thread_id, f"Lookup should return '{thread_id}', got '{result}'"
        
        # Unregister
        success = await thread_registry.unregister_run(run_id)
        assert success, "Unregistration should succeed"
        
        # Verify removal
        result = await thread_registry.get_thread(run_id)
        assert result is None, "Lookup should return None after unregistration"
    
    @pytest.mark.asyncio
    async def test_concurrent_registry_operations(self, thread_registry):
        """Test concurrent registry operations."""
        
        async def register_and_lookup(index: int) -> bool:
            run_id = f"concurrent_test_{index}"
            thread_id = f"thread_concurrent_{index}"
            
            # Register
            reg_success = await thread_registry.register(run_id, thread_id)
            if not reg_success:
                return False
            
            # Lookup
            result = await thread_registry.get_thread(run_id)
            return result == thread_id
        
        # Run concurrent operations
        tasks = [register_and_lookup(i) for i in range(20)]
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(results), "All concurrent operations should succeed"


class TestErrorHandling:
    """Basic error handling tests."""
    
    @pytest.mark.asyncio
    async def test_malformed_run_ids(self, websocket_bridge):
        """Test handling of malformed run_ids."""
        
        malformed_cases = [
            "",  # Empty string
            "   ",  # Whitespace
            "thread_",  # Incomplete pattern
            "no_pattern_here",  # No pattern
        ]
        
        for run_id in malformed_cases:
            try:
                result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
                # Should either return None or a valid string, never crash
                if result is not None:
                    assert isinstance(result, str), f"Result should be string or None, got {type(result)}"
            except Exception as e:
                pytest.fail(f"Should not crash on malformed run_id '{run_id}': {e}")
    
    @pytest.mark.asyncio
    async def test_performance_basic(self, websocket_bridge, thread_registry):
        """Basic performance test for resolution."""
        
        # Setup mappings
        mappings = []
        for i in range(100):
            run_id = f"perf_test_{i}"
            thread_id = f"thread_perf_{i}"
            await thread_registry.register(run_id, thread_id)
            mappings.append((run_id, thread_id))
        
        # Test resolution performance
        start_time = time.time()
        
        for run_id, expected_thread_id in mappings:
            result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
            assert result == expected_thread_id, f"Resolution failed for {run_id}"
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should be fast
        assert total_time < 2.0, f"Resolution took too long: {total_time:.2f}s for {len(mappings)} operations"
        
        avg_time = (total_time / len(mappings)) * 1000  # ms
        print(f"Average resolution time: {avg_time:.2f}ms per operation")


if __name__ == "__main__":
    # Run the basic test suite
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ])

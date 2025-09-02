from shared.isolated_environment import get_env
#!/usr/bin/env python
"""
MISSION CRITICAL: Comprehensive WebSocket Bridge Critical Flows Test Suite

CRITICAL BUSINESS CONTEXT:
This test suite validates the most critical flows of the WebSocket bridge system that directly 
impact the core business value - delivering AI chat experiences to users. These tests ensure:

1. 90% of platform value depends on WebSocket events reaching users correctly
2. Thread ID resolution must work under all scenarios to route events properly
3. Run ID generation must follow SSOT to prevent silent failures
4. Registry operations must be thread-safe and performant under load
5. Orchestrator failures must not break user experiences
6. System recovery must be automatic and transparent

COVERAGE FOCUS:
- Run ID SSOT compliance and thread extraction accuracy
- Thread registry persistence, TTL, and cleanup operations  
- Priority chain resolution: Registry → Orchestrator → Pattern → Fail
- End-to-end WebSocket event delivery validation
- Orchestrator initialization and fallback mechanisms
- Concurrent multi-agent operations and performance
- Error scenarios, recovery paths, and system resilience
- Business metrics validation and performance tracking

These tests are designed to catch critical regressions before they impact users.
"""

import asyncio
import json
import os
import sys
import time
import uuid
import threading
import random
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple, Any
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from contextlib import asynccontextmanager
import pytest

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set up isolated test environment
os.environ['WEBSOCKET_TEST_ISOLATED'] = 'true'
os.environ['SKIP_REAL_SERVICES'] = 'true'
os.environ['TEST_COLLECTION_MODE'] = '1'

# Import critical components
try:
    from netra_backend.app.utils.run_id_generator import (
        generate_run_id,
        extract_thread_id_from_run_id,
        validate_run_id_format,
        is_legacy_run_id,
        migrate_legacy_run_id_to_standard,
        RUN_ID_PREFIX,
        RUN_ID_SEPARATOR
    )
    from netra_backend.app.services.thread_run_registry import (
        ThreadRunRegistry,
        RegistryConfig,
        RunMapping,
        MappingState,
        get_thread_run_registry,
        initialize_thread_run_registry
    )
    from netra_backend.app.services.agent_websocket_bridge import (
        AgentWebSocketBridge,
        IntegrationState
    )
except ImportError as e:
    pytest.skip(f"Could not import required WebSocket bridge modules: {e}", allow_module_level=True)


class MockWebSocketManager:
    """Enhanced WebSocket manager mock with comprehensive failure scenarios."""
    
    def __init__(self):
        self.sent_messages: List[Tuple[str, Dict]] = []
        self.thread_connections: Dict[str, bool] = {}
        self.delivery_delays: Dict[str, float] = {}
        self.failure_modes: Dict[str, str] = {}  # thread_id -> failure_type
        self.message_history: Dict[str, List[Dict]] = {}
        self.call_metrics = {
            'total_calls': 0,
            'successful_sends': 0,
            'failed_sends': 0,
            'avg_response_time': 0.0
        }
        self.is_healthy = True
        self.network_partitioned = False
    
    async def send_to_thread(self, thread_id: str, message: Dict) -> bool:
        """Mock WebSocket send with realistic failure scenarios."""
        start_time = time.time()
        self.call_metrics['total_calls'] += 1
        
        try:
            # Simulate network partition
            if self.network_partitioned:
                return False
            
            # Check connection health
            if not self.is_healthy:
                self.call_metrics['failed_sends'] += 1
                return False
            
            # Simulate specific failure modes
            failure_mode = self.failure_modes.get(thread_id)
            if failure_mode:
                if failure_mode == 'timeout':
                    await asyncio.sleep(10)  # Simulate timeout
                    return False
                elif failure_mode == 'connection_closed':
                    return False
                elif failure_mode == 'rate_limited':
                    await asyncio.sleep(0.5)
                    return False
            
            # Simulate delivery delay
            delay = self.delivery_delays.get(thread_id, 0)
            if delay > 0:
                await asyncio.sleep(delay)
            
            # Check if thread has active connection
            if thread_id in self.thread_connections and not self.thread_connections[thread_id]:
                self.call_metrics['failed_sends'] += 1
                return False
            
            # Record successful message
            self.sent_messages.append((thread_id, message.copy()))
            
            # Track per-thread message history
            if thread_id not in self.message_history:
                self.message_history[thread_id] = []
            self.message_history[thread_id].append(message.copy())
            
            # Update metrics
            response_time = time.time() - start_time
            self.call_metrics['successful_sends'] += 1
            self._update_avg_response_time(response_time)
            
            return True
            
        except Exception as e:
            self.call_metrics['failed_sends'] += 1
            return False
    
    def _update_avg_response_time(self, response_time: float):
        """Update rolling average response time."""
        current_avg = self.call_metrics['avg_response_time']
        total_successful = self.call_metrics['successful_sends']
        
        if total_successful == 1:
            self.call_metrics['avg_response_time'] = response_time
        else:
            # Rolling average
            self.call_metrics['avg_response_time'] = (
                (current_avg * (total_successful - 1) + response_time) / total_successful
            )
    
    def set_connection_status(self, thread_id: str, connected: bool):
        """Set connection status for thread."""
        self.thread_connections[thread_id] = connected
    
    def set_failure_mode(self, thread_id: str, failure_mode: str):
        """Set failure mode for specific thread."""
        self.failure_modes[thread_id] = failure_mode
    
    def set_delivery_delay(self, thread_id: str, delay: float):
        """Set artificial delay for thread."""
        self.delivery_delays[thread_id] = delay
    
    def partition_network(self):
        """Simulate network partition."""
        self.network_partitioned = True
    
    def restore_network(self):
        """Restore network connectivity."""
        self.network_partitioned = False
    
    def get_thread_message_count(self, thread_id: str) -> int:
        """Get message count for specific thread."""
        return len(self.message_history.get(thread_id, []))
    
    def get_thread_messages(self, thread_id: str) -> List[Dict]:
        """Get all messages for specific thread."""
        return self.message_history.get(thread_id, []).copy()
    
    def clear_all_messages(self):
        """Clear all message history."""
        self.sent_messages.clear()
        self.message_history.clear()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get WebSocket manager metrics."""
        total_calls = self.call_metrics['total_calls']
        success_rate = (
            self.call_metrics['successful_sends'] / max(1, total_calls)
        )
        
        return {
            'total_calls': total_calls,
            'successful_sends': self.call_metrics['successful_sends'],
            'failed_sends': self.call_metrics['failed_sends'],
            'success_rate': success_rate,
            'avg_response_time_ms': self.call_metrics['avg_response_time'] * 1000,
            'active_connections': len([
                tid for tid, connected in self.thread_connections.items() 
                if connected
            ]),
            'is_healthy': self.is_healthy,
            'network_partitioned': self.network_partitioned
        }


class MockOrchestrator:
    """Enhanced orchestrator mock with comprehensive scenarios."""
    
    def __init__(self):
        self.thread_mappings: Dict[str, str] = {}
        self.resolution_delays: Dict[str, float] = {}
        self.resolution_failures: Set[str] = set()
        self.call_metrics = {
            'resolution_calls': 0,
            'successful_resolutions': 0,
            'failed_resolutions': 0,
            'avg_resolution_time': 0.0
        }
        self.is_available = True
        self.initialization_complete = True
        self.health_status = 'healthy'
    
    async def get_thread_id_for_run(self, run_id: str) -> Optional[str]:
        """Mock thread resolution with comprehensive failure modes."""
        start_time = time.time()
        self.call_metrics['resolution_calls'] += 1
        
        try:
            # Check if orchestrator is available
            if not self.is_available:
                self.call_metrics['failed_resolutions'] += 1
                raise Exception("Orchestrator unavailable")
            
            # Check initialization
            if not self.initialization_complete:
                self.call_metrics['failed_resolutions'] += 1
                return None
            
            # Simulate resolution failure
            if run_id in self.resolution_failures:
                self.call_metrics['failed_resolutions'] += 1
                return None
            
            # Simulate resolution delay
            delay = self.resolution_delays.get(run_id, 0)
            if delay > 0:
                await asyncio.sleep(delay)
            
            # Get mapping
            thread_id = self.thread_mappings.get(run_id)
            
            # Update metrics
            resolution_time = time.time() - start_time
            if thread_id:
                self.call_metrics['successful_resolutions'] += 1
            else:
                self.call_metrics['failed_resolutions'] += 1
            
            self._update_avg_resolution_time(resolution_time)
            
            return thread_id
            
        except Exception as e:
            self.call_metrics['failed_resolutions'] += 1
            return None
    
    def _update_avg_resolution_time(self, resolution_time: float):
        """Update rolling average resolution time."""
        current_avg = self.call_metrics['avg_resolution_time']
        total_calls = self.call_metrics['resolution_calls']
        
        if total_calls == 1:
            self.call_metrics['avg_resolution_time'] = resolution_time
        else:
            self.call_metrics['avg_resolution_time'] = (
                (current_avg * (total_calls - 1) + resolution_time) / total_calls
            )
    
    def set_thread_mapping(self, run_id: str, thread_id: str):
        """Set thread mapping."""
        self.thread_mappings[run_id] = thread_id
    
    def set_resolution_delay(self, run_id: str, delay: float):
        """Set resolution delay."""
        self.resolution_delays[run_id] = delay
    
    def set_resolution_failure(self, run_id: str):
        """Mark run_id as resolution failure."""
        self.resolution_failures.add(run_id)
    
    def set_availability(self, available: bool):
        """Set orchestrator availability."""
        self.is_available = available
    
    def set_initialization_status(self, complete: bool):
        """Set initialization status."""
        self.initialization_complete = complete
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get orchestrator metrics."""
        total_calls = self.call_metrics['resolution_calls']
        success_rate = (
            self.call_metrics['successful_resolutions'] / max(1, total_calls)
        )
        
        return {
            'resolution_calls': total_calls,
            'successful_resolutions': self.call_metrics['successful_resolutions'],
            'failed_resolutions': self.call_metrics['failed_resolutions'],
            'success_rate': success_rate,
            'avg_resolution_time_ms': self.call_metrics['avg_resolution_time'] * 1000,
            'is_available': self.is_available,
            'initialization_complete': self.initialization_complete,
            'health_status': self.health_status
        }
    
    async def set_websocket_manager(self, manager):
        """Mock method for integration."""
        pass


@pytest.fixture
def mock_websocket_manager():
    """WebSocket manager fixture."""
    return MockWebSocketManager()


@pytest.fixture
def mock_orchestrator():
    """Orchestrator fixture."""
    return MockOrchestrator()


@pytest.fixture
def test_registry():
    """Test registry with short TTL for testing."""
    config = RegistryConfig(
        mapping_ttl_hours=0.1,  # 6 minutes for testing
        cleanup_interval_minutes=1,  # Fast cleanup for testing
        enable_debug_logging=False,  # Reduce noise in tests
        max_mappings=1000
    )
    return ThreadRunRegistry(config)


@pytest.fixture
def websocket_bridge(mock_websocket_manager, mock_orchestrator, test_registry):
    """WebSocket bridge with mocked dependencies."""
    bridge = AgentWebSocketBridge()
    
    # Set mocked dependencies
    bridge._websocket_manager = mock_websocket_manager  
    bridge._orchestrator = mock_orchestrator
    bridge._thread_registry = test_registry
    bridge.state = IntegrationState.ACTIVE
    
    return bridge


class TestRunIdSSotCompliance:
    """Test SSOT compliance for run ID generation and thread extraction."""
    
    @pytest.mark.asyncio
    async def test_run_id_always_includes_thread(self):
        """CRITICAL: Verify all generated run IDs include thread information."""
        
        test_thread_ids = [
            "user_session_123",
            "chat_conversation_456", 
            "admin_tool_789",
            "background_task_abc",
            "websocket_connection_def",
            "thread_complex_nested_ghi",
            "a",  # Minimal thread ID
            "x" * 200,  # Maximum length thread ID
        ]
        
        for thread_id in test_thread_ids:
            # Generate run ID
            run_id = generate_run_id(thread_id, "ssot_test")
            
            # Verify format compliance
            assert run_id.startswith(RUN_ID_PREFIX), f"Run ID missing prefix: {run_id}"
            assert RUN_ID_SEPARATOR in run_id, f"Run ID missing separator: {run_id}"
            
            # Verify thread extraction works
            extracted_thread = extract_thread_id_from_run_id(run_id)
            assert extracted_thread == thread_id, f"Thread extraction failed: expected '{thread_id}', got '{extracted_thread}'"
            
            # Verify validation passes
            assert validate_run_id_format(run_id, thread_id), f"Validation failed for run_id: {run_id}"
            
            # Verify not legacy format
            assert not is_legacy_run_id(run_id), f"Generated run_id marked as legacy: {run_id}"
        
        print("✅ Run ID always includes thread: PASSED")
    
    @pytest.mark.asyncio
    async def test_thread_resolution_priority_chain(self, websocket_bridge, test_registry, mock_orchestrator):
        """CRITICAL: Test priority chain Resolution: Registry → Orchestrator → Pattern → None."""
        
        # Test case setup
        run_id = "priority_test_run_123" 
        registry_thread = "thread_from_registry"
        orchestrator_thread = "thread_from_orchestrator"
        pattern_thread = "thread_from_pattern_456"  # Matches pattern in run_id
        
        # Case 1: Registry has mapping (highest priority)
        await test_registry.register(run_id, registry_thread)
        mock_orchestrator.set_thread_mapping(run_id, orchestrator_thread)
        
        result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
        assert result == registry_thread, f"Registry priority failed: expected '{registry_thread}', got '{result}'"
        
        # Case 2: Clear registry, orchestrator should be used
        await test_registry.unregister_run(run_id)
        
        result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
        assert result == orchestrator_thread, f"Orchestrator fallback failed: expected '{orchestrator_thread}', got '{result}'"
        
        # Case 3: Clear orchestrator, pattern should be used  
        mock_orchestrator.thread_mappings.clear()
        run_id_with_pattern = "fallback_thread_pattern_extraction_789"
        
        result = await websocket_bridge._resolve_thread_id_from_run_id(run_id_with_pattern)
        assert result == "thread_pattern", f"Pattern fallback failed: expected 'thread_pattern', got '{result}'"
        
        # Case 4: No resolution possible
        impossible_run_id = "no_resolution_possible_anywhere"
        
        result = await websocket_bridge._resolve_thread_id_from_run_id(impossible_run_id)
        assert result is None, f"Should return None when no resolution possible, got '{result}'"
        
        print("✅ Thread resolution priority chain: PASSED")
    
    @pytest.mark.asyncio  
    async def test_registry_backup_when_orchestrator_fails(self, websocket_bridge, test_registry, mock_orchestrator):
        """CRITICAL: Test registry backup when orchestrator is unavailable."""
        
        run_id = "orchestrator_failure_test"
        backup_thread = "thread_backup_registry"
        
        # Register in backup registry
        await test_registry.register(run_id, backup_thread)
        
        # Simulate orchestrator failure
        mock_orchestrator.set_availability(False)
        
        # Resolution should still work via registry
        result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
        assert result == backup_thread, f"Registry backup failed: expected '{backup_thread}', got '{result}'"
        
        # Verify orchestrator was attempted (metrics should show failure)
        orchestrator_metrics = await mock_orchestrator.get_metrics()
        assert orchestrator_metrics['failed_resolutions'] > 0, "Should attempt orchestrator resolution"
        
        print("✅ Registry backup when orchestrator fails: PASSED")
    
    @pytest.mark.asyncio
    async def test_simple_run_id_failure_detection(self, websocket_bridge):
        """CRITICAL: Detect and handle legacy/invalid run IDs that break thread resolution."""
        
        # Legacy run ID formats that should fail gracefully
        legacy_run_ids = [
            "run_12345",  # Old format without thread
            "admin_tool_timestamp_67890",  # Admin format without thread
            "batch_process_abc123",  # Batch format without thread
            "user_session_456",  # User format without thread marker
            "",  # Empty string
            "thread_",  # Incomplete thread format
            "_run_",  # Separator only
            "malformed_format",  # No recognizable pattern
        ]
        
        for legacy_run_id in legacy_run_ids:
            if not legacy_run_id:  # Skip empty string
                continue
                
            # Verify it's detected as legacy/invalid
            if legacy_run_id not in ["", "thread_", "_run_"]:
                assert is_legacy_run_id(legacy_run_id), f"Should detect '{legacy_run_id}' as legacy"
            
            # Thread resolution should handle gracefully (return None, not crash)
            result = await websocket_bridge._resolve_thread_id_from_run_id(legacy_run_id)
            assert result is None or isinstance(result, str), f"Should handle '{legacy_run_id}' gracefully"
            
            # Extraction should return None for invalid formats
            extracted = extract_thread_id_from_run_id(legacy_run_id) 
            if legacy_run_id.startswith("thread_") and "_run_" in legacy_run_id:
                # Valid format should extract
                assert isinstance(extracted, str) or extracted is None
            else:
                # Invalid format should return None
                assert extracted is None, f"Should return None for invalid format '{legacy_run_id}'"
        
        print("✅ Simple run ID failure detection: PASSED")


class TestThreadRegistryOperations:
    """Test thread registry operations including TTL and cleanup."""
    
    @pytest.mark.asyncio
    async def test_registry_performance_under_load(self, test_registry):
        """CRITICAL: Test registry performance with 1000+ mappings."""
        
        # Create large number of mappings
        mapping_count = 1500
        mappings = []
        
        start_time = time.time()
        
        # Register mappings
        for i in range(mapping_count):
            run_id = f"load_test_{i}"
            thread_id = f"thread_load_{i}"
            metadata = {"index": i, "batch": "performance_test"}
            
            success = await test_registry.register(run_id, thread_id, metadata)
            assert success, f"Registration {i} should succeed"
            mappings.append((run_id, thread_id))
        
        registration_time = time.time() - start_time
        
        # Test lookup performance
        lookup_start = time.time()
        lookup_tasks = []
        
        # Random lookup pattern (realistic access)
        for _ in range(500):
            run_id, expected_thread = random.choice(mappings)
            lookup_tasks.append(test_registry.get_thread(run_id))
        
        lookup_results = await asyncio.gather(*lookup_tasks)
        lookup_time = time.time() - lookup_start
        
        # Verify all lookups succeeded  
        successful_lookups = sum(1 for result in lookup_results if result is not None)
        lookup_success_rate = successful_lookups / len(lookup_results)
        
        # Performance assertions
        assert registration_time < 5.0, f"Registration took too long: {registration_time:.2f}s"
        assert lookup_time < 2.0, f"Lookup took too long: {lookup_time:.2f}s"
        assert lookup_success_rate > 0.95, f"Lookup success rate too low: {lookup_success_rate:.2%}"
        
        # Verify registry health under load
        metrics = await test_registry.get_metrics()
        assert metrics['registry_healthy'], "Registry should remain healthy under load"
        assert metrics['active_mappings'] >= mapping_count * 0.9, "Most mappings should still be active"
        
        print(f"✅ Registry performance under load: {mapping_count} mappings registered in {registration_time:.2f}s, {len(lookup_results)} lookups in {lookup_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_registry_ttl_and_cleanup(self, test_registry):
        """CRITICAL: Test TTL expiration and automatic cleanup."""
        
        # Override TTL for fast testing
        original_ttl = test_registry.config.mapping_ttl_hours
        test_registry.config.mapping_ttl_hours = 0.001  # ~3.6 seconds
        
        try:
            # Register test mappings
            test_mappings = [
                ("ttl_test_1", "thread_ttl_1"),
                ("ttl_test_2", "thread_ttl_2"), 
                ("ttl_test_3", "thread_ttl_3"),
            ]
            
            for run_id, thread_id in test_mappings:
                await test_registry.register(run_id, thread_id)
            
            # Verify immediate lookup works
            for run_id, thread_id in test_mappings:
                result = await test_registry.get_thread(run_id)
                assert result == thread_id, f"Immediate lookup should work for {run_id}"
            
            # Wait for TTL expiration
            await asyncio.sleep(5.0)
            
            # Verify lookups fail after expiration  
            for run_id, thread_id in test_mappings:
                result = await test_registry.get_thread(run_id)
                assert result is None, f"Lookup should fail after TTL for {run_id}"
            
            # Force cleanup and verify metrics
            cleaned = await test_registry.cleanup_old_mappings()
            assert cleaned >= len(test_mappings), f"Should clean at least {len(test_mappings)} mappings"
            
            metrics = await test_registry.get_metrics()
            assert metrics['expired_mappings_cleaned'] >= len(test_mappings), "Cleanup metrics should reflect removed mappings"
            
        finally:
            # Restore original TTL
            test_registry.config.mapping_ttl_hours = original_ttl
        
        print("✅ Registry TTL and cleanup: PASSED")
    
    @pytest.mark.asyncio
    async def test_registry_concurrent_access(self, test_registry):
        """CRITICAL: Test thread-safe concurrent registry operations."""
        
        async def concurrent_worker(worker_id: int, operations: int) -> Dict[str, int]:
            stats = {'registered': 0, 'lookups': 0, 'unregistered': 0}
            
            for i in range(operations):
                run_id = f"worker_{worker_id}_op_{i}"
                thread_id = f"thread_worker_{worker_id}_{i}"
                
                # Register
                success = await test_registry.register(run_id, thread_id)
                if success:
                    stats['registered'] += 1
                
                # Immediate lookup
                result = await test_registry.get_thread(run_id)
                if result == thread_id:
                    stats['lookups'] += 1
                
                # Unregister every other mapping
                if i % 2 == 0:
                    success = await test_registry.unregister_run(run_id)
                    if success:
                        stats['unregistered'] += 1
            
            return stats
        
        # Run concurrent workers
        worker_count = 10
        operations_per_worker = 50
        
        tasks = [
            concurrent_worker(worker_id, operations_per_worker)
            for worker_id in range(worker_count)
        ]
        
        worker_stats = await asyncio.gather(*tasks)
        
        # Aggregate stats
        total_stats = {'registered': 0, 'lookups': 0, 'unregistered': 0}
        for stats in worker_stats:
            for key, value in stats.items():
                total_stats[key] += value
        
        # Verify concurrent operations succeeded
        expected_operations = worker_count * operations_per_worker
        assert total_stats['registered'] >= expected_operations * 0.95, "Most registrations should succeed"
        assert total_stats['lookups'] >= expected_operations * 0.95, "Most lookups should succeed"
        
        # Verify registry integrity
        metrics = await test_registry.get_metrics()
        assert metrics['registry_healthy'], "Registry should remain healthy after concurrent access"
        
        print(f"✅ Registry concurrent access: {total_stats['registered']} registrations, {total_stats['lookups']} lookups across {worker_count} workers")


class TestWebSocketEventDelivery:
    """Test end-to-end WebSocket event delivery."""
    
    @pytest.mark.asyncio
    async def test_websocket_events_reach_users(self, websocket_bridge, mock_websocket_manager, test_registry):
        """CRITICAL: Verify WebSocket events actually reach users end-to-end."""
        
        # Setup user scenarios
        user_scenarios = [
            {
                "user_id": "user_123",
                "session_id": "session_abc",
                "thread_id": "thread_user_123_session_abc",
                "run_id": generate_run_id("user_123_session_abc", "user_test"),
                "agent_name": "ChatAgent"
            },
            {
                "user_id": "user_456", 
                "session_id": "session_def",
                "thread_id": "thread_user_456_session_def",
                "run_id": generate_run_id("user_456_session_def", "user_test"),
                "agent_name": "AnalysisAgent"
            },
            {
                "user_id": "user_789",
                "session_id": "session_ghi", 
                "thread_id": "thread_user_789_session_ghi",
                "run_id": generate_run_id("user_789_session_ghi", "user_test"),
                "agent_name": "SupportAgent"
            }
        ]
        
        # Register all thread mappings
        for scenario in user_scenarios:
            await test_registry.register(
                scenario["run_id"],
                scenario["thread_id"],
                {"user_id": scenario["user_id"], "session_id": scenario["session_id"]}
            )
            
            # Mark connections as active
            mock_websocket_manager.set_connection_status(scenario["thread_id"], True)
        
        # Test full event sequence for each user
        event_types = [
            ("notify_agent_started", {"context": {"user_query": "Test query"}}),
            ("notify_agent_thinking", {"reasoning": "Processing request", "step_number": 1}),
            ("notify_tool_executing", {"tool_name": "test_tool", "parameters": {"param": "value"}}),
            ("notify_tool_completed", {"tool_name": "test_tool", "result": {"success": True}}),
            ("notify_progress_update", {"progress": {"percentage": 75, "message": "Nearly done"}}),
            ("notify_agent_completed", {"result": {"status": "success", "data": "response"}})
        ]
        
        # Send events for all users
        for scenario in user_scenarios:
            for event_method, event_kwargs in event_types:
                method = getattr(websocket_bridge, event_method)
                success = await method(
                    scenario["run_id"],
                    scenario["agent_name"],
                    **event_kwargs
                )
                assert success, f"Event {event_method} should succeed for {scenario['user_id']}"
        
        # Verify event delivery per user
        for scenario in user_scenarios:
            thread_messages = mock_websocket_manager.get_thread_messages(scenario["thread_id"])
            
            # Should have all event types
            assert len(thread_messages) == len(event_types), f"User {scenario['user_id']} should receive all events"
            
            # Verify message routing integrity
            for message in thread_messages:
                assert message['run_id'] == scenario['run_id'], "Message should have correct run_id"
                assert message['agent_name'] == scenario['agent_name'], "Message should have correct agent_name"
            
            # Verify event sequence order
            expected_event_types = [event[0].replace("notify_", "") for event in event_types]
            actual_event_types = [msg['type'] for msg in thread_messages]
            assert actual_event_types == expected_event_types, f"Event sequence wrong for {scenario['user_id']}"
        
        # Verify no cross-user contamination
        all_sent_messages = mock_websocket_manager.sent_messages
        user_message_counts = {}
        
        for thread_id, message in all_sent_messages:
            user_message_counts[thread_id] = user_message_counts.get(thread_id, 0) + 1
        
        for scenario in user_scenarios:
            expected_count = len(event_types)
            actual_count = user_message_counts.get(scenario["thread_id"], 0)
            assert actual_count == expected_count, f"User {scenario['user_id']} should receive exactly {expected_count} messages"
        
        print(f"✅ WebSocket events reach users: {len(user_scenarios)} users × {len(event_types)} events delivered successfully")
    
    @pytest.mark.asyncio
    async def test_event_delivery_failure_recovery(self, websocket_bridge, mock_websocket_manager, test_registry):
        """CRITICAL: Test event delivery failure handling and recovery."""
        
        # Setup test scenario  
        run_id = generate_run_id("recovery_test_user", "failure_test")
        thread_id = "thread_recovery_test_user"
        agent_name = "RecoveryTestAgent"
        
        await test_registry.register(run_id, thread_id)
        
        # Test different failure scenarios
        failure_scenarios = [
            {
                "name": "connection_timeout",
                "failure_mode": "timeout",
                "expected_success": False,
                "recovery_action": lambda: mock_websocket_manager.failure_modes.clear()
            },
            {
                "name": "connection_closed", 
                "failure_mode": "connection_closed",
                "expected_success": False,
                "recovery_action": lambda: mock_websocket_manager.set_connection_status(thread_id, True)
            },
            {
                "name": "rate_limited",
                "failure_mode": "rate_limited", 
                "expected_success": False,
                "recovery_action": lambda: mock_websocket_manager.failure_modes.clear()
            },
            {
                "name": "network_partition",
                "failure_mode": "network_partition",
                "expected_success": False, 
                "recovery_action": lambda: mock_websocket_manager.restore_network()
            }
        ]
        
        for scenario in failure_scenarios:
            mock_websocket_manager.clear_all_messages()
            
            # Set failure condition
            if scenario["failure_mode"] == "network_partition":
                mock_websocket_manager.partition_network()
            else:
                mock_websocket_manager.set_failure_mode(thread_id, scenario["failure_mode"])
            
            # Attempt to send event
            success = await websocket_bridge.notify_agent_started(run_id, agent_name)
            assert success == scenario["expected_success"], f"Failure scenario '{scenario['name']}' should return {scenario['expected_success']}"
            
            # Verify no message delivered during failure
            thread_messages = mock_websocket_manager.get_thread_messages(thread_id)
            assert len(thread_messages) == 0, f"No messages should be delivered during {scenario['name']}"
            
            # Perform recovery action
            scenario["recovery_action"]()
            
            # Verify recovery works
            success = await websocket_bridge.notify_agent_thinking(run_id, agent_name, "Recovery test")
            assert success, f"Recovery should work after {scenario['name']}"
            
            # Verify message delivered after recovery
            thread_messages = mock_websocket_manager.get_thread_messages(thread_id)
            assert len(thread_messages) == 1, f"Message should be delivered after recovery from {scenario['name']}"
        
        print("✅ Event delivery failure recovery: PASSED")
    
    @pytest.mark.asyncio
    async def test_high_frequency_event_delivery(self, websocket_bridge, mock_websocket_manager, test_registry):
        """CRITICAL: Test high-frequency event delivery without loss."""
        
        run_id = generate_run_id("high_frequency_user", "performance_test")
        thread_id = "thread_high_frequency_user"
        agent_name = "HighFrequencyAgent"
        
        await test_registry.register(run_id, thread_id)
        mock_websocket_manager.set_connection_status(thread_id, True)
        
        # Send rapid sequence of events
        event_count = 200
        event_batch_size = 50
        
        start_time = time.time()
        
        # Send events in batches to simulate realistic load
        for batch in range(0, event_count, event_batch_size):
            batch_tasks = []
            
            for i in range(batch_size):
                event_index = batch + i
                if event_index >= event_count:
                    break
                
                # Vary event types
                event_type = event_index % 4
                if event_type == 0:
                    task = websocket_bridge.notify_agent_thinking(run_id, agent_name, f"Step {event_index}")
                elif event_type == 1:
                    task = websocket_bridge.notify_tool_executing(run_id, agent_name, f"tool_{event_index}")
                elif event_type == 2:
                    task = websocket_bridge.notify_progress_update(run_id, agent_name, {"percentage": event_index % 100})
                else:
                    task = websocket_bridge.notify_tool_completed(run_id, agent_name, f"tool_{event_index}", {"result": f"output_{event_index}"})
                
                batch_tasks.append(task)
            
            # Execute batch
            batch_results = await asyncio.gather(*batch_tasks)
            
            # Verify all succeeded
            assert all(batch_results), f"All events in batch {batch // event_batch_size} should succeed"
            
            # Small delay between batches
            await asyncio.sleep(0.01)
        
        total_time = time.time() - start_time
        
        # Verify all messages delivered
        thread_messages = mock_websocket_manager.get_thread_messages(thread_id)
        assert len(thread_messages) == event_count, f"Should deliver all {event_count} messages"
        
        # Verify message ordering (run_id should be consistent)
        for i, message in enumerate(thread_messages):
            assert message['run_id'] == run_id, f"Message {i} should have correct run_id"
            assert message['agent_name'] == agent_name, f"Message {i} should have correct agent_name"
        
        # Performance assertion
        events_per_second = event_count / total_time
        assert events_per_second > 50, f"Event throughput too low: {events_per_second:.1f} events/sec"
        
        print(f"✅ High-frequency event delivery: {event_count} events delivered in {total_time:.2f}s ({events_per_second:.1f} events/sec)")


class TestOrchestratorIntegration:
    """Test orchestrator initialization and fallback mechanisms."""
    
    @pytest.mark.asyncio
    async def test_orchestrator_initialization_required(self, websocket_bridge, mock_orchestrator):
        """CRITICAL: Test that orchestrator initialization is properly validated."""
        
        # Test uninitialized orchestrator
        mock_orchestrator.set_initialization_status(False)
        
        run_id = "init_test_123"
        thread_id = "thread_init_test"
        
        # Set mapping in orchestrator (but it's not initialized)
        mock_orchestrator.set_thread_mapping(run_id, thread_id)
        
        # Resolution should fail when orchestrator not initialized
        result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
        # Should fall back to pattern extraction since orchestrator fails
        assert result is None, "Should return None when orchestrator not initialized and no other resolution"
        
        # Initialize orchestrator
        mock_orchestrator.set_initialization_status(True)
        
        # Resolution should now work
        result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
        assert result == thread_id, f"Should resolve after initialization: expected '{thread_id}', got '{result}'"
        
        # Verify metrics show the failure and recovery
        metrics = await mock_orchestrator.get_metrics()
        assert metrics['failed_resolutions'] > 0, "Should show failures during uninitialized period"
        assert metrics['successful_resolutions'] > 0, "Should show success after initialization"
        
        print("✅ Orchestrator initialization required: PASSED")
    
    @pytest.mark.asyncio  
    async def test_orchestrator_unavailable_fallback(self, websocket_bridge, mock_orchestrator, test_registry):
        """CRITICAL: Test graceful fallback when orchestrator becomes unavailable."""
        
        run_id_1 = "orchestrator_unavailable_1"
        thread_id_1 = "thread_unavailable_1" 
        
        run_id_2 = "orchestrator_unavailable_thread_pattern_456" 
        expected_pattern_thread = "thread_pattern"
        
        # Setup: Registry has run_id_1, orchestrator has both
        await test_registry.register(run_id_1, thread_id_1)
        mock_orchestrator.set_thread_mapping(run_id_1, "thread_orchestrator_1")
        mock_orchestrator.set_thread_mapping(run_id_2, "thread_orchestrator_2")
        
        # Test 1: Normal operation (registry takes priority)
        result = await websocket_bridge._resolve_thread_id_from_run_id(run_id_1)
        assert result == thread_id_1, "Registry should take priority"
        
        # Test 2: Make orchestrator unavailable
        mock_orchestrator.set_availability(False)
        
        # run_id_1 should still resolve via registry
        result = await websocket_bridge._resolve_thread_id_from_run_id(run_id_1)
        assert result == thread_id_1, "Should fall back to registry when orchestrator unavailable"
        
        # run_id_2 should fall back to pattern extraction
        result = await websocket_bridge._resolve_thread_id_from_run_id(run_id_2)
        assert result == expected_pattern_thread, f"Should fall back to pattern: expected '{expected_pattern_thread}', got '{result}'"
        
        # Test 3: Restore orchestrator availability
        mock_orchestrator.set_availability(True)
        
        # Verify orchestrator works again
        result = await websocket_bridge._resolve_thread_id_from_run_id(run_id_2)
        assert result == "thread_orchestrator_2", "Should use orchestrator again when available"
        
        print("✅ Orchestrator unavailable fallback: PASSED")
    
    @pytest.mark.asyncio
    async def test_orchestrator_performance_degradation(self, websocket_bridge, mock_orchestrator):
        """CRITICAL: Test behavior when orchestrator performance degrades."""
        
        # Setup slow orchestrator responses
        slow_run_ids = [f"slow_test_{i}" for i in range(5)]
        fast_run_ids = [f"fast_test_{i}" for i in range(5)]
        
        # Make some run_ids slow
        for run_id in slow_run_ids:
            thread_id = f"thread_{run_id}"
            mock_orchestrator.set_thread_mapping(run_id, thread_id)
            mock_orchestrator.set_resolution_delay(run_id, 2.0)  # 2 second delay
        
        # Make some run_ids fast
        for run_id in fast_run_ids:
            thread_id = f"thread_{run_id}"
            mock_orchestrator.set_thread_mapping(run_id, thread_id)
            # No delay for these
        
        # Test concurrent resolution (mix of fast and slow)
        all_run_ids = slow_run_ids + fast_run_ids
        random.shuffle(all_run_ids)
        
        start_time = time.time()
        
        # Resolve all concurrently
        tasks = [
            websocket_bridge._resolve_thread_id_from_run_id(run_id)
            for run_id in all_run_ids
        ]
        
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Verify all resolutions succeeded despite delays
        assert all(result is not None for result in results), "All resolutions should succeed"
        
        # Verify correct mappings returned
        for i, run_id in enumerate(all_run_ids):
            expected = f"thread_{run_id}"
            actual = results[i]
            assert actual == expected, f"Resolution failed for {run_id}: expected '{expected}', got '{actual}'"
        
        # Total time should be around 2 seconds (concurrent execution)
        assert total_time < 3.0, f"Concurrent resolution should be faster: {total_time:.2f}s"
        assert total_time > 1.8, f"Should respect delays: {total_time:.2f}s"
        
        # Check orchestrator metrics
        metrics = await mock_orchestrator.get_metrics()
        assert metrics['resolution_calls'] == len(all_run_ids), "Should have called orchestrator for each run_id"
        assert metrics['avg_resolution_time_ms'] > 1000, "Average time should reflect delays"
        
        print(f"✅ Orchestrator performance degradation: {len(all_run_ids)} resolutions in {total_time:.2f}s")


class TestConcurrentOperations:
    """Test concurrent agent executions and multi-user scenarios."""
    
    @pytest.mark.asyncio
    async def test_concurrent_agents_different_threads(self, websocket_bridge, mock_websocket_manager, test_registry):
        """CRITICAL: Test multiple agents running concurrently in different threads."""
        
        # Setup multiple concurrent agent scenarios
        agent_scenarios = []
        for i in range(20):  # 20 concurrent agents
            scenario = {
                "agent_id": f"agent_{i}",
                "user_id": f"user_{i}",
                "thread_id": f"thread_user_{i}_session",
                "run_id": generate_run_id(f"user_{i}_session", "concurrent_test"),
                "agent_name": f"ConcurrentAgent_{i}"
            }
            agent_scenarios.append(scenario)
        
        # Register all thread mappings
        for scenario in agent_scenarios:
            await test_registry.register(scenario["run_id"], scenario["thread_id"])
            mock_websocket_manager.set_connection_status(scenario["thread_id"], True)
        
        # Define agent execution flow
        async def execute_agent(scenario: Dict) -> Dict[str, Any]:
            results = {
                "scenario": scenario,
                "events_sent": 0,
                "events_succeeded": 0,
                "start_time": time.time(),
                "end_time": None
            }
            
            # Agent execution sequence
            events = [
                ("notify_agent_started", {"context": {"task": f"Task for {scenario['agent_name']}"}}),
                ("notify_agent_thinking", {"reasoning": "Analyzing request", "step_number": 1}),
                ("notify_tool_executing", {"tool_name": "data_processor", "parameters": {"source": "database"}}),
                ("notify_progress_update", {"progress": {"percentage": 33, "message": "Processing data"}}),
                ("notify_tool_completed", {"tool_name": "data_processor", "result": {"rows": 100}}),
                ("notify_agent_thinking", {"reasoning": "Generating response", "step_number": 2}),
                ("notify_tool_executing", {"tool_name": "response_generator", "parameters": {"format": "json"}}),
                ("notify_progress_update", {"progress": {"percentage": 66, "message": "Generating response"}}),
                ("notify_tool_completed", {"tool_name": "response_generator", "result": {"response": "Generated"}}),
                ("notify_progress_update", {"progress": {"percentage": 100, "message": "Complete"}}),
                ("notify_agent_completed", {"result": {"status": "success", "output": "Final result"}})
            ]
            
            # Execute events with small delays to simulate realistic execution
            for event_method, event_kwargs in events:
                results["events_sent"] += 1
                
                method = getattr(websocket_bridge, event_method)
                success = await method(
                    scenario["run_id"],
                    scenario["agent_name"],
                    **event_kwargs
                )
                
                if success:
                    results["events_succeeded"] += 1
                
                # Small delay between events
                await asyncio.sleep(random.uniform(0.01, 0.05))
            
            results["end_time"] = time.time()
            return results
        
        # Execute all agents concurrently
        start_time = time.time()
        execution_tasks = [execute_agent(scenario) for scenario in agent_scenarios]
        execution_results = await asyncio.gather(*execution_tasks)
        total_execution_time = time.time() - start_time
        
        # Analyze results
        total_events_sent = sum(result["events_sent"] for result in execution_results)
        total_events_succeeded = sum(result["events_succeeded"] for result in execution_results)
        success_rate = total_events_succeeded / max(1, total_events_sent)
        
        # Verify high success rate
        assert success_rate > 0.95, f"Success rate too low: {success_rate:.2%}"
        
        # Verify all agents completed
        for result in execution_results:
            agent_success_rate = result["events_succeeded"] / result["events_sent"]
            assert agent_success_rate > 0.9, f"Agent {result['scenario']['agent_name']} success rate too low: {agent_success_rate:.2%}"
        
        # Verify message isolation (no cross-contamination)
        for scenario in agent_scenarios:
            thread_messages = mock_websocket_manager.get_thread_messages(scenario["thread_id"])
            
            # Should have all expected events
            expected_event_count = 11  # Number of events in sequence
            assert len(thread_messages) == expected_event_count, f"Thread {scenario['thread_id']} should have {expected_event_count} messages"
            
            # All messages should be for this agent
            for message in thread_messages:
                assert message["run_id"] == scenario["run_id"], "Message should have correct run_id"
                assert message["agent_name"] == scenario["agent_name"], "Message should have correct agent_name"
        
        # Performance verification
        events_per_second = total_events_sent / total_execution_time
        assert events_per_second > 100, f"Event throughput too low: {events_per_second:.1f} events/sec"
        
        print(f"✅ Concurrent agents different threads: {len(agent_scenarios)} agents × 11 events = {total_events_sent} events in {total_execution_time:.2f}s ({events_per_second:.1f} events/sec)")
    
    @pytest.mark.asyncio
    async def test_reconnection_preserves_mappings(self, websocket_bridge, mock_websocket_manager, test_registry):
        """CRITICAL: Test that reconnection preserves thread mappings."""
        
        # Setup initial mappings
        scenarios = [
            {"run_id": generate_run_id("user_1_session", "reconnect_test"), "thread_id": "thread_user_1_session"},
            {"run_id": generate_run_id("user_2_chat", "reconnect_test"), "thread_id": "thread_user_2_chat"},
            {"run_id": generate_run_id("user_3_support", "reconnect_test"), "thread_id": "thread_user_3_support"}
        ]
        
        # Register mappings
        for scenario in scenarios:
            await test_registry.register(scenario["run_id"], scenario["thread_id"])
            mock_websocket_manager.set_connection_status(scenario["thread_id"], True)
        
        # Send initial events to verify connectivity
        for scenario in scenarios:
            success = await websocket_bridge.notify_agent_started(scenario["run_id"], "InitialAgent")
            assert success, f"Initial event should succeed for {scenario['thread_id']}"
        
        initial_message_counts = {
            scenario["thread_id"]: mock_websocket_manager.get_thread_message_count(scenario["thread_id"])
            for scenario in scenarios
        }
        
        # Simulate network disconnection
        mock_websocket_manager.partition_network()
        
        # Events should fail during disconnection
        for scenario in scenarios:
            success = await websocket_bridge.notify_agent_thinking(scenario["run_id"], "DisconnectedAgent", "Should fail")
            assert not success, f"Event should fail during disconnection for {scenario['thread_id']}"
        
        # Verify no new messages during disconnection
        for scenario in scenarios:
            current_count = mock_websocket_manager.get_thread_message_count(scenario["thread_id"])
            initial_count = initial_message_counts[scenario["thread_id"]]
            assert current_count == initial_count, f"No new messages should arrive during disconnection for {scenario['thread_id']}"
        
        # Restore network connectivity (simulate reconnection)
        mock_websocket_manager.restore_network()
        
        # Re-establish connections
        for scenario in scenarios:
            mock_websocket_manager.set_connection_status(scenario["thread_id"], True)
        
        # Verify mappings preserved after reconnection
        for scenario in scenarios:
            # Resolution should still work
            resolved_thread = await websocket_bridge._resolve_thread_id_from_run_id(scenario["run_id"])
            assert resolved_thread == scenario["thread_id"], f"Mapping should be preserved after reconnection"
            
            # Events should work again
            success = await websocket_bridge.notify_agent_completed(scenario["run_id"], "ReconnectedAgent")
            assert success, f"Event should succeed after reconnection for {scenario['thread_id']}"
        
        # Verify new messages delivered after reconnection
        for scenario in scenarios:
            current_count = mock_websocket_manager.get_thread_message_count(scenario["thread_id"])
            initial_count = initial_message_counts[scenario["thread_id"]]
            assert current_count == initial_count + 1, f"Should have one new message after reconnection for {scenario['thread_id']}"
        
        print("✅ Reconnection preserves mappings: PASSED")
    
    @pytest.mark.asyncio
    async def test_system_under_extreme_load(self, websocket_bridge, mock_websocket_manager, test_registry):
        """CRITICAL: Test system behavior under extreme concurrent load."""
        
        # Setup extreme load scenario
        thread_count = 100
        events_per_thread = 20
        total_expected_events = thread_count * events_per_thread
        
        # Generate scenarios
        scenarios = []
        for i in range(thread_count):
            scenario = {
                "thread_id": f"thread_load_test_{i}",
                "run_id": generate_run_id(f"load_test_user_{i}", "extreme_load"),
                "agent_name": f"LoadTestAgent_{i}"
            }
            scenarios.append(scenario)
        
        # Register all mappings
        registration_start = time.time()
        for scenario in scenarios:
            await test_registry.register(scenario["run_id"], scenario["thread_id"])
            mock_websocket_manager.set_connection_status(scenario["thread_id"], True)
        registration_time = time.time() - registration_start
        
        # Define load generator
        async def generate_load(scenario: Dict, event_count: int) -> Dict[str, Any]:
            results = {"sent": 0, "succeeded": 0, "errors": 0}
            
            for event_idx in range(event_count):
                try:
                    # Vary event types
                    event_type = event_idx % 5
                    
                    if event_type == 0:
                        success = await websocket_bridge.notify_agent_started(
                            scenario["run_id"], 
                            scenario["agent_name"]
                        )
                    elif event_type == 1:
                        success = await websocket_bridge.notify_agent_thinking(
                            scenario["run_id"],
                            scenario["agent_name"], 
                            f"Processing step {event_idx}"
                        )
                    elif event_type == 2:
                        success = await websocket_bridge.notify_tool_executing(
                            scenario["run_id"],
                            scenario["agent_name"],
                            f"tool_{event_idx}"
                        )
                    elif event_type == 3:
                        success = await websocket_bridge.notify_progress_update(
                            scenario["run_id"],
                            scenario["agent_name"],
                            {"percentage": (event_idx * 100) // event_count}
                        )
                    else:
                        success = await websocket_bridge.notify_tool_completed(
                            scenario["run_id"],
                            scenario["agent_name"],
                            f"tool_{event_idx}",
                            {"result": f"output_{event_idx}"}
                        )
                    
                    results["sent"] += 1
                    if success:
                        results["succeeded"] += 1
                
                except Exception as e:
                    results["errors"] += 1
            
            return results
        
        # Execute extreme load
        load_start = time.time()
        load_tasks = [generate_load(scenario, events_per_thread) for scenario in scenarios]
        load_results = await asyncio.gather(*load_tasks)
        load_time = time.time() - load_start
        
        # Aggregate results
        total_sent = sum(result["sent"] for result in load_results)
        total_succeeded = sum(result["succeeded"] for result in load_results)
        total_errors = sum(result["errors"] for result in load_results)
        
        success_rate = total_succeeded / max(1, total_sent)
        events_per_second = total_sent / load_time
        
        # Verify system handled extreme load
        assert success_rate > 0.90, f"Success rate under extreme load too low: {success_rate:.2%}"
        assert total_errors < total_sent * 0.05, f"Too many errors: {total_errors}"
        assert events_per_second > 200, f"Throughput too low under load: {events_per_second:.1f} events/sec"
        
        # Verify registry health under load
        registry_metrics = await test_registry.get_metrics()
        assert registry_metrics['registry_healthy'], "Registry should remain healthy under extreme load"
        assert registry_metrics['lookup_success_rate'] > 0.95, f"Registry lookup success rate too low: {registry_metrics['lookup_success_rate']:.2%}"
        
        # Verify WebSocket manager health
        ws_metrics = mock_websocket_manager.get_metrics()
        assert ws_metrics['success_rate'] > 0.90, f"WebSocket success rate too low: {ws_metrics['success_rate']:.2%}"
        
        print(f"✅ System under extreme load: {thread_count} threads × {events_per_thread} events = {total_sent} events in {load_time:.2f}s ({events_per_second:.1f} events/sec, {success_rate:.1%} success rate)")


class TestBusinessMetrics:
    """Test business value validation and metrics tracking."""
    
    @pytest.mark.asyncio
    async def test_event_delivery_success_rate_metrics(self, websocket_bridge, mock_websocket_manager, test_registry):
        """CRITICAL: Validate business metrics for event delivery success rate."""
        
        # Setup business scenarios representing different user types
        business_scenarios = [
            {"type": "free_user", "thread_count": 10, "events_per_thread": 5},
            {"type": "early_user", "thread_count": 20, "events_per_thread": 10},
            {"type": "mid_user", "thread_count": 30, "events_per_thread": 15},
            {"type": "enterprise_user", "thread_count": 40, "events_per_thread": 20}
        ]
        
        business_metrics = {}
        
        for scenario in business_scenarios:
            scenario_start = time.time()
            
            # Setup threads for this user type
            threads = []
            for i in range(scenario["thread_count"]):
                thread_info = {
                    "thread_id": f"thread_{scenario['type']}_{i}",
                    "run_id": generate_run_id(f"{scenario['type']}_{i}", "business_metrics"),
                    "agent_name": f"Agent_{scenario['type']}_{i}"
                }
                threads.append(thread_info)
                
                # Register mapping
                await test_registry.register(thread_info["run_id"], thread_info["thread_id"])
                mock_websocket_manager.set_connection_status(thread_info["thread_id"], True)
            
            # Send events for all threads in this scenario
            events_sent = 0
            events_succeeded = 0
            
            for thread_info in threads:
                for event_idx in range(scenario["events_per_thread"]):
                    # Vary event types to match real usage
                    event_type = event_idx % 3
                    
                    if event_type == 0:
                        success = await websocket_bridge.notify_agent_started(
                            thread_info["run_id"],
                            thread_info["agent_name"]
                        )
                    elif event_type == 1:
                        success = await websocket_bridge.notify_agent_thinking(
                            thread_info["run_id"],
                            thread_info["agent_name"],
                            f"Business logic step {event_idx}"
                        )
                    else:
                        success = await websocket_bridge.notify_agent_completed(
                            thread_info["run_id"],
                            thread_info["agent_name"]
                        )
                    
                    events_sent += 1
                    if success:
                        events_succeeded += 1
            
            scenario_time = time.time() - scenario_start
            success_rate = events_succeeded / max(1, events_sent)
            events_per_second = events_sent / scenario_time
            
            # Store business metrics
            business_metrics[scenario["type"]] = {
                "events_sent": events_sent,
                "events_succeeded": events_succeeded,
                "success_rate": success_rate,
                "events_per_second": events_per_second,
                "execution_time": scenario_time,
                "thread_count": scenario["thread_count"],
                "avg_events_per_thread": scenario["events_per_thread"]
            }
            
            # Business value assertions per user type
            if scenario["type"] == "enterprise_user":
                # Enterprise users require highest reliability
                assert success_rate >= 0.99, f"Enterprise success rate too low: {success_rate:.2%}"
                assert events_per_second >= 100, f"Enterprise throughput too low: {events_per_second:.1f}"
            elif scenario["type"] in ["early_user", "mid_user"]:
                # Paid users require high reliability
                assert success_rate >= 0.95, f"Paid user success rate too low for {scenario['type']}: {success_rate:.2%}"
                assert events_per_second >= 50, f"Paid user throughput too low: {events_per_second:.1f}"
            else:  # free_user
                # Free users still need good experience for conversion
                assert success_rate >= 0.90, f"Free user success rate too low: {success_rate:.2%}"
        
        # Cross-scenario business metrics validation
        total_events = sum(metrics["events_sent"] for metrics in business_metrics.values())
        total_succeeded = sum(metrics["events_succeeded"] for metrics in business_metrics.values())
        overall_success_rate = total_succeeded / total_events
        
        # Overall platform reliability
        assert overall_success_rate >= 0.95, f"Overall platform success rate too low: {overall_success_rate:.2%}"
        
        # Enterprise performance should be best
        enterprise_rate = business_metrics["enterprise_user"]["success_rate"]
        free_rate = business_metrics["free_user"]["success_rate"]
        assert enterprise_rate >= free_rate, "Enterprise users should have equal or better performance than free users"
        
        # Log business metrics
        print("✅ Business Metrics Summary:")
        for user_type, metrics in business_metrics.items():
            print(f"  {user_type}: {metrics['success_rate']:.1%} success, {metrics['events_per_second']:.1f} events/sec, {metrics['thread_count']} threads")
        print(f"  Overall: {overall_success_rate:.1%} success rate, {total_events} total events")
    
    @pytest.mark.asyncio
    async def test_thread_resolution_accuracy_metrics(self, websocket_bridge, test_registry, mock_orchestrator):
        """CRITICAL: Measure and validate thread resolution accuracy for business impact."""
        
        # Setup comprehensive resolution test cases
        test_cases = [
            {
                "category": "registry_resolution",
                "setup": lambda run_id, thread_id: test_registry.register(run_id, thread_id),
                "expected_source": "registry"
            },
            {
                "category": "orchestrator_resolution", 
                "setup": lambda run_id, thread_id: mock_orchestrator.set_thread_mapping(run_id, thread_id),
                "expected_source": "orchestrator"
            },
            {
                "category": "pattern_resolution",
                "setup": lambda run_id, thread_id: None,  # No setup needed for pattern
                "expected_source": "pattern",
                "run_id_pattern": "pattern_test_thread_{}_extraction"
            }
        ]
        
        resolution_metrics = {}
        
        for test_case in test_cases:
            category = test_case["category"]
            resolution_start = time.time()
            
            # Generate test data
            test_count = 100
            successful_resolutions = 0
            failed_resolutions = 0
            incorrect_resolutions = 0
            
            for i in range(test_count):
                if test_case.get("run_id_pattern"):
                    # Use pattern-based run_id for pattern resolution tests
                    thread_id = f"thread_{i}"
                    run_id = test_case["run_id_pattern"].format(i)
                else:
                    # Use generated run_id for registry/orchestrator tests
                    thread_id = f"thread_{category}_{i}"
                    run_id = generate_run_id(f"{category}_{i}", "resolution_accuracy")
                
                # Setup according to test case
                if test_case["setup"](run_id, thread_id):
                    await test_case["setup"](run_id, thread_id)
                
                # Attempt resolution
                resolved_thread = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
                
                if resolved_thread is None:
                    failed_resolutions += 1
                elif resolved_thread == thread_id:
                    successful_resolutions += 1
                else:
                    incorrect_resolutions += 1
            
            resolution_time = time.time() - resolution_start
            
            # Calculate metrics
            total_attempts = test_count
            success_rate = successful_resolutions / total_attempts
            failure_rate = failed_resolutions / total_attempts
            accuracy_rate = successful_resolutions / max(1, successful_resolutions + incorrect_resolutions)
            avg_resolution_time = (resolution_time / total_attempts) * 1000  # Convert to ms
            
            resolution_metrics[category] = {
                "total_attempts": total_attempts,
                "successful_resolutions": successful_resolutions,
                "failed_resolutions": failed_resolutions,
                "incorrect_resolutions": incorrect_resolutions,
                "success_rate": success_rate,
                "accuracy_rate": accuracy_rate,
                "avg_resolution_time_ms": avg_resolution_time,
                "total_time": resolution_time
            }
            
            # Business-critical assertions per resolution source
            if category == "registry_resolution":
                # Registry should be most reliable (primary source)
                assert success_rate >= 0.99, f"Registry resolution rate too low: {success_rate:.2%}"
                assert accuracy_rate >= 0.999, f"Registry accuracy too low: {accuracy_rate:.3%}"
                assert avg_resolution_time < 5.0, f"Registry resolution too slow: {avg_resolution_time:.1f}ms"
            elif category == "orchestrator_resolution":
                # Orchestrator should be highly reliable (backup source)
                assert success_rate >= 0.95, f"Orchestrator resolution rate too low: {success_rate:.2%}"
                assert accuracy_rate >= 0.99, f"Orchestrator accuracy too low: {accuracy_rate:.2%}"
                assert avg_resolution_time < 50.0, f"Orchestrator resolution too slow: {avg_resolution_time:.1f}ms"
            else:  # pattern_resolution
                # Pattern should be reliable fallback
                assert success_rate >= 0.90, f"Pattern resolution rate too low: {success_rate:.2%}"
                assert accuracy_rate >= 0.95, f"Pattern accuracy too low: {accuracy_rate:.2%}"
                assert avg_resolution_time < 10.0, f"Pattern resolution too slow: {avg_resolution_time:.1f}ms"
        
        # Cross-source validation
        registry_success = resolution_metrics["registry_resolution"]["success_rate"]
        orchestrator_success = resolution_metrics["orchestrator_resolution"]["success_rate"]
        pattern_success = resolution_metrics["pattern_resolution"]["success_rate"]
        
        # Priority order should reflect reliability
        assert registry_success >= orchestrator_success, "Registry should be most reliable"
        assert orchestrator_success >= pattern_success * 0.95, "Orchestrator should be more reliable than pattern"
        
        # Log resolution accuracy metrics
        print("✅ Thread Resolution Accuracy Metrics:")
        for source, metrics in resolution_metrics.items():
            print(f"  {source}: {metrics['success_rate']:.1%} success, {metrics['accuracy_rate']:.2%} accuracy, {metrics['avg_resolution_time_ms']:.1f}ms avg")
        
        return resolution_metrics


if __name__ == "__main__":
    # Run comprehensive critical flows test suite
    pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "--asyncio-mode=auto",
        "-s",  # Show print statements
        "--maxfail=5"  # Stop after 5 failures for faster feedback
    ])

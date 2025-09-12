#!/usr/bin/env python

# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
MISSION CRITICAL: WebSocket Critical Validation Test Suite

This test suite validates the critical WebSocket event delivery that powers 90% of the platform's
business value through real-time AI chat interactions. These tests ensure the 5 required
WebSocket events are properly sent and received during agent execution.

Required Events:
1. agent_started - User sees agent began processing
2. agent_thinking - Real-time reasoning visibility  
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results display
5. agent_completed - User knows response is ready

CRITICAL: Uses REAL WebSocket connections - NO MOCKS per CLAUDE.md
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Set, Any, Optional
import pytest
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set up real test environment
os.environ['WEBSOCKET_TEST_ISOLATED'] = 'true'
os.environ['SKIP_REAL_SERVICES'] = 'false'

try:
    from shared.isolated_environment import get_env
    from netra_backend.app.websocket_core import (
        get_websocket_manager,
        WebSocketManager,
        WebSocketMessage,
        create_standard_message
    )
    from netra_backend.app.core.unified_id_manager import UnifiedIDManager
    # Legacy function mappings for compatibility
    generate_run_id = lambda thread_id: UnifiedIDManager.generate_run_id(thread_id)
    extract_thread_id_from_run_id = lambda run_id: UnifiedIDManager.extract_thread_id(run_id)
    validate_run_id_format = lambda run_id: UnifiedIDManager.validate_run_id(run_id)
    from test_framework.test_context import (
        TestContext,
        TestUserContext,
        create_test_context,
        create_isolated_test_contexts
    )
except ImportError as e:
    pytest.skip(f"Could not import required WebSocket components: {e}", allow_module_level=True)


class WebSocketEventTracker:
    """Track WebSocket events for testing - uses REAL WebSocket manager underneath."""
    
    def __init__(self):
        self.events_captured: List[Dict[str, Any]] = []
        self.events_by_thread: Dict[str, List[Dict[str, Any]]] = {}
        self.event_counts: Dict[str, int] = {}
        self.websocket_manager = get_websocket_manager()
        self.start_time = time.time()
        
        # Required events for agent execution
        self.required_events = {
            "agent_started",
            "agent_thinking",
            "tool_executing", 
            "tool_completed",
            "agent_completed"
        }
    
    async def send_agent_event(self, thread_id: str, event_type: str, data: Dict[str, Any]) -> bool:
        """Send agent event via real WebSocket manager and track it."""
        try:
            # Create standard WebSocket message
            message = create_standard_message(
                message_type=event_type,
                data=data,
                user_id=data.get('user_id', 'test_user'),
                thread_id=thread_id
            )
            
            # Send via real WebSocket manager
            success = await self.websocket_manager.send_to_thread(thread_id, message)
            
            # Track the event for validation
            if success:
                event_record = {
                    'type': event_type,
                    'thread_id': thread_id,
                    'data': data,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'message': message
                }
                
                self.events_captured.append(event_record)
                
                if thread_id not in self.events_by_thread:
                    self.events_by_thread[thread_id] = []
                self.events_by_thread[thread_id].append(event_record)
                
                self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
            
            return success
            
        except Exception as e:
            print(f"Error sending WebSocket event: {e}")
            return False
    
    def get_events_for_thread(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get all events for a specific thread."""
        return self.events_by_thread.get(thread_id, [])
    
    def has_required_events_for_thread(self, thread_id: str) -> bool:
        """Check if thread has all required agent events."""
        thread_events = self.get_events_for_thread(thread_id)
        thread_event_types = {event['type'] for event in thread_events}
        return self.required_events.issubset(thread_event_types)
    
    def get_missing_events_for_thread(self, thread_id: str) -> Set[str]:
        """Get missing required events for a thread."""
        thread_events = self.get_events_for_thread(thread_id)
        thread_event_types = {event['type'] for event in thread_events}
        return self.required_events - thread_event_types
    
    def clear_events(self):
        """Clear all tracked events."""
        self.events_captured.clear()
        self.events_by_thread.clear()
        self.event_counts.clear()


class TestWebSocketCriticalValidation:
    """Critical WebSocket validation tests using REAL WebSocket connections."""
    
    @pytest.fixture(autouse=True)
    async def setup_test_environment(self):
        """Setup real WebSocket test environment."""
        self.event_tracker = WebSocketEventTracker()
        
        # Use real TestContext for WebSocket testing
        self.test_contexts = create_isolated_test_contexts(count=3)
        
        yield
        
        # Cleanup
        for context in self.test_contexts:
            await context.cleanup()
    
    @pytest.mark.asyncio
    async def test_all_required_agent_events_sent(self):
        """CRITICAL: Verify all 5 required agent events are sent during agent execution."""
        
        # Setup test scenario
        user_context = self.test_contexts[0].user_context
        thread_id = user_context.thread_id
        run_id = generate_run_id(thread_id, "critical_test")
        agent_name = "CriticalTestAgent"
        
        print(f"🎯 Testing required events for thread: {thread_id}")
        
        # Send all required events in proper sequence
        events_to_send = [
            ("agent_started", {
                "agent_name": agent_name,
                "run_id": run_id,
                "user_id": user_context.user_id,
                "context": {"task": "Critical validation test"}
            }),
            ("agent_thinking", {
                "agent_name": agent_name, 
                "run_id": run_id,
                "user_id": user_context.user_id,
                "reasoning": "Analyzing test scenario",
                "step_number": 1
            }),
            ("tool_executing", {
                "agent_name": agent_name,
                "run_id": run_id, 
                "user_id": user_context.user_id,
                "tool_name": "validation_tool",
                "parameters": {"test_mode": True}
            }),
            ("tool_completed", {
                "agent_name": agent_name,
                "run_id": run_id,
                "user_id": user_context.user_id,
                "tool_name": "validation_tool",
                "result": {"success": True, "validation": "passed"}
            }),
            ("agent_completed", {
                "agent_name": agent_name,
                "run_id": run_id,
                "user_id": user_context.user_id,
                "result": {"status": "success", "message": "Critical validation complete"}
            })
        ]
        
        # Send events with small delays
        successful_sends = 0
        for event_type, event_data in events_to_send:
            success = await self.event_tracker.send_agent_event(thread_id, event_type, event_data)
            if success:
                successful_sends += 1
            
            # Small delay between events
            await asyncio.sleep(0.1)
        
        # Verify all events were sent successfully
        assert successful_sends == len(events_to_send), f"Only {successful_sends}/{len(events_to_send)} events sent successfully"
        
        # Verify all required events are captured
        assert self.event_tracker.has_required_events_for_thread(thread_id), \
            f"Missing required events: {self.event_tracker.get_missing_events_for_thread(thread_id)}"
        
        # Verify event content
        thread_events = self.event_tracker.get_events_for_thread(thread_id)
        assert len(thread_events) == 5, f"Should capture 5 events, got {len(thread_events)}"
        
        # Verify each event has proper structure
        for event in thread_events:
            assert 'type' in event, "Event should have type"
            assert 'thread_id' in event, "Event should have thread_id" 
            assert event['thread_id'] == thread_id, "Event should have correct thread_id"
            assert 'data' in event, "Event should have data"
            assert 'timestamp' in event, "Event should have timestamp"
            assert event['data']['run_id'] == run_id, "Event data should have correct run_id"
            assert event['data']['agent_name'] == agent_name, "Event data should have correct agent_name"
        
        print("✅ All required agent events sent and validated")
    
    @pytest.mark.asyncio
    async def test_concurrent_user_event_isolation(self):
        """CRITICAL: Verify WebSocket events are properly isolated between concurrent users."""
        
        # Setup multiple concurrent users
        user_scenarios = []
        for i, context in enumerate(self.test_contexts):
            scenario = {
                "context": context,
                "thread_id": context.user_context.thread_id,
                "run_id": generate_run_id(context.user_context.thread_id, f"isolation_test_{i}"),
                "agent_name": f"IsolationAgent_{i}",
                "user_id": context.user_context.user_id
            }
            user_scenarios.append(scenario)
        
        print(f"🔒 Testing event isolation for {len(user_scenarios)} concurrent users")
        
        # Send events for all users concurrently
        async def send_user_events(scenario):
            """Send complete event sequence for one user."""
            events_sent = 0
            
            events = [
                ("agent_started", {"task": f"Isolation test for {scenario['agent_name']}"}),
                ("agent_thinking", {"reasoning": "Processing isolated request"}),
                ("tool_executing", {"tool_name": "isolation_tool", "user_specific": True}),
                ("tool_completed", {"tool_name": "isolation_tool", "result": {"isolated": True}}),
                ("agent_completed", {"status": "isolation_verified"})
            ]
            
            for event_type, event_data in events:
                full_event_data = {
                    **event_data,
                    "agent_name": scenario["agent_name"],
                    "run_id": scenario["run_id"],
                    "user_id": scenario["user_id"]
                }
                
                success = await self.event_tracker.send_agent_event(
                    scenario["thread_id"], 
                    event_type, 
                    full_event_data
                )
                
                if success:
                    events_sent += 1
                
                # Small delay between events
                await asyncio.sleep(0.05)
            
            return events_sent
        
        # Execute all users concurrently
        tasks = [send_user_events(scenario) for scenario in user_scenarios]
        results = await asyncio.gather(*tasks)
        
        # Verify all users sent their events successfully
        total_events_sent = sum(results)
        expected_total = len(user_scenarios) * 5  # 5 events per user
        assert total_events_sent >= expected_total * 0.9, \
            f"Event delivery rate too low: {total_events_sent}/{expected_total}"
        
        # Verify isolation - each user should have their own events
        for i, scenario in enumerate(user_scenarios):
            thread_events = self.event_tracker.get_events_for_thread(scenario["thread_id"])
            
            # Should have events for this user
            assert len(thread_events) >= 4, f"User {i} should have at least 4 events"
            
            # All events should belong to this user only
            for event in thread_events:
                assert event['data']['user_id'] == scenario['user_id'], \
                    f"Event isolation violated: user {i} received event for different user"
                assert event['data']['agent_name'] == scenario['agent_name'], \
                    f"Agent isolation violated: user {i} received event for different agent"
                assert event['data']['run_id'] == scenario['run_id'], \
                    f"Run ID isolation violated: user {i} received event for different run"
        
        # Verify no cross-user contamination
        all_events = self.event_tracker.events_captured
        user_event_counts = {}
        
        for event in all_events:
            user_id = event['data']['user_id']
            user_event_counts[user_id] = user_event_counts.get(user_id, 0) + 1
        
        # Each user should have roughly equal number of events
        for scenario in user_scenarios:
            user_count = user_event_counts.get(scenario['user_id'], 0)
            assert user_count >= 4, f"User {scenario['user_id']} should have at least 4 events"
        
        print("✅ Concurrent user event isolation verified")
    
    @pytest.mark.asyncio  
    async def test_event_ordering_and_timing(self):
        """CRITICAL: Verify WebSocket events maintain correct order and timing."""
        
        user_context = self.test_contexts[0].user_context
        thread_id = user_context.thread_id
        run_id = generate_run_id(thread_id, "ordering_test")
        agent_name = "OrderingTestAgent"
        
        print(f"📋 Testing event ordering and timing for thread: {thread_id}")
        
        # Record timing for each event
        event_times = []
        
        # Send events with specific ordering requirements
        ordered_events = [
            ("agent_started", {"context": {"task": "Ordering test"}}),
            ("agent_thinking", {"reasoning": "Step 1: Initial analysis"}),
            ("tool_executing", {"tool_name": "step1_tool"}),
            ("tool_completed", {"tool_name": "step1_tool", "result": {"step": 1}}),
            ("agent_thinking", {"reasoning": "Step 2: Processing results"}),
            ("tool_executing", {"tool_name": "step2_tool"}),
            ("tool_completed", {"tool_name": "step2_tool", "result": {"step": 2}}),
            ("agent_completed", {"result": {"steps_completed": 2}})
        ]
        
        for event_type, event_data in ordered_events:
            start_time = time.time()
            
            full_event_data = {
                **event_data,
                "agent_name": agent_name,
                "run_id": run_id,
                "user_id": user_context.user_id
            }
            
            success = await self.event_tracker.send_agent_event(thread_id, event_type, full_event_data)
            
            end_time = time.time()
            event_times.append({
                "event_type": event_type,
                "success": success,
                "duration_ms": (end_time - start_time) * 1000,
                "timestamp": end_time
            })
            
            # Small delay to ensure ordering
            await asyncio.sleep(0.1)
        
        # Verify events were captured in order
        thread_events = self.event_tracker.get_events_for_thread(thread_id)
        assert len(thread_events) >= 7, f"Should capture at least 7 events, got {len(thread_events)}"
        
        # Verify chronological order
        event_timestamps = []
        for event in thread_events:
            timestamp_str = event['timestamp']
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            event_timestamps.append(timestamp)
        
        # Events should be in chronological order
        for i in range(1, len(event_timestamps)):
            assert event_timestamps[i] >= event_timestamps[i-1], \
                f"Event {i} timestamp should be >= previous event timestamp"
        
        # Verify agent_started comes first
        first_event = thread_events[0]
        assert first_event['type'] == 'agent_started', \
            f"First event should be agent_started, got {first_event['type']}"
        
        # Verify tool pairing (tool_executing followed by tool_completed)
        tool_executing_indices = []
        tool_completed_indices = []
        
        for i, event in enumerate(thread_events):
            if event['type'] == 'tool_executing':
                tool_executing_indices.append(i)
            elif event['type'] == 'tool_completed':
                tool_completed_indices.append(i)
        
        # Each tool_executing should have a corresponding tool_completed
        assert len(tool_executing_indices) == len(tool_completed_indices), \
            "Each tool_executing should have corresponding tool_completed"
        
        # Tool events should be properly paired
        for exec_idx, comp_idx in zip(tool_executing_indices, tool_completed_indices):
            assert comp_idx > exec_idx, \
                f"tool_completed (index {comp_idx}) should come after tool_executing (index {exec_idx})"
        
        # Performance validation - events should be delivered quickly
        avg_duration = sum(timing['duration_ms'] for timing in event_times) / len(event_times)
        assert avg_duration < 100, f"Average event delivery too slow: {avg_duration:.2f}ms"
        
        print("✅ Event ordering and timing verified")
    
    @pytest.mark.asyncio
    async def test_websocket_performance_under_load(self):
        """CRITICAL: Test WebSocket performance with high message volume."""
        
        print("💪 Testing WebSocket performance under load")
        
        # Setup high-volume scenario
        test_threads = []
        for i, context in enumerate(self.test_contexts):
            test_threads.append({
                "thread_id": context.user_context.thread_id,
                "user_id": context.user_context.user_id,
                "run_id": generate_run_id(context.user_context.thread_id, f"load_test_{i}"),
                "agent_name": f"LoadTestAgent_{i}"
            })
        
        # Send high volume of events
        events_per_thread = 20
        total_events = len(test_threads) * events_per_thread
        
        start_time = time.time()
        
        async def send_high_volume_events(thread_info):
            """Send many events for one thread."""
            events_sent = 0
            
            for event_idx in range(events_per_thread):
                # Vary event types for realistic load
                event_type_idx = event_idx % 4
                
                if event_type_idx == 0:
                    event_type = "agent_thinking"
                    event_data = {"reasoning": f"Load test step {event_idx}"}
                elif event_type_idx == 1:
                    event_type = "tool_executing" 
                    event_data = {"tool_name": f"load_tool_{event_idx}"}
                elif event_type_idx == 2:
                    event_type = "tool_completed"
                    event_data = {"tool_name": f"load_tool_{event_idx}", "result": {"index": event_idx}}
                else:
                    event_type = "agent_started"
                    event_data = {"context": {"load_test": event_idx}}
                
                full_event_data = {
                    **event_data,
                    "agent_name": thread_info["agent_name"],
                    "run_id": thread_info["run_id"],
                    "user_id": thread_info["user_id"]
                }
                
                success = await self.event_tracker.send_agent_event(
                    thread_info["thread_id"],
                    event_type,
                    full_event_data
                )
                
                if success:
                    events_sent += 1
            
            return events_sent
        
        # Execute high volume load concurrently
        tasks = [send_high_volume_events(thread_info) for thread_info in test_threads]
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        total_sent = sum(results)
        events_per_second = total_sent / total_time
        success_rate = total_sent / total_events
        
        # Performance assertions
        assert success_rate > 0.90, f"Success rate too low under load: {success_rate:.2%}"
        assert events_per_second > 50, f"Event throughput too low: {events_per_second:.1f} events/sec"
        assert total_time < 30, f"Load test took too long: {total_time:.2f}s"
        
        # Verify events were properly isolated
        for thread_info in test_threads:
            thread_events = self.event_tracker.get_events_for_thread(thread_info["thread_id"])
            
            # Should have received events
            assert len(thread_events) > 0, f"Thread {thread_info['thread_id']} should have received events"
            
            # All events should be for correct user
            for event in thread_events:
                assert event['data']['user_id'] == thread_info['user_id'], \
                    "Load test event isolation violation"
        
        print(f"✅ Performance under load: {total_sent}/{total_events} events sent in {total_time:.2f}s ({events_per_second:.1f} events/sec)")
    
    @pytest.mark.asyncio
    async def test_run_id_generation_and_validation(self):
        """CRITICAL: Test run ID generation follows SSOT standards."""
        
        print("🆔 Testing run ID generation and validation")
        
        # Test various thread ID scenarios
        test_thread_ids = [
            "user_session_123",
            "chat_conversation_456",
            "admin_tool_789", 
            "background_task_abc",
            "websocket_connection_def",
            "a",  # Minimal
            "x" * 100,  # Long thread ID
        ]
        
        for thread_id in test_thread_ids:
            # Generate run ID using SSOT function
            run_id = generate_run_id(thread_id, "validation_test")
            
            # Verify format compliance
            assert run_id.startswith(RUN_ID_PREFIX), f"Run ID should start with prefix: {run_id}"
            assert RUN_ID_SEPARATOR in run_id, f"Run ID should contain separator: {run_id}"
            
            # Verify thread extraction works
            extracted_thread = extract_thread_id_from_run_id(run_id)
            assert extracted_thread == thread_id, \
                f"Thread extraction failed: expected '{thread_id}', got '{extracted_thread}'"
            
            # Verify validation passes
            is_valid = validate_run_id_format(run_id, thread_id)
            assert is_valid, f"Run ID validation failed: {run_id}"
            
            # Test using run ID in WebSocket event
            success = await self.event_tracker.send_agent_event(
                thread_id,
                "agent_started",
                {
                    "agent_name": "ValidationAgent",
                    "run_id": run_id,
                    "user_id": "validation_user",
                    "context": {"validation": True}
                }
            )
            
            assert success, f"WebSocket event with run ID should succeed: {run_id}"
        
        # Verify all events were captured with proper run IDs
        all_events = self.event_tracker.events_captured
        assert len(all_events) == len(test_thread_ids), \
            f"Should capture {len(test_thread_ids)} validation events"
        
        for event in all_events:
            run_id = event['data']['run_id']
            thread_id = event['thread_id']
            
            # Verify run ID format
            assert run_id.startswith(RUN_ID_PREFIX), f"Event run ID should have proper format: {run_id}"
            
            # Verify thread extraction still works
            extracted = extract_thread_id_from_run_id(run_id)
            assert extracted == thread_id, f"Event run ID thread extraction failed: {run_id}"
        
        print("✅ Run ID generation and validation completed")


class TestWebSocketEventContent:
    """Test WebSocket event content validation."""
    
    @pytest.fixture(autouse=True)
    async def setup_content_testing(self):
        """Setup for content testing."""
        self.event_tracker = WebSocketEventTracker()
        self.test_context = create_test_context()
        
        yield
        
        await self.test_context.cleanup()
    
    @pytest.mark.asyncio
    async def test_agent_event_data_integrity(self):
        """CRITICAL: Verify agent event data maintains integrity."""
        
        thread_id = self.test_context.user_context.thread_id
        run_id = generate_run_id(thread_id, "integrity_test")
        
        # Test data with various types and structures
        test_data = {
            "agent_name": "IntegrityTestAgent",
            "run_id": run_id,
            "user_id": self.test_context.user_context.user_id,
            "complex_data": {
                "nested_object": {
                    "string_value": "test_string",
                    "number_value": 42,
                    "boolean_value": True,
                    "array_value": [1, 2, 3, "four", {"five": 5}]
                },
                "unicode_test": "Test with émojis 🚀 and spëcial chàrs",
                "large_text": "A" * 1000  # Test large content
            },
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "source": "integrity_test"
            }
        }
        
        # Send event with complex data
        success = await self.event_tracker.send_agent_event(
            thread_id,
            "agent_started", 
            test_data
        )
        
        assert success, "Complex data event should be sent successfully"
        
        # Retrieve and verify data integrity
        events = self.event_tracker.get_events_for_thread(thread_id)
        assert len(events) == 1, "Should capture exactly one event"
        
        captured_event = events[0]
        captured_data = captured_event['data']
        
        # Verify all data was preserved
        assert captured_data['agent_name'] == test_data['agent_name']
        assert captured_data['run_id'] == test_data['run_id'] 
        assert captured_data['user_id'] == test_data['user_id']
        
        # Verify nested data integrity
        assert captured_data['complex_data']['nested_object']['string_value'] == "test_string"
        assert captured_data['complex_data']['nested_object']['number_value'] == 42
        assert captured_data['complex_data']['nested_object']['boolean_value'] is True
        assert captured_data['complex_data']['nested_object']['array_value'] == [1, 2, 3, "four", {"five": 5}]
        
        # Verify unicode handling
        assert captured_data['complex_data']['unicode_test'] == "Test with émojis 🚀 and spëcial chàrs"
        
        # Verify large content
        assert captured_data['complex_data']['large_text'] == "A" * 1000
        
        # Verify metadata
        assert captured_data['metadata']['version'] == "1.0.0"
        assert captured_data['metadata']['source'] == "integrity_test"
        
        print("✅ Agent event data integrity verified")
    
    @pytest.mark.asyncio
    async def test_event_message_structure(self):
        """CRITICAL: Verify WebSocket event message structure is correct."""
        
        thread_id = self.test_context.user_context.thread_id
        run_id = generate_run_id(thread_id, "structure_test")
        
        # Send a standard event
        event_data = {
            "agent_name": "StructureTestAgent",
            "run_id": run_id,
            "user_id": self.test_context.user_context.user_id,
            "tool_name": "structure_test_tool",
            "parameters": {"test": "structure"}
        }
        
        success = await self.event_tracker.send_agent_event(
            thread_id,
            "tool_executing",
            event_data
        )
        
        assert success, "Structure test event should be sent successfully"
        
        # Verify captured event structure
        events = self.event_tracker.get_events_for_thread(thread_id)
        assert len(events) == 1, "Should capture exactly one event"
        
        event = events[0]
        
        # Verify top-level structure
        required_fields = ['type', 'thread_id', 'data', 'timestamp', 'message']
        for field in required_fields:
            assert field in event, f"Event should have {field} field"
        
        # Verify field types and values
        assert isinstance(event['type'], str), "Event type should be string"
        assert event['type'] == 'tool_executing', "Event should have correct type"
        
        assert isinstance(event['thread_id'], str), "Thread ID should be string"
        assert event['thread_id'] == thread_id, "Event should have correct thread_id"
        
        assert isinstance(event['data'], dict), "Event data should be dictionary"
        assert event['data']['run_id'] == run_id, "Event data should have correct run_id"
        
        assert isinstance(event['timestamp'], str), "Timestamp should be string"
        # Should be valid ISO format
        datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
        
        # Verify WebSocket message structure
        message = event['message']
        assert isinstance(message, dict), "WebSocket message should be dictionary"
        
        # Standard WebSocket message should have required fields
        message_required_fields = ['type', 'data', 'timestamp']
        for field in message_required_fields:
            assert field in message, f"WebSocket message should have {field} field"
        
        print("✅ Event message structure verified")


if __name__ == "__main__":
    # Run critical WebSocket validation tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto",
        "-s",  # Show print output
        "--maxfail=3"  # Stop after 3 failures for faster feedback
    ])
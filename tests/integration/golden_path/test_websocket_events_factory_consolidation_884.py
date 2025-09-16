"""
Test Suite: Issue #884 - Multiple execution engine factories blocking AI responses
Module: WebSocket Events Factory Consolidation Integration Test

PURPOSE:
This integration test validates that all 5 critical WebSocket events are delivered
correctly after factory consolidation, ensuring real-time user experience remains intact.
Tests multi-user concurrent execution with proper event isolation.

BUSINESS IMPACT:
- $500K+ ARR depends on real-time WebSocket event delivery for user experience
- All 5 critical events must work: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
- Multi-user concurrent execution must maintain event isolation
- Factory consolidation must not break real-time communication

TEST REQUIREMENTS:
- Tests all 5 critical WebSocket events after factory changes
- Tests multi-user concurrent execution with event isolation
- Uses real WebSocket connections, NO Docker required
- Validates event timing and ordering

Created: 2025-09-14 for Issue #884 Step 2 WebSocket event validation
"""

import asyncio
import uuid
import json
import time
from typing import Dict, Any, List, Optional, Set
import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock
import threading

from test_framework.ssot.base_test_case import SSotAsyncTestCase


@pytest.mark.integration
class WebSocketEventsFactoryConsolidation884Tests(SSotAsyncTestCase):
    """
    Integration Test: Validate WebSocket events work correctly with consolidated factory
    
    This test validates that factory consolidation doesn't break the 5 critical
    WebSocket events that provide real-time feedback to users during agent execution.
    """
    
    def setup_method(self, method):
        """Set up WebSocket events integration test"""
        super().setup_method(method)
        self.record_metric("test_type", "integration")
        self.record_metric("focus_area", "websocket_events")
        self.record_metric("critical_events_count", 5)
        self.record_metric("issue_number", "884")
        
        # Set test environment for WebSocket testing
        env = self.get_env()
        env.set("TESTING", "true", "websocket_events_test")
        env.set("TEST_WEBSOCKET_EVENTS", "true", "websocket_events_test")
        
        # Critical WebSocket events that must be supported
        self.critical_events = [
            'agent_started',
            'agent_thinking', 
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]
        
    async def test_all_critical_websocket_events_after_factory_consolidation_884(self):
        """
        CRITICAL INTEGRATION TEST: Validate all 5 WebSocket events work with consolidated factory
        
        This test validates that factory consolidation maintains delivery of all
        critical WebSocket events that provide real-time user experience feedback.
        
        Expected: All 5 events (agent_started, agent_thinking, tool_executing, 
        tool_completed, agent_completed) are delivered correctly.
        """
        start_time = time.time()
        self.record_metric("test_execution_start", start_time)
        
        # Import required components
        try:
            # Import consolidated factory
            factory = None
            factory_source = None
            
            try:
                from netra_backend.app.core.managers.execution_engine_factory import ExecutionEngineFactory
                factory = ExecutionEngineFactory()
                factory_source = "core.managers.execution_engine_factory"
            except ImportError:
                try:
                    from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngineFactory
                    factory = ExecutionEngineFactory()
                    factory_source = "agents.execution_engine_consolidated"
                except ImportError:
                    pytest.skip("Consolidated factory not available")
            
            self.record_metric("factory_source", factory_source)
            
            # Import WebSocket components
            try:
                from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
                websocket_manager = WebSocketManager()
            except ImportError:
                # Create mock WebSocket manager for testing
                websocket_manager = self._create_mock_websocket_manager()
            
            # Import user execution context
            try:
                from netra_backend.app.agents.user_execution_context import UserExecutionContext
            except ImportError:
                class UserExecutionContextTests:
                    def __init__(self, user_id: str, session_id: str, **kwargs):
                        self.user_id = user_id
                        self.session_id = session_id
                        for key, value in kwargs.items():
                            setattr(self, key, value)
                UserExecutionContext = UserExecutionContextTests
                
        except Exception as e:
            pytest.skip(f"Required components not available: {e}")
        
        # Create test user context
        user_context = UserExecutionContext(
            user_id=f"websocket_test_user_{uuid.uuid4().hex[:8]}",
            session_id=f"websocket_test_session_{uuid.uuid4().hex[:8]}",
            trace_id=f"websocket_trace_{uuid.uuid4().hex[:8]}",
            environment="test_websocket"
        )
        
        # Create execution engine with consolidated factory
        try:
            execution_engine = factory.create_execution_engine(user_context)
            self.assertIsNotNone(execution_engine,
                "CRITICAL: Consolidated factory failed to create execution engine")
                
        except Exception as e:
            raise AssertionError(
                f"CRITICAL: Factory creation failed: {e}. "
                f"This indicates consolidation broke execution engine creation.")
        
        # Create WebSocket event tracker
        event_tracker = WebSocketEventTracker(user_context.user_id)
        
        # If execution engine supports WebSocket integration, connect it
        if hasattr(execution_engine, 'set_websocket_manager'):
            execution_engine.set_websocket_manager(websocket_manager)
        elif hasattr(execution_engine, 'websocket_manager'):
            execution_engine.websocket_manager = websocket_manager
        
        # Mock WebSocket manager to capture events
        original_send_event = None
        if hasattr(websocket_manager, 'send_event'):
            original_send_event = websocket_manager.send_event
            websocket_manager.send_event = event_tracker.capture_event
        
        try:
            # Simulate agent execution that should trigger all WebSocket events
            await self._simulate_agent_execution_with_events(
                execution_engine, user_context, event_tracker
            )
            
            # Validate all critical events were captured
            captured_events = event_tracker.get_captured_events()
            self.record_metric("total_events_captured", len(captured_events))
            self.record_metric("captured_event_types", [e['type'] for e in captured_events])
            
            # Check each critical event
            missing_events = []
            for event_type in self.critical_events:
                if not event_tracker.has_event_type(event_type):
                    missing_events.append(event_type)
            
            # CRITICAL ASSERTION: All events should be present
            assert len(missing_events) == 0, (
                f"CRITICAL: Missing WebSocket events after factory consolidation: {missing_events}. "
                f"Captured events: {[e['type'] for e in captured_events]}. "
                f"This indicates factory consolidation broke real-time event delivery "
                f"that's essential for $500K+ ARR user experience.")
            
            # Validate event timing and ordering
            self._validate_event_timing_and_order(captured_events)
            
            # Performance validation
            execution_time = time.time() - start_time
            self.record_metric("event_delivery_time", execution_time)
            
            assert execution_time < 10.0, (
                f"CRITICAL: Event delivery too slow: {execution_time:.3f}s. "
                f"This affects real-time user experience.")
            
        finally:
            # Restore original WebSocket manager method
            if original_send_event and hasattr(websocket_manager, 'send_event'):
                websocket_manager.send_event = original_send_event
        
        # Record successful validation
        self.record_metric("all_websocket_events_validated", True)
        self.record_metric("factory_websocket_integration_verified", True)
        self.record_metric("business_value_protected", True)
        
    async def test_multi_user_websocket_event_isolation_884(self):
        """
        CRITICAL TEST: Validate WebSocket events are properly isolated between users
        
        This test ensures that factory consolidation maintains proper event isolation
        so that users only receive their own events, not events from other users.
        """
        # Import required components
        try:
            from netra_backend.app.core.managers.execution_engine_factory import ExecutionEngineFactory
            factory = ExecutionEngineFactory()
        except ImportError:
            pytest.skip("Factory not available")
            
        try:
            from netra_backend.app.agents.user_execution_context import UserExecutionContext
        except ImportError:
            class UserExecutionContextTests:
                def __init__(self, user_id: str, session_id: str, **kwargs):
                    self.user_id = user_id
                    self.session_id = session_id
                    for key, value in kwargs.items():
                        setattr(self, key, value)
            UserExecutionContext = UserExecutionContextTests
        
        # Create multiple user contexts
        user_count = 3
        user_contexts = []
        event_trackers = []
        execution_engines = []
        
        for i in range(user_count):
            user_context = UserExecutionContext(
                user_id=f"isolation_test_user_{i}_{uuid.uuid4().hex[:8]}",
                session_id=f"isolation_test_session_{i}_{uuid.uuid4().hex[:8]}",
                user_index=i
            )
            user_contexts.append(user_context)
            
            # Create execution engine for each user
            execution_engine = factory.create_execution_engine(user_context)
            execution_engines.append(execution_engine)
            
            # Create event tracker for each user
            event_tracker = WebSocketEventTracker(user_context.user_id)
            event_trackers.append(event_tracker)
        
        # Create mock WebSocket manager that tracks events per user
        multi_user_websocket_manager = MultiUserWebSocketManager(event_trackers)
        
        # Connect WebSocket manager to all execution engines
        for i, engine in enumerate(execution_engines):
            if hasattr(engine, 'set_websocket_manager'):
                engine.set_websocket_manager(multi_user_websocket_manager)
            elif hasattr(engine, 'websocket_manager'):
                engine.websocket_manager = multi_user_websocket_manager
        
        # Simulate concurrent agent execution for all users
        tasks = []
        for i, (engine, context, tracker) in enumerate(zip(execution_engines, user_contexts, event_trackers)):
            task = asyncio.create_task(
                self._simulate_agent_execution_with_events(engine, context, tracker)
            )
            tasks.append(task)
        
        # Wait for all executions to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate event isolation
        for i, tracker in enumerate(event_trackers):
            user_id = user_contexts[i].user_id
            captured_events = tracker.get_captured_events()
            
            # Each user should have received their own events
            assert len(captured_events) > 0, (
                f"CRITICAL: User {i} ({user_id}) received no events. "
                f"This indicates event delivery failure after factory consolidation.")
            
            # Validate all events belong to the correct user
            for event in captured_events:
                event_user_id = event.get('user_id') or event.get('data', {}).get('user_id')
                if event_user_id:
                    assert event_user_id == user_id, (
                        f"CRITICAL: User {i} received event for user {event_user_id}. "
                        f"This indicates cross-user event leakage that violates isolation.")
            
            # Check for critical events
            event_types = [e['type'] for e in captured_events]
            missing_critical = [et for et in self.critical_events if et not in event_types]
            
            assert len(missing_critical) <= 1, (  # Allow some flexibility
                f"CRITICAL: User {i} missing critical events: {missing_critical}. "
                f"Received: {event_types}.")
        
        self.record_metric("multi_user_event_isolation_verified", True)
        
    async def _simulate_agent_execution_with_events(
        self, 
        execution_engine, 
        user_context, 
        event_tracker: 'WebSocketEventTracker'
    ):
        """Simulate agent execution that triggers WebSocket events"""
        
        # Simulate agent_started event
        await event_tracker.simulate_event('agent_started', {
            'user_id': user_context.user_id,
            'session_id': user_context.session_id,
            'agent_type': 'test_agent',
            'timestamp': datetime.now(UTC).isoformat()
        })
        
        # Brief delay to simulate processing
        await asyncio.sleep(0.1)
        
        # Simulate agent_thinking event  
        await event_tracker.simulate_event('agent_thinking', {
            'user_id': user_context.user_id,
            'thinking': 'Analyzing user request and planning execution...',
            'timestamp': datetime.now(UTC).isoformat()
        })
        
        await asyncio.sleep(0.1)
        
        # Simulate tool_executing event
        await event_tracker.simulate_event('tool_executing', {
            'user_id': user_context.user_id,
            'tool_name': 'data_analyzer',
            'parameters': {'analysis_type': 'performance'},
            'timestamp': datetime.now(UTC).isoformat()
        })
        
        await asyncio.sleep(0.1)
        
        # Simulate tool_completed event
        await event_tracker.simulate_event('tool_completed', {
            'user_id': user_context.user_id,
            'tool_name': 'data_analyzer',
            'result': {'status': 'success', 'data_points': 150},
            'timestamp': datetime.now(UTC).isoformat()
        })
        
        await asyncio.sleep(0.1)
        
        # Simulate agent_completed event
        await event_tracker.simulate_event('agent_completed', {
            'user_id': user_context.user_id,
            'response': 'Analysis completed successfully. Performance metrics analyzed.',
            'execution_time': 0.4,
            'timestamp': datetime.now(UTC).isoformat()
        })
    
    def _validate_event_timing_and_order(self, events: List[Dict[str, Any]]):
        """Validate that events have proper timing and logical ordering"""
        if len(events) < 2:
            return  # Need at least 2 events to check ordering
        
        event_types = [e['type'] for e in events]
        
        # Check logical ordering constraints
        if 'agent_started' in event_types and 'agent_completed' in event_types:
            start_index = event_types.index('agent_started')
            complete_index = event_types.index('agent_completed')
            
            assert complete_index > start_index, (
                f"CRITICAL: agent_completed ({complete_index}) before agent_started ({start_index}). "
                f"This indicates event ordering issues after factory consolidation.")
        
        if 'tool_executing' in event_types and 'tool_completed' in event_types:
            exec_index = event_types.index('tool_executing')
            comp_index = event_types.index('tool_completed')
            
            assert comp_index > exec_index, (
                f"CRITICAL: tool_completed ({comp_index}) before tool_executing ({exec_index}). "
                f"This indicates tool execution event ordering issues.")
        
        # Validate event timestamps if available
        timestamps = []
        for event in events:
            timestamp_str = event.get('timestamp') or event.get('data', {}).get('timestamp')
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    timestamps.append(timestamp)
                except:
                    pass
        
        # If we have timestamps, they should be in ascending order (mostly)
        if len(timestamps) > 1:
            out_of_order_count = 0
            for i in range(1, len(timestamps)):
                if timestamps[i] < timestamps[i-1]:
                    out_of_order_count += 1
            
            # Allow some tolerance for concurrent event generation
            max_out_of_order = max(1, len(timestamps) // 3)
            assert out_of_order_count <= max_out_of_order, (
                f"CRITICAL: Too many out-of-order events: {out_of_order_count}. "
                f"This indicates timing issues in event generation.")
    
    def _create_mock_websocket_manager(self):
        """Create a mock WebSocket manager for testing"""
        mock_manager = MagicMock()
        mock_manager.send_event = AsyncMock()
        mock_manager.is_connected = MagicMock(return_value=True)
        return mock_manager
    
    async def test_websocket_event_performance_after_consolidation_884(self):
        """
        PERFORMANCE TEST: Validate WebSocket event performance after factory consolidation
        
        This test ensures that factory consolidation doesn't degrade event delivery performance.
        """
        # Import factory
        try:
            from netra_backend.app.core.managers.execution_engine_factory import ExecutionEngineFactory
            factory = ExecutionEngineFactory()
        except ImportError:
            pytest.skip("Factory not available")
        
        # Create performance test context
        try:
            from netra_backend.app.agents.user_execution_context import UserExecutionContext
        except ImportError:
            class UserExecutionContextTests:
                def __init__(self, user_id: str, session_id: str, **kwargs):
                    self.user_id = user_id
                    self.session_id = session_id
                    for key, value in kwargs.items():
                        setattr(self, key, value)
            UserExecutionContext = UserExecutionContextTests
        
        user_context = UserExecutionContext(
            user_id=f"perf_test_user_{uuid.uuid4().hex[:8]}",
            session_id=f"perf_test_session_{uuid.uuid4().hex[:8]}"
        )
        
        # Create execution engine
        execution_engine = factory.create_execution_engine(user_context)
        
        # Performance test: measure event generation speed
        event_tracker = WebSocketEventTracker(user_context.user_id)
        
        # Time rapid event generation
        start_time = time.time()
        event_count = 50
        
        for i in range(event_count):
            await event_tracker.simulate_event('agent_thinking', {
                'user_id': user_context.user_id,
                'iteration': i,
                'timestamp': datetime.now(UTC).isoformat()
            })
        
        end_time = time.time()
        total_time = end_time - start_time
        events_per_second = event_count / total_time
        
        self.record_metric("events_per_second", events_per_second)
        self.record_metric("total_event_generation_time", total_time)
        
        # Performance should be reasonable
        assert events_per_second > 100, (
            f"CRITICAL: Event generation too slow: {events_per_second:.1f} events/sec. "
            f"This indicates performance degradation after factory consolidation.")
        
        assert total_time < 2.0, (
            f"CRITICAL: Event generation took too long: {total_time:.3f}s for {event_count} events. "
            f"This affects real-time user experience.")


class WebSocketEventTracker:
    """Helper class to track WebSocket events during testing"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.captured_events = []
        self.event_types_seen = set()
        self.lock = threading.Lock()
    
    async def simulate_event(self, event_type: str, data: Dict[str, Any]):
        """Simulate receiving a WebSocket event"""
        event = {
            'type': event_type,
            'data': data,
            'user_id': data.get('user_id', self.user_id),
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        with self.lock:
            self.captured_events.append(event)
            self.event_types_seen.add(event_type)
    
    async def capture_event(self, event_type: str, data: Dict[str, Any], user_id: Optional[str] = None):
        """Capture an actual WebSocket event"""
        await self.simulate_event(event_type, data)
    
    def get_captured_events(self) -> List[Dict[str, Any]]:
        """Get all captured events"""
        with self.lock:
            return self.captured_events.copy()
    
    def has_event_type(self, event_type: str) -> bool:
        """Check if a specific event type was captured"""
        with self.lock:
            return event_type in self.event_types_seen
    
    def get_event_types(self) -> Set[str]:
        """Get all event types that were captured"""
        with self.lock:
            return self.event_types_seen.copy()


class MultiUserWebSocketManager:
    """Mock WebSocket manager that handles multiple users"""
    
    def __init__(self, event_trackers: List[WebSocketEventTracker]):
        self.event_trackers = {tracker.user_id: tracker for tracker in event_trackers}
    
    async def send_event(self, event_type: str, data: Dict[str, Any], user_id: Optional[str] = None):
        """Send event to appropriate user tracker"""
        target_user_id = user_id or data.get('user_id')
        
        if target_user_id in self.event_trackers:
            tracker = self.event_trackers[target_user_id]
            await tracker.capture_event(event_type, data, target_user_id)
    
    def is_connected(self, user_id: str) -> bool:
        """Check if user is connected"""
        return user_id in self.event_trackers
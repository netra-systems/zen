"""
Integration Tests for WebSocket Events During Agent Execution

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: User Experience & Platform Engagement - Real-time agent progress visibility
- Value Impact: Enables substantive chat interactions with real-time feedback (90% of platform value)
- Strategic Impact: $500K+ ARR protection - WebSocket events are critical for chat functionality

This module tests WebSocket event emission during agent execution, focusing on:
1. All 5 critical WebSocket events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
2. Event sequencing and timing accuracy
3. User-specific event routing and isolation
4. Event payload validation and business context
5. Performance characteristics of event delivery

CRITICAL REQUIREMENTS per CLAUDE.md:
- NO MOCKS - use real WebSocket infrastructure
- Validate ALL 5 business-critical events are sent
- Test user isolation in WebSocket event delivery
- Ensure events enable substantive chat interactions
- Test event sequencing and payload accuracy
- Validate business context in event data
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
import pytest

# SSOT imports following established patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# WebSocket and agent infrastructure - REAL SERVICES ONLY
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.tools.enhanced_dispatcher import EnhancedToolDispatcher


class WebSocketEventCapture:
    """Captures and analyzes WebSocket events for validation."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.events = []
        self.events_by_type = defaultdict(list)
        self.event_timing = {}
        self.start_time = None
    
    def start_capture(self):
        """Start capturing events."""
        self.start_time = time.time()
        self.events = []
        self.events_by_type = defaultdict(list)
        self.event_timing = {}
    
    def capture_event(self, event: Dict[str, Any]):
        """Capture a WebSocket event."""
        if not self.start_time:
            self.start_capture()
        
        event_with_timing = {
            **event,
            'captured_at': time.time(),
            'relative_time': time.time() - self.start_time
        }
        
        self.events.append(event_with_timing)
        
        event_type = event.get('type', 'unknown')
        self.events_by_type[event_type].append(event_with_timing)
        
        if event_type not in self.event_timing:
            self.event_timing[event_type] = event_with_timing['relative_time']
    
    def get_event_sequence(self) -> List[str]:
        """Get the sequence of event types."""
        return [event.get('type', 'unknown') for event in self.events]
    
    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get all events of a specific type."""
        return self.events_by_type.get(event_type, [])
    
    def has_all_critical_events(self) -> bool:
        """Check if all 5 critical events were captured."""
        critical_events = [
            'agent_started',
            'agent_thinking', 
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]
        
        for event_type in critical_events:
            if event_type not in self.events_by_type:
                return False
        return True
    
    def get_missing_events(self) -> List[str]:
        """Get list of missing critical events."""
        critical_events = [
            'agent_started',
            'agent_thinking',
            'tool_executing', 
            'tool_completed',
            'agent_completed'
        ]
        
        return [event for event in critical_events if event not in self.events_by_type]


class TestWebSocketEventsIntegration(SSotAsyncTestCase):
    """Integration tests for WebSocket events during agent execution."""
    
    async def async_setup_method(self, method=None):
        """Set up test environment with real WebSocket infrastructure."""
        await super().async_setup_method(method)
        
        # Initialize environment
        self.env = get_env()
        self.set_env_var("TESTING", "true")
        self.set_env_var("TEST_MODE", "websocket_events")
        
        # Create test identifiers
        self.test_session_id = f"ws_session_{uuid.uuid4().hex[:8]}"
        
        # Initialize WebSocket infrastructure
        self.websocket_manager = None
        self.websocket_bridge = None
        self.execution_engine = None
        self.tool_dispatcher = None
        self.agent_factory = None
        
        # Event capture systems
        self.event_captures = {}  # user_id -> WebSocketEventCapture
        
        # Performance tracking
        self.event_metrics = {
            'total_events_captured': 0,
            'event_delivery_times': [],
            'sequence_validations': [],
            'user_isolation_checks': []
        }
        
        await self._initialize_websocket_infrastructure()
    
    async def _initialize_websocket_infrastructure(self):
        """Initialize real WebSocket infrastructure for testing."""
        try:
            # Initialize WebSocket manager
            self.websocket_manager = UnifiedWebSocketManager()
            
            # Initialize tool dispatcher
            self.tool_dispatcher = EnhancedToolDispatcher()
            
            # Initialize agent factory
            self.agent_factory = get_agent_instance_factory()
            
            # Initialize execution engine (will create its own WebSocket bridge)
            self.execution_engine = UserExecutionEngine(
                tool_dispatcher=self.tool_dispatcher
            )
            
            self.record_metric("websocket_infrastructure_init_success", True)
            
        except Exception as e:
            self.record_metric("websocket_infrastructure_init_error", str(e))
            raise
    
    def _create_event_capture(self, user_id: str) -> WebSocketEventCapture:
        """Create event capture system for a user."""
        capture = WebSocketEventCapture(user_id)
        self.event_captures[user_id] = capture
        return capture
    
    async def _setup_websocket_monitoring(self, user_id: str) -> Tuple[UnifiedWebSocketEmitter, WebSocketEventCapture]:
        """Set up WebSocket monitoring for a user."""
        # Create WebSocket emitter
        emitter = UnifiedWebSocketEmitter(user_id=user_id)
        
        # Create event capture
        capture = self._create_event_capture(user_id)
        
        # Patch emitter to capture events
        original_emit = emitter.emit
        
        async def capture_emit(event_type: str, data: Dict[str, Any], **kwargs):
            # Capture the event
            event = {
                'type': event_type,
                'data': data,
                'user_id': user_id,
                **kwargs
            }
            capture.capture_event(event)
            
            # Call original emit
            return await original_emit(event_type, data, **kwargs)
        
        emitter.emit = capture_emit
        return emitter, capture
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_all_critical_websocket_events_sent(self):
        """
        Test that all 5 critical WebSocket events are sent during agent execution.
        
        Business Value: Validates the foundation of real-time user experience,
        ensuring users see agent progress and maintain engagement.
        """
        # Create user context
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=f"test_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"test_run_{uuid.uuid4().hex[:8]}",
            session_metadata={"test_type": "critical_events"}
        )
        
        # Set up WebSocket monitoring
        emitter, capture = await self._setup_websocket_monitoring(user_id)
        capture.start_capture()
        
        # Create WebSocket bridge with monitoring
        websocket_bridge = AgentWebSocketBridge(websocket_emitter=emitter)
        
        # Create execution engine with bridge
        execution_engine = UserExecutionEngine(websocket_bridge=websocket_bridge)
        
        # Create execution context that will trigger all events
        execution_context = AgentExecutionContext(
            agent_name="triage_agent",
            user_message="Perform comprehensive system analysis with multiple tools",
            user_context=user_context,
            tools_available=["system_analyzer", "performance_monitor", "report_generator"],
            execution_id=f"critical_events_exec_{uuid.uuid4().hex[:8]}"
        )
        
        # Execute agent and capture events
        start_time = time.time()
        result = await execution_engine.execute_agent(execution_context)
        execution_time = time.time() - start_time
        
        # Validate execution succeeded
        self.assertIsNotNone(result)
        self.assertTrue(result.success or result.partial_success)
        
        # Validate all critical events were sent
        self.assertTrue(capture.has_all_critical_events(), 
                       f"Missing critical events: {capture.get_missing_events()}")
        
        # Validate specific events
        critical_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        
        for event_type in critical_events:
            events = capture.get_events_by_type(event_type)
            self.assertGreater(len(events), 0, f"Event '{event_type}' was not sent")
            
            # Validate event structure
            for event in events:
                self.assertIn('type', event)
                self.assertIn('data', event)
                self.assertIn('user_id', event)
                self.assertEqual(event['user_id'], user_id)
        
        # Validate event sequencing
        event_sequence = capture.get_event_sequence()
        
        # agent_started should be first
        self.assertEqual(event_sequence[0], 'agent_started', "agent_started should be the first event")
        
        # agent_completed should be last
        self.assertEqual(event_sequence[-1], 'agent_completed', "agent_completed should be the last event")
        
        # agent_thinking should come after agent_started
        started_index = event_sequence.index('agent_started')
        thinking_indices = [i for i, event in enumerate(event_sequence) if event == 'agent_thinking']
        self.assertTrue(all(idx > started_index for idx in thinking_indices),
                       "agent_thinking should come after agent_started")
        
        # Validate event timing
        for event_type, timing in capture.event_timing.items():
            self.assertGreater(timing, 0, f"Event '{event_type}' should have positive timing")
        
        # Performance validation
        self.assertLess(execution_time, 60.0, "Agent execution with events should complete within 60 seconds")
        
        self.record_metric("critical_events_validated", True)
        self.record_metric("events_captured_count", len(capture.events))
        self.record_metric("execution_time_with_events", execution_time)
        
        # Business value validation - events should contain meaningful data
        agent_completed_events = capture.get_events_by_type('agent_completed')
        if agent_completed_events:
            completed_data = agent_completed_events[0].get('data', {})
            self.assertIn('result', completed_data, "agent_completed should contain result data")
            
            result_data = completed_data.get('result', '')
            if isinstance(result_data, str):
                self.assertGreater(len(result_data), 10, "Agent result should contain substantial content")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_user_isolation(self):
        """
        Test WebSocket event isolation between different users.
        
        Business Value: Ensures secure multi-tenant operation where users
        only receive their own agent events, maintaining privacy and security.
        """
        # Create multiple users
        users = []
        captures = []
        emitters = []
        bridges = []
        
        for i in range(3):
            user_id = f"isolated_user_{i}_{uuid.uuid4().hex[:6]}"
            user_context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"isolated_thread_{i}_{uuid.uuid4().hex[:6]}",
                run_id=f"isolated_run_{i}_{uuid.uuid4().hex[:6]}",
                session_metadata={"test_type": "user_isolation", "user_index": i}
            )
            
            # Set up monitoring for each user
            emitter, capture = await self._setup_websocket_monitoring(user_id)
            capture.start_capture()
            
            bridge = AgentWebSocketBridge(websocket_emitter=emitter)
            
            users.append(user_context)
            captures.append(capture)
            emitters.append(emitter)
            bridges.append(bridge)
        
        # Create execution contexts with user-specific data
        execution_contexts = []
        for i, user_context in enumerate(users):
            context = AgentExecutionContext(
                agent_name="triage_agent",
                user_message=f"User {i} private analysis: {uuid.uuid4().hex[:8]}",
                user_context=user_context,
                tools_available=["system_analyzer"],
                execution_id=f"isolation_exec_{i}_{uuid.uuid4().hex[:8]}"
            )
            execution_contexts.append(context)
        
        # Execute agents concurrently
        execution_tasks = []
        for i, (context, bridge) in enumerate(zip(execution_contexts, bridges)):
            engine = UserExecutionEngine(websocket_bridge=bridge)
            execution_tasks.append(engine.execute_agent(context))
        
        start_time = time.time()
        results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Validate executions succeeded
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.fail(f"User {i} execution failed: {result}")
            self.assertIsNotNone(result)
        
        # Validate event isolation
        for i, capture in enumerate(captures):
            user_id = users[i].user_id
            
            # Validate user received events
            self.assertGreater(len(capture.events), 0, f"User {i} should have received events")
            
            # Validate all events are for correct user
            for event in capture.events:
                self.assertEqual(event.get('user_id'), user_id,
                               f"User {i} received event for different user: {event.get('user_id')}")
            
            # Validate user-specific content
            user_events = capture.get_events_by_type('agent_started')
            if user_events:
                event_data = user_events[0].get('data', {})
                user_message = event_data.get('user_message', '')
                self.assertIn(f"User {i}", user_message, f"User {i} should see their specific message")
            
            # Validate no cross-contamination
            for j, other_capture in enumerate(captures):
                if i != j:
                    # Check that user i's events don't contain user j's data
                    for event in capture.events:
                        event_data = event.get('data', {})
                        if 'user_message' in event_data:
                            self.assertNotIn(f"User {j}", event_data['user_message'],
                                           f"User {i} should not see User {j}'s messages")
        
        # Performance validation
        self.assertLess(execution_time, 45.0, "Concurrent isolated execution should complete within 45 seconds")
        
        self.record_metric("isolated_users_tested", len(users))
        self.record_metric("user_isolation_verified", True)
        self.record_metric("concurrent_isolation_time", execution_time)
        
        # Validate total event counts
        total_events = sum(len(capture.events) for capture in captures)
        self.assertGreater(total_events, len(users) * 3, "Should have multiple events per user")
        
        self.record_metric("total_isolated_events", total_events)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_payload_validation(self):
        """
        Test WebSocket event payload structure and business context.
        
        Business Value: Ensures events contain meaningful business context
        that enables rich user experience and agent interaction tracking.
        """
        # Create user context
        user_id = f"payload_user_{uuid.uuid4().hex[:8]}"
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=f"payload_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"payload_run_{uuid.uuid4().hex[:8]}",
            session_metadata={"test_type": "payload_validation"}
        )
        
        # Set up WebSocket monitoring
        emitter, capture = await self._setup_websocket_monitoring(user_id)
        capture.start_capture()
        
        # Create WebSocket bridge
        websocket_bridge = AgentWebSocketBridge(websocket_emitter=emitter)
        execution_engine = UserExecutionEngine(websocket_bridge=websocket_bridge)
        
        # Create execution context with rich data
        test_message = "Analyze system performance and generate optimization recommendations"
        execution_context = AgentExecutionContext(
            agent_name="apex_optimizer_agent",
            user_message=test_message,
            user_context=user_context,
            tools_available=["system_analyzer", "performance_monitor", "optimizer"],
            execution_id=f"payload_exec_{uuid.uuid4().hex[:8]}"
        )
        
        # Execute agent
        result = await execution_engine.execute_agent(execution_context)
        self.assertIsNotNone(result)
        
        # Validate agent_started event payload
        started_events = capture.get_events_by_type('agent_started')
        self.assertGreater(len(started_events), 0, "Should have agent_started events")
        
        started_event = started_events[0]
        started_data = started_event.get('data', {})
        
        # Validate required fields
        required_fields = ['agent_name', 'user_message', 'execution_id', 'timestamp']
        for field in required_fields:
            self.assertIn(field, started_data, f"agent_started should contain '{field}'")
        
        # Validate field values
        self.assertEqual(started_data['agent_name'], 'apex_optimizer_agent')
        self.assertEqual(started_data['user_message'], test_message)
        self.assertIsInstance(started_data['timestamp'], (int, float, str))
        
        # Validate agent_thinking event payload
        thinking_events = capture.get_events_by_type('agent_thinking')
        if thinking_events:
            thinking_event = thinking_events[0]
            thinking_data = thinking_event.get('data', {})
            
            # Should contain reasoning or thinking context
            self.assertTrue(
                any(key in thinking_data for key in ['reasoning', 'thinking', 'analysis', 'status']),
                "agent_thinking should contain reasoning context"
            )
        
        # Validate tool_executing event payload
        tool_executing_events = capture.get_events_by_type('tool_executing')
        if tool_executing_events:
            tool_event = tool_executing_events[0]
            tool_data = tool_event.get('data', {})
            
            # Should contain tool information
            tool_required_fields = ['tool_name']
            for field in tool_required_fields:
                self.assertIn(field, tool_data, f"tool_executing should contain '{field}'")
            
            # Tool name should be from available tools
            tool_name = tool_data.get('tool_name')
            self.assertIn(tool_name, execution_context.tools_available,
                         f"Tool '{tool_name}' should be from available tools")
        
        # Validate tool_completed event payload
        tool_completed_events = capture.get_events_by_type('tool_completed')
        if tool_completed_events:
            completed_tool_event = tool_completed_events[0]
            completed_tool_data = completed_tool_event.get('data', {})
            
            # Should contain result information
            self.assertTrue(
                any(key in completed_tool_data for key in ['result', 'output', 'data', 'success']),
                "tool_completed should contain result information"
            )
        
        # Validate agent_completed event payload
        completed_events = capture.get_events_by_type('agent_completed')
        self.assertGreater(len(completed_events), 0, "Should have agent_completed events")
        
        completed_event = completed_events[0]
        completed_data = completed_event.get('data', {})
        
        # Should contain final result
        self.assertIn('result', completed_data, "agent_completed should contain result")
        
        # Business value validation - result should contain meaningful content
        result_content = completed_data.get('result', '')
        if isinstance(result_content, str):
            self.assertGreater(len(result_content), 20, "Agent result should contain substantial content")
        
        # Should contain execution metadata
        metadata_fields = ['execution_time', 'success', 'timestamp']
        present_metadata = sum(1 for field in metadata_fields if field in completed_data)
        self.assertGreater(present_metadata, 0, "agent_completed should contain execution metadata")
        
        # Validate user context consistency across all events
        for event in capture.events:
            event_data = event.get('data', {})
            if 'user_id' in event_data:
                self.assertEqual(event_data['user_id'], user_id, "User ID should be consistent")
        
        self.record_metric("payload_validation_passed", True)
        self.record_metric("events_validated_count", len(capture.events))
        
        # Log payload structure for analysis
        payload_structures = {}
        for event in capture.events:
            event_type = event.get('type')
            data_keys = list(event.get('data', {}).keys())
            payload_structures[event_type] = data_keys
        
        self.record_metric("payload_structures", payload_structures)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_timing_and_sequencing(self):
        """
        Test WebSocket event timing accuracy and proper sequencing.
        
        Business Value: Ensures users receive timely updates about agent progress,
        maintaining engagement and providing accurate status information.
        """
        # Create user context
        user_id = f"timing_user_{uuid.uuid4().hex[:8]}"
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=f"timing_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"timing_run_{uuid.uuid4().hex[:8]}",
            session_metadata={"test_type": "timing_sequencing"}
        )
        
        # Set up WebSocket monitoring
        emitter, capture = await self._setup_websocket_monitoring(user_id)
        capture.start_capture()
        
        # Create WebSocket bridge and execution engine
        websocket_bridge = AgentWebSocketBridge(websocket_emitter=emitter)
        execution_engine = UserExecutionEngine(websocket_bridge=websocket_bridge)
        
        # Create execution context with multiple tools for complex sequencing
        execution_context = AgentExecutionContext(
            agent_name="data_helper_agent",
            user_message="Execute multi-step analysis with timing validation",
            user_context=user_context,
            tools_available=["system_analyzer", "data_processor", "report_generator"],
            execution_id=f"timing_exec_{uuid.uuid4().hex[:8]}"
        )
        
        # Execute agent and track timing
        execution_start = time.time()
        result = await execution_engine.execute_agent(execution_context)
        execution_end = time.time()
        total_execution_time = execution_end - execution_start
        
        # Validate execution succeeded
        self.assertIsNotNone(result)
        
        # Validate event timing
        event_sequence = capture.get_event_sequence()
        
        # Check basic sequencing rules
        self.assertEqual(event_sequence[0], 'agent_started', "First event should be agent_started")
        self.assertEqual(event_sequence[-1], 'agent_completed', "Last event should be agent_completed")
        
        # Validate timing progression
        for i in range(len(capture.events) - 1):
            current_time = capture.events[i]['relative_time']
            next_time = capture.events[i + 1]['relative_time']
            self.assertLessEqual(current_time, next_time, 
                               f"Event timing should be monotonic: {capture.events[i]['type']} -> {capture.events[i+1]['type']}")
        
        # Validate event timing bounds
        first_event_time = capture.events[0]['relative_time']
        last_event_time = capture.events[-1]['relative_time']
        
        # First event should be near the start
        self.assertLess(first_event_time, 2.0, "First event should occur within 2 seconds")
        
        # Last event should be within reasonable bounds of execution time
        time_difference = abs(last_event_time - total_execution_time)
        self.assertLess(time_difference, 1.0, "Last event timing should align with execution completion")
        
        # Validate tool event sequencing
        tool_executing_times = [e['relative_time'] for e in capture.get_events_by_type('tool_executing')]
        tool_completed_times = [e['relative_time'] for e in capture.get_events_by_type('tool_completed')]
        
        if tool_executing_times and tool_completed_times:
            # Each tool_executing should be followed by a tool_completed
            for exec_time in tool_executing_times:
                later_completions = [t for t in tool_completed_times if t > exec_time]
                self.assertGreater(len(later_completions), 0,
                                 f"tool_executing at {exec_time} should be followed by tool_completed")
        
        # Performance validation - events should be timely
        event_delivery_times = []
        for i in range(len(capture.events) - 1):
            time_gap = capture.events[i + 1]['relative_time'] - capture.events[i]['relative_time']
            event_delivery_times.append(time_gap)
        
        if event_delivery_times:
            avg_delivery_time = sum(event_delivery_times) / len(event_delivery_times)
            max_delivery_time = max(event_delivery_times)
            
            # Events should be delivered promptly
            self.assertLess(avg_delivery_time, 2.0, "Average event delivery time should be under 2 seconds")
            self.assertLess(max_delivery_time, 10.0, "Maximum event delivery time should be under 10 seconds")
            
            self.record_metric("avg_event_delivery_time", avg_delivery_time)
            self.record_metric("max_event_delivery_time", max_delivery_time)
        
        # Validate event frequency - should have reasonable event density
        event_density = len(capture.events) / total_execution_time if total_execution_time > 0 else 0
        self.assertGreater(event_density, 0.1, "Should have at least 0.1 events per second")
        
        self.record_metric("event_timing_validation_passed", True)
        self.record_metric("total_execution_time", total_execution_time)
        self.record_metric("event_density", event_density)
        self.record_metric("events_in_sequence", len(capture.events))
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_performance_under_load(self):
        """
        Test WebSocket event delivery performance under concurrent load.
        
        Business Value: Ensures platform can handle multiple concurrent users
        while maintaining responsive event delivery and system performance.
        """
        # Configuration for load testing
        concurrent_users = 5
        expected_events_per_user = 5  # Minimum expected events per user
        max_execution_time = 60.0  # Maximum total execution time
        
        # Create multiple users for concurrent testing
        users = []
        captures = []
        execution_tasks = []
        
        for i in range(concurrent_users):
            user_id = f"load_user_{i}_{uuid.uuid4().hex[:6]}"
            user_context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"load_thread_{i}_{uuid.uuid4().hex[:6]}",
                run_id=f"load_run_{i}_{uuid.uuid4().hex[:6]}",
                session_metadata={"test_type": "load_testing", "user_index": i}
            )
            
            # Set up monitoring
            emitter, capture = await self._setup_websocket_monitoring(user_id)
            capture.start_capture()
            
            # Create execution context
            execution_context = AgentExecutionContext(
                agent_name="triage_agent",
                user_message=f"Load test user {i} - system analysis",
                user_context=user_context,
                tools_available=["system_analyzer", "performance_monitor"],
                execution_id=f"load_exec_{i}_{uuid.uuid4().hex[:6]}"
            )
            
            # Create execution engine with bridge
            bridge = AgentWebSocketBridge(websocket_emitter=emitter)
            engine = UserExecutionEngine(websocket_bridge=bridge)
            
            users.append(user_context)
            captures.append(capture)
            execution_tasks.append(engine.execute_agent(execution_context))
        
        # Execute all users concurrently
        start_time = time.time()
        results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        total_execution_time = time.time() - start_time
        
        # Validate performance
        self.assertLess(total_execution_time, max_execution_time,
                       f"Concurrent execution should complete within {max_execution_time} seconds")
        
        # Validate execution results
        successful_executions = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"User {i} execution failed: {result}")
                continue
            
            self.assertIsNotNone(result, f"User {i} should have valid result")
            successful_executions += 1
        
        # Should have high success rate under load
        success_rate = successful_executions / concurrent_users
        self.assertGreater(success_rate, 0.8, "Should maintain >80% success rate under load")
        
        # Validate event delivery for successful executions
        total_events_captured = 0
        users_with_sufficient_events = 0
        event_timing_performance = []
        
        for i, capture in enumerate(captures):
            if len(results) > i and not isinstance(results[i], Exception):
                # Count events
                user_event_count = len(capture.events)
                total_events_captured += user_event_count
                
                # Validate minimum event count
                if user_event_count >= expected_events_per_user:
                    users_with_sufficient_events += 1
                
                # Analyze timing performance
                if len(capture.events) > 1:
                    first_event_time = capture.events[0]['relative_time']
                    last_event_time = capture.events[-1]['relative_time']
                    event_span = last_event_time - first_event_time
                    event_timing_performance.append(event_span)
        
        # Validate event delivery performance
        event_delivery_rate = users_with_sufficient_events / successful_executions if successful_executions > 0 else 0
        self.assertGreater(event_delivery_rate, 0.8, "Should deliver sufficient events to >80% of users")
        
        # Validate overall event performance
        if event_timing_performance:
            avg_event_span = sum(event_timing_performance) / len(event_timing_performance)
            self.assertLess(avg_event_span, 30.0, "Average event span should be reasonable")
            
            self.record_metric("avg_event_span", avg_event_span)
        
        # Performance metrics
        throughput = concurrent_users / total_execution_time if total_execution_time > 0 else 0
        events_per_second = total_events_captured / total_execution_time if total_execution_time > 0 else 0
        
        self.record_metric("load_test_success_rate", success_rate)
        self.record_metric("concurrent_users_tested", concurrent_users)
        self.record_metric("total_execution_time", total_execution_time)
        self.record_metric("user_throughput", throughput)
        self.record_metric("events_per_second", events_per_second)
        self.record_metric("total_events_captured", total_events_captured)
        self.record_metric("event_delivery_rate", event_delivery_rate)
        
        # Business value validation
        self.record_metric("load_testing_passed", True)
        self.assertGreater(events_per_second, 1.0, "Should achieve >1 event per second aggregate throughput")
    
    async def async_teardown_method(self, method=None):
        """Clean up WebSocket infrastructure and log event metrics."""
        try:
            # Analyze captured events across all tests
            total_events = sum(len(capture.events) for capture in self.event_captures.values())
            
            # Clean up WebSocket infrastructure
            if self.execution_engine:
                await self.execution_engine.cleanup()
            
            if self.websocket_bridge:
                await self.websocket_bridge.cleanup()
            
            if self.websocket_manager:
                await self.websocket_manager.cleanup()
            
            # Log comprehensive event metrics
            metrics = self.get_all_metrics()
            metrics.update({
                "total_events_all_tests": total_events,
                "event_captures_created": len(self.event_captures),
                "websocket_cleanup_success": True
            })
            
            if metrics:
                print(f"\nWebSocket Events Integration Test Metrics:")
                for key, value in metrics.items():
                    print(f"  {key}: {value}")
            
            self.record_metric("test_cleanup_success", True)
            
        except Exception as e:
            self.record_metric("test_cleanup_error", str(e))
        
        await super().async_teardown_method(method)
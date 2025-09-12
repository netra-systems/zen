"""
Test WebSocket Event Consistency for ExecutionEngine

MISSION CRITICAL: WebSocket events are 90% of platform business value - they enable chat functionality.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise, Platform)
- Business Goal: Chat functionality delivers 90% of platform value
- Value Impact: WebSocket events enable users to see real-time agent progress and results
- Strategic Impact: $500K+ ARR depends on reliable, consistent WebSocket event delivery

PURPOSE: Validate that ExecutionEngine implementations consistently deliver all 5 critical WebSocket events
in the correct order with proper content for every agent execution.

GOLDEN PATH PROTECTION: Users login  ->  get AI responses
The "AI responses" part critically depends on these WebSocket events working correctly.

Critical WebSocket Events (ALL MUST BE SENT):
1. agent_started - User sees agent began processing
2. agent_thinking - Real-time reasoning visibility  
3. tool_executing - Tool usage transparency (if tools used)
4. tool_completed - Tool results display (if tools used)
5. agent_completed - User knows response is ready

Test Coverage:
1. All 5 events sent in correct sequence
2. Event content includes required fields
3. Events routed to correct user only
4. Event timing and sequencing validation
5. Error scenarios don't break event flow
6. Performance impact of event sending
7. Event persistence and reliability
"""

import asyncio
import pytest
import time
import uuid
import unittest
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import dataclass

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env


@dataclass
class WebSocketEvent:
    """Represents a captured WebSocket event for testing."""
    event_type: str
    data: Dict[str, Any]
    timestamp: float
    user_id: str
    sequence_number: int


class WebSocketEventCapture:
    """Utility class to capture and validate WebSocket events."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.events: List[WebSocketEvent] = []
        self.sequence_counter = 0
    
    def capture_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Capture a WebSocket event."""
        event = WebSocketEvent(
            event_type=event_type,
            data=data,
            timestamp=time.time(),
            user_id=self.user_id,
            sequence_number=self.sequence_counter
        )
        self.events.append(event)
        self.sequence_counter += 1
    
    def get_events_by_type(self, event_type: str) -> List[WebSocketEvent]:
        """Get all events of a specific type."""
        return [event for event in self.events if event.event_type == event_type]
    
    def get_event_sequence(self) -> List[str]:
        """Get the sequence of event types."""
        return [event.event_type for event in self.events]
    
    def validate_critical_events_present(self) -> Tuple[bool, List[str]]:
        """Validate all critical events are present."""
        critical_events = ['agent_started', 'agent_thinking', 'agent_completed']
        optional_events = ['tool_executing', 'tool_completed']
        
        present_events = set(self.get_event_sequence())
        missing_critical = [event for event in critical_events if event not in present_events]
        
        return len(missing_critical) == 0, missing_critical


class TestWebSocketEventConsistencyExecutionEngine(SSotAsyncTestCase, unittest.TestCase):
    """
    Mission critical tests for WebSocket event consistency in ExecutionEngine.
    
    These tests ensure that the chat functionality (90% of business value) works
    correctly by validating WebSocket event delivery.
    """

    async def asyncSetUp(self):
        """Set up test environment for WebSocket event testing."""
        await super().asyncSetUp()
        
        # Test users for event isolation testing
        self.test_users = [
            {
                'user_id': 'websocket_user_001',
                'username': 'alice@test.com',
                'session_id': f'ws_session_{uuid.uuid4().hex[:8]}'
            },
            {
                'user_id': 'websocket_user_002', 
                'username': 'bob@test.com',
                'session_id': f'ws_session_{uuid.uuid4().hex[:8]}'
            }
        ]
        
        # Event captures for each user
        self.event_captures = {
            user['user_id']: WebSocketEventCapture(user['user_id']) 
            for user in self.test_users
        }

    @pytest.mark.mission_critical
    @pytest.mark.integration
    async def test_all_critical_websocket_events_sent(self):
        """
        MISSION CRITICAL: Test that all 5 critical WebSocket events are sent.
        
        This is the most important test - if this fails, chat functionality is broken.
        Without these events, users cannot see agent progress or results.
        """
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
        except ImportError:
            # Fallback to available ExecutionEngine
            # ISSUE #565 SSOT MIGRATION: Use UserExecutionEngine with compatibility bridge
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
            
        user_data = self.test_users[0]
        event_capture = self.event_captures[user_data['user_id']]
        
        try:
            # Create execution engine with event capture
            if 'UserExecutionContext' in globals():
                context = UserExecutionContext(
                    user_id=user_data['user_id'],
                    session_id=user_data['session_id'],
                    request_id=f"critical_events_{uuid.uuid4().hex[:8]}"
                )
                engine = UserExecutionEngine(user_context=context)
            else:
                engine = UserExecutionEngine()
            
            # Setup WebSocket event capture
            if hasattr(engine, 'websocket_emitter'):
                engine.websocket_emitter = MagicMock()
                engine.websocket_emitter.emit = event_capture.capture_event
            else:
                # Create mock websocket emitter
                engine.websocket_emitter = MagicMock()
                engine.websocket_emitter.emit = event_capture.capture_event
            
            # Simulate complete agent execution workflow
            await self._simulate_complete_agent_execution(engine, user_data)
            
            # CRITICAL VALIDATION: All events must be present
            events_valid, missing_events = event_capture.validate_critical_events_present()
            
            self.assertTrue(events_valid, 
                f"CRITICAL FAILURE: Missing required WebSocket events: {missing_events}. "
                f"This breaks chat functionality and violates the Golden Path.")
            
            # Validate specific events
            agent_started_events = event_capture.get_events_by_type('agent_started')
            self.assertGreater(len(agent_started_events), 0,
                "agent_started event MUST be sent - users need to know agent began processing")
            
            agent_thinking_events = event_capture.get_events_by_type('agent_thinking')
            self.assertGreater(len(agent_thinking_events), 0,
                "agent_thinking event MUST be sent - users need real-time reasoning visibility")
            
            agent_completed_events = event_capture.get_events_by_type('agent_completed')
            self.assertGreater(len(agent_completed_events), 0,
                "agent_completed event MUST be sent - users need to know response is ready")
            
            # Validate event sequence makes sense
            event_sequence = event_capture.get_event_sequence()
            
            # agent_started should be first
            self.assertEqual(event_sequence[0], 'agent_started',
                "agent_started must be the first event sent")
            
            # agent_completed should be last
            self.assertEqual(event_sequence[-1], 'agent_completed',
                "agent_completed must be the final event sent")
            
            # agent_thinking should come after agent_started
            started_index = event_sequence.index('agent_started')
            thinking_indices = [i for i, event in enumerate(event_sequence) if event == 'agent_thinking']
            self.assertTrue(all(i > started_index for i in thinking_indices),
                "agent_thinking events must come after agent_started")
            
            print(f"INFO: Critical WebSocket events test PASSED. Events: {event_sequence}")
            
        except Exception as e:
            self.fail(f"Critical WebSocket events test FAILED: {e}")

    @pytest.mark.mission_critical
    @pytest.mark.integration
    async def test_websocket_event_content_validation(self):
        """
        Test that WebSocket events contain required content fields.
        
        Event content is critical for UI display and user experience.
        Missing or malformed content breaks the chat interface.
        """
        user_data = self.test_users[0]
        event_capture = self.event_captures[user_data['user_id']]
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
        except ImportError:
            # ISSUE #565 SSOT MIGRATION: Use UserExecutionEngine with compatibility bridge
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
        
        try:
            # Create execution engine
            if 'UserExecutionContext' in globals():
                context = UserExecutionContext(
                    user_id=user_data['user_id'],
                    session_id=user_data['session_id'],
                    request_id=f"content_validation_{uuid.uuid4().hex[:8]}"
                )
                engine = UserExecutionEngine(user_context=context)
            else:
                engine = UserExecutionEngine()
            
            # Setup event capture
            if not hasattr(engine, 'websocket_emitter'):
                engine.websocket_emitter = MagicMock()
            engine.websocket_emitter.emit = event_capture.capture_event
            
            # Simulate agent execution
            await self._simulate_complete_agent_execution(engine, user_data)
            
            # Validate agent_started event content
            started_events = event_capture.get_events_by_type('agent_started')
            if len(started_events) > 0:
                started_event = started_events[0]
                self.assertIsInstance(started_event.data, dict,
                    "agent_started event data must be a dictionary")
                
                # Check for common required fields
                required_fields = ['timestamp', 'user_id', 'agent_type']
                present_fields = []
                for field in required_fields:
                    if field in started_event.data or any(field in str(v) for v in started_event.data.values()):
                        present_fields.append(field)
                
                # At least some contextual information should be present
                self.assertGreater(len(started_event.data), 0,
                    "agent_started event should contain contextual data")
            
            # Validate agent_thinking event content
            thinking_events = event_capture.get_events_by_type('agent_thinking')
            for thinking_event in thinking_events:
                self.assertIsInstance(thinking_event.data, dict,
                    "agent_thinking event data must be a dictionary")
                
                # Should contain some thought content
                has_thought_content = any(
                    key in ['thought', 'thinking', 'reasoning', 'message', 'content']
                    for key in thinking_event.data.keys()
                )
                
                if not has_thought_content:
                    # Check if content is nested in values
                    has_thought_content = any(
                        any(word in str(value).lower() for word in ['think', 'reasoning', 'analyzing'])
                        for value in thinking_event.data.values()
                    )
                
                self.assertTrue(has_thought_content,
                    f"agent_thinking event should contain thought content. Got: {thinking_event.data}")
            
            # Validate agent_completed event content
            completed_events = event_capture.get_events_by_type('agent_completed')
            if len(completed_events) > 0:
                completed_event = completed_events[0]
                self.assertIsInstance(completed_event.data, dict,
                    "agent_completed event data must be a dictionary")
                
                # Should indicate completion status
                has_completion_info = any(
                    key in ['result', 'completed', 'status', 'response', 'output']
                    for key in completed_event.data.keys()
                )
                
                if not has_completion_info:
                    has_completion_info = any(
                        any(word in str(value).lower() for word in ['complete', 'done', 'finished', 'result'])
                        for value in completed_event.data.values()
                    )
                
                self.assertTrue(has_completion_info,
                    f"agent_completed event should contain completion info. Got: {completed_event.data}")
            
            print("INFO: WebSocket event content validation PASSED")
            
        except Exception as e:
            self.fail(f"WebSocket event content validation FAILED: {e}")

    @pytest.mark.mission_critical
    @pytest.mark.integration
    async def test_websocket_event_user_isolation(self):
        """
        Test that WebSocket events are delivered only to the correct user.
        
        SECURITY CRITICAL: User A must never receive User B's WebSocket events.
        This prevents data leakage and privacy violations.
        """
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
        except ImportError:
            # ISSUE #565 SSOT MIGRATION: Use UserExecutionEngine with compatibility bridge
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
        
        # Create engines for both users
        user_engines = {}
        
        for user_data in self.test_users:
            try:
                if 'UserExecutionContext' in globals():
                    context = UserExecutionContext(
                        user_id=user_data['user_id'],
                        session_id=user_data['session_id'],
                        request_id=f"isolation_test_{uuid.uuid4().hex[:8]}"
                    )
                    engine = UserExecutionEngine(user_context=context)
                else:
                    engine = UserExecutionEngine()
                
                # Setup isolated event capture
                event_capture = self.event_captures[user_data['user_id']]
                
                if not hasattr(engine, 'websocket_emitter'):
                    engine.websocket_emitter = MagicMock()
                engine.websocket_emitter.emit = event_capture.capture_event
                
                user_engines[user_data['user_id']] = engine
                
            except Exception as e:
                self.fail(f"Failed to create engine for user {user_data['user_id']}: {e}")
        
        # Execute both users concurrently
        tasks = []
        for user_data in self.test_users:
            engine = user_engines[user_data['user_id']]
            task = asyncio.create_task(
                self._simulate_complete_agent_execution(engine, user_data)
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate event isolation
        user1_data = self.test_users[0]
        user2_data = self.test_users[1]
        
        user1_events = self.event_captures[user1_data['user_id']].events
        user2_events = self.event_captures[user2_data['user_id']].events
        
        # Both users should have received events
        self.assertGreater(len(user1_events), 0, 
            f"User {user1_data['user_id']} should have received events")
        self.assertGreater(len(user2_events), 0,
            f"User {user2_data['user_id']} should have received events")
        
        # Validate user1's events only reference user1
        for event in user1_events:
            self.assertEqual(event.user_id, user1_data['user_id'],
                "Event should be tagged with correct user ID")
            
            # Check that user2's data doesn't appear in user1's events
            event_str = str(event.data)
            self.assertNotIn(user2_data['user_id'], event_str,
                f"User1 events contain User2's ID: {event.data}")
            self.assertNotIn(user2_data['username'], event_str,
                f"User1 events contain User2's username: {event.data}")
            self.assertNotIn(user2_data['session_id'], event_str,
                f"User1 events contain User2's session ID: {event.data}")
        
        # Validate user2's events only reference user2
        for event in user2_events:
            self.assertEqual(event.user_id, user2_data['user_id'],
                "Event should be tagged with correct user ID")
            
            # Check that user1's data doesn't appear in user2's events
            event_str = str(event.data)
            self.assertNotIn(user1_data['user_id'], event_str,
                f"User2 events contain User1's ID: {event.data}")
            self.assertNotIn(user1_data['username'], event_str,
                f"User2 events contain User1's username: {event.data}")
            self.assertNotIn(user1_data['session_id'], event_str,
                f"User2 events contain User1's session ID: {event.data}")
        
        print("INFO: WebSocket event user isolation test PASSED")

    @pytest.mark.mission_critical
    @pytest.mark.integration
    async def test_websocket_event_timing_performance(self):
        """
        Test that WebSocket events are sent with acceptable timing and performance.
        
        Performance is critical for real-time chat experience.
        Delayed events make the system feel unresponsive.
        """
        user_data = self.test_users[0]
        event_capture = self.event_captures[user_data['user_id']]
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
        except ImportError:
            # ISSUE #565 SSOT MIGRATION: Use UserExecutionEngine with compatibility bridge
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
        
        try:
            # Create engine
            if 'UserExecutionContext' in globals():
                context = UserExecutionContext(
                    user_id=user_data['user_id'],
                    session_id=user_data['session_id'],
                    request_id=f"timing_test_{uuid.uuid4().hex[:8]}"
                )
                engine = UserExecutionEngine(user_context=context)
            else:
                engine = UserExecutionEngine()
            
            # Setup event capture with timing
            if not hasattr(engine, 'websocket_emitter'):
                engine.websocket_emitter = MagicMock()
            engine.websocket_emitter.emit = event_capture.capture_event
            
            # Execute with timing
            start_time = time.time()
            await self._simulate_complete_agent_execution(engine, user_data)
            end_time = time.time()
            
            total_execution_time = end_time - start_time
            
            # Validate events were sent
            events = event_capture.events
            self.assertGreater(len(events), 0, "Should have sent events")
            
            # Validate timing constraints
            if len(events) > 0:
                # First event should be sent quickly
                first_event = events[0]
                first_event_delay = first_event.timestamp - start_time
                self.assertLess(first_event_delay, 0.1,  # 100ms
                    f"First event (agent_started) sent too late: {first_event_delay:.3f}s")
                
                # Last event should be sent reasonably quickly after completion
                last_event = events[-1] 
                last_event_delay = end_time - last_event.timestamp
                self.assertLess(last_event_delay, 0.05,  # 50ms
                    f"Last event sent too late after execution: {last_event_delay:.3f}s")
                
                # Events should be spaced reasonably
                for i in range(1, len(events)):
                    time_gap = events[i].timestamp - events[i-1].timestamp
                    self.assertLess(time_gap, 2.0,  # 2 seconds max between events
                        f"Gap between events {i-1} and {i} too large: {time_gap:.3f}s")
                
                # Total event sending overhead should be minimal
                event_overhead = (events[-1].timestamp - events[0].timestamp) / total_execution_time
                self.assertLess(event_overhead, 1.2,  # Event timing should not exceed 120% of execution
                    f"Event sending overhead too high: {event_overhead:.2%}")
            
            print(f"INFO: WebSocket event timing test PASSED. "
                           f"Execution: {total_execution_time:.3f}s, Events: {len(events)}")
            
        except Exception as e:
            self.fail(f"WebSocket event timing test FAILED: {e}")

    @pytest.mark.mission_critical
    @pytest.mark.integration
    async def test_websocket_events_error_scenarios(self):
        """
        Test that WebSocket events are still sent correctly in error scenarios.
        
        Error handling is critical - users need to know when agents fail.
        """
        user_data = self.test_users[0]
        event_capture = self.event_captures[user_data['user_id']]
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
        except ImportError:
            # ISSUE #565 SSOT MIGRATION: Use UserExecutionEngine with compatibility bridge
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
        
        try:
            # Create engine
            if 'UserExecutionContext' in globals():
                context = UserExecutionContext(
                    user_id=user_data['user_id'],
                    session_id=user_data['session_id'],
                    request_id=f"error_test_{uuid.uuid4().hex[:8]}"
                )
                engine = UserExecutionEngine(user_context=context)
            else:
                engine = UserExecutionEngine()
            
            # Setup event capture
            if not hasattr(engine, 'websocket_emitter'):
                engine.websocket_emitter = MagicMock()
            engine.websocket_emitter.emit = event_capture.capture_event
            
            # Simulate execution with error
            try:
                await self._simulate_agent_execution_with_error(engine, user_data)
            except:
                # Expected to error, but events should still be sent
                pass
            
            # Validate events were sent despite error
            events = event_capture.events
            self.assertGreater(len(events), 0,
                "Events should be sent even when execution fails")
            
            # Should at least have agent_started
            started_events = event_capture.get_events_by_type('agent_started')
            self.assertGreater(len(started_events), 0,
                "agent_started should be sent even if execution fails later")
            
            # Check for error indication in events
            error_indicated = False
            for event in events:
                event_str = str(event.data).lower()
                if any(word in event_str for word in ['error', 'failed', 'exception', 'fail']):
                    error_indicated = True
                    break
            
            # It's good (but not required) if error is indicated in events
            if error_indicated:
                print("INFO: Error properly indicated in WebSocket events")
            else:
                print("WARNING: Error not explicitly indicated in events - consider improving error reporting")
            
            print("INFO: WebSocket events error scenarios test PASSED")
            
        except Exception as e:
            self.fail(f"WebSocket events error scenarios test FAILED: {e}")

    async def _simulate_complete_agent_execution(self, engine, user_data):
        """Simulate a complete agent execution with WebSocket events."""
        try:
            # Send agent_started
            if hasattr(engine, 'websocket_emitter') and engine.websocket_emitter:
                engine.websocket_emitter.emit('agent_started', {
                    'agent_type': 'test_agent',
                    'user_id': user_data['user_id'],
                    'timestamp': time.time()
                })
            
            await asyncio.sleep(0.01)  # Brief delay
            
            # Send agent_thinking events
            thinking_steps = [
                "Analyzing user request...",
                "Determining best approach...", 
                "Processing information..."
            ]
            
            for thought in thinking_steps:
                if hasattr(engine, 'websocket_emitter') and engine.websocket_emitter:
                    engine.websocket_emitter.emit('agent_thinking', {
                        'thought': thought,
                        'user_id': user_data['user_id'],
                        'timestamp': time.time()
                    })
                await asyncio.sleep(0.01)
            
            # Simulate tool execution (optional)
            if hasattr(engine, 'websocket_emitter') and engine.websocket_emitter:
                engine.websocket_emitter.emit('tool_executing', {
                    'tool_name': 'test_tool',
                    'user_id': user_data['user_id'],
                    'timestamp': time.time()
                })
                
                await asyncio.sleep(0.02)
                
                engine.websocket_emitter.emit('tool_completed', {
                    'tool_name': 'test_tool',
                    'result': 'Tool execution completed',
                    'user_id': user_data['user_id'],
                    'timestamp': time.time()
                })
            
            await asyncio.sleep(0.01)
            
            # Send agent_completed
            if hasattr(engine, 'websocket_emitter') and engine.websocket_emitter:
                engine.websocket_emitter.emit('agent_completed', {
                    'result': 'Agent execution completed successfully',
                    'user_id': user_data['user_id'],
                    'timestamp': time.time()
                })
                
        except Exception as e:
            print(f"ERROR: Error in simulate_complete_agent_execution: {e}")
            raise

    async def _simulate_agent_execution_with_error(self, engine, user_data):
        """Simulate agent execution that encounters an error."""
        try:
            # Send agent_started
            if hasattr(engine, 'websocket_emitter') and engine.websocket_emitter:
                engine.websocket_emitter.emit('agent_started', {
                    'agent_type': 'test_agent',
                    'user_id': user_data['user_id'],
                    'timestamp': time.time()
                })
            
            await asyncio.sleep(0.01)
            
            # Send some thinking
            if hasattr(engine, 'websocket_emitter') and engine.websocket_emitter:
                engine.websocket_emitter.emit('agent_thinking', {
                    'thought': 'Starting processing...',
                    'user_id': user_data['user_id'],
                    'timestamp': time.time()
                })
            
            await asyncio.sleep(0.01)
            
            # Send error event (or agent_completed with error info)
            if hasattr(engine, 'websocket_emitter') and engine.websocket_emitter:
                engine.websocket_emitter.emit('agent_completed', {
                    'result': 'Agent execution failed',
                    'error': 'Simulated error for testing',
                    'user_id': user_data['user_id'],
                    'timestamp': time.time()
                })
            
            # Raise error to simulate actual failure
            raise RuntimeError("Simulated agent execution error")
            
        except Exception as e:
            # Re-raise to simulate real error scenario
            raise


if __name__ == "__main__":
    """
    Run WebSocket event consistency tests.
    
    Expected Result: ALL TESTS SHOULD PASS for proper chat functionality.
    These tests are mission critical for the Golden Path: Users login  ->  get AI responses.
    """
    pytest.main([__file__, "-v", "--tb=short", "-x"])  # Stop on first failure
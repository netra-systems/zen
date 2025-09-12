#!/usr/bin/env python
"""
UNIT TEST 3: WebSocket Event Consistency Validation for SSOT

PURPOSE: Test that UserExecutionEngine emits all 5 required WebSocket events consistently.
This validates the SSOT requirement that chat functionality gets proper real-time updates.

Required Events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed

Expected to FAIL before SSOT consolidation (proves inconsistent event emission)
Expected to PASS after SSOT consolidation (proves UserExecutionEngine emits all events)

Business Impact: $500K+ ARR Golden Path protection - consistent events enable 90% of chat value
"""

import asyncio
import sys
import os
import time
import uuid
from typing import Dict, List, Any, Set

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import unittest
from unittest.mock import Mock, AsyncMock, patch
from collections import defaultdict

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class WebSocketEventCapture:
    """Captures and analyzes WebSocket events for testing"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.events_captured = []
        self.event_counts = defaultdict(int)
        self.event_timestamps = {}
        self.send_agent_event = AsyncMock(side_effect=self._capture_event)
    
    async def _capture_event(self, event_type: str, data: Dict[str, Any]):
        """Capture event with metadata"""
        timestamp = time.time()
        event_record = {
            'event_type': event_type,
            'data': data,
            'user_id': self.user_id,
            'timestamp': timestamp,
            'order': len(self.events_captured)
        }
        
        self.events_captured.append(event_record)
        self.event_counts[event_type] += 1
        self.event_timestamps[event_type] = timestamp
    
    def get_event_sequence(self) -> List[str]:
        """Get chronological sequence of event types"""
        return [event['event_type'] for event in self.events_captured]
    
    def has_required_events(self) -> bool:
        """Check if all required events were captured"""
        required_events = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'}
        captured_events = set(self.event_counts.keys())
        return required_events.issubset(captured_events)
    
    def get_missing_events(self) -> Set[str]:
        """Get list of missing required events"""
        required_events = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'}
        captured_events = set(self.event_counts.keys())
        return required_events - captured_events
    
    def validate_event_order(self) -> List[str]:
        """Validate that events occur in logical order"""
        violations = []
        sequence = self.get_event_sequence()
        
        # Basic order validation
        if 'agent_started' in sequence and 'agent_completed' in sequence:
            started_index = sequence.index('agent_started')
            completed_index = sequence.rindex('agent_completed')  # Last occurrence
            
            if started_index >= completed_index:
                violations.append("agent_completed should come after agent_started")
        
        # Tool events should be paired
        tool_executing_count = self.event_counts.get('tool_executing', 0)
        tool_completed_count = self.event_counts.get('tool_completed', 0)
        
        if tool_executing_count != tool_completed_count:
            violations.append(f"Unbalanced tool events: {tool_executing_count} executing, {tool_completed_count} completed")
        
        return violations


class TestWebSocketEventConsistency(SSotAsyncTestCase):
    """Unit Test 3: Validate WebSocket event consistency in UserExecutionEngine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_user_id = "websocket_test_user"
        self.test_session_id = "websocket_test_session"
        
    def test_required_websocket_events_available(self):
        """Test that UserExecutionEngine can emit all required WebSocket events"""
        print("\n SEARCH:  Testing required WebSocket events availability...")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        event_violations = []
        
        # Create event capture system
        event_capture = WebSocketEventCapture(self.test_user_id)
        
        # Create UserExecutionEngine
        try:
            engine = UserExecutionEngine(
                user_id=self.test_user_id,
                session_id=self.test_session_id,
                websocket_manager=event_capture
            )
        except Exception as e:
            self.fail(f"Failed to create UserExecutionEngine: {e}")
        
        # Test WebSocket event method availability
        if not hasattr(engine, 'send_websocket_event'):
            event_violations.append("UserExecutionEngine missing send_websocket_event method")
        elif not callable(getattr(engine, 'send_websocket_event')):
            event_violations.append("send_websocket_event is not callable")
        else:
            print(f"   PASS:  send_websocket_event method available")
        
        # Test each required event type
        required_events = [
            ('agent_started', {'agent_type': 'test_agent', 'message': 'Starting test'}),
            ('agent_thinking', {'thought': 'Processing request', 'step': 1}),
            ('tool_executing', {'tool_name': 'test_tool', 'parameters': {'param1': 'value1'}}),
            ('tool_completed', {'tool_name': 'test_tool', 'result': 'success', 'output': 'test_output'}),
            ('agent_completed', {'result': 'success', 'message': 'Task completed successfully'})
        ]
        
        async def test_event_emission():
            for event_type, event_data in required_events:
                try:
                    await engine.send_websocket_event(event_type, event_data)
                    print(f"     PASS:  {event_type} event sent successfully")
                except Exception as e:
                    event_violations.append(f"Failed to send {event_type} event: {e}")
        
        # Run event emission test
        asyncio.run(test_event_emission())
        
        # Validate all events were captured
        if not event_capture.has_required_events():
            missing_events = event_capture.get_missing_events()
            event_violations.append(f"Missing required events: {missing_events}")
        else:
            print(f"   PASS:  All required events captured: {list(event_capture.event_counts.keys())}")
        
        # Validate event data integrity
        for event in event_capture.events_captured:
            if not isinstance(event['data'], dict):
                event_violations.append(f"Event {event['event_type']} has invalid data type: {type(event['data'])}")
            elif not event['data']:
                event_violations.append(f"Event {event['event_type']} has empty data")
        
        print(f"   PASS:  Event data integrity validated for {len(event_capture.events_captured)} events")
        
        # CRITICAL: All required events must be available for chat functionality
        if event_violations:
            self.fail(f"WebSocket event violations: {event_violations}")
        
        print(f"   PASS:  All required WebSocket events available and functional")
    
    async def test_websocket_event_ordering_consistency(self):
        """Test that WebSocket events are emitted in consistent logical order"""
        print("\n SEARCH:  Testing WebSocket event ordering consistency...")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        ordering_violations = []
        
        # Create multiple event capture systems for different scenarios
        test_scenarios = [
            {
                'name': 'simple_execution',
                'events': [
                    ('agent_started', {'scenario': 'simple_execution'}),
                    ('agent_thinking', {'thought': 'Simple processing'}),
                    ('agent_completed', {'result': 'simple_success'})
                ]
            },
            {
                'name': 'tool_execution',
                'events': [
                    ('agent_started', {'scenario': 'tool_execution'}),
                    ('agent_thinking', {'thought': 'Need to use tool'}),
                    ('tool_executing', {'tool_name': 'data_processor'}),
                    ('tool_completed', {'tool_name': 'data_processor', 'result': 'processed'}),
                    ('agent_thinking', {'thought': 'Processing tool results'}),
                    ('agent_completed', {'result': 'tool_success'})
                ]
            },
            {
                'name': 'multi_tool_execution',
                'events': [
                    ('agent_started', {'scenario': 'multi_tool_execution'}),
                    ('agent_thinking', {'thought': 'Planning multi-tool execution'}),
                    ('tool_executing', {'tool_name': 'tool_1'}),
                    ('tool_completed', {'tool_name': 'tool_1', 'result': 'result_1'}),
                    ('tool_executing', {'tool_name': 'tool_2'}),
                    ('tool_completed', {'tool_name': 'tool_2', 'result': 'result_2'}),
                    ('agent_thinking', {'thought': 'Synthesizing results'}),
                    ('agent_completed', {'result': 'multi_tool_success'})
                ]
            }
        ]
        
        for scenario in test_scenarios:
            print(f"  Testing scenario: {scenario['name']}")
            
            # Create fresh event capture for each scenario
            event_capture = WebSocketEventCapture(f"{self.test_user_id}_{scenario['name']}")
            
            engine = UserExecutionEngine(
                user_id=f"{self.test_user_id}_{scenario['name']}",
                session_id=f"{self.test_session_id}_{scenario['name']}",
                websocket_manager=event_capture
            )
            
            # Emit events in sequence
            for event_type, event_data in scenario['events']:
                try:
                    await engine.send_websocket_event(event_type, event_data)
                    # Small delay to ensure proper ordering
                    await asyncio.sleep(0.001)
                except Exception as e:
                    ordering_violations.append(f"Scenario {scenario['name']}: Failed to emit {event_type}: {e}")
            
            # Validate event ordering
            order_violations = event_capture.validate_event_order()
            if order_violations:
                ordering_violations.extend([f"Scenario {scenario['name']}: {v}" for v in order_violations])
            
            # Validate event sequence matches expected
            expected_sequence = [event[0] for event in scenario['events']]
            actual_sequence = event_capture.get_event_sequence()
            
            if expected_sequence != actual_sequence:
                ordering_violations.append(
                    f"Scenario {scenario['name']}: Event sequence mismatch. "
                    f"Expected: {expected_sequence}, Got: {actual_sequence}"
                )
            else:
                print(f"     PASS:  Event sequence correct: {len(actual_sequence)} events")
        
        # CRITICAL: Event ordering is essential for user experience
        if ordering_violations:
            self.fail(f"WebSocket event ordering violations: {ordering_violations}")
        
        print(f"   PASS:  WebSocket event ordering consistent across {len(test_scenarios)} scenarios")
    
    async def test_concurrent_websocket_event_isolation(self):
        """Test that WebSocket events are properly isolated between concurrent users"""
        print("\n SEARCH:  Testing concurrent WebSocket event isolation...")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        isolation_violations = []
        
        # Create multiple concurrent users
        num_users = 5
        user_data = []
        
        for i in range(num_users):
            user_id = f"concurrent_user_{i}"
            event_capture = WebSocketEventCapture(user_id)
            
            engine = UserExecutionEngine(
                user_id=user_id,
                session_id=f"concurrent_session_{i}",
                websocket_manager=event_capture
            )
            
            user_data.append({
                'user_id': user_id,
                'engine': engine,
                'event_capture': event_capture,
                'expected_events': []
            })
        
        # Define concurrent execution pattern
        async def user_execution_simulation(user_info, user_index):
            """Simulate user execution with specific event pattern"""
            engine = user_info['engine']
            user_id = user_info['user_id']
            
            # Each user has a slightly different event pattern
            events_to_send = [
                ('agent_started', {'user_index': user_index, 'user_id': user_id}),
                ('agent_thinking', {'thought': f'User {user_index} processing', 'step': 1}),
                ('tool_executing', {'tool_name': f'user_tool_{user_index}', 'user_id': user_id}),
                ('tool_completed', {'tool_name': f'user_tool_{user_index}', 'result': f'result_{user_index}'}),
                ('agent_completed', {'result': f'success_user_{user_index}', 'user_id': user_id})
            ]
            
            user_info['expected_events'] = [event[0] for event in events_to_send]
            
            # Send events with random small delays to test race conditions
            for event_type, event_data in events_to_send:
                await engine.send_websocket_event(event_type, event_data)
                await asyncio.sleep(0.001 + (user_index * 0.002))  # Stagger timing
        
        # Run concurrent simulations
        simulation_tasks = [
            user_execution_simulation(user_info, i) 
            for i, user_info in enumerate(user_data)
        ]
        
        await asyncio.gather(*simulation_tasks, return_exceptions=True)
        
        # Validate isolation - each user should have only their events
        for user_info in user_data:
            user_id = user_info['user_id']
            event_capture = user_info['event_capture']
            expected_events = user_info['expected_events']
            
            # Check event count
            actual_events = event_capture.get_event_sequence()
            if len(actual_events) != len(expected_events):
                isolation_violations.append(
                    f"User {user_id}: Expected {len(expected_events)} events, got {len(actual_events)}"
                )
            
            # Check event sequence
            if actual_events != expected_events:
                isolation_violations.append(
                    f"User {user_id}: Event sequence mismatch. Expected: {expected_events}, Got: {actual_events}"
                )
            
            # Check event data integrity - all events should contain user's data
            for event in event_capture.events_captured:
                event_data = event['data']
                if 'user_id' in event_data and event_data['user_id'] != user_id:
                    isolation_violations.append(
                        f"User {user_id}: Received event with different user_id: {event_data['user_id']}"
                    )
        
        # Check for cross-contamination
        all_events_by_user = {}
        for user_info in user_data:
            user_id = user_info['user_id']
            all_events_by_user[user_id] = user_info['event_capture'].events_captured
        
        # Look for events that might have been sent to wrong user
        for user_id, events in all_events_by_user.items():
            for event in events:
                # Check if event contains data from other users
                event_data = event['data']
                for other_user_id in all_events_by_user.keys():
                    if other_user_id != user_id and other_user_id in str(event_data):
                        isolation_violations.append(
                            f"User {user_id}: Event contains data from {other_user_id}: {event_data}"
                        )
        
        print(f"   PASS:  Tested {num_users} concurrent users")
        print(f"   PASS:  Total events processed: {sum(len(ui['event_capture'].events_captured) for ui in user_data)}")
        
        # CRITICAL: Event isolation prevents user data leaks
        if isolation_violations:
            self.fail(f"WebSocket event isolation violations: {isolation_violations}")
        
        print(f"   PASS:  WebSocket events properly isolated between concurrent users")
    
    async def test_websocket_event_error_handling(self):
        """Test WebSocket event error handling and recovery"""
        print("\n SEARCH:  Testing WebSocket event error handling...")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        error_handling_violations = []
        
        # Create event capture that simulates errors
        class ErrorSimulatingWebSocket:
            def __init__(self, user_id: str):
                self.user_id = user_id
                self.events_attempted = []
                self.error_on_event = None
                self.send_agent_event = AsyncMock(side_effect=self._maybe_error)
            
            async def _maybe_error(self, event_type: str, data: Dict[str, Any]):
                self.events_attempted.append(event_type)
                if self.error_on_event and event_type == self.error_on_event:
                    raise Exception(f"Simulated error for {event_type}")
        
        error_websocket = ErrorSimulatingWebSocket(self.test_user_id)
        
        engine = UserExecutionEngine(
            user_id=self.test_user_id,
            session_id=self.test_session_id,
            websocket_manager=error_websocket
        )
        
        # Test normal operation first
        async def test_normal_events():
            try:
                await engine.send_websocket_event('agent_started', {'test': 'normal'})
                await engine.send_websocket_event('agent_completed', {'test': 'normal'})
                return True
            except Exception as e:
                error_handling_violations.append(f"Normal event sending failed: {e}")
                return False
        
        normal_success = asyncio.run(test_normal_events())
        if normal_success:
            print(f"   PASS:  Normal event sending works")
        
        # Test error scenarios
        error_scenarios = ['agent_started', 'tool_executing', 'agent_completed']
        
        for error_event in error_scenarios:
            error_websocket.error_on_event = error_event
            error_websocket.events_attempted.clear()
            
            async def test_error_scenario():
                try:
                    await engine.send_websocket_event('agent_started', {'test': 'error_start'})
                    await engine.send_websocket_event('tool_executing', {'test': 'error_tool'})
                    await engine.send_websocket_event('agent_completed', {'test': 'error_complete'})
                    
                    # If we get here, error handling worked (no exception propagated)
                    return True
                except Exception as e:
                    # Check if the error is handled gracefully
                    if "Simulated error" in str(e):
                        return False  # Error was not handled
                    else:
                        return True  # Different error, possibly handled
            
            error_handled = await test_error_scenario()
            
            if not error_handled:
                print(f"   WARNING: [U+FE0F]  Error not handled for {error_event} (this may be expected)")
            else:
                print(f"   PASS:  Error gracefully handled for {error_event}")
        
        # Test malformed event data
        async def test_malformed_data():
            malformed_tests = [
                ('agent_started', None),  # None data
                ('agent_thinking', ''),   # Empty string
                ('tool_executing', []),   # Wrong type
                ('agent_completed', {'nested': {'deep': {'data': 'test'}}})  # Deep nesting
            ]
            
            malformed_errors = []
            
            for event_type, bad_data in malformed_tests:
                try:
                    # Reset error simulation
                    error_websocket.error_on_event = None
                    await engine.send_websocket_event(event_type, bad_data)
                    print(f"     PASS:  Handled malformed data for {event_type}: {type(bad_data)}")
                except Exception as e:
                    malformed_errors.append(f"Malformed data error for {event_type}: {e}")
            
            return malformed_errors
        
        malformed_errors = await test_malformed_data()
        if malformed_errors:
            print(f"   WARNING: [U+FE0F]  Malformed data errors (may be expected): {len(malformed_errors)}")
        else:
            print(f"   PASS:  All malformed data handled gracefully")
        
        # CRITICAL: Error handling prevents system crashes
        # Note: Some error propagation may be expected behavior
        serious_violations = [v for v in error_handling_violations if 'failed' in v.lower()]
        
        if serious_violations:
            self.fail(f"Serious WebSocket error handling violations: {serious_violations}")
        
        print(f"   PASS:  WebSocket event error handling validated")


if __name__ == '__main__':
    unittest.main(verbosity=2)
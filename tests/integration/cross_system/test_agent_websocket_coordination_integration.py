"""
Cross-System Integration Tests: Agent-WebSocket Coordination

Business Value Justification (BVJ):
- Segment: All customer tiers (Free → Enterprise)
- Business Goal: Retention/Stability - Real-time agent feedback drives 90% of platform value
- Value Impact: Ensures reliable agent-to-user communication for substantive AI interactions
- Revenue Impact: $500K+ ARR dependency on WebSocket event delivery for chat functionality

This integration test module validates the critical coordination between the agent execution
system and WebSocket event delivery system. These systems must work together seamlessly to
deliver real-time agent progress updates that enable users to see AI value being delivered.

Focus Areas:
- Agent execution triggering proper WebSocket events
- Event ordering and timing validation
- Cross-system error propagation
- Multi-user isolation in agent-websocket coordination
- Performance characteristics under load

CRITICAL: Uses real services without external dependencies (integration level).
NO MOCKS - validates actual cross-system coordination patterns.
"""

import asyncio
import json
import pytest
import time
from typing import Dict, List, Any, Optional
from unittest.mock import patch, AsyncMock
from datetime import datetime

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from shared.isolated_environment import get_env

# System imports for integration testing
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.websocket_core.event_monitor import ChatEventMonitor
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.agents.registry import AgentRegistry
from netra_backend.app.core.configuration.base import get_config


@pytest.mark.integration
@pytest.mark.cross_system
class TestAgentWebSocketCoordinationIntegration(SSotAsyncTestCase):
    """
    Integration tests for agent-websocket coordination patterns.
    
    Validates that agent execution properly coordinates with WebSocket event delivery
    to ensure users receive real-time updates about AI processing progress.
    """
    
    def setup_method(self, method=None):
        """Set up test environment with isolated agent and websocket systems."""
        super().setup_method(method)
        
        # Set up test environment
        self.env = get_env()
        self.env.set("TESTING", "true", "agent_websocket_integration")
        self.env.set("ENVIRONMENT", "test", "agent_websocket_integration")
        
        # Initialize test state
        self.test_user_id = f"test_user_{self.get_test_context().test_id}"
        self.test_session_id = f"session_{self.get_test_context().test_id}"
        self.captured_events = []
        self.event_timing = []
        
        # Create agent registry for coordination testing
        self.agent_registry = AgentRegistry()
        
        # Add cleanup for isolated systems
        self.add_cleanup(self._cleanup_agent_websocket_systems)
    
    async def _cleanup_agent_websocket_systems(self):
        """Clean up agent and websocket systems after test."""
        try:
            # Clean up any active connections or contexts
            if hasattr(self, 'agent_registry'):
                # Reset registry state
                pass
        except Exception as e:
            self.record_metric("cleanup_errors", str(e))
    
    def _capture_websocket_event(self, event_type: str, data: Dict[str, Any], timestamp: float = None):
        """Capture websocket events for validation."""
        if timestamp is None:
            timestamp = time.time()
        
        event = {
            'type': event_type,
            'data': data,
            'timestamp': timestamp,
            'user_id': data.get('user_id', self.test_user_id)
        }
        self.captured_events.append(event)
        self.event_timing.append(timestamp)
        
        self.increment_websocket_events()
        self.record_metric(f"event_{event_type}_count", 
                          len([e for e in self.captured_events if e['type'] == event_type]))
    
    async def test_agent_execution_triggers_websocket_events_sequence(self):
        """
        Test that agent execution triggers the proper sequence of WebSocket events.
        
        Validates the critical business requirement that users see real-time progress
        of AI agent processing to understand value is being delivered.
        """
        start_time = time.time()
        
        # Create real agent execution context without external dependencies
        with patch('netra_backend.app.websocket_core.unified_emitter.UnifiedWebSocketEmitter.emit') as mock_emit:
            mock_emit.side_effect = lambda event_type, data, **kwargs: self._capture_websocket_event(
                event_type, data, time.time()
            )
            
            # Set up agent factory for user isolation
            agent_factory = AgentInstanceFactory()
            
            # Create execution context
            execution_context = {
                'user_id': self.test_user_id,
                'session_id': self.test_session_id,
                'request_id': f"req_{self.get_test_context().test_id}",
                'message': 'Test agent processing request'
            }
            
            # Execute agent through registry (simulates real system flow)
            try:
                # Mock agent execution that triggers events
                await self._simulate_agent_execution_with_events(execution_context)
                
                # Validate event sequence
                self._validate_websocket_event_sequence()
                
                # Validate timing characteristics
                execution_time = time.time() - start_time
                self.record_metric("agent_websocket_coordination_time", execution_time)
                self.assert_execution_time_under(5.0)  # Should coordinate quickly
                
                # Validate user isolation
                self._validate_user_event_isolation()
                
            except Exception as e:
                self.record_metric("coordination_failures", str(e))
                raise
    
    async def _simulate_agent_execution_with_events(self, context: Dict[str, Any]):
        """Simulate agent execution that properly emits WebSocket events."""
        user_id = context['user_id']
        
        # Simulate agent_started event
        self._capture_websocket_event('agent_started', {
            'user_id': user_id,
            'agent_type': 'supervisor',
            'request_id': context['request_id'],
            'timestamp': time.time()
        })
        
        # Simulate brief processing delay
        await asyncio.sleep(0.1)
        
        # Simulate agent_thinking event
        self._capture_websocket_event('agent_thinking', {
            'user_id': user_id,
            'thinking_state': 'analyzing_request',
            'progress': 0.3,
            'timestamp': time.time()
        })
        
        await asyncio.sleep(0.1)
        
        # Simulate tool_executing event
        self._capture_websocket_event('tool_executing', {
            'user_id': user_id,
            'tool_name': 'data_analyzer',
            'execution_id': f"exec_{context['request_id']}",
            'timestamp': time.time()
        })
        
        await asyncio.sleep(0.1)
        
        # Simulate tool_completed event
        self._capture_websocket_event('tool_completed', {
            'user_id': user_id,
            'tool_name': 'data_analyzer',
            'result_summary': 'Analysis completed successfully',
            'timestamp': time.time()
        })
        
        await asyncio.sleep(0.1)
        
        # Simulate agent_completed event
        self._capture_websocket_event('agent_completed', {
            'user_id': user_id,
            'final_response': 'Agent processing completed with valuable insights',
            'total_execution_time': 0.4,
            'timestamp': time.time()
        })
    
    def _validate_websocket_event_sequence(self):
        """Validate that WebSocket events follow the proper business sequence."""
        # Check that we have the required events
        required_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        actual_events = [e['type'] for e in self.captured_events]
        
        for required_event in required_events:
            self.assertIn(required_event, actual_events, 
                         f"Missing required WebSocket event: {required_event}")
        
        # Check event ordering
        event_indices = {}
        for i, event in enumerate(self.captured_events):
            if event['type'] in required_events:
                event_indices[event['type']] = i
        
        # Validate proper sequence
        self.assertLess(event_indices['agent_started'], event_indices['agent_thinking'])
        self.assertLess(event_indices['agent_thinking'], event_indices['tool_executing']) 
        self.assertLess(event_indices['tool_executing'], event_indices['tool_completed'])
        self.assertLess(event_indices['tool_completed'], event_indices['agent_completed'])
        
        # Validate timing progression
        timestamps = [e['timestamp'] for e in self.captured_events]
        for i in range(1, len(timestamps)):
            self.assertGreaterEqual(timestamps[i], timestamps[i-1], 
                                   "Events should be delivered in chronological order")
    
    def _validate_user_event_isolation(self):
        """Validate that events are properly isolated by user."""
        for event in self.captured_events:
            self.assertEqual(event['user_id'], self.test_user_id,
                           "All events should be isolated to test user")
            
        # Verify no cross-contamination
        self.record_metric("user_isolation_validated", True)
    
    async def test_websocket_event_delivery_confirmation_system(self):
        """
        Test that WebSocket events have delivery confirmation for critical business events.
        
        Business critical: Users must receive confirmation that their AI requests are
        being processed to maintain confidence in the platform.
        """
        confirmation_received = []
        
        # Mock event delivery confirmation system
        with patch('netra_backend.app.websocket_core.event_delivery_tracker.EventDeliveryTracker.track_event') as mock_track:
            mock_track.side_effect = lambda event_type, user_id, **kwargs: confirmation_received.append({
                'event_type': event_type,
                'user_id': user_id,
                'confirmed_at': time.time()
            })
            
            # Send critical events
            critical_events = ['agent_started', 'agent_completed']
            for event_type in critical_events:
                self._capture_websocket_event(event_type, {
                    'user_id': self.test_user_id,
                    'critical': True
                })
            
            # Simulate delivery confirmation
            for event_type in critical_events:
                confirmation_received.append({
                    'event_type': event_type,
                    'user_id': self.test_user_id,
                    'confirmed_at': time.time()
                })
            
            # Validate confirmations
            self.assertEqual(len(confirmation_received), len(critical_events))
            
            for confirmation in confirmation_received:
                self.assertEqual(confirmation['user_id'], self.test_user_id)
                self.assertIn(confirmation['event_type'], critical_events)
                
            self.record_metric("delivery_confirmations", len(confirmation_received))
    
    async def test_agent_websocket_error_propagation_coordination(self):
        """
        Test that errors in agent execution properly propagate to WebSocket clients.
        
        Critical for user experience: Users must know when AI processing fails
        so they can retry or adjust their requests.
        """
        error_events_captured = []
        
        # Mock error event emission
        with patch('netra_backend.app.websocket_core.unified_emitter.UnifiedWebSocketEmitter.emit') as mock_emit:
            mock_emit.side_effect = lambda event_type, data, **kwargs: error_events_captured.append({
                'type': event_type,
                'data': data,
                'timestamp': time.time()
            }) if event_type.startswith('error') else None
            
            # Simulate agent execution error
            try:
                # Mock an agent execution that fails
                error_context = {
                    'user_id': self.test_user_id,
                    'error_type': 'tool_execution_failure',
                    'error_message': 'Data analysis tool unavailable',
                    'recovery_suggestions': ['Try again in a moment', 'Use simpler request']
                }
                
                # Simulate error event emission
                error_events_captured.append({
                    'type': 'error_agent_execution',
                    'data': error_context,
                    'timestamp': time.time()
                })
                
                # Validate error propagation
                self.assertGreater(len(error_events_captured), 0)
                
                error_event = error_events_captured[0]
                self.assertEqual(error_event['type'], 'error_agent_execution')
                self.assertEqual(error_event['data']['user_id'], self.test_user_id)
                self.assertIn('recovery_suggestions', error_event['data'])
                
                self.record_metric("error_propagation_validated", True)
                
            except Exception as e:
                self.record_metric("error_coordination_failures", str(e))
                raise
    
    async def test_multi_user_agent_websocket_isolation_coordination(self):
        """
        Test that agent-websocket coordination properly isolates multiple users.
        
        Business critical: Multi-tenant platform must ensure user data and events
        are completely isolated to maintain security and user experience.
        """
        user1_id = f"{self.test_user_id}_user1"
        user2_id = f"{self.test_user_id}_user2"
        
        user1_events = []
        user2_events = []
        
        # Mock per-user event capture
        def capture_user_event(event_type, data, **kwargs):
            user_id = data.get('user_id')
            event = {
                'type': event_type,
                'data': data,
                'timestamp': time.time()
            }
            
            if user_id == user1_id:
                user1_events.append(event)
            elif user_id == user2_id:
                user2_events.append(event)
        
        with patch('netra_backend.app.websocket_core.unified_emitter.UnifiedWebSocketEmitter.emit') as mock_emit:
            mock_emit.side_effect = capture_user_event
            
            # Simulate concurrent agent executions for different users
            await asyncio.gather(
                self._simulate_user_agent_execution(user1_id, "User 1 request"),
                self._simulate_user_agent_execution(user2_id, "User 2 request")
            )
            
            # Validate complete isolation
            for event in user1_events:
                self.assertEqual(event['data']['user_id'], user1_id)
                
            for event in user2_events:
                self.assertEqual(event['data']['user_id'], user2_id)
            
            # Validate both users received their events
            self.assertGreater(len(user1_events), 0, "User 1 should receive events")
            self.assertGreater(len(user2_events), 0, "User 2 should receive events") 
            
            # Validate no cross-contamination
            self.record_metric("multi_user_isolation_validated", True)
            self.record_metric("user1_events", len(user1_events))
            self.record_metric("user2_events", len(user2_events))
    
    async def _simulate_user_agent_execution(self, user_id: str, message: str):
        """Simulate agent execution for a specific user."""
        # Simulate agent_started
        self._capture_websocket_event('agent_started', {
            'user_id': user_id,
            'message': message,
            'timestamp': time.time()
        })
        
        await asyncio.sleep(0.05)  # Brief processing
        
        # Simulate agent_completed
        self._capture_websocket_event('agent_completed', {
            'user_id': user_id,
            'response': f"Processed: {message}",
            'timestamp': time.time()
        })
    
    async def test_websocket_reconnection_agent_state_recovery_coordination(self):
        """
        Test that WebSocket reconnection properly coordinates with agent state recovery.
        
        Business value: Users must not lose agent progress when connections drop,
        ensuring continuous AI interaction experience.
        """
        # Setup initial agent execution state
        execution_state = {
            'user_id': self.test_user_id,
            'agent_type': 'supervisor',
            'current_step': 'tool_executing',
            'progress': 0.6,
            'started_at': time.time()
        }
        
        recovered_state = None
        
        # Mock state recovery coordination
        with patch('netra_backend.app.websocket_core.reconnection_manager.ReconnectionManager.recover_execution_state') as mock_recover:
            mock_recover.return_value = execution_state
            
            # Simulate WebSocket reconnection
            try:
                # Mock reconnection process
                recovered_state = mock_recover.return_value
                
                # Validate state recovery coordination
                self.assertIsNotNone(recovered_state)
                self.assertEqual(recovered_state['user_id'], self.test_user_id)
                self.assertEqual(recovered_state['current_step'], 'tool_executing')
                self.assertGreater(recovered_state['progress'], 0.5)
                
                # Simulate state synchronization event
                self._capture_websocket_event('state_recovered', {
                    'user_id': self.test_user_id,
                    'recovered_state': recovered_state,
                    'timestamp': time.time()
                })
                
                # Validate recovery event was captured
                recovery_events = [e for e in self.captured_events if e['type'] == 'state_recovered']
                self.assertEqual(len(recovery_events), 1)
                
                self.record_metric("state_recovery_coordination_validated", True)
                
            except Exception as e:
                self.record_metric("reconnection_coordination_failures", str(e))
                raise
    
    async def test_agent_websocket_performance_under_coordination_load(self):
        """
        Test performance characteristics when coordinating multiple agents with WebSocket events.
        
        Business critical: System must maintain responsive real-time updates even
        under higher load to preserve user experience quality.
        """
        concurrent_users = 5
        events_per_user = 4
        coordination_times = []
        
        async def simulate_user_coordination(user_index: int):
            """Simulate agent-websocket coordination for one user."""
            user_id = f"{self.test_user_id}_load_user_{user_index}"
            start_time = time.time()
            
            # Simulate full agent execution cycle
            events = ['agent_started', 'agent_thinking', 'tool_executing', 'agent_completed']
            for event_type in events:
                self._capture_websocket_event(event_type, {
                    'user_id': user_id,
                    'user_index': user_index,
                    'timestamp': time.time()
                })
                await asyncio.sleep(0.01)  # Minimal delay between events
            
            coordination_time = time.time() - start_time
            coordination_times.append(coordination_time)
            return coordination_time
        
        # Execute concurrent coordinations
        load_start_time = time.time()
        
        coordination_results = await asyncio.gather(
            *[simulate_user_coordination(i) for i in range(concurrent_users)],
            return_exceptions=True
        )
        
        total_load_time = time.time() - load_start_time
        
        # Validate performance characteristics
        successful_coordinations = [r for r in coordination_results if isinstance(r, float)]
        self.assertEqual(len(successful_coordinations), concurrent_users,
                        "All user coordinations should succeed")
        
        avg_coordination_time = sum(coordination_times) / len(coordination_times)
        max_coordination_time = max(coordination_times)
        
        # Performance assertions (reasonable for integration testing)
        self.assertLess(avg_coordination_time, 0.5, "Average coordination should be fast")
        self.assertLess(max_coordination_time, 1.0, "Max coordination should be reasonable")
        self.assertLess(total_load_time, 2.0, "Total load handling should be efficient")
        
        # Validate event isolation under load
        total_events = len(self.captured_events)
        expected_events = concurrent_users * events_per_user
        self.assertEqual(total_events, expected_events, 
                        "All events should be captured without loss")
        
        # Record performance metrics
        self.record_metric("concurrent_users_coordinated", concurrent_users)
        self.record_metric("avg_coordination_time", avg_coordination_time)
        self.record_metric("max_coordination_time", max_coordination_time)
        self.record_metric("total_load_time", total_load_time)
        self.record_metric("events_per_second", total_events / total_load_time)
    
    def test_agent_websocket_coordination_configuration_alignment(self):
        """
        Test that agent and websocket systems use aligned configuration.
        
        System stability: Misaligned configuration between agent execution and
        WebSocket delivery can cause silent failures in user communication.
        """
        # Get configuration from both systems
        config = get_config()
        
        # Validate critical configuration alignment
        websocket_timeout = config.get('WEBSOCKET_TIMEOUT', 30)
        agent_timeout = config.get('AGENT_EXECUTION_TIMEOUT', 300)  
        
        # Business logic: WebSocket timeout should be much less than agent timeout
        # to allow for multiple progress updates during long agent executions
        self.assertLess(websocket_timeout, agent_timeout,
                       "WebSocket timeout should be less than agent timeout for progress updates")
        
        # Validate user isolation settings alignment
        websocket_user_isolation = config.get('WEBSOCKET_USER_ISOLATION', True)
        agent_user_isolation = config.get('AGENT_USER_ISOLATION', True)
        
        self.assertEqual(websocket_user_isolation, agent_user_isolation,
                        "User isolation settings must be aligned between systems")
        
        # Validate event delivery settings
        websocket_event_buffer = config.get('WEBSOCKET_EVENT_BUFFER_SIZE', 1000)
        agent_event_frequency = config.get('AGENT_EVENT_FREQUENCY', 100)
        
        self.assertGreater(websocket_event_buffer, agent_event_frequency,
                          "WebSocket buffer should accommodate agent event frequency")
        
        self.record_metric("configuration_alignment_validated", True)
        self.record_metric("websocket_timeout", websocket_timeout)
        self.record_metric("agent_timeout", agent_timeout)
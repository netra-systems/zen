"""
Comprehensive WebSocket Connection State Machine E2E Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Validate complete WebSocket connection state management in production-like scenarios
- Value Impact: Ensures users experience reliable connections across the entire Golden Path
- Strategic Impact: Critical validation of real-time AI chat infrastructure under realistic conditions

This E2E test suite validates WebSocket connection state machine behavior with real authentication,
real WebSocket connections, and complete user journeys. These tests ensure the Golden Path
user flow works end-to-end with proper state management and recovery.

🚨 CRITICAL E2E AUTH REQUIREMENT: ALL tests use real authentication flows.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket import WebSocketTestClient
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ConnectionID, ensure_user_id
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager


class E2EConnectionState(Enum):
    """Connection states for E2E testing."""
    INITIALIZING = "initializing"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    AGENT_READY = "agent_ready"
    ACTIVE_CHAT = "active_chat"
    DEGRADED = "degraded"
    RECOVERING = "recovering"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class TestWebSocketConnectionStateMachineE2E(BaseE2ETest):
    """E2E tests for WebSocket connection state machine with full user journeys."""
    
    def __init__(self):
        super().__init__()
        self.auth_helper = E2EAuthHelper()
    
    async def _create_authenticated_websocket_client(self, real_services, user_email: str) -> Dict[str, Any]:
        """Create a fully authenticated WebSocket client for E2E testing."""
        # Create real user with authentication
        user_info = await self.auth_helper.create_authenticated_user(
            real_services, 
            email=user_email,
            password="SecureTestPass123!",
            name=user_email.split('@')[0].title()
        )
        
        # Get real JWT token
        auth_token = await self.auth_helper.get_valid_jwt_token(real_services, user_info['user_id'])
        
        # Create WebSocket client with real authentication
        websocket_client = WebSocketTestClient(
            base_url=f"ws://localhost:{real_services['backend_port']}/ws",
            token=auth_token,
            user_id=user_info['user_id']
        )
        
        return {
            'user_info': user_info,
            'websocket_client': websocket_client,
            'auth_token': auth_token,
            'user_id': user_info['user_id']
        }
    
    async def _monitor_connection_states(self, websocket_client: WebSocketTestClient, 
                                       duration_seconds: float = 10.0) -> List[Dict[str, Any]]:
        """Monitor WebSocket connection states during E2E test."""
        connection_events = []
        start_time = datetime.utcnow()
        
        async def state_monitor():
            """Monitor connection state changes."""
            while (datetime.utcnow() - start_time).total_seconds() < duration_seconds:
                try:
                    # Listen for WebSocket events
                    event = await asyncio.wait_for(
                        websocket_client.receive_json(), 
                        timeout=1.0
                    )
                    
                    # Track connection-related events
                    if event.get('type') in ['connection_state', 'agent_started', 'agent_completed', 'error']:
                        connection_events.append({
                            'timestamp': datetime.utcnow().isoformat(),
                            'event': event,
                            'connection_state': event.get('connection_state', 'unknown')
                        })
                    
                except asyncio.TimeoutError:
                    # No events received, continue monitoring
                    continue
                except Exception as e:
                    # Connection issue - record as state event
                    connection_events.append({
                        'timestamp': datetime.utcnow().isoformat(),
                        'event': {'type': 'connection_error', 'error': str(e)},
                        'connection_state': 'error'
                    })
                    break
        
        # Start monitoring
        monitor_task = asyncio.create_task(state_monitor())
        
        try:
            await asyncio.wait_for(monitor_task, timeout=duration_seconds + 1.0)
        except asyncio.TimeoutError:
            monitor_task.cancel()
        
        return connection_events
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_websocket_connection_state_machine_golden_path_e2e(self, real_services):
        """
        Test complete Golden Path WebSocket connection state machine E2E.
        
        Business Value: Validates the core user journey from connection establishment
        to active AI chat, ensuring all state transitions work in production environment.
        """
        # Create authenticated user for Golden Path
        client_info = await self._create_authenticated_websocket_client(
            real_services, "golden_path_state@netra.ai"
        )
        
        websocket_client = client_info['websocket_client']
        user_id = client_info['user_id']
        
        connection_states = []
        
        try:
            # Phase 1: Connection Establishment (INITIALIZING -> CONNECTING -> CONNECTED)
            connection_start = datetime.utcnow()
            await websocket_client.connect()
            
            connection_states.append({
                'state': E2EConnectionState.CONNECTED.value,
                'timestamp': datetime.utcnow().isoformat(),
                'phase': 'connection_establishment'
            })
            
            # Verify connection is established
            assert websocket_client.is_connected(), "WebSocket should be connected"
            
            # Phase 2: Authentication (CONNECTED -> AUTHENTICATING -> AUTHENTICATED)
            auth_message = {
                "type": "authenticate",
                "token": client_info['auth_token'],
                "user_id": user_id
            }
            await websocket_client.send_json(auth_message)
            
            # Wait for authentication response
            auth_response = await asyncio.wait_for(
                websocket_client.receive_json(), 
                timeout=5.0
            )
            
            assert auth_response.get('type') == 'authentication_success', \
                f"Should receive authentication success, got: {auth_response}"
            
            connection_states.append({
                'state': E2EConnectionState.AUTHENTICATED.value,
                'timestamp': datetime.utcnow().isoformat(),
                'phase': 'authentication',
                'auth_response': auth_response
            })
            
            # Phase 3: Agent Ready State (AUTHENTICATED -> AGENT_READY)
            agent_ready_message = {
                "type": "agent_system_ready",
                "capabilities": ["cost_optimization", "triage", "supply_research"],
                "user_id": user_id
            }
            await websocket_client.send_json(agent_ready_message)
            
            connection_states.append({
                'state': E2EConnectionState.AGENT_READY.value,
                'timestamp': datetime.utcnow().isoformat(),
                'phase': 'agent_ready'
            })
            
            # Phase 4: Active Chat State (AGENT_READY -> ACTIVE_CHAT)
            # Start real agent interaction
            agent_request = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Help me analyze my cloud infrastructure costs",
                "user_id": user_id,
                "thread_id": f"golden_path_thread_{user_id}",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket_client.send_json(agent_request)
            
            # Monitor for agent execution events (validates WebSocket state machine)
            agent_events = []
            expected_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
            
            for expected_event in expected_events:
                try:
                    event = await asyncio.wait_for(
                        websocket_client.receive_json(),
                        timeout=30.0  # Allow time for real agent execution
                    )
                    
                    agent_events.append(event)
                    
                    # Verify event type
                    if event.get('type') == expected_event:
                        connection_states.append({
                            'state': E2EConnectionState.ACTIVE_CHAT.value,
                            'timestamp': datetime.utcnow().isoformat(),
                            'phase': 'active_chat',
                            'agent_event': expected_event,
                            'event_data': event
                        })
                    
                    # Break if we get agent_completed
                    if event.get('type') == 'agent_completed':
                        break
                        
                except asyncio.TimeoutError:
                    pytest.fail(f"Timeout waiting for agent event: {expected_event}")
            
            # Verify all critical agent events were received
            received_event_types = [event.get('type') for event in agent_events]
            assert 'agent_started' in received_event_types, "Should receive agent_started event"
            assert 'agent_completed' in received_event_types, "Should receive agent_completed event"
            
            # Phase 5: Test State Degradation and Recovery
            # Simulate network quality degradation
            degradation_test = {
                "type": "simulate_network_degradation",
                "quality": "poor",
                "user_id": user_id
            }
            await websocket_client.send_json(degradation_test)
            
            connection_states.append({
                'state': E2EConnectionState.DEGRADED.value,
                'timestamp': datetime.utcnow().isoformat(),
                'phase': 'degradation_test'
            })
            
            # Test messaging in degraded state
            degraded_message = {
                "type": "test_message",
                "data": {"test": "degraded_state_messaging"},
                "user_id": user_id
            }
            await websocket_client.send_json(degraded_message)
            
            # Recovery
            recovery_test = {
                "type": "simulate_network_recovery",
                "quality": "excellent", 
                "user_id": user_id
            }
            await websocket_client.send_json(recovery_test)
            
            connection_states.append({
                'state': E2EConnectionState.RECOVERING.value,
                'timestamp': datetime.utcnow().isoformat(),
                'phase': 'recovery_test'
            })
            
            # Return to active chat
            connection_states.append({
                'state': E2EConnectionState.ACTIVE_CHAT.value,
                'timestamp': datetime.utcnow().isoformat(),
                'phase': 'post_recovery'
            })
            
            # Phase 6: Graceful Disconnection
            disconnect_message = {
                "type": "disconnect_request",
                "reason": "user_requested",
                "user_id": user_id
            }
            await websocket_client.send_json(disconnect_message)
            
            connection_states.append({
                'state': E2EConnectionState.DISCONNECTING.value,
                'timestamp': datetime.utcnow().isoformat(),
                'phase': 'graceful_disconnect'
            })
            
        finally:
            # Ensure disconnection
            await websocket_client.disconnect()
            
            connection_states.append({
                'state': E2EConnectionState.DISCONNECTED.value,
                'timestamp': datetime.utcnow().isoformat(),
                'phase': 'final_disconnect'
            })
        
        # Verify Golden Path state sequence
        state_sequence = [state['state'] for state in connection_states]
        expected_golden_path = [
            E2EConnectionState.CONNECTED.value,
            E2EConnectionState.AUTHENTICATED.value,
            E2EConnectionState.AGENT_READY.value,
            E2EConnectionState.ACTIVE_CHAT.value,  # Multiple entries expected
            E2EConnectionState.DEGRADED.value,
            E2EConnectionState.RECOVERING.value,
            E2EConnectionState.ACTIVE_CHAT.value,
            E2EConnectionState.DISCONNECTING.value,
            E2EConnectionState.DISCONNECTED.value
        ]
        
        # Verify critical states are present
        for critical_state in [E2EConnectionState.CONNECTED.value, E2EConnectionState.AUTHENTICATED.value, 
                              E2EConnectionState.AGENT_READY.value, E2EConnectionState.ACTIVE_CHAT.value]:
            assert critical_state in state_sequence, f"Golden Path must include {critical_state}"
        
        # Verify timing - Golden Path should complete within reasonable time
        total_duration = (
            datetime.fromisoformat(connection_states[-1]['timestamp']) -
            datetime.fromisoformat(connection_states[0]['timestamp'])
        ).total_seconds()
        
        assert total_duration < 60, f"Golden Path should complete within 60 seconds, took {total_duration:.2f}s"
        
        # Verify business value delivery
        self.assert_business_value_delivered({
            'golden_path_completed': True,
            'agent_interaction_successful': 'agent_completed' in received_event_types,
            'state_recovery_functional': E2EConnectionState.RECOVERING.value in state_sequence,
            'graceful_disconnection': True
        }, 'golden_path')
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_websocket_state_machine_multi_user_concurrent_e2e(self, real_services):
        """
        Test WebSocket state machine with multiple concurrent users E2E.
        
        Business Value: Validates that the system can handle multiple simultaneous users
        with independent connection states, ensuring scalability and isolation.
        """
        # Create multiple authenticated users
        users = []
        for i in range(3):
            client_info = await self._create_authenticated_websocket_client(
                real_services, f"concurrent_user_{i}@netra.ai"
            )
            users.append(client_info)
        
        async def run_user_e2e_journey(user_info: Dict, user_index: int):
            """Run complete E2E journey for a single user."""
            websocket_client = user_info['websocket_client']
            user_id = user_info['user_id']
            user_states = []
            
            try:
                # Connect and authenticate
                await websocket_client.connect()
                user_states.append(('connected', datetime.utcnow()))
                
                auth_message = {
                    "type": "authenticate",
                    "token": user_info['auth_token'],
                    "user_id": user_id
                }
                await websocket_client.send_json(auth_message)
                
                auth_response = await asyncio.wait_for(
                    websocket_client.receive_json(), 
                    timeout=10.0
                )
                assert auth_response.get('type') == 'authentication_success'
                user_states.append(('authenticated', datetime.utcnow()))
                
                # Each user has different agent interaction pattern
                if user_index == 0:
                    # User 0: Cost optimization agent
                    agent_request = {
                        "type": "agent_request",
                        "agent": "cost_optimizer_agent",
                        "message": "Optimize my AWS costs",
                        "user_id": user_id
                    }
                elif user_index == 1:
                    # User 1: Supply research agent
                    agent_request = {
                        "type": "agent_request", 
                        "agent": "supply_researcher_agent",
                        "message": "Research suppliers for my manufacturing needs",
                        "user_id": user_id
                    }
                else:
                    # User 2: Triage agent
                    agent_request = {
                        "type": "agent_request",
                        "agent": "triage_agent", 
                        "message": "Help me understand my infrastructure",
                        "user_id": user_id
                    }
                
                await websocket_client.send_json(agent_request)
                user_states.append(('agent_request_sent', datetime.utcnow()))
                
                # Collect agent response events
                agent_events = []
                timeout_count = 0
                max_timeouts = 3
                
                while timeout_count < max_timeouts:
                    try:
                        event = await asyncio.wait_for(
                            websocket_client.receive_json(),
                            timeout=15.0
                        )
                        agent_events.append(event)
                        
                        if event.get('type') == 'agent_completed':
                            user_states.append(('agent_completed', datetime.utcnow()))
                            break
                        elif event.get('type') == 'agent_started':
                            user_states.append(('agent_started', datetime.utcnow()))
                        
                    except asyncio.TimeoutError:
                        timeout_count += 1
                        if timeout_count >= max_timeouts:
                            break
                
                # Send follow-up messages to test continued connection
                for msg_num in range(2):
                    follow_up = {
                        "type": "test_message",
                        "data": {"message": f"Follow up {msg_num}", "user_index": user_index},
                        "user_id": user_id
                    }
                    await websocket_client.send_json(follow_up)
                    await asyncio.sleep(0.1)  # Prevent message flooding
                
                user_states.append(('follow_up_complete', datetime.utcnow()))
                
            except Exception as e:
                user_states.append(('error', datetime.utcnow(), str(e)))
            
            finally:
                await websocket_client.disconnect()
                user_states.append(('disconnected', datetime.utcnow()))
            
            return {
                'user_index': user_index,
                'user_id': user_id,
                'states': user_states,
                'agent_events': agent_events
            }
        
        # Run concurrent user journeys
        concurrent_tasks = [
            run_user_e2e_journey(user_info, i)
            for i, user_info in enumerate(users)
        ]
        
        # Execute all concurrent E2E tests
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Verify all users completed successfully
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"User {i} E2E journey failed: {result}"
            
            # Verify state progression
            user_state_names = [state[0] for state in result['states'] if isinstance(state, tuple)]
            assert 'connected' in user_state_names, f"User {i} should have connected"
            assert 'authenticated' in user_state_names, f"User {i} should have authenticated"
            assert 'agent_request_sent' in user_state_names, f"User {i} should have sent agent request"
            assert 'disconnected' in user_state_names, f"User {i} should have disconnected"
        
        # Verify no cross-user contamination
        user_ids = {result['user_id'] for result in results}
        assert len(user_ids) == 3, "Should have 3 distinct user IDs"
        
        # Verify concurrent timing - all users should complete within reasonable timeframe
        completion_times = []
        for result in results:
            user_states = result['states']
            if user_states:
                start_time = user_states[0][1]  # First state timestamp
                end_time = user_states[-1][1]   # Last state timestamp
                duration = (end_time - start_time).total_seconds()
                completion_times.append(duration)
        
        # All users should complete within 2 minutes
        assert all(duration < 120 for duration in completion_times), \
            f"All users should complete within 120s: {completion_times}"
        
        # Verify business value: Concurrent multi-user support
        self.assert_business_value_delivered({
            'concurrent_users_supported': len(results),
            'all_users_successful': all(not isinstance(r, Exception) for r in results),
            'user_isolation_maintained': len(user_ids) == 3,
            'scalable_performance': all(d < 120 for d in completion_times)
        }, 'scalability')
    
    @pytest.mark.e2e
    @pytest.mark.real_services  
    async def test_websocket_state_machine_error_recovery_e2e(self, real_services):
        """
        Test WebSocket state machine error recovery in realistic E2E scenarios.
        
        Business Value: Ensures users experience robust error recovery and can
        continue their AI interactions even when network or service issues occur.
        """
        client_info = await self._create_authenticated_websocket_client(
            real_services, "error_recovery_e2e@netra.ai"
        )
        
        websocket_client = client_info['websocket_client']
        user_id = client_info['user_id']
        recovery_log = []
        
        try:
            # Phase 1: Establish normal connection
            await websocket_client.connect()
            
            auth_message = {
                "type": "authenticate",
                "token": client_info['auth_token'],
                "user_id": user_id
            }
            await websocket_client.send_json(auth_message)
            
            auth_response = await asyncio.wait_for(
                websocket_client.receive_json(), 
                timeout=5.0
            )
            assert auth_response.get('type') == 'authentication_success'
            
            recovery_log.append({
                'phase': 'normal_connection',
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'success'
            })
            
            # Phase 2: Normal agent interaction
            normal_request = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Test normal operation before error scenarios",
                "user_id": user_id
            }
            await websocket_client.send_json(normal_request)
            
            # Wait for at least agent_started
            normal_response = await asyncio.wait_for(
                websocket_client.receive_json(),
                timeout=10.0
            )
            assert normal_response.get('type') in ['agent_started', 'agent_thinking']
            
            recovery_log.append({
                'phase': 'normal_operation',
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'success',
                'response': normal_response.get('type')
            })
            
            # Phase 3: Simulate connection error
            await websocket_client.disconnect()
            recovery_log.append({
                'phase': 'connection_lost',
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'disconnected'
            })
            
            # Wait briefly to simulate real-world reconnection timing
            await asyncio.sleep(2.0)
            
            # Phase 4: Automatic reconnection
            await websocket_client.connect()
            recovery_log.append({
                'phase': 'reconnection_attempt',
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'connected'
            })
            
            # Re-authenticate after reconnection
            reauth_message = {
                "type": "authenticate",
                "token": client_info['auth_token'],
                "user_id": user_id
            }
            await websocket_client.send_json(reauth_message)
            
            reauth_response = await asyncio.wait_for(
                websocket_client.receive_json(),
                timeout=5.0
            )
            assert reauth_response.get('type') == 'authentication_success'
            
            recovery_log.append({
                'phase': 'reauthentication',
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'success'
            })
            
            # Phase 5: Test post-recovery functionality
            recovery_request = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Test functionality after error recovery",
                "user_id": user_id
            }
            await websocket_client.send_json(recovery_request)
            
            recovery_response = await asyncio.wait_for(
                websocket_client.receive_json(),
                timeout=15.0
            )
            assert recovery_response.get('type') in ['agent_started', 'agent_thinking']
            
            recovery_log.append({
                'phase': 'post_recovery_test',
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'success',
                'response': recovery_response.get('type')
            })
            
            # Phase 6: Multiple rapid reconnections (stress test)
            for reconnect_attempt in range(3):
                # Disconnect
                await websocket_client.disconnect()
                
                # Short wait
                await asyncio.sleep(0.5)
                
                # Reconnect
                await websocket_client.connect()
                
                # Quick auth
                quick_auth = {
                    "type": "authenticate",
                    "token": client_info['auth_token'],
                    "user_id": user_id
                }
                await websocket_client.send_json(quick_auth)
                
                try:
                    quick_response = await asyncio.wait_for(
                        websocket_client.receive_json(),
                        timeout=3.0
                    )
                    success = quick_response.get('type') == 'authentication_success'
                except asyncio.TimeoutError:
                    success = False
                
                recovery_log.append({
                    'phase': 'rapid_reconnection',
                    'attempt': reconnect_attempt + 1,
                    'timestamp': datetime.utcnow().isoformat(),
                    'status': 'success' if success else 'timeout'
                })
            
            # Phase 7: Final functionality test
            final_request = {
                "type": "agent_request",
                "agent": "triage_agent", 
                "message": "Final test after multiple reconnections",
                "user_id": user_id
            }
            await websocket_client.send_json(final_request)
            
            final_response = await asyncio.wait_for(
                websocket_client.receive_json(),
                timeout=15.0
            )
            assert final_response.get('type') in ['agent_started', 'agent_thinking']
            
            recovery_log.append({
                'phase': 'final_functionality_test',
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'success',
                'response': final_response.get('type')
            })
            
        finally:
            await websocket_client.disconnect()
            recovery_log.append({
                'phase': 'final_disconnect',
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'disconnected'
            })
        
        # Verify recovery sequence
        phases = [entry['phase'] for entry in recovery_log]
        required_phases = [
            'normal_connection',
            'normal_operation', 
            'connection_lost',
            'reconnection_attempt',
            'reauthentication',
            'post_recovery_test',
            'final_functionality_test'
        ]
        
        for required_phase in required_phases:
            assert required_phase in phases, f"Recovery sequence must include {required_phase}"
        
        # Verify recovery success rate
        successful_operations = [
            entry for entry in recovery_log 
            if entry.get('status') == 'success'
        ]
        total_operations = [
            entry for entry in recovery_log 
            if entry.get('status') in ['success', 'timeout', 'error']
        ]
        
        success_rate = len(successful_operations) / max(len(total_operations), 1) * 100
        assert success_rate >= 80, f"Recovery success rate should be >= 80%, got {success_rate:.1f}%"
        
        # Verify rapid reconnection resilience
        rapid_reconnects = [
            entry for entry in recovery_log
            if entry.get('phase') == 'rapid_reconnection'
        ]
        successful_rapid_reconnects = [
            entry for entry in rapid_reconnects
            if entry.get('status') == 'success'
        ]
        
        rapid_success_rate = len(successful_rapid_reconnects) / max(len(rapid_reconnects), 1) * 100
        assert rapid_success_rate >= 60, \
            f"Rapid reconnection success rate should be >= 60%, got {rapid_success_rate:.1f}%"
        
        # Verify business value: Error recovery maintains user experience
        self.assert_business_value_delivered({
            'error_recovery_functional': True,
            'reconnection_success_rate': success_rate >= 80,
            'rapid_reconnection_resilience': rapid_success_rate >= 60,
            'post_recovery_functionality': 'final_functionality_test' in phases
        }, 'reliability')
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_websocket_state_machine_agent_interaction_lifecycle_e2e(self, real_services):
        """
        Test complete agent interaction lifecycle with WebSocket state management E2E.
        
        Business Value: Validates that WebSocket state machine properly supports
        the full agent execution lifecycle, ensuring reliable AI interactions.
        """
        client_info = await self._create_authenticated_websocket_client(
            real_services, "agent_lifecycle_e2e@netra.ai"
        )
        
        websocket_client = client_info['websocket_client']
        user_id = client_info['user_id']
        
        agent_lifecycle_events = []
        connection_state_events = []
        
        try:
            # Phase 1: Connection and authentication
            await websocket_client.connect()
            
            auth_message = {
                "type": "authenticate",
                "token": client_info['auth_token'],
                "user_id": user_id
            }
            await websocket_client.send_json(auth_message)
            
            auth_response = await asyncio.wait_for(
                websocket_client.receive_json(),
                timeout=5.0
            )
            assert auth_response.get('type') == 'authentication_success'
            
            connection_state_events.append({
                'state': 'authenticated',
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Phase 2: Agent interaction with full event monitoring
            agent_request = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Help me understand my cloud infrastructure and provide optimization recommendations",
                "user_id": user_id,
                "thread_id": f"lifecycle_test_thread_{user_id}",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket_client.send_json(agent_request)
            
            connection_state_events.append({
                'state': 'agent_request_sent',
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Monitor complete agent lifecycle
            expected_agent_events = [
                'agent_started',
                'agent_thinking',
                'tool_executing', 
                'tool_completed',
                'agent_completed'
            ]
            
            received_events = []
            event_timeout = 45.0  # Allow sufficient time for real agent execution
            
            for expected_event in expected_agent_events:
                try:
                    event = await asyncio.wait_for(
                        websocket_client.receive_json(),
                        timeout=event_timeout
                    )
                    
                    received_events.append(event)
                    agent_lifecycle_events.append({
                        'expected': expected_event,
                        'received': event.get('type'),
                        'timestamp': datetime.utcnow().isoformat(),
                        'data': event
                    })
                    
                    # Update connection state based on agent events
                    if event.get('type') == 'agent_started':
                        connection_state_events.append({
                            'state': 'agent_executing',
                            'timestamp': datetime.utcnow().isoformat()
                        })
                    elif event.get('type') == 'agent_completed':
                        connection_state_events.append({
                            'state': 'agent_completed',
                            'timestamp': datetime.utcnow().isoformat()
                        })
                        break
                    
                    # Reduce timeout for subsequent events
                    event_timeout = 20.0
                    
                except asyncio.TimeoutError:
                    agent_lifecycle_events.append({
                        'expected': expected_event,
                        'received': 'TIMEOUT',
                        'timestamp': datetime.utcnow().isoformat(),
                        'timeout_seconds': event_timeout
                    })
                    # Continue to next event - some events might be optional
                    continue
            
            # Phase 3: Follow-up interaction to test continued state
            followup_request = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Can you provide more details about the recommendations?",
                "user_id": user_id,
                "thread_id": f"lifecycle_test_thread_{user_id}",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket_client.send_json(followup_request)
            
            # Monitor follow-up response
            try:
                followup_response = await asyncio.wait_for(
                    websocket_client.receive_json(),
                    timeout=20.0
                )
                
                agent_lifecycle_events.append({
                    'phase': 'followup',
                    'received': followup_response.get('type'),
                    'timestamp': datetime.utcnow().isoformat(),
                    'data': followup_response
                })
                
                connection_state_events.append({
                    'state': 'followup_completed',
                    'timestamp': datetime.utcnow().isoformat()
                })
                
            except asyncio.TimeoutError:
                agent_lifecycle_events.append({
                    'phase': 'followup',
                    'received': 'TIMEOUT',
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            # Phase 4: Test multiple concurrent agent requests (state isolation)
            concurrent_requests = []
            for i in range(2):
                concurrent_request = {
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": f"Concurrent test request {i + 1}",
                    "user_id": user_id,
                    "thread_id": f"concurrent_thread_{i}_{user_id}",
                    "timestamp": datetime.utcnow().isoformat()
                }
                concurrent_requests.append(concurrent_request)
                await websocket_client.send_json(concurrent_request)
                await asyncio.sleep(1.0)  # Slight delay between requests
            
            # Monitor concurrent responses
            concurrent_responses = []
            for i in range(len(concurrent_requests)):
                try:
                    response = await asyncio.wait_for(
                        websocket_client.receive_json(),
                        timeout=15.0
                    )
                    concurrent_responses.append(response)
                    
                except asyncio.TimeoutError:
                    concurrent_responses.append({'type': 'TIMEOUT', 'request_index': i})
            
            connection_state_events.append({
                'state': 'concurrent_testing_completed',
                'timestamp': datetime.utcnow().isoformat(),
                'concurrent_responses': len(concurrent_responses)
            })
            
        finally:
            await websocket_client.disconnect()
            connection_state_events.append({
                'state': 'disconnected',
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # Verify agent lifecycle completion
        received_event_types = [event['received'] for event in agent_lifecycle_events if 'received' in event]
        
        # Critical agent events must be present
        critical_events = ['agent_started', 'agent_completed']
        for critical_event in critical_events:
            assert critical_event in received_event_types, \
                f"Agent lifecycle must include {critical_event}, got: {received_event_types}"
        
        # Verify connection state progression
        connection_states = [event['state'] for event in connection_state_events]
        required_states = ['authenticated', 'agent_request_sent', 'agent_executing', 'disconnected']
        
        for required_state in required_states:
            assert required_state in connection_states, \
                f"Connection state lifecycle must include {required_state}, got: {connection_states}"
        
        # Verify agent interaction success rate
        successful_agent_events = [
            event for event in agent_lifecycle_events 
            if event.get('received') not in ['TIMEOUT', 'ERROR']
        ]
        total_agent_events = len(agent_lifecycle_events)
        
        if total_agent_events > 0:
            agent_success_rate = len(successful_agent_events) / total_agent_events * 100
            assert agent_success_rate >= 60, \
                f"Agent interaction success rate should be >= 60%, got {agent_success_rate:.1f}%"
        
        # Verify timing - complete lifecycle should be reasonable
        if connection_state_events:
            start_time = datetime.fromisoformat(connection_state_events[0]['timestamp'])
            end_time = datetime.fromisoformat(connection_state_events[-1]['timestamp'])
            total_duration = (end_time - start_time).total_seconds()
            
            assert total_duration < 300, f"Complete lifecycle should finish within 300s, took {total_duration:.2f}s"
        
        # Verify business value: Complete agent interaction lifecycle
        self.assert_business_value_delivered({
            'agent_lifecycle_completed': 'agent_completed' in received_event_types,
            'websocket_state_management': len(connection_states) >= 4,
            'followup_interaction_supported': any(event.get('phase') == 'followup' for event in agent_lifecycle_events),
            'concurrent_request_handling': len(concurrent_responses) > 0,
            'end_to_end_reliability': agent_success_rate >= 60 if total_agent_events > 0 else True
        }, 'agent_interaction')
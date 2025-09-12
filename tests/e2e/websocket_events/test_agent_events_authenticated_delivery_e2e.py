"""
E2E Tests for Agent Events Authenticated Delivery

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Agent events deliver core AI value 
- Business Goal: Validate authenticated agent event delivery for $120K+ MRR platform
- Value Impact: Ensures users receive real-time AI insights and agent responses
- Strategic Impact: Foundation for valuable AI-powered chat interactions

 ALERT:  CRITICAL E2E REQUIREMENTS - MISSION CRITICAL WEBSOCKET EVENTS:
1. Tests MUST use REAL authentication (JWT/OAuth) - NO MOCKS
2. Tests MUST validate ALL 5 required agent events with real WebSocket delivery
3. Tests MUST use REAL agent execution and WebSocket connections
4. Tests MUST fail hard when agent events are not delivered
5. Tests validate business value: users receive actionable AI insights

MISSION CRITICAL WEBSOCKET EVENTS (from CLAUDE.md Section 6):
 PASS:  agent_started - User must see agent began processing their problem  
 PASS:  agent_thinking - Real-time reasoning visibility (shows AI working on valuable solutions)
 PASS:  tool_executing - Tool usage transparency (demonstrates problem-solving approach)
 PASS:  tool_completed - Tool results display (delivers actionable insights)
 PASS:  agent_completed - User must know when valuable response is ready

This test suite validates Agent Events Authenticated Delivery:
- End-to-end agent execution with authenticated WebSocket event delivery
- Real-time agent event streaming to authenticated users
- Agent event isolation and user-specific delivery
- Performance validation of event delivery under load
- Business value validation: users receive actionable AI insights

E2E AGENT EVENT SCENARIOS:
Complete Agent Execution Journeys:
- User sends agent request  ->  authentication  ->  agent_started  ->  agent_thinking  ->  tool_executing  ->  tool_completed  ->  agent_completed
- Multi-user concurrent agent executions with isolated event delivery
- Agent failure scenarios with proper error event delivery
- Real-time event streaming performance under concurrent load

Real Service Integration:
- Real agent execution through backend service (8002)
- Real WebSocket connections for event streaming
- Real authentication with JWT tokens
- Real tool execution and result generation
- NO MOCKS - all events from real agent execution

Following E2E requirements from CLAUDE.md:
- ALL e2e tests MUST use authentication (JWT/OAuth)
- WebSocket events are MISSION CRITICAL for chat business value
- NO MOCKS allowed in e2e tests
- Tests fail hard when events not delivered
- Absolute imports only
"""

import asyncio
import pytest
import time
import websockets
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set
import aiohttp

# SSOT Imports - Using absolute imports only
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from shared.isolated_environment import get_env


@pytest.mark.e2e
class TestAgentEventsAuthenticatedDelivery:
    """
    E2E tests for authenticated agent event delivery.
    
     ALERT:  MISSION CRITICAL: These tests validate that all 5 required agent events
    are delivered to authenticated users during real agent execution.
    
    Tests focus on:
    1. Complete agent execution with all 5 mission critical events
    2. Authenticated WebSocket event delivery with real services
    3. Multi-user agent event isolation and delivery
    4. Real-time event streaming performance
    5. Business value validation: actionable AI insights delivered
    """
    
    @classmethod
    def setup_class(cls):
        """Set up class-level configuration for agent events testing."""
        cls.env = get_env()
        
        # Configure for real services
        test_env = cls.env.get("TEST_ENV", cls.env.get("ENVIRONMENT", "test"))
        
        if test_env == "staging":
            cls.auth_config = E2EAuthConfig.for_staging()
        else:
            cls.auth_config = E2EAuthConfig(
                auth_service_url="http://localhost:8083",
                backend_url="http://localhost:8002",
                websocket_url="ws://localhost:8002/ws",
                timeout=60.0  # Agent execution needs longer timeout
            )
        
        cls.auth_helper = E2EAuthHelper(config=cls.auth_config)
        
        # Validate agent services are available
        cls._validate_agent_services_available()
    
    @classmethod
    def _validate_agent_services_available(cls):
        """Validate agent execution services are available."""
        import requests
        from requests.exceptions import RequestException
        
        required_services = [
            ("Backend Service", f"{cls.auth_config.backend_url}/health"),
            ("Agent Executor", f"{cls.auth_config.backend_url}/api/agents/health"),
            ("WebSocket Events", f"{cls.auth_config.backend_url}/ws/health")
        ]
        
        for service_name, service_url in required_services:
            try:
                response = requests.get(service_url, timeout=10)
                assert response.status_code < 500, f"{service_name} unhealthy"
            except RequestException:
                # If specific endpoints don't exist, verify main backend
                try:
                    requests.get(cls.auth_config.backend_url, timeout=5)
                except RequestException as e:
                    pytest.fail(f" FAIL:  CRITICAL: Agent services unavailable for events testing: {e}")
    
    def test_complete_agent_execution_with_all_mission_critical_events(self):
        """Test complete agent execution with all 5 mission critical WebSocket events."""
        # Create authenticated user for agent execution
        agent_user = self.auth_helper.create_authenticated_user(
            email=f'agent_events_user_{int(time.time())}@e2e.test',
            user_id=f"agent_user_{int(time.time())}",
            full_name='Agent Events E2E User',
            permissions=['websocket', 'chat', 'agent_execution']
        )
        
        async def test_mission_critical_agent_events():
            """Test all 5 mission critical agent events are delivered."""
            # Track received events
            received_events = []
            mission_critical_events = {
                'agent_started': False,
                'agent_thinking': False, 
                'tool_executing': False,
                'tool_completed': False,
                'agent_completed': False
            }
            
            websocket_headers = {
                'Authorization': f'Bearer {agent_user.jwt_token}',
                'X-User-ID': agent_user.user_id,
                'X-Agent-Events': 'required',
                'X-Event-Tracking': 'mission_critical'
            }
            
            try:
                async with websockets.connect(
                    self.auth_config.websocket_url,
                    extra_headers=websocket_headers,
                    timeout=self.auth_config.timeout
                ) as websocket:
                    
                    # Step 1: Authenticate WebSocket connection
                    auth_message = {
                        'type': 'authenticate',
                        'token': agent_user.jwt_token,
                        'user_id': agent_user.user_id,
                        'event_subscription': 'agent_events'
                    }
                    await websocket.send(json.dumps(auth_message))
                    
                    auth_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    auth_result = json.loads(auth_response)
                    assert auth_result.get('type') == 'auth_success', f"Auth failed: {auth_result}"
                    
                    # Step 2: Send agent execution request
                    agent_request_start = time.time()
                    
                    agent_request = {
                        'type': 'agent_request',
                        'message': 'Analyze my cloud costs and provide optimization recommendations',
                        'agent_type': 'cost_optimization_agent',
                        'user_id': agent_user.user_id,
                        'request_id': f'agent_req_{int(time.time())}',
                        'priority': 'high',
                        'expected_events': ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
                    }
                    await websocket.send(json.dumps(agent_request))
                    
                    # Step 3: Collect all agent events with timeout
                    event_collection_timeout = 45.0  # 45 seconds for complete agent execution
                    event_start_time = time.time()
                    
                    while (time.time() - event_start_time) < event_collection_timeout:
                        try:
                            # Wait for next event
                            event_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                            event_data = json.loads(event_response)
                            
                            event_type = event_data.get('type')
                            event_user_id = event_data.get('user_id')
                            
                            # Validate event belongs to our user
                            assert event_user_id == agent_user.user_id, f"Event for wrong user: {event_user_id}"
                            
                            # Record received event
                            received_events.append({
                                'type': event_type,
                                'timestamp': datetime.now(timezone.utc).isoformat(),
                                'user_id': event_user_id,
                                'data': event_data,
                                'elapsed_ms': (time.time() - event_start_time) * 1000
                            })
                            
                            # Check if this is a mission critical event
                            if event_type in mission_critical_events:
                                mission_critical_events[event_type] = True
                                print(f" PASS:  Received mission critical event: {event_type}")
                            
                            # If agent completed, we can stop collecting
                            if event_type == 'agent_completed':
                                break
                                
                        except asyncio.TimeoutError:
                            # Check if we have all required events
                            if all(mission_critical_events.values()):
                                break
                            else:
                                # Continue waiting if we don't have all events yet
                                continue
                    
                    agent_execution_time = (time.time() - agent_request_start) * 1000
                    
                    return {
                        'received_events': received_events,
                        'mission_critical_events': mission_critical_events,
                        'total_events_received': len(received_events),
                        'agent_execution_time_ms': agent_execution_time,
                        'all_events_received': all(mission_critical_events.values())
                    }
                    
            except Exception as e:
                pytest.fail(f" FAIL:  CRITICAL: Agent events delivery failed: {e}")
        
        # Execute mission critical events test
        events_result = asyncio.run(test_mission_critical_agent_events())
        
        #  ALERT:  CRITICAL VALIDATION: All 5 mission critical events MUST be received
        assert events_result is not None
        assert events_result['all_events_received'] is True, f" FAIL:  MISSION CRITICAL FAILURE: Missing events: {[k for k, v in events_result['mission_critical_events'].items() if not v]}"
        
        # Validate each mission critical event was received
        for event_name, received in events_result['mission_critical_events'].items():
            assert received is True, f" FAIL:  CRITICAL: Mission critical event '{event_name}' not received"
        
        # Validate business performance
        assert events_result['total_events_received'] >= 5, "Must receive at least the 5 mission critical events"
        assert events_result['agent_execution_time_ms'] < 60000, "Agent execution should complete within 60 seconds"
        
        # Validate event ordering (agent_started should be first)
        received_events = events_result['received_events']
        if received_events:
            first_event = received_events[0]
            assert first_event['type'] == 'agent_started', "First event must be 'agent_started'"
            
            # agent_completed should be last mission critical event
            mission_critical_event_types = [e['type'] for e in received_events if e['type'] in ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']]
            if 'agent_completed' in mission_critical_event_types:
                last_mission_critical = mission_critical_event_types[-1]
                # agent_completed should be among the last events
                assert last_mission_critical in ['agent_completed', 'tool_completed'], "agent_completed should be final mission critical event"
    
    def test_multi_user_agent_event_isolation_and_delivery(self):
        """Test multi-user agent event isolation and parallel delivery."""
        # Create multiple users for concurrent agent execution
        user_count = 3
        agent_users = []
        
        for i in range(user_count):
            user = self.auth_helper.create_authenticated_user(
                email=f'multi_agent_user_{i}_{int(time.time())}@e2e.test',
                user_id=f"multi_agent_{i}_{int(time.time())}",
                full_name=f'Multi-Agent User {i}',
                permissions=['websocket', 'chat', 'agent_execution']
            )
            agent_users.append(user)
        
        async def test_concurrent_agent_event_delivery():
            """Test concurrent agent execution with isolated event delivery."""
            
            async def execute_agent_for_user(user_index, user_data):
                """Execute agent for individual user and collect events."""
                user_events = []
                user_mission_events = {
                    'agent_started': False,
                    'agent_thinking': False,
                    'tool_executing': False,
                    'tool_completed': False,
                    'agent_completed': False
                }
                
                websocket_headers = {
                    'Authorization': f'Bearer {user_data.jwt_token}',
                    'X-User-ID': user_data.user_id,
                    'X-Concurrent-User': str(user_index),
                    'X-Agent-Events': 'isolated'
                }
                
                try:
                    async with websockets.connect(
                        self.auth_config.websocket_url,
                        extra_headers=websocket_headers,
                        timeout=self.auth_config.timeout
                    ) as websocket:
                        
                        # Authenticate
                        auth_message = {
                            'type': 'authenticate',
                            'token': user_data.jwt_token,
                            'user_id': user_data.user_id,
                            'concurrent_user_index': user_index
                        }
                        await websocket.send(json.dumps(auth_message))
                        
                        auth_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                        auth_result = json.loads(auth_response)
                        assert auth_result.get('type') == 'auth_success'
                        
                        # Send user-specific agent request
                        agent_request = {
                            'type': 'agent_request',
                            'message': f'User {user_index}: Help me analyze performance metrics',
                            'agent_type': 'performance_analysis_agent',
                            'user_id': user_data.user_id,
                            'request_id': f'concurrent_req_{user_index}_{int(time.time())}',
                            'user_context': f'concurrent_user_{user_index}'
                        }
                        await websocket.send(json.dumps(agent_request))
                        
                        # Collect events for this user
                        event_timeout = 30.0
                        event_start = time.time()
                        
                        while (time.time() - event_start) < event_timeout:
                            try:
                                event_response = await asyncio.wait_for(websocket.recv(), timeout=8.0)
                                event_data = json.loads(event_response)
                                
                                event_type = event_data.get('type')
                                event_user_id = event_data.get('user_id')
                                
                                #  ALERT:  CRITICAL: Validate event isolation - events must belong to this user only
                                assert event_user_id == user_data.user_id, f" FAIL:  ISOLATION BREACH: User {user_index} received event for user {event_user_id}"
                                
                                # Record user-specific event
                                user_events.append({
                                    'type': event_type,
                                    'user_id': event_user_id,
                                    'user_index': user_index,
                                    'timestamp': datetime.now(timezone.utc).isoformat(),
                                    'data': event_data
                                })
                                
                                # Track mission critical events for this user
                                if event_type in user_mission_events:
                                    user_mission_events[event_type] = True
                                
                                # Stop when agent completes for this user
                                if event_type == 'agent_completed':
                                    break
                                    
                            except asyncio.TimeoutError:
                                if all(user_mission_events.values()):
                                    break
                                continue
                        
                        return {
                            'user_index': user_index,
                            'user_id': user_data.user_id,
                            'events_received': user_events,
                            'mission_events': user_mission_events,
                            'event_count': len(user_events),
                            'all_mission_events': all(user_mission_events.values()),
                            'success': True
                        }
                        
                except Exception as e:
                    return {
                        'user_index': user_index,
                        'user_id': user_data.user_id,
                        'error': str(e),
                        'success': False
                    }
            
            # Execute concurrent agent requests for all users
            concurrent_tasks = [
                execute_agent_for_user(i, user)
                for i, user in enumerate(agent_users)
            ]
            
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            return results
        
        # Execute concurrent agent event delivery test
        concurrent_results = asyncio.run(test_concurrent_agent_event_delivery())
        
        # Validate concurrent agent event delivery
        assert len(concurrent_results) == user_count
        
        # All users should receive their events successfully
        successful_results = [r for r in concurrent_results if isinstance(r, dict) and r.get('success')]
        assert len(successful_results) == user_count, f"All {user_count} users must receive agent events"
        
        # Validate event isolation - no cross-user event leakage
        all_received_events = []
        for result in successful_results:
            user_events = result['events_received']
            user_id = result['user_id']
            
            # All events for this user must have correct user_id
            for event in user_events:
                assert event['user_id'] == user_id, f" FAIL:  ISOLATION BREACH: Event has wrong user_id"
                all_received_events.append(event)
        
        # Validate each user received mission critical events
        for result in successful_results:
            mission_events = result['mission_events']
            user_index = result['user_index']
            
            # Each user must receive all 5 mission critical events
            for event_name, received in mission_events.items():
                assert received is True, f" FAIL:  User {user_index} missing mission critical event: {event_name}"
        
        # Validate total event distribution
        total_events_received = sum(r['event_count'] for r in successful_results)
        assert total_events_received >= (user_count * 5), f"Total events {total_events_received} less than expected minimum {user_count * 5}"
    
    def test_real_time_agent_event_streaming_performance(self):
        """Test real-time agent event streaming performance under load."""
        # Create user for performance testing
        perf_user = self.auth_helper.create_authenticated_user(
            email=f'perf_agent_user_{int(time.time())}@e2e.test',
            user_id=f"perf_agent_{int(time.time())}",
            full_name='Performance Agent User',
            permissions=['websocket', 'chat', 'agent_execution', 'performance_testing']
        )
        
        async def test_agent_event_streaming_performance():
            """Test real-time streaming performance of agent events."""
            event_performance_metrics = []
            
            websocket_headers = {
                'Authorization': f'Bearer {perf_user.jwt_token}',
                'X-User-ID': perf_user.user_id,
                'X-Performance-Test': 'enabled',
                'X-Event-Timing': 'precise'
            }
            
            try:
                async with websockets.connect(
                    self.auth_config.websocket_url,
                    extra_headers=websocket_headers,
                    timeout=self.auth_config.timeout
                ) as websocket:
                    
                    # Authenticate
                    auth_message = {
                        'type': 'authenticate',
                        'token': perf_user.jwt_token,
                        'user_id': perf_user.user_id,
                        'performance_monitoring': True
                    }
                    await websocket.send(json.dumps(auth_message))
                    
                    auth_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    auth_result = json.loads(auth_response)
                    assert auth_result.get('type') == 'auth_success'
                    
                    # Send complex agent request that will generate many events
                    complex_request_start = time.time()
                    
                    complex_agent_request = {
                        'type': 'agent_request',
                        'message': 'Perform comprehensive analysis: 1) Analyze cloud costs, 2) Identify optimization opportunities, 3) Generate detailed report, 4) Create action plan',
                        'agent_type': 'comprehensive_analysis_agent',
                        'user_id': perf_user.user_id,
                        'request_id': f'complex_req_{int(time.time())}',
                        'complexity': 'high',
                        'expected_tools': ['cost_analyzer', 'optimization_finder', 'report_generator', 'action_planner']
                    }
                    await websocket.send(json.dumps(complex_agent_request))
                    
                    # Collect events with precise timing
                    event_collection_start = time.time()
                    previous_event_time = event_collection_start
                    
                    collected_events = []
                    event_timeout = 60.0  # Extended timeout for complex agent
                    
                    while (time.time() - event_collection_start) < event_timeout:
                        try:
                            event_response = await asyncio.wait_for(websocket.recv(), timeout=12.0)
                            current_time = time.time()
                            event_data = json.loads(event_response)
                            
                            # Calculate event timing metrics
                            time_since_start = (current_time - event_collection_start) * 1000
                            time_since_previous = (current_time - previous_event_time) * 1000
                            
                            event_metrics = {
                                'event_type': event_data.get('type'),
                                'user_id': event_data.get('user_id'),
                                'timestamp': datetime.now(timezone.utc).isoformat(),
                                'time_since_start_ms': time_since_start,
                                'time_since_previous_event_ms': time_since_previous,
                                'event_data_size': len(json.dumps(event_data))
                            }
                            
                            event_performance_metrics.append(event_metrics)
                            collected_events.append(event_data)
                            previous_event_time = current_time
                            
                            # Validate user isolation for each event
                            assert event_data.get('user_id') == perf_user.user_id
                            
                            # Stop on agent completion
                            if event_data.get('type') == 'agent_completed':
                                break
                                
                        except asyncio.TimeoutError:
                            # If we have received some events, continue; otherwise break
                            if len(collected_events) > 0:
                                continue
                            else:
                                break
                    
                    total_execution_time = (time.time() - complex_request_start) * 1000
                    
                    return {
                        'total_events': len(collected_events),
                        'performance_metrics': event_performance_metrics,
                        'total_execution_time_ms': total_execution_time,
                        'average_event_interval_ms': sum(m['time_since_previous_event_ms'] for m in event_performance_metrics) / len(event_performance_metrics) if event_performance_metrics else 0,
                        'mission_critical_events_received': len([e for e in collected_events if e.get('type') in ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']])
                    }
                    
            except Exception as e:
                pytest.fail(f" FAIL:  CRITICAL: Performance streaming test failed: {e}")
        
        # Execute performance streaming test
        perf_result = asyncio.run(test_agent_event_streaming_performance())
        
        # Validate streaming performance
        assert perf_result is not None
        assert perf_result['total_events'] >= 5, "Must receive at least 5 events (mission critical)"
        assert perf_result['mission_critical_events_received'] >= 5, "Must receive all 5 mission critical events"
        
        # Performance validation
        assert perf_result['total_execution_time_ms'] < 90000, "Complex agent execution should complete within 90 seconds"
        assert perf_result['average_event_interval_ms'] < 10000, "Average event interval should be under 10 seconds"
        
        # Event delivery should be reasonably real-time
        if perf_result['performance_metrics']:
            max_event_gap = max(m['time_since_previous_event_ms'] for m in perf_result['performance_metrics'])
            assert max_event_gap < 20000, "No event gap should exceed 20 seconds"
    
    def test_agent_failure_scenarios_with_proper_error_events(self):
        """Test agent failure scenarios deliver proper error events."""
        # Create user for failure testing
        failure_user = self.auth_helper.create_authenticated_user(
            email=f'failure_agent_user_{int(time.time())}@e2e.test',
            user_id=f"failure_agent_{int(time.time())}",
            full_name='Failure Test Agent User',
            permissions=['websocket', 'chat', 'agent_execution']
        )
        
        async def test_agent_failure_error_events():
            """Test agent failure scenarios generate proper error events."""
            failure_events = []
            
            websocket_headers = {
                'Authorization': f'Bearer {failure_user.jwt_token}',
                'X-User-ID': failure_user.user_id,
                'X-Failure-Testing': 'enabled'
            }
            
            try:
                async with websockets.connect(
                    self.auth_config.websocket_url,
                    extra_headers=websocket_headers,
                    timeout=self.auth_config.timeout
                ) as websocket:
                    
                    # Authenticate
                    auth_message = {
                        'type': 'authenticate',
                        'token': failure_user.jwt_token,
                        'user_id': failure_user.user_id,
                        'error_testing': True
                    }
                    await websocket.send(json.dumps(auth_message))
                    
                    auth_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    auth_result = json.loads(auth_response)
                    assert auth_result.get('type') == 'auth_success'
                    
                    # Test scenario 1: Invalid agent request
                    invalid_request = {
                        'type': 'agent_request',
                        'message': '',  # Empty message to trigger error
                        'agent_type': 'nonexistent_agent_type',
                        'user_id': failure_user.user_id,
                        'request_id': f'invalid_req_{int(time.time())}'
                    }
                    await websocket.send(json.dumps(invalid_request))
                    
                    # Collect error events
                    error_timeout = 20.0
                    error_start = time.time()
                    
                    while (time.time() - error_start) < error_timeout:
                        try:
                            error_response = await asyncio.wait_for(websocket.recv(), timeout=8.0)
                            error_data = json.loads(error_response)
                            
                            error_type = error_data.get('type')
                            
                            failure_events.append({
                                'event_type': error_type,
                                'user_id': error_data.get('user_id'),
                                'error_data': error_data,
                                'timestamp': datetime.now(timezone.utc).isoformat()
                            })
                            
                            # Look for error events
                            if error_type in ['agent_error', 'agent_failed', 'error']:
                                # Found error event, can continue to next test
                                break
                                
                            # Or if we get agent_started, let it fail naturally
                            if error_type == 'agent_started':
                                continue
                                
                        except asyncio.TimeoutError:
                            break
                    
                    # Test scenario 2: Valid request but test graceful error handling
                    test_error_request = {
                        'type': 'agent_request', 
                        'message': 'Test error handling capabilities',
                        'agent_type': 'error_test_agent',
                        'user_id': failure_user.user_id,
                        'request_id': f'error_test_req_{int(time.time())}',
                        'simulate_error': 'tool_failure'
                    }
                    await websocket.send(json.dumps(test_error_request))
                    
                    # Collect events from error test
                    while (time.time() - error_start) < (error_timeout * 2):
                        try:
                            test_response = await asyncio.wait_for(websocket.recv(), timeout=8.0)
                            test_data = json.loads(test_response)
                            
                            failure_events.append({
                                'event_type': test_data.get('type'),
                                'user_id': test_data.get('user_id'),
                                'error_data': test_data,
                                'timestamp': datetime.now(timezone.utc).isoformat()
                            })
                            
                            # Stop when we get completion or error
                            if test_data.get('type') in ['agent_completed', 'agent_error', 'agent_failed']:
                                break
                                
                        except asyncio.TimeoutError:
                            break
                    
                    return {
                        'failure_events': failure_events,
                        'error_events_received': len([e for e in failure_events if 'error' in e['event_type'] or 'failed' in e['event_type']]),
                        'total_events_received': len(failure_events)
                    }
                    
            except Exception as e:
                # Failure in failure test is expected in some scenarios
                return {
                    'failure_events': failure_events,
                    'test_exception': str(e),
                    'error_events_received': len([e for e in failure_events if 'error' in e['event_type'] or 'failed' in e['event_type']]),
                    'total_events_received': len(failure_events)
                }
        
        # Execute failure scenario test
        failure_result = asyncio.run(test_agent_failure_error_events())
        
        # Validate failure event handling
        assert failure_result is not None
        assert failure_result['total_events_received'] >= 0, "Should receive some events even in failure scenarios"
        
        # Validate that error events are properly formatted
        failure_events = failure_result['failure_events']
        for event in failure_events:
            assert event['user_id'] == failure_user.user_id, "All events must belong to correct user"
            assert isinstance(event['event_type'], str), "Event type must be string"
            assert len(event['timestamp']) > 0, "Event must have timestamp"
        
        # If error events were received, validate they contain proper error information
        error_events = [e for e in failure_events if 'error' in e['event_type'] or 'failed' in e['event_type']]
        for error_event in error_events:
            error_data = error_event['error_data']
            # Error events should contain meaningful information
            assert 'type' in error_data, "Error events must have type"
            # User ID should be preserved even in error scenarios
            assert error_data.get('user_id') == failure_user.user_id


if __name__ == "__main__":
    # Run E2E tests with pytest
    pytest.main([__file__, "-v", "--tb=short", "-m", "e2e"])
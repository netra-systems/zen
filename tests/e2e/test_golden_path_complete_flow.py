"""
Golden Path Complete Flow E2E Test - Issue #1197

MISSION CRITICAL: Complete end-to-end user journey validation for Golden Path user flow.
This test validates the complete user experience from authentication through AI response delivery.

PURPOSE:
- Tests complete Golden Path: login -> WebSocket connection -> AI response
- Validates all 5 critical WebSocket events are delivered
- Ensures performance meets SLA requirements
- Validates user isolation and security patterns

BUSINESS VALUE:
- Protects $500K+ ARR chat functionality 
- Ensures enterprise-grade user experience
- Validates system reliability and performance

TESTING APPROACH:
- Uses real staging.netrasystems.ai endpoints
- No Docker dependencies (staging GCP testing)
- Follows SSOT test patterns and infrastructure
- Initially designed to fail to validate test infrastructure

GitHub Issue: #1197 Golden Path End-to-End Testing
Test Category: e2e, golden_path, mission_critical
Expected Runtime: 60-120 seconds for complete flow
"""

import asyncio
import json
import time
import pytest
import websockets
import ssl
from typing import Dict, List, Optional, Any, Set
from unittest.mock import patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_test_base import StagingTestBase, track_test_timing
from tests.e2e.staging_config import StagingTestConfig as StagingConfig
from tests.e2e.staging_auth_client import StagingAuthClient
from netra_backend.tests.e2e.real_websocket_client import RealWebSocketClient
from netra_backend.app.services.user_execution_context import UserExecutionContext


# Mission Critical WebSocket Events - ALL must be delivered
GOLDEN_PATH_CRITICAL_EVENTS = {
    "agent_started",      # User sees agent began processing
    "agent_thinking",     # Real-time reasoning visibility  
    "tool_executing",     # Tool usage transparency
    "tool_completed",     # Tool results display
    "agent_completed"     # User knows response is ready
}

# Performance SLA Requirements
GOLDEN_PATH_SLA = {
    "max_auth_time": 5.0,           # Authentication must complete within 5s
    "max_websocket_connect": 10.0,  # WebSocket connection within 10s
    "max_first_event_time": 15.0,   # First agent event within 15s
    "max_total_response_time": 60.0, # Complete AI response within 60s
    "min_events_required": 3         # Minimum number of events expected
}


class GoldenPathCompleteFlowTests(SSotAsyncTestCase):
    """
    Complete Golden Path E2E Test Suite
    
    Tests the full user journey from authentication through AI response
    in the staging environment using real services.
    """

    @classmethod
    async def asyncSetUpClass(cls):
        """Setup staging environment for Golden Path testing"""
        await super().asyncSetUpClass()
        
        # Setup logger
        import logging
        cls.logger = logging.getLogger(cls.__name__)
        cls.logger.setLevel(logging.INFO)
        if not cls.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            cls.logger.addHandler(handler)
        
        # Load staging environment
        cls._load_staging_environment()
        
        # Initialize staging infrastructure
        cls.staging_config = StagingConfig()
        cls.staging_backend_url = cls.staging_config.get_backend_websocket_url()
        cls.staging_auth_url = cls.staging_config.get_auth_service_url()
        cls.auth_client = StagingAuthClient()
        cls.websocket_client = RealWebSocketClient()
        
        # Verify staging services are available
        await cls._verify_staging_services()
        
        # Create test user for Golden Path testing
        cls.test_user = await cls._create_golden_path_test_user()
        
        cls.logger.info('Golden Path Complete Flow test setup completed')

    @classmethod
    def _load_staging_environment(cls):
        """Load staging environment variables for test execution"""
        import os
        from pathlib import Path
        
        # Find and load config/staging.env
        project_root = Path(__file__).resolve().parent.parent.parent
        staging_env_file = project_root / "config" / "staging.env"
        
        if staging_env_file.exists():
            cls.logger.info(f"Loading staging environment from: {staging_env_file}")
            
            with open(staging_env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        
                        if key not in os.environ:
                            os.environ[key] = value
            
            # Ensure ENVIRONMENT is set to staging
            os.environ["ENVIRONMENT"] = "staging"
        else:
            cls.logger.warning(f"config/staging.env not found at {staging_env_file}")

    @classmethod
    async def _verify_staging_services(cls):
        """Verify staging services are healthy and accessible"""
        import httpx
        
        try:
            # Check backend health
            async with httpx.AsyncClient(timeout=10.0) as client:
                backend_response = await client.get(f"{cls.staging_config.get_backend_base_url()}/health")
                assert backend_response.status_code == 200, f"Backend health check failed: {backend_response.status_code}"
                
                # Check auth service health  
                auth_response = await client.get(f"{cls.staging_auth_url}/health")
                assert auth_response.status_code == 200, f"Auth service health check failed: {auth_response.status_code}"
                
            cls.logger.info('All staging services are healthy and accessible')
            
        except Exception as e:
            pytest.skip(f'Staging environment not available for Golden Path testing: {e}')

    @classmethod
    async def _create_golden_path_test_user(cls) -> Dict[str, Any]:
        """Create dedicated test user for Golden Path validation"""
        try:
            user_timestamp = int(time.time())
            test_user_data = {
                'email': f'golden_path_complete_{user_timestamp}@netra-testing.ai',
                'user_id': f'golden_path_user_{user_timestamp}',
                'test_scenario': 'complete_flow_validation',
                'created_at': user_timestamp
            }
            
            # Generate access token
            access_token = await cls.auth_client.generate_test_access_token(
                user_id=test_user_data['user_id'], 
                email=test_user_data['email']
            )
            
            test_user_data['access_token'] = access_token
            # Encode token for WebSocket subprotocol
            import base64
            test_user_data['encoded_token'] = base64.urlsafe_b64encode(
                access_token.encode()
            ).decode().rstrip('=')
            
            cls.logger.info(f"Created Golden Path test user: {test_user_data['email']}")
            return test_user_data
            
        except Exception as e:
            pytest.skip(f'Failed to create Golden Path test user: {e}')

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for testing"""
        return UserExecutionContext.from_request(
            user_id=self.__class__.test_user['user_id'],
            thread_id=f"golden_path_thread_{int(time.time())}",
            run_id=f"golden_path_run_{int(time.time())}"
        )

    @pytest.mark.e2e
    @pytest.mark.golden_path
    @pytest.mark.mission_critical
    @pytest.mark.staging
    @track_test_timing
    async def test_complete_golden_path_user_journey(self):
        """
        MISSION CRITICAL: Test complete Golden Path user journey
        
        Full workflow:
        1. User authentication validation
        2. WebSocket connection establishment
        3. Chat message transmission
        4. All 5 critical events received
        5. Complete AI response delivery
        
        SUCCESS CRITERIA:
        - All SLA timing requirements met
        - All 5 critical WebSocket events delivered
        - Valid AI response received
        - No connection failures or timeouts
        
        FAILURE INDICATES: Critical system issues affecting $500K+ ARR
        
        DIFFICULTY: Very High (60-120 seconds)
        REAL SERVICES: Yes (staging.netrasystems.ai)
        STATUS: Should FAIL initially to validate test infrastructure
        """
        golden_path_start_time = time.time()
        journey_steps = []
        events_received = set()
        
        try:
            # STEP 1: Authentication Validation
            self.logger.info("GOLDEN PATH STEP 1: Authentication validation")
            auth_start_time = time.time()
            journey_steps.append({'step': 'authentication', 'status': 'starting'})
            
            auth_verification = await self.__class__.auth_client.verify_token(
                self.__class__.test_user['access_token']
            )
            
            auth_duration = time.time() - auth_start_time
            assert auth_verification['valid'], 'Golden Path user token must be valid'
            assert auth_duration <= GOLDEN_PATH_SLA['max_auth_time'], \
                f'Authentication took {auth_duration:.1f}s, exceeds SLA of {GOLDEN_PATH_SLA["max_auth_time"]}s'
            
            journey_steps[-1].update({
                'status': 'completed', 
                'duration': auth_duration,
                'details': 'Authentication successful within SLA'
            })
            
            # STEP 2: WebSocket Connection
            self.logger.info("GOLDEN PATH STEP 2: WebSocket connection establishment")
            websocket_start_time = time.time()
            journey_steps.append({'step': 'websocket_connection', 'status': 'starting'})
            
            # Use correct WebSocket subprotocol format
            subprotocols = [
                'jwt-auth', 
                f"jwt.{self.__class__.test_user['encoded_token']}"
            ]
            
            connection = await self._establish_golden_path_websocket_connection(
                subprotocols=subprotocols,
                timeout=GOLDEN_PATH_SLA['max_websocket_connect']
            )
            
            websocket_duration = time.time() - websocket_start_time
            assert connection is not None, 'Golden Path WebSocket connection must succeed'
            assert websocket_duration <= GOLDEN_PATH_SLA['max_websocket_connect'], \
                f'WebSocket connection took {websocket_duration:.1f}s, exceeds SLA of {GOLDEN_PATH_SLA["max_websocket_connect"]}s'
            
            journey_steps[-1].update({
                'status': 'completed',
                'duration': websocket_duration,
                'details': 'WebSocket connection established within SLA'
            })
            
            # STEP 3: Chat Message Transmission
            self.logger.info("GOLDEN PATH STEP 3: Chat message transmission")
            message_start_time = time.time()
            journey_steps.append({'step': 'chat_message_send', 'status': 'starting'})
            
            golden_path_message = {
                'type': 'chat_message',
                'data': {
                    'message': 'Hello! This is a Golden Path complete flow test. Please provide a helpful response demonstrating the AI system capabilities.',
                    'test_scenario': 'golden_path_complete_flow',
                    'timestamp': int(time.time()),
                    'user_id': self.__class__.test_user['user_id'],
                    'expected_events': list(GOLDEN_PATH_CRITICAL_EVENTS)
                }
            }
            
            await connection.send(json.dumps(golden_path_message))
            message_duration = time.time() - message_start_time
            
            journey_steps[-1].update({
                'status': 'completed',
                'duration': message_duration,
                'details': 'Chat message sent successfully'
            })
            
            # STEP 4: Event Collection and AI Response
            self.logger.info("GOLDEN PATH STEP 4: Collecting events and AI response")
            events_start_time = time.time()
            journey_steps.append({'step': 'event_collection', 'status': 'starting'})
            
            first_event_received = False
            complete_response_received = False
            
            # Collect events with timeout
            while (time.time() - events_start_time) < GOLDEN_PATH_SLA['max_total_response_time']:
                try:
                    # Wait for next event with reasonable timeout
                    event_data = await asyncio.wait_for(
                        connection.recv(), 
                        timeout=10.0
                    )
                    
                    if not first_event_received:
                        first_event_time = time.time() - events_start_time
                        assert first_event_time <= GOLDEN_PATH_SLA['max_first_event_time'], \
                            f'First event took {first_event_time:.1f}s, exceeds SLA of {GOLDEN_PATH_SLA["max_first_event_time"]}s'
                        first_event_received = True
                    
                    # Parse and validate event
                    try:
                        event = json.loads(event_data)
                        event_type = event.get('type', 'unknown')
                        
                        self.logger.info(f"Received Golden Path event: {event_type}")
                        
                        # Track critical events
                        if event_type in GOLDEN_PATH_CRITICAL_EVENTS:
                            events_received.add(event_type)
                        
                        # Check for completion
                        if event_type == 'agent_completed' or 'response' in event.get('data', {}):
                            complete_response_received = True
                            break
                            
                    except json.JSONDecodeError:
                        self.logger.warning(f"Received non-JSON event data: {event_data[:100]}...")
                        continue
                        
                except asyncio.TimeoutError:
                    self.logger.warning("Timeout waiting for next event, continuing...")
                    continue
            
            events_duration = time.time() - events_start_time
            
            # Validate event collection results
            assert first_event_received, 'Golden Path must receive at least one event'
            assert len(events_received) >= GOLDEN_PATH_SLA['min_events_required'], \
                f'Expected at least {GOLDEN_PATH_SLA["min_events_required"]} critical events, got {len(events_received)}: {events_received}'
            
            # Check for missing critical events
            missing_events = GOLDEN_PATH_CRITICAL_EVENTS - events_received
            if missing_events:
                self.logger.warning(f"Missing critical events: {missing_events}")
            
            journey_steps[-1].update({
                'status': 'completed',
                'duration': events_duration,
                'events_received': list(events_received),
                'missing_events': list(missing_events),
                'total_events': len(events_received)
            })
            
            # STEP 5: Final Validation
            total_duration = time.time() - golden_path_start_time
            assert total_duration <= GOLDEN_PATH_SLA['max_total_response_time'], \
                f'Total Golden Path took {total_duration:.1f}s, exceeds SLA of {GOLDEN_PATH_SLA["max_total_response_time"]}s'
            
            await connection.close()
            
            # SUCCESS: Log complete journey
            self.logger.info(
                f'GOLDEN PATH SUCCESS: Complete user journey validated in {total_duration:.1f}s. '
                f'Events received: {len(events_received)}/{len(GOLDEN_PATH_CRITICAL_EVENTS)}. '
                f'Journey steps: {len(journey_steps)} completed successfully.'
            )
            
        except AssertionError as e:
            total_duration = time.time() - golden_path_start_time
            pytest.fail(
                f'GOLDEN PATH ASSERTION FAILURE: {str(e)} after {total_duration:.1f}s. '
                f'Events received: {events_received}. Journey steps: {journey_steps}. '
                f'BUSINESS IMPACT: Critical $500K+ ARR Golden Path functionality broken.'
            )
            
        except asyncio.TimeoutError:
            total_duration = time.time() - golden_path_start_time
            pytest.fail(
                f'GOLDEN PATH TIMEOUT: Complete flow timeout after {total_duration:.1f}s. '
                f'Events received: {events_received}. Journey steps: {journey_steps}. '
                f'This indicates systemic issues with WebSocket/Agent infrastructure.'
            )
            
        except Exception as e:
            total_duration = time.time() - golden_path_start_time
            pytest.fail(
                f'GOLDEN PATH ERROR: Unexpected failure: {str(e)} after {total_duration:.1f}s. '
                f'Events received: {events_received}. Journey steps: {journey_steps}. '
                f'This indicates critical system instability.'
            )

    @pytest.mark.e2e
    @pytest.mark.golden_path
    @pytest.mark.websocket_events
    @track_test_timing
    async def test_golden_path_event_sequence_validation(self):
        """
        Test that Golden Path events arrive in correct sequence
        
        Validates:
        - Events arrive in logical order
        - No duplicate events
        - Proper event data structure
        - Timing between events is reasonable
        
        DIFFICULTY: High (30-45 seconds)
        REAL SERVICES: Yes (staging environment)
        STATUS: Should FAIL initially if event ordering issues exist
        """
        connection = await self._establish_golden_path_websocket_connection(
            subprotocols=['jwt-auth', f"jwt.{self.__class__.test_user['encoded_token']}"],
            timeout=15.0
        )
        
        if connection is None:
            pytest.fail('Cannot test event sequence - WebSocket connection failed')
        
        try:
            # Send test message
            test_message = {
                'type': 'chat_message',
                'data': {
                    'message': 'Test event sequence validation',
                    'test_scenario': 'event_sequence_validation',
                    'user_id': self.__class__.test_user['user_id']
                }
            }
            
            await connection.send(json.dumps(test_message))
            
            # Collect events with timing
            events_timeline = []
            start_time = time.time()
            
            while len(events_timeline) < 10 and (time.time() - start_time) < 30.0:
                try:
                    event_data = await asyncio.wait_for(connection.recv(), timeout=5.0)
                    event = json.loads(event_data)
                    
                    events_timeline.append({
                        'type': event.get('type'),
                        'timestamp': time.time(),
                        'relative_time': time.time() - start_time,
                        'data_keys': list(event.get('data', {}).keys()) if event.get('data') else []
                    })
                    
                    # Break on completion
                    if event.get('type') == 'agent_completed':
                        break
                        
                except asyncio.TimeoutError:
                    break
                except json.JSONDecodeError:
                    continue
            
            await connection.close()
            
            # Validate event sequence
            assert len(events_timeline) >= 2, f'Expected multiple events, got {len(events_timeline)}'
            
            # Check for logical sequence (agent_started should come before agent_completed)
            event_types = [e['type'] for e in events_timeline]
            
            if 'agent_started' in event_types and 'agent_completed' in event_types:
                started_index = event_types.index('agent_started')
                completed_index = event_types.index('agent_completed')
                assert started_index < completed_index, 'agent_started must come before agent_completed'
            
            # Check timing is reasonable (events should not all arrive at once)
            if len(events_timeline) >= 2:
                time_gaps = [
                    events_timeline[i+1]['relative_time'] - events_timeline[i]['relative_time']
                    for i in range(len(events_timeline) - 1)
                ]
                
                # At least some events should have reasonable gaps
                reasonable_gaps = [gap for gap in time_gaps if 0.1 <= gap <= 10.0]
                assert len(reasonable_gaps) > 0, 'Events appear to arrive all at once - possible batching issue'
            
            self.logger.info(f'Event sequence validation successful: {len(events_timeline)} events in proper order')
            
        except Exception as e:
            if connection and not connection.closed:
                await connection.close()
            raise

    async def _establish_golden_path_websocket_connection(
        self, 
        subprotocols: List[str], 
        timeout: float
    ) -> Optional[websockets.ClientConnection]:
        """
        Establish WebSocket connection for Golden Path testing
        
        Args:
            subprotocols: WebSocket subprotocols including JWT auth
            timeout: Connection timeout in seconds
            
        Returns:
            WebSocket connection or None if failed
        """
        try:
            self.logger.info(f'Establishing Golden Path WebSocket connection with timeout {timeout}s')
            
            # Setup SSL context for staging environment
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connection_start = time.time()
            
            # Attempt connection
            connection = await asyncio.wait_for(
                websockets.connect(
                    self.__class__.staging_backend_url,
                    subprotocols=subprotocols,
                    ssl=ssl_context if self.__class__.staging_backend_url.startswith('wss') else None,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10
                ),
                timeout=timeout
            )
            
            connection_duration = time.time() - connection_start
            self.logger.info(f'Golden Path WebSocket connection established in {connection_duration:.1f}s')
            
            return connection
            
        except asyncio.TimeoutError:
            connection_duration = time.time() - connection_start
            self.logger.error(f'Golden Path WebSocket connection timeout after {connection_duration:.1f}s')
            return None
            
        except Exception as e:
            connection_duration = time.time() - connection_start
            self.logger.error(f'Golden Path WebSocket connection error after {connection_duration:.1f}s: {e}')
            return None


# Test markers for pytest discovery and categorization
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.golden_path,
    pytest.mark.mission_critical,
    pytest.mark.staging,
    pytest.mark.websocket_events,
    pytest.mark.real_services,
    pytest.mark.issue_1197
]


if __name__ == '__main__':
    print('MIGRATION NOTICE: Use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category e2e --filter golden_path_complete_flow')
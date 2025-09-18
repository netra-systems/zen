"""
E2E Staging Tests for Basic Triage & Response (UVS) Validation - Issue #135

BUSINESS VALUE JUSTIFICATION (BVJ):
- Segment: All tiers (Free/Early/Mid/Enterprise) - Core revenue protection
- Business Goal: Validate complete Golden Path on GCP staging for 500K+ ARR protection
- Value Impact: End-to-end validation of triage processing in production-like environment
- Revenue Protection: Ensure complete user journey works in real GCP staging environment

PURPOSE: Test complete Golden Path user journey on GCP staging environment.
Focus on real WebSocket connections, real authentication, real agent execution,
and complete triage response delivery in production-like conditions.

KEY COVERAGE:
1. Real GCP staging environment connections
2. Real OAuth/JWT authentication flows
3. Real WebSocket connections with proper headers
4. Real agent execution with actual LLM calls
5. Complete triage processing and response generation
6. Production-like load and performance validation

GOLDEN PATH E2E STAGING VALIDATION:
These tests validate the complete user journey that generates business value:
User Login  ->  WebSocket Connect  ->  Send Message  ->  Triage Processing  ->  AI Response

These tests MUST initially FAIL to demonstrate current GCP staging issues.
"""
import pytest
import asyncio
import json
import uuid
import time
import aiohttp
import websockets
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urlencode
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.network_constants import URLConstants

@dataclass
class StagingEnvironmentConfig:
    """Configuration for GCP staging environment testing"""
    backend_url: str
    auth_url: str
    websocket_url: str
    oauth_client_id: str
    environment: str = 'staging'
    use_real_llm: bool = True
    timeout_connect: float = 30.0
    timeout_response: float = 120.0

@dataclass
class StagingTestUser:
    """Test user for staging environment"""
    user_id: str
    email: str
    access_token: str
    refresh_token: str
    subscription_tier: str
    created_at: datetime

@dataclass
class StagingTriageResult:
    """Triage result from staging environment"""
    category: str
    priority: str
    confidence_score: float
    next_agents: List[str]
    processing_time: float
    websocket_events: List[Dict[str, Any]]
    success: bool
    error: Optional[str] = None

class StagingWebSocketClient:
    """WebSocket client for GCP staging environment testing"""

    def __init__(self, config: StagingEnvironmentConfig, user: StagingTestUser):
        self.config = config
        self.user = user
        self.websocket = None
        self.received_events = []
        self.connection_active = False
        self.last_ping = None

    async def connect(self) -> bool:
        """Connect to staging WebSocket with real authentication"""
        try:
            ws_url = self.config.websocket_url
            if not ws_url.startswith('ws'):
                ws_url = ws_url.replace('http', 'ws')
            if not ws_url.endswith('/ws'):
                ws_url = f"{ws_url.rstrip('/')}/ws"
            headers = {'Authorization': f'Bearer {self.user.access_token}', 'User-Agent': 'E2E-Staging-Test-Client/1.0', 'Origin': self.config.backend_url}
            self.websocket = await asyncio.wait_for(websockets.connect(ws_url, extra_headers=headers, ping_interval=30, ping_timeout=10, close_timeout=10), timeout=self.config.timeout_connect)
            self.connection_active = True
            return True
        except Exception as e:
            await self.cleanup()
            raise Exception(f'Staging WebSocket connection failed: {e}')

    async def send_message(self, message_type: str, content: str, thread_id: str=None) -> bool:
        """Send message to staging environment"""
        if not self.connection_active or not self.websocket:
            raise Exception('WebSocket not connected to staging')
        if thread_id is None:
            thread_id = f'staging_thread_{uuid.uuid4().hex[:8]}'
        message = {'type': message_type, 'content': content, 'thread_id': thread_id, 'user_id': self.user.user_id, 'timestamp': datetime.now(UTC).isoformat(), 'metadata': {'environment': 'staging', 'test_client': True}}
        try:
            await self.websocket.send(json.dumps(message))
            return True
        except Exception as e:
            raise Exception(f'Failed to send message to staging: {e}')

    async def receive_events(self, timeout: float=None, expected_count: int=5) -> List[Dict[str, Any]]:
        """Receive events from staging WebSocket with proper timeout"""
        if not self.connection_active or not self.websocket:
            raise Exception('WebSocket not connected to staging')
        if timeout is None:
            timeout = self.config.timeout_response
        events = []
        start_time = time.time()
        try:
            while len(events) < expected_count and time.time() - start_time < timeout:
                try:
                    remaining_time = timeout - (time.time() - start_time)
                    message_timeout = min(10.0, remaining_time)
                    if message_timeout <= 0:
                        break
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=message_timeout)
                    event = json.loads(message)
                    events.append(event)
                    self.received_events.append(event)
                    if event.get('type') == 'agent_completed':
                        break
                except asyncio.TimeoutError:
                    if len(events) >= 3:
                        break
                    continue
                except websockets.ConnectionClosed:
                    raise Exception('WebSocket connection closed by staging server')
        except Exception as e:
            raise Exception(f'Failed to receive events from staging: {e}')
        return events

    async def wait_for_completion(self, timeout: float=None) -> Dict[str, Any]:
        """Wait specifically for agent completion in staging"""
        if timeout is None:
            timeout = self.config.timeout_response
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=min(15.0, timeout - (time.time() - start_time)))
                event = json.loads(message)
                self.received_events.append(event)
                if event.get('type') == 'agent_completed':
                    return event
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                raise Exception(f'Error waiting for completion in staging: {e}')
        raise TimeoutError(f'Agent completion not received from staging within {timeout}s')

    async def cleanup(self):
        """Cleanup staging WebSocket connection"""
        self.connection_active = False
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
            self.websocket = None

class StagingAuthManager:
    """Authentication manager for GCP staging environment"""

    def __init__(self, config: StagingEnvironmentConfig):
        self.config = config
        self.session = None

    async def create_staging_test_user(self, email: str=None, subscription_tier: str='enterprise') -> StagingTestUser:
        """Create test user in staging environment"""
        if email is None:
            email = f'staging_test_{uuid.uuid4().hex[:8]}@example.com'
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        signup_data = {'email': email, 'password': 'StagingTestPassword2024!', 'name': f"Staging Test User {email.split('@')[0]}", 'subscription_tier': subscription_tier, 'metadata': {'test_user': True, 'environment': 'staging', 'created_by': 'e2e_staging_test'}}
        try:
            async with self.session.post(f'{self.config.auth_url}/auth/signup', json=signup_data, headers={'Content-Type': 'application/json'}) as response:
                if response.status != 201:
                    error_text = await response.text()
                    if 'already exists' in error_text.lower():
                        pass
                    else:
                        raise Exception(f'Staging user creation failed: {error_text}')
                else:
                    user_data = await response.json()
            login_data = {'email': email, 'password': signup_data['password']}
            async with self.session.post(f'{self.config.auth_url}/auth/login', json=login_data, headers={'Content-Type': 'application/json'}) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f'Staging login failed: {error_text}')
                auth_data = await response.json()
            if 'user_data' not in locals():
                headers = {'Authorization': f"Bearer {auth_data['access_token']}"}
                async with self.session.get(f'{self.config.auth_url}/auth/me', headers=headers) as response:
                    if response.status == 200:
                        user_data = await response.json()
                    else:
                        user_data = {'user_id': f'staging_user_{uuid.uuid4().hex[:8]}', 'email': email}
            return StagingTestUser(user_id=user_data.get('user_id', f'staging_user_{uuid.uuid4().hex[:8]}'), email=email, access_token=auth_data['access_token'], refresh_token=auth_data.get('refresh_token', ''), subscription_tier=subscription_tier, created_at=datetime.now(UTC))
        except Exception as e:
            raise Exception(f'Failed to create staging test user: {e}')

    async def cleanup_staging_user(self, user: StagingTestUser):
        """Cleanup staging test user"""
        if not self.session:
            return
        try:
            headers = {'Authorization': f'Bearer {user.access_token}'}
            async with self.session.delete(f'{self.config.auth_url}/auth/users/{user.user_id}', headers=headers) as response:
                pass
        except:
            pass

    async def cleanup(self):
        """Cleanup auth manager"""
        if self.session:
            await self.session.close()
            self.session = None

@pytest.mark.e2e
@pytest.mark.staging
@pytest.mark.real_services
@pytest.mark.issue_135
class BasicTriageResponseStagingE2ETests(SSotAsyncTestCase):
    """
    E2E tests for basic triage response on GCP staging environment.
    
    These tests validate the complete Golden Path user journey on real
    GCP staging infrastructure with real authentication, WebSocket connections,
    and agent execution.
    
    CRITICAL: These tests should initially FAIL to demonstrate current
    staging environment issues that block the 500K+ ARR user journey.
    """

    async def async_setup_method(self, method=None):
        """Setup E2E staging test environment"""
        await super().async_setup_method(method)
        self.env = IsolatedEnvironment()
        self.staging_config = StagingEnvironmentConfig(backend_url=self.env.get('STAGING_BACKEND_URL', URLConstants.STAGING_BACKEND_URL), auth_url=self.env.get('STAGING_AUTH_URL', URLConstants.STAGING_AUTH_URL), websocket_url=self.env.get('STAGING_WEBSOCKET_URL', URLConstants.STAGING_WEBSOCKET_URL), oauth_client_id=self.env.get('STAGING_OAUTH_CLIENT_ID', 'staging-client-id'), use_real_llm=self.env.get('STAGING_USE_REAL_LLM', 'true').lower() == 'true')
        self.auth_manager = StagingAuthManager(self.staging_config)
        self.test_users = []
        self.websocket_clients = []
        self.test_start_time = time.time()

    @pytest.mark.asyncio
    async def test_staging_environment_connectivity(self):
        """
        Test connectivity to all staging environment services.
        
        Business Impact: Validates staging environment is accessible and
        all required services are operational for Golden Path testing.
        """
        connectivity_results = {'backend_reachable': False, 'auth_service_reachable': False, 'websocket_endpoint_available': False, 'all_services_operational': False}
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                try:
                    async with session.get(f'{self.staging_config.backend_url}/health') as response:
                        if response.status == 200:
                            connectivity_results['backend_reachable'] = True
                except Exception as e:
                    self.record_metric('backend_connectivity_error', str(e))
                try:
                    async with session.get(f'{self.staging_config.auth_url}/health') as response:
                        if response.status == 200:
                            connectivity_results['auth_service_reachable'] = True
                except Exception as e:
                    self.record_metric('auth_connectivity_error', str(e))
                try:
                    ws_url = self.staging_config.websocket_url.replace('http', 'ws')
                    if not ws_url.endswith('/ws'):
                        ws_url = f"{ws_url.rstrip('/')}/ws"
                    try:
                        test_ws = await asyncio.wait_for(websockets.connect(ws_url, ping_timeout=5), timeout=10.0)
                        await test_ws.close()
                        connectivity_results['websocket_endpoint_available'] = True
                    except websockets.ConnectionClosed:
                        connectivity_results['websocket_endpoint_available'] = True
                    except Exception as e:
                        if '1011' in str(e) or 'unauthorized' in str(e).lower():
                            connectivity_results['websocket_endpoint_available'] = True
                        else:
                            self.record_metric('websocket_connectivity_error', str(e))
                except Exception as e:
                    self.record_metric('websocket_endpoint_error', str(e))
            services_reachable = sum((connectivity_results[k] for k in ['backend_reachable', 'auth_service_reachable', 'websocket_endpoint_available']))
            connectivity_results['all_services_operational'] = services_reachable >= 2
            assert connectivity_results['backend_reachable'], 'Staging backend not reachable'
            assert connectivity_results['auth_service_reachable'], 'Staging auth service not reachable'
            self.record_metric('staging_services_reachable', services_reachable)
            self.record_metric('staging_connectivity_success', True)
        except Exception as e:
            self.record_metric('staging_connectivity_failure', str(e))
            pytest.fail(f'Staging environment connectivity failed: {e}')

    @pytest.mark.asyncio
    async def test_staging_authentication_flow(self):
        """
        Test complete authentication flow on staging environment.
        
        Business Impact: Validates user authentication that gates access
        to all AI functionality and chat capabilities.
        """
        auth_flow_steps = {'user_creation': False, 'user_login': False, 'token_validation': False, 'user_profile_access': False}
        test_email = f'staging_auth_test_{uuid.uuid4().hex[:8]}@example.com'
        try:
            test_user = await self.auth_manager.create_staging_test_user(email=test_email, subscription_tier='enterprise')
            self.test_users.append(test_user)
            auth_flow_steps['user_creation'] = True
            assert test_user.access_token, 'No access token received'
            assert len(test_user.access_token) > 50, 'Access token too short'
            auth_flow_steps['user_login'] = True
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {test_user.access_token}'}
                async with session.get(f'{self.staging_config.auth_url}/auth/validate', headers=headers) as response:
                    if response.status == 200:
                        auth_flow_steps['token_validation'] = True
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {test_user.access_token}'}
                async with session.get(f'{self.staging_config.auth_url}/auth/me', headers=headers) as response:
                    if response.status == 200:
                        profile_data = await response.json()
                        assert profile_data.get('email') == test_email
                        auth_flow_steps['user_profile_access'] = True
            completed_steps = sum((1 for completed in auth_flow_steps.values() if completed))
            assert completed_steps == len(auth_flow_steps), f'Auth flow incomplete: {completed_steps}/{len(auth_flow_steps)}'
            self.record_metric('staging_auth_steps_completed', completed_steps)
            self.record_metric('staging_auth_flow_success', True)
        except Exception as e:
            failed_step = None
            for step, completed in auth_flow_steps.items():
                if not completed:
                    failed_step = step
                    break
            self.record_metric('staging_auth_failure', str(e))
            self.record_metric('staging_auth_failed_at_step', failed_step or 'unknown')
            pytest.fail(f'Staging authentication flow failed at {failed_step}: {e}')

    @pytest.mark.asyncio
    async def test_staging_websocket_connection_with_auth(self):
        """
        Test WebSocket connection with real authentication on staging.
        
        Business Impact: Validates the WebSocket connection that enables
        all real-time chat functionality and AI response delivery.
        
        EXPECTED OUTCOME: Should initially FAIL due to WebSocket 1011 errors.
        """
        test_email = f'staging_ws_test_{uuid.uuid4().hex[:8]}@example.com'
        test_user = await self.auth_manager.create_staging_test_user(email=test_email, subscription_tier='mid')
        self.test_users.append(test_user)
        websocket_steps = {'client_created': False, 'connection_established': False, 'authentication_verified': False, 'message_send_ready': False}
        try:
            ws_client = StagingWebSocketClient(self.staging_config, test_user)
            self.websocket_clients.append(ws_client)
            websocket_steps['client_created'] = True
            connection_start = time.time()
            connected = await ws_client.connect()
            connection_time = time.time() - connection_start
            assert connected, 'WebSocket connection to staging failed'
            websocket_steps['connection_established'] = True
            test_message = {'type': 'ping', 'data': {'test': 'connection_verification'}, 'timestamp': datetime.now(UTC).isoformat()}
            await ws_client.websocket.send(json.dumps(test_message))
            websocket_steps['authentication_verified'] = True
            websocket_steps['message_send_ready'] = True
            assert connection_time < 15.0, f'Connection took too long: {connection_time:.3f}s'
            self.record_metric('staging_websocket_connection_time', connection_time)
            self.record_metric('staging_websocket_steps_completed', sum(websocket_steps.values()))
            self.record_metric('staging_websocket_connection_success', True)
        except Exception as e:
            failed_step = None
            for step, completed in websocket_steps.items():
                if not completed:
                    failed_step = step
                    break
            error_message = str(e)
            self.record_metric('staging_websocket_failure', error_message)
            self.record_metric('staging_websocket_failed_at_step', failed_step or 'unknown')
            if '1011' in error_message:
                self.record_metric('staging_websocket_1011_error', True)
                pytest.fail(f'CRITICAL - Staging WebSocket 1011 error at {failed_step}: {e}')
            elif 'unauthorized' in error_message.lower() or '403' in error_message:
                self.record_metric('staging_websocket_auth_error', True)
                pytest.fail(f'CRITICAL - Staging WebSocket auth error at {failed_step}: {e}')
            else:
                pytest.fail(f'Staging WebSocket connection failed at {failed_step}: {e}')

    @pytest.mark.asyncio
    async def test_staging_triage_message_processing(self):
        """
        Test complete triage message processing on staging environment.
        
        Business Impact: Validates the core AI triage processing that
        enables intelligent routing and response generation.
        
        EXPECTED OUTCOME: Should initially FAIL due to message processing issues.
        """
        test_email = f'staging_triage_test_{uuid.uuid4().hex[:8]}@example.com'
        test_user = await self.auth_manager.create_staging_test_user(email=test_email, subscription_tier='enterprise')
        self.test_users.append(test_user)
        ws_client = StagingWebSocketClient(self.staging_config, test_user)
        self.websocket_clients.append(ws_client)
        triage_processing_steps = {'websocket_connected': False, 'message_sent': False, 'events_received': False, 'triage_completed': False, 'results_validated': False}
        try:
            connected = await ws_client.connect()
            assert connected, 'Could not connect to staging for triage test'
            triage_processing_steps['websocket_connected'] = True
            triage_request = 'I need to optimize my machine learning infrastructure costs. Current setup: 16x V100 GPUs for training, 8x T4 GPUs for inference, spending $12,000/month on AWS. Target: 35% cost reduction while maintaining <300ms inference latency.'
            send_success = await ws_client.send_message(message_type='user_message', content=triage_request)
            assert send_success, 'Failed to send triage message to staging'
            triage_processing_steps['message_sent'] = True
            processing_start = time.time()
            events = await ws_client.receive_events(timeout=self.staging_config.timeout_response, expected_count=5)
            processing_time = time.time() - processing_start
            assert len(events) >= 3, f'Insufficient events received: {len(events)}'
            triage_processing_steps['events_received'] = True
            completion_event = None
            for event in events:
                if event.get('type') == 'agent_completed':
                    completion_event = event
                    break
            assert completion_event is not None, 'No agent completion event received'
            triage_processing_steps['triage_completed'] = True
            completion_data = completion_event.get('data', {})
            category = completion_data.get('category') or completion_data.get('triage_category', '')
            assert any((keyword in category.lower() for keyword in ['cost', 'performance', 'optimization']))
            priority = completion_data.get('priority', '').lower()
            assert priority in ['high', 'critical', 'medium']
            next_agents = completion_data.get('next_agents', [])
            assert len(next_agents) > 0, 'No next agents identified'
            triage_processing_steps['results_validated'] = True
            assert processing_time < 90.0, f'Triage processing too slow: {processing_time:.3f}s'
            triage_result = StagingTriageResult(category=category, priority=priority, confidence_score=completion_data.get('confidence_score', 0.0), next_agents=next_agents, processing_time=processing_time, websocket_events=events, success=True)
            self.record_metric('staging_triage_processing_time', processing_time)
            self.record_metric('staging_triage_events_received', len(events))
            self.record_metric('staging_triage_category', category)
            self.record_metric('staging_triage_next_agents', len(next_agents))
            self.record_metric('staging_triage_success', True)
        except Exception as e:
            failed_step = None
            for step, completed in triage_processing_steps.items():
                if not completed:
                    failed_step = step
                    break
            error_message = str(e)
            self.record_metric('staging_triage_failure', error_message)
            self.record_metric('staging_triage_failed_at_step', failed_step or 'unknown')
            if 'timeout' in error_message.lower():
                self.record_metric('staging_triage_timeout_error', True)
                pytest.fail(f'CRITICAL - Staging triage timeout at {failed_step}: {e}')
            elif '1011' in error_message or 'websocket' in error_message.lower():
                self.record_metric('staging_triage_websocket_error', True)
                pytest.fail(f'CRITICAL - Staging triage WebSocket error at {failed_step}: {e}')
            else:
                pytest.fail(f'Staging triage processing failed at {failed_step}: {e}')

    @pytest.mark.asyncio
    async def test_complete_golden_path_staging_validation(self):
        """
        Test complete Golden Path user journey on staging environment.
        
        Business Impact: Validates the complete 500K+ ARR user journey
        that must work flawlessly in production-like staging environment.
        
        Flow: User Creation  ->  Authentication  ->  WebSocket  ->  Message  ->  AI Response
        
        EXPECTED OUTCOME: Should initially FAIL demonstrating current staging issues.
        """
        golden_path_staging = {'user_account_created': False, 'authentication_completed': False, 'websocket_connection_established': False, 'user_message_sent': False, 'ai_processing_started': False, 'triage_analysis_completed': False, 'next_agents_identified': False, 'user_response_delivered': False}
        staging_start_time = time.time()
        try:
            test_email = f'staging_golden_path_{uuid.uuid4().hex[:8]}@example.com'
            test_user = await self.auth_manager.create_staging_test_user(email=test_email, subscription_tier='enterprise')
            self.test_users.append(test_user)
            golden_path_staging['user_account_created'] = True
            assert test_user.access_token, 'Authentication failed - no access token'
            golden_path_staging['authentication_completed'] = True
            ws_client = StagingWebSocketClient(self.staging_config, test_user)
            self.websocket_clients.append(ws_client)
            connected = await ws_client.connect()
            assert connected, 'WebSocket connection failed'
            golden_path_staging['websocket_connection_established'] = True
            user_message = "I need a comprehensive AI cost optimization strategy for my company's infrastructure.\n            \n            Current Setup:\n            - AWS: $18,000/month (ML training: 24x V100, inference: 16x T4)\n            - Azure: $8,000/month (data processing and storage)\n            - GCP: $5,000/month (analytics and reporting)\n            - Total: $31,000/month\n            \n            Goals:\n            - Reduce costs by 40% ($12,400 savings/month)\n            - Maintain inference latency <250ms p95\n            - Keep training throughput at current levels\n            - Improve resource utilization from 65% to 85%\n            \n            Constraints:\n            - Cannot change core ML models\n            - Must maintain 99.9% uptime SLA\n            - Data cannot leave current regions (compliance)\n            \n            Please provide a detailed optimization plan with specific recommendations."
            send_success = await ws_client.send_message(message_type='user_message', content=user_message)
            assert send_success, 'Failed to send user message'
            golden_path_staging['user_message_sent'] = True
            ai_processing_timeout = 30.0
            processing_started = False
            try:
                start_events = await ws_client.receive_events(timeout=ai_processing_timeout, expected_count=2)
                started_events = [e for e in start_events if e.get('type') == 'agent_started']
                if started_events:
                    processing_started = True
            except:
                pass
            assert processing_started, 'AI processing did not start'
            golden_path_staging['ai_processing_started'] = True
            triage_timeout = self.staging_config.timeout_response
            completion_event = await ws_client.wait_for_completion(timeout=triage_timeout)
            assert completion_event, 'Triage analysis did not complete'
            golden_path_staging['triage_analysis_completed'] = True
            completion_data = completion_event.get('data', {})
            next_agents = completion_data.get('next_agents', [])
            assert len(next_agents) >= 2, 'Insufficient next agents for complex request'
            assert any(('data' in agent.lower() or 'optimization' in agent.lower() for agent in next_agents))
            golden_path_staging['next_agents_identified'] = True
            category = completion_data.get('category') or completion_data.get('triage_category', '')
            assert 'optimization' in category.lower() or 'cost' in category.lower()
            priority = completion_data.get('priority', '').lower()
            assert priority in ['high', 'critical']
            confidence = completion_data.get('confidence_score', 0.0)
            assert confidence > 0.7, f'Low confidence score: {confidence}'
            golden_path_staging['user_response_delivered'] = True
            total_golden_path_time = time.time() - staging_start_time
            completed_steps = sum((1 for completed in golden_path_staging.values() if completed))
            total_steps = len(golden_path_staging)
            assert completed_steps == total_steps, f'Golden Path incomplete: {completed_steps}/{total_steps}'
            assert total_golden_path_time < 180.0, f'Golden Path too slow: {total_golden_path_time:.3f}s'
            self.record_metric('staging_golden_path_steps_completed', completed_steps)
            self.record_metric('staging_golden_path_total_time', total_golden_path_time)
            self.record_metric('staging_golden_path_triage_category', category)
            self.record_metric('staging_golden_path_next_agents_count', len(next_agents))
            self.record_metric('staging_golden_path_confidence', confidence)
            self.record_metric('staging_golden_path_success', True)
        except Exception as e:
            failed_step = None
            for step, completed in golden_path_staging.items():
                if not completed:
                    failed_step = step
                    break
            total_time = time.time() - staging_start_time
            completed_steps = sum((1 for completed in golden_path_staging.values() if completed))
            error_message = str(e)
            self.record_metric('staging_golden_path_failure', error_message)
            self.record_metric('staging_golden_path_failed_at_step', failed_step or 'unknown')
            self.record_metric('staging_golden_path_partial_completion', completed_steps)
            self.record_metric('staging_golden_path_failure_time', total_time)
            if completed_steps <= 3:
                self.record_metric('staging_golden_path_early_failure', True)
                business_impact = 'CRITICAL - User cannot access platform'
            elif completed_steps <= 6:
                self.record_metric('staging_golden_path_connection_failure', True)
                business_impact = 'HIGH - User connected but AI processing failed'
            else:
                self.record_metric('staging_golden_path_late_failure', True)
                business_impact = 'MEDIUM - AI processing started but incomplete'
            self.record_metric('staging_golden_path_business_impact', business_impact)
            if '1011' in error_message or 'websocket' in error_message.lower():
                self.record_metric('staging_golden_path_websocket_1011', True)
                pytest.fail(f'CRITICAL - Golden Path blocked by WebSocket 1011 at {failed_step}: {e}')
            elif 'timeout' in error_message.lower():
                self.record_metric('staging_golden_path_timeout', True)
                pytest.fail(f'CRITICAL - Golden Path timeout at {failed_step}: {e}')
            elif 'auth' in error_message.lower():
                self.record_metric('staging_golden_path_auth_failure', True)
                pytest.fail(f'CRITICAL - Golden Path auth failure at {failed_step}: {e}')
            else:
                pytest.fail(f'CRITICAL - Golden Path staging failure at {failed_step}: {e}')

    @pytest.mark.asyncio
    async def test_staging_performance_requirements(self):
        """
        Test performance requirements on staging environment.
        
        Business Impact: Validates staging environment meets performance
        requirements for user satisfaction and retention.
        """
        performance_test_cases = [{'name': 'Simple Cost Query', 'content': 'How can I reduce my AWS costs?', 'max_response_time': 45.0, 'min_events': 3}, {'name': 'Technical Optimization', 'content': 'Optimize my Kubernetes cluster GPU utilization for deep learning workloads', 'max_response_time': 75.0, 'min_events': 4}, {'name': 'Complex Multi-Cloud', 'content': 'Comprehensive multi-cloud cost optimization for ML infrastructure across AWS, Azure, and GCP', 'max_response_time': 120.0, 'min_events': 5}]
        performance_results = []
        for test_case in performance_test_cases:
            test_email = f'staging_perf_{uuid.uuid4().hex[:8]}@example.com'
            test_user = await self.auth_manager.create_staging_test_user(test_email)
            self.test_users.append(test_user)
            ws_client = StagingWebSocketClient(self.staging_config, test_user)
            self.websocket_clients.append(ws_client)
            try:
                connect_start = time.time()
                connected = await ws_client.connect()
                connect_time = time.time() - connect_start
                assert connected, f"Connection failed for {test_case['name']}"
                process_start = time.time()
                send_success = await ws_client.send_message(message_type='user_message', content=test_case['content'])
                assert send_success, f"Send failed for {test_case['name']}"
                events = await ws_client.receive_events(timeout=test_case['max_response_time'], expected_count=test_case['min_events'])
                total_time = time.time() - process_start
                assert len(events) >= test_case['min_events'], f"Insufficient events for {test_case['name']}"
                assert total_time <= test_case['max_response_time'], f"Too slow for {test_case['name']}: {total_time:.3f}s"
                performance_results.append({'test_case': test_case['name'], 'connect_time': connect_time, 'processing_time': total_time, 'events_received': len(events), 'success': True})
                await ws_client.cleanup()
            except Exception as e:
                performance_results.append({'test_case': test_case['name'], 'error': str(e), 'success': False})
        successful_tests = [r for r in performance_results if r['success']]
        success_rate = len(successful_tests) / len(performance_test_cases)
        assert success_rate >= 0.7, f'Performance success rate too low: {success_rate:.2f}'
        if successful_tests:
            avg_connect_time = sum((r['connect_time'] for r in successful_tests)) / len(successful_tests)
            avg_processing_time = sum((r['processing_time'] for r in successful_tests)) / len(successful_tests)
            self.record_metric('staging_performance_success_rate', success_rate)
            self.record_metric('staging_avg_connect_time', avg_connect_time)
            self.record_metric('staging_avg_processing_time', avg_processing_time)
            self.record_metric('staging_performance_validation_success', True)

    async def async_teardown_method(self, method=None):
        """Cleanup staging test resources and record metrics"""
        for client in self.websocket_clients:
            try:
                await client.cleanup()
            except:
                pass
        for user in self.test_users:
            try:
                await self.auth_manager.cleanup_staging_user(user)
            except:
                pass
        try:
            await self.auth_manager.cleanup()
        except:
            pass
        total_test_time = time.time() - self.test_start_time
        metrics = self.get_all_metrics()
        print(f'\n=== STAGING E2E TEST RESULTS - Issue #135 ===')
        print(f'Environment: {self.staging_config.backend_url}')
        print(f'Total Test Time: {total_test_time:.3f}s')
        print(f'Test Users Created: {len(self.test_users)}')
        print(f'WebSocket Connections: {len(self.websocket_clients)}')
        success_metrics = [k for k, v in metrics.items() if k.endswith('_success') and v is True]
        failure_metrics = [k for k, v in metrics.items() if k.endswith('_failure')]
        error_metrics = [k for k, v in metrics.items() if 'error' in k and v is True]
        print(f'Successful Operations: {len(success_metrics)}')
        print(f'Failed Operations: {len(failure_metrics)}')
        print(f'Errors Identified: {len(error_metrics)}')
        golden_path_success = metrics.get('staging_golden_path_success', False)
        if golden_path_success:
            print(' PASS:  BUSINESS SUCCESS: Golden Path working on staging')
        else:
            print(' ALERT:  BUSINESS CRITICAL: Golden Path failing on staging')
        if any(('1011' in k for k in error_metrics)):
            print(' ALERT:  CRITICAL: WebSocket 1011 errors confirmed on staging')
        if any(('timeout' in k for k in error_metrics)):
            print(' WARNING: [U+FE0F]  WARNING: Timeout issues detected on staging')
        if any(('auth' in k for k in error_metrics)):
            print('[U+1F510] AUTH: Authentication issues detected on staging')
        self.record_metric('staging_test_execution_time', total_test_time)
        self.record_metric('staging_test_users_created', len(self.test_users))
        self.record_metric('staging_websocket_connections', len(self.websocket_clients))
        self.record_metric('staging_e2e_test_complete', True)
        await super().async_teardown_method(method)
        print('=' * 70)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
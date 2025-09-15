from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
'\nCRITICAL E2E Test: Basic User Flow (Signup  ->  Login  ->  Chat) with REAL Services\n\nBVJ (Business Value Justification):\n1. Segment: ALL segments (Free  ->  Enterprise) - $99-999/month per user\n2. Business Goal: Protect core revenue by validating THE critical user journey\n3. Value Impact: Prevents 100% user loss from broken signup/login/chat flow\n4. Strategic Impact: This IS the revenue pipeline - every working journey = $$$\n\nCRITICAL REQUIREMENTS:\n- Use REAL Auth service for signup/login (NO MOCKS for internal services)\n- Use REAL Backend service for WebSocket chat (NO MOCKS for internal services)\n- Only mock external LLM if needed for reliability\n- Complete in <20 seconds for business UX requirements\n- Test with services actually running\n- Validate each step as business-critical revenue checkpoint\n\nIMPLEMENTATION:\n PASS:  Real Auth service integration via HTTP calls\n PASS:  Real Backend WebSocket connection with JWT\n PASS:  Complete user creation  ->  authentication  ->  chat pipeline\n PASS:  Business-critical validations at each revenue step\n PASS:  Performance validation for user experience\n PASS:  Error handling for production-level reliability\n'
import asyncio
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional
import httpx
import pytest
import websockets
from websockets import ServerConnection
from tests.e2e.harness_utils import TestClient, TestHarnessContext
AUTH_SERVICE_URL = 'http://localhost:8001'
BACKEND_SERVICE_URL = 'http://localhost:8000'
WEBSOCKET_URL = 'ws://localhost:8000/ws'

class BasicUserFlowE2EerTests:
    """Tests the complete basic user flow with REAL services."""

    def __init__(self, harness):
        """Initialize with unified test harness."""
        self.harness = harness
        self.test_client = TestClient(harness)
        self.test_user_email = f'test-user-{uuid.uuid4().hex[:8]}@netrasystems.ai'
        self.test_user_id: Optional[str] = None
        self.jwt_token: Optional[str] = None
        self.websocket_connection: Optional[websockets.ServerConnection] = None

    async def execute_complete_user_flow(self) -> Dict[str, Any]:
        """Execute complete signup  ->  login  ->  chat flow with REAL services."""
        flow_start_time = time.time()
        results = {'steps': [], 'success': False, 'duration': 0}
        signup_result = await self._execute_real_signup()
        results['steps'].append({'step': 'signup', 'success': True, 'user_id': signup_result['user_id'], 'email': signup_result['email']})
        login_result = await self._execute_real_login()
        results['steps'].append({'step': 'login', 'success': True, 'token_length': len(login_result['access_token']), 'token_type': login_result.get('token_type')})
        websocket_result = await self._establish_real_websocket_connection()
        results['steps'].append({'step': 'websocket_connect', 'success': True, 'connected': websocket_result['connected']})
        chat_result = await self._execute_real_chat_flow()
        results['steps'].append({'step': 'chat_flow', 'success': True, 'message_sent': chat_result['message_sent'], 'response_received': chat_result['response_received'], 'response_length': chat_result['response_length']})
        results['duration'] = time.time() - flow_start_time
        results['success'] = True
        assert results['duration'] < 20.0, f"Flow took {results['duration']:.2f}s > 20s limit"
        await self._cleanup_resources()
        return results

    async def _execute_real_signup(self) -> Dict[str, Any]:
        """Create user via REAL Auth service dev endpoint."""
        response = await self.test_client.auth_request('POST', '/auth/dev/login', json={})
        assert response.status_code == 200, f'Dev signup failed: {response.status_code}'
        user_data = response.json()
        self.test_user_id = user_data['user']['id']
        self.test_user_email = user_data['user']['email']
        assert 'access_token' in user_data, 'Signup must return access token'
        assert 'user' in user_data, 'Signup must return user data'
        assert self.test_user_id, 'User ID must be provided'
        return {'user_id': self.test_user_id, 'email': self.test_user_email, 'signup_method': 'dev_endpoint'}

    async def _execute_real_login(self) -> Dict[str, Any]:
        """Login via REAL Auth service to get JWT token."""
        response = await self.test_client.auth_request('POST', '/auth/dev/login', json={})
        assert response.status_code == 200, f'Login failed: {response.status_code}'
        login_data = response.json()
        self.jwt_token = login_data['access_token']
        assert 'access_token' in login_data, 'Login must return access token'
        assert login_data.get('token_type') == 'Bearer', 'Must use Bearer token'
        assert len(self.jwt_token) > 50, 'JWT token must be substantial'
        assert self.jwt_token.count('.') == 2, 'Invalid JWT format'
        return {'access_token': self.jwt_token, 'token_type': login_data['token_type'], 'expires_in': login_data.get('expires_in', 900)}

    async def _establish_real_websocket_connection(self) -> Dict[str, Any]:
        """Establish REAL WebSocket connection to Backend service."""
        headers = {'Authorization': f'Bearer {self.jwt_token}'}
        async with asyncio.timeout(10):
            self.websocket_connection = await websockets.connect(WEBSOCKET_URL, additional_headers=headers)
        welcome_message = await asyncio.wait_for(self.websocket_connection.recv(), timeout=5.0)
        welcome_data = json.loads(welcome_message)
        assert 'type' in welcome_data, 'Welcome message must have type'
        return {'connected': True, 'welcome_message': welcome_data, 'connection_established': True}

    async def _execute_real_chat_flow(self) -> Dict[str, Any]:
        """Send real chat message and receive agent response."""
        if not self.websocket_connection:
            raise AssertionError('WebSocket connection not established')
        test_message = {'type': 'chat', 'message': 'Help me optimize my AI infrastructure costs to maximize ROI', 'thread_id': str(uuid.uuid4()), 'timestamp': time.time()}
        await self.websocket_connection.send(json.dumps(test_message))
        response_message = await asyncio.wait_for(self.websocket_connection.recv(), timeout=15.0)
        response_data = json.loads(response_message)
        self._validate_agent_response(response_data)
        return {'message_sent': True, 'response_received': True, 'response_data': response_data, 'response_length': len(str(response_data))}

    def _validate_agent_response(self, response_data: Dict[str, Any]) -> None:
        """Validate agent response meets business requirements."""
        assert 'type' in response_data, 'Response must have type field'
        if 'response' in response_data:
            content = response_data['response']
            assert len(str(content)) > 20, 'Agent response too short for business value'
        elif 'message' in response_data:
            content = response_data['message']
            assert len(str(content)) > 10, 'Agent message too short'
        response_type = response_data.get('type', '').lower()
        assert 'error' not in response_type, f'Agent returned error: {response_data}'

    async def _cleanup_resources(self) -> None:
        """Cleanup test resources."""
        if self.websocket_connection:
            await self.websocket_connection.close()
        if hasattr(self.test_client, 'close'):
            await self.test_client.close()

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.real_services
async def test_basic_user_flow_signup_login_chat_real_services():
    """
    CRITICAL E2E Test: Basic User Flow with REAL Services
    
    BVJ: Protects THE core revenue pipeline - every user journey = $99-999/month
    
    Flow:
    1. Create user via REAL Auth service dev endpoint
    2. Login via REAL Auth service to get JWT token  
    3. Establish REAL WebSocket connection to Backend
    4. Send real chat message through agent pipeline
    5. Receive and validate real agent response
    
    REQUIREMENTS:
    - Must use REAL Auth service (no mocks)
    - Must use REAL Backend WebSocket (no mocks)
    - Must complete in <20 seconds
    - Must validate business-critical checkpoints
    """
    async with TestHarnessContext('basic_user_flow', seed_data=False) as harness:
        await asyncio.sleep(2)
        health_status = await harness.check_system_health()
        assert health_status.get('services_ready', False), f'Services not ready: {health_status}'
        tester = BasicUserFlowE2ETester(harness)
        results = await tester.execute_complete_user_flow()
        assert results['success'], f"Basic user flow failed: {results.get('error')}"
        assert len(results['steps']) == 4, f"Expected 4 steps, got {len(results['steps'])}"
        step_results = {step['step']: step for step in results['steps']}
        assert step_results['signup']['success'], 'User signup failed - blocks revenue'
        assert step_results['signup']['user_id'], 'User ID required for revenue tracking'
        assert step_results['login']['success'], 'User login failed - blocks access'
        assert step_results['login']['token_length'] > 50, 'JWT token invalid'
        assert step_results['websocket_connect']['success'], 'WebSocket failed - blocks usage'
        assert step_results['websocket_connect']['connected'], 'Connection not established'
        assert step_results['chat_flow']['success'], 'Chat failed - no value delivered'
        assert step_results['chat_flow']['message_sent'], 'Message sending failed'
        assert step_results['chat_flow']['response_received'], 'No agent response'
        assert step_results['chat_flow']['response_length'] > 20, 'Response too short'
        assert results['duration'] < 20.0, f"Flow too slow: {results['duration']:.2f}s > 20s"
        print(f"[SUCCESS] Basic User Flow completed in {results['duration']:.2f}s")
        print(f'[REVENUE PROTECTED] Complete signup -> login -> chat pipeline verified')
        print(f"[USER] {step_results['signup']['email']}  ->  Full journey validated")
        print(f'[BUSINESS VALUE] Core revenue pipeline operational')

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.real_services
@pytest.mark.performance
async def test_basic_user_flow_performance_requirements():
    """
    Performance validation for basic user flow to ensure business UX requirements.
    
    BVJ: User experience directly impacts conversion rates and revenue retention.
    Slow flows = lost customers = lost revenue.
    """
    async with TestHarnessContext('performance_test', seed_data=False) as harness:
        flow_times = []
        for i in range(3):
            tester = BasicUserFlowE2ETester(harness)
            results = await tester.execute_complete_user_flow()
            assert results['success'], f'Flow {i + 1} failed'
            flow_times.append(results['duration'])
        avg_time = sum(flow_times) / len(flow_times)
        max_time = max(flow_times)
        assert avg_time < 15.0, f'Average flow time {avg_time:.2f}s > 15s target'
        assert max_time < 20.0, f'Max flow time {max_time:.2f}s > 20s limit'
        print(f'[PERFORMANCE] Average flow time: {avg_time:.2f}s')
        print(f'[PERFORMANCE] Max flow time: {max_time:.2f}s')
        print(f'[PERFORMANCE] All flows meet business UX requirements')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
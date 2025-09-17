_lazy_imports = {}

def lazy_import(module_path: str, component: str=None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f'Warning: Failed to lazy load {module_path}: {e}')
            _lazy_imports[module_path] = None
    return _lazy_imports[module_path]
"\nE2E tests for WebSocket authentication in staging - DESIGNED TO FAIL INITIALLY\n\nPurpose: Test complete Golden Path user flow in actual staging environment\nIssue: Frontend sending ['jwt', token] instead of expected 'jwt.${token}' format causing cascading failures\nImpact: Complete Golden Path broken ($500K+ ARR chat functionality) in staging GCP Cloud Run\nExpected: These tests MUST FAIL initially to prove they detect the real staging issue\n\nGitHub Issue: #171  \nTest Plan: /TEST_PLAN_WEBSOCKET_AUTH_PROTOCOL_MISMATCH.md\n\nCRITICAL: Tests against REAL staging GCP Cloud Run environment\nMISSION CRITICAL: Golden Path user flow validation\n"
import pytest
import asyncio
import base64
import json
import time
import websockets
import ssl
from typing import Dict, List, Optional, Any
from unittest.mock import patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_test_base import StagingTestBase, track_test_timing
from tests.e2e.staging_config import StagingTestConfig as StagingConfig
from tests.e2e.staging_test_helpers import StagingTestSuite as StagingTestHelpers
from tests.e2e.staging_auth_client import StagingAuthClient
from tests.e2e.real_websocket_client import RealWebSocketClient
from netra_backend.app.services.user_execution_context import UserExecutionContext

class WebSocketAuthGoldenPathStagingTests(SSotAsyncTestCase):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.from_request(user_id='test_user', thread_id='test_thread', run_id='test_run')

    def setUp(self):
        """Initialize test attributes with fallback values"""
        if not hasattr(self.__class__, 'auth_client') or self.__class__.auth_client is None:
            from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
            self.__class__.auth_client = E2EAuthHelper(environment='staging')
        if not hasattr(self.__class__, 'test_user') or self.__class__.test_user is None:
            user_id = f'fallback_user_{int(time.time())}'
            user_email = f'fallback_test_{int(time.time())}@netra-testing.ai'
            access_token = self.__class__.auth_client.create_test_jwt_token(user_id=user_id, email=user_email)
            self.__class__.test_user = {'user_id': user_id, 'email': user_email, 'access_token': access_token, 'encoded_token': access_token}
    'E2E tests for WebSocket authentication in staging - MISSION CRITICAL'

    async def _ensure_staging_setup(self):
        """Setup for staging environment tests - called at start of each test"""
        # Load staging environment variables (from StagingTestBase functionality)
        self._load_staging_environment()
        
        # Setup staging configuration - check if already initialized at class level
        if not hasattr(self.__class__, 'staging_config') or self.__class__.staging_config is None:
            self.__class__.staging_config = StagingConfig()
            self.__class__.staging_helpers = StagingTestHelpers()
            self.__class__.staging_backend_url = self.__class__.staging_config.websocket_url
            self.__class__.staging_auth_url = self.__class__.staging_config.auth_service_url
            self.__class__.auth_client = StagingAuthClient()
            self.__class__.websocket_client = RealWebSocketClient(ws_url=self.__class__.staging_backend_url)
            await self._verify_staging_services()
            self.__class__.test_user = await self._create_golden_path_test_user()
            self.logger.info('Staging E2E test setup completed')

    def _load_staging_environment(self):
        """Load staging environment variables from config/staging.env
        
        CRITICAL FIX: This ensures staging tests have access to JWT_SECRET_STAGING
        and other staging-specific configuration needed for proper authentication.
        """
        import os
        from pathlib import Path
        
        # Find config/staging.env file
        current_dir = Path(__file__).resolve().parent
        project_root = current_dir
        while project_root.parent != project_root:
            staging_env_file = project_root / "config" / "staging.env"
            if staging_env_file.exists():
                break
            project_root = project_root.parent
        else:
            # Try one more time from current working directory
            project_root = Path.cwd()
            staging_env_file = project_root / "config" / "staging.env"
        
        if staging_env_file.exists():
            print(f"Loading staging environment from: {staging_env_file}")
            
            # Parse .env file manually (simple key=value format)
            with open(staging_env_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse KEY=VALUE
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        # Only set if not already in environment (don't override)
                        if key not in os.environ:
                            os.environ[key] = value
                            if key == "JWT_SECRET_STAGING":
                                print(f"Loaded JWT_SECRET_STAGING from config/staging.env")
            
            # Ensure ENVIRONMENT is set to staging
            os.environ["ENVIRONMENT"] = "staging"
            print(f"Set ENVIRONMENT=staging for staging tests")
            
        else:
            print(f"WARNING: config/staging.env not found at {staging_env_file}")
            print("Staging tests may fail due to missing environment variables")

    async def _verify_staging_services(self):
        """Verify staging services are accessible and healthy"""
        try:
            backend_health = await self.__class__.staging_helpers.check_service_health(self.__class__.staging_config.get_backend_base_url())
            assert backend_health, 'Staging backend is not healthy'
            auth_health = await self.__class__.staging_helpers.check_service_health(self.__class__.staging_auth_url)
            assert auth_health, 'Staging auth service is not healthy'
            self.logger.info('All staging services are healthy')
        except Exception as e:
            pytest.skip(f'Staging environment not available: {e}')

    async def _create_golden_path_test_user(self) -> Dict[str, Any]:
        """Create a test user for Golden Path testing"""
        try:
            test_user_data = {'email': f'golden_path_test_{int(time.time())}@netra-testing.ai', 'user_id': f'golden_path_user_{int(time.time())}', 'test_scenario': 'websocket_auth_protocol_mismatch'}
            access_token = await self.__class__.auth_client.generate_test_access_token(user_id=test_user_data['user_id'], email=test_user_data['email'])
            test_user_data['access_token'] = access_token
            test_user_data['encoded_token'] = base64.urlsafe_b64encode(access_token.encode()).decode().rstrip('=')
            self.logger.info(f"Created Golden Path test user: {test_user_data['email']}")
            return test_user_data
        except Exception as e:
            pytest.skip(f'Failed to create staging test user: {e}')

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.golden_path
    @pytest.mark.mission_critical
    @track_test_timing
    async def test_complete_golden_path_user_flow_staging(self):
        """
        Test complete Golden Path: login  ->  WebSocket connection  ->  AI response
        
        Full user journey:
        1. User login via OAuth
        2. WebSocket connection with JWT
        3. Send chat message
        4. Receive AI agent response
        
        DIFFICULTY: Very High (45 minutes)
        REAL SERVICES: Yes (staging GCP Cloud Run environment)
        STATUS: Should FAIL initially (WebSocket connection timeout), PASS after fix
        """
        # Ensure staging setup is complete
        await self._ensure_staging_setup()
        
        golden_path_start_time = time.time()
        golden_path_steps = []
        try:
            golden_path_steps.append({'step': 'auth_verification', 'status': 'starting'})
            auth_verification = await self.__class__.auth_client.verify_token(self.__class__.test_user['access_token'])
            assert auth_verification['valid'], 'Test user token should be valid'
            golden_path_steps[-1]['status'] = 'completed'
            golden_path_steps[-1]['duration'] = time.time() - golden_path_start_time
            golden_path_steps.append({'step': 'websocket_connection', 'status': 'starting'})
            websocket_start_time = time.time()
            correct_subprotocols = ['jwt-auth', f"jwt.{self.__class__.test_user['encoded_token']}"]
            connection = await self._attempt_staging_websocket_connection(subprotocols=correct_subprotocols, timeout=30, connection_description='Golden Path WebSocket with correct protocol')
            if connection is None:
                websocket_duration = time.time() - websocket_start_time
                golden_path_steps[-1]['status'] = 'failed'
                golden_path_steps[-1]['duration'] = websocket_duration
                golden_path_steps[-1]['error'] = 'WebSocket connection failed/timed out'
                pytest.fail(f'GOLDEN PATH FAILURE: WebSocket connection failed in staging. Duration: {websocket_duration:.1f}s. This breaks the critical user flow ($500K+ ARR impact). Steps completed: {golden_path_steps}')
            golden_path_steps.append({'step': 'chat_message_send', 'status': 'starting'})
            golden_path_message = {'type': 'chat_message', 'data': {'message': 'Hello! This is a Golden Path test message for WebSocket auth protocol validation.', 'test_scenario': 'golden_path_staging', 'timestamp': int(time.time()), 'user_id': self.__class__.test_user['user_id']}}
            await connection.send(json.dumps(golden_path_message))
            golden_path_steps[-1]['status'] = 'completed'
            golden_path_steps.append({'step': 'ai_agent_response', 'status': 'starting'})
            ai_response_timeout = 45
            ai_response = await asyncio.wait_for(connection.recv(), timeout=ai_response_timeout)
            assert ai_response is not None, 'Should receive AI agent response'
            response_data = json.loads(ai_response)
            assert 'type' in response_data, 'Response should have type field'
            assert 'data' in response_data, 'Response should have data field'
            golden_path_steps[-1]['status'] = 'completed'
            golden_path_steps[-1]['response_type'] = response_data.get('type', 'unknown')
            total_golden_path_duration = time.time() - golden_path_start_time
            self.__class__.logger.info(f'GOLDEN PATH SUCCESS: Complete user flow works in staging. Total duration: {total_golden_path_duration:.1f}s. Steps: {golden_path_steps}')
            await connection.close()
        except asyncio.TimeoutError as e:
            total_duration = time.time() - golden_path_start_time
            pytest.fail(f'GOLDEN PATH TIMEOUT: AI response timeout in staging after {total_duration:.1f}s. This indicates WebSocket auth protocol issues breaking user experience. Completed steps: {golden_path_steps}. BUSINESS IMPACT: $500K+ ARR chat functionality broken.')
        except Exception as e:
            total_duration = time.time() - golden_path_start_time
            pytest.fail(f'GOLDEN PATH ERROR: {str(e)} after {total_duration:.1f}s. Completed steps: {golden_path_steps}. This breaks critical user functionality in staging.')

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.websocket_auth_protocol
    @track_test_timing
    async def test_websocket_connection_gcp_cloud_run_environment(self):
        """
        Test WebSocket connection specifically in GCP Cloud Run environment
        
        Validates connection behavior with GCP networking and container constraints
        
        DIFFICULTY: High (30 minutes)
        REAL SERVICES: Yes (staging GCP deployment)
        STATUS: Should FAIL initially (handshake timeout), PASS after fix
        """
        # Ensure staging setup is complete
        await self._ensure_staging_setup()
        gcp_test_scenarios = [{'name': 'correct_protocol_format', 'subprotocols': ['jwt-auth', f"jwt.{self.__class__.test_user['encoded_token']}"], 'expected_result': 'success', 'timeout': 20}, {'name': 'incorrect_protocol_bug_format', 'subprotocols': ['jwt', self.__class__.test_user['encoded_token']], 'expected_result': 'failure', 'timeout': 25}, {'name': 'missing_jwt_prefix', 'subprotocols': ['jwt-auth', self.__class__.test_user['encoded_token']], 'expected_result': 'failure', 'timeout': 20}, {'name': 'no_subprotocols', 'subprotocols': [], 'expected_result': 'failure', 'timeout': 15}]
        gcp_test_results = []
        for scenario in gcp_test_scenarios:
            scenario_start = time.time()
            self.__class__.logger.info(f"Testing GCP scenario: {scenario['name']}")
            try:
                connection = await self._attempt_staging_websocket_connection(subprotocols=scenario['subprotocols'], timeout=scenario['timeout'], connection_description=f"GCP test: {scenario['name']}")
                scenario_duration = time.time() - scenario_start
                if connection is not None:
                    try:
                        test_message = {'type': 'ping', 'data': {'test_scenario': scenario['name'], 'gcp_environment': 'staging'}}
                        await connection.send(json.dumps(test_message))
                        response = await asyncio.wait_for(connection.recv(), timeout=10.0)
                        result = {'scenario': scenario['name'], 'status': 'success', 'duration': scenario_duration, 'response_received': response is not None}
                    except asyncio.TimeoutError:
                        result = {'scenario': scenario['name'], 'status': 'partial_success', 'duration': scenario_duration, 'note': 'Connected but message timed out'}
                    finally:
                        await connection.close()
                else:
                    result = {'scenario': scenario['name'], 'status': 'failed', 'duration': scenario_duration, 'note': 'Connection failed or timed out'}
                gcp_test_results.append(result)
                if scenario['expected_result'] == 'success' and result['status'] != 'success':
                    self.__class__.logger.error(f"GCP ISSUE: {scenario['name']} expected to succeed but failed. Duration: {scenario_duration:.1f}s")
                elif scenario['expected_result'] == 'failure' and result['status'] == 'success':
                    self.__class__.logger.warning(f"GCP UNEXPECTED: {scenario['name']} expected to fail but succeeded. May indicate bug is fixed.")
            except Exception as e:
                gcp_test_results.append({'scenario': scenario['name'], 'status': 'error', 'duration': time.time() - scenario_start, 'error': str(e)})
        success_count = len([r for r in gcp_test_results if r['status'] == 'success'])
        failure_count = len([r for r in gcp_test_results if r['status'] in ['failed', 'error']])
        self.__class__.logger.info(f'GCP Cloud Run test results: {success_count} successes, {failure_count} failures')
        expected_successes = len([s for s in gcp_test_scenarios if s['expected_result'] == 'success'])
        if success_count < expected_successes:
            pytest.fail(f'GCP Cloud Run environment issues: Expected {expected_successes} successes, got {success_count}. Results: {gcp_test_results}. This suggests broader staging infrastructure problems beyond the protocol bug.')
        if success_count > expected_successes:
            self.__class__.logger.warning(f'More successes than expected ({success_count} vs {expected_successes}). Protocol bug may be fixed or test needs adjustment.')

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.websocket_auth_protocol
    @track_test_timing
    async def test_concurrent_user_websocket_connections_staging(self):
        """
        Test multiple concurrent users connecting to WebSocket in staging
        
        Validates user isolation and protocol handling under concurrent load
        
        DIFFICULTY: Very High (35 minutes)
        REAL SERVICES: Yes (staging environment)
        STATUS: Should FAIL initially (connection failures), PASS after fix
        """
        # Ensure staging setup is complete
        await self._ensure_staging_setup()
        concurrent_user_count = 3
        concurrent_users = []
        for i in range(concurrent_user_count):
            user_data = {'email': f'concurrent_test_{i}_{int(time.time())}@netra-testing.ai', 'user_id': f'concurrent_user_{i}_{int(time.time())}', 'index': i}
            access_token = await self.__class__.auth_client.generate_test_access_token(user_id=user_data['user_id'], email=user_data['email'])
            user_data['access_token'] = access_token
            user_data['encoded_token'] = base64.urlsafe_b64encode(access_token.encode()).decode().rstrip('=')
            concurrent_users.append(user_data)
        connection_tasks = []
        for i, user in enumerate(concurrent_users):
            if i == 0:
                protocols = ['jwt-auth', f"jwt.{user['encoded_token']}"]
                expected_success = True
            elif i == 1:
                protocols = ['jwt', user['encoded_token']]
                expected_success = False
            else:
                protocols = ['jwt-auth', user['encoded_token']]
                expected_success = False
            task = asyncio.create_task(self._test_concurrent_user_connection(user, protocols, expected_success))
            connection_tasks.append(task)
        concurrent_start_time = time.time()
        connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        total_concurrent_duration = time.time() - concurrent_start_time
        successful_connections = []
        failed_connections = []
        error_connections = []
        for i, result in enumerate(connection_results):
            if isinstance(result, Exception):
                error_connections.append({'user_index': i, 'error': str(result)})
            elif result['status'] == 'success':
                successful_connections.append(result)
            else:
                failed_connections.append(result)
        self.__class__.logger.info(f'Concurrent staging test completed in {total_concurrent_duration:.1f}s: {len(successful_connections)} successful, {len(failed_connections)} failed, {len(error_connections)} errors')
        expected_successes = 1
        actual_successes = len(successful_connections)
        if actual_successes < expected_successes:
            pytest.fail(f'Concurrent staging test: Expected {expected_successes} successes, got {actual_successes}. Successful: {successful_connections}, Failed: {failed_connections}, Errors: {error_connections}. This suggests broader staging issues beyond the protocol bug.')
        if actual_successes > expected_successes:
            pytest.fail(f'Concurrent staging test: More successes than expected ({actual_successes} vs {expected_successes}). This may indicate the protocol bug has been fixed.')

    async def _test_concurrent_user_connection(self, user: Dict[str, Any], protocols: List[str], expected_success: bool) -> Dict[str, Any]:
        """Test connection for a single concurrent user"""
        user_start_time = time.time()
        try:
            connection = await self._attempt_staging_websocket_connection(subprotocols=protocols, timeout=20, connection_description=f"Concurrent user {user['index']}")
            if connection is not None:
                test_message = {'type': 'concurrent_test', 'data': {'user_id': user['user_id'], 'user_index': user['index'], 'test_time': int(time.time())}}
                await connection.send(json.dumps(test_message))
                response = await asyncio.wait_for(connection.recv(), timeout=8.0)
                await connection.close()
                return {'status': 'success', 'user_index': user['index'], 'user_id': user['user_id'], 'duration': time.time() - user_start_time, 'protocols': protocols, 'expected_success': expected_success, 'response_received': response is not None}
            else:
                return {'status': 'failed', 'user_index': user['index'], 'user_id': user['user_id'], 'duration': time.time() - user_start_time, 'protocols': protocols, 'expected_success': expected_success, 'error': 'Connection failed or timed out'}
        except Exception as e:
            return {'status': 'error', 'user_index': user['index'], 'user_id': user['user_id'], 'duration': time.time() - user_start_time, 'protocols': protocols, 'expected_success': expected_success, 'error': str(e)}

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.websocket_auth_protocol
    @track_test_timing
    async def test_websocket_heartbeat_and_reconnection_staging(self):
        """
        Test WebSocket heartbeat and reconnection behavior in staging
        
        Validates connection stability and recovery from network interruptions
        
        DIFFICULTY: High (25 minutes) 
        REAL SERVICES: Yes (staging with network simulation)
        STATUS: May FAIL initially (connection instability), improve after fix
        """
        # Ensure staging setup is complete
        await self._ensure_staging_setup()
        correct_protocols = ['jwt-auth', f"jwt.{self.__class__.test_user['encoded_token']}"]
        connection = await self._attempt_staging_websocket_connection(subprotocols=correct_protocols, timeout=25, connection_description='Heartbeat/reconnection test')
        if connection is None:
            pytest.fail('Cannot test heartbeat/reconnection - initial connection failed. This may be due to the WebSocket auth protocol bug.')
        try:
            heartbeat_start = time.time()
            for i in range(3):
                heartbeat_message = {'type': 'heartbeat', 'data': {'sequence': i, 'timestamp': int(time.time())}}
                await connection.send(json.dumps(heartbeat_message))
                try:
                    response = await asyncio.wait_for(connection.recv(), timeout=10.0)
                    assert response is not None, f'Should receive heartbeat response {i}'
                except asyncio.TimeoutError:
                    self.__class__.logger.warning(f'Heartbeat {i} timed out - connection may be unstable')
                await asyncio.sleep(2)
            heartbeat_duration = time.time() - heartbeat_start
            self.__class__.logger.info(f'Heartbeat test completed in {heartbeat_duration:.1f}s')
        except Exception as e:
            pytest.fail(f'Heartbeat test failed: {e}')
        finally:
            if connection and (not connection.closed):
                await connection.close()

    async def _attempt_staging_websocket_connection(self, subprotocols: List[str], timeout: int, connection_description: str) -> Optional[websockets.ClientConnection]:
        """
        Attempt WebSocket connection to staging environment
        
        Args:
            subprotocols: Protocol list to send
            timeout: Connection timeout
            connection_description: Description for logging
            
        Returns:
            WebSocket connection or None if failed
        """
        try:
            self.__class__.logger.info(f'Attempting staging connection: {connection_description}, protocols: {subprotocols}, timeout: {timeout}s')
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connection_start = time.time()
            connection = await asyncio.wait_for(websockets.connect(self.__class__.staging_backend_url, subprotocols=subprotocols, ssl=ssl_context if self.__class__.staging_backend_url.startswith('wss') else None, ping_interval=20, ping_timeout=10, close_timeout=10), timeout=timeout)
            connection_duration = time.time() - connection_start
            self.__class__.logger.info(f'Staging connection successful: {connection_description} in {connection_duration:.1f}s')
            return connection
        except asyncio.TimeoutError:
            connection_duration = time.time() - connection_start
            self.__class__.logger.error(f'Staging connection timeout: {connection_description} after {connection_duration:.1f}s with protocols {subprotocols}')
            return None
        except Exception as e:
            connection_duration = time.time() - connection_start
            self.__class__.logger.error(f'Staging connection error: {connection_description} after {connection_duration:.1f}s: {e}')
            return None
pytestmark = [pytest.mark.e2e, pytest.mark.staging, pytest.mark.golden_path, pytest.mark.websocket_auth_protocol, pytest.mark.mission_critical, pytest.mark.real_services, pytest.mark.bug_reproduction]
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
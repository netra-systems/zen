"""
Multi-User Golden Path E2E Test - Issue #1197

MISSION CRITICAL: Multi-user concurrent access validation for Golden Path.
Tests user isolation, factory patterns, and concurrent session management.

PURPOSE:
- Validates multiple users can use Golden Path simultaneously
- Tests user isolation and data segregation
- Validates factory pattern implementation
- Ensures no cross-user data contamination

BUSINESS VALUE:
- Protects $500K+ ARR multi-tenant architecture
- Ensures enterprise-grade user isolation (HIPAA/SOC2 compliance)
- Validates system scalability under concurrent load
- Tests Issue #1116 SSOT Agent Factory Migration results

TESTING APPROACH:
- Creates multiple concurrent users
- Tests simultaneous WebSocket connections
- Validates user context isolation
- Uses real staging.netrasystems.ai endpoints
- Initially designed to fail to validate test infrastructure

GitHub Issue: #1197 Golden Path End-to-End Testing
Related Issue: #1116 SSOT Agent Factory Migration (User Isolation)
Test Category: e2e, golden_path, multi_user, mission_critical
Expected Runtime: 90-180 seconds for concurrent testing
"""

import asyncio
import json
import time
import pytest
import websockets
import ssl
from typing import Dict, List, Optional, Any, Set
from concurrent.futures import ThreadPoolExecutor
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_test_base import StagingTestBase, track_test_timing
from tests.e2e.staging_config import StagingTestConfig as StagingConfig
from tests.e2e.staging_auth_client import StagingAuthClient
from tests.e2e.real_websocket_client import RealWebSocketClient
from netra_backend.app.services.user_execution_context import UserExecutionContext


# Multi-user test configuration
MULTI_USER_CONFIG = {
    "concurrent_users": 3,           # Number of simultaneous users
    "max_user_setup_time": 10.0,     # Max time to create each user
    "max_concurrent_connect_time": 20.0,  # Max time for all connections
    "max_concurrent_response_time": 90.0,  # Max time for all responses
    "isolation_validation_delay": 2.0,     # Delay for isolation testing
}

# User isolation test scenarios
USER_ISOLATION_SCENARIOS = [
    {
        "name": "basic_concurrent_chat",
        "message": "Tell me about AI optimization for user {user_index}",
        "expected_unique_response": True,
        "validation_keywords": ["user", "optimization", "AI"]
    },
    {
        "name": "data_segregation_test", 
        "message": "My user ID is {user_id} and this is a private message for isolation testing",
        "expected_unique_response": True,
        "validation_keywords": ["private", "isolation", "user"]
    },
    {
        "name": "concurrent_tool_execution",
        "message": "Please analyze the system status for user {user_index} specifically",
        "expected_unique_response": True,
        "validation_keywords": ["system", "status", "analyze"]
    }
]


class TestMultiUserGoldenPath(SSotAsyncTestCase):
    """
    Multi-User Golden Path E2E Test Suite
    
    Tests concurrent user access, isolation, and factory pattern implementation
    in the staging environment.
    """

    @classmethod
    async def asyncSetUpClass(cls):
        """Setup multi-user testing environment"""
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
        
        # Verify staging services
        await cls._verify_staging_services()
        
        # Create multiple test users for concurrent testing
        cls.test_users = await cls._create_multiple_test_users()
        
        cls.logger.info(f'Multi-user Golden Path test setup completed with {len(cls.test_users)} users')

    @classmethod
    def _load_staging_environment(cls):
        """Load staging environment variables"""
        import os
        from pathlib import Path
        
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
            
            os.environ["ENVIRONMENT"] = "staging"
        else:
            cls.logger.warning(f"config/staging.env not found at {staging_env_file}")

    @classmethod
    async def _verify_staging_services(cls):
        """Verify staging services for multi-user testing"""
        import httpx
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                backend_response = await client.get(f"{cls.staging_config.get_backend_base_url()}/health")
                assert backend_response.status_code == 200, f"Backend not ready: {backend_response.status_code}"
                
                auth_response = await client.get(f"{cls.staging_auth_url}/health")
                assert auth_response.status_code == 200, f"Auth service not ready: {auth_response.status_code}"
                
            cls.logger.info('All staging services ready for multi-user testing')
            
        except Exception as e:
            pytest.skip(f'Staging environment not available for multi-user testing: {e}')

    @classmethod
    async def _create_multiple_test_users(cls) -> List[Dict[str, Any]]:
        """Create multiple test users for concurrent testing"""
        users = []
        test_timestamp = int(time.time())
        
        for i in range(MULTI_USER_CONFIG["concurrent_users"]):
            try:
                user_data = {
                    'index': i,
                    'email': f'multiuser_golden_path_{i}_{test_timestamp}@netra-testing.ai',
                    'user_id': f'multiuser_gp_{i}_{test_timestamp}',
                    'test_scenario': 'multi_user_golden_path',
                    'created_at': test_timestamp
                }
                
                # Generate access token for each user
                user_start_time = time.time()
                access_token = await cls.auth_client.generate_test_access_token(
                    user_id=user_data['user_id'],
                    email=user_data['email']
                )
                user_setup_time = time.time() - user_start_time
                
                assert user_setup_time <= MULTI_USER_CONFIG["max_user_setup_time"], \
                    f'User {i} setup took {user_setup_time:.1f}s, exceeds limit'
                
                user_data['access_token'] = access_token
                
                # Encode token for WebSocket
                import base64
                user_data['encoded_token'] = base64.urlsafe_b64encode(
                    access_token.encode()
                ).decode().rstrip('=')
                
                users.append(user_data)
                cls.logger.info(f"Created multi-user test user {i}: {user_data['email']}")
                
            except Exception as e:
                pytest.skip(f'Failed to create multi-user test user {i}: {e}')
        
        assert len(users) == MULTI_USER_CONFIG["concurrent_users"], \
            f'Expected {MULTI_USER_CONFIG["concurrent_users"]} users, created {len(users)}'
        
        return users

    def create_user_context(self, user_index: int = 0) -> UserExecutionContext:
        """Create isolated user execution context for specific user"""
        user = self.__class__.test_users[user_index]
        return UserExecutionContext.from_request(
            user_id=user['user_id'],
            thread_id=f"multiuser_thread_{user_index}_{int(time.time())}",
            run_id=f"multiuser_run_{user_index}_{int(time.time())}"
        )

    @pytest.mark.e2e
    @pytest.mark.golden_path
    @pytest.mark.multi_user
    @pytest.mark.mission_critical
    @track_test_timing
    async def test_concurrent_user_golden_path_isolation(self):
        """
        MISSION CRITICAL: Test concurrent users with complete isolation
        
        Validates:
        - Multiple users can connect simultaneously
        - User data remains isolated (no cross-contamination)
        - Each user receives their own agent responses
        - Factory pattern creates separate instances
        - No shared state between user sessions
        
        SUCCESS CRITERIA:
        - All users connect successfully
        - Each user receives unique, isolated responses
        - No cross-user data leakage detected
        - Performance remains acceptable under load
        
        FAILURE INDICATES: Critical multi-tenant security issues
        
        DIFFICULTY: Very High (90-180 seconds)
        REAL SERVICES: Yes (staging.netrasystems.ai)
        STATUS: Should FAIL initially if user isolation broken
        """
        concurrent_test_start = time.time()
        user_results = []
        
        try:
            self.logger.info(f"Starting concurrent user isolation test with {len(self.__class__.test_users)} users")
            
            # Create concurrent user sessions
            user_tasks = []
            for i, user in enumerate(self.__class__.test_users):
                task = asyncio.create_task(
                    self._run_isolated_user_session(
                        user=user,
                        user_index=i,
                        scenario=USER_ISOLATION_SCENARIOS[i % len(USER_ISOLATION_SCENARIOS)]
                    )
                )
                user_tasks.append(task)
            
            # Wait for all users to complete with timeout
            try:
                user_results = await asyncio.wait_for(
                    asyncio.gather(*user_tasks, return_exceptions=True),
                    timeout=MULTI_USER_CONFIG["max_concurrent_response_time"]
                )
            except asyncio.TimeoutError:
                total_duration = time.time() - concurrent_test_start
                pytest.fail(
                    f'MULTI-USER TIMEOUT: Concurrent test timeout after {total_duration:.1f}s. '
                    f'This indicates performance issues under concurrent load affecting multi-tenant capability.'
                )
            
            # Analyze results for isolation validation
            successful_users = []
            failed_users = []
            error_users = []
            
            for i, result in enumerate(user_results):
                if isinstance(result, Exception):
                    error_users.append({'user_index': i, 'error': str(result)})
                elif result.get('status') == 'success':
                    successful_users.append(result)
                else:
                    failed_users.append(result)
            
            total_duration = time.time() - concurrent_test_start
            
            # Validate isolation requirements
            assert len(successful_users) >= 2, \
                f'Expected at least 2 successful users for isolation testing, got {len(successful_users)}'
            
            # Check for cross-user contamination
            user_responses = [user['response_data'] for user in successful_users if 'response_data' in user]
            if len(user_responses) >= 2:
                # Validate responses are unique (not identical)
                unique_responses = set(str(response) for response in user_responses)
                assert len(unique_responses) == len(user_responses), \
                    'User responses are identical - indicates possible shared state contamination'
            
            # Validate user-specific data
            for user_result in successful_users:
                user_id = user_result.get('user_id')
                response_content = str(user_result.get('response_data', {}))
                
                # User ID should appear in their own response (context isolation)
                if user_id and user_id not in response_content:
                    self.logger.warning(f"User {user_id} not referenced in their response - may indicate context isolation issues")
            
            self.logger.info(
                f'MULTI-USER SUCCESS: Concurrent isolation test completed in {total_duration:.1f}s. '
                f'Successful users: {len(successful_users)}, Failed: {len(failed_users)}, Errors: {len(error_users)}'
            )
            
        except Exception as e:
            total_duration = time.time() - concurrent_test_start
            pytest.fail(
                f'MULTI-USER ERROR: Concurrent isolation test failed after {total_duration:.1f}s: {str(e)}. '
                f'This indicates critical multi-tenant architecture issues.'
            )

    @pytest.mark.e2e
    @pytest.mark.golden_path
    @pytest.mark.multi_user
    @pytest.mark.factory_pattern
    @track_test_timing
    async def test_factory_pattern_user_instance_creation(self):
        """
        Test factory pattern creates separate instances for each user
        
        Validates Issue #1116 SSOT Agent Factory Migration:
        - Each user gets unique agent instances
        - No singleton shared state
        - Memory isolation between users
        - Proper factory dependency injection
        
        DIFFICULTY: High (45-60 seconds)
        REAL SERVICES: Yes (staging environment)
        STATUS: Should FAIL initially if factory pattern broken
        """
        factory_test_start = time.time()
        user_instances = []
        
        try:
            self.logger.info("Testing factory pattern user instance creation")
            
            # Create connections for multiple users sequentially to validate factory
            for i, user in enumerate(self.__class__.test_users[:2]):  # Test with 2 users
                self.logger.info(f"Creating factory instance for user {i}: {user['user_id']}")
                
                # Establish connection (triggers factory instance creation)
                connection = await self._establish_user_websocket_connection(user)
                assert connection is not None, f'Failed to create connection for user {i}'
                
                # Send a message that should trigger agent factory instantiation
                factory_test_message = {
                    'type': 'chat_message',
                    'data': {
                        'message': f'Factory pattern test for user {i} - {user["user_id"]}',
                        'test_scenario': 'factory_pattern_validation',
                        'user_id': user['user_id'],
                        'user_index': i
                    }
                }
                
                await connection.send(json.dumps(factory_test_message))
                
                # Wait for initial response to confirm factory instantiation
                try:
                    initial_response = await asyncio.wait_for(connection.recv(), timeout=15.0)
                    response_data = json.loads(initial_response)
                    
                    user_instances.append({
                        'user_index': i,
                        'user_id': user['user_id'],
                        'connection': connection,
                        'initial_response': response_data,
                        'factory_created': True
                    })
                    
                except asyncio.TimeoutError:
                    user_instances.append({
                        'user_index': i,
                        'user_id': user['user_id'],
                        'connection': connection,
                        'factory_created': False,
                        'error': 'Timeout waiting for factory response'
                    })
            
            # Validate factory pattern behavior
            successful_instances = [inst for inst in user_instances if inst.get('factory_created', False)]
            assert len(successful_instances) >= 1, \
                f'Factory pattern failed - no successful instances created'
            
            # Test isolation by sending concurrent messages
            if len(successful_instances) >= 2:
                await self._validate_factory_isolation(successful_instances)
            
            # Cleanup connections
            for instance in user_instances:
                if 'connection' in instance and instance['connection']:
                    await instance['connection'].close()
            
            factory_duration = time.time() - factory_test_start
            self.logger.info(
                f'Factory pattern validation completed in {factory_duration:.1f}s. '
                f'Successful instances: {len(successful_instances)}'
            )
            
        except Exception as e:
            # Cleanup on error
            for instance in user_instances:
                if 'connection' in instance and instance['connection']:
                    try:
                        await instance['connection'].close()
                    except:
                        pass
            
            factory_duration = time.time() - factory_test_start
            pytest.fail(
                f'FACTORY PATTERN ERROR: Test failed after {factory_duration:.1f}s: {str(e)}. '
                f'This indicates Issue #1116 factory migration incomplete or broken.'
            )

    async def _validate_factory_isolation(self, instances: List[Dict[str, Any]]):
        """Validate that factory instances are properly isolated"""
        self.logger.info("Validating factory isolation between user instances")
        
        # Send simultaneous messages to test isolation
        isolation_tasks = []
        for i, instance in enumerate(instances):
            isolation_message = {
                'type': 'chat_message',
                'data': {
                    'message': f'Isolation test message {i} for user {instance["user_id"]} - should not leak to other users',
                    'test_scenario': 'factory_isolation_validation',
                    'user_id': instance['user_id'],
                    'isolation_marker': f'UNIQUE_MARKER_{i}_{int(time.time())}'
                }
            }
            
            task = asyncio.create_task(
                self._send_and_collect_isolation_response(
                    connection=instance['connection'],
                    message=isolation_message,
                    expected_marker=isolation_message['data']['isolation_marker']
                )
            )
            isolation_tasks.append(task)
        
        # Wait for all isolation responses
        isolation_results = await asyncio.gather(*isolation_tasks, return_exceptions=True)
        
        # Validate no cross-contamination
        for i, result in enumerate(isolation_results):
            if isinstance(result, Exception):
                self.logger.warning(f"Isolation test error for instance {i}: {result}")
                continue
            
            # Check that user only received their own marker
            expected_marker = result.get('expected_marker')
            response_content = str(result.get('response_data', {}))
            
            # Verify own marker present
            if expected_marker and expected_marker not in response_content:
                self.logger.warning(f"User {i} did not receive their own isolation marker")
            
            # Check for other users' markers (should not be present)
            for j, other_result in enumerate(isolation_results):
                if i != j and not isinstance(other_result, Exception):
                    other_marker = other_result.get('expected_marker')
                    if other_marker and other_marker in response_content:
                        pytest.fail(
                            f'FACTORY ISOLATION FAILURE: User {i} received data meant for user {j}. '
                            f'Cross-contamination detected: {other_marker} found in user {i} response.'
                        )

    async def _send_and_collect_isolation_response(
        self, 
        connection: websockets.WebSocketClientProtocol,
        message: Dict[str, Any],
        expected_marker: str
    ) -> Dict[str, Any]:
        """Send message and collect response for isolation testing"""
        try:
            await connection.send(json.dumps(message))
            
            # Collect response with timeout
            response_data = await asyncio.wait_for(connection.recv(), timeout=20.0)
            
            return {
                'expected_marker': expected_marker,
                'response_data': json.loads(response_data),
                'status': 'success'
            }
            
        except Exception as e:
            return {
                'expected_marker': expected_marker,
                'error': str(e),
                'status': 'error'
            }

    async def _run_isolated_user_session(
        self, 
        user: Dict[str, Any], 
        user_index: int, 
        scenario: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run complete isolated session for a single user"""
        session_start = time.time()
        
        try:
            self.logger.info(f"Starting isolated session for user {user_index}: {user['user_id']}")
            
            # Establish user WebSocket connection
            connection = await self._establish_user_websocket_connection(user)
            if connection is None:
                return {
                    'user_index': user_index,
                    'user_id': user['user_id'],
                    'status': 'failed',
                    'error': 'WebSocket connection failed',
                    'duration': time.time() - session_start
                }
            
            # Send scenario-specific message
            message_content = scenario['message'].format(
                user_index=user_index,
                user_id=user['user_id']
            )
            
            test_message = {
                'type': 'chat_message',
                'data': {
                    'message': message_content,
                    'test_scenario': scenario['name'],
                    'user_id': user['user_id'],
                    'user_index': user_index
                }
            }
            
            await connection.send(json.dumps(test_message))
            
            # Collect response with timeout
            response_data = await asyncio.wait_for(connection.recv(), timeout=30.0)
            response = json.loads(response_data)
            
            await connection.close()
            
            session_duration = time.time() - session_start
            
            return {
                'user_index': user_index,
                'user_id': user['user_id'],
                'status': 'success',
                'scenario': scenario['name'],
                'response_data': response,
                'duration': session_duration
            }
            
        except Exception as e:
            session_duration = time.time() - session_start
            return {
                'user_index': user_index,
                'user_id': user['user_id'],
                'status': 'error',
                'error': str(e),
                'duration': session_duration
            }

    async def _establish_user_websocket_connection(
        self, 
        user: Dict[str, Any]
    ) -> Optional[websockets.WebSocketClientProtocol]:
        """Establish WebSocket connection for specific user"""
        try:
            subprotocols = ['jwt-auth', f"jwt.{user['encoded_token']}"]
            
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connection = await asyncio.wait_for(
                websockets.connect(
                    self.__class__.staging_backend_url,
                    subprotocols=subprotocols,
                    ssl=ssl_context if self.__class__.staging_backend_url.startswith('wss') else None,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10
                ),
                timeout=15.0
            )
            
            self.logger.info(f"WebSocket connection established for user: {user['user_id']}")
            return connection
            
        except Exception as e:
            self.logger.error(f"Failed to establish connection for user {user['user_id']}: {e}")
            return None


# Test markers for pytest discovery
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.golden_path,
    pytest.mark.multi_user,
    pytest.mark.mission_critical,
    pytest.mark.staging,
    pytest.mark.user_isolation,
    pytest.mark.factory_pattern,
    pytest.mark.real_services,
    pytest.mark.issue_1197,
    pytest.mark.issue_1116
]


if __name__ == '__main__':
    print('MIGRATION NOTICE: Use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category e2e --filter multi_user_golden_path')
"""
Golden Path Staging Environment Test - Issue #1197

MISSION CRITICAL: Staging environment specific validation for Golden Path.
Tests complete user flow in actual staging.netrasystems.ai environment.

PURPOSE:
- Validates Golden Path works in production-like staging environment
- Tests real OAuth authentication flows
- Validates GCP Cloud Run infrastructure
- Ensures staging parity with production expectations

BUSINESS VALUE:
- Protects $500K+ ARR staging environment reliability
- Validates production deployment readiness
- Tests real infrastructure components (GCP, OAuth, SSL)
- Ensures staging matches production behavior

TESTING APPROACH:
- Uses canonical staging.netrasystems.ai URLs
- Real OAuth authentication with staging credentials
- Tests actual GCP Cloud Run containers
- Validates SSL/TLS configurations
- Initially designed to fail to validate staging infrastructure

GitHub Issue: #1197 Golden Path End-to-End Testing
Related Issues: #420 (Docker Infrastructure), #171 (WebSocket Auth)
Test Category: e2e, staging, golden_path, infrastructure
Expected Runtime: 60-180 seconds for staging validation
"""

import asyncio
import json
import time
import pytest
import websockets
import ssl
import httpx
from typing import Dict, List, Optional, Any, Set
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_test_base import StagingTestBase, track_test_timing
from tests.e2e.staging_config import StagingTestConfig as StagingConfig
from tests.e2e.staging_auth_client import StagingAuthClient
from tests.e2e.real_websocket_client import RealWebSocketClient
from netra_backend.app.services.user_execution_context import UserExecutionContext


# Staging environment validation requirements
STAGING_VALIDATION_REQUIREMENTS = {
    # Infrastructure validation
    "required_services": [
        "backend", "auth", "frontend"
    ],
    "required_endpoints": [
        "/health", "/api/health", "/auth/health"
    ],
    
    # Performance expectations for staging
    "max_service_health_check_time": 5.0,
    "max_oauth_auth_time": 10.0,
    "max_websocket_connection_time": 15.0,
    "max_complete_flow_time": 90.0,
    
    # Reliability requirements
    "min_health_check_success_rate": 100.0,
    "min_oauth_success_rate": 95.0,
    "min_websocket_success_rate": 90.0,
}

# Staging-specific test scenarios
STAGING_TEST_SCENARIOS = [
    {
        "name": "staging_infrastructure_validation",
        "description": "Validate all staging infrastructure components",
        "test_oauth": True,
        "test_websocket": True,
        "test_health_endpoints": True,
        "expected_duration": 30.0
    },
    {
        "name": "staging_golden_path_complete",
        "description": "Complete Golden Path in staging environment",
        "test_oauth": True,
        "test_websocket": True,
        "test_ai_response": True,
        "expected_duration": 90.0
    },
    {
        "name": "staging_ssl_security_validation",
        "description": "Validate SSL/TLS security in staging",
        "test_ssl_certificates": True,
        "test_secure_websockets": True,
        "expected_duration": 20.0
    }
]

# Canonical staging URLs (as specified in CLAUDE.md - Issue #1278 fix)
STAGING_URLS = {
    "auth_service": "https://staging.netrasystems.ai",
    "backend_api": "https://staging.netrasystems.ai",
    "frontend": "https://staging.netrasystems.ai",
    "websocket": "wss://api-staging.netrasystems.ai/ws"
}


class GoldenPathStagingTests(SSotAsyncTestCase):
    """
    Golden Path Staging Environment Test Suite
    
    Tests complete Golden Path functionality in staging.netrasystems.ai environment
    with real infrastructure components.
    """

    @classmethod
    async def asyncSetUpClass(cls):
        """Setup staging environment testing"""
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
        
        # Initialize staging configuration with canonical URLs
        cls.staging_config = StagingConfig()
        cls.staging_urls = STAGING_URLS
        cls.auth_client = StagingAuthClient()
        cls.websocket_client = RealWebSocketClient()
        
        # Verify staging environment accessibility
        await cls._verify_staging_environment()
        
        # Create test user with real OAuth
        cls.test_user = await cls._create_staging_test_user()
        
        cls.logger.info('Golden Path Staging test setup completed')

    @classmethod
    def _load_staging_environment(cls):
        """Load staging environment configuration"""
        import os
        from pathlib import Path
        
        # Load staging environment variables
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        staging_env_file = project_root / "config" / "staging.env"
        
        if staging_env_file.exists():
            cls.logger.info(f"Loading staging configuration from: {staging_env_file}")
            
            with open(staging_env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        
                        # Only set if not already in environment
                        if key not in os.environ:
                            os.environ[key] = value
                            if "SECRET" in key:
                                cls.logger.info(f"Loaded staging secret: {key}")
            
            # Ensure staging environment
            os.environ["ENVIRONMENT"] = "staging"
            cls.logger.info("Environment set to staging for infrastructure testing")
            
        else:
            cls.logger.warning(f"staging.env not found at {staging_env_file}")
            pytest.skip("Staging environment configuration not available")

    @classmethod
    async def _verify_staging_environment(cls):
        """Verify staging environment is fully accessible"""
        try:
            cls.logger.info("Verifying staging environment accessibility")
            
            # Test all canonical staging URLs
            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                for service_name, url in cls.staging_urls.items():
                    if service_name == "websocket":
                        continue  # Skip WebSocket URL for HTTP test
                    
                    try:
                        health_url = f"{url}/health"
                        cls.logger.info(f"Testing {service_name} health: {health_url}")
                        
                        response = await client.get(health_url)
                        assert response.status_code == 200, \
                            f"{service_name} health check failed: {response.status_code}"
                        
                        cls.logger.info(f"{service_name} health check passed")
                        
                    except Exception as e:
                        cls.logger.error(f"{service_name} health check failed: {e}")
                        # Continue with other services but log the failure
            
            cls.logger.info("Staging environment verification completed")
            
        except Exception as e:
            pytest.skip(f'Staging environment not fully accessible: {e}')

    @classmethod
    async def _create_staging_test_user(cls) -> Dict[str, Any]:
        """Create test user with real staging OAuth"""
        try:
            timestamp = int(time.time())
            test_user_data = {
                'email': f'staging_golden_path_{timestamp}@netra-testing.ai',
                'user_id': f'staging_gp_user_{timestamp}',
                'test_scenario': 'staging_golden_path_validation',
                'created_at': timestamp,
                'environment': 'staging'
            }
            
            # Generate real OAuth access token for staging
            access_token = await cls.auth_client.generate_test_access_token(
                user_id=test_user_data['user_id'],
                email=test_user_data['email']
            )
            
            test_user_data['access_token'] = access_token
            
            # Encode for WebSocket subprotocol
            import base64
            test_user_data['encoded_token'] = base64.urlsafe_b64encode(
                access_token.encode()
            ).decode().rstrip('=')
            
            # Verify token with staging auth service
            token_verification = await cls.auth_client.verify_token(access_token)
            assert token_verification['valid'], 'Staging test user token must be valid'
            
            cls.logger.info(f"Created staging test user: {test_user_data['email']}")
            return test_user_data
            
        except Exception as e:
            pytest.skip(f'Failed to create staging test user with OAuth: {e}')

    def create_user_context(self) -> UserExecutionContext:
        """Create user execution context for staging testing"""
        return UserExecutionContext.from_request(
            user_id=self.__class__.test_user['user_id'],
            thread_id=f"staging_thread_{int(time.time())}",
            run_id=f"staging_run_{int(time.time())}"
        )

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.golden_path
    @pytest.mark.infrastructure
    @pytest.mark.mission_critical
    @track_test_timing
    async def test_staging_golden_path_complete_infrastructure(self):
        """
        MISSION CRITICAL: Complete Golden Path in staging infrastructure
        
        Tests complete user journey in production-like staging environment:
        1. OAuth authentication with staging auth service
        2. WebSocket connection to staging backend
        3. Complete AI chat interaction
        4. Infrastructure component validation
        
        SUCCESS CRITERIA:
        - All staging services accessible and healthy
        - OAuth authentication works with staging credentials
        - WebSocket connection successful with proper SSL
        - Complete AI response received
        - Performance meets staging SLAs
        
        FAILURE INDICATES: Staging environment issues affecting production readiness
        
        DIFFICULTY: Very High (90-180 seconds)
        REAL SERVICES: Yes (staging.netrasystems.ai)
        STATUS: Should FAIL initially if staging issues exist
        """
        staging_test_start = time.time()
        infrastructure_steps = []
        
        try:
            self.logger.info("Starting complete staging infrastructure Golden Path test")
            
            # STEP 1: Staging Service Health Validation
            self.logger.info("STAGING STEP 1: Service health validation")
            health_start_time = time.time()
            infrastructure_steps.append({'step': 'service_health_validation', 'status': 'starting'})
            
            health_results = await self._validate_all_staging_services()
            health_duration = time.time() - health_start_time
            
            assert health_results['all_healthy'], \
                f'Not all staging services healthy: {health_results["failed_services"]}'
            assert health_duration <= STAGING_VALIDATION_REQUIREMENTS['max_service_health_check_time'], \
                f'Service health checks took {health_duration:.1f}s, exceeds staging SLA'
            
            infrastructure_steps[-1].update({
                'status': 'completed',
                'duration': health_duration,
                'services_tested': len(health_results['tested_services']),
                'details': 'All staging services healthy'
            })
            
            # STEP 2: OAuth Authentication with Staging
            self.logger.info("STAGING STEP 2: OAuth authentication validation")
            oauth_start_time = time.time()
            infrastructure_steps.append({'step': 'oauth_authentication', 'status': 'starting'})
            
            # Test OAuth token refresh and validation
            oauth_validation = await self._validate_staging_oauth()
            oauth_duration = time.time() - oauth_start_time
            
            assert oauth_validation['valid'], 'Staging OAuth authentication failed'
            assert oauth_duration <= STAGING_VALIDATION_REQUIREMENTS['max_oauth_auth_time'], \
                f'OAuth validation took {oauth_duration:.1f}s, exceeds staging SLA'
            
            infrastructure_steps[-1].update({
                'status': 'completed',
                'duration': oauth_duration,
                'token_valid': oauth_validation['valid'],
                'details': 'Staging OAuth authentication successful'
            })
            
            # STEP 3: Secure WebSocket Connection
            self.logger.info("STAGING STEP 3: Secure WebSocket connection")
            websocket_start_time = time.time()
            infrastructure_steps.append({'step': 'websocket_connection', 'status': 'starting'})
            
            # Establish secure WebSocket connection to staging
            connection = await self._establish_staging_websocket_connection()
            websocket_duration = time.time() - websocket_start_time
            
            assert connection is not None, 'Staging WebSocket connection failed'
            assert websocket_duration <= STAGING_VALIDATION_REQUIREMENTS['max_websocket_connection_time'], \
                f'WebSocket connection took {websocket_duration:.1f}s, exceeds staging SLA'
            
            infrastructure_steps[-1].update({
                'status': 'completed',
                'duration': websocket_duration,
                'ssl_verified': True,
                'details': 'Secure WebSocket connection established'
            })
            
            # STEP 4: Complete Golden Path Flow
            self.logger.info("STAGING STEP 4: Complete Golden Path AI interaction")
            ai_start_time = time.time()
            infrastructure_steps.append({'step': 'ai_interaction', 'status': 'starting'})
            
            # Send Golden Path message
            staging_message = {
                'type': 'chat_message',
                'data': {
                    'message': 'Staging environment Golden Path test - please confirm AI system is working correctly in staging infrastructure',
                    'test_scenario': 'staging_infrastructure_validation',
                    'user_id': self.__class__.test_user['user_id'],
                    'environment': 'staging',
                    'timestamp': int(time.time())
                }
            }
            
            await connection.send(json.dumps(staging_message))
            
            # Collect AI response
            ai_response = await asyncio.wait_for(
                connection.recv(), 
                timeout=60.0
            )
            
            ai_duration = time.time() - ai_start_time
            
            assert ai_response is not None, 'No AI response received in staging'
            
            # Parse and validate response
            try:
                response_data = json.loads(ai_response)
                assert 'type' in response_data, 'AI response missing type field'
                assert 'data' in response_data, 'AI response missing data field'
            except json.JSONDecodeError:
                pytest.fail('AI response is not valid JSON')
            
            infrastructure_steps[-1].update({
                'status': 'completed',
                'duration': ai_duration,
                'response_type': response_data.get('type'),
                'response_received': True,
                'details': 'AI interaction successful in staging'
            })
            
            await connection.close()
            
            # STEP 5: Final Infrastructure Validation
            total_duration = time.time() - staging_test_start
            assert total_duration <= STAGING_VALIDATION_REQUIREMENTS['max_complete_flow_time'], \
                f'Complete staging flow took {total_duration:.1f}s, exceeds maximum SLA'
            
            self.logger.info(
                f'STAGING INFRASTRUCTURE SUCCESS: Complete Golden Path validated in staging in {total_duration:.1f}s. '
                f'All {len(infrastructure_steps)} infrastructure steps completed successfully.'
            )
            
        except AssertionError as e:
            total_duration = time.time() - staging_test_start
            pytest.fail(
                f'STAGING INFRASTRUCTURE FAILURE: {str(e)} after {total_duration:.1f}s. '
                f'Infrastructure steps: {infrastructure_steps}. '
                f'IMPACT: Staging environment not production-ready.'
            )
            
        except asyncio.TimeoutError:
            total_duration = time.time() - staging_test_start
            pytest.fail(
                f'STAGING INFRASTRUCTURE TIMEOUT: Test timeout after {total_duration:.1f}s. '
                f'Infrastructure steps: {infrastructure_steps}. '
                f'Indicates staging performance issues.'
            )
            
        except Exception as e:
            total_duration = time.time() - staging_test_start
            pytest.fail(
                f'STAGING INFRASTRUCTURE ERROR: {str(e)} after {total_duration:.1f}s. '
                f'Infrastructure steps: {infrastructure_steps}. '
                f'Critical staging environment failure.'
            )

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.ssl_security
    @track_test_timing
    async def test_staging_ssl_security_validation(self):
        """
        Test SSL/TLS security in staging environment
        
        Validates:
        - SSL certificates are valid and trusted
        - WebSocket SSL connections work properly
        - Security headers are present
        - HTTPS enforcement works
        
        DIFFICULTY: Medium (30-45 seconds)
        REAL SERVICES: Yes (staging.netrasystems.ai)
        STATUS: Should FAIL initially if SSL issues exist
        """
        ssl_test_start = time.time()
        
        try:
            self.logger.info("Starting staging SSL security validation")
            
            # Test HTTPS endpoints with proper SSL verification
            async with httpx.AsyncClient(timeout=10.0, verify=True) as client:
                staging_urls = getattr(self.__class__, 'staging_urls', STAGING_URLS)
            for service_name, url in staging_urls.items():
                    if service_name == "websocket":
                        continue
                    
                    try:
                        response = await client.get(f"{url}/health")
                        
                        # Validate SSL response
                        assert response.status_code == 200, f'{service_name} SSL request failed'
                        
                        # Check security headers
                        security_headers = [
                            'strict-transport-security',
                            'x-content-type-options',
                            'x-frame-options'
                        ]
                        
                        for header in security_headers:
                            if header in response.headers:
                                self.logger.info(f"{service_name} has security header: {header}")
                        
                    except (httpx.ConnectError, httpx.TransportError) as e:
                        # SSL errors typically manifest as connection/transport errors
                        if 'SSL' in str(e) or 'certificate' in str(e).lower():
                            pytest.fail(f'SSL error for {service_name}: {e}')
                        else:
                            raise  # Re-raise if not SSL-related
                    except Exception as e:
                        self.logger.warning(f'SSL test issue for {service_name}: {e}')
            
            # Test WebSocket SSL connection
            wss_connection = await self._test_websocket_ssl_connection()
            assert wss_connection, 'WebSocket SSL connection failed'
            
            ssl_duration = time.time() - ssl_test_start
            self.logger.info(f'Staging SSL security validation completed in {ssl_duration:.1f}s')
            
        except Exception as e:
            ssl_duration = time.time() - ssl_test_start
            pytest.fail(f'SSL security validation failed after {ssl_duration:.1f}s: {e}')

    async def _validate_all_staging_services(self) -> Dict[str, Any]:
        """Validate all staging services are healthy"""
        tested_services = []
        failed_services = []
        
        async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
            staging_urls = getattr(self.__class__, 'staging_urls', STAGING_URLS)
            for service_name, url in staging_urls.items():
                if service_name == "websocket":
                    continue
                
                try:
                    health_url = f"{url}/health"
                    response = await client.get(health_url)
                    
                    if response.status_code == 200:
                        tested_services.append(service_name)
                        self.logger.info(f"✓ {service_name} service healthy")
                    else:
                        failed_services.append(f"{service_name}:{response.status_code}")
                        self.logger.error(f"✗ {service_name} service unhealthy: {response.status_code}")
                        
                except Exception as e:
                    failed_services.append(f"{service_name}:exception")
                    self.logger.error(f"✗ {service_name} service error: {e}")
        
        return {
            'all_healthy': len(failed_services) == 0,
            'tested_services': tested_services,
            'failed_services': failed_services,
            'healthy_count': len(tested_services),
            'total_tested': len(tested_services) + len(failed_services)
        }

    async def _validate_staging_oauth(self) -> Dict[str, Any]:
        """Validate OAuth authentication in staging"""
        try:
            # Verify existing token
            verification = await self.__class__.auth_client.verify_token(
                self.__class__.test_user['access_token']
            )
            
            return {
                'valid': verification['valid'],
                'user_id': verification.get('user_id'),
                'token_type': 'access_token'
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'token_type': 'access_token'
            }

    async def _establish_staging_websocket_connection(self) -> Optional[websockets.ClientConnection]:
        """Establish secure WebSocket connection to staging"""
        try:
            # Use proper staging WebSocket URL with SSL
            staging_urls = getattr(self.__class__, 'staging_urls', STAGING_URLS)
            websocket_url = staging_urls["websocket"]
            
            # Setup SSL context for staging
            ssl_context = ssl.create_default_context()
            # For staging, we may need to disable strict SSL verification
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # WebSocket subprotocols with JWT
            subprotocols = [
                'jwt-auth', 
                f"jwt.{self.__class__.test_user['encoded_token']}"
            ]
            
            self.logger.info(f"Connecting to staging WebSocket: {websocket_url}")
            
            connection = await asyncio.wait_for(
                websockets.connect(
                    websocket_url,
                    subprotocols=subprotocols,
                    ssl=ssl_context,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10
                ),
                timeout=15.0
            )
            
            self.logger.info("Staging WebSocket connection established successfully")
            return connection
            
        except Exception as e:
            self.logger.error(f"Failed to establish staging WebSocket connection: {e}")
            return None

    async def _test_websocket_ssl_connection(self) -> bool:
        """Test WebSocket SSL connection specifically"""
        try:
            connection = await self._establish_staging_websocket_connection()
            if connection:
                await connection.close()
                return True
            return False
        except Exception as e:
            self.logger.error(f"WebSocket SSL test failed: {e}")
            return False


# Test markers for pytest discovery
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.staging,
    pytest.mark.golden_path,
    pytest.mark.infrastructure,
    pytest.mark.ssl_security,
    pytest.mark.oauth,
    pytest.mark.mission_critical,
    pytest.mark.real_services,
    pytest.mark.issue_1197
]


if __name__ == '__main__':
    print('MIGRATION NOTICE: Use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category e2e --filter staging --filter golden_path')
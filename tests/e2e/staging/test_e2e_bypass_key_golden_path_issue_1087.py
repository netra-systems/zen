"""
E2E Staging Tests for Issue #1087: E2E OAuth Bypass Key Golden Path Validation

Tests complete Golden Path authentication flow in real staging GCP environment.
Validates end-to-end user authentication flow with E2E bypass key configuration.

Business Value: Restores $500K+ ARR Golden Path authentication functionality.
"""

import pytest
import asyncio
import aiohttp
import websockets
import json
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env


class E2EBypassKeyGoldenPathIssue1087Tests(SSotAsyncTestCase):
    """E2E tests for Golden Path authentication with bypass key in staging."""

    def setup_method(self, method):
        """Set up E2E staging test environment."""
        super().setup_method(method)
        self.env = get_env()

        # Staging URLs - must use canonical staging URLs per CLAUDE.md
        self.staging_auth_url = "https://auth.staging.netrasystems.ai"
        self.staging_backend_url = "https://api.staging.netrasystems.ai"
        self.staging_websocket_url = "wss://api.staging.netrasystems.ai/ws"

        self.test_user_email = f"e2e_golden_path_issue_1087_{self.generate_test_id()}@example.com"
        self.timeout = 30.0  # 30 second timeout for staging operations

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.critical
    async def test_golden_path_authentication_with_bypass_key(self):
        """Test complete Golden Path authentication flow with E2E bypass key.

        CRITICAL BUSINESS VALUE: Validates $500K+ ARR Golden Path restoration.
        Tests complete auth flow: bypass key → JWT token → WebSocket connection.

        Expected: FAIL initially → PASS after configuration fix
        """
        print("\n🚀 GOLDEN PATH E2E TEST: Complete authentication flow")
        print(f"Test User: {self.test_user_email}")
        print(f"Staging Auth URL: {self.staging_auth_url}")

        try:
            # Step 1: Attempt E2E bypass key authentication
            bypass_key = self.env.get("E2E_OAUTH_SIMULATION_KEY")
            if not bypass_key:
                print("⚠️  WARNING: E2E_OAUTH_SIMULATION_KEY not found in environment")
                print("   Attempting to test against staging configuration...")

            # Prepare E2E authentication request
            e2e_headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'E2E-Golden-Path-Test/Issue-1087'
            }

            # Add bypass key if available
            if bypass_key:
                e2e_headers['X-E2E-Bypass-Key'] = bypass_key
                print(f"   Using bypass key: {bypass_key[:10]}...")

            e2e_auth_data = {
                'email': self.test_user_email,
                'name': 'Golden Path Issue 1087 Test',
                'e2e_test_mode': True
            }

            # Step 2: Attempt authentication with staging auth service
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                try:
                    auth_url = f"{self.staging_auth_url}/auth/e2e-test-auth"
                    print(f"   Testing authentication: {auth_url}")

                    async with session.post(
                        auth_url,
                        headers=e2e_headers,
                        json=e2e_auth_data
                    ) as response:

                        response_text = await response.text()
                        print(f"   Auth Response Status: {response.status}")
                        print(f"   Auth Response: {response_text[:200]}...")

                        if response.status == 401:
                            # This reproduces Issue #1087
                            if "E2E bypass key required" in response_text:
                                print("🔄 ISSUE #1087 REPRODUCED: E2E bypass key required")
                                print("   Authentication failed with missing bypass key")

                                pytest.fail(
                                    f"ISSUE #1087 GOLDEN PATH BLOCKED: "
                                    f"E2E bypass key authentication failed in staging. "
                                    f"Status: {response.status}, Response: {response_text}. "
                                    f"This completely blocks $500K+ ARR Golden Path functionality. "
                                    f"Configuration fix required for E2E_OAUTH_SIMULATION_KEY."
                                )

                            elif "Invalid E2E bypass key" in response_text:
                                print("🔄 ISSUE #1087 VARIATION: Invalid bypass key configuration")

                                pytest.fail(
                                    f"ISSUE #1087 INVALID BYPASS KEY: "
                                    f"E2E bypass key configured but invalid in staging. "
                                    f"Status: {response.status}, Response: {response_text}. "
                                    f"Bypass key configuration needs validation."
                                )

                        elif response.status == 200:
                            # Authentication successful - configuration has been fixed
                            auth_result = json.loads(response_text)
                            access_token = auth_result.get('access_token')

                            assert access_token, f"No access token in response: {auth_result}"

                            print(f"✅ GOLDEN PATH RESTORED: E2E authentication successful")
                            print(f"   Access Token: {access_token[:20]}...")

                            # Step 3: Test authenticated WebSocket connection
                            await self._test_authenticated_websocket_connection(access_token)

                        else:
                            pytest.fail(
                                f"Unexpected authentication response: {response.status} - {response_text}"
                            )

                except asyncio.TimeoutError:
                    pytest.fail(f"Authentication request timed out after {self.timeout}s")
                except aiohttp.ClientConnectorError as e:
                    pytest.fail(f"Cannot connect to staging auth service: {e}")

        except Exception as e:
            pytest.fail(f"Golden Path E2E test failed with exception: {e}")

    async def _test_authenticated_websocket_connection(self, access_token: str):
        """Test WebSocket connection with authenticated token."""
        print("   🔗 Testing authenticated WebSocket connection...")

        try:
            websocket_headers = {
                'Authorization': f'Bearer {access_token}',
                'User-Agent': 'E2E-Golden-Path-Test/Issue-1087'
            }

            async with websockets.connect(
                self.staging_websocket_url,
                extra_headers=websocket_headers,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            ) as websocket:

                print("   ✅ WebSocket connection established successfully")

                # Test basic WebSocket functionality
                test_message = {
                    'type': 'test_connection',
                    'message': 'Golden Path Issue 1087 test',
                    'timestamp': self.get_current_timestamp()
                }

                await websocket.send(json.dumps(test_message))
                print("   📤 Test message sent to WebSocket")

                # Wait for response with timeout
                try:
                    response = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=10.0
                    )
                    print(f"   📥 WebSocket response received: {response[:100]}...")
                    print("   ✅ GOLDEN PATH WEBSOCKET: Authenticated connection working")

                except asyncio.TimeoutError:
                    print("   ⚠️  WebSocket response timeout (may be normal for test message)")
                    print("   ✅ GOLDEN PATH WEBSOCKET: Connection established successfully")

        except websockets.ConnectionClosed as e:
            pytest.fail(f"WebSocket connection closed unexpectedly: {e}")
        except Exception as e:
            pytest.fail(f"WebSocket connection failed: {e}")

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.critical
    async def test_staging_websocket_authenticated_connection_e2e(self):
        """Test WebSocket connection with bypass key authentication in staging.

        Tests that WebSocket connections can be established after successful
        E2E bypass key authentication.

        Expected: FAIL initially → PASS after configuration fix
        """
        print("\n🔗 WEBSOCKET E2E TEST: Authenticated connection")

        # This test depends on bypass key authentication working
        # If Issue #1087 is not fixed, this will fail at authentication step
        await self.test_golden_path_authentication_with_bypass_key()

    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_staging_agent_execution_with_authentication_e2e(self):
        """Test complete agent execution pipeline with proper authentication.

        Validates that agents can execute and return substantive responses
        after successful E2E bypass key authentication.

        Expected: FAIL initially → PASS after configuration fix
        """
        print("\n🤖 AGENT EXECUTION E2E TEST: Authenticated agent pipeline")
        print("   Testing complete agent workflow with E2E authentication")

        try:
            # First ensure authentication works
            bypass_key = self.env.get("E2E_OAUTH_SIMULATION_KEY")

            if not bypass_key:
                pytest.fail(
                    "AGENT EXECUTION BLOCKED: E2E bypass key not configured. "
                    "Cannot test agent execution without authentication. "
                    "Issue #1087 must be resolved first."
                )

            # Authenticate and get access token
            access_token = await self._authenticate_with_bypass_key(bypass_key)

            # Test agent execution with authenticated token
            agent_request = {
                'message': 'Test agent execution for Issue 1087',
                'user_id': f'e2e_test_{self.generate_test_id()}',
                'thread_id': f'thread_{self.generate_test_id()}',
                'agent_type': 'supervisor'
            }

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
                agent_url = f"{self.staging_backend_url}/api/v1/agent/execute"
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }

                async with session.post(
                    agent_url,
                    headers=headers,
                    json=agent_request
                ) as response:

                    if response.status == 200:
                        result = await response.json()
                        print(f"   ✅ AGENT EXECUTION SUCCESSFUL: {result.get('status', 'Unknown')}")
                        print("   🚀 GOLDEN PATH AGENT PIPELINE: Working end-to-end")

                        # Validate substantive response (not just technical success)
                        agent_response = result.get('response', '')
                        assert len(agent_response) > 0, "Agent should return substantive response"

                    else:
                        response_text = await response.text()
                        pytest.fail(f"Agent execution failed: {response.status} - {response_text}")

        except Exception as e:
            pytest.fail(f"Agent execution E2E test failed: {e}")

    async def _authenticate_with_bypass_key(self, bypass_key: str) -> str:
        """Helper method to authenticate with bypass key and return access token."""
        e2e_headers = {
            'Content-Type': 'application/json',
            'X-E2E-Bypass-Key': bypass_key,
            'User-Agent': 'E2E-Agent-Test/Issue-1087'
        }

        e2e_auth_data = {
            'email': self.test_user_email,
            'name': 'Agent Execution Test Issue 1087',
            'e2e_test_mode': True
        }

        async with aiohttp.ClientSession() as session:
            auth_url = f"{self.staging_auth_url}/auth/e2e-test-auth"

            async with session.post(
                auth_url,
                headers=e2e_headers,
                json=e2e_auth_data
            ) as response:

                if response.status != 200:
                    response_text = await response.text()
                    raise Exception(f"Authentication failed: {response.status} - {response_text}")

                auth_result = await response.json()
                access_token = auth_result.get('access_token')

                if not access_token:
                    raise Exception(f"No access token in auth response: {auth_result}")

                return access_token

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.infrastructure
    async def test_staging_environment_bypass_key_configuration_validation(self):
        """Test staging environment bypass key configuration infrastructure.

        INFRASTRUCTURE VALIDATION: Verifies bypass key is properly configured
        in staging environment through both environment variable and Secret Manager.

        Expected: FAIL initially → PASS after configuration fix
        """
        print("\n⚙️  INFRASTRUCTURE TEST: Staging bypass key configuration")

        try:
            from auth_service.auth_core.secret_loader import AuthSecretLoader

            # Test 1: Environment variable configuration
            env_bypass_key = self.env.get("E2E_OAUTH_SIMULATION_KEY")
            print(f"   Environment Variable (E2E_OAUTH_SIMULATION_KEY): {'✅ SET' if env_bypass_key else '❌ NOT SET'}")

            if env_bypass_key:
                print(f"   Key length: {len(env_bypass_key)} characters")

            # Test 2: AuthSecretLoader configuration method
            try:
                configured_key = AuthSecretLoader.get_E2E_OAUTH_SIMULATION_KEY()
                print(f"   AuthSecretLoader result: {'✅ CONFIGURED' if configured_key else '❌ NOT CONFIGURED'}")

                if configured_key:
                    print(f"   Configured key length: {len(configured_key)} characters")
                    assert len(configured_key) > 10, "Bypass key should be sufficiently long for security"

            except Exception as e:
                print(f"   ❌ AuthSecretLoader error: {e}")
                configured_key = None

            # Test 3: Overall configuration status
            if not configured_key:
                print("🔄 ISSUE #1087 CONFIGURATION PROBLEM CONFIRMED:")
                print("   - E2E bypass key not available through any configuration method")
                print("   - This blocks all E2E testing in staging environment")
                print("   - Authentication endpoint returns 401: 'E2E bypass key required'")

                pytest.fail(
                    "STAGING INFRASTRUCTURE FAILURE: E2E bypass key not configured. "
                    "Neither environment variable nor Secret Manager provides valid bypass key. "
                    "This is the root cause of Issue #1087. "
                    "Required actions: "
                    "1. Set E2E_OAUTH_SIMULATION_KEY environment variable, OR "
                    "2. Configure 'e2e-bypass-key' in Google Secret Manager for staging"
                )

            else:
                print("✅ CONFIGURATION SUCCESS: E2E bypass key properly configured")
                print("   🚀 Infrastructure ready for Golden Path authentication")

                # Test configuration with actual auth endpoint
                await self._validate_bypass_key_with_auth_endpoint(configured_key)

        except ImportError as e:
            pytest.skip(f"Auth service components not available for infrastructure test: {e}")

    async def _validate_bypass_key_with_auth_endpoint(self, bypass_key: str):
        """Validate bypass key works with actual auth endpoint."""
        print("   🔍 Validating bypass key with auth endpoint...")

        test_headers = {
            'Content-Type': 'application/json',
            'X-E2E-Bypass-Key': bypass_key,
            'User-Agent': 'Infrastructure-Validation/Issue-1087'
        }

        test_data = {
            'email': f'infrastructure_test_{self.generate_test_id()}@example.com',
            'name': 'Infrastructure Validation Test',
            'e2e_test_mode': True
        }

        try:
            async with aiohttp.ClientSession() as session:
                auth_url = f"{self.staging_auth_url}/auth/e2e-test-auth"

                async with session.post(
                    auth_url,
                    headers=test_headers,
                    json=test_data
                ) as response:

                    if response.status == 200:
                        print("   ✅ Bypass key validation successful with auth endpoint")
                        result = await response.json()
                        assert result.get('access_token'), "Should receive access token"

                    else:
                        response_text = await response.text()
                        pytest.fail(
                            f"Bypass key validation failed with auth endpoint: "
                            f"{response.status} - {response_text}"
                        )

        except Exception as e:
            pytest.fail(f"Auth endpoint validation error: {e}")

    def generate_test_id(self) -> str:
        """Generate unique test identifier."""
        import time
        import random
        return f"{int(time.time())}_{random.randint(1000, 9999)}"

    def get_current_timestamp(self) -> str:
        """Get current timestamp for test messages."""
        import datetime
        return datetime.datetime.utcnow().isoformat() + "Z"
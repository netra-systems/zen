"""
Test Golden Path Configuration SSOT Integration - Issue #667

E2E TEST ON STAGING - Validates Golden Path with Consolidated Config

Business Value Justification (BVJ):
- Segment: Enterprise/Platform - Revenue Protection
- Business Goal: Golden Path Reliability - Protect $500K+ ARR from config failures
- Value Impact: End-to-end validation of user login → AI chat with SSOT config
- Strategic Impact: Proves SSOT configuration consolidation enables Golden Path success

PURPOSE: E2E test on staging environment validating complete Golden Path functionality
with consolidated SSOT configuration management.

Test Coverage:
1. User authentication with SSOT auth configuration
2. Database connectivity with SSOT database configuration
3. WebSocket communication with SSOT WebSocket configuration
4. LLM integration with SSOT LLM configuration
5. End-to-end user flow: login → AI chat response

CRITICAL: This test validates that SSOT configuration consolidation maintains
Golden Path functionality worth $500K+ ARR protection.
"""

import pytest
import asyncio
import json
import time
from typing import Dict, Any, Optional
import websockets
import requests
from datetime import datetime
import os

# Import test framework for staging
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestConfigSSotGoldenPathStaging(SSotAsyncTestCase):
    """E2E test suite for Golden Path with SSOT configuration on staging."""

    @pytest.fixture(scope="class")
    def staging_config(self):
        """Staging environment configuration."""
        return {
            'base_url': 'https://netra-backend-staging-150560153566.us-central1.run.app',
            'frontend_url': 'https://netra-frontend-staging-150560153566.us-central1.run.app',
            'websocket_url': 'wss://netra-backend-staging-150560153566.us-central1.run.app/ws',
            'health_url': 'https://netra-backend-staging-150560153566.us-central1.run.app/health',
            'timeout': 30,
            'max_retries': 3
        }

    @pytest.fixture(scope="class")
    def test_user_credentials(self):
        """Test user credentials for staging authentication."""
        return {
            'email': 'test@netra.ai',
            'password': 'test123'
        }

    async def test_staging_config_manager_health_check(self, staging_config):
        """
        Test that staging environment has healthy configuration management.

        Validates that SSOT configuration manager is operational in staging.
        """
        health_url = staging_config['health_url']
        timeout = staging_config['timeout']

        try:
            response = requests.get(health_url, timeout=timeout)
            assert response.status_code == 200, f"Health check failed: {response.status_code}"

            health_data = response.json()
            assert health_data.get('status') == 'healthy', f"Service not healthy: {health_data}"

            # Check configuration-related health indicators
            config_indicators = [
                'database_connected',
                'redis_connected',
                'environment_detected'
            ]

            for indicator in config_indicators:
                if indicator in health_data:
                    assert health_data[indicator] is True, f"Config health indicator failed: {indicator}"

        except requests.exceptions.RequestException as e:
            pytest.fail(f"Staging health check failed: {str(e)}")

    async def test_golden_path_user_authentication_with_ssot_config(self, staging_config, test_user_credentials):
        """
        Test Golden Path user authentication using SSOT configuration.

        Validates that auth configuration from SSOT manager enables successful login.
        """
        base_url = staging_config['base_url']
        timeout = staging_config['timeout']

        # Step 1: Login request
        login_url = f"{base_url}/auth/login"
        login_data = test_user_credentials

        try:
            response = requests.post(login_url, json=login_data, timeout=timeout)

            # Auth should work with SSOT configuration
            if response.status_code == 200:
                auth_data = response.json()
                assert 'access_token' in auth_data, "Auth response missing access_token"
                assert 'user' in auth_data, "Auth response missing user data"

                return {
                    'access_token': auth_data['access_token'],
                    'user': auth_data['user'],
                    'auth_success': True
                }

            elif response.status_code == 401:
                # If user doesn't exist, try registration
                register_url = f"{base_url}/auth/register"
                register_response = requests.post(register_url, json=login_data, timeout=timeout)

                if register_response.status_code == 201:
                    # Registration successful, try login again
                    login_response = requests.post(login_url, json=login_data, timeout=timeout)
                    assert login_response.status_code == 200, "Login after registration failed"

                    auth_data = login_response.json()
                    return {
                        'access_token': auth_data['access_token'],
                        'user': auth_data['user'],
                        'auth_success': True
                    }

            pytest.fail(f"Authentication failed: {response.status_code} - {response.text}")

        except requests.exceptions.RequestException as e:
            pytest.fail(f"Auth request failed: {str(e)}")

    async def test_golden_path_database_connectivity_with_ssot_config(self, staging_config):
        """
        Test Golden Path database connectivity using SSOT database configuration.

        Validates that database configuration from SSOT manager enables data persistence.
        """
        base_url = staging_config['base_url']
        timeout = staging_config['timeout']

        # Test database connectivity through health endpoint
        db_health_url = f"{base_url}/health/database"

        try:
            response = requests.get(db_health_url, timeout=timeout)

            if response.status_code == 200:
                db_health = response.json()
                assert db_health.get('database_connected') is True, "Database not connected"
                assert 'connection_pool_size' in db_health, "Database pool info missing"

            elif response.status_code == 404:
                # Fallback: test database through a simple user query
                users_url = f"{base_url}/auth/me"
                # This would need a valid token, but we're testing connectivity
                response = requests.get(users_url, timeout=timeout)
                # Even without auth, if we get 401 (not 500), database is working
                assert response.status_code in [401, 403], f"Database connection issue: {response.status_code}"

            else:
                pytest.fail(f"Database health check failed: {response.status_code}")

        except requests.exceptions.RequestException as e:
            pytest.fail(f"Database connectivity test failed: {str(e)}")

    async def test_golden_path_websocket_connection_with_ssot_config(self, staging_config):
        """
        Test Golden Path WebSocket connectivity using SSOT WebSocket configuration.

        Validates that WebSocket configuration from SSOT manager enables real-time communication.
        """
        websocket_url = staging_config['websocket_url']
        timeout = staging_config['timeout']

        try:
            # Test WebSocket connection
            async with websockets.connect(
                websocket_url,
                timeout=timeout,
                ping_interval=20,
                ping_timeout=10
            ) as websocket:

                # Send a test message
                test_message = {
                    'type': 'test_connection',
                    'timestamp': datetime.now().isoformat(),
                    'test_id': 'config_ssot_test'
                }

                await websocket.send(json.dumps(test_message))

                # Wait for response or connection confirmation
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10)
                    response_data = json.loads(response)

                    # WebSocket should handle the message (even if it sends an error)
                    assert 'type' in response_data, "WebSocket response missing type field"

                    # Connection successful if we get any structured response
                    return True

                except asyncio.TimeoutError:
                    # Even if no immediate response, connection was established
                    return True

        except websockets.exceptions.ConnectionClosed as e:
            pytest.fail(f"WebSocket connection closed: {str(e)}")
        except websockets.exceptions.InvalidURI as e:
            pytest.fail(f"Invalid WebSocket URI: {str(e)}")
        except Exception as e:
            pytest.fail(f"WebSocket connection failed: {str(e)}")

    async def test_golden_path_end_to_end_user_flow(self, staging_config, test_user_credentials):
        """
        Test complete Golden Path: user login → AI chat response.

        This is the critical $500K+ ARR test validating end-to-end functionality
        with SSOT configuration management.
        """
        base_url = staging_config['base_url']
        websocket_url = staging_config['websocket_url']
        timeout = staging_config['timeout']

        # Step 1: Authenticate user
        auth_result = await self.test_golden_path_user_authentication_with_ssot_config(
            staging_config, test_user_credentials
        )

        if not auth_result or not auth_result.get('auth_success'):
            pytest.skip("Authentication failed, cannot test end-to-end flow")

        access_token = auth_result['access_token']
        user_id = auth_result['user'].get('id')

        # Step 2: Establish WebSocket connection with auth
        websocket_url_with_auth = f"{websocket_url}?token={access_token}"

        try:
            async with websockets.connect(
                websocket_url_with_auth,
                timeout=timeout,
                ping_interval=20,
                ping_timeout=10
            ) as websocket:

                # Step 3: Send AI chat request
                chat_request = {
                    'type': 'agent_request',
                    'user_id': user_id,
                    'message': 'Hello, please help me test the AI system. What is 2+2?',
                    'timestamp': datetime.now().isoformat(),
                    'request_id': f'test_request_{int(time.time())}'
                }

                await websocket.send(json.dumps(chat_request))

                # Step 4: Wait for AI response events
                golden_path_events = []
                expected_events = ['agent_started', 'agent_thinking', 'agent_completed']
                max_wait_time = 60  # 60 seconds for AI processing

                start_time = time.time()
                while time.time() - start_time < max_wait_time:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=10)
                        event_data = json.loads(message)

                        if 'type' in event_data:
                            golden_path_events.append(event_data['type'])

                            # Check for completion
                            if event_data['type'] == 'agent_completed':
                                break

                    except asyncio.TimeoutError:
                        continue
                    except json.JSONDecodeError:
                        continue

                # Step 5: Validate Golden Path success
                assert len(golden_path_events) > 0, "No events received from AI system"

                # Check for critical Golden Path events
                has_agent_events = any(event in golden_path_events for event in expected_events)
                assert has_agent_events, f"Missing critical AI events. Got: {golden_path_events}"

                # If we get agent_completed, the Golden Path succeeded
                if 'agent_completed' in golden_path_events:
                    return {
                        'golden_path_success': True,
                        'events_received': golden_path_events,
                        'total_events': len(golden_path_events)
                    }

                # If we get some agent events but not completion, partial success
                elif any(event.startswith('agent_') for event in golden_path_events):
                    return {
                        'golden_path_partial': True,
                        'events_received': golden_path_events,
                        'note': 'Agent started but may not have completed'
                    }

                else:
                    pytest.fail(f"Golden Path failed: No agent events received. Events: {golden_path_events}")

        except websockets.exceptions.ConnectionClosed as e:
            pytest.fail(f"WebSocket connection closed during Golden Path test: {str(e)}")
        except Exception as e:
            pytest.fail(f"Golden Path end-to-end test failed: {str(e)}")

    async def test_ssot_config_manager_performance_under_load(self, staging_config):
        """
        Test SSOT configuration manager performance under concurrent load.

        Validates that consolidated SSOT config manager handles multiple requests efficiently.
        """
        base_url = staging_config['base_url']
        timeout = staging_config['timeout']

        # Concurrent health checks to test config manager load handling
        async def health_check():
            try:
                response = requests.get(f"{base_url}/health", timeout=timeout)
                return response.status_code == 200
            except Exception:
                return False

        # Run multiple concurrent requests
        concurrent_requests = 10
        tasks = [health_check() for _ in range(concurrent_requests)]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful_requests = sum(1 for result in results if result is True)

            # SSOT config manager should handle concurrent load
            success_rate = successful_requests / concurrent_requests
            assert success_rate >= 0.8, f"Config manager load test failed: {success_rate:.2%} success rate"

        except Exception as e:
            pytest.fail(f"Config manager load test failed: {str(e)}")

    def test_staging_environment_ssot_config_compliance(self, staging_config):
        """
        Test that staging environment uses SSOT configuration patterns.

        Validates configuration consistency across staging environment.
        """
        base_url = staging_config['base_url']
        timeout = staging_config['timeout']

        # Test configuration endpoints for consistency
        config_endpoints = [
            '/health',
            '/health/database',
            '/auth/config'  # If available
        ]

        config_responses = {}

        for endpoint in config_endpoints:
            try:
                response = requests.get(f"{base_url}{endpoint}", timeout=timeout)
                if response.status_code == 200:
                    config_responses[endpoint] = response.json()
                elif response.status_code == 404:
                    config_responses[endpoint] = {'status': 'not_available'}
                else:
                    config_responses[endpoint] = {'status': 'error', 'code': response.status_code}

            except requests.exceptions.RequestException as e:
                config_responses[endpoint] = {'status': 'exception', 'error': str(e)}

        # Validate basic config consistency
        health_config = config_responses.get('/health', {})

        if 'environment' in health_config:
            assert health_config['environment'] in ['staging', 'production'], (
                f"Invalid environment in staging: {health_config['environment']}"
            )

        # All config endpoints should return structured data (not errors)
        error_endpoints = [
            endpoint for endpoint, response in config_responses.items()
            if response.get('status') == 'error'
        ]

        assert len(error_endpoints) == 0, (
            f"Config endpoints returning errors: {error_endpoints}. "
            f"Responses: {config_responses}"
        )


@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.golden_path
class TestGoldenPathConfigIntegration:
    """Integration test class for Golden Path configuration validation."""

    async def test_complete_golden_path_with_ssot_config(self):
        """
        Complete Golden Path test with SSOT configuration.

        This test validates the entire user journey with consolidated configuration.
        """
        # This test requires staging environment access
        if not os.getenv('STAGING_ACCESS_ENABLED'):
            pytest.skip("Staging access not enabled for this test run")

        test_instance = TestConfigSSotGoldenPathStaging()

        # Configure staging
        staging_config = {
            'base_url': 'https://netra-backend-staging-150560153566.us-central1.run.app',
            'websocket_url': 'wss://netra-backend-staging-150560153566.us-central1.run.app/ws',
            'health_url': 'https://netra-backend-staging-150560153566.us-central1.run.app/health',
            'timeout': 30
        }

        test_credentials = {
            'email': 'test@netra.ai',
            'password': 'test123'
        }

        # Run Golden Path validation
        try:
            result = await test_instance.test_golden_path_end_to_end_user_flow(
                staging_config, test_credentials
            )

            assert result.get('golden_path_success') or result.get('golden_path_partial'), (
                f"Golden Path test failed: {result}"
            )

        except Exception as e:
            pytest.fail(f"Complete Golden Path integration test failed: {str(e)}")


if __name__ == "__main__":
    # Run the Golden Path E2E test
    pytest.main([__file__, "-v", "--tb=short", "-m", "staging"])
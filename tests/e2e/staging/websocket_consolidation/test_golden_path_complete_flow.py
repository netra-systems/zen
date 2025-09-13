"""
E2E Staging Test: Golden Path Complete Flow Validation

This test is designed to FAIL initially, proving that the complete Golden Path
user flow (users login → get AI responses) is broken due to SSOT violations.

Business Impact:
- Complete Golden Path user flow broken
- Users cannot login and get AI responses
- End-to-end chat functionality non-functional
- $500K+ ARR completely blocked by system failures

SSOT Violations Blocking Golden Path:
- WebSocket SSOT violations prevent real-time communication
- Factory pattern failures block user isolation
- Authentication integration failures prevent login
- Event delivery failures break chat experience

This test MUST FAIL until SSOT consolidation fixes the Golden Path.

STAGING ENVIRONMENT REQUIREMENTS:
- Requires access to GCP staging environment
- Real WebSocket connections to staging services
- Actual authentication flow validation
- Complete end-to-end user flow testing
"""
import asyncio
import pytest
import websockets
import json
import time
import jwt
from typing import Dict, List, Any, Optional
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from dev_launcher.isolated_environment import IsolatedEnvironment

try:
    # Staging environment imports
    import aiohttp
    import requests
except ImportError as e:
    print(f"WARNING: HTTP client libraries not available for E2E testing: {e}")
    aiohttp = None
    requests = None


class TestGoldenPathCompleteFlow(SSotAsyncTestCase):
    """
    CRITICAL E2E: This test proves Golden Path is completely broken.

    EXPECTED RESULT: FAIL - Complete user flow broken by SSOT violations
    BUSINESS IMPACT: $500K+ ARR blocked - users cannot use core platform functionality
    """

    def setup_method(self):
        """Set up test environment for Golden Path E2E testing."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.staging_config = self._get_staging_config()
        self.test_user_credentials = {
            'email': 'e2e.test@netra.com',
            'password': 'E2ETestPassword123!',
            'user_id': 'e2e_test_user_golden_path'
        }
        self.golden_path_success = False
        self.failure_points = []

    @pytest.mark.asyncio
    async def test_complete_golden_path_user_flow_failure(self):
        """
        CRITICAL BUSINESS TEST: Prove complete Golden Path user flow fails

        Expected Result: FAIL - Users cannot complete login → AI response flow
        Business Impact: $500K+ ARR - Core platform functionality completely broken
        """
        if not self._staging_available():
            pytest.skip("Staging environment not available for E2E testing")

        golden_path_steps = []

        try:
            # Step 1: User Login
            login_result = await self._test_user_login()
            golden_path_steps.append({
                'step': 'user_login',
                'success': login_result['success'],
                'details': login_result
            })

            if not login_result['success']:
                self.failure_points.append('LOGIN_FAILURE')

            # Step 2: WebSocket Connection
            websocket_result = await self._test_websocket_connection(login_result.get('jwt_token'))
            golden_path_steps.append({
                'step': 'websocket_connection',
                'success': websocket_result['success'],
                'details': websocket_result
            })

            if not websocket_result['success']:
                self.failure_points.append('WEBSOCKET_CONNECTION_FAILURE')

            # Step 3: AI Request Submission
            ai_request_result = await self._test_ai_request_submission(
                websocket_result.get('websocket'),
                login_result.get('jwt_token')
            )
            golden_path_steps.append({
                'step': 'ai_request_submission',
                'success': ai_request_result['success'],
                'details': ai_request_result
            })

            if not ai_request_result['success']:
                self.failure_points.append('AI_REQUEST_FAILURE')

            # Step 4: Real-time Event Delivery
            event_delivery_result = await self._test_realtime_event_delivery(
                websocket_result.get('websocket')
            )
            golden_path_steps.append({
                'step': 'realtime_event_delivery',
                'success': event_delivery_result['success'],
                'details': event_delivery_result
            })

            if not event_delivery_result['success']:
                self.failure_points.append('EVENT_DELIVERY_FAILURE')

            # Step 5: AI Response Completion
            ai_response_result = await self._test_ai_response_completion(
                websocket_result.get('websocket')
            )
            golden_path_steps.append({
                'step': 'ai_response_completion',
                'success': ai_response_result['success'],
                'details': ai_response_result
            })

            if not ai_response_result['success']:
                self.failure_points.append('AI_RESPONSE_FAILURE')

            # Calculate overall Golden Path success
            self.golden_path_success = all(step['success'] for step in golden_path_steps)

        except Exception as e:
            self.failure_points.append(f'UNEXPECTED_ERROR: {str(e)}')
            golden_path_steps.append({
                'step': 'unexpected_error',
                'success': False,
                'details': {'error': str(e)}
            })

        # CRITICAL ASSERTION: Complete Golden Path should work (will fail due to SSOT violations)
        assert self.golden_path_success, (
            f"SSOT VIOLATION: Golden Path user flow COMPLETELY BROKEN. "
            f"Failure points: {self.failure_points}. "
            f"Steps completed: {[s['step'] for s in golden_path_steps if s['success']]}. "
            f"Steps failed: {[s['step'] for s in golden_path_steps if not s['success']]}. "
            f"BUSINESS IMPACT: $500K+ ARR blocked - users cannot use core platform functionality."
        )

    @pytest.mark.asyncio
    async def test_concurrent_user_golden_path_failure(self):
        """
        CRITICAL BUSINESS TEST: Prove concurrent users cannot complete Golden Path

        Expected Result: FAIL - Multiple users cannot use platform simultaneously
        Business Impact: 0% concurrent user success rate blocks scalability
        """
        if not self._staging_available():
            pytest.skip("Staging environment not available for E2E testing")

        num_concurrent_users = 3
        concurrent_results = []

        async def test_single_user_golden_path(user_index: int):
            """Test Golden Path for a single user."""
            user_credentials = {
                'email': f'e2e.test.user{user_index}@netra.com',
                'password': 'E2ETestPassword123!',
                'user_id': f'e2e_concurrent_user_{user_index}'
            }

            try:
                # Complete Golden Path for this user
                login_result = await self._test_user_login(user_credentials)
                if not login_result['success']:
                    return {
                        'user_index': user_index,
                        'success': False,
                        'failure_point': 'LOGIN',
                        'error': login_result.get('error')
                    }

                websocket_result = await self._test_websocket_connection(login_result.get('jwt_token'))
                if not websocket_result['success']:
                    return {
                        'user_index': user_index,
                        'success': False,
                        'failure_point': 'WEBSOCKET',
                        'error': websocket_result.get('error')
                    }

                ai_request_result = await self._test_ai_request_submission(
                    websocket_result.get('websocket'),
                    login_result.get('jwt_token')
                )
                if not ai_request_result['success']:
                    return {
                        'user_index': user_index,
                        'success': False,
                        'failure_point': 'AI_REQUEST',
                        'error': ai_request_result.get('error')
                    }

                # Success
                return {
                    'user_index': user_index,
                    'success': True,
                    'completion_time': time.time()
                }

            except Exception as e:
                return {
                    'user_index': user_index,
                    'success': False,
                    'failure_point': 'UNEXPECTED_ERROR',
                    'error': str(e)
                }

        # Execute concurrent Golden Path tests
        tasks = [test_single_user_golden_path(i) for i in range(num_concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze concurrent results
        successful_users = [r for r in results if isinstance(r, dict) and r.get('success', False)]
        failed_users = [r for r in results if not (isinstance(r, dict) and r.get('success', False))]

        concurrent_success_rate = len(successful_users) / num_concurrent_users

        # CRITICAL ASSERTION: All concurrent users should succeed
        assert concurrent_success_rate == 1.0, (
            f"SSOT VIOLATION: Concurrent user Golden Path failures. "
            f"Success rate: {concurrent_success_rate:.2%} ({len(successful_users)}/{num_concurrent_users}). "
            f"Failed users: {failed_users}. "
            f"BUSINESS IMPACT: Platform cannot handle multiple users simultaneously."
        )

    async def _test_user_login(self, credentials: Dict = None) -> Dict[str, Any]:
        """Test user login against staging auth service."""
        if credentials is None:
            credentials = self.test_user_credentials

        try:
            auth_url = f"{self.staging_config['auth_service_url']}/auth/login"

            if not requests:
                return {
                    'success': False,
                    'error': 'HTTP client not available for testing'
                }

            # Attempt login
            response = requests.post(auth_url, json={
                'email': credentials['email'],
                'password': credentials['password']
            }, timeout=10)

            if response.status_code == 200:
                login_data = response.json()
                jwt_token = login_data.get('access_token') or login_data.get('token')

                if jwt_token:
                    return {
                        'success': True,
                        'jwt_token': jwt_token,
                        'user_data': login_data
                    }
                else:
                    return {
                        'success': False,
                        'error': 'No JWT token in login response',
                        'response_data': login_data
                    }
            else:
                return {
                    'success': False,
                    'error': f'Login failed with status {response.status_code}',
                    'response_text': response.text
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'Login request failed: {str(e)}'
            }

    async def _test_websocket_connection(self, jwt_token: str) -> Dict[str, Any]:
        """Test WebSocket connection to staging backend."""
        if not jwt_token:
            return {
                'success': False,
                'error': 'No JWT token provided for WebSocket connection'
            }

        try:
            websocket_url = f"{self.staging_config['websocket_url']}/ws"

            # Add JWT token to headers
            headers = {
                'Authorization': f'Bearer {jwt_token}'
            }

            # Attempt WebSocket connection
            websocket = await websockets.connect(
                websocket_url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )

            # Test connection with ping
            await websocket.ping()

            return {
                'success': True,
                'websocket': websocket,
                'connection_established': True
            }

        except websockets.exceptions.InvalidStatusCode as e:
            return {
                'success': False,
                'error': f'WebSocket connection failed with status {e.status_code}',
                'status_code': e.status_code
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'WebSocket connection failed: {str(e)}'
            }

    async def _test_ai_request_submission(self, websocket, jwt_token: str) -> Dict[str, Any]:
        """Test AI request submission through WebSocket."""
        if not websocket:
            return {
                'success': False,
                'error': 'No WebSocket connection available'
            }

        try:
            # Prepare AI request
            ai_request = {
                'type': 'ai_request',
                'message': 'Please provide AI optimization recommendations for my system.',
                'user_id': self.test_user_credentials['user_id'],
                'timestamp': time.time()
            }

            # Send AI request
            await websocket.send(json.dumps(ai_request))

            # Wait for acknowledgment
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)

                if response_data.get('type') == 'request_received':
                    return {
                        'success': True,
                        'request_acknowledged': True,
                        'response_data': response_data
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Request not acknowledged properly',
                        'response_data': response_data
                    }

            except asyncio.TimeoutError:
                return {
                    'success': False,
                    'error': 'No acknowledgment received for AI request'
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'AI request submission failed: {str(e)}'
            }

    async def _test_realtime_event_delivery(self, websocket) -> Dict[str, Any]:
        """Test real-time event delivery through WebSocket."""
        if not websocket:
            return {
                'success': False,
                'error': 'No WebSocket connection available'
            }

        try:
            # Wait for the 5 critical WebSocket events
            critical_events = [
                'agent_started',
                'agent_thinking',
                'tool_executing',
                'tool_completed',
                'agent_completed'
            ]

            received_events = []
            event_timeout = 30.0  # 30 seconds timeout for all events

            start_time = time.time()

            while len(received_events) < len(critical_events):
                try:
                    remaining_time = event_timeout - (time.time() - start_time)
                    if remaining_time <= 0:
                        break

                    message = await asyncio.wait_for(websocket.recv(), timeout=remaining_time)
                    event_data = json.loads(message)

                    event_type = event_data.get('type') or event_data.get('event_type')
                    if event_type in critical_events:
                        received_events.append({
                            'event_type': event_type,
                            'data': event_data,
                            'timestamp': time.time()
                        })

                except asyncio.TimeoutError:
                    break
                except json.JSONDecodeError:
                    # Skip non-JSON messages
                    continue

            # Analyze event delivery
            received_event_types = [e['event_type'] for e in received_events]
            missing_events = [e for e in critical_events if e not in received_event_types]

            if len(received_events) == len(critical_events):
                return {
                    'success': True,
                    'events_received': received_events,
                    'delivery_complete': True
                }
            else:
                return {
                    'success': False,
                    'error': f'Missing critical events: {missing_events}',
                    'events_received': received_events,
                    'missing_events': missing_events
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'Event delivery test failed: {str(e)}'
            }

    async def _test_ai_response_completion(self, websocket) -> Dict[str, Any]:
        """Test AI response completion through WebSocket."""
        if not websocket:
            return {
                'success': False,
                'error': 'No WebSocket connection available'
            }

        try:
            # Wait for final AI response
            response_timeout = 60.0  # 60 seconds timeout for AI response

            try:
                start_time = time.time()
                final_response = None

                while time.time() - start_time < response_timeout:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    event_data = json.loads(message)

                    event_type = event_data.get('type') or event_data.get('event_type')
                    if event_type == 'agent_completed':
                        final_response = event_data
                        break

                if final_response:
                    # Validate response quality
                    response_text = final_response.get('data', {}).get('final_response', '')
                    if len(response_text) > 50:  # Substantial response
                        return {
                            'success': True,
                            'final_response': final_response,
                            'response_quality': 'substantial'
                        }
                    else:
                        return {
                            'success': False,
                            'error': 'AI response too brief or empty',
                            'final_response': final_response
                        }
                else:
                    return {
                        'success': False,
                        'error': 'No final AI response received within timeout'
                    }

            except asyncio.TimeoutError:
                return {
                    'success': False,
                    'error': 'AI response timeout - no completion event received'
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'AI response completion test failed: {str(e)}'
            }

    def _get_staging_config(self) -> Dict[str, str]:
        """Get staging environment configuration."""
        return {
            'auth_service_url': self.env.get_env('STAGING_AUTH_SERVICE_URL', 'https://auth-staging.netra.com'),
            'backend_service_url': self.env.get_env('STAGING_BACKEND_SERVICE_URL', 'https://backend-staging.netra.com'),
            'websocket_url': self.env.get_env('STAGING_WEBSOCKET_URL', 'wss://backend-staging.netra.com'),
        }

    def _staging_available(self) -> bool:
        """Check if staging environment is available for testing."""
        try:
            # Check if staging URL is accessible
            if not requests:
                return False

            health_url = f"{self.staging_config['backend_service_url']}/health"
            response = requests.get(health_url, timeout=5)
            return response.status_code == 200

        except Exception:
            return False


if __name__ == "__main__":
    # Run this test to prove Golden Path is completely broken
    pytest.main([__file__, "-v", "--tb=short"])
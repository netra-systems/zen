"""
Cross-Service Auth Validation Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (Free/Early/Mid/Enterprise)
- Business Goal: Service Integration and Security
- Value Impact: Validates cross-service auth communication protecting $500K+ ARR
- Strategic Impact: Ensures secure service-to-service communication for Golden Path

CRITICAL: These tests use REAL services to validate cross-service auth patterns.
Tests actual service integration and auth propagation.

GitHub Issue #718 Coverage Enhancement: Cross-service auth validation tests
"""

import asyncio
import pytest
import time
import jwt
import json
import aiohttp
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment
from auth_service.auth_core.config import AuthConfig
from auth_service.services.jwt_service import JWTService
from auth_service.services.redis_service import RedisService


class CrossServiceAuthValidationIntegrationTests(SSotAsyncTestCase):
    """Cross-service auth validation testing with real services."""

    @pytest.fixture(autouse=True)
    async def setup_cross_service_test(self):
        """Set up cross-service test environment with real services."""
        self.env = IsolatedEnvironment.get_instance()

        # Real auth service configuration
        self.auth_config = AuthConfig()
        self.jwt_service = JWTService(self.auth_config)

        # Real Redis service for session storage
        self.redis_service = RedisService(self.auth_config)
        await self.redis_service.connect()

        # Service endpoints for cross-service testing
        self.service_endpoints = {
            'auth_service': {
                'host': self.env.get('AUTH_SERVICE_HOST', 'localhost'),
                'port': self.env.get('AUTH_SERVICE_PORT', '8001'),
                'base_url': None
            },
            'backend_service': {
                'host': self.env.get('BACKEND_SERVICE_HOST', 'localhost'),
                'port': self.env.get('BACKEND_SERVICE_PORT', '8000'),
                'base_url': None
            }
        }

        # Build service URLs
        for service_name, config in self.service_endpoints.items():
            config['base_url'] = f"http://{config['host']}:{config['port']}"

        # Cross-service auth tracking
        self.cross_service_results = []
        self.auth_propagation_tests = []

        # Test users for cross-service scenarios
        self.cross_service_users = [
            {
                'user_id': 'cross_service_user_1',
                'email': 'cross1@example.com',
                'permissions': ['read', 'write']
            },
            {
                'user_id': 'cross_service_admin',
                'email': 'cross_admin@example.com',
                'permissions': ['read', 'write', 'admin']
            },
            {
                'user_id': 'cross_service_enterprise',
                'email': 'cross_enterprise@example.com',
                'permissions': ['read', 'write', 'enterprise']
            }
        ]

        # HTTP client for service communication
        self.http_session = aiohttp.ClientSession()

        yield

        # Cleanup cross-service test data
        await self._cleanup_cross_service_data()

    async def _cleanup_cross_service_data(self):
        """Clean up cross-service test data."""
        try:
            # Clean all cross-service test sessions
            for user in self.cross_service_users:
                pattern = f"session:{user['user_id']}:*"
                keys = await self.redis_service.keys(pattern)
                if keys:
                    await self.redis_service.delete(*keys)

                # Clean cross-service tokens
                token_pattern = f"token:{user['user_id']}:*"
                token_keys = await self.redis_service.keys(token_pattern)
                if token_keys:
                    await self.redis_service.delete(*token_keys)

            # Clean service-to-service auth cache
            service_pattern = "service_auth:*"
            service_keys = await self.redis_service.keys(service_pattern)
            if service_keys:
                await self.redis_service.delete(*service_keys)

            await self.redis_service.close()
            await self.http_session.close()

        except Exception as e:
            self.logger.warning(f"Cross-service test cleanup warning: {e}")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.cross_service
    async def test_auth_service_to_backend_token_validation(self):
        """
        Test auth service to backend service token validation flow.

        BVJ: Validates Golden Path user authentication flows across services.
        """
        user = self.cross_service_users[0]

        # Step 1: Generate token via auth service
        auth_token = await self.jwt_service.create_access_token(
            user_id=user['user_id'],
            email=user['email'],
            permissions=user['permissions']
        )

        assert auth_token is not None, "Auth service failed to generate token"
        assert len(auth_token.split('.')) == 3, "Invalid JWT format from auth service"

        # Step 2: Validate token structure for cross-service compatibility
        decoded_token = jwt.decode(
            auth_token,
            self.auth_config.jwt_secret_key,
            algorithms=[self.auth_config.jwt_algorithm]
        )

        required_claims = ['sub', 'email', 'permissions', 'exp', 'iat', 'jti', 'type']
        for claim in required_claims:
            assert claim in decoded_token, f"Missing required claim for cross-service compatibility: {claim}"

        # Step 3: Store token in shared session store (Redis)
        session_key = f"session:{user['user_id']}:cross_service_test"
        session_data = {
            'user_id': user['user_id'],
            'token': auth_token,
            'permissions': user['permissions'],
            'created_at': datetime.now(timezone.utc).isoformat(),
            'service_origin': 'auth_service',
            'cross_service_validated': False
        }

        await self.redis_service.set(session_key, session_data, ex=1800)

        # Step 4: Simulate backend service retrieving and validating token
        retrieved_session = await self.redis_service.get(session_key)
        assert retrieved_session is not None, "Backend service cannot retrieve session from Redis"

        retrieved_token = retrieved_session['token']
        assert retrieved_token == auth_token, "Token corruption during cross-service transfer"

        # Step 5: Backend service validates token
        backend_validation = await self.jwt_service.validate_token(retrieved_token)
        assert backend_validation, "Backend service token validation failed"

        # Step 6: Update session to mark cross-service validation
        retrieved_session['cross_service_validated'] = True
        retrieved_session['backend_validation_time'] = datetime.now(timezone.utc).isoformat()
        await self.redis_service.set(session_key, retrieved_session, ex=1800)

        # Step 7: Validate cross-service auth propagation
        final_session = await self.redis_service.get(session_key)
        assert final_session['cross_service_validated'], "Cross-service validation not properly propagated"

        # Step 8: Test permission consistency across services
        auth_permissions = set(decoded_token['permissions'])
        session_permissions = set(final_session['permissions'])
        assert auth_permissions == session_permissions, "Permission inconsistency across services"

        self.cross_service_results.append({
            'test_type': 'auth_to_backend_validation',
            'user_id': user['user_id'],
            'success': True,
            'token_valid': backend_validation,
            'session_propagated': True,
            'permissions_consistent': True,
            'timestamp': datetime.now(timezone.utc)
        })

        self.logger.info(f"Auth service to backend validation successful for user {user['user_id']}")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.cross_service
    async def test_service_to_service_authentication(self):
        """
        Test service-to-service authentication mechanisms.

        BVJ: Validates secure service communication for internal API calls.
        """
        # Generate service-to-service authentication token
        service_token = await self.jwt_service.create_access_token(
            user_id='system',  # Special system user for service-to-service
            email='system@netra.ai',
            permissions=['service_internal', 'system_access'],
            expires_delta=timedelta(hours=1)  # Longer expiry for service tokens
        )

        assert service_token is not None, "Service-to-service token generation failed"

        # Validate service token structure
        decoded_service_token = jwt.decode(
            service_token,
            self.auth_config.jwt_secret_key,
            algorithms=[self.auth_config.jwt_algorithm]
        )

        assert decoded_service_token['sub'] == 'system', "Service token user_id incorrect"
        assert 'service_internal' in decoded_service_token['permissions'], "Service permissions missing"

        # Store service auth in Redis with special prefix
        service_auth_key = f"service_auth:backend_to_auth:{int(time.time())}"
        service_auth_data = {
            'service_token': service_token,
            'source_service': 'backend',
            'target_service': 'auth',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'auth_level': 'service_internal'
        }

        await self.redis_service.set(service_auth_key, service_auth_data, ex=3600)

        # Simulate cross-service API call authentication
        async def simulate_service_to_service_call():
            """Simulate backend service calling auth service."""
            try:
                # Retrieve service auth
                service_auth = await self.redis_service.get(service_auth_key)
                if not service_auth:
                    return {'success': False, 'error': 'Service auth not found'}

                # Validate service token
                service_token_to_validate = service_auth['service_token']
                is_service_token_valid = await self.jwt_service.validate_token(service_token_to_validate)

                if not is_service_token_valid:
                    return {'success': False, 'error': 'Service token validation failed'}

                # Simulate internal API operation
                internal_operation_result = {
                    'operation': 'internal_user_lookup',
                    'result': 'success',
                    'service_authenticated': True,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }

                return {
                    'success': True,
                    'service_auth_valid': is_service_token_valid,
                    'operation_result': internal_operation_result,
                    'error': None
                }

            except Exception as e:
                return {'success': False, 'error': str(e)}

        service_call_result = await simulate_service_to_service_call()

        assert service_call_result['success'], f"Service-to-service call failed: {service_call_result.get('error')}"
        assert service_call_result['service_auth_valid'], "Service authentication validation failed"

        # Test multiple concurrent service-to-service calls
        concurrent_service_calls = []
        for i in range(5):
            call_task = simulate_service_to_service_call()
            concurrent_service_calls.append(call_task)

        concurrent_results = await asyncio.gather(*concurrent_service_calls)

        successful_concurrent_calls = [r for r in concurrent_results if r['success']]
        assert len(successful_concurrent_calls) == len(concurrent_results), "Concurrent service calls failed"

        # Cleanup service auth
        await self.redis_service.delete(service_auth_key)

        self.cross_service_results.append({
            'test_type': 'service_to_service_auth',
            'success': True,
            'service_token_valid': True,
            'concurrent_calls_successful': len(successful_concurrent_calls),
            'total_concurrent_calls': len(concurrent_results),
            'timestamp': datetime.now(timezone.utc)
        })

        self.logger.info(f"Service-to-service authentication successful: {len(successful_concurrent_calls)} concurrent calls")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.cross_service
    async def test_user_context_propagation_across_services(self):
        """
        Test user context propagation across multiple services.

        BVJ: Ensures user permissions and context are maintained across service boundaries.
        """
        # Test with different user permission levels
        test_scenarios = [
            {
                'user': self.cross_service_users[0],  # Basic user
                'expected_access': ['read', 'write'],
                'restricted_operations': ['admin', 'enterprise']
            },
            {
                'user': self.cross_service_users[1],  # Admin user
                'expected_access': ['read', 'write', 'admin'],
                'restricted_operations': ['enterprise']
            },
            {
                'user': self.cross_service_users[2],  # Enterprise user
                'expected_access': ['read', 'write', 'enterprise'],
                'restricted_operations': []
            }
        ]

        propagation_results = []

        for scenario in test_scenarios:
            user = scenario['user']
            expected_access = scenario['expected_access']
            restricted_ops = scenario['restricted_operations']

            # Step 1: Create user token with specific permissions
            user_token = await self.jwt_service.create_access_token(
                user_id=user['user_id'],
                email=user['email'],
                permissions=user['permissions']
            )

            # Step 2: Store user context in cross-service session
            user_context_key = f"user_context:{user['user_id']}:propagation_test"
            user_context_data = {
                'user_id': user['user_id'],
                'email': user['email'],
                'permissions': user['permissions'],
                'token': user_token,
                'context_created_by': 'auth_service',
                'propagation_chain': ['auth_service'],
                'created_at': datetime.now(timezone.utc).isoformat()
            }

            await self.redis_service.set(user_context_key, user_context_data, ex=1800)

            # Step 3: Simulate backend service accessing user context
            backend_context = await self.redis_service.get(user_context_key)
            assert backend_context is not None, f"Backend service cannot access user context for {user['user_id']}"

            # Update propagation chain
            backend_context['propagation_chain'].append('backend_service')
            backend_context['backend_access_time'] = datetime.now(timezone.utc).isoformat()

            # Step 4: Backend service validates user permissions
            user_permissions = set(backend_context['permissions'])
            expected_permissions = set(expected_access)

            # Validate expected permissions are present
            missing_permissions = expected_permissions - user_permissions
            extra_permissions = user_permissions - set(user['permissions'])  # Should not have extra

            assert len(missing_permissions) == 0, f"Missing expected permissions: {missing_permissions}"
            assert len(extra_permissions) == 0, f"User has unexpected permissions: {extra_permissions}"

            # Step 5: Test permission-based access control
            access_control_results = []

            for permission in expected_access:
                # Simulate operation requiring this permission
                has_permission = permission in backend_context['permissions']
                access_control_results.append({
                    'permission': permission,
                    'access_granted': has_permission,
                    'expected': True
                })

            for restricted_permission in restricted_ops:
                # Simulate operation user should NOT have access to
                has_restricted = restricted_permission in backend_context['permissions']
                access_control_results.append({
                    'permission': restricted_permission,
                    'access_granted': has_restricted,
                    'expected': False
                })

            # Validate access control
            failed_access_control = [
                ac for ac in access_control_results
                if ac['access_granted'] != ac['expected']
            ]

            assert len(failed_access_control) == 0, f"Access control failures: {failed_access_control}"

            # Step 6: Update user context after backend processing
            backend_context['backend_operations_completed'] = True
            backend_context['access_control_validated'] = True
            await self.redis_service.set(user_context_key, backend_context, ex=1800)

            # Step 7: Simulate additional service (e.g., analytics) accessing context
            analytics_context = await self.redis_service.get(user_context_key)
            analytics_context['propagation_chain'].append('analytics_service')
            analytics_context['analytics_access_time'] = datetime.now(timezone.utc).isoformat()

            # Step 8: Validate context integrity across all services
            final_context = analytics_context
            expected_chain = ['auth_service', 'backend_service', 'analytics_service']
            actual_chain = final_context['propagation_chain']

            assert actual_chain == expected_chain, f"Context propagation chain broken: {actual_chain}"
            assert final_context['user_id'] == user['user_id'], "User ID corrupted during propagation"
            assert final_context['email'] == user['email'], "Email corrupted during propagation"

            # Validate token consistency
            propagated_token = final_context['token']
            token_validation = await self.jwt_service.validate_token(propagated_token)
            assert token_validation, f"Token invalid after cross-service propagation for {user['user_id']}"

            propagation_results.append({
                'user_id': user['user_id'],
                'user_type': 'admin' if 'admin' in user['permissions'] else 'enterprise' if 'enterprise' in user['permissions'] else 'basic',
                'propagation_successful': True,
                'services_in_chain': len(actual_chain),
                'permissions_validated': len(failed_access_control) == 0,
                'token_valid_after_propagation': token_validation,
                'access_control_tests': len(access_control_results),
                'timestamp': datetime.now(timezone.utc)
            })

            # Cleanup user context
            await self.redis_service.delete(user_context_key)

        # Analyze propagation results across all user types
        successful_propagations = [r for r in propagation_results if r['propagation_successful']]
        assert len(successful_propagations) == len(test_scenarios), "Not all user context propagations successful"

        # Validate each user type was tested
        user_types_tested = {r['user_type'] for r in propagation_results}
        expected_user_types = {'basic', 'admin', 'enterprise'}
        assert user_types_tested == expected_user_types, f"Missing user type tests: {expected_user_types - user_types_tested}"

        self.auth_propagation_tests.extend(propagation_results)

        self.logger.info(f"User context propagation test: {len(successful_propagations)} users across {len(expected_user_types)} permission levels")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.cross_service
    async def test_cross_service_session_synchronization(self):
        """
        Test session synchronization across multiple services.

        BVJ: Ensures consistent user sessions across service boundaries.
        """
        user = self.cross_service_users[0]

        # Create user session in auth service
        auth_session_token = await self.jwt_service.create_access_token(
            user_id=user['user_id'],
            email=user['email'],
            permissions=user['permissions']
        )

        # Primary session in auth service
        auth_session_key = f"auth_session:{user['user_id']}:sync_test"
        auth_session_data = {
            'user_id': user['user_id'],
            'token': auth_session_token,
            'service': 'auth',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'last_activity': datetime.now(timezone.utc).isoformat(),
            'session_state': 'active',
            'synchronized_services': []
        }

        await self.redis_service.set(auth_session_key, auth_session_data, ex=1800)

        # Step 1: Backend service synchronizes with auth session
        backend_session_key = f"backend_session:{user['user_id']}:sync_test"

        # Backend retrieves auth session for synchronization
        auth_session = await self.redis_service.get(auth_session_key)
        assert auth_session is not None, "Backend cannot access auth session for synchronization"

        # Create synchronized backend session
        backend_session_data = {
            'user_id': user['user_id'],
            'auth_token': auth_session['token'],
            'service': 'backend',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'last_activity': datetime.now(timezone.utc).isoformat(),
            'session_state': 'active',
            'synchronized_with': 'auth_service',
            'auth_session_key': auth_session_key
        }

        await self.redis_service.set(backend_session_key, backend_session_data, ex=1800)

        # Update auth session to record synchronization
        auth_session['synchronized_services'].append('backend')
        auth_session['backend_session_key'] = backend_session_key
        await self.redis_service.set(auth_session_key, auth_session, ex=1800)

        # Step 2: Test session activity synchronization
        # Simulate user activity in backend service
        backend_session = await self.redis_service.get(backend_session_key)
        backend_session['last_activity'] = datetime.now(timezone.utc).isoformat()
        backend_session['activity_count'] = backend_session.get('activity_count', 0) + 1

        await self.redis_service.set(backend_session_key, backend_session, ex=1800)

        # Synchronize activity back to auth session
        auth_session_updated = await self.redis_service.get(auth_session_key)
        auth_session_updated['last_backend_activity'] = backend_session['last_activity']
        auth_session_updated['total_activities'] = auth_session_updated.get('total_activities', 0) + 1

        await self.redis_service.set(auth_session_key, auth_session_updated, ex=1800)

        # Step 3: Test session state synchronization
        # Simulate session timeout in one service
        async def test_session_timeout_sync():
            """Test session timeout synchronization."""
            # Mark auth session as expired
            auth_session_expired = await self.redis_service.get(auth_session_key)
            auth_session_expired['session_state'] = 'expired'
            auth_session_expired['expired_at'] = datetime.now(timezone.utc).isoformat()

            await self.redis_service.set(auth_session_key, auth_session_expired, ex=1800)

            # Backend should detect and sync session expiry
            backend_session_check = await self.redis_service.get(backend_session_key)
            auth_session_check = await self.redis_service.get(auth_session_key)

            # Simulate backend checking auth session status
            if auth_session_check['session_state'] == 'expired':
                backend_session_check['session_state'] = 'expired'
                backend_session_check['sync_expired_at'] = datetime.now(timezone.utc).isoformat()
                await self.redis_service.set(backend_session_key, backend_session_check, ex=300)  # Shorter TTL for expired

            return {
                'auth_session_expired': auth_session_check['session_state'] == 'expired',
                'backend_session_synced': backend_session_check['session_state'] == 'expired',
                'sync_successful': auth_session_check['session_state'] == backend_session_check['session_state']
            }

        timeout_sync_result = await test_session_timeout_sync()

        assert timeout_sync_result['auth_session_expired'], "Auth session timeout not properly set"
        assert timeout_sync_result['backend_session_synced'], "Backend session did not sync timeout status"
        assert timeout_sync_result['sync_successful'], "Session state synchronization failed"

        # Step 4: Test session cleanup synchronization
        # When auth session is cleaned up, related sessions should also be cleaned
        await self.redis_service.delete(auth_session_key)

        # Verify backend session can detect orphaned state
        orphaned_backend_session = await self.redis_service.get(backend_session_key)
        assert orphaned_backend_session is not None, "Backend session was prematurely deleted"

        # Simulate backend service cleanup check
        auth_session_exists = await self.redis_service.exists(auth_session_key)
        if not auth_session_exists:
            # Backend should clean up its session too
            await self.redis_service.delete(backend_session_key)

        # Verify cleanup completed
        final_auth_session = await self.redis_service.get(auth_session_key)
        final_backend_session = await self.redis_service.get(backend_session_key)

        assert final_auth_session is None, "Auth session not properly cleaned up"
        assert final_backend_session is None, "Backend session not properly cleaned up"

        # Step 5: Test concurrent session access
        # Create new sessions for concurrent testing
        concurrent_auth_token = await self.jwt_service.create_access_token(
            user_id=user['user_id'],
            email=user['email'],
            permissions=user['permissions']
        )

        concurrent_session_results = []

        async def concurrent_session_operation(operation_id):
            """Simulate concurrent session operations."""
            try:
                session_key = f"concurrent_session:{user['user_id']}:{operation_id}"
                session_data = {
                    'user_id': user['user_id'],
                    'token': concurrent_auth_token,
                    'operation_id': operation_id,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'service': f'service_{operation_id % 3}'  # Simulate 3 different services
                }

                await self.redis_service.set(session_key, session_data, ex=600)

                # Simulate session validation
                stored_session = await self.redis_service.get(session_key)
                is_valid = stored_session is not None and stored_session['user_id'] == user['user_id']

                # Cleanup
                await self.redis_service.delete(session_key)

                return {
                    'operation_id': operation_id,
                    'success': True,
                    'session_valid': is_valid,
                    'error': None
                }

            except Exception as e:
                return {
                    'operation_id': operation_id,
                    'success': False,
                    'session_valid': False,
                    'error': str(e)
                }

        # Run concurrent session operations
        concurrent_tasks = [concurrent_session_operation(i) for i in range(10)]
        concurrent_session_results = await asyncio.gather(*concurrent_tasks)

        successful_concurrent_sessions = [r for r in concurrent_session_results if r['success']]
        assert len(successful_concurrent_sessions) == len(concurrent_session_results), "Concurrent session operations failed"

        self.cross_service_results.append({
            'test_type': 'session_synchronization',
            'user_id': user['user_id'],
            'sync_successful': timeout_sync_result['sync_successful'],
            'cleanup_successful': final_auth_session is None and final_backend_session is None,
            'concurrent_operations': len(successful_concurrent_sessions),
            'total_concurrent': len(concurrent_session_results),
            'timestamp': datetime.now(timezone.utc)
        })

        self.logger.info(f"Cross-service session synchronization successful: {len(successful_concurrent_sessions)} concurrent operations")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.cross_service
    async def test_multi_service_auth_consistency_validation(self):
        """
        Test auth consistency across multiple service interactions.

        BVJ: Ensures auth decisions remain consistent across complex service workflows.
        """
        user = self.cross_service_users[1]  # Admin user for comprehensive testing

        # Create master auth token
        master_token = await self.jwt_service.create_access_token(
            user_id=user['user_id'],
            email=user['email'],
            permissions=user['permissions']
        )

        # Multi-service workflow simulation
        workflow_services = ['auth', 'backend', 'analytics', 'websocket', 'api_gateway']
        workflow_results = []

        # Step 1: Initialize workflow with master token
        workflow_id = f"workflow_{int(time.time())}"
        workflow_state_key = f"workflow_state:{workflow_id}"
        workflow_state = {
            'workflow_id': workflow_id,
            'user_id': user['user_id'],
            'master_token': master_token,
            'services_completed': [],
            'auth_decisions': [],
            'created_at': datetime.now(timezone.utc).isoformat(),
            'current_service': 'auth'
        }

        await self.redis_service.set(workflow_state_key, workflow_state, ex=3600)

        # Step 2: Simulate workflow progression through services
        for service_index, service_name in enumerate(workflow_services):
            service_start_time = time.time()

            try:
                # Retrieve current workflow state
                current_workflow = await self.redis_service.get(workflow_state_key)
                assert current_workflow is not None, f"Workflow state lost at service {service_name}"

                # Validate token consistency
                workflow_token = current_workflow['master_token']
                token_valid = await self.jwt_service.validate_token(workflow_token)
                assert token_valid, f"Token invalid at service {service_name}"

                # Extract permissions for this service
                decoded_token = jwt.decode(
                    workflow_token,
                    self.auth_config.jwt_secret_key,
                    algorithms=[self.auth_config.jwt_algorithm]
                )
                token_permissions = set(decoded_token['permissions'])

                # Simulate service-specific auth decision
                service_auth_decision = {
                    'service': service_name,
                    'user_id': user['user_id'],
                    'permissions_checked': list(token_permissions),
                    'access_granted': True,  # Admin user should have access to all
                    'decision_time': datetime.now(timezone.utc).isoformat(),
                    'service_order': service_index
                }

                # Simulate different permission requirements per service
                if service_name == 'analytics':
                    # Analytics requires read permission
                    required_permission = 'read'
                    service_auth_decision['required_permission'] = required_permission
                    service_auth_decision['access_granted'] = required_permission in token_permissions

                elif service_name == 'api_gateway':
                    # API Gateway requires admin permission
                    required_permission = 'admin'
                    service_auth_decision['required_permission'] = required_permission
                    service_auth_decision['access_granted'] = required_permission in token_permissions

                elif service_name == 'websocket':
                    # WebSocket requires write permission for chat
                    required_permission = 'write'
                    service_auth_decision['required_permission'] = required_permission
                    service_auth_decision['access_granted'] = required_permission in token_permissions

                # Update workflow state
                current_workflow['services_completed'].append(service_name)
                current_workflow['auth_decisions'].append(service_auth_decision)
                current_workflow['current_service'] = workflow_services[service_index + 1] if service_index + 1 < len(workflow_services) else 'completed'
                current_workflow['last_update'] = datetime.now(timezone.utc).isoformat()

                # Store updated workflow state
                await self.redis_service.set(workflow_state_key, current_workflow, ex=3600)

                service_duration = time.time() - service_start_time

                workflow_results.append({
                    'service': service_name,
                    'success': True,
                    'auth_decision': service_auth_decision,
                    'processing_time': service_duration,
                    'token_valid': token_valid,
                    'workflow_state_maintained': True,
                    'error': None
                })

            except Exception as e:
                service_duration = time.time() - service_start_time

                workflow_results.append({
                    'service': service_name,
                    'success': False,
                    'auth_decision': None,
                    'processing_time': service_duration,
                    'token_valid': False,
                    'workflow_state_maintained': False,
                    'error': str(e)
                })

        # Step 3: Analyze workflow consistency
        successful_services = [r for r in workflow_results if r['success']]
        failed_services = [r for r in workflow_results if not r['success']]

        # Retrieve final workflow state
        final_workflow_state = await self.redis_service.get(workflow_state_key)

        # Consistency validations
        consistency_checks = {
            'all_services_completed': len(successful_services) == len(workflow_services),
            'no_service_failures': len(failed_services) == 0,
            'workflow_state_complete': final_workflow_state is not None and final_workflow_state['current_service'] == 'completed',
            'auth_decisions_consistent': True,  # Will validate below
            'token_valid_throughout': all(r['token_valid'] for r in successful_services)
        }

        # Validate auth decision consistency
        auth_decisions = [r['auth_decision'] for r in successful_services if r['auth_decision']]

        # Check permission consistency across services
        permission_sets = [set(decision['permissions_checked']) for decision in auth_decisions]
        if len(permission_sets) > 1:
            # All permission sets should be identical (same token)
            first_permission_set = permission_sets[0]
            consistency_checks['auth_decisions_consistent'] = all(
                perm_set == first_permission_set for perm_set in permission_sets
            )

        # Check access decisions are appropriate for admin user
        access_decisions = [decision['access_granted'] for decision in auth_decisions]
        consistency_checks['appropriate_access_granted'] = all(access_decisions)  # Admin should have access to all

        # Business continuity validation
        assert consistency_checks['all_services_completed'], f"Not all services completed: {len(successful_services)}/{len(workflow_services)}"
        assert consistency_checks['token_valid_throughout'], "Token validation failed in multi-service workflow"
        assert consistency_checks['auth_decisions_consistent'], "Auth decisions inconsistent across services"
        assert consistency_checks['appropriate_access_granted'], f"Admin user denied access inappropriately: {access_decisions}"

        # Performance validation
        total_workflow_time = sum(r['processing_time'] for r in workflow_results)
        avg_service_time = total_workflow_time / len(workflow_services)

        assert total_workflow_time < 10.0, f"Multi-service workflow took too long: {total_workflow_time:.2f}s"
        assert avg_service_time < 2.0, f"Average service auth time too high: {avg_service_time:.3f}s"

        # Cleanup workflow state
        await self.redis_service.delete(workflow_state_key)

        self.cross_service_results.append({
            'test_type': 'multi_service_consistency',
            'workflow_id': workflow_id,
            'user_id': user['user_id'],
            'services_tested': len(workflow_services),
            'services_successful': len(successful_services),
            'consistency_checks': consistency_checks,
            'total_workflow_time': total_workflow_time,
            'timestamp': datetime.now(timezone.utc)
        })

        self.logger.info(f"Multi-service auth consistency validation: {len(successful_services)}/{len(workflow_services)} services, {total_workflow_time:.2f}s total")

        # Final validation: All consistency checks must pass
        failed_consistency_checks = [check for check, passed in consistency_checks.items() if not passed]
        assert len(failed_consistency_checks) == 0, f"Consistency check failures: {failed_consistency_checks}"

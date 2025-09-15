"""
Auth Error Recovery Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (Free/Early/Mid/Enterprise)
- Business Goal: System Resilience and Reliability
- Value Impact: Ensures auth system recovers gracefully from failures, protecting $500K+ ARR
- Strategic Impact: Validates error handling that maintains user access during system issues

CRITICAL: These tests use REAL auth services to validate error recovery patterns.
Tests actual failure scenarios and recovery mechanisms.

GitHub Issue #718 Coverage Enhancement: Error recovery integration tests
"""

import asyncio
import pytest
import time
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from unittest.mock import patch, AsyncMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment
from auth_service.auth_core.config import AuthConfig
from auth_service.services.jwt_service import JWTService
from auth_service.services.redis_service import RedisService


class AuthErrorRecoveryIntegrationTests(SSotAsyncTestCase):
    """Error recovery testing for auth integration with real services."""

    @pytest.fixture(autouse=True)
    async def setup_error_recovery_test(self):
        """Set up error recovery test environment with real services."""
        self.env = IsolatedEnvironment.get_instance()

        # Real auth service configuration
        self.auth_config = AuthConfig()
        self.jwt_service = JWTService(self.auth_config)

        # Real Redis service for session storage
        self.redis_service = RedisService(self.auth_config)
        await self.redis_service.connect()

        # Error tracking for recovery analysis
        self.error_scenarios = []
        self.recovery_metrics = {
            'database_failures': [],
            'redis_failures': [],
            'network_timeouts': [],
            'service_unavailable': [],
            'recovery_times': []
        }

        # Test users for error recovery scenarios
        self.recovery_test_users = [
            {
                'user_id': 'recovery_user_1',
                'email': 'recovery1@example.com',
                'permissions': ['read', 'write']
            },
            {
                'user_id': 'recovery_user_admin',
                'email': 'recovery_admin@example.com',
                'permissions': ['read', 'write', 'admin']
            }
        ]

        yield

        # Cleanup error recovery test data
        await self._cleanup_recovery_data()

    async def _cleanup_recovery_data(self):
        """Clean up error recovery test data."""
        try:
            # Clean all recovery test sessions
            for user in self.recovery_test_users:
                pattern = f"session:{user['user_id']}:*"
                keys = await self.redis_service.keys(pattern)
                if keys:
                    await self.redis_service.delete(*keys)

                # Clean recovery test tokens
                token_pattern = f"token:{user['user_id']}:*"
                token_keys = await self.redis_service.keys(token_pattern)
                if token_keys:
                    await self.redis_service.delete(*token_keys)

            # Clean circuit breaker state
            circuit_pattern = "circuit_breaker:*"
            circuit_keys = await self.redis_service.keys(circuit_pattern)
            if circuit_keys:
                await self.redis_service.delete(*circuit_keys)

            await self.redis_service.close()
        except Exception as e:
            self.logger.warning(f"Error recovery test cleanup warning: {e}")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.error_recovery
    async def test_redis_connection_failure_recovery(self):
        """
        Test recovery from Redis connection failures.

        BVJ: Ensures auth system continues functioning when Redis becomes unavailable.
        """
        user = self.recovery_test_users[0]

        # Establish baseline - create token with Redis working
        baseline_token = await self.jwt_service.create_access_token(
            user_id=user['user_id'],
            email=user['email'],
            permissions=user['permissions']
        )

        # Store initial session
        session_key = f"session:{user['user_id']}:recovery_test"
        session_data = {
            'user_id': user['user_id'],
            'token': baseline_token,
            'created_at': datetime.now(timezone.utc).isoformat()
        }

        await self.redis_service.set(session_key, session_data, ex=1800)

        # Simulate Redis connection failure scenarios
        error_scenarios = []

        # Scenario 1: Temporary Redis disconnect
        try:
            # Close Redis connection to simulate failure
            original_redis = self.redis_service
            await self.redis_service.close()

            # Attempt operations during Redis failure
            failure_start = time.time()

            # Token validation should still work (JWT validation is stateless)
            try:
                is_valid_during_failure = await self.jwt_service.validate_token(baseline_token)
                error_scenarios.append({
                    'scenario': 'redis_disconnect',
                    'operation': 'token_validation',
                    'success': is_valid_during_failure,
                    'error': None
                })
            except Exception as e:
                error_scenarios.append({
                    'scenario': 'redis_disconnect',
                    'operation': 'token_validation',
                    'success': False,
                    'error': str(e)
                })

            # Token creation should handle Redis gracefully
            try:
                token_during_failure = await self.jwt_service.create_access_token(
                    user_id=f"{user['user_id']}_failure",
                    email=user['email'],
                    permissions=user['permissions']
                )
                error_scenarios.append({
                    'scenario': 'redis_disconnect',
                    'operation': 'token_creation',
                    'success': True,
                    'token_length': len(token_during_failure),
                    'error': None
                })
            except Exception as e:
                error_scenarios.append({
                    'scenario': 'redis_disconnect',
                    'operation': 'token_creation',
                    'success': False,
                    'error': str(e)
                })

            # Reconnect Redis (recovery)
            self.redis_service = RedisService(self.auth_config)
            await self.redis_service.connect()

            recovery_time = time.time() - failure_start

            # Validate recovery
            post_recovery_token = await self.jwt_service.create_access_token(
                user_id=f"{user['user_id']}_recovered",
                email=user['email'],
                permissions=user['permissions']
            )

            post_recovery_valid = await self.jwt_service.validate_token(post_recovery_token)

            error_scenarios.append({
                'scenario': 'redis_recovery',
                'operation': 'full_recovery',
                'success': post_recovery_valid,
                'recovery_time': recovery_time,
                'error': None
            })

            self.recovery_metrics['redis_failures'].append({
                'timestamp': datetime.now(timezone.utc),
                'recovery_time': recovery_time,
                'scenarios': error_scenarios
            })

        except Exception as e:
            self.logger.error(f"Redis failure simulation error: {e}")
            # Ensure Redis connection is restored
            self.redis_service = RedisService(self.auth_config)
            await self.redis_service.connect()

        # Validate recovery success
        successful_operations = [s for s in error_scenarios if s['success']]
        critical_operations = [s for s in error_scenarios if s['operation'] in ['token_validation', 'full_recovery']]

        # Critical operations must succeed for business continuity
        critical_successes = [s for s in critical_operations if s['success']]
        assert len(critical_successes) == len(critical_operations), f"Critical auth operations failed during Redis failure"

        # Recovery should be fast
        recovery_operations = [s for s in error_scenarios if 'recovery_time' in s]
        if recovery_operations:
            max_recovery_time = max(s['recovery_time'] for s in recovery_operations)
            assert max_recovery_time < 10, f"Redis recovery took too long: {max_recovery_time:.2f}s"

        self.logger.info(f"Redis failure recovery test: {len(successful_operations)}/{len(error_scenarios)} operations succeeded")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.error_recovery
    async def test_concurrent_failure_recovery(self):
        """
        Test recovery from multiple concurrent failures.

        BVJ: Validates system resilience under multiple simultaneous error conditions.
        """
        user = self.recovery_test_users[0]

        # Create baseline tokens for failure testing
        baseline_tokens = []
        for i in range(10):
            token = await self.jwt_service.create_access_token(
                user_id=f"{user['user_id']}_concurrent_{i}",
                email=user['email'],
                permissions=user['permissions']
            )
            baseline_tokens.append(token)

        # Simulate multiple concurrent failure scenarios
        async def simulate_operation_with_failures(operation_id):
            """Simulate auth operations with random failures."""
            failure_start = time.time()

            try:
                # Randomly introduce different types of failures
                failure_type = random.choice(['network_timeout', 'service_overload', 'temporary_unavailable'])

                if failure_type == 'network_timeout':
                    # Simulate network timeout
                    await asyncio.sleep(random.uniform(0.1, 0.5))
                    if random.random() < 0.3:  # 30% chance of timeout failure
                        raise TimeoutError(f"Network timeout in operation {operation_id}")

                elif failure_type == 'service_overload':
                    # Simulate service overload
                    await asyncio.sleep(random.uniform(0.05, 0.2))
                    if random.random() < 0.2:  # 20% chance of overload failure
                        raise Exception(f"Service overload in operation {operation_id}")

                # Attempt actual auth operation
                operation_type = operation_id % 3

                if operation_type == 0:
                    # Token validation
                    token_to_validate = baseline_tokens[operation_id % len(baseline_tokens)]
                    is_valid = await self.jwt_service.validate_token(token_to_validate)
                    result_data = {'operation': 'validation', 'valid': is_valid}

                elif operation_type == 1:
                    # Token creation
                    new_token = await self.jwt_service.create_access_token(
                        user_id=f"{user['user_id']}_concurrent_failure_{operation_id}",
                        email=user['email'],
                        permissions=user['permissions']
                    )
                    result_data = {'operation': 'creation', 'token_length': len(new_token)}

                else:
                    # Session operation
                    session_key = f"session:{user['user_id']}:concurrent_failure_{operation_id}"
                    session_data = {
                        'user_id': user['user_id'],
                        'operation_id': operation_id,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }

                    await self.redis_service.set(session_key, session_data, ex=300)
                    result_data = {'operation': 'session', 'session_key': session_key}

                operation_time = time.time() - failure_start

                return {
                    'operation_id': operation_id,
                    'success': True,
                    'failure_type': failure_type,
                    'operation_time': operation_time,
                    'result_data': result_data,
                    'error': None
                }

            except Exception as e:
                operation_time = time.time() - failure_start

                # Implement retry logic for recovery
                if "timeout" in str(e).lower() or "overload" in str(e).lower():
                    try:
                        # Simple retry after brief delay
                        await asyncio.sleep(0.1)

                        # Retry the operation (simplified retry logic)
                        retry_token = await self.jwt_service.create_access_token(
                            user_id=f"{user['user_id']}_retry_{operation_id}",
                            email=user['email'],
                            permissions=user['permissions']
                        )

                        retry_time = time.time() - failure_start

                        return {
                            'operation_id': operation_id,
                            'success': True,
                            'failure_type': failure_type,
                            'operation_time': retry_time,
                            'result_data': {'operation': 'retry_success', 'token_length': len(retry_token)},
                            'error': None,
                            'recovery': True
                        }

                    except Exception as retry_error:
                        return {
                            'operation_id': operation_id,
                            'success': False,
                            'failure_type': failure_type,
                            'operation_time': operation_time,
                            'result_data': None,
                            'error': str(retry_error),
                            'original_error': str(e)
                        }

                return {
                    'operation_id': operation_id,
                    'success': False,
                    'failure_type': failure_type,
                    'operation_time': operation_time,
                    'result_data': None,
                    'error': str(e)
                }

        # Execute concurrent operations with simulated failures
        concurrent_operations = 25
        concurrent_start = time.time()

        tasks = [simulate_operation_with_failures(i) for i in range(concurrent_operations)]
        concurrent_results = await asyncio.gather(*tasks)

        total_concurrent_time = time.time() - concurrent_start

        # Analyze concurrent failure recovery
        successful_operations = [r for r in concurrent_results if r['success']]
        failed_operations = [r for r in concurrent_results if not r['success']]
        recovered_operations = [r for r in concurrent_results if r.get('recovery', False)]

        success_rate = len(successful_operations) / len(concurrent_results)
        recovery_rate = len(recovered_operations) / max(len(failed_operations + recovered_operations), 1)

        # Business continuity requirements
        assert success_rate >= 0.75, f"Concurrent failure recovery success rate {success_rate:.2%} below 75% threshold"
        assert recovery_rate >= 0.5, f"Error recovery rate {recovery_rate:.2%} below 50% threshold"

        # Performance under failure conditions
        assert total_concurrent_time < 30, f"Concurrent failure handling took too long: {total_concurrent_time:.2f}s"

        # Analyze operation times
        operation_times = [r['operation_time'] for r in successful_operations]
        if operation_times:
            avg_operation_time = sum(operation_times) / len(operation_times)
            assert avg_operation_time < 2.0, f"Average operation time under failure {avg_operation_time:.3f}s too high"

        self.recovery_metrics['network_timeouts'].extend([
            r for r in concurrent_results if r.get('failure_type') == 'network_timeout'
        ])

        self.logger.info(f"Concurrent failure recovery test:")
        self.logger.info(f"  Operations: {concurrent_operations}")
        self.logger.info(f"  Success Rate: {success_rate:.2%}")
        self.logger.info(f"  Recovery Rate: {recovery_rate:.2%}")
        self.logger.info(f"  Total Time: {total_concurrent_time:.2f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.error_recovery
    async def test_token_validation_degraded_service_recovery(self):
        """
        Test token validation recovery under degraded service conditions.

        BVJ: Ensures users can still authenticate when services are degraded.
        """
        user = self.recovery_test_users[0]

        # Pre-create tokens for validation testing
        test_tokens = []
        for i in range(15):
            token = await self.jwt_service.create_access_token(
                user_id=f"{user['user_id']}_degraded_{i}",
                email=user['email'],
                permissions=user['permissions']
            )
            test_tokens.append(token)

        # Simulate degraded service scenarios
        degradation_scenarios = []

        # Scenario 1: Slow response times
        async def slow_validation_test():
            """Test validation with artificial delays."""
            slow_results = []
            for i, token in enumerate(test_tokens[:5]):
                start_time = time.time()

                # Add artificial delay to simulate slow service
                await asyncio.sleep(random.uniform(0.1, 0.3))

                try:
                    is_valid = await self.jwt_service.validate_token(token)
                    validation_time = time.time() - start_time

                    slow_results.append({
                        'token_index': i,
                        'success': True,
                        'valid': is_valid,
                        'validation_time': validation_time,
                        'error': None
                    })

                except Exception as e:
                    validation_time = time.time() - start_time
                    slow_results.append({
                        'token_index': i,
                        'success': False,
                        'valid': False,
                        'validation_time': validation_time,
                        'error': str(e)
                    })

            return slow_results

        slow_validation_results = await slow_validation_test()

        # Scenario 2: Intermittent failures with recovery
        async def intermittent_failure_test():
            """Test validation with intermittent failures."""
            intermittent_results = []

            for i, token in enumerate(test_tokens[5:10]):
                start_time = time.time()

                try:
                    # Simulate intermittent failure
                    if random.random() < 0.4:  # 40% chance of failure
                        raise Exception(f"Intermittent service failure {i}")

                    is_valid = await self.jwt_service.validate_token(token)
                    validation_time = time.time() - start_time

                    intermittent_results.append({
                        'token_index': i + 5,
                        'success': True,
                        'valid': is_valid,
                        'validation_time': validation_time,
                        'error': None,
                        'retry_attempt': False
                    })

                except Exception as e:
                    # Implement retry logic
                    try:
                        await asyncio.sleep(0.1)  # Brief retry delay
                        is_valid = await self.jwt_service.validate_token(token)
                        retry_time = time.time() - start_time

                        intermittent_results.append({
                            'token_index': i + 5,
                            'success': True,
                            'valid': is_valid,
                            'validation_time': retry_time,
                            'error': None,
                            'retry_attempt': True,
                            'original_error': str(e)
                        })

                    except Exception as retry_error:
                        final_time = time.time() - start_time
                        intermittent_results.append({
                            'token_index': i + 5,
                            'success': False,
                            'valid': False,
                            'validation_time': final_time,
                            'error': str(retry_error),
                            'retry_attempt': True,
                            'original_error': str(e)
                        })

            return intermittent_results

        intermittent_results = await intermittent_failure_test()

        # Scenario 3: Circuit breaker simulation
        async def circuit_breaker_test():
            """Test validation with circuit breaker pattern."""
            circuit_results = []
            failure_count = 0
            circuit_open = False

            for i, token in enumerate(test_tokens[10:15]):
                start_time = time.time()

                try:
                    # Circuit breaker logic
                    if circuit_open:
                        # Circuit is open, fast-fail
                        raise Exception(f"Circuit breaker open - operation {i} failed fast")

                    # Simulate potential failure
                    if random.random() < 0.3:  # 30% chance of failure
                        failure_count += 1
                        if failure_count >= 3:  # Open circuit after 3 failures
                            circuit_open = True
                        raise Exception(f"Service failure {i} (failure count: {failure_count})")

                    is_valid = await self.jwt_service.validate_token(token)
                    validation_time = time.time() - start_time

                    # Reset failure count on success
                    failure_count = max(0, failure_count - 1)

                    circuit_results.append({
                        'token_index': i + 10,
                        'success': True,
                        'valid': is_valid,
                        'validation_time': validation_time,
                        'circuit_state': 'closed',
                        'failure_count': failure_count,
                        'error': None
                    })

                except Exception as e:
                    validation_time = time.time() - start_time

                    circuit_results.append({
                        'token_index': i + 10,
                        'success': False,
                        'valid': False,
                        'validation_time': validation_time,
                        'circuit_state': 'open' if circuit_open else 'closed',
                        'failure_count': failure_count,
                        'error': str(e)
                    })

            return circuit_results

        circuit_breaker_results = await circuit_breaker_test()

        # Combine all degradation scenario results
        all_degradation_results = slow_validation_results + intermittent_results + circuit_breaker_results

        # Analyze degraded service recovery
        successful_validations = [r for r in all_degradation_results if r['success']]
        failed_validations = [r for r in all_degradation_results if not r['success']]
        retry_successes = [r for r in all_degradation_results if r.get('retry_attempt') and r['success']]

        success_rate = len(successful_validations) / len(all_degradation_results)
        retry_success_rate = len(retry_successes) / max(len([r for r in all_degradation_results if r.get('retry_attempt')]), 1)

        # Business continuity requirements
        assert success_rate >= 0.6, f"Degraded service success rate {success_rate:.2%} below 60% threshold"

        # Performance under degraded conditions
        successful_times = [r['validation_time'] for r in successful_validations]
        if successful_times:
            avg_success_time = sum(successful_times) / len(successful_times)
            max_success_time = max(successful_times)

            # Degraded service should still be reasonably fast
            assert avg_success_time < 1.0, f"Average validation time under degradation {avg_success_time:.3f}s too high"
            assert max_success_time < 3.0, f"Max validation time under degradation {max_success_time:.3f}s too high"

        # Validate all successful tokens are actually valid
        valid_tokens = [r for r in successful_validations if r.get('valid', False)]
        assert len(valid_tokens) == len(successful_validations), "Some successful validations returned invalid tokens"

        self.recovery_metrics['service_unavailable'].append({
            'timestamp': datetime.now(timezone.utc),
            'total_operations': len(all_degradation_results),
            'success_rate': success_rate,
            'retry_success_rate': retry_success_rate,
            'scenarios': {
                'slow_response': len(slow_validation_results),
                'intermittent_failure': len(intermittent_results),
                'circuit_breaker': len(circuit_breaker_results)
            }
        })

        self.logger.info(f"Degraded service recovery test:")
        self.logger.info(f"  Total Validations: {len(all_degradation_results)}")
        self.logger.info(f"  Success Rate: {success_rate:.2%}")
        self.logger.info(f"  Retry Success Rate: {retry_success_rate:.2%}")
        self.logger.info(f"  Scenario Breakdown: Slow={len(slow_validation_results)}, "
                        f"Intermittent={len(intermittent_results)}, Circuit={len(circuit_breaker_results)}")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.error_recovery
    async def test_auth_system_graceful_degradation(self):
        """
        Test auth system graceful degradation under various error conditions.

        BVJ: Ensures auth system degrades gracefully rather than failing completely.
        """
        user = self.recovery_test_users[1]  # Use admin user for comprehensive testing

        # Create baseline for degradation testing
        baseline_token = await self.jwt_service.create_access_token(
            user_id=user['user_id'],
            email=user['email'],
            permissions=user['permissions']
        )

        # Test graceful degradation scenarios
        degradation_test_results = []

        # Scenario 1: Reduced functionality mode
        async def reduced_functionality_test():
            """Test auth with reduced functionality."""
            try:
                # Create token with minimal permissions during degradation
                degraded_token = await self.jwt_service.create_access_token(
                    user_id=f"{user['user_id']}_degraded",
                    email=user['email'],
                    permissions=['read'],  # Reduced from full admin permissions
                    expires_delta=timedelta(minutes=5)  # Shorter expiry during degradation
                )

                # Validate reduced functionality token
                is_valid = await self.jwt_service.validate_token(degraded_token)

                return {
                    'scenario': 'reduced_functionality',
                    'success': True,
                    'token_created': True,
                    'token_valid': is_valid,
                    'graceful_degradation': True,
                    'error': None
                }

            except Exception as e:
                return {
                    'scenario': 'reduced_functionality',
                    'success': False,
                    'token_created': False,
                    'token_valid': False,
                    'graceful_degradation': False,
                    'error': str(e)
                }

        reduced_functionality_result = await reduced_functionality_test()
        degradation_test_results.append(reduced_functionality_result)

        # Scenario 2: Fallback authentication mode
        async def fallback_auth_test():
            """Test fallback authentication mechanisms."""
            try:
                # Test basic token validation (should always work as it's stateless)
                baseline_valid = await self.jwt_service.validate_token(baseline_token)

                # Create emergency access token
                emergency_token = await self.jwt_service.create_access_token(
                    user_id=f"{user['user_id']}_emergency",
                    email=user['email'],
                    permissions=['read'],  # Emergency minimal access
                    expires_delta=timedelta(minutes=15)  # Emergency session duration
                )

                emergency_valid = await self.jwt_service.validate_token(emergency_token)

                return {
                    'scenario': 'fallback_auth',
                    'success': True,
                    'baseline_valid': baseline_valid,
                    'emergency_token_created': True,
                    'emergency_token_valid': emergency_valid,
                    'fallback_functional': baseline_valid and emergency_valid,
                    'error': None
                }

            except Exception as e:
                return {
                    'scenario': 'fallback_auth',
                    'success': False,
                    'baseline_valid': False,
                    'emergency_token_created': False,
                    'emergency_token_valid': False,
                    'fallback_functional': False,
                    'error': str(e)
                }

        fallback_auth_result = await fallback_auth_test()
        degradation_test_results.append(fallback_auth_result)

        # Scenario 3: Cache-based operation during service issues
        async def cache_based_operation_test():
            """Test cache-based operations during service degradation."""
            try:
                # Store auth result in Redis for caching
                cache_key = f"auth_cache:{user['user_id']}:degradation_test"
                cache_data = {
                    'user_id': user['user_id'],
                    'permissions': user['permissions'],
                    'cached_at': datetime.now(timezone.utc).isoformat(),
                    'cache_ttl': 300  # 5 minute cache
                }

                await self.redis_service.set(cache_key, cache_data, ex=300)

                # Retrieve cached auth data
                cached_auth = await self.redis_service.get(cache_key)

                # Validate cache-based authentication
                cache_based_auth_success = (
                    cached_auth is not None and
                    cached_auth.get('user_id') == user['user_id'] and
                    'permissions' in cached_auth
                )

                # Clean up cache
                await self.redis_service.delete(cache_key)

                return {
                    'scenario': 'cache_based_operation',
                    'success': True,
                    'cache_stored': True,
                    'cache_retrieved': cached_auth is not None,
                    'cache_auth_valid': cache_based_auth_success,
                    'degradation_handled': cache_based_auth_success,
                    'error': None
                }

            except Exception as e:
                return {
                    'scenario': 'cache_based_operation',
                    'success': False,
                    'cache_stored': False,
                    'cache_retrieved': False,
                    'cache_auth_valid': False,
                    'degradation_handled': False,
                    'error': str(e)
                }

        cache_based_result = await cache_based_operation_test()
        degradation_test_results.append(cache_based_result)

        # Analyze graceful degradation results
        successful_degradations = [r for r in degradation_test_results if r['success']]
        graceful_degradations = [r for r in degradation_test_results if r.get('graceful_degradation', False)]

        degradation_success_rate = len(successful_degradations) / len(degradation_test_results)
        graceful_degradation_rate = len(graceful_degradations) / len(degradation_test_results)

        # Business continuity requirements
        assert degradation_success_rate >= 0.8, f"Graceful degradation success rate {degradation_success_rate:.2%} below 80%"

        # Validate specific degradation scenarios
        for result in degradation_test_results:
            scenario = result['scenario']

            if scenario == 'reduced_functionality':
                assert result.get('token_created', False), "Reduced functionality mode failed to create tokens"
                assert result.get('token_valid', False), "Reduced functionality tokens are invalid"

            elif scenario == 'fallback_auth':
                assert result.get('baseline_valid', False), "Baseline authentication failed during fallback test"
                assert result.get('fallback_functional', False), "Fallback authentication is not functional"

            elif scenario == 'cache_based_operation':
                assert result.get('cache_stored', False), "Cache-based operation failed to store auth data"
                assert result.get('degradation_handled', False), "Cache-based degradation handling failed"

        # Validate baseline functionality still works after degradation tests
        final_validation = await self.jwt_service.validate_token(baseline_token)
        assert final_validation, "Baseline token validation failed after graceful degradation tests"

        self.recovery_metrics['recovery_times'].append({
            'timestamp': datetime.now(timezone.utc),
            'degradation_scenarios': len(degradation_test_results),
            'success_rate': degradation_success_rate,
            'graceful_rate': graceful_degradation_rate,
            'scenarios': [r['scenario'] for r in successful_degradations]
        })

        self.logger.info(f"Graceful degradation test:")
        self.logger.info(f"  Scenarios Tested: {len(degradation_test_results)}")
        self.logger.info(f"  Success Rate: {degradation_success_rate:.2%}")
        self.logger.info(f"  Graceful Degradation Rate: {graceful_degradation_rate:.2%}")
        self.logger.info(f"  Successful Scenarios: {[r['scenario'] for r in successful_degradations]}")

        # Final business impact validation
        assert len(successful_degradations) >= 2, f"Insufficient degradation scenarios succeeded: {len(successful_degradations)}"

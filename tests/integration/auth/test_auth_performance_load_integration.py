"""
Auth Performance Load Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (Free/Early/Mid/Enterprise)
- Business Goal: System Reliability and Performance Validation
- Value Impact: Validates auth system can handle 100+ concurrent users without degradation
- Strategic Impact: Protects $500K+ ARR by ensuring auth scalability for user growth

CRITICAL: These tests use REAL auth services (no mocks) with performance monitoring.
Validates business-critical auth flows under realistic load conditions.

GitHub Issue #718 Coverage Enhancement: Performance Testing Scenarios (100+ concurrent users)
"""

import asyncio
import time
import pytest
import statistics
from datetime import datetime, timezone
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment
from auth_service.auth_core.config import AuthConfig
from auth_service.services.jwt_service import JWTService
from auth_service.services.redis_service import RedisService


class AuthPerformanceLoadIntegrationTests(SSotAsyncTestCase):
    """Performance load testing for auth integration with real services."""

    @pytest.fixture(autouse=True)
    async def setup_performance_test(self):
        """Set up performance test environment with real services."""
        self.env = IsolatedEnvironment.get_instance()

        # Real auth service configuration
        self.auth_config = AuthConfig()
        self.jwt_service = JWTService(self.auth_config)

        # Real Redis service for session storage
        self.redis_service = RedisService(self.auth_config)
        await self.redis_service.connect()

        # Performance monitoring
        self.performance_metrics = {
            'token_generation_times': [],
            'token_validation_times': [],
            'concurrent_operations': [],
            'error_rates': [],
            'memory_usage': []
        }

        # Test user pool for concurrent testing
        self.user_pool = [
            {
                'user_id': f'perf_user_{i}',
                'email': f'perf_user_{i}@example.com',
                'permissions': ['read', 'write'] if i % 2 == 0 else ['read']
            }
            for i in range(150)  # Pool larger than concurrent test size
        ]

        yield

        # Cleanup performance test data
        await self._cleanup_performance_data()

    async def _cleanup_performance_data(self):
        """Clean up all performance test data from Redis."""
        try:
            # Clean all test user sessions
            for user in self.user_pool[:100]:  # Only cleanup users actually used
                pattern = f"session:{user['user_id']}:*"
                keys = await self.redis_service.keys(pattern)
                if keys:
                    await self.redis_service.delete(*keys)

                # Clean user tokens
                token_pattern = f"token:{user['user_id']}:*"
                token_keys = await self.redis_service.keys(token_pattern)
                if token_keys:
                    await self.redis_service.delete(*token_keys)

            await self.redis_service.close()
        except Exception as e:
            self.logger.warning(f"Performance test cleanup warning: {e}")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.performance
    async def test_concurrent_token_generation_100_users(self):
        """
        Test concurrent token generation for 100+ users.

        BVJ: Validates auth system can handle user growth without performance degradation.
        GitHub Issue #718: Performance testing scenarios (100+ concurrent users)
        """
        num_concurrent_users = 100
        start_time = time.time()

        async def generate_token_for_user(user_data):
            """Generate token for a single user with timing."""
            user_start = time.time()
            try:
                token = await self.jwt_service.create_access_token(
                    user_id=user_data['user_id'],
                    email=user_data['email'],
                    permissions=user_data['permissions']
                )
                generation_time = time.time() - user_start
                return {
                    'success': True,
                    'user_id': user_data['user_id'],
                    'token': token,
                    'generation_time': generation_time,
                    'error': None
                }
            except Exception as e:
                generation_time = time.time() - user_start
                return {
                    'success': False,
                    'user_id': user_data['user_id'],
                    'token': None,
                    'generation_time': generation_time,
                    'error': str(e)
                }

        # Execute concurrent token generation
        tasks = [generate_token_for_user(user) for user in self.user_pool[:num_concurrent_users]]
        results = await asyncio.gather(*tasks)

        total_time = time.time() - start_time

        # Analyze performance results
        successful_results = [r for r in results if r['success']]
        failed_results = [r for r in results if not r['success']]

        # Performance assertions
        success_rate = len(successful_results) / len(results)
        assert success_rate >= 0.95, f"Success rate {success_rate:.2%} below 95% threshold"

        generation_times = [r['generation_time'] for r in successful_results]
        avg_generation_time = statistics.mean(generation_times)
        max_generation_time = max(generation_times)

        # Performance SLA validation
        assert avg_generation_time < 1.0, f"Average generation time {avg_generation_time:.3f}s exceeds 1s SLA"
        assert max_generation_time < 5.0, f"Max generation time {max_generation_time:.3f}s exceeds 5s SLA"
        assert total_time < 30.0, f"Total concurrent operation time {total_time:.3f}s exceeds 30s limit"

        # Business impact validation
        tokens_per_second = len(successful_results) / total_time
        assert tokens_per_second >= 10, f"Throughput {tokens_per_second:.1f} tokens/s below business requirement"

        # Log performance metrics for monitoring
        self.logger.info(f"Performance Test Results - 100 Concurrent Users:")
        self.logger.info(f"  Success Rate: {success_rate:.2%}")
        self.logger.info(f"  Average Generation Time: {avg_generation_time:.3f}s")
        self.logger.info(f"  Max Generation Time: {max_generation_time:.3f}s")
        self.logger.info(f"  Total Time: {total_time:.3f}s")
        self.logger.info(f"  Throughput: {tokens_per_second:.1f} tokens/second")
        self.logger.info(f"  Failed Operations: {len(failed_results)}")

        # Store metrics for trending analysis
        self.performance_metrics['concurrent_operations'].append({
            'timestamp': datetime.now(timezone.utc),
            'users': num_concurrent_users,
            'success_rate': success_rate,
            'avg_time': avg_generation_time,
            'throughput': tokens_per_second
        })

        # Validate all tokens are unique and properly formatted
        tokens = [r['token'] for r in successful_results]
        assert len(set(tokens)) == len(tokens), "Duplicate tokens generated in concurrent test"

        for token in tokens[:10]:  # Sample validation
            assert len(token.split('.')) == 3, f"Invalid JWT format: {token[:50]}..."

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.performance
    async def test_concurrent_token_validation_load(self):
        """
        Test concurrent token validation under load.

        BVJ: Validates auth validation performance for active user sessions.
        """
        # Pre-generate tokens for validation testing
        num_tokens = 50
        pre_generated_tokens = []

        for i, user in enumerate(self.user_pool[:num_tokens]):
            token = await self.jwt_service.create_access_token(
                user_id=user['user_id'],
                email=user['email'],
                permissions=user['permissions']
            )
            pre_generated_tokens.append(token)

        # Concurrent validation test
        start_time = time.time()

        async def validate_token_with_timing(token):
            """Validate token with performance timing."""
            validation_start = time.time()
            try:
                is_valid = await self.jwt_service.validate_token(token)
                validation_time = time.time() - validation_start
                return {
                    'success': True,
                    'is_valid': is_valid,
                    'validation_time': validation_time,
                    'error': None
                }
            except Exception as e:
                validation_time = time.time() - validation_start
                return {
                    'success': False,
                    'is_valid': False,
                    'validation_time': validation_time,
                    'error': str(e)
                }

        # Test with multiple validation rounds (simulating real usage)
        validation_rounds = 5
        all_results = []

        for round_num in range(validation_rounds):
            tasks = [validate_token_with_timing(token) for token in pre_generated_tokens]
            round_results = await asyncio.gather(*tasks)
            all_results.extend(round_results)

            # Brief pause between rounds to simulate realistic usage
            await asyncio.sleep(0.1)

        total_time = time.time() - start_time

        # Performance analysis
        successful_validations = [r for r in all_results if r['success']]
        validation_times = [r['validation_time'] for r in successful_validations]

        success_rate = len(successful_validations) / len(all_results)
        avg_validation_time = statistics.mean(validation_times)
        max_validation_time = max(validation_times)
        validations_per_second = len(successful_validations) / total_time

        # Performance SLA assertions
        assert success_rate >= 0.98, f"Validation success rate {success_rate:.2%} below 98% threshold"
        assert avg_validation_time < 0.1, f"Average validation time {avg_validation_time:.3f}s exceeds 100ms SLA"
        assert max_validation_time < 1.0, f"Max validation time {max_validation_time:.3f}s exceeds 1s SLA"
        assert validations_per_second >= 50, f"Validation throughput {validations_per_second:.1f}/s below requirement"

        # All tokens should be valid
        valid_results = [r for r in successful_validations if r['is_valid']]
        assert len(valid_results) == len(successful_validations), "Some valid tokens failed validation"

        self.logger.info(f"Validation Performance Results:")
        self.logger.info(f"  Validations: {len(all_results)} (across {validation_rounds} rounds)")
        self.logger.info(f"  Success Rate: {success_rate:.2%}")
        self.logger.info(f"  Average Validation Time: {avg_validation_time:.3f}s")
        self.logger.info(f"  Throughput: {validations_per_second:.1f} validations/second")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.performance
    async def test_mixed_load_auth_operations(self):
        """
        Test mixed auth operations under concurrent load.

        BVJ: Simulates realistic production load with mixed operations.
        """
        num_concurrent_operations = 120

        async def mixed_auth_operation(operation_id):
            """Perform mixed auth operations with different types."""
            operation_start = time.time()
            operation_type = operation_id % 4  # 4 different operation types

            try:
                if operation_type == 0:
                    # Token generation
                    user = self.user_pool[operation_id % len(self.user_pool)]
                    token = await self.jwt_service.create_access_token(
                        user_id=user['user_id'],
                        email=user['email'],
                        permissions=user['permissions']
                    )
                    result_type = 'token_generation'
                    result_data = {'token_length': len(token)}

                elif operation_type == 1:
                    # Token validation (use a pre-existing token)
                    user = self.user_pool[0]  # Use first user's token
                    token = await self.jwt_service.create_access_token(
                        user_id=user['user_id'],
                        email=user['email'],
                        permissions=user['permissions']
                    )
                    is_valid = await self.jwt_service.validate_token(token)
                    result_type = 'token_validation'
                    result_data = {'is_valid': is_valid}

                elif operation_type == 2:
                    # Refresh token generation
                    user = self.user_pool[operation_id % len(self.user_pool)]
                    refresh_token = await self.jwt_service.create_refresh_token(
                        user_id=user['user_id'],
                        email=user['email']
                    )
                    result_type = 'refresh_generation'
                    result_data = {'refresh_token_length': len(refresh_token)}

                else:  # operation_type == 3
                    # Redis session storage
                    user = self.user_pool[operation_id % len(self.user_pool)]
                    session_key = f"session:{user['user_id']}:mixed_load_{operation_id}"
                    session_data = {
                        'user_id': user['user_id'],
                        'operation_id': operation_id,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    await self.redis_service.set(session_key, session_data, ex=300)
                    result_type = 'redis_operation'
                    result_data = {'session_key': session_key}

                operation_time = time.time() - operation_start
                return {
                    'success': True,
                    'operation_id': operation_id,
                    'operation_type': result_type,
                    'operation_time': operation_time,
                    'result_data': result_data,
                    'error': None
                }

            except Exception as e:
                operation_time = time.time() - operation_start
                return {
                    'success': False,
                    'operation_id': operation_id,
                    'operation_type': f'failed_{operation_type}',
                    'operation_time': operation_time,
                    'result_data': None,
                    'error': str(e)
                }

        # Execute mixed concurrent operations
        start_time = time.time()
        tasks = [mixed_auth_operation(i) for i in range(num_concurrent_operations)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Analyze results by operation type
        successful_results = [r for r in results if r['success']]
        failed_results = [r for r in results if not r['success']]

        operation_stats = {}
        for result in successful_results:
            op_type = result['operation_type']
            if op_type not in operation_stats:
                operation_stats[op_type] = []
            operation_stats[op_type].append(result['operation_time'])

        # Overall performance validation
        overall_success_rate = len(successful_results) / len(results)
        overall_throughput = len(successful_results) / total_time

        assert overall_success_rate >= 0.95, f"Overall success rate {overall_success_rate:.2%} below 95%"
        assert overall_throughput >= 20, f"Overall throughput {overall_throughput:.1f} ops/s below requirement"

        # Per-operation-type validation
        for op_type, times in operation_stats.items():
            avg_time = statistics.mean(times)
            max_time = max(times)
            assert avg_time < 2.0, f"{op_type} average time {avg_time:.3f}s exceeds 2s limit"
            assert max_time < 10.0, f"{op_type} max time {max_time:.3f}s exceeds 10s limit"

        # Business impact validation
        assert len(failed_results) < 5, f"Too many failures: {len(failed_results)} (max 5 allowed)"

        self.logger.info(f"Mixed Load Test Results:")
        self.logger.info(f"  Total Operations: {num_concurrent_operations}")
        self.logger.info(f"  Success Rate: {overall_success_rate:.2%}")
        self.logger.info(f"  Total Time: {total_time:.3f}s")
        self.logger.info(f"  Throughput: {overall_throughput:.1f} operations/second")
        self.logger.info(f"  Operation Types Performance:")

        for op_type, times in operation_stats.items():
            avg_time = statistics.mean(times)
            self.logger.info(f"    {op_type}: {len(times)} ops, avg {avg_time:.3f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.performance
    async def test_auth_system_scalability_limits(self):
        """
        Test auth system behavior at scalability limits.

        BVJ: Identifies system limits before they impact production users.
        """
        # Gradual load increase to find limits
        load_levels = [25, 50, 75, 100, 125, 150]
        scalability_results = []

        for load_level in load_levels:
            self.logger.info(f"Testing scalability at {load_level} concurrent users...")

            start_time = time.time()

            async def create_and_validate_token(user_index):
                """Create and immediately validate token."""
                user = self.user_pool[user_index % len(self.user_pool)]
                try:
                    # Create token
                    token = await self.jwt_service.create_access_token(
                        user_id=f"{user['user_id']}_scale_{load_level}",
                        email=user['email'],
                        permissions=user['permissions']
                    )

                    # Validate token
                    is_valid = await self.jwt_service.validate_token(token)

                    return {'success': True, 'valid': is_valid}
                except Exception as e:
                    return {'success': False, 'error': str(e)}

            # Execute current load level
            tasks = [create_and_validate_token(i) for i in range(load_level)]
            level_results = await asyncio.gather(*tasks)
            level_time = time.time() - start_time

            # Analyze this load level
            successful_ops = [r for r in level_results if r['success']]
            success_rate = len(successful_ops) / len(level_results)
            throughput = len(successful_ops) / level_time

            scalability_results.append({
                'load_level': load_level,
                'success_rate': success_rate,
                'throughput': throughput,
                'response_time': level_time,
                'successful_ops': len(successful_ops),
                'failed_ops': len(level_results) - len(successful_ops)
            })

            self.logger.info(f"  Load {load_level}: {success_rate:.2%} success, {throughput:.1f} ops/s")

            # Break if system starts degrading significantly
            if success_rate < 0.8:  # Below 80% success rate
                self.logger.warning(f"System degradation detected at {load_level} concurrent users")
                break

            # Brief cooldown between load levels
            await asyncio.sleep(1.0)

        # Validate scalability characteristics
        assert len(scalability_results) >= 4, "System failed too early in scalability testing"

        # Find the effective scalability limit
        effective_limits = [r for r in scalability_results if r['success_rate'] >= 0.95]
        assert len(effective_limits) >= 2, "System doesn't scale effectively beyond basic load"

        max_effective_load = max(r['load_level'] for r in effective_limits)
        assert max_effective_load >= 75, f"System scalability limit {max_effective_load} below business requirement"

        # Business requirement validation
        peak_throughput = max(r['throughput'] for r in scalability_results)
        assert peak_throughput >= 25, f"Peak throughput {peak_throughput:.1f} ops/s below business requirement"

        self.logger.info(f"Scalability Test Summary:")
        self.logger.info(f"  Max Effective Load: {max_effective_load} concurrent users")
        self.logger.info(f"  Peak Throughput: {peak_throughput:.1f} operations/second")
        self.logger.info(f"  Load Levels Tested: {len(scalability_results)}")

        # Store scalability metrics for capacity planning
        self.performance_metrics['scalability_test'] = {
            'timestamp': datetime.now(timezone.utc),
            'max_effective_load': max_effective_load,
            'peak_throughput': peak_throughput,
            'results': scalability_results
        }

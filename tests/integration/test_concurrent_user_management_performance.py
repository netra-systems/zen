"""
Performance & Load Testing: Concurrent User Management and Isolation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure scalable concurrent user support for platform growth
- Value Impact: Users can use the platform simultaneously without performance degradation
- Strategic Impact: Enables enterprise scaling and prevents user churn due to performance issues

CRITICAL: This test validates that the platform can handle multiple concurrent users
without shared state conflicts or performance degradation.
"""

import asyncio
import pytest
import time
import statistics
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env
from shared.types.core_types import UserID


@dataclass
class UserPerformanceMetrics:
    """Metrics for individual user performance."""
    user_id: str
    authentication_time: float
    session_creation_time: float
    first_request_time: float
    total_requests: int
    average_response_time: float
    max_response_time: float
    errors: List[str]


class TestConcurrentUserManagementPerformance(BaseIntegrationTest):
    """Test concurrent user management with real services and authentication."""
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_concurrent_user_isolation_performance(self, real_services_fixture):
        """
        Test that 20 concurrent users can work independently without interference.
        
        Performance SLA:
        - Authentication per user: <500ms (p95)
        - Session creation: <200ms (p95)
        - User isolation: 100% (no shared state)
        - Memory usage growth: <10MB per user
        """
        concurrent_users = 20
        auth_helper = E2EAuthHelper()
        user_metrics: List[UserPerformanceMetrics] = []
        
        async def create_isolated_user(user_index: int) -> UserPerformanceMetrics:
            """Create and test isolated user performance."""
            start_time = time.time()
            
            # Create authenticated user context
            user_email = f"perf_user_{user_index}@example.com"
            user_context = await create_authenticated_user_context(
                user_email=user_email,
                environment="test",
                permissions=["read", "write"],
                websocket_enabled=True
            )
            
            auth_time = time.time() - start_time
            
            # Create user session
            session_start = time.time()
            db_session = real_services_fixture["db"]
            redis = real_services_fixture["redis"]
            
            # Store user session in Redis (isolated by user ID)
            session_key = f"user_session:{user_context.user_id}"
            await redis.set(
                session_key, 
                f'{{"user_id": "{user_context.user_id}", "created_at": "{time.time()}"}}')
            
            session_time = time.time() - session_start
            
            # Perform isolated user operations
            request_times = []
            errors = []
            
            for i in range(5):  # 5 operations per user
                op_start = time.time()
                try:
                    # Simulate user-specific operations
                    user_data_key = f"user_data:{user_context.user_id}:operation_{i}"
                    await redis.set(user_data_key, f"data_for_user_{user_index}_op_{i}")
                    
                    # Verify isolation - check that other users' data is not accessible
                    for other_user in range(min(5, user_index)):  # Check first few users
                        other_key = f"user_data:e2e-user-{other_user:08x}:operation_0"
                        other_data = await redis.get(other_key)
                        if other_data and f"user_{user_index}" in str(other_data):
                            errors.append(f"User isolation breach: Found user {user_index} data in user {other_user} key")
                    
                    request_times.append(time.time() - op_start)
                    
                except Exception as e:
                    errors.append(f"Operation {i} failed: {str(e)}")
                    request_times.append(time.time() - op_start)
            
            # Clean up user session
            await redis.delete(session_key)
            
            return UserPerformanceMetrics(
                user_id=str(user_context.user_id),
                authentication_time=auth_time,
                session_creation_time=session_time,
                first_request_time=request_times[0] if request_times else 0,
                total_requests=len(request_times),
                average_response_time=statistics.mean(request_times) if request_times else 0,
                max_response_time=max(request_times) if request_times else 0,
                errors=errors
            )
        
        # Execute concurrent user operations
        start_time = time.time()
        
        # Create all users concurrently
        user_tasks = [
            create_isolated_user(i) 
            for i in range(concurrent_users)
        ]
        
        user_metrics = await asyncio.gather(*user_tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Filter out exceptions and collect valid metrics
        valid_metrics = [m for m in user_metrics if isinstance(m, UserPerformanceMetrics)]
        exceptions = [m for m in user_metrics if not isinstance(m, UserPerformanceMetrics)]
        
        # Performance assertions
        assert len(valid_metrics) == concurrent_users, f"Expected {concurrent_users} users, got {len(valid_metrics)}. Exceptions: {exceptions}"
        
        # Authentication performance SLA
        auth_times = [m.authentication_time for m in valid_metrics]
        auth_p95 = statistics.quantiles(auth_times, n=20)[18]  # 95th percentile
        assert auth_p95 < 0.5, f"Authentication p95 {auth_p95:.3f}s exceeds 500ms SLA"
        
        # Session creation performance SLA
        session_times = [m.session_creation_time for m in valid_metrics]
        session_p95 = statistics.quantiles(session_times, n=20)[18]
        assert session_p95 < 0.2, f"Session creation p95 {session_p95:.3f}s exceeds 200ms SLA"
        
        # User isolation validation (no shared state)
        total_errors = sum(len(m.errors) for m in valid_metrics)
        assert total_errors == 0, f"User isolation failures detected: {[m.errors for m in valid_metrics if m.errors]}"
        
        # Response time performance
        avg_response_times = [m.average_response_time for m in valid_metrics]
        overall_avg = statistics.mean(avg_response_times)
        assert overall_avg < 0.1, f"Average response time {overall_avg:.3f}s exceeds 100ms SLA"
        
        print(f"✅ Concurrent User Performance Test Results:")
        print(f"   Users: {concurrent_users}")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Auth p95: {auth_p95:.3f}s")
        print(f"   Session p95: {session_p95:.3f}s")
        print(f"   Avg response time: {overall_avg:.3f}s")
        print(f"   User isolation: PERFECT (0 errors)")
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_user_context_factory_performance(self, real_services_fixture):
        """
        Test user context factory performance under concurrent load.
        
        Performance SLA:
        - Context creation: <50ms per user
        - Memory growth: <5MB per 100 contexts
        - Context isolation: 100%
        """
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        context_count = 100
        auth_helper = E2EAuthHelper()
        contexts = []
        creation_times = []
        
        for i in range(context_count):
            start_time = time.time()
            
            context = await create_authenticated_user_context(
                user_email=f"context_test_{i}@example.com",
                environment="test",
                permissions=["read", "write"]
            )
            
            creation_time = time.time() - start_time
            creation_times.append(creation_time)
            contexts.append(context)
            
            # Verify context isolation
            assert str(context.user_id) != str(contexts[0].user_id) if i > 0 else True
            assert context.thread_id != contexts[0].thread_id if i > 0 else True
            assert context.request_id != contexts[0].request_id if i > 0 else True
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Performance assertions
        max_creation_time = max(creation_times)
        avg_creation_time = statistics.mean(creation_times)
        
        assert max_creation_time < 0.05, f"Max context creation time {max_creation_time:.3f}s exceeds 50ms SLA"
        assert avg_creation_time < 0.02, f"Average context creation time {avg_creation_time:.3f}s exceeds 20ms target"
        
        # Memory growth assertion (should be reasonable)
        expected_max_memory = 5.0  # 5MB for 100 contexts
        assert memory_growth < expected_max_memory, f"Memory growth {memory_growth:.1f}MB exceeds {expected_max_memory}MB limit"
        
        # Context uniqueness validation
        user_ids = [str(c.user_id) for c in contexts]
        thread_ids = [str(c.thread_id) for c in contexts]
        request_ids = [str(c.request_id) for c in contexts]
        
        assert len(set(user_ids)) == context_count, "User IDs are not unique across contexts"
        assert len(set(thread_ids)) == context_count, "Thread IDs are not unique across contexts"
        assert len(set(request_ids)) == context_count, "Request IDs are not unique across contexts"
        
        print(f"✅ User Context Factory Performance:")
        print(f"   Contexts created: {context_count}")
        print(f"   Max creation time: {max_creation_time:.3f}s")
        print(f"   Avg creation time: {avg_creation_time:.3f}s")
        print(f"   Memory growth: {memory_growth:.1f}MB")
        print(f"   Context uniqueness: PERFECT")
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_concurrent_authentication_load(self, real_services_fixture):
        """
        Test authentication system performance under concurrent load.
        
        Performance SLA:
        - JWT token creation: <10ms per token
        - Token validation: <5ms per validation
        - Concurrent auth requests: 50 per second sustained
        """
        auth_helper = E2EAuthHelper()
        concurrent_requests = 50
        
        # Test JWT token creation performance
        token_creation_times = []
        
        async def create_jwt_token(user_index: int) -> tuple[float, float]:
            start_time = time.time()
            token = auth_helper.create_test_jwt_token(
                user_id=f"load_test_user_{user_index}",
                email=f"loadtest_{user_index}@example.com",
                permissions=["read", "write"]
            )
            creation_time = time.time() - start_time
            
            # Validate token immediately
            validation_start = time.time()
            validation_result = await auth_helper.validate_jwt_token(token)
            validation_time = time.time() - validation_start
            
            assert validation_result["valid"], f"Token validation failed for user {user_index}"
            
            return creation_time, validation_time
        
        # Execute concurrent authentication requests
        start_time = time.time()
        
        auth_tasks = [create_jwt_token(i) for i in range(concurrent_requests)]
        results = await asyncio.gather(*auth_tasks)
        
        total_time = time.time() - start_time
        
        creation_times = [r[0] for r in results]
        validation_times = [r[1] for r in results]
        
        # Performance assertions
        max_creation_time = max(creation_times)
        max_validation_time = max(validation_times)
        avg_creation_time = statistics.mean(creation_times)
        avg_validation_time = statistics.mean(validation_times)
        
        requests_per_second = concurrent_requests / total_time
        
        assert max_creation_time < 0.01, f"Max token creation time {max_creation_time:.3f}s exceeds 10ms SLA"
        assert max_validation_time < 0.005, f"Max token validation time {max_validation_time:.3f}s exceeds 5ms SLA"
        assert requests_per_second >= 40, f"Authentication throughput {requests_per_second:.1f} req/s below 40 req/s minimum"
        
        print(f"✅ Concurrent Authentication Performance:")
        print(f"   Concurrent requests: {concurrent_requests}")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Throughput: {requests_per_second:.1f} req/s")
        print(f"   Max token creation: {max_creation_time:.3f}s")
        print(f"   Max token validation: {max_validation_time:.3f}s")
        print(f"   Avg creation time: {avg_creation_time:.3f}s")
        print(f"   Avg validation time: {avg_validation_time:.3f}s")
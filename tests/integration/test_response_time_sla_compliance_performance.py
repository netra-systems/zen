"""
Performance & Load Testing: Response Time Optimization and SLA Compliance

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure responsive user experience with predictable performance
- Value Impact: Users receive fast responses that meet or exceed expectations
- Strategic Impact: Response time SLAs are critical for user retention and enterprise adoption

CRITICAL: This test validates that all system operations meet defined SLA response times
under various load conditions and usage patterns.
"""

import asyncio
import pytest
import time
import statistics
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env


@dataclass
class ResponseTimeMetrics:
    """Response time metrics for performance analysis."""
    operation_name: str
    sample_count: int
    min_time: float
    max_time: float
    mean_time: float
    median_time: float
    p95_time: float
    p99_time: float
    std_deviation: float
    sla_threshold: float
    sla_compliance_rate: float
    failures: List[str] = field(default_factory=list)


@dataclass
class SLADefinition:
    """Service Level Agreement definition for an operation."""
    operation_name: str
    p95_threshold_ms: float
    p99_threshold_ms: float
    mean_threshold_ms: float
    success_rate_threshold: float = 0.99


class TestResponseTimeSLACompliance(BaseIntegrationTest):
    """Test response time SLAs across all system operations."""
    
    # Define SLA thresholds for different operations
    SLA_DEFINITIONS = {
        "authentication": SLADefinition("JWT Token Creation", 10, 20, 5, 0.999),
        "user_context_creation": SLADefinition("User Context Creation", 50, 100, 20, 0.99),
        "database_operation": SLADefinition("Database Query", 100, 200, 50, 0.99),
        "redis_operation": SLADefinition("Redis Operation", 10, 20, 5, 0.995),
        "websocket_connection": SLADefinition("WebSocket Connection", 2000, 5000, 1000, 0.95),
        "api_request": SLADefinition("API Request Processing", 500, 1000, 200, 0.98)
    }
    
    def _calculate_response_time_metrics(self, operation_name: str, response_times: List[float], 
                                       sla_threshold: float) -> ResponseTimeMetrics:
        """Calculate comprehensive response time metrics."""
        if not response_times:
            return ResponseTimeMetrics(
                operation_name=operation_name,
                sample_count=0,
                min_time=0, max_time=0, mean_time=0, median_time=0,
                p95_time=0, p99_time=0, std_deviation=0,
                sla_threshold=sla_threshold,
                sla_compliance_rate=0,
                failures=["No response time samples collected"]
            )
        
        # Convert to milliseconds for better readability
        times_ms = [t * 1000 for t in response_times]
        
        # Calculate percentiles
        percentiles = np.percentile(times_ms, [50, 95, 99])
        
        # Calculate SLA compliance
        compliant_responses = sum(1 for t in times_ms if t <= sla_threshold)
        sla_compliance_rate = compliant_responses / len(times_ms)
        
        return ResponseTimeMetrics(
            operation_name=operation_name,
            sample_count=len(times_ms),
            min_time=min(times_ms),
            max_time=max(times_ms),
            mean_time=statistics.mean(times_ms),
            median_time=percentiles[0],
            p95_time=percentiles[1],
            p99_time=percentiles[2],
            std_deviation=statistics.stdev(times_ms) if len(times_ms) > 1 else 0,
            sla_threshold=sla_threshold,
            sla_compliance_rate=sla_compliance_rate
        )
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_authentication_response_time_sla(self, real_services_fixture):
        """
        Test JWT authentication response time SLA compliance.
        
        SLA Requirements:
        - P95: <10ms
        - P99: <20ms
        - Mean: <5ms
        - Success rate: >99.9%
        """
        auth_helper = E2EAuthHelper()
        sla = self.SLA_DEFINITIONS["authentication"]
        
        sample_count = 1000
        response_times = []
        failures = []
        
        async def measure_authentication_time(iteration: int) -> float:
            """Measure JWT token creation time."""
            start_time = time.time()
            
            try:
                token = auth_helper.create_test_jwt_token(
                    user_id=f"sla_test_user_{iteration}",
                    email=f"slatest_{iteration}@example.com",
                    permissions=["read", "write"]
                )
                
                # Validate token to ensure it's properly formed
                validation_result = await auth_helper.validate_jwt_token(token)
                if not validation_result.get("valid", False):
                    failures.append(f"Token validation failed for iteration {iteration}")
                    return -1
                
                return time.time() - start_time
                
            except Exception as e:
                failures.append(f"Authentication failed for iteration {iteration}: {str(e)}")
                return -1
        
        # Execute authentication performance test
        tasks = [measure_authentication_time(i) for i in range(sample_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful measurements
        response_times = [r for r in results if isinstance(r, float) and r > 0]
        
        # Calculate metrics
        metrics = self._calculate_response_time_metrics(
            "JWT Authentication", response_times, sla.p95_threshold_ms
        )
        
        success_rate = len(response_times) / sample_count
        
        # SLA Assertions
        assert metrics.p95_time <= sla.p95_threshold_ms, f"P95 response time {metrics.p95_time:.1f}ms exceeds SLA {sla.p95_threshold_ms}ms"
        assert metrics.p99_time <= sla.p99_threshold_ms, f"P99 response time {metrics.p99_time:.1f}ms exceeds SLA {sla.p99_threshold_ms}ms"
        assert metrics.mean_time <= sla.mean_threshold_ms, f"Mean response time {metrics.mean_time:.1f}ms exceeds SLA {sla.mean_threshold_ms}ms"
        assert success_rate >= sla.success_rate_threshold, f"Success rate {success_rate:.3f} below SLA {sla.success_rate_threshold}"
        
        print(f" PASS:  Authentication Response Time SLA Results:")
        print(f"   Samples: {metrics.sample_count}/{sample_count}")
        print(f"   Success rate: {success_rate:.3f} (SLA: {sla.success_rate_threshold})")
        print(f"   Mean: {metrics.mean_time:.1f}ms (SLA: {sla.mean_threshold_ms}ms)")
        print(f"   P95: {metrics.p95_time:.1f}ms (SLA: {sla.p95_threshold_ms}ms)")
        print(f"   P99: {metrics.p99_time:.1f}ms (SLA: {sla.p99_threshold_ms}ms)")
        print(f"   Max: {metrics.max_time:.1f}ms")
        print(f"   Std Dev: {metrics.std_deviation:.1f}ms")
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_user_context_creation_sla(self, real_services_fixture):
        """
        Test user context creation response time SLA compliance.
        
        SLA Requirements:
        - P95: <50ms
        - P99: <100ms
        - Mean: <20ms
        - Success rate: >99%
        """
        sla = self.SLA_DEFINITIONS["user_context_creation"]
        sample_count = 500
        response_times = []
        failures = []
        
        async def measure_context_creation_time(iteration: int) -> float:
            """Measure user context creation time."""
            start_time = time.time()
            
            try:
                context = await create_authenticated_user_context(
                    user_email=f"sla_context_{iteration}@example.com",
                    environment="test",
                    permissions=["read", "write", "execute"],
                    websocket_enabled=True
                )
                
                # Verify context is properly created
                if not context.user_id or not context.thread_id or not context.request_id:
                    failures.append(f"Context creation incomplete for iteration {iteration}")
                    return -1
                
                return time.time() - start_time
                
            except Exception as e:
                failures.append(f"Context creation failed for iteration {iteration}: {str(e)}")
                return -1
        
        # Execute context creation performance test
        tasks = [measure_context_creation_time(i) for i in range(sample_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful measurements
        response_times = [r for r in results if isinstance(r, float) and r > 0]
        
        # Calculate metrics
        metrics = self._calculate_response_time_metrics(
            "User Context Creation", response_times, sla.p95_threshold_ms
        )
        
        success_rate = len(response_times) / sample_count
        
        # SLA Assertions
        assert metrics.p95_time <= sla.p95_threshold_ms, f"P95 response time {metrics.p95_time:.1f}ms exceeds SLA {sla.p95_threshold_ms}ms"
        assert metrics.p99_time <= sla.p99_threshold_ms, f"P99 response time {metrics.p99_time:.1f}ms exceeds SLA {sla.p99_threshold_ms}ms"
        assert metrics.mean_time <= sla.mean_threshold_ms, f"Mean response time {metrics.mean_time:.1f}ms exceeds SLA {sla.mean_threshold_ms}ms"
        assert success_rate >= sla.success_rate_threshold, f"Success rate {success_rate:.3f} below SLA {sla.success_rate_threshold}"
        
        print(f" PASS:  User Context Creation SLA Results:")
        print(f"   Samples: {metrics.sample_count}/{sample_count}")
        print(f"   Success rate: {success_rate:.3f} (SLA: {sla.success_rate_threshold})")
        print(f"   Mean: {metrics.mean_time:.1f}ms (SLA: {sla.mean_threshold_ms}ms)")
        print(f"   P95: {metrics.p95_time:.1f}ms (SLA: {sla.p95_threshold_ms}ms)")
        print(f"   P99: {metrics.p99_time:.1f}ms (SLA: {sla.p99_threshold_ms}ms)")
        print(f"   Max: {metrics.max_time:.1f}ms")
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_database_operations_sla(self, real_services_fixture):
        """
        Test database operations response time SLA compliance.
        
        SLA Requirements:
        - P95: <100ms
        - P99: <200ms
        - Mean: <50ms
        - Success rate: >99%
        """
        sla = self.SLA_DEFINITIONS["database_operation"]
        sample_count = 300
        response_times = []
        failures = []
        
        db = real_services_fixture["db"]
        
        async def measure_database_operation_time(iteration: int) -> float:
            """Measure database operation time."""
            start_time = time.time()
            
            try:
                # Simulate typical database operations
                test_key = f"sla_test_{iteration}"
                test_value = f"test_data_for_iteration_{iteration}_{time.time()}"
                
                # Use raw SQL for consistent timing
                await db.execute(f"SELECT 1 as test_column")
                
                return time.time() - start_time
                
            except Exception as e:
                failures.append(f"Database operation failed for iteration {iteration}: {str(e)}")
                return -1
        
        # Execute database performance test
        tasks = [measure_database_operation_time(i) for i in range(sample_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful measurements
        response_times = [r for r in results if isinstance(r, float) and r > 0]
        
        # Calculate metrics
        metrics = self._calculate_response_time_metrics(
            "Database Operations", response_times, sla.p95_threshold_ms
        )
        
        success_rate = len(response_times) / sample_count
        
        # SLA Assertions
        assert metrics.p95_time <= sla.p95_threshold_ms, f"P95 response time {metrics.p95_time:.1f}ms exceeds SLA {sla.p95_threshold_ms}ms"
        assert metrics.p99_time <= sla.p99_threshold_ms, f"P99 response time {metrics.p99_time:.1f}ms exceeds SLA {sla.p99_threshold_ms}ms"
        assert metrics.mean_time <= sla.mean_threshold_ms, f"Mean response time {metrics.mean_time:.1f}ms exceeds SLA {sla.mean_threshold_ms}ms"
        assert success_rate >= sla.success_rate_threshold, f"Success rate {success_rate:.3f} below SLA {sla.success_rate_threshold}"
        
        print(f" PASS:  Database Operations SLA Results:")
        print(f"   Samples: {metrics.sample_count}/{sample_count}")
        print(f"   Success rate: {success_rate:.3f} (SLA: {sla.success_rate_threshold})")
        print(f"   Mean: {metrics.mean_time:.1f}ms (SLA: {sla.mean_threshold_ms}ms)")
        print(f"   P95: {metrics.p95_time:.1f}ms (SLA: {sla.p95_threshold_ms}ms)")
        print(f"   P99: {metrics.p99_time:.1f}ms (SLA: {sla.p99_threshold_ms}ms)")
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_redis_operations_sla(self, real_services_fixture):
        """
        Test Redis operations response time SLA compliance.
        
        SLA Requirements:
        - P95: <10ms
        - P99: <20ms
        - Mean: <5ms
        - Success rate: >99.5%
        """
        sla = self.SLA_DEFINITIONS["redis_operation"]
        sample_count = 500
        response_times = []
        failures = []
        
        redis = real_services_fixture["redis"]
        
        async def measure_redis_operation_time(iteration: int) -> float:
            """Measure Redis operation time."""
            start_time = time.time()
            
            try:
                # Test Redis SET and GET operations
                test_key = f"sla_redis_test_{iteration}"
                test_value = f"redis_test_data_{iteration}_{time.time()}"
                
                # SET operation
                await redis.set(test_key, test_value, ex=60)  # 60s expiry
                
                # GET operation to verify
                retrieved_value = await redis.get(test_key)
                
                if retrieved_value != test_value:
                    failures.append(f"Redis data integrity failed for iteration {iteration}")
                    return -1
                
                return time.time() - start_time
                
            except Exception as e:
                failures.append(f"Redis operation failed for iteration {iteration}: {str(e)}")
                return -1
        
        # Execute Redis performance test
        tasks = [measure_redis_operation_time(i) for i in range(sample_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful measurements
        response_times = [r for r in results if isinstance(r, float) and r > 0]
        
        # Calculate metrics
        metrics = self._calculate_response_time_metrics(
            "Redis Operations", response_times, sla.p95_threshold_ms
        )
        
        success_rate = len(response_times) / sample_count
        
        # SLA Assertions
        assert metrics.p95_time <= sla.p95_threshold_ms, f"P95 response time {metrics.p95_time:.1f}ms exceeds SLA {sla.p95_threshold_ms}ms"
        assert metrics.p99_time <= sla.p99_threshold_ms, f"P99 response time {metrics.p99_time:.1f}ms exceeds SLA {sla.p99_threshold_ms}ms"
        assert metrics.mean_time <= sla.mean_threshold_ms, f"Mean response time {metrics.mean_time:.1f}ms exceeds SLA {sla.mean_threshold_ms}ms"
        assert success_rate >= sla.success_rate_threshold, f"Success rate {success_rate:.3f} below SLA {sla.success_rate_threshold}"
        
        print(f" PASS:  Redis Operations SLA Results:")
        print(f"   Samples: {metrics.sample_count}/{sample_count}")
        print(f"   Success rate: {success_rate:.3f} (SLA: {sla.success_rate_threshold})")
        print(f"   Mean: {metrics.mean_time:.1f}ms (SLA: {sla.mean_threshold_ms}ms)")
        print(f"   P95: {metrics.p95_time:.1f}ms (SLA: {sla.p95_threshold_ms}ms)")
        print(f"   P99: {metrics.p99_time:.1f}ms (SLA: {sla.p99_threshold_ms}ms)")
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_end_to_end_operation_sla_compliance(self, real_services_fixture):
        """
        Test end-to-end operation response time SLA across all components.
        
        SLA Requirements (Combined Operations):
        - P95: <200ms for full user workflow
        - P99: <500ms for full user workflow  
        - Mean: <100ms for full user workflow
        - Success rate: >97%
        """
        sample_count = 100  # Smaller sample for complex E2E operations
        response_times = []
        failures = []
        
        auth_helper = E2EAuthHelper()
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        async def measure_end_to_end_operation(iteration: int) -> float:
            """Measure complete end-to-end operation time."""
            start_time = time.time()
            
            try:
                # 1. Create authenticated user context
                context = await create_authenticated_user_context(
                    user_email=f"e2e_sla_{iteration}@example.com",
                    environment="test",
                    permissions=["read", "write"]
                )
                
                # 2. Perform database operation
                await db.execute("SELECT 1 as health_check")
                
                # 3. Perform Redis operation
                session_key = f"e2e_session:{context.user_id}"
                session_data = {
                    "user_id": str(context.user_id),
                    "thread_id": str(context.thread_id),
                    "created_at": time.time()
                }
                await redis.set(session_key, json.dumps(session_data), ex=300)
                
                # 4. Verify session retrieval
                retrieved_session = await redis.get(session_key)
                if not retrieved_session:
                    failures.append(f"E2E session retrieval failed for iteration {iteration}")
                    return -1
                
                # 5. JWT token validation
                token = auth_helper.create_test_jwt_token(
                    user_id=str(context.user_id),
                    email=f"e2e_sla_{iteration}@example.com"
                )
                validation_result = await auth_helper.validate_jwt_token(token)
                
                if not validation_result.get("valid", False):
                    failures.append(f"E2E token validation failed for iteration {iteration}")
                    return -1
                
                # Clean up
                await redis.delete(session_key)
                
                return time.time() - start_time
                
            except Exception as e:
                failures.append(f"E2E operation failed for iteration {iteration}: {str(e)}")
                return -1
        
        # Execute end-to-end performance test
        tasks = [measure_end_to_end_operation(i) for i in range(sample_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful measurements
        response_times = [r for r in results if isinstance(r, float) and r > 0]
        
        # Calculate metrics with custom SLA thresholds for E2E
        metrics = self._calculate_response_time_metrics(
            "End-to-End Operations", response_times, 200  # 200ms P95 threshold
        )
        
        success_rate = len(response_times) / sample_count
        
        # E2E SLA Assertions
        assert metrics.p95_time <= 200, f"E2E P95 response time {metrics.p95_time:.1f}ms exceeds 200ms SLA"
        assert metrics.p99_time <= 500, f"E2E P99 response time {metrics.p99_time:.1f}ms exceeds 500ms SLA"
        assert metrics.mean_time <= 100, f"E2E mean response time {metrics.mean_time:.1f}ms exceeds 100ms SLA"
        assert success_rate >= 0.97, f"E2E success rate {success_rate:.3f} below 97% SLA"
        
        print(f" PASS:  End-to-End Operation SLA Results:")
        print(f"   Samples: {metrics.sample_count}/{sample_count}")
        print(f"   Success rate: {success_rate:.3f} (SLA: 97%)")
        print(f"   Mean: {metrics.mean_time:.1f}ms (SLA: 100ms)")
        print(f"   P95: {metrics.p95_time:.1f}ms (SLA: 200ms)")
        print(f"   P99: {metrics.p99_time:.1f}ms (SLA: 500ms)")
        print(f"   Max: {metrics.max_time:.1f}ms")
        print(f"   Failed operations: {len(failures)}")
        
        if len(failures) > 3:  # Show sample failures for debugging
            print(f"   Sample failures: {failures[:3]}")
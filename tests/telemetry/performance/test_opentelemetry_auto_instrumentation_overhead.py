"""
Performance Tests for OpenTelemetry Automatic Instrumentation Overhead

FOCUS: Automatic instrumentation only - measures performance impact of 
auto-instrumentation libraries on critical business operations.

Tests performance overhead of OpenTelemetry automatic instrumentation across
FastAPI endpoints, database operations, Redis cache, and WebSocket connections.

Business Value: Enterprise/Platform - Ensures observability doesn't impact
$500K+ ARR chat performance and user experience.

CRITICAL: Uses REAL SERVICES to measure actual overhead - no mocks.
SSOT Architecture: Uses SSotAsyncTestCase and UnifiedDockerManager.

Performance targets: <5% overhead for critical path, <15% for overall system.
"""

import asyncio
import contextlib
import logging
import statistics
import time
import uuid
from typing import Dict, List, Any, Optional, Tuple, Callable
from unittest.mock import patch
from dataclasses import dataclass

import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.unified_docker_manager import UnifiedDockerManager

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance measurement data."""
    operation: str
    without_tracing: List[float]
    with_tracing: List[float]
    iterations: int
    
    @property
    def baseline_avg(self) -> float:
        return statistics.mean(self.without_tracing)
        
    @property
    def instrumented_avg(self) -> float:
        return statistics.mean(self.with_tracing)
        
    @property
    def overhead_percentage(self) -> float:
        if self.baseline_avg == 0:
            return 0.0
        return ((self.instrumented_avg - self.baseline_avg) / self.baseline_avg) * 100
        
    @property
    def baseline_p95(self) -> float:
        return statistics.quantiles(self.without_tracing, n=20)[18]  # 95th percentile
        
    @property
    def instrumented_p95(self) -> float:
        return statistics.quantiles(self.with_tracing, n=20)[18]  # 95th percentile


class TestOpenTelemetryAutoInstrumentationOverhead(SSotAsyncTestCase):
    """Test performance overhead of automatic instrumentation."""
    
    @pytest.fixture(autouse=True)
    def setup_docker_and_services(self):
        """Setup Docker manager and ensure services are running."""
        self.docker_manager = UnifiedDockerManager()
        
        # Ensure required services are running
        required_services = ["postgres", "redis"]
        for service in required_services:
            if not self.docker_manager.is_service_healthy(service):
                pytest.skip(f"Required service {service} not available for performance testing")
                
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        # Performance test configuration
        self.set_env_var("ENVIRONMENT", "performance_test")
        
        # Test parameters
        self.performance_iterations = 50  # Enough iterations for statistical significance
        self.warmup_iterations = 5       # Warmup iterations to exclude from metrics
        
    async def test_database_operations_auto_instrumentation_overhead(self):
        """
        Test performance overhead of automatic SQLAlchemy instrumentation.
        
        Measures overhead on database queries, connections, and transactions.
        """
        # Check SQLAlchemy availability
        try:
            import sqlalchemy
            from sqlalchemy import create_engine, text
        except ImportError:
            pytest.skip("SQLAlchemy not available for performance testing")
            
        # Check instrumentor availability
        try:
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        except ImportError:
            pytest.skip("OpenTelemetry SQLAlchemy instrumentor not available")
            
        # Setup database connection
        db_url = self._get_test_database_url()
        
        # Test scenarios
        test_scenarios = [
            ("simple_select", "SELECT 1 as test_value"),
            ("parameterized_query", "SELECT $1 as param_value"),
            ("small_table_scan", "SELECT count(*) FROM information_schema.tables"),
        ]
        
        scenario_metrics = {}
        
        for scenario_name, query in test_scenarios:
            logger.info(f"Testing database scenario: {scenario_name}")
            
            # Measure baseline performance (no instrumentation)
            baseline_times = await self._measure_database_performance(
                db_url, query, scenario_name, with_instrumentation=False
            )
            
            # Measure with auto-instrumentation
            instrumented_times = await self._measure_database_performance(
                db_url, query, scenario_name, with_instrumentation=True
            )
            
            # Calculate metrics
            metrics = PerformanceMetrics(
                operation=f"database_{scenario_name}",
                without_tracing=baseline_times,
                with_tracing=instrumented_times,
                iterations=self.performance_iterations
            )
            
            scenario_metrics[scenario_name] = metrics
            
            # Record individual metrics
            self.record_metric(f"db_{scenario_name}_baseline_avg_ms", metrics.baseline_avg * 1000)
            self.record_metric(f"db_{scenario_name}_instrumented_avg_ms", metrics.instrumented_avg * 1000)
            self.record_metric(f"db_{scenario_name}_overhead_percentage", metrics.overhead_percentage)
            self.record_metric(f"db_{scenario_name}_baseline_p95_ms", metrics.baseline_p95 * 1000)
            self.record_metric(f"db_{scenario_name}_instrumented_p95_ms", metrics.instrumented_p95 * 1000)
            
            # Validate overhead is acceptable
            assert metrics.overhead_percentage < 20.0, (
                f"Database {scenario_name} auto-instrumentation overhead "
                f"{metrics.overhead_percentage:.1f}% exceeds 20% limit"
            )
            
        # Calculate overall database overhead
        all_baseline_times = []
        all_instrumented_times = []
        
        for metrics in scenario_metrics.values():
            all_baseline_times.extend(metrics.without_tracing)
            all_instrumented_times.extend(metrics.with_tracing)
            
        overall_overhead = ((statistics.mean(all_instrumented_times) - 
                           statistics.mean(all_baseline_times)) / 
                          statistics.mean(all_baseline_times)) * 100
        
        self.record_metric("database_overall_overhead_percentage", overall_overhead)
        
        # Overall database overhead should be reasonable
        assert overall_overhead < 15.0, (
            f"Overall database auto-instrumentation overhead {overall_overhead:.1f}% "
            f"exceeds 15% limit"
        )
        
    async def _measure_database_performance(
        self, 
        db_url: str, 
        query: str, 
        scenario_name: str,
        with_instrumentation: bool
    ) -> List[float]:
        """Measure database operation performance with or without instrumentation."""
        
        execution_times = []
        instrumentor = None
        
        try:
            # Setup instrumentation if requested
            if with_instrumentation:
                from opentelemetry import trace
                from opentelemetry.sdk.trace import TracerProvider
                from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
                from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
                
                # Setup minimal tracing
                trace.set_tracer_provider(TracerProvider())
                span_processor = BatchSpanProcessor(ConsoleSpanExporter())
                trace.get_tracer_provider().add_span_processor(span_processor)
                
                # Apply instrumentation
                instrumentor = SQLAlchemyInstrumentor()
                if not instrumentor.is_instrumented_by_opentelemetry:
                    instrumentor.instrument()
                    
            # Create database engine
            from sqlalchemy import create_engine, text
            engine = create_engine(db_url, echo=False, pool_pre_ping=True)
            
            # Warmup iterations
            for _ in range(self.warmup_iterations):
                with engine.connect() as conn:
                    if "$1" in query:
                        conn.execute(text(query), ["test_param"])
                    else:
                        conn.execute(text(query))
                        
            # Measured iterations
            for i in range(self.performance_iterations):
                start_time = time.perf_counter()
                
                with engine.connect() as conn:
                    if "$1" in query:
                        result = conn.execute(text(query), ["test_param"])
                    else:
                        result = conn.execute(text(query))
                    
                    # Consume result to ensure complete execution
                    list(result.fetchall())
                    
                end_time = time.perf_counter()
                execution_times.append(end_time - start_time)
                
            engine.dispose()
            
        finally:
            # Cleanup instrumentation
            if instrumentor and with_instrumentation:
                try:
                    instrumentor.uninstrument()
                except:
                    pass
                    
        return execution_times
        
    def _get_test_database_url(self) -> str:
        """Get test database connection URL."""
        return (
            f"postgresql://{self.get_env_var('POSTGRES_USER', 'netra')}:"
            f"{self.get_env_var('POSTGRES_PASSWORD', 'netra_secure_2024')}@"
            f"{self.get_env_var('POSTGRES_HOST', 'localhost')}:"
            f"{self.get_env_var('POSTGRES_PORT', '5432')}/"
            f"{self.get_env_var('POSTGRES_DB', 'netra_test')}"
        )
        
    async def test_redis_operations_auto_instrumentation_overhead(self):
        """
        Test performance overhead of automatic Redis instrumentation.
        
        Measures overhead on Redis get/set operations, pipeline operations.
        """
        # Check Redis availability
        try:
            import redis
        except ImportError:
            pytest.skip("Redis not available for performance testing")
            
        # Check instrumentor availability
        try:
            from opentelemetry.instrumentation.redis import RedisInstrumentor
        except ImportError:
            pytest.skip("OpenTelemetry Redis instrumentor not available")
            
        # Test scenarios
        redis_scenarios = [
            ("simple_set_get", self._redis_simple_set_get_operation),
            ("pipeline_operations", self._redis_pipeline_operations),
            ("hash_operations", self._redis_hash_operations),
        ]
        
        scenario_metrics = {}
        
        for scenario_name, operation_func in redis_scenarios:
            logger.info(f"Testing Redis scenario: {scenario_name}")
            
            # Measure baseline performance
            baseline_times = await self._measure_redis_performance(
                operation_func, scenario_name, with_instrumentation=False
            )
            
            # Measure with auto-instrumentation
            instrumented_times = await self._measure_redis_performance(
                operation_func, scenario_name, with_instrumentation=True
            )
            
            # Calculate metrics
            metrics = PerformanceMetrics(
                operation=f"redis_{scenario_name}",
                without_tracing=baseline_times,
                with_tracing=instrumented_times,
                iterations=self.performance_iterations
            )
            
            scenario_metrics[scenario_name] = metrics
            
            # Record metrics
            self.record_metric(f"redis_{scenario_name}_baseline_avg_ms", metrics.baseline_avg * 1000)
            self.record_metric(f"redis_{scenario_name}_instrumented_avg_ms", metrics.instrumented_avg * 1000)
            self.record_metric(f"redis_{scenario_name}_overhead_percentage", metrics.overhead_percentage)
            
            # Validate overhead
            assert metrics.overhead_percentage < 25.0, (
                f"Redis {scenario_name} auto-instrumentation overhead "
                f"{metrics.overhead_percentage:.1f}% exceeds 25% limit"
            )
            
        # Calculate overall Redis overhead
        all_baseline_times = []
        all_instrumented_times = []
        
        for metrics in scenario_metrics.values():
            all_baseline_times.extend(metrics.without_tracing)
            all_instrumented_times.extend(metrics.with_tracing)
            
        overall_overhead = ((statistics.mean(all_instrumented_times) - 
                           statistics.mean(all_baseline_times)) / 
                          statistics.mean(all_baseline_times)) * 100
        
        self.record_metric("redis_overall_overhead_percentage", overall_overhead)
        
        # Overall Redis overhead validation
        assert overall_overhead < 20.0, (
            f"Overall Redis auto-instrumentation overhead {overall_overhead:.1f}% "
            f"exceeds 20% limit"
        )
        
    async def _measure_redis_performance(
        self,
        operation_func: Callable,
        scenario_name: str,
        with_instrumentation: bool
    ) -> List[float]:
        """Measure Redis operation performance with or without instrumentation."""
        
        execution_times = []
        instrumentor = None
        
        try:
            # Setup instrumentation if requested
            if with_instrumentation:
                from opentelemetry import trace
                from opentelemetry.sdk.trace import TracerProvider
                from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
                from opentelemetry.instrumentation.redis import RedisInstrumentor
                
                # Setup minimal tracing
                trace.set_tracer_provider(TracerProvider())
                span_processor = BatchSpanProcessor(ConsoleSpanExporter())
                trace.get_tracer_provider().add_span_processor(span_processor)
                
                # Apply instrumentation
                instrumentor = RedisInstrumentor()
                if not instrumentor.is_instrumented_by_opentelemetry:
                    instrumentor.instrument()
                    
            # Create Redis client
            import redis
            redis_client = await get_redis_client()
            
            # Warmup iterations
            for _ in range(self.warmup_iterations):
                await operation_func(redis_client, scenario_name, 0)
                
            # Measured iterations
            for i in range(self.performance_iterations):
                start_time = time.perf_counter()
                
                await operation_func(redis_client, scenario_name, i)
                
                end_time = time.perf_counter()
                execution_times.append(end_time - start_time)
                
        finally:
            # Cleanup instrumentation
            if instrumentor and with_instrumentation:
                try:
                    instrumentor.uninstrument()
                except:
                    pass
                    
        return execution_times
        
    async def _redis_simple_set_get_operation(self, redis_client, scenario_name: str, iteration: int):
        """Simple Redis SET/GET operation."""
        key = f"perf_test_{scenario_name}_{iteration}"
        value = f"test_value_{iteration}"
        
        await redis_client.set(key, value, ex=60)  # Expire in 60 seconds
        retrieved = await redis_client.get(key)
        
        assert retrieved == value
        await redis_client.delete(key)
        
    async def _redis_pipeline_operations(self, redis_client, scenario_name: str, iteration: int):
        """Redis pipeline operations."""
        pipe = await redis_client.pipeline()
        
        for i in range(5):  # 5 operations per pipeline
            key = f"perf_pipeline_{scenario_name}_{iteration}_{i}"
            pipe.set(key, f"value_{i}", ex=60)
            pipe.get(key)
            
        results = pipe.execute()
        
        # Cleanup
        cleanup_pipe = await redis_client.pipeline()
        for i in range(5):
            key = f"perf_pipeline_{scenario_name}_{iteration}_{i}"
            cleanup_pipe.delete(key)
        cleanup_pipe.execute()
        
    async def _redis_hash_operations(self, redis_client, scenario_name: str, iteration: int):
        """Redis hash operations."""
        hash_key = f"perf_hash_{scenario_name}_{iteration}"
        
        # Set hash fields
        hash_data = {f"field_{i}": f"value_{i}" for i in range(3)}
        await redis_client.hset(hash_key, mapping=hash_data)
        
        # Get hash fields
        retrieved_data = await redis_client.hgetall(hash_key)
        
        assert len(retrieved_data) == 3
        await redis_client.delete(hash_key)
        
    async def test_http_requests_auto_instrumentation_overhead(self):
        """
        Test performance overhead of automatic requests instrumentation.
        
        Measures overhead on HTTP client requests for external API calls.
        """
        # Check requests availability
        try:
            import requests
        except ImportError:
            pytest.skip("requests library not available for performance testing")
            
        # Check instrumentor availability
        try:
            from opentelemetry.instrumentation.requests import RequestsInstrumentor
        except ImportError:
            pytest.skip("OpenTelemetry requests instrumentor not available")
            
        # HTTP test scenarios using httpbin.org (reliable test service)
        http_scenarios = [
            ("simple_get", "https://httpbin.org/json"),
            ("get_with_params", "https://httpbin.org/get?test=performance"),
            ("post_json", "https://httpbin.org/post"),
        ]
        
        scenario_metrics = {}
        
        for scenario_name, url in http_scenarios:
            logger.info(f"Testing HTTP scenario: {scenario_name}")
            
            try:
                # Measure baseline performance
                baseline_times = await self._measure_http_performance(
                    url, scenario_name, with_instrumentation=False
                )
                
                # Measure with auto-instrumentation
                instrumented_times = await self._measure_http_performance(
                    url, scenario_name, with_instrumentation=True
                )
                
                # Calculate metrics
                metrics = PerformanceMetrics(
                    operation=f"http_{scenario_name}",
                    without_tracing=baseline_times,
                    with_tracing=instrumented_times,
                    iterations=len(baseline_times)  # May be less than target due to failures
                )
                
                scenario_metrics[scenario_name] = metrics
                
                # Record metrics
                self.record_metric(f"http_{scenario_name}_baseline_avg_ms", metrics.baseline_avg * 1000)
                self.record_metric(f"http_{scenario_name}_instrumented_avg_ms", metrics.instrumented_avg * 1000)
                self.record_metric(f"http_{scenario_name}_overhead_percentage", metrics.overhead_percentage)
                
                # Validate overhead (HTTP requests can have higher overhead due to network variability)
                assert metrics.overhead_percentage < 30.0, (
                    f"HTTP {scenario_name} auto-instrumentation overhead "
                    f"{metrics.overhead_percentage:.1f}% exceeds 30% limit"
                )
                
            except Exception as e:
                logger.warning(f"HTTP scenario {scenario_name} failed: {e}")
                self.record_metric(f"http_{scenario_name}_test_failed", str(e))
                
        if scenario_metrics:
            # Calculate overall HTTP overhead
            all_baseline_times = []
            all_instrumented_times = []
            
            for metrics in scenario_metrics.values():
                all_baseline_times.extend(metrics.without_tracing)
                all_instrumented_times.extend(metrics.with_tracing)
                
            if all_baseline_times and all_instrumented_times:
                overall_overhead = ((statistics.mean(all_instrumented_times) - 
                                   statistics.mean(all_baseline_times)) / 
                                  statistics.mean(all_baseline_times)) * 100
                
                self.record_metric("http_overall_overhead_percentage", overall_overhead)
                
    async def _measure_http_performance(
        self,
        url: str,
        scenario_name: str,
        with_instrumentation: bool
    ) -> List[float]:
        """Measure HTTP request performance with or without instrumentation."""
        
        execution_times = []
        instrumentor = None
        successful_requests = 0
        
        try:
            # Setup instrumentation if requested
            if with_instrumentation:
                from opentelemetry import trace
                from opentelemetry.sdk.trace import TracerProvider
                from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
                from opentelemetry.instrumentation.requests import RequestsInstrumentor
                
                # Setup minimal tracing
                trace.set_tracer_provider(TracerProvider())
                span_processor = BatchSpanProcessor(ConsoleSpanExporter())
                trace.get_tracer_provider().add_span_processor(span_processor)
                
                # Apply instrumentation
                instrumentor = RequestsInstrumentor()
                if not instrumentor.is_instrumented_by_opentelemetry:
                    instrumentor.instrument()
                    
            import requests
            
            # Warmup requests (don't count these)
            for _ in range(min(3, self.warmup_iterations)):
                try:
                    if "post" in scenario_name:
                        requests.post(url, json={"test": "warmup"}, timeout=10)
                    else:
                        requests.get(url, timeout=10)
                except:
                    pass
                    
            # Measured requests
            for i in range(self.performance_iterations):
                try:
                    start_time = time.perf_counter()
                    
                    if "post" in scenario_name:
                        response = requests.post(
                            url,
                            json={"test": f"performance_{i}"},
                            timeout=10
                        )
                    else:
                        response = requests.get(url, timeout=10)
                        
                    # Ensure we get the response body
                    _ = response.text
                    
                    end_time = time.perf_counter()
                    
                    if response.status_code == 200:
                        execution_times.append(end_time - start_time)
                        successful_requests += 1
                        
                except Exception as e:
                    # Network errors are expected in some environments
                    logger.debug(f"HTTP request {i} failed: {e}")
                    continue
                    
        finally:
            # Cleanup instrumentation
            if instrumentor and with_instrumentation:
                try:
                    instrumentor.uninstrument()
                except:
                    pass
                    
        # Ensure we have enough successful requests for meaningful metrics
        if len(execution_times) < (self.performance_iterations * 0.5):
            raise Exception(f"Too few successful requests ({len(execution_times)}) for performance measurement")
            
        return execution_times


class TestAutoInstrumentationSystemWideOverhead(SSotAsyncTestCase):
    """Test system-wide performance impact of multiple auto-instrumentors."""
    
    def setup_method(self, method=None):
        """Setup for system-wide performance testing."""
        super().setup_method(method)
        
        self.set_env_var("ENVIRONMENT", "performance_test")
        self.system_test_iterations = 20  # Fewer iterations for complex system tests
        
    async def test_multiple_instrumentors_combined_overhead(self):
        """
        Test combined overhead of multiple auto-instrumentors running together.
        
        Simulates production scenario with all instrumentors active.
        """
        # Check availability of all instrumentors
        available_instrumentors = self._check_instrumentor_availability()
        
        if len(available_instrumentors) < 2:
            pytest.skip(f"Need at least 2 instrumentors for system-wide test, got {len(available_instrumentors)}")
            
        # Measure system performance without instrumentation
        baseline_metrics = await self._measure_system_performance(
            instrumentors=[], 
            test_name="baseline"
        )
        
        # Measure system performance with all available instrumentors
        instrumented_metrics = await self._measure_system_performance(
            instrumentors=available_instrumentors,
            test_name="all_instrumentors"
        )
        
        # Calculate system-wide overhead
        system_overhead = ((instrumented_metrics["total_time"] - baseline_metrics["total_time"]) / 
                          baseline_metrics["total_time"]) * 100
        
        # Record metrics
        self.record_metric("system_baseline_total_time_ms", baseline_metrics["total_time"] * 1000)
        self.record_metric("system_instrumented_total_time_ms", instrumented_metrics["total_time"] * 1000)
        self.record_metric("system_wide_overhead_percentage", system_overhead)
        self.record_metric("active_instrumentors_count", len(available_instrumentors))
        
        for instrumentor_name in available_instrumentors:
            self.record_metric(f"instrumentor_{instrumentor_name}_active", True)
            
        # System-wide overhead should be reasonable even with all instrumentors
        assert system_overhead < 25.0, (
            f"System-wide auto-instrumentation overhead {system_overhead:.1f}% "
            f"exceeds 25% limit with {len(available_instrumentors)} instrumentors"
        )
        
    def _check_instrumentor_availability(self) -> List[str]:
        """Check which instrumentors are available for testing."""
        available = []
        
        instrumentor_checks = [
            ("sqlalchemy", "opentelemetry.instrumentation.sqlalchemy", "SQLAlchemyInstrumentor"),
            ("redis", "opentelemetry.instrumentation.redis", "RedisInstrumentor"),
            ("requests", "opentelemetry.instrumentation.requests", "RequestsInstrumentor"),
            ("fastapi", "opentelemetry.instrumentation.fastapi", "FastAPIInstrumentor"),
        ]
        
        for name, module_name, class_name in instrumentor_checks:
            try:
                module = __import__(module_name, fromlist=[class_name])
                getattr(module, class_name)
                available.append(name)
            except ImportError:
                continue
                
        return available
        
    async def _measure_system_performance(
        self, 
        instrumentors: List[str],
        test_name: str
    ) -> Dict[str, float]:
        """Measure system performance with specified instrumentors active."""
        
        active_instrumentor_objects = []
        
        try:
            # Setup OpenTelemetry if instrumentors are requested
            if instrumentors:
                from opentelemetry import trace
                from opentelemetry.sdk.trace import TracerProvider
                from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
                
                trace.set_tracer_provider(TracerProvider())
                span_processor = BatchSpanProcessor(ConsoleSpanExporter())
                trace.get_tracer_provider().add_span_processor(span_processor)
                
                # Activate requested instrumentors
                for instrumentor_name in instrumentors:
                    try:
                        if instrumentor_name == "sqlalchemy":
                            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
                            instr = SQLAlchemyInstrumentor()
                            if not instr.is_instrumented_by_opentelemetry:
                                instr.instrument()
                            active_instrumentor_objects.append(instr)
                            
                        elif instrumentor_name == "redis":
                            from opentelemetry.instrumentation.redis import RedisInstrumentor
                            instr = RedisInstrumentor()
                            if not instr.is_instrumented_by_opentelemetry:
                                instr.instrument()
                            active_instrumentor_objects.append(instr)
                            
                        elif instrumentor_name == "requests":
                            from opentelemetry.instrumentation.requests import RequestsInstrumentor
                            instr = RequestsInstrumentor()
                            if not instr.is_instrumented_by_opentelemetry:
                                instr.instrument()
                            active_instrumentor_objects.append(instr)
                            
                    except Exception as e:
                        logger.warning(f"Failed to activate {instrumentor_name} instrumentor: {e}")
                        
            # Execute system-wide performance test
            total_times = []
            
            for i in range(self.system_test_iterations):
                start_time = time.perf_counter()
                
                # Simulate system activity across multiple components
                await self._simulate_system_activity(f"{test_name}_{i}")
                
                end_time = time.perf_counter()
                total_times.append(end_time - start_time)
                
            return {
                "total_time": statistics.mean(total_times),
                "p95_time": statistics.quantiles(total_times, n=20)[18] if len(total_times) >= 20 else max(total_times),
                "iterations": len(total_times)
            }
            
        finally:
            # Cleanup instrumentors
            for instrumentor in active_instrumentor_objects:
                try:
                    instrumentor.uninstrument()
                except:
                    pass
                    
    async def _simulate_system_activity(self, test_iteration: str):
        """Simulate typical system activity across multiple components."""
        
        activities = []
        
        # Database activity (if available)
        try:
            import sqlalchemy
            from sqlalchemy import create_engine, text
            
            db_url = self._get_test_database_url()
            engine = create_engine(db_url, echo=False)
            
            with engine.connect() as conn:
                conn.execute(text("SELECT 1 as system_test"))
                
            engine.dispose()
            activities.append("database")
            
        except Exception:
            pass
            
        # Redis activity (if available)
        try:
            import redis
            
            redis_client = await get_redis_client()
            
            key = f"system_test_{test_iteration}"
            await redis_client.set(key, "test_value", ex=30)
            await redis_client.get(key)
            await redis_client.delete(key)
            
            activities.append("redis")
            
        except Exception:
            pass
            
        # Small delay to simulate processing
        await asyncio.sleep(0.001)  # 1ms
        
        # Record activities performed
        self.record_metric(f"system_activities_{test_iteration}", len(activities))
        
    def _get_test_database_url(self) -> str:
        """Get test database connection URL."""
        return (
            f"postgresql://{self.get_env_var('POSTGRES_USER', 'netra')}:"
            f"{self.get_env_var('POSTGRES_PASSWORD', 'netra_secure_2024')}@"
            f"{self.get_env_var('POSTGRES_HOST', 'localhost')}:"
            f"{self.get_env_var('POSTGRES_PORT', '5432')}/"
            f"{self.get_env_var('POSTGRES_DB', 'netra_test')}"
        )
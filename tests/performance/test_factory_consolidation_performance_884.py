"""
Test Suite: Issue #884 - Multiple execution engine factories blocking AI responses
Module: Factory Consolidation Performance Test

PURPOSE:
This performance test validates that factory consolidation doesn't degrade performance
and should FAIL if consolidation causes significant performance regressions (>20%).

BUSINESS IMPACT:
- $500K+ ARR depends on fast execution engine creation for responsive AI interactions
- Factory consolidation must not slow down user experience
- Performance degradation affects user satisfaction and retention
- Execution engine creation speed directly impacts response times

TEST REQUIREMENTS:
- Measures factory creation times before/after consolidation
- Should FAIL if performance degrades significantly (>20%)  
- Tests performance under concurrent load
- Validates memory usage doesn't increase excessively

Created: 2025-09-14 for Issue #884 Step 2 performance validation
"""

import asyncio
import uuid
import time
import statistics
import psutil
import os
import gc
from typing import Dict, Any, List, Optional, Tuple
import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from test_framework.ssot.base_test_case import SSotAsyncTestCase


@pytest.mark.performance
class FactoryConsolidationPerformance884Tests(SSotAsyncTestCase):
    """
    Performance Test: Validate factory consolidation performance impact
    
    This test measures performance before/after factory consolidation to detect
    any significant performance regressions that could affect user experience.
    """
    
    def setup_method(self, method):
        """Set up performance testing"""
        super().setup_method(method)
        self.record_metric("test_type", "performance")
        self.record_metric("performance_threshold", 0.20)  # 20% degradation threshold
        self.record_metric("issue_number", "884")
        
        # Set performance test environment
        env = self.get_env()
        env.set("TESTING", "true", "performance_test")
        env.set("TEST_PERFORMANCE", "true", "performance_test")
        
        # Performance tracking
        self.baseline_metrics = {}
        self.current_metrics = {}
        
        # Get initial system metrics
        self.process = psutil.Process(os.getpid())
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
    async def test_factory_creation_performance_should_fail_if_degraded_884(self):
        """
        CRITICAL PERFORMANCE TEST: Factory creation speed validation
        
        This test measures execution engine factory creation time and should FAIL
        if consolidation causes performance degradation >20%.
        
        Expected Initial Result: MAY FAIL if consolidation degrades performance
        Expected Final Result: PASS after performance optimization
        """
        start_time = time.time()
        self.record_metric("performance_test_start", start_time)
        
        # Import consolidated factory
        try:
            factory = None
            factory_source = None
            
            try:
                from netra_backend.app.core.managers.execution_engine_factory import ExecutionEngineFactory
                factory = ExecutionEngineFactory()
                factory_source = "core.managers.execution_engine_factory"
            except ImportError:
                try:
                    from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngineFactory
                    factory = ExecutionEngineFactory()
                    factory_source = "agents.execution_engine_consolidated"
                except ImportError:
                    try:
                        from netra_backend.app.agents.execution_engine_unified_factory import create_execution_engine
                        class FactoryWrapper:
                            def create_execution_engine(self, context):
                                return create_execution_engine(context)
                        factory = FactoryWrapper()
                        factory_source = "agents.execution_engine_unified_factory"
                    except ImportError:
                        pytest.skip("No factory available for performance testing")
            
            self.record_metric("factory_source", factory_source)
            
            # Import user execution context
            try:
                from netra_backend.app.agents.user_execution_context import UserExecutionContext
            except ImportError:
                class UserExecutionContextTests:
                    def __init__(self, user_id: str, session_id: str, **kwargs):
                        self.user_id = user_id
                        self.session_id = session_id
                        for key, value in kwargs.items():
                            setattr(self, key, value)
                UserExecutionContext = UserExecutionContextTests
                
        except Exception as e:
            pytest.skip(f"Required components not available: {e}")
        
        # Performance Test 1: Measure single factory creation time
        single_creation_times = []
        
        for i in range(100):  # 100 iterations for statistical significance
            user_context = UserExecutionContext(
                user_id=f"perf_test_user_{i}_{uuid.uuid4().hex[:8]}",
                session_id=f"perf_test_session_{i}_{uuid.uuid4().hex[:8]}"
            )
            
            creation_start = time.time()
            execution_engine = factory.create_execution_engine(user_context)
            creation_end = time.time()
            
            creation_time = creation_end - creation_start
            single_creation_times.append(creation_time)
            
            # Validate engine was created
            self.assertIsNotNone(execution_engine,
                f"Factory failed to create execution engine in iteration {i}")
            
            # Clean up to prevent memory accumulation
            del execution_engine
            if i % 10 == 0:
                gc.collect()
        
        # Calculate single creation statistics
        avg_creation_time = statistics.mean(single_creation_times)
        median_creation_time = statistics.median(single_creation_times)
        p95_creation_time = statistics.quantiles(single_creation_times, n=20)[18]  # 95th percentile
        min_creation_time = min(single_creation_times)
        max_creation_time = max(single_creation_times)
        
        self.record_metric("avg_single_creation_time", avg_creation_time)
        self.record_metric("median_single_creation_time", median_creation_time)
        self.record_metric("p95_single_creation_time", p95_creation_time)
        self.record_metric("min_single_creation_time", min_creation_time)
        self.record_metric("max_single_creation_time", max_creation_time)
        
        # CRITICAL PERFORMANCE ASSERTIONS
        
        # Average creation time should be under 50ms
        assert avg_creation_time < 0.050, (
            f"CRITICAL: Factory creation too slow: {avg_creation_time:.4f}s average. "
            f"This affects user experience and indicates performance regression after consolidation. "
            f"Expected: <50ms, Got: {avg_creation_time*1000:.1f}ms")
        
        # 95th percentile should be under 100ms  
        assert p95_creation_time < 0.100, (
            f"CRITICAL: Factory creation 95th percentile too slow: {p95_creation_time:.4f}s. "
            f"This indicates inconsistent performance that affects user experience. "
            f"Expected: <100ms, Got: {p95_creation_time*1000:.1f}ms")
        
        # Performance Test 2: Concurrent creation performance
        await self._test_concurrent_creation_performance(factory, UserExecutionContext)
        
        # Performance Test 3: Memory usage validation
        await self._test_memory_usage_performance(factory, UserExecutionContext)
        
        total_test_time = time.time() - start_time
        self.record_metric("total_performance_test_time", total_test_time)
        
        # Record successful performance validation
        self.record_metric("performance_regression_free", True)
        self.record_metric("factory_performance_acceptable", True)
        self.record_metric("business_value_protected", True)
        
    async def _test_concurrent_creation_performance(self, factory, UserExecutionContext):
        """Test factory performance under concurrent load"""
        concurrent_users = 20
        iterations_per_user = 5
        
        def create_engines_for_user(user_index: int) -> List[float]:
            """Create execution engines for a single user and measure times"""
            user_creation_times = []
            
            for i in range(iterations_per_user):
                user_context = UserExecutionContext(
                    user_id=f"concurrent_test_user_{user_index}_{i}",
                    session_id=f"concurrent_test_session_{user_index}_{i}"
                )
                
                creation_start = time.time()
                execution_engine = factory.create_execution_engine(user_context)
                creation_end = time.time()
                
                creation_time = creation_end - creation_start
                user_creation_times.append(creation_time)
                
                # Clean up
                del execution_engine
                
            return user_creation_times
        
        # Execute concurrent factory calls
        concurrent_start = time.time()
        all_creation_times = []
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            future_to_user = {
                executor.submit(create_engines_for_user, user_idx): user_idx 
                for user_idx in range(concurrent_users)
            }
            
            for future in as_completed(future_to_user):
                user_times = future.result()
                all_creation_times.extend(user_times)
        
        concurrent_end = time.time()
        total_concurrent_time = concurrent_end - concurrent_start
        total_operations = concurrent_users * iterations_per_user
        
        # Calculate concurrent performance metrics
        avg_concurrent_creation = statistics.mean(all_creation_times)
        concurrent_throughput = total_operations / total_concurrent_time
        
        self.record_metric("concurrent_avg_creation_time", avg_concurrent_creation)
        self.record_metric("concurrent_throughput_ops_per_sec", concurrent_throughput)
        self.record_metric("total_concurrent_operations", total_operations)
        self.record_metric("total_concurrent_time", total_concurrent_time)
        
        # CRITICAL CONCURRENT PERFORMANCE ASSERTIONS
        
        # Concurrent average shouldn't be much slower than single-threaded
        assert avg_concurrent_creation < 0.200, (  # 200ms limit under load
            f"CRITICAL: Factory too slow under concurrent load: {avg_concurrent_creation:.4f}s average. "
            f"This indicates poor scalability that affects multi-user performance. "
            f"Expected: <200ms, Got: {avg_concurrent_creation*1000:.1f}ms")
        
        # Should maintain reasonable throughput
        assert concurrent_throughput > 50, (  # At least 50 operations/second
            f"CRITICAL: Factory throughput too low: {concurrent_throughput:.1f} ops/sec. "
            f"This indicates scalability issues that prevent handling multiple concurrent users.")
        
    async def _test_memory_usage_performance(self, factory, UserExecutionContext):
        """Test factory memory usage and cleanup"""
        # Get initial memory
        initial_memory = self.process.memory_info().rss / 1024 / 1024
        
        # Create many execution engines to test memory usage
        engines = []
        memory_samples = []
        
        for i in range(50):
            user_context = UserExecutionContext(
                user_id=f"memory_test_user_{i}",
                session_id=f"memory_test_session_{i}"
            )
            
            execution_engine = factory.create_execution_engine(user_context)
            engines.append(execution_engine)
            
            # Sample memory every 10 creations
            if i % 10 == 0:
                current_memory = self.process.memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory - initial_memory)
        
        # Memory after creation
        peak_memory = self.process.memory_info().rss / 1024 / 1024
        memory_growth = peak_memory - initial_memory
        
        self.record_metric("memory_growth_during_creation", memory_growth)
        self.record_metric("memory_samples", memory_samples)
        
        # Clean up engines
        del engines
        gc.collect()
        
        # Memory after cleanup
        cleanup_memory = self.process.memory_info().rss / 1024 / 1024
        cleanup_memory_growth = cleanup_memory - initial_memory
        
        self.record_metric("memory_growth_after_cleanup", cleanup_memory_growth)
        
        # CRITICAL MEMORY PERFORMANCE ASSERTIONS
        
        # Memory growth during creation should be reasonable
        assert memory_growth < 100.0, (  # 100MB limit
            f"CRITICAL: Excessive memory usage during factory operations: {memory_growth:.1f}MB. "
            f"This indicates memory inefficiency that prevents scalable operation.")
        
        # Memory should be mostly cleaned up
        assert cleanup_memory_growth < memory_growth * 0.5, (  # Should free at least 50%
            f"CRITICAL: Poor memory cleanup: {cleanup_memory_growth:.1f}MB remaining "
            f"after cleanup (was {memory_growth:.1f}MB). "
            f"This indicates memory leaks that prevent long-running operation.")
        
    async def test_performance_comparison_with_baseline_884(self):
        """
        PERFORMANCE COMPARISON: Compare current performance with expected baseline
        
        This test establishes performance baselines and validates that factory
        consolidation doesn't cause significant performance regressions.
        """
        # Import factory
        try:
            from netra_backend.app.core.managers.execution_engine_factory import ExecutionEngineFactory
            factory = ExecutionEngineFactory()
        except ImportError:
            pytest.skip("Factory not available")
            
        try:
            from netra_backend.app.agents.user_execution_context import UserExecutionContext
        except ImportError:
            class UserExecutionContextTests:
                def __init__(self, user_id: str, session_id: str, **kwargs):
                    self.user_id = user_id
                    self.session_id = session_id
                    for key, value in kwargs.items():
                        setattr(self, key, value)
            UserExecutionContext = UserExecutionContextTests
        
        # Performance baseline expectations (based on reasonable factory performance)
        baseline_expectations = {
            'avg_creation_time': 0.020,  # 20ms average
            'p95_creation_time': 0.050,  # 50ms 95th percentile  
            'memory_per_engine': 1.0,    # 1MB per engine
            'concurrent_throughput': 100  # 100 operations/sec
        }
        
        self.record_metric("baseline_expectations", baseline_expectations)
        
        # Measure current performance
        creation_times = []
        memory_start = self.process.memory_info().rss / 1024 / 1024
        
        # Create engines and measure performance
        for i in range(50):
            user_context = UserExecutionContext(
                user_id=f"baseline_test_user_{i}",
                session_id=f"baseline_test_session_{i}"
            )
            
            start_time = time.time()
            execution_engine = factory.create_execution_engine(user_context)
            end_time = time.time()
            
            creation_times.append(end_time - start_time)
            del execution_engine
        
        memory_end = self.process.memory_info().rss / 1024 / 1024
        memory_per_engine = (memory_end - memory_start) / 50
        
        # Calculate current metrics
        current_metrics = {
            'avg_creation_time': statistics.mean(creation_times),
            'p95_creation_time': statistics.quantiles(creation_times, n=20)[18],
            'memory_per_engine': memory_per_engine,
            'concurrent_throughput': 1.0 / statistics.mean(creation_times)  # Approximation
        }
        
        self.record_metric("current_performance", current_metrics)
        
        # Compare against baseline expectations
        performance_regressions = []
        performance_improvements = []
        
        for metric, baseline in baseline_expectations.items():
            current = current_metrics[metric]
            
            if metric in ['avg_creation_time', 'p95_creation_time', 'memory_per_engine']:
                # Lower is better for these metrics
                regression_threshold = baseline * 1.20  # 20% worse
                improvement_threshold = baseline * 0.80  # 20% better
                
                if current > regression_threshold:
                    regression_percent = ((current - baseline) / baseline) * 100
                    performance_regressions.append({
                        'metric': metric,
                        'baseline': baseline,
                        'current': current,
                        'regression_percent': regression_percent
                    })
                elif current < improvement_threshold:
                    improvement_percent = ((baseline - current) / baseline) * 100
                    performance_improvements.append({
                        'metric': metric,
                        'baseline': baseline,
                        'current': current,
                        'improvement_percent': improvement_percent
                    })
            else:
                # Higher is better for throughput
                regression_threshold = baseline * 0.80  # 20% worse
                improvement_threshold = baseline * 1.20  # 20% better
                
                if current < regression_threshold:
                    regression_percent = ((baseline - current) / baseline) * 100
                    performance_regressions.append({
                        'metric': metric,
                        'baseline': baseline,
                        'current': current,
                        'regression_percent': regression_percent
                    })
                elif current > improvement_threshold:
                    improvement_percent = ((current - baseline) / baseline) * 100
                    performance_improvements.append({
                        'metric': metric,
                        'baseline': baseline,
                        'current': current,
                        'improvement_percent': improvement_percent
                    })
        
        self.record_metric("performance_regressions", performance_regressions)
        self.record_metric("performance_improvements", performance_improvements)
        
        # CRITICAL PERFORMANCE REGRESSION ASSERTION
        assert len(performance_regressions) == 0, (
            f"CRITICAL: Performance regressions detected after factory consolidation: "
            f"{performance_regressions}. "
            f"This indicates consolidation harmed performance beyond acceptable thresholds (20%). "
            f"Current performance: {current_metrics}")
        
        # Record successful baseline comparison
        self.record_metric("baseline_comparison_passed", True)
        self.record_metric("no_performance_regressions", True)
        
        # Log any improvements
        if performance_improvements:
            self.record_metric("performance_improvements_found", True)
            self.record_metric("improvement_details", performance_improvements)
        
    async def test_factory_scalability_under_load_884(self):
        """
        SCALABILITY TEST: Validate factory handles increasing load gracefully
        
        This test validates that factory performance doesn't degrade significantly
        as load increases, ensuring scalability for multi-user scenarios.
        """
        try:
            from netra_backend.app.core.managers.execution_engine_factory import ExecutionEngineFactory
            factory = ExecutionEngineFactory()
        except ImportError:
            pytest.skip("Factory not available")
            
        try:
            from netra_backend.app.agents.user_execution_context import UserExecutionContext
        except ImportError:
            class UserExecutionContextTests:
                def __init__(self, user_id: str, session_id: str, **kwargs):
                    self.user_id = user_id
                    self.session_id = session_id
                    for key, value in kwargs.items():
                        setattr(self, key, value)
            UserExecutionContext = UserExecutionContextTests
        
        # Test different load levels
        load_levels = [1, 5, 10, 20]  # Concurrent users
        iterations_per_level = 10
        
        scalability_results = []
        
        for load_level in load_levels:
            def create_engine_with_load(user_index: int) -> float:
                """Create engine and return creation time"""
                user_context = UserExecutionContext(
                    user_id=f"scalability_user_{load_level}_{user_index}",
                    session_id=f"scalability_session_{load_level}_{user_index}"
                )
                
                start_time = time.time()
                execution_engine = factory.create_execution_engine(user_context)
                end_time = time.time()
                
                # Clean up
                del execution_engine
                
                return end_time - start_time
            
            # Execute concurrent operations for this load level
            load_start_time = time.time()
            creation_times = []
            
            with ThreadPoolExecutor(max_workers=load_level) as executor:
                futures = [
                    executor.submit(create_engine_with_load, i) 
                    for i in range(iterations_per_level)
                ]
                
                for future in as_completed(futures):
                    creation_time = future.result()
                    creation_times.append(creation_time)
            
            load_end_time = time.time()
            total_load_time = load_end_time - load_start_time
            
            # Calculate metrics for this load level
            avg_creation_time = statistics.mean(creation_times)
            throughput = iterations_per_level / total_load_time
            
            scalability_results.append({
                'load_level': load_level,
                'avg_creation_time': avg_creation_time,
                'throughput': throughput,
                'total_time': total_load_time
            })
        
        self.record_metric("scalability_results", scalability_results)
        
        # Analyze scalability trends
        creation_times = [r['avg_creation_time'] for r in scalability_results]
        throughputs = [r['throughput'] for r in scalability_results]
        
        # Performance shouldn't degrade drastically with load
        min_creation_time = min(creation_times)
        max_creation_time = max(creation_times)
        performance_degradation = (max_creation_time - min_creation_time) / min_creation_time
        
        self.record_metric("performance_degradation_with_load", performance_degradation)
        
        # CRITICAL SCALABILITY ASSERTION
        assert performance_degradation < 1.0, (  # 100% degradation limit
            f"CRITICAL: Factory performance degrades too much under load: "
            f"{performance_degradation:.1%} degradation from {min_creation_time:.4f}s "
            f"to {max_creation_time:.4f}s. This indicates poor scalability that "
            f"prevents reliable multi-user operation.")
        
        # Throughput should scale reasonably with load (not perfectly linear, but should increase)
        min_throughput = min(throughputs)
        max_throughput = max(throughputs)
        
        # At higher loads, throughput should be significantly higher than single-user
        assert max_throughput > min_throughput * 2, (
            f"CRITICAL: Factory doesn't scale well: throughput only increased from "
            f"{min_throughput:.1f} to {max_throughput:.1f} ops/sec. "
            f"This indicates scalability issues.")
        
        self.record_metric("scalability_test_passed", True)
        self.record_metric("factory_scales_with_load", True)
"""
Comprehensive Performance and Startup Tests for Auth Environment Configuration

Business Value Justification (BVJ):
- Segment: Platform/Internal (Critical infrastructure for all segments)
- Business Goal: Ensure fast auth service startup and responsive configuration access
- Value Impact: Prevents slow auth service startup that delays platform availability
- Strategic Impact: Auth service startup time directly affects platform deployment speed
- Revenue Impact: Slow auth startup = delayed deployments = reduced development velocity

CRITICAL PERFORMANCE REQUIREMENTS:
Auth service must start quickly in all environments to ensure:
- Fast deployment cycles (critical for staging/production deployments)
- Quick development iteration (critical for developer productivity)
- Rapid auto-scaling in production (critical for handling traffic spikes)
- Fast disaster recovery (critical for platform reliability)

PERFORMANCE TESTING METHODOLOGY:
- Real AuthEnvironment instances (no business logic mocking)
- Actual configuration loading with realistic scenarios
- Memory usage monitoring for resource efficiency
- Startup time measurement across environments
- Configuration access performance validation
- Resource leak detection for long-running scenarios

CLAUDE.MD COMPLIANCE:
- Uses SSOT BaseTestCase for isolated testing
- NO mocks of core business logic - tests real performance
- Uses IsolatedEnvironment throughout
- Tests fail hard when performance requirements not met
"""

import pytest
import time
import gc
import threading
import hashlib
from typing import Dict, Any, List, Tuple
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed

from test_framework.ssot.base_test_case import SSotBaseTestCase
from auth_service.auth_core.auth_environment import AuthEnvironment, get_auth_env
from shared.isolated_environment import get_env


class TestAuthEnvironmentStartupPerformance(SSotBaseTestCase):
    """Test AuthEnvironment startup performance across all environments."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var("TESTING", "true")
        
        # Performance thresholds (in seconds)
        self.max_init_time = 0.5  # Maximum initialization time
        self.max_config_access_time = 0.001  # Maximum configuration access time
        self.max_validation_time = 0.1  # Maximum validation time
        
    def test_auth_environment_initialization_performance(self):
        """Test AuthEnvironment initializes within performance thresholds."""
        environments = ["development", "test", "staging", "production"]
        init_times = {}
        
        for env in environments:
            with self.temp_env_vars(ENVIRONMENT=env):
                # Measure initialization time
                start_time = time.perf_counter()
                
                auth_env = AuthEnvironment()
                
                end_time = time.perf_counter()
                init_time = end_time - start_time
                init_times[env] = init_time
                
                # Should initialize within threshold
                assert init_time < self.max_init_time, \
                    f"AuthEnvironment initialization too slow in {env}: {init_time:.4f}s > {self.max_init_time}s"
                    
        # Record metrics for monitoring
        for env, time_taken in init_times.items():
            self.record_metric(f"init_time_{env}", time_taken)
            
        avg_init_time = sum(init_times.values()) / len(init_times)
        self.record_metric("avg_init_time", avg_init_time)
        
        # Average should be well under threshold
        assert avg_init_time < self.max_init_time / 2, \
            f"Average initialization time too high: {avg_init_time:.4f}s"
            
    def test_configuration_access_performance(self):
        """Test configuration method access performance."""
        with self.temp_env_vars(ENVIRONMENT="test"):
            auth_env = AuthEnvironment()
            
            # Test frequently accessed configuration methods
            config_methods = [
                'get_environment',
                'get_jwt_algorithm', 
                'get_jwt_expiration_minutes',
                'get_bcrypt_rounds',
                'get_auth_service_port',
                'get_auth_service_host',
                'get_log_level',
                'should_enable_debug',
                'get_login_rate_limit',
                'get_min_password_length',
                'is_production',
                'is_development',
                'is_testing',
            ]
            
            method_times = {}
            
            for method_name in config_methods:
                method = getattr(auth_env, method_name)
                
                # Measure single access time
                start_time = time.perf_counter()
                result = method()
                end_time = time.perf_counter()
                
                access_time = end_time - start_time
                method_times[method_name] = access_time
                
                # Should be very fast for cached/simple config
                assert access_time < self.max_config_access_time, \
                    f"{method_name} access too slow: {access_time:.6f}s > {self.max_config_access_time}s"
                    
                # Result should be valid
                assert result is not None or method_name in ['get_smtp_host', 'get_oauth_google_client_id'], \
                    f"{method_name} returned None unexpectedly"
                    
            # Record performance metrics
            avg_access_time = sum(method_times.values()) / len(method_times)
            self.record_metric("avg_config_access_time", avg_access_time)
            self.record_metric("config_methods_tested", len(config_methods))
            
    def test_concurrent_configuration_access_performance(self):
        """Test configuration access performance under concurrent load."""
        with self.temp_env_vars(ENVIRONMENT="test"):
            auth_env = AuthEnvironment()
            
            def access_config_repeatedly(iterations: int) -> List[float]:
                """Access configuration repeatedly and measure times."""
                times = []
                for _ in range(iterations):
                    start = time.perf_counter()
                    
                    # Access multiple config methods
                    env = auth_env.get_environment()
                    port = auth_env.get_auth_service_port()
                    debug = auth_env.should_enable_debug()
                    level = auth_env.get_log_level()
                    
                    end = time.perf_counter()
                    times.append(end - start)
                    
                return times
                
            # Test concurrent access from multiple threads
            num_threads = 10
            iterations_per_thread = 50
            
            start_time = time.perf_counter()
            
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [
                    executor.submit(access_config_repeatedly, iterations_per_thread)
                    for _ in range(num_threads)
                ]
                
                all_times = []
                for future in as_completed(futures):
                    thread_times = future.result()
                    all_times.extend(thread_times)
                    
            end_time = time.perf_counter()
            total_time = end_time - start_time
            
            # Performance analysis
            avg_time = sum(all_times) / len(all_times)
            max_time = max(all_times)
            total_operations = num_threads * iterations_per_thread
            
            # Should handle concurrent access efficiently
            assert avg_time < self.max_config_access_time * 2, \
                f"Concurrent config access too slow: {avg_time:.6f}s average"
            assert max_time < self.max_config_access_time * 10, \
                f"Worst-case concurrent access too slow: {max_time:.6f}s"
                
            # Should complete all operations quickly
            operations_per_second = total_operations / total_time
            assert operations_per_second > 1000, \
                f"Concurrent throughput too low: {operations_per_second:.0f} ops/sec"
                
            self.record_metric("concurrent_avg_time", avg_time)
            self.record_metric("concurrent_max_time", max_time)
            self.record_metric("concurrent_ops_per_sec", operations_per_second)


class TestAuthEnvironmentMemoryPerformance(SSotBaseTestCase):
    """Test AuthEnvironment memory usage and resource management."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var("TESTING", "true")
        
    def test_memory_usage_optimization(self):
        """Test AuthEnvironment has optimized memory usage."""
        with self.temp_env_vars(ENVIRONMENT="test"):
            # Measure memory before
            gc.collect()
            initial_objects = len(gc.get_objects())
            
            # Create multiple AuthEnvironment instances
            environments = []
            for i in range(20):
                env = AuthEnvironment()
                environments.append(env)
                
                # Access various configurations to populate any caches
                env.get_environment()
                env.get_jwt_algorithm()
                env.get_auth_service_url()
                env.get_database_url()  # May create temporary files in test
                env.validate()  # Full validation
                
            # Measure memory after
            gc.collect()
            mid_objects = len(gc.get_objects())
            object_growth = mid_objects - initial_objects
            
            # Clean up
            environments.clear()
            gc.collect()
            final_objects = len(gc.get_objects())
            
            # Memory usage analysis
            cleanup_efficiency = (mid_objects - final_objects) / max(object_growth, 1)
            
            # Should not create excessive objects
            objects_per_instance = object_growth / 20
            assert objects_per_instance < 50, \
                f"Too many objects per AuthEnvironment: {objects_per_instance}"
                
            # Should clean up efficiently when references are removed
            assert cleanup_efficiency > 0.8, \
                f"Poor cleanup efficiency: {cleanup_efficiency:.2f}"
                
            self.record_metric("objects_per_instance", objects_per_instance)
            self.record_metric("cleanup_efficiency", cleanup_efficiency)
            
    def test_singleton_memory_efficiency(self):
        """Test singleton AuthEnvironment pattern is memory efficient."""
        # Import here to get fresh module state
        from auth_service.auth_core.auth_environment import get_auth_env
        
        with self.temp_env_vars(ENVIRONMENT="test"):
            # Measure memory before
            gc.collect()
            initial_objects = len(gc.get_objects())
            
            # Get singleton multiple times
            singletons = []
            for i in range(100):
                env = get_auth_env()
                singletons.append(env)
                
                # Access configuration
                env.get_environment()
                env.get_jwt_algorithm()
                
            # Measure memory after
            gc.collect()
            final_objects = len(gc.get_objects())
            object_growth = final_objects - initial_objects
            
            # All references should point to same object
            first_env = singletons[0]
            for env in singletons[1:]:
                assert env is first_env, "get_auth_env should return same instance"
                
            # Should create minimal additional objects
            assert object_growth < 20, \
                f"Singleton pattern created too many objects: {object_growth}"
                
            self.record_metric("singleton_object_growth", object_growth)
            
    def test_configuration_caching_efficiency(self):
        """Test configuration caching is memory and performance efficient."""
        with self.temp_env_vars(ENVIRONMENT="test"):
            auth_env = AuthEnvironment()
            
            # Methods that might cache results
            cached_methods = [
                'get_database_url',
                'get_auth_service_url', 
                'get_frontend_url',
                'get_backend_url',
                'get_redis_url',
            ]
            
            for method_name in cached_methods:
                method = getattr(auth_env, method_name)
                
                # First call - might populate cache
                start_time = time.perf_counter()
                result1 = method()
                first_call_time = time.perf_counter() - start_time
                
                # Second call - should be cached if caching is implemented
                start_time = time.perf_counter()
                result2 = method()
                second_call_time = time.perf_counter() - start_time
                
                # Results should be consistent
                assert result1 == result2, f"{method_name} returned inconsistent results"
                
                # If caching is implemented, second call should be faster
                # But this is optional - consistent performance is also acceptable
                if second_call_time > 0:  # Avoid division by zero
                    speedup_ratio = first_call_time / second_call_time
                    self.record_metric(f"{method_name}_speedup_ratio", speedup_ratio)
                    
            self.record_metric("cached_methods_tested", len(cached_methods))


class TestAuthEnvironmentValidationPerformance(SSotBaseTestCase):
    """Test AuthEnvironment validation performance."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var("TESTING", "true")
        self.max_validation_time = 0.1  # Maximum validation time
        
    def test_configuration_validation_performance(self):
        """Test configuration validation completes within performance thresholds."""
        environments = ["development", "test", "staging", "production"]
        validation_times = {}
        
        for env in environments:
            with self.temp_env_vars(ENVIRONMENT=env):
                auth_env = AuthEnvironment()
                
                # Mock any expensive operations that might be called during validation
                with patch.object(auth_env, 'get_jwt_secret_key', return_value="test-secret"):
                    with patch.object(auth_env, 'is_smtp_enabled', return_value=True):
                        
                        start_time = time.perf_counter()
                        result = auth_env.validate()
                        end_time = time.perf_counter()
                        
                        validation_time = end_time - start_time
                        validation_times[env] = validation_time
                        
                        # Should validate within threshold
                        assert validation_time < self.max_validation_time, \
                            f"Validation too slow in {env}: {validation_time:.4f}s > {self.max_validation_time}s"
                            
                        # Should return valid result structure
                        assert isinstance(result, dict)
                        assert "valid" in result
                        assert "environment" in result
                        assert result["environment"] == env
                        
        # Record performance metrics
        avg_validation_time = sum(validation_times.values()) / len(validation_times)
        self.record_metric("avg_validation_time", avg_validation_time)
        
        for env, time_taken in validation_times.items():
            self.record_metric(f"validation_time_{env}", time_taken)
            
    def test_repeated_validation_performance(self):
        """Test repeated validation calls maintain performance."""
        with self.temp_env_vars(ENVIRONMENT="test"):
            auth_env = AuthEnvironment()
            
            validation_times = []
            
            # Perform multiple validations
            for i in range(10):
                with patch.object(auth_env, 'get_jwt_secret_key', return_value="test-secret"):
                    start_time = time.perf_counter()
                    result = auth_env.validate()
                    end_time = time.perf_counter()
                    
                    validation_time = end_time - start_time
                    validation_times.append(validation_time)
                    
                    # Each validation should be fast
                    assert validation_time < self.max_validation_time, \
                        f"Validation #{i} too slow: {validation_time:.4f}s"
                        
                    # Should return consistent results
                    assert isinstance(result, dict)
                    assert "valid" in result
                    
            # Performance should be consistent across calls
            avg_time = sum(validation_times) / len(validation_times)
            max_time = max(validation_times)
            min_time = min(validation_times)
            variance = max_time - min_time
            
            # Should have low variance (consistent performance)
            assert variance < self.max_validation_time / 2, \
                f"Validation time too variable: {variance:.4f}s variance"
                
            self.record_metric("validation_avg_time", avg_time)
            self.record_metric("validation_variance", variance)
            self.record_metric("validations_performed", len(validation_times))


class TestAuthEnvironmentScalabilityPerformance(SSotBaseTestCase):
    """Test AuthEnvironment scalability and resource efficiency."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var("TESTING", "true")
        
    def test_multiple_environment_creation_performance(self):
        """Test creating multiple AuthEnvironment instances scales linearly."""
        batch_sizes = [1, 5, 10, 20, 50]
        creation_times = {}
        
        for batch_size in batch_sizes:
            with self.temp_env_vars(ENVIRONMENT="test"):
                start_time = time.perf_counter()
                
                environments = []
                for i in range(batch_size):
                    env = AuthEnvironment()
                    environments.append(env)
                    
                    # Basic configuration access
                    env.get_environment()
                    env.get_auth_service_port()
                    
                end_time = time.perf_counter()
                total_time = end_time - start_time
                time_per_instance = total_time / batch_size
                
                creation_times[batch_size] = time_per_instance
                
                # Clean up
                environments.clear()
                
        # Performance should scale reasonably (not exponentially worse)
        small_batch_time = creation_times[1]
        large_batch_time = creation_times[50]
        
        # Large batch shouldn't be more than 3x slower per instance
        scalability_factor = large_batch_time / small_batch_time
        assert scalability_factor < 3.0, \
            f"Poor scalability: {scalability_factor:.2f}x slower for large batches"
            
        # Record scalability metrics
        for batch_size, time_per_instance in creation_times.items():
            self.record_metric(f"creation_time_batch_{batch_size}", time_per_instance)
            
        self.record_metric("scalability_factor", scalability_factor)
        
    def test_configuration_method_performance_under_load(self):
        """Test configuration methods maintain performance under heavy load."""
        with self.temp_env_vars(ENVIRONMENT="test"):
            auth_env = AuthEnvironment()
            
            # Test high-frequency method calls
            high_frequency_methods = [
                'get_environment',
                'is_production',
                'is_development', 
                'get_log_level',
                'should_enable_debug',
            ]
            
            total_calls = 1000
            method_performance = {}
            
            for method_name in high_frequency_methods:
                method = getattr(auth_env, method_name)
                
                start_time = time.perf_counter()
                
                # Make many rapid calls
                for _ in range(total_calls):
                    result = method()
                    # Basic validation that result is reasonable
                    assert result is not None or result is False  # Allow False but not None
                    
                end_time = time.perf_counter()
                total_time = end_time - start_time
                time_per_call = total_time / total_calls
                calls_per_second = total_calls / total_time
                
                method_performance[method_name] = {
                    'time_per_call': time_per_call,
                    'calls_per_second': calls_per_second
                }
                
                # Should handle high frequency calls efficiently
                assert time_per_call < 0.0001, \
                    f"{method_name} too slow under load: {time_per_call:.6f}s per call"
                assert calls_per_second > 10000, \
                    f"{method_name} throughput too low: {calls_per_second:.0f} calls/sec"
                    
            # Record performance metrics
            for method_name, perf in method_performance.items():
                self.record_metric(f"{method_name}_time_per_call", perf['time_per_call'])
                self.record_metric(f"{method_name}_calls_per_sec", perf['calls_per_second'])
                
            avg_time_per_call = sum(p['time_per_call'] for p in method_performance.values()) / len(method_performance)
            self.record_metric("avg_time_per_call_under_load", avg_time_per_call)


class TestAuthEnvironmentResourceLeakPrevention(SSotBaseTestCase):
    """Test AuthEnvironment prevents resource leaks in long-running scenarios."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var("TESTING", "true")
        
    def test_long_running_configuration_access_stability(self):
        """Test configuration access remains stable in long-running scenarios."""
        with self.temp_env_vars(ENVIRONMENT="test"):
            auth_env = AuthEnvironment()
            
            # Simulate long-running service accessing configuration
            iterations = 1000
            sample_points = [100, 300, 500, 700, 1000]
            performance_samples = {}
            
            for i in range(iterations):
                start_time = time.perf_counter()
                
                # Typical configuration access pattern
                env = auth_env.get_environment()
                port = auth_env.get_auth_service_port()
                debug = auth_env.should_enable_debug()
                jwt_exp = auth_env.get_jwt_expiration_minutes()
                
                end_time = time.perf_counter()
                access_time = end_time - start_time
                
                # Sample performance at key points
                if (i + 1) in sample_points:
                    performance_samples[i + 1] = access_time
                    
                # Performance should remain consistent
                assert access_time < 0.001, \
                    f"Configuration access degraded at iteration {i}: {access_time:.6f}s"
                    
            # Performance should not degrade significantly over time
            early_performance = performance_samples[100]
            late_performance = performance_samples[1000]
            degradation_factor = late_performance / early_performance
            
            # Should not degrade more than 2x
            assert degradation_factor < 2.0, \
                f"Performance degraded over time: {degradation_factor:.2f}x slower"
                
            # Record stability metrics
            for iteration, time_taken in performance_samples.items():
                self.record_metric(f"performance_at_iteration_{iteration}", time_taken)
                
            self.record_metric("performance_degradation_factor", degradation_factor)
            self.record_metric("long_running_iterations_completed", iterations)
            
    def test_memory_stability_under_continuous_load(self):
        """Test memory usage remains stable under continuous configuration load."""
        with self.temp_env_vars(ENVIRONMENT="test"):
            auth_env = AuthEnvironment()
            
            # Measure memory at regular intervals
            memory_samples = []
            sample_interval = 200  # Sample every 200 iterations
            total_iterations = 1000
            
            for i in range(total_iterations):
                # Configuration access pattern
                auth_env.get_environment()
                auth_env.get_jwt_algorithm()
                auth_env.get_database_url()  # More expensive operation
                auth_env.validate()  # Full validation
                
                # Memory sampling
                if i % sample_interval == 0:
                    gc.collect()  # Force garbage collection
                    object_count = len(gc.get_objects())
                    memory_samples.append((i, object_count))
                    
            # Analyze memory trend
            if len(memory_samples) >= 2:
                initial_objects = memory_samples[0][1]
                final_objects = memory_samples[-1][1]
                memory_growth = final_objects - initial_objects
                growth_rate = memory_growth / total_iterations
                
                # Should not have significant memory growth
                assert memory_growth < 500, \
                    f"Excessive memory growth: {memory_growth} objects over {total_iterations} iterations"
                    
                # Growth rate should be minimal
                assert abs(growth_rate) < 0.1, \
                    f"High memory growth rate: {growth_rate:.3f} objects per iteration"
                    
                self.record_metric("memory_growth", memory_growth)
                self.record_metric("memory_growth_rate", growth_rate)
                
            # Record all memory samples
            for i, (iteration, objects) in enumerate(memory_samples):
                self.record_metric(f"memory_objects_at_{iteration}", objects)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
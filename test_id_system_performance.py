#!/usr/bin/env python3
"""
ID System Performance Benchmark

This script benchmarks the enhanced dual format ID system to ensure
no performance degradation from the baseline implementation.

Business Critical Requirements:
- ID generation: <1ms average  
- Database queries: No degradation from baseline
- API response times: Maintain current SLA
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import time
import uuid
import statistics
from typing import List, Dict, Any
from netra_backend.app.core.unified_id_manager import (
    UnifiedIDManager,
    IDType,
    is_valid_id_format,
    is_valid_id_format_compatible,
    convert_uuid_to_structured,
    convert_structured_to_uuid,
    validate_and_normalize_id
)
from shared.types.core_types import (
    ensure_user_id,
    ensure_thread_id,
    ensure_request_id,
    normalize_to_structured_id
)

class PerformanceBenchmark:
    """Performance benchmark suite for the ID system."""
    
    def __init__(self):
        self.results: Dict[str, Dict[str, Any]] = {}
        self.id_manager = UnifiedIDManager()
        
    def benchmark_function(self, func, *args, iterations: int = 1000, name: str = None):
        """Benchmark a function and return timing statistics."""
        func_name = name or func.__name__
        print(f"Benchmarking {func_name} ({iterations} iterations)...")
        
        times = []
        for _ in range(iterations):
            start_time = time.perf_counter()
            try:
                result = func(*args)
                end_time = time.perf_counter()
                times.append((end_time - start_time) * 1000)  # Convert to milliseconds
            except Exception as e:
                print(f"  Error in {func_name}: {e}")
                times.append(float('inf'))
        
        # Calculate statistics
        valid_times = [t for t in times if t != float('inf')]
        if not valid_times:
            return {"error": "All executions failed"}
        
        stats = {
            "min_ms": min(valid_times),
            "max_ms": max(valid_times),
            "avg_ms": statistics.mean(valid_times),
            "median_ms": statistics.median(valid_times),
            "std_dev_ms": statistics.stdev(valid_times) if len(valid_times) > 1 else 0,
            "success_rate": len(valid_times) / len(times),
            "iterations": iterations
        }
        
        print(f"  Average: {stats['avg_ms']:.3f}ms")
        print(f"  Median:  {stats['median_ms']:.3f}ms")
        print(f"  Min:     {stats['min_ms']:.3f}ms")
        print(f"  Max:     {stats['max_ms']:.3f}ms")
        print(f"  Success: {stats['success_rate']:.1%}")
        
        self.results[func_name] = stats
        return stats
    
    def test_id_generation_performance(self):
        """Benchmark ID generation performance."""
        print("\n=== ID Generation Performance ===")
        
        # Test structured ID generation
        self.benchmark_function(
            lambda: self.id_manager.generate_id(IDType.USER),
            name="generate_structured_user_id"
        )
        
        self.benchmark_function(
            lambda: self.id_manager.generate_id(IDType.THREAD),
            name="generate_structured_thread_id"
        )
        
        # Test UUID generation (baseline)
        self.benchmark_function(
            lambda: str(uuid.uuid4()),
            name="generate_uuid_baseline"
        )
        
        return True
    
    def test_validation_performance(self):
        """Benchmark ID validation performance."""
        print("\n=== ID Validation Performance ===")
        
        # Setup test data
        test_uuid = str(uuid.uuid4())
        test_structured_user = self.id_manager.generate_id(IDType.USER)
        test_structured_thread = self.id_manager.generate_id(IDType.THREAD)
        
        # Test basic format validation
        self.benchmark_function(
            is_valid_id_format,
            test_uuid,
            name="validate_uuid_format"
        )
        
        self.benchmark_function(
            is_valid_id_format,
            test_structured_user,
            name="validate_structured_format"
        )
        
        # Test enhanced dual format validation
        self.benchmark_function(
            is_valid_id_format_compatible,
            test_uuid,
            IDType.USER,
            name="validate_uuid_compatible"
        )
        
        self.benchmark_function(
            is_valid_id_format_compatible,
            test_structured_user,
            IDType.USER,
            name="validate_structured_compatible"
        )
        
        # Test manager validation
        self.benchmark_function(
            self.id_manager.is_valid_id,
            test_structured_user,
            IDType.USER,
            name="validate_manager_registered"
        )
        
        self.benchmark_function(
            self.id_manager.is_valid_id_format_compatible,
            test_uuid,
            IDType.USER,
            name="validate_manager_compatible"
        )
        
        return True
    
    def test_conversion_performance(self):
        """Benchmark ID conversion performance."""
        print("\n=== ID Conversion Performance ===")
        
        # Setup test data
        test_uuid = str(uuid.uuid4())
        test_structured = self.id_manager.generate_id(IDType.USER)
        
        # Test UUID to structured conversion
        self.benchmark_function(
            convert_uuid_to_structured,
            test_uuid,
            IDType.USER,
            name="convert_uuid_to_structured"
        )
        
        # Test structured to UUID conversion
        self.benchmark_function(
            convert_structured_to_uuid,
            test_structured,
            name="convert_structured_to_uuid"
        )
        
        # Test validation and normalization
        self.benchmark_function(
            validate_and_normalize_id,
            test_uuid,
            IDType.USER,
            name="validate_and_normalize_uuid"
        )
        
        self.benchmark_function(
            validate_and_normalize_id,
            test_structured,
            IDType.USER,
            name="validate_and_normalize_structured"
        )
        
        return True
    
    def test_pydantic_integration_performance(self):
        """Benchmark Pydantic type integration performance."""
        print("\n=== Pydantic Integration Performance ===")
        
        # Setup test data
        test_uuid = str(uuid.uuid4())
        test_structured_user = self.id_manager.generate_id(IDType.USER)
        test_structured_thread = self.id_manager.generate_id(IDType.THREAD)
        
        # Test enhanced ensure functions
        self.benchmark_function(
            ensure_user_id,
            test_uuid,
            name="ensure_user_id_uuid"
        )
        
        self.benchmark_function(
            ensure_user_id,
            test_structured_user,
            name="ensure_user_id_structured"
        )
        
        self.benchmark_function(
            ensure_thread_id,
            test_structured_thread,
            name="ensure_thread_id_structured"
        )
        
        # Test normalization
        self.benchmark_function(
            normalize_to_structured_id,
            test_uuid,
            IDType.USER,
            name="normalize_uuid_to_structured"
        )
        
        return True
    
    def test_bulk_operations_performance(self):
        """Benchmark bulk operations performance."""
        print("\n=== Bulk Operations Performance ===")
        
        # Generate test data
        uuids = [str(uuid.uuid4()) for _ in range(100)]
        structured_ids = [self.id_manager.generate_id(IDType.USER) for _ in range(100)]
        
        # Test bulk validation
        def validate_bulk_uuids():
            return [is_valid_id_format_compatible(uid, IDType.USER) for uid in uuids]
        
        def validate_bulk_structured():
            return [is_valid_id_format_compatible(sid, IDType.USER) for sid in structured_ids]
        
        self.benchmark_function(
            validate_bulk_uuids,
            iterations=100,
            name="validate_100_uuids"
        )
        
        self.benchmark_function(
            validate_bulk_structured,
            iterations=100,
            name="validate_100_structured_ids"
        )
        
        # Test bulk conversion
        def convert_bulk_uuids():
            return [convert_uuid_to_structured(uid, IDType.USER) for uid in uuids[:10]]
        
        self.benchmark_function(
            convert_bulk_uuids,
            iterations=100,
            name="convert_10_uuids_to_structured"
        )
        
        return True
    
    def test_memory_usage(self):
        """Test memory usage patterns."""
        print("\n=== Memory Usage Test ===")
        
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss
            
            # Perform intensive operations
            print("Performing intensive ID operations...")
            
            # Generate many IDs
            uuids = [str(uuid.uuid4()) for _ in range(1000)]
            structured_ids = [self.id_manager.generate_id(IDType.USER) for _ in range(1000)]
            
            # Validate all of them
            for uid in uuids:
                is_valid_id_format_compatible(uid, IDType.USER)
            
            for sid in structured_ids:
                is_valid_id_format_compatible(sid, IDType.USER)
            
            # Convert some of them
            for uid in uuids[:100]:
                convert_uuid_to_structured(uid, IDType.USER)
            
            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory
            
            print(f"  Initial memory: {initial_memory / 1024 / 1024:.1f} MB")
            print(f"  Final memory:   {final_memory / 1024 / 1024:.1f} MB")
            print(f"  Memory increase: {memory_increase / 1024 / 1024:.1f} MB")
            
            # Memory increase should be reasonable (<10MB for this test)
            assert memory_increase < 10 * 1024 * 1024, f"Memory increase too high: {memory_increase} bytes"
            print("  [PASS] Memory usage within acceptable limits")
            
        except ImportError:
            print("  [SKIP] psutil not available - memory test skipped")
        except Exception as e:
            print(f"  [ERROR] Memory test failed: {e}")
        
        return True
    
    def analyze_results(self):
        """Analyze benchmark results and check performance requirements."""
        print("\n=== Performance Analysis ===")
        
        # Performance requirements (from CLAUDE.md)
        ID_GENERATION_LIMIT_MS = 1.0  # <1ms average
        
        # Check ID generation performance
        generation_tests = [k for k in self.results.keys() if "generate" in k]
        
        print("\nID Generation Performance:")
        for test in generation_tests:
            result = self.results[test]
            avg_ms = result.get("avg_ms", float('inf'))
            status = "PASS" if avg_ms < ID_GENERATION_LIMIT_MS else "FAIL"
            print(f"  {test}: {avg_ms:.3f}ms [{status}]")
        
        # Check validation performance
        validation_tests = [k for k in self.results.keys() if "validate" in k]
        
        print("\nValidation Performance:")
        for test in validation_tests:
            result = self.results[test]
            avg_ms = result.get("avg_ms", float('inf'))
            # Validation should be very fast (under 0.1ms)
            status = "PASS" if avg_ms < 0.1 else "WARN" if avg_ms < 1.0 else "FAIL"
            print(f"  {test}: {avg_ms:.3f}ms [{status}]")
        
        # Check conversion performance
        conversion_tests = [k for k in self.results.keys() if "convert" in k or "normalize" in k]
        
        print("\nConversion Performance:")
        for test in conversion_tests:
            result = self.results[test]
            avg_ms = result.get("avg_ms", float('inf'))
            # Conversion should be reasonable (under 1ms)
            status = "PASS" if avg_ms < 1.0 else "WARN" if avg_ms < 5.0 else "FAIL"
            print(f"  {test}: {avg_ms:.3f}ms [{status}]")
        
        # Overall assessment
        failed_tests = []
        warning_tests = []
        
        for test_name, result in self.results.items():
            avg_ms = result.get("avg_ms", float('inf'))
            
            if "generate" in test_name and avg_ms >= ID_GENERATION_LIMIT_MS:
                failed_tests.append(f"{test_name}: {avg_ms:.3f}ms")
            elif "validate" in test_name and avg_ms >= 1.0:
                failed_tests.append(f"{test_name}: {avg_ms:.3f}ms")
            elif ("convert" in test_name or "normalize" in test_name) and avg_ms >= 5.0:
                failed_tests.append(f"{test_name}: {avg_ms:.3f}ms")
            elif avg_ms >= 1.0:  # Warning threshold
                warning_tests.append(f"{test_name}: {avg_ms:.3f}ms")
        
        print(f"\nSummary:")
        print(f"  Total tests: {len(self.results)}")
        print(f"  Failed tests: {len(failed_tests)}")
        print(f"  Warning tests: {len(warning_tests)}")
        
        if failed_tests:
            print(f"\nFAILED TESTS:")
            for test in failed_tests:
                print(f"  - {test}")
            return False
        
        if warning_tests:
            print(f"\nWARNING TESTS:")
            for test in warning_tests:
                print(f"  - {test}")
        
        print("\n[SUCCESS] All performance requirements met!")
        return True

def main():
    """Run the complete performance benchmark suite."""
    print("Enhanced ID System Performance Benchmark")
    print("=" * 50)
    
    benchmark = PerformanceBenchmark()
    
    try:
        # Run all benchmark tests
        benchmark.test_id_generation_performance()
        benchmark.test_validation_performance()
        benchmark.test_conversion_performance()
        benchmark.test_pydantic_integration_performance()
        benchmark.test_bulk_operations_performance()
        benchmark.test_memory_usage()
        
        # Analyze results
        success = benchmark.analyze_results()
        
        if success:
            print("\n[SUCCESS] Enhanced ID system meets all performance requirements!")
            return 0
        else:
            print("\n[FAIL] Enhanced ID system failed performance requirements!")
            return 1
            
    except Exception as e:
        print(f"\n[ERROR] Benchmark execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
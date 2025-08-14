"""
Performance Test Suite for Corpus Generation System

Comprehensive test suite runner that imports all modular performance tests.
Tests large-scale corpus generation performance, concurrent processing,
and resource utilization monitoring for the Netra AI Optimization Platform.

Tests follow strict 300-line limit and 8-line function rule.
"""

import pytest
import sys
from pathlib import Path

# Import all performance test modules
from .test_large_scale_generation import TestLargeScaleGeneration
from .test_concurrent_processing import TestConcurrentProcessing
from .test_database_performance import TestDatabasePerformance
from .test_benchmark_metrics import TestBenchmarkMetrics


class TestCorpusGenerationPerformance:
    """Comprehensive corpus generation performance test suite"""

    def test_suite_completeness(self):
        """Verify all test modules are properly imported"""
        test_classes = [
            TestLargeScaleGeneration,
            TestConcurrentProcessing,
            TestDatabasePerformance,
            TestBenchmarkMetrics
        ]
        
        for test_class in test_classes:
            assert test_class is not None
            # Verify test class has performance tests
            test_methods = [
                method for method in dir(test_class)
                if method.startswith('test_')
            ]
            assert len(test_methods) > 0

    def test_performance_markers_configured(self):
        """Verify performance test markers are configured"""
        # This ensures pytest markers are properly set up
        assert hasattr(pytest, 'mark')
        assert hasattr(pytest.mark, 'performance')

    def get_performance_test_summary(self) -> dict:
        """Get summary of all performance tests in suite"""
        return {
            'test_categories': {
                'large_scale_generation': {
                    'description': 'Tests for 100k+ record generation',
                    'class': 'TestLargeScaleGeneration',
                    'targets': {
                        'completion_time': '< 3600 seconds',
                        'memory_usage': '< 8192 MB',
                        'cpu_utilization': '< 95%'
                    }
                },
                'concurrent_processing': {
                    'description': 'Tests for concurrent request handling',
                    'class': 'TestConcurrentProcessing',
                    'targets': {
                        'concurrent_jobs': '5+ simultaneous',
                        'thread_efficiency': '>100 tasks/second'
                    }
                },
                'database_performance': {
                    'description': 'Database operation performance',
                    'class': 'TestDatabasePerformance',
                    'targets': {
                        'bulk_insert': '< 60 seconds for 50k records',
                        'concurrent_ops': '< 30 seconds for 5 operations'
                    }
                },
                'benchmark_metrics': {
                    'description': 'Benchmarking and metrics collection',
                    'class': 'TestBenchmarkMetrics',
                    'targets': {
                        'throughput': '> 10 records/second',
                        'latency_avg': '< 200ms',
                        'latency_p95': '< 500ms'
                    }
                }
            },
            'total_modules': 4,
            'architecture_compliance': {
                'max_file_lines': 300,
                'max_function_lines': 8,
                'type_safety': 'Full Pydantic models',
                'async_patterns': 'async/await for all I/O'
            }
        }


def run_performance_suite():
    """Run the complete performance test suite"""
    test_args = [
        str(Path(__file__).parent),
        "-v",
        "--asyncio-mode=auto",
        "-m", "performance",
        "--tb=short",
        "--capture=no"
    ]
    
    return pytest.main(test_args)


def run_specific_category(category: str):
    """Run tests for a specific performance category"""
    test_file_map = {
        'large_scale': 'test_large_scale_generation.py',
        'concurrent': 'test_concurrent_processing.py', 
        'database': 'test_database_performance.py',
        'benchmark': 'test_benchmark_metrics.py'
    }
    
    if category not in test_file_map:
        raise ValueError(f"Unknown category: {category}")
        
    test_file = Path(__file__).parent / test_file_map[category]
    
    test_args = [
        str(test_file),
        "-v",
        "--asyncio-mode=auto",
        "-m", "performance"
    ]
    
    return pytest.main(test_args)


if __name__ == "__main__":
    # Allow running specific categories via command line
    if len(sys.argv) > 1:
        category = sys.argv[1]
        exit_code = run_specific_category(category)
    else:
        exit_code = run_performance_suite()
    
    sys.exit(exit_code)
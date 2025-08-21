#!/usr/bin/env python3
"""
Performance Test Runner for Corpus Generation

Runs comprehensive performance tests with resource monitoring and reporting.
Generates performance metrics and benchmarking reports.
"""

import sys
import os
import time
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List

import psutil
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class PerformanceTestRunner:
    """Manages performance test execution and reporting"""

    def __init__(self, output_dir: str = "test_reports/performance"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.start_time = None
        self.metrics = {}

    def run_performance_tests(self, test_args: List[str] = None) -> Dict[str, Any]:
        """Run performance tests with monitoring"""
        if test_args is None:
            test_args = []

        self._start_monitoring()
        
        # Default performance test configuration
        default_args = [
            str(Path(__file__).parent / "test_corpus_generation_perf.py"),
            "-v",
            "--asyncio-mode=auto", 
            "-m", "performance",
            "--tb=short",
            "--capture=no"
        ]
        
        test_args = default_args + test_args
        
        try:
            exit_code = pytest.main(test_args)
            self._stop_monitoring()
            
            report = self._generate_performance_report(exit_code)
            self._save_report(report)
            
            return report
            
        except Exception as e:
            self._stop_monitoring()
            print(f"Error running performance tests: {e}")
            return {"status": "error", "message": str(e)}

    def _start_monitoring(self):
        """Start system resource monitoring"""
        self.start_time = time.time()
        self.initial_memory = psutil.virtual_memory().used / 1024 / 1024
        self.initial_cpu = psutil.cpu_percent()
        
    def _stop_monitoring(self):
        """Stop monitoring and collect metrics"""
        end_time = time.time()
        final_memory = psutil.virtual_memory().used / 1024 / 1024
        
        self.metrics = {
            'execution_time_seconds': end_time - self.start_time,
            'memory_usage_mb': final_memory - self.initial_memory,
            'cpu_percent_avg': psutil.cpu_percent(interval=1),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }

    def _generate_performance_report(self, exit_code: int) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            'test_run': {
                'timestamp': self.metrics.get('timestamp', time.strftime('%Y-%m-%d %H:%M:%S')),
                'status': 'passed' if exit_code == 0 else 'failed',
                'exit_code': exit_code
            },
            'system_metrics': self.metrics,
            'test_categories': {
                'large_scale_generation': {
                    'description': 'Tests for 100k+ record generation',
                    'performance_targets': {
                        'completion_time': '< 3600 seconds',
                        'memory_usage': '< 8192 MB',
                        'cpu_utilization': '< 95%'
                    }
                },
                'concurrent_processing': {
                    'description': 'Tests for concurrent request handling',
                    'performance_targets': {
                        'concurrent_jobs': '5+ simultaneous',
                        'resource_contention': 'Graceful handling',
                        'thread_efficiency': '>100 tasks/second'
                    }
                },
                'database_performance': {
                    'description': 'Database operation performance',
                    'performance_targets': {
                        'bulk_insert': '< 60 seconds for 50k records',
                        'concurrent_ops': '< 30 seconds for 5 operations'
                    }
                }
            },
            'benchmarks': self._collect_benchmark_results()
        }
        
        return report

    def _collect_benchmark_results(self) -> Dict[str, Any]:
        """Collect benchmark results from test execution"""
        # This would be enhanced to parse actual test results
        return {
            'throughput': {
                'records_per_second': 'measured_during_test',
                'target': '> 10 records/second'
            },
            'latency': {
                'average_ms': 'measured_during_test',
                'p95_ms': 'measured_during_test',
                'targets': {
                    'average': '< 200ms',
                    'p95': '< 500ms'
                }
            }
        }

    def _save_report(self, report: Dict[str, Any]):
        """Save performance report to file"""
        report_file = self.output_dir / f"performance_report_{int(time.time())}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"Performance report saved to: {report_file}")
        
        # Also save as latest report
        latest_file = self.output_dir / "latest_performance_report.json"
        with open(latest_file, 'w') as f:
            json.dump(report, f, indent=2)


def generate_performance_summary():
    """Generate performance test summary"""
    print("\n" + "="*60)
    print("CORPUS GENERATION PERFORMANCE TESTS")
    print("="*60)
    print("\nTest Categories:")
    print("• Large Scale Generation (100k+ records)")
    print("• Concurrent Processing")
    print("• Resource Utilization Monitoring")
    print("• Database Performance Under Load")
    print("• Benchmarking and Metrics Collection")
    print("\nPerformance Targets:")
    print("• Memory usage < 8GB for large generation")
    print("• CPU utilization < 95%")
    print("• Throughput > 10 records/second")
    print("• Latency < 200ms average")
    print("="*60)


def main():
    """Main entry point for performance test runner"""
    parser = argparse.ArgumentParser(description='Run corpus generation performance tests')
    parser.add_argument('--output-dir', default='test_reports/performance',
                      help='Directory for test reports')
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='Verbose output')
    parser.add_argument('--benchmark-only', action='store_true',
                      help='Run only benchmark tests')
    
    args = parser.parse_args()
    
    generate_performance_summary()
    
    runner = PerformanceTestRunner(args.output_dir)
    
    test_args = []
    if args.verbose:
        test_args.extend(['-v', '-s'])
    if args.benchmark_only:
        test_args.extend(['-m', 'benchmark'])
    
    report = runner.run_performance_tests(test_args)
    
    print(f"\nTest execution completed with status: {report['test_run']['status']}")
    print(f"System metrics collected and saved to: {args.output_dir}")
    
    return 0 if report['test_run']['status'] == 'passed' else 1


if __name__ == "__main__":
    sys.exit(main())
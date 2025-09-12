#!/usr/bin/env python3
"""
Performance Test Runner for UserExecutionContext Migration

This script provides a comprehensive test runner for all performance validation tests,
generating detailed reports and metrics for the Phase 1 migration.

Usage:
    python run_performance_tests.py --all
    python run_performance_tests.py --context-only
    python run_performance_tests.py --database-only
    python run_performance_tests.py --generate-report
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import pytest
    import psutil
    from netra_backend.app.logging_config import central_logger
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure all dependencies are installed:")
    print("pip install pytest psutil")
    sys.exit(1)

logger = central_logger.get_logger(__name__)


class PerformanceTestRunner:
    """Comprehensive performance test runner."""
    
    def __init__(self):
        self.test_results = []
        self.start_time = None
        self.end_time = None
        self.system_info = self._get_system_info()
        
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for test environment."""
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'python_version': sys.version,
            'platform': sys.platform,
            'cpu_count': os.cpu_count(),
            'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
            'working_directory': str(Path.cwd())
        }
    
    def run_context_performance_tests(self) -> Dict[str, Any]:
        """Run UserExecutionContext performance tests."""
        logger.info("Running UserExecutionContext performance tests...")
        
        test_file = Path(__file__).parent / "test_phase1_context_performance.py"
        
        # Run pytest with detailed output
        exit_code = pytest.main([
            str(test_file),
            "-v",
            "--tb=short",
            "--durations=10",
            "--capture=no"
        ])
        
        return {
            'test_suite': 'UserExecutionContext Performance',
            'exit_code': exit_code,
            'status': 'PASSED' if exit_code == 0 else 'FAILED',
            'test_file': str(test_file)
        }
    
    def run_database_performance_tests(self) -> Dict[str, Any]:
        """Run database performance tests."""
        logger.info("Running database performance tests...")
        
        test_file = Path(__file__).parent / "test_database_performance.py"
        
        # Run pytest with detailed output
        exit_code = pytest.main([
            str(test_file),
            "-v",
            "--tb=short",
            "--durations=10",
            "--capture=no"
        ])
        
        return {
            'test_suite': 'Database Performance',
            'exit_code': exit_code,
            'status': 'PASSED' if exit_code == 0 else 'FAILED',
            'test_file': str(test_file)
        }
    
    def run_all_performance_tests(self) -> List[Dict[str, Any]]:
        """Run all performance test suites."""
        logger.info("Starting comprehensive performance test run...")
        self.start_time = time.time()
        
        results = []
        
        try:
            # Run context performance tests
            context_results = self.run_context_performance_tests()
            results.append(context_results)
            
            # Run database performance tests
            database_results = self.run_database_performance_tests()
            results.append(database_results)
            
        except Exception as e:
            logger.error(f"Error running performance tests: {e}")
            results.append({
                'test_suite': 'Error',
                'exit_code': 1,
                'status': 'ERROR',
                'error': str(e)
            })
        
        self.end_time = time.time()
        self.test_results = results
        
        return results
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        logger.info("Generating performance test report...")
        
        total_duration = (self.end_time - self.start_time) if self.start_time and self.end_time else 0
        
        # Count test results
        passed_suites = len([r for r in self.test_results if r.get('status') == 'PASSED'])
        failed_suites = len([r for r in self.test_results if r.get('status') == 'FAILED'])
        error_suites = len([r for r in self.test_results if r.get('status') == 'ERROR'])
        
        report = {
            'performance_test_summary': {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'total_duration_seconds': total_duration,
                'test_suites_run': len(self.test_results),
                'suites_passed': passed_suites,
                'suites_failed': failed_suites,
                'suites_error': error_suites,
                'overall_status': 'PASSED' if failed_suites == 0 and error_suites == 0 else 'FAILED'
            },
            'system_information': self.system_info,
            'test_suite_results': self.test_results,
            'performance_thresholds': self._get_performance_thresholds(),
            'recommendations': self._generate_recommendations()
        }
        
        return report
    
    def _get_performance_thresholds(self) -> Dict[str, Any]:
        """Get performance thresholds for validation."""
        return {
            'context_creation': {
                'max_duration_ms_per_1k': 500,
                'max_memory_delta_mb_per_1k': 10,
                'min_creation_rate_per_sec': 2000
            },
            'concurrent_requests': {
                'min_success_rate_percent': 95,
                'max_p95_response_time_ms': 500,
                'max_memory_growth_mb': 100
            },
            'database_operations': {
                'min_transaction_throughput_per_sec': 100,
                'max_connection_leak_percent': 0,
                'min_connection_reuse_percent': 90
            },
            'memory_leak_detection': {
                'max_memory_growth_mb_per_1k_requests': 20,
                'min_gc_effectiveness_percent': 80
            },
            'websocket_performance': {
                'min_events_per_second': 1000,
                'max_event_dispatch_time_ms': 1
            }
        }
    
    def _generate_recommendations(self) -> List[Dict[str, str]]:
        """Generate performance recommendations based on results."""
        recommendations = []
        
        if any(r.get('status') == 'FAILED' for r in self.test_results):
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Test Failures',
                'recommendation': 'Investigate and fix failing performance tests before deployment'
            })
        
        recommendations.extend([
            {
                'priority': 'MEDIUM',
                'category': 'Monitoring',
                'recommendation': 'Implement continuous performance monitoring in production'
            },
            {
                'priority': 'MEDIUM',
                'category': 'Optimization',
                'recommendation': 'Consider implementing context pooling to reduce creation overhead'
            },
            {
                'priority': 'LOW',
                'category': 'Enhancement',
                'recommendation': 'Add real-time performance dashboards for operational visibility'
            }
        ])
        
        return recommendations
    
    def save_report(self, report: Dict[str, Any], filename: str = None) -> str:
        """Save performance report to file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_test_report_{timestamp}.json"
        
        report_path = Path(__file__).parent.parent.parent / filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Performance report saved to: {report_path}")
        return str(report_path)
    
    def print_summary(self) -> None:
        """Print performance test summary to console."""
        if not self.test_results:
            print("No test results available")
            return
        
        print("\n" + "="*80)
        print("PERFORMANCE TEST EXECUTION SUMMARY")
        print("="*80)
        
        total_duration = (self.end_time - self.start_time) if self.start_time and self.end_time else 0
        
        print(f"Execution Time: {total_duration:.2f} seconds")
        print(f"Test Suites Run: {len(self.test_results)}")
        print(f"System: {self.system_info.get('platform')} | "
              f"CPUs: {self.system_info.get('cpu_count')} | "
              f"Memory: {self.system_info.get('memory_total_gb', 0):.1f}GB")
        print()
        
        for result in self.test_results:
            status_icon = " PASS: " if result.get('status') == 'PASSED' else " FAIL: "
            print(f"{status_icon} {result.get('test_suite', 'Unknown')}: {result.get('status', 'UNKNOWN')}")
        
        print("\n" + "="*80)
        
        # Overall status
        overall_status = all(r.get('status') == 'PASSED' for r in self.test_results)
        status_message = "ALL TESTS PASSED" if overall_status else "SOME TESTS FAILED"
        status_icon = " PASS: " if overall_status else " FAIL: "
        
        print(f"{status_icon} OVERALL STATUS: {status_message}")
        print("="*80)


def main():
    """Main entry point for performance test runner."""
    parser = argparse.ArgumentParser(
        description="Performance Test Runner for UserExecutionContext Migration"
    )
    
    parser.add_argument(
        '--all', 
        action='store_true',
        help='Run all performance test suites'
    )
    
    parser.add_argument(
        '--context-only',
        action='store_true',
        help='Run only UserExecutionContext performance tests'
    )
    
    parser.add_argument(
        '--database-only',
        action='store_true',
        help='Run only database performance tests'
    )
    
    parser.add_argument(
        '--generate-report',
        action='store_true',
        help='Generate detailed performance report after tests'
    )
    
    parser.add_argument(
        '--output-file',
        type=str,
        help='Output file for performance report (JSON format)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Default to running all tests if no specific option is provided
    if not any([args.all, args.context_only, args.database_only]):
        args.all = True
    
    runner = PerformanceTestRunner()
    
    try:
        if args.all:
            results = runner.run_all_performance_tests()
        elif args.context_only:
            result = runner.run_context_performance_tests()
            results = [result]
            runner.test_results = results
        elif args.database_only:
            result = runner.run_database_performance_tests()
            results = [result]
            runner.test_results = results
        else:
            print("No test suite specified")
            return 1
        
        # Print summary
        runner.print_summary()
        
        # Generate detailed report if requested
        if args.generate_report:
            report = runner.generate_performance_report()
            report_file = runner.save_report(report, args.output_file)
            
            print(f"\n CHART:  Detailed performance report generated: {report_file}")
            
            # Print key metrics
            summary = report['performance_test_summary']
            print(f"[U+1F4C8] Test Duration: {summary['total_duration_seconds']:.2f}s")
            print(f"[U+1F4CB] Suites: {summary['suites_passed']}/{summary['test_suites_run']} passed")
            print(f" TARGET:  Overall Status: {summary['overall_status']}")
        
        # Return appropriate exit code
        overall_success = all(r.get('status') == 'PASSED' for r in results)
        return 0 if overall_success else 1
        
    except KeyboardInterrupt:
        print("\n WARNING: [U+FE0F]  Performance tests interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Error running performance tests: {e}")
        print(f" FAIL:  Error running performance tests: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
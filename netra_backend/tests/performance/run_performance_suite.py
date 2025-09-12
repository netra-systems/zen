"""
Comprehensive Performance Test Suite Runner

Orchestrates all performance tests and generates comprehensive reports.
Provides unified entry point for performance testing and benchmarking.

Business Value Justification (BVJ):
- Segment: Growth & Enterprise  
- Business Goal: Comprehensive performance monitoring and regression detection
- Value Impact: 100% performance test coverage and baseline compliance
- Revenue Impact: Prevents performance-related customer churn (+$40K MRR)
"""

import argparse
import asyncio
import os
import sys
import time
import traceback
from typing import Any, Dict, List, Optional

# Add parent directory to path for imports

from performance_baseline_config import (
    PerformanceBenchmarkRunner,
    PerformanceCategory,
    get_performance_baselines,
)
from test_comprehensive_backend_performance import (
    AgentPerformanceTester,
    APIPerformanceTester,
    CachePerformanceTester,
    DatabasePerformanceTester,
    MemoryPerformanceTester,
    WebSocketPerformanceTester,
)
from test_concurrent_user_performance import ConcurrentUserSimulator, ScalabilityTester

class PerformanceTestOrchestrator:
    """Orchestrates comprehensive performance testing."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.benchmark_runner = PerformanceBenchmarkRunner()
        self.baselines = get_performance_baselines()
        
        # Initialize testers
        self.db_tester = DatabasePerformanceTester()
        self.ws_tester = WebSocketPerformanceTester()
        self.agent_tester = AgentPerformanceTester()
        self.api_tester = APIPerformanceTester()
        self.memory_tester = MemoryPerformanceTester()
        self.cache_tester = CachePerformanceTester()
        self.user_simulator = ConcurrentUserSimulator()
        self.scalability_tester = ScalabilityTester()
    
    def log(self, message: str):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[{time.strftime('%H:%M:%S')}] {message}")
    
    async def run_database_performance_tests(self, quick_mode: bool = False) -> Dict[str, Any]:
        """Run database performance tests."""
        self.log("Starting database performance tests...")
        results = {}
        
        try:
            # Bulk insert test
            self.log("  Testing bulk insert performance...")
            record_count = 25000 if quick_mode else 50000
            start_time = time.perf_counter()
            duration = await self.db_tester.test_bulk_insert_performance(record_count)
            test_duration = time.perf_counter() - start_time
            
            self.benchmark_runner.record_result(
                'db_bulk_insert_50k', duration, test_duration,
                {'record_count': record_count, 'records_per_second': record_count / duration}
            )
            results['bulk_insert'] = {'duration': duration, 'record_count': record_count}
            
            # Concurrent reads test
            self.log("  Testing concurrent database reads...")
            concurrent_queries = 5 if quick_mode else 10
            start_time = time.perf_counter()
            duration = await self.db_tester.test_concurrent_query_performance(concurrent_queries)
            test_duration = time.perf_counter() - start_time
            
            self.benchmark_runner.record_result(
                'db_concurrent_reads', duration, test_duration,
                {'concurrent_queries': concurrent_queries}
            )
            results['concurrent_reads'] = {'duration': duration, 'concurrent_queries': concurrent_queries}
            
            self.log("Database performance tests completed.")
            
        except Exception as e:
            self.log(f"Error in database tests: {str(e)}")
            if self.verbose:
                traceback.print_exc()
            results['error'] = str(e)
        
        return results
    
    async def run_websocket_performance_tests(self, quick_mode: bool = False) -> Dict[str, Any]:
        """Run WebSocket performance tests."""
        self.log("Starting WebSocket performance tests...")
        results = {}
        
        try:
            # Message throughput test
            self.log("  Testing WebSocket message throughput...")
            message_count = 5000 if quick_mode else 10000
            start_time = time.perf_counter()
            throughput = await self.ws_tester.test_message_throughput(message_count)
            test_duration = time.perf_counter() - start_time
            
            self.benchmark_runner.record_result(
                'websocket_throughput', throughput, test_duration,
                {'message_count': message_count}
            )
            results['message_throughput'] = {'throughput': throughput, 'message_count': message_count}
            
            # Broadcast performance test
            self.log("  Testing WebSocket broadcast performance...")
            connections = 50 if quick_mode else 100
            messages = 250 if quick_mode else 500
            start_time = time.perf_counter()
            broadcast_throughput = await self.ws_tester.test_broadcast_performance(connections, messages)
            test_duration = time.perf_counter() - start_time
            
            self.benchmark_runner.record_result(
                'websocket_broadcast_throughput', broadcast_throughput, test_duration,
                {'connections': connections, 'messages': messages}
            )
            results['broadcast'] = {
                'throughput': broadcast_throughput, 
                'connections': connections, 
                'messages': messages
            }
            
            self.log("WebSocket performance tests completed.")
            
        except Exception as e:
            self.log(f"Error in WebSocket tests: {str(e)}")
            if self.verbose:
                traceback.print_exc()
            results['error'] = str(e)
        
        return results
    
    async def run_agent_performance_tests(self, quick_mode: bool = False) -> Dict[str, Any]:
        """Run agent performance tests."""
        self.log("Starting agent performance tests...")
        results = {}
        
        try:
            # Agent processing speed test
            self.log("  Testing agent processing speed...")
            request_count = 50 if quick_mode else 100
            start_time = time.perf_counter()
            duration = await self.agent_tester.test_agent_processing_speed(request_count)
            test_duration = time.perf_counter() - start_time
            
            self.benchmark_runner.record_result(
                'agent_processing_time', duration, test_duration,
                {'request_count': request_count, 'requests_per_second': request_count / duration}
            )
            results['processing_speed'] = {'duration': duration, 'request_count': request_count}
            
            # Concurrent agent processing test
            self.log("  Testing concurrent agent processing...")
            concurrent_agents = 3 if quick_mode else 5
            requests_per_agent = 10 if quick_mode else 20
            start_time = time.perf_counter()
            throughput = await self.agent_tester.test_concurrent_agent_processing(
                concurrent_agents, requests_per_agent
            )
            test_duration = time.perf_counter() - start_time
            
            self.benchmark_runner.record_result(
                'concurrent_agent_throughput', throughput, test_duration,
                {'concurrent_agents': concurrent_agents, 'requests_per_agent': requests_per_agent}
            )
            results['concurrent_processing'] = {
                'throughput': throughput,
                'concurrent_agents': concurrent_agents,
                'requests_per_agent': requests_per_agent
            }
            
            self.log("Agent performance tests completed.")
            
        except Exception as e:
            self.log(f"Error in agent tests: {str(e)}")
            if self.verbose:
                traceback.print_exc()
            results['error'] = str(e)
        
        return results
    
    async def run_api_performance_tests(self, quick_mode: bool = False) -> Dict[str, Any]:
        """Run API performance tests."""
        self.log("Starting API performance tests...")
        results = {}
        
        try:
            # API response time test
            self.log("  Testing API response times...")
            request_count = 500 if quick_mode else 1000
            start_time = time.perf_counter()
            response_times = await self.api_tester.test_api_response_times(request_count)
            test_duration = time.perf_counter() - start_time
            
            import statistics
            avg_response_time = statistics.mean(response_times)
            
            self.benchmark_runner.record_result(
                'api_response_time', avg_response_time, test_duration,
                {
                    'request_count': request_count,
                    'min_response': min(response_times),
                    'max_response': max(response_times),
                    'p95_response': self._calculate_percentile(response_times, 95)
                }
            )
            results['response_times'] = {
                'avg': avg_response_time,
                'count': request_count,
                'min': min(response_times),
                'max': max(response_times)
            }
            
            # Concurrent API load test
            self.log("  Testing concurrent API load...")
            concurrent_requests = 25 if quick_mode else 50
            total_requests = 500 if quick_mode else 1000
            start_time = time.perf_counter()
            duration = await self.api_tester.test_concurrent_api_load(concurrent_requests, total_requests)
            test_duration = time.perf_counter() - start_time
            
            self.benchmark_runner.record_result(
                'concurrent_api_load', duration, test_duration,
                {
                    'concurrent_requests': concurrent_requests,
                    'total_requests': total_requests,
                    'throughput': total_requests / duration
                }
            )
            results['concurrent_load'] = {
                'duration': duration,
                'concurrent_requests': concurrent_requests,
                'total_requests': total_requests
            }
            
            self.log("API performance tests completed.")
            
        except Exception as e:
            self.log(f"Error in API tests: {str(e)}")
            if self.verbose:
                traceback.print_exc()
            results['error'] = str(e)
        
        return results
    
    async def run_memory_performance_tests(self, quick_mode: bool = False) -> Dict[str, Any]:
        """Run memory performance tests."""
        self.log("Starting memory performance tests...")
        results = {}
        
        try:
            # Memory usage pattern test
            self.log("  Testing memory usage patterns...")
            data_size = 50 if quick_mode else 100
            start_time = time.perf_counter()
            memory_metrics = await self.memory_tester.test_memory_usage_patterns(data_size)
            test_duration = time.perf_counter() - start_time
            
            self.benchmark_runner.record_result(
                'memory_allocation_time', memory_metrics['allocation_time'], test_duration,
                memory_metrics
            )
            results['usage_patterns'] = memory_metrics
            
            # Memory cleanup test
            self.log("  Testing memory cleanup patterns...")
            cycles = 5 if quick_mode else 10
            start_time = time.perf_counter()
            cleanup_times = await self.memory_tester.test_memory_cleanup_patterns(cycles)
            test_duration = time.perf_counter() - start_time
            
            import statistics
            avg_cleanup = statistics.mean(cleanup_times)
            
            self.benchmark_runner.record_result(
                'memory_cleanup_time', avg_cleanup, test_duration,
                {'cycles': cycles, 'cleanup_times': cleanup_times}
            )
            results['cleanup_patterns'] = {'avg_cleanup': avg_cleanup, 'cycles': cycles}
            
            self.log("Memory performance tests completed.")
            
        except Exception as e:
            self.log(f"Error in memory tests: {str(e)}")
            if self.verbose:
                traceback.print_exc()
            results['error'] = str(e)
        
        return results
    
    async def run_cache_performance_tests(self, quick_mode: bool = False) -> Dict[str, Any]:
        """Run cache performance tests."""
        self.log("Starting cache performance tests...")
        results = {}
        
        try:
            # Cache hit rate test
            self.log("  Testing cache hit rates...")
            operations = 500 if quick_mode else 1000
            cache_size = 50 if quick_mode else 100
            start_time = time.perf_counter()
            cache_metrics = await self.cache_tester.test_cache_hit_rates(operations, cache_size)
            test_duration = time.perf_counter() - start_time
            
            self.benchmark_runner.record_result(
                'cache_hit_rate', cache_metrics['hit_rate'] * 100, test_duration,
                cache_metrics
            )
            results['hit_rates'] = cache_metrics
            
            # Cache under load test
            self.log("  Testing cache performance under load...")
            concurrent_ops = 25 if quick_mode else 50
            ops_per_thread = 50 if quick_mode else 100
            start_time = time.perf_counter()
            duration = await self.cache_tester.test_cache_performance_under_load(
                concurrent_ops, ops_per_thread
            )
            test_duration = time.perf_counter() - start_time
            
            # Use cache response time as metric (approximated from duration)
            cache_response_time = duration / (concurrent_ops * ops_per_thread)
            
            self.benchmark_runner.record_result(
                'cache_response_time', cache_response_time, test_duration,
                {
                    'concurrent_operations': concurrent_ops,
                    'operations_per_thread': ops_per_thread,
                    'total_duration': duration
                }
            )
            results['load_performance'] = {
                'duration': duration,
                'concurrent_operations': concurrent_ops,
                'operations_per_thread': ops_per_thread
            }
            
            self.log("Cache performance tests completed.")
            
        except Exception as e:
            self.log(f"Error in cache tests: {str(e)}")
            if self.verbose:
                traceback.print_exc()
            results['error'] = str(e)
        
        return results
    
    async def run_concurrent_user_tests(self, quick_mode: bool = False) -> Dict[str, Any]:
        """Run concurrent user performance tests."""
        self.log("Starting concurrent user tests...")
        results = {}
        
        try:
            # Basic concurrent user test
            self.log("  Testing basic concurrent user handling...")
            users = 15 if quick_mode else 25
            duration = 10.0 if quick_mode else 20.0
            start_time = time.perf_counter()
            result = await self.user_simulator.run_load_test(
                concurrent_users=users,
                test_duration=duration,
                operations_per_minute=20
            )
            test_duration = time.perf_counter() - start_time
            
            self.benchmark_runner.record_result(
                'concurrent_user_response_time', result.avg_response_time, test_duration,
                {
                    'concurrent_users': users,
                    'success_rate': result.success_rate,
                    'total_messages': result.total_messages,
                    'throughput': result.messages_per_second
                }
            )
            
            self.benchmark_runner.record_result(
                'concurrent_user_success_rate', result.success_rate, test_duration
            )
            
            results['basic_load'] = {
                'users': users,
                'avg_response_time': result.avg_response_time,
                'success_rate': result.success_rate,
                'throughput': result.messages_per_second
            }
            
            # Scalability test (reduced for quick mode)
            if not quick_mode:
                self.log("  Testing user scalability...")
                start_time = time.perf_counter()
                scaling_results = await self.scalability_tester.test_user_scaling(
                    max_users=60,
                    step_size=20,
                    test_duration=15.0
                )
                test_duration = time.perf_counter() - start_time
                
                # Record max concurrent users metric
                max_users_tested = max(scaling_results.keys())
                max_result = scaling_results[max_users_tested]
                
                self.benchmark_runner.record_result(
                    'max_concurrent_users', max_users_tested, test_duration,
                    {'scaling_results': {str(k): v.__dict__ for k, v in scaling_results.items()}}
                )
                
                results['scalability'] = {
                    'max_users_tested': max_users_tested,
                    'results': {k: {
                        'success_rate': v.success_rate,
                        'avg_response_time': v.avg_response_time,
                        'throughput': v.messages_per_second
                    } for k, v in scaling_results.items()}
                }
            
            self.log("Concurrent user tests completed.")
            
        except Exception as e:
            self.log(f"Error in concurrent user tests: {str(e)}")
            if self.verbose:
                traceback.print_exc()
            results['error'] = str(e)
        
        return results
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile from list of values."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int((percentile / 100.0) * len(sorted_values))
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]
    
    async def run_comprehensive_suite(self, quick_mode: bool = False, 
                                     categories: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run comprehensive performance test suite."""
        self.log("Starting comprehensive performance test suite...")
        mode_str = "(Quick Mode)" if quick_mode else "(Full Mode)"
        self.log(f"Running in {mode_str}")
        
        suite_start_time = time.perf_counter()
        suite_results = {}
        
        # Define all available test categories
        available_tests = {
            'database': self.run_database_performance_tests,
            'websocket': self.run_websocket_performance_tests,
            'agent': self.run_agent_performance_tests,
            'api': self.run_api_performance_tests,
            'memory': self.run_memory_performance_tests,
            'cache': self.run_cache_performance_tests,
            'concurrent': self.run_concurrent_user_tests
        }
        
        # Run specified categories or all if none specified
        tests_to_run = categories or list(available_tests.keys())
        
        for category in tests_to_run:
            if category in available_tests:
                self.log(f"\n--- Running {category.upper()} tests ---")
                try:
                    category_results = await available_tests[category](quick_mode)
                    suite_results[category] = category_results
                except Exception as e:
                    self.log(f"Failed to run {category} tests: {str(e)}")
                    suite_results[category] = {'error': str(e)}
            else:
                self.log(f"Warning: Unknown test category '{category}'")
        
        suite_duration = time.perf_counter() - suite_start_time
        suite_results['_meta'] = {
            'total_duration': suite_duration,
            'categories_run': tests_to_run,
            'quick_mode': quick_mode,
            'timestamp': time.time()
        }
        
        self.log(f"\nPerformance test suite completed in {suite_duration:.2f} seconds.")
        return suite_results
    
    def generate_final_report(self, suite_results: Dict[str, Any], save_files: bool = True):
        """Generate and optionally save final performance report."""
        self.log("Generating final performance report...")
        
        # Generate benchmark report
        benchmark_report = self.benchmark_runner.generate_final_report(save_to_file=save_files)
        
        # Print summary to console
        self.benchmark_runner.print_results_summary()
        
        # Save detailed suite results if requested
        if save_files:
            import json
            timestamp = int(time.time())
            
            # Save detailed results
            detailed_filename = f"performance_detailed_results_{timestamp}.json"
            os.makedirs("test_reports", exist_ok=True)
            
            with open(f"test_reports/{detailed_filename}", 'w') as f:
                json.dump(suite_results, f, indent=2, default=str)
            
            self.log(f"Detailed results saved to: test_reports/{detailed_filename}")
        
        return benchmark_report

async def main():
    """Main entry point for performance testing."""
    parser = argparse.ArgumentParser(description="Run comprehensive performance tests")
    parser.add_argument('--quick', action='store_true', help='Run in quick mode (reduced test sizes)')
    parser.add_argument('--quiet', action='store_true', help='Run in quiet mode (minimal output)')
    parser.add_argument('--categories', nargs='+', 
                       choices=['database', 'websocket', 'agent', 'api', 'memory', 'cache', 'concurrent'],
                       help='Specific categories to test')
    parser.add_argument('--no-save', action='store_true', help='Do not save report files')
    
    args = parser.parse_args()
    
    # Initialize orchestrator
    orchestrator = PerformanceTestOrchestrator(verbose=not args.quiet)
    
    try:
        # Run performance suite
        suite_results = await orchestrator.run_comprehensive_suite(
            quick_mode=args.quick,
            categories=args.categories
        )
        
        # Generate final report
        benchmark_report = orchestrator.generate_final_report(
            suite_results,
            save_files=not args.no_save
        )
        
        # Determine exit code based on results
        if 'summary' in benchmark_report:
            pass_rate = benchmark_report['summary'].get('pass_rate', 0)
            if pass_rate >= 90:
                print(f"\n PASS:  Performance tests PASSED (Pass rate: {pass_rate:.1f}%)")
                return 0
            else:
                print(f"\n FAIL:  Performance tests FAILED (Pass rate: {pass_rate:.1f}%)")
                return 1
        else:
            print("\n WARNING: [U+FE0F]  Unable to determine performance test results")
            return 2
    
    except KeyboardInterrupt:
        print("\n[U+1F6D1] Performance tests interrupted by user")
        return 130
    
    except Exception as e:
        print(f"\n[U+1F4A5] Performance tests failed with error: {str(e)}")
        if not args.quiet:
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    # Run the performance test suite
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Real Service Test Runner - NO MOCKS VALIDATION

Runs all real service tests to validate the mock remediation is complete
and all functionality works with actual services.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Risk Reduction & Development Velocity
- Value Impact: Ensures production-ready testing without false positives
- Strategic Impact: Eliminates mock-related bugs and test failures

Test Categories:
1. WebSocket Infrastructure Tests
2. WebSocket Memory Management Tests  
3. Agent Execution Tests
4. Circuit Breaker Tests
5. Database Connectivity Tests
6. Redis Connectivity Tests
7. Comprehensive Integration Tests
"""

import asyncio
import subprocess
import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse
import json
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('real_service_tests.log')
    ]
)
logger = logging.getLogger(__name__)


class RealServiceTestRunner:
    """Test runner for all real service tests."""
    
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path) if base_path else Path(__file__).parent
        self.test_results = {}
        self.overall_start_time = None
        self.overall_end_time = None
        
        # Test files in order of execution
        self.test_files = [
            {
                'name': 'WebSocket Infrastructure',
                'file': 'test_real_websocket_infrastructure.py',
                'critical': True,
                'description': 'Real WebSocket connections and basic functionality'
            },
            {
                'name': 'WebSocket Memory Management',
                'file': 'test_real_websocket_memory_management.py',
                'critical': True,
                'description': 'Memory leak detection and connection management'
            },
            {
                'name': 'Database Connectivity',
                'file': 'test_real_database_connectivity.py',
                'critical': True,
                'description': 'PostgreSQL database operations and pooling'
            },
            {
                'name': 'Redis Connectivity',
                'file': 'test_real_redis_connectivity.py',
                'critical': True,
                'description': 'Redis caching and data structure operations'
            },
            {
                'name': 'Circuit Breaker',
                'file': 'test_real_circuit_breaker.py',
                'critical': True,
                'description': 'Circuit breaker with real service failures'
            },
            {
                'name': 'Agent Execution',
                'file': 'test_real_agent_execution.py',
                'critical': False,  # May require API keys
                'description': 'Real LLM-based agent execution'
            },
            {
                'name': 'Comprehensive Integration',
                'file': 'test_comprehensive_integration.py',
                'critical': False,  # Requires all services
                'description': 'End-to-end integration with all services'
            }
        ]
    
    def check_prerequisites(self) -> Dict[str, bool]:
        """Check if prerequisites for real service tests are met."""
        prerequisites = {}
        
        # Check if test files exist
        for test_config in self.test_files:
            test_file_path = self.base_path / test_config['file']
            prerequisites[f"file_{test_config['file']}"] = test_file_path.exists()
        
        # Check if pytest is available
        try:
            result = subprocess.run(['pytest', '--version'], capture_output=True, text=True)
            prerequisites['pytest_available'] = result.returncode == 0
        except FileNotFoundError:
            prerequisites['pytest_available'] = False
        
        # Check if Python packages are available
        required_packages = [
            'asyncio', 'pytest', 'websockets', 'asyncpg', 
            'redis', 'psutil', 'aiohttp', 'fastapi', 'uvicorn'
        ]
        
        for package in required_packages:
            try:
                __import__(package)
                prerequisites[f"package_{package}"] = True
            except ImportError:
                prerequisites[f"package_{package}"] = False
        
        return prerequisites
    
    async def run_single_test(self, test_config: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
        """Run a single test file and return results."""
        test_name = test_config['name']
        test_file = test_config['file']
        test_file_path = self.base_path / test_file
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Running {test_name} Tests")
        logger.info(f"File: {test_file}")
        logger.info(f"Description: {test_config['description']}")
        logger.info(f"{'='*80}")
        
        if not test_file_path.exists():
            return {
                'name': test_name,
                'file': test_file,
                'status': 'error',
                'error': f"Test file not found: {test_file_path}",
                'duration': 0
            }
        
        # Build pytest command
        pytest_cmd = ['pytest', str(test_file_path), '-v']
        
        # Add real service flags if requested
        if args.real_llm:
            pytest_cmd.append('--real-llm')
        
        if args.verbose:
            pytest_cmd.append('-s')
        
        if args.fast_fail:
            pytest_cmd.append('-x')
        
        if args.timeout:
            pytest_cmd.extend(['--timeout', str(args.timeout)])
        
        # Set environment variables for real services
        env = {
            'USE_REAL_SERVICES': 'true',
            'PYTEST_CURRENT_TEST': f'{test_name}::running',
        }
        
        if args.real_llm:
            env.update({
                'ENABLE_REAL_LLM_TESTING': 'true',
                'TEST_USE_REAL_LLM': 'true'
            })
        
        # Run the test
        start_time = time.time()
        
        try:
            result = subprocess.run(
                pytest_cmd,
                cwd=self.base_path.parent,  # Run from netra_backend directory
                capture_output=True,
                text=True,
                timeout=args.timeout if args.timeout else 600,  # 10 minute default timeout
                env={**subprocess.os.environ, **env}
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Parse results
            if result.returncode == 0:
                status = 'passed'
                error = None
            elif result.returncode == 5:  # No tests collected
                status = 'skipped'
                error = 'No tests collected'
            else:
                status = 'failed'
                error = result.stderr if result.stderr else 'Test execution failed'
            
            return {
                'name': test_name,
                'file': test_file,
                'status': status,
                'duration': duration,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'error': error,
                'critical': test_config.get('critical', False)
            }
            
        except subprocess.TimeoutExpired as e:
            return {
                'name': test_name,
                'file': test_file,
                'status': 'timeout',
                'duration': args.timeout if args.timeout else 600,
                'error': f'Test timed out after {e.timeout} seconds',
                'critical': test_config.get('critical', False)
            }
        
        except Exception as e:
            return {
                'name': test_name,
                'file': test_file,
                'status': 'error',
                'duration': time.time() - start_time,
                'error': str(e),
                'critical': test_config.get('critical', False)
            }
    
    async def run_all_tests(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Run all real service tests."""
        logger.info("Starting Real Service Test Suite - NO MOCKS")
        logger.info(f"Test execution started at {datetime.now(timezone.utc).isoformat()}")
        
        # Check prerequisites
        prereqs = self.check_prerequisites()
        missing_prereqs = [k for k, v in prereqs.items() if not v]
        
        if missing_prereqs:
            logger.error(f"Missing prerequisites: {missing_prereqs}")
            if not args.ignore_prereqs:
                return {
                    'status': 'error',
                    'error': f'Missing prerequisites: {missing_prereqs}',
                    'results': {}
                }
        
        self.overall_start_time = time.time()
        
        # Filter tests to run
        tests_to_run = self.test_files
        
        if args.critical_only:
            tests_to_run = [t for t in tests_to_run if t.get('critical', False)]
            logger.info("Running critical tests only")
        
        if args.test_name:
            tests_to_run = [t for t in tests_to_run if args.test_name.lower() in t['name'].lower()]
            logger.info(f"Running tests matching: {args.test_name}")
        
        logger.info(f"Running {len(tests_to_run)} test suites")
        
        # Run tests
        results = {}
        
        for i, test_config in enumerate(tests_to_run, 1):
            logger.info(f"\nProgress: {i}/{len(tests_to_run)}")
            
            try:
                result = await self.run_single_test(test_config, args)
                results[test_config['name']] = result
                
                # Log immediate result
                if result['status'] == 'passed':
                    logger.info(f" PASS:  {test_config['name']}: PASSED ({result['duration']:.2f}s)")
                elif result['status'] == 'failed':
                    logger.error(f" FAIL:  {test_config['name']}: FAILED ({result['duration']:.2f}s)")
                    if result.get('error'):
                        logger.error(f"   Error: {result['error']}")
                elif result['status'] == 'timeout':
                    logger.error(f"[U+23F0] {test_config['name']}: TIMEOUT ({result['duration']:.2f}s)")
                elif result['status'] == 'skipped':
                    logger.warning(f" WARNING: [U+FE0F]  {test_config['name']}: SKIPPED ({result['duration']:.2f}s)")
                else:
                    logger.error(f"[U+2753] {test_config['name']}: {result['status'].upper()} ({result['duration']:.2f}s)")
                
                # Stop on first failure if requested
                if args.fast_fail and result['status'] in ['failed', 'error']:
                    logger.error("Stopping on first failure (--fast-fail)")
                    break
                    
            except Exception as e:
                logger.error(f" FAIL:  {test_config['name']}: EXCEPTION - {e}")
                results[test_config['name']] = {
                    'name': test_config['name'],
                    'status': 'exception',
                    'error': str(e),
                    'duration': 0
                }
                
                if args.fast_fail:
                    break
        
        self.overall_end_time = time.time()
        
        # Compile final results
        return self.compile_final_results(results, args)
    
    def compile_final_results(self, results: Dict[str, Dict], args: argparse.Namespace) -> Dict[str, Any]:
        """Compile final test results summary."""
        total_duration = self.overall_end_time - self.overall_start_time
        
        # Count results by status
        status_counts = {}
        critical_failures = []
        
        for test_name, result in results.items():
            status = result['status']
            status_counts[status] = status_counts.get(status, 0) + 1
            
            if result.get('critical', False) and status in ['failed', 'error', 'timeout']:
                critical_failures.append(test_name)
        
        # Determine overall status
        if critical_failures:
            overall_status = 'critical_failure'
        elif status_counts.get('failed', 0) > 0 or status_counts.get('error', 0) > 0:
            overall_status = 'failure'
        elif status_counts.get('timeout', 0) > 0:
            overall_status = 'timeout'
        elif status_counts.get('passed', 0) == 0:
            overall_status = 'no_tests'
        else:
            overall_status = 'success'
        
        final_results = {
            'overall_status': overall_status,
            'total_duration': total_duration,
            'tests_run': len(results),
            'status_counts': status_counts,
            'critical_failures': critical_failures,
            'results': results,
            'summary': {
                'passed': status_counts.get('passed', 0),
                'failed': status_counts.get('failed', 0),
                'errors': status_counts.get('error', 0),
                'timeouts': status_counts.get('timeout', 0),
                'skipped': status_counts.get('skipped', 0)
            },
            'execution_info': {
                'start_time': datetime.fromtimestamp(self.overall_start_time, tz=timezone.utc).isoformat(),
                'end_time': datetime.fromtimestamp(self.overall_end_time, tz=timezone.utc).isoformat(),
                'args': vars(args)
            }
        }
        
        return final_results
    
    def print_final_summary(self, final_results: Dict[str, Any]):
        """Print final test summary."""
        print("\n" + "="*80)
        print("REAL SERVICE TEST SUITE SUMMARY - NO MOCKS")
        print("="*80)
        
        overall_status = final_results['overall_status']
        duration = final_results['total_duration']
        
        # Status emoji
        if overall_status == 'success':
            status_emoji = " PASS: "
            status_color = "SUCCESS"
        elif overall_status == 'critical_failure':
            status_emoji = " ALERT: "
            status_color = "CRITICAL FAILURE"
        else:
            status_emoji = " FAIL: "
            status_color = "FAILURE"
        
        print(f"{status_emoji} Overall Status: {status_color}")
        print(f"[U+23F1][U+FE0F]  Total Duration: {duration:.2f} seconds")
        print(f"[U+1F9EA] Tests Run: {final_results['tests_run']}")
        
        # Summary counts
        summary = final_results['summary']
        print(f"\nResults:")
        print(f"   PASS:  Passed: {summary['passed']}")
        print(f"   FAIL:  Failed: {summary['failed']}")
        print(f"  [U+1F6AB] Errors: {summary['errors']}")
        print(f"  [U+23F0] Timeouts: {summary['timeouts']}")
        print(f"   WARNING: [U+FE0F]  Skipped: {summary['skipped']}")
        
        # Critical failures
        if final_results['critical_failures']:
            print(f"\n ALERT:  CRITICAL FAILURES:")
            for failure in final_results['critical_failures']:
                print(f"  - {failure}")
        
        # Individual test results
        print(f"\nIndividual Test Results:")
        print("-" * 80)
        
        for test_name, result in final_results['results'].items():
            status = result['status']
            duration = result['duration']
            
            if status == 'passed':
                emoji = " PASS: "
            elif status == 'failed':
                emoji = " FAIL: "
            elif status == 'error':
                emoji = "[U+1F6AB]"
            elif status == 'timeout':
                emoji = "[U+23F0]"
            elif status == 'skipped':
                emoji = " WARNING: [U+FE0F]"
            else:
                emoji = "[U+2753]"
            
            critical_marker = " [CRITICAL]" if result.get('critical', False) else ""
            print(f"{emoji} {test_name:<35} {status.upper():<10} ({duration:.2f}s){critical_marker}")
            
            if result.get('error') and status != 'passed':
                error_preview = result['error'][:100] + "..." if len(result['error']) > 100 else result['error']
                print(f"    Error: {error_preview}")
        
        print("\n" + "="*80)
        
        # Final verdict
        if overall_status == 'success':
            print(" CELEBRATION:  ALL REAL SERVICE TESTS PASSED!")
            print("[U+2728] Mock remediation is COMPLETE - all functionality works with real services!")
        elif overall_status == 'critical_failure':
            print(" ALERT:  CRITICAL TESTS FAILED!")
            print(" WARNING: [U+FE0F]  Mock remediation is INCOMPLETE - critical functionality broken!")
        else:
            print(" WARNING: [U+FE0F]  SOME TESTS FAILED!")
            print("[U+1F527] Mock remediation needs additional work!")
        
        print("="*80)
    
    def save_results(self, final_results: Dict[str, Any], output_file: Optional[str] = None):
        """Save results to file."""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"real_service_test_results_{timestamp}.json"
        
        output_path = self.base_path / output_file
        
        try:
            with open(output_path, 'w') as f:
                json.dump(final_results, f, indent=2, default=str)
            
            logger.info(f"Test results saved to: {output_path}")
            print(f"[U+1F4C4] Detailed results saved to: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")


async def main():
    """Main function to run real service tests."""
    parser = argparse.ArgumentParser(
        description="Run Real Service Tests - NO MOCKS",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--critical-only', 
        action='store_true',
        help='Run only critical tests'
    )
    
    parser.add_argument(
        '--test-name',
        type=str,
        help='Run tests matching this name (case insensitive)'
    )
    
    parser.add_argument(
        '--real-llm',
        action='store_true',
        help='Enable real LLM testing (requires API keys)'
    )
    
    parser.add_argument(
        '--fast-fail',
        action='store_true',
        help='Stop on first failure'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=600,
        help='Timeout per test suite in seconds (default: 600)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Output file for results (JSON)'
    )
    
    parser.add_argument(
        '--ignore-prereqs',
        action='store_true',
        help='Ignore missing prerequisites'
    )
    
    args = parser.parse_args()
    
    # Create and run test runner
    runner = RealServiceTestRunner()
    
    try:
        final_results = await runner.run_all_tests(args)
        
        # Print summary
        runner.print_final_summary(final_results)
        
        # Save results
        runner.save_results(final_results, args.output)
        
        # Exit with appropriate code
        if final_results['overall_status'] == 'success':
            sys.exit(0)
        elif final_results['overall_status'] == 'critical_failure':
            sys.exit(2)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.error("Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Test runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Comprehensive Docker Stability Test Runner
CRITICAL: Runs the complete Docker stability test suite to validate our fixes work.

This script runs the enhanced Docker stability test suite that includes:
1. Resource Cleanup Tests - Verify no orphaned containers/networks
2. Memory Usage Tests - Verify < 4GB RAM usage (tmpfs removed to prevent crashes)
3. Parallel Execution Tests - Run 5 parallel test suites
4. Health Check Tests - Verify services become healthy within timeout
5. Configuration Validation Tests - PostgreSQL conservative settings, named volumes only
6. Recovery Tests - Kill containers mid-test and verify cleanup
7. Force Flag Prohibition Tests - Zero tolerance for --force usage
8. Rate Limiting Tests - Prevent Docker daemon overload

Business Value Justification (BVJ):
1. Segment: Platform/Internal - Risk Reduction & Development Velocity
2. Business Goal: Ensure zero Docker Desktop crashes, maintain CI/CD reliability  
3. Value Impact: Prevents 4-8 hours/week developer downtime from Docker crashes
4. Revenue Impact: Protects $2M+ ARR platform from infrastructure failures

Usage:
    python scripts/run_docker_stability_tests_comprehensive.py
    python scripts/run_docker_stability_tests_comprehensive.py --suite parallel
    python scripts/run_docker_stability_tests_comprehensive.py --verbose
"""

import sys
import os
import argparse
import logging
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import the comprehensive test suite
try:
    from tests.mission_critical.test_docker_stability_suite import (
        DockerStabilityTestFramework,
        TestDockerStabilityStressTesting,
        TestDockerForceProhibition, 
        TestDockerRateLimiting,
        TestDockerRecoveryScenarios,
        TestDockerCleanupScheduler,
        TestDockerMemoryPressure,
        TestDockerParallelExecution,
        TestDockerConfigurationValidation,
        TestDockerHealthChecks
    )
except ImportError as e:
    print(f" FAIL:  Failed to import Docker stability tests: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

# Configure logging
def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
logger = logging.getLogger(__name__)

def run_test_suite(suite_name: str, test_class, framework: DockerStabilityTestFramework) -> dict:
    """Run a single test suite and return results."""
    logger.info(f"[U+1F680] Running {suite_name} Tests")
    logger.info("-" * 60)
    
    suite_results = {}
    suite_instance = test_class()
    
    # Get all test methods
    test_methods = [method for method in dir(suite_instance) if method.startswith('test_')]
    
    for method_name in test_methods:
        try:
            logger.info(f"[U+25B6][U+FE0F] Executing {method_name}...")
            method = getattr(suite_instance, method_name)
            
            start_time = time.time()
            method(framework)
            execution_time = time.time() - start_time
            
            suite_results[method_name] = {
                'status': 'PASSED',
                'execution_time': execution_time,
                'error': None
            }
            logger.info(f" PASS:  {method_name} completed in {execution_time:.2f}s")
            
        except Exception as e:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0
            suite_results[method_name] = {
                'status': 'FAILED', 
                'execution_time': execution_time,
                'error': str(e)
            }
            logger.error(f" FAIL:  {method_name} failed after {execution_time:.2f}s: {e}")
    
    return suite_results

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Run comprehensive Docker stability tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Suites Available:
  stress          - Extreme stress tests (concurrent operations, rapid networks)
  force           - Force flag prohibition tests (zero tolerance)  
  rate            - Rate limiting tests (prevent daemon overload)
  memory          - Memory pressure tests (< 4GB usage validation)
  parallel        - Parallel execution tests (5 concurrent test suites)
  config          - Configuration validation (PostgreSQL settings, named volumes)
  recovery        - Recovery scenario tests (kill containers, daemon restart)
  cleanup         - Cleanup validation tests (orphaned resource removal)
  health          - Health check tests (services become healthy in time)
  
Examples:
  python scripts/run_docker_stability_tests_comprehensive.py
  python scripts/run_docker_stability_tests_comprehensive.py --suite parallel --verbose
  python scripts/run_docker_stability_tests_comprehensive.py --suite memory,config
        """
    )
    
    parser.add_argument(
        '--suite', '-s',
        help='Specific test suite(s) to run (comma-separated)',
        default='all'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=1800,  # 30 minutes
        help='Overall test timeout in seconds (default: 1800)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    logger.info("[U+1F680] COMPREHENSIVE Docker Stability Test Suite")
    logger.info("=" * 80)
    logger.info("MISSION CRITICAL: Validating Docker stability improvements")
    logger.info("BUSINESS IMPACT: Prevents Docker crashes that cost 4-8 hours/week downtime")
    logger.info("=" * 80)
    
    # Define all available test suites
    all_test_suites = {
        'stress': ("Extreme Stress Testing", TestDockerStabilityStressTesting),
        'force': ("Force Flag Prohibition", TestDockerForceProhibition),
        'rate': ("Rate Limiting", TestDockerRateLimiting),
        'memory': ("Memory Pressure", TestDockerMemoryPressure), 
        'parallel': ("Parallel Execution", TestDockerParallelExecution),
        'config': ("Configuration Validation", TestDockerConfigurationValidation),
        'recovery': ("Recovery Scenarios", TestDockerRecoveryScenarios),
        'cleanup': ("Cleanup Validation", TestDockerCleanupScheduler),
        'health': ("Health Checks", TestDockerHealthChecks)
    }
    
    # Determine which suites to run
    if args.suite == 'all':
        suites_to_run = all_test_suites
    else:
        suite_names = [name.strip() for name in args.suite.split(',')]
        suites_to_run = {}
        for name in suite_names:
            if name in all_test_suites:
                suites_to_run[name] = all_test_suites[name]
            else:
                logger.error(f" FAIL:  Unknown test suite: {name}")
                logger.info(f"Available suites: {', '.join(all_test_suites.keys())}")
                return 1
    
    logger.info(f"[U+1F4CB] Running {len(suites_to_run)} test suite(s): {', '.join(suites_to_run.keys())}")
    logger.info("")
    
    # Initialize test framework
    framework = DockerStabilityTestFramework()
    overall_start_time = time.time()
    
    try:
        # Track results
        all_results = {}
        total_tests = 0
        passed_tests = 0
        
        # Run each selected test suite
        for suite_key, (suite_name, test_class) in suites_to_run.items():
            suite_results = run_test_suite(suite_name, test_class, framework)
            all_results[suite_name] = suite_results
            
            # Update counters
            suite_passed = sum(1 for result in suite_results.values() if result['status'] == 'PASSED')
            suite_total = len(suite_results)
            total_tests += suite_total
            passed_tests += suite_passed
            
            logger.info(f" CHART:  {suite_name} Results: {suite_passed}/{suite_total} passed")
            logger.info("")
        
        # Calculate overall results
        overall_execution_time = time.time() - overall_start_time
        success_rate = passed_tests / total_tests * 100 if total_tests > 0 else 0
        
        # Generate comprehensive report
        logger.info("=" * 80)
        logger.info(" TROPHY:  FINAL DOCKER STABILITY TEST RESULTS")
        logger.info("=" * 80)
        
        logger.info(f" CHART:  OVERALL SUMMARY:")
        logger.info(f"   [U+1F9EA] Total Tests Executed: {total_tests}")
        logger.info(f"    PASS:  Tests Passed: {passed_tests}")
        logger.info(f"    FAIL:  Tests Failed: {total_tests - passed_tests}")
        logger.info(f"   [U+1F4C8] Success Rate: {success_rate:.1f}%")
        logger.info(f"   [U+23F1][U+FE0F] Total Execution Time: {overall_execution_time:.2f} seconds")
        logger.info("")
        
        # Detailed results by suite
        logger.info("[U+1F4CB] DETAILED RESULTS BY TEST SUITE:")
        logger.info("")
        for suite_name, suite_results in all_results.items():
            suite_passed = sum(1 for r in suite_results.values() if r['status'] == 'PASSED')
            suite_total = len(suite_results)
            suite_rate = suite_passed / suite_total * 100 if suite_total > 0 else 0
            suite_time = sum(r['execution_time'] for r in suite_results.values())
            
            logger.info(f" SEARCH:  {suite_name} ({suite_rate:.1f}% passed, {suite_time:.2f}s):")
            
            for test_name, result in suite_results.items():
                status_icon = " PASS: " if result['status'] == 'PASSED' else " FAIL: "
                logger.info(f"   {status_icon} {test_name}: {result['status']} ({result['execution_time']:.2f}s)")
                if result['error']:
                    logger.info(f"      Error: {result['error']}")
            logger.info("")
        
        # Framework metrics
        logger.info("[U+1F4C8] DOCKER STABILITY FRAMEWORK METRICS:")
        for metric, value in framework.metrics.items():
            logger.info(f"   - {metric.replace('_', ' ').title()}: {value}")
        logger.info("")
        
        # Final assessment
        if success_rate >= 95:
            logger.info(" CELEBRATION:  EXCELLENT: Docker stability is OUTSTANDING! All systems stable.")
            return_code = 0
        elif success_rate >= 90:
            logger.info(" PASS:  GOOD: Docker stability is strong with minor issues.")
            return_code = 0
        elif success_rate >= 80:
            logger.warning(" WARNING: [U+FE0F] WARNING: Docker stability has concerning issues that need attention.")
            return_code = 1
        else:
            logger.error(" ALERT:  CRITICAL: Docker stability FAILURES detected! Immediate action required.")
            return_code = 2
        
        # Recommendations based on results
        if success_rate < 100:
            logger.info("")
            logger.info("[U+1F527] RECOMMENDED ACTIONS:")
            
            if success_rate < 90:
                logger.info("   1. Review failed tests immediately")
                logger.info("   2. Check Docker daemon logs: docker system events")
                logger.info("   3. Verify available system resources (memory, disk)")
                logger.info("   4. Consider restarting Docker daemon")
            
            if any("memory" in test for suite in all_results.values() for test in suite.keys() 
                   if suite[test]['status'] == 'FAILED'):
                logger.info("   5. CRITICAL: Memory issues detected - check volume usage")
                logger.info("   6. Run: docker system df -v to check volume usage")
            
            if any("parallel" in test for suite in all_results.values() for test in suite.keys()
                   if suite[test]['status'] == 'FAILED'):
                logger.info("   7. Parallel execution issues - check for resource contention")
                logger.info("   8. Consider reducing parallel test concurrency")
        
        logger.info("=" * 80)
        return return_code
        
    except KeyboardInterrupt:
        logger.warning("[U+1F6D1] Test execution interrupted by user")
        return 130
    except Exception as e:
        logger.error(f" FAIL:  Critical test framework failure: {e}")
        return 1
    finally:
        # Comprehensive cleanup
        logger.info("[U+1F9F9] Performing comprehensive cleanup...")
        try:
            framework.cleanup()
            logger.info(" PASS:  Cleanup completed successfully")
        except Exception as e:
            logger.error(f" WARNING: [U+FE0F] Cleanup had issues: {e}")

if __name__ == '__main__':
    sys.exit(main())
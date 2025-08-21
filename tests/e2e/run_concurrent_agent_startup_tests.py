#!/usr/bin/env python3
"""
Concurrent Agent Startup Test Suite Runner
==========================================

This script provides a convenient way to run the concurrent agent startup
test suite with proper environment configuration and reporting.

Usage:
    python run_concurrent_agent_startup_tests.py [OPTIONS]

Options:
    --users N           Number of concurrent users (default: 100)
    --timeout N         Test timeout in seconds (default: 300)
    --verbose           Enable verbose logging
    --performance-only  Run only performance tests
    --isolation-only    Run only isolation tests
    --quick             Quick test with 20 users
    --report-file FILE  Save detailed report to file

Environment Variables:
    CONCURRENT_TEST_USERS=100
    CONCURRENT_TEST_TIMEOUT=300
    AGENT_STARTUP_TIMEOUT=30
    MAX_AGENT_STARTUP_TIME=5.0
    MIN_SUCCESS_RATE=0.95
    ISOLATION_VALIDATION_STRICT=true

Examples:
    # Run full test suite with 100 users
    python run_concurrent_agent_startup_tests.py

    # Quick test with 20 users
    python run_concurrent_agent_startup_tests.py --quick

    # Performance-focused test with custom user count
    python run_concurrent_agent_startup_tests.py --users 50 --performance-only

    # Verbose mode with detailed logging
    python run_concurrent_agent_startup_tests.py --verbose --report-file results.json
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import pytest


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('concurrent_test_run.log')
        ]
    )


def configure_test_environment(args: argparse.Namespace):
    """Configure test environment based on arguments."""
    # Set environment variables
    os.environ["RUN_E2E_TESTS"] = "true"
    os.environ["USE_REAL_SERVICES"] = "true"
    os.environ["CONCURRENT_TEST_MODE"] = "true"
    os.environ["TESTING"] = "1"
    
    # Configure test parameters
    if args.users:
        os.environ["CONCURRENT_TEST_USERS"] = str(args.users)
    
    if args.timeout:
        os.environ["CONCURRENT_TEST_TIMEOUT"] = str(args.timeout)
    
    if args.quick:
        os.environ["CONCURRENT_TEST_USERS"] = "20"
        os.environ["CONCURRENT_TEST_TIMEOUT"] = "120"
        os.environ["AGENT_STARTUP_TIMEOUT"] = "15"
    
    # Performance settings
    if args.performance_only:
        os.environ["FOCUS_PERFORMANCE_TESTS"] = "true"
    
    if args.isolation_only:
        os.environ["FOCUS_ISOLATION_TESTS"] = "true"


def build_pytest_args(args: argparse.Namespace) -> list:
    """Build pytest arguments based on command line options."""
    pytest_args = [
        "tests/e2e/test_concurrent_agent_startup.py",
        "-v",
        "--tb=short",
        "--durations=10"
    ]
    
    # Add markers based on test focus
    if args.performance_only:
        pytest_args.extend(["-m", "performance"])
    elif args.isolation_only:
        pytest_args.extend(["-m", "critical"])
    else:
        pytest_args.extend(["-m", "e2e"])
    
    # Add verbose flag if requested
    if args.verbose:
        pytest_args.append("-s")
    
    # Add specific test selection for quick mode
    if args.quick:
        pytest_args.extend([
            "-k", "test_concurrent_agent_startup_isolation or test_performance_under_concurrent_load"
        ])
    
    return pytest_args


def generate_test_report(start_time: float, exit_code: int, args: argparse.Namespace) -> Dict[str, Any]:
    """Generate comprehensive test report."""
    end_time = time.time()
    duration = end_time - start_time
    
    report = {
        "test_run_metadata": {
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": duration,
            "exit_code": exit_code,
            "success": exit_code == 0
        },
        "test_configuration": {
            "user_count": int(os.environ.get("CONCURRENT_TEST_USERS", "100")),
            "timeout": int(os.environ.get("CONCURRENT_TEST_TIMEOUT", "300")),
            "agent_timeout": int(os.environ.get("AGENT_STARTUP_TIMEOUT", "30")),
            "quick_mode": args.quick,
            "performance_only": args.performance_only,
            "isolation_only": args.isolation_only
        },
        "environment": {
            "python_version": sys.version,
            "working_directory": str(Path.cwd()),
            "environment_variables": {
                k: v for k, v in os.environ.items() 
                if k.startswith(("CONCURRENT_", "E2E_", "TEST_"))
            }
        }
    }
    
    return report


def save_report(report: Dict[str, Any], filename: Optional[str]):
    """Save test report to file."""
    if not filename:
        return
    
    try:
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"Test report saved to: {filename}")
    except Exception as e:
        print(f"Failed to save report: {e}")


def print_summary(report: Dict[str, Any]):
    """Print test execution summary."""
    metadata = report["test_run_metadata"]
    config = report["test_configuration"]
    
    print("\n" + "="*60)
    print("CONCURRENT AGENT STARTUP TEST SUMMARY")
    print("="*60)
    print(f"Test Duration: {metadata['duration_seconds']:.2f} seconds")
    print(f"Exit Code: {metadata['exit_code']}")
    print(f"Success: {'✅ PASSED' if metadata['success'] else '❌ FAILED'}")
    print(f"User Count: {config['user_count']}")
    print(f"Test Mode: {'Quick' if config['quick_mode'] else 'Full'}")
    
    if config['performance_only']:
        print("Focus: Performance Tests Only")
    elif config['isolation_only']:
        print("Focus: Isolation Tests Only")
    else:
        print("Focus: All Test Cases")
    
    print("="*60)


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(
        description="Run Concurrent Agent Startup Test Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--users", type=int, 
        help="Number of concurrent users (default: 100)"
    )
    parser.add_argument(
        "--timeout", type=int,
        help="Test timeout in seconds (default: 300)"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--performance-only", action="store_true",
        help="Run only performance tests"
    )
    parser.add_argument(
        "--isolation-only", action="store_true",
        help="Run only isolation tests"
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Quick test with 20 users"
    )
    parser.add_argument(
        "--report-file", type=str,
        help="Save detailed report to file"
    )
    
    args = parser.parse_args()
    
    # Setup
    setup_logging(args.verbose)
    configure_test_environment(args)
    
    # Build pytest command
    pytest_args = build_pytest_args(args)
    
    print(f"Running concurrent agent startup tests...")
    print(f"Command: pytest {' '.join(pytest_args)}")
    print(f"Users: {os.environ.get('CONCURRENT_TEST_USERS', '100')}")
    print(f"Timeout: {os.environ.get('CONCURRENT_TEST_TIMEOUT', '300')}s")
    
    # Run tests
    start_time = time.time()
    
    try:
        exit_code = pytest.main(pytest_args)
    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")
        exit_code = 130
    except Exception as e:
        print(f"Test execution failed: {e}")
        exit_code = 1
    
    # Generate and save report
    report = generate_test_report(start_time, exit_code, args)
    save_report(report, args.report_file)
    print_summary(report)
    
    # Exit with pytest exit code
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
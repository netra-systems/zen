#!/usr/bin/env python
"""
Enhanced test runner with parallel execution and failure-first reporting
"""

import os
import sys
import asyncio
import argparse
import multiprocessing

# Set testing environment
os.environ["TESTING"] = "1"
os.environ["REDIS_HOST"] = "localhost"
os.environ["CLICKHOUSE_HOST"] = "localhost"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"

# Add project to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Configure asyncio for Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

def get_cpu_count():
    """Get optimal number of CPUs for parallel testing"""
    try:
        # Use all available CPUs minus 1 to keep system responsive
        return max(1, multiprocessing.cpu_count() - 1)
    except:
        return 4  # Default fallback

def main():
    parser = argparse.ArgumentParser(description="Run tests with enhanced options")
    parser.add_argument(
        "--parallel", "-p",
        type=int,
        default=get_cpu_count(),
        help=f"Number of parallel workers (default: {get_cpu_count()}, use 0 for sequential)"
    )
    parser.add_argument(
        "--failed-first", "-f",
        action="store_true",
        default=True,
        help="Run previously failed tests first (default: True)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=True,
        help="Verbose output (default: True)"
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Quick mode - stop on first failure"
    )
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Run with coverage reporting"
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Profile test execution time"
    )
    parser.add_argument(
        "tests",
        nargs="*",
        default=["tests/"],
        help="Specific test files or directories to run"
    )
    
    args = parser.parse_args()
    
    import pytest
    
    # Build pytest arguments
    pytest_args = []
    
    # Add test paths
    pytest_args.extend(args.tests)
    
    # Verbosity
    if args.verbose:
        pytest_args.append("-v")
    
    # Parallel execution
    if args.parallel > 0:
        pytest_args.extend(["-n", str(args.parallel)])
        print(f"Running tests with {args.parallel} parallel workers")
    else:
        print("Running tests sequentially")
    
    # Failed first
    if args.failed_first:
        pytest_args.append("--failed-first")
        pytest_args.append("-rf")  # Show failure summary
        print("Running previously failed tests first")
    
    # Quick mode
    if args.quick:
        pytest_args.append("-x")  # Stop on first failure
        pytest_args.append("--maxfail=1")
        print("Quick mode: Will stop on first failure")
    
    # Coverage
    if args.coverage:
        pytest_args.extend([
            "--cov=app",
            "--cov-report=html",
            "--cov-report=term-missing"
        ])
        print("Running with coverage reporting")
    
    # Profile
    if args.profile:
        pytest_args.append("--durations=10")
        print("Profiling: Will show 10 slowest tests")
    
    # Common options
    pytest_args.extend([
        "--tb=short",  # Short traceback
        "--asyncio-mode=auto",  # Auto async mode
        "--disable-warnings",
        "--color=yes",  # Colored output
        "--capture=no",  # Show print statements
    ])
    
    print(f"Running: pytest {' '.join(pytest_args)}")
    print("-" * 60)
    
    # Run tests
    exit_code = pytest.main(pytest_args)
    
    # Show results
    print("-" * 60)
    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print(f"❌ Tests failed with exit code: {exit_code}")
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
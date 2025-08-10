#!/usr/bin/env python
"""
Comprehensive backend test runner for Netra AI Platform
Designed for easy use by Claude Code and CI/CD pipelines
"""

import os
import sys
import json
import time
import asyncio
import argparse
import subprocess
from pathlib import Path
from typing import List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Test categories for organized testing
TEST_CATEGORIES = {
    "unit": ["app/tests/services", "app/tests/core", "app/tests/utils"],
    "integration": ["integration_tests", "app/tests/routes"],
    "agent": ["app/tests/agents", "app/tests/services/agents", "app/tests/services/apex_optimizer_agent"],
    "websocket": ["app/tests/test_websocket.py", "app/tests/routes/test_websocket_*.py"],
    "auth": ["app/tests/test_auth*.py", "app/tests/routes/test_*auth*.py"],
    "database": ["app/tests/services/database", "app/tests/test_database*.py"],
    "critical": ["app/tests/test_main.py", "app/tests/test_agent_flow.py"],
    "smoke": ["app/tests/routes/test_health_route.py", "app/tests/routes/test_health_endpoints.py", "app/tests/test_main.py"],
}


def setup_test_environment():
    """Setup test environment variables"""
    test_env = {
        "TESTING": "1",
        "ENVIRONMENT": "testing",
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "CLICKHOUSE_URL": "clickhouse://localhost:9000/test",
        "REDIS_URL": "redis://localhost:6379/1",
        "SECRET_KEY": "test-secret-key-for-testing-only",
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", "test-api-key"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "test-api-key"),
        "LOG_LEVEL": "WARNING",
        "GOOGLE_CLIENT_ID": "test-google-client",
        "GOOGLE_CLIENT_SECRET": "test-google-secret",
        "FRONTEND_URL": "http://localhost:3000",
    }
    
    for key, value in test_env.items():
        if key not in os.environ or os.environ.get("OVERRIDE_TEST_ENV") == "1":
            os.environ[key] = value
    
    # Configure asyncio for Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def check_dependencies() -> dict:
    """Check if required test dependencies are available"""
    status = {
        "pytest": False,
        "pytest-asyncio": False,
        "pytest-mock": False,
        "pytest-cov": False,
        "pytest-xdist": False,
        "redis": False,
        "postgresql": False,
    }
    
    # Check Python packages
    try:
        import pytest
        status["pytest"] = True
    except ImportError:
        pass
    
    try:
        import pytest_asyncio
        status["pytest-asyncio"] = True
    except ImportError:
        pass
    
    try:
        import pytest_mock
        status["pytest-mock"] = True
    except ImportError:
        pass
    
    try:
        import pytest_cov
        status["pytest-cov"] = True
    except ImportError:
        pass
    
    try:
        import xdist
        status["pytest-xdist"] = True
    except ImportError:
        pass
    
    # Check external services (optional)
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=1)
        r.ping()
        status["redis"] = True
    except:
        pass
    
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            connect_timeout=1
        )
        conn.close()
        status["postgresql"] = True
    except:
        pass
    
    return status


def build_pytest_args(args) -> List[str]:
    """Build pytest command arguments"""
    pytest_args = []
    
    # Add test paths based on category or specific paths
    if args.category:
        if args.category in TEST_CATEGORIES:
            test_paths = TEST_CATEGORIES[args.category]
            pytest_args.extend(test_paths)
        else:
            print(f"Unknown category: {args.category}")
            print(f"Available categories: {', '.join(TEST_CATEGORIES.keys())}")
            sys.exit(1)
    elif args.tests:
        pytest_args.extend(args.tests)
    else:
        # Default to all tests
        pytest_args.extend(["app/tests", "tests", "integration_tests"])
    
    # Verbosity
    if args.verbose:
        pytest_args.append("-vv")
    elif not args.quiet:
        pytest_args.append("-v")
    
    # Parallel execution
    if args.parallel and args.parallel > 0:
        pytest_args.extend(["-n", str(args.parallel)])
    elif args.parallel == -1:
        pytest_args.extend(["-n", "auto"])
    
    # Failed first
    if args.failed_first:
        pytest_args.append("--failed-first")
        pytest_args.append("--ff")
    
    # Stop on first failure
    if args.fail_fast:
        pytest_args.append("-x")
        pytest_args.append("--maxfail=1")
    
    # Coverage
    if args.coverage:
        pytest_args.extend([
            "--cov=app",
            "--cov-report=html:reports/coverage/html",
            "--cov-report=term-missing",
            "--cov-report=json:reports/coverage/coverage.json",
            f"--cov-fail-under={args.min_coverage}",
        ])
    
    # Markers
    if args.markers:
        pytest_args.extend(["-m", args.markers])
    
    # Keywords
    if args.keyword:
        pytest_args.extend(["-k", args.keyword])
    
    # Duration profiling
    if args.profile:
        pytest_args.extend(["--durations=20"])
    
    # Output format
    if args.json_output:
        pytest_args.extend(["--json-report", "--json-report-file=reports/tests/report.json"])
    
    if args.html_output:
        pytest_args.extend(["--html=reports/tests/report.html", "--self-contained-html"])
    
    # Common options
    pytest_args.extend([
        "--tb=short",
        "--asyncio-mode=auto",
        "--color=yes",
        "--strict-markers",
        "--disable-warnings" if not args.show_warnings else "",
        "-p" if not args.show_warnings else "",
        "no:warnings" if not args.show_warnings else "",
    ])
    
    # Remove empty strings
    pytest_args = [arg for arg in pytest_args if arg]
    
    return pytest_args


def run_tests(pytest_args: List[str], args) -> int:
    """Run tests with pytest"""
    import pytest
    
    # Create reports directory if needed
    if args.coverage or args.json_output or args.html_output:
        reports_dir = PROJECT_ROOT / "reports"
        reports_dir.mkdir(exist_ok=True)
        (reports_dir / "tests").mkdir(exist_ok=True)
        (reports_dir / "coverage").mkdir(exist_ok=True)
    
    print("=" * 80)
    print("NETRA AI PLATFORM - BACKEND TEST RUNNER")
    print("=" * 80)
    
    # Check dependencies
    if args.check_deps:
        print("\nChecking dependencies...")
        deps = check_dependencies()
        for dep, available in deps.items():
            status = "[OK]" if available else "[MISSING]"
            print(f"  {status} {dep}")
        print()
    
    # Display test configuration
    print("Test Configuration:")
    print(f"  Category: {args.category or 'all'}")
    print(f"  Parallel: {args.parallel if args.parallel > 0 else 'disabled'}")
    print(f"  Coverage: {'enabled' if args.coverage else 'disabled'}")
    print(f"  Fail Fast: {'enabled' if args.fail_fast else 'disabled'}")
    print(f"  Environment: {os.environ.get('ENVIRONMENT', 'testing')}")
    print()
    
    # Display command
    print("Running command:")
    print(f"  pytest {' '.join(pytest_args)}")
    print("=" * 80)
    
    # Record start time
    start_time = time.time()
    
    # Run tests
    exit_code = pytest.main(pytest_args)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Display results
    print("=" * 80)
    if exit_code == 0:
        print(f"[PASS] ALL TESTS PASSED in {duration:.2f}s")
    else:
        print(f"[FAIL] TESTS FAILED with exit code {exit_code} after {duration:.2f}s")
    
    # Show coverage summary if enabled
    if args.coverage and exit_code == 0:
        coverage_file = PROJECT_ROOT / "reports" / "coverage" / "coverage.json"
        if coverage_file.exists():
            with open(coverage_file) as f:
                coverage_data = json.load(f)
                total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
                print(f"\n[Coverage] Total Coverage: {total_coverage:.2f}%")
    
    # Show report locations
    if args.html_output:
        print(f"\n[Report] HTML Report: reports/tests/report.html")
    if args.coverage:
        print(f"[Coverage] Coverage Report: reports/coverage/html/index.html")
    
    print("=" * 80)
    
    return exit_code


def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive backend test runner for Netra AI Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python scripts/test_backend.py
  
  # Run specific category
  python scripts/test_backend.py --category unit
  python scripts/test_backend.py --category agent
  
  # Run with coverage
  python scripts/test_backend.py --coverage --min-coverage 80
  
  # Run specific test file
  python scripts/test_backend.py app/tests/test_main.py
  
  # Run tests matching keyword
  python scripts/test_backend.py -k "test_login"
  
  # Quick smoke test
  python scripts/test_backend.py --category smoke --fail-fast
  
  # Full CI/CD run
  python scripts/test_backend.py --coverage --html-output --json-output --parallel auto
        """
    )
    
    # Test selection
    parser.add_argument(
        "tests",
        nargs="*",
        help="Specific test files or directories to run"
    )
    parser.add_argument(
        "--category", "-c",
        choices=list(TEST_CATEGORIES.keys()),
        help="Run tests from a specific category"
    )
    parser.add_argument(
        "--keyword", "-k",
        help="Only run tests matching the given keyword expression"
    )
    parser.add_argument(
        "--markers", "-m",
        help="Only run tests matching given mark expression"
    )
    
    # Execution options
    parser.add_argument(
        "--parallel", "-p",
        type=int,
        default=0,
        help="Number of parallel workers (0=sequential, -1=auto)"
    )
    parser.add_argument(
        "--fail-fast", "-x",
        action="store_true",
        help="Stop on first test failure"
    )
    parser.add_argument(
        "--failed-first", "--ff",
        action="store_true",
        help="Run previously failed tests first"
    )
    
    # Coverage options
    parser.add_argument(
        "--coverage", "--cov",
        action="store_true",
        help="Enable coverage reporting"
    )
    parser.add_argument(
        "--min-coverage",
        type=int,
        default=70,
        help="Minimum coverage percentage required (default: 70)"
    )
    
    # Output options
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Minimal output"
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Generate JSON test report"
    )
    parser.add_argument(
        "--html-output",
        action="store_true",
        help="Generate HTML test report"
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Show slowest tests"
    )
    
    # Environment options
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Check test dependencies before running"
    )
    parser.add_argument(
        "--show-warnings",
        action="store_true",
        help="Show warning messages"
    )
    
    args = parser.parse_args()
    
    # Setup environment
    setup_test_environment()
    
    # Build pytest arguments
    pytest_args = build_pytest_args(args)
    
    # Run tests
    exit_code = run_tests(pytest_args, args)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
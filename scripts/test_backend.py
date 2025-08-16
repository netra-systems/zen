#!/usr/bin/env python
"""
Comprehensive backend test runner for Netra AI Platform
Designed for easy use by Claude Code and CI/CD pipelines
Now with test isolation support for concurrent execution
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

# Import test isolation utilities
try:
    from scripts.test_isolation import TestIsolationManager
except ImportError:
    TestIsolationManager = None

# Test categories for organized testing
TEST_CATEGORIES = {
    "unit": ["app/tests/services", "app/tests/core"],
    "integration": ["integration_tests", "app/tests/routes"],
    "agent": ["app/tests/agents", "app/tests/services/agents", "app/tests/services/apex_optimizer_agent"],
    "websocket": ["app/tests/test_websocket.py", "app/tests/routes/test_websocket_*.py"],
    "auth": ["app/tests/test_auth*.py", "app/tests/routes/test_*auth*.py"],
    "database": ["app/tests/services/database", "app/tests/test_database*.py"],
    "critical": ["app/tests/test_api_endpoints_critical.py", "app/tests/test_agent_service_critical.py"],
    "smoke": [
        "app/tests/routes/test_health_route.py",
        "app/tests/core/test_error_handling.py::TestNetraExceptions::test_configuration_error",
        "app/tests/core/test_config_manager.py::TestConfigManager::test_initialization",
        "app/tests/services/test_security_service.py::test_encrypt_and_decrypt",
        "tests/test_system_startup.py::TestSystemStartup::test_configuration_loading"
    ],
}


def setup_test_environment(isolation_manager=None):
    """Setup test environment variables"""
    # If using isolation manager, it will have already set up the environment
    if isolation_manager:
        # Just ensure asyncio is configured for Windows
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        return
    
    # Try to load from .env.test file first
    env_test_file = PROJECT_ROOT / ".env.test"
    if env_test_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_test_file, override=True)
            print(f"Loaded test environment from {env_test_file}")
        except ImportError:
            print("Warning: python-dotenv not installed, using default test environment")
    
    # Standard test environment setup (when not using isolation)
    test_env = {
        "TESTING": "1",
        "ENVIRONMENT": "testing",
        "DATABASE_URL": "postgresql://test:test@localhost:5432/netra_test",
        "CLICKHOUSE_URL": "clickhouse://localhost:9000/test",
        "REDIS_URL": "redis://localhost:6379/1",
        "JWT_SECRET_KEY": "test-secret-key-for-testing-only-must-be-at-least-32-chars",
        "FERNET_KEY": "test-fernet-key-for-testing-only-base64encode=",
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", "test-api-key"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "test-api-key"),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", "test-api-key"),
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
    if args.parallel == "auto":
        pytest_args.extend(["-n", "auto"])
    elif args.parallel and str(args.parallel).isdigit() and int(args.parallel) > 0:
        pytest_args.extend(["-n", str(args.parallel)])
    
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


def run_tests(pytest_args: List[str], args, isolation_manager=None) -> int:
    """Run tests with pytest"""
    import pytest
    
    # Create reports directory if needed
    if args.coverage or args.json_output or args.html_output:
        if isolation_manager and isolation_manager.directories:
            # Use isolated directories
            reports_dir = isolation_manager.directories.get('reports', PROJECT_ROOT / "reports")
        else:
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
    print(f"  Parallel: {args.parallel if str(args.parallel).isdigit() and int(args.parallel) > 0 else args.parallel if args.parallel == 'auto' else 'disabled'}")
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


def create_backend_argument_parser():
    """Create and configure backend argument parser"""
    parser = argparse.ArgumentParser(
        description="Comprehensive backend test runner for Netra AI Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=get_backend_usage_examples()
    )
    return parser


def get_backend_usage_examples():
    """Get backend usage examples string"""
    return """
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


def add_backend_test_selection_args(parser):
    """Add test selection arguments to backend parser"""
    parser.add_argument("tests", nargs="*", help="Specific test files or directories to run")
    parser.add_argument("--category", "-c", choices=list(TEST_CATEGORIES.keys()), help="Run tests from a specific category")
    parser.add_argument("--keyword", "-k", help="Only run tests matching the given keyword expression")
    parser.add_argument("--markers", "-m", help="Only run tests matching given mark expression")


def add_backend_execution_args(parser):
    """Add execution arguments to backend parser"""
    parser.add_argument("--parallel", "-p", default=0, help="Number of parallel workers (0=sequential, auto=auto, or number)")
    parser.add_argument("--fail-fast", "-x", action="store_true", help="Stop on first test failure")
    parser.add_argument("--failed-first", "--ff", action="store_true", help="Run previously failed tests first")


def add_backend_coverage_args(parser):
    """Add coverage arguments to backend parser"""
    parser.add_argument("--coverage", "--cov", action="store_true", help="Enable coverage reporting")
    parser.add_argument("--min-coverage", type=int, default=70, help="Minimum coverage percentage required (default: 70)")


def add_backend_output_args(parser):
    """Add output arguments to backend parser"""
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")
    parser.add_argument("--json-output", action="store_true", help="Generate JSON test report")
    parser.add_argument("--html-output", action="store_true", help="Generate HTML test report")
    parser.add_argument("--profile", action="store_true", help="Show slowest tests")


def add_backend_env_args(parser):
    """Add environment arguments to backend parser"""
    parser.add_argument("--check-deps", action="store_true", help="Check test dependencies before running")
    parser.add_argument("--show-warnings", action="store_true", help="Show warning messages")
    parser.add_argument("--isolation", action="store_true", help="Use test isolation for concurrent execution")


def setup_backend_isolation_manager(args):
    """Setup backend test isolation manager if requested"""
    if not (args.isolation and TestIsolationManager):
        return None
    manager = TestIsolationManager()
    manager.setup_environment()
    manager.apply_environment()
    manager.register_cleanup()
    return manager


def prepare_pytest_args(args, isolation_manager):
    """Prepare pytest arguments with isolation if needed"""
    pytest_args = build_pytest_args(args)
    if isolation_manager:
        isolation_args = isolation_manager.get_pytest_args()
        pytest_args.extend(isolation_args)
    return pytest_args


def main():
    """Main entry point for backend test runner"""
    parser = create_backend_argument_parser()
    add_backend_test_selection_args(parser)
    add_backend_execution_args(parser)
    add_backend_coverage_args(parser)
    add_backend_output_args(parser)
    add_backend_env_args(parser)
    args = parser.parse_args()
    
    isolation_manager = setup_backend_isolation_manager(args)
    setup_test_environment(isolation_manager)
    pytest_args = prepare_pytest_args(args, isolation_manager)
    exit_code = run_tests(pytest_args, args, isolation_manager)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
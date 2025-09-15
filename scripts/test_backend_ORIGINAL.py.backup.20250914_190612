from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
#!/usr/bin/env python
"""
env = get_env()
Comprehensive backend test runner for Netra AI Platform
Designed for easy use by Claude Code and CI/CD pipelines
Now with test isolation support for concurrent execution
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

# Add project root to path

# Import test isolation utilities
try:
    from test_framework.test_isolation import TestIsolationManager
except ImportError:
    TestIsolationManager = None

# Test categories for organized testing
TEST_CATEGORIES = {
    "unit": ["netra_backend/tests/services", "netra_backend/tests/core"],
    "integration": ["netra_backend/tests/integration", "netra_backend/tests/routes"],
    "agent": ["netra_backend/tests/agents", "netra_backend/tests/services/agents", "netra_backend/tests/services/apex_optimizer_agent"],
    "websocket": ["netra_backend/tests/test_websocket.py", "netra_backend/tests/routes/test_websocket_*.py"],
    "auth": ["netra_backend/tests/test_auth*.py", "netra_backend/tests/routes/test_*auth*.py"],
    "database": ["netra_backend/tests/services/database", "netra_backend/tests/test_database*.py"],
    "critical": ["netra_backend/tests/test_api_endpoints_critical.py", "netra_backend/tests/test_agent_service_critical.py"],
    "smoke": [
        "netra_backend/tests/routes/test_health_route.py",
        "netra_backend/tests/core/test_error_handling.py::TestNetraExceptions::test_configuration_error",
        "netra_backend/tests/core/test_config_manager.py::TestSecretManager::test_initialization",
        "netra_backend/tests/services/test_security_service.py::test_encrypt_and_decrypt",
        "netra_backend/tests/e2e/test_system_startup.py::TestSystemStartup"
    ],
}


def setup_test_environment(isolation_manager=None):
    """Setup test environment variables"""
    if isolation_manager:
        _configure_windows_asyncio()
        return
    _setup_dotenv_test_config()
    _apply_standard_test_environment()
    _configure_windows_asyncio()

def _configure_windows_asyncio():
    """Configure asyncio for Windows platform"""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

def _setup_dotenv_test_config():
    """Setup test configuration from .env.mock file (or legacy .env.test)"""
    env_test_file = PROJECT_ROOT / ".env.mock"
    if not env_test_file.exists():
        env_test_file = PROJECT_ROOT / ".env.test"  # Legacy fallback
    if not env_test_file.exists():
        return
    _load_dotenv_file(env_test_file)

def _load_dotenv_file(env_test_file):
    """Load environment from dotenv file"""
    try:
        from dotenv import load_dotenv
        load_dotenv(env_test_file, override=True)
        print(f"Loaded test environment from {env_test_file}")
    except ImportError:
        print("Warning: python-dotenv not installed, using default test environment")

def _create_test_environment_dict():
    """Create standard test environment dictionary"""
    return {
        "TESTING": "1", "ENVIRONMENT": "testing",
        "DATABASE_URL": "postgresql://test:test@localhost:5432/netra_test",
        "CLICKHOUSE_URL": "clickhouse://localhost:9000/test",
        "REDIS_URL": "redis://localhost:6379/1",
        "JWT_SECRET_KEY": "test-secret-key-for-testing-only-must-be-at-least-32-chars",
        "FERNET_KEY": "test-fernet-key-for-testing-only-base64encode=",
        "ANTHROPIC_API_KEY": get_env().get("ANTHROPIC_API_KEY", "test-api-key")
    }

def _add_additional_test_env_vars(test_env):
    """Add additional test environment variables"""
    additional_vars = {
        "OPENAI_API_KEY": get_env().get("OPENAI_API_KEY", "test-api-key"),
        "GEMINI_API_KEY": get_env().get("GEMINI_API_KEY", "test-api-key"),
        "LOG_LEVEL": "WARNING", "GOOGLE_CLIENT_ID": "test-google-client",
        "GOOGLE_CLIENT_SECRET": "test-google-secret", "FRONTEND_URL": "http://localhost:3000"
    }
    test_env.update(additional_vars)

def _apply_standard_test_environment():
    """Apply standard test environment when not using isolation"""
    test_env = _create_test_environment_dict()
    _add_additional_test_env_vars(test_env)
    _apply_environment_variables(test_env)

def _apply_environment_variables(test_env):
    """Apply environment variables to os.environ"""
    for key, value in test_env.items():
        should_override = key not in os.environ or env.get("OVERRIDE_TEST_ENV") == "1"
        if should_override:
            os.environ[key] = value


def _initialize_dependency_status():
    """Initialize dependency status dictionary"""
    return {
        "pytest": False, "pytest-asyncio": False, "pytest-mock": False,
        "pytest-cov": False, "pytest-xdist": False, "redis": False, "postgresql": False
    }

def _check_python_package(package_name, status_key, status):
    """Check if a Python package is available"""
    try:
        __import__(package_name)
        status[status_key] = True
    except ImportError:
        pass

def _check_redis_service(status):
    """Check Redis service availability"""
    try:
        import redis
        r = await get_redis_client()  # MIGRATED: was redis.Redis(host='localhost', port=6379, socket_connect_timeout=1)
        r.ping()
        status["redis"] = True
    except:
        pass

def _check_postgresql_service(status):
    """Check PostgreSQL service availability"""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost", port=5432, user="postgres",
            password="postgres", connect_timeout=1
        )
        conn.close()
        status["postgresql"] = True
    except:
        pass

def _check_all_python_packages(status):
    """Check all required Python packages"""
    packages = [("pytest", "pytest"), ("pytest_asyncio", "pytest-asyncio"),
                ("xdist", "pytest-xdist")]
    for pkg_name, status_key in packages:
        _check_python_package(pkg_name, status_key, status)

def _check_external_services(status):
    """Check external service availability"""
    _check_redis_service(status)
    _check_postgresql_service(status)

def check_dependencies() -> dict:
    """Check if required test dependencies are available"""
    status = _initialize_dependency_status()
    _check_all_python_packages(status)
    _check_external_services(status)
    return status


def build_pytest_args(args) -> List[str]:
    """Build pytest command arguments"""
    pytest_args = []
    _add_config_file_args(pytest_args)
    _add_test_paths(args, pytest_args)
    _add_verbosity_args(args, pytest_args)
    _add_parallel_args(args, pytest_args)
    _add_execution_control_args(args, pytest_args)
    _add_coverage_args(args, pytest_args)
    _add_filter_args(args, pytest_args)
    _add_output_args(args, pytest_args)
    _add_bad_test_detection_args(args, pytest_args)
    return [arg for arg in pytest_args if arg]

def _add_config_file_args(pytest_args):
    """Add pytest configuration file path"""
    # Use netra_backend pytest.ini for backend tests if it exists
    netra_backend_pytest = PROJECT_ROOT / "netra_backend" / "pytest.ini"
    root_pytest_ini = PROJECT_ROOT / "pytest.ini"
    
    # Prefer netra_backend pytest.ini for proper path resolution
    if netra_backend_pytest.exists():
        pytest_args.extend(["-c", str(netra_backend_pytest)])
    elif root_pytest_ini.exists():
        pytest_args.extend(["-c", str(root_pytest_ini)])

def _add_test_paths(args, pytest_args):
    """Add test paths based on category or specific paths"""
    if args.category:
        _handle_category_selection(args, pytest_args)
    elif args.tests:
        pytest_args.extend(args.tests)
    else:
        pytest_args.extend(["netra_backend/tests", "tests", "integration_tests"])

def _handle_category_selection(args, pytest_args):
    """Handle test category selection"""
    if args.category in TEST_CATEGORIES:
        test_paths = TEST_CATEGORIES[args.category]
        pytest_args.extend(test_paths)
    else:
        _print_category_error(args.category)
        sys.exit(1)

def _print_category_error(category):
    """Print error for unknown category"""
    print(f"Unknown category: {category}")
    print(f"Available categories: {', '.join(TEST_CATEGORIES.keys())}")

def _add_verbosity_args(args, pytest_args):
    """Add verbosity arguments"""
    if args.verbose:
        pytest_args.append("-vv")
    elif not args.quiet:
        pytest_args.append("-v")

def _add_parallel_args(args, pytest_args):
    """Add parallel execution arguments"""
    if args.parallel == "auto":
        pytest_args.extend(["-n", "auto"])
    elif args.parallel and str(args.parallel).isdigit() and int(args.parallel) > 0:
        pytest_args.extend(["-n", str(args.parallel)])

def _add_execution_control_args(args, pytest_args):
    """Add execution control arguments"""
    _add_failed_first_args(args, pytest_args)
    _add_fail_fast_args(args, pytest_args)
    _add_common_options(args, pytest_args)

def _add_failed_first_args(args, pytest_args):
    """Add failed first arguments"""
    if args.failed_first:
        pytest_args.append("--failed-first")
        pytest_args.append("--ff")

def _add_fail_fast_args(args, pytest_args):
    """Add fail fast arguments"""
    if args.fail_fast:
        pytest_args.append("-x")
        pytest_args.append("--maxfail=1")

def _add_coverage_args(args, pytest_args):
    """Add coverage arguments"""
    if not args.coverage:
        return
    coverage_options = _get_coverage_options(args)
    pytest_args.extend(coverage_options)

def _get_coverage_options(args):
    """Get coverage configuration options"""
    return [
        "--cov=netra_backend.app", "--cov-report=html:reports/coverage/html",
        "--cov-report=term-missing", "--cov-report=json:reports/coverage/coverage.json",
        f"--cov-fail-under={args.min_coverage}"
    ]

def _add_filter_args(args, pytest_args):
    """Add filter arguments (markers and keywords)"""
    if args.markers:
        pytest_args.extend(["-m", args.markers])
    if args.keyword:
        pytest_args.extend(["-k", args.keyword])
    if args.profile:
        pytest_args.extend(["--durations=20"])

def _add_output_args(args, pytest_args):
    """Add output format arguments"""
    if args.json_output:
        pytest_args.extend(["--json-report", "--json-report-file=reports/tests/report.json"])
    if args.html_output:
        pytest_args.extend(["--html=reports/tests/report.html", "--self-contained-html"])

def _add_common_options(args, pytest_args):
    """Add common pytest options"""
    common_opts = ["--tb=short", "--asyncio-mode=auto", "--color=yes", "--strict-markers"]
    pytest_args.extend(common_opts)
    if not args.show_warnings:
        pytest_args.extend(["--disable-warnings", "-p", "no:warnings"])

def _add_bad_test_detection_args(args, pytest_args):
    """Add bad test detection plugin arguments"""
    # Bad test detection disabled - using single test_results.json
    # pytest_args.extend(["-p", "test_framework.pytest_bad_test_plugin"])
    
    # Component info not needed since plugin is disabled
    # pytest_args.extend(["--test-component", "backend"])


def setup_reports_directory(args, isolation_manager=None) -> Path:
    """Setup reports directory structure."""
    if not _should_create_reports(args):
        return None
    reports_dir = _get_reports_directory(isolation_manager)
    _ensure_report_subdirectories(reports_dir, isolation_manager)
    return reports_dir

def _should_create_reports(args):
    """Check if any report generation is enabled"""
    return args.coverage or args.json_output or args.html_output

def _get_reports_directory(isolation_manager):
    """Get the reports directory path"""
    if isolation_manager and isolation_manager.directories:
        return isolation_manager.directories.get('reports', PROJECT_ROOT / "reports")
    return PROJECT_ROOT / "reports"

def _ensure_report_subdirectories(reports_dir, isolation_manager):
    """Ensure report subdirectories exist"""
    if isolation_manager and isolation_manager.directories:
        return
    reports_dir.mkdir(exist_ok=True)
    (reports_dir / "tests").mkdir(exist_ok=True)
    (reports_dir / "coverage").mkdir(exist_ok=True)

def display_test_header_and_deps(args):
    """Display test runner header and check dependencies."""
    _print_test_runner_header()
    if args.check_deps:
        _check_and_display_dependencies()

def _print_test_runner_header():
    """Print the test runner header"""
    print("=" * 80)
    print("NETRA AI PLATFORM - BACKEND TEST RUNNER")
    print("=" * 80)

def _check_and_display_dependencies():
    """Check and display dependency status"""
    print("\nChecking dependencies...")
    deps = check_dependencies()
    _display_dependency_statuses(deps)
    print()

def _display_dependency_statuses(deps):
    """Display status for each dependency"""
    for dep, available in deps.items():
        status = "[OK]" if available else "[MISSING]"
        print(f"  {status} {dep}")

def display_test_configuration(args, pytest_args):
    """Display test configuration and command."""
    parallel_status = _get_parallel_status(args)
    _print_test_config_details(args, parallel_status)
    _print_pytest_command(pytest_args)

def _get_parallel_status(args):
    """Get parallel execution status string"""
    if str(args.parallel).isdigit() and int(args.parallel) > 0:
        return args.parallel
    return args.parallel if args.parallel == 'auto' else 'disabled'

def _print_test_config_details(args, parallel_status):
    """Print test configuration details"""
    print("Test Configuration:")
    print(f"  Category: {args.category or 'all'}")
    print(f"  Parallel: {parallel_status}")
    print(f"  Coverage: {'enabled' if args.coverage else 'disabled'}")
    print(f"  Fail Fast: {'enabled' if args.fail_fast else 'disabled'}")
    print(f"  Environment: {env.get('ENVIRONMENT', 'testing')}")

def _print_pytest_command(pytest_args):
    """Print the pytest command being executed"""
    print(f"\nRunning command:\n  pytest {' '.join(pytest_args)}")
    print("=" * 80)

def execute_pytest_with_timing(pytest_args) -> Tuple[int, float]:
    """Execute pytest and return exit code and duration."""
    import pytest
    start_time = time.time()
    exit_code = pytest.main(pytest_args)
    duration = time.time() - start_time
    return exit_code, duration

def display_test_results(exit_code: int, duration: float, args):
    """Display test results, coverage, and report locations."""
    print("=" * 80)
    _print_test_outcome(exit_code, duration)
    _show_coverage_summary(args, exit_code)
    _show_report_locations(args)
    print("=" * 80)

def _print_test_outcome(exit_code: int, duration: float):
    """Print test outcome message"""
    if exit_code == 0:
        print(f"[PASS] ALL TESTS PASSED in {duration:.2f}s")
    else:
        print(f"[FAIL] TESTS FAILED with exit code {exit_code} after {duration:.2f}s")

def _show_coverage_summary(args, exit_code: int):
    """Show coverage summary if enabled and tests passed."""
    if not (args.coverage and exit_code == 0):
        return
    coverage_file = PROJECT_ROOT / "reports" / "coverage" / "coverage.json"
    _display_coverage_from_file(coverage_file)

def _display_coverage_from_file(coverage_file):
    """Display coverage percentage from coverage file"""
    if not coverage_file.exists():
        return
    with open(coverage_file) as f:
        coverage_data = json.load(f)
        total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
        print(f"\n[Coverage] Total Coverage: {total_coverage:.2f}%")

def _show_report_locations(args):
    """Show locations of generated reports."""
    if args.html_output:
        print(f"\n[Report] HTML Report: reports/tests/report.html")
    if args.coverage:
        print(f"[Coverage] Coverage Report: reports/coverage/html/index.html")

def run_tests(pytest_args: List[str], args, isolation_manager=None) -> int:
    """Run tests with pytest"""
    setup_reports_directory(args, isolation_manager)
    display_test_header_and_deps(args)
    display_test_configuration(args, pytest_args)
    exit_code, duration = execute_pytest_with_timing(pytest_args)
    display_test_results(exit_code, duration, args)
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
    basic_examples = _get_basic_usage_examples()
    advanced_examples = _get_advanced_usage_examples()
    return f"\n{basic_examples}{advanced_examples}"

def _get_basic_usage_examples():
    """Get basic usage examples"""
    return """Examples:
  # Run all tests
  python unified_test_runner.py --service backend
  
  # Run specific category
  python unified_test_runner.py --service backend --category unit
  python unified_test_runner.py --service backend --category agent"""

def _get_advanced_usage_examples():
    """Get advanced usage examples"""
    return """
  
  # Run with coverage
  python unified_test_runner.py --service backend --coverage --min-coverage 80
  
  # Run specific test file
  python unified_test_runner.py --service backend netra_backend/tests/test_main.py
  
  # Run tests matching keyword
  python unified_test_runner.py --service backend -k "test_login"
  
  # Quick smoke test
  python unified_test_runner.py --service backend --category smoke --fail-fast
  
  # Full CI/CD run
  python unified_test_runner.py --service backend --coverage --html-output --json-output --parallel auto
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
    parser.add_argument("--no-bad-test-detection", action="store_true", help="Disable bad test detection")


def setup_backend_isolation_manager(args):
    """Setup backend test isolation manager if requested"""
    if not (args.isolation and TestIsolationManager):
        return None
    return _create_configured_isolation_manager()

def _create_configured_isolation_manager():
    """Create and configure isolation manager"""
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
    parser = _create_configured_parser()
    args = parser.parse_args()
    isolation_manager = setup_backend_isolation_manager(args)
    setup_test_environment(isolation_manager)
    pytest_args = prepare_pytest_args(args, isolation_manager)
    exit_code = run_tests(pytest_args, args, isolation_manager)
    sys.exit(exit_code)

def _create_configured_parser():
    """Create and configure argument parser with all options"""
    parser = create_backend_argument_parser()
    add_backend_test_selection_args(parser)
    add_backend_execution_args(parser)
    add_backend_coverage_args(parser)
    add_backend_output_args(parser)
    add_backend_env_args(parser)
    return parser


if __name__ == "__main__":
    main()

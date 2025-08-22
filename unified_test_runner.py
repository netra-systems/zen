#!/usr/bin/env python
"""
NETRA APEX UNIFIED TEST RUNNER
==============================
Single entry point for ALL testing operations across the entire Netra platform.
This runner coordinates testing for backend, frontend, auth service, and integration tests.

USAGE:
    python unified_test_runner.py              # Run default test suite
    python unified_test_runner.py --help       # Show all options
    
TEST LEVELS:
    unit            Fast isolated component tests (1-3min)
    integration     Service interaction tests (3-8min) [DEFAULT]
    e2e             End-to-end real service tests (10-30min)
    performance     Performance and load testing (3-10min)
    comprehensive   Complete system validation (30-60min)
    
    Legacy levels (deprecated, will redirect):
    smoke, critical, agents -> unit
    real_e2e, real_services, staging* -> e2e

SERVICES:
    backend         Main backend application
    auth            Auth service
    frontend        Frontend application
    dev_launcher    Development launcher and system startup tests
    all             Run tests for all services

EXAMPLES:
    python unified_test_runner.py                           # Run integration tests (default)
    python unified_test_runner.py --level unit              # Quick development tests
    python unified_test_runner.py --level e2e --real-llm    # Real service E2E tests
    python unified_test_runner.py --level performance       # Performance validation
    python unified_test_runner.py --level comprehensive     # Full release validation
    python unified_test_runner.py --service dev_launcher    # Run only dev_launcher tests
    python unified_test_runner.py --service dev_launcher --level unit  # Quick dev_launcher validation
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Project root
PROJECT_ROOT = Path(__file__).parent.absolute()

def _check_pytest_timeout_installed() -> bool:
    """Check if pytest-timeout plugin is installed."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", "pytest-timeout"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False

# Import test framework
from test_framework.runner import UnifiedTestRunner as FrameworkRunner
from test_framework.test_config import TEST_LEVELS, configure_dev_environment, configure_real_llm, resolve_test_level
from test_framework.test_discovery import TestDiscovery
from test_framework.test_validation import TestValidation


class UnifiedTestRunner:
    """Main test runner orchestrating all test operations."""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.test_framework_path = self.project_root / "test_framework"
        self.backend_path = self.project_root / "netra_backend"
        self.auth_path = self.project_root / "auth_service"
        self.frontend_path = self.project_root / "frontend"
        
        # Test configurations
        self.test_configs = {
            "backend": {
                "path": self.backend_path,
                "test_dir": "tests",
                "config": "pytest.ini",
                "command": "pytest"
            },
            "auth": {
                "path": self.auth_path,
                "test_dir": "tests",
                "config": "pytest.ini",
                "command": "pytest"
            },
            "frontend": {
                "path": self.frontend_path,
                "test_dir": "__tests__",
                "config": "jest.config.cjs",
                "command": "npm test"
            },
            "dev_launcher": {
                "path": self.project_root,
                "test_dir": "tests",
                "config": "pytest.ini",
                "command": "pytest"
            }
        }
        
    def run(self, args: argparse.Namespace) -> int:
        """Main entry point for test execution."""
        
        # Configure environment
        self._configure_environment(args)
        
        # Determine which services to test
        services = self._get_services_to_test(args)
        
        # Run tests for each service
        results = {}
        for service in services:
            print(f"\n{'='*60}")
            print(f"Running {service.upper()} tests - Level: {args.level}")
            print(f"{'='*60}\n")
            
            result = self._run_service_tests(service, args)
            results[service] = result
            
        # Generate consolidated report
        self._generate_report(results, args)
        
        # Return overall status
        return 0 if all(r["success"] for r in results.values()) else 1
    
    def _configure_environment(self, args: argparse.Namespace):
        """Configure test environment based on arguments."""
        if args.env == "dev":
            configure_dev_environment()
        elif args.real_llm:
            # Use default values for real LLM configuration
            configure_real_llm(
                model="gemini-2.5-flash",  # Default model
                timeout=60,  # Default timeout
                parallel="auto",  # Auto-detect parallelism
                test_level=args.level,  # Pass the test level
                use_dedicated_env=True  # Use dedicated test environment
            )
            
        # Set environment variables
        os.environ["TEST_LEVEL"] = args.level
        os.environ["TEST_ENV"] = args.env
        
        if args.no_coverage:
            os.environ["COVERAGE_ENABLED"] = "false"
        
    def _get_services_to_test(self, args: argparse.Namespace) -> List[str]:
        """Determine which services to test based on arguments."""
        if args.service == "all":
            return ["backend", "auth", "frontend", "dev_launcher"]
        return [args.service]
    
    def _run_service_tests(self, service: str, args: argparse.Namespace) -> Dict:
        """Run tests for a specific service."""
        config = self.test_configs[service]
        
        # Build test command
        if service == "frontend":
            cmd = self._build_frontend_command(args)
        elif service == "dev_launcher":
            cmd = self._build_dev_launcher_command(args)
        else:
            cmd = self._build_pytest_command(service, args)
        
        # Execute tests
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=config["path"],
                capture_output=True,
                text=True,
                shell=True,
                encoding='utf-8',
                errors='replace'
            )
            success = result.returncode == 0
        except Exception as e:
            print(f"[ERROR] Failed to run {service} tests: {e}")
            success = False
            result = None
        
        duration = time.time() - start_time
        
        return {
            "success": success,
            "duration": duration,
            "output": result.stdout if result else "",
            "errors": result.stderr if result else ""
        }
    
    def _build_pytest_command(self, service: str, args: argparse.Namespace) -> str:
        """Build pytest command for backend/auth services."""
        config = self.test_configs[service]
        
        cmd_parts = ["pytest"]
        
        # Add test directory
        cmd_parts.append(str(config["test_dir"]))
        
        # Add level-specific markers
        if args.level in TEST_LEVELS:
            level_config = TEST_LEVELS[args.level]
            if "markers" in level_config:
                for marker in level_config["markers"]:
                    cmd_parts.append(f"-m {marker}")
        
        # Add coverage options
        if not args.no_coverage:
            cmd_parts.extend([
                "--cov=.",
                "--cov-report=html",
                "--cov-report=term-missing"
            ])
        
        # Add parallelization
        if args.parallel:
            cmd_parts.append(f"-n {args.workers}")
        
        # Add verbosity
        if args.verbose:
            cmd_parts.append("-vv")
        
        # Add fast fail
        if args.fast_fail:
            cmd_parts.append("-x")
        
        # Add specific test pattern
        if args.pattern:
            cmd_parts.append(f"-k {args.pattern}")
        
        return " ".join(cmd_parts)
    
    def _build_dev_launcher_command(self, args: argparse.Namespace) -> str:
        """Build pytest command for dev_launcher tests."""
        cmd_parts = ["pytest"]
        
        # Dev launcher test patterns - tests that validate dev_launcher functionality
        dev_launcher_patterns = [
            "tests/test_system_startup.py",
            "tests/e2e/test_dev_launcher_real_startup.py", 
            "tests/e2e/integration/test_dev_launcher_startup_complete.py",
            "tests/integration/test_dev_launcher_utilities_validation.py",
            "-k", "dev_launcher"
        ]
        
        # Add test level specific filtering
        if args.level == "unit":
            # For unit tests, focus on basic dev_launcher functionality
            cmd_parts.extend([
                "tests/test_system_startup.py::TestSystemStartup::test_dev_launcher_help",
                "tests/test_system_startup.py::TestSystemStartup::test_dev_launcher_list_services",
                "tests/test_system_startup.py::TestSystemStartup::test_dev_launcher_minimal_mode"
            ])
        elif args.level == "integration":
            # For integration tests, include service interaction tests
            cmd_parts.extend([
                "tests/e2e/test_dev_launcher_real_startup.py",
                "tests/integration/test_dev_launcher_utilities_validation.py",
                "tests/test_system_startup.py"
            ])
            # Only add timeout if pytest-timeout is installed
            if _check_pytest_timeout_installed():
                cmd_parts.append("--timeout=300")  # 5 minute timeout for integration tests
        elif args.level == "e2e":
            # For e2e tests, include comprehensive startup tests
            cmd_parts.extend(dev_launcher_patterns)
            # Only add timeout if pytest-timeout is installed
            if _check_pytest_timeout_installed():
                cmd_parts.extend(["--timeout=600"])  # 10 minute timeout for e2e tests
        elif args.level == "performance":
            # For performance tests, focus on startup performance
            cmd_parts.extend([
                "tests/e2e/test_dev_launcher_real_startup.py::TestDevLauncherRealStartup::test_service_startup_order_validation"
            ])
            # Only add timeout if pytest-timeout is installed  
            if _check_pytest_timeout_installed():
                cmd_parts.append("--timeout=300")
        elif args.level == "comprehensive":
            # For comprehensive tests, run all dev_launcher tests
            cmd_parts.extend(dev_launcher_patterns)
            # Only add timeout if pytest-timeout is installed
            if _check_pytest_timeout_installed():
                cmd_parts.extend(["--timeout=900"])  # 15 minute timeout for comprehensive tests
        else:
            # Default pattern
            cmd_parts.extend(dev_launcher_patterns)
        
        # Add coverage options (skip for performance tests)
        if not args.no_coverage and args.level not in ["performance", "e2e"]:
            cmd_parts.extend([
                "--cov=scripts.dev_launcher",
                "--cov=scripts.dev_launcher_core", 
                "--cov=scripts.dev_launcher_config",
                "--cov-report=html:htmlcov/dev_launcher",
                "--cov-report=term-missing"
            ])
        
        # Add parallelization (limited for dev_launcher tests due to port conflicts)
        if args.parallel and args.level not in ["e2e", "performance"]:
            # Limited parallelization to avoid port conflicts
            cmd_parts.append("-n 2")
        
        # Add verbosity
        if args.verbose:
            cmd_parts.append("-vv")
        
        # Add fast fail
        if args.fast_fail:
            cmd_parts.append("-x")
        
        # Add specific test pattern
        if args.pattern:
            cmd_parts.append(f"-k {args.pattern}")
        
        # Windows compatibility - ensure proper test isolation
        cmd_parts.extend([
            "--tb=short",  # Shorter tracebacks for cleaner output
            "--strict-markers",  # Ensure test markers are defined
            "--disable-warnings"  # Reduce noise in dev_launcher tests
        ])
        
        return " ".join(cmd_parts)
    
    def _build_frontend_command(self, args: argparse.Namespace) -> str:
        """Build test command for frontend using level mapping."""
        from test_framework.frontend_test_mapping import get_jest_command_for_level
        
        # Use the mapping to get appropriate Jest command
        base_command = get_jest_command_for_level(args.level)
        
        # Add additional flags based on args
        if args.no_coverage and "--coverage" not in base_command:
            base_command += " --coverage=false"
        if args.fast_fail and "--bail" not in base_command:
            base_command += " --bail"
        if args.verbose:
            base_command += " --verbose"
            
        return base_command
    
    def _generate_report(self, results: Dict, args: argparse.Namespace):
        """Generate consolidated test report."""
        report_dir = self.project_root / "test_reports"
        report_dir.mkdir(exist_ok=True)
        
        # Create timestamp for report
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Build report data
        report_data = {
            "timestamp": timestamp,
            "level": args.level,
            "environment": args.env,
            "services": results,
            "overall_success": all(r["success"] for r in results.values()),
            "total_duration": sum(r["duration"] for r in results.values())
        }
        
        # Save JSON report
        json_report = report_dir / f"unified_test_report_{timestamp}.json"
        with open(json_report, "w") as f:
            json.dump(report_data, f, indent=2)
        
        # Print summary
        print(f"\n{'='*60}")
        print("TEST EXECUTION SUMMARY")
        print(f"{'='*60}")
        print(f"Level: {args.level}")
        print(f"Environment: {args.env}")
        print(f"Total Duration: {report_data['total_duration']:.2f}s")
        print(f"\nService Results:")
        
        for service, result in results.items():
            status = "PASSED" if result["success"] else "FAILED"
            print(f"  {service:10} {status:10} ({result['duration']:.2f}s)")
        
        print(f"\nOverall: {'PASSED' if report_data['overall_success'] else 'FAILED'}")
        print(f"Report saved: {json_report}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified Test Runner for Netra Apex Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Test level selection - new 5-level system with backward compatibility
    parser.add_argument(
        "--level",
        choices=["unit", "integration", "e2e", "performance", "comprehensive", 
                # Legacy levels for backward compatibility
                "smoke", "critical", "agents", "real_e2e", "real_services", 
                "staging", "staging-real", "staging-quick"],
        default="integration",
        help="Test level to run (default: integration). See docs for 5-level system."
    )
    
    # Service selection
    parser.add_argument(
        "--service",
        choices=["backend", "auth", "frontend", "dev_launcher", "all"],
        default="all",
        help="Service to test (default: all)"
    )
    
    # Environment configuration
    parser.add_argument(
        "--env",
        choices=["local", "dev", "staging", "prod"],
        default="local",
        help="Environment to test against (default: local)"
    )
    
    # LLM configuration
    parser.add_argument(
        "--real-llm",
        action="store_true",
        help="Use real LLM instead of mocks"
    )
    
    # Coverage options
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Disable coverage reporting"
    )
    
    # Execution options
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)"
    )
    
    parser.add_argument(
        "--fast-fail",
        action="store_true",
        help="Stop on first test failure"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--pattern",
        help="Run tests matching pattern"
    )
    
    # Discovery options
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available tests without running"
    )
    
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate test structure and configuration"
    )
    
    args = parser.parse_args()
    
    # Handle special operations
    if args.list:
        # Simple pytest-based test listing for now
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "-q", "tests/integration/"], 
            capture_output=True, text=True, cwd=PROJECT_ROOT
        )
        if result.returncode == 0:
            print("Integration Tests Found:")
            for line in result.stdout.strip().split('\n')[:20]:  # Show first 20
                if "::" in line:
                    print(f"  - {line}")
        else:
            print("Error collecting tests:")
            print(result.stderr)
        return 0
    
    if args.validate:
        validator = TestValidation(PROJECT_ROOT)
        issues = validator.validate_all()
        if issues:
            print("Validation Issues Found:")
            for issue in issues:
                print(f"  - {issue}")
            return 1
        print("All tests validated successfully")
        return 0
    
    # Run tests
    runner = UnifiedTestRunner()
    return runner.run(args)


if __name__ == "__main__":
    sys.exit(main())
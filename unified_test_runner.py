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
    smoke           Quick validation (<30s)
    unit            Component testing (1-2min)  
    integration     Feature testing (3-5min)
    comprehensive   Full coverage (30-45min)
    critical        Essential paths (1-2min)

SERVICES:
    backend         Main backend application
    auth            Auth service
    frontend        Frontend application
    all             Run tests for all services

EXAMPLES:
    python unified_test_runner.py --level smoke
    python unified_test_runner.py --service backend --level integration
    python unified_test_runner.py --real-llm --env staging
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
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import test framework
from test_framework.runner import UnifiedTestRunner as FrameworkRunner
from test_framework.test_config import TEST_LEVELS, configure_dev_environment, configure_real_llm
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
            configure_real_llm()
            
        # Set environment variables
        os.environ["TEST_LEVEL"] = args.level
        os.environ["TEST_ENV"] = args.env
        
        if args.no_coverage:
            os.environ["COVERAGE_ENABLED"] = "false"
        
    def _get_services_to_test(self, args: argparse.Namespace) -> List[str]:
        """Determine which services to test based on arguments."""
        if args.service == "all":
            return ["backend", "auth", "frontend"]
        return [args.service]
    
    def _run_service_tests(self, service: str, args: argparse.Namespace) -> Dict:
        """Run tests for a specific service."""
        config = self.test_configs[service]
        
        # Build test command
        if service == "frontend":
            cmd = self._build_frontend_command(args)
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
                shell=True
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
    
    def _build_frontend_command(self, args: argparse.Namespace) -> str:
        """Build test command for frontend."""
        if args.level == "smoke":
            return "npm run test:smoke"
        elif args.level == "unit":
            return "npm run test:unit"
        elif args.level == "integration":
            return "npm run test:integration"
        else:
            return "npm test"
    
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
            status = "✓ PASSED" if result["success"] else "✗ FAILED"
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
    
    # Test level selection
    parser.add_argument(
        "--level",
        choices=["smoke", "unit", "integration", "comprehensive", "critical", "agents"],
        default="integration",
        help="Test level to run (default: integration)"
    )
    
    # Service selection
    parser.add_argument(
        "--service",
        choices=["backend", "auth", "frontend", "all"],
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
        discovery = TestDiscovery(PROJECT_ROOT)
        tests = discovery.discover_tests()
        for category, test_list in tests.items():
            print(f"\n{category}:")
            for test in test_list[:5]:  # Show first 5
                print(f"  - {test}")
            if len(test_list) > 5:
                print(f"  ... and {len(test_list)-5} more")
        return 0
    
    if args.validate:
        validator = TestValidation(PROJECT_ROOT)
        issues = validator.validate_all()
        if issues:
            print("Validation Issues Found:")
            for issue in issues:
                print(f"  - {issue}")
            return 1
        print("✓ All tests validated successfully")
        return 0
    
    # Run tests
    runner = UnifiedTestRunner()
    return runner.run(args)


if __name__ == "__main__":
    sys.exit(main())
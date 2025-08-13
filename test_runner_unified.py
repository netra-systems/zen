#!/usr/bin/env python3
"""Unified Test Runner for Netra Platform.

This simplified test runner consolidates all test configurations and provides
a single entry point for running tests at different levels.
"""

import os
import sys
import time
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================================
# TEST LEVEL DEFINITIONS
# ============================================================================

@dataclass
class TestLevel:
    """Test level configuration."""
    name: str
    description: str
    markers: str
    timeout: int
    max_failures: Optional[int] = None
    coverage: bool = False
    parallel: bool = True
    estimated_time: str = "varies"
    
    def get_pytest_args(self) -> List[str]:
        """Get pytest arguments for this level."""
        args = [
            "-c", "config/test_config_unified.ini",
            "-m", self.markers,
            f"--timeout={self.timeout}",
        ]
        
        if self.max_failures:
            args.extend(["--maxfail", str(self.max_failures)])
        
        if self.coverage:
            args.extend([
                "--cov=app",
                "--cov-report=term-missing:skip-covered",
                "--cov-report=html",
                "--cov-report=xml"
            ])
        
        if self.parallel:
            # Use auto to detect CPU cores automatically
            args.extend(["-n", "auto"])
        
        return args


# Define test levels
TEST_LEVELS = {
    "smoke": TestLevel(
        name="smoke",
        description="Quick validation tests for pre-commit checks",
        markers="smoke",
        timeout=30,
        max_failures=1,
        coverage=False,
        parallel=True,
        estimated_time="< 30 seconds"
    ),
    "unit": TestLevel(
        name="unit",
        description="Unit tests for individual components",
        markers="unit and not slow",
        timeout=120,
        coverage=True,
        parallel=True,
        estimated_time="1-2 minutes"
    ),
    "integration": TestLevel(
        name="integration",
        description="Integration tests for feature validation",
        markers="integration",
        timeout=300,
        coverage=True,
        parallel=False,  # Integration tests often need sequential execution
        estimated_time="3-5 minutes"
    ),
    "comprehensive": TestLevel(
        name="comprehensive",
        description="Full test suite with complete coverage",
        markers="not skip_ci",
        timeout=900,
        coverage=True,
        parallel=True,
        estimated_time="10-15 minutes"
    ),
    "critical": TestLevel(
        name="critical",
        description="Essential tests for core functionality",
        markers="critical",
        timeout=120,
        max_failures=1,
        coverage=False,
        parallel=True,
        estimated_time="1-2 minutes"
    ),
}


# ============================================================================
# TEST RUNNER
# ============================================================================

class UnifiedTestRunner:
    """Unified test runner with consolidated configuration."""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.report_dir = self.project_root / "test_reports"
        self.report_dir.mkdir(exist_ok=True)
        
        # Environment setup
        self.env = os.environ.copy()
        self.env["TESTING"] = "true"
        self.env["PYTHONDONTWRITEBYTECODE"] = "1"
        self.env["PYTEST_CURRENT_TEST"] = ""
        
        # Statistics
        self.stats = {
            "start_time": None,
            "end_time": None,
            "duration": 0,
            "level": None,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "coverage": None
        }
    
    def run_tests(self, level: str, additional_args: List[str] = None) -> int:
        """Run tests for specified level.
        
        Args:
            level: Test level to run
            additional_args: Additional pytest arguments
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        if level not in TEST_LEVELS:
            logger.error(f"Invalid test level: {level}")
            logger.info(f"Available levels: {', '.join(TEST_LEVELS.keys())}")
            return 1
        
        test_config = TEST_LEVELS[level]
        logger.info("=" * 70)
        logger.info(f"🧪 Running {test_config.name.upper()} Tests")
        logger.info(f"📝 {test_config.description}")
        logger.info(f"⏱️  Estimated time: {test_config.estimated_time}")
        logger.info("=" * 70)
        
        self.stats["level"] = level
        self.stats["start_time"] = datetime.now()
        
        # Build pytest command
        cmd = ["python", "-m", "pytest"]
        cmd.extend(test_config.get_pytest_args())
        
        # Add additional arguments if provided
        if additional_args:
            cmd.extend(additional_args)
        
        # Add test paths
        cmd.extend(["app/tests"])
        
        # Log command for debugging
        logger.debug(f"Command: {' '.join(cmd)}")
        
        # Run tests
        try:
            result = subprocess.run(
                cmd,
                env=self.env,
                capture_output=False,
                text=True,
                cwd=str(self.project_root)
            )
            
            self.stats["end_time"] = datetime.now()
            self.stats["duration"] = (
                self.stats["end_time"] - self.stats["start_time"]
            ).total_seconds()
            
            # Parse results if available
            self._parse_results()
            
            # Print summary
            self._print_summary()
            
            return result.returncode
            
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return 1
    
    def _parse_results(self):
        """Parse test results from reports."""
        # Try to parse JUnit XML report
        junit_file = self.report_dir / "junit.xml"
        if junit_file.exists():
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(junit_file)
                root = tree.getroot()
                
                # Parse test suite statistics
                for testsuite in root.findall("testsuite"):
                    self.stats["passed"] += int(
                        testsuite.get("tests", 0)
                    ) - int(
                        testsuite.get("failures", 0)
                    ) - int(
                        testsuite.get("errors", 0)
                    ) - int(
                        testsuite.get("skipped", 0)
                    )
                    self.stats["failed"] += int(testsuite.get("failures", 0))
                    self.stats["errors"] += int(testsuite.get("errors", 0))
                    self.stats["skipped"] += int(testsuite.get("skipped", 0))
                    
            except Exception as e:
                logger.debug(f"Could not parse JUnit XML: {e}")
        
        # Try to parse coverage report
        coverage_file = self.report_dir / "coverage.xml"
        if coverage_file.exists():
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(coverage_file)
                root = tree.getroot()
                
                # Get coverage percentage
                coverage = root.get("line-rate")
                if coverage:
                    self.stats["coverage"] = float(coverage) * 100
                    
            except Exception as e:
                logger.debug(f"Could not parse coverage XML: {e}")
    
    def _print_summary(self):
        """Print test execution summary."""
        logger.info("")
        logger.info("=" * 70)
        logger.info("📊 TEST EXECUTION SUMMARY")
        logger.info("=" * 70)
        
        # Results
        total_tests = (
            self.stats["passed"] + 
            self.stats["failed"] + 
            self.stats["errors"] + 
            self.stats["skipped"]
        )
        
        if total_tests > 0:
            logger.info(f"Total Tests: {total_tests}")
            logger.info(f"✅ Passed: {self.stats['passed']}")
            logger.info(f"❌ Failed: {self.stats['failed']}")
            logger.info(f"🔥 Errors: {self.stats['errors']}")
            logger.info(f"⏭️  Skipped: {self.stats['skipped']}")
            
            pass_rate = (self.stats["passed"] / total_tests) * 100
            logger.info(f"Pass Rate: {pass_rate:.1f}%")
        
        # Coverage
        if self.stats["coverage"] is not None:
            logger.info(f"📈 Coverage: {self.stats['coverage']:.1f}%")
        
        # Duration
        logger.info(f"⏱️  Duration: {self.stats['duration']:.2f} seconds")
        
        # Reports
        logger.info("")
        logger.info("📁 Reports generated in: test_reports/")
        if (self.report_dir / "report.html").exists():
            logger.info("   - HTML Report: test_reports/report.html")
        if (self.report_dir / "coverage_html" / "index.html").exists():
            logger.info("   - Coverage Report: test_reports/coverage_html/index.html")
        
        logger.info("=" * 70)
    
    def list_levels(self):
        """List all available test levels."""
        logger.info("📋 Available Test Levels:")
        logger.info("")
        
        for name, config in TEST_LEVELS.items():
            logger.info(f"  {name:15} - {config.description}")
            logger.info(f"  {'':15}   Time: {config.estimated_time}")
            logger.info(f"  {'':15}   Coverage: {'Yes' if config.coverage else 'No'}")
            logger.info("")
    
    def run_simple(self) -> int:
        """Run simple smoke tests (fallback mode)."""
        logger.info("Running in simple mode (smoke tests only)...")
        return self.run_tests("smoke", ["--tb=short", "-v"])
    
    def run_by_marker(self, marker: str, additional_args: List[str] = None) -> int:
        """Run tests by specific marker.
        
        Args:
            marker: Test marker to filter by
            additional_args: Additional pytest arguments
            
        Returns:
            Exit code
        """
        logger.info(f"Running tests with marker: {marker}")
        
        cmd = [
            "python", "-m", "pytest",
            "-c", "config/test_config_unified.ini",
            "-m", marker,
            "--tb=short",
            "app/tests"
        ]
        
        if additional_args:
            cmd.extend(additional_args)
        
        result = subprocess.run(
            cmd,
            env=self.env,
            capture_output=False,
            text=True,
            cwd=str(self.project_root)
        )
        
        return result.returncode
    
    def run_specific_tests(self, test_paths: List[str]) -> int:
        """Run specific test files or directories.
        
        Args:
            test_paths: List of test paths to run
            
        Returns:
            Exit code
        """
        logger.info(f"Running specific tests: {', '.join(test_paths)}")
        
        cmd = [
            "python", "-m", "pytest",
            "-c", "config/test_config_unified.ini",
            "--tb=short",
            "-v"
        ]
        cmd.extend(test_paths)
        
        result = subprocess.run(
            cmd,
            env=self.env,
            capture_output=False,
            text=True,
            cwd=str(self.project_root)
        )
        
        return result.returncode


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified Test Runner for Netra Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_runner_unified.py --level smoke       # Quick validation
  python test_runner_unified.py --level unit        # Unit tests
  python test_runner_unified.py --level integration # Integration tests
  python test_runner_unified.py --level comprehensive # Full suite
  python test_runner_unified.py --level critical    # Critical paths
  
  python test_runner_unified.py --simple            # Fallback mode
  python test_runner_unified.py --list              # List all levels
  python test_runner_unified.py --marker websocket  # Run by marker
  python test_runner_unified.py app/tests/test_auth.py  # Specific file
        """
    )
    
    parser.add_argument(
        "--level",
        choices=list(TEST_LEVELS.keys()),
        help="Test level to run"
    )
    
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Run in simple mode (smoke tests only)"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available test levels"
    )
    
    parser.add_argument(
        "--marker",
        help="Run tests with specific marker"
    )
    
    parser.add_argument(
        "test_paths",
        nargs="*",
        help="Specific test files or directories to run"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel test execution"
    )
    
    args, unknown_args = parser.parse_known_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create runner
    runner = UnifiedTestRunner()
    
    # Handle different modes
    if args.list:
        runner.list_levels()
        return 0
    
    if args.simple:
        return runner.run_simple()
    
    if args.marker:
        additional_args = unknown_args
        if args.no_parallel:
            additional_args.append("-n0")
        return runner.run_by_marker(args.marker, additional_args)
    
    if args.test_paths:
        return runner.run_specific_tests(args.test_paths)
    
    if args.level:
        additional_args = unknown_args
        if args.no_parallel:
            additional_args.append("-n0")
        return runner.run_tests(args.level, additional_args)
    
    # Default: show help
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
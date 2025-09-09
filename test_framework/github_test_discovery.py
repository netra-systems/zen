"""
GitHub Integration Test Discovery and Runner Integration

Integrates GitHub integration tests with the unified test runner system.
Provides test discovery, categorization, and execution for GitHub tests.

CRITICAL: Follows SSOT patterns and unified test runner architecture.
"""

import os
import pytest
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from test_framework.test_discovery import TestDiscovery
from test_framework.test_categories import TestCategories
from test_framework.config.github_test_config import get_github_test_config, validate_github_test_environment


class GitHubTestDiscovery:
    """
    GitHub integration test discovery and categorization
    
    CRITICAL: Integrates with unified test runner system following SSOT patterns.
    """
    
    def __init__(self):
        self.base_discovery = TestDiscovery()
        self.test_categories = TestCategories()
        self.github_config = get_github_test_config()
    
    def discover_github_tests(self, root_dir: str = None) -> Dict[str, List[str]]:
        """
        Discover all GitHub integration tests and categorize them
        
        Returns:
            Dictionary mapping test categories to lists of test file paths
        """
        if root_dir is None:
            root_dir = os.getcwd()
        
        github_tests = {
            "unit": [],
            "integration": [],
            "e2e": [],
            "mission_critical": []
        }
        
        # Discover unit tests
        unit_test_dir = os.path.join(root_dir, "test_framework", "tests", "unit", "github_integration")
        if os.path.exists(unit_test_dir):
            github_tests["unit"] = self._find_test_files(unit_test_dir)
        
        # Discover integration tests  
        integration_test_dir = os.path.join(root_dir, "test_framework", "tests", "integration", "github_integration")
        if os.path.exists(integration_test_dir):
            github_tests["integration"] = self._find_test_files(integration_test_dir)
        
        # Discover e2e tests
        e2e_test_dir = os.path.join(root_dir, "tests", "e2e", "github_integration")
        if os.path.exists(e2e_test_dir):
            github_tests["e2e"] = self._find_test_files(e2e_test_dir)
        
        # Discover mission critical tests
        critical_test_dir = os.path.join(root_dir, "tests", "mission_critical", "github_integration")
        if os.path.exists(critical_test_dir):
            github_tests["mission_critical"] = self._find_test_files(critical_test_dir)
        
        return github_tests
    
    def _find_test_files(self, directory: str) -> List[str]:
        """Find all test files in directory"""
        test_files = []
        
        if not os.path.exists(directory):
            return test_files
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.startswith("test_") and file.endswith(".py"):
                    test_files.append(os.path.join(root, file))
        
        return test_files
    
    def get_github_test_markers(self) -> List[str]:
        """Get list of pytest markers for GitHub tests"""
        return [
            "github",
            "github_integration",
            "github_api",
            "github_issue",
            "github_webhook",
            "github_auth",
            "github_rate_limit",
            "github_security",
            "github_performance"
        ]
    
    def should_run_github_tests(self) -> Tuple[bool, str]:
        """
        Check if GitHub tests should be run based on configuration
        
        Returns:
            Tuple of (should_run: bool, reason: str)
        """
        # Check environment configuration
        is_valid, errors = validate_github_test_environment()
        
        if not is_valid:
            return False, f"GitHub environment configuration invalid: {'; '.join(errors)}"
        
        # Check if tests are enabled
        should_skip, skip_reason = self.github_config.should_skip_tests()
        
        if should_skip:
            return False, skip_reason
        
        return True, "GitHub tests enabled and configured"
    
    def get_github_test_categories(self) -> Dict[str, Dict[str, str]]:
        """Get GitHub-specific test categories"""
        return {
            "github_unit": {
                "description": "GitHub integration unit tests",
                "priority": "high",
                "timeout": "2m",
                "requires_api": False
            },
            "github_integration": {
                "description": "GitHub API integration tests",
                "priority": "high", 
                "timeout": "10m",
                "requires_api": True
            },
            "github_e2e": {
                "description": "GitHub end-to-end workflow tests",
                "priority": "medium",
                "timeout": "15m",
                "requires_api": True,
                "requires_auth": True
            },
            "github_critical": {
                "description": "GitHub mission critical automation tests",
                "priority": "critical",
                "timeout": "30m",
                "requires_api": True,
                "requires_auth": True
            }
        }


class GitHubTestRunnerIntegration:
    """
    Integration with unified test runner for GitHub tests
    
    CRITICAL: This class provides the interface between GitHub tests
    and the unified test runner system.
    """
    
    def __init__(self):
        self.discovery = GitHubTestDiscovery()
        self.config = get_github_test_config()
    
    def get_pytest_args_for_github_tests(
        self, 
        test_category: str = "all",
        verbose: bool = False,
        fail_fast: bool = False
    ) -> List[str]:
        """
        Generate pytest arguments for running GitHub tests
        
        Args:
            test_category: Category of tests to run ("unit", "integration", "e2e", "mission_critical", "all")
            verbose: Enable verbose output
            fail_fast: Stop on first failure
        
        Returns:
            List of pytest command line arguments
        """
        args = []
        
        # Check if tests should run
        should_run, reason = self.discovery.should_run_github_tests()
        if not should_run:
            # Return args that will skip all GitHub tests
            args.extend(["-m", "not github"])
            if verbose:
                print(f"Skipping GitHub tests: {reason}")
            return args
        
        # Add GitHub test markers
        if test_category == "all":
            args.extend(["-m", "github"])
        elif test_category == "unit":
            args.extend(["-m", "github and unit"])
        elif test_category == "integration": 
            args.extend(["-m", "github and integration"])
        elif test_category == "e2e":
            args.extend(["-m", "github and e2e"])
        elif test_category == "mission_critical":
            args.extend(["-m", "github and mission_critical"])
        
        # Add test directories
        discovered_tests = self.discovery.discover_github_tests()
        
        if test_category == "all":
            for category_tests in discovered_tests.values():
                args.extend(category_tests)
        elif test_category in discovered_tests:
            args.extend(discovered_tests[test_category])
        
        # Add configuration-based arguments
        if self.config.verbose_logging or verbose:
            args.append("-v")
            args.append("--tb=short")
        
        if fail_fast:
            args.append("-x")
        
        # Add timeout settings
        args.extend(["--timeout", str(self.config.timeout_seconds)])
        
        # Add GitHub-specific configuration
        if self.config.debug_mode:
            args.extend(["-s", "--capture=no"])
        
        # Add environment markers
        args.extend(["-m", f"not requires_real_api or github_{self.config.environment}"])
        
        return args
    
    def generate_github_test_report(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate GitHub-specific test report
        
        Args:
            test_results: Raw test results from pytest
        
        Returns:
            GitHub test report dictionary
        """
        github_report = {
            "github_integration_status": "unknown",
            "configuration": self.config.to_dict(),
            "test_categories": {},
            "api_usage": {
                "total_calls": 0,
                "rate_limit_hits": 0,
                "authentication_errors": 0
            },
            "issues_created": 0,
            "issues_cleaned_up": 0,
            "recommendations": []
        }
        
        # Analyze test results for GitHub-specific metrics
        if "github" in test_results.get("markers", {}):
            github_results = test_results["markers"]["github"]
            
            # Categorize results
            for category in ["unit", "integration", "e2e", "mission_critical"]:
                category_results = [r for r in github_results if category in r.get("markers", [])]
                
                github_report["test_categories"][category] = {
                    "total": len(category_results),
                    "passed": len([r for r in category_results if r.get("outcome") == "passed"]),
                    "failed": len([r for r in category_results if r.get("outcome") == "failed"]),
                    "skipped": len([r for r in category_results if r.get("outcome") == "skipped"])
                }
            
            # Determine overall status
            total_tests = len(github_results)
            passed_tests = len([r for r in github_results if r.get("outcome") == "passed"])
            failed_tests = len([r for r in github_results if r.get("outcome") == "failed"])
            
            if total_tests == 0:
                github_report["github_integration_status"] = "no_tests"
            elif failed_tests == 0:
                github_report["github_integration_status"] = "all_passing"
            elif passed_tests > failed_tests:
                github_report["github_integration_status"] = "mostly_passing"
            else:
                github_report["github_integration_status"] = "failing"
        
        # Generate recommendations
        if github_report["github_integration_status"] == "failing":
            github_report["recommendations"].append(
                "Review GitHub API configuration and authentication"
            )
        
        if github_report["api_usage"]["rate_limit_hits"] > 0:
            github_report["recommendations"].append(
                "Consider reducing API calls or increasing rate limit buffer"
            )
        
        return github_report


def register_github_tests_with_unified_runner():
    """
    Register GitHub tests with the unified test runner system
    
    CRITICAL: This function should be called during test runner initialization
    to ensure GitHub tests are properly integrated.
    """
    try:
        # Import unified test runner (this will fail if not implemented)
        from tests.unified_test_runner import UnifiedTestRunner
        
        # Create GitHub test integration
        github_integration = GitHubTestRunnerIntegration()
        
        # Register GitHub test discovery
        runner = UnifiedTestRunner()
        runner.register_test_discovery("github", github_integration.discovery)
        
        # Register GitHub test categories
        github_categories = github_integration.discovery.get_github_test_categories()
        for category, config in github_categories.items():
            runner.register_test_category(category, config)
        
        # Register GitHub markers
        github_markers = github_integration.discovery.get_github_test_markers()
        for marker in github_markers:
            runner.register_test_marker(marker, "GitHub integration test marker")
        
        return True
        
    except ImportError:
        # Unified test runner not available yet
        return False


# CLI interface for running GitHub tests directly
def run_github_tests(
    category: str = "all",
    verbose: bool = False,
    fail_fast: bool = False,
    dry_run: bool = False
) -> int:
    """
    Run GitHub integration tests directly
    
    Args:
        category: Test category to run
        verbose: Enable verbose output  
        fail_fast: Stop on first failure
        dry_run: Show what would be run without executing
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    integration = GitHubTestRunnerIntegration()
    
    # Generate pytest arguments
    pytest_args = integration.get_pytest_args_for_github_tests(
        test_category=category,
        verbose=verbose,
        fail_fast=fail_fast
    )
    
    if dry_run:
        print("Would run GitHub tests with arguments:")
        print(" ".join(pytest_args))
        return 0
    
    # Check prerequisites
    should_run, reason = integration.discovery.should_run_github_tests()
    if not should_run:
        print(f"Skipping GitHub tests: {reason}")
        return 0
    
    # Run tests
    return pytest.main(pytest_args)


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Run GitHub integration tests")
    parser.add_argument("--category", choices=["all", "unit", "integration", "e2e", "mission_critical"], 
                       default="all", help="Test category to run")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-x", "--fail-fast", action="store_true", help="Stop on first failure")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be run")
    
    args = parser.parse_args()
    
    exit_code = run_github_tests(
        category=args.category,
        verbose=args.verbose,
        fail_fast=args.fail_fast,
        dry_run=args.dry_run
    )
    
    sys.exit(exit_code)
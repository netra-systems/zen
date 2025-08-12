#!/usr/bin/env python
"""
Runner for Real Service Tests

This script specifically runs tests that require real external services like:
- Real LLM providers (OpenAI, Anthropic, Google)
- Real databases (PostgreSQL, ClickHouse, Redis)
- Real external APIs

These tests are separated from the basic plumbing tests for better organization.
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.tests.test_categories import (
    TEST_CATEGORIES,
    get_runnable_categories,
    categorize_test_files,
    validate_environment_for_category,
    should_run_category
)


class RealServiceTestRunner:
    """Runner for tests that require real external services."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.test_dir = Path(__file__).parent
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    def check_environment(self) -> Dict[str, bool]:
        """Check which real service categories can be run."""
        print("\n" + "="*60)
        print("CHECKING ENVIRONMENT FOR REAL SERVICE TESTS")
        print("="*60)
        
        runnable = get_runnable_categories()
        real_service_categories = [
            "real_llm", "real_database", "real_clickhouse", "real_redis"
        ]
        
        results = {}
        for category in real_service_categories:
            can_run = runnable.get(category, False)
            is_valid, missing = validate_environment_for_category(category)
            
            results[category] = can_run
            
            status = "[OK]" if can_run else "[MISSING]"
            print(f"\n{status} {category.upper()}")
            
            if not can_run and missing:
                print(f"  Missing: {', '.join(missing)}")
            elif can_run:
                print(f"  Ready to run")
        
        return results
    
    def run_category_tests(self, category: str, test_files: List[Path]) -> Dict:
        """Run tests for a specific category."""
        print(f"\n{'='*60}")
        print(f"RUNNING {category.upper()} TESTS")
        print(f"{'='*60}")
        print(f"Found {len(test_files)} test files")
        
        start_time = time.time()
        passed = 0
        failed = 0
        skipped = 0
        errors = []
        
        for test_file in test_files:
            relative_path = test_file.relative_to(self.test_dir.parent.parent)
            print(f"\n> Running: {relative_path}")
            
            # Run pytest for this specific file
            cmd = [
                sys.executable, "-m", "pytest",
                str(test_file),
                "-v" if self.verbose else "-q",
                "--tb=short",
                "--no-header",
                "-W", "ignore::DeprecationWarning"
            ]
            
            # Add specific markers for real service tests
            if category == "real_llm":
                cmd.extend(["-m", "not skip"])
                # Set environment for real LLM testing
                env = os.environ.copy()
                env["ENABLE_REAL_LLM_TESTING"] = "true"
            else:
                env = os.environ.copy()
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout per file
                    env=env
                )
                
                # Parse pytest output
                output = result.stdout + result.stderr
                
                # Look for test results in output
                if "passed" in output:
                    # Extract test counts from pytest output
                    import re
                    match = re.search(r'(\d+) passed', output)
                    if match:
                        passed += int(match.group(1))
                
                if "failed" in output:
                    match = re.search(r'(\d+) failed', output)
                    if match:
                        failed += int(match.group(1))
                        errors.append(f"{relative_path}: {match.group(0)}")
                
                if "skipped" in output:
                    match = re.search(r'(\d+) skipped', output)
                    if match:
                        skipped += int(match.group(1))
                
                if result.returncode != 0 and "failed" not in output:
                    errors.append(f"{relative_path}: Test execution error")
                    failed += 1
                
                if self.verbose and result.returncode != 0:
                    print(f"  Output: {output[:500]}")
                    
            except subprocess.TimeoutExpired:
                print(f"  [TIMEOUT] Test took longer than 5 minutes")
                errors.append(f"{relative_path}: Timeout")
                failed += 1
            except Exception as e:
                print(f"  [ERROR] {str(e)}")
                errors.append(f"{relative_path}: {str(e)}")
                failed += 1
        
        duration = time.time() - start_time
        
        return {
            "category": category,
            "duration": duration,
            "total": passed + failed + skipped,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "errors": errors,
            "status": "passed" if failed == 0 else "failed"
        }
    
    def run_real_service_tests(self, categories: Optional[List[str]] = None):
        """Run all real service tests that have proper environment setup."""
        self.start_time = datetime.now()
        
        # Check environment
        runnable = self.check_environment()
        
        # Categorize all test files
        categorized = categorize_test_files(self.test_dir)
        
        # Determine which categories to run
        if categories:
            categories_to_run = [c for c in categories if runnable.get(c, False)]
        else:
            # Run all available real service categories
            real_service_categories = [
                "real_llm", "real_database", "real_clickhouse", "real_redis"
            ]
            categories_to_run = [c for c in real_service_categories if runnable.get(c, False)]
        
        if not categories_to_run:
            print("\n[WARNING] No real service tests can be run!")
            print("Set appropriate environment variables to enable:")
            print("  - ENABLE_REAL_LLM_TESTING=true + API keys for LLM tests")
            print("  - ENABLE_REAL_DB_TESTING=true + DATABASE_URL for database tests")
            print("  - ENABLE_REAL_CLICKHOUSE_TESTING=true + CLICKHOUSE_URL for ClickHouse tests")
            print("  - ENABLE_REAL_REDIS_TESTING=true + REDIS_URL for Redis tests")
            return
        
        print(f"\n[RUNNING] Tests for categories: {', '.join(categories_to_run)}")
        
        # Run tests for each category
        for category in categories_to_run:
            test_files = categorized.get(category, [])
            if test_files:
                result = self.run_category_tests(category, test_files)
                self.results[category] = result
        
        self.end_time = datetime.now()
        self.print_summary()
    
    def run_plumbing_tests(self):
        """Run only the basic plumbing tests (no external services required)."""
        self.start_time = datetime.now()
        
        print("\n" + "="*60)
        print("RUNNING PLUMBING TESTS (No External Services)")
        print("="*60)
        
        # Categorize test files
        categorized = categorize_test_files(self.test_dir)
        
        # Run plumbing and integration tests (these use mocks)
        categories_to_run = ["plumbing", "websocket", "integration"]
        
        for category in categories_to_run:
            test_files = categorized.get(category, [])
            if test_files:
                result = self.run_category_tests(category, test_files)
                self.results[category] = result
        
        self.end_time = datetime.now()
        self.print_summary()
    
    def print_summary(self):
        """Print test execution summary."""
        if not self.results:
            return
        
        print("\n" + "="*60)
        print("TEST EXECUTION SUMMARY")
        print("="*60)
        
        total_passed = sum(r["passed"] for r in self.results.values())
        total_failed = sum(r["failed"] for r in self.results.values())
        total_skipped = sum(r["skipped"] for r in self.results.values())
        total_duration = sum(r["duration"] for r in self.results.values())
        
        for category, result in self.results.items():
            status_icon = "[PASS]" if result["status"] == "passed" else "[FAIL]"
            print(f"\n{status_icon} {category.upper()}")
            print(f"  Passed: {result['passed']}")
            print(f"  Failed: {result['failed']}")
            print(f"  Skipped: {result['skipped']}")
            print(f"  Duration: {result['duration']:.2f}s")
            
            if result["errors"]:
                print(f"  Errors:")
                for error in result["errors"][:5]:  # Show first 5 errors
                    print(f"    - {error}")
        
        print(f"\n{'='*60}")
        print(f"TOTAL: {total_passed} passed, {total_failed} failed, {total_skipped} skipped")
        print(f"Duration: {total_duration:.2f}s")
        print(f"Status: {'SUCCESS' if total_failed == 0 else 'FAILED'}")
        
        if self.start_time and self.end_time:
            print(f"Execution Time: {self.end_time - self.start_time}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run real service tests")
    parser.add_argument(
        "--category",
        choices=["real_llm", "real_database", "real_clickhouse", "real_redis", "plumbing", "all"],
        help="Specific category to run"
    )
    parser.add_argument(
        "--plumbing-only",
        action="store_true",
        help="Run only plumbing tests (no external services)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check environment, don't run tests"
    )
    
    args = parser.parse_args()
    
    runner = RealServiceTestRunner(verbose=args.verbose)
    
    if args.check_only:
        runner.check_environment()
    elif args.plumbing_only:
        runner.run_plumbing_tests()
    elif args.category:
        if args.category == "all":
            runner.run_real_service_tests()
        elif args.category == "plumbing":
            runner.run_plumbing_tests()
        else:
            runner.run_real_service_tests([args.category])
    else:
        # Default: run plumbing tests
        print("Running plumbing tests by default. Use --category to run real service tests.")
        runner.run_plumbing_tests()


if __name__ == "__main__":
    main()
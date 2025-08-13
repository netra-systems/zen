#!/usr/bin/env python
"""
Modular Test Runner - Advanced test execution with intelligent features
Integrates orchestration, pattern analysis, and smart test selection
"""

import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set, Any
from dataclasses import dataclass
import subprocess
import time
import io

# Add project root and test_framework to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "test_framework"))

# Set stdout to handle UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def safe_print(*args, **kwargs):
    """Safe print function that handles Unicode characters"""
    try:
        print(*args, **kwargs)
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Fallback: replace emojis with text
        text = ' '.join(str(arg) for arg in args)
        text = text.replace('📂', '[DIR]')
        text = text.replace('🎯', '[TARGET]')
        text = text.replace('🔍', '[SEARCH]')
        text = text.replace('💡', '[IDEA]')
        text = text.replace('📄', '[FILE]')
        text = text.replace('🔥', '[ERROR]')
        text = text.replace('🔄', '[RETRY]')
        text = text.replace('✅', '[PASS]')
        text = text.replace('❌', '[FAIL]')
        text = text.replace('⏭️', '[SKIP]')
        print(text, **kwargs)

# Import our components
from test_suite_orchestrator import TestSuiteOrchestrator, TestPriority, TestStatus
from failure_pattern_analyzer import FailurePatternAnalyzer, TestFailure

@dataclass
class TestRunConfig:
    """Configuration for a test run"""
    level: str = "smoke"
    parallel: bool = True
    fail_fast: bool = False
    retry_failed: bool = True
    max_workers: int = 4
    timeout: int = 300
    coverage: bool = False
    verbose: bool = False
    categories: List[str] = None
    exclude_categories: List[str] = None
    pattern: Optional[str] = None
    
    def __post_init__(self):
        if self.categories is None:
            self.categories = []
        if self.exclude_categories is None:
            self.exclude_categories = []

class ModularTestRunner:
    """
    Advanced modular test runner with intelligent features:
    - Smart test selection based on recent changes
    - Failure pattern analysis
    - Parallel execution with dependency management
    - Automatic retry for flaky tests
    - Comprehensive reporting
    """
    
    def __init__(self):
        self.orchestrator = TestSuiteOrchestrator()
        self.analyzer = FailurePatternAnalyzer()
        self.reports_dir = PROJECT_ROOT / "test_reports" / "modular"
        self.reports_dir.mkdir(exist_ok=True, parents=True)
        
        # Test levels with configurations
        self.test_levels = {
            "smoke": {
                "description": "Quick smoke tests (< 30s)",
                "categories": ["smoke", "critical"],
                "timeout": 30,
                "parallel": True,
                "fail_fast": True,
                "coverage": False
            },
            "unit": {
                "description": "Unit tests (1-2 min)",
                "categories": ["unit"],
                "timeout": 120,
                "parallel": True,
                "fail_fast": False,
                "coverage": True
            },
            "integration": {
                "description": "Integration tests (3-5 min)",
                "categories": ["integration", "api"],
                "timeout": 300,
                "parallel": True,
                "fail_fast": False,
                "coverage": True
            },
            "comprehensive": {
                "description": "All tests (10-15 min)",
                "categories": [],  # All categories
                "timeout": 900,
                "parallel": True,
                "fail_fast": False,
                "coverage": True
            },
            "critical": {
                "description": "Critical path tests (1-2 min)",
                "categories": ["critical", "auth", "database"],
                "timeout": 120,
                "parallel": False,
                "fail_fast": True,
                "coverage": False
            }
        }
    
    async def run_tests(self, config: TestRunConfig) -> Dict[str, Any]:
        """Run tests based on configuration"""
        safe_print("=" * 80)
        safe_print(f"MODULAR TEST RUNNER - {config.level.upper()}")
        safe_print("=" * 80)
        
        start_time = datetime.now()
        results = {
            "level": config.level,
            "start_time": start_time.isoformat(),
            "config": config.__dict__,
            "suites": {},
            "summary": {},
            "analysis": {},
            "recommendations": []
        }
        
        # Discover tests
        safe_print("\n📂 Discovering tests...")
        discovered = self.orchestrator.discover_tests()
        
        # Apply filters
        tests_to_run = self._filter_tests(discovered, config)
        
        # Group tests by priority
        prioritized = self._prioritize_tests(tests_to_run)
        
        safe_print(f"Found {sum(len(tests) for tests in tests_to_run.values())} tests in {len(tests_to_run)} categories")
        
        # Run tests by priority
        all_failures = []
        for priority_level, test_groups in prioritized.items():
            if not test_groups:
                continue
                
            safe_print(f"\n🎯 Running {priority_level} priority tests...")
            
            for category, tests in test_groups.items():
                if not tests:
                    continue
                    
                safe_print(f"  Running {category} tests ({len(tests)} tests)...")
                
                # Run test suite
                suite_results = await self._run_test_suite(
                    category, tests, config
                )
                
                results["suites"][category] = suite_results
                
                # Collect failures for analysis
                failures = self._extract_failures(suite_results)
                all_failures.extend(failures)
                
                # Fail fast if configured
                if config.fail_fast and failures:
                    safe_print(f"  ❌ Failing fast due to failures in {category}")
                    break
            
            if config.fail_fast and all_failures:
                break
        
        # Analyze failures
        if all_failures:
            safe_print(f"\n🔍 Analyzing {len(all_failures)} failures...")
            results["analysis"] = self.analyzer.analyze_batch(all_failures)
            
            # Add recommendations
            if results["analysis"]["recommendations"]:
                results["recommendations"] = results["analysis"]["recommendations"]
                safe_print("\n💡 Recommendations:")
                for rec in results["recommendations"][:3]:
                    safe_print(f"  [{rec['priority']}] {rec['issue']}")
                    safe_print(f"    → {rec['action']}")
        
        # Generate summary
        results["end_time"] = datetime.now().isoformat()
        results["summary"] = self._generate_summary(results)
        
        # Save report
        self._save_report(results)
        
        # Print summary
        self._print_summary(results)
        
        return results
    
    def _filter_tests(self, discovered: Dict[str, List[str]], config: TestRunConfig) -> Dict[str, List[str]]:
        """Filter tests based on configuration"""
        filtered = {}
        
        # Get categories to run
        if config.categories:
            categories = config.categories
        elif config.level in self.test_levels:
            level_config = self.test_levels[config.level]
            categories = level_config.get("categories", [])
        else:
            categories = []
        
        # If no specific categories, use all
        if not categories:
            categories = list(discovered.keys())
        
        # Apply filters
        for category in categories:
            if category in config.exclude_categories:
                continue
            
            if category in discovered:
                tests = discovered[category]
                
                # Apply pattern filter if specified
                if config.pattern:
                    import re
                    pattern = re.compile(config.pattern)
                    tests = [t for t in tests if pattern.search(t)]
                
                if tests:
                    filtered[category] = tests
        
        return filtered
    
    def _prioritize_tests(self, tests: Dict[str, List[str]]) -> Dict[str, Dict[str, List[str]]]:
        """Group tests by priority"""
        prioritized = {
            "critical": {},
            "high": {},
            "medium": {},
            "low": {}
        }
        
        # Define priority mappings
        priority_map = {
            "smoke": "critical",
            "critical": "critical",
            "auth": "critical",
            "database": "high",
            "api": "high",
            "unit": "medium",
            "integration": "medium",
            "websocket": "medium",
            "e2e": "low",
            "performance": "low"
        }
        
        for category, test_list in tests.items():
            priority = priority_map.get(category, "medium")
            prioritized[priority][category] = test_list
        
        return prioritized
    
    async def _run_test_suite(
        self,
        category: str,
        tests: List[str],
        config: TestRunConfig
    ) -> Dict[str, Any]:
        """Run a test suite"""
        suite_start = time.time()
        
        # Prepare test profiles
        test_profiles = []
        for test_path in tests:
            test_name = Path(test_path).stem
            profile = self.orchestrator.test_profiles.get(test_name)
            
            if not profile:
                # Create new profile
                from test_suite_orchestrator import TestProfile
                profile = TestProfile(
                    path=test_path,
                    name=test_name,
                    category=category,
                    priority=TestPriority.MEDIUM
                )
                self.orchestrator.test_profiles[test_name] = profile
            
            test_profiles.append(profile)
        
        # Create suite
        from test_suite_orchestrator import TestSuite
        suite = TestSuite(
            name=category,
            tests=test_profiles,
            parallel_safe=config.parallel,
            max_parallel=config.max_workers,
            timeout=config.timeout,
            retry_failed=config.retry_failed
        )
        
        # Add to orchestrator
        self.orchestrator.suites[category] = suite
        
        # Execute suite
        results = await self.orchestrator.execute_suite(
            category,
            parallel=config.parallel,
            fail_fast=config.fail_fast,
            retry_failed=config.retry_failed
        )
        
        results["duration"] = time.time() - suite_start
        
        return results
    
    def _extract_failures(self, suite_results: Dict) -> List[TestFailure]:
        """Extract failures from suite results"""
        failures = []
        
        for test_result in suite_results.get("tests", []):
            if test_result.get("status") in ["failed", "error", "timeout"]:
                failure = TestFailure(
                    test_name=test_result.get("name", "unknown"),
                    test_path=test_result.get("path", ""),
                    error_type=test_result.get("status", "error"),
                    error_message=test_result.get("error", ""),
                    stack_trace=test_result.get("output", ""),
                    timestamp=datetime.now(),
                    duration=test_result.get("duration", 0),
                    exit_code=test_result.get("exit_code", 1)
                )
                failures.append(failure)
        
        return failures
    
    def _generate_summary(self, results: Dict) -> Dict[str, Any]:
        """Generate test run summary"""
        summary = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "timeouts": 0,
            "retried": 0,
            "total_duration": 0,
            "suites_run": len(results["suites"]),
            "pass_rate": 0
        }
        
        for suite_results in results["suites"].values():
            suite_summary = suite_results.get("summary", {})
            summary["total_tests"] += suite_summary.get("total", 0)
            summary["passed"] += suite_summary.get("passed", 0)
            summary["failed"] += suite_summary.get("failed", 0)
            summary["skipped"] += suite_summary.get("skipped", 0)
            summary["errors"] += suite_summary.get("errors", 0)
            summary["timeouts"] += suite_summary.get("timeouts", 0)
            summary["retried"] += suite_summary.get("retried", 0)
            summary["total_duration"] += suite_results.get("duration", 0)
        
        if summary["total_tests"] > 0:
            summary["pass_rate"] = (summary["passed"] / summary["total_tests"]) * 100
        
        return summary
    
    def _save_report(self, results: Dict):
        """Save test report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.reports_dir / f"test_report_{results['level']}_{timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        
        safe_print(f"\n📄 Report saved to: {report_file.relative_to(PROJECT_ROOT)}")
        
        # Also save a markdown report
        md_report = self._generate_markdown_report(results)
        md_file = self.reports_dir / f"test_report_{results['level']}_{timestamp}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_report)
    
    def _generate_markdown_report(self, results: Dict) -> str:
        """Generate markdown report"""
        summary = results["summary"]
        
        report = []
        report.append(f"# Test Report - {results['level'].upper()}")
        report.append(f"\n**Generated:** {results.get('end_time', 'N/A')}")
        report.append(f"**Duration:** {summary['total_duration']:.2f}s")
        report.append(f"**Pass Rate:** {summary['pass_rate']:.1f}%")
        
        report.append("\n## Summary")
        report.append(f"- **Total Tests:** {summary['total_tests']}")
        report.append(f"- **Passed:** {summary['passed']} ✅")
        report.append(f"- **Failed:** {summary['failed']} ❌")
        report.append(f"- **Skipped:** {summary['skipped']} ⏭️")
        report.append(f"- **Errors:** {summary['errors']} 🔥")
        
        if results.get("recommendations"):
            report.append("\n## Recommendations")
            for rec in results["recommendations"]:
                report.append(f"\n### [{rec['priority']}] {rec['issue']}")
                report.append(f"{rec['action']}")
                if "affected_tests" in rec:
                    report.append(f"\n**Affected Tests:**")
                    for test in rec.get("affected_tests", [])[:5]:
                        report.append(f"- {test}")
        
        if results.get("analysis"):
            analysis = results["analysis"]
            if analysis.get("flaky_tests"):
                report.append("\n## Flaky Tests")
                for flaky in analysis["flaky_tests"][:10]:
                    report.append(f"- {flaky['test']} (failure rate: {flaky['failure_rate']:.1%})")
            
            if analysis.get("consistent_failures"):
                report.append("\n## Consistent Failures")
                for failure in analysis["consistent_failures"][:10]:
                    report.append(f"- {failure['test']} ({failure['consecutive_failures']} consecutive)")
        
        report.append("\n## Suite Results")
        for suite_name, suite_results in results["suites"].items():
            suite_summary = suite_results.get("summary", {})
            report.append(f"\n### {suite_name}")
            report.append(f"- Tests: {suite_summary.get('total', 0)}")
            report.append(f"- Passed: {suite_summary.get('passed', 0)}")
            report.append(f"- Failed: {suite_summary.get('failed', 0)}")
            report.append(f"- Duration: {suite_results.get('duration', 0):.2f}s")
        
        return "\n".join(report)
    
    def _print_summary(self, results: Dict):
        """Print test summary to console"""
        summary = results["summary"]
        
        safe_print("\n" + "=" * 80)
        safe_print("TEST SUMMARY")
        safe_print("=" * 80)
        
        # Use emojis for visual feedback
        if summary["pass_rate"] == 100:
            status = "✅ ALL TESTS PASSED!"
        elif summary["pass_rate"] >= 90:
            status = "⚠️  MOSTLY PASSING"
        elif summary["pass_rate"] >= 70:
            status = "⚠️  NEEDS ATTENTION"
        else:
            status = "❌ CRITICAL FAILURES"
        
        safe_print(f"\n{status}")
        safe_print(f"Pass Rate: {summary['pass_rate']:.1f}%")
        safe_print(f"\nTests Run: {summary['total_tests']}")
        safe_print(f"  Passed:  {summary['passed']} ✅")
        safe_print(f"  Failed:  {summary['failed']} ❌")
        safe_print(f"  Skipped: {summary['skipped']} ⏭️")
        safe_print(f"  Errors:  {summary['errors']} 🔥")
        
        if summary.get("retried", 0) > 0:
            safe_print(f"  Retried: {summary['retried']} 🔄")
        
        safe_print(f"\nDuration: {summary['total_duration']:.2f}s")
        safe_print(f"Suites Run: {summary['suites_run']}")
        
        if results.get("recommendations"):
            safe_print(f"\n💡 Top Recommendations:")
            for rec in results["recommendations"][:3]:
                safe_print(f"  • {rec['action']}")
        
        safe_print("=" * 80)


async def main():
    """Main entry point for the modular test runner"""
    parser = argparse.ArgumentParser(
        description="Modular Test Runner - Advanced test execution",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--level", "-l",
        choices=["smoke", "unit", "integration", "comprehensive", "critical"],
        default="smoke",
        help="Test level to run"
    )
    
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        default=True,
        help="Run tests in parallel"
    )
    
    parser.add_argument(
        "--no-parallel",
        action="store_false",
        dest="parallel",
        help="Run tests sequentially"
    )
    
    parser.add_argument(
        "--fail-fast", "-f",
        action="store_true",
        help="Stop on first failure"
    )
    
    parser.add_argument(
        "--no-retry",
        action="store_false",
        dest="retry_failed",
        help="Don't retry failed tests"
    )
    
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=4,
        help="Number of parallel workers"
    )
    
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        help="Override default timeout"
    )
    
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Enable coverage reporting"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--category",
        action="append",
        dest="categories",
        help="Specific categories to test"
    )
    
    parser.add_argument(
        "--exclude",
        action="append",
        dest="exclude_categories",
        help="Categories to exclude"
    )
    
    parser.add_argument(
        "--pattern",
        help="Regex pattern to filter tests"
    )
    
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only analyze previous failures"
    )
    
    args = parser.parse_args()
    
    # Create runner
    runner = ModularTestRunner()
    
    if args.analyze_only:
        # Just show analysis
        safe_print("Analyzing previous test failures...")
        report = runner.analyzer.get_pattern_report()
        safe_print(report)
        
        insights = runner.orchestrator.get_test_insights()
        safe_print("\n" + "=" * 80)
        safe_print("TEST SUITE INSIGHTS")
        safe_print("=" * 80)
        safe_print(f"Total Tests: {insights['total_tests']}")
        safe_print(f"Overall Failure Rate: {insights['health_metrics']['overall_failure_rate']:.1%}")
        safe_print(f"Flaky Test Percentage: {insights['health_metrics']['flaky_test_percentage']:.1%}")
        
        if insights['recommended_fixes']:
            safe_print("\nRecommended Fixes:")
            for fix in insights['recommended_fixes']:
                safe_print(f"  • {fix}")
    else:
        # Create config
        config = TestRunConfig(
            level=args.level,
            parallel=args.parallel,
            fail_fast=args.fail_fast,
            retry_failed=args.retry_failed,
            max_workers=args.workers,
            timeout=args.timeout or runner.test_levels.get(args.level, {}).get("timeout", 300),
            coverage=args.coverage,
            verbose=args.verbose,
            categories=args.categories or [],
            exclude_categories=args.exclude_categories or [],
            pattern=args.pattern
        )
        
        # Run tests
        results = await runner.run_tests(config)
        
        # Exit with appropriate code
        if results["summary"]["failed"] > 0 or results["summary"]["errors"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
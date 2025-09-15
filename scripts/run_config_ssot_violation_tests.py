#!/usr/bin/env python3
"""
Comprehensive Test Runner for Issue #667: Configuration Manager SSOT Violations

This script executes the comprehensive test plan for validating configuration manager
SSOT violations and providing detailed analysis of test results.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability - Protect $500K+ ARR by identifying config conflicts
- Value Impact: Validates tests correctly detect SSOT violations blocking Golden Path
- Strategic Impact: Proves test quality before proceeding to remediation

Usage:
    python scripts/run_config_ssot_violation_tests.py [options]

Options:
    --category=[all|mission-critical|integration|e2e]  Test category to run
    --verbose                                          Verbose output
    --report-file=FILE                                 Generate report file
    --no-fail-fast                                    Continue running tests even if some fail
"""

import sys
import os
import subprocess
import time
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from shared.logging.unified_logging_ssot import get_logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    get_logger = lambda name: logging.getLogger(name)

logger = get_logger(__name__)


@dataclass
class TestResult:
    """Test execution result."""
    test_file: str
    category: str
    status: str  # PASS, FAIL, ERROR, SKIP
    duration: float
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    output: str
    violations_detected: List[str]
    test_quality_score: float  # 0-100


@dataclass
class TestSummary:
    """Overall test execution summary."""
    total_duration: float
    total_test_files: int
    total_tests: int
    categories_tested: List[str]
    results: List[TestResult]
    violations_summary: Dict[str, int]
    test_quality_analysis: Dict[str, Any]
    recommendations: List[str]


class ConfigSSotTestRunner:
    """Comprehensive test runner for config SSOT violations."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.start_time = time.time()
        self.results: List[TestResult] = []

        # Test configuration based on previous analysis
        self.test_categories = {
            'mission-critical': [
                'tests/mission_critical/test_config_manager_ssot_violations.py',
                'tests/mission_critical/test_single_config_manager_ssot.py',
                'tests/mission_critical/test_configuration_validator_ssot_violations.py',
            ],
            'integration': [
                'tests/integration/config_ssot/test_config_ssot_direct_environ_access_violations.py',
                'tests/integration/config_ssot/test_config_ssot_unified_config_manager_patterns.py',
                'tests/integration/config_ssot/test_config_system_consistency_integration.py',
                'tests/integration/config_ssot/test_config_ssot_environment_isolation_patterns.py',
                'tests/integration/config_ssot/test_config_ssot_scattered_config_antipatterns.py',
            ],
            'e2e': [
                'tests/e2e/golden_path/test_config_ssot_golden_path_staging.py',
                # Note: Staging-specific tests skip if staging not available
            ]
        }

    def run_tests(self, categories: List[str] = None, fail_fast: bool = True, verbose: bool = False) -> TestSummary:
        """Execute the comprehensive test plan."""
        logger.info("🚀 Starting Configuration Manager SSOT Violations Test Execution")
        logger.info("=" * 80)

        if categories is None:
            categories = ['mission-critical', 'integration']  # Skip E2E by default (requires staging)

        total_tests_run = 0

        for category in categories:
            if category not in self.test_categories:
                logger.warning(f"Unknown test category: {category}")
                continue

            logger.info(f"\n📋 Running {category.upper()} tests...")
            logger.info("-" * 60)

            for test_file in self.test_categories[category]:
                if not (self.project_root / test_file).exists():
                    logger.warning(f"Test file not found: {test_file}")
                    continue

                result = self._run_single_test(test_file, category, verbose)
                self.results.append(result)
                total_tests_run += result.total_tests

                # Log immediate results
                status_icon = "✅" if result.status == "PASS" else "❌" if result.status == "FAIL" else "⚠️"
                logger.info(f"{status_icon} {test_file}: {result.passed}/{result.total_tests} passed "
                           f"({result.duration:.2f}s)")

                if result.violations_detected:
                    logger.info(f"   🔍 Violations detected: {len(result.violations_detected)}")

                if fail_fast and result.status in ["FAIL", "ERROR"] and result.failed > 0:
                    # Allow expected failures for SSOT violation tests
                    if not self._is_expected_failure(test_file, result):
                        logger.error(f"Test failed unexpectedly: {test_file}")
                        break

        # Generate comprehensive summary
        summary = self._generate_summary()
        self._log_summary(summary)

        return summary

    def _run_single_test(self, test_file: str, category: str, verbose: bool = False) -> TestResult:
        """Run a single test file and analyze results."""
        logger.info(f"▶️  Running: {test_file}")

        start_time = time.time()

        # Construct pytest command
        cmd = [
            sys.executable, "-m", "pytest",
            test_file,
            "-v",
            "--tb=short",
            "--no-cov"  # Disable coverage for speed
        ]

        if not verbose:
            cmd.append("-q")

        try:
            # Run the test
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per test file
            )

            duration = time.time() - start_time

            # Parse pytest output
            test_counts = self._parse_pytest_output(result.stdout, result.stderr)
            violations = self._extract_violations(result.stdout, result.stderr)
            quality_score = self._calculate_test_quality(test_file, result, violations)

            status = "PASS" if result.returncode == 0 else "FAIL"
            if "ERRORS" in result.stdout or "ERROR" in result.stderr:
                status = "ERROR"

            return TestResult(
                test_file=test_file,
                category=category,
                status=status,
                duration=duration,
                total_tests=test_counts['total'],
                passed=test_counts['passed'],
                failed=test_counts['failed'],
                skipped=test_counts['skipped'],
                errors=test_counts['errors'],
                output=result.stdout + "\n" + result.stderr,
                violations_detected=violations,
                test_quality_score=quality_score
            )

        except subprocess.TimeoutExpired:
            logger.error(f"Test timeout: {test_file}")
            return TestResult(
                test_file=test_file,
                category=category,
                status="TIMEOUT",
                duration=300.0,
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                output="Test execution timed out after 5 minutes",
                violations_detected=[],
                test_quality_score=0.0
            )

        except Exception as e:
            logger.error(f"Error running test {test_file}: {e}")
            return TestResult(
                test_file=test_file,
                category=category,
                status="ERROR",
                duration=time.time() - start_time,
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                output=f"Execution error: {str(e)}",
                violations_detected=[],
                test_quality_score=0.0
            )

    def _parse_pytest_output(self, stdout: str, stderr: str) -> Dict[str, int]:
        """Parse pytest output to extract test counts."""
        counts = {'total': 0, 'passed': 0, 'failed': 0, 'skipped': 0, 'errors': 0}

        # Look for pytest summary line
        output = stdout + stderr
        lines = output.split('\n')

        for line in lines:
            if 'failed' in line and 'passed' in line:
                # Parse line like "2 failed, 3 passed in 1.23s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'failed' and i > 0:
                        counts['failed'] = int(parts[i-1])
                    elif part == 'passed' and i > 0:
                        counts['passed'] = int(parts[i-1])
                    elif part == 'skipped' and i > 0:
                        counts['skipped'] = int(parts[i-1])
                    elif part == 'error' and i > 0:
                        counts['errors'] = int(parts[i-1])
            elif line.startswith('collected'):
                # Parse "collected X items"
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        counts['total'] = int(parts[1])
                    except ValueError:
                        pass

        # Calculate total if not found
        if counts['total'] == 0:
            counts['total'] = counts['passed'] + counts['failed'] + counts['skipped'] + counts['errors']

        return counts

    def _extract_violations(self, stdout: str, stderr: str) -> List[str]:
        """Extract SSOT violations from test output."""
        violations = []
        output = stdout + stderr

        # Look for specific violation patterns
        violation_patterns = [
            "SSOT VIOLATION:",
            "Found 3 config managers",
            "Method signature conflicts",
            "Direct os.environ access",
            "import conflicts",
            "missing required methods",
            "duplicate config managers"
        ]

        for line in output.split('\n'):
            for pattern in violation_patterns:
                if pattern.lower() in line.lower():
                    violations.append(line.strip())
                    break

        return violations

    def _calculate_test_quality(self, test_file: str, result: subprocess.CompletedProcess, violations: List[str]) -> float:
        """Calculate test quality score (0-100)."""
        score = 100.0

        # Check if test runs successfully
        if result.returncode != 0:
            # For SSOT violation tests, failures might be expected
            if "ssot" in test_file.lower() and violations:
                # Good - test detected violations as expected
                score = 90.0
            else:
                # Bad - test failed without detecting violations
                score = 30.0

        # Check for test setup issues
        if "AttributeError" in result.stderr and "has no attribute" in result.stderr:
            score -= 20  # Test quality issue

        if "ImportError" in result.stderr:
            score -= 30  # Serious test setup issue

        # Check if test is actually validating SSOT violations
        if "ssot" in test_file.lower() and not violations:
            score -= 40  # Test not detecting expected violations

        # Bonus for finding many violations (comprehensive test)
        if len(violations) > 5:
            score += 10

        return max(0.0, min(100.0, score))

    def _is_expected_failure(self, test_file: str, result: TestResult) -> bool:
        """Check if this is an expected failure for SSOT violation tests."""
        # SSOT violation tests are EXPECTED to fail until violations are fixed
        expected_failure_files = [
            'test_config_manager_ssot_violations.py',
            'test_single_config_manager_ssot.py',
            'test_config_ssot_direct_environ_access_violations.py'
        ]

        for expected_file in expected_failure_files:
            if expected_file in test_file:
                # Expected to fail if violations detected
                return len(result.violations_detected) > 0

        return False

    def _generate_summary(self) -> TestSummary:
        """Generate comprehensive test execution summary."""
        total_duration = time.time() - self.start_time

        # Calculate totals
        total_tests = sum(r.total_tests for r in self.results)
        total_passed = sum(r.passed for r in self.results)
        total_failed = sum(r.failed for r in self.results)
        total_skipped = sum(r.skipped for r in self.results)

        # Analyze violations
        violations_summary = {}
        all_violations = []
        for result in self.results:
            all_violations.extend(result.violations_detected)

        # Count violation types
        violation_types = [
            "config managers",
            "method signature conflicts",
            "direct os.environ access",
            "import conflicts"
        ]

        for vtype in violation_types:
            count = sum(1 for v in all_violations if vtype in v.lower())
            if count > 0:
                violations_summary[vtype] = count

        # Test quality analysis
        avg_quality = sum(r.test_quality_score for r in self.results) / len(self.results) if self.results else 0
        quality_analysis = {
            'average_quality_score': avg_quality,
            'tests_with_quality_issues': len([r for r in self.results if r.test_quality_score < 60]),
            'tests_detecting_violations': len([r for r in self.results if r.violations_detected]),
            'expected_failures': len([r for r in self.results if self._is_expected_failure(r.test_file, r)])
        }

        # Generate recommendations
        recommendations = self._generate_recommendations(violations_summary, quality_analysis)

        return TestSummary(
            total_duration=total_duration,
            total_test_files=len(self.results),
            total_tests=total_tests,
            categories_tested=list(set(r.category for r in self.results)),
            results=self.results,
            violations_summary=violations_summary,
            test_quality_analysis=quality_analysis,
            recommendations=recommendations
        )

    def _generate_recommendations(self, violations: Dict[str, int], quality: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []

        # Violation-based recommendations
        if violations.get('config managers', 0) >= 3:
            recommendations.append(
                "🎯 CRITICAL: 3 configuration managers detected - proceed with SSOT consolidation"
            )

        if violations.get('method signature conflicts', 0) > 0:
            recommendations.append(
                "⚠️  HIGH: Method signature conflicts will cause runtime errors in Golden Path"
            )

        if violations.get('direct os.environ access', 0) > 0:
            recommendations.append(
                "🔧 MEDIUM: Direct os.environ access violations need IsolatedEnvironment migration"
            )

        # Quality-based recommendations
        if quality['average_quality_score'] < 70:
            recommendations.append(
                "🧪 Test quality needs improvement - fix test setup issues before remediation"
            )

        if quality['tests_with_quality_issues'] > 0:
            recommendations.append(
                f"🔨 Fix {quality['tests_with_quality_issues']} tests with quality issues"
            )

        # Strategic recommendations
        if quality['tests_detecting_violations'] >= 2:
            recommendations.append(
                "✅ Tests are effectively detecting SSOT violations - ready for remediation planning"
            )
        else:
            recommendations.append(
                "❌ Tests not detecting enough violations - improve test coverage before proceeding"
            )

        return recommendations

    def _log_summary(self, summary: TestSummary):
        """Log comprehensive test execution summary."""
        logger.info("\n" + "=" * 80)
        logger.info("📊 CONFIGURATION MANAGER SSOT VIOLATIONS - TEST EXECUTION SUMMARY")
        logger.info("=" * 80)

        logger.info(f"⏱️  Total Duration: {summary.total_duration:.2f} seconds")
        logger.info(f"📁 Test Files: {summary.total_test_files}")
        logger.info(f"🧪 Total Tests: {summary.total_tests}")
        logger.info(f"📋 Categories: {', '.join(summary.categories_tested)}")

        # Test results summary
        logger.info("\n📈 TEST RESULTS BY CATEGORY:")
        for category in summary.categories_tested:
            category_results = [r for r in summary.results if r.category == category]
            total_tests = sum(r.total_tests for r in category_results)
            passed = sum(r.passed for r in category_results)
            failed = sum(r.failed for r in category_results)

            logger.info(f"  {category}: {passed}/{total_tests} passed, {failed} failed")

        # Violations summary
        if summary.violations_summary:
            logger.info("\n🔍 SSOT VIOLATIONS DETECTED:")
            for violation_type, count in summary.violations_summary.items():
                logger.info(f"  • {violation_type}: {count} instances")
        else:
            logger.info("\n✅ No SSOT violations detected")

        # Test quality analysis
        logger.info(f"\n🎯 TEST QUALITY ANALYSIS:")
        logger.info(f"  • Average Quality Score: {summary.test_quality_analysis['average_quality_score']:.1f}/100")
        logger.info(f"  • Tests with Quality Issues: {summary.test_quality_analysis['tests_with_quality_issues']}")
        logger.info(f"  • Tests Detecting Violations: {summary.test_quality_analysis['tests_detecting_violations']}")
        logger.info(f"  • Expected Failures: {summary.test_quality_analysis['expected_failures']}")

        # Recommendations
        if summary.recommendations:
            logger.info("\n🚀 RECOMMENDATIONS:")
            for i, rec in enumerate(summary.recommendations, 1):
                logger.info(f"  {i}. {rec}")

        # Decision guidance
        logger.info("\n🎯 NEXT STEPS DECISION MATRIX:")
        if summary.test_quality_analysis['average_quality_score'] >= 70:
            if summary.violations_summary:
                logger.info("  ✅ PROCEED TO REMEDIATION: Tests are working and detecting violations")
            else:
                logger.info("  ⚠️  INVESTIGATE: Tests working but no violations found")
        else:
            logger.info("  🔧 FIX TESTS FIRST: Improve test quality before proceeding")

        logger.info("=" * 80)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Run Configuration Manager SSOT Violations Tests')
    parser.add_argument('--category', choices=['all', 'mission-critical', 'integration', 'e2e'],
                       default='all', help='Test category to run')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--report-file', help='Generate JSON report file')
    parser.add_argument('--no-fail-fast', action='store_true', help='Continue on failures')

    args = parser.parse_args()

    # Determine categories to run
    if args.category == 'all':
        categories = ['mission-critical', 'integration']  # Skip E2E unless explicitly requested
    elif args.category == 'e2e':
        categories = ['e2e']
        logger.warning("⚠️  E2E tests require staging environment access")
    else:
        categories = [args.category]

    # Run tests
    runner = ConfigSSotTestRunner(project_root)
    summary = runner.run_tests(
        categories=categories,
        fail_fast=not args.no_fail_fast,
        verbose=args.verbose
    )

    # Generate report file if requested
    if args.report_file:
        with open(args.report_file, 'w') as f:
            json.dump(asdict(summary), f, indent=2)
        logger.info(f"📄 Report saved to: {args.report_file}")

    # Exit with appropriate code
    if summary.test_quality_analysis['average_quality_score'] >= 70:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Need to fix tests first


if __name__ == "__main__":
    main()
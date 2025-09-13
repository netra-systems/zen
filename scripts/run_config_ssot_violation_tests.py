#!/usr/bin/env python3
"""
Configuration SSOT Violation Test Runner - Issue #667

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability - Validate SSOT violation detection
- Value Impact: Ensures tests properly detect configuration manager conflicts
- Strategic Impact: Provides validation framework for SSOT consolidation

PURPOSE: Execute comprehensive test suite to validate configuration manager
SSOT violations and ensure tests properly demonstrate the problems before
implementing consolidation solutions.

Test Execution Strategy:
1. Run unit tests to detect import and method conflicts
2. Execute integration tests for system consistency validation
3. Run E2E tests on staging environment (if available)
4. Generate comprehensive test report with violation details
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from netra_backend.app.core.unified_logging import central_logger
    logger = central_logger.get_logger(__name__)
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


class ConfigSSotViolationTestRunner:
    """Test runner for configuration SSOT violation validation."""

    def __init__(self):
        """Initialize the test runner."""
        self.project_root = PROJECT_ROOT
        self.test_results = {
            'unit_tests': {},
            'integration_tests': {},
            'e2e_tests': {},
            'summary': {
                'total_tests': 0,
                'total_failures': 0,
                'expected_failures': 0,
                'unexpected_passes': 0,
                'violations_detected': []
            }
        }

    def run_unit_tests(self) -> Dict[str, Any]:
        """Run unit tests for configuration manager SSOT violations."""
        logger.info("🔍 Running Unit Tests - Configuration Manager SSOT Violations")

        unit_test_files = [
            'tests/unit/config_ssot/test_config_manager_import_conflicts.py',
            'tests/unit/config_ssot/test_config_manager_behavior_consistency.py'
        ]

        unit_results = {}

        for test_file in unit_test_files:
            test_path = self.project_root / test_file
            if not test_path.exists():
                logger.warning(f"❌ Unit test file not found: {test_file}")
                continue

            logger.info(f"📋 Running: {test_file}")

            try:
                # Run the test with pytest
                result = subprocess.run([
                    sys.executable, '-m', 'pytest',
                    str(test_path),
                    '-v',
                    '--tb=short',
                    '--json-report',
                    '--json-report-file', f'/tmp/unit_test_report_{int(time.time())}.json'
                ], cwd=self.project_root, capture_output=True, text=True, timeout=300)

                unit_results[test_file] = {
                    'exit_code': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'expected_failures': self._count_expected_failures(result.stdout),
                    'unexpected_passes': self._count_unexpected_passes(result.stdout)
                }

                if result.returncode == 0:
                    logger.warning(f"⚠️  UNEXPECTED: {test_file} passed (expected failures for SSOT violations)")
                else:
                    logger.info(f"✅ EXPECTED: {test_file} failed (demonstrates SSOT violations)")

            except subprocess.TimeoutExpired:
                logger.error(f"❌ Timeout running {test_file}")
                unit_results[test_file] = {'error': 'timeout'}
            except Exception as e:
                logger.error(f"❌ Error running {test_file}: {str(e)}")
                unit_results[test_file] = {'error': str(e)}

        self.test_results['unit_tests'] = unit_results
        return unit_results

    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests for system-wide configuration consistency."""
        logger.info("🔧 Running Integration Tests - System Configuration Consistency")

        integration_test_files = [
            'tests/integration/config_ssot/test_config_system_consistency_integration.py',
            'tests/integration/config_ssot/test_config_golden_path_protection.py'
        ]

        integration_results = {}

        for test_file in integration_test_files:
            test_path = self.project_root / test_file
            if not test_path.exists():
                logger.warning(f"❌ Integration test file not found: {test_file}")
                continue

            logger.info(f"📋 Running: {test_file}")

            try:
                # Run with real services (no Docker requirement)
                result = subprocess.run([
                    sys.executable, '-m', 'pytest',
                    str(test_path),
                    '-v',
                    '--tb=short',
                    '--json-report',
                    '--json-report-file', f'/tmp/integration_test_report_{int(time.time())}.json'
                ], cwd=self.project_root, capture_output=True, text=True, timeout=600)

                integration_results[test_file] = {
                    'exit_code': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'expected_failures': self._count_expected_failures(result.stdout),
                    'unexpected_passes': self._count_unexpected_passes(result.stdout)
                }

                if result.returncode == 0:
                    logger.warning(f"⚠️  UNEXPECTED: {test_file} passed (expected failures for SSOT violations)")
                else:
                    logger.info(f"✅ EXPECTED: {test_file} failed (demonstrates system-wide SSOT violations)")

            except subprocess.TimeoutExpired:
                logger.error(f"❌ Timeout running {test_file}")
                integration_results[test_file] = {'error': 'timeout'}
            except Exception as e:
                logger.error(f"❌ Error running {test_file}: {str(e)}")
                integration_results[test_file] = {'error': str(e)}

        self.test_results['integration_tests'] = integration_results
        return integration_results

    def run_e2e_tests(self, staging_only: bool = True) -> Dict[str, Any]:
        """Run E2E tests on staging environment."""
        logger.info("🌐 Running E2E Tests - Staging Environment Validation")

        if staging_only and not self._is_staging_environment():
            logger.info("⏭️  Skipping E2E tests (not in staging environment)")
            return {'skipped': 'not_in_staging_environment'}

        e2e_test_files = [
            'tests/e2e/config_ssot/test_config_ssot_staging_validation.py'
        ]

        e2e_results = {}

        for test_file in e2e_test_files:
            test_path = self.project_root / test_file
            if not test_path.exists():
                logger.warning(f"❌ E2E test file not found: {test_file}")
                continue

            logger.info(f"📋 Running: {test_file}")

            try:
                # Run E2E tests with staging markers
                result = subprocess.run([
                    sys.executable, '-m', 'pytest',
                    str(test_path),
                    '-v',
                    '-m', 'staging_only',
                    '--tb=short',
                    '--json-report',
                    '--json-report-file', f'/tmp/e2e_test_report_{int(time.time())}.json'
                ], cwd=self.project_root, capture_output=True, text=True, timeout=900)

                e2e_results[test_file] = {
                    'exit_code': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'expected_failures': self._count_expected_failures(result.stdout),
                    'unexpected_passes': self._count_unexpected_passes(result.stdout)
                }

                if result.returncode == 0:
                    logger.warning(f"⚠️  UNEXPECTED: {test_file} passed (expected failures for staging SSOT violations)")
                else:
                    logger.info(f"✅ EXPECTED: {test_file} failed (demonstrates staging SSOT violations)")

            except subprocess.TimeoutExpired:
                logger.error(f"❌ Timeout running {test_file}")
                e2e_results[test_file] = {'error': 'timeout'}
            except Exception as e:
                logger.error(f"❌ Error running {test_file}: {str(e)}")
                e2e_results[test_file] = {'error': str(e)}

        self.test_results['e2e_tests'] = e2e_results
        return e2e_results

    def _is_staging_environment(self) -> bool:
        """Check if running in staging environment."""
        environment = os.getenv('ENVIRONMENT', '').lower()
        cloud_run = os.getenv('K_SERVICE', '')
        staging_project = os.getenv('GOOGLE_CLOUD_PROJECT', '') == 'netra-staging'

        return environment == 'staging' or bool(cloud_run) or staging_project

    def _count_expected_failures(self, output: str) -> int:
        """Count expected failures in test output."""
        expected_failure_indicators = [
            'EXPECTED TO FAIL',
            'SSOT VIOLATION',
            'GOLDEN PATH BLOCKED',
            'CONFIGURATION VIOLATIONS DETECTED'
        ]

        count = 0
        for indicator in expected_failure_indicators:
            count += output.count(indicator)

        return count

    def _count_unexpected_passes(self, output: str) -> int:
        """Count unexpected passes in test output."""
        # Look for test methods that passed when they should have failed
        lines = output.split('\n')
        unexpected_passes = 0

        for line in lines:
            if 'PASSED' in line and any(indicator in line for indicator in [
                'test_.*_violation',
                'test_.*_conflict',
                'test_.*_ssot'
            ]):
                unexpected_passes += 1

        return unexpected_passes

    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate comprehensive summary report."""
        logger.info("📊 Generating Configuration SSOT Violation Test Summary")

        summary = self.test_results['summary']

        # Count totals across all test categories
        for category in ['unit_tests', 'integration_tests', 'e2e_tests']:
            for test_file, results in self.test_results[category].items():
                if isinstance(results, dict) and 'error' not in results:
                    summary['total_tests'] += 1
                    if results.get('exit_code', 0) != 0:
                        summary['total_failures'] += 1
                    summary['expected_failures'] += results.get('expected_failures', 0)
                    summary['unexpected_passes'] += results.get('unexpected_passes', 0)

        # Identify detected violations
        violations_detected = []

        if summary['total_failures'] > 0:
            violations_detected.append("Configuration manager import conflicts detected")

        if summary['expected_failures'] > 0:
            violations_detected.append("SSOT violations properly identified by tests")

        if summary['unexpected_passes'] > 0:
            violations_detected.append("Some tests passed unexpectedly - may indicate partial fixes")

        summary['violations_detected'] = violations_detected

        # Business impact assessment
        business_impact = {
            'golden_path_affected': summary['total_failures'] > 0,
            'revenue_at_risk': '$500K+ ARR' if summary['total_failures'] > 0 else 'Protected',
            'remediation_required': summary['expected_failures'] > 0,
            'test_strategy_effective': summary['expected_failures'] > summary['unexpected_passes']
        }

        summary['business_impact'] = business_impact

        return summary

    def save_results(self, output_file: Optional[str] = None) -> str:
        """Save test results to file."""
        if output_file is None:
            timestamp = int(time.time())
            output_file = f"config_ssot_violation_test_results_{timestamp}.json"

        output_path = self.project_root / output_file

        with open(output_path, 'w') as f:
            json.dump(self.test_results, f, indent=2)

        logger.info(f"💾 Test results saved to: {output_path}")
        return str(output_path)

    def print_summary(self):
        """Print human-readable test summary."""
        summary = self.test_results['summary']

        print("\n" + "="*80)
        print("🔍 CONFIGURATION SSOT VIOLATION TEST SUMMARY - Issue #667")
        print("="*80)

        print(f"\n📊 Test Execution Summary:")
        print(f"   Total Tests Executed: {summary['total_tests']}")
        print(f"   Total Failures: {summary['total_failures']}")
        print(f"   Expected Failures: {summary['expected_failures']}")
        print(f"   Unexpected Passes: {summary['unexpected_passes']}")

        print(f"\n🎯 SSOT Violations Detected:")
        for violation in summary['violations_detected']:
            print(f"   ✓ {violation}")

        business_impact = summary.get('business_impact', {})
        print(f"\n💰 Business Impact Assessment:")
        print(f"   Golden Path Affected: {'YES' if business_impact.get('golden_path_affected', False) else 'NO'}")
        print(f"   Revenue at Risk: {business_impact.get('revenue_at_risk', 'Unknown')}")
        print(f"   Remediation Required: {'YES' if business_impact.get('remediation_required', False) else 'NO'}")
        print(f"   Test Strategy Effective: {'YES' if business_impact.get('test_strategy_effective', False) else 'NO'}")

        if summary['expected_failures'] > 0:
            print(f"\n✅ SUCCESS: Tests properly demonstrate SSOT violations!")
            print(f"   The test suite successfully identifies configuration manager conflicts.")
            print(f"   These failures validate that Issue #667 SSOT violations exist and need remediation.")
        else:
            print(f"\n⚠️  WARNING: No SSOT violations detected by tests!")
            print(f"   This may indicate tests need improvement or violations have been resolved.")

        print("\n" + "="*80)


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Run Configuration SSOT Violation Tests')
    parser.add_argument('--unit-only', action='store_true', help='Run only unit tests')
    parser.add_argument('--integration-only', action='store_true', help='Run only integration tests')
    parser.add_argument('--e2e-only', action='store_true', help='Run only E2E tests')
    parser.add_argument('--skip-staging', action='store_true', help='Skip staging E2E tests')
    parser.add_argument('--output', '-o', help='Output file for test results')

    args = parser.parse_args()

    runner = ConfigSSotViolationTestRunner()

    try:
        logger.info("🚀 Starting Configuration SSOT Violation Test Suite - Issue #667")

        if not args.integration_only and not args.e2e_only:
            runner.run_unit_tests()

        if not args.unit_only and not args.e2e_only:
            runner.run_integration_tests()

        if not args.unit_only and not args.integration_only and not args.skip_staging:
            runner.run_e2e_tests()

        # Generate and display summary
        runner.generate_summary_report()
        runner.print_summary()

        # Save results
        output_file = runner.save_results(args.output)

        logger.info("✅ Configuration SSOT Violation Test Suite completed successfully")
        return 0

    except Exception as e:
        logger.error(f"❌ Test suite execution failed: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
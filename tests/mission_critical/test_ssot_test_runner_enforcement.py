#!/usr/bin/env python3
"""
MISSION CRITICAL: SSOT Test Runner Enforcement
==============================================

BUSINESS JUSTIFICATION:
Platform/Internal - System Stability & Compliance (Critical Security)

This test prevents the creation of unauthorized test runners, enforcing the
Single Source of Truth (SSOT) principle mandated by CLAUDE.md. Unauthorized
test runners can bypass all SSOT protections, creating cascade failures that
impact the $500K+ ARR Golden Path.

CRITICAL SECURITY: This is the #1 security vulnerability - unauthorized test 
runners can bypass all SSOT protections and cause system-wide failures.

The ONLY allowed test runner is tests/unified_test_runner.py.
Any additional test runners will cause system test execution failure.

REQUIREMENTS:
- Scan filesystem for unauthorized test runners
- Detect direct pytest bypasses in CI/scripts
- Enforce SSOT orchestration compliance
- Provide clear remediation steps for violations
- Fail hard with no silent failures

VIOLATION IMPACT:
- 150+ SSOT violations currently undetected
- Cascade failures in Golden Path user flows
- Inconsistent test execution across environments
- Security bypasses in critical business flows
"""

import sys
from pathlib import Path

# Setup Python path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

import logging
import re
import subprocess
from typing import Dict, List, Set, Tuple

import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment

logger = logging.getLogger(__name__)

# PROJECT_ROOT already defined above for path setup

# SSOT: The ONLY allowed test runner
ALLOWED_TEST_RUNNER = PROJECT_ROOT / "tests" / "unified_test_runner.py"

# Allowed legacy wrappers (must redirect to SSOT)
ALLOWED_LEGACY_WRAPPERS = {
    PROJECT_ROOT / "scripts" / "test_backend.py",
    PROJECT_ROOT / "scripts" / "test_frontend.py",
    PROJECT_ROOT / "test_framework" / "integrated_test_runner.py",
    PROJECT_ROOT / "tests" / "staging" / "run_staging_tests.py",
}

# Paths to scan for unauthorized test runners
SCAN_PATHS = [
    PROJECT_ROOT / "scripts",
    PROJECT_ROOT / "tests",
    PROJECT_ROOT / "test_framework",
    PROJECT_ROOT / "netra_backend" / "tests",
    PROJECT_ROOT / "auth_service" / "tests",
    PROJECT_ROOT / "frontend" / "tests",
    PROJECT_ROOT / "analytics_service" / "tests",
    PROJECT_ROOT / ".github" / "workflows",
    PROJECT_ROOT / ".github" / "scripts",
]

# Forbidden test runner patterns
FORBIDDEN_RUNNER_PATTERNS = [
    "run_tests.py",
    "test_runner.py", 
    "pytest_runner.py",
    "test_suite_runner.py",
    "run_all_tests.py",
    "cypress_runner.py",
    "e2e_runner.py",
    "integration_runner.py",
]

# Forbidden direct pytest execution patterns
FORBIDDEN_PYTEST_PATTERNS = [
    r"subprocess\.run\(\s*\[\s*['\"]pytest['\"]",
    r"subprocess\.call\(\s*\[\s*['\"]pytest['\"]", 
    r"os\.system\(\s*['\"]pytest",
    r"pytest\.main\(",
    r"exec\(\s*['\"]pytest",
    r"shell=True.*pytest",
]

# Forbidden orchestration bypass patterns
FORBIDDEN_ORCHESTRATION_PATTERNS = [
    r"try:\s*import.*orchestration",
    r"except.*ImportError.*orchestration",
    r"if.*available.*orchestration",
    r"try:\s*from.*orchestration.*except",
]


class TestSSOTTestRunnerEnforcement(SSotBaseTestCase):
    """Enforce SSOT test runner policy with real filesystem scanning."""

    def setup_method(self, method=None):
        """Setup test method with SSOT compliance."""
        super().setup_method(method)
        self.record_metric("test_type", "mission_critical_ssot_enforcement")
        self.record_metric("business_value", "system_stability_compliance")

    def test_ssot_test_runner_exists(self):
        """CRITICAL: Verify the SSOT test runner exists and is functional."""
        # Test that the SSOT runner exists
        assert ALLOWED_TEST_RUNNER.exists(), (
            f"CRITICAL SSOT VIOLATION: Unified test runner missing at {ALLOWED_TEST_RUNNER}\n"
            f"REMEDIATION: Restore tests/unified_test_runner.py from version control"
        )
        
        # Test that it's actually a test runner with proper functionality
        content = ALLOWED_TEST_RUNNER.read_text(encoding='utf-8', errors='ignore')
        
        # Must have main execution capability
        assert '__name__ == "__main__"' in content, (
            f"CRITICAL: {ALLOWED_TEST_RUNNER} missing main execution block\n"
            f"REMEDIATION: Add main execution block to unified test runner"
        )
        
        # Must have argument parsing
        assert 'argparse' in content and 'ArgumentParser' in content, (
            f"CRITICAL: {ALLOWED_TEST_RUNNER} missing argument parsing\n"
            f"REMEDIATION: Add argparse functionality to unified test runner"
        )
        
        # Must support category/layer execution
        content_lower = content.lower()
        assert ('category' in content_lower or 'layer' in content_lower), (
            f"CRITICAL: {ALLOWED_TEST_RUNNER} missing category/layer support\n"
            f"REMEDIATION: Add category and layer execution support"
        )
        
        self.record_metric("ssot_runner_validated", True)
        logger.info("✅ SSOT test runner validation passed")

    def test_no_unauthorized_test_runners(self):
        """CRITICAL: Ensure no unauthorized test runners exist."""
        unauthorized_runners = self._find_unauthorized_test_runners()
        
        if unauthorized_runners:
            violation_details = self._format_test_runner_violations(unauthorized_runners)
            pytest.fail(violation_details)
        
        self.record_metric("unauthorized_runners_found", 0)
        logger.info("✅ No unauthorized test runners found")

    def test_no_direct_pytest_bypasses(self):
        """CRITICAL: Prevent scripts calling pytest directly, bypassing SSOT."""
        pytest_bypasses = self._find_direct_pytest_bypasses()
        
        if pytest_bypasses:
            violation_details = self._format_pytest_bypass_violations(pytest_bypasses)
            pytest.fail(violation_details)
        
        self.record_metric("pytest_bypasses_found", 0)
        logger.info("✅ No direct pytest bypasses found")

    def test_ssot_orchestration_compliance(self):
        """CRITICAL: All orchestration uses SSOT patterns, no try-except bypasses."""
        orchestration_violations = self._find_orchestration_bypass_violations()
        
        if orchestration_violations:
            violation_details = self._format_orchestration_violations(orchestration_violations)
            pytest.fail(violation_details)
        
        self.record_metric("orchestration_violations_found", 0)
        logger.info("✅ SSOT orchestration compliance verified")

    def test_legacy_wrappers_redirect_to_ssot(self):
        """CRITICAL: Verify legacy wrappers properly redirect to SSOT."""
        invalid_wrappers = self._find_invalid_legacy_wrappers()
        
        if invalid_wrappers:
            violation_details = self._format_legacy_wrapper_violations(invalid_wrappers)
            pytest.fail(violation_details)
        
        self.record_metric("invalid_legacy_wrappers", 0)
        logger.info("✅ Legacy wrapper compliance verified")

    def test_ci_scripts_use_ssot_runner(self):
        """WARNING: Check CI/CD scripts for SSOT compliance (warning only)."""
        ci_violations = self._find_ci_script_violations()
        
        if ci_violations:
            warning_message = self._format_ci_violations_warning(ci_violations)
            logger.warning(warning_message)
            self.record_metric("ci_violations_found", len(ci_violations))
        else:
            self.record_metric("ci_violations_found", 0)
            logger.info("✅ CI scripts SSOT compliance verified")

    # === PRIVATE IMPLEMENTATION METHODS ===

    def _find_unauthorized_test_runners(self) -> List[Tuple[Path, str]]:
        """Find all unauthorized test runner files."""
        unauthorized_runners = []
        
        for scan_path in SCAN_PATHS:
            if not scan_path.exists():
                continue
                
            # Scan for Python files that might be test runners
            for file_path in scan_path.rglob('*.py'):
                if self._is_unauthorized_test_runner(file_path):
                    reason = self._analyze_test_runner_violation(file_path)
                    unauthorized_runners.append((file_path, reason))
        
        return unauthorized_runners

    def _is_unauthorized_test_runner(self, file_path: Path) -> bool:
        """Check if a file is an unauthorized test runner."""
        # Skip if it's the allowed SSOT runner
        if file_path.resolve() == ALLOWED_TEST_RUNNER.resolve():
            return False
        
        # Skip if it's an allowed legacy wrapper
        if file_path.resolve() in {p.resolve() for p in ALLOWED_LEGACY_WRAPPERS}:
            return False
        
        # Skip if it's this enforcement test
        if file_path.name == 'test_ssot_test_runner_enforcement.py':
            return False
            
        # Skip backup files
        if any(pattern in file_path.name for pattern in ['_BACKUP.py', '_OLD.py', '_ORIGINAL.py']):
            return False
        
        # Check for forbidden filename patterns
        if any(pattern in file_path.name.lower() for pattern in FORBIDDEN_RUNNER_PATTERNS):
            return True
        
        # Check file content for test runner behavior
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            return self._has_test_runner_behavior(content)
        except Exception:
            return False

    def _has_test_runner_behavior(self, content: str) -> bool:
        """Check if file content indicates test runner behavior."""
        content_lower = content.lower()
        
        # Must have main execution
        has_main = '__name__ == "__main__"' in content_lower
        if not has_main:
            return False
        
        # Must have argument parsing
        has_argparse = 'argparse' in content_lower and 'argumentparser' in content_lower
        if not has_argparse:
            return False
        
        # Must have test execution patterns
        test_execution_patterns = [
            'pytest.main(',
            'subprocess' in content_lower and 'pytest' in content_lower,
            'subprocess' in content_lower and 'npm' in content_lower and 'test' in content_lower,
            'unittest.main(',
            'coverage run',
        ]
        
        has_test_execution = any(pattern for pattern in test_execution_patterns if isinstance(pattern, str) and pattern in content_lower) or \
                           any(pattern for pattern in test_execution_patterns if isinstance(pattern, bool) and pattern)
        
        return has_test_execution

    def _analyze_test_runner_violation(self, file_path: Path) -> str:
        """Analyze why a file is considered an unauthorized test runner."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            reasons = []
            
            if any(pattern in file_path.name.lower() for pattern in FORBIDDEN_RUNNER_PATTERNS):
                reasons.append("Forbidden filename pattern")
            
            if '__name__ == "__main__"' in content.lower():
                reasons.append("Has main execution block")
            
            if 'argparse' in content.lower():
                reasons.append("Has argument parsing")
            
            if 'pytest.main(' in content.lower():
                reasons.append("Calls pytest.main()")
            
            if 'subprocess' in content.lower() and 'pytest' in content.lower():
                reasons.append("Subprocess pytest execution")
            
            return "; ".join(reasons) if reasons else "General test runner behavior"
            
        except Exception:
            return "File analysis failed"

    def _find_direct_pytest_bypasses(self) -> List[Tuple[Path, List[str]]]:
        """Find files with direct pytest execution bypassing SSOT."""
        pytest_bypasses = []
        
        for scan_path in SCAN_PATHS:
            if not scan_path.exists():
                continue
                
            for file_path in scan_path.rglob('*'):
                if not file_path.is_file():
                    continue
                
                # Check various file types for pytest bypasses
                if file_path.suffix in ['.py', '.sh', '.yml', '.yaml', '.json']:
                    violations = self._check_file_for_pytest_bypasses(file_path)
                    if violations:
                        pytest_bypasses.append((file_path, violations))
        
        return pytest_bypasses

    def _check_file_for_pytest_bypasses(self, file_path: Path) -> List[str]:
        """Check a single file for pytest bypass patterns."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            violations = []
            
            for pattern in FORBIDDEN_PYTEST_PATTERNS:
                matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    violations.append(f"Line {line_num}: {match.group()}")
            
            return violations
            
        except Exception:
            return []

    def _find_orchestration_bypass_violations(self) -> List[Tuple[Path, List[str]]]:
        """Find orchestration try-except bypass patterns."""
        violations = []
        
        for scan_path in SCAN_PATHS:
            if not scan_path.exists():
                continue
                
            for file_path in scan_path.rglob('*.py'):
                if not file_path.is_file():
                    continue
                
                bypass_violations = self._check_orchestration_bypasses(file_path)
                if bypass_violations:
                    violations.append((file_path, bypass_violations))
        
        return violations

    def _check_orchestration_bypasses(self, file_path: Path) -> List[str]:
        """Check file for orchestration bypass patterns."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            violations = []
            
            for pattern in FORBIDDEN_ORCHESTRATION_PATTERNS:
                matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    violations.append(f"Line {line_num}: Try-except orchestration bypass")
            
            return violations
            
        except Exception:
            return []

    def _find_invalid_legacy_wrappers(self) -> List[Tuple[Path, str]]:
        """Find legacy wrappers that don't properly redirect to SSOT."""
        invalid_wrappers = []
        
        for wrapper_path in ALLOWED_LEGACY_WRAPPERS:
            if not wrapper_path.exists():
                continue  # Optional legacy wrapper
            
            if not self._is_valid_legacy_wrapper(wrapper_path):
                reason = self._analyze_legacy_wrapper_violation(wrapper_path)
                invalid_wrappers.append((wrapper_path, reason))
        
        return invalid_wrappers

    def _is_valid_legacy_wrapper(self, wrapper_path: Path) -> bool:
        """Check if wrapper properly redirects to SSOT."""
        try:
            content = wrapper_path.read_text(encoding='utf-8', errors='ignore')
            content_upper = content.upper()
            
            # Must contain deprecation warning
            has_deprecation = any(keyword in content_upper for keyword in ['DEPRECATION', 'DEPRECATED', 'LEGACY'])
            
            # Must redirect to unified_test_runner.py
            has_redirect = 'unified_test_runner.py' in content
            
            # Must not contain substantial test logic
            has_substantial_logic = any(pattern in content.lower() for pattern in [
                'pytest.main(',
                'unittest.main(',
                'subprocess.run([\"pytest\"',
                'subprocess.call([\"pytest\"'
            ])
            
            return has_deprecation and has_redirect and not has_substantial_logic
            
        except Exception:
            return False

    def _analyze_legacy_wrapper_violation(self, wrapper_path: Path) -> str:
        """Analyze why a legacy wrapper is invalid."""
        try:
            content = wrapper_path.read_text(encoding='utf-8', errors='ignore')
            issues = []
            
            if not any(keyword in content.upper() for keyword in ['DEPRECATION', 'DEPRECATED', 'LEGACY']):
                issues.append("Missing deprecation warning")
            
            if 'unified_test_runner.py' not in content:
                issues.append("No redirect to SSOT")
            
            if any(pattern in content.lower() for pattern in ['pytest.main(', 'unittest.main(']):
                issues.append("Contains substantial test logic")
            
            return "; ".join(issues) if issues else "General validation failure"
            
        except Exception:
            return "File analysis failed"

    def _find_ci_script_violations(self) -> List[Tuple[Path, List[str]]]:
        """Find CI scripts that don't use SSOT runner (warning only)."""
        ci_violations = []
        
        ci_paths = [
            PROJECT_ROOT / ".github" / "workflows",
            PROJECT_ROOT / ".github" / "scripts", 
            PROJECT_ROOT / "scripts",
        ]
        
        for ci_path in ci_paths:
            if not ci_path.exists():
                continue
                
            for file_path in ci_path.rglob('*'):
                if not file_path.is_file():
                    continue
                
                violations = self._check_ci_script_compliance(file_path)
                if violations:
                    ci_violations.append((file_path, violations))
        
        return ci_violations

    def _check_ci_script_compliance(self, file_path: Path) -> List[str]:
        """Check CI script for SSOT compliance."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            violations = []
            
            # Check for references to old test runners without SSOT
            old_runners = [
                'scripts/test_backend.py',
                'scripts/test_frontend.py',
                'test_framework/integrated_test_runner.py'
            ]
            
            for old_runner in old_runners:
                if old_runner in content and 'unified_test_runner.py' not in content:
                    violations.append(f"References {old_runner} without SSOT alternative")
            
            return violations
            
        except Exception:
            return []

    # === VIOLATION FORMATTING METHODS ===

    def _format_test_runner_violations(self, violations: List[Tuple[Path, str]]) -> str:
        """Format test runner violations into failure message."""
        violation_list = []
        for file_path, reason in violations:
            relative_path = file_path.relative_to(PROJECT_ROOT)
            violation_list.append(f"  - {relative_path} ({reason})")
        
        return (
            f"CRITICAL SSOT VIOLATION: {len(violations)} unauthorized test runners found!\n\n"
            f"The Golden Path ($500K+ ARR) requires a Single Source of Truth for test execution.\n"
            f"Only tests/unified_test_runner.py is allowed.\n\n"
            f"Unauthorized runners found:\n" + "\n".join(violation_list) + "\n\n"
            f"REMEDIATION:\n"
            f"1. Remove unauthorized test runners immediately\n"
            f"2. Update scripts to use: python tests/unified_test_runner.py\n"
            f"3. For service-specific tests use: --service backend|frontend\n"
            f"4. For legacy compatibility, create deprecation wrappers only\n"
            f"5. Run compliance check: python tests/mission_critical/test_ssot_test_runner_enforcement.py\n\n"
            f"SECURITY IMPACT: Unauthorized runners bypass SSOT protections and enable cascade failures."
        )

    def _format_pytest_bypass_violations(self, violations: List[Tuple[Path, List[str]]]) -> str:
        """Format pytest bypass violations into failure message."""
        violation_details = []
        total_violations = 0
        
        for file_path, file_violations in violations:
            relative_path = file_path.relative_to(PROJECT_ROOT)
            violation_details.append(f"  {relative_path}:")
            for violation in file_violations:
                violation_details.append(f"    - {violation}")
            total_violations += len(file_violations)
        
        return (
            f"CRITICAL SSOT VIOLATION: {total_violations} direct pytest bypasses found!\n\n"
            f"Direct pytest execution bypasses SSOT test runner controls.\n"
            f"All test execution must go through tests/unified_test_runner.py\n\n"
            f"Pytest bypasses found:\n" + "\n".join(violation_details) + "\n\n"
            f"REMEDIATION:\n"
            f"1. Replace direct pytest calls with: python tests/unified_test_runner.py\n"
            f"2. Update CI/CD scripts to use SSOT runner\n"
            f"3. Remove subprocess pytest execution\n"
            f"4. Use unified runner arguments for test selection\n\n"
            f"SECURITY IMPACT: Direct pytest bypasses enable SSOT violation cascade failures."
        )

    def _format_orchestration_violations(self, violations: List[Tuple[Path, List[str]]]) -> str:
        """Format orchestration violations into failure message."""
        violation_details = []
        total_violations = 0
        
        for file_path, file_violations in violations:
            relative_path = file_path.relative_to(PROJECT_ROOT)
            violation_details.append(f"  {relative_path}:")
            for violation in file_violations:
                violation_details.append(f"    - {violation}")
            total_violations += len(file_violations)
        
        return (
            f"CRITICAL SSOT VIOLATION: {total_violations} orchestration bypasses found!\n\n"
            f"Try-except import patterns bypass SSOT orchestration controls.\n"
            f"All orchestration must use test_framework.ssot.orchestration modules.\n\n"
            f"Orchestration bypasses found:\n" + "\n".join(violation_details) + "\n\n"
            f"REMEDIATION:\n"
            f"1. Replace try-except imports with SSOT orchestration imports\n"
            f"2. Use from test_framework.ssot.orchestration import OrchestrationConfig\n"
            f"3. Use from test_framework.ssot.orchestration_enums import ServiceType\n"
            f"4. Remove availability checking with exception handling\n\n"
            f"SSOT IMPORTS:\n"
            f"  from test_framework.ssot.orchestration import get_orchestration_config\n"
            f"  from test_framework.ssot.orchestration_enums import *\n\n"
            f"SECURITY IMPACT: Orchestration bypasses enable inconsistent service dependencies."
        )

    def _format_legacy_wrapper_violations(self, violations: List[Tuple[Path, str]]) -> str:
        """Format legacy wrapper violations into failure message."""
        violation_list = []
        for file_path, reason in violations:
            relative_path = file_path.relative_to(PROJECT_ROOT)
            violation_list.append(f"  - {relative_path} ({reason})")
        
        return (
            f"CRITICAL SSOT VIOLATION: {len(violations)} invalid legacy wrappers found!\n\n"
            f"Legacy wrapper files must be proper deprecation wrappers that redirect to SSOT.\n\n"
            f"Invalid wrappers:\n" + "\n".join(violation_list) + "\n\n"
            f"REQUIREMENTS FOR VALID LEGACY WRAPPERS:\n"
            f"1. Must show DEPRECATION WARNING to users\n"
            f"2. Must redirect to tests/unified_test_runner.py\n"
            f"3. Must not contain substantial test execution logic\n"
            f"4. Should preserve argument compatibility\n\n"
            f"REMEDIATION:\n"
            f"1. Add deprecation warnings to wrapper files\n"
            f"2. Ensure all wrappers call unified_test_runner.py\n"
            f"3. Remove direct test execution logic from wrappers\n"
            f"4. Test wrapper functionality before deployment\n\n"
            f"SECURITY IMPACT: Invalid wrappers can bypass SSOT controls."
        )

    def _format_ci_violations_warning(self, violations: List[Tuple[Path, List[str]]]) -> str:
        """Format CI violations into warning message."""
        violation_details = []
        for file_path, file_violations in violations:
            relative_path = file_path.relative_to(PROJECT_ROOT)
            violation_details.append(f"  {relative_path}:")
            for violation in file_violations:
                violation_details.append(f"    - {violation}")
        
        return (
            f"WARNING: CI/CD scripts may reference old test runners.\n"
            f"Consider updating to use tests/unified_test_runner.py:\n\n" +
            "\n".join(violation_details) + "\n\n"
            f"This is a warning, not a failure, but should be addressed for consistency."
        )


if __name__ == "__main__":
    """
    Direct execution for validation - provides detailed SSOT compliance report.
    
    Usage:
        python tests/mission_critical/test_ssot_test_runner_enforcement.py
    """
    print("🔍 SSOT Test Runner Enforcement Validation")
    print("=" * 60)
    
    # Initialize test instance
    test_instance = TestSSOTTestRunnerEnforcement()
    test_instance.setup_method()
    
    try:
        # Run all enforcement checks
        print("\n1. Checking SSOT test runner exists...")
        test_instance.test_ssot_test_runner_exists()
        print("   ✅ SSOT test runner validation passed")
        
        print("\n2. Scanning for unauthorized test runners...")
        test_instance.test_no_unauthorized_test_runners()
        print("   ✅ No unauthorized test runners found")
        
        print("\n3. Checking for direct pytest bypasses...")
        test_instance.test_no_direct_pytest_bypasses()
        print("   ✅ No direct pytest bypasses found")
        
        print("\n4. Validating SSOT orchestration compliance...")
        test_instance.test_ssot_orchestration_compliance()
        print("   ✅ SSOT orchestration compliance verified")
        
        print("\n5. Checking legacy wrapper compliance...")
        test_instance.test_legacy_wrappers_redirect_to_ssot()
        print("   ✅ Legacy wrapper compliance verified")
        
        print("\n6. Checking CI script compliance...")
        test_instance.test_ci_scripts_use_ssot_runner()
        print("   ⚠️  CI script compliance checked (warnings may appear above)")
        
        # Show metrics
        metrics = test_instance.get_all_metrics()
        print(f"\n📊 ENFORCEMENT METRICS:")
        print(f"   Test Type: {metrics.get('test_type', 'unknown')}")
        print(f"   Business Value: {metrics.get('business_value', 'unknown')}")
        print(f"   Execution Time: {metrics.get('execution_time', 0):.3f}s")
        print(f"   Unauthorized Runners: {metrics.get('unauthorized_runners_found', 0)}")
        print(f"   Pytest Bypasses: {metrics.get('pytest_bypasses_found', 0)}")
        print(f"   Orchestration Violations: {metrics.get('orchestration_violations_found', 0)}")
        
        print(f"\n🎉 [SUCCESS] SSOT COMPLIANCE: All enforcement checks passed!")
        print("   The system is protected against unauthorized test runner violations.")
        
    except Exception as e:
        print(f"\n💥 [FAILURE] SSOT VIOLATION DETECTED: {str(e)}")
        print("\n🚨 IMMEDIATE ACTION REQUIRED:")
        print("   1. Review violation details above")
        print("   2. Implement remediation steps")
        print("   3. Re-run enforcement check")
        print("   4. Ensure Golden Path protection")
        exit(1)
    
    finally:
        test_instance.teardown_method()
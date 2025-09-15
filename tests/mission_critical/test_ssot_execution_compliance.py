#!/usr/bin/env python3
"""
MISSION CRITICAL: SSOT Test Execution Compliance Validation

CRITICAL MISSION: Detect and prevent fragmented test execution patterns that bypass
the unified test runner and violate SSOT testing infrastructure.

BUSINESS VALUE: Protects $500K+ ARR Golden Path functionality by ensuring all tests
follow SSOT patterns and preventing test infrastructure fragmentation.

TARGET VIOLATIONS:
1. test_plans/rollback/test_emergency_rollback_validation.py (bypassing unified_test_runner.py)
2. test_plans/phase5/test_golden_path_protection_validation.py (bypassing unified_test_runner.py)
3. test_plans/phase3/test_critical_configuration_drift_detection.py (bypassing unified_test_runner.py)

SSOT REQUIREMENTS ENFORCED:
- ALL test execution must go through tests/unified_test_runner.py
- ALL tests must inherit from SSOT BaseTestCase
- NO direct pytest execution allowed in production test files
- NO fragmented test execution patterns outside unified infrastructure

PURPOSE: These tests MUST FAIL initially to detect current SSOT violations,
then pass after remediation to protect ongoing SSOT compliance.
"""

import sys
import subprocess
import ast
import inspect
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Import SSOT test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase

@dataclass
class SSOTViolation:
    """SSOT violation detected in test file."""
    file_path: str
    violation_type: str
    description: str
    line_number: Optional[int] = None
    severity: str = "HIGH"

class TestSSOTExecutionCompliance(SSotBaseTestCase):
    """
    MISSION CRITICAL: Test SSOT execution compliance across all test files.
    
    This test suite MUST detect violations where test files bypass the unified
    test runner or use non-SSOT patterns, protecting the $500K+ ARR Golden Path.
    """
    
    def setup_method(self, method):
        """Setup for SSOT execution compliance testing."""
        super().setup_method(method)
        self.violations: List[SSOTViolation] = []
        self.known_violating_files = [
            "test_plans/rollback/test_emergency_rollback_validation.py",
            "test_plans/phase5/test_golden_path_protection_validation.py", 
            "test_plans/phase3/test_critical_configuration_drift_detection.py"
        ]
    
    def test_no_direct_pytest_main_execution_in_test_files(self):
        """
        CRITICAL: Test files must NOT execute # MIGRATED: Use SSOT unified test runner
    # python tests/unified_test_runner.py --category unit
    pass  # TODO: Replace with appropriate SSOT test execution directly.
        
        This bypasses the unified test runner and violates SSOT execution patterns.
        ALL test execution must go through tests/unified_test_runner.py.
        """
        violations = self._scan_for_direct_pytest_execution()
        
        # These specific files are known violators - this test MUST detect them
        expected_violators = set(self.known_violating_files)
        detected_violators = {v.file_path for v in violations if "pytest.main" in v.description}
        
        # Assert that we detect the known violations
        missing_detections = expected_violators - detected_violators
        assert not missing_detections, (
            f"CRITICAL FAILURE: Failed to detect known SSOT violations: {missing_detections}. "
            f"The SSOT compliance detection system is not working correctly."
        )
        
        # This test SHOULD FAIL initially because violations exist
        if violations:
            violation_details = "\n".join([
                f"  - {v.file_path}:{v.line_number} - {v.description}"
                for v in violations
            ])
            assert False, (
                f"SSOT VIOLATION DETECTED: {len(violations)} files bypass unified test runner:\n"
                f"{violation_details}\n\n"
                f"REMEDIATION REQUIRED:\n"
                f"1. Remove direct test execution calls from test files\n"
                f"2. Execute tests through: python tests/unified_test_runner.py\n"
                f"3. Use SSOT test execution patterns only\n\n"
                f"BUSINESS IMPACT: Fragmented test execution threatens $500K+ ARR Golden Path stability"
            )
    
    def test_all_test_classes_inherit_from_ssot_base_test_case(self):
        """
        CRITICAL: All test classes must inherit from SSOT BaseTestCase.
        
        This ensures consistent test infrastructure and prevents test duplication.
        """
        violations = self._scan_for_non_ssot_test_inheritance()
        
        # Check that we detect inheritance violations in known files
        inheritance_violations = [v for v in violations if "BaseTestCase" not in v.description or "SSOT" not in v.description]
        
        if inheritance_violations:
            violation_details = "\n".join([
                f"  - {v.file_path}:{v.line_number} - {v.description}"
                for v in inheritance_violations
            ])
            assert False, (
                f"SSOT INHERITANCE VIOLATION: {len(inheritance_violations)} test classes don't use SSOT BaseTestCase:\n"
                f"{violation_details}\n\n"
                f"REMEDIATION REQUIRED:\n"
                f"1. Import: from test_framework.ssot.base_test_case import SSotBaseTestCase\n"
                f"2. Change: class MyTest(unittest.TestCase) → class MyTest(SSotBaseTestCase)\n"
                f"3. Update setUp/tearDown to setup_method/teardown_method patterns\n\n"
                f"BUSINESS IMPACT: Non-SSOT test patterns create infrastructure debt and instability"
            )
    
    def test_no_fragmented_test_execution_patterns(self):
        """
        CRITICAL: Detect fragmented test execution patterns that bypass SSOT infrastructure.
        
        Includes direct subprocess calls to pytest, standalone test runners, etc.
        """
        violations = self._scan_for_fragmented_execution_patterns()
        
        if violations:
            violation_details = "\n".join([
                f"  - {v.file_path}:{v.line_number} - {v.description}"
                for v in violations
            ])
            assert False, (
                f"FRAGMENTED EXECUTION DETECTED: {len(violations)} files use non-SSOT execution:\n"
                f"{violation_details}\n\n"
                f"REMEDIATION REQUIRED:\n"
                f"1. Remove direct subprocess calls to pytest\n"
                f"2. Remove standalone test execution patterns\n"
                f"3. Use unified_test_runner.py for ALL test execution\n\n"
                f"BUSINESS IMPACT: Fragmented execution prevents proper test orchestration and monitoring"
            )
    
    def test_unified_test_runner_is_canonical_entry_point(self):
        """
        CRITICAL: Verify unified_test_runner.py is the canonical test execution entry point.
        
        No other test runners should exist that bypass this SSOT infrastructure.
        """
        canonical_runner = PROJECT_ROOT / "tests" / "unified_test_runner.py"
        
        # Verify canonical runner exists and is functional
        assert canonical_runner.exists(), (
            f"CRITICAL: Canonical test runner missing: {canonical_runner}"
        )
        
        # Scan for other test runners that might bypass SSOT
        alternative_runners = self._scan_for_alternative_test_runners()
        
        if alternative_runners:
            runner_details = "\n".join([
                f"  - {runner.file_path} - {runner.description}"
                for runner in alternative_runners
            ])
            assert False, (
                f"ALTERNATIVE TEST RUNNERS DETECTED: {len(alternative_runners)} files bypass canonical runner:\n"
                f"{runner_details}\n\n"
                f"REMEDIATION REQUIRED:\n"
                f"1. Consolidate all test execution through tests/unified_test_runner.py\n"
                f"2. Remove or refactor alternative test runners\n"
                f"3. Update CI/CD to use canonical runner only\n\n"
                f"BUSINESS IMPACT: Multiple test runners create inconsistent test execution and reporting"
            )
    
    def test_detect_specific_known_violating_files(self):
        """
        CRITICAL: Explicitly test detection of the 3 specific files identified in Issue #1145.
        
        This ensures our detection system works correctly for the actual violations.
        """
        for file_path in self.known_violating_files:
            full_path = PROJECT_ROOT / file_path
            
            # Verify file exists
            assert full_path.exists(), f"Known violating file not found: {file_path}"
            
            # Verify we can detect violations in this specific file
            file_violations = self._analyze_single_file_for_violations(full_path)
            
            assert file_violations, (
                f"DETECTION FAILURE: No SSOT violations detected in known violator: {file_path}\n"
                f"This indicates the compliance detection system is not working correctly."
            )
    
    def _scan_for_direct_pytest_execution(self) -> List[SSOTViolation]:
        """Scan for files that execute # MIGRATED: Use SSOT unified test runner
    # python tests/unified_test_runner.py --category unit
    pass  # TODO: Replace with appropriate SSOT test execution directly."""
        violations = []
        
        for test_file in self._find_test_files():
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    if 'pytest.main(' in line:
                        pass  # REMOVED_SYNTAX_ERROR: violations.append block
                        # REMOVED_SYNTAX_ERROR: "file": str(file_path.relative_to(self.project_root)),
                            "line": line_num,
                            "violation_type": "DIRECT_PYTEST_EXECUTION",
                            "description": "Direct pytest.main execution bypasses unified test runner",
                            "line_number": line_num,
                            "severity": "CRITICAL"
                        ))
                        
            except Exception as e:
                # Log but don't fail on file reading errors
                print(f"Warning: Could not analyze {test_file}: {e}")
        
        return violations
    
    def _scan_for_non_ssot_test_inheritance(self) -> List[SSOTViolation]:
        """Scan for test classes that don't inherit from SSOT BaseTestCase."""
        violations = []
        
        for test_file in self._find_test_files():
            try:
                violations.extend(self._analyze_single_file_for_violations(test_file))
            except Exception as e:
                print(f"Warning: Could not analyze {test_file}: {e}")
        
        return violations
    
    def _analyze_single_file_for_violations(self, test_file: Path) -> List[SSOTViolation]:
        """Analyze a single file for SSOT violations."""
        violations = []
        
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the AST to find class definitions
            try:
                tree = ast.parse(content)
            except SyntaxError:
                return violations  # Skip files with syntax errors
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if this is a test class (starts with Test or contains test methods)
                    if (node.name.startswith('Test') or 
                        any(method.name.startswith('test_') for method in node.body 
                            if isinstance(method, ast.FunctionDef))):
                        
                        # Check inheritance
                        base_names = []
                        for base in node.bases:
                            if isinstance(base, ast.Name):
                                base_names.append(base.id)
                            elif isinstance(base, ast.Attribute):
                                # Handle module.ClassName patterns
                                base_names.append(f"{base.attr}")
                        
                        # Check for SSOT compliance
                        has_ssot_inheritance = any(
                            'SSot' in base or 'SSOT' in base 
                            for base in base_names
                        )
                        
                        if not has_ssot_inheritance and base_names:
                            violations.append(SSOTViolation(
                                file_path=str(test_file.relative_to(PROJECT_ROOT)),
                                violation_type="NON_SSOT_INHERITANCE",
                                description=f"Test class '{node.name}' inherits from {base_names} instead of SSOT BaseTestCase",
                                line_number=node.lineno,
                                severity="HIGH"
                            ))
        
        except Exception as e:
            print(f"Warning: Could not parse {test_file}: {e}")
        
        return violations
    
    def _scan_for_fragmented_execution_patterns(self) -> List[SSOTViolation]:
        """Scan for fragmented test execution patterns."""
        violations = []
        
        fragmented_patterns = [
            ('subprocess.*pytest', 'Direct subprocess call to pytest'),
            ('os.system.*pytest', 'Direct os.system call to pytest'),
            ('unittest.main()', 'Direct unittest.main() execution'),
            ('pytest.main.*__file__', 'Direct pytest execution of current file')
        ]
        
        for test_file in self._find_test_files():
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    for pattern, description in fragmented_patterns:
                        import re
                        if re.search(pattern, line):
                            violations.append(SSOTViolation(
                                file_path=str(test_file.relative_to(PROJECT_ROOT)),
                                violation_type="FRAGMENTED_EXECUTION",
                                description=description,
                                line_number=line_num,
                                severity="HIGH"
                            ))
                            
            except Exception as e:
                print(f"Warning: Could not analyze {test_file}: {e}")
        
        return violations
    
    def _scan_for_alternative_test_runners(self) -> List[SSOTViolation]:
        """Scan for alternative test runners that bypass unified infrastructure."""
        violations = []
        
        # Look for Python files that might be alternative test runners
        for py_file in PROJECT_ROOT.rglob("*.py"):
            if py_file.name == "unified_test_runner.py":
                continue  # Skip the canonical runner
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for test runner patterns
                runner_patterns = [
                    '# MIGRATED: Use SSOT unified test runner
    # python tests/unified_test_runner.py --category unit
    pass  # TODO: Replace with appropriate SSOT test execution:
                    # Check if this is actually a test runner (not just a test file)
                    if ('test_runner' in py_file.name.lower() or 
                        'run_test' in py_file.name.lower() or
                        (__name__ == "__main__" in content and len(content.split('\n')) > 50)):
                        
                        violations.append(SSOTViolation(
                            file_path=str(py_file.relative_to(PROJECT_ROOT)),
                            violation_type="ALTERNATIVE_TEST_RUNNER",
                            description=f"Alternative test runner found: {py_file.name}",
                            severity="MEDIUM"
                        ))
                        
            except Exception as e:
                print(f"Warning: Could not analyze {py_file}: {e}")
        
        return violations
    
    def _find_test_files(self) -> List[Path]:
        """Find all test files in the project."""
        test_files = []
        
        # Look in common test directories
        test_dirs = [
            PROJECT_ROOT / "tests",
            PROJECT_ROOT / "test_plans", 
            PROJECT_ROOT / "netra_backend" / "tests",
            PROJECT_ROOT / "auth_service" / "tests",
            PROJECT_ROOT / "frontend" / "tests",
            PROJECT_ROOT / "test_framework" / "tests"
        ]
        
        for test_dir in test_dirs:
            if test_dir.exists():
                test_files.extend(test_dir.rglob("test_*.py"))
                test_files.extend(test_dir.rglob("*_test.py"))
        
        return test_files

if __name__ == "__main__":
    # MIGRATED: Use SSOT unified test runner instead of direct pytest execution
    # Issue #1024: Unauthorized test runners blocking Golden Path
    print("MIGRATION NOTICE: This file previously used direct pytest execution.")
    print("Please use: python tests/unified_test_runner.py --category <appropriate_category>")
    print("For more info: reports/TEST_EXECUTION_GUIDE.md")

    # Uncomment and customize the following for SSOT execution:
    # result = run_tests_via_ssot_runner()
    # sys.exit(result)
    pass  # TODO: Replace with appropriate SSOT test execution
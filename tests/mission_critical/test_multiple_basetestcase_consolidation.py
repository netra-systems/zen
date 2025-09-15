#!/usr/bin/env python3
"""
Mission Critical Test Suite: Multiple BaseTestCase Inheritance Violation Reproduction - Issue #1075

Business Value: Platform/Internal - Test Infrastructure SSOT Compliance  
Critical for $500K+ ARR protection through unified test base class patterns and consistent testing infrastructure.

This test reproduces the critical violation where 1343+ test files have fragmented BaseTestCase 
inheritance patterns, compromising test infrastructure consistency and SSOT compliance.

VIOLATION BEING REPRODUCED:
- Multiple BaseTestCase implementations across the codebase
- Fragmented test infrastructure with competing base classes
- Inconsistent test setup/teardown patterns
- Environment isolation not properly inherited

EXPECTED BEHAVIOR AFTER REMEDIATION:
- Single SSOT BaseTestCase (SSotBaseTestCase) used by all tests
- Consistent test infrastructure patterns across all test files
- Proper environment isolation and metrics recording
- Unified setup/teardown behavior

Author: SSOT Gardener Agent - Issue #1075 Step 1
Date: 2025-09-14
"""

import ast
import os
import sys
import subprocess
import importlib
from pathlib import Path
from typing import List, Dict, Set, Any, Optional, Tuple, Union
from dataclasses import dataclass
import pytest
import inspect

# Test framework imports (following SSOT patterns)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment


@dataclass
class BaseTestCaseViolation:
    """Details about a multiple BaseTestCase inheritance violation."""
    file_path: str
    line_number: int
    class_name: str
    base_class: str
    violation_type: str  # 'multiple_inheritance', 'wrong_base_class', 'no_base_class', 'custom_base_class'
    inheritance_chain: List[str]


class MultipleBaseTestCaseConsolidationTests(SSotBaseTestCase):
    """
    Test suite to reproduce and validate multiple BaseTestCase inheritance violations.
    
    This test is DESIGNED TO FAIL until SSOT BaseTestCase consolidation is complete,
    demonstrating the fragmentation of test base classes across the codebase.
    """

    def setUp(self):
        super().setUp()
        self.project_root = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
        self.violations_found: List[BaseTestCaseViolation] = []
        self.test_directories = [
            'tests',
            'netra_backend/tests', 
            'auth_service/tests',
            'test_framework/tests',
            'shared/tests'
        ]
        self.ssot_base_classes = {
            'SSotBaseTestCase',
            'SSotAsyncTestCase'
        }
        self.legacy_base_classes = {
            'TestCase',
            'unittest.TestCase',
            'AsyncTestCase', 
            'BaseTestCase',
            'IsolatedTestCase',
            'WebSocketTestCase',
            'IntegrationTestCase',
            'DatabaseTestCase'
        }

    def scan_file_for_basetestcase_violations(self, file_path: Path) -> List[BaseTestCaseViolation]:
        """
        Scan a Python file for multiple BaseTestCase inheritance violations.
        
        Detects:
        1. Classes inheriting from multiple BaseTestCase variants
        2. Classes using wrong base class (not SSOT)  
        3. Test classes with no proper base class
        4. Custom base classes that should use SSOT
        """
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse AST for class analysis
            try:
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_name = node.name
                        
                        # Skip non-test classes
                        if not (class_name.startswith('Test') or 
                                class_name.endswith('Test') or
                                class_name.endswith('TestCase') or
                                'test' in class_name.lower()):
                            continue
                            
                        # Analyze inheritance
                        base_classes = []
                        inheritance_chain = []
                        
                        for base in node.bases:
                            base_name = self.extract_base_class_name(base)
                            if base_name:
                                base_classes.append(base_name)
                                inheritance_chain.append(base_name)
                        
                        # Detect violations
                        violation = self.analyze_inheritance_violations(
                            file_path, node.lineno, class_name, 
                            base_classes, inheritance_chain
                        )
                        
                        if violation:
                            violations.append(violation)
                            
            except SyntaxError as e:
                # Create violation for unparseable files
                violation = BaseTestCaseViolation(
                    file_path=str(file_path.relative_to(self.project_root)),
                    line_number=1,
                    class_name="SYNTAX_ERROR",
                    base_class="UNPARSEABLE",
                    violation_type="syntax_error",
                    inheritance_chain=[]
                )
                violations.append(violation)
                
        except Exception as e:
            # Log but don't fail on individual file errors
            print(f"Warning: Could not scan {file_path}: {e}")
            
        return violations

    def extract_base_class_name(self, base_node: ast.AST) -> Optional[str]:
        """Extract base class name from AST node."""
        if isinstance(base_node, ast.Name):
            return base_node.id
        elif isinstance(base_node, ast.Attribute):
            # Handle qualified names like unittest.TestCase
            value = base_node.value
            if isinstance(value, ast.Name):
                return f"{value.id}.{base_node.attr}"
        return None

    def analyze_inheritance_violations(self, file_path: Path, line_number: int, 
                                     class_name: str, base_classes: List[str],
                                     inheritance_chain: List[str]) -> Optional[BaseTestCaseViolation]:
        """Analyze inheritance pattern and detect violations."""
        
        if not base_classes:
            # Test class with no base class
            return BaseTestCaseViolation(
                file_path=str(file_path.relative_to(self.project_root)),
                line_number=line_number,
                class_name=class_name,
                base_class="NONE",
                violation_type="no_base_class",
                inheritance_chain=inheritance_chain
            )
        
        # Check for SSOT compliance
        ssot_bases = [bc for bc in base_classes if bc in self.ssot_base_classes]
        legacy_bases = [bc for bc in base_classes if bc in self.legacy_base_classes]
        
        if not ssot_bases and legacy_bases:
            # Using legacy base class instead of SSOT
            return BaseTestCaseViolation(
                file_path=str(file_path.relative_to(self.project_root)),
                line_number=line_number,
                class_name=class_name,
                base_class=legacy_bases[0],
                violation_type="wrong_base_class",
                inheritance_chain=inheritance_chain
            )
        
        if len(base_classes) > 1:
            # Multiple inheritance (potentially problematic)
            return BaseTestCaseViolation(
                file_path=str(file_path.relative_to(self.project_root)),
                line_number=line_number,
                class_name=class_name,
                base_class=", ".join(base_classes),
                violation_type="multiple_inheritance",
                inheritance_chain=inheritance_chain
            )
            
        # Check for custom base classes that should use SSOT
        if base_classes and not ssot_bases and not legacy_bases:
            custom_base = base_classes[0]
            if 'Base' in custom_base or 'Test' in custom_base:
                return BaseTestCaseViolation(
                    file_path=str(file_path.relative_to(self.project_root)),
                    line_number=line_number,
                    class_name=class_name,
                    base_class=custom_base,
                    violation_type="custom_base_class",
                    inheritance_chain=inheritance_chain
                )
        
        return None

    def scan_codebase_for_basetestcase_violations(self) -> List[BaseTestCaseViolation]:
        """Scan entire codebase for BaseTestCase inheritance violations."""
        all_violations = []
        
        for test_dir in self.test_directories:
            test_path = self.project_root / test_dir
            if not test_path.exists():
                continue
                
            # Scan all Python test files
            for py_file in test_path.rglob('test_*.py'):
                # Skip __pycache__ and similar
                if '__pycache__' in str(py_file) or '.git' in str(py_file):
                    continue
                    
                violations = self.scan_file_for_basetestcase_violations(py_file)
                all_violations.extend(violations)
                
            # Also scan files with Test in the name
            for py_file in test_path.rglob('*Test*.py'):
                if '__pycache__' in str(py_file) or '.git' in str(py_file):
                    continue
                if py_file.name.startswith('test_'):
                    continue  # Already scanned above
                    
                violations = self.scan_file_for_basetestcase_violations(py_file)
                all_violations.extend(violations)
                
        return all_violations

    def validate_ssot_base_test_case_functionality(self) -> Dict[str, Any]:
        """
        Validate that the SSOT BaseTestCase exists and provides required functionality.
        This should PASS even before remediation.
        """
        validation_results = {
            'exists': False,
            'importable': False,
            'has_setup': False,
            'has_teardown': False,
            'has_environment_isolation': False,
            'has_metrics_recording': False,
            'functionality_score': 0
        }
        
        try:
            # Check if SSOT base test case exists and is importable
            from test_framework.ssot.base_test_case import SSotBaseTestCase
            validation_results['exists'] = True
            validation_results['importable'] = True
            
            # Check for required methods
            if hasattr(SSotBaseTestCase, 'setUp'):
                validation_results['has_setup'] = True
                validation_results['functionality_score'] += 1
                
            if hasattr(SSotBaseTestCase, 'tearDown'):
                validation_results['has_teardown'] = True
                validation_results['functionality_score'] += 1
                
            # Check for environment isolation
            if hasattr(SSotBaseTestCase, '_test_env_manager') or hasattr(SSotBaseTestCase, 'isolated_env'):
                validation_results['has_environment_isolation'] = True
                validation_results['functionality_score'] += 1
                
            # Check for metrics recording
            if (hasattr(SSotBaseTestCase, '_record_test_metrics') or 
                hasattr(SSotBaseTestCase, 'test_metrics') or
                'metric' in str(SSotBaseTestCase.__dict__).lower()):
                validation_results['has_metrics_recording'] = True
                validation_results['functionality_score'] += 1
                
        except ImportError:
            pass
            
        return validation_results

    def test_reproduce_multiple_basetestcase_violations(self):
        """
        REPRODUCTION TEST: This test WILL FAIL until violations are remediated.
        
        Scans codebase and identifies all test files with fragmented BaseTestCase 
        inheritance patterns instead of using SSOT BaseTestCase.
        """
        violations = self.scan_codebase_for_basetestcase_violations()
        self.violations_found = violations
        
        # Generate detailed violation report
        violation_report = self.generate_violation_report(violations)
        print("\n" + "="*80)
        print("MULTIPLE BASETESTCASE VIOLATION REPRODUCTION RESULTS")
        print("="*80)
        print(violation_report)
        
        # This assertion SHOULD FAIL until remediation is complete
        self.assertEqual(
            len(violations), 0, 
            f"CRITICAL VIOLATION REPRODUCED: Found {len(violations)} BaseTestCase inheritance violations. "
            f"All test classes should inherit from SSOT BaseTestCase (SSotBaseTestCase). "
            f"Violations found in: {[v.file_path for v in violations[:10]]}{'...' if len(violations) > 10 else ''}"
        )

    def test_validate_ssot_base_test_case_functionality(self):
        """
        VALIDATION TEST: This test should PASS both before and after remediation.
        
        Validates that the SSOT BaseTestCase exists and provides required functionality.
        """
        validation_results = self.validate_ssot_base_test_case_functionality()
        
        self.assertTrue(
            validation_results['exists'] and validation_results['importable'],
            "CRITICAL: SSOT BaseTestCase (SSotBaseTestCase) must exist and be importable. "
            "This is the canonical base class for all tests in the system."
        )
        
        self.assertGreater(
            validation_results['functionality_score'], 2,
            f"SSOT BaseTestCase must provide core functionality. "
            f"Score: {validation_results['functionality_score']}/4. "
            f"Missing: {[k for k, v in validation_results.items() if k.startswith('has_') and not v]}"
        )

    def test_basetestcase_environment_isolation_compliance(self):
        """
        COMPLIANCE TEST: Validates that SSOT BaseTestCase provides proper environment isolation.
        
        This test should PASS - it validates the SSOT base class functionality.
        """
        # Validate that this test class (which inherits from SSOT) has isolation
        self.assertIsNotNone(
            getattr(self, '_test_env_manager', None) or getattr(self, 'isolated_env', None),
            "SSOT BaseTestCase must provide environment isolation for multi-user system safety"
        )
        
        # Validate that environment isolation is properly configured
        env_manager = IsolatedEnvironment()
        self.assertIsNotNone(env_manager, "Environment isolation must be available")

    def generate_violation_report(self, violations: List[BaseTestCaseViolation]) -> str:
        """Generate detailed report of BaseTestCase inheritance violations."""
        if not violations:
            return "✅ NO VIOLATIONS FOUND - All test classes use SSOT BaseTestCase patterns"
            
        report_lines = [
            f"🚨 CRITICAL VIOLATIONS FOUND: {len(violations)} BaseTestCase inheritance violations",
            "",
            "VIOLATION BREAKDOWN BY TYPE:"
        ]
        
        # Group by violation type
        by_type = {}
        for violation in violations:
            if violation.violation_type not in by_type:
                by_type[violation.violation_type] = []
            by_type[violation.violation_type].append(violation)
            
        for violation_type, type_violations in by_type.items():
            report_lines.append(f"  {violation_type}: {len(type_violations)} violations")
            
        # Group by base class
        by_base_class = {}
        for violation in violations:
            base_class = violation.base_class
            if base_class not in by_base_class:
                by_base_class[base_class] = []
            by_base_class[base_class].append(violation)
            
        report_lines.extend([
            "",
            "VIOLATION BREAKDOWN BY BASE CLASS:"
        ])
        
        for base_class, base_violations in sorted(by_base_class.items(), 
                                                  key=lambda x: len(x[1]), reverse=True):
            report_lines.append(f"  {base_class}: {len(base_violations)} violations")
        
        report_lines.extend([
            "",
            "DETAILED VIOLATIONS (first 25):"
        ])
        
        for i, violation in enumerate(violations[:25]):
            report_lines.extend([
                f"  {i+1}. File: {violation.file_path}",
                f"     Line {violation.line_number}: class {violation.class_name}({violation.base_class})",
                f"     Type: {violation.violation_type}",
                f"     Inheritance: {' -> '.join(violation.inheritance_chain) if violation.inheritance_chain else 'None'}",
                ""
            ])
            
        if len(violations) > 25:
            report_lines.append(f"  ... and {len(violations) - 25} more violations")
            
        report_lines.extend([
            "",
            "REMEDIATION REQUIRED:",
            "1. Replace all legacy BaseTestCase inheritance with SSotBaseTestCase",
            "2. Remove custom base class implementations in favor of SSOT pattern",
            "3. Ensure all test classes inherit from SSotBaseTestCase or SSotAsyncTestCase",
            "4. Consolidate test setup/teardown patterns through SSOT base class",
            "5. Maintain consistent environment isolation across all tests"
        ])
        
        return "\n".join(report_lines)

    def tearDown(self):
        """Clean up after test execution."""
        # Log summary for debugging
        if hasattr(self, 'violations_found') and self.violations_found:
            print(f"\nTest completed. Found {len(self.violations_found)} BaseTestCase inheritance violations.")
        super().tearDown()


if __name__ == '__main__':
    # Note: This file should be run through unified_test_runner.py for SSOT compliance
    print("WARNING: This test should be run through unified_test_runner.py for SSOT compliance")
    print("Example: python tests/unified_test_runner.py --file tests/mission_critical/test_multiple_basetestcase_consolidation.py")
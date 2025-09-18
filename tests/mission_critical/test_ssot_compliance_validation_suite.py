#!/usr/bin/env python3
"""
"""
SSOT Compliance Validation Test Suite - Issue #1075 Implementation
Tests designed to FAIL initially and detect the specific SSOT violations identified in the analysis.

CRITICAL BUSINESS IMPACT: These tests protect $500K+ ARR by ensuring SSOT architectural compliance.
Violations detected lead to system instability, development inefficiency, and technical debt accumulation.

Test Implementation Strategy:
1. Unit tests for individual compliance validation (no Docker required)
2. Integration tests for cross-module SSOT issues
3. Tests initially FAIL to prove violations exist
4. Detailed violation reporting with specific counts and locations

SSOT Violations to Detect:
- Production compliance gap: 16.6% between claimed vs actual
"""
"""
- 89 duplicate type definitions across modules
- Test infrastructure fragmentation: -1981.6% compliance
- Configuration manager duplicates
- Authentication service violations
"
"

import os
import sys
import unittest
import importlib.util
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict
import ast
import re

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env


class SsotComplianceViolation:
    "Container for SSOT compliance violations"

    def __init__(self, violation_type: str, location: str, description: str, severity: str = "high):"
        self.violation_type = violation_type
        self.location = location
        self.description = description
        self.severity = severity
        self.metadata = {}

    def __repr__(self):
        return fSsotComplianceViolation(type={self.violation_type), location={self.location), severity={self.severity)


class SsotComplianceValidator:
    Core SSOT compliance validation logic""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.violations = []
        self.production_files = set()
        self.test_files = set()
        self.duplicate_type_definitions = defaultdict(list)
        self.auth_violations = []
        self.config_violations = []

    def scan_project_structure(self) -> None:
        Scan project structure to identify production vs test files""
        for file_path in self.project_root.rglob(*.py):
            relative_path = file_path.relative_to(self.project_root)

            # Skip __pycache__ and .git directories
            if any(part.startswith('.') or part == '__pycache__' for part in relative_path.parts):
                continue

            # Classify as production or test file
            if any(part.startswith('test') for part in relative_path.parts) or 'test_' in file_path.name:
                self.test_files.add(file_path)
            else:
                self.production_files.add(file_path)

    def validate_production_ssot_compliance(self) -> List[SsotComplianceViolation]:
        "
        "
        Validate production SSOT compliance to detect 16.6% gap

        This test is designed to FAIL initially to prove the violations exist.
        Expected violations:
        - Duplicate class definitions across modules
        - Multiple import patterns for same functionality
        - Inconsistent singleton vs factory patterns
"
"
        violations = []

        # Track duplicate class definitions
        class_definitions = defaultdict(list)
        import_patterns = defaultdict(set)

        for file_path in self.production_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)

                    # Check for class definitions
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            class_definitions[node.name].append(str(file_path))

                        elif isinstance(node, ast.Import):
                            for alias in node.names:
                                import_patterns[alias.name].add(str(file_path))

                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                import_patterns[node.module].add(str(file_path))

            except Exception as e:
                # Add violation for unparseable files
                violations.append(SsotComplianceViolation(
                    violation_type=parse_error,"
                    violation_type=parse_error,"
                    location=str(file_path),
                    description=fUnable to parse production file: {e}","
                    severity=critical
                ))

        # Detect duplicate class definitions (should find 89+ violations)
        for class_name, locations in class_definitions.items():
            if len(locations) > 1:
                # Filter out obvious test-related duplicates
                production_locations = [loc for loc in locations if 'test' not in loc.lower()]
                if len(production_locations) > 1:
                    violations.append(SsotComplianceViolation(
                        violation_type=duplicate_class_definition","
                        location=, .join(production_locations),
                        description=fClass '{class_name}' defined in multiple production locations: {production_locations},"
                        description=fClass '{class_name}' defined in multiple production locations: {production_locations},"
                        severity="high"
                    ))

        # Detect SSOT pattern violations
        ssot_patterns = [
            BaseTestCase, MockFactory, ConfigManager", "DatabaseManager,
            WebSocketManager, AuthService, ExecutionEngine"
            WebSocketManager, AuthService, ExecutionEngine"
        ]

        for pattern in ssot_patterns:
            matching_classes = [name for name in class_definitions.keys() if pattern in name]
            if len(matching_classes) > 1:
                violations.append(SsotComplianceViolation(
                    violation_type="ssot_pattern_violation,"
                    location=Multiple files,
                    description=f"Multiple implementations of SSOT pattern '{pattern}': {matching_classes},"
                    severity=critical"
                    severity=critical"
                ))

        return violations

    def validate_duplicate_type_definitions(self) -> List[SsotComplianceViolation]:
    "
    "
        Detect 89 duplicate type definitions identified in the analysis

        This test should FAIL initially and report specific duplicates including:
        - Multiple BaseTestCase implementations
        - Duplicate configuration classes
        - Multiple agent registry implementations
        "
        "
        violations = []
        type_definitions = defaultdict(list)

        # Known SSOT violation patterns to specifically detect
        critical_duplicates = [
            BaseTestCase, AsyncTestCase, MockFactory", "ConfigManager,
            DatabaseManager, WebSocketManager, AgentRegistry, "AuthService,"
            ExecutionEngine", UserExecutionContext, TestMetrics"
        ]

        for file_path in self.production_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)

                    # Check for type definitions (classes, TypedDict, Enum, etc.)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            type_definitions[node.name).append({
                                'file': str(file_path),
                                'line': node.lineno,
                                'type': 'class'
                            }

                        elif isinstance(node, ast.AnnAssign) and hasattr(node.target, 'id'):
                            # Type aliases
                            type_definitions[node.target.id).append({
                                'file': str(file_path),
                                'line': node.lineno,
                                'type': 'type_alias'
                            }

            except Exception:
                continue  # Skip unparseable files for this analysis

        # Report duplicate type definitions
        for type_name, definitions in type_definitions.items():
            if len(definitions) > 1:
                # Filter to production files only
                prod_definitions = [d for d in definitions if 'test' not in d['file'].lower()]

                if len(prod_definitions) > 1:
                    locations = [f"{d['file']}:{d['line']} for d in prod_definitions]"

                    severity = critical" if type_name in critical_duplicates else high"

                    violations.append(SsotComplianceViolation(
                        violation_type=duplicate_type_definition,
                        location="; .join(locations),"
                        description=fType '{type_name}' defined in {len(prod_definitions)} production locations,
                        severity=severity
                    ))

        return violations

    def validate_test_infrastructure_compliance(self) -> List[SsotComplianceViolation]:
    ""
        Detect test infrastructure fragmentation leading to -1981.6% compliance

        This test should FAIL initially and report:
        - Multiple test base classes
        - Inconsistent test utilities
        - Direct pytest usage bypassing SSOT unified test runner
        
        violations = []

        # Track test infrastructure patterns
        test_base_classes = defaultdict(list)
        direct_pytest_usage = []
        mock_implementations = defaultdict(list)

        for file_path in self.test_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)

                    # Check for test base class definitions
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            if any(keyword in node.name for keyword in ['Test', 'Base', 'Mock'):
                                if 'TestCase' in node.name or 'Base' in node.name:
                                    test_base_classes[node.name].append(str(file_path))
                                elif 'Mock' in node.name:
                                    mock_implementations[node.name].append(str(file_path))

                        elif isinstance(node, ast.Import):
                            for alias in node.names:
                                if alias.name == 'pytest':
                                    direct_pytest_usage.append(str(file_path))

            except Exception:
                continue

        # Detect multiple test base class implementations (should find 6,96+ violations)
        for class_name, locations in test_base_classes.items():
            if len(locations) > 1:
                violations.append(SsotComplianceViolation(
                    violation_type=duplicate_test_base_class,"
                    violation_type=duplicate_test_base_class,"
                    location="; .join(locations),"
                    description=fTest base class '{class_name}' implemented in {len(locations)} files (violates SSOT),
                    severity="critical"
                ))

        # Detect multiple mock implementations
        for mock_name, locations in mock_implementations.items():
            if len(locations) > 1:
                violations.append(SsotComplianceViolation(
                    violation_type=duplicate_mock_implementation,
                    location=; .join(locations),"
                    location=; .join(locations),"
                    description=fMock class '{mock_name}' implemented in {len(locations)} files (violates SSOT)","
                    severity=high
                ))

        # Detect direct pytest usage (should use unified test runner)
        for file_path in direct_pytest_usage:
            violations.append(SsotComplianceViolation(
                violation_type=direct_pytest_usage","
                location=file_path,
                description=Direct pytest import detected (should use unified test runner),
                severity=medium"
                severity=medium"
            ))

        return violations

    def validate_auth_service_ssot_compliance(self) -> List[SsotComplianceViolation]:
    "
    "
        Validate auth service SSOT compliance

        Expected violations:
        - Multiple JWT handlers
        - Duplicate authentication logic
        - Backend auth integration violations
        "
        "
        violations = []

        auth_patterns = [
            JWTHandler", TokenValidator, AuthService, SessionManager,"
            Authenticator", "AuthMiddleware
        ]

        auth_implementations = defaultdict(list)

        # Scan auth service and backend auth integration files
        auth_paths = [
            self.project_root / auth_service,
            self.project_root / netra_backend / app" / "auth_integration
        ]

        for auth_path in auth_paths:
            if auth_path.exists():
                for file_path in auth_path.rglob(*.py):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            tree = ast.parse(content)

                            for node in ast.walk(tree):
                                if isinstance(node, ast.ClassDef):
                                    for pattern in auth_patterns:
                                        if pattern in node.name:
                                            auth_implementations[pattern].append(str(file_path))

                    except Exception:
                        continue

        # Report auth SSOT violations
        for pattern, implementations in auth_implementations.items():
            if len(implementations) > 1:
                violations.append(SsotComplianceViolation(
                    violation_type="auth_ssot_violation,"
                    location=; .join(implementations),
                    description=fMultiple implementations of auth pattern '{pattern}' violate SSOT principle,
                    severity=critical""
                ))

        return violations

    def run_all_validations(self) -> Dict[str, List[SsotComplianceViolation]]:
        Run all SSOT compliance validations"
        Run all SSOT compliance validations"
        self.scan_project_structure()

        results = {
            'production_compliance': self.validate_production_ssot_compliance(),
            'duplicate_types': self.validate_duplicate_type_definitions(),
            'test_infrastructure': self.validate_test_infrastructure_compliance(),
            'auth_service': self.validate_auth_service_ssot_compliance()
        }

        return results


class TestSsotComplianceValidationSuite(SSotBaseTestCase):
    "
    "
    SSOT Compliance Validation Test Suite

    These tests are designed to FAIL initially and detect specific SSOT violations.
    Business Value: Protects $500K+ ARR by ensuring architectural compliance.
"
"

    @classmethod
    def setup_class(cls):
        "Setup class-level resources"
        super().setup_class()
        cls.project_root = PROJECT_ROOT
        cls.validator = SsotComplianceValidator(cls.project_root)

    def test_unit_production_ssot_compliance_gap_detection(self):
        ""
        Unit Test: Detect 16.6% production SSOT compliance gap

        This test is designed to FAIL initially to prove the violations exist.
        Expected: 50+ violations in production code

        self.record_metric("test_type, unit")
        self.record_metric(expected_outcome, FAIL - prove violations exist)

        violations = self.validator.validate_production_ssot_compliance()

        # Record detailed metrics
        self.record_metric(total_violations, len(violations))"
        self.record_metric(total_violations, len(violations))"
        self.record_metric(critical_violations", len([v for v in violations if v.severity == critical])"
        self.record_metric(high_violations, len([v for v in violations if v.severity == high])

        # Log violations for analysis
        if violations:
            print(f\n=== PRODUCTION SSOT VIOLATIONS DETECTED ({len(violations)} total) ===")"
            for i, violation in enumerate(violations[:10):  # Show first 10
                print(f{i+1}. {violation.violation_type}: {violation.description})
                print(f   Location: {violation.location}")"
                print(f   Severity: {violation.severity})
                print()

        # This assertion should FAIL initially to prove violations exist
        self.assertGreater(
            len(violations), 20,  # Expect significant violations
            fExpected 20+ production SSOT violations but found {len(violations)}. "
            fExpected 20+ production SSOT violations but found {len(violations)}. "
            f"If this passes, the violations may have been fixed or test is incorrect."
        )

        # Specific violation type checks
        violation_types = [v.violation_type for v in violations]
        self.assertIn(duplicate_class_definition, violation_types,
                     Expected duplicate class definition violations)"
                     Expected duplicate class definition violations)"
        self.assertIn(ssot_pattern_violation", violation_types,"
                     Expected SSOT pattern violations)

    def test_unit_duplicate_type_definitions_detection(self):
        ""
        Unit Test: Detect 89 duplicate type definitions

        This test should FAIL initially and report specific duplicates.
        Expected: 89+ duplicate type definitions across modules

        self.record_metric("test_type, unit")
        self.record_metric(expected_duplicate_count, 89)

        violations = self.validator.validate_duplicate_type_definitions()

        self.record_metric(detected_duplicates, len(violations))"
        self.record_metric(detected_duplicates, len(violations))"
        self.record_metric("critical_duplicates, len([v for v in violations if v.severity == critical])"

        # Log critical duplicates
        critical_violations = [v for v in violations if v.severity == critical]
        if critical_violations:
            print(f\n=== CRITICAL DUPLICATE TYPE DEFINITIONS ({len(critical_violations)} total) ===")"
            for violation in critical_violations[:5]:  # Show first 5 critical
                print(f- {violation.description})
                print(f  Locations: {violation.location}")"
                print()

        # This assertion should FAIL initially
        self.assertGreater(
            len(violations), 30,  # Conservative threshold
            fExpected 30+ duplicate type definition violations but found {len(violations)}. 
            fThe analysis indicated 89 duplicates - test may need adjustment.
        )

        # Check for specific critical duplicates
        violation_descriptions = [v.description for v in violations]
        critical_patterns = ["BaseTestCase, MockFactory", ConfigManager]

        for pattern in critical_patterns:
            matching_violations = [desc for desc in violation_descriptions if pattern in desc]
            self.assertGreater(
                len(matching_violations), 0,
                fExpected violations for critical SSOT pattern '{pattern}' but found none"
                fExpected violations for critical SSOT pattern '{pattern}' but found none"
            )

    def test_integration_test_infrastructure_fragmentation(self):
    "
    "
        Integration Test: Detect test infrastructure fragmentation (-1981.6% compliance)

        This test should FAIL initially and report massive fragmentation.
        Expected: 6,96+ duplicate test implementations
        "
        "
        self.record_metric(test_type", integration)"
        self.record_metric(expected_compliance, -1981.6%)

        violations = self.validator.validate_test_infrastructure_compliance()

        self.record_metric(infrastructure_violations", len(violations))"

        # Categorize violations
        duplicate_base_classes = [v for v in violations if v.violation_type == duplicate_test_base_class]
        duplicate_mocks = [v for v in violations if v.violation_type == duplicate_mock_implementation]"
        duplicate_mocks = [v for v in violations if v.violation_type == duplicate_mock_implementation]"
        direct_pytest = [v for v in violations if v.violation_type == "direct_pytest_usage]"

        self.record_metric(duplicate_base_classes, len(duplicate_base_classes))
        self.record_metric("duplicate_mocks, len(duplicate_mocks))"
        self.record_metric(direct_pytest_usage, len(direct_pytest))

        # Log test infrastructure violations
        if violations:
            print(f\n=== TEST INFRASTRUCTURE FRAGMENTATION ({len(violations)} total) ===)
            print(fDuplicate base classes: {len(duplicate_base_classes")}")
            print(fDuplicate mock implementations: {len(duplicate_mocks)})
            print(fDirect pytest usage: {len(direct_pytest)}")"
            print()

            if duplicate_base_classes:
                print(Sample duplicate base classes:)
                for violation in duplicate_base_classes[:3]:
                    print(f- {violation.description}"")
                print()

        # This assertion should FAIL initially
        self.assertGreater(
            len(violations), 50,  # Expect significant fragmentation
            fExpected 50+ test infrastructure violations but found {len(violations)}. 
            fTest infrastructure should be heavily fragmented according to analysis."
            fTest infrastructure should be heavily fragmented according to analysis."
        )

        # Specific checks for known fragmentation
        self.assertGreater(
            len(duplicate_base_classes), 5,
            "Expected multiple duplicate test base class implementations"
        )

    def test_integration_auth_service_ssot_violations(self):
        pass
        Integration Test: Detect auth service SSOT violations

        Expected violations:
        - Multiple JWT handlers across auth service and backend
        - Duplicate authentication logic
""
        self.record_metric(test_type, integration)

        violations = self.validator.validate_auth_service_ssot_compliance()

        self.record_metric("auth_ssot_violations, len(violations))"

        # Log auth violations
        if violations:
            print(f\n=== AUTH SERVICE SSOT VIOLATIONS ({len(violations)} total) ===)
            for violation in violations:
                print(f- {violation.description}")"
                print(f  Locations: {violation.location}")"
                print()

        # This may pass if auth service is properly consolidated
        # But should detect violations if they exist
        if len(violations) > 0:
            critical_violations = [v for v in violations if v.severity == critical]"
            critical_violations = [v for v in violations if v.severity == critical]"
            self.record_metric(critical_auth_violations", len(critical_violations))"

            # If violations exist, they should be critical
            self.assertGreater(
                len(critical_violations), 0,
                fFound {len(violations)} auth violations but none were critical - this suggests minor issues only
            )

    def test_comprehensive_ssot_compliance_summary(self):
        "
        "
        Comprehensive Test: Generate complete SSOT compliance summary

        This test runs all validations and provides a complete violation summary.
        Business Value: Complete assessment for architectural remediation planning.
"
"
        self.record_metric(test_type, comprehensive")"

        # Run all validations
        all_results = self.validator.run_all_validations()

        # Calculate summary metrics
        total_violations = sum(len(violations) for violations in all_results.values())
        critical_violations = sum(
            len([v for v in violations if v.severity == "critical)"
            for violations in all_results.values()
        )

        self.record_metric(total_violations_all_categories, total_violations)
        self.record_metric("critical_violations_all_categories, critical_violations)"

        # Generate comprehensive report
        print(f\n{'='*80})
        print(f"COMPREHENSIVE SSOT COMPLIANCE VALIDATION REPORT")
        print(f{'='*80})
        print(f"Total Violations: {total_violations}")
        print(fCritical Violations: {critical_violations})
        print()

        for category, violations in all_results.items():
            print(f"{category.upper().replace('_', ' ')}: {len(violations)} violations")
            if violations:
                critical_count = len([v for v in violations if v.severity == critical)
                high_count = len([v for v in violations if v.severity == high)"
                high_count = len([v for v in violations if v.severity == high)"
                print(f  - Critical: {critical_count}")"
                print(f  - High: {high_count})
                print(f  - Other: {len(violations") - critical_count - high_count}")
            print()

        # Business impact assessment
        compliance_percentage = max(0, 100 - (total_violations / 10))  # Rough calculation
        self.record_metric(estimated_compliance_percentage, compliance_percentage)

        print(fEstimated SSOT Compliance: {compliance_percentage:.1f}%"")
        print(fBusiness Risk Level: {'CRITICAL' if compliance_percentage < 70 else 'HIGH' if compliance_percentage < 85 else 'MEDIUM'})
        print()

        # This assertion validates the comprehensive analysis
        self.assertGreater(
            total_violations, 75,  # Expect significant violations across all categories
            fExpected 75+ total SSOT violations across all categories but found {total_violations}. ""
            fThis indicates either the violations have been fixed or the analysis needs adjustment.
        )

        # Ensure violations span multiple categories
        categories_with_violations = sum(1 for violations in all_results.values() if len(violations) > 0)
        self.assertGreaterEqual(
            categories_with_violations, 3,
            fExpected violations in at least 3 categories but found violations in {categories_with_violations} categories
        )


if __name__ == "__main__":
    # Run the tests
    unittest.main(verbosity=2)
)))))))))))
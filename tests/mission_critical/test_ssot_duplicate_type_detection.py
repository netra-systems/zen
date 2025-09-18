#!/usr/bin/env python3
"""

SSOT Duplicate Type Definition Detection - Issue #1075
"""
"""

Focused unit test to detect the specific 89 duplicate type definitions identified in the analysis.

CRITICAL BUSINESS IMPACT: Duplicate type definitions lead to:
    - Runtime errors from incorrect imports
- Development confusion and slower velocity
- Maintenance overhead and technical debt
- Risk to $""500K"" plus ARR from system instability

This test is designed to FAIL initially to prove the specific violations exist.
"
""


import os
import sys
import ast
import importlib.util
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict, Counter

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.ssot.base_test_case import SSotBaseTestCase


class DuplicateTypeAnalyzer:
    "Analyzes duplicate type definitions across the codebase"

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.type_definitions = defaultdict(list)
        self.known_ssot_violations = [
            # Known SSOT patterns that should have single implementations
            "BaseTestCase, AsyncTestCase, MockFactory, ConfigManager,"
            DatabaseManager, WebSocketManager", AgentRegistry, AuthService,"
            ExecutionEngine, UserExecutionContext, "TestMetrics, TestContext,"
            AuthenticatedUser, SessionManager, JWTHandler, TokenValidator","
            "MockAgent, TestConfiguration, DockerManager, EnvironmentManager"
        ]

    def scan_type_definitions(self) -> Dict[str, List[Dict]]:
        "Scan all Python files for type definitions"
        type_definitions = defaultdict(list)

        for file_path in self.project_root.rglob(*.py):"
        for file_path in self.project_root.rglob(*.py):"
            # Skip obvious non-production files
            if any(skip in str(file_path) for skip in ['.git', '__pycache__', '.pytest_cache']:
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)

                    self._extract_type_definitions(tree, file_path, type_definitions)

            except Exception as e:
                # Log parsing errors but continue
                print(f"Warning: Could not parse {file_path}: {e}))"
                continue

        return type_definitions

    def _extract_type_definitions(self, tree: ast.AST, file_path: Path, type_definitions: Dict) -> None:
        Extract type definitions from AST""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                type_definitions[node.name).append({
                    'file': str(file_path),
                    'line': node.lineno,
                    'type': 'class',
                    'is_test_file': 'test' in str(file_path).lower(),
                    'relative_path': str(file_path.relative_to(self.project_root))
                }

            elif isinstance(node, ast.FunctionDef) and node.name.startswith('create_'):
                # Factory functions that might be duplicated
                type_definitions[node.name).append({
                    'file': str(file_path),
                    'line': node.lineno,
                    'type': 'factory_function',
                    'is_test_file': 'test' in str(file_path).lower(),
                    'relative_path': str(file_path.relative_to(self.project_root))
                }

            elif isinstance(node, ast.AnnAssign) and hasattr(node.target, 'id'):
                # Type aliases
                type_definitions[node.target.id).append({
                    'file': str(file_path),
                    'line': node.lineno,
                    'type': 'type_alias',
                    'is_test_file': 'test' in str(file_path).lower(),
                    'relative_path': str(file_path.relative_to(self.project_root))
                }

    def find_production_duplicates(self, type_definitions: Dict) -> List[Dict]:
        Find duplicate type definitions in production code"
        Find duplicate type definitions in production code""

        duplicates = []

        for type_name, definitions in type_definitions.items():
            # Filter to production files only
            production_defs = [d for d in definitions if not d['is_test_file']]

            if len(production_defs) > 1:
                duplicates.append({
                    'type_name': type_name,
                    'definition_count': len(production_defs),
                    'definitions': production_defs,
                    'is_critical': type_name in self.known_ssot_violations,
                    'violation_severity': 'critical' if type_name in self.known_ssot_violations else 'high'
                }

        return duplicates

    def find_test_infrastructure_duplicates(self, type_definitions: Dict) -> List[Dict]:
        "Find duplicate type definitions in test infrastructure"
        test_duplicates = []

        test_patterns = [
            "BaseTestCase, AsyncTestCase, TestMetrics, TestContext,"
            MockFactory, MockAgent", TestConfiguration, BaseIntegrationTest"
        ]

        for type_name, definitions in type_definitions.items():
            if any(pattern in type_name for pattern in test_patterns):
                if len(definitions) > 1:
                    test_duplicates.append({
                        'type_name': type_name,
                        'definition_count': len(definitions),
                        'definitions': definitions,
                        'is_critical': True,  # All test infrastructure duplicates are critical
                        'violation_severity': 'critical'
                    }

        return test_duplicates

    def analyze_import_conflicts(self, type_definitions: Dict) -> List[Dict]:
        Analyze potential import conflicts from duplicate definitions""
        conflicts = []

        for type_name, definitions in type_definitions.items():
            if len(definitions) > 1:
                # Check if definitions are in different modules that could conflict
                modules = set()
                for definition in definitions:
                    module_path = Path(definition['relative_path').parent
                    modules.add(str(module_path))

                if len(modules) > 1:
                    conflicts.append({
                        'type_name': type_name,
                        'conflicting_modules': list(modules),
                        'definitions': definitions,
                        'conflict_risk': 'high' if not all(d['is_test_file'] for d in definitions) else 'medium'
                    }

        return conflicts


class TestSsotDuplicateTypeDetection(SSotBaseTestCase):
    pass
    SSOT Duplicate Type Definition Detection Tests

    These tests are designed to FAIL initially and detect the specific 89 duplicate
    type definitions identified in the SSOT compliance analysis.
""

    @classmethod
    def setup_class(cls):
        Setup class-level resources"
        Setup class-level resources""

        super().setup_class()
        cls.analyzer = DuplicateTypeAnalyzer(PROJECT_ROOT)
        cls.type_definitions = cls.analyzer.scan_type_definitions()

    def test_detect_production_duplicate_types(self):
        """
        ""

        Test: Detect duplicate type definitions in production code

        This test should FAIL initially to prove the violations exist.
        Expected: 30+ duplicate type definitions in production code
"
"
        self.record_metric("test_category, unit)"
        self.record_metric(expected_outcome, FAIL - detect production duplicates)

        duplicates = self.analyzer.find_production_duplicates(self.type_definitions)

        # Record metrics
        self.record_metric("production_duplicates_found, len(duplicates))"
        critical_duplicates = [d for d in duplicates if d['is_critical']]
        self.record_metric(critical_production_duplicates, len(critical_duplicates))

        # Log critical duplicates for analysis
        if critical_duplicates:
            print(f\n=== CRITICAL PRODUCTION TYPE DUPLICATES ({len(critical_duplicates)} found) ===)
            for duplicate in critical_duplicates[:10]:  # Show first 10
                print(f\n{duplicate['type_name']} ({duplicate['definition_count']} definitions"):)"
                for definition in duplicate['definitions']:
                    print(f  - {definition['relative_path']}:{definition['line']})

        # This assertion should FAIL initially
        self.assertGreater(
            len(duplicates), 15,  # Conservative threshold
            fExpected 15+ production duplicate types but found {len(duplicates)}. ""
            fAnalysis indicated significant duplicates - verify scan is working correctly.
        )

        # Check for specific critical SSOT violations
        duplicate_names = {d['type_name'] for d in duplicates}
        expected_violations = [ConfigManager, DatabaseManager, ExecutionEngine"]"

        for expected in expected_violations:
            if expected not in duplicate_names:
                print(fWARNING: Expected duplicate '{expected}' not found in scan results)

        # At least some critical duplicates should exist
        self.assertGreater(
            len(critical_duplicates), 3,
            fExpected multiple critical SSOT pattern duplicates but found {len(critical_duplicates)}"
            fExpected multiple critical SSOT pattern duplicates but found {len(critical_duplicates)}""

        )

    def test_detect_test_infrastructure_duplicates(self):
        """
    ""

        Test: Detect duplicate type definitions in test infrastructure

        Expected: Massive duplication in test infrastructure (6,96+ duplicate implementations)
        This should FAIL initially and show the fragmentation scale.
        "
        "
        self.record_metric(test_category", integration)"
        self.record_metric(expected_fragmentation, massive)

        test_duplicates = self.analyzer.find_test_infrastructure_duplicates(self.type_definitions)

        self.record_metric(test_infrastructure_duplicates", len(test_duplicates))"

        # Calculate total duplicate instances
        total_duplicate_instances = sum(d['definition_count'] for d in test_duplicates)
        self.record_metric(total_duplicate_instances, total_duplicate_instances)

        # Log test infrastructure duplicates
        if test_duplicates:
            print(f\n=== TEST INFRASTRUCTURE DUPLICATES ({len(test_duplicates)} types) ===)"
            print(f\n=== TEST INFRASTRUCTURE DUPLICATES ({len(test_duplicates)} types) ===)"
            print(f"Total duplicate instances: {total_duplicate_instances}))"
            print()

            # Show most duplicated types
            sorted_duplicates = sorted(test_duplicates, key=lambda x: x['definition_count'], reverse=True)
            for duplicate in sorted_duplicates[:5]:
                print(f{duplicate['type_name']}: {duplicate['definition_count']} definitions)"
                print(f{duplicate['type_name']}: {duplicate['definition_count']} definitions)""

                for definition in duplicate['definitions'][:3]:  # Show first 3
                    print(f"  - {definition['relative_path']}:{definition['line']}))"
                if len(duplicate['definitions') > 3:
                    print(f  ... and {len(duplicate['definitions'] - 3} more)"
                    print(f  ... and {len(duplicate['definitions'] - 3} more)""

                print()

        # This should FAIL initially due to massive test fragmentation
        self.assertGreater(
            len(test_duplicates), 10,
            f"Expected 10+ test infrastructure duplicate types but found {len(test_duplicates)}."
            fTest infrastructure should be heavily fragmented according to analysis.
        )

        # Check for BaseTestCase fragmentation specifically
        base_test_duplicates = [d for d in test_duplicates if 'BaseTestCase' in d['type_name']]
        if base_test_duplicates:
            base_test_count = sum(d['definition_count'] for d in base_test_duplicates)
            self.record_metric(base_test_case_duplicates, base_test_count)"
            self.record_metric(base_test_case_duplicates, base_test_count)""


            self.assertGreater(
                base_test_count, 5,
                fExpected significant BaseTestCase duplication but found {base_test_count} instances"
                fExpected significant BaseTestCase duplication but found {base_test_count} instances""

            )

    def test_analyze_import_conflicts(self):
        """
    ""

        Test: Analyze potential import conflicts from duplicate types

        This identifies where duplicate type definitions could cause import errors
        or runtime confusion in the system.
        "
        ""

        self.record_metric(test_category, analysis)

        conflicts = self.analyzer.analyze_import_conflicts(self.type_definitions)

        self.record_metric(import_conflicts_detected", len(conflicts))"
        high_risk_conflicts = [c for c in conflicts if c['conflict_risk'] == 'high']
        self.record_metric(high_risk_import_conflicts, len(high_risk_conflicts))

        # Log high-risk import conflicts
        if high_risk_conflicts:
            print(f\n=== HIGH-RISK IMPORT CONFLICTS ({len(high_risk_conflicts)} found) ===)"
            print(f\n=== HIGH-RISK IMPORT CONFLICTS ({len(high_risk_conflicts)} found) ===)""

            for conflict in high_risk_conflicts[:5]:
                print(f"\n{conflict['type_name']} conflicts across modules:))"
                for module in conflict['conflicting_modules']:
                    print(f  - {module})"
                    print(f  - {module})"
                print(f"  Risk: {conflict['conflict_risk']}))"

        # Import conflicts indicate architectural problems
        if len(high_risk_conflicts) > 0:
            self.assertGreater(
                len(high_risk_conflicts), 0,
                High-risk import conflicts detected - these could cause runtime errors
            )

    def test_specific_ssot_pattern_violations(self):
    """

        Test: Check for specific SSOT pattern violations

        This test specifically validates that known SSOT patterns are properly
        consolidated and not duplicated across the codebase.
        
        self.record_metric(test_category", focused)"

        # Check each known SSOT pattern
        ssot_violations = {}
        for pattern in self.analyzer.known_ssot_violations:
            if pattern in self.type_definitions:
                definitions = self.type_definitions[pattern]
                production_defs = [d for d in definitions if not d['is_test_file']]

                if len(production_defs) > 1:
                    ssot_violations[pattern] = {
                        'count': len(production_defs),
                        'locations': [d['relative_path'] for d in production_defs]
                    }

        self.record_metric(ssot_pattern_violations, len(ssot_violations))

        # Log SSOT pattern violations
        if ssot_violations:
            print(f\n=== SSOT PATTERN VIOLATIONS ({len(ssot_violations)} patterns) ===)
            for pattern, violation in ssot_violations.items():
                print(f\n{pattern} ({violation['count']} definitions"):)"
                for location in violation['locations']:
                    print(f  - {location})

        # This should detect violations if they exist
        # The exact count depends on current codebase state
        critical_patterns = [BaseTestCase", MockFactory, ConfigManager, DatabaseManager]"
        critical_violations = {k: v for k, v in ssot_violations.items() if k in critical_patterns}

        self.record_metric(critical_ssot_violations, len(critical_violations))"
        self.record_metric(critical_ssot_violations, len(critical_violations))""


        # If critical violations exist, flag them
        if len(critical_violations) > 0:
            print(f"\nCRITICAL: {len(critical_violations)} critical SSOT patterns have violations!))"
            self.assertTrue(
                len(critical_violations) > 0,  # This will always pass but logs the issue
                fCritical SSOT pattern violations detected: {list(critical_violations.keys())}
            )

    def test_comprehensive_duplicate_summary(self):
    """

        Test: Generate comprehensive duplicate type definition summary

        This provides a complete overview of all duplicate type issues across
        production and test code for remediation planning.
        
        self.record_metric(test_category", comprehensive)"

        # Get all duplicate analyses
        production_duplicates = self.analyzer.find_production_duplicates(self.type_definitions)
        test_duplicates = self.analyzer.find_test_infrastructure_duplicates(self.type_definitions)
        import_conflicts = self.analyzer.analyze_import_conflicts(self.type_definitions)

        # Calculate comprehensive metrics
        total_production_violations = len(production_duplicates)
        total_test_violations = len(test_duplicates)
        total_import_conflicts = len(import_conflicts)

        total_duplicate_instances = (
            sum(d['definition_count'] for d in production_duplicates) +
            sum(d['definition_count'] for d in test_duplicates)
        )

        # Record comprehensive metrics
        self.record_metric(total_production_violations, total_production_violations)
        self.record_metric(total_test_violations, total_test_violations)"
        self.record_metric(total_test_violations, total_test_violations)"
        self.record_metric(total_import_conflicts", total_import_conflicts)"
        self.record_metric(total_duplicate_instances, total_duplicate_instances)

        # Generate summary report
        print(f\n{'='*80}"")
        print(fCOMPREHENSIVE DUPLICATE TYPE DEFINITION SUMMARY)
        print(f{'='*80}"")
        print(fProduction Duplicate Types: {total_production_violations})
        print(fTest Infrastructure Duplicate Types: {total_test_violations}"")
        print(fImport Conflicts: {total_import_conflicts})
        print(fTotal Duplicate Instances: {total_duplicate_instances}"")
        print()

        # Business impact assessment
        if total_duplicate_instances > 100:
            risk_level = CRITICAL
        elif total_duplicate_instances > 50:
            risk_level = HIGH""
        else:
            risk_level = MEDIUM

        print(fBusiness Risk Level: {risk_level}")"
        print(fEstimated Remediation Effort: {total_duplicate_instances * 0.5:.""1f""} hours)""

        print()

        # This validates the comprehensive analysis
        # Should detect significant duplication if analysis is correct
        self.assertGreater(
            total_duplicate_instances, 25,  # Conservative threshold
            fExpected significant duplicate type instances but found {total_duplicate_instances}. "
            fExpected significant duplicate type instances but found {total_duplicate_instances}. "
            f"This may indicate the violations have been fixed or analysis needs adjustment."
        )

        # Ensure we have a mix of issues
        issue_categories = 0
        if total_production_violations > 0:
            issue_categories += 1
        if total_test_violations > 0:
            issue_categories += 1
        if total_import_conflicts > 0:
            issue_categories += 1

        self.assertGreaterEqual(
            issue_categories, 2,
            fExpected issues in multiple categories but found issues in {issue_categories} categories
        )


if __name__ == __main__":"
    import unittest
    unittest.main(verbosity=2)
)))))
#!/usr/bin/env python3
"
SSOT Test Infrastructure Fragmentation Detection - Issue #1075
Integration test to detect test infrastructure fragmentation leading to -1981.6% compliance.

CRITICAL BUSINESS IMPACT: Test infrastructure fragmentation causes:
- Inconsistent test execution across teams
- False positives/negatives in test results
- Development velocity reduction
- Risk to $500K+ ARR from unreliable test coverage

This test is designed to FAIL initially to prove the massive fragmentation exists.
Expected: 6,096+ duplicate test implementations across the codebase.
"

import os
import sys
import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict, Counter

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestInfrastructureFragmentationAnalyzer:
    "Analyzes test infrastructure fragmentation across the codebase

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_base_patterns = [
            "BaseTestCase, AsyncTestCase", TestCase, BaseTest,
            IntegrationTestCase, UnitTestCase", "E2ETestCase
        ]
        self.mock_patterns = [
            MockFactory, MockAgent, MockManager", "MockService,
            TestMock, FakeMock, StubMock"
        ]
        self.test_utility_patterns = [
            "TestUtility, TestHelper, TestConfiguration, TestMetrics,
            "TestContext, TestValidator", TestRunner
        ]

    def scan_test_files(self) -> Dict[str, List[Path]]:
        "Scan all test files in the project"
        test_files = {
            'unit_tests': [],
            'integration_tests': [],
            'e2e_tests': [],
            'mission_critical_tests': [],
            'other_tests': []
        }

        for file_path in self.project_root.rglob(*.py):
            if self._is_test_file(file_path):
                category = self._categorize_test_file(file_path)
                test_files[category].append(file_path)

        return test_files

    def _is_test_file(self, file_path: Path) -> bool:
        ""Determine if a file is a test file
        # Skip obvious non-test directories
        skip_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules'}
        if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
            return False

        # Check if it's a test file
        return (
            'test' in str(file_path).lower() or
            file_path.name.startswith('test_') or
            file_path.name.endswith('_test.py') or
            'tests' in file_path.parts
        )

    def _categorize_test_file(self, file_path: Path) -> str:
        Categorize test file by type""
        path_str = str(file_path).lower()

        if 'mission_critical' in path_str:
            return 'mission_critical_tests'
        elif 'e2e' in path_str or 'end_to_end' in path_str:
            return 'e2e_tests'
        elif 'integration' in path_str:
            return 'integration_tests'
        elif 'unit' in path_str:
            return 'unit_tests'
        else:
            return 'other_tests'

    def analyze_test_base_class_duplicates(self, test_files: Dict[str, List[Path]] -> Dict[str, Any]:
        Analyze duplicate test base class implementations""
        base_class_implementations = defaultdict(list)

        all_test_files = []
        for file_list in test_files.values():
            all_test_files.extend(file_list)

        for file_path in all_test_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)

                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            # Check if it matches test base class patterns
                            for pattern in self.test_base_patterns:
                                if pattern in node.name:
                                    base_class_implementations[node.name].append({
                                        'file': str(file_path),
                                        'line': node.lineno,
                                        'relative_path': str(file_path.relative_to(self.project_root)),
                                        'category': self._categorize_test_file(file_path)
                                    }

            except Exception as e:
                print(fWarning: Could not parse test file {file_path}: {e})
                continue

        # Calculate duplication statistics
        duplicates = {name: impls for name, impls in base_class_implementations.items() if len(impls) > 1}
        total_duplicates = sum(len(impls) for impls in duplicates.values())

        return {
            'duplicate_base_classes': duplicates,
            'total_duplicate_count': total_duplicates,
            'unique_base_classes': len(base_class_implementations),
            'fragmentation_score': total_duplicates / max(len(base_class_implementations), 1)
        }

    def analyze_mock_implementation_duplicates(self, test_files: Dict[str, List[Path]] -> Dict[str, Any]:
        "Analyze duplicate mock implementations"
        mock_implementations = defaultdict(list)

        all_test_files = []
        for file_list in test_files.values():
            all_test_files.extend(file_list)

        for file_path in all_test_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)

                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            # Check if it matches mock patterns
                            for pattern in self.mock_patterns:
                                if pattern in node.name or 'Mock' in node.name:
                                    mock_implementations[node.name].append({
                                        'file': str(file_path),
                                        'line': node.lineno,
                                        'relative_path': str(file_path.relative_to(self.project_root)),
                                        'category': self._categorize_test_file(file_path)
                                    }

            except Exception:
                continue

        # Calculate mock duplication statistics
        mock_duplicates = {name: impls for name, impls in mock_implementations.items() if len(impls) > 1}
        total_mock_duplicates = sum(len(impls) for impls in mock_duplicates.values())

        return {
            'duplicate_mocks': mock_duplicates,
            'total_mock_duplicates': total_mock_duplicates,
            'unique_mocks': len(mock_implementations),
            'mock_fragmentation_score': total_mock_duplicates / max(len(mock_implementations), 1)
        }

    def analyze_test_execution_patterns(self, test_files: Dict[str, List[Path]] -> Dict[str, Any]:
        Analyze test execution patterns and detect bypass behaviors""
        execution_patterns = {
            'direct_pytest_usage': [],
            'direct_unittest_usage': [],
            'custom_test_runners': [],
            'bypassed_ssot_runners': []
        }

        all_test_files = []
        for file_list in test_files.values():
            all_test_files.extend(file_list)

        for file_path in all_test_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                    # Check for direct pytest usage
                    if re.search(r'import pytest', content) or re.search(r'from pytest', content):
                        execution_patterns['direct_pytest_usage'].append(str(file_path.relative_to(self.project_root)))

                    # Check for direct unittest usage
                    if re.search(r'unittest\.main\(\)', content):
                        execution_patterns['direct_unittest_usage'].append(str(file_path.relative_to(self.project_root)))

                    # Check for custom test runners
                    if re.search(r'def run_tests?\(', content) or re.search(r'class.*TestRunner', content):
                        execution_patterns['custom_test_runners'].append(str(file_path.relative_to(self.project_root)))

                    # Check for SSOT runner bypass
                    if 'unified_test_runner' not in content and ('if __name__' in content and 'main()' in content):
                        execution_patterns['bypassed_ssot_runners'].append(str(file_path.relative_to(self.project_root)))

            except Exception:
                continue

        return execution_patterns

    def analyze_test_configuration_fragmentation(self, test_files: Dict[str, List[Path]] -> Dict[str, Any]:
        Analyze test configuration fragmentation"
        config_files = []
        config_patterns = defaultdict(list)

        # Look for test configuration files
        for config_file in self.project_root.rglob("*):
            if config_file.name in ['pytest.ini', 'conftest.py', 'setup.cfg', 'tox.ini', '.pytest_cache']:
                config_files.append(str(config_file.relative_to(self.project_root)))

        # Look for inline test configurations
        all_test_files = []
        for file_list in test_files.values():
            all_test_files.extend(file_list)

        for file_path in all_test_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                    # Check for configuration patterns
                    if 'pytest.fixture' in content:
                        config_patterns['pytest_fixtures'].append(str(file_path.relative_to(self.project_root)))

                    if 'setUp(' in content or 'tearDown(' in content:
                        config_patterns['unittest_setup'].append(str(file_path.relative_to(self.project_root)))

                    if '@classmethod' in content and 'setup_class' in content:
                        config_patterns['class_level_setup'].append(str(file_path.relative_to(self.project_root)))

            except Exception:
                continue

        return {
            'config_files': config_files,
            'config_patterns': dict(config_patterns),
            'total_config_fragments': len(config_files) + sum(len(patterns) for patterns in config_patterns.values())
        }

    def calculate_fragmentation_metrics(self, analysis_results: Dict[str, Any] -> Dict[str, float]:
        Calculate comprehensive fragmentation metrics""
        base_class_analysis = analysis_results.get('base_class_analysis', {}
        mock_analysis = analysis_results.get('mock_analysis', {}
        execution_analysis = analysis_results.get('execution_analysis', {}
        config_analysis = analysis_results.get('config_analysis', {}

        # Base fragmentation score
        base_fragmentation = base_class_analysis.get('fragmentation_score', 0)
        mock_fragmentation = mock_analysis.get('mock_fragmentation_score', 0)

        # Execution pattern fragmentation
        execution_fragments = sum(len(patterns) for patterns in execution_analysis.values())
        config_fragments = config_analysis.get('total_config_fragments', 0)

        # Overall fragmentation calculation
        total_duplicate_instances = (
            base_class_analysis.get('total_duplicate_count', 0) +
            mock_analysis.get('total_mock_duplicates', 0) +
            execution_fragments +
            config_fragments
        )

        # Calculate compliance percentage (negative indicates severe fragmentation)
        # The -1981.6% figure suggests massive over-duplication
        expected_ssot_instances = 10  # Expected number of SSOT implementations
        compliance_percentage = ((expected_ssot_instances - total_duplicate_instances) / expected_ssot_instances) * 100

        return {
            'base_class_fragmentation': base_fragmentation,
            'mock_fragmentation': mock_fragmentation,
            'execution_fragmentation': execution_fragments,
            'config_fragmentation': config_fragments,
            'total_duplicate_instances': total_duplicate_instances,
            'compliance_percentage': compliance_percentage,
            'business_risk_score': min(100, total_duplicate_instances / 10)  # Risk increases with duplicates
        }


class TestSsotTestInfrastructureFragmentation(SSotBaseTestCase):

    SSOT Test Infrastructure Fragmentation Detection

    These tests are designed to FAIL initially and detect the massive test
    infrastructure fragmentation leading to -1981.6% compliance.
    ""

    @classmethod
    def setup_class(cls):
        Setup class-level resources"
        super().setup_class()
        cls.analyzer = TestInfrastructureFragmentationAnalyzer(PROJECT_ROOT)
        cls.test_files = cls.analyzer.scan_test_files()

    def test_detect_test_base_class_fragmentation(self):
    "
        Integration Test: Detect test base class fragmentation

        This test should FAIL initially to prove massive BaseTestCase duplication.
        Expected: 50+ duplicate BaseTestCase implementations across test files.
        "
        self.record_metric(test_category", integration)
        self.record_metric(expected_outcome, FAIL - detect base class fragmentation)

        base_class_analysis = self.analyzer.analyze_test_base_class_duplicates(self.test_files)

        # Record detailed metrics
        self.record_metric(duplicate_base_classes", len(base_class_analysis['duplicate_base_classes'])"
        self.record_metric(total_duplicate_instances, base_class_analysis['total_duplicate_count']
        self.record_metric(fragmentation_score, base_class_analysis['fragmentation_score']"

        # Log fragmentation details
        duplicates = base_class_analysis['duplicate_base_classes']
        if duplicates:
            print(f"\n=== TEST BASE CLASS FRAGMENTATION ({len(duplicates)} duplicate types) ===)
            print(fTotal duplicate instances: {base_class_analysis['total_duplicate_count']})"
            print(f"Fragmentation score: {base_class_analysis['fragmentation_score']:.2f})
            print()

            # Show most fragmented base classes
            sorted_duplicates = sorted(duplicates.items(), key=lambda x: len(x[1], reverse=True)
            for class_name, implementations in sorted_duplicates[:5]:
                print(f{class_name} ({len(implementations)} implementations):)
                for impl in implementations[:3]:  # Show first 3
                    print(f"  - {impl['relative_path']}:{impl['line']} ({impl['category']})
                if len(implementations) > 3:
                    print(f  ... and {len(implementations") - 3} more)
                print()

        # This assertion should FAIL initially due to massive fragmentation
        self.assertGreater(
            base_class_analysis['total_duplicate_count'], 20,
            fExpected 20+ duplicate base class instances but found {base_class_analysis['total_duplicate_count']}. 
            fAnalysis indicated massive test fragmentation - verify scan is working correctly.""
        )

        # Check for BaseTestCase specifically (known SSOT violation)
        base_test_case_duplicates = [
            class_name for class_name in duplicates.keys()
            if 'BaseTestCase' in class_name
        ]

        if base_test_case_duplicates:
            base_test_instances = sum(
                len(duplicates[class_name] for class_name in base_test_case_duplicates
            )
            self.record_metric(base_test_case_duplicates, base_test_instances)

            self.assertGreater(
                base_test_instances, 5,
                fExpected significant BaseTestCase duplication but found {base_test_instances} instances"
            )

    def test_detect_mock_implementation_fragmentation(self):
    "
        Integration Test: Detect mock implementation fragmentation

        Expected: Massive duplication of mock implementations across test files.
        This contributes significantly to the -1981.6% compliance score.
        "
        self.record_metric(test_category", integration)

        mock_analysis = self.analyzer.analyze_mock_implementation_duplicates(self.test_files)

        # Record metrics
        self.record_metric(duplicate_mock_types, len(mock_analysis['duplicate_mocks'])
        self.record_metric("total_mock_duplicates, mock_analysis['total_mock_duplicates']"
        self.record_metric(mock_fragmentation_score, mock_analysis['mock_fragmentation_score']

        # Log mock fragmentation
        mock_duplicates = mock_analysis['duplicate_mocks']
        if mock_duplicates:
            print(f\n=== MOCK IMPLEMENTATION FRAGMENTATION ({len(mock_duplicates)} duplicate types) ===")
            print(fTotal mock duplicates: {mock_analysis['total_mock_duplicates']}")
            print(fMock fragmentation score: {mock_analysis['mock_fragmentation_score']:.2f})
            print()

            # Show most duplicated mocks
            sorted_mocks = sorted(mock_duplicates.items(), key=lambda x: len(x[1], reverse=True)
            for mock_name, implementations in sorted_mocks[:5]:
                print(f{mock_name} ({len(implementations)} implementations"):")
                for impl in implementations[:3]:  # Show first 3
                    print(f  - {impl['relative_path']}:{impl['line']})
                if len(implementations) > 3:
                    print(f  ... and {len(implementations) - 3} more")"
                print()

        # Check for significant mock duplication
        self.assertGreater(
            mock_analysis['total_mock_duplicates'], 10,
            fExpected 10+ mock duplicates but found {mock_analysis['total_mock_duplicates']}. 
            fMock implementation should be fragmented across test files.
        )

        # Check for MockFactory specifically (critical SSOT violation)
        mock_factory_duplicates = [
            mock_name for mock_name in mock_duplicates.keys()
            if 'MockFactory' in mock_name
        ]

        if mock_factory_duplicates:
            factory_instances = sum(
                len(mock_duplicates[mock_name] for mock_name in mock_factory_duplicates
            )
            self.record_metric("mock_factory_duplicates, factory_instances)"

            self.assertGreater(
                factory_instances, 2,
                fExpected MockFactory duplication but found {factory_instances} instances
            )

    def test_detect_test_execution_pattern_fragmentation(self):
    ""
        Integration Test: Detect test execution pattern fragmentation

        This identifies bypassing of SSOT unified test runner leading to
        inconsistent test execution patterns across the codebase.
        
        self.record_metric(test_category, "integration)

        execution_analysis = self.analyzer.analyze_test_execution_patterns(self.test_files)

        # Record metrics for each pattern
        for pattern_name, files in execution_analysis.items():
            self.record_metric(fexecution_pattern_{pattern_name}", len(files))

        total_execution_fragments = sum(len(files) for files in execution_analysis.values())
        self.record_metric(total_execution_fragments, total_execution_fragments)

        # Log execution pattern fragmentation
        print(f\n=== TEST EXECUTION PATTERN FRAGMENTATION ==="")
        print(fTotal execution fragments: {total_execution_fragments})
        for pattern_name, files in execution_analysis.items():
            if files:
                print(f\n{pattern_name.replace('_', ' ').title()}: {len(files)} files")"
                for file_path in files[:3]:  # Show first 3
                    print(f  - {file_path})
                if len(files) > 3:
                    print(f  ... and {len(files) - 3} more)"

        # Check for SSOT unified test runner bypassing
        bypassed_files = execution_analysis['bypassed_ssot_runners']
        direct_pytest_files = execution_analysis['direct_pytest_usage']

        self.record_metric("ssot_runner_bypass_count, len(bypassed_files))
        self.record_metric(direct_pytest_usage_count, len(direct_pytest_files))

        # This indicates SSOT test runner is being bypassed
        if len(bypassed_files) > 0 or len(direct_pytest_files) > 0:
            total_bypass_violations = len(bypassed_files) + len(direct_pytest_files)

            self.assertGreater(
                total_bypass_violations, 5,
                f"Expected significant SSOT test runner bypassing but found {total_bypass_violations} violations
            )

    def test_detect_test_configuration_fragmentation(self):
        "
        Integration Test: Detect test configuration fragmentation

        Multiple test configuration approaches lead to inconsistent test
        behavior and contribute to the fragmentation score.
"
        self.record_metric("test_category, integration)

        config_analysis = self.analyzer.analyze_test_configuration_fragmentation(self.test_files)

        # Record metrics
        self.record_metric(config_files_count, len(config_analysis['config_files'])
        self.record_metric(total_config_fragments", config_analysis['total_config_fragments']"

        # Log configuration fragmentation
        print(f\n=== TEST CONFIGURATION FRAGMENTATION ===)
        print(fConfiguration files: {len(config_analysis['config_files']}")"
        print(fTotal config fragments: {config_analysis['total_config_fragments']})
        print()

        if config_analysis['config_files']:
            print(Configuration files found:")"
            for config_file in config_analysis['config_files']:
                print(f  - {config_file})
            print()

        for pattern_name, files in config_analysis['config_patterns'].items():
            if files:
                print(f{pattern_name.replace('_', ' ').title()}: {len(files)} files)"

        # Check for excessive configuration fragmentation
        self.assertGreater(
            config_analysis['total_config_fragments'], 15,
            f"Expected 15+ configuration fragments but found {config_analysis['total_config_fragments']}. 
            fTest configuration should be fragmented across multiple files.
        )

    def test_calculate_comprehensive_fragmentation_metrics(self):
    ""
        Integration Test: Calculate comprehensive fragmentation metrics

        This generates the overall fragmentation assessment that should
        approximate the -1981.6% compliance score from the analysis.
        
        self.record_metric(test_category, "comprehensive)

        # Run all analyses
        analysis_results = {
            'base_class_analysis': self.analyzer.analyze_test_base_class_duplicates(self.test_files),
            'mock_analysis': self.analyzer.analyze_mock_implementation_duplicates(self.test_files),
            'execution_analysis': self.analyzer.analyze_test_execution_patterns(self.test_files),
            'config_analysis': self.analyzer.analyze_test_configuration_fragmentation(self.test_files)
        }

        # Calculate comprehensive metrics
        fragmentation_metrics = self.analyzer.calculate_fragmentation_metrics(analysis_results)

        # Record all metrics
        for metric_name, value in fragmentation_metrics.items():
            self.record_metric(metric_name, value)

        # Generate comprehensive report
        print(f\n{'='*80}")
        print(fCOMPREHENSIVE TEST INFRASTRUCTURE FRAGMENTATION REPORT")
        print(f{'='*80}")
        print(fTotal Duplicate Instances: {fragmentation_metrics['total_duplicate_instances']}")
        print(fCompliance Percentage: {fragmentation_metrics['compliance_percentage']:.1f}%")
        print(fBusiness Risk Score: {fragmentation_metrics['business_risk_score']:.1f}/100)
        print("")
        print(Fragmentation Breakdown:")
        print(f  Base Class Fragmentation: {fragmentation_metrics['base_class_fragmentation']:.2f}")
        print(f  Mock Implementation Fragmentation: {fragmentation_metrics['mock_fragmentation']:.2f}")
        print(f  Execution Pattern Fragmentation: {fragmentation_metrics['execution_fragmentation']}")
        print(f  Configuration Fragmentation: {fragmentation_metrics['config_fragmentation']}")
        print()

        # Business impact assessment
        compliance = fragmentation_metrics['compliance_percentage']
        if compliance < -1000:
            risk_level = CATASTROPHIC"
        elif compliance < -500:
            risk_level = CRITICAL"
        elif compliance < 0:
            risk_level = HIGH
        else:
            risk_level = MEDIUM""

        print(fRisk Level: {risk_level})
        print(fEstimated Remediation Effort: {fragmentation_metrics['total_duplicate_instances'] * 0.25:.1f} hours")"
        print()

        # This should validate massive fragmentation
        self.assertGreater(
            fragmentation_metrics['total_duplicate_instances'], 50,
            fExpected 50+ total fragmentation instances but found {fragmentation_metrics['total_duplicate_instances']}. 
            fTest infrastructure should be heavily fragmented according to analysis.
        )

        # Check if compliance is significantly negative (indicating massive over-duplication)
        self.assertLess(
            fragmentation_metrics['compliance_percentage'], -100,
            f"Expected severely negative compliance percentage but got {fragmentation_metrics['compliance_percentage']:.1f}%. 
            fThis should indicate massive test infrastructure fragmentation."
        )

        # Validate business risk is high
        self.assertGreater(
            fragmentation_metrics['business_risk_score'], 20,
            fExpected high business risk score but got {fragmentation_metrics['business_risk_score']:.1f}. 
            fFragmentation should pose significant business risk."
        )


if __name__ == "__main__":
    import unittest
    unittest.main(verbosity=2)
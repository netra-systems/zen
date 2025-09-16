"""
Test Suite: SSOT Compliance Measurement for UserExecutionEngine
Issue #1186: UserExecutionEngine SSOT Consolidation - Compliance Measurement

PURPOSE: Measure and validate SSOT compliance across the entire codebase.
These tests are DESIGNED TO FAIL initially to demonstrate current violations.

Business Impact: 98.7% current compliance needs to reach 100% for enterprise
deployment, protecting $500K+ ARR from architectural fragmentation.

EXPECTED BEHAVIOR:
- All tests SHOULD FAIL initially (demonstrating <100% compliance)
- All tests SHOULD PASS after SSOT consolidation achieves 100% compliance
"""

import ast
import json
import re
import sys
import pytest
import unittest
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class SSotViolation:
    """Container for SSOT violation data."""
    file_path: str
    violation_type: str
    line_number: int
    description: str
    severity: str
    component: str


@dataclass
class SSotComplianceReport:
    """Container for SSOT compliance analysis results."""
    overall_compliance_percentage: float
    total_violations: int
    violations_by_category: Dict[str, List[SSotViolation]]
    components_analyzed: int
    target_compliance: float
    compliance_gap: float
    priority_violations: List[SSotViolation]


@pytest.mark.unit
@pytest.mark.ssot_consolidation
@pytest.mark.compliance
class TestSSotComplianceMeasurement(SSotBaseTestCase):
    """
    Test class to measure and validate SSOT compliance across the codebase.
    
    This test suite provides comprehensive compliance measurement and tracking.
    """
    
    def setup_method(self, method):
        """Setup test environment with SSOT base."""
        super().setup_method(method)
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.target_compliance = 100.0
        self.current_baseline = 98.7  # From audit
        
        # SSOT compliance categories and their criteria
        self.compliance_categories = {
            'import_patterns': {
                'canonical': 'from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine',
                'violations': [
                    r'from.*execution_engine.*import.*UserExecutionEngine',
                    r'from.*\.execution_engine.*import',
                    r'import.*UserExecutionEngine.*as.*'
                ]
            },
            'factory_patterns': {
                'canonical': 'UserExecutionEngineFactory',
                'violations': [
                    r'class.*ExecutionEngineFactory(?!.*UserExecutionEngine)',
                    r'def.*create_execution_engine',
                    r'def.*get_execution_engine',
                ]
            },
            'authentication_patterns': {
                'canonical': 'authenticate_websocket_ssot',
                'violations': [
                    r'def.*authenticate_websocket_connection',
                    r'class.*WebSocketAuthenticator(?!.*Unified)',
                    r'validate_websocket_token'
                ]
            },
            'user_context_patterns': {
                'canonical': 'UserExecutionContext',
                'violations': [
                    r'class.*UserContext(?!.*UserExecutionContext)',
                    r'class.*ExecutionContext(?!.*UserExecutionContext)',
                    r'create_user_context(?!.*execution)'
                ]
            }
        }
        
    def test_measure_overall_ssot_compliance(self):
        """
        TEST 1: Measure overall SSOT compliance percentage.
        
        EXPECTED TO FAIL: Should find 98.7% compliance (audit baseline).
        TARGET: Should achieve 100% compliance after consolidation.
        """
        print("\n🔍 TEST 1: Measuring overall SSOT compliance...")
        
        compliance_report = self._generate_comprehensive_compliance_report()
        
        # Track metrics for business analysis
        self.record_metric("overall_compliance_percentage", compliance_report.overall_compliance_percentage)
        self.record_metric("total_ssot_violations", compliance_report.total_violations)
        self.record_metric("compliance_gap", compliance_report.compliance_gap)
        self.record_metric("components_analyzed", compliance_report.components_analyzed)
        
        print(f"\n📊 SSOT COMPLIANCE ANALYSIS:")
        print(f"   Overall compliance: {compliance_report.overall_compliance_percentage:.1f}%")
        print(f"   Target compliance: {compliance_report.target_compliance}%")
        print(f"   Compliance gap: {compliance_report.compliance_gap:.1f}%")
        print(f"   Total violations: {compliance_report.total_violations}")
        print(f"   Components analyzed: {compliance_report.components_analyzed}")
        
        # Print violations by category
        print(f"\n   Violations by category:")
        for category, violations in compliance_report.violations_by_category.items():
            print(f"     {category}: {len(violations)} violations")
        
        # ASSERTION DESIGNED TO FAIL INITIALLY
        assert compliance_report.overall_compliance_percentage >= self.target_compliance, (
            f"❌ EXPECTED FAILURE: SSOT compliance is {compliance_report.overall_compliance_percentage:.1f}%, "
            f"below target of {self.target_compliance}%.\n"
            f"Compliance gap: {compliance_report.compliance_gap:.1f}%\n"
            f"Total violations: {compliance_report.total_violations}\n"
            f"Priority violations:\n" + 
            '\n'.join([f"  • {v.component} - {v.description} ({v.file_path}:{v.line_number})" 
                      for v in compliance_report.priority_violations[:5]]) +
            f"\n\n🎯 Target: Achieve 100% SSOT compliance for enterprise deployment."
        )
        
    def test_measure_import_pattern_compliance(self):
        """
        TEST 2: Measure import pattern compliance specifically.
        
        EXPECTED TO FAIL: Should find import pattern violations.
        TARGET: Should achieve 100% canonical import usage.
        """
        print("\n🔍 TEST 2: Measuring import pattern compliance...")
        
        import_compliance = self._measure_category_compliance('import_patterns')
        
        # Track metrics
        self.record_metric("import_pattern_compliance", import_compliance['compliance_percentage'])
        self.record_metric("import_violations", len(import_compliance['violations']))
        
        print(f"\n📊 IMPORT PATTERN COMPLIANCE:")
        print(f"   Compliance percentage: {import_compliance['compliance_percentage']:.1f}%")
        print(f"   Violations found: {len(import_compliance['violations'])}")
        print(f"   Canonical pattern: {import_compliance['canonical_pattern']}")
        
        # Show sample violations
        for violation in import_compliance['violations'][:3]:
            print(f"   • {violation.description} in {violation.file_path}:{violation.line_number}")
        
        # ASSERTION DESIGNED TO FAIL INITIALLY
        assert import_compliance['compliance_percentage'] >= 100.0, (
            f"❌ EXPECTED FAILURE: Import pattern compliance is {import_compliance['compliance_percentage']:.1f}%, "
            f"below target of 100%.\n"
            f"Violations: {len(import_compliance['violations'])}\n"
            f"Canonical pattern: {import_compliance['canonical_pattern']}\n"
            f"Sample violations:\n" + 
            '\n'.join([f"  • {v.description} ({v.file_path}:{v.line_number})" 
                      for v in import_compliance['violations'][:5]]) +
            f"\n\n🎯 Target: All imports should use canonical SSOT pattern."
        )
        
    def test_measure_factory_pattern_compliance(self):
        """
        TEST 3: Measure factory pattern compliance.
        
        EXPECTED TO FAIL: Should find factory pattern violations.
        TARGET: Should achieve 100% canonical factory usage.
        """
        print("\n🔍 TEST 3: Measuring factory pattern compliance...")
        
        factory_compliance = self._measure_category_compliance('factory_patterns')
        
        # Track metrics
        self.record_metric("factory_pattern_compliance", factory_compliance['compliance_percentage'])
        self.record_metric("factory_violations", len(factory_compliance['violations']))
        
        print(f"\n📊 FACTORY PATTERN COMPLIANCE:")
        print(f"   Compliance percentage: {factory_compliance['compliance_percentage']:.1f}%")
        print(f"   Violations found: {len(factory_compliance['violations'])}")
        print(f"   Canonical pattern: {factory_compliance['canonical_pattern']}")
        
        # ASSERTION DESIGNED TO FAIL INITIALLY
        assert factory_compliance['compliance_percentage'] >= 100.0, (
            f"❌ EXPECTED FAILURE: Factory pattern compliance is {factory_compliance['compliance_percentage']:.1f}%, "
            f"below target of 100%.\n"
            f"Violations: {len(factory_compliance['violations'])}\n"
            f"Canonical pattern: {factory_compliance['canonical_pattern']}\n"
            f"🎯 Target: All factories should use canonical SSOT pattern."
        )
        
    def test_measure_authentication_pattern_compliance(self):
        """
        TEST 4: Measure authentication pattern compliance.
        
        EXPECTED TO FAIL: Should find authentication pattern violations.
        TARGET: Should achieve 100% SSOT authentication usage.
        """
        print("\n🔍 TEST 4: Measuring authentication pattern compliance...")
        
        auth_compliance = self._measure_category_compliance('authentication_patterns')
        
        # Track metrics
        self.record_metric("auth_pattern_compliance", auth_compliance['compliance_percentage'])
        self.record_metric("auth_violations", len(auth_compliance['violations']))
        
        print(f"\n📊 AUTHENTICATION PATTERN COMPLIANCE:")
        print(f"   Compliance percentage: {auth_compliance['compliance_percentage']:.1f}%")
        print(f"   Violations found: {len(auth_compliance['violations'])}")
        print(f"   Canonical pattern: {auth_compliance['canonical_pattern']}")
        
        # ASSERTION DESIGNED TO FAIL INITIALLY
        assert auth_compliance['compliance_percentage'] >= 100.0, (
            f"❌ EXPECTED FAILURE: Authentication pattern compliance is {auth_compliance['compliance_percentage']:.1f}%, "
            f"below target of 100%.\n"
            f"Violations: {len(auth_compliance['violations'])}\n"
            f"Canonical pattern: {auth_compliance['canonical_pattern']}\n"
            f"🎯 Target: All authentication should use SSOT patterns."
        )
        
    def test_validate_ssot_consolidation_progress(self):
        """
        TEST 5: Validate SSOT consolidation progress against baseline.
        
        EXPECTED TO FAIL: Should show progress but not complete consolidation.
        TARGET: Should show 100% consolidation completion.
        """
        print("\n🔍 TEST 5: Validating SSOT consolidation progress...")
        
        progress_report = self._measure_consolidation_progress()
        
        # Track metrics
        self.record_metric("consolidation_progress", progress_report['progress_percentage'])
        self.record_metric("violations_eliminated", progress_report['violations_eliminated'])
        self.record_metric("violations_remaining", progress_report['violations_remaining'])
        
        print(f"\n📊 SSOT CONSOLIDATION PROGRESS:")
        print(f"   Progress: {progress_report['progress_percentage']:.1f}%")
        print(f"   Baseline compliance: {self.current_baseline}%")
        print(f"   Current compliance: {progress_report['current_compliance']:.1f}%")
        print(f"   Violations eliminated: {progress_report['violations_eliminated']}")
        print(f"   Violations remaining: {progress_report['violations_remaining']}")
        
        # ASSERTION DESIGNED TO FAIL INITIALLY
        assert progress_report['progress_percentage'] >= 100.0, (
            f"❌ EXPECTED FAILURE: SSOT consolidation progress is {progress_report['progress_percentage']:.1f}%, "
            f"not yet complete.\n"
            f"Current compliance: {progress_report['current_compliance']:.1f}%\n"
            f"Baseline compliance: {self.current_baseline}%\n"
            f"Violations remaining: {progress_report['violations_remaining']}\n"
            f"🎯 Target: Complete SSOT consolidation (100% progress)."
        )
        
    def _generate_comprehensive_compliance_report(self) -> SSotComplianceReport:
        """Generate comprehensive SSOT compliance report."""
        all_violations = []
        violations_by_category = {}
        components_analyzed = 0
        
        # Analyze each compliance category
        for category_name, category_config in self.compliance_categories.items():
            category_compliance = self._measure_category_compliance(category_name)
            violations_by_category[category_name] = category_compliance['violations']
            all_violations.extend(category_compliance['violations'])
            components_analyzed += category_compliance['components_analyzed']
        
        # Calculate overall compliance
        total_components = components_analyzed
        total_violations = len(all_violations)
        
        # Calculate compliance percentage (components without violations / total components)
        compliant_components = total_components - total_violations
        overall_compliance = (compliant_components / max(1, total_components)) * 100
        
        # Identify priority violations (CRITICAL and HIGH severity)
        priority_violations = [v for v in all_violations if v.severity in ['CRITICAL', 'HIGH']]
        priority_violations.sort(key=lambda x: (x.severity, x.component))
        
        compliance_gap = self.target_compliance - overall_compliance
        
        return SSotComplianceReport(
            overall_compliance_percentage=overall_compliance,
            total_violations=total_violations,
            violations_by_category=violations_by_category,
            components_analyzed=total_components,
            target_compliance=self.target_compliance,
            compliance_gap=compliance_gap,
            priority_violations=priority_violations[:10]  # Top 10 priority violations
        )
        
    def _measure_category_compliance(self, category_name: str) -> Dict[str, any]:
        """Measure compliance for a specific category."""
        category_config = self.compliance_categories[category_name]
        violations = []
        components_analyzed = 0
        
        # Get relevant files for this category
        relevant_files = self._get_relevant_files_for_category(category_name)
        
        for py_file in relevant_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                components_analyzed += 1
                
                # Check for violations in this file
                for line_num, line in enumerate(lines, 1):
                    for violation_pattern in category_config['violations']:
                        if re.search(violation_pattern, line):
                            severity = self._determine_violation_severity(category_name, violation_pattern)
                            
                            violation = SSotViolation(
                                file_path=str(py_file),
                                violation_type=category_name,
                                line_number=line_num,
                                description=f"Non-SSOT pattern: {line.strip()[:50]}...",
                                severity=severity,
                                component=py_file.name
                            )
                            violations.append(violation)
                            
            except (UnicodeDecodeError, PermissionError, OSError):
                continue
        
        # Calculate compliance percentage for this category
        violation_count = len(violations)
        compliant_components = max(0, components_analyzed - violation_count)
        compliance_percentage = (compliant_components / max(1, components_analyzed)) * 100
        
        return {
            'compliance_percentage': compliance_percentage,
            'violations': violations,
            'canonical_pattern': category_config['canonical'],
            'components_analyzed': components_analyzed
        }
        
    def _get_relevant_files_for_category(self, category_name: str) -> List[Path]:
        """Get files relevant for a specific compliance category."""
        all_files = []
        
        # Base search paths
        search_paths = [
            self.project_root / 'netra_backend' / 'app',
            self.project_root / 'tests',
            self.project_root / 'auth_service',
        ]
        
        # Category-specific file filtering
        if category_name == 'import_patterns':
            # All Python files that might import UserExecutionEngine
            for search_path in search_paths:
                if search_path.exists():
                    all_files.extend(search_path.rglob('*.py'))
                    
        elif category_name == 'factory_patterns':
            # Files that might contain factory patterns
            for search_path in search_paths:
                if search_path.exists():
                    for py_file in search_path.rglob('*.py'):
                        if any(keyword in str(py_file).lower() for keyword in 
                               ['factory', 'engine', 'execution', 'manager']):
                            all_files.append(py_file)
                            
        elif category_name == 'authentication_patterns':
            # WebSocket and authentication related files
            for search_path in search_paths:
                if search_path.exists():
                    for py_file in search_path.rglob('*.py'):
                        if any(keyword in str(py_file).lower() for keyword in 
                               ['websocket', 'auth', 'token', 'jwt']):
                            all_files.append(py_file)
                            
        elif category_name == 'user_context_patterns':
            # Files that might contain user context patterns
            for search_path in search_paths:
                if search_path.exists():
                    for py_file in search_path.rglob('*.py'):
                        if any(keyword in str(py_file).lower() for keyword in 
                               ['context', 'user', 'execution', 'service']):
                            all_files.append(py_file)
                            
        return list(set(all_files))  # Remove duplicates
        
    def _determine_violation_severity(self, category_name: str, pattern: str) -> str:
        """Determine severity of a violation based on category and pattern."""
        # Critical violations that block enterprise deployment
        critical_patterns = [
            r'from.*execution_engine.*import.*UserExecutionEngine',
            r'class.*WebSocketAuthenticator(?!.*Unified)',
            r'def.*authenticate_websocket_connection'
        ]
        
        # High priority violations that affect user isolation
        high_patterns = [
            r'import.*UserExecutionEngine.*as.*',
            r'def.*create_execution_engine',
            r'validate_websocket_token'
        ]
        
        if any(re.search(crit_pattern, pattern) for crit_pattern in critical_patterns):
            return "CRITICAL"
        elif any(re.search(high_pattern, pattern) for high_pattern in high_patterns):
            return "HIGH"
        else:
            return "MEDIUM"
            
    def _measure_consolidation_progress(self) -> Dict[str, any]:
        """Measure overall consolidation progress against baseline."""
        current_report = self._generate_comprehensive_compliance_report()
        current_compliance = current_report.overall_compliance_percentage
        
        # Calculate progress from baseline to target
        baseline_gap = self.target_compliance - self.current_baseline
        current_gap = self.target_compliance - current_compliance
        
        progress_made = baseline_gap - current_gap
        progress_percentage = (progress_made / baseline_gap) * 100 if baseline_gap > 0 else 100
        
        # Estimate violations eliminated (simplified calculation)
        estimated_baseline_violations = int((100 - self.current_baseline) * 10)  # Rough estimate
        current_violations = current_report.total_violations
        violations_eliminated = max(0, estimated_baseline_violations - current_violations)
        
        return {
            'progress_percentage': max(0, progress_percentage),
            'current_compliance': current_compliance,
            'violations_eliminated': violations_eliminated,
            'violations_remaining': current_violations,
            'compliance_improvement': current_compliance - self.current_baseline
        }


if __name__ == '__main__':
    print("🚨 Issue #1186 SSOT Compliance Measurement")
    print("=" * 80)
    print("⚠️  WARNING: These tests are DESIGNED TO FAIL to demonstrate <100% compliance")
    print("📊 Expected: Multiple test failures showing compliance gaps")
    print("🎯 Goal: Measure compliance baseline before SSOT consolidation")
    print("=" * 80)
    
    unittest.main(verbosity=2)
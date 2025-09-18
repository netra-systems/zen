#!/usr/bin/env python3
"""
Production SSOT Compliance Gap Validation Test - Issue #1075 Implementation

CRITICAL BUSINESS IMPACT: These tests are designed to FAIL initially and detect the specific 
16.6% compliance gap between claimed (98.7%) and actual (82.1%) SSOT compliance.

This test validates the core finding from Issue #1075 that there is a significant gap 
between claimed and actual SSOT compliance in production code.

DESIGNED TO FAIL: These tests are expected to FAIL initially to prove the violations exist.
Once remediation is complete, these tests should pass.

Business Value: Platform/Infrastructure - Protects $500K+ ARR by ensuring architectural compliance
prevents system failures and development inefficiency.
"""

import ast
import sys
import os
import unittest
import importlib
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict
import re

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.ssot.base_test_case import SSotBaseTestCase


class SsotProductionComplianceValidator:
    """
    Validates actual SSOT compliance in production code to detect the 16.6% gap.
    
    This validator is designed to detect specific violations that create the gap
    between claimed and actual compliance.
    """
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.production_files = self._get_production_files()
        self.violations = []
        
    def _get_production_files(self) -> List[Path]:
        """Get all production Python files (excluding tests)."""
        production_files = []
        
        production_paths = [
            self.project_root / "netra_backend" / "app",
            self.project_root / "auth_service", 
            self.project_root / "shared"
        ]
        
        for path in production_paths:
            if path.exists():
                for file_path in path.rglob("*.py"):
                    # Skip test files, __pycache__, and backup files
                    if (not any(part.startswith('.') or part == '__pycache__' 
                              for part in file_path.relative_to(self.project_root).parts) and
                        'test_' not in file_path.name and 
                        '.backup' not in str(file_path) and
                        'tests/' not in str(file_path)):
                        production_files.append(file_path)
                        
        return production_files
    
    def detect_duplicate_class_definitions(self) -> Dict[str, List[str]]:
        """
        Detect duplicate class definitions across production modules.
        
        This should find significant duplicates that contribute to the compliance gap.
        """
        class_definitions = defaultdict(list)
        
        for file_path in self.production_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            class_definitions[node.name].append(str(file_path))
                            
            except Exception:
                continue
                
        # Return only duplicates
        return {name: paths for name, paths in class_definitions.items() 
                if len(paths) > 1}
    
    def detect_ssot_pattern_violations(self) -> List[Dict[str, Any]]:
        """
        Detect violations of SSOT patterns in production code.
        
        Expected to find multiple manager classes, factory classes, and config classes
        that should be consolidated.
        """
        violations = []
        
        # SSOT patterns that should have single implementations
        ssot_patterns = {
            'Manager': ['WebSocketManager', 'DatabaseManager', 'ConfigManager', 'AuthManager'],
            'Factory': ['WebSocketFactory', 'AgentFactory', 'UserContextFactory'],
            'Service': ['AuthService', 'TokenService', 'ValidationService'],
            'Handler': ['RequestHandler', 'EventHandler', 'MessageHandler'],
            'Config': ['Config', 'Configuration', 'Settings']
        }
        
        for pattern_type, patterns in ssot_patterns.items():
            for pattern in patterns:
                matching_files = []
                
                for file_path in self.production_files:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                            # Check for class definitions matching the pattern
                            if f"class {pattern}" in content or f"class Base{pattern}" in content:
                                matching_files.append(str(file_path))
                                
                    except Exception:
                        continue
                
                if len(matching_files) > 1:
                    violations.append({
                        'pattern': pattern,
                        'type': pattern_type,
                        'file_count': len(matching_files),
                        'files': matching_files,
                        'severity': 'critical'
                    })
                    
        return violations
    
    def detect_import_fragmentation(self) -> List[Dict[str, Any]]:
        """
        Detect import fragmentation that indicates SSOT violations.
        
        This should find multiple import paths for the same functionality.
        """
        import_patterns = defaultdict(set)
        violations = []
        
        # Track imports across all production files
        for file_path in self.production_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for line in lines:
                        line = line.strip()
                        if line.startswith('from ') and 'import' in line:
                            # Extract the module path
                            parts = line.split(' import')[0].replace('from ', '')
                            import_patterns[parts].add(str(file_path))
                            
            except Exception:
                continue
        
        # Look for fragmented import patterns (same functionality, different paths)
        fragmented_patterns = [
            ('websocket', ['websocket_core', 'websocket_manager', 'websocket']),
            ('config', ['config', 'configuration', 'settings']),
            ('auth', ['auth', 'authentication', 'auth_service']),
            ('database', ['db', 'database', 'persistence'])
        ]
        
        for functionality, variant_patterns in fragmented_patterns:
            found_variants = []
            
            for pattern, files in import_patterns.items():
                if any(variant in pattern.lower() for variant in variant_patterns):
                    if functionality in pattern.lower():
                        found_variants.append({
                            'pattern': pattern,
                            'file_count': len(files),
                            'files': list(files)[:3]  # First 3 files as examples
                        })
            
            if len(found_variants) > 2:  # Multiple import patterns for same functionality
                violations.append({
                    'functionality': functionality,
                    'variant_count': len(found_variants),
                    'variants': found_variants,
                    'severity': 'high'
                })
        
        return violations
    
    def calculate_compliance_score(self) -> Dict[str, Any]:
        """
        Calculate actual SSOT compliance score based on detected violations.
        
        This should demonstrate the gap between claimed and actual compliance.
        """
        # Get all violations
        duplicate_classes = self.detect_duplicate_class_definitions()
        pattern_violations = self.detect_ssot_pattern_violations()
        import_violations = self.detect_import_fragmentation()
        
        # Calculate penalty scores
        duplicate_penalty = len(duplicate_classes) * 2  # 2 points per duplicate class
        pattern_penalty = len(pattern_violations) * 5   # 5 points per SSOT pattern violation
        import_penalty = sum(v['variant_count'] for v in import_violations) * 3  # 3 points per import variant
        
        total_penalty = duplicate_penalty + pattern_penalty + import_penalty
        total_files = len(self.production_files)
        
        # Calculate compliance percentage (100% - penalty percentage)
        max_penalty = total_files * 2  # Maximum realistic penalty
        compliance_percentage = max(0, 100 - (total_penalty / max_penalty * 100))
        
        return {
            'compliance_percentage': compliance_percentage,
            'total_files_scanned': total_files,
            'duplicate_classes': len(duplicate_classes),
            'pattern_violations': len(pattern_violations),
            'import_fragmentation_issues': len(import_violations),
            'total_penalty_points': total_penalty,
            'violations': {
                'duplicates': duplicate_classes,
                'patterns': pattern_violations,
                'imports': import_violations
            }
        }


class TestProductionComplianceGapValidation(SSotBaseTestCase):
    """
    Unit tests designed to FAIL initially and prove the 16.6% SSOT compliance gap exists.
    
    These tests validate the core findings from Issue #1075 analysis.
    """
    
    @classmethod
    def setup_class(cls):
        """Setup class-level resources."""
        super().setup_class()
        cls.validator = SsotProductionComplianceValidator(PROJECT_ROOT)
    
    def test_production_compliance_gap_detection(self):
        """
        Test designed to FAIL: Detect significant gap between claimed and actual compliance.
        
        Expected: Actual compliance significantly lower than claimed 98.7%
        This test should FAIL initially to prove the gap exists.
        """
        self.record_metric("test_purpose", "detect_compliance_gap")
        self.record_metric("expected_outcome", "FAIL - prove gap exists")
        
        # Calculate actual compliance
        compliance_results = self.validator.calculate_compliance_score()
        actual_compliance = compliance_results['compliance_percentage']
        
        self.record_metric("actual_compliance_percentage", actual_compliance)
        self.record_metric("total_files_scanned", compliance_results['total_files_scanned'])
        self.record_metric("duplicate_classes_found", compliance_results['duplicate_classes'])
        self.record_metric("pattern_violations_found", compliance_results['pattern_violations'])
        
        # Log detailed findings
        print(f"\n=== PRODUCTION SSOT COMPLIANCE GAP ANALYSIS ===")
        print(f"Files scanned: {compliance_results['total_files_scanned']}")
        print(f"Actual compliance: {actual_compliance:.1f}%")
        print(f"Claimed compliance: 98.7%")
        print(f"Compliance gap: {98.7 - actual_compliance:.1f}%")
        print(f"Duplicate classes: {compliance_results['duplicate_classes']}")
        print(f"SSOT pattern violations: {compliance_results['pattern_violations']}")
        print(f"Import fragmentation issues: {compliance_results['import_fragmentation_issues']}")
        print()
        
        # Show specific examples of violations
        violations = compliance_results['violations']
        
        if violations['duplicates']:
            print("DUPLICATE CLASS EXAMPLES:")
            for class_name, files in list(violations['duplicates'].items())[:3]:
                print(f"  {class_name}: {len(files)} implementations")
                for file_path in files[:2]:  # Show first 2 files
                    print(f"    - {file_path}")
            print()
        
        if violations['patterns']:
            print("SSOT PATTERN VIOLATIONS:")
            for violation in violations['patterns'][:3]:
                print(f"  {violation['pattern']}: {violation['file_count']} implementations")
            print()
        
        # ASSERTION DESIGNED TO FAIL INITIALLY
        # This proves the compliance gap exists
        self.assertGreater(
            actual_compliance, 95.0,
            f"PRODUCTION COMPLIANCE GAP DETECTED: Actual compliance is {actual_compliance:.1f}% "
            f"which is significantly lower than claimed 98.7%. Gap: {98.7 - actual_compliance:.1f}%. "
            f"Found {compliance_results['duplicate_classes']} duplicate classes, "
            f"{compliance_results['pattern_violations']} SSOT pattern violations, "
            f"and {compliance_results['import_fragmentation_issues']} import fragmentation issues."
        )
        
        # Additional assertion to detect specific violation types
        self.assertLess(
            compliance_results['duplicate_classes'], 10,
            f"Too many duplicate classes found: {compliance_results['duplicate_classes']}. "
            f"This indicates significant SSOT violations."
        )
        
        self.assertLess(
            compliance_results['pattern_violations'], 5,
            f"Too many SSOT pattern violations: {compliance_results['pattern_violations']}. "
            f"Multiple implementations of the same patterns violate SSOT principles."
        )
    
    def test_duplicate_class_definition_violations(self):
        """
        Test designed to FAIL: Detect duplicate class definitions in production.
        
        Expected: Significant number of duplicate class definitions
        This should contribute to the compliance gap.
        """
        self.record_metric("test_purpose", "detect_duplicate_classes")
        
        duplicate_classes = self.validator.detect_duplicate_class_definitions()
        total_duplicates = len(duplicate_classes)
        
        self.record_metric("duplicate_classes_detected", total_duplicates)
        
        # Log duplicate class findings
        if duplicate_classes:
            print(f"\n=== DUPLICATE CLASS DEFINITIONS ({total_duplicates} found) ===")
            
            # Show worst offenders (classes with most duplicates)
            sorted_duplicates = sorted(duplicate_classes.items(), 
                                     key=lambda x: len(x[1]), reverse=True)
            
            for class_name, file_paths in sorted_duplicates[:5]:
                print(f"{class_name}: {len(file_paths)} implementations")
                for path in file_paths[:3]:  # Show first 3 paths
                    print(f"  - {path}")
                print()
        
        # ASSERTION DESIGNED TO FAIL INITIALLY
        self.assertLess(
            total_duplicates, 5,
            f"DUPLICATE CLASS VIOLATION: Found {total_duplicates} duplicate class definitions "
            f"in production code. This violates SSOT principles and indicates architectural debt. "
            f"Examples: {list(duplicate_classes.keys())[:3]}"
        )
        
        # Check for critical SSOT pattern duplicates
        critical_patterns = ['Manager', 'Factory', 'Service', 'Handler', 'Config']
        critical_duplicates = {
            name: paths for name, paths in duplicate_classes.items()
            if any(pattern in name for pattern in critical_patterns)
        }
        
        if critical_duplicates:
            self.record_metric("critical_duplicates", len(critical_duplicates))
            
            self.assertEqual(
                len(critical_duplicates), 0,
                f"CRITICAL SSOT VIOLATIONS: Found duplicate implementations of core patterns: "
                f"{list(critical_duplicates.keys())}. These should have single implementations."
            )
    
    def test_ssot_pattern_compliance_violations(self):
        """
        Test designed to FAIL: Detect SSOT pattern violations in production.
        
        Expected: Multiple implementations of patterns that should be singular
        """
        self.record_metric("test_purpose", "detect_pattern_violations")
        
        pattern_violations = self.validator.detect_ssot_pattern_violations()
        total_violations = len(pattern_violations)
        
        self.record_metric("ssot_pattern_violations", total_violations)
        
        if pattern_violations:
            print(f"\n=== SSOT PATTERN VIOLATIONS ({total_violations} found) ===")
            
            for violation in pattern_violations[:5]:  # Show first 5
                print(f"{violation['pattern']} ({violation['type']}): "
                      f"{violation['file_count']} implementations")
                for file_path in violation['files'][:2]:  # Show first 2 files
                    print(f"  - {file_path}")
                print()
        
        # ASSERTION DESIGNED TO FAIL INITIALLY
        self.assertEqual(
            total_violations, 0,
            f"SSOT PATTERN VIOLATIONS: Found {total_violations} violations where single "
            f"implementations should exist. Patterns with multiple implementations: "
            f"{[v['pattern'] for v in pattern_violations[:3]]}"
        )
        
        # Check for critical violations
        critical_violations = [v for v in pattern_violations if v['severity'] == 'critical']
        if critical_violations:
            self.record_metric("critical_pattern_violations", len(critical_violations))
            
            self.assertEqual(
                len(critical_violations), 0,
                f"CRITICAL SSOT PATTERN VIOLATIONS: {len(critical_violations)} critical "
                f"violations found: {[v['pattern'] for v in critical_violations]}"
            )
    
    def test_import_fragmentation_detection(self):
        """
        Test designed to FAIL: Detect import fragmentation indicating SSOT violations.
        
        Expected: Multiple import paths for same functionality
        """
        self.record_metric("test_purpose", "detect_import_fragmentation")
        
        import_violations = self.validator.detect_import_fragmentation()
        total_violations = len(import_violations)
        
        self.record_metric("import_fragmentation_violations", total_violations)
        
        if import_violations:
            print(f"\n=== IMPORT FRAGMENTATION VIOLATIONS ({total_violations} found) ===")
            
            for violation in import_violations:
                print(f"{violation['functionality']}: {violation['variant_count']} import variants")
                for variant in violation['variants'][:2]:  # Show first 2 variants
                    print(f"  - {variant['pattern']} ({variant['file_count']} files)")
                print()
        
        # ASSERTION DESIGNED TO FAIL INITIALLY
        self.assertEqual(
            total_violations, 0,
            f"IMPORT FRAGMENTATION VIOLATIONS: Found {total_violations} cases where "
            f"multiple import paths exist for the same functionality. This indicates "
            f"SSOT violations and architectural fragmentation."
        )
        
        # Check total import variant count
        total_variants = sum(v['variant_count'] for v in import_violations)
        if total_variants > 0:
            self.record_metric("total_import_variants", total_variants)
            
            self.assertLess(
                total_variants, 5,
                f"TOO MANY IMPORT VARIANTS: Found {total_variants} total import variants "
                f"across {total_violations} functionalities. This indicates significant "
                f"architectural fragmentation."
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
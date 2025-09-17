#!/usr/bin/env python3
"""
Duplicate Type Definition Detection Test - Issue #1075 Implementation

CRITICAL BUSINESS IMPACT: This test is designed to FAIL initially and detect the specific
89 duplicate type definitions identified in the Issue #1075 analysis.

This test validates the finding that there are 89 duplicate type definitions across
modules, which contributes significantly to the 16.6% SSOT compliance gap.

DESIGNED TO FAIL: These tests are expected to FAIL initially to prove the violations exist.
The analysis indicated 89 duplicate type definitions - this test should find them.

Business Value: Platform/Infrastructure - Prevents architectural debt accumulation
and development inefficiency caused by duplicate implementations.
"""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict, Counter
import unittest

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.ssot.base_test_case import SSotBaseTestCase


class DuplicateTypeDefinitionDetector:
    """
    Specialized detector for duplicate type definitions across production modules.
    
    Designed to find the specific 89 duplicate type definitions mentioned in Issue #1075.
    """
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.production_files = self._get_production_files()
        self.duplicate_analysis = {}
        
    def _get_production_files(self) -> List[Path]:
        """Get all production Python files, excluding tests and generated files."""
        production_files = []
        
        # Production code paths
        production_paths = [
            self.project_root / "netra_backend" / "app",
            self.project_root / "auth_service",
            self.project_root / "shared",
            self.project_root / "test_framework"  # Include test framework for SSOT analysis
        ]
        
        for path in production_paths:
            if path.exists():
                for file_path in path.rglob("*.py"):
                    relative_path = file_path.relative_to(self.project_root)
                    
                    # Skip test files, backups, pycache, and generated files
                    should_skip = (
                        any(part.startswith('.') or part == '__pycache__' 
                            for part in relative_path.parts) or
                        'test_' in file_path.name or
                        '.backup' in str(file_path) or
                        'tests/' in str(file_path) or
                        'migrations/' in str(file_path) or
                        file_path.name.startswith('test_') or
                        '/tests/' in str(file_path)
                    )
                    
                    if not should_skip:
                        production_files.append(file_path)
        
        return production_files
    
    def detect_duplicate_classes(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detect duplicate class definitions with detailed location information.
        
        Returns:
            Dictionary mapping class names to list of locations where they're defined.
        """
        class_definitions = defaultdict(list)
        
        for file_path in self.production_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            class_info = {
                                'file_path': str(file_path),
                                'line_number': node.lineno,
                                'module_path': self._file_to_module_path(file_path),
                                'class_size': self._estimate_class_size(node, content)
                            }
                            class_definitions[node.name].append(class_info)
                            
            except Exception as e:
                # Log unparseable files but continue
                continue
        
        # Return only duplicates (classes defined in multiple locations)
        duplicates = {
            name: locations for name, locations in class_definitions.items()
            if len(locations) > 1
        }
        
        return duplicates
    
    def detect_duplicate_functions(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detect duplicate function definitions across modules.
        
        Returns:
            Dictionary mapping function names to their locations.
        """
        function_definitions = defaultdict(list)
        
        for file_path in self.production_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            # Skip private functions and common utility names
                            if (not node.name.startswith('_') and 
                                node.name not in ['setUp', 'tearDown', 'main']):
                                
                                function_info = {
                                    'file_path': str(file_path),
                                    'line_number': node.lineno,
                                    'module_path': self._file_to_module_path(file_path),
                                    'is_async': isinstance(node, ast.AsyncFunctionDef)
                                }
                                function_definitions[node.name].append(function_info)
                                
            except Exception:
                continue
        
        # Return only duplicates
        duplicates = {
            name: locations for name, locations in function_definitions.items()
            if len(locations) > 1
        }
        
        return duplicates
    
    def detect_duplicate_type_aliases(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detect duplicate type aliases and TypedDict definitions.
        
        Returns:
            Dictionary mapping type alias names to their locations.
        """
        type_definitions = defaultdict(list)
        
        for file_path in self.production_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        # Type aliases (variable annotations with type hints)
                        if isinstance(node, ast.AnnAssign) and hasattr(node.target, 'id'):
                            type_info = {
                                'file_path': str(file_path),
                                'line_number': node.lineno,
                                'module_path': self._file_to_module_path(file_path),
                                'type': 'type_alias'
                            }
                            type_definitions[node.target.id].append(type_info)
                        
                        # Check for TypedDict and other typing constructs
                        elif isinstance(node, ast.Assign):
                            for target in node.targets:
                                if hasattr(target, 'id'):
                                    # Look for TypedDict patterns in the value
                                    if hasattr(node.value, 'id') and 'TypedDict' in str(node.value.id):
                                        type_info = {
                                            'file_path': str(file_path),
                                            'line_number': node.lineno,
                                            'module_path': self._file_to_module_path(file_path),
                                            'type': 'typed_dict'
                                        }
                                        type_definitions[target.id].append(type_info)
                                        
            except Exception:
                continue
        
        # Return only duplicates
        duplicates = {
            name: locations for name, locations in type_definitions.items()
            if len(locations) > 1
        }
        
        return duplicates
    
    def analyze_ssot_critical_duplicates(self) -> Dict[str, Any]:
        """
        Analyze duplicates that are critical for SSOT compliance.
        
        Returns:
            Analysis of critical SSOT pattern duplicates.
        """
        all_class_duplicates = self.detect_duplicate_classes()
        
        # Critical SSOT patterns that should never be duplicated
        critical_patterns = {
            'Base Classes': ['BaseTestCase', 'BaseTest', 'BaseAsyncTest', 'AsyncTestCase'],
            'Managers': ['Manager', 'ConfigManager', 'DatabaseManager', 'WebSocketManager'],
            'Factories': ['Factory', 'WebSocketFactory', 'AgentFactory', 'UserContextFactory'],
            'Services': ['Service', 'AuthService', 'TokenService', 'ValidationService'],
            'Handlers': ['Handler', 'RequestHandler', 'EventHandler', 'MessageHandler'],
            'Utilities': ['Utility', 'TestUtility', 'MockFactory', 'TestRunner'],
            'Configurations': ['Config', 'Configuration', 'Settings', 'Environment']
        }
        
        critical_violations = {}
        
        for category, patterns in critical_patterns.items():
            category_violations = {}
            
            for pattern in patterns:
                # Find classes that match this pattern
                matching_duplicates = {}
                
                for class_name, locations in all_class_duplicates.items():
                    if (pattern in class_name or 
                        class_name.endswith(pattern) or 
                        class_name.startswith(pattern)):
                        matching_duplicates[class_name] = locations
                
                if matching_duplicates:
                    category_violations[pattern] = matching_duplicates
            
            if category_violations:
                critical_violations[category] = category_violations
        
        return {
            'critical_violations': critical_violations,
            'total_critical_duplicates': sum(
                len(pattern_dups) for category in critical_violations.values()
                for pattern_dups in category.values()
            ),
            'categories_affected': len(critical_violations)
        }
    
    def get_comprehensive_analysis(self) -> Dict[str, Any]:
        """
        Get comprehensive analysis of all duplicate type definitions.
        
        Returns:
            Complete analysis including counts, examples, and severity assessment.
        """
        duplicate_classes = self.detect_duplicate_classes()
        duplicate_functions = self.detect_duplicate_functions()
        duplicate_types = self.detect_duplicate_type_aliases()
        critical_analysis = self.analyze_ssot_critical_duplicates()
        
        total_duplicates = (len(duplicate_classes) + 
                          len(duplicate_functions) + 
                          len(duplicate_types))
        
        return {
            'total_duplicate_types': total_duplicates,
            'duplicate_classes': duplicate_classes,
            'duplicate_functions': duplicate_functions,
            'duplicate_type_aliases': duplicate_types,
            'critical_ssot_violations': critical_analysis,
            'files_scanned': len(self.production_files),
            'severity_assessment': self._assess_severity(total_duplicates, critical_analysis)
        }
    
    def _file_to_module_path(self, file_path: Path) -> str:
        """Convert file path to Python module path."""
        try:
            relative_path = file_path.relative_to(self.project_root)
            module_path = str(relative_path).replace('/', '.').replace('\\', '.')
            if module_path.endswith('.py'):
                module_path = module_path[:-3]
            return module_path
        except ValueError:
            return str(file_path)
    
    def _estimate_class_size(self, node: ast.ClassDef, content: str) -> int:
        """Estimate class size in lines of code."""
        if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
            return node.end_lineno - node.lineno + 1
        return 0
    
    def _assess_severity(self, total_duplicates: int, critical_analysis: Dict) -> str:
        """Assess overall severity of duplicate violations."""
        critical_count = critical_analysis['total_critical_duplicates']
        
        if critical_count > 10 or total_duplicates > 50:
            return 'critical'
        elif critical_count > 5 or total_duplicates > 25:
            return 'high'
        elif critical_count > 2 or total_duplicates > 10:
            return 'medium'
        else:
            return 'low'


class TestDuplicateTypeDefinitionDetection(SSotBaseTestCase):
    """
    Unit tests designed to FAIL initially and detect the 89 duplicate type definitions.
    
    These tests validate the specific finding from Issue #1075 analysis.
    """
    
    @classmethod
    def setup_class(cls):
        """Setup class-level resources."""
        super().setup_class()
        cls.detector = DuplicateTypeDefinitionDetector(PROJECT_ROOT)
    
    def test_detect_duplicate_class_definitions(self):
        """
        Test designed to FAIL: Detect duplicate class definitions across modules.
        
        Expected: Significant number of duplicate class definitions found.
        The analysis indicated 89 total duplicate type definitions.
        """
        self.record_metric("test_purpose", "detect_duplicate_classes")
        self.record_metric("expected_outcome", "FAIL - prove duplicates exist")
        
        duplicate_classes = self.detector.detect_duplicate_classes()
        total_class_duplicates = len(duplicate_classes)
        
        self.record_metric("duplicate_classes_found", total_class_duplicates)
        
        # Log duplicate class findings
        if duplicate_classes:
            print(f"\n=== DUPLICATE CLASS DEFINITIONS ({total_class_duplicates} found) ===")
            
            # Sort by number of duplicates (worst offenders first)
            sorted_duplicates = sorted(duplicate_classes.items(), 
                                     key=lambda x: len(x[1]), reverse=True)
            
            for class_name, locations in sorted_duplicates[:10]:  # Show top 10
                print(f"{class_name}: {len(locations)} implementations")
                for loc in locations[:3]:  # Show first 3 locations
                    print(f"  - {loc['module_path']} (line {loc['line_number']})")
                print()
        
        # ASSERTION DESIGNED TO FAIL INITIALLY
        self.assertLess(
            total_class_duplicates, 5,
            f"DUPLICATE CLASS DEFINITIONS DETECTED: Found {total_class_duplicates} classes "
            f"with multiple implementations across production modules. This violates SSOT "
            f"principles. Examples: {list(duplicate_classes.keys())[:5]}"
        )
        
        # Check for extremely problematic duplicates (>3 implementations)
        extreme_duplicates = {
            name: locations for name, locations in duplicate_classes.items()
            if len(locations) > 3
        }
        
        if extreme_duplicates:
            self.record_metric("extreme_duplicates", len(extreme_duplicates))
            
            self.assertEqual(
                len(extreme_duplicates), 0,
                f"EXTREME DUPLICATION: Found {len(extreme_duplicates)} classes with >3 "
                f"implementations: {list(extreme_duplicates.keys())[:3]}"
            )
    
    def test_detect_ssot_critical_duplicate_patterns(self):
        """
        Test designed to FAIL: Detect duplicates of critical SSOT patterns.
        
        Expected: Multiple implementations of managers, factories, services, etc.
        These are the most critical violations.
        """
        self.record_metric("test_purpose", "detect_critical_ssot_duplicates")
        
        critical_analysis = self.detector.analyze_ssot_critical_duplicates()
        total_critical = critical_analysis['total_critical_duplicates']
        categories_affected = critical_analysis['categories_affected']
        
        self.record_metric("critical_ssot_duplicates", total_critical)
        self.record_metric("categories_affected", categories_affected)
        
        # Log critical SSOT violations
        if critical_analysis['critical_violations']:
            print(f"\n=== CRITICAL SSOT PATTERN DUPLICATES ({total_critical} total) ===")
            
            for category, patterns in critical_analysis['critical_violations'].items():
                print(f"{category}:")
                for pattern, duplicates in patterns.items():
                    total_pattern_duplicates = sum(len(locs) for locs in duplicates.values())
                    print(f"  {pattern}: {len(duplicates)} classes, {total_pattern_duplicates} total implementations")
                    
                    # Show specific examples
                    for class_name, locations in list(duplicates.items())[:2]:
                        print(f"    {class_name}: {len(locations)} implementations")
                print()
        
        # ASSERTION DESIGNED TO FAIL INITIALLY
        self.assertEqual(
            total_critical, 0,
            f"CRITICAL SSOT VIOLATIONS: Found {total_critical} duplicate implementations "
            f"of critical SSOT patterns across {categories_affected} categories. These "
            f"patterns should have single implementations to maintain SSOT compliance."
        )
        
        # Check specific critical patterns
        critical_violations = critical_analysis['critical_violations']
        
        if 'Base Classes' in critical_violations:
            base_class_violations = sum(
                len(duplicates) for duplicates in critical_violations['Base Classes'].values()
            )
            self.assertEqual(
                base_class_violations, 0,
                f"BASE CLASS DUPLICATES: Found {base_class_violations} duplicate base class "
                f"implementations. Test infrastructure should have single base classes."
            )
        
        if 'Managers' in critical_violations:
            manager_violations = sum(
                len(duplicates) for duplicates in critical_violations['Managers'].values()
            )
            self.assertEqual(
                manager_violations, 0,
                f"MANAGER CLASS DUPLICATES: Found {manager_violations} duplicate manager "
                f"implementations. Each manager type should have single implementation."
            )
    
    def test_detect_duplicate_function_definitions(self):
        """
        Test designed to FAIL: Detect duplicate function definitions.
        
        Expected: Multiple functions with same names across modules
        """
        self.record_metric("test_purpose", "detect_duplicate_functions")
        
        duplicate_functions = self.detector.detect_duplicate_functions()
        total_function_duplicates = len(duplicate_functions)
        
        self.record_metric("duplicate_functions_found", total_function_duplicates)
        
        if duplicate_functions:
            print(f"\n=== DUPLICATE FUNCTION DEFINITIONS ({total_function_duplicates} found) ===")
            
            # Show functions with most duplicates
            sorted_duplicates = sorted(duplicate_functions.items(),
                                     key=lambda x: len(x[1]), reverse=True)
            
            for func_name, locations in sorted_duplicates[:5]:
                print(f"{func_name}: {len(locations)} implementations")
                for loc in locations[:2]:  # Show first 2 locations
                    print(f"  - {loc['module_path']} (line {loc['line_number']})")
                print()
        
        # ASSERTION DESIGNED TO FAIL INITIALLY
        self.assertLess(
            total_function_duplicates, 10,
            f"DUPLICATE FUNCTION DEFINITIONS: Found {total_function_duplicates} functions "
            f"with multiple implementations. This indicates code duplication and potential "
            f"SSOT violations. Examples: {list(duplicate_functions.keys())[:5]}"
        )
        
        # Check for utility function duplicates (most problematic)
        utility_functions = {
            name: locations for name, locations in duplicate_functions.items()
            if any(keyword in name.lower() for keyword in 
                  ['create', 'get_config', 'setup', 'initialize', 'validate'])
        }
        
        if utility_functions:
            self.record_metric("utility_function_duplicates", len(utility_functions))
            
            self.assertEqual(
                len(utility_functions), 0,
                f"UTILITY FUNCTION DUPLICATES: Found {len(utility_functions)} duplicate "
                f"utility functions: {list(utility_functions.keys())[:3]}. These should "
                f"be consolidated into shared utilities."
            )
    
    def test_comprehensive_duplicate_type_analysis(self):
        """
        Test designed to FAIL: Comprehensive analysis targeting the 89 duplicate types.
        
        Expected: Total duplicate types approaching or exceeding 89 as reported in analysis.
        """
        self.record_metric("test_purpose", "comprehensive_duplicate_analysis")
        self.record_metric("target_duplicate_count", 89)
        
        analysis = self.detector.get_comprehensive_analysis()
        total_duplicates = analysis['total_duplicate_types']
        
        self.record_metric("total_duplicates_detected", total_duplicates)
        self.record_metric("files_scanned", analysis['files_scanned'])
        self.record_metric("severity_assessment", analysis['severity_assessment'])
        
        # Generate comprehensive report
        print(f"\n{'='*80}")
        print(f"COMPREHENSIVE DUPLICATE TYPE ANALYSIS REPORT")
        print(f"{'='*80}")
        print(f"Files scanned: {analysis['files_scanned']}")
        print(f"Total duplicate types found: {total_duplicates}")
        print(f"Target from analysis: 89 duplicate types")
        print(f"Gap from target: {89 - total_duplicates}")
        print(f"Severity assessment: {analysis['severity_assessment']}")
        print()
        
        print(f"BREAKDOWN:")
        print(f"- Duplicate classes: {len(analysis['duplicate_classes'])}")
        print(f"- Duplicate functions: {len(analysis['duplicate_functions'])}")
        print(f"- Duplicate type aliases: {len(analysis['duplicate_type_aliases'])}")
        print(f"- Critical SSOT violations: {analysis['critical_ssot_violations']['total_critical_duplicates']}")
        print()
        
        # Show worst offenders
        if analysis['duplicate_classes']:
            worst_class = max(analysis['duplicate_classes'].items(), 
                            key=lambda x: len(x[1]))
            print(f"Worst class duplicate: {worst_class[0]} ({len(worst_class[1])} implementations)")
        
        if analysis['duplicate_functions']:
            worst_function = max(analysis['duplicate_functions'].items(),
                               key=lambda x: len(x[1]))
            print(f"Worst function duplicate: {worst_function[0]} ({len(worst_function[1])} implementations)")
        print()
        
        # MAIN ASSERTION DESIGNED TO FAIL INITIALLY
        self.assertLess(
            total_duplicates, 20,
            f"MASSIVE DUPLICATE TYPE VIOLATION: Found {total_duplicates} duplicate type "
            f"definitions across production code. The Issue #1075 analysis indicated 89 "
            f"duplicate types. Current findings: {len(analysis['duplicate_classes'])} "
            f"classes, {len(analysis['duplicate_functions'])} functions, "
            f"{len(analysis['duplicate_type_aliases'])} type aliases. "
            f"Severity: {analysis['severity_assessment']}"
        )
        
        # Validate we're approaching the target number from analysis
        if total_duplicates > 50:
            self.record_metric("approaching_target_89", True)
            
            self.assertLess(
                total_duplicates, 89,
                f"DUPLICATE COUNT APPROACHING ANALYSIS TARGET: Found {total_duplicates} "
                f"duplicate types, approaching the 89 reported in Issue #1075 analysis. "
                f"This confirms the compliance gap findings."
            )
        
        # Check severity assessment
        if analysis['severity_assessment'] in ['critical', 'high']:
            self.record_metric("high_severity_confirmed", True)
            
            self.assertEqual(
                analysis['severity_assessment'], 'low',
                f"HIGH SEVERITY DUPLICATE VIOLATIONS: Severity assessed as "
                f"'{analysis['severity_assessment']}' based on {total_duplicates} "
                f"duplicates and {analysis['critical_ssot_violations']['total_critical_duplicates']} "
                f"critical SSOT violations."
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
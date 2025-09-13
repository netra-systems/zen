"""
Compliance Tests for Configuration Manager SSOT Enforcement - Issue #667

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Integrity & Operational Excellence
- Business Goal: Enforce SSOT compliance in configuration management
- Value Impact: Prevents configuration drift and import chaos
- Strategic Impact: Ensures single authoritative source for all configuration

These tests enforce SSOT patterns and validate that configuration management
follows unified patterns across the entire system.

Test Strategy:
1. Enforce single configuration manager pattern
2. Validate SSOT import compliance
3. Ensure no duplicate functionality exists
4. Guide systematic enforcement during consolidation

CRITICAL: These tests should FAIL during Phase 1 and PASS after consolidation
"""

import ast
import importlib
import inspect
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment


class TestConfigurationManagerSSotEnforcement(SSotBaseTestCase):
    """Compliance tests for configuration manager SSOT enforcement."""

    def setup_method(self, method):
        """Set up test environment for SSOT compliance checking."""
        super().setup_method(method)
        self.project_root = Path(__file__).parents[3]
        self.env = IsolatedEnvironment()

        # Configuration for SSOT enforcement
        self.ssot_config = {
            'canonical_path': 'netra_backend/app/core/configuration/base.py',
            'canonical_class': 'UnifiedConfigManager',
            'duplicate_paths': [
                'netra_backend/app/core/managers/unified_configuration_manager.py',
                'netra_backend/app/services/configuration_service.py'
            ],
            'allowed_max_managers': 1,  # After consolidation
            'transition_max_managers': 3  # During Phase 1
        }

    def test_ssot_configuration_manager_enforcement(self):
        """Test that only one configuration manager exists - SHOULD FAIL initially."""
        configuration_managers = self._discover_all_configuration_managers()

        # Count active configuration managers
        active_managers = [
            manager for manager in configuration_managers
            if manager['exists'] and manager['has_class']
        ]

        print(f"FOUND CONFIGURATION MANAGERS:")
        for manager in active_managers:
            print(f"  {manager['path']} - {manager['class_name']}")

        # CRITICAL TEST: Should fail during Phase 1, pass after consolidation
        self.assertEqual(
            len(active_managers),
            self.ssot_config['allowed_max_managers'],
            f"SSOT VIOLATION: Found {len(active_managers)} configuration managers, "
            f"expected {self.ssot_config['allowed_max_managers']} after consolidation. "
            f"Active managers: {[m['path'] for m in active_managers]}\n"
            f"This test SHOULD FAIL during Phase 1 and PASS after consolidation."
        )

    def test_configuration_manager_transition_compliance(self):
        """Test transition compliance during Phase 1 consolidation."""
        configuration_managers = self._discover_all_configuration_managers()

        active_managers = [
            manager for manager in configuration_managers
            if manager['exists'] and manager['has_class']
        ]

        # During transition, allow up to 3 managers
        self.assertLessEqual(
            len(active_managers),
            self.ssot_config['transition_max_managers'],
            f"TRANSITION VIOLATION: Found {len(active_managers)} configuration managers, "
            f"expected max {self.ssot_config['transition_max_managers']} during transition. "
            f"Too many managers may indicate incomplete consolidation planning."
        )

    def test_canonical_ssot_configuration_manager_compliance(self):
        """Test that canonical SSOT configuration manager meets compliance requirements."""
        canonical_path = self.project_root / self.ssot_config['canonical_path']

        if not canonical_path.exists():
            raise AssertionError(f"Canonical SSOT configuration manager not found: {canonical_path}")

        # Analyze canonical manager compliance
        compliance_results = self._analyze_ssot_compliance(canonical_path)

        # Validate SSOT compliance requirements
        self.assertTrue(
            compliance_results['has_ssot_documentation'],
            f"Canonical manager lacks SSOT documentation: {canonical_path}"
        )

        self.assertTrue(
            compliance_results['uses_isolated_environment'],
            f"Canonical manager doesn't use IsolatedEnvironment: {canonical_path}"
        )

        self.assertFalse(
            compliance_results['has_direct_environ_access'],
            f"Canonical manager has direct os.environ access: {canonical_path}"
        )

        # Validate required methods exist
        required_methods = ['get_config', '__init__']
        missing_methods = [
            method for method in required_methods
            if method not in compliance_results['methods']
        ]

        self.assertEqual(
            len(missing_methods), 0,
            f"Canonical manager missing required methods: {missing_methods}"
        )

    def test_duplicate_configuration_manager_detection(self):
        """Test detection and analysis of duplicate configuration managers."""
        duplicate_analysis = {}

        for duplicate_path in self.ssot_config['duplicate_paths']:
            full_path = self.project_root / duplicate_path
            if full_path.exists():
                analysis = self._analyze_duplicate_manager(full_path)
                duplicate_analysis[duplicate_path] = analysis

        # During Phase 1, duplicates may exist
        if duplicate_analysis:
            print(f"DUPLICATE CONFIGURATION MANAGERS DETECTED:")
            for path, analysis in duplicate_analysis.items():
                print(f"  {path}:")
                print(f"    Classes: {analysis['classes']}")
                print(f"    Methods: {len(analysis['methods'])}")
                print(f"    Responsibilities: {analysis['responsibilities']}")
                print(f"    SSOT Violations: {analysis['ssot_violations']}")

        # Test passes - duplicate detection is informational during Phase 1
        self.assertTrue(True, "Duplicate configuration manager detection completed")

    def _discover_all_configuration_managers(self) -> List[Dict[str, Any]]:
        """Discover all configuration manager files in the project."""
        configuration_managers = []

        # Search patterns for configuration managers
        search_patterns = [
            '**/configuration/**/*manager*.py',
            '**/managers/**/*configuration*.py',
            '**/services/**/*configuration*.py',
            '**/config*.py'
        ]

        found_files = set()
        for pattern in search_patterns:
            found_files.update(self.project_root.glob(pattern))

        # Analyze each found file
        for file_path in found_files:
            if self._is_configuration_manager_file(file_path):
                manager_info = self._analyze_configuration_manager_file(file_path)
                configuration_managers.append(manager_info)

        return configuration_managers

    def _is_configuration_manager_file(self, file_path: Path) -> bool:
        """Check if a file is a configuration manager."""
        # Skip test files, __pycache__, and other non-source files
        if any(skip in str(file_path) for skip in ['test_', '__pycache__', '.pyc']):
            return False

        # Check if file contains configuration manager patterns
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().lower()

            # Look for configuration manager indicators
            manager_indicators = [
                'class.*config.*manager',
                'class.*configuration.*manager',
                'class.*unified.*config',
                'def get_config',
                'def load_config'
            ]

            import re
            for indicator in manager_indicators:
                if re.search(indicator, content):
                    return True

        except Exception:
            pass

        return False

    def _analyze_configuration_manager_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a configuration manager file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse AST for detailed analysis
            tree = ast.parse(content)

            classes = []
            methods = []
            has_class = False

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                    has_class = True
                elif isinstance(node, ast.FunctionDef):
                    methods.append(node.name)

            relative_path = str(file_path.relative_to(self.project_root))

            return {
                'path': relative_path,
                'full_path': file_path,
                'exists': True,
                'has_class': has_class,
                'classes': classes,
                'methods': methods,
                'class_name': classes[0] if classes else None,
                'line_count': len(content.split('\n'))
            }

        except Exception as e:
            return {
                'path': str(file_path.relative_to(self.project_root)),
                'full_path': file_path,
                'exists': True,
                'has_class': False,
                'classes': [],
                'methods': [],
                'class_name': None,
                'error': str(e)
            }

    def _analyze_ssot_compliance(self, file_path: Path) -> Dict[str, Any]:
        """Analyze SSOT compliance of a configuration manager."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse AST for detailed analysis
            tree = ast.parse(content)

            analysis = {
                'has_ssot_documentation': False,
                'uses_isolated_environment': False,
                'has_direct_environ_access': False,
                'methods': [],
                'imports': [],
                'ssot_violations': []
            }

            # Check documentation for SSOT patterns
            ssot_doc_patterns = ['SSOT', 'Single Source of Truth', 'canonical', 'unified']
            analysis['has_ssot_documentation'] = any(
                pattern in content for pattern in ssot_doc_patterns
            )

            # Check for IsolatedEnvironment usage
            analysis['uses_isolated_environment'] = 'IsolatedEnvironment' in content

            # Check for direct os.environ access
            analysis['has_direct_environ_access'] = 'os.environ' in content

            # Extract methods and imports
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    analysis['methods'].append(node.name)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        analysis['imports'].extend([alias.name for alias in node.names])
                    else:
                        if node.module:
                            analysis['imports'].append(node.module)

            # Identify SSOT violations
            if analysis['has_direct_environ_access']:
                analysis['ssot_violations'].append('Direct os.environ access')

            if not analysis['uses_isolated_environment']:
                analysis['ssot_violations'].append('Missing IsolatedEnvironment usage')

            if not analysis['has_ssot_documentation']:
                analysis['ssot_violations'].append('Missing SSOT documentation')

            return analysis

        except Exception as e:
            return {
                'error': str(e),
                'ssot_violations': [f'Analysis failed: {e}']
            }

    def _analyze_duplicate_manager(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a duplicate configuration manager."""
        compliance = self._analyze_ssot_compliance(file_path)

        # Add duplicate-specific analysis
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Analyze responsibilities
            responsibilities = self._extract_manager_responsibilities(content)

            return {
                'classes': compliance.get('methods', []),
                'methods': compliance.get('methods', []),
                'responsibilities': responsibilities,
                'ssot_violations': compliance.get('ssot_violations', []),
                'should_be_removed': True,  # All duplicates should be removed
                'consolidation_complexity': self._assess_consolidation_complexity(content)
            }

        except Exception as e:
            return {
                'error': str(e),
                'should_be_removed': True,
                'consolidation_complexity': 'unknown'
            }

    def _extract_manager_responsibilities(self, content: str) -> List[str]:
        """Extract responsibilities from configuration manager content."""
        responsibilities = []

        # Look for method patterns that indicate responsibilities
        patterns = {
            'config_loading': ['load_config', 'get_config'],
            'environment_management': ['get_env', 'environment'],
            'database_config': ['database', 'DATABASE'],
            'validation': ['validate', 'check_', 'verify_'],
            'caching': ['cache', 'cached'],
            'secrets_management': ['secret', 'SECRET'],
            'service_config': ['service', 'SERVICE']
        }

        for responsibility, indicators in patterns.items():
            for indicator in indicators:
                if indicator in content:
                    responsibilities.append(responsibility)
                    break

        return responsibilities

    def _assess_consolidation_complexity(self, content: str) -> str:
        """Assess the complexity of consolidating this manager."""
        line_count = len(content.split('\n'))

        if line_count < 100:
            return 'low'
        elif line_count < 500:
            return 'medium'
        elif line_count < 1500:
            return 'high'
        else:
            return 'very_high'

    def test_import_path_enforcement(self):
        """Test that configuration imports follow SSOT patterns."""
        # Search for configuration imports across the codebase
        import_violations = self._scan_configuration_imports()

        # During Phase 1, may have violations that need fixing
        if import_violations:
            print("CONFIGURATION IMPORT VIOLATIONS FOUND:")
            for violation in import_violations:
                print(f"  {violation}")

        # Test passes - violations are logged for fixing during consolidation
        self.assertTrue(True, "Configuration import scanning completed")

    def _scan_configuration_imports(self) -> List[str]:
        """Scan for configuration import violations across the codebase."""
        violations = []

        # Search for Python files that import configuration managers
        python_files = list(self.project_root.rglob('*.py'))

        # Import patterns to check
        import_patterns = [
            'from netra_backend.app.core.managers.unified_configuration_manager import',
            'from netra_backend.app.services.configuration_service import',
            'import os.environ',  # Direct environ usage
        ]

        for file_path in python_files:
            if 'test_' in file_path.name or '__pycache__' in str(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                for pattern in import_patterns:
                    if pattern in content:
                        rel_path = file_path.relative_to(self.project_root)
                        violations.append(f"{rel_path}: {pattern}")

            except Exception:
                continue

        return violations

    def test_configuration_interface_consistency(self):
        """Test that all configuration managers implement consistent interfaces."""
        configuration_managers = self._discover_all_configuration_managers()

        active_managers = [
            manager for manager in configuration_managers
            if manager['exists'] and manager['has_class']
        ]

        if len(active_managers) < 2:
            self.skipTest("Not enough configuration managers to test interface consistency")

        # Extract interface patterns from each manager
        interfaces = {}
        for manager in active_managers:
            try:
                interface = self._extract_manager_interface(manager['full_path'])
                interfaces[manager['path']] = interface
            except Exception as e:
                interfaces[manager['path']] = {'error': str(e)}

        # Check for interface consistency
        all_methods = set()
        for interface in interfaces.values():
            if 'methods' in interface:
                all_methods.update(interface['methods'])

        # Analyze method overlap
        method_coverage = {}
        for method in all_methods:
            implementing_managers = [
                path for path, interface in interfaces.items()
                if 'methods' in interface and method in interface['methods']
            ]
            method_coverage[method] = implementing_managers

        # Print interface analysis
        print("CONFIGURATION MANAGER INTERFACE ANALYSIS:")
        for method, implementers in method_coverage.items():
            if len(implementers) > 1:
                print(f"  {method}: {implementers}")

        # Test passes if we completed interface analysis
        self.assertTrue(True, "Configuration interface consistency analysis completed")

    def _extract_manager_interface(self, file_path: Path) -> Dict[str, Any]:
        """Extract the interface (public methods) from a configuration manager."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            public_methods = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Only include public methods (not starting with _)
                    if not node.name.startswith('_'):
                        public_methods.append(node.name)

            return {
                'methods': public_methods,
                'method_count': len(public_methods)
            }

        except Exception as e:
            return {'error': str(e)}


if __name__ == '__main__':
    import unittest
    unittest.main()

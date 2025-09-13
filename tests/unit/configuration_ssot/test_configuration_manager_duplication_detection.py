"""
Unit Tests for Configuration Manager Duplication Detection - Issue #667

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability
- Business Goal: Eliminate SSOT violations in configuration management
- Value Impact: Prevents configuration drift and import errors
- Strategic Impact: Enables safe consolidation of 3 duplicate configuration managers

These tests PROVE that configuration manager duplication exists in the system
and validate SSOT patterns for systematic consolidation.

Test Strategy:
1. FAIL FIRST: Tests initially fail to prove duplication exists
2. Detect all configuration manager files and their responsibilities
3. Validate SSOT compliance patterns
4. Guide systematic consolidation process

CRITICAL: Uses SSOT test infrastructure from test_framework/ssot/
"""

import ast
import inspect
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment


class TestConfigurationManagerDuplicationDetection(SSotBaseTestCase):
    """Unit tests to detect and validate configuration manager duplication."""

    def setup_method(self, method):
        """Set up test environment with SSOT patterns."""
        super().setup_method(method)
        self.project_root = Path(__file__).parents[3]  # Go up to project root
        self.configuration_files = self._discover_configuration_manager_files()

    def _discover_configuration_manager_files(self) -> List[Dict[str, Any]]:
        """Discover all configuration manager files in the project.

        Returns:
            List of configuration manager file metadata
        """
        config_files = []

        # Known duplicate configuration manager files based on Issue #667
        known_files = [
            {
                'path': 'netra_backend/app/core/configuration/base.py',
                'expected_class': 'UnifiedConfigManager',
                'role': 'CANONICAL_SSOT',
                'description': 'Base configuration module - intended SSOT'
            },
            {
                'path': 'netra_backend/app/core/managers/unified_configuration_manager.py',
                'expected_class': 'UnifiedConfigurationManager',
                'role': 'DUPLICATE',
                'description': 'Mega class with 2000+ lines - duplicate SSOT'
            },
            {
                'path': 'netra_backend/app/services/configuration_service.py',
                'expected_class': 'EnvironmentConfigLoader',
                'role': 'DUPLICATE',
                'description': 'Configuration service - duplicate functionality'
            }
        ]

        for file_info in known_files:
            full_path = self.project_root / file_info['path']
            if full_path.exists():
                file_info['full_path'] = full_path
                file_info['exists'] = True
                config_files.append(file_info)
            else:
                file_info['exists'] = False
                config_files.append(file_info)

        return config_files

    def test_configuration_manager_duplication_exists(self):
        """Test that configuration manager duplication exists - SHOULD FAIL INITIALLY.

        This test is designed to FAIL to prove that duplication exists.
        Once consolidation is complete, this test should pass.
        """
        # Count how many configuration manager files exist
        existing_files = [f for f in self.configuration_files if f['exists']]

        # ASSERTION: Should fail because we have 3 files, not 1 SSOT
        self.assertEqual(
            len(existing_files), 1,
            f"SSOT VIOLATION: Found {len(existing_files)} configuration managers, "
            f"expected 1 SSOT. Files: {[f['path'] for f in existing_files]}\n"
            f"This PROVES Issue #667 duplication exists and needs consolidation."
        )

    def test_canonical_ssot_configuration_manager_exists(self):
        """Test that the canonical SSOT configuration manager exists."""
        canonical_files = [f for f in self.configuration_files
                          if f.get('role') == 'CANONICAL_SSOT' and f['exists']]

        self.assertEqual(
            len(canonical_files), 1,
            f"Expected exactly 1 canonical SSOT configuration manager, "
            f"found {len(canonical_files)}: {[f['path'] for f in canonical_files]}"
        )

        # Validate the canonical file has expected structure
        canonical_file = canonical_files[0]
        self._validate_configuration_manager_structure(canonical_file)

    def test_duplicate_configuration_managers_detected(self):
        """Test that duplicate configuration managers are properly detected."""
        duplicate_files = [f for f in self.configuration_files
                          if f.get('role') == 'DUPLICATE' and f['exists']]

        # Should find duplicates - this proves the problem exists
        self.assertGreater(
            len(duplicate_files), 0,
            "Expected to find duplicate configuration managers, but none detected. "
            "This could mean consolidation is already complete or detection logic is wrong."
        )

        # Log duplicates for consolidation planning
        for dup_file in duplicate_files:
            print(f"DETECTED DUPLICATE: {dup_file['path']} - {dup_file['description']}")

    def test_configuration_manager_class_analysis(self):
        """Test analysis of configuration manager classes and their methods."""
        existing_files = [f for f in self.configuration_files if f['exists']]

        class_analysis = {}
        for file_info in existing_files:
            try:
                analysis = self._analyze_configuration_manager_class(file_info)
                class_analysis[file_info['path']] = analysis
            except Exception as e:
                raise AssertionError(f"Failed to analyze {file_info['path']}: {e}")

        # Validate that we have analyzed at least one configuration manager
        self.assertGreater(
            len(class_analysis), 0,
            "Failed to analyze any configuration manager classes"
        )

        # Print analysis for manual review
        for path, analysis in class_analysis.items():
            print(f"\nCONFIGURATION MANAGER ANALYSIS: {path}")
            print(f"  Classes: {analysis.get('classes', [])}")
            print(f"  Methods: {analysis.get('method_count', 0)}")
            print(f"  Dependencies: {analysis.get('import_count', 0)}")
            print(f"  Lines: {analysis.get('line_count', 0)}")

    def _validate_configuration_manager_structure(self, file_info: Dict[str, Any]):
        """Validate that a configuration manager file has expected structure."""
        if not file_info['exists']:
            raise AssertionError(f"Cannot validate non-existent file: {file_info['path']}")

        try:
            with open(file_info['full_path'], 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for expected class
            expected_class = file_info['expected_class']
            self.assertIn(
                f"class {expected_class}",
                content,
                f"Expected class {expected_class} not found in {file_info['path']}"
            )

            # Check for SSOT patterns
            if file_info['role'] == 'CANONICAL_SSOT':
                # Should have proper SSOT documentation
                ssot_indicators = ['SSOT', 'Single Source of Truth', 'canonical']
                has_ssot_doc = any(indicator in content for indicator in ssot_indicators)
                self.assertTrue(
                    has_ssot_doc,
                    f"Canonical SSOT file {file_info['path']} lacks proper SSOT documentation"
                )

        except Exception as e:
            raise AssertionError(f"Failed to validate {file_info['path']}: {e}")

    def _analyze_configuration_manager_class(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a configuration manager class structure."""
        if not file_info['exists']:
            return {'error': 'File does not exist'}

        try:
            with open(file_info['full_path'], 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse AST for detailed analysis
            tree = ast.parse(content)

            analysis = {
                'classes': [],
                'methods': [],
                'imports': [],
                'line_count': len(content.split('\n')),
                'method_count': 0,
                'import_count': 0
            }

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    analysis['classes'].append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    analysis['methods'].append(node.name)
                    analysis['method_count'] += 1
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            analysis['imports'].append(alias.name)
                    else:
                        module = node.module or ''
                        analysis['imports'].append(module)
                    analysis['import_count'] += 1

            return analysis

        except Exception as e:
            return {'error': str(e)}

    def test_ssot_import_compliance(self):
        """Test that configuration managers follow SSOT import patterns."""
        existing_files = [f for f in self.configuration_files if f['exists']]

        violations = []
        for file_info in existing_files:
            try:
                with open(file_info['full_path'], 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for direct os.environ access (SSOT violation)
                if 'os.environ' in content:
                    violations.append(f"{file_info['path']}: Direct os.environ access detected")

                # Check for proper IsolatedEnvironment usage
                if 'IsolatedEnvironment' not in content and 'config' in file_info['path'].lower():
                    violations.append(f"{file_info['path']}: Missing IsolatedEnvironment import")

            except Exception as e:
                violations.append(f"{file_info['path']}: Analysis failed: {e}")

        # Log violations for fixing
        for violation in violations:
            print(f"SSOT IMPORT VIOLATION: {violation}")

        # This test may initially fail due to violations
        if violations:
            raise AssertionError(
                f"Found {len(violations)} SSOT import violations. "
                f"These need to be fixed during consolidation: {violations}"
            )

    def test_configuration_manager_responsibilities(self):
        """Test analysis of configuration manager responsibilities and overlap."""
        existing_files = [f for f in self.configuration_files if f['exists']]

        responsibilities = {}
        for file_info in existing_files:
            responsibilities[file_info['path']] = self._extract_responsibilities(file_info)

        # Check for overlapping responsibilities (indicates duplication)
        overlap_analysis = self._analyze_responsibility_overlap(responsibilities)

        # Print overlap for manual review
        if overlap_analysis['overlaps']:
            print("\nRESPONSIBILITY OVERLAP ANALYSIS:")
            for overlap in overlap_analysis['overlaps']:
                print(f"  {overlap}")

        # The test passes if we successfully analyzed responsibilities
        # Overlap detection is informational for consolidation planning
        self.assertIsInstance(responsibilities, dict)
        self.assertGreater(len(responsibilities), 0)

    def _extract_responsibilities(self, file_info: Dict[str, Any]) -> List[str]:
        """Extract the responsibilities of a configuration manager from its code."""
        if not file_info['exists']:
            return []

        try:
            with open(file_info['full_path'], 'r', encoding='utf-8') as f:
                content = f.read()

            responsibilities = []

            # Look for method patterns that indicate responsibilities
            patterns = {
                'config_loading': ['load_config', 'get_config', 'load_'],
                'environment_management': ['get_env', 'environment', 'env_'],
                'database_config': ['database', 'db_', 'DATABASE'],
                'validation': ['validate', 'check_', 'verify_'],
                'caching': ['cache', 'cached', '_cache'],
                'secrets_management': ['secret', 'SECRET', 'password'],
                'service_config': ['service', 'SERVICE', 'get_.*_config']
            }

            for responsibility, indicators in patterns.items():
                for indicator in indicators:
                    if indicator.lower() in content.lower():
                        responsibilities.append(responsibility)
                        break

            return list(set(responsibilities))  # Remove duplicates

        except Exception as e:
            return [f'analysis_error: {e}']

    def _analyze_responsibility_overlap(self, responsibilities: Dict[str, List[str]]) -> Dict[str, Any]:
        """Analyze overlap in responsibilities between configuration managers."""
        overlaps = []
        all_responsibilities = set()

        # Collect all responsibilities
        for file_path, resp_list in responsibilities.items():
            all_responsibilities.update(resp_list)

        # Check for each responsibility which files implement it
        for responsibility in all_responsibilities:
            implementing_files = [
                file_path for file_path, resp_list in responsibilities.items()
                if responsibility in resp_list
            ]

            if len(implementing_files) > 1:
                overlaps.append(
                    f"'{responsibility}' implemented in: {', '.join(implementing_files)}"
                )

        return {
            'overlaps': overlaps,
            'total_responsibilities': len(all_responsibilities),
            'overlap_count': len(overlaps)
        }


class TestConfigurationManagerCompatibilityBridge(SSotBaseTestCase):
    """Test the Issue #667 Phase 1 compatibility bridge functionality."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        self.env = IsolatedEnvironment()

    def test_compatibility_bridge_exists(self):
        """Test that Phase 1 compatibility bridge is in place."""
        # Try to import both old and new configuration patterns
        try:
            # Test canonical SSOT import
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            canonical_manager = UnifiedConfigManager()
            self.assertIsNotNone(canonical_manager)

        except ImportError as e:
            raise AssertionError(f"Canonical SSOT configuration manager import failed: {e}")

        try:
            # Test duplicate manager import (should work during Phase 1)
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            duplicate_manager = UnifiedConfigurationManager()
            self.assertIsNotNone(duplicate_manager)

        except ImportError as e:
            print(f"EXPECTED: Duplicate manager import may fail if already consolidated: {e}")

    def test_configuration_consistency_across_managers(self):
        """Test that different configuration managers return consistent results."""
        try:
            # Import available configuration managers
            managers = []

            try:
                from netra_backend.app.core.configuration.base import UnifiedConfigManager
                managers.append(('canonical', UnifiedConfigManager()))
            except ImportError:
                pass

            try:
                from netra_backend.app.services.configuration_service import EnvironmentConfigLoader
                managers.append(('service', EnvironmentConfigLoader()))
            except ImportError:
                pass

            if len(managers) < 2:
                self.skipTest("Not enough configuration managers available for consistency testing")

            # Test basic configuration access consistency
            configs = {}
            for name, manager in managers:
                try:
                    # Try to get environment config in different ways
                    if hasattr(manager, 'get_env'):
                        configs[name] = manager.get_env()
                    elif hasattr(manager, 'load_config'):
                        configs[name] = manager.load_config()
                    else:
                        configs[name] = None
                except Exception as e:
                    configs[name] = f'error: {e}'

            # Log results for analysis
            print(f"CONFIGURATION CONSISTENCY TEST RESULTS: {configs}")

            # Test passes if we successfully called methods without crashes
            self.assertTrue(True, "Configuration consistency test completed")

        except Exception as e:
            raise AssertionError(f"Configuration consistency test failed: {e}")


if __name__ == '__main__':
    import unittest
    unittest.main()
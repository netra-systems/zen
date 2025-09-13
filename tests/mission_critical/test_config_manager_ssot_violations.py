"""
Test SSOT Config Manager Violations - Issue #667

EXPECTED TO FAIL - Reproduces Current SSOT Violations

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability - Prevent $120K+ MRR Golden Path failures
- Value Impact: Demonstrates how 3 duplicate config managers create auth failures
- Strategic Impact: Provides clear evidence of SSOT violations blocking Golden Path

PURPOSE: This test is EXPECTED TO FAIL until Issue #667 is resolved.
It demonstrates the exact SSOT violations that cause Golden Path auth failures.

Test Coverage:
1. Import conflicts between 3 configuration managers
2. Method signature conflicts causing runtime errors
3. Environment access pattern violations
4. Auth configuration conflicts affecting login flow

CRITICAL: This test protects $500K+ ARR by detecting configuration management
failures that prevent user login and AI chat functionality.
"""

import pytest
import sys
from typing import Any, Dict, List
import importlib
import inspect
from unittest.mock import patch, MagicMock

# Import test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestConfigManagerSSotViolations(SSotBaseTestCase):
    """Test suite to reproduce and validate config manager SSOT violations."""

    def test_config_manager_import_conflicts_detected(self):
        """
        EXPECTED TO FAIL - Detect import conflicts between 3 config managers.

        This test demonstrates how having 3 different configuration managers
        creates import conflicts that break Golden Path auth functionality.
        """
        # Expected imports that create conflicts
        config_managers = [
            "netra_backend.app.core.configuration.base.UnifiedConfigManager",
            "netra_backend.app.core.managers.unified_configuration_manager.UnifiedConfigurationManager",
            "netra_backend.app.services.configuration_service.ConfigurationManager"
        ]

        imported_managers = []
        import_errors = []

        # Attempt to import all three managers
        for manager_path in config_managers:
            try:
                module_path, class_name = manager_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                manager_class = getattr(module, class_name)
                imported_managers.append({
                    'path': manager_path,
                    'class': manager_class,
                    'methods': [m for m in dir(manager_class) if not m.startswith('_')]
                })
            except ImportError as e:
                import_errors.append(f"Failed to import {manager_path}: {str(e)}")
            except AttributeError as e:
                import_errors.append(f"Class not found in {manager_path}: {str(e)}")

        # TEST ASSERTION: This should fail because all 3 managers exist and conflict
        assert len(imported_managers) < 3, (
            f"SSOT VIOLATION: Found {len(imported_managers)} config managers, should be only 1. "
            f"Managers found: {[m['path'] for m in imported_managers]}. "
            f"Import errors: {import_errors}. "
            f"This violates SSOT principles and causes auth configuration conflicts."
        )

    def test_config_manager_method_signature_conflicts(self):
        """
        EXPECTED TO FAIL - Detect method signature conflicts between managers.

        Different config managers may have conflicting method signatures
        for the same functionality, causing runtime errors.
        """
        # Import the managers that exist
        managers_to_test = []

        try:
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            managers_to_test.append(('UnifiedConfigManager', UnifiedConfigManager))
        except ImportError:
            pass

        try:
            from netra_backend.app.core.managers.unified_configuration_manager import UnifiedConfigurationManager
            managers_to_test.append(('UnifiedConfigurationManager', UnifiedConfigurationManager))
        except ImportError:
            pass

        try:
            from netra_backend.app.services.configuration_service import ConfigurationManager
            managers_to_test.append(('ConfigurationManager', ConfigurationManager))
        except ImportError:
            pass

        if len(managers_to_test) < 2:
            pytest.skip("Need at least 2 config managers to test conflicts")

        # Check for conflicting method signatures
        method_conflicts = []
        common_methods = ['get_config']  # Methods that should be consistent

        for method_name in common_methods:
            signatures = {}
            for manager_name, manager_class in managers_to_test:
                if hasattr(manager_class, method_name):
                    method = getattr(manager_class, method_name)
                    if callable(method):
                        sig = inspect.signature(method)
                        signatures[manager_name] = str(sig)

            # Check for signature conflicts
            if len(set(signatures.values())) > 1:
                method_conflicts.append({
                    'method': method_name,
                    'signatures': signatures
                })

        # TEST ASSERTION: This should fail if method signature conflicts exist
        assert len(method_conflicts) == 0, (
            f"SSOT VIOLATION: Method signature conflicts detected: {method_conflicts}. "
            f"Different config managers have incompatible method signatures, "
            f"causing runtime errors in Golden Path auth flow."
        )

    def test_environment_access_ssot_violations_detected(self):
        """
        EXPECTED TO FAIL - Detect direct os.environ access violations in config managers.

        Config managers should use IsolatedEnvironment, not direct os.environ access.
        This test scans for violations that cause environment detection failures.
        """
        import os
        import ast
        from pathlib import Path

        config_manager_files = [
            "netra_backend/app/core/configuration/base.py",
            "netra_backend/app/core/managers/unified_configuration_manager.py",
            "netra_backend/app/services/configuration_service.py"
        ]

        violations = []

        for file_path in config_manager_files:
            full_path = Path(file_path)
            if full_path.exists():
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Parse AST to find os.environ usage
                    tree = ast.parse(content)

                    for node in ast.walk(tree):
                        if isinstance(node, ast.Attribute):
                            # Check for os.environ access
                            if (isinstance(node.value, ast.Name) and
                                node.value.id == 'os' and
                                node.attr == 'environ'):
                                violations.append({
                                    'file': file_path,
                                    'line': node.lineno,
                                    'violation': 'Direct os.environ access'
                                })
                        elif isinstance(node, ast.Call):
                            # Check for os.getenv calls
                            if (isinstance(node.func, ast.Attribute) and
                                isinstance(node.func.value, ast.Name) and
                                node.func.value.id == 'os' and
                                node.func.attr == 'getenv'):
                                violations.append({
                                    'file': file_path,
                                    'line': node.lineno,
                                    'violation': 'Direct os.getenv access'
                                })

                except Exception as e:
                    violations.append({
                        'file': file_path,
                        'error': f"Failed to parse: {str(e)}"
                    })

        # TEST ASSERTION: This should fail if os.environ violations exist
        assert len(violations) == 0, (
            f"SSOT VIOLATION: Found {len(violations)} direct os.environ access violations: {violations}. "
            f"Config managers must use IsolatedEnvironment for SSOT compliance. "
            f"Direct environment access causes Golden Path environment detection failures."
        )

    def test_auth_configuration_conflicts_affect_golden_path(self):
        """
        EXPECTED TO FAIL - Demonstrate auth config conflicts blocking Golden Path.

        Different config managers may return different auth configurations,
        causing login failures in the Golden Path user flow.
        """
        config_managers = []

        # Collect available config managers
        try:
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            config_managers.append(('UnifiedConfigManager', UnifiedConfigManager()))
        except Exception:
            pass

        try:
            from netra_backend.app.core.managers.unified_configuration_manager import UnifiedConfigurationManager
            config_managers.append(('UnifiedConfigurationManager', UnifiedConfigurationManager()))
        except Exception:
            pass

        try:
            from netra_backend.app.services.configuration_service import ConfigurationManager
            config_managers.append(('ConfigurationManager', ConfigurationManager()))
        except Exception:
            pass

        if len(config_managers) < 2:
            pytest.skip("Need at least 2 config managers to test auth conflicts")

        # Test auth-related configuration consistency
        auth_config_keys = [
            'JWT_SECRET_KEY',
            'JWT_ALGORITHM',
            'AUTH_SERVICE_URL',
            'SESSION_TIMEOUT'
        ]

        config_conflicts = []

        for key in auth_config_keys:
            values = {}
            for manager_name, manager_instance in config_managers:
                try:
                    if hasattr(manager_instance, 'get_config'):
                        value = manager_instance.get_config(key)
                        values[manager_name] = value
                    elif hasattr(manager_instance, 'get'):
                        value = manager_instance.get(key)
                        values[manager_name] = value
                except Exception as e:
                    values[manager_name] = f"ERROR: {str(e)}"

            # Check for conflicts (different values for same key)
            unique_values = set(str(v) for v in values.values() if v is not None)
            if len(unique_values) > 1:
                config_conflicts.append({
                    'key': key,
                    'values': values
                })

        # TEST ASSERTION: This should fail if auth config conflicts exist
        assert len(config_conflicts) == 0, (
            f"SSOT VIOLATION: Auth configuration conflicts detected: {config_conflicts}. "
            f"Different config managers return different auth settings, "
            f"causing Golden Path login failures worth $500K+ ARR protection."
        )

    def test_config_manager_singleton_vs_factory_pattern_conflicts(self):
        """
        EXPECTED TO FAIL - Detect singleton vs factory pattern conflicts.

        Mixed singleton and factory patterns in config managers create
        race conditions and state sharing issues in multi-user scenarios.
        """
        singleton_managers = []
        factory_managers = []

        # Check UnifiedConfigManager pattern
        try:
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            manager1 = UnifiedConfigManager()
            manager2 = UnifiedConfigManager()

            if manager1 is manager2:
                singleton_managers.append('UnifiedConfigManager')
            else:
                factory_managers.append('UnifiedConfigManager')
        except Exception:
            pass

        # Check UnifiedConfigurationManager pattern
        try:
            from netra_backend.app.core.managers.unified_configuration_manager import UnifiedConfigurationManager
            manager1 = UnifiedConfigurationManager()
            manager2 = UnifiedConfigurationManager()

            if manager1 is manager2:
                singleton_managers.append('UnifiedConfigurationManager')
            else:
                factory_managers.append('UnifiedConfigurationManager')
        except Exception:
            pass

        # Check ConfigurationManager pattern
        try:
            from netra_backend.app.services.configuration_service import ConfigurationManager
            manager1 = ConfigurationManager()
            manager2 = ConfigurationManager()

            if manager1 is manager2:
                singleton_managers.append('ConfigurationManager')
            else:
                factory_managers.append('ConfigurationManager')
        except Exception:
            pass

        # TEST ASSERTION: This should fail if mixed patterns exist
        has_mixed_patterns = len(singleton_managers) > 0 and len(factory_managers) > 0

        assert not has_mixed_patterns, (
            f"SSOT VIOLATION: Mixed singleton/factory patterns detected. "
            f"Singleton managers: {singleton_managers}, Factory managers: {factory_managers}. "
            f"This creates race conditions and state sharing issues in Golden Path multi-user scenarios."
        )


if __name__ == "__main__":
    # Run the test to demonstrate current violations
    pytest.main([__file__, "-v", "--tb=short", "-x"])
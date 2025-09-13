"""
Test Configuration Environment Access SSOT Violations - Issue #667

EXPECTED TO FAIL - Detects Current Environment Access Violations

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Environment Detection Reliability - Prevent Golden Path failures
- Value Impact: Validates SSOT environment access patterns prevent configuration drift
- Strategic Impact: Protects $500K+ ARR by ensuring consistent environment detection

PURPOSE: This test is EXPECTED TO FAIL until all config managers use IsolatedEnvironment.
It detects the 51 os.environ violations that cause environment detection failures.

Test Coverage:
1. Direct os.environ access violations in config managers
2. Non-SSOT environment variable access patterns
3. Configuration drift between environments
4. Environment detection reliability issues

CRITICAL: Environmental configuration failures block user login and AI chat
functionality, directly impacting $500K+ ARR Golden Path revenue protection.
"""

import pytest
import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Set
import importlib
import inspect
from unittest.mock import patch, MagicMock

# Import test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestConfigEnvironmentAccessSSot(SSotBaseTestCase):
    """Test suite to detect environment access SSOT violations in config managers."""

    def test_config_managers_use_isolated_environment_only(self):
        """
        EXPECTED TO FAIL - Validate config managers use IsolatedEnvironment ONLY.

        Config managers must use IsolatedEnvironment for SSOT compliance.
        Direct os.environ access causes configuration drift and environment detection failures.
        """
        config_manager_modules = [
            "netra_backend.app.core.configuration.base",
            "netra_backend.app.core.managers.unified_configuration_manager",
            "netra_backend.app.services.configuration_service"
        ]

        os_environ_violations = []
        missing_isolated_env_imports = []

        for module_name in config_manager_modules:
            try:
                # Get module file path
                module = importlib.import_module(module_name)
                if hasattr(module, '__file__') and module.__file__:
                    file_path = Path(module.__file__)

                    # Read and parse the source code
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source_code = f.read()

                    # Check for IsolatedEnvironment import
                    has_isolated_env_import = (
                        'from shared.isolated_environment import' in source_code or
                        'import shared.isolated_environment' in source_code or
                        'from dev_launcher.isolated_environment import' in source_code
                    )

                    if not has_isolated_env_import:
                        missing_isolated_env_imports.append(module_name)

                    # Parse AST to find os.environ violations
                    try:
                        tree = ast.parse(source_code)
                        violations = self._find_os_environ_violations(tree, str(file_path))
                        os_environ_violations.extend(violations)
                    except SyntaxError as e:
                        os_environ_violations.append({
                            'file': str(file_path),
                            'line': e.lineno,
                            'violation': f'Syntax error during AST parsing: {str(e)}'
                        })

            except ImportError as e:
                # Module doesn't exist - this is expected during SSOT consolidation
                pass
            except Exception as e:
                os_environ_violations.append({
                    'module': module_name,
                    'error': f'Failed to analyze: {str(e)}'
                })

        # TEST ASSERTION: Should fail if os.environ violations exist
        assert len(os_environ_violations) == 0, (
            f"SSOT VIOLATION: Found {len(os_environ_violations)} direct os.environ access violations "
            f"in config managers: {os_environ_violations}. "
            f"Missing IsolatedEnvironment imports: {missing_isolated_env_imports}. "
            f"Config managers MUST use IsolatedEnvironment for SSOT compliance."
        )

    def test_no_direct_os_getenv_usage_in_config_managers(self):
        """
        EXPECTED TO FAIL - Detect direct os.getenv usage in config managers.

        Direct os.getenv calls bypass SSOT environment management and
        cause configuration inconsistencies across environments.
        """
        config_files = [
            "netra_backend/app/core/configuration/base.py",
            "netra_backend/app/core/managers/unified_configuration_manager.py",
            "netra_backend/app/services/configuration_service.py",
            "netra_backend/app/core/configuration/loader.py",
            "netra_backend/app/core/configuration/validator.py"
        ]

        os_getenv_violations = []

        for file_path in config_files:
            full_path = Path(file_path)
            if full_path.exists():
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Simple string search for os.getenv patterns
                    lines = content.split('\n')
                    for line_num, line in enumerate(lines, 1):
                        line_stripped = line.strip()
                        if 'os.getenv' in line_stripped and not line_stripped.startswith('#'):
                            os_getenv_violations.append({
                                'file': file_path,
                                'line': line_num,
                                'content': line_stripped,
                                'violation': 'Direct os.getenv usage'
                            })
                        if 'os.environ[' in line_stripped and not line_stripped.startswith('#'):
                            os_getenv_violations.append({
                                'file': file_path,
                                'line': line_num,
                                'content': line_stripped,
                                'violation': 'Direct os.environ[] access'
                            })
                        if 'os.environ.get(' in line_stripped and not line_stripped.startswith('#'):
                            os_getenv_violations.append({
                                'file': file_path,
                                'line': line_num,
                                'content': line_stripped,
                                'violation': 'Direct os.environ.get() access'
                            })

                except Exception as e:
                    os_getenv_violations.append({
                        'file': file_path,
                        'error': f'Failed to read file: {str(e)}'
                    })

        # TEST ASSERTION: Should fail if direct os access violations exist
        assert len(os_getenv_violations) == 0, (
            f"SSOT VIOLATION: Found {len(os_getenv_violations)} direct os environment access violations: "
            f"{os_getenv_violations}. "
            f"All environment access must use IsolatedEnvironment.get_env() pattern."
        )

    def test_config_managers_use_consistent_env_access_patterns(self):
        """
        EXPECTED TO FAIL - Validate consistent environment access patterns.

        Config managers should all use the same SSOT pattern for environment access.
        Inconsistent patterns cause configuration drift between environments.
        """
        config_managers = []

        # Collect config manager instances
        try:
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            config_managers.append(('UnifiedConfigManager', UnifiedConfigManager))
        except ImportError:
            pass

        try:
            from netra_backend.app.core.managers.unified_configuration_manager import UnifiedConfigurationManager
            config_managers.append(('UnifiedConfigurationManager', UnifiedConfigurationManager))
        except ImportError:
            pass

        try:
            from netra_backend.app.services.configuration_service import ConfigurationManager
            config_managers.append(('ConfigurationManager', ConfigurationManager))
        except ImportError:
            pass

        if len(config_managers) < 2:
            pytest.skip("Need at least 2 config managers to test consistency")

        # Test environment access method consistency
        env_access_patterns = {}

        for manager_name, manager_class in config_managers:
            patterns = []

            # Check for IsolatedEnvironment usage
            try:
                import inspect
                source = inspect.getsource(manager_class)

                if 'IsolatedEnvironment' in source:
                    patterns.append('IsolatedEnvironment')
                if 'get_env()' in source:
                    patterns.append('get_env()')
                if 'os.environ' in source:
                    patterns.append('os.environ')
                if 'os.getenv' in source:
                    patterns.append('os.getenv')

                env_access_patterns[manager_name] = patterns

            except Exception as e:
                env_access_patterns[manager_name] = [f'ERROR: {str(e)}']

        # Check for pattern consistency
        ssot_pattern = ['IsolatedEnvironment', 'get_env()']
        non_ssot_managers = []

        for manager_name, patterns in env_access_patterns.items():
            has_ssot_pattern = all(p in patterns for p in ssot_pattern)
            has_non_ssot_pattern = any(p in patterns for p in ['os.environ', 'os.getenv'])

            if not has_ssot_pattern or has_non_ssot_pattern:
                non_ssot_managers.append({
                    'manager': manager_name,
                    'patterns': patterns,
                    'has_ssot': has_ssot_pattern,
                    'has_violations': has_non_ssot_pattern
                })

        # TEST ASSERTION: Should fail if non-SSOT patterns exist
        assert len(non_ssot_managers) == 0, (
            f"SSOT VIOLATION: Found {len(non_ssot_managers)} config managers with non-SSOT "
            f"environment access patterns: {non_ssot_managers}. "
            f"All managers must use consistent IsolatedEnvironment pattern."
        )

    def test_environment_variables_loaded_consistently_across_managers(self):
        """
        EXPECTED TO FAIL - Test environment variable loading consistency.

        Different config managers may load environment variables differently,
        causing configuration drift and Golden Path failures.
        """
        # Test critical environment variables
        critical_env_vars = [
            'ENVIRONMENT',
            'DATABASE_URL',
            'REDIS_URL',
            'JWT_SECRET_KEY',
            'AUTH_SERVICE_URL'
        ]

        config_managers = []

        # Collect available managers
        try:
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            manager = UnifiedConfigManager()
            config_managers.append(('UnifiedConfigManager', manager))
        except Exception:
            pass

        try:
            from netra_backend.app.core.managers.unified_configuration_manager import UnifiedConfigurationManager
            manager = UnifiedConfigurationManager()
            config_managers.append(('UnifiedConfigurationManager', manager))
        except Exception:
            pass

        try:
            from netra_backend.app.services.configuration_service import ConfigurationManager
            manager = ConfigurationManager()
            config_managers.append(('ConfigurationManager', manager))
        except Exception:
            pass

        if len(config_managers) < 2:
            pytest.skip("Need at least 2 config managers to test consistency")

        # Test environment variable loading consistency
        env_var_conflicts = []

        for env_var in critical_env_vars:
            values = {}

            for manager_name, manager_instance in config_managers:
                try:
                    # Try different methods managers might use
                    value = None

                    if hasattr(manager_instance, 'get_config'):
                        value = manager_instance.get_config(env_var)
                    elif hasattr(manager_instance, 'get'):
                        value = manager_instance.get(env_var)
                    elif hasattr(manager_instance, 'get_env_var'):
                        value = manager_instance.get_env_var(env_var)

                    values[manager_name] = value

                except Exception as e:
                    values[manager_name] = f'ERROR: {str(e)}'

            # Check for value conflicts
            non_none_values = {k: v for k, v in values.items() if v is not None and not str(v).startswith('ERROR:')}
            unique_values = set(str(v) for v in non_none_values.values())

            if len(unique_values) > 1:
                env_var_conflicts.append({
                    'env_var': env_var,
                    'values': values,
                    'unique_values': list(unique_values)
                })

        # TEST ASSERTION: Should fail if environment loading conflicts exist
        assert len(env_var_conflicts) == 0, (
            f"SSOT VIOLATION: Found {len(env_var_conflicts)} environment variable loading conflicts: "
            f"{env_var_conflicts}. "
            f"Config managers must load environment variables consistently using SSOT patterns."
        )

    def _find_os_environ_violations(self, tree: ast.AST, file_path: str) -> List[Dict[str, Any]]:
        """Find os.environ access violations in AST."""
        violations = []

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

        return violations


if __name__ == "__main__":
    # Run the test to demonstrate current violations
    pytest.main([__file__, "-v", "--tb=short", "-x"])
"""
Test Single Configuration Manager SSOT Validation - Issue #667

EXPECTED TO PASS AFTER CONSOLIDATION - Validates SSOT Config Manager

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability - Ensure single source of truth for configuration
- Value Impact: Validates SSOT consolidation prevents configuration conflicts
- Strategic Impact: Protects $500K+ ARR by ensuring consistent configuration management

PURPOSE: This test will PASS after Issue #667 consolidation is complete.
It validates that only one configuration manager exists and provides consistent API.

Test Coverage:
1. Single import path for configuration management
2. Consistent API across all usage patterns
3. SSOT environment access validation
4. Configuration method availability validation

CRITICAL: This test ensures consolidated configuration management supports
Golden Path user login and AI chat functionality worth $500K+ ARR protection.
"""

import pytest
import sys
import importlib
import inspect
from typing import Any, Dict, List, Optional
from unittest.mock import patch, MagicMock

# Import test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestSingleConfigManagerSSot(SSotBaseTestCase):
    """Test suite to validate single configuration manager SSOT compliance."""

    def test_only_one_config_manager_can_be_imported(self):
        """
        EXPECTED TO PASS AFTER CONSOLIDATION - Validate single config manager import.

        After SSOT consolidation, only one configuration manager should be importable.
        Multiple managers indicate incomplete SSOT migration.
        """
        # Expected SSOT import path after consolidation
        ssot_config_manager_path = "netra_backend.app.core.configuration.base.UnifiedConfigManager"

        # Paths that should NOT exist after consolidation
        deprecated_paths = [
            "netra_backend.app.core.managers.unified_configuration_manager.UnifiedConfigurationManager",
            "netra_backend.app.services.configuration_service.ConfigurationManager"
        ]

        # Test SSOT manager can be imported
        ssot_manager = None
        try:
            module_path, class_name = ssot_config_manager_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            ssot_manager_class = getattr(module, class_name)
            ssot_manager = ssot_manager_class()
        except (ImportError, AttributeError) as e:
            pytest.fail(f"SSOT config manager not found at {ssot_config_manager_path}: {str(e)}")

        # Verify deprecated managers are removed or redirected
        deprecated_managers_found = []
        for deprecated_path in deprecated_paths:
            try:
                module_path, class_name = deprecated_path.rsplit('.', 1)
                module = importlib.import_module(module_path)

                if hasattr(module, class_name):
                    deprecated_class = getattr(module, class_name)

                    # Check if it's the same class (redirect) or different (violation)
                    if deprecated_class is not ssot_manager.__class__:
                        deprecated_managers_found.append(deprecated_path)

            except (ImportError, AttributeError):
                # This is expected - deprecated paths should not exist
                pass

        # TEST ASSERTION: Should pass when only SSOT manager exists
        assert len(deprecated_managers_found) == 0, (
            f"SSOT VIOLATION: Found deprecated config managers that were not properly consolidated: "
            f"{deprecated_managers_found}. Only {ssot_config_manager_path} should exist after consolidation."
        )

        # Verify SSOT manager is functional
        assert ssot_manager is not None, "SSOT config manager must be instantiable"
        assert hasattr(ssot_manager, 'get_config'), "SSOT config manager must have get_config method"

    def test_config_manager_import_paths_redirect_to_ssot(self):
        """
        EXPECTED TO PASS AFTER CONSOLIDATION - Validate import path redirection to SSOT.

        Legacy import paths should redirect to the SSOT manager to maintain compatibility.
        """
        # SSOT import
        ssot_import = "netra_backend.app.core.configuration.base"

        # Legacy imports that should redirect to SSOT
        legacy_imports = [
            "netra_backend.app.core.managers.unified_configuration_manager",
            "netra_backend.app.services.configuration_service"
        ]

        # Get SSOT manager class
        try:
            ssot_module = importlib.import_module(ssot_import)
            ssot_manager_class = getattr(ssot_module, 'UnifiedConfigManager')
        except (ImportError, AttributeError) as e:
            pytest.fail(f"Cannot import SSOT manager: {str(e)}")

        # Test legacy imports
        import_redirections = []

        for legacy_import in legacy_imports:
            try:
                legacy_module = importlib.import_module(legacy_import)

                # Check what manager classes are available
                for attr_name in dir(legacy_module):
                    if 'Manager' in attr_name and not attr_name.startswith('_'):
                        attr_value = getattr(legacy_module, attr_name)

                        # Check if it's a class and if it redirects to SSOT
                        if inspect.isclass(attr_value):
                            if attr_value is ssot_manager_class:
                                import_redirections.append({
                                    'legacy_path': f"{legacy_import}.{attr_name}",
                                    'redirects_to_ssot': True
                                })
                            else:
                                import_redirections.append({
                                    'legacy_path': f"{legacy_import}.{attr_name}",
                                    'redirects_to_ssot': False,
                                    'class': attr_value
                                })

            except ImportError:
                # Legacy module doesn't exist - this is acceptable
                import_redirections.append({
                    'legacy_path': legacy_import,
                    'status': 'module_removed'
                })

        # Validate redirection compliance
        non_redirected_managers = [
            item for item in import_redirections
            if item.get('redirects_to_ssot') is False
        ]

        # TEST ASSERTION: Should pass when all legacy paths redirect to SSOT
        assert len(non_redirected_managers) == 0, (
            f"SSOT VIOLATION: Found manager classes that don't redirect to SSOT: {non_redirected_managers}. "
            f"All legacy manager imports should redirect to SSOT or be removed."
        )

    def test_ssot_config_manager_has_complete_api(self):
        """
        EXPECTED TO PASS AFTER CONSOLIDATION - Validate SSOT manager API completeness.

        The SSOT config manager should have all methods needed for Golden Path functionality.
        """
        # Import SSOT manager
        try:
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            manager = UnifiedConfigManager()
        except ImportError as e:
            pytest.fail(f"Cannot import SSOT config manager: {str(e)}")

        # Required API methods for Golden Path functionality
        required_methods = [
            'get_config',          # Basic configuration access
            'get_database_config', # Database connection config
            'get_auth_config',     # Authentication configuration
            'get_redis_config',    # Redis cache configuration
            'get_environment',     # Environment detection
        ]

        # Optional but recommended methods
        recommended_methods = [
            'reload_config',       # Configuration refresh
            'validate_config',     # Configuration validation
            'get_all_config',      # Complete configuration dump
        ]

        # Test required methods
        missing_required_methods = []
        for method_name in required_methods:
            if not hasattr(manager, method_name):
                missing_required_methods.append(method_name)

        # Test method signatures for consistency
        method_signatures = {}
        for method_name in required_methods:
            if hasattr(manager, method_name):
                method = getattr(manager, method_name)
                if callable(method):
                    sig = inspect.signature(method)
                    method_signatures[method_name] = str(sig)

        # TEST ASSERTION: Should pass when SSOT manager has complete API
        assert len(missing_required_methods) == 0, (
            f"SSOT API INCOMPLETE: SSOT config manager missing required methods: {missing_required_methods}. "
            f"Available methods: {[m for m in dir(manager) if not m.startswith('_')]}. "
            f"Required for Golden Path functionality."
        )

        # Verify methods are callable
        for method_name in required_methods:
            if hasattr(manager, method_name):
                method = getattr(manager, method_name)
                assert callable(method), f"Method {method_name} must be callable"

    def test_ssot_config_manager_uses_isolated_environment(self):
        """
        EXPECTED TO PASS AFTER CONSOLIDATION - Validate SSOT manager uses IsolatedEnvironment.

        The SSOT config manager must use IsolatedEnvironment for environment access.
        """
        # Import SSOT manager
        try:
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            manager_class = UnifiedConfigManager
        except ImportError as e:
            pytest.fail(f"Cannot import SSOT config manager: {str(e)}")

        # Check source code for IsolatedEnvironment usage
        try:
            source_code = inspect.getsource(manager_class)
        except OSError as e:
            pytest.skip(f"Cannot get source code for manager: {str(e)}")

        # Validate IsolatedEnvironment import and usage
        has_isolated_env_import = (
            'from shared.isolated_environment import' in source_code or
            'import shared.isolated_environment' in source_code or
            'from dev_launcher.isolated_environment import' in source_code
        )

        has_isolated_env_usage = (
            'IsolatedEnvironment' in source_code or
            'get_env()' in source_code
        )

        # Check for SSOT violations
        has_os_environ_violation = (
            'os.environ[' in source_code or
            'os.environ.get(' in source_code or
            'os.getenv(' in source_code
        )

        # TEST ASSERTION: Should pass when SSOT manager uses IsolatedEnvironment
        assert has_isolated_env_import, (
            f"SSOT VIOLATION: SSOT config manager does not import IsolatedEnvironment. "
            f"Must use SSOT environment access pattern."
        )

        assert has_isolated_env_usage, (
            f"SSOT VIOLATION: SSOT config manager does not use IsolatedEnvironment. "
            f"Must use get_env() pattern for environment access."
        )

        assert not has_os_environ_violation, (
            f"SSOT VIOLATION: SSOT config manager uses direct os.environ access. "
            f"Must use IsolatedEnvironment only."
        )

    def test_ssot_config_manager_factory_pattern_compliance(self):
        """
        EXPECTED TO PASS AFTER CONSOLIDATION - Validate factory pattern for multi-user isolation.

        The SSOT config manager should support factory pattern for user isolation.
        """
        # Import SSOT manager
        try:
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            manager_class = UnifiedConfigManager
        except ImportError as e:
            pytest.fail(f"Cannot import SSOT config manager: {str(e)}")

        # Test factory pattern (different instances)
        manager1 = manager_class()
        manager2 = manager_class()

        # Instances should be different for user isolation
        assert manager1 is not manager2, (
            f"FACTORY PATTERN VIOLATION: Config manager instances are same object. "
            f"Factory pattern required for multi-user isolation in Golden Path."
        )

        # Test that instances have independent state
        if hasattr(manager1, '_config_cache'):
            # Modify cache in one instance
            original_cache1 = getattr(manager1, '_config_cache', {})
            original_cache2 = getattr(manager2, '_config_cache', {})

            # They should start with independent caches
            assert original_cache1 is not original_cache2, (
                f"ISOLATION VIOLATION: Config manager instances share cache objects. "
                f"Must have independent state for multi-user scenarios."
            )

    def test_ssot_config_manager_golden_path_integration(self):
        """
        EXPECTED TO PASS AFTER CONSOLIDATION - Validate Golden Path integration readiness.

        The SSOT config manager should provide configuration needed for Golden Path functionality.
        """
        # Import SSOT manager
        try:
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            manager = UnifiedConfigManager()
        except ImportError as e:
            pytest.fail(f"Cannot import SSOT config manager: {str(e)}")

        # Test Golden Path configuration requirements
        golden_path_configs = {
            'database': ['DATABASE_URL'],
            'auth': ['JWT_SECRET_KEY', 'AUTH_SERVICE_URL'],
            'cache': ['REDIS_URL'],
            'environment': ['ENVIRONMENT']
        }

        missing_configurations = {}

        for config_category, required_keys in golden_path_configs.items():
            missing_keys = []

            for key in required_keys:
                try:
                    # Try to get configuration
                    value = None
                    if hasattr(manager, 'get_config'):
                        value = manager.get_config(key)

                    # Configuration doesn't need to have a value, but method should work
                    # The important thing is that the manager can handle the request

                except Exception as e:
                    missing_keys.append(f"{key}: {str(e)}")

            if missing_keys:
                missing_configurations[config_category] = missing_keys

        # TEST ASSERTION: Should pass when manager can handle Golden Path config requests
        assert len(missing_configurations) == 0, (
            f"GOLDEN PATH INTEGRATION FAILURE: SSOT config manager cannot handle required "
            f"Golden Path configurations: {missing_configurations}. "
            f"Must support all configuration categories for $500K+ ARR protection."
        )

        # Test basic functionality
        try:
            # Basic configuration access should work without errors
            environment = manager.get_config('ENVIRONMENT', 'test')
            assert environment is not None, "Environment configuration must be accessible"

        except Exception as e:
            pytest.fail(f"SSOT config manager basic functionality failed: {str(e)}")


if __name__ == "__main__":
    # Run the test to validate SSOT consolidation
    pytest.main([__file__, "-v", "--tb=short"])
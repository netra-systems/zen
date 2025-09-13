"""
Test Configuration Manager SSOT Violations for Issue #683 (Mission Critical)

This mission critical test reproduces SSOT violations in configuration management
that contribute to staging environment configuration validation failures. These
violations break the Single Source of Truth principle and cause configuration
inconsistencies.

Business Impact: Protects $500K+ ARR staging validation pipeline
Priority: P0 - Mission Critical

Issue #683: Staging environment configuration validation failures
Root Cause: SSOT violations in configuration management causing inconsistent state
Test Strategy: Detect SSOT violations that contribute to configuration validation failures
"""

import pytest
import os
import importlib
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment


class TestConfigManagerSsotViolationsIssue683(SSotBaseTestCase):
    """
    Mission critical tests to detect SSOT violations in configuration management.

    These tests identify SSOT violations that contribute to staging configuration
    validation failures by creating inconsistent configuration state.
    """

    def setup_method(self, method):
        """Set up mission critical test environment for SSOT violation detection."""
        super().setup_method(method)
        self.env = IsolatedEnvironment()
        # Store original environment to restore after test
        self.original_env = self.env.copy()

    def teardown_method(self, method):
        """Clean up mission critical test environment."""
        # Restore original environment
        for key in list(self.env._env.keys()):
            if key not in self.original_env:
                del self.env._env[key]
        for key, value in self.original_env.items():
            self.env.set(key, value)
        super().teardown_method(method)

    def test_multiple_config_managers_ssot_violation(self):
        """
        CRITICAL SSOT VIOLATION: Test detection of multiple configuration manager instances.

        This detects the critical SSOT violation where multiple configuration managers
        exist, causing inconsistent configuration state in staging environment.
        """
        # Test for multiple UnifiedConfigManager instances
        config_manager_modules = [
            'netra_backend.app.core.configuration.base',
            'netra_backend.app.config',
            'netra_backend.app.core.config'
        ]

        config_manager_instances = []
        ssot_violations = []

        for module_name in config_manager_modules:
            try:
                module = importlib.import_module(module_name)

                # Check for multiple config manager classes/instances
                config_manager_attrs = []
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if hasattr(attr, '__class__') and 'config' in attr_name.lower():
                        if 'manager' in attr_name.lower() or 'unified' in attr_name.lower():
                            config_manager_attrs.append((module_name, attr_name, attr))

                if config_manager_attrs:
                    config_manager_instances.extend(config_manager_attrs)

            except ImportError:
                # Module doesn't exist, skip
                continue

        # SSOT VIOLATION: Multiple configuration managers
        if len(config_manager_instances) > 1:
            unique_managers = set()
            for module_name, attr_name, attr in config_manager_instances:
                manager_type = type(attr).__name__
                unique_managers.add(f"{module_name}.{attr_name}:{manager_type}")

            if len(unique_managers) > 1:
                ssot_violations.append(f"Multiple configuration manager instances detected: {unique_managers}")

        # Test for singleton violation in UnifiedConfigManager
        from netra_backend.app.core.configuration.base import config_manager as manager1
        from netra_backend.app.core.configuration.base import config_manager as manager2

        if manager1 is not manager2:
            ssot_violations.append("UnifiedConfigManager singleton violation: Multiple instances created")

        if ssot_violations:
            pytest.fail(f"CRITICAL SSOT VIOLATION: Multiple configuration managers detected. "
                      f"This causes inconsistent configuration state in staging environment: {ssot_violations}")

    def test_duplicate_secret_config_definitions_ssot_violation(self):
        """
        CRITICAL SSOT VIOLATION: Test detection of duplicate SECRET_CONFIG definitions.

        This detects SSOT violations where SECRET_CONFIG is defined in multiple places,
        causing inconsistent secret configuration in staging environment.
        """
        # Search for multiple SECRET_CONFIG definitions
        config_modules_with_secrets = [
            'netra_backend.app.schemas.config',
            'netra_backend.app.core.configuration.secrets',
            'netra_backend.app.core.config',
            'netra_backend.app.config'
        ]

        secret_config_definitions = []
        ssot_violations = []

        for module_name in config_modules_with_secrets:
            try:
                module = importlib.import_module(module_name)

                if hasattr(module, 'SECRET_CONFIG'):
                    secret_config = getattr(module, 'SECRET_CONFIG')
                    secret_config_definitions.append((module_name, secret_config))

            except ImportError:
                continue

        # SSOT VIOLATION: Multiple SECRET_CONFIG definitions
        if len(secret_config_definitions) > 1:
            config_sources = [module_name for module_name, _ in secret_config_definitions]
            ssot_violations.append(f"Multiple SECRET_CONFIG definitions found in: {config_sources}")

            # Check if the definitions are actually different
            if len(secret_config_definitions) >= 2:
                config1 = secret_config_definitions[0][1]
                config2 = secret_config_definitions[1][1]

                # Compare configurations
                if len(config1) != len(config2):
                    ssot_violations.append(f"SECRET_CONFIG definitions have different lengths: "
                                        f"{secret_config_definitions[0][0]}={len(config1)}, "
                                        f"{secret_config_definitions[1][0]}={len(config2)}")

        if ssot_violations:
            pytest.fail(f"CRITICAL SSOT VIOLATION: Multiple SECRET_CONFIG definitions detected. "
                      f"This causes inconsistent secret configuration in staging: {ssot_violations}")

    def test_configuration_schema_duplication_ssot_violation(self):
        """
        CRITICAL SSOT VIOLATION: Test detection of duplicate configuration schema definitions.

        This detects SSOT violations where configuration schemas are duplicated,
        causing inconsistent validation in staging environment.
        """
        # Test for duplicate AppConfig schemas
        config_schema_modules = [
            'netra_backend.app.schemas.config',
            'netra_backend.app.core.configuration.schemas',
            'netra_backend.app.config_types'
        ]

        app_config_definitions = []
        staging_config_definitions = []
        ssot_violations = []

        for module_name in config_schema_modules:
            try:
                module = importlib.import_module(module_name)

                # Check for AppConfig duplicates
                if hasattr(module, 'AppConfig'):
                    app_config = getattr(module, 'AppConfig')
                    app_config_definitions.append((module_name, app_config))

                # Check for StagingConfig duplicates
                if hasattr(module, 'StagingConfig'):
                    staging_config = getattr(module, 'StagingConfig')
                    staging_config_definitions.append((module_name, staging_config))

            except ImportError:
                continue

        # SSOT VIOLATION: Multiple AppConfig definitions
        if len(app_config_definitions) > 1:
            config_sources = [module_name for module_name, _ in app_config_definitions]
            ssot_violations.append(f"Multiple AppConfig schema definitions found in: {config_sources}")

        # SSOT VIOLATION: Multiple StagingConfig definitions
        if len(staging_config_definitions) > 1:
            config_sources = [module_name for module_name, _ in staging_config_definitions]
            ssot_violations.append(f"Multiple StagingConfig schema definitions found in: {config_sources}")

        # Test for inconsistent field definitions
        if len(app_config_definitions) >= 2:
            config1_fields = set(dir(app_config_definitions[0][1]))
            config2_fields = set(dir(app_config_definitions[1][1]))

            missing_fields = config1_fields - config2_fields
            extra_fields = config2_fields - config1_fields

            if missing_fields or extra_fields:
                ssot_violations.append(f"AppConfig schema inconsistency: "
                                    f"missing fields: {missing_fields}, "
                                    f"extra fields: {extra_fields}")

        if ssot_violations:
            pytest.fail(f"CRITICAL SSOT VIOLATION: Duplicate configuration schemas detected. "
                      f"This causes inconsistent validation in staging environment: {ssot_violations}")

    def test_environment_access_ssot_violations(self):
        """
        CRITICAL SSOT VIOLATION: Test detection of direct os.environ access bypassing SSOT.

        This detects SSOT violations where configuration modules directly access os.environ
        instead of using IsolatedEnvironment, causing inconsistent environment state.
        """
        import ast
        import os as os_module
        from pathlib import Path

        # Configuration files to check for SSOT violations
        config_files = [
            'netra_backend/app/config.py',
            'netra_backend/app/core/configuration/base.py',
            'netra_backend/app/core/configuration/secrets.py',
            'netra_backend/app/schemas/config.py'
        ]

        ssot_violations = []

        for config_file in config_files:
            file_path = Path(f"C:\\GitHub\\netra-apex\\{config_file}")
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()

                    # Parse file to detect direct os.environ access
                    try:
                        tree = ast.parse(file_content)

                        class EnvironAccessVisitor(ast.NodeVisitor):
                            def __init__(self):
                                self.violations = []

                            def visit_Attribute(self, node):
                                # Check for os.environ access
                                if (isinstance(node.value, ast.Name) and
                                    node.value.id == 'os' and
                                    node.attr == 'environ'):
                                    self.violations.append(f"Line: os.environ.{node.attr}")
                                self.generic_visit(node)

                            def visit_Subscript(self, node):
                                # Check for os.environ['KEY'] access
                                if (isinstance(node.value, ast.Attribute) and
                                    isinstance(node.value.value, ast.Name) and
                                    node.value.value.id == 'os' and
                                    node.value.attr == 'environ'):
                                    self.violations.append("Direct os.environ subscript access")
                                self.generic_visit(node)

                        visitor = EnvironAccessVisitor()
                        visitor.visit(tree)

                        if visitor.violations:
                            ssot_violations.append(f"{config_file}: {visitor.violations}")

                    except SyntaxError:
                        # Skip files with syntax errors
                        continue

                except Exception:
                    # Skip files that can't be read
                    continue

        # Also check for string patterns that indicate SSOT violations
        for config_file in config_files:
            file_path = Path(f"C:\\GitHub\\netra-apex\\{config_file}")
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()

                    # Check for direct os.environ patterns
                    if 'os.environ[' in file_content or 'os.environ.get(' in file_content:
                        # Make sure it's not in comments
                        lines = file_content.split('\n')
                        for i, line in enumerate(lines):
                            if ('os.environ[' in line or 'os.environ.get(' in line) and not line.strip().startswith('#'):
                                ssot_violations.append(f"{config_file}:Line {i+1}: Direct os.environ access")

                except Exception:
                    continue

        if ssot_violations:
            pytest.fail(f"CRITICAL SSOT VIOLATION: Direct os.environ access detected bypassing IsolatedEnvironment. "
                      f"This causes inconsistent environment state in staging: {ssot_violations}")

    def test_configuration_loader_ssot_violations(self):
        """
        CRITICAL SSOT VIOLATION: Test detection of multiple configuration loader implementations.

        This detects SSOT violations where multiple configuration loaders exist,
        causing inconsistent configuration loading in staging environment.
        """
        # Test for multiple ConfigurationLoader classes
        loader_modules = [
            'netra_backend.app.core.configuration.loader',
            'netra_backend.app.core.config_loader',
            'netra_backend.app.configuration.loader'
        ]

        loader_classes = []
        ssot_violations = []

        for module_name in loader_modules:
            try:
                module = importlib.import_module(module_name)

                # Check for ConfigurationLoader classes
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        'loader' in attr_name.lower() and
                        'config' in attr_name.lower()):
                        loader_classes.append((module_name, attr_name, attr))

            except ImportError:
                continue

        # SSOT VIOLATION: Multiple configuration loaders
        if len(loader_classes) > 1:
            loader_sources = [f"{module}.{attr_name}" for module, attr_name, _ in loader_classes]
            ssot_violations.append(f"Multiple ConfigurationLoader implementations found: {loader_sources}")

        # Test for inconsistent loading methods
        if len(loader_classes) >= 2:
            loader1_methods = set(dir(loader_classes[0][2]))
            loader2_methods = set(dir(loader_classes[1][2]))

            method_differences = loader1_methods.symmetric_difference(loader2_methods)
            if method_differences:
                ssot_violations.append(f"ConfigurationLoader implementations have different methods: {method_differences}")

        if ssot_violations:
            pytest.fail(f"CRITICAL SSOT VIOLATION: Multiple configuration loader implementations detected. "
                      f"This causes inconsistent configuration loading in staging: {ssot_violations}")

    def test_secret_manager_ssot_violations(self):
        """
        CRITICAL SSOT VIOLATION: Test detection of multiple secret manager implementations.

        This detects SSOT violations where multiple secret managers exist,
        causing inconsistent secret management in staging environment.
        """
        # Test for multiple SecretManager/SecretsManager classes
        secret_modules = [
            'netra_backend.app.core.configuration.secrets',
            'netra_backend.app.core.configuration.unified_secrets',
            'netra_backend.app.core.secret_manager',
            'shared.secret_manager'
        ]

        secret_manager_classes = []
        ssot_violations = []

        for module_name in secret_modules:
            try:
                module = importlib.import_module(module_name)

                # Check for SecretManager classes
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        'secret' in attr_name.lower() and
                        'manager' in attr_name.lower()):
                        secret_manager_classes.append((module_name, attr_name, attr))

            except ImportError:
                continue

        # SSOT VIOLATION: Multiple secret managers
        if len(secret_manager_classes) > 1:
            manager_sources = [f"{module}.{attr_name}" for module, attr_name, _ in secret_manager_classes]
            ssot_violations.append(f"Multiple SecretManager implementations found: {manager_sources}")

        # Test for global secret manager instance violations
        secret_manager_instances = []
        for module_name in secret_modules:
            try:
                module = importlib.import_module(module_name)

                # Check for global instances
                for attr_name in dir(module):
                    if 'secrets_manager' in attr_name or 'secret_manager' in attr_name:
                        attr = getattr(module, attr_name)
                        if not callable(attr) and hasattr(attr, '__class__'):
                            secret_manager_instances.append((module_name, attr_name))

            except ImportError:
                continue

        # SSOT VIOLATION: Multiple global instances
        if len(secret_manager_instances) > 1:
            instance_sources = [f"{module}.{attr_name}" for module, attr_name in secret_manager_instances]
            ssot_violations.append(f"Multiple global secret manager instances found: {instance_sources}")

        if ssot_violations:
            pytest.fail(f"CRITICAL SSOT VIOLATION: Multiple secret manager implementations detected. "
                      f"This causes inconsistent secret management in staging: {ssot_violations}")

    def test_configuration_validation_ssot_violations(self):
        """
        CRITICAL SSOT VIOLATION: Test detection of multiple configuration validator implementations.

        This detects SSOT violations where multiple configuration validators exist,
        causing inconsistent validation logic in staging environment.
        """
        # Test for multiple ConfigurationValidator classes
        validator_modules = [
            'netra_backend.app.core.configuration.validator',
            'netra_backend.app.core.config_validator',
            'netra_backend.app.configuration.validator'
        ]

        validator_classes = []
        ssot_violations = []

        for module_name in validator_modules:
            try:
                module = importlib.import_module(module_name)

                # Check for ConfigurationValidator classes
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        'validator' in attr_name.lower() and
                        'config' in attr_name.lower()):
                        validator_classes.append((module_name, attr_name, attr))

            except ImportError:
                continue

        # SSOT VIOLATION: Multiple configuration validators
        if len(validator_classes) > 1:
            validator_sources = [f"{module}.{attr_name}" for module, attr_name, _ in validator_classes]
            ssot_violations.append(f"Multiple ConfigurationValidator implementations found: {validator_sources}")

        # Test for inconsistent validation rules
        if len(validator_classes) >= 2:
            validator1_methods = set(method for method in dir(validator_classes[0][2])
                                   if method.startswith('validate_'))
            validator2_methods = set(method for method in dir(validator_classes[1][2])
                                   if method.startswith('validate_'))

            validation_differences = validator1_methods.symmetric_difference(validator2_methods)
            if validation_differences:
                ssot_violations.append(f"ConfigurationValidator implementations have different validation methods: {validation_differences}")

        if ssot_violations:
            pytest.fail(f"CRITICAL SSOT VIOLATION: Multiple configuration validator implementations detected. "
                      f"This causes inconsistent validation logic in staging: {ssot_violations}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
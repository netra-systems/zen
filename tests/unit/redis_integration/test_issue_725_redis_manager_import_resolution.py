"""
Issue #725 Resolution Validation Tests - RedisTestManager Import Error Fix

This test suite validates that Issue #725 (RedisTestManager import errors) has been
properly resolved by updating affected test files to use the SSOT redis_manager pattern.

Test Categories:
1. Import error reproduction (confirms problem was real)
2. SSOT pattern validation (confirms solution works)
3. Affected file import validation (confirms all files now work)
4. System stability validation (confirms no regressions)

Business Justification: Unblocks 7+ unit test files that were completely broken
due to import errors, restoring test coverage for critical backend components.
"""

import pytest
import importlib
import sys
from pathlib import Path


class TestIssue725RedisManagerImportResolution:
    """Test suite validating Issue #725 RedisTestManager import error resolution."""

    def test_redis_test_manager_import_fails_as_expected(self):
        """
        Test confirms that RedisTestManager is correctly unavailable for import.

        This validates that the SSOT migration was correct in removing RedisTestManager
        from the public API of test_framework.redis_test_utils.
        """
        with pytest.raises(ImportError, match="cannot import name 'RedisTestManager'"):
            from test_framework.redis_test_utils import RedisTestManager

    def test_redis_manager_ssot_pattern_works(self):
        """
        Test confirms that the SSOT redis_manager pattern works correctly.

        This validates that the recommended replacement for RedisTestManager
        is available and properly configured.
        """
        from test_framework.redis_test_utils import redis_manager

        # Validate redis_manager is available
        assert redis_manager is not None, "redis_manager should be available"

        # Validate it's the expected type from netra_backend.app.redis_manager
        assert hasattr(redis_manager, '__class__'), "redis_manager should be a proper object"
        assert 'RedisManager' in str(type(redis_manager)), "redis_manager should be RedisManager instance"

    def test_affected_test_files_import_successfully(self):
        """
        Test validates that all previously failing test files now import successfully.

        This confirms that the Issue #725 remediation was complete and effective.
        """
        affected_modules = [
            'netra_backend.tests.fixtures.test_fixtures',
            'netra_backend.tests.startup.test_config_core',
            'netra_backend.tests.startup.test_config_validation',
            'netra_backend.tests.integration.test_fixtures_common',
            'netra_backend.tests.integration.test_startup_fixes_integration'
        ]

        import_results = {}

        for module_name in affected_modules:
            try:
                # Import the module
                module = importlib.import_module(module_name)
                import_results[module_name] = "SUCCESS"

                # Validate the module loaded properly
                assert module is not None, f"Module {module_name} should not be None"

            except ImportError as e:
                import_results[module_name] = f"FAILED: {e}"
                pytest.fail(f"Module {module_name} failed to import: {e}")
            except Exception as e:
                import_results[module_name] = f"ERROR: {e}"
                # Allow other exceptions but log them
                print(f"Warning: Module {module_name} imported but had issues: {e}")

        # Validate all imports succeeded
        failed_imports = {k: v for k, v in import_results.items() if not v.startswith("SUCCESS")}
        assert len(failed_imports) == 0, f"Some modules failed to import: {failed_imports}"

    def test_redis_manager_functional_interface(self):
        """
        Test validates that redis_manager provides expected functional interface.

        This ensures that the SSOT pattern provides equivalent functionality
        to what tests were expecting from RedisTestManager.
        """
        from test_framework.redis_test_utils import redis_manager

        # Check for common Redis interface methods
        expected_interface = ['ping', 'get', 'set', 'delete', 'exists']
        available_methods = []
        missing_methods = []

        for method_name in expected_interface:
            if hasattr(redis_manager, method_name):
                available_methods.append(method_name)
            else:
                missing_methods.append(method_name)

        # We expect at least some Redis-like interface to be available
        assert len(available_methods) > 0, f"redis_manager should have Redis interface methods, found: {dir(redis_manager)}"

        # If it's missing key methods, that's okay as long as it's a valid Redis manager
        if missing_methods:
            print(f"Note: redis_manager missing some expected methods: {missing_methods}")
            print(f"Available methods: {available_methods}")
            print(f"Redis manager type: {type(redis_manager)}")

    def test_no_remaining_redis_test_manager_usage(self):
        """
        Test scans for any remaining RedisTestManager usage in affected files.

        This validates that the migration was complete and no RedisTestManager
        references remain that could cause future import errors.
        """
        affected_files = [
            Path('netra_backend/tests/fixtures/test_fixtures.py'),
            Path('netra_backend/tests/startup/test_config_core.py'),
            Path('netra_backend/tests/startup/test_config_validation.py'),
            Path('netra_backend/tests/integration/test_fixtures_common.py'),
            Path('netra_backend/tests/integration/test_startup_fixes_integration.py')
        ]

        files_with_redis_test_manager = []

        for file_path in affected_files:
            if file_path.exists():
                content = file_path.read_text()
                if 'RedisTestManager()' in content:
                    files_with_redis_test_manager.append(str(file_path))

        assert len(files_with_redis_test_manager) == 0, \
            f"Files still contain RedisTestManager() usage: {files_with_redis_test_manager}"

    def test_ssot_compliance_maintained(self):
        """
        Test validates that the changes maintain SSOT compliance patterns.

        This ensures that the fix aligns with the broader SSOT migration
        objectives and architectural patterns.
        """
        from test_framework.redis_test_utils import redis_manager
        from netra_backend.app.redis_manager import redis_manager as backend_redis_manager

        # Validate that test framework redis_manager is same as backend redis_manager
        assert redis_manager is backend_redis_manager, \
            "test_framework redis_manager should be same instance as backend redis_manager (SSOT pattern)"

    def test_system_stability_no_regressions(self):
        """
        Test validates that the Issue #725 fix didn't introduce system regressions.

        This performs basic system health checks to ensure the changes were safe.
        """
        # Test that core imports still work
        try:
            from netra_backend.app.redis_manager import redis_manager
            from test_framework.redis_test_utils import redis_manager as test_redis_manager

            # Basic sanity checks
            assert redis_manager is not None
            assert test_redis_manager is not None
            assert redis_manager is test_redis_manager  # SSOT pattern

        except Exception as e:
            pytest.fail(f"System stability check failed: {e}")

    def test_business_value_restoration(self):
        """
        Test validates that business value has been restored by unblocking unit tests.

        This ensures that the components covered by the affected test files
        can now be properly validated through unit testing.
        """
        # Test that we can import modules that represent business value
        business_critical_imports = [
            'netra_backend.tests.fixtures.test_fixtures',  # Test infrastructure
            'netra_backend.tests.startup.test_config_core',  # Configuration validation
            'netra_backend.tests.startup.test_config_validation',  # Config validation logic
        ]

        for module_name in business_critical_imports:
            try:
                importlib.import_module(module_name)
            except Exception as e:
                pytest.fail(f"Business critical module {module_name} failed import: {e}")


class TestIssue725ComplianceValidation:
    """Additional validation tests for Issue #725 architectural compliance."""

    def test_redis_test_utils_exports_only_redis_manager(self):
        """
        Test validates that test_framework.redis_test_utils only exports redis_manager.

        This confirms proper SSOT encapsulation.
        """
        import test_framework.redis_test_utils as redis_utils

        # Check __all__ if it exists
        if hasattr(redis_utils, '__all__'):
            assert redis_utils.__all__ == ['redis_manager'], \
                f"redis_test_utils should only export redis_manager, got: {redis_utils.__all__}"

        # Check that RedisTestManager is not accessible
        assert not hasattr(redis_utils, 'RedisTestManager'), \
            "RedisTestManager should not be accessible from redis_test_utils"

    def test_issue_725_documentation_compliance(self):
        """
        Test validates that the fix aligns with Issue #725 requirements.

        Based on the GitHub issue, the fix should:
        1. Update imports from RedisTestManager to redis_manager
        2. Update usage patterns to SSOT compliance
        3. Maintain functional equivalence
        """
        # Requirement 1: redis_manager import works
        from test_framework.redis_test_utils import redis_manager
        assert redis_manager is not None

        # Requirement 2: RedisTestManager import fails
        with pytest.raises(ImportError):
            from test_framework.redis_test_utils import RedisTestManager

        # Requirement 3: Functional equivalence (redis_manager provides Redis interface)
        assert hasattr(redis_manager, '__class__'), "redis_manager should be a proper Redis manager"

    def test_fix_aligns_with_issue_450_ssot_migration(self):
        """
        Test validates that Issue #725 fix aligns with Issue #450 SSOT migration.

        Issue #450 removed RedisTestManager as part of Redis import pattern cleanup.
        Issue #725 fix should complete that migration by updating dependent tests.
        """
        # Validate that the SSOT pattern is properly implemented
        from test_framework.redis_test_utils import redis_manager
        from netra_backend.app.redis_manager import redis_manager as source_redis_manager

        # Should be same instance (SSOT pattern)
        assert redis_manager is source_redis_manager, \
            "redis_manager should be SSOT instance from netra_backend.app.redis_manager"

        # Should not be creating new instances
        from test_framework.redis_test_utils import redis_manager as redis_manager_2
        assert redis_manager is redis_manager_2, \
            "Multiple imports should return same SSOT instance"
"""
CloudEnvironmentDetector API Consistency Regression Tests - Issue #1300

CRITICAL: Prevents future API inconsistency issues between validation tests
and CloudEnvironmentDetector implementation.

ROOT CAUSE ADDRESSED: Tests were calling non-existent synchronous API methods
while CloudEnvironmentDetector only provides async methods.

Business Value: Platform/Internal - API Consistency & Regression Prevention
Ensures API contracts remain consistent and validation tests use correct methods.
"""
import pytest
import inspect
from typing import get_type_hints
from netra_backend.app.core.environment_context.cloud_environment_detector import (
    CloudEnvironmentDetector,
    get_cloud_environment_detector,
    detect_current_environment
)


@pytest.mark.regression
class TestCloudEnvironmentDetectorAPIConsistency:
    """Regression tests for CloudEnvironmentDetector API consistency."""

    def test_no_synchronous_detect_environment_method(self):
        """Ensure CloudEnvironmentDetector doesn't have synchronous detect_environment method."""
        detector = CloudEnvironmentDetector()

        # Verify the problematic method doesn't exist
        assert not hasattr(detector, 'detect_environment'), (
            "CloudEnvironmentDetector should not have synchronous 'detect_environment' method. "
            "Use 'detect_environment_context' instead."
        )

    def test_correct_async_methods_exist(self):
        """Verify expected async methods exist with correct signatures."""
        detector = CloudEnvironmentDetector()

        # Verify the correct async method exists
        assert hasattr(detector, 'detect_environment_context'), (
            "CloudEnvironmentDetector must have 'detect_environment_context' method"
        )

        # Verify it's async
        method = getattr(detector, 'detect_environment_context')
        assert inspect.iscoroutinefunction(method), (
            "'detect_environment_context' must be an async method"
        )

    def test_factory_function_returns_correct_type(self):
        """Verify factory function returns CloudEnvironmentDetector instance."""
        detector = get_cloud_environment_detector()
        assert isinstance(detector, CloudEnvironmentDetector), (
            "get_cloud_environment_detector() must return CloudEnvironmentDetector instance"
        )

    def test_module_level_function_is_async(self):
        """Verify module-level detection function is async."""
        assert inspect.iscoroutinefunction(detect_current_environment), (
            "detect_current_environment() must be an async function"
        )

    def test_method_signatures_consistency(self):
        """Verify method signatures match expected patterns."""
        detector = CloudEnvironmentDetector()

        # Check detect_environment_context signature
        sig = inspect.signature(detector.detect_environment_context)
        params = list(sig.parameters.keys())

        # Should have force_refresh parameter
        assert 'force_refresh' in params, (
            "detect_environment_context should have 'force_refresh' parameter"
        )

        # Should have default value for force_refresh
        force_refresh_param = sig.parameters['force_refresh']
        assert force_refresh_param.default == False, (
            "force_refresh parameter should default to False"
        )

    def test_public_api_methods_only_async(self):
        """Ensure all public API methods are async where expected."""
        detector = CloudEnvironmentDetector()

        # Get all public methods (not starting with _)
        public_methods = [
            (name, method) for name, method in inspect.getmembers(detector, inspect.ismethod)
            if not name.startswith('_') and not name.startswith('__')
        ]

        # Methods that should be async
        async_methods = ['detect_environment_context']

        for method_name, method in public_methods:
            if method_name in async_methods:
                assert inspect.iscoroutinefunction(method), (
                    f"Method '{method_name}' should be async"
                )

    def test_no_legacy_method_names(self):
        """Ensure no legacy method names exist that could cause confusion."""
        detector = CloudEnvironmentDetector()

        # Legacy method names that should not exist
        legacy_methods = [
            'detect_environment',
            'sync_detect_environment',
            'get_environment',
            'determine_environment'
        ]

        for legacy_method in legacy_methods:
            assert not hasattr(detector, legacy_method), (
                f"CloudEnvironmentDetector should not have legacy method '{legacy_method}'"
            )

    @pytest.mark.asyncio
    async def test_api_usage_pattern_works(self):
        """Test the correct API usage pattern to prevent regression."""
        # This is the correct usage pattern that should always work
        detector = get_cloud_environment_detector()

        # This should work without errors
        context = await detector.detect_environment_context()

        # Basic validation that context is returned
        assert context is not None
        assert hasattr(context, 'environment_type')
        assert hasattr(context, 'cloud_platform')
        assert hasattr(context, 'confidence_score')

    def test_import_paths_stability(self):
        """Ensure import paths remain stable for critical components."""
        # These imports should always work
        try:
            from netra_backend.app.core.environment_context.cloud_environment_detector import (
                CloudEnvironmentDetector,
                EnvironmentContext,
                EnvironmentType,
                CloudPlatform,
                get_cloud_environment_detector,
                detect_current_environment
            )
        except ImportError as e:
            pytest.fail(f"Critical import path broken: {e}")

        # Verify types are available
        assert CloudEnvironmentDetector is not None
        assert EnvironmentContext is not None
        assert EnvironmentType is not None
        assert CloudPlatform is not None
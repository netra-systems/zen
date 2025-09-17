"""
Issue #1300: CloudEnvironmentDetector API Consistency Tests

Tests to ensure CloudEnvironmentDetector API is used correctly throughout the codebase
and that the async detect_environment_context() method works properly.

Business Value: Platform stability - ensures environment detection works reliably
in staging and production deployments, preventing deployment failures.
"""

import asyncio
import pytest
from test_framework.ssot.base_test_case import SSotAsyncTestCase

class CloudEnvironmentDetectorAPIConsistencyTests(SSotAsyncTestCase):
    """Test CloudEnvironmentDetector API consistency and functionality."""

    async def test_cloud_environment_detector_basic_functionality(self):
        """Verify CloudEnvironmentDetector basic functionality works."""
        from netra_backend.app.core.environment_context.cloud_environment_detector import get_cloud_environment_detector

        detector = get_cloud_environment_detector()
        self.assertIsNotNone(detector)

        # Test async method works
        context = await detector.detect_environment_context()

        # Verify context has required attributes
        self.assertTrue(hasattr(context, 'environment_type'))
        self.assertTrue(hasattr(context, 'cloud_platform'))
        self.assertTrue(hasattr(context, 'confidence'))

        # Verify confidence is valid
        self.assertGreaterEqual(context.confidence, 0.0)
        self.assertLessEqual(context.confidence, 1.0)

        # Verify environment type is valid
        self.assertIn(context.environment_type.value, ['development', 'staging', 'production', 'testing'])

    async def test_singleton_behavior(self):
        """Verify get_cloud_environment_detector returns singleton."""
        from netra_backend.app.core.environment_context.cloud_environment_detector import get_cloud_environment_detector

        detector1 = get_cloud_environment_detector()
        detector2 = get_cloud_environment_detector()

        self.assertIs(detector1, detector2, "get_cloud_environment_detector should return singleton instance")

    async def test_detect_environment_context_consistency(self):
        """Verify detect_environment_context returns consistent results."""
        from netra_backend.app.core.environment_context.cloud_environment_detector import get_cloud_environment_detector

        detector = get_cloud_environment_detector()

        # Call multiple times and verify consistency
        context1 = await detector.detect_environment_context()
        context2 = await detector.detect_environment_context()

        self.assertEqual(context1.environment_type, context2.environment_type)
        self.assertEqual(context1.cloud_platform, context2.cloud_platform)

    def test_deprecated_methods_not_called(self):
        """Verify that deprecated environment detection methods are not used."""
        # This test ensures that the old synchronous methods are not accidentally called
        from netra_backend.app.core.environment_context.cloud_environment_detector import CloudEnvironmentDetector

        detector = CloudEnvironmentDetector()

        # Verify the async method exists
        self.assertTrue(hasattr(detector, 'detect_environment_context'))
        self.assertTrue(asyncio.iscoroutinefunction(detector.detect_environment_context))

        # Verify old synchronous method doesn't exist
        self.assertFalse(hasattr(detector, 'detect_environment'))

    async def test_startup_module_compatibility(self):
        """Verify CloudEnvironmentDetector works with startup module."""
        from netra_backend.app.core.environment_context.cloud_environment_detector import get_cloud_environment_detector, CloudPlatform

        detector = get_cloud_environment_detector()
        context = await detector.detect_environment_context()

        # Test the specific logic used in startup_module._should_check_docker_containers
        if context.cloud_platform == CloudPlatform.CLOUD_RUN:
            should_check_docker = False
        else:
            should_check_docker = True

        # Just verify this doesn't crash - the actual value depends on environment
        self.assertIsInstance(should_check_docker, bool)

    async def test_environment_context_attributes(self):
        """Verify EnvironmentContext has all required attributes."""
        from netra_backend.app.core.environment_context.cloud_environment_detector import get_cloud_environment_detector

        detector = get_cloud_environment_detector()
        context = await detector.detect_environment_context()

        # Test all the attributes that should be available
        required_attributes = [
            'environment_type',
            'cloud_platform',
            'confidence',
            'service_name',
            'project_id',
            'region'
        ]

        for attr in required_attributes:
            self.assertTrue(hasattr(context, attr), f"EnvironmentContext missing required attribute: {attr}")

if __name__ == '__main__':
    pytest.main([__file__])
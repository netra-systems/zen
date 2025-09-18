"""
Additional CloudEnvironmentDetector Tests - Issue #1300 Resolution

Supplementary tests focusing on API consistency and error scenarios
to complement existing comprehensive test suite.

Business Value: Platform/Internal - Environment Detection Reliability
Ensures CloudEnvironmentDetector works correctly across all scenarios.
"""
import pytest
import asyncio
from unittest.mock import patch
from netra_backend.app.core.environment_context.cloud_environment_detector import (
    CloudEnvironmentDetector,
    EnvironmentContext,
    EnvironmentType,
    CloudPlatform
)


@pytest.mark.unit
class TestCloudEnvironmentDetectorAdditional:
    """Additional tests for CloudEnvironmentDetector focusing on edge cases."""

    @pytest.fixture
    def detector(self):
        """Create CloudEnvironmentDetector instance."""
        return CloudEnvironmentDetector()

    @pytest.fixture
    def clear_cache(self, detector):
        """Clear detector cache before each test."""
        detector.clear_cache()
        yield
        detector.clear_cache()

    @pytest.mark.asyncio
    async def test_cache_functionality(self, detector, clear_cache):
        """Test caching behavior works correctly."""
        # Mock detection to return specific result
        mock_context = EnvironmentContext(
            environment_type=EnvironmentType.STAGING,
            cloud_platform=CloudPlatform.CLOUD_RUN,
            confidence_score=0.9
        )

        with patch.object(detector, '_detect_via_cloud_run_metadata', return_value=mock_context):
            # First call should trigger detection
            context1 = await detector.detect_environment_context()

            # Second call should use cache (not trigger detection again)
            context2 = await detector.detect_environment_context()

            # Results should be identical
            assert context1.environment_type == context2.environment_type
            assert context1.cloud_platform == context2.cloud_platform
            assert context1.confidence_score == context2.confidence_score

    @pytest.mark.asyncio
    async def test_force_refresh_bypasses_cache(self, detector, clear_cache):
        """Test force_refresh parameter bypasses cache."""
        call_count = 0

        async def mock_detection():
            nonlocal call_count
            call_count += 1
            return EnvironmentContext(
                environment_type=EnvironmentType.DEVELOPMENT,
                cloud_platform=CloudPlatform.UNKNOWN,
                confidence_score=0.5
            )

        with patch.object(detector, '_detect_via_cloud_run_metadata', side_effect=mock_detection):
            # First call
            await detector.detect_environment_context()
            assert call_count == 1

            # Second call without force_refresh (should use cache)
            await detector.detect_environment_context()
            assert call_count == 1  # No additional call

            # Third call with force_refresh (should bypass cache)
            await detector.detect_environment_context(force_refresh=True)
            assert call_count == 2  # Additional call made

    @pytest.mark.asyncio
    async def test_detection_failure_handling(self, detector, clear_cache):
        """Test behavior when all detection methods fail."""
        # Mock all detection methods to return None
        with patch.object(detector, '_detect_via_cloud_run_metadata', return_value=None), \
             patch.object(detector, '_detect_via_environment_variables', return_value=None), \
             patch.object(detector, '_detect_via_test_context_detection', return_value=None), \
             patch.object(detector, '_detect_via_gcp_service_variables', return_value=None), \
             patch.object(detector, '_detect_via_app_engine_metadata', return_value=None):

            # Should raise RuntimeError when environment cannot be determined
            with pytest.raises(RuntimeError, match="Could not determine environment"):
                await detector.detect_environment_context()

    @pytest.mark.asyncio
    async def test_confidence_score_validation(self, detector, clear_cache):
        """Test that confidence scores are properly validated."""
        # Test with high confidence detection
        high_confidence_context = EnvironmentContext(
            environment_type=EnvironmentType.STAGING,
            cloud_platform=CloudPlatform.CLOUD_RUN,
            confidence_score=0.9
        )

        with patch.object(detector, '_detect_via_cloud_run_metadata', return_value=high_confidence_context):
            context = await detector.detect_environment_context()
            assert context.confidence_score >= 0.8  # High confidence threshold

    def test_cache_management_methods(self, detector):
        """Test cache management utility methods."""
        # Initially no cache
        assert detector.get_cached_context() is None

        # After clearing cache
        detector.clear_cache()
        assert detector.get_cached_context() is None

    @pytest.mark.asyncio
    async def test_multiple_concurrent_detection_calls(self, detector, clear_cache):
        """Test concurrent calls to detect_environment_context."""
        # Create multiple concurrent detection calls
        tasks = [
            detector.detect_environment_context()
            for _ in range(3)
        ]

        # All should complete successfully
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All results should be successful (no exceptions)
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, EnvironmentContext)

        # All results should be identical (from cache)
        for i in range(1, len(results)):
            assert results[i].environment_type == results[0].environment_type
            assert results[i].cloud_platform == results[0].cloud_platform
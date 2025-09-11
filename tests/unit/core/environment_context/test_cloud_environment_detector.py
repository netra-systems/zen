"""
Test suite for CloudEnvironmentDetector - Environment detection validation.

This test suite validates the comprehensive environment detection system
designed to prevent Golden Path validation failures.

Tests cover:
- Cloud Run metadata detection
- Environment variable analysis
- GCP service variable parsing
- Confidence scoring
- Fail-fast behavior when environment cannot be determined

ROOT CAUSE VALIDATION: Ensures staging environment is correctly detected
in Cloud Run preventing localhost:8081 connection attempts.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from aiohttp import ClientTimeout, ClientSession
import os

from netra_backend.app.core.environment_context.cloud_environment_detector import (
    CloudEnvironmentDetector,
    EnvironmentContext,
    EnvironmentType,
    CloudPlatform,
    get_cloud_environment_detector,
    detect_current_environment
)


class TestCloudEnvironmentDetector:
    """Test comprehensive cloud environment detection."""
    
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
    async def test_cloud_run_staging_detection_success(self, detector, clear_cache):
        """Test successful Cloud Run staging detection via metadata API."""
        # Mock successful Cloud Run metadata responses
        mock_responses = {
            "instance/attributes/goog-cloudrun-service-name": "netra-backend-staging",
            "project/project-id": "netra-staging-test",
            "instance/region": "projects/123456/regions/us-central1",
            "instance/attributes/goog-revision": "netra-backend-staging-00001-abc"
        }
        
        async def mock_fetch_metadata(session, endpoint):
            return mock_responses.get(endpoint)
        
        with patch.object(detector, '_fetch_metadata', side_effect=mock_fetch_metadata):
            context = await detector.detect_environment_context()
            
            assert context is not None
            assert context.environment_type == EnvironmentType.STAGING
            assert context.cloud_platform == CloudPlatform.CLOUD_RUN
            assert context.service_name == "netra-backend-staging"
            assert context.project_id == "netra-staging-test"
            assert context.region == "us-central1"
            assert context.confidence_score == 0.9
            assert "cloud_run_metadata" in context.detection_metadata.get("method", "")
    
    @pytest.mark.asyncio
    async def test_cloud_run_production_detection_success(self, detector, clear_cache):
        """Test successful Cloud Run production detection."""
        mock_responses = {
            "instance/attributes/goog-cloudrun-service-name": "netra-backend",
            "project/project-id": "netra-production",
            "instance/region": "projects/123456/regions/us-central1",
            "instance/attributes/goog-revision": "netra-backend-00001-xyz"
        }
        
        async def mock_fetch_metadata(session, endpoint):
            return mock_responses.get(endpoint)
        
        with patch.object(detector, '_fetch_metadata', side_effect=mock_fetch_metadata):
            context = await detector.detect_environment_context()
            
            assert context.environment_type == EnvironmentType.PRODUCTION
            assert context.service_name == "netra-backend"
            assert context.confidence_score == 0.9
    
    @pytest.mark.asyncio
    async def test_environment_variable_staging_detection(self, detector, clear_cache):
        """Test staging detection via ENVIRONMENT variable."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            "K_SERVICE": "netra-backend-staging"
        }, clear=False):
            context = await detector.detect_environment_context()
            
            assert context.environment_type == EnvironmentType.STAGING
            assert context.cloud_platform == CloudPlatform.CLOUD_RUN
            assert context.service_name == "netra-backend-staging"
            assert context.confidence_score == 0.8
            assert "environment_variables" in context.detection_metadata.get("method", "")
    
    @pytest.mark.asyncio
    async def test_k_service_only_detection(self, detector, clear_cache):
        """Test detection using only K_SERVICE variable."""
        with patch.dict(os.environ, {"K_SERVICE": "netra-backend-staging"}, clear=True):
            # Mock metadata API failure to force environment variable detection
            with patch.object(detector, '_fetch_metadata', return_value=None):
                context = await detector.detect_environment_context()
                
                assert context.environment_type == EnvironmentType.STAGING
                assert context.service_name == "netra-backend-staging"
                assert context.confidence_score == 0.75
    
    @pytest.mark.asyncio 
    async def test_gcp_project_staging_detection(self, detector, clear_cache):
        """Test staging detection via GCP project variables."""
        with patch.dict(os.environ, {
            "GOOGLE_CLOUD_PROJECT": "netra-staging-test",
            "K_REVISION": "netra-backend-staging-00001"
        }, clear=True):
            # Mock metadata API failure to force GCP variable detection
            with patch.object(detector, '_fetch_metadata', return_value=None):
                context = await detector.detect_environment_context()
                
                assert context.environment_type == EnvironmentType.STAGING
                assert context.project_id == "netra-staging-test"
                assert context.confidence_score == 0.7
    
    @pytest.mark.asyncio
    async def test_app_engine_detection(self, detector, clear_cache):
        """Test App Engine environment detection."""
        with patch.dict(os.environ, {
            "GAE_APPLICATION": "netra-staging-app",
            "GAE_VERSION": "staging-v1",
            "GAE_SERVICE": "default"
        }, clear=True):
            # Mock metadata API failure to force App Engine detection
            with patch.object(detector, '_fetch_metadata', return_value=None):
                context = await detector.detect_environment_context()
                
                assert context.environment_type == EnvironmentType.STAGING
                assert context.cloud_platform == CloudPlatform.APP_ENGINE
                assert context.service_name == "default"
                assert context.project_id == "netra-staging-app"
                assert context.confidence_score == 0.8
    
    @pytest.mark.asyncio
    async def test_detection_failure_low_confidence(self, detector, clear_cache):
        """Test detection failure when confidence is too low."""
        # Clear all environment variables that could indicate environment
        env_vars_to_clear = [
            "ENVIRONMENT", "K_SERVICE", "GOOGLE_CLOUD_PROJECT", 
            "GAE_APPLICATION", "GAE_VERSION", "GAE_SERVICE"
        ]
        
        with patch.dict(os.environ, {}, clear=True):
            # Mock metadata API failure
            with patch.object(detector, '_fetch_metadata', return_value=None):
                with pytest.raises(RuntimeError) as exc_info:
                    await detector.detect_environment_context()
                
                assert "Cannot determine environment with sufficient confidence" in str(exc_info.value)
                assert "critical failure for Golden Path validation" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_metadata_api_timeout_fallback(self, detector, clear_cache):
        """Test fallback to environment variables when metadata API times out."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            "K_SERVICE": "netra-backend-staging"
        }, clear=False):
            # Mock metadata API timeout
            with patch.object(detector, '_fetch_metadata', side_effect=asyncio.TimeoutError):
                context = await detector.detect_environment_context()
                
                assert context.environment_type == EnvironmentType.STAGING
                assert context.confidence_score >= 0.7  # Should have sufficient confidence
    
    def test_service_name_classification(self, detector):
        """Test service name classification logic."""
        test_cases = [
            ("netra-backend-staging", EnvironmentType.STAGING),
            ("netra-backend", EnvironmentType.PRODUCTION),
            ("api-prod-v1", EnvironmentType.PRODUCTION),
            ("service-dev-test", EnvironmentType.DEVELOPMENT),
            ("unknown-service", EnvironmentType.UNKNOWN)
        ]
        
        for service_name, expected_env in test_cases:
            result = detector._classify_service_environment(service_name)
            assert result == expected_env, f"Failed for service: {service_name}"
    
    def test_environment_type_parsing(self, detector):
        """Test environment string parsing."""
        test_cases = [
            ("staging", EnvironmentType.STAGING),
            ("PRODUCTION", EnvironmentType.PRODUCTION),
            ("dev", EnvironmentType.DEVELOPMENT),
            ("test", EnvironmentType.TESTING),
            ("unknown", EnvironmentType.UNKNOWN)
        ]
        
        for env_str, expected_env in test_cases:
            result = detector._parse_environment_type(env_str)
            assert result == expected_env
    
    @pytest.mark.asyncio
    async def test_caching_behavior(self, detector, clear_cache):
        """Test that detection results are cached properly."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            "K_SERVICE": "netra-backend-staging"
        }, clear=False):
            
            # First detection
            context1 = await detector.detect_environment_context()
            
            # Second detection should use cache
            with patch.object(detector, '_detect_via_cloud_run_metadata') as mock_detect:
                context2 = await detector.detect_environment_context()
                
                # Should not call detection strategies again
                mock_detect.assert_not_called()
                
                # Should return same context
                assert context1 is context2
    
    @pytest.mark.asyncio
    async def test_force_refresh_bypasses_cache(self, detector, clear_cache):
        """Test that force_refresh bypasses cache."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            "K_SERVICE": "netra-backend-staging"
        }, clear=False):
            
            # First detection
            await detector.detect_environment_context()
            
            # Force refresh should trigger new detection
            with patch.object(detector, '_detect_via_environment_variables', wraps=detector._detect_via_environment_variables) as mock_detect:
                await detector.detect_environment_context(force_refresh=True)
                
                # Should call detection strategies again
                mock_detect.assert_called()


class TestEnvironmentDetectionIntegration:
    """Integration tests for environment detection."""
    
    @pytest.mark.asyncio
    async def test_singleton_behavior(self):
        """Test singleton detector behavior."""
        detector1 = get_cloud_environment_detector()
        detector2 = get_cloud_environment_detector()
        
        assert detector1 is detector2
    
    @pytest.mark.asyncio
    async def test_detect_current_environment_function(self):
        """Test convenience function for environment detection."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            "K_SERVICE": "netra-backend-staging"
        }, clear=False):
            context = await detect_current_environment()
            
            assert context.environment_type == EnvironmentType.STAGING
            assert isinstance(context, EnvironmentContext)
    
    @pytest.mark.asyncio
    async def test_real_cloud_run_metadata_structure(self):
        """Test with realistic Cloud Run metadata structure."""
        detector = CloudEnvironmentDetector()
        detector.clear_cache()
        
        # Simulate real Cloud Run metadata responses
        realistic_responses = {
            "instance/attributes/goog-cloudrun-service-name": "netra-backend-staging",
            "project/project-id": "netra-staging-12345",
            "instance/region": "projects/123456789/regions/us-central1",
            "instance/attributes/goog-revision": "netra-backend-staging-00001-rev"
        }
        
        async def mock_fetch_metadata(session, endpoint):
            response = realistic_responses.get(endpoint)
            if response:
                return response
            return None
        
        with patch.object(detector, '_fetch_metadata', side_effect=mock_fetch_metadata):
            context = await detector.detect_environment_context()
            
            # Verify all metadata is correctly parsed
            assert context.environment_type == EnvironmentType.STAGING
            assert context.cloud_platform == CloudPlatform.CLOUD_RUN
            assert context.service_name == "netra-backend-staging"
            assert context.project_id == "netra-staging-12345"
            assert context.region == "us-central1"  # Should extract region name from full path
            assert context.revision == "netra-backend-staging-00001-rev"
            assert context.confidence_score == 0.9
    
    @pytest.mark.asyncio
    async def test_golden_path_critical_scenario(self):
        """
        Test the critical scenario that causes Golden Path failures.
        
        This test validates that staging environment is correctly detected
        in Cloud Run, preventing the localhost:8081 connection issue.
        """
        detector = CloudEnvironmentDetector()
        detector.clear_cache()
        
        # Simulate the exact Cloud Run staging environment
        with patch.dict(os.environ, {
            "K_SERVICE": "netra-backend-staging",
            "GOOGLE_CLOUD_PROJECT": "netra-staging",
            "K_REVISION": "netra-backend-staging-00001-abc"
        }, clear=False):
            
            # Mock successful metadata API (what happens in real Cloud Run)
            realistic_metadata = {
                "instance/attributes/goog-cloudrun-service-name": "netra-backend-staging",
                "project/project-id": "netra-staging",
                "instance/region": "projects/123456/regions/us-central1"
            }
            
            with patch.object(detector, '_fetch_metadata', side_effect=lambda session, endpoint: realistic_metadata.get(endpoint)):
                context = await detector.detect_environment_context()
                
                # CRITICAL ASSERTIONS - These prevent the Golden Path failure
                assert context.environment_type == EnvironmentType.STAGING, "Must detect STAGING, not DEVELOPMENT"
                assert context.confidence_score >= 0.7, "Must have high confidence to prevent fallback"
                
                # This is the key fix - no more DEVELOPMENT default!
                assert context.environment_type != EnvironmentType.DEVELOPMENT, "DEVELOPMENT default eliminated"
                
                # Verify complete context for Golden Path validation
                assert context.cloud_platform == CloudPlatform.CLOUD_RUN
                assert context.service_name == "netra-backend-staging"
                assert "netra-staging" in context.project_id
                
                # Log the success for debugging
                print(f"✅ GOLDEN PATH FIX VALIDATED:")
                print(f"   Environment: {context.environment_type.value}")
                print(f"   Confidence: {context.confidence_score}")
                print(f"   Platform: {context.cloud_platform.value}")
                print(f"   Service: {context.service_name}")
                print(f"   ❌ NO MORE localhost:8081 in staging!")


class TestEnvironmentDetectionFailureCases:
    """Test failure scenarios and error handling."""
    
    @pytest.mark.asyncio
    async def test_metadata_api_network_error(self):
        """Test handling of metadata API network errors."""
        detector = CloudEnvironmentDetector()
        detector.clear_cache()
        
        with patch.object(detector, '_fetch_metadata', side_effect=Exception("Network error")):
            # Should fall back to environment variables if available
            with patch.dict(os.environ, {"ENVIRONMENT": "staging"}, clear=False):
                context = await detector.detect_environment_context()
                assert context.environment_type == EnvironmentType.STAGING
    
    @pytest.mark.asyncio 
    async def test_partial_metadata_availability(self):
        """Test handling when only some metadata is available."""
        detector = CloudEnvironmentDetector()
        detector.clear_cache()
        
        # Only service name available, other metadata fails
        partial_responses = {
            "instance/attributes/goog-cloudrun-service-name": "netra-backend-staging"
        }
        
        async def mock_fetch_metadata(session, endpoint):
            return partial_responses.get(endpoint)
        
        with patch.object(detector, '_fetch_metadata', side_effect=mock_fetch_metadata):
            context = await detector.detect_environment_context()
            
            assert context.environment_type == EnvironmentType.STAGING
            assert context.service_name == "netra-backend-staging"
            assert context.project_id is None  # Should handle missing gracefully
            assert context.region is None
    
    @pytest.mark.asyncio
    async def test_conflicting_environment_signals(self):
        """Test handling of conflicting environment signals."""
        detector = CloudEnvironmentDetector()
        detector.clear_cache()
        
        # Environment variables suggest production, but service name suggests staging
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "K_SERVICE": "netra-backend-staging"  # Conflicting signal
        }, clear=False):
            
            with patch.object(detector, '_fetch_metadata', return_value=None):
                context = await detector.detect_environment_context()
                
                # Should prioritize explicit ENVIRONMENT variable
                assert context.environment_type == EnvironmentType.PRODUCTION
                assert context.confidence_score >= 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
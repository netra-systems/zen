"""
CloudEnvironmentDetector Confidence Failure Reproduction Test

ISSUE #523: Golden Path Environment Detection Confidence Failure
ERROR: "Best confidence: 0.00, required: 0.7"

This test reproduces the environment detection confidence failure by mocking
an environment where all 4 detection strategies return None or low confidence.

EXPECTED TEST RESULT: FAILURE - This test is designed to FAIL and reproduce 
the exact error reported in Issue #523.

TEST SCENARIOS:
1. All GCP metadata API calls fail or return None
2. No ENVIRONMENT or K_SERVICE environment variables set  
3. No GCP project variables (GOOGLE_CLOUD_PROJECT, etc.)
4. No App Engine variables (GAE_APPLICATION, etc.)

When all strategies fail, confidence = 0.00, which is < 0.7 required threshold.
"""
import pytest
import asyncio
import aiohttp
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.environment_context.cloud_environment_detector import CloudEnvironmentDetector, EnvironmentContext, EnvironmentType, CloudPlatform

class CloudEnvironmentDetectorConfidenceFailureTests(SSotAsyncTestCase):
    """
    Tests designed to reproduce the CloudEnvironmentDetector confidence failure.
    
    These tests mock environments where ALL detection strategies fail,
    resulting in 0.00 confidence and the specific RuntimeError we need to reproduce.
    """

    async def test_reproduce_confidence_failure_all_strategies_fail(self):
        """
        MAIN REPRODUCTION TEST: All detection strategies return None/fail.
        
        This test is DESIGNED TO FAIL and reproduce the exact error:
        "Cannot determine environment with sufficient confidence. 
         Best confidence: 0.00, required: 0.7"
        
        EXPECTED RESULT: RuntimeError with specific confidence message
        """
        detector = CloudEnvironmentDetector()
        detector.clear_cache()
        with patch.dict('os.environ', {}, clear=True):
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value.__aenter__.return_value = mock_session

                async def mock_fetch_metadata(endpoint):
                    return None
                with patch.object(detector, '_fetch_metadata', side_effect=mock_fetch_metadata):
                    with pytest.raises(RuntimeError) as exc_info:
                        await detector.detect_environment_context()
                    error_message = str(exc_info.value)
                    assert 'Best confidence: 0.00' in error_message, f"Expected 'Best confidence: 0.00' in error message. Actual: {error_message}"
                    assert 'required: 0.7' in error_message, f"Expected 'required: 0.7' in error message. Actual: {error_message}"
                    assert 'Cannot determine environment with sufficient confidence' in error_message, f'Expected confidence determination failure message. Actual: {error_message}'
                    assert 'Golden Path validation' in error_message, f'Expected Golden Path validation reference. Actual: {error_message}'

    async def test_confidence_failure_no_environment_variables(self):
        """
        Test confidence failure when no environment variables are set.
        
        EXPECTED RESULT: All environment-based strategies return None,
        contributing to overall 0.00 confidence.
        """
        detector = CloudEnvironmentDetector()
        env_vars_to_clear = ['ENVIRONMENT', 'K_SERVICE', 'GOOGLE_CLOUD_PROJECT', 'GCP_PROJECT', 'GCLOUD_PROJECT', 'K_REVISION', 'K_CONFIGURATION', 'GAE_APPLICATION', 'GAE_VERSION', 'GAE_SERVICE']
        with patch.dict('os.environ', {}, clear=True):
            result = await detector._detect_via_environment_variables()
            assert result is None, 'Environment variable detection should return None when no variables set'
            result = await detector._detect_via_gcp_service_variables()
            assert result is None, 'GCP service variables detection should return None when no variables set'
            result = await detector._detect_via_app_engine_metadata()
            assert result is None, 'App Engine metadata detection should return None when no variables set'

    async def test_confidence_failure_gcp_metadata_unavailable(self):
        """
        Test confidence failure when GCP metadata API is completely unavailable.
        
        Simulates environments where:
        - Not running in Cloud Run (no metadata service)
        - Metadata API timeouts
        - Metadata API returns 404/403 errors
        
        EXPECTED RESULT: Cloud Run metadata strategy returns None
        """
        detector = CloudEnvironmentDetector()
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session.get.side_effect = asyncio.TimeoutError('Metadata API timeout')
            result = await detector._detect_via_cloud_run_metadata()
            assert result is None, 'Cloud Run metadata detection should return None on timeout'
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_session.get.return_value.__aenter__.return_value = mock_response
            result = await detector._detect_via_cloud_run_metadata()
            assert result is None, 'Cloud Run metadata detection should return None on HTTP error'

    async def test_confidence_failure_integration_all_strategies_disabled(self):
        """
        INTEGRATION TEST: Verify all 4 detection strategies fail together.
        
        This test ensures that when we mock a complete environment failure,
        ALL strategies return None, leading to 0.00 overall confidence.
        
        EXPECTED RESULT: RuntimeError with 0.00 confidence
        """
        detector = CloudEnvironmentDetector()
        with patch.dict('os.environ', {}, clear=True):
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value.__aenter__.return_value = mock_session
                mock_session.get.side_effect = Exception('Metadata service unavailable')
                strategy_results = {}
                original_cloud_run = detector._detect_via_cloud_run_metadata
                original_env_vars = detector._detect_via_environment_variables
                original_gcp_vars = detector._detect_via_gcp_service_variables
                original_app_engine = detector._detect_via_app_engine_metadata

                async def track_cloud_run():
                    result = await original_cloud_run()
                    strategy_results['cloud_run'] = result
                    return result

                async def track_env_vars():
                    result = await original_env_vars()
                    strategy_results['env_vars'] = result
                    return result

                async def track_gcp_vars():
                    result = await original_gcp_vars()
                    strategy_results['gcp_vars'] = result
                    return result

                async def track_app_engine():
                    result = await original_app_engine()
                    strategy_results['app_engine'] = result
                    return result
                with patch.object(detector, '_detect_via_cloud_run_metadata', side_effect=track_cloud_run), patch.object(detector, '_detect_via_environment_variables', side_effect=track_env_vars), patch.object(detector, '_detect_via_gcp_service_variables', side_effect=track_gcp_vars), patch.object(detector, '_detect_via_app_engine_metadata', side_effect=track_app_engine):
                    with pytest.raises(RuntimeError) as exc_info:
                        await detector.detect_environment_context()
                    assert strategy_results['cloud_run'] is None, 'Cloud Run strategy should return None'
                    assert strategy_results['env_vars'] is None, 'Environment variables strategy should return None'
                    assert strategy_results['gcp_vars'] is None, 'GCP variables strategy should return None'
                    assert strategy_results['app_engine'] is None, 'App Engine strategy should return None'
                    error_message = str(exc_info.value)
                    assert 'Best confidence: 0.00' in error_message
                    assert 'required: 0.7' in error_message

    async def test_partial_confidence_still_fails(self):
        """
        Test that even partial confidence (< 0.7) still causes failure.
        
        This test mocks a scenario where ONE strategy returns low confidence
        (e.g., 0.3) but it's still below the 0.7 threshold.
        
        EXPECTED RESULT: RuntimeError with confidence like "0.30, required: 0.7"
        """
        detector = CloudEnvironmentDetector()
        with patch.dict('os.environ', {'GOOGLE_CLOUD_PROJECT': 'unknown-project'}, clear=True):
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value.__aenter__.return_value = mock_session
                mock_session.get.side_effect = Exception('Metadata service unavailable')
                with pytest.raises(RuntimeError) as exc_info:
                    await detector.detect_environment_context()
                error_message = str(exc_info.value)
                assert 'required: 0.7' in error_message
                assert '0.30' in error_message or '0.3' in error_message, f'Expected low confidence around 0.30. Actual error: {error_message}'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
"""
Pre-Deployment Environment URL Validation Tests

PURPOSE: Validate service URLs match expected environment patterns before deployment
CONTEXT: Process Improvement - Would have caught localhost:8081 in staging issue
BUSINESS IMPACT: Protects $500K+ ARR Golden Path functionality from environment config errors

These tests MUST PASS before any staging/production deployment.
Designed to catch the specific root cause: localhost URLs being used in Cloud Run environments.
"""
import pytest
import os
import asyncio
from unittest.mock import patch, Mock
from typing import Dict, Any
from enum import Enum
from netra_backend.app.core.service_dependencies.service_health_client import ServiceHealthClient
from netra_backend.app.core.service_dependencies.models import ServiceType, EnvironmentType
from netra_backend.app.core.environment_context.cloud_environment_detector import CloudEnvironmentDetector, EnvironmentType as DetectorEnvironmentType

class ServiceHealthClientEnvironmentURLValidationTests:
    """
    Test ServiceHealthClient uses correct URLs for each environment.
    
    CRITICAL: These tests would have caught localhost:8081 being used in staging.
    """

    @pytest.fixture
    def mock_environment_context_service(self):
        """Mock environment context service for controlled testing."""
        mock_service = Mock()
        mock_service.is_initialized.return_value = True
        return mock_service

    def create_mock_environment_context(self, environment_type: DetectorEnvironmentType):
        """Create mock environment context for specified environment type."""
        mock_context = Mock()
        mock_context.environment_type = environment_type
        return mock_context

    @pytest.mark.pre_deployment
    @pytest.mark.environment_validation
    @pytest.mark.parametrize('environment,expected_auth_url,expected_backend_url', [(EnvironmentType.DEVELOPMENT, 'http://localhost:8081', 'http://localhost:8000'), (EnvironmentType.STAGING, 'https://auth.staging.netrasystems.ai', 'https://api.staging.netrasystems.ai'), (EnvironmentType.PRODUCTION, 'https://auth.netrasystems.ai', 'https://api.netrasystems.ai')])
    def test_service_health_client_environment_url_mapping(self, environment: EnvironmentType, expected_auth_url: str, expected_backend_url: str, mock_environment_context_service):
        """
        Test ServiceHealthClient URL mapping for each environment.
        
        CRITICAL: This test would have caught localhost:8081 in staging.
        """
        detector_env_map = {EnvironmentType.DEVELOPMENT: DetectorEnvironmentType.DEVELOPMENT, EnvironmentType.STAGING: DetectorEnvironmentType.STAGING, EnvironmentType.PRODUCTION: DetectorEnvironmentType.PRODUCTION, EnvironmentType.TESTING: DetectorEnvironmentType.TESTING}
        detector_environment = detector_env_map[environment]
        mock_context = self.create_mock_environment_context(detector_environment)
        mock_environment_context_service.get_environment_context.return_value = mock_context
        client = ServiceHealthClient(environment_context_service=mock_environment_context_service)
        actual_auth_url = client.service_urls[ServiceType.AUTH_SERVICE]
        actual_backend_url = client.service_urls[ServiceType.BACKEND_SERVICE]
        assert actual_auth_url == expected_auth_url, f'Auth service URL mismatch for {environment.value}: expected {expected_auth_url}, got {actual_auth_url}'
        assert actual_backend_url == expected_backend_url, f'Backend service URL mismatch for {environment.value}: expected {expected_backend_url}, got {actual_backend_url}'
        if environment in [EnvironmentType.STAGING, EnvironmentType.PRODUCTION]:
            assert 'localhost' not in actual_auth_url, f'localhost found in {environment.value} auth URL: {actual_auth_url}. This would cause connection failures in Cloud Run.'
            assert 'localhost' not in actual_backend_url, f'localhost found in {environment.value} backend URL: {actual_backend_url}. This would cause connection failures in Cloud Run.'
            assert 'netrasystems.ai' in actual_auth_url, f'Expected netrasystems.ai domain in {environment.value} auth URL: {actual_auth_url}'

    @pytest.mark.pre_deployment
    @pytest.mark.environment_validation
    @pytest.mark.critical
    def test_staging_environment_never_uses_localhost_urls(self, mock_environment_context_service):
        """
        CRITICAL TEST: Ensure staging environment never uses localhost URLs.
        
        This test specifically catches the root cause issue:
        localhost:8081 being used in staging Cloud Run environment.
        """
        staging_context = self.create_mock_environment_context(DetectorEnvironmentType.STAGING)
        mock_environment_context_service.get_environment_context.return_value = staging_context
        client = ServiceHealthClient(environment_context_service=mock_environment_context_service)
        all_urls = list(client.service_urls.values())
        for url in all_urls:
            assert 'localhost' not in url, f'CRITICAL BUG DETECTED: localhost URL found in staging configuration: {url}. This would cause Golden Path validation failures in Cloud Run staging environment. All staging URLs must use staging.netrasystems.ai domain.'
        auth_url = client.service_urls[ServiceType.AUTH_SERVICE]
        assert auth_url == 'https://auth.staging.netrasystems.ai', f'Auth service URL incorrect for staging: {auth_url}. Expected: https://auth.staging.netrasystems.ai'
        backend_url = client.service_urls[ServiceType.BACKEND_SERVICE]
        assert backend_url == 'https://api.staging.netrasystems.ai', f'Backend service URL incorrect for staging: {backend_url}. Expected: https://api.staging.netrasystems.ai'

    @pytest.mark.pre_deployment
    @pytest.mark.environment_validation
    @pytest.mark.critical
    def test_production_environment_never_uses_localhost_urls(self, mock_environment_context_service):
        """
        CRITICAL TEST: Ensure production environment never uses localhost URLs.
        
        Similar protection for production environment.
        """
        production_context = self.create_mock_environment_context(DetectorEnvironmentType.PRODUCTION)
        mock_environment_context_service.get_environment_context.return_value = production_context
        client = ServiceHealthClient(environment_context_service=mock_environment_context_service)
        all_urls = list(client.service_urls.values())
        for url in all_urls:
            assert 'localhost' not in url, f'CRITICAL BUG DETECTED: localhost URL found in production configuration: {url}. This would cause service failures in production environment. All production URLs must use netrasystems.ai domain.'
        auth_url = client.service_urls[ServiceType.AUTH_SERVICE]
        assert auth_url == 'https://auth.netrasystems.ai', f'Auth service URL incorrect for production: {auth_url}. Expected: https://auth.netrasystems.ai'

class CloudRunEnvironmentDetectionTests:
    """
    Test environment detection in Cloud Run scenarios.
    
    CRITICAL: These tests would have caught environment detection defaulting to DEVELOPMENT in staging.
    """

    @pytest.mark.pre_deployment
    @pytest.mark.environment_validation
    @pytest.mark.asyncio
    async def test_cloud_run_staging_environment_never_defaults_to_development(self):
        """
        CRITICAL TEST: Staging Cloud Run environment never misdetected as development.
        
        This test would have caught the DEVELOPMENT default that caused
        localhost:8081 to be used in staging.
        """
        staging_env_vars = {'K_SERVICE': 'netra-backend-staging', 'GOOGLE_CLOUD_PROJECT': 'netra-staging', 'K_REVISION': 'netra-backend-staging-00001-abc'}
        with patch.dict(os.environ, staging_env_vars, clear=False):
            detector = CloudEnvironmentDetector()
            detector.clear_cache()
            context = await detector.detect_environment_context()
            assert context.environment_type == DetectorEnvironmentType.STAGING, f'CRITICAL BUG DETECTED: Staging Cloud Run environment misdetected as {context.environment_type}. Expected: {DetectorEnvironmentType.STAGING}. This causes localhost URLs to be used in staging Cloud Run, breaking Golden Path.'
            assert context.environment_type != DetectorEnvironmentType.DEVELOPMENT, f'CRITICAL BUG DETECTED: Staging environment incorrectly defaulted to DEVELOPMENT. This causes localhost:8081 to be used instead of https://auth.staging.netrasystems.ai'
            assert context.confidence_score >= 0.8, f'Environment detection confidence too low: {context.confidence_score}. Low confidence may cause fallback to incorrect environment defaults.'
            from netra_backend.app.core.environment_context.environment_context_service import get_environment_context_service
            with patch.object(get_environment_context_service(), 'get_environment_context', return_value=context):
                service_client = ServiceHealthClient()
                auth_url = service_client.service_urls[ServiceType.AUTH_SERVICE]
                assert auth_url == 'https://auth.staging.netrasystems.ai', f'Service URL mapping failed after environment detection: {auth_url}. Expected: https://auth.staging.netrasystems.ai'
                assert 'localhost:8081' not in auth_url, f'CRITICAL BUG DETECTED: localhost:8081 found in staging service URL: {auth_url}. This is the exact issue that broke Golden Path validation.'

    @pytest.mark.pre_deployment
    @pytest.mark.environment_validation
    @pytest.mark.asyncio
    async def test_cloud_run_production_environment_detection(self):
        """
        Test production Cloud Run environment detection.
        
        Similar protection for production environment detection.
        """
        production_env_vars = {'K_SERVICE': 'netra-backend', 'GOOGLE_CLOUD_PROJECT': 'netra-production', 'K_REVISION': 'netra-backend-00001-xyz'}
        with patch.dict(os.environ, production_env_vars, clear=False):
            detector = CloudEnvironmentDetector()
            detector.clear_cache()
            context = await detector.detect_environment_context()
            assert context.environment_type == DetectorEnvironmentType.PRODUCTION, f'Production Cloud Run environment misdetected as {context.environment_type}. Expected: {DetectorEnvironmentType.PRODUCTION}'
            assert context.environment_type != DetectorEnvironmentType.DEVELOPMENT, f'Production environment incorrectly defaulted to DEVELOPMENT'

    @pytest.mark.pre_deployment
    @pytest.mark.environment_validation
    @pytest.mark.parametrize('cloud_run_scenario,expected_environment', [({'K_SERVICE': 'netra-backend-staging', 'GOOGLE_CLOUD_PROJECT': 'netra-staging'}, DetectorEnvironmentType.STAGING), ({'K_SERVICE': 'netra-backend', 'GOOGLE_CLOUD_PROJECT': 'netra-production'}, DetectorEnvironmentType.PRODUCTION), ({'K_SERVICE': 'netra-backend-dev', 'GOOGLE_CLOUD_PROJECT': 'netra-development'}, DetectorEnvironmentType.DEVELOPMENT)])
    @pytest.mark.asyncio
    async def test_cloud_run_environment_scenarios_never_default_incorrectly(self, cloud_run_scenario: Dict[str, str], expected_environment: DetectorEnvironmentType):
        """
        Test various Cloud Run scenarios never default to wrong environment.
        
        Comprehensive test to prevent environment misdetection.
        """
        with patch.dict(os.environ, cloud_run_scenario, clear=False):
            detector = CloudEnvironmentDetector()
            detector.clear_cache()
            context = await detector.detect_environment_context()
            assert context.environment_type == expected_environment, f'Cloud Run scenario {cloud_run_scenario} detected as {context.environment_type}, expected {expected_environment}'
            if expected_environment in [DetectorEnvironmentType.STAGING, DetectorEnvironmentType.PRODUCTION]:
                with patch('netra_backend.app.core.service_dependencies.service_health_client.get_environment_context_service') as mock_service:
                    mock_service.return_value.is_initialized.return_value = True
                    mock_service.return_value.get_environment_context.return_value = context
                    service_client = ServiceHealthClient()
                    auth_url = service_client.service_urls[ServiceType.AUTH_SERVICE]
                    assert 'localhost' not in auth_url, f'localhost URL found for {expected_environment.value}: {auth_url}'

class GoldenPathEnvironmentIntegrationTests:
    """
    Test Golden Path integration with environment-specific configurations.
    
    These tests validate the complete integration that would have caught
    the end-to-end Golden Path failure.
    """

    @pytest.mark.pre_deployment
    @pytest.mark.golden_path
    @pytest.mark.environment_validation
    @pytest.mark.asyncio
    async def test_golden_path_staging_environment_integration(self):
        """
        CRITICAL TEST: Golden Path integration with staging environment.
        
        This test validates the complete chain that failed:
        1. Environment detection in Cloud Run staging
        2. Service URL mapping
        3. Golden Path validation prerequisites
        """
        staging_env_vars = {'K_SERVICE': 'netra-backend-staging', 'GOOGLE_CLOUD_PROJECT': 'netra-staging', 'K_REVISION': 'netra-backend-staging-00001-abc'}
        with patch.dict(os.environ, staging_env_vars, clear=False):
            detector = CloudEnvironmentDetector()
            detector.clear_cache()
            context = await detector.detect_environment_context()
            assert context.environment_type == DetectorEnvironmentType.STAGING
            with patch('netra_backend.app.core.service_dependencies.service_health_client.get_environment_context_service') as mock_service:
                mock_service.return_value.is_initialized.return_value = True
                mock_service.return_value.get_environment_context.return_value = context
                service_client = ServiceHealthClient()
                auth_url = service_client.service_urls[ServiceType.AUTH_SERVICE]
                backend_url = service_client.service_urls[ServiceType.BACKEND_SERVICE]
                assert auth_url == 'https://auth.staging.netrasystems.ai'
                assert backend_url == 'https://api.staging.netrasystems.ai'
                assert 'localhost' not in auth_url
                assert 'localhost' not in backend_url
                golden_path_urls = {'auth_service': auth_url, 'backend_service': backend_url}
                assert all(('staging.netrasystems.ai' in url for url in golden_path_urls.values())), f'Golden Path URLs must use staging domain: {golden_path_urls}'
                assert all(('localhost' not in url for url in golden_path_urls.values())), f'CRITICAL: Golden Path URLs contain localhost: {golden_path_urls}. This would cause connection failures in Cloud Run.'

    @pytest.mark.pre_deployment
    @pytest.mark.golden_path
    @pytest.mark.environment_validation
    def test_golden_path_url_configuration_matrix(self):
        """
        Test Golden Path URL configuration for all environments.
        
        Matrix test to validate Golden Path works with correct URLs for each environment.
        """
        environment_url_matrix = {DetectorEnvironmentType.DEVELOPMENT: {'auth_service': 'http://localhost:8081', 'backend_service': 'http://localhost:8000'}, DetectorEnvironmentType.STAGING: {'auth_service': 'https://auth.staging.netrasystems.ai', 'backend_service': 'https://api.staging.netrasystems.ai'}, DetectorEnvironmentType.PRODUCTION: {'auth_service': 'https://auth.netrasystems.ai', 'backend_service': 'https://api.netrasystems.ai'}}
        for environment, expected_urls in environment_url_matrix.items():
            with patch('netra_backend.app.core.service_dependencies.service_health_client.get_environment_context_service') as mock_service:
                mock_context = Mock()
                mock_context.environment_type = environment
                mock_service.return_value.is_initialized.return_value = True
                mock_service.return_value.get_environment_context.return_value = mock_context
                service_client = ServiceHealthClient()
                assert service_client.service_urls[ServiceType.AUTH_SERVICE] == expected_urls['auth_service']
                assert service_client.service_urls[ServiceType.BACKEND_SERVICE] == expected_urls['backend_service']
                if environment != DetectorEnvironmentType.DEVELOPMENT:
                    for url in service_client.service_urls.values():
                        assert 'localhost' not in url, f'localhost URL found in {environment.value}: {url}'
                        assert 'netrasystems.ai' in url, f'netrasystems.ai domain missing in {environment.value}: {url}'
pytestmark = [pytest.mark.pre_deployment, pytest.mark.environment_validation, pytest.mark.critical]
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
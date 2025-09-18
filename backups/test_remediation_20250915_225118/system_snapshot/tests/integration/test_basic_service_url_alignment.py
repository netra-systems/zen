from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
'\nBasic Service URL Alignment Tests\n\nBusiness Value Justification (BVJ):\n- Segment: All tiers (Free, Early, Mid, Enterprise)\n- Business Goal: Platform Stability & Risk Reduction\n- Value Impact: Prevents service communication failures due to URL misconfiguration\n- Strategic Impact: Foundational test ensuring services can find and communicate with each other\n\nThis test verifies that services have correctly configured URLs for communicating with each other.\nMissing or incorrect service URLs are a common cause of deployment failures and integration issues.\n'
import asyncio
import os
import pytest
from typing import Dict, List, Optional
from netra_backend.app.core.unified_logging import central_logger
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
logger = central_logger.get_logger(__name__)

class ServiceURLAlignmentTester:
    """Tests basic URL alignment between services."""

    def __init__(self):
        """Initialize URL alignment tester."""
        self.services_to_test = ['auth_service', 'netra_backend', 'frontend']
        self.expected_url_patterns = {'auth_service': {'development': 'http://127.0.0.1:8001', 'staging': 'https://auth.staging.netrasystems.ai', 'production': 'https://auth.netrasystems.ai'}, 'netra_backend': {'development': 'http://127.0.0.1:8000', 'staging': 'https://api.staging.netrasystems.ai', 'production': 'https://api.netrasystems.ai'}, 'frontend': {'development': 'http://127.0.0.1:3000', 'staging': 'https://app.staging.netrasystems.ai', 'production': 'https://app.netrasystems.ai'}}

    def get_current_environment(self) -> str:
        """Detect current environment from environment variables."""
        if get_env().get('TESTING') == 'true':
            return 'development'
        elif get_env().get('ENVIRONMENT') == 'staging':
            return 'staging'
        elif get_env().get('ENVIRONMENT') == 'production':
            return 'production'
        else:
            return 'development'

    async def test_auth_service_url_configuration(self) -> Dict[str, bool]:
        """Test that netra_backend has correct auth service URL configured."""
        current_env = self.get_current_environment()
        expected_auth_url = self.expected_url_patterns['auth_service'][current_env]
        results = {}
        try:
            auth_service_url = get_env().get('AUTH_SERVICE_URL')
            if auth_service_url:
                url_matches = auth_service_url.rstrip('/') == expected_auth_url.rstrip('/')
                results['environment_variable_match'] = url_matches
                if not url_matches:
                    logger.warning(f'AUTH_SERVICE_URL mismatch: got {auth_service_url}, expected {expected_auth_url}')
            else:
                results['environment_variable_match'] = False
                logger.warning('AUTH_SERVICE_URL not set in environment')
            if auth_service_url:
                is_valid_url = self._is_valid_url_format(auth_service_url)
                results['url_format_valid'] = is_valid_url
                if not is_valid_url:
                    logger.warning(f'Invalid URL format: {auth_service_url}')
            else:
                results['url_format_valid'] = False
        except Exception as e:
            logger.error(f'Error testing auth service URL configuration: {e}')
            results['error'] = str(e)
        return results

    async def test_backend_service_url_configuration(self) -> Dict[str, bool]:
        """Test that frontend has correct backend service URL configured."""
        current_env = self.get_current_environment()
        expected_backend_url = self.expected_url_patterns['netra_backend'][current_env]
        results = {}
        try:
            backend_url_vars = ['REACT_APP_API_URL', 'API_URL', 'BACKEND_URL', 'NEXT_PUBLIC_API_URL']
            backend_url = None
            for var_name in backend_url_vars:
                backend_url = get_env().get(var_name)
                if backend_url:
                    break
            if backend_url:
                url_matches = backend_url.rstrip('/') == expected_backend_url.rstrip('/')
                results['environment_variable_match'] = url_matches
                if not url_matches:
                    logger.warning(f'Backend URL mismatch: got {backend_url}, expected {expected_backend_url}')
            elif current_env == 'development':
                results['environment_variable_match'] = True
                logger.info('Backend URL not explicitly configured - acceptable for development')
            else:
                results['environment_variable_match'] = False
                logger.warning('Backend URL not configured for non-development environment')
            if backend_url:
                is_valid_url = self._is_valid_url_format(backend_url)
                results['url_format_valid'] = is_valid_url
                if not is_valid_url:
                    logger.warning(f'Invalid backend URL format: {backend_url}')
            else:
                results['url_format_valid'] = True
        except Exception as e:
            logger.error(f'Error testing backend service URL configuration: {e}')
            results['error'] = str(e)
        return results

    async def test_cross_service_url_consistency(self) -> Dict[str, bool]:
        """Test that all services have consistent URL configurations."""
        current_env = self.get_current_environment()
        results = {}
        try:
            configured_urls = {}
            auth_url = get_env().get('AUTH_SERVICE_URL')
            if auth_url:
                configured_urls['auth_service'] = auth_url
            backend_url_vars = ['REACT_APP_API_URL', 'API_URL', 'BACKEND_URL', 'NEXT_PUBLIC_API_URL']
            for var_name in backend_url_vars:
                backend_url = get_env().get(var_name)
                if backend_url:
                    configured_urls['netra_backend'] = backend_url
                    break
            frontend_url_vars = ['FRONTEND_URL', 'APP_URL', 'CLIENT_URL']
            for var_name in frontend_url_vars:
                frontend_url = get_env().get(var_name)
                if frontend_url:
                    configured_urls['frontend'] = frontend_url
                    break
            consistent_count = 0
            total_configured = len(configured_urls)
            for service_name, configured_url in configured_urls.items():
                expected_url = self.expected_url_patterns.get(service_name, {}).get(current_env)
                if expected_url:
                    if configured_url.rstrip('/') == expected_url.rstrip('/'):
                        consistent_count += 1
                    else:
                        logger.warning(f'URL inconsistency for {service_name}: configured={configured_url}, expected={expected_url}')
            if total_configured > 0:
                consistency_percentage = consistent_count / total_configured * 100
                results['consistency_percentage'] = consistency_percentage
                results['all_urls_consistent'] = consistency_percentage == 100.0
            else:
                results['consistency_percentage'] = 0.0
                results['all_urls_consistent'] = False
                logger.warning('No service URLs configured - this may cause communication issues')
            results['configured_services_count'] = total_configured
            results['consistent_services_count'] = consistent_count
        except Exception as e:
            logger.error(f'Error testing cross-service URL consistency: {e}')
            results['error'] = str(e)
        return results

    def _is_valid_url_format(self, url: str) -> bool:
        """Basic URL format validation."""
        if not url:
            return False
        url = url.strip()
        if not url:
            return False
        if not (url.startswith('http://') or url.startswith('https://')):
            return False
        if '://' in url:
            domain_part = url.split('://')[1].split('/')[0]
            if not domain_part:
                return False
            host_part = domain_part.split(':')[0] if ':' in domain_part else domain_part
            if '.' in host_part or host_part == 'localhost' or host_part.startswith('127.0.0.1') or host_part.startswith('192.168.') or host_part.startswith('10.'):
                return True
        return False

@pytest.fixture
def url_tester():
    """Create URL alignment tester instance."""
    return ServiceURLAlignmentTester()

class BasicServiceURLAlignmentTests:
    """Test suite for basic service URL alignment."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_auth_service_url_alignment(self, url_tester):
        """Test that auth service URL is correctly configured."""
        results = await url_tester.test_auth_service_url_configuration()
        logger.info(f'Auth service URL test results: {results}')
        current_env = url_tester.get_current_environment()
        auth_service_url = get_env().get('AUTH_SERVICE_URL')
        if current_env == 'development' and auth_service_url:
            assert results.get('environment_variable_match', False), f"AUTH_SERVICE_URL should match expected format for development environment. Found: {auth_service_url}, Expected: {url_tester.expected_url_patterns['auth_service']['development']}"
        if not results.get('error') and auth_service_url:
            assert results.get('url_format_valid', False), 'Auth service URL format should be valid'
        elif not auth_service_url:
            logger.info('AUTH_SERVICE_URL not configured - this may be acceptable depending on deployment setup')

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_backend_service_url_alignment(self, url_tester):
        """Test that backend service URL is correctly configured."""
        results = await url_tester.test_backend_service_url_configuration()
        logger.info(f'Backend service URL test results: {results}')
        if not results.get('error'):
            assert results.get('url_format_valid', False), 'Backend service URL format should be valid'
        current_env = url_tester.get_current_environment()
        if current_env in ['staging', 'production']:
            assert results.get('environment_variable_match', False), f'Backend service URL must be explicitly configured for {current_env} environment'

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_cross_service_url_consistency(self, url_tester):
        """Test that all service URLs are consistent with environment expectations."""
        results = await url_tester.test_cross_service_url_consistency()
        logger.info(f'Cross-service URL consistency results: {results}')
        if not results.get('error'):
            configured_services_count = results.get('configured_services_count', 0)
            if configured_services_count == 0:
                logger.info('No service URLs explicitly configured - may be using implicit configuration')
                logger.warning('Consider explicitly configuring service URLs for better deployment reliability')
            else:
                consistency_percentage = results.get('consistency_percentage', 0.0)
                current_env = url_tester.get_current_environment()
                if current_env == 'development':
                    assert consistency_percentage >= 50.0, f"URL consistency too low: {consistency_percentage}%. Configured services: {configured_services_count}, Consistent services: {results.get('consistent_services_count', 0)}"
                else:
                    assert consistency_percentage >= 80.0, f'URL consistency too low for {current_env}: {consistency_percentage}%'

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_environment_detection_accuracy(self, url_tester):
        """Test that environment detection works correctly."""
        detected_env = url_tester.get_current_environment()
        expected_environments = ['development', 'staging', 'production']
        assert detected_env in expected_environments, f"Detected environment '{detected_env}' not in expected environments: {expected_environments}"
        if get_env().get('TESTING') == 'true':
            assert detected_env == 'development', f"Should detect 'development' environment in test context, got '{detected_env}'"
        logger.info(f'Successfully detected environment: {detected_env}')

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_url_format_validation(self, url_tester):
        """Test URL format validation functionality."""
        valid_urls = ['http://127.0.0.1:8001', 'https://auth.netrasystems.ai', 'http://localhost:3000', 'https://api.staging.netrasystems.ai']
        for url in valid_urls:
            assert url_tester._is_valid_url_format(url), f'URL should be valid: {url}'
        invalid_urls = ['', 'not-a-url', 'ftp://invalid-protocol.com', 'http://', 'https://', 'http:///no-domain', None]
        for url in invalid_urls:
            assert not url_tester._is_valid_url_format(url), f'URL should be invalid: {url}'
        logger.info('URL format validation working correctly')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
_lazy_imports = {}

def lazy_import(module_path: str, component: str=None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f'Warning: Failed to lazy load {module_path}: {e}')
            _lazy_imports[module_path] = None
    return _lazy_imports[module_path]
_lazy_imports = {}

def lazy_import(module_path: str, component: str=None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f'Warning: Failed to lazy load {module_path}: {e}')
            _lazy_imports[module_path] = None
    return _lazy_imports[module_path]
'\nIntegration Test for Environment Context Golden Path Fix\n\nThis test validates the complete fix for the critical Golden Path issue\nwhere staging services were connecting to localhost:8081 instead of \nproper staging URLs due to EnvironmentType.DEVELOPMENT defaults.\n\nBUSINESS IMPACT: Protects 500K+ ARR by ensuring Golden Path validation \nworks correctly in staging Cloud Run environments.\n'
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import os
from typing import Dict, Any
from netra_backend.app.core.environment_context import CloudEnvironmentDetector, EnvironmentContextService, EnvironmentContext, EnvironmentType, CloudPlatform, initialize_environment_context, get_environment_context_service
from netra_backend.app.core.service_dependencies.golden_path_validator import GoldenPathValidator
from netra_backend.app.core.service_dependencies.service_health_client import ServiceHealthClient
from netra_backend.app.core.service_dependencies.models import ServiceType
from netra_backend.app.services.user_execution_context import UserExecutionContext

@pytest.mark.integration
class EnvironmentContextGoldenPathFixTests:

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.from_request(user_id='test_user', thread_id='test_thread', run_id='test_run')
    'Integration tests for the complete Golden Path environment fix.'

    @pytest.fixture
    def clear_environment_cache(self):
        """Clear all environment detection caches."""
        detector = CloudEnvironmentDetector()
        detector.clear_cache()
        service = get_environment_context_service()
        service._initialized = False
        service._context = None
        service._service_configs.clear()
        yield
        detector.clear_cache()
        service._initialized = False
        service._context = None
        service._service_configs.clear()

    @pytest.mark.asyncio
    async def test_complete_staging_golden_path_fix(self, clear_environment_cache):
        """
        Test the complete fix for staging Golden Path validation.
        
        CRITICAL: This test validates the exact scenario that was causing
        500K+ ARR Golden Path failures in Cloud Run staging.
        """
        cloud_run_env = {'K_SERVICE': 'netra-backend-staging', 'GOOGLE_CLOUD_PROJECT': 'netra-staging', 'K_REVISION': 'netra-backend-staging-00001-abc'}
        metadata_responses = {'instance/attributes/goog-cloudrun-service-name': 'netra-backend-staging', 'project/project-id': 'netra-staging', 'instance/region': 'projects/123456/regions/us-central1', 'instance/attributes/goog-revision': 'netra-backend-staging-00001-abc'}
        with patch.dict(os.environ, cloud_run_env, clear=False):

            async def mock_fetch_metadata(session, endpoint):
                return metadata_responses.get(endpoint)
            detector = CloudEnvironmentDetector()
            with patch.object(detector, '_fetch_metadata', side_effect=mock_fetch_metadata):
                service = EnvironmentContextService(detector=detector)
                await service.initialize()
                context = service.get_environment_context()
                assert context.environment_type == EnvironmentType.STAGING, 'Must detect STAGING in Cloud Run'
                assert context.confidence_score >= 0.7, 'Must have high confidence'
                assert context.cloud_platform == CloudPlatform.CLOUD_RUN, 'Must detect Cloud Run platform'
                config = service.get_service_configuration()
                auth_url = config.get_service_url('auth_service')
                backend_url = config.get_service_url('backend_service')
                assert auth_url == 'https://auth.staging.netrasystems.ai', f'Wrong auth URL: {auth_url}'
                assert backend_url == 'https://api.staging.netrasystems.ai', f'Wrong backend URL: {backend_url}'
                assert 'localhost' not in auth_url, 'localhost found in staging auth URL!'
                assert 'localhost' not in backend_url, 'localhost found in staging backend URL!'
                print(f' PASS:  GOLDEN PATH FIX VALIDATED:')
                print(f'   Environment: {context.environment_type.value}')
                print(f'   Auth Service: {auth_url}')
                print(f'   Backend Service: {backend_url}')
                print(f'    FAIL:  NO MORE localhost:8081 in staging!')

    @pytest.mark.asyncio
    async def test_golden_path_validator_uses_correct_environment(self, clear_environment_cache):
        """
        Test that GoldenPathValidator uses correct environment context.
        
        This validates that the validator no longer defaults to DEVELOPMENT
        and properly uses detected staging environment.
        """
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend-staging'}, clear=False):
            detector = CloudEnvironmentDetector()
            detector.clear_cache()

            async def mock_fetch_metadata(session, endpoint):
                if endpoint == 'instance/attributes/goog-cloudrun-service-name':
                    return 'netra-backend-staging'
                return None
            with patch.object(detector, '_fetch_metadata', side_effect=mock_fetch_metadata):
                env_service = EnvironmentContextService(detector=detector)
                validator = GoldenPathValidator(environment_context_service=env_service)
                mock_app = Mock()
                with patch('netra_backend.app.core.service_dependencies.golden_path_validator.ServiceHealthClient') as mock_health_client:
                    mock_health_client.return_value.__aenter__ = AsyncMock()
                    mock_health_client.return_value.__aexit__ = AsyncMock()
                    mock_health_client.return_value.validate_auth_service_health = AsyncMock(return_value={'requirement': 'jwt_validation_ready', 'success': True, 'message': 'Staging auth service validated'})
                    result = await validator.validate_golden_path_services(mock_app, [ServiceType.AUTH_SERVICE])
                    mock_health_client.assert_called_once()
                    called_env_type = mock_health_client.call_args[0][0]
                    from netra_backend.app.core.service_dependencies.models import EnvironmentType as ModelsEnvironmentType
                    assert called_env_type == ModelsEnvironmentType.STAGING, f'ServiceHealthClient called with wrong environment: {called_env_type}'
                    assert called_env_type != ModelsEnvironmentType.DEVELOPMENT, 'Must not default to DEVELOPMENT'
                    print(f' PASS:  GOLDEN PATH VALIDATOR FIX VALIDATED:')
                    print(f'   ServiceHealthClient environment: {called_env_type.value}')
                    print(f'    FAIL:  NO MORE DEVELOPMENT default!')

    @pytest.mark.asyncio
    async def test_service_health_client_uses_correct_urls(self, clear_environment_cache):
        """
        Test that ServiceHealthClient uses correct staging URLs.
        
        This validates that the ServiceHealthClient will connect to
        https://auth.staging.netrasystems.ai instead of localhost:8081
        """
        from netra_backend.app.core.service_dependencies.models import EnvironmentType as ModelsEnvironmentType
        client = ServiceHealthClient(ModelsEnvironmentType.STAGING)
        service_urls = client._get_service_urls(ModelsEnvironmentType.STAGING)
        auth_url = service_urls.get(ServiceType.AUTH_SERVICE)
        backend_url = service_urls.get(ServiceType.BACKEND_SERVICE)
        assert auth_url == 'https://auth.staging.netrasystems.ai', f'Wrong auth URL: {auth_url}'
        assert backend_url == 'https://api.staging.netrasystems.ai', f'Wrong backend URL: {backend_url}'
        assert 'localhost' not in auth_url, 'localhost found in staging auth URL!'
        assert 'localhost' not in backend_url, 'localhost found in staging backend URL!'
        assert ':8081' not in auth_url, 'Port 8081 found in staging auth URL!'
        print(f' PASS:  SERVICE HEALTH CLIENT FIX VALIDATED:')
        print(f'   Auth URL: {auth_url}')
        print(f'   Backend URL: {backend_url}')
        print(f'    FAIL:  NO MORE localhost:8081!')

    @pytest.mark.asyncio
    async def test_environment_detection_failure_prevents_golden_path(self, clear_environment_cache):
        """
        Test that Golden Path validation fails fast when environment cannot be detected.
        
        This ensures we don't fall back to dangerous defaults.
        """
        with patch.dict(os.environ, {}, clear=True):
            detector = CloudEnvironmentDetector()
            detector.clear_cache()
            with patch.object(detector, '_fetch_metadata', return_value=None):
                env_service = EnvironmentContextService(detector=detector)
                validator = GoldenPathValidator(environment_context_service=env_service)
                mock_app = Mock()
                with pytest.raises(RuntimeError) as exc_info:
                    await validator.validate_golden_path_services(mock_app, [ServiceType.AUTH_SERVICE])
                assert 'Cannot determine environment with sufficient confidence' in str(exc_info.value)
                print(f' PASS:  FAIL-FAST BEHAVIOR VALIDATED:')
                print(f'   Error: {str(exc_info.value)}')
                print(f'    PASS:  NO DANGEROUS DEFAULTS!')

    @pytest.mark.asyncio
    async def test_production_environment_detection(self, clear_environment_cache):
        """Test production environment detection and URL configuration."""
        with patch.dict(os.environ, {'K_SERVICE': 'netra-backend', 'GOOGLE_CLOUD_PROJECT': 'netra-production'}, clear=False):
            detector = CloudEnvironmentDetector()
            detector.clear_cache()

            async def mock_fetch_metadata(session, endpoint):
                if endpoint == 'instance/attributes/goog-cloudrun-service-name':
                    return 'netra-backend'
                elif endpoint == 'project/project-id':
                    return 'netra-production'
                return None
            with patch.object(detector, '_fetch_metadata', side_effect=mock_fetch_metadata):
                env_service = EnvironmentContextService(detector=detector)
                await env_service.initialize()
                context = env_service.get_environment_context()
                assert context.environment_type == EnvironmentType.PRODUCTION
                config = env_service.get_service_configuration()
                auth_url = config.get_service_url('auth_service')
                backend_url = config.get_service_url('backend_service')
                assert auth_url == 'https://auth.netrasystems.ai'
                assert backend_url == 'https://api.netrasystems.ai'
                assert 'staging' not in auth_url
                assert 'staging' not in backend_url

    @pytest.mark.asyncio
    async def test_development_environment_localhost_acceptable(self, clear_environment_cache):
        """Test that localhost is acceptable in development environment."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}, clear=False):
            detector = CloudEnvironmentDetector()
            detector.clear_cache()
            with patch.object(detector, '_fetch_metadata', return_value=None):
                env_service = EnvironmentContextService(detector=detector)
                await env_service.initialize()
                context = env_service.get_environment_context()
                assert context.environment_type == EnvironmentType.DEVELOPMENT
                config = env_service.get_service_configuration()
                auth_url = config.get_service_url('auth_service')
                backend_url = config.get_service_url('backend_service')
                assert auth_url == 'http://localhost:8081'
                assert backend_url == 'http://localhost:8000'

    @pytest.mark.asyncio
    async def test_comprehensive_golden_path_end_to_end(self, clear_environment_cache):
        """
        Comprehensive end-to-end test of the Golden Path fix.
        
        Tests the complete flow from environment detection through
        Golden Path validation with correct service URLs.
        """
        staging_env = {'K_SERVICE': 'netra-backend-staging', 'GOOGLE_CLOUD_PROJECT': 'netra-staging', 'K_REVISION': 'netra-backend-staging-00001'}
        metadata_responses = {'instance/attributes/goog-cloudrun-service-name': 'netra-backend-staging', 'project/project-id': 'netra-staging', 'instance/region': 'projects/123/regions/us-central1'}
        with patch.dict(os.environ, staging_env, clear=False):
            detector = CloudEnvironmentDetector()
            detector.clear_cache()

            async def mock_fetch_metadata(session, endpoint):
                return metadata_responses.get(endpoint)
            with patch.object(detector, '_fetch_metadata', side_effect=mock_fetch_metadata):
                env_service = EnvironmentContextService(detector=detector)
                await env_service.initialize()
                context = env_service.get_environment_context()
                validator = GoldenPathValidator(environment_context_service=env_service)
                mock_app = Mock()
                with patch('netra_backend.app.core.service_dependencies.golden_path_validator.ServiceHealthClient') as mock_health_client:
                    mock_client_instance = Mock()
                    mock_health_client.return_value = mock_client_instance
                    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
                    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                    mock_client_instance.validate_auth_service_health = AsyncMock(return_value={'requirement': 'jwt_validation_ready', 'success': True, 'message': 'Auth service healthy via https://auth.staging.netrasystems.ai'})
                    mock_client_instance.validate_backend_service_health = AsyncMock(return_value={'requirement': 'agent_execution_ready', 'success': True, 'message': 'Backend service healthy via https://api.staging.netrasystems.ai'})
                    result = await validator.validate_golden_path_services(mock_app, [ServiceType.AUTH_SERVICE, ServiceType.BACKEND_SERVICE])
                    assert result.overall_success == True, 'Golden Path validation should succeed'
                    assert result.requirements_passed >= 2, 'Should pass auth and backend validation'
                    assert len(result.critical_failures) == 0, 'Should have no critical failures'
                    assert mock_health_client.call_count >= 2, 'Should create ServiceHealthClient instances'
                    first_call_env = mock_health_client.call_args_list[0][0][0]
                    from netra_backend.app.core.service_dependencies.models import EnvironmentType as ModelsEnvironmentType
                    assert first_call_env == ModelsEnvironmentType.STAGING
                    print(f' PASS:  COMPREHENSIVE GOLDEN PATH FIX VALIDATED:')
                    print(f'   Environment Detection: {context.environment_type.value}')
                    print(f'   Platform: {context.cloud_platform.value}')
                    print(f'   Confidence: {context.confidence_score}')
                    print(f'   Service: {context.service_name}')
                    print(f'   Validation Success: {result.overall_success}')
                    print(f'   Requirements Passed: {result.requirements_passed}')
                    print(f'    PASS:  GOLDEN PATH PROTECTED: 500K+ ARR SECURED!')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
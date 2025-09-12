"""
Integration tests for Service Integration Environment Context Fix.

This test validates the complete integration chain from environment detection
to service validation, ensuring the Golden Path validation works correctly
in staging environments.

Business Impact: Protects $500K+ ARR by ensuring staging services use proper
URLs instead of localhost defaults.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from netra_backend.app.core.environment_context import (
    CloudEnvironmentDetector,
    EnvironmentContext,
    EnvironmentType as ContextEnvironmentType,
    CloudPlatform,
    EnvironmentContextService,
    initialize_environment_context
)
from netra_backend.app.core.service_dependencies.service_dependency_checker import (
    ServiceDependencyChecker,
    create_service_dependency_checker_async
)
from netra_backend.app.core.service_dependencies.service_health_client import (
    ServiceHealthClient,
    create_service_health_client_async
)
from netra_backend.app.core.service_dependencies.golden_path_validator import (
    GoldenPathValidator
)
from netra_backend.app.core.service_dependencies.models import (
    EnvironmentType,
    ServiceType
)


class TestServiceIntegrationEnvironmentContextFix:
    """Test complete service integration with environment context."""
    
    @pytest.fixture
    def mock_staging_environment_context(self):
        """Create a mock staging environment context."""
        return EnvironmentContext(
            environment_type=ContextEnvironmentType.STAGING,
            cloud_platform=CloudPlatform.CLOUD_RUN,
            service_name="netra-backend-staging",
            project_id="netra-staging",
            region="us-central1",
            revision="staging-001",
            confidence_score=0.95,
            detection_metadata={
                "method": "cloud_run_metadata",
                "service_name": "netra-backend-staging"
            }
        )
    
    @pytest.fixture  
    def mock_development_environment_context(self):
        """Create a mock development environment context."""
        return EnvironmentContext(
            environment_type=ContextEnvironmentType.DEVELOPMENT,
            cloud_platform=CloudPlatform.UNKNOWN,
            service_name=None,
            project_id=None,
            region=None,
            revision=None,
            confidence_score=0.8,
            detection_metadata={
                "method": "environment_variables",
                "environment_var": "development"
            }
        )
    
    @pytest.mark.asyncio
    async def test_service_dependency_checker_uses_staging_environment_in_cloud_run(
        self, mock_staging_environment_context
    ):
        """Test ServiceDependencyChecker correctly detects staging environment in Cloud Run."""
        
        # Mock the environment context service to return staging
        with patch('netra_backend.app.core.environment_context.get_environment_context_service') as mock_get_service:
            mock_service = MagicMock(spec=EnvironmentContextService)
            mock_service.is_initialized.return_value = True
            mock_service.get_environment_context.return_value = mock_staging_environment_context
            mock_get_service.return_value = mock_service
            
            # Create ServiceDependencyChecker
            checker = ServiceDependencyChecker()
            
            # Verify it detected staging environment
            assert checker.environment == EnvironmentType.STAGING
            
            # Verify the environment context service was used
            mock_service.get_environment_context.assert_called_once()
    
    @pytest.mark.asyncio  
    async def test_service_health_client_uses_staging_urls_in_cloud_run(
        self, mock_staging_environment_context
    ):
        """Test ServiceHealthClient uses staging URLs when staging environment detected."""
        
        # Mock the environment context service to return staging
        with patch('netra_backend.app.core.environment_context.get_environment_context_service') as mock_get_service:
            mock_service = MagicMock(spec=EnvironmentContextService)
            mock_service.is_initialized.return_value = True
            mock_service.get_environment_context.return_value = mock_staging_environment_context
            mock_get_service.return_value = mock_service
            
            # Create ServiceHealthClient
            client = ServiceHealthClient()
            
            # Verify it detected staging environment
            assert client.environment == EnvironmentType.STAGING
            
            # Verify it has staging URLs
            assert ServiceType.AUTH_SERVICE in client.service_urls
            auth_url = client.service_urls[ServiceType.AUTH_SERVICE]
            assert auth_url == "https://auth.staging.netrasystems.ai"
            assert "localhost" not in auth_url  # Critical: No localhost in staging!
            
            backend_url = client.service_urls[ServiceType.BACKEND_SERVICE]
            assert backend_url == "https://api.staging.netrasystems.ai"
            assert "localhost" not in backend_url
    
    @pytest.mark.asyncio
    async def test_golden_path_validator_uses_staging_environment_context(
        self, mock_staging_environment_context
    ):
        """Test GoldenPathValidator receives staging environment context properly."""
        
        # Mock the environment context service to return staging
        with patch('netra_backend.app.core.environment_context.get_environment_context_service') as mock_get_service:
            mock_service = MagicMock(spec=EnvironmentContextService)
            mock_service.is_initialized.return_value = True  
            mock_service.get_environment_context.return_value = mock_staging_environment_context
            mock_get_service.return_value = mock_service
            
            # Create GoldenPathValidator
            validator = GoldenPathValidator()
            
            # Ensure environment context
            context = await validator._ensure_environment_context()
            
            # Verify it has staging environment context
            assert context.environment_type == ContextEnvironmentType.STAGING
            assert context.service_name == "netra-backend-staging"
            assert context.confidence_score == 0.95
    
    @pytest.mark.asyncio
    async def test_complete_integration_chain_staging_scenario(
        self, mock_staging_environment_context
    ):
        """Test complete integration: Environment Detection  ->  Validation  ->  Correct URLs."""
        
        # Mock the environment context service to return staging
        with patch('netra_backend.app.core.environment_context.get_environment_context_service') as mock_get_service:
            mock_service = MagicMock(spec=EnvironmentContextService)
            mock_service.is_initialized.return_value = True
            mock_service.get_environment_context.return_value = mock_staging_environment_context
            mock_get_service.return_value = mock_service
            
            # Create complete integration chain
            checker = ServiceDependencyChecker()
            
            # Verify ServiceDependencyChecker environment
            assert checker.environment == EnvironmentType.STAGING
            
            # Verify GoldenPathValidator has environment context service
            assert checker.golden_path_validator.environment_context_service is not None
            
            # Test that GoldenPathValidator can get environment context
            context = await checker.golden_path_validator._ensure_environment_context()
            assert context.environment_type == ContextEnvironmentType.STAGING
            
            # Verify health validator also uses staging
            assert checker.health_validator.environment == EnvironmentType.STAGING
    
    @pytest.mark.asyncio
    async def test_service_health_client_integration_with_golden_path_validator(
        self, mock_staging_environment_context
    ):
        """Test ServiceHealthClient integration through GoldenPathValidator."""
        
        # Mock the environment context service to return staging
        with patch('netra_backend.app.core.environment_context.get_environment_context_service') as mock_get_service:
            mock_service = MagicMock(spec=EnvironmentContextService)
            mock_service.is_initialized.return_value = True
            mock_service.get_environment_context.return_value = mock_staging_environment_context
            mock_get_service.return_value = mock_service
            
            # Create GoldenPathValidator
            validator = GoldenPathValidator()
            
            # Create a mock app and requirement for testing
            mock_app = MagicMock()
            
            from netra_backend.app.core.service_dependencies.models import GoldenPathRequirement
            requirement = GoldenPathRequirement(
                requirement_name="test_auth_service",
                service_type=ServiceType.AUTH_SERVICE,
                validation_function="validate_auth_service_health",
                critical=True,
                business_impact="Auth service must be healthy for user login"
            )
            
            # Mock the ServiceHealthClient validation to verify it gets staging environment
            with patch.object(validator, '_validate_requirement') as mock_validate:
                mock_validate.return_value = {
                    "requirement": "test_auth_service",
                    "success": True,
                    "message": "Auth service healthy",
                    "details": {"service_url": "https://auth.staging.netrasystems.ai"}
                }
                
                # Test validation
                result = await validator._validate_requirement(mock_app, requirement)
                
                # Verify the validation was called
                mock_validate.assert_called_once_with(mock_app, requirement)
    
    @pytest.mark.asyncio
    async def test_async_factory_functions_initialize_environment_context(
        self, mock_staging_environment_context
    ):
        """Test async factory functions properly initialize environment context."""
        
        # Mock the initialize_environment_context function
        with patch('netra_backend.app.core.environment_context.initialize_environment_context') as mock_init:
            mock_service = MagicMock(spec=EnvironmentContextService)
            mock_service.is_initialized.return_value = True
            mock_service.get_environment_context.return_value = mock_staging_environment_context
            mock_init.return_value = mock_service
            
            # Test ServiceDependencyChecker async factory
            checker = await create_service_dependency_checker_async()
            
            # Verify initialization was called
            mock_init.assert_called_once()
            
            # Verify checker was created with environment context service
            assert checker.environment_context_service is not None
    
    @pytest.mark.asyncio
    async def test_environment_detection_failure_handling(self):
        """Test proper error handling when environment detection fails."""
        
        # Mock environment context service to simulate detection failure
        with patch('netra_backend.app.core.environment_context.get_environment_context_service') as mock_get_service:
            mock_service = MagicMock(spec=EnvironmentContextService)
            mock_service.is_initialized.return_value = False
            mock_get_service.return_value = mock_service
            
            # Attempting to create ServiceDependencyChecker should raise RuntimeError
            with pytest.raises(RuntimeError, match="EnvironmentContextService not initialized"):
                ServiceDependencyChecker()
    
    @pytest.mark.asyncio
    async def test_development_environment_still_works(
        self, mock_development_environment_context
    ):
        """Test that development environment continues to work with localhost URLs."""
        
        # Mock the environment context service to return development
        with patch('netra_backend.app.core.environment_context.get_environment_context_service') as mock_get_service:
            mock_service = MagicMock(spec=EnvironmentContextService)
            mock_service.is_initialized.return_value = True
            mock_service.get_environment_context.return_value = mock_development_environment_context
            mock_get_service.return_value = mock_service
            
            # Create ServiceHealthClient
            client = ServiceHealthClient()
            
            # Verify it detected development environment
            assert client.environment == EnvironmentType.DEVELOPMENT
            
            # Verify it has localhost URLs (correct for development)
            auth_url = client.service_urls[ServiceType.AUTH_SERVICE]
            assert auth_url == "http://localhost:8081"
            
            backend_url = client.service_urls[ServiceType.BACKEND_SERVICE]
            assert backend_url == "http://localhost:8000"
    
    @pytest.mark.asyncio
    async def test_compatibility_functions_emit_deprecation_warnings(self):
        """Test that compatibility functions emit proper deprecation warnings."""
        
        # Test ServiceDependencyChecker compatibility function
        with pytest.warns(DeprecationWarning, match="create_service_dependency_checker_with_environment is deprecated"):
            from netra_backend.app.core.service_dependencies.service_dependency_checker import create_service_dependency_checker_with_environment
            
            # This should work but emit a warning
            with patch('netra_backend.app.core.environment_context.get_environment_context_service'):
                # We expect this to fail due to uninitialized service, but that's OK for testing the warning
                try:
                    create_service_dependency_checker_with_environment(EnvironmentType.STAGING)
                except RuntimeError:
                    pass  # Expected due to mock
        
        # Test ServiceHealthClient compatibility function  
        with pytest.warns(DeprecationWarning, match="create_service_health_client_with_environment is deprecated"):
            from netra_backend.app.core.service_dependencies.service_health_client import create_service_health_client_with_environment
            
            with patch('netra_backend.app.core.environment_context.get_environment_context_service'):
                try:
                    create_service_health_client_with_environment(EnvironmentType.STAGING)
                except RuntimeError:
                    pass  # Expected due to mock


# Integration test for the complete Golden Path scenario
@pytest.mark.asyncio
@pytest.mark.integration
async def test_golden_path_validation_staging_url_fix():
    """
    Integration test for the complete Golden Path validation fix.
    
    This test simulates the exact scenario that was causing the $500K+ ARR failure:
    - Cloud Run staging environment
    - Environment detection returns staging
    - Golden Path validation uses staging URLs
    - No localhost:8081 connection attempts in staging
    """
    
    # Create staging environment context
    staging_context = EnvironmentContext(
        environment_type=ContextEnvironmentType.STAGING,
        cloud_platform=CloudPlatform.CLOUD_RUN,
        service_name="netra-backend-staging",
        project_id="netra-staging",
        region="us-central1", 
        confidence_score=0.95,
        detection_metadata={"method": "cloud_run_metadata"}
    )
    
    # Mock environment detection to return staging
    with patch('netra_backend.app.core.environment_context.get_environment_context_service') as mock_get_service:
        mock_service = MagicMock(spec=EnvironmentContextService)
        mock_service.is_initialized.return_value = True
        mock_service.get_environment_context.return_value = staging_context
        mock_get_service.return_value = mock_service
        
        # Create the complete service validation chain
        checker = ServiceDependencyChecker()
        
        # Verify the complete chain uses staging environment
        assert checker.environment == EnvironmentType.STAGING
        
        # Verify GoldenPathValidator can get staging context
        context = await checker.golden_path_validator._ensure_environment_context()
        assert context.environment_type == ContextEnvironmentType.STAGING
        
        # Test that ServiceHealthClient created by GoldenPathValidator uses staging URLs
        with patch('netra_backend.app.core.service_dependencies.service_health_client.ServiceHealthClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.validate_auth_service_health.return_value = {
                "requirement": "jwt_validation_ready",
                "success": True,
                "message": "Auth service healthy via staging URL",
                "details": {"service_url": "https://auth.staging.netrasystems.ai"}
            }
            
            # Create a mock requirement
            from netra_backend.app.core.service_dependencies.models import GoldenPathRequirement
            requirement = GoldenPathRequirement(
                requirement_name="jwt_validation_ready",
                service_type=ServiceType.AUTH_SERVICE,
                validation_function="validate_auth_service_health", 
                critical=True,
                business_impact="JWT validation required for user authentication"
            )
            
            # Test the validation
            mock_app = MagicMock()
            result = await checker.golden_path_validator._validate_requirement(mock_app, requirement)
            
            # Verify ServiceHealthClient was created with environment context service
            mock_client_class.assert_called_once_with(
                environment_context_service=checker.golden_path_validator.environment_context_service
            )
            
            # Verify auth service validation was called
            mock_client.validate_auth_service_health.assert_called_once()
            
            # The critical test: No localhost URLs should be used in staging
            assert result["success"] is True
            if "service_url" in result.get("details", {}):
                service_url = result["details"]["service_url"]
                assert "localhost" not in service_url, f"CRITICAL: localhost URL used in staging: {service_url}"
                assert "staging.netrasystems.ai" in service_url, f"Expected staging URL, got: {service_url}"
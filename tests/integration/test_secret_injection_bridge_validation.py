"""
Integration Test for Secret Injection Bridge Implementation (Issue #683)

This test validates that the automated secret injection bridge correctly:
1. Validates secrets via SecretConfig SSOT
2. Provides meaningful error messages when secrets are unavailable
3. Prevents deployment when critical secrets are missing
4. Integrates properly with the deployment pipeline

Business Impact: Prevents deployment failures that affect $500K+ ARR staging functionality
"""

import pytest
from unittest.mock import patch, MagicMock
import subprocess
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.deploy_to_gcp_actual import GCPDeployer


class TestSecretInjectionBridge:
    """Integration tests for the automated secret injection bridge."""
    
    def test_secret_bridge_validation_with_missing_credentials(self):
        """Test that bridge correctly identifies missing GCP credentials."""
        deployer = GCPDeployer("test-project", use_alpine=True)
        
        # Test the bridge validation without actual GCP credentials
        # This should fail gracefully with meaningful error messages
        result = deployer._validate_secrets_via_bridge()
        
        # Validate the bridge provides comprehensive feedback
        assert isinstance(result, dict)
        assert 'success' in result
        assert 'errors' in result
        assert 'services' in result
        assert 'total_secrets' in result
        assert 'critical_secrets' in result
        
        # Should validate for backend and auth services
        assert 'backend' in result['services']
        
    def test_secret_bridge_gsm_availability_check(self):
        """Test that bridge correctly checks GSM availability."""
        deployer = GCPDeployer("test-project", use_alpine=True)
        
        # Mock subprocess to simulate GSM access failure
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "Authentication failed"
            mock_run.return_value = mock_result
            
            # Test GSM availability validation
            is_available = deployer._validate_gsm_availability()
            
            # Should correctly identify GSM as unavailable
            assert is_available is False
            
            # Verify the correct gcloud command was called
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert "secrets" in call_args
            assert "list" in call_args
    
    def test_secret_quality_validation_bridge(self):
        """Test that bridge correctly validates secret quality."""
        deployer = GCPDeployer("test-project", use_alpine=True)
        
        # Test JWT secret quality validation
        jwt_result = deployer._validate_secret_quality("JWT_SECRET_KEY", "short")
        assert jwt_result is not None  # Should fail - too short
        assert "32 characters" in jwt_result
        
        # Test valid JWT secret
        valid_jwt = "a" * 32
        jwt_result = deployer._validate_secret_quality("JWT_SECRET_KEY", valid_jwt)
        assert jwt_result is None  # Should pass
        
        # Test placeholder detection
        placeholder_result = deployer._validate_secret_quality("TEST_SECRET", "PLACEHOLDER_VALUE")
        assert placeholder_result is not None  # Should fail - placeholder
        assert "placeholder" in placeholder_result.lower()
        
    def test_deployment_bridge_readiness_validation(self):
        """Test that bridge correctly validates deployment readiness."""
        deployer = GCPDeployer("test-project", use_alpine=True)
        
        # Test deployment readiness validation
        with patch('deployment.secrets_config.SecretConfig.validate_deployment_readiness') as mock_validate:
            # Mock a successful readiness validation
            mock_validate.return_value = {
                'deployment_ready': True,
                'secrets_validated': 15,
                'critical_secrets_found': 5,
                'issues': [],
                'deployment_fragment': '--set-secrets JWT_SECRET_KEY=jwt-secret-staging:latest'
            }
            
            result = deployer.validate_deployment_bridge_readiness('backend')
            
            assert result['deployment_ready'] is True
            assert result['secrets_validated'] == 15
            assert result['critical_secrets_found'] == 5
            
            # Verify SecretConfig integration was called correctly
            mock_validate.assert_called_once_with('backend', 'test-project')
    
    def test_cross_service_consistency_validation(self):
        """Test that bridge validates cross-service secret consistency."""
        deployer = GCPDeployer("test-project", use_alpine=True)
        
        # Mock JWT consistency validation
        with patch.object(deployer, '_validate_jwt_secret_consistency') as mock_jwt:
            with patch.object(deployer, '_validate_oauth_configuration_consistency') as mock_oauth:
                mock_jwt.return_value = {'success': True, 'errors': []}
                mock_oauth.return_value = {'success': True, 'errors': []}
                
                result = deployer._validate_cross_service_consistency()
                
                assert result['success'] is True
                assert len(result['errors']) == 0
                
                # Verify both validations were called
                mock_jwt.assert_called_once()
                mock_oauth.assert_called_once()
    
    def test_bridge_integration_with_deployment_pipeline(self):
        """Test that bridge properly integrates with the deployment pipeline."""
        deployer = GCPDeployer("test-project", use_alpine=True)
        
        # Mock all the bridge validation methods
        with patch.object(deployer, 'check_gcloud') as mock_gcloud:
            with patch.object(deployer, 'enable_apis') as mock_apis:
                with patch.object(deployer, 'validate_all_secrets_exist') as mock_secrets:
                    with patch.object(deployer, 'validate_deployment_config') as mock_config:
                        
                        # Set up successful validations
                        mock_gcloud.return_value = True
                        mock_apis.return_value = True
                        mock_config.return_value = True
                        mock_secrets.return_value = False  # Fail secrets validation
                        
                        # Test that deployment fails when secret bridge validation fails
                        result = deployer.deploy_all(
                            skip_build=True,
                            check_secrets=True,
                            service_filter='backend'
                        )
                        
                        assert result is False  # Deployment should fail
                        
                        # Verify secret validation was called
                        mock_secrets.assert_called_once_with(check_secrets=True)
    
    def test_secret_config_integration(self):
        """Test integration with SecretConfig SSOT."""
        from deployment.secrets_config import SecretConfig
        
        # Test that SecretConfig provides the expected interface
        backend_secrets = SecretConfig.get_all_service_secrets('backend')
        assert isinstance(backend_secrets, list)
        assert len(backend_secrets) > 0
        
        # Test critical secrets identification
        critical_secrets = SecretConfig.CRITICAL_SECRETS.get('backend', [])
        assert 'JWT_SECRET_KEY' in critical_secrets
        assert 'SECRET_KEY' in critical_secrets
        
        # Test secrets string generation for deployment
        secrets_string = SecretConfig.generate_secrets_string('backend', 'staging')
        assert isinstance(secrets_string, str)
        assert 'JWT_SECRET_KEY=' in secrets_string
        assert ':latest' in secrets_string
    
    def test_bridge_error_messaging(self):
        """Test that bridge provides helpful structure and error handling."""
        deployer = GCPDeployer("test-project", use_alpine=True)
        
        # Test that validation returns proper structure
        result = deployer._validate_secrets_via_bridge()
        
        # Should have all required fields in the result structure
        assert isinstance(result, dict)
        assert 'success' in result
        assert 'errors' in result
        assert 'services' in result
        assert 'total_secrets' in result
        assert 'critical_secrets' in result
        
        # Should identify services to validate
        assert len(result['services']) > 0
        assert 'backend' in result['services']
        
        # Should count secrets properly
        assert result['total_secrets'] > 0
        assert result['critical_secrets'] > 0
        
        # Without real GCP access, should fail as expected
        assert result['success'] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
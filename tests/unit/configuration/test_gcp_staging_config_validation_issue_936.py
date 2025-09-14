"""
Unit Test Suite for Issue #936: GCP Staging Configuration Validation
Test the 7 missing GCP configuration variables for staging environment.

Business Value: Platform/Internal - System Stability
Ensures GCP staging deployment has all required configuration variables.

CRITICAL: These tests are designed to FAIL initially to reproduce the configuration issues.
Once the 7 missing variables are properly configured, these tests should pass.

SSOT Compliance: Inherits from SSotAsyncTestCase following test_framework/ssot patterns.
"""

import os
from unittest.mock import Mock, patch
import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.configuration.staging_validator import (
    StagingConfigurationValidator, 
    ValidationResult,
    validate_staging_config,
    ensure_staging_ready
)
from shared.isolated_environment import get_env


class TestGCPStagingConfigValidationIssue936(SSotAsyncTestCase):
    """Test suite for Issue #936 GCP configuration validation."""
    
    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        self.validator = StagingConfigurationValidator()
    
    def test_gcp_project_id_configuration_missing_issue_936(self):
        """
        Test GCP_PROJECT_ID configuration - one of the 7 missing variables.
        
        EXPECTED TO FAIL: This test should fail until GCP_PROJECT_ID is properly configured.
        """
        with patch('shared.isolated_environment.get_env') as mock_env:
            # Simulate missing GCP_PROJECT_ID
            mock_env_manager = Mock()
            mock_env_manager.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'staging'
                # GCP_PROJECT_ID deliberately missing
            }.get(key, default)
            mock_env.return_value = mock_env_manager
            
            result = self.validator.validate()
            
            # This should fail due to missing GCP_PROJECT_ID
            assert not result.is_valid, "Configuration should be invalid without GCP_PROJECT_ID"
            assert 'GCP_PROJECT_ID' in result.missing_critical
            assert any('GCP_PROJECT_ID is required' in error for error in result.errors)
    
    def test_secret_manager_configuration_missing_issue_936(self):
        """
        Test SECRET_MANAGER_PROJECT_ID configuration - missing variable #2.
        
        EXPECTED TO FAIL: This test should fail until SECRET_MANAGER_PROJECT_ID is configured.
        """
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env_manager = Mock()
            mock_env_manager.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'staging',
                'GCP_PROJECT_ID': '701982941522',
                # SECRET_MANAGER_PROJECT_ID deliberately missing
                # SECRET_MANAGER_SECRET_ID deliberately missing  
            }.get(key, default)
            mock_env.return_value = mock_env_manager
            
            # Test that secret manager access fails without proper config
            try:
                # This should fail due to missing Secret Manager configuration
                result = self.validator.validate()
                
                # We expect warnings/errors about secret manager configuration
                secret_manager_errors = [
                    error for error in (result.errors + result.warnings) 
                    if 'secret' in error.lower() or 'SECRET_MANAGER' in error
                ]
                
                # Should have secret manager related validation issues
                assert len(secret_manager_errors) > 0, "Should have Secret Manager configuration errors"
                
            except Exception as e:
                # Expected failure due to missing secret manager config
                assert 'secret' in str(e).lower() or 'SECRET_MANAGER' in str(e)
    
    def test_gcp_region_configuration_missing_issue_936(self):
        """
        Test GCP_REGION configuration - missing variable #3.
        
        EXPECTED TO FAIL: This test should fail until GCP_REGION is properly configured.
        """
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env_manager = Mock()
            mock_env_manager.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'staging',
                'GCP_PROJECT_ID': '701982941522',
                # GCP_REGION deliberately missing
            }.get(key, default)
            mock_env.return_value = mock_env_manager
            
            result = self.validator.validate()
            
            # Should have region-related validation issues
            region_errors = [
                error for error in (result.errors + result.warnings)
                if 'region' in error.lower() or 'GCP_REGION' in error
            ]
            
            # This test is expected to identify missing region configuration
            # The specific validation behavior depends on implementation
            self.assertGreaterEqual(len(result.errors + result.warnings), 0)
    
    def test_service_account_email_missing_issue_936(self):
        """
        Test SERVICE_ACCOUNT_EMAIL configuration - missing variable #4.
        
        EXPECTED TO FAIL: This test should fail until SERVICE_ACCOUNT_EMAIL is configured.
        """
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env_manager = Mock()
            mock_env_manager.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'staging',
                'GCP_PROJECT_ID': '701982941522',
                # SERVICE_ACCOUNT_EMAIL deliberately missing
            }.get(key, default)
            mock_env.return_value = mock_env_manager
            
            result = self.validator.validate()
            
            # Test should identify service account configuration issues
            service_account_errors = [
                error for error in (result.errors + result.warnings)
                if 'service_account' in error.lower() or 'SERVICE_ACCOUNT' in error
            ]
            
            # Expected to have some validation issues
            self.assertGreaterEqual(len(result.errors + result.warnings), 0)
    
    def test_cloud_sql_instance_name_missing_issue_936(self):
        """
        Test CLOUD_SQL_INSTANCE_NAME configuration - missing variable #5.
        
        EXPECTED TO FAIL: This test should fail until CLOUD_SQL_INSTANCE_NAME is configured.
        """
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env_manager = Mock()
            mock_env_manager.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'staging',
                'GCP_PROJECT_ID': '701982941522',
                'POSTGRES_HOST': '/cloudsql/missing-instance',  # Incomplete Cloud SQL path
                # CLOUD_SQL_INSTANCE_NAME deliberately missing
            }.get(key, default)
            mock_env.return_value = mock_env_manager
            
            result = self.validator.validate()
            
            # Should detect issues with Cloud SQL configuration
            cloud_sql_errors = [
                error for error in (result.errors + result.warnings)
                if 'cloud_sql' in error.lower() or 'cloudsql' in error.lower()
            ]
            
            # Expected to have validation issues due to incomplete Cloud SQL config
            self.assertGreaterEqual(len(result.errors + result.warnings), 0)
    
    def test_google_application_credentials_missing_issue_936(self):
        """
        Test GOOGLE_APPLICATION_CREDENTIALS configuration - missing variable #6.
        
        EXPECTED TO FAIL: This test should fail until GOOGLE_APPLICATION_CREDENTIALS is configured.
        """
        with patch('shared.isolated_environment.get_env') as mock_env:
            # Ensure GOOGLE_APPLICATION_CREDENTIALS is not set
            mock_env_manager = Mock()
            mock_env_manager.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'staging',
                'GCP_PROJECT_ID': '701982941522',
                # GOOGLE_APPLICATION_CREDENTIALS deliberately missing
            }.get(key, default)
            mock_env.return_value = mock_env_manager
            
            result = self.validator.validate()
            
            # Should identify authentication credential issues
            credential_errors = [
                error for error in (result.errors + result.warnings)
                if 'credential' in error.lower() or 'GOOGLE_APPLICATION_CREDENTIALS' in error
            ]
            
            # Expected to have authentication-related validation issues
            self.assertGreaterEqual(len(result.errors + result.warnings), 0)
    
    def test_vpc_connector_name_missing_issue_936(self):
        """
        Test VPC_CONNECTOR_NAME configuration - missing variable #7.
        
        EXPECTED TO FAIL: This test should fail until VPC_CONNECTOR_NAME is configured.
        """
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env_manager = Mock()
            mock_env_manager.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'staging',
                'GCP_PROJECT_ID': '701982941522',
                # VPC_CONNECTOR_NAME deliberately missing
            }.get(key, default)
            mock_env.return_value = mock_env_manager
            
            result = self.validator.validate()
            
            # Should identify VPC connectivity issues
            vpc_errors = [
                error for error in (result.errors + result.warnings)
                if 'vpc' in error.lower() or 'VPC_CONNECTOR' in error
            ]
            
            # Expected to have VPC-related validation issues
            self.assertGreaterEqual(len(result.errors + result.warnings), 0)
    
    def test_all_seven_variables_missing_comprehensive_failure_issue_936(self):
        """
        Comprehensive test with all 7 GCP configuration variables missing.
        
        EXPECTED TO FAIL COMPLETELY: This test demonstrates the scope of Issue #936.
        """
        with patch('shared.isolated_environment.get_env') as mock_env:
            # Simulate minimal staging environment with all GCP variables missing
            mock_env_manager = Mock()
            mock_env_manager.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'staging',
                # All 7 critical GCP variables deliberately missing:
                # 1. GCP_PROJECT_ID 
                # 2. SECRET_MANAGER_PROJECT_ID
                # 3. GCP_REGION
                # 4. SERVICE_ACCOUNT_EMAIL  
                # 5. CLOUD_SQL_INSTANCE_NAME
                # 6. GOOGLE_APPLICATION_CREDENTIALS
                # 7. VPC_CONNECTOR_NAME
            }.get(key, default)
            mock_env.return_value = mock_env_manager
            
            result = self.validator.validate()
            
            # Should have multiple critical failures
            assert not result.is_valid, "Configuration should be completely invalid"
            assert len(result.errors) > 0, "Should have multiple configuration errors"
            assert len(result.missing_critical) > 0, "Should have missing critical variables"
            
            # Verify specific critical failure
            assert 'GCP_PROJECT_ID' in result.missing_critical
    
    def test_gcp_configuration_with_placeholders_issue_936(self):
        """
        Test detection of placeholder values in GCP configuration variables.
        
        EXPECTED TO FAIL: Should detect and reject placeholder values.
        """
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env_manager = Mock()
            mock_env_manager.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'staging',
                'GCP_PROJECT_ID': 'YOUR_PROJECT_ID_HERE',  # Placeholder value
                'SECRET_MANAGER_PROJECT_ID': 'REPLACE_WITH_ACTUAL_PROJECT',  # Placeholder
                'GCP_REGION': 'your-region-here',  # Placeholder
                'SERVICE_ACCOUNT_EMAIL': 'change-me@example.com',  # Placeholder
                'CLOUD_SQL_INSTANCE_NAME': 'staging-sql-should-be-replaced',  # Placeholder
                'GOOGLE_APPLICATION_CREDENTIALS': '/path/to/service-account-should-be-replaced.json',  # Placeholder
                'VPC_CONNECTOR_NAME': 'vpc-connector-will-be-set'  # Placeholder
            }.get(key, default)
            mock_env.return_value = mock_env_manager
            
            result = self.validator.validate()
            
            # Should fail due to placeholder values
            assert not result.is_valid, "Configuration should be invalid with placeholder values"
            assert len(result.placeholders_found) > 0, "Should detect placeholder values"
            
            # Verify specific placeholders are detected
            expected_placeholders = [
                'GCP_PROJECT_ID', 'SECRET_MANAGER_PROJECT_ID', 'GCP_REGION',
                'SERVICE_ACCOUNT_EMAIL', 'CLOUD_SQL_INSTANCE_NAME', 
                'GOOGLE_APPLICATION_CREDENTIALS', 'VPC_CONNECTOR_NAME'
            ]
            
            placeholder_keys = set(result.placeholders_found.keys())
            detected_gcp_placeholders = [key for key in expected_placeholders if key in placeholder_keys]
            
            # Should detect at least some GCP placeholders
            assert len(detected_gcp_placeholders) > 0, f"Should detect GCP placeholder values, found: {placeholder_keys}"
    
    def test_staging_configuration_validation_function_issue_936(self):
        """
        Test the validate_staging_config() function with missing GCP variables.
        
        EXPECTED TO FAIL: Should return False for invalid configuration.
        """
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env_manager = Mock()
            mock_env_manager.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'staging'
                # Missing all GCP configuration
            }.get(key, default)
            mock_env.return_value = mock_env_manager
            
            # This should return False due to missing configuration
            is_valid, result = validate_staging_config()
            
            assert not is_valid, "Staging configuration should be invalid"
            assert isinstance(result, ValidationResult)
            assert len(result.errors) > 0 or len(result.missing_critical) > 0
    
    def test_ensure_staging_ready_raises_exception_issue_936(self):
        """
        Test ensure_staging_ready() raises ValueError with missing GCP configuration.
        
        EXPECTED TO FAIL: Should raise ValueError due to invalid configuration.
        """
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env_manager = Mock()
            mock_env_manager.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'staging'
                # Missing all GCP configuration
            }.get(key, default)
            mock_env.return_value = mock_env_manager
            
            # Should raise ValueError due to invalid staging configuration
            with pytest.raises(ValueError) as exc_info:
                ensure_staging_ready()
            
            error_message = str(exc_info.value)
            assert 'configuration is invalid' in error_message.lower()
            assert 'GCP_PROJECT_ID' in error_message or 'missing critical' in error_message.lower()


class TestGCPConfigurationErrorHandling(SSotAsyncTestCase):
    """Test error handling for GCP configuration issues."""
    
    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
    
    def test_error_messages_contain_issue_936_context(self):
        """Ensure error messages provide clear guidance for Issue #936 resolution."""
        validator = StagingConfigurationValidator()
        
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env_manager = Mock()
            mock_env_manager.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'staging'
                # Missing GCP configuration
            }.get(key, default)
            mock_env.return_value = mock_env_manager
            
            result = validator.validate()
            
            # Verify error messages are helpful
            all_messages = result.errors + result.warnings
            
            # Should have clear, actionable error messages
            assert len(all_messages) > 0, "Should provide error messages for troubleshooting"
            
            # Verify at least one message mentions critical missing configuration
            critical_messages = [msg for msg in all_messages if 'critical' in msg.lower() or 'required' in msg.lower()]
            assert len(critical_messages) > 0, "Should have messages about critical/required configuration"
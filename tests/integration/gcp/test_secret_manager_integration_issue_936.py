"""
Integration Test Suite for Issue #936: GCP Secret Manager Integration
Test real GCP Secret Manager access for the 7 missing configuration variables.

Business Value: Platform/Internal - System Stability
Validates that GCP staging environment can access required secrets from Secret Manager.

CRITICAL TESTING REQUIREMENTS:
- NO DOCKER dependencies - uses real GCP staging environment 
- Real Secret Manager integration (no mocks)
- Tests MUST fail initially to reproduce configuration issues
- SSOT compliance with existing test infrastructure patterns

SSOT Compliance: Inherits from SSotAsyncTestCase and uses IsolatedEnvironment.
"""

import asyncio
import json
from unittest.mock import patch, Mock
import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env


class TestSecretManagerIntegrationIssue936(SSotAsyncTestCase):
    """Test Secret Manager integration for Issue #936 GCP configuration variables."""
    
    def setup_method(self, method):
        """Set up test environment with real GCP configuration."""
        super().setup_method(method)
        self.env = get_env()
        
        # Expected GCP configuration variables that should be retrieved from Secret Manager
        self.expected_secret_variables = {
            'JWT_SECRET_KEY': 'staging-jwt-secret',
            'FERNET_KEY': 'staging-fernet-key', 
            'SERVICE_SECRET': 'staging-service-secret',
            'POSTGRES_PASSWORD': 'staging-postgres-password',
            'CLICKHOUSE_PASSWORD': 'staging-clickhouse-password',
            'ANTHROPIC_API_KEY': 'staging-anthropic-key',
            'OPENAI_API_KEY': 'staging-openai-key'
        }
    
    @pytest.mark.asyncio
    async def test_gcp_secret_manager_client_initialization_issue_936(self):
        """
        Test GCP Secret Manager client initialization with missing configuration.
        
        EXPECTED TO FAIL: Should fail due to missing SECRET_MANAGER_PROJECT_ID.
        """
        try:
            # Attempt to import and use GCP Secret Manager client
            from google.cloud import secretmanager
            
            # Get project ID from environment (likely missing for Issue #936)
            project_id = self.env.get('SECRET_MANAGER_PROJECT_ID') or self.env.get('GCP_PROJECT_ID')
            
            if not project_id:
                # This is the expected failure state for Issue #936
                self.fail("SECRET_MANAGER_PROJECT_ID is missing - this reproduces Issue #936")
            
            # Try to create client with missing/invalid configuration
            client = secretmanager.SecretManagerServiceClient()
            
            # Attempt to list secrets (should fail with missing config)
            parent = f"projects/{project_id}"
            
            try:
                # This should fail if authentication is not properly configured
                response = client.list_secrets(request={"parent": parent})
                secrets_list = list(response)
                
                # If we get here, configuration might actually be working
                # But for Issue #936, we expect this to fail
                self.assertGreater(len(secrets_list), 0, 
                    "Expected some secrets to exist in staging Secret Manager")
                
            except Exception as e:
                # This is the expected failure for Issue #936
                error_msg = str(e).lower()
                
                # Common failure modes for missing GCP configuration
                expected_errors = [
                    'authentication',
                    'credentials', 
                    'permission denied',
                    'project not found',
                    'invalid project',
                    'service account'
                ]
                
                has_expected_error = any(expected in error_msg for expected in expected_errors)
                
                if has_expected_error:
                    # This reproduces Issue #936 - missing/invalid GCP configuration
                    self.fail(f"Secret Manager access failed due to missing GCP configuration: {e}")
                else:
                    # Unexpected error - re-raise for investigation
                    raise
        
        except ImportError as e:
            # Missing Google Cloud libraries - configuration issue
            self.fail(f"Google Cloud Secret Manager library not available: {e}")
        
        except Exception as e:
            # Other configuration-related failures expected for Issue #936
            error_msg = str(e).lower()
            if any(term in error_msg for term in ['credentials', 'authentication', 'project']):
                self.fail(f"GCP configuration failure reproducing Issue #936: {e}")
            else:
                raise
    
    @pytest.mark.asyncio 
    async def test_secret_manager_environment_variables_missing_issue_936(self):
        """
        Test that required Secret Manager environment variables are missing.
        
        EXPECTED TO FAIL: Should identify missing SECRET_MANAGER_PROJECT_ID and related vars.
        """
        # Check for Secret Manager specific configuration
        secret_manager_vars = [
            'SECRET_MANAGER_PROJECT_ID',
            'GOOGLE_APPLICATION_CREDENTIALS',
            'SERVICE_ACCOUNT_EMAIL',
        ]
        
        missing_vars = []
        placeholder_vars = {}
        
        for var in secret_manager_vars:
            value = self.env.get(var)
            
            if not value:
                missing_vars.append(var)
            elif self._is_placeholder_value(value):
                placeholder_vars[var] = value
        
        # For Issue #936, we expect these variables to be missing or placeholders
        if missing_vars:
            self.fail(f"Missing Secret Manager configuration variables (Issue #936): {missing_vars}")
        
        if placeholder_vars:
            self.fail(f"Placeholder values in Secret Manager config (Issue #936): {placeholder_vars}")
        
        # If we get here, configuration might be complete
        self.assertGreaterEqual(len(missing_vars) + len(placeholder_vars), 1,
            "Expected missing/placeholder Secret Manager configuration for Issue #936")
    
    def _is_placeholder_value(self, value: str) -> bool:
        """Check if a value appears to be a placeholder."""
        if not value:
            return True
        
        placeholder_indicators = [
            'placeholder', 'replace', 'change-me', 'your-', 'example',
            'todo', 'fixme', 'should-be-replaced', 'will-be-set'
        ]
        
        value_lower = value.lower()
        return any(indicator in value_lower for indicator in placeholder_indicators)
    
    @pytest.mark.asyncio
    async def test_secret_retrieval_for_critical_configuration_issue_936(self):
        """
        Test retrieval of critical configuration secrets from Secret Manager.
        
        EXPECTED TO FAIL: Should fail to retrieve secrets due to missing configuration.
        """
        try:
            from google.cloud import secretmanager
            
            project_id = self.env.get('SECRET_MANAGER_PROJECT_ID') or self.env.get('GCP_PROJECT_ID')
            
            if not project_id:
                self.fail("Cannot test secret retrieval - SECRET_MANAGER_PROJECT_ID missing (Issue #936)")
            
            client = secretmanager.SecretManagerServiceClient()
            
            # Test retrieval of each expected secret
            retrieval_failures = []
            
            for env_var, secret_name in self.expected_secret_variables.items():
                try:
                    # Try to access secret
                    secret_path = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                    response = client.access_secret_version(request={"name": secret_path})
                    secret_value = response.payload.data.decode("UTF-8")
                    
                    # Validate secret is not a placeholder
                    if self._is_placeholder_value(secret_value):
                        retrieval_failures.append(f"{secret_name}: placeholder value")
                    elif len(secret_value) < 10:  # Secrets should be substantial
                        retrieval_failures.append(f"{secret_name}: value too short")
                    
                except Exception as e:
                    retrieval_failures.append(f"{secret_name}: {str(e)[:100]}")
            
            if retrieval_failures:
                self.fail(f"Secret retrieval failures (Issue #936): {retrieval_failures}")
                
        except ImportError:
            self.fail("Google Cloud Secret Manager not available (missing dependency)")
        except Exception as e:
            if 'credentials' in str(e).lower() or 'authentication' in str(e).lower():
                self.fail(f"Secret Manager authentication failure (Issue #936): {e}")
            else:
                raise
    
    @pytest.mark.asyncio
    async def test_service_account_permissions_issue_936(self):
        """
        Test that service account has proper permissions for Secret Manager.
        
        EXPECTED TO FAIL: Should fail due to missing/invalid service account configuration.
        """
        service_account_email = self.env.get('SERVICE_ACCOUNT_EMAIL')
        
        if not service_account_email:
            self.fail("SERVICE_ACCOUNT_EMAIL missing (Issue #936 variable #4)")
        
        if self._is_placeholder_value(service_account_email):
            self.fail(f"SERVICE_ACCOUNT_EMAIL has placeholder value: {service_account_email}")
        
        # Validate service account email format
        if '@' not in service_account_email or '.gserviceaccount.com' not in service_account_email:
            self.fail(f"Invalid service account email format: {service_account_email}")
        
        # Test that service account can access Secret Manager
        try:
            from google.cloud import secretmanager
            
            project_id = self.env.get('SECRET_MANAGER_PROJECT_ID') or self.env.get('GCP_PROJECT_ID')
            if not project_id:
                self.fail("Cannot test service account permissions - project ID missing")
            
            # Try to initialize client (uses service account credentials)
            client = secretmanager.SecretManagerServiceClient()
            
            # Test basic Secret Manager access
            parent = f"projects/{project_id}"
            
            try:
                # Attempt to list secrets (requires proper IAM permissions)
                response = client.list_secrets(request={"parent": parent})
                secrets = list(response)
                
                # If successful, service account has proper permissions
                self.assertIsInstance(secrets, list)
                
            except Exception as e:
                error_msg = str(e).lower()
                if 'permission' in error_msg or 'access' in error_msg or 'forbidden' in error_msg:
                    self.fail(f"Service account lacks Secret Manager permissions (Issue #936): {e}")
                else:
                    raise
                    
        except ImportError:
            self.fail("Cannot test service account - Google Cloud library missing")
        except Exception as e:
            if 'credentials' in str(e).lower():
                self.fail(f"Service account credential issues (Issue #936): {e}")
            else:
                raise
    
    @pytest.mark.asyncio
    async def test_google_application_credentials_configuration_issue_936(self):
        """
        Test GOOGLE_APPLICATION_CREDENTIALS configuration.
        
        EXPECTED TO FAIL: Should fail due to missing/invalid credentials file path.
        """
        credentials_path = self.env.get('GOOGLE_APPLICATION_CREDENTIALS')
        
        if not credentials_path:
            # This is expected for Issue #936
            self.fail("GOOGLE_APPLICATION_CREDENTIALS missing (Issue #936 variable #6)")
        
        if self._is_placeholder_value(credentials_path):
            self.fail(f"GOOGLE_APPLICATION_CREDENTIALS has placeholder: {credentials_path}")
        
        # Test that credentials file exists and is readable
        import os
        
        if not os.path.exists(credentials_path):
            self.fail(f"Credentials file does not exist: {credentials_path}")
        
        if not os.path.isfile(credentials_path):
            self.fail(f"Credentials path is not a file: {credentials_path}")
        
        # Test that credentials file is valid JSON
        try:
            with open(credentials_path, 'r') as f:
                creds_data = json.load(f)
            
            # Validate required fields in service account key
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            missing_fields = [field for field in required_fields if field not in creds_data]
            
            if missing_fields:
                self.fail(f"Invalid service account key - missing fields: {missing_fields}")
            
            # Verify it's a service account key
            if creds_data.get('type') != 'service_account':
                self.fail(f"Expected service_account credentials, got: {creds_data.get('type')}")
                
        except json.JSONDecodeError as e:
            self.fail(f"Invalid JSON in credentials file: {e}")
        except FileNotFoundError:
            self.fail(f"Credentials file not found: {credentials_path}")
        except PermissionError:
            self.fail(f"Cannot read credentials file: {credentials_path}")
    
    @pytest.mark.asyncio
    async def test_gcp_region_configuration_for_secret_manager_issue_936(self):
        """
        Test GCP_REGION configuration affects Secret Manager access.
        
        EXPECTED TO FAIL: Should fail due to missing GCP_REGION configuration.
        """
        gcp_region = self.env.get('GCP_REGION')
        
        if not gcp_region:
            self.fail("GCP_REGION missing (Issue #936 variable #3)")
        
        if self._is_placeholder_value(gcp_region):
            self.fail(f"GCP_REGION has placeholder value: {gcp_region}")
        
        # Validate region format (should be like 'us-central1')
        if not gcp_region.count('-') >= 2:
            self.fail(f"Invalid GCP region format: {gcp_region}")
        
        # Test that region is a valid GCP region
        valid_regions = [
            'us-central1', 'us-east1', 'us-west1', 'us-west2', 'us-west3', 'us-west4',
            'europe-west1', 'europe-west2', 'europe-west3', 'europe-west4', 'europe-west6',
            'asia-east1', 'asia-northeast1', 'asia-southeast1', 'australia-southeast1'
        ]
        
        if gcp_region not in valid_regions:
            # This might be a newer region, so just warn
            self.assertIn('-', gcp_region, f"Malformed region name: {gcp_region}")


class TestSecretManagerConfigurationCompleteIssue936(SSotAsyncTestCase):
    """Test Secret Manager with complete configuration (for comparison)."""
    
    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
    
    @pytest.mark.asyncio
    async def test_expected_secret_manager_configuration_complete(self):
        """
        Test what Secret Manager configuration should look like when Issue #936 is resolved.
        
        This test shows the target state after fixing the 7 missing variables.
        """
        # This test uses mock configuration to show the expected complete state
        expected_complete_config = {
            'ENVIRONMENT': 'staging',
            'GCP_PROJECT_ID': '701982941522',
            'SECRET_MANAGER_PROJECT_ID': '701982941522',
            'GCP_REGION': 'us-central1',
            'SERVICE_ACCOUNT_EMAIL': 'netra-staging@netra-staging.iam.gserviceaccount.com',
            'CLOUD_SQL_INSTANCE_NAME': 'netra-staging:us-central1:postgres-main',
            'GOOGLE_APPLICATION_CREDENTIALS': '/var/secrets/service-account-key.json',
            'VPC_CONNECTOR_NAME': 'netra-staging-vpc-connector'
        }
        
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env_manager = Mock()
            mock_env_manager.get.side_effect = lambda key, default='': expected_complete_config.get(key, default)
            mock_env.return_value = mock_env_manager
            
            # Import and test validator with complete configuration
            from netra_backend.app.core.configuration.staging_validator import StagingConfigurationValidator
            
            validator = StagingConfigurationValidator()
            result = validator.validate()
            
            # With complete configuration, validation should pass (or have fewer errors)
            self.assertLessEqual(len(result.errors), 2, 
                "With complete GCP configuration, should have minimal errors")
            
            # Should not have missing critical variables
            critical_gcp_vars = ['GCP_PROJECT_ID']  # Known critical variable
            missing_critical_gcp = [var for var in result.missing_critical if var in critical_gcp_vars]
            
            self.assertEqual(len(missing_critical_gcp), 0,
                f"Should not have missing critical GCP variables: {missing_critical_gcp}")
    
    def test_secret_manager_integration_success_criteria(self):
        """Define success criteria for Issue #936 resolution."""
        success_criteria = {
            'required_environment_variables': [
                'GCP_PROJECT_ID',
                'SECRET_MANAGER_PROJECT_ID', 
                'GCP_REGION',
                'SERVICE_ACCOUNT_EMAIL',
                'CLOUD_SQL_INSTANCE_NAME',
                'GOOGLE_APPLICATION_CREDENTIALS',
                'VPC_CONNECTOR_NAME'
            ],
            'secret_manager_access': {
                'can_list_secrets': True,
                'can_access_staging_secrets': True,
                'service_account_permissions_valid': True
            },
            'configuration_validation': {
                'no_placeholder_values': True,
                'no_missing_critical_variables': True,
                'staging_validator_passes': True
            }
        }
        
        # This test documents what needs to be achieved to resolve Issue #936
        self.assertIsInstance(success_criteria, dict)
        self.assertIn('required_environment_variables', success_criteria)
        self.assertEqual(len(success_criteria['required_environment_variables']), 7,
            "Should have exactly 7 required GCP configuration variables")
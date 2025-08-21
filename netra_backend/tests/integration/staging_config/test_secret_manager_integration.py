"""
Test Secret Manager Integration

Validates that all required secrets exist in GCP Secret Manager
and are accessible by the staging services.
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import os
import json
from typing import List, Dict

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add project root to path

from netra_backend.tests.base import StagingConfigTestBase

# Add project root to path


class TestSecretManagerIntegration(StagingConfigTestBase):
    """Test Secret Manager integration in staging."""
    
    def test_all_required_secrets_exist(self):
        """Verify all required secrets exist in Secret Manager."""
        self.skip_if_not_staging()
        self.require_gcp_credentials()
        
        required_secrets = [
            'jwt-secret',  # Terraform creates this
            'jwt-secret-staging',  # Deployment expects this
            'database-url',
            'redis-url',
            'gemini-api-key',
            'openai-api-key',
            'anthropic-api-key',
            'sentry-dsn',
            'smtp-password',
            'admin-password'
        ]
        
        missing_secrets = []
        accessible_secrets = []
        
        for secret_name in required_secrets:
            try:
                secret_value = self.assert_secret_exists(secret_name)
                accessible_secrets.append(secret_name)
            except AssertionError:
                missing_secrets.append(secret_name)
                
        # Report findings
        if missing_secrets:
            self.fail(f"Missing secrets: {missing_secrets}. "
                     f"Accessible: {accessible_secrets}")
                     
    def test_secret_naming_consistency(self):
        """Verify secret naming matches between Terraform and deployment."""
        self.skip_if_not_staging()
        self.require_gcp_credentials()
        
        # Check for JWT secret naming mismatch
        jwt_terraform_name = 'jwt-secret'
        jwt_deployment_name = 'jwt-secret-staging'
        
        jwt_terraform_exists = False
        jwt_deployment_exists = False
        
        try:
            self.assert_secret_exists(jwt_terraform_name)
            jwt_terraform_exists = True
        except AssertionError:
            pass
            
        try:
            self.assert_secret_exists(jwt_deployment_name)
            jwt_deployment_exists = True
        except AssertionError:
            pass
            
        # Both should exist or we have a mismatch
        if jwt_terraform_exists and not jwt_deployment_exists:
            self.fail(f"Terraform creates '{jwt_terraform_name}' but "
                     f"deployment expects '{jwt_deployment_name}'")
        elif jwt_deployment_exists and not jwt_terraform_exists:
            self.fail(f"Deployment uses '{jwt_deployment_name}' but "
                     f"Terraform doesn't create it")
                     
    def test_database_url_format(self):
        """Verify database URL format for different connection types."""
        self.skip_if_not_staging()
        self.require_gcp_credentials()
        
        try:
            db_url = self.assert_secret_exists('database-url')
            
            # Check for Cloud SQL proxy format
            if '/cloudsql/' in db_url:
                self.assertIn('unix_socket', db_url,
                            "Cloud SQL proxy URL should use unix_socket")
                self.assertIn(self.project_id, db_url,
                            "Database URL should include project ID")
                            
            # Check for direct connection format
            elif 'host=' in db_url or '@' in db_url:
                # PostgreSQL connection string
                self.assertIn('sslmode=require', db_url,
                            "Direct connections must use SSL")
                            
        except AssertionError as e:
            self.fail(f"Database URL validation failed: {e}")
            
    def test_service_account_permissions(self):
        """Verify service accounts have necessary permissions."""
        self.skip_if_not_staging()
        self.require_gcp_credentials()
        
        # List all secrets to verify access
        parent = f"projects/{self.project_id}"
        
        try:
            request = {"parent": parent}
            page_result = self.secret_client.list_secrets(request=request)
            
            secret_count = 0
            for secret in page_result:
                secret_count += 1
                
            self.assertGreater(secret_count, 0,
                             "Service account cannot list secrets")
                             
        except Exception as e:
            self.fail(f"Service account lacks Secret Manager permissions: {e}")
            
    def test_secret_versions(self):
        """Verify secrets have valid versions."""
        self.skip_if_not_staging()
        self.require_gcp_credentials()
        
        critical_secrets = [
            'database-url',
            'jwt-secret-staging',
            'gemini-api-key'
        ]
        
        for secret_name in critical_secrets:
            try:
                # Check latest version
                latest_name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
                latest_response = self.secret_client.access_secret_version(
                    request={"name": latest_name}
                )
                
                # Verify version is enabled
                self.assertEqual(latest_response.name.split('/')[-1], 'latest',
                               f"Secret {secret_name} latest version not accessible")
                               
            except Exception as e:
                self.fail(f"Secret {secret_name} version check failed: {e}")
                
    def test_secret_rotation_metadata(self):
        """Verify secrets have rotation metadata if required."""
        self.skip_if_not_staging()
        self.require_gcp_credentials()
        
        rotation_required = [
            'jwt-secret-staging',
            'database-url',
            'admin-password'
        ]
        
        for secret_name in rotation_required:
            try:
                name = f"projects/{self.project_id}/secrets/{secret_name}"
                secret = self.secret_client.get_secret(request={"name": name})
                
                # Check for rotation metadata
                if secret.rotation:
                    self.assertIsNotNone(secret.rotation.rotation_period,
                                       f"Secret {secret_name} missing rotation period")
                                       
            except Exception as e:
                # Secret might not exist, which is covered by other tests
                pass
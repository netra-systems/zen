from shared.isolated_environment import get_env
"""
Base class for staging configuration integration tests.

Provides common functionality for testing against real
GCP staging environment resources.
"""

import asyncio
import os
import unittest
from typing import Any, Dict, Optional

try:
    from google.cloud import secretmanager
except ImportError:
    secretmanager = None
try:
    from google.cloud import sql_v1
except ImportError:
    sql_v1 = None
import httpx
import pytest

class StagingConfigTestBase(unittest.TestCase):
    """Base class for staging configuration tests."""
    
    @classmethod
    def setUpClass(cls):
        """Set up class-level resources."""
        # Staging-specific configuration from environment
        cls.project_id = get_env().get('GCP_PROJECT_ID', 'netra-ai-staging')
        cls.region = get_env().get('GCP_REGION', 'us-central1')
        
        # Use actual staging URLs from environment
        cls.staging_url = get_env().get('STAGING_URL', 'https://app.staging.netrasystems.ai')
        cls.staging_api_url = get_env().get('STAGING_API_URL', 'https://api.staging.netrasystems.ai')
        cls.staging_auth_url = get_env().get('STAGING_AUTH_URL', 'https://auth.staging.netrasystems.ai')
        cls.staging_frontend_url = get_env().get('STAGING_FRONTEND_URL', 'https://app.staging.netrasystems.ai')
        
        # Initialize GCP clients if available
        try:
            cls.secret_client = secretmanager.SecretManagerServiceClient() if secretmanager else None
        except Exception:
            cls.secret_client = None
            
        try:
            cls.sql_client = sql_v1.SqlInstancesServiceClient() if sql_v1 else None
        except Exception:
            cls.sql_client = None
        
        # Mark as staging test
        cls.is_staging_test = True
        
    def setUp(self):
        """Set up test-specific resources."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
    def tearDown(self):
        """Clean up test-specific resources."""
        self.loop.close()
        
    def assert_secret_exists(self, secret_name: str) -> str:
        """
        Assert that a secret exists in Secret Manager.
        
        Args:
            secret_name: Name of the secret to check
            
        Returns:
            The secret value
            
        Raises:
            AssertionError: If secret doesn't exist or isn't accessible
        """
        if not self.secret_client:
            self.skipTest("Google Cloud Secret Manager client not available")
        try:
            name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
            response = self.secret_client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode('UTF-8')
            self.assertIsNotNone(secret_value, f"Secret {secret_name} exists but is empty")
            return secret_value
        except Exception as e:
            self.fail(f"Secret {secret_name} not accessible: {e}")
            
    def assert_cloud_sql_instance_exists(self, instance_name: str) -> Dict[str, Any]:
        """
        Assert that a Cloud SQL instance exists and is running.
        
        Args:
            instance_name: Name of the Cloud SQL instance
            
        Returns:
            Instance metadata
            
        Raises:
            AssertionError: If instance doesn't exist or isn't running
        """
        if not self.sql_client or not sql_v1:
            self.skipTest("Google Cloud SQL client not available")
        try:
            request = sql_v1.SqlInstancesGetRequest(
                project=self.project_id,
                instance=instance_name
            )
            instance = self.sql_client.get(request=request)
            self.assertEqual(instance.state, 'RUNNABLE', 
                           f"Cloud SQL instance {instance_name} is not running")
            return {
                'connection_name': instance.connection_name,
                'ip_address': instance.ip_addresses[0].ip_address if instance.ip_addresses else None,
                'state': instance.state
            }
        except Exception as e:
            self.fail(f"Cloud SQL instance {instance_name} not found: {e}")
            
    async def assert_service_healthy(self, service_url: str, path: str = '/health') -> Dict[str, Any]:
        """
        Assert that a service is healthy.
        
        Args:
            service_url: Base URL of the service
            path: Health check endpoint path
            
        Returns:
            Health check response data
            
        Raises:
            AssertionError: If service is not healthy
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{service_url}{path}", timeout=10.0)
                self.assertEqual(response.status_code, 200, 
                               f"Service {service_url} health check failed")
                return response.json()
            except Exception as e:
                self.fail(f"Service {service_url} not reachable: {e}")
                
    def get_staging_env_vars(self) -> Dict[str, str]:
        """
        Get environment variables for staging environment.
        
        Returns:
            Dictionary of staging environment variables
        """
        return {
            'ENVIRONMENT': 'staging',
            'GCP_PROJECT_ID': self.project_id,
            'GCP_REGION': self.region,
            'USE_SECRET_MANAGER': 'true',
            'CLOUD_SQL_CONNECTION_NAME': f"{self.project_id}:{self.region}:postgres-staging",
            'REDIS_HOST': 'redis-staging',
            'ENABLE_OBSERVABILITY': 'true'
        }
        
    def skip_if_not_staging(self):
        """Skip test if not running against staging environment."""
        # Check staging environment from test settings
        if get_env().get('ENVIRONMENT') != 'staging':
            self.skipTest("Test requires staging environment")
        # Also skip if GCP clients are not available
        if not self.secret_client and not self.sql_client:
            self.skipTest("GCP clients not available - requires GCP credentials")
            
    def require_gcp_credentials(self):
        """Ensure GCP credentials are available."""
        # Check GCP credentials from environment for staging tests
        if not get_env().get('GOOGLE_APPLICATION_CREDENTIALS'):
            self.skipTest("GOOGLE_APPLICATION_CREDENTIALS not set")
        # Also check if clients are available
        if not self.secret_client and not self.sql_client:
            self.skipTest("GCP clients not available")
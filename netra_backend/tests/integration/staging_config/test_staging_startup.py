"""
Test Staging Startup

Validates full application startup in staging environment
with all dependencies and configurations.
"""

from netra_backend.app.websocket_core.manager import WebSocketManager
# Test framework import - using pytest fixtures instead

import pytest
import asyncio
import os
import sys
import time
from typing import Dict, List, Optional
from unittest.mock import MagicMock, patch

from netra_backend.tests.integration.staging_config.base import StagingConfigTestBase

# Add app to path for imports

class TestStagingStartup(StagingConfigTestBase):

    """Test full application startup in staging."""
    
    async def _start_application(self, env_vars: Dict[str, str]) -> bool:

        """

        Attempt to start the application with given environment.
        
        Returns:

            True if startup successful, False otherwise

        """
        # Set environment variables

        original_env = os.environ.copy()

        try:

            os.environ.update(env_vars)
            
            # Import app modules
            from netra_backend.app.core.config import get_config
            from netra_backend.app.db.session import get_db
            from netra_backend.app.main import app
            from netra_backend.app.websocket_core.manager import WebSocketManager
            
            # Initialize configuration

            config = get_config()
            
            # Validate configuration loaded correctly

            self.assertEqual(config.environment, 'staging',

                           "Environment not set to staging")

            self.assertTrue(config.use_secret_manager,

                           "Secret Manager not enabled")
                           
            # Test database connection

            try:

                db = await get_db()

                await db.execute("SELECT 1")

                await db.close()

            except Exception as e:

                self.fail(f"Database connection failed: {e}")
                
            # Test Redis connection
            from netra_backend.app.redis_manager import redis_manager

            if redis_manager.redis_client:

                try:

                    await redis_manager.redis_client.ping()

                except Exception as e:

                    self.fail(f"Redis connection failed: {e}")
                    
            # Test WebSocket manager initialization

            ws_manager = WebSocketManager()

            self.assertIsNotNone(ws_manager, "WebSocket manager not initialized")
            
            return True
            
        except Exception as e:

            print(f"Startup failed: {e}")

            return False
            
        finally:
            # Restore original environment

            os.environ.clear()

            os.environ.update(original_env)
            
    def test_startup_with_staging_config(self):

        """Test application starts with staging configuration."""

        self.skip_if_not_staging()

        self.require_gcp_credentials()
        
        # Staging environment variables

        env_vars = self.get_staging_env_vars()

        env_vars.update({

            'GOOGLE_APPLICATION_CREDENTIALS': os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),

            'DATABASE_URL': f"postgresql://netra_user:{{password}}@/cloudsql/{self.project_id}:{self.region}:postgres-staging/netra_staging",

            'REDIS_URL': 'redis://redis-staging:6379/0'

        })
        
        # Run startup test

        success = self.loop.run_until_complete(

            self._start_application(env_vars)

        )
        
        self.assertTrue(success, "Application failed to start with staging config")
        
    def test_startup_secret_loading(self):

        """Test secrets are loaded correctly during startup."""

        self.skip_if_not_staging()

        self.require_gcp_credentials()
        
        with patch('app.config.secretmanager') as mock_secret_manager:
            # Mock secret client

            mock_client = MagicMock()

            mock_secret_manager.SecretManagerServiceClient.return_value = mock_client
            
            # Track secret access

            accessed_secrets = []
            
            def mock_access_secret(request):

                secret_name = request['name'].split('/')[-3]

                accessed_secrets.append(secret_name)
                
                # Return mock secret value

                mock_response = MagicMock()

                mock_response.payload.data = b'mock_secret_value'

                return mock_response
                
            mock_client.access_secret_version = mock_access_secret
            
            # Start application

            env_vars = self.get_staging_env_vars()

            self.loop.run_until_complete(

                self._start_application(env_vars)

            )
            
            # Verify critical secrets were accessed

            expected_secrets = [

                'jwt-secret-staging',

                'database-password',

                'gemini-api-key'

            ]
            
            for secret in expected_secrets:

                self.assertIn(secret, accessed_secrets,

                            f"Secret '{secret}' not loaded during startup")
                            
    def test_startup_with_missing_secrets(self):

        """Test startup behavior when secrets are missing."""

        self.skip_if_not_staging()
        
        with patch('app.config.secretmanager') as mock_secret_manager:
            # Mock secret client that throws errors

            mock_client = MagicMock()

            mock_secret_manager.SecretManagerServiceClient.return_value = mock_client
            
            def mock_access_secret(request):

                raise Exception("Secret not found")
                
            mock_client.access_secret_version = mock_access_secret
            
            # Start application - should fail gracefully

            env_vars = self.get_staging_env_vars()
            
            with self.assertRaises(Exception) as context:

                self.loop.run_until_complete(

                    self._start_application(env_vars)

                )
                
            self.assertIn("Secret", str(context.exception),

                        "Should fail with secret-related error")
                        
    def test_startup_service_initialization_order(self):

        """Test services initialize in correct order."""

        self.skip_if_not_staging()
        
        initialization_order = []
        
        # Patch service initializations to track order

        with patch('app.database.init_db') as mock_db_init:

            with patch('app.cache.init_redis') as mock_redis_init:

                with patch('app.ws_manager.WebSocketManager.__init__') as mock_ws_init:
                    
                    def track_init(name):

                        def wrapper(*args, **kwargs):

                            initialization_order.append(name)

                            return MagicMock()

                        return wrapper
                        
                    mock_db_init.side_effect = track_init('database')

                    mock_redis_init.side_effect = track_init('redis')

                    mock_ws_init.side_effect = track_init('websocket')
                    
                    # Start application

                    env_vars = self.get_staging_env_vars()

                    self.loop.run_until_complete(

                        self._start_application(env_vars)

                    )
                    
        # Verify initialization order

        expected_order = ['database', 'redis', 'websocket']

        self.assertEqual(initialization_order[:3], expected_order,

                        f"Services initialized in wrong order: {initialization_order}")
                        
    def test_startup_health_checks(self):

        """Test health checks pass after startup."""

        self.skip_if_not_staging()
        
        # Start application

        env_vars = self.get_staging_env_vars()

        success = self.loop.run_until_complete(

            self._start_application(env_vars)

        )
        
        if not success:

            self.skipTest("Application startup failed")
            
        # Test health endpoints

        health_checks = self.loop.run_until_complete(

            self.assert_service_healthy(self.staging_url)

        )
        
        # Verify health check response

        self.assertEqual(health_checks.get('status'), 'healthy',

                        "Health check reports unhealthy")

        self.assertIn('database', health_checks.get('checks', {}),

                     "Database health not reported")

        self.assertIn('redis', health_checks.get('checks', {}),

                     "Redis health not reported")
                     
    def test_startup_performance(self):

        """Test application starts within acceptable time."""

        self.skip_if_not_staging()
        
        start_time = time.time()
        
        # Start application

        env_vars = self.get_staging_env_vars()

        success = self.loop.run_until_complete(

            self._start_application(env_vars)

        )
        
        startup_time = time.time() - start_time
        
        self.assertTrue(success, "Application failed to start")

        self.assertLess(startup_time, 30,

                       f"Startup took {startup_time:.2f}s, exceeds 30s limit")
                       
    def test_startup_graceful_shutdown(self):

        """Test application shuts down gracefully."""

        self.skip_if_not_staging()
        
        # Start application

        env_vars = self.get_staging_env_vars()

        success = self.loop.run_until_complete(

            self._start_application(env_vars)

        )
        
        if not success:

            self.skipTest("Application startup failed")
            
        # Simulate shutdown
        from netra_backend.app.routes.mcp.main import shutdown_handlers
        
        shutdown_start = time.time()
        
        # Execute shutdown handlers

        for handler in shutdown_handlers:

            self.loop.run_until_complete(handler())
            
        shutdown_time = time.time() - shutdown_start
        
        self.assertLess(shutdown_time, 10,

                       f"Shutdown took {shutdown_time:.2f}s, exceeds 10s limit")
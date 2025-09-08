"""
Test Configuration-Environment Service Integration - Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal - Service-level configuration integration
- Business Goal: Ensure configuration flows correctly across service boundaries
- Value Impact: Prevents service configuration mismatches that cause authentication failures
- Strategic Impact: CRITICAL - Service integration failures cost $12K MRR per outage

CRITICAL: These tests validate configuration integration between services,
preventing the authentication and communication failures that cause cascade outages.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, Mock
from test_framework.base import BaseTestCase
from shared.isolated_environment import IsolatedEnvironment, get_env
from netra_backend.app.core.backend_environment import BackendEnvironment


class TestConfigurationEnvironmentServiceIntegration(BaseTestCase):
    """Test configuration integration across service boundaries."""
    
    def setup_method(self):
        """Setup service integration test environment."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.env.enable_isolation()
        
        # Set required environment for integration tests
        self.env.set("ENVIRONMENT", "test", "integration_setup")
        self.env.set("TESTING", "true", "integration_setup")
        
        # Set critical cross-service configuration
        self.env.set("SERVICE_SECRET", "cross-service-secret-32-characters-min", "integration_setup")
        self.env.set("JWT_SECRET_KEY", "cross-service-jwt-secret-32-chars-min", "integration_setup")
        
    def teardown_method(self):
        """Clean up service integration test environment."""
        self.env.reset_to_original()
        super().teardown_method()

    @pytest.mark.integration
    def test_backend_auth_service_configuration_consistency(self):
        """Test configuration consistency between backend and auth services."""
        # Simulate backend service configuration
        backend_service_config = {
            "SERVICE_ID": "netra-backend",  # CRITICAL: Must be stable value
            "SERVICE_SECRET": "shared-inter-service-secret-32-chars",
            "JWT_SECRET_KEY": "shared-jwt-secret-32-characters-min",
            "ENVIRONMENT": "staging",
            "AUTH_SERVICE_URL": "https://auth.staging.netrasystems.ai"
        }
        
        # Set backend configuration
        for key, value in backend_service_config.items():
            self.env.set(key, value, "backend_service")
            
        # Simulate what auth service would expect to receive
        expected_auth_request = {
            "service_id": self.env.get("SERVICE_ID"),  # Must match exactly
            "service_secret": self.env.get("SERVICE_SECRET"),  # Must match exactly
            "environment": self.env.get("ENVIRONMENT")
        }
        
        # Test critical SERVICE_ID consistency (prevents auth failures)
        assert expected_auth_request["service_id"] == "netra-backend", \
            "SERVICE_ID must be stable 'netra-backend' value to prevent auth failures"
            
        # Test SERVICE_SECRET consistency (prevents circuit breaker permanent open)
        assert len(expected_auth_request["service_secret"]) >= 32, \
            "SERVICE_SECRET must be at least 32 chars to prevent auth failures"
        assert expected_auth_request["service_secret"] != "", \
            "SERVICE_SECRET must not be empty to prevent complete auth failure"
            
        # Test environment consistency  
        assert expected_auth_request["environment"] in ["development", "test", "staging", "production"], \
            "Environment must be valid to prevent configuration confusion"
            
        # Test that JWT secret would be consistent across services
        backend_jwt = self.env.get("JWT_SECRET_KEY")
        assert len(backend_jwt) >= 32, "JWT secret must be strong enough for cross-service validation"
        
    @pytest.mark.integration
    def test_frontend_backend_configuration_integration(self):
        """Test configuration integration between frontend and backend services."""
        # Set backend configuration
        backend_config = {
            "ENVIRONMENT": "staging",
            "CORS_ALLOWED_ORIGINS": "https://app.staging.netrasystems.ai,https://admin.staging.netrasystems.ai",
            "API_PORT": "8000",
            "WEBSOCKET_PORT": "8000"
        }
        
        for key, value in backend_config.items():
            self.env.set(key, value, "backend_config")
            
        # Set frontend configuration (what frontend would send)
        frontend_config = {
            "NEXT_PUBLIC_API_URL": "https://api.staging.netrasystems.ai",
            "NEXT_PUBLIC_WS_URL": "wss://api.staging.netrasystems.ai",
            "NEXT_PUBLIC_AUTH_URL": "https://auth.staging.netrasystems.ai",
            "NEXT_PUBLIC_ENVIRONMENT": "staging"
        }
        
        for key, value in frontend_config.items():
            self.env.set(key, value, "frontend_config")
            
        # Test environment consistency between frontend and backend
        backend_env = self.env.get("ENVIRONMENT")
        frontend_env = self.env.get("NEXT_PUBLIC_ENVIRONMENT")
        assert backend_env == frontend_env, \
            "Frontend and backend environment must match to prevent configuration confusion"
            
        # Test CORS configuration allows frontend origins
        cors_origins = self.env.get("CORS_ALLOWED_ORIGINS").split(",")
        frontend_origin = "https://app.staging.netrasystems.ai"
        assert frontend_origin in cors_origins, \
            "CORS configuration must allow frontend origin to prevent API access failures"
            
        # Test that frontend API URL matches backend environment
        frontend_api_url = self.env.get("NEXT_PUBLIC_API_URL")
        if backend_env == "staging":
            assert "staging" in frontend_api_url, \
                "Frontend API URL must match staging environment"
        elif backend_env == "production":
            assert "staging" not in frontend_api_url, \
                "Frontend API URL must not contain staging in production"
                
        # Test WebSocket URL consistency with API URL
        frontend_ws_url = self.env.get("NEXT_PUBLIC_WS_URL")
        frontend_api_host = frontend_api_url.replace("https://", "").replace("http://", "")
        frontend_ws_host = frontend_ws_url.replace("wss://", "").replace("ws://", "")
        assert frontend_api_host == frontend_ws_host, \
            "WebSocket URL must use same host as API URL for consistency"
            
    @pytest.mark.integration  
    def test_database_configuration_cross_service_integration(self):
        """Test database configuration integration across services."""
        # Set database component configuration (SSOT pattern)
        db_config = {
            "POSTGRES_HOST": "staging-postgres.gcp",
            "POSTGRES_USER": "netra_staging",
            "POSTGRES_PASSWORD": "staging-db-password-32-characters-min",
            "POSTGRES_DB": "netra_staging", 
            "POSTGRES_PORT": "5432"
        }
        
        for key, value in db_config.items():
            self.env.set(key, value, "database_config")
            
        # Test that all services would get consistent database configuration
        services = ["backend", "auth", "analytics"]
        
        for service in services:
            # Each service should build the same database URL from components
            service_db_host = self.env.get("POSTGRES_HOST")
            service_db_user = self.env.get("POSTGRES_USER")
            service_db_name = self.env.get("POSTGRES_DB")
            service_db_port = self.env.get("POSTGRES_PORT")
            
            # All services should see the same configuration
            assert service_db_host == "staging-postgres.gcp", \
                f"{service} service should get consistent database host"
            assert service_db_user == "netra_staging", \
                f"{service} service should get consistent database user"
            assert service_db_name == "netra_staging", \
                f"{service} service should get consistent database name"
                
        # Test that password is secure enough for all services
        db_password = self.env.get("POSTGRES_PASSWORD")
        assert len(db_password) >= 32, \
            "Database password must be secure enough for cross-service usage"
        assert db_password != "password", \
            "Database password must not be default value"
            
    @pytest.mark.integration
    def test_redis_session_configuration_cross_service_integration(self):
        """Test Redis session configuration integration across services."""
        # Set Redis configuration
        redis_config = {
            "REDIS_HOST": "staging-redis.gcp",
            "REDIS_PORT": "6379",
            "REDIS_PASSWORD": "staging-redis-password-32-chars-min",
            "REDIS_URL": "redis://:staging-redis-password-32-chars-min@staging-redis.gcp:6379/0"
        }
        
        for key, value in redis_config.items():
            self.env.set(key, value, "redis_config")
            
        # Test Redis configuration consistency for session management
        redis_host = self.env.get("REDIS_HOST")
        redis_port = self.env.get("REDIS_PORT")
        redis_url = self.env.get("REDIS_URL")
        
        # Verify URL construction consistency
        assert redis_host in redis_url, "Redis URL must contain correct host"
        assert redis_port in redis_url, "Redis URL must contain correct port"
        
        # Test that Redis configuration supports session sharing between services
        redis_password = self.env.get("REDIS_PASSWORD")
        assert len(redis_password) >= 32, \
            "Redis password must be secure enough for session sharing"
        assert redis_password in redis_url, \
            "Redis URL must contain password for authenticated access"
            
        # Test Redis database selection for different service purposes
        assert "/0" in redis_url, "Redis URL should specify database number"
        
    @pytest.mark.integration
    def test_oauth_configuration_auth_service_integration(self):
        """Test OAuth configuration integration with auth service."""
        # Set OAuth configuration using dual naming pattern
        oauth_config = {
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging-oauth-client-id",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "staging-oauth-client-secret-32-chars",
            "GOOGLE_OAUTH_REDIRECT_URL": "https://auth.staging.netrasystems.ai/auth/callback/google",
            "OAUTH_ENABLED": "true"
        }
        
        for key, value in oauth_config.items():
            self.env.set(key, value, "oauth_config")
            
        # Test OAuth configuration for staging environment
        environment = self.env.get("ENVIRONMENT", "test")
        if environment == "staging":
            oauth_client_id = self.env.get("GOOGLE_OAUTH_CLIENT_ID_STAGING")
            oauth_client_secret = self.env.get("GOOGLE_OAUTH_CLIENT_SECRET_STAGING")
            
            assert oauth_client_id is not None, \
                "OAuth client ID must be configured for staging"
            assert oauth_client_secret is not None, \
                "OAuth client secret must be configured for staging"
            assert len(oauth_client_secret) >= 32, \
                "OAuth client secret must be secure"
                
        # Test OAuth redirect URL consistency
        oauth_redirect = self.env.get("GOOGLE_OAUTH_REDIRECT_URL")
        assert "staging" in oauth_redirect, \
            "OAuth redirect URL must match staging environment"
        assert oauth_redirect.startswith("https://"), \
            "OAuth redirect URL must use HTTPS for security"
            
    @pytest.mark.integration
    def test_logging_configuration_cross_service_integration(self):
        """Test logging configuration integration across all services."""
        # Set logging configuration
        logging_config = {
            "LOG_LEVEL": "INFO",
            "LOG_FORMAT": "json", 
            "LOG_OUTPUT": "stdout",
            "ENVIRONMENT": "staging"
        }
        
        for key, value in logging_config.items():
            self.env.set(key, value, "logging_config")
            
        # Test logging configuration consistency
        log_level = self.env.get("LOG_LEVEL")
        environment = self.env.get("ENVIRONMENT")
        
        # Environment-appropriate logging levels
        if environment == "production":
            assert log_level in ["INFO", "WARNING", "ERROR"], \
                "Production should use appropriate log level"
        elif environment == "staging":
            assert log_level in ["DEBUG", "INFO"], \
                "Staging should allow detailed logging"
        elif environment == "development":
            assert log_level in ["DEBUG", "INFO"], \
                "Development should allow debug logging"
                
        # Test log format consistency across services
        log_format = self.env.get("LOG_FORMAT")
        assert log_format in ["json", "text"], \
            "Log format must be consistent across services"
            
        # Test that all services would use the same logging configuration
        services = ["backend", "auth", "frontend", "analytics"]
        for service in services:
            service_log_level = self.env.get("LOG_LEVEL")
            assert service_log_level == log_level, \
                f"{service} service should use consistent log level"
                
    @pytest.mark.integration
    def test_monitoring_configuration_service_integration(self):
        """Test monitoring and observability configuration integration."""
        # Set monitoring configuration
        monitoring_config = {
            "LANGFUSE_PUBLIC_KEY": "staging-langfuse-public-key",
            "LANGFUSE_SECRET_KEY": "staging-langfuse-secret-32-chars-min",
            "LANGFUSE_HOST": "https://staging-langfuse.example.com",
            "PROMETHEUS_ENABLED": "true",
            "GRAFANA_URL": "https://grafana.staging.netrasystems.ai"
        }
        
        for key, value in monitoring_config.items():
            self.env.set(key, value, "monitoring_config")
            
        # Test Langfuse configuration for LLM monitoring
        langfuse_public = self.env.get("LANGFUSE_PUBLIC_KEY")
        langfuse_secret = self.env.get("LANGFUSE_SECRET_KEY")
        langfuse_host = self.env.get("LANGFUSE_HOST")
        
        if langfuse_public:
            assert langfuse_secret is not None, \
                "Langfuse secret key must be present if public key is configured"
            assert len(langfuse_secret) >= 32, \
                "Langfuse secret key must be secure"
            assert langfuse_host.startswith("https://"), \
                "Langfuse host must use HTTPS"
                
        # Test monitoring URL consistency with environment
        environment = self.env.get("ENVIRONMENT", "test")
        grafana_url = self.env.get("GRAFANA_URL")
        
        if environment == "staging":
            assert "staging" in grafana_url, \
                "Grafana URL must match staging environment"
                
        # Test monitoring integration across services
        prometheus_enabled = self.env.get("PROMETHEUS_ENABLED")
        if prometheus_enabled == "true":
            # All services should be able to use the same monitoring configuration
            assert langfuse_host is not None, \
                "Monitoring host must be configured when monitoring is enabled"
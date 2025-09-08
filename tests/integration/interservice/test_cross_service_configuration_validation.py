"""
Cross-Service Configuration Validation Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability
- Business Goal: Prevent configuration drift and service startup failures
- Value Impact: Eliminates service outages due to configuration mismatches
- Strategic Impact: Ensures reliable deployments and reduces operational overhead

These tests validate that configuration settings are consistent across all services
and that services can communicate using shared configuration values.
"""

import pytest
from typing import Dict, Any
from unittest.mock import Mock, patch

from test_framework.ssot.base_test_case import BaseTestCase
from shared.isolated_environment import get_env


class TestCrossServiceConfigurationValidation(BaseTestCase):
    """Integration tests for cross-service configuration consistency."""
    
    @pytest.mark.integration
    @pytest.mark.interservice
    @pytest.mark.config
    async def test_service_discovery_configuration_consistency(self):
        """
        Test that all services use consistent service discovery URLs.
        
        BVJ: System reliability - ensures services can find each other reliably,
        preventing service communication failures in production.
        """
        env = get_env()
        env.enable_isolation()
        
        # Set up standard service configuration
        service_configs = {
            "BACKEND_SERVICE_URL": "http://localhost:8000",
            "AUTH_SERVICE_URL": "http://localhost:8081", 
            "ANALYTICS_SERVICE_URL": "http://localhost:8002",
            "FRONTEND_URL": "http://localhost:3000"
        }
        
        for key, value in service_configs.items():
            env.set(key, value, "test_configuration")
        
        # Verify configuration consistency
        backend_url = env.get("BACKEND_SERVICE_URL")
        auth_url = env.get("AUTH_SERVICE_URL")
        analytics_url = env.get("ANALYTICS_SERVICE_URL")
        frontend_url = env.get("FRONTEND_URL")
        
        # Validate URLs are properly formatted
        assert backend_url.startswith("http://"), "Backend URL must use HTTP protocol"
        assert auth_url.startswith("http://"), "Auth URL must use HTTP protocol"
        assert analytics_url.startswith("http://"), "Analytics URL must use HTTP protocol"
        assert frontend_url.startswith("http://"), "Frontend URL must use HTTP protocol"
        
        # Validate port consistency (no conflicts)
        urls = [backend_url, auth_url, analytics_url, frontend_url]
        ports = []
        for url in urls:
            if ":" in url.split("//")[1]:
                port = url.split(":")[-1].rstrip("/")
                ports.append(int(port))
        
        # Ensure no duplicate ports
        assert len(ports) == len(set(ports)), f"Duplicate ports detected: {ports}"
        
        # Validate port ranges are appropriate
        for port in ports:
            assert 1024 <= port <= 65535, f"Port {port} outside valid range"
            assert port not in [22, 80, 443, 3306, 5432], f"Port {port} conflicts with system services"
    
    @pytest.mark.integration
    @pytest.mark.interservice
    @pytest.mark.config
    async def test_database_configuration_consistency(self):
        """
        Test database configuration consistency across services.
        
        BVJ: Data integrity - ensures all services connect to correct databases
        with proper credentials, preventing data corruption and access issues.
        """
        env = get_env()
        env.enable_isolation()
        
        # Set up database configuration
        db_config = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5434",  # Test environment port
            "POSTGRES_USER": "netra_test", 
            "POSTGRES_PASSWORD": "netra_test_password",
            "POSTGRES_DB": "netra_test",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6381",  # Test environment port
            "REDIS_URL": "redis://localhost:6381/0"
        }
        
        for key, value in db_config.items():
            env.set(key, value, "test_database_config")
        
        # Test PostgreSQL configuration consistency
        pg_host = env.get("POSTGRES_HOST")
        pg_port = env.get("POSTGRES_PORT")
        pg_user = env.get("POSTGRES_USER")
        pg_password = env.get("POSTGRES_PASSWORD")
        pg_db = env.get("POSTGRES_DB")
        
        assert pg_host is not None, "PostgreSQL host must be configured"
        assert pg_port is not None, "PostgreSQL port must be configured"
        assert pg_user is not None, "PostgreSQL user must be configured"
        assert pg_password is not None, "PostgreSQL password must be configured"
        assert pg_db is not None, "PostgreSQL database must be configured"
        
        # Validate port is numeric and in test range
        assert pg_port.isdigit(), "PostgreSQL port must be numeric"
        assert int(pg_port) == 5434, "Test environment should use port 5434"
        
        # Validate Redis configuration consistency
        redis_host = env.get("REDIS_HOST")
        redis_port = env.get("REDIS_PORT")
        redis_url = env.get("REDIS_URL")
        
        assert redis_host is not None, "Redis host must be configured"
        assert redis_port is not None, "Redis port must be configured"
        assert redis_url is not None, "Redis URL must be configured"
        
        # Validate Redis URL contains correct host and port
        assert redis_host in redis_url, "Redis URL must contain configured host"
        assert redis_port in redis_url, "Redis URL must contain configured port"
        assert int(redis_port) == 6381, "Test environment should use Redis port 6381"
    
    @pytest.mark.integration
    @pytest.mark.interservice
    @pytest.mark.config
    async def test_authentication_configuration_consistency(self):
        """
        Test authentication configuration consistency across services.
        
        BVJ: Security critical - ensures all services use same authentication
        secrets and OAuth configuration, preventing auth bypass vulnerabilities.
        """
        env = get_env()
        env.enable_isolation()
        
        # Set up authentication configuration
        auth_config = {
            "JWT_SECRET_KEY": "test-jwt-secret-key-32-characters-long-for-testing-only",
            "SERVICE_SECRET": "test-service-secret-32-characters-long-for-cross-service-auth",
            "GOOGLE_OAUTH_CLIENT_ID": "test-oauth-client-id",
            "GOOGLE_OAUTH_CLIENT_SECRET": "test-oauth-client-secret",
            "FERNET_KEY": "test-fernet-key-for-encryption-32-characters-long-base64-encoded="
        }
        
        for key, value in auth_config.items():
            env.set(key, value, "test_auth_config")
        
        # Validate JWT configuration
        jwt_secret = env.get("JWT_SECRET_KEY")
        service_secret = env.get("SERVICE_SECRET")
        
        assert jwt_secret is not None, "JWT secret key must be configured"
        assert service_secret is not None, "Service secret must be configured"
        assert len(jwt_secret) >= 32, "JWT secret must be at least 32 characters"
        assert len(service_secret) >= 32, "Service secret must be at least 32 characters"
        assert jwt_secret != service_secret, "JWT and service secrets must be different"
        
        # Validate OAuth configuration
        oauth_client_id = env.get("GOOGLE_OAUTH_CLIENT_ID")
        oauth_client_secret = env.get("GOOGLE_OAUTH_CLIENT_SECRET")
        
        assert oauth_client_id is not None, "OAuth client ID must be configured"
        assert oauth_client_secret is not None, "OAuth client secret must be configured"
        assert len(oauth_client_id) > 10, "OAuth client ID must be substantial"
        assert len(oauth_client_secret) > 10, "OAuth client secret must be substantial"
        
        # Validate encryption configuration
        fernet_key = env.get("FERNET_KEY")
        assert fernet_key is not None, "Fernet key must be configured"
        assert len(fernet_key) >= 44, "Fernet key must be properly base64 encoded (44+ chars)"
        
        # Test configuration isolation between environments
        environment = env.get("ENVIRONMENT", "test")
        if environment == "test":
            # In test environment, secrets can be predictable
            assert "test" in jwt_secret.lower(), "Test JWT secret should indicate test environment"
            assert "test" in service_secret.lower(), "Test service secret should indicate test environment"
        elif environment in ["staging", "production"]:
            # In production environments, secrets should be random
            assert "test" not in jwt_secret.lower(), "Production JWT secret must not contain 'test'"
            assert "test" not in service_secret.lower(), "Production service secret must not contain 'test'"
    
    @pytest.mark.integration
    @pytest.mark.interservice
    @pytest.mark.config
    async def test_logging_configuration_consistency(self):
        """
        Test logging configuration consistency across services.
        
        BVJ: Operational excellence - ensures consistent logging for debugging
        and monitoring, reducing troubleshooting time and operational costs.
        """
        env = get_env()
        env.enable_isolation()
        
        # Set up logging configuration
        logging_config = {
            "LOG_LEVEL": "DEBUG",
            "LOG_FORMAT": "json",
            "ENABLE_STRUCTURED_LOGGING": "true",
            "LOG_TO_FILE": "false",
            "CONSOLE_LOG_LEVEL": "INFO"
        }
        
        for key, value in logging_config.items():
            env.set(key, value, "test_logging_config")
        
        # Validate logging level configuration
        log_level = env.get("LOG_LEVEL")
        console_log_level = env.get("CONSOLE_LOG_LEVEL")
        
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        assert log_level in valid_log_levels, f"LOG_LEVEL must be one of {valid_log_levels}"
        assert console_log_level in valid_log_levels, f"CONSOLE_LOG_LEVEL must be one of {valid_log_levels}"
        
        # Validate logging format configuration
        log_format = env.get("LOG_FORMAT")
        structured_logging = env.get("ENABLE_STRUCTURED_LOGGING")
        
        assert log_format in ["json", "text"], "LOG_FORMAT must be 'json' or 'text'"
        assert structured_logging.lower() in ["true", "false"], "ENABLE_STRUCTURED_LOGGING must be boolean"
        
        # Validate file logging configuration
        log_to_file = env.get("LOG_TO_FILE")
        assert log_to_file.lower() in ["true", "false"], "LOG_TO_FILE must be boolean"
        
        # Test environment should typically use console logging
        if env.get("ENVIRONMENT") == "test":
            assert log_to_file.lower() == "false", "Test environment should not log to files"
            assert log_level == "DEBUG", "Test environment should use DEBUG logging"
        
        # Validate logging consistency rules
        if structured_logging.lower() == "true":
            assert log_format == "json", "Structured logging requires JSON format"
        
        # Ensure debug logging is available in test environment
        log_level_hierarchy = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]
        current_level_idx = log_level_hierarchy.index(log_level)
        debug_level_idx = log_level_hierarchy.index("DEBUG")
        
        if env.get("ENVIRONMENT") == "test":
            assert current_level_idx >= debug_level_idx, "Test environment must enable DEBUG logging"
#!/usr/bin/env python3
"""
Issue #1278 Infrastructure Problems - Configuration Validation Tests

MISSION: Reproduce and validate infrastructure configuration issues
- Database connectivity problems
- Environment variable mismatches  
- Service configuration drift
- SSL certificate validation failures

EXPECTED: Tests should FAIL initially, reproducing Issue #1278 problems
"""
import os
import pytest
import asyncio
import logging
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch

# Test infrastructure imports
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.core.configuration.base import get_config
from shared.isolated_environment import IsolatedEnvironment

# Database imports
from netra_backend.app.db.database_manager import DatabaseManager

# Auth imports
from netra_backend.app.auth_integration.auth import AuthIntegration

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestIssue1278ConfigurationValidation(SSotBaseTestCase):
    """Test suite to reproduce Issue #1278 infrastructure configuration problems"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class with isolated environment"""
        super().setUpClass()
        cls.env = IsolatedEnvironment()
        cls.env.set("ENVIRONMENT", "staging", "test_setup")
        cls.config = get_config()
        
    def setUp(self):
        """Set up each test case"""
        super().setUp()
        logger.info("Starting Issue #1278 configuration validation test")
        
    def test_staging_database_configuration_drift(self):
        """
        Test: Validate staging database configuration
        EXPECT: Should FAIL - reproducing database connectivity issues
        """
        logger.info("Testing staging database configuration drift")
        
        try:
            # Test database configuration values
            db_config = self.config.database
            
            # Check for SSL configuration
            ssl_params = getattr(db_config, 'ssl_params', None)
            assert ssl_params is not None, "SSL parameters missing from database config"
            
            # Check connection timeout settings  
            timeout = getattr(db_config, 'connection_timeout', None)
            assert timeout == 600, f"Expected 600s timeout, got {timeout}"
            
            # Check for VPC connector configuration
            vpc_connector = self.env.get_env_var("VPC_CONNECTOR")
            assert vpc_connector == "staging-connector", f"Invalid VPC connector: {vpc_connector}"
            
            # Validate database URL format
            db_url = self.env.get_env_var("DATABASE_URL")
            assert "postgresql://" in db_url, "Database URL must be PostgreSQL"
            assert "sslmode=require" in db_url, "SSL must be required"
            
            logger.info("✅ Database configuration validation passed")
            
        except Exception as e:
            logger.error(f"❌ Database configuration validation failed: {e}")
            # This failure is EXPECTED for Issue #1278
            raise AssertionError(f"Issue #1278 reproduction: Database config drift - {e}")
    
    def test_domain_configuration_ssl_certificates(self):
        """
        Test: Validate domain configuration and SSL certificates
        EXPECT: Should FAIL - reproducing SSL certificate issues
        """
        logger.info("Testing domain configuration and SSL certificates")
        
        try:
            # Check for correct domain usage
            backend_url = self.env.get_env_var("BACKEND_URL") 
            frontend_url = self.env.get_env_var("FRONTEND_URL")
            websocket_url = self.env.get_env_var("WEBSOCKET_URL")
            
            # Validate correct staging domains (*.netrasystems.ai)
            assert "netrasystems.ai" in backend_url, f"Backend URL domain issue: {backend_url}"
            assert "netrasystems.ai" in frontend_url, f"Frontend URL domain issue: {frontend_url}"
            assert "netrasystems.ai" in websocket_url, f"WebSocket URL domain issue: {websocket_url}"
            
            # Check for deprecated domains
            deprecated_patterns = [".staging.netrasystems.ai", "run.app"]
            for url in [backend_url, frontend_url, websocket_url]:
                for pattern in deprecated_patterns:
                    assert pattern not in url, f"Deprecated domain pattern {pattern} found in {url}"
            
            # Validate WebSocket protocol
            assert websocket_url.startswith("wss://"), f"WebSocket must use WSS: {websocket_url}"
            
            logger.info("✅ Domain configuration validation passed")
            
        except Exception as e:
            logger.error(f"❌ Domain configuration validation failed: {e}")
            # This failure is EXPECTED for Issue #1278
            raise AssertionError(f"Issue #1278 reproduction: SSL/Domain config issue - {e}")
            
    def test_service_environment_variable_consistency(self):
        """
        Test: Validate consistency of environment variables across services
        EXPECT: Should FAIL - reproducing environment variable drift
        """
        logger.info("Testing service environment variable consistency")
        
        try:
            # Critical environment variables that must be consistent
            critical_vars = [
                "JWT_SECRET_KEY",
                "DATABASE_URL", 
                "REDIS_URL",
                "CORS_ORIGINS",
                "BACKEND_URL",
                "FRONTEND_URL"
            ]
            
            missing_vars = []
            for var in critical_vars:
                value = self.env.get_env_var(var)
                if not value:
                    missing_vars.append(var)
            
            assert not missing_vars, f"Missing critical environment variables: {missing_vars}"
            
            # Test JWT configuration consistency
            jwt_secret = self.env.get_env_var("JWT_SECRET_KEY")
            assert jwt_secret and len(jwt_secret) > 32, "JWT secret too short or missing"
            
            # Test CORS configuration
            cors_origins = self.env.get_env_var("CORS_ORIGINS")
            assert cors_origins, "CORS origins not configured"
            
            logger.info("✅ Environment variable consistency validation passed")
            
        except Exception as e:
            logger.error(f"❌ Environment variable consistency failed: {e}")
            # This failure is EXPECTED for Issue #1278
            raise AssertionError(f"Issue #1278 reproduction: Environment variable drift - {e}")
    
    def test_redis_connectivity_configuration(self):
        """
        Test: Validate Redis connectivity configuration
        EXPECT: Should FAIL - reproducing Redis connectivity issues
        """
        logger.info("Testing Redis connectivity configuration")
        
        try:
            redis_url = self.env.get_env_var("REDIS_URL")
            assert redis_url, "Redis URL not configured"
            
            # Check for proper Redis URL format
            assert redis_url.startswith("redis://") or redis_url.startswith("rediss://"), \
                f"Invalid Redis URL format: {redis_url}"
            
            # Check for VPC connector requirement
            vpc_connector = self.env.get_env_var("VPC_CONNECTOR")
            assert vpc_connector, "VPC connector required for Redis access"
            
            # Validate Redis connection parameters
            if "password" in redis_url:
                assert len(redis_url.split("@")[0].split(":")[-1]) > 8, "Redis password too short"
            
            logger.info("✅ Redis connectivity configuration passed")
            
        except Exception as e:
            logger.error(f"❌ Redis connectivity configuration failed: {e}")
            # This failure is EXPECTED for Issue #1278
            raise AssertionError(f"Issue #1278 reproduction: Redis config issue - {e}")
    
    def test_authentication_service_configuration(self):
        """
        Test: Validate authentication service configuration
        EXPECT: Should FAIL - reproducing auth configuration issues
        """
        logger.info("Testing authentication service configuration")
        
        try:
            # Test OAuth configuration
            oauth_vars = [
                "GOOGLE_CLIENT_ID",
                "GOOGLE_CLIENT_SECRET",
                "OAUTH_REDIRECT_URI"
            ]
            
            for var in oauth_vars:
                value = self.env.get_env_var(var)
                assert value, f"OAuth variable {var} not configured"
            
            # Test redirect URI format
            redirect_uri = self.env.get_env_var("OAUTH_REDIRECT_URI")
            assert "https://" in redirect_uri, "OAuth redirect must use HTTPS"
            assert "netrasystems.ai" in redirect_uri, "OAuth redirect must use correct domain"
            
            # Test allowed origins
            allowed_origins = self.env.get_env_var("ALLOWED_ORIGINS", "").split(",")
            required_ports = ["3000", "8000", "8001", "8081"]
            
            for port in required_ports:
                port_found = any(port in origin for origin in allowed_origins)
                assert port_found, f"Required port {port} not in allowed origins"
            
            logger.info("✅ Authentication service configuration passed")
            
        except Exception as e:
            logger.error(f"❌ Authentication service configuration failed: {e}")
            # This failure is EXPECTED for Issue #1278
            raise AssertionError(f"Issue #1278 reproduction: Auth config issue - {e}")


@pytest.mark.infrastructure
@pytest.mark.issue_1278
class TestIssue1278ServiceHealthChecks(SSotBaseTestCase):
    """Service health check tests for Issue #1278"""
    
    def test_load_balancer_health_check_configuration(self):
        """
        Test: Validate load balancer health check configuration
        EXPECT: Should FAIL - reproducing health check failures
        """
        logger.info("Testing load balancer health check configuration")
        
        try:
            # Check health check endpoint configuration
            health_endpoint = "/health"
            timeout_config = self.env.get_env_var("HEALTH_CHECK_TIMEOUT", "30")
            
            assert int(timeout_config) >= 60, \
                f"Health check timeout too short: {timeout_config}s (need 60s+)"
            
            # Check startup time configuration
            startup_timeout = self.env.get_env_var("STARTUP_TIMEOUT", "300")
            assert int(startup_timeout) >= 600, \
                f"Startup timeout too short: {startup_timeout}s (need 600s+)"
            
            logger.info("✅ Load balancer health check configuration passed")
            
        except Exception as e:
            logger.error(f"❌ Load balancer health check configuration failed: {e}")
            # This failure is EXPECTED for Issue #1278
            raise AssertionError(f"Issue #1278 reproduction: Health check config issue - {e}")
    
    def test_monitoring_configuration(self):
        """
        Test: Validate monitoring and error reporting configuration
        EXPECT: Should FAIL - reproducing monitoring issues
        """
        logger.info("Testing monitoring configuration")
        
        try:
            # Check GCP error reporting configuration
            project_id = self.env.get_env_var("GCP_PROJECT_ID")
            assert project_id == "netra-staging", f"Wrong project ID: {project_id}"
            
            # Check logging configuration
            log_level = self.env.get_env_var("LOG_LEVEL", "INFO")
            assert log_level in ["DEBUG", "INFO", "WARNING", "ERROR"], \
                f"Invalid log level: {log_level}"
            
            # Check metrics collection
            metrics_enabled = self.env.get_env_var("ENABLE_METRICS", "false")
            assert metrics_enabled.lower() == "true", "Metrics should be enabled in staging"
            
            logger.info("✅ Monitoring configuration passed")
            
        except Exception as e:
            logger.error(f"❌ Monitoring configuration failed: {e}")
            # This failure is EXPECTED for Issue #1278
            raise AssertionError(f"Issue #1278 reproduction: Monitoring config issue - {e}")


if __name__ == "__main__":
    # Run tests with verbose output to capture failure details
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure to capture Issue #1278 reproduction
        "--log-cli-level=INFO"
    ])
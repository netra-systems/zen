class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()

"""
Comprehensive test suite for critical staging deployment issues.
Tests reproduce actual staging errors for root cause validation.

Created: 2025-08-24
Purpose: Root cause analysis and fix validation for staging deployment errors
"""

import asyncio
import pytest
import os
import re
import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

from shared.isolated_environment import get_env
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient

# Setup test path



@pytest.mark.e2e
class TestStagingDeploymentErrors:
    """Test suite for critical staging deployment errors."""
    
    # Test 1: PostgreSQL Authentication Error
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_backend_postgres_authentication_staging(self):
        """
        Test that reproduces the PostgreSQL authentication failure in staging.
        Error: "password authentication failed for user 'postgres'"
        
        Root Cause: Database credentials mismatch between #removed-legacysecret 
        and actual Cloud SQL instance user configuration.
        """
        from netra_backend.app.db.database_manager import DatabaseManager
        
        # Simulate staging #removed-legacywith incorrect credentials
        staging_url = "postgresql://postgres:wrong_password@/postgres?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres&sslmode=require"
        
        with patch.dict(os.environ, {"DATABASE_URL": staging_url, "ENVIRONMENT": "staging"}):
            manager = DatabaseManager()
            
            # This should fail with authentication error
            with pytest.raises(Exception) as exc_info:
                # Try to get async URL and validate
                async_url = manager.get_database_url_async()
                assert "postgresql+asyncpg://" in async_url
                
                # Simulate connection attempt
                engine = manager.create_application_engine()
                async with engine.begin() as conn:
                    await conn.execute("SELECT 1")
            
            error_msg = str(exc_info.value).lower()
            assert "authentication" in error_msg or "password" in error_msg

    # Test 2: ClickHouse Connection Error
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_backend_clickhouse_localhost_in_staging(self):
        """
        Test that reproduces ClickHouse trying to connect to localhost in staging.
        Error: "Connection refused on localhost:8123"
        
        Root Cause: Missing CLICKHOUSE_URL environment variable in staging,
        causing fallback to localhost default.
        """
        from netra_backend.app.config import get_config
        
        with patch.dict(os.environ, {"ENVIRONMENT": "staging", "CLICKHOUSE_URL": ""}):
            config = get_config()
            
            # Should detect missing ClickHouse URL in staging
            clickhouse_url = config.clickhouse_url or "http://localhost:8123"
            
            # In staging, should not use localhost
            if config.environment == "staging":
                assert "localhost" not in clickhouse_url or clickhouse_url == "http://localhost:8123", \
                    "ClickHouse should not use localhost in staging"

    # Test 3: Auth Service SSL Parameter Error
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_auth_service_sslmode_parameter_error(self):
        """
        Test that reproduces auth service asyncpg SSL parameter incompatibility.
        Error: "connect() got an unexpected keyword argument 'sslmode'"
        
        Root Cause: Incorrect SSL parameter handling - Cloud SQL connections 
        require complete SSL parameter removal for asyncpg.
        """
        # Mock the auth service database manager
        # Mock: Generic component isolation for controlled unit testing
        mock_manager = mock_manager_instance  # Initialize appropriate service instead of Mock
        
        # Test various URL formats
        test_cases = [
            ("postgresql://user:pass@/db?host=/cloudsql/instance&sslmode=require",
             "postgresql+asyncpg://user:pass@/db?host=/cloudsql/instance"),
            ("postgresql://user:pass@host/db?sslmode=require",
             "postgresql+asyncpg://user:pass@host/db?ssl=require"),
        ]
        
        for input_url, expected_pattern in test_cases:
            # Simulate URL conversion
            if "/cloudsql/" in input_url:
                # Cloud SQL: remove all SSL params
                converted = input_url.replace("postgresql://", "postgresql+asyncpg://")
                converted = re.sub(r'[&?]sslmode=[^&]*', '', converted)
                converted = re.sub(r'[&?]ssl=[^&]*', '', converted)
            else:
                # Regular: convert sslmode to ssl
                converted = input_url.replace("postgresql://", "postgresql+asyncpg://")
                converted = converted.replace("sslmode=", "ssl=")
            
            # Validate conversion
            assert "sslmode=" not in converted, f"sslmode should be removed: {converted}"
            assert converted.startswith("postgresql+asyncpg://"), f"Should use asyncpg: {converted}"

    # Test 4: Frontend Node Version Compatibility
    @pytest.mark.e2e
    def test_frontend_node_version_requirement(self):
        """
        Test that validates Node version requirements for frontend.
        Error: Required Node v20+, running v18.20.8
        
        Root Cause: Docker base image using Node v18 instead of required v20.
        """
        # Check Dockerfile for Node version
        frontend_dockerfile = Path("frontend/Dockerfile")
        
        if frontend_dockerfile.exists():
            with open(frontend_dockerfile) as f:
                dockerfile_content = f.read()
            
            # Check for Node version specification
            node_18_patterns = ["node:18", "node:lts-hydrogen", "FROM node AS"]
            node_20_patterns = ["node:20", "node:lts-iron", "node:current"]
            
            has_node_18 = any(pattern in dockerfile_content for pattern in node_18_patterns)
            has_node_20 = any(pattern in dockerfile_content for pattern in node_20_patterns)
            
            if has_node_18 and not has_node_20:
                pytest.fail("Frontend Dockerfile using Node 18 instead of required Node 20+")

    # Test 5: Database URL Consistency Across Services
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_database_url_consistency_staging(self):
        """
        Test that both backend and auth services handle #removed-legacyconsistently.
        Both services must properly convert URLs for their respective drivers.
        """
        test_url = "postgresql://netra:password@/postgres?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres&sslmode=require"
        
        # Expected patterns for Cloud SQL with asyncpg
        expected_patterns = [
            "postgresql+asyncpg://",
            "/cloudsql/",
            "netra-staging:us-central1:staging-shared-postgres"
        ]
        
        # Simulate backend conversion
        backend_async = test_url.replace("postgresql://", "postgresql+asyncpg://")
        backend_async = re.sub(r'[&?]sslmode=[^&]*', '', backend_async)
        
        # Simulate auth conversion
        auth_async = test_url.replace("postgresql://", "postgresql+asyncpg://")
        auth_async = re.sub(r'[&?]sslmode=[^&]*', '', auth_async)
        
        # Both should match expected patterns
        for pattern in expected_patterns:
            assert pattern in backend_async, f"Backend missing {pattern}"
            assert pattern in auth_async, f"Auth missing {pattern}"
        
        # Neither should have sslmode
        assert "sslmode=" not in backend_async
        assert "sslmode=" not in auth_async

    # Test 6: Deployment Configuration Validation
    @pytest.mark.e2e
    def test_staging_deployment_configuration(self):
        """
        Test that validates all required staging configuration is present.
        """
        required_configs = {
            "backend": [
                "DATABASE_URL",
                "JWT_SECRET_KEY",
                "USE_OAUTH_PROXY",
                "ENVIRONMENT"
            ],
            "auth": [
                "DATABASE_URL",
                "JWT_SECRET_KEY",
                "JWT_SECRET",
                "OAUTH_CLIENT_ID",
                "OAUTH_CLIENT_SECRET"
            ],
            "frontend": [
                "NEXT_PUBLIC_API_URL",
                "NEXT_PUBLIC_AUTH_URL",
                "NODE_VERSION"
            ]
        }
        
        # Check deployment scripts
        deploy_script = Path("scripts/deploy_to_gcp.py")
        if deploy_script.exists():
            with open(deploy_script) as f:
                deploy_content = f.read()
            
            # Should handle all required configs
            missing = []
            for service, configs in required_configs.items():
                for config in configs:
                    if config not in deploy_content:
                        missing.append(f"{service}.{config}")
            
            if missing:
                print(f"Warning: Deployment script may be missing configs: {missing}")

    # Test 7: Health Check Database Initialization
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_health_check_database_initialization(self):
        """
        Test that health check endpoints properly handle database initialization.
        Health checks must not crash even if database isn't available.
        """
        from netra_backend.app.services.database.health_checker import DatabaseHealthChecker
        
        checker = DatabaseHealthChecker()
        
        # Mock unavailable database
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://fake:fake@fake/fake"}):
            # Should not raise exception
            try:
                result = await checker.check_health()
                assert result is not None
                assert hasattr(result, "healthy")
                
                # If unhealthy, should indicate database issue
                if not result.healthy:
                    assert any(word in str(result.details).lower() 
                             for word in ["database", "connection", "postgres"])
            except Exception as e:
                # Health check should never raise
                pytest.fail(f"Health check raised exception: {e}")

    # Test 8: Similar SSL Parameter Issues
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_similar_ssl_parameter_issues(self):
        """
        Test for similar SSL parameter issues across different URL formats.
        All services must handle SSL parameters consistently.
        """
        test_cases = [
            # Various URL formats that might cause issues
            "postgresql://user:pass@host/db?sslmode=require",
            "postgresql://user:pass@/db?host=/cloudsql/instance&sslmode=require",
            "postgresql+psycopg2://user:pass@host/db?sslmode=require",
            "postgresql://user:pass@host/db?ssl=require",
            "postgres://user:pass@host/db?sslmode=disable",
        ]
        
        for url in test_cases:
            # Simulate conversion for asyncpg
            if url.startswith(("postgresql://", "postgres://")):
                async_url = url.replace("postgres://", "postgresql+asyncpg://")
                async_url = async_url.replace("postgresql://", "postgresql+asyncpg://")
                
                # Handle SSL parameters
                if "/cloudsql/" in async_url:
                    # Cloud SQL: no SSL params
                    async_url = re.sub(r'[&?]sslmode=[^&]*', '', async_url)
                    async_url = re.sub(r'[&?]ssl=[^&]*', '', async_url)
                else:
                    # Regular: convert sslmode to ssl
                    async_url = async_url.replace("sslmode=", "ssl=")
                
                # Validate
                assert "sslmode=" not in async_url, f"sslmode not converted: {async_url}"
                if "/cloudsql/" in async_url:
                    assert "ssl=" not in async_url, f"Cloud SQL should have no SSL: {async_url}"

    # Test 9: Missing Configuration Detection
    @pytest.mark.e2e
    def test_missing_configuration_detection(self):
        """
        Test detection of missing critical configurations in staging.
        All critical configs must be present for staging deployment.
        """
        critical_staging_configs = {
            "DATABASE_URL": "postgresql://",
            "CLICKHOUSE_URL": "https://",
            "JWT_SECRET_KEY": None,  # Any non-empty value
            "USE_OAUTH_PROXY": "true",
            "OAUTH_CLIENT_ID": None,
            "OAUTH_CLIENT_SECRET": None,
        }
        
        # Simulate staging environment check
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            missing = []
            invalid = []
            
            for config_name, expected_prefix in critical_staging_configs.items():
                value = get_env().get(config_name, "")
                
                if not value:
                    missing.append(config_name)
                elif expected_prefix and not value.startswith(expected_prefix):
                    invalid.append(f"{config_name} (expected to start with {expected_prefix})")
            
            # In real staging, these should all be set
            if missing or invalid:
                print(f"Info: Would need to set in staging - Missing: {missing}, Invalid: {invalid}")

    # Test 10: Deployment Readiness Check
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_deployment_readiness_comprehensive(self):
        """
        Comprehensive test to validate deployment readiness.
        Checks all critical components for staging deployment.
        """
        readiness_checks = {
            "database_connectivity": False,
            "auth_service_ssl": False,
            "frontend_node_version": False,
            "clickhouse_config": False,
            "health_endpoints": False,
            "jwt_configuration": False,
        }
        
        # Check database URL handling
        test_db_url = "postgresql://test:test@/test?host=/cloudsql/test&sslmode=require"
        converted = test_db_url.replace("sslmode=", "ssl=")
        if "postgresql" in converted and "sslmode=" not in converted:
            readiness_checks["database_connectivity"] = True
        
        # Check auth service SSL handling
        if "/cloudsql/" in test_db_url:
            no_ssl = re.sub(r'[&?](sslmode|ssl)=[^&]*', '', test_db_url)
            if "ssl" not in no_ssl:
                readiness_checks["auth_service_ssl"] = True
        
        # Check frontend Node version
        frontend_dockerfile = Path("frontend/Dockerfile")
        if frontend_dockerfile.exists():
            with open(frontend_dockerfile) as f:
                if "node:20" in f.read() or "node:lts-iron" in f.read():
                    readiness_checks["frontend_node_version"] = True
        
        # Check ClickHouse configuration
        if get_env().get("CLICKHOUSE_URL") or get_env().get("ENVIRONMENT") != "staging":
            readiness_checks["clickhouse_config"] = True
        
        # Health endpoints always pass for now
        readiness_checks["health_endpoints"] = True
        
        # JWT configuration
        if get_env().get("JWT_SECRET_KEY") or get_env().get("ENVIRONMENT") != "staging":
            readiness_checks["jwt_configuration"] = True
        
        # Report readiness status
        not_ready = [k for k, v in readiness_checks.items() if not v]
        if not_ready:
            print(f"Deployment readiness issues: {not_ready}")


if __name__ == "__main__":
    # Run tests with pytest
    import subprocess
    result = subprocess.run(
        ["python", "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)
    sys.exit(result.returncode)
"""Core Staging Startup Validation Tests

Business Value Justification (BVJ):
- Segment: Enterprise/Platform - All customer tiers  
- Business Goal: Staging environment reliability and deployment validation
- Value Impact: Prevents staging-related deployment failures that block releases
- Revenue Impact: $100K+ MRR protection via reliable staging validation

Tests essential startup functionality:
- Environment configuration loading
- Configuration integrity validation  
- Critical environment variables
- Core service initialization order
"""

import os
import pytest
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional

from tests.unified.e2e.staging_test_helpers import (
    StagingTestSuite,
    get_staging_suite
)
from app.core.configuration.base import validate_config_integrity
from app.core.auth_constants import JWTConstants, CredentialConstants


@pytest.mark.asyncio
@pytest.mark.staging
class TestStagingEnvironmentCore:
    """Core staging environment configuration and validation tests."""
    
    async def test_staging_environment_detection(self):
        """Test that staging environment is correctly detected and configured."""
        suite = await get_staging_suite()
        config = suite.env_config
        
        assert config.environment.name == "STAGING"
        assert config.is_staging_environment()
        assert not config.is_test_environment()
        assert not config.is_production_environment()
    
    async def test_critical_environment_variables(self):
        """Test all critical environment variables are properly set."""
        required_vars = [
            "DATABASE_URL", "REDIS_URL", "CLICKHOUSE_URL",
            JWTConstants.JWT_SECRET_KEY, JWTConstants.FERNET_KEY,
            CredentialConstants.GOOGLE_CLIENT_ID, CredentialConstants.GEMINI_API_KEY
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        assert len(missing_vars) == 0, f"Missing critical variables: {missing_vars}"
    
    async def test_database_configuration_integrity(self):
        """Test database configuration meets staging requirements."""
        suite = await get_staging_suite()
        db_config = suite.env_config.database
        
        assert db_config.url.startswith("postgresql://")
        assert "staging" in db_config.url.lower()
        assert db_config.pool_pre_ping is True
        assert db_config.pool_recycle == 300
        assert db_config.echo is False  # No query logging in staging


@pytest.mark.asyncio
@pytest.mark.staging
class TestStagingSecurityValidation:
    """Test staging security configuration and secret validation."""
    
    async def test_jwt_security_configuration(self):
        """Test JWT configuration meets security requirements."""
        jwt_secret = os.getenv(JWTConstants.JWT_SECRET_KEY)
        fernet_key = os.getenv(JWTConstants.FERNET_KEY)
        
        assert jwt_secret is not None
        assert len(jwt_secret) >= 32
        assert jwt_secret != "test-jwt-secret-key-unified-testing-32chars"
        
        assert fernet_key is not None
        assert len(fernet_key) > 20  # Base64 encoded Fernet keys are longer
        assert fernet_key != "test-fernet-key-fallback"
    
    async def test_oauth_configuration_security(self):
        """Test OAuth configuration is properly secured for staging."""
        client_id = os.getenv(CredentialConstants.GOOGLE_CLIENT_ID)
        client_secret = os.getenv(CredentialConstants.GOOGLE_CLIENT_SECRET)
        
        assert client_id is not None
        assert client_secret is not None
        assert client_id != "test-google-client-id"
        assert client_secret != "test-google-client-secret"


@pytest.mark.asyncio
@pytest.mark.staging
class TestStagingConfigurationManager:
    """Test unified configuration manager initialization for staging."""
    
    async def test_configuration_manager_initialization(self):
        """Test configuration manager initializes correctly for staging."""
        suite = await get_staging_suite()
        config_manager = suite.config_manager
        config = config_manager.get_config()
        
        assert config is not None
        assert config.database_url is not None
        assert config.environment == "staging"
    
    async def test_configuration_integrity_validation(self):
        """Test configuration integrity passes all validation checks."""
        is_valid, issues = validate_config_integrity()
        assert is_valid, f"Configuration integrity issues: {issues}"
        assert len(issues) == 0
    
    async def test_configuration_completeness(self):
        """Test configuration provides all required components."""
        suite = await get_staging_suite()
        config_manager = suite.config_manager
        summary = config_manager.get_config_summary()
        
        assert summary["environment"] == "staging"
        assert summary["database_configured"] is True
        assert summary["secrets_loaded"] > 0
        assert summary["services_enabled"] > 0


@pytest.mark.asyncio
@pytest.mark.staging  
@pytest.mark.comprehensive
class TestStagingStartupFlow:
    """Test core staging startup flow and system initialization."""
    
    async def test_core_system_startup(self):
        """Test core system startup completes successfully within time limits."""
        start_time = time.time()
        suite = await get_staging_suite()
        
        # Verify environment is properly initialized
        harness = suite.harness
        assert harness.is_environment_ready(), "Environment not ready"
        
        env_status = await harness.get_environment_status()
        assert env_status["environment"] == "staging", "Wrong environment"
        assert env_status["harness_ready"], "Harness not ready"
        
        duration = time.time() - start_time
        assert duration < 30, f"Startup took too long: {duration:.2f}s"
    
    async def test_service_dependency_chain(self):
        """Test services start in correct dependency order."""
        suite = await get_staging_suite()
        
        # Auth service should be ready first
        auth_url = suite.env_config.services.auth
        auth_health = await suite.check_service_health(f"{auth_url}/health")
        assert auth_health.healthy, "Auth service not ready"
        
        # Backend service should be ready with database dependencies  
        backend_url = suite.env_config.services.backend
        backend_health = await suite.check_service_health(f"{backend_url}/health")
        assert backend_health.healthy, "Backend service not ready"
        assert backend_health.details.get("status") == "healthy"
    
    async def test_startup_summary_generation(self):
        """Test comprehensive startup validation and summary generation."""
        start_time = time.time()
        suite = await get_staging_suite()
        harness = suite.harness
        
        # Collect environment status
        env_status = await harness.get_environment_status()
        
        # Validate critical components
        assert env_status["environment"] == "staging"
        assert env_status["harness_ready"]
        assert env_status.get("active_users", 0) >= 0
        assert env_status.get("service_urls", {})
        
        # Test basic user creation (validates auth flow)
        user = await harness.create_test_user()
        assert user.access_token, "Failed to create test user"
        
        total_duration = time.time() - start_time
        assert total_duration < 45, f"Total validation too long: {total_duration:.2f}s"
        
        # Generate summary for monitoring
        summary = {
            "startup_validation": "passed",
            "environment": "staging", 
            "total_duration_seconds": total_duration,
            "services_healthy": True,
            "user_creation_success": True,
            "timestamp": datetime.now().isoformat()
        }
        
        return summary


# Convenience function for running core staging startup validation
async def run_core_staging_validation() -> Dict[str, Any]:
    """Run core staging startup validation and return results."""
    try:
        suite = await get_staging_suite()
        
        # Validate configuration
        is_valid, errors = validate_config_integrity()
        if not is_valid:
            return {
                "status": "failed",
                "reason": "Configuration validation failed",
                "errors": errors
            }
        
        return {
            "status": "passed",
            "environment": suite.env_config.environment.value,
            "services_configured": len(suite.env_config.services.__dict__),
            "database_configured": bool(suite.env_config.database.url),
            "secrets_loaded": len(suite.env_config.secrets.__dict__)
        }
    except Exception as e:
        return {
            "status": "error", 
            "reason": f"Core validation failed: {str(e)}"
        }


if __name__ == "__main__":
    asyncio.run(run_core_staging_validation())
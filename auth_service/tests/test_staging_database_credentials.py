"""Test Auth Service Staging Database Credentials
Tests that validate database credential configuration for staging environment.

CRITICAL VALIDATION FOR STAGING:
1. Correct database credentials are loaded from environment
2. Staging-specific DATABASE_URL format is valid  
3. Cloud SQL proxy configuration compatibility
4. Credential validation before deployment
5. No invalid user patterns like 'user_pr-4'

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent staging deployment failures due to credential issues
- Value Impact: Ensures auth service can connect to staging database successfully  
- Strategic Impact: Prevents auth service downtime that affects all customer authentication
"""

import os
import pytest
import asyncio
import logging
from unittest.mock import patch, MagicMock
from urllib.parse import urlparse

from auth_service.auth_core.database.database_manager import AuthDatabaseManager
from auth_service.auth_core.database.staging_validation import StagingDatabaseValidator
from auth_service.auth_core.isolated_environment import get_env, IsolatedEnvironment
from auth_service.auth_core.config import AuthConfig
from test_framework.environment_markers import env

logger = logging.getLogger(__name__)


class TestStagingDatabaseCredentials:
    """Test suite for staging database credential validation."""
    
    def test_staging_database_url_credential_format_validation(self):
        """FAILING TEST: Validates staging DATABASE_URL has correct credential format.
        
        This test ensures the staging DATABASE_URL contains valid credentials 
        and not problematic patterns like 'user_pr-4' found in production logs.
        """
        # Simulate staging environment configuration
        staging_env = {
            "ENVIRONMENT": "staging",
            "DATABASE_URL": "postgresql://postgres:correct_password@/netra_staging?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres"
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            with patch.object(get_env(), 'get') as mock_env_get:
                def mock_get(key, default=None):
                    return staging_env.get(key, default)
                mock_env_get.side_effect = mock_get
                
                # Get the database URL through IsolatedEnvironment
                database_url = get_env().get("DATABASE_URL")
                
                # Validate credential format using StagingDatabaseValidator
                credential_validation = StagingDatabaseValidator.validate_credentials_format(database_url)
                
                # This should pass with correct credentials
                assert credential_validation["valid"], f"Credential validation failed: {credential_validation}"
                
                # Verify no critical credential issues
                assert not credential_validation.get("credential_issues", []), \
                    f"Critical credential issues found: {credential_validation.get('credential_issues')}"
                
                # Parse URL to validate specific credential components
                parsed = urlparse(database_url)
                
                # Ensure username is not problematic patterns from logs
                assert parsed.username != "user_pr-4", "Invalid username pattern 'user_pr-4' found in staging URL"
                assert parsed.username == "postgres", f"Expected 'postgres' username, got '{parsed.username}'"
                
                # Ensure password is not placeholder or weak
                assert parsed.password is not None, "Password is missing from staging DATABASE_URL"
                assert parsed.password != "wrong_password", "Staging URL contains placeholder password"
                assert len(parsed.password) >= 8, "Staging password is too short"
    
    def test_staging_database_url_validation_with_invalid_user_pr4(self):
        """FAILING TEST: Detects invalid 'user_pr-4' credential pattern.
        
        This test replicates the exact credential error found in production logs
        where the auth service attempted to connect with username 'user_pr-4'.
        """
        # Simulate the problematic staging configuration from logs
        invalid_staging_env = {
            "ENVIRONMENT": "staging",
            "DATABASE_URL": "postgresql://user_pr-4:some_password@/netra_staging?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres"
        }
        
        with patch.dict(os.environ, invalid_staging_env, clear=True):
            with patch.object(get_env(), 'get') as mock_env_get:
                def mock_get(key, default=None):
                    return invalid_staging_env.get(key, default)
                mock_env_get.side_effect = mock_get
                
                database_url = get_env().get("DATABASE_URL")
                
                # Parse the URL to check for the problematic pattern
                parsed = urlparse(database_url)
                
                # This test should detect and fail on the invalid user pattern
                if parsed.username == "user_pr-4":
                    pytest.fail(f"DETECTED INVALID USER PATTERN: Found 'user_pr-4' in staging DATABASE_URL. "
                              f"This will cause 'password authentication failed for user user_pr-4' errors.")
                
                # Also validate through StagingDatabaseValidator
                credential_validation = StagingDatabaseValidator.validate_credentials_format(database_url)
                
                # Should detect credential issues with this pattern
                if "user_pr-4" in database_url:
                    assert not credential_validation["valid"] or credential_validation.get("warnings"), \
                        "StagingDatabaseValidator should detect problematic 'user_pr-4' pattern"
    
    def test_staging_database_url_validation_with_incorrect_postgres_password(self):
        """FAILING TEST: Detects incorrect postgres user password.
        
        This test replicates the 'password authentication failed for user postgres' 
        error by validating password format and strength requirements.
        """
        # Test various invalid password scenarios
        invalid_password_scenarios = [
            ("postgresql://postgres:@/netra_staging?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres", "empty password"),
            ("postgresql://postgres:password@/netra_staging?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres", "default password"),
            ("postgresql://postgres:123@/netra_staging?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres", "weak password"),
            ("postgresql://postgres:wrong_password@/netra_staging?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres", "placeholder password")
        ]
        
        for invalid_url, error_description in invalid_password_scenarios:
            staging_env = {
                "ENVIRONMENT": "staging",
                "DATABASE_URL": invalid_url
            }
            
            with patch.dict(os.environ, staging_env, clear=True):
                with patch.object(get_env(), 'get') as mock_env_get:
                    def mock_get(key, default=None):
                        return staging_env.get(key, default)
                    mock_env_get.side_effect = mock_get
                    
                    database_url = get_env().get("DATABASE_URL")
                    
                    # Validate credentials using StagingDatabaseValidator
                    credential_validation = StagingDatabaseValidator.validate_credentials_format(database_url)
                    
                    # These scenarios should be detected as problematic
                    if not credential_validation["valid"] or credential_validation.get("credential_issues"):
                        logger.warning(f"Correctly detected credential issue: {error_description}")
                        assert True  # Expected behavior
                    else:
                        # If not detected, this is a validation gap that needs fixing
                        pytest.fail(f"StagingDatabaseValidator failed to detect credential issue: {error_description}")
    
    def test_staging_environment_credential_loading_through_isolated_environment(self):
        """FAILING TEST: Validates credential loading through IsolatedEnvironment.
        
        This test ensures that staging credentials are properly loaded through 
        the IsolatedEnvironment system and not through direct os.environ access.
        """
        # Set up staging environment variables
        staging_credentials = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "34.132.142.103",  # Actual staging IP from learnings
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "netra_staging",
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": "staging_secure_password_123",
            "DATABASE_URL": ""  # Force building from components
        }
        
        with patch.dict(os.environ, staging_credentials, clear=True):
            # Create fresh IsolatedEnvironment instance
            isolated_env = IsolatedEnvironment()
            
            with patch.object(isolated_env, 'get') as mock_get:
                def mock_get(key, default=None):
                    return staging_credentials.get(key, default)
                mock_get.side_effect = mock_get
                
                # Validate that all required credentials are accessible
                required_vars = ["POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", 
                               "POSTGRES_USER", "POSTGRES_PASSWORD"]
                
                missing_vars = []
                for var in required_vars:
                    value = isolated_env.get(var)
                    if not value:
                        missing_vars.append(var)
                
                # This should fail if any required credentials are missing
                if missing_vars:
                    pytest.fail(f"Missing required staging credentials: {missing_vars}")
                
                # Validate credential values are staging-appropriate
                postgres_host = isolated_env.get("POSTGRES_HOST")
                postgres_user = isolated_env.get("POSTGRES_USER")
                postgres_password = isolated_env.get("POSTGRES_PASSWORD")
                
                # Staging should use external IP, not localhost
                assert postgres_host != "localhost", "Staging should not use localhost for database host"
                
                # Should use proper postgres user, not problematic patterns
                assert postgres_user == "postgres", f"Expected 'postgres' user, got '{postgres_user}'"
                
                # Password should meet minimum security requirements  
                assert postgres_password and len(postgres_password) >= 8, \
                    "Staging password must be at least 8 characters"
    
    def test_staging_database_url_format_validation_for_cloud_sql(self):
        """FAILING TEST: Validates DATABASE_URL format for Cloud SQL compatibility.
        
        This test ensures the DATABASE_URL is formatted correctly for Cloud SQL proxy
        connections as expected in staging environment.
        """
        # Test correct Cloud SQL format
        correct_cloud_sql_url = "postgresql://postgres:secure_password@/netra_staging?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres"
        
        staging_env = {
            "ENVIRONMENT": "staging", 
            "DATABASE_URL": correct_cloud_sql_url
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            with patch.object(get_env(), 'get') as mock_env_get:
                def mock_get(key, default=None):
                    return staging_env.get(key, default)
                mock_env_get.side_effect = mock_get
                
                database_url = get_env().get("DATABASE_URL")
                
                # Validate URL format using StagingDatabaseValidator
                url_validation = StagingDatabaseValidator.validate_database_url_format(database_url)
                
                # Should pass format validation
                assert url_validation["valid"], f"URL format validation failed: {url_validation.get('error')}"
                
                # Should be detected as Cloud SQL type
                assert url_validation["url_type"] == "cloud_sql", \
                    f"Expected 'cloud_sql' type, got '{url_validation['url_type']}'"
                
                # Verify Cloud SQL specific requirements
                assert "/cloudsql/" in database_url, "Cloud SQL URL must contain /cloudsql/ path"
                assert "netra-staging:us-central1:staging-shared-postgres" in database_url, \
                    "URL must contain correct Cloud SQL connection name"
    
    def test_staging_database_url_format_validation_with_invalid_patterns(self):
        """FAILING TEST: Detects invalid URL patterns that cause staging failures.
        
        This test validates against known problematic URL patterns that cause
        connection failures in staging environment.
        """
        # Test various invalid staging URL patterns
        invalid_staging_patterns = [
            # localhost instead of Cloud SQL
            ("postgresql://postgres:password@localhost:5432/netra_staging", "localhost in staging URL"),
            
            # Missing Cloud SQL path
            ("postgresql://postgres:password@34.132.142.103:5432/netra_staging", "missing Cloud SQL path"),
            
            # Wrong Cloud SQL connection name
            ("postgresql://postgres:password@/netra_staging?host=/cloudsql/wrong-project:region:instance", "wrong connection name"),
            
            # Invalid user pattern from logs
            ("postgresql://user_pr-4:password@/netra_staging?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres", "invalid user pattern"),
            
            # SSL parameters that shouldn't be in Cloud SQL URLs
            ("postgresql://postgres:password@/netra_staging?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres&sslmode=require", "SSL parameters in Cloud SQL URL")
        ]
        
        for invalid_url, error_description in invalid_staging_patterns:
            staging_env = {
                "ENVIRONMENT": "staging",
                "DATABASE_URL": invalid_url
            }
            
            with patch.dict(os.environ, staging_env, clear=True):
                with patch.object(get_env(), 'get') as mock_env_get:
                    def mock_get(key, default=None):
                        return staging_env.get(key, default)
                    mock_env_get.side_effect = mock_get
                    
                    database_url = get_env().get("DATABASE_URL")
                    
                    # Validate URL format
                    url_validation = StagingDatabaseValidator.validate_database_url_format(database_url)
                    credential_validation = StagingDatabaseValidator.validate_credentials_format(database_url)
                    
                    # Should detect issues with these patterns
                    has_issues = (not url_validation["valid"] or 
                                url_validation.get("warnings") or
                                not credential_validation["valid"] or
                                credential_validation.get("credential_issues"))
                    
                    if not has_issues:
                        pytest.fail(f"Failed to detect staging URL issue: {error_description}")
                    
                    logger.info(f"Correctly detected staging URL issue: {error_description}")
    
    def test_auth_database_manager_staging_readiness_validation(self):
        """FAILING TEST: Validates AuthDatabaseManager.validate_staging_readiness().
        
        This test ensures the database manager properly validates staging deployment
        readiness, including credential and configuration checks.
        """
        # Test with correct staging configuration
        correct_staging_env = {
            "ENVIRONMENT": "staging",
            "DATABASE_URL": "postgresql://postgres:secure_staging_password@/netra_staging?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres"
        }
        
        with patch.dict(os.environ, correct_staging_env, clear=True):
            with patch.object(get_env(), 'get') as mock_env_get:
                def mock_get(key, default=None):
                    return correct_staging_env.get(key, default)
                mock_env_get.side_effect = mock_get
                
                # This should pass validation
                is_ready = AuthDatabaseManager.validate_staging_readiness()
                assert is_ready, "AuthDatabaseManager should validate staging readiness with correct configuration"
        
        # Test with problematic staging configuration
        problematic_staging_env = {
            "ENVIRONMENT": "staging",
            "DATABASE_URL": "postgresql://user_pr-4:wrong_password@localhost:5432/netra_staging"  # Multiple issues
        }
        
        with patch.dict(os.environ, problematic_staging_env, clear=True):
            with patch.object(get_env(), 'get') as mock_env_get:
                def mock_get(key, default=None):
                    return problematic_staging_env.get(key, default)
                mock_env_get.side_effect = mock_get
                
                # This should fail validation
                is_ready = AuthDatabaseManager.validate_staging_readiness()
                assert not is_ready, "AuthDatabaseManager should detect problematic staging configuration"
    
    def test_comprehensive_pre_deployment_validation(self):
        """FAILING TEST: Comprehensive pre-deployment validation for staging.
        
        This test performs complete validation that should be run before any
        staging deployment to catch credential and configuration issues early.
        """
        # Test data representing different staging deployment scenarios
        test_scenarios = [
            {
                "name": "valid_staging_config",
                "env": {
                    "ENVIRONMENT": "staging",
                    "DATABASE_URL": "postgresql://postgres:secure_password_123@/netra_staging?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres"
                },
                "should_pass": True
            },
            {
                "name": "invalid_user_pattern",
                "env": {
                    "ENVIRONMENT": "staging", 
                    "DATABASE_URL": "postgresql://user_pr-4:password@/netra_staging?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres"
                },
                "should_pass": False
            },
            {
                "name": "localhost_in_staging",
                "env": {
                    "ENVIRONMENT": "staging",
                    "DATABASE_URL": "postgresql://postgres:password@localhost:5432/netra_staging"
                },
                "should_pass": False
            },
            {
                "name": "weak_password",
                "env": {
                    "ENVIRONMENT": "staging",
                    "DATABASE_URL": "postgresql://postgres:123@/netra_staging?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres"
                },
                "should_pass": False
            }
        ]
        
        validation_failures = []
        
        for scenario in test_scenarios:
            with patch.dict(os.environ, scenario["env"], clear=True):
                with patch.object(get_env(), 'get') as mock_env_get:
                    def mock_get(key, default=None):
                        return scenario["env"].get(key, default)
                    mock_env_get.side_effect = mock_get
                    
                    # Run comprehensive validation
                    report = StagingDatabaseValidator.pre_deployment_validation()
                    
                    # Check if validation result matches expectation
                    passed_validation = report["overall_status"] in ["passed", "warning"]
                    
                    if passed_validation != scenario["should_pass"]:
                        validation_failures.append({
                            "scenario": scenario["name"],
                            "expected_pass": scenario["should_pass"],
                            "actual_pass": passed_validation,
                            "report": report
                        })
        
        # Report validation failures
        if validation_failures:
            failure_details = "\n".join([
                f"Scenario '{f['scenario']}': Expected pass={f['expected_pass']}, Actual pass={f['actual_pass']}"
                for f in validation_failures
            ])
            pytest.fail(f"Pre-deployment validation failures:\n{failure_details}")


class TestStagingCredentialIntegration:
    """Integration tests for staging credential validation."""
    
    @pytest.mark.asyncio
    async def test_staging_database_connection_with_valid_credentials(self):
        """INTEGRATION TEST: Test actual database connection with staging-like credentials.
        
        This test validates that properly configured staging credentials would
        allow successful database connection (mocked for testing).
        """
        # Mock staging configuration
        staging_config = {
            "ENVIRONMENT": "staging",
            "DATABASE_URL": "postgresql+asyncpg://postgres:test_staging_password@/test_db?host=/cloudsql/test:region:instance"
        }
        
        with patch.dict(os.environ, staging_config, clear=True):
            with patch.object(get_env(), 'get') as mock_env_get:
                def mock_get(key, default=None):
                    return staging_config.get(key, default)
                mock_env_get.side_effect = mock_get
                
                # Mock successful engine creation for valid credentials
                with patch('auth_service.auth_core.database.database_manager.create_async_engine') as mock_create_engine:
                    mock_engine = MagicMock()
                    mock_create_engine.return_value = mock_engine
                    
                    # This should succeed with proper credentials
                    try:
                        database_url = AuthDatabaseManager.get_auth_database_url_async()
                        engine = AuthDatabaseManager.create_async_engine(database_url)
                        assert engine is not None, "Engine creation should succeed with valid staging credentials"
                        
                    except Exception as e:
                        pytest.fail(f"Valid staging credentials should not cause connection failure: {e}")
    
    @pytest.mark.asyncio  
    async def test_staging_database_connection_with_invalid_credentials(self):
        """INTEGRATION TEST: Test database connection failure with invalid credentials.
        
        This test validates that invalid staging credentials properly fail
        connection attempts with appropriate error messages.
        """
        # Mock invalid staging configuration (the problematic patterns from logs)
        invalid_staging_config = {
            "ENVIRONMENT": "staging",
            "DATABASE_URL": "postgresql+asyncpg://user_pr-4:wrong_password@/test_db?host=/cloudsql/test:region:instance"
        }
        
        with patch.dict(os.environ, invalid_staging_config, clear=True):
            with patch.object(get_env(), 'get') as mock_env_get:
                def mock_get(key, default=None):
                    return invalid_staging_config.get(key, default)
                mock_env_get.side_effect = mock_get
                
                # Mock authentication failure for invalid credentials  
                with patch('auth_service.auth_core.database.database_manager.create_async_engine') as mock_create_engine:
                    # Simulate the exact error from production logs
                    auth_error = RuntimeError("password authentication failed for user 'user_pr-4'")
                    mock_create_engine.side_effect = auth_error
                    
                    # This should fail with authentication error
                    with pytest.raises(RuntimeError) as exc_info:
                        database_url = AuthDatabaseManager.get_auth_database_url_async()
                        AuthDatabaseManager.create_async_engine(database_url)
                    
                    # Verify the error message matches production logs
                    error_message = str(exc_info.value)
                    assert "password authentication failed" in error_message, \
                        f"Expected authentication error, got: {error_message}"


# Mark all tests in this module for integration testing
pytestmark = pytest.mark.integration
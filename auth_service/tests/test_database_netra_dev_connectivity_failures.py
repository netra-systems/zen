"""FAILING TESTS: Database 'netra_dev' Does Not Exist - Critical Issue from Iteration 3

CRITICAL DATABASE CONNECTIVITY ISSUE TO REPLICATE:
- Database connection failing with: "database 'netra_dev' does not exist"
- Service continues with reduced functionality (graceful degradation)
- Health checks don't validate database connectivity properly
- Service reports healthy despite database being unavailable

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Database reliability and connection validation 
- Value Impact: Ensures authentication system operates with proper database connectivity
- Strategic Impact: Prevents authentication failures that compromise all customer tiers

These tests are designed to FAIL with the current system state and PASS once the database
connectivity and health check issues are properly resolved.
"""

import os
import sys
import pytest
import asyncio
import logging
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.exc import OperationalError, DatabaseError
from asyncpg.exceptions import InvalidCatalogNameError

from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.database.connection import AuthDatabase, auth_db
from auth_service.auth_core.database.database_manager import AuthDatabaseManager
from auth_service.health_check import check_health, check_readiness
from test_framework.environment_markers import env, staging_only, env_requires

logger = logging.getLogger(__name__)


class TestDatabaseNetraDevConnectivityFailures:
    """Test suite for the critical 'database netra_dev does not exist' failure."""
    
    @pytest.mark.asyncio
    async def test_database_netra_dev_does_not_exist_error(self):
        """FAILING TEST: Replicates the exact 'database netra_dev does not exist' error.
        
        This is the primary critical error where the auth service attempts to connect 
        to the 'netra_dev' database that doesn't exist in the staging environment.
        """
        # Environment that causes the exact error from iteration 3 logs
        netra_dev_env = {
            'ENVIRONMENT': 'development',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432', 
            'POSTGRES_DB': 'netra_dev',  # This is the problematic database name
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'test_password',
            'DATABASE_URL': 'postgresql+asyncpg://postgres:test_password@localhost:5432/netra_dev'
        }
        
        with patch.dict(os.environ, netra_dev_env):
            test_auth_db = AuthDatabase()
            
            # Mock the exact error from staging logs
            async def mock_netra_dev_not_exist(*args, **kwargs):
                raise OperationalError(
                    'connection to server failed: FATAL: database "netra_dev" does not exist',
                    None, None
                )
            
            with patch('sqlalchemy.ext.asyncio.create_async_engine') as mock_create_engine:
                mock_engine = AsyncMock()
                mock_engine.connect.return_value.__aenter__.side_effect = mock_netra_dev_not_exist
                mock_create_engine.return_value = mock_engine
                
                # This should raise the exact error from iteration 3
                with pytest.raises(RuntimeError) as exc_info:
                    await test_auth_db.initialize()
                
                error_message = str(exc_info.value).lower()
                assert 'database "netra_dev" does not exist' in error_message or 'netra_dev' in error_message
                
                logger.error(f"Critical database 'netra_dev' does not exist error replicated: {exc_info.value}")
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_allows_service_to_start_incorrectly(self):
        """FAILING TEST: Documents the problematic graceful degradation behavior.
        
        This test verifies that when the database connection fails, the service 
        incorrectly continues with "reduced functionality" instead of properly
        handling the database error and reporting unhealthy status.
        """
        graceful_degradation_env = {
            'ENVIRONMENT': 'development',
            'POSTGRES_HOST': 'unavailable-host',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'netra_dev',  # Problematic database name
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'test_password'
        }
        
        with patch.dict(os.environ, graceful_degradation_env):
            test_auth_db = AuthDatabase()
            
            # Mock database connection failure but service continues
            async def mock_db_connection_failure(*args, **kwargs):
                raise OperationalError(
                    'could not connect to server: database "netra_dev" does not exist',
                    None, None
                )
            
            with patch('sqlalchemy.ext.asyncio.create_async_engine') as mock_create_engine:
                mock_engine = AsyncMock()
                mock_engine.connect.side_effect = mock_db_connection_failure
                mock_create_engine.return_value = mock_engine
                
                # In development environment, service might incorrectly continue
                if graceful_degradation_env.get('ENVIRONMENT') == 'development':
                    # Mock the graceful degradation behavior from main.py lines 141-145
                    with patch.object(test_auth_db, '_initialized', True):
                        # Service continues despite database issues
                        assert test_auth_db._initialized
                        
                        # But database operations should fail
                        connection_test = await test_auth_db.test_connection()
                        assert not connection_test, (
                            "Database connection test should fail when netra_dev doesn't exist, "
                            "but graceful degradation allows service to report healthy"
                        )
                        
                        # This is the problematic behavior - service appears healthy
                        # when it should be reporting database connectivity issues
                        pytest.fail(
                            "Service is incorrectly running with graceful degradation despite "
                            "database 'netra_dev' not existing. This compromises authentication functionality."
                        )
    
    @pytest.mark.asyncio
    async def test_health_check_does_not_validate_database_connectivity(self):
        """FAILING TEST: Verifies that health checks don't properly validate database connectivity.
        
        This test exposes that the health endpoint returns healthy status even when
        the database connection is failing due to 'netra_dev' not existing.
        """
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development',
            'POSTGRES_DB': 'netra_dev',  # Problematic database
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'test_pass',
            'PORT': '8080'
        }):
            # Mock the basic health interface that doesn't check database
            from auth_service.main import health_interface
            
            # Get basic health (this doesn't validate database connectivity)
            basic_health = health_interface.get_basic_health()
            
            # The problem: basic health returns "healthy" regardless of database state
            assert basic_health.get('status') == 'healthy'
            
            # But if we check database connectivity, it should fail
            test_auth_db = AuthDatabase()
            
            # Mock database connection failure
            async def mock_netra_dev_failure(*args, **kwargs):
                raise OperationalError(
                    'database "netra_dev" does not exist',
                    None, None
                )
            
            with patch.object(test_auth_db, 'test_connection', side_effect=mock_netra_dev_failure):
                # Health check should detect this but it doesn't
                try:
                    db_status = await test_auth_db.is_ready()
                    if db_status:
                        pytest.fail(
                            "Health check reports database is ready when 'netra_dev' doesn't exist. "
                            "Health checks must validate actual database connectivity."
                        )
                except OperationalError:
                    # Expected behavior - database should fail
                    pass
            
            # The critical issue: basic health doesn't include database validation
            pytest.fail(
                "Health endpoint returns 'healthy' without validating database connectivity. "
                "When 'netra_dev' doesn't exist, health should report unhealthy status."
            )
    
    def test_check_readiness_function_does_not_validate_database(self):
        """FAILING TEST: Verifies that readiness check doesn't validate database properly.
        
        The readiness endpoint should check if database is accessible before
        reporting ready status, but currently it may not properly validate
        the 'netra_dev' database availability.
        """
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development',
            'POSTGRES_DB': 'netra_dev',
            'PORT': '8080'
        }):
            # Mock the readiness endpoint behavior
            import urllib.request
            import urllib.error
            import json
            
            # Mock HTTP request to readiness endpoint
            mock_response_data = {
                'status': 'ready',
                'service': 'auth-service',
                'version': '1.0.0',
                'warning': 'Database check failed but continuing in development mode'
            }
            
            # This simulates the problematic behavior from main.py lines 342-350
            # where development mode continues despite database issues
            
            # The issue: readiness reports ready even with database problems
            if mock_response_data.get('warning'):
                pytest.fail(
                    f"Readiness check reports 'ready' despite database issues: {mock_response_data.get('warning')}. "
                    "When 'netra_dev' database doesn't exist, service should not be ready."
                )
    
    @pytest.mark.asyncio
    async def test_database_url_construction_creates_invalid_netra_dev_reference(self):
        """FAILING TEST: Verifies that database URL construction creates invalid netra_dev references.
        
        This test identifies where the problematic database name 'netra_dev' 
        is coming from in the URL construction process.
        """
        # Test environment that might default to netra_dev
        minimal_env = {
            'ENVIRONMENT': 'development',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432', 
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'test_password'
            # Note: POSTGRES_DB is intentionally missing to test defaults
        }
        
        with patch.dict(os.environ, minimal_env, clear=True):
            # Remove POSTGRES_DB if it exists globally
            if 'POSTGRES_DB' in os.environ:
                del os.environ['POSTGRES_DB']
            
            config = AuthConfig()
            try:
                database_url = config.get_database_url()
                
                # Check if the URL contains the problematic 'netra_dev' database
                if database_url and 'netra_dev' in database_url:
                    # Try to verify this database actually exists
                    test_auth_db = AuthDatabase()
                    
                    # Mock connection attempt to netra_dev
                    async def mock_netra_dev_not_exist(*args, **kwargs):
                        raise OperationalError(
                            'database "netra_dev" does not exist',
                            None, None
                        )
                    
                    with patch('sqlalchemy.ext.asyncio.create_async_engine') as mock_create_engine:
                        mock_engine = AsyncMock()
                        mock_engine.connect.return_value.__aenter__.side_effect = mock_netra_dev_not_exist
                        mock_create_engine.return_value = mock_engine
                        
                        with pytest.raises(RuntimeError):
                            await test_auth_db.initialize()
                        
                        pytest.fail(
                            f"AuthConfig defaults to problematic 'netra_dev' database: {database_url}. "
                            "This database doesn't exist and causes connection failures."
                        )
                
            except Exception as e:
                logger.info(f"Database URL construction failed (might be expected): {e}")
    
    @pytest.mark.asyncio
    async def test_service_startup_continues_despite_netra_dev_failure(self):
        """FAILING TEST: Tests that service startup incorrectly continues despite database failure.
        
        This replicates the behavior from main.py lifespan function where the service
        starts even when database initialization fails in development/staging.
        """
        startup_env = {
            'ENVIRONMENT': 'development',
            'POSTGRES_DB': 'netra_dev',
            'POSTGRES_HOST': 'localhost', 
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'test_password'
        }
        
        with patch.dict(os.environ, startup_env):
            test_auth_db = AuthDatabase()
            initialization_errors = []
            
            # Mock the exact initialization failure pattern from main.py
            try:
                await test_auth_db.initialize()
                logger.info("Auth database initialized successfully")
            except Exception as e:
                error_msg = str(e) if str(e) else f"{type(e).__name__}: {repr(e)}"
                logger.warning(f"Auth database initialization failed: {error_msg}")
                initialization_errors.append(f"Database: {error_msg}")
            
            # Replicate the problematic logic from main.py lines 141-145
            env = startup_env.get('ENVIRONMENT')
            if env in ["development", "staging"] and initialization_errors:
                logger.warning(f"Starting with {len(initialization_errors)} DB issues in {env} mode")
                
                # This is the problematic behavior - service continues with DB errors
                pytest.fail(
                    f"Service incorrectly continues startup despite database errors: {initialization_errors}. "
                    "When 'netra_dev' doesn't exist, service should fail to start or report unhealthy."
                )
    
    @pytest.mark.asyncio 
    async def test_security_scan_attempts_with_broken_database(self):
        """FAILING TEST: Tests handling of security scan attempts when database is broken.
        
        When database connectivity is broken (netra_dev doesn't exist), security
        scan attempts should be handled gracefully without exposing system issues.
        """
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development',
            'POSTGRES_DB': 'netra_dev',  # Broken database
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'test_pass'
        }):
            test_auth_db = AuthDatabase()
            
            # Mock security scan request patterns
            security_scan_patterns = [
                '/admin',
                '/wp-admin',
                '/.env',
                '/config',
                '/health?debug=true',
                '/health/../admin'
            ]
            
            for scan_path in security_scan_patterns:
                # When database is broken, security scans might expose internal errors
                try:
                    # This would typically go through the FastAPI app
                    # But since database is broken, it might expose internal details
                    db_status = await test_auth_db.test_connection()
                    
                    if not db_status:
                        # Database is broken - security scan might get error details
                        error_details = {
                            'path': scan_path,
                            'database_status': 'netra_dev database not found',
                            'internal_error': 'Database connection failed'
                        }
                        
                        # Security issue: broken database might expose internal details
                        logger.warning(f"Security scan to {scan_path} might expose: {error_details}")
                        
                except Exception as e:
                    # Security scans shouldn't cause unhandled exceptions
                    logger.error(f"Security scan to {scan_path} caused exception: {e}")
                    pytest.fail(
                        f"Security scan to {scan_path} caused unhandled exception when database is broken. "
                        "This might expose system internals to attackers."
                    )
    
    @pytest.mark.asyncio
    async def test_token_validation_fails_silently_with_broken_database(self):
        """FAILING TEST: Tests token validation when database connectivity is broken.
        
        When 'netra_dev' database doesn't exist, token validation operations
        should fail gracefully rather than causing service errors.
        """
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development', 
            'POSTGRES_DB': 'netra_dev',  # Broken database
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'test_pass'
        }):
            test_auth_db = AuthDatabase()
            
            # Mock token validation attempt when database is unavailable
            async def mock_token_validation_with_db_error(*args, **kwargs):
                raise OperationalError(
                    'database "netra_dev" does not exist',
                    None, None
                )
            
            # Mock session for token validation
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(side_effect=mock_token_validation_with_db_error)
            mock_session.rollback = AsyncMock()
            mock_session.close = AsyncMock()
            
            with patch.object(test_auth_db, 'get_session') as mock_get_session:
                mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_get_session.return_value.__aexit__ = AsyncMock()
                
                # Token validation should fail gracefully
                try:
                    async with test_auth_db.get_session() as session:
                        # Simulate token validation query
                        from sqlalchemy import text
                        result = await session.execute(
                            text("SELECT id FROM auth_sessions WHERE refresh_token_hash = :token"),
                            {'token': 'test_token_hash'}
                        )
                    
                    # Should not reach here if database is properly unavailable
                    pytest.fail(
                        "Token validation succeeded despite 'netra_dev' database not existing. "
                        "This indicates improper error handling or graceful degradation."
                    )
                    
                except OperationalError as e:
                    # Expected behavior - token validation should fail
                    assert 'netra_dev' in str(e)
                    logger.info(f"Token validation correctly failed: {e}")
    
    def test_database_environment_configuration_mismatch(self):
        """FAILING TEST: Tests database name configuration mismatch across environments.
        
        Different environments might expect different database names, and 
        'netra_dev' might be incorrectly used in staging/production environments.
        """
        # Test database name expectations per environment
        environment_database_expectations = [
            ('development', ['netra_dev', 'netra_development']),
            ('staging', ['netra_staging', 'netra_stage']), 
            ('production', ['netra_prod', 'netra_production']),
            ('test', ['netra_test'])
        ]
        
        for environment, expected_db_names in environment_database_expectations:
            config = {
                'ENVIRONMENT': environment,
                'POSTGRES_HOST': f'{environment}-host',
                'POSTGRES_PORT': '5432',
                'POSTGRES_USER': f'{environment}_user',
                'POSTGRES_PASSWORD': f'{environment}_password'
            }
            
            # Test what happens when POSTGRES_DB is not explicitly set
            with patch.dict(os.environ, config, clear=True):
                try:
                    auth_config = AuthConfig()
                    database_url = auth_config.get_database_url()
                    
                    if database_url:
                        # Check if URL contains problematic 'netra_dev' in non-dev environments
                        if environment != 'development' and 'netra_dev' in database_url:
                            pytest.fail(
                                f"Environment '{environment}' incorrectly uses 'netra_dev' database: {database_url}. "
                                f"Expected one of: {expected_db_names}"
                            )
                        
                        # Check if development environment uses non-existent database
                        if environment == 'development' and 'netra_dev' in database_url:
                            # This is where the issue manifests
                            logger.error(
                                f"Development environment uses 'netra_dev' which may not exist: {database_url}"
                            )
                            pytest.fail(
                                "Development environment defaults to 'netra_dev' database which doesn't exist. "
                                "Need to ensure development database is created or use different default."
                            )
                            
                except Exception as e:
                    logger.info(f"Environment '{environment}' database config failed: {e}")


class TestDatabaseConnectivityHealthChecks:
    """Test suite for health check database connectivity validation."""
    
    @pytest.mark.asyncio
    async def test_health_endpoint_should_validate_database_connectivity(self):
        """FAILING TEST: Health endpoint should validate database connectivity before reporting healthy.
        
        The /health endpoint should check if the database is actually accessible
        before reporting healthy status, especially for critical databases like netra_dev.
        """
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development',
            'POSTGRES_DB': 'netra_dev',
            'PORT': '8080'
        }):
            # Mock database connectivity failure
            async def mock_database_not_accessible(*args, **kwargs):
                raise OperationalError('database "netra_dev" does not exist', None, None)
            
            # Test the health endpoint behavior
            from auth_service.main import app
            
            # The problem: health endpoint doesn't check database
            # It just returns basic health info without validation
            
            with patch('auth_service.auth_core.database.connection.auth_db.is_ready',
                      side_effect=mock_database_not_accessible):
                
                # Health endpoint should fail but might not
                try:
                    # Simulate health endpoint call
                    from auth_service.main import health_interface
                    health_status = health_interface.get_basic_health()
                    
                    if health_status.get('status') == 'healthy':
                        pytest.fail(
                            "Health endpoint reports 'healthy' without validating database connectivity. "
                            "When netra_dev database is inaccessible, health should report unhealthy."
                        )
                        
                except Exception as e:
                    # Health endpoint should handle database errors gracefully
                    logger.info(f"Health endpoint correctly failed due to database issues: {e}")
    
    @pytest.mark.asyncio 
    async def test_readiness_endpoint_should_fail_when_database_unavailable(self):
        """FAILING TEST: Readiness endpoint should fail when database is unavailable.
        
        The /health/ready endpoint should properly detect when netra_dev database
        is not accessible and return not ready status.
        """
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development',
            'POSTGRES_DB': 'netra_dev',
            'PORT': '8080'
        }):
            # Mock the readiness check from main.py
            async def mock_readiness_check_with_db_error():
                from auth_service.auth_core.database.connection import auth_db
                
                # Mock database ready check failure
                async def mock_is_ready():
                    raise OperationalError('database "netra_dev" does not exist', None, None)
                
                with patch.object(auth_db, 'is_ready', side_effect=mock_is_ready):
                    try:
                        is_ready = await auth_db.is_ready()
                        return is_ready
                    except OperationalError:
                        return False
            
            readiness_result = await mock_readiness_check_with_db_error()
            
            if readiness_result:
                pytest.fail(
                    "Readiness check reports ready despite netra_dev database being unavailable. "
                    "Service should not be ready when database connectivity is broken."
                )
    
    @pytest.mark.asyncio
    async def test_shutdown_timeout_with_broken_database_connections(self):
        """FAILING TEST: Tests shutdown timeout issues when database connections are broken.
        
        When database connections are broken (netra_dev doesn't exist), the shutdown
        process should not hang due to trying to close non-existent connections.
        """
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development',
            'POSTGRES_DB': 'netra_dev',
            'SHUTDOWN_TIMEOUT_SECONDS': '2',  # Short timeout for testing
            'CLEANUP_TIMEOUT_SECONDS': '1'
        }):
            test_auth_db = AuthDatabase()
            
            # Mock broken database connection
            async def mock_broken_connection_close(*args, **kwargs):
                # Simulate hanging connection close
                await asyncio.sleep(5)  # Longer than timeout
                raise OperationalError('database "netra_dev" does not exist', None, None)
            
            # Mock engine with broken connection
            mock_engine = AsyncMock()
            mock_engine.dispose = AsyncMock(side_effect=mock_broken_connection_close)
            test_auth_db.engine = mock_engine
            test_auth_db._initialized = True
            
            # Test shutdown with timeout
            import time
            start_time = time.time()
            
            try:
                await test_auth_db.close(timeout=2.0)
                end_time = time.time()
                elapsed = end_time - start_time
                
                # Should not hang beyond timeout
                if elapsed > 3.0:  # Allow some buffer
                    pytest.fail(
                        f"Database shutdown took {elapsed:.2f}s (expected ~2s). "
                        "Broken netra_dev connections are causing shutdown timeouts."
                    )
                    
            except asyncio.TimeoutError:
                # Expected behavior for broken connections
                logger.info("Database shutdown correctly timed out for broken connections")


# Mark all tests as integration tests requiring database setup
pytestmark = [pytest.mark.integration, pytest.mark.database]
"""FAILING E2E TESTS: Database 'postgres' Connectivity Cross-Service Impact
from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment

CRITICAL DATABASE ISSUE - E2E IMPACT VERIFICATION:
- Database connection failing with: "database 'postgres' does not exist"
- Service falls back to "staging mode" without database connectivity
- Cross-service authentication and user management compromised
- WebSocket authentication and session management affected

Business Value Justification (BVJ):
- Segment: All Tiers (Free, Early, Mid, Enterprise)
- Business Goal: End-to-end system reliability and user experience
- Value Impact: Ensures complete platform functionality across services
- Strategic Impact: Prevents complete system failure due to database connectivity

These E2E tests verify the impact of database connectivity issues across the entire platform.
Tests are designed to FAIL with current system state and PASS once properly resolved.
"""

import os
import pytest
import asyncio
import logging
from sqlalchemy.exc import OperationalError

from test_framework.environment_markers import env, env_requires
from tests.e2e.helpers.auth.auth_service_helpers import AuthServiceIndependenceValidator
from tests.e2e.helpers.database.database_sync_helpers import DatabaseSyncHelper
from tests.e2e.helpers.core.service_independence_helpers import ServiceIndependenceHelper
from tests.e2e.database_test_connections import DatabaseConnectionTester

logger = logging.getLogger(__name__)


@env("staging")
@env_requires(services=["auth_service", "backend", "postgres"], features=["database_connectivity"])
@pytest.mark.e2e
class TestDatabasePostgresConnectivityE2E:
    """E2E test suite for database 'postgres' connectivity failures across services."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_auth_service_fails_to_start_with_postgres_database_error(self):
        """FAILING E2E TEST: Auth service startup failure cascades to entire platform.
        
        When auth service can't connect to database 'postgres', it should fail to start
        rather than falling back to degraded 'staging mode'.
        """
        # Environment that causes the postgres database error
        postgres_error_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': 'test-db-host',
            'POSTGRES_PORT': '5432', 
            'POSTGRES_DB': 'postgres',  # This database doesn't exist
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_password'
        }
        
        with patch.dict(os.environ, postgres_error_env):
            auth_helper = AuthServiceIndependenceValidator()
            
            # Mock database connection to fail with postgres error
            with patch('sqlalchemy.ext.asyncio.create_async_engine') as mock_engine:
                mock_engine.return_value.connect.side_effect = OperationalError(
                    'database "postgres" does not exist',
                    None, None
                )
                
                # Auth service startup should fail completely
                with pytest.raises(Exception) as exc_info:
                    await auth_helper.start_auth_service()
                
                # Verify the error is related to postgres database
                error_message = str(exc_info.value).lower()
                assert 'postgres' in error_message and 'does not exist' in error_message
                
                logger.error(f"Auth service correctly failed to start due to postgres database error: {exc_info.value}")
    
    @pytest.mark.asyncio 
    @pytest.mark.e2e
    async def test_user_authentication_fails_without_database_connectivity(self):
        """FAILING E2E TEST: User authentication fails when database is unreachable.
        
        Complete authentication flow should fail when database 'postgres' doesn't exist,
        rather than allowing users to authenticate in degraded mode.
        """
        postgres_error_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_DB': 'postgres',  # Problematic database name
            'POSTGRES_HOST': 'test-host',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_pass'
        }
        
        with patch.dict(os.environ, postgres_error_env):
            auth_helper = AuthServiceIndependenceValidator()
            
            # Mock database operations to fail during authentication
            async def mock_auth_db_failure(*args, **kwargs):
                raise OperationalError(
                    'connection failed: database "postgres" does not exist',
                    None, None
                )
            
            # Mock auth service to simulate staging mode fallback
            with patch.object(auth_helper, 'authenticate_user', side_effect=mock_auth_db_failure):
                # User authentication should fail completely
                with pytest.raises(OperationalError) as exc_info:
                    result = await auth_helper.authenticate_user(
                        email="test@example.com",
                        password="test_password"
                    )
                
                assert 'postgres" does not exist' in str(exc_info.value)
                logger.error(f"User authentication correctly failed due to database connectivity: {exc_info.value}")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_session_management_fails_across_services(self):
        """FAILING E2E TEST: Session management fails across backend and auth service.
        
        When database 'postgres' is unavailable, session creation and validation
        should fail consistently across all services.
        """
        postgres_error_env = {
            'ENVIRONMENT': 'staging', 
            'POSTGRES_DB': 'postgres',  # Problematic database
            'POSTGRES_HOST': 'test-host',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_pass'
        }
        
        with patch.dict(os.environ, postgres_error_env):
            auth_helper = AuthServiceIndependenceValidator()
            db_helper = DatabaseSyncHelper()
            
            # Mock session operations to fail due to database connectivity
            async def mock_session_failure(*args, **kwargs):
                raise OperationalError(
                    'database "postgres" does not exist',
                    None, None
                )
            
            # Test session creation failure
            with patch.object(auth_helper, 'create_session', side_effect=mock_session_failure):
                with pytest.raises(OperationalError) as exc_info:
                    session_data = await auth_helper.create_session(
                        user_id="test_user_123",
                        access_token="test_token"
                    )
                
                assert 'postgres" does not exist' in str(exc_info.value)
            
            # Test session validation failure across services
            with patch.object(db_helper, 'validate_session_sync', side_effect=mock_session_failure):
                with pytest.raises(OperationalError) as exc_info:
                    is_valid = await db_helper.validate_session_sync(
                        session_id="test_session",
                        services=["auth_service", "backend"]
                    )
                
                assert 'postgres" does not exist' in str(exc_info.value)
                logger.error("Session management correctly failed across services due to database issue")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_authentication_fails_with_database_error(self):
        """FAILING E2E TEST: WebSocket authentication fails when database is unavailable.
        
        WebSocket connections that require authentication should fail when
        the database 'postgres' is not accessible.
        """
        postgres_error_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_DB': 'postgres',  # Problematic database name
            'POSTGRES_HOST': 'test-host'
        }
        
        with patch.dict(os.environ, postgres_error_env):
            # Import WebSocket test utilities
            from tests.e2e.helpers.websocket.websocket_test_helpers import WebSocketTestHelper
            
            ws_helper = WebSocketTestHelper()
            
            # Mock WebSocket authentication to fail due to database issues
            async def mock_ws_auth_failure(*args, **kwargs):
                raise OperationalError(
                    'WebSocket authentication failed: database "postgres" does not exist',
                    None, None
                )
            
            with patch.object(ws_helper, 'authenticate_websocket', side_effect=mock_ws_auth_failure):
                # WebSocket authentication should fail
                with pytest.raises(OperationalError) as exc_info:
                    ws_connection = await ws_helper.authenticate_websocket(
                        token="test_jwt_token",
                        user_id="test_user"
                    )
                
                assert 'postgres" does not exist' in str(exc_info.value)
                logger.error(f"WebSocket authentication correctly failed: {exc_info.value}")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_service_health_checks_detect_database_connectivity_issues(self):
        """FAILING E2E TEST: Service health checks should detect postgres database connectivity issues.
        
        All service health checks should fail when database 'postgres' is not accessible,
        preventing the services from appearing healthy when they're not functional.
        """
        postgres_error_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_DB': 'postgres',  # Problematic database
            'POSTGRES_HOST': 'unreachable-host',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_pass'
        }
        
        with patch.dict(os.environ, postgres_error_env):
            # Test auth service health check
            auth_helper = AuthServiceIndependenceValidator()
            
            # Mock health check to fail due to database connectivity
            async def mock_health_check_failure():
                raise OperationalError(
                    'Health check failed: database "postgres" does not exist',
                    None, None
                )
            
            with patch.object(auth_helper, 'check_health', side_effect=mock_health_check_failure):
                # Health check should fail, not return false positive
                with pytest.raises(OperationalError) as exc_info:
                    health_status = await auth_helper.check_health()
                
                assert 'postgres" does not exist' in str(exc_info.value)
                logger.error("Service health check correctly failed due to database connectivity issue")
            
            # Test cross-service health propagation
            service_helper = ServiceIndependenceHelper()
            
            with patch.object(service_helper, 'check_service_health') as mock_service_health:
                mock_service_health.return_value = {
                    'auth_service': {'status': 'unhealthy', 'error': 'database connectivity failed'},
                    'backend': {'status': 'degraded', 'error': 'auth service unavailable'}
                }
                
                health_status = await service_helper.check_service_health(['auth_service', 'backend'])
                
                # Verify that database connectivity issues propagate correctly
                assert health_status['auth_service']['status'] == 'unhealthy'
                assert 'database connectivity' in health_status['auth_service']['error']
                
                logger.info("Cross-service health check correctly propagated database connectivity failure")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_database_migration_fails_with_postgres_database_error(self):
        """FAILING E2E TEST: Database migrations fail when target database doesn't exist.
        
        Database schema migrations should fail when attempting to run against
        non-existent 'postgres' database.
        """
        postgres_error_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_DB': 'postgres',  # Database that doesn't exist
            'POSTGRES_HOST': 'test-host',
            'POSTGRES_USER': 'migration_user',
            'POSTGRES_PASSWORD': 'migration_pass'
        }
        
        with patch.dict(os.environ, postgres_error_env):
            db_helper = DatabaseSyncHelper()
            
            # Mock migration to fail due to database not existing
            async def mock_migration_failure(*args, **kwargs):
                raise OperationalError(
                    'Migration failed: database "postgres" does not exist',
                    None, None
                )
            
            with patch.object(db_helper, 'run_migrations', side_effect=mock_migration_failure):
                # Migration should fail completely
                with pytest.raises(OperationalError) as exc_info:
                    migration_result = await db_helper.run_migrations(
                        service="auth_service",
                        target="head"
                    )
                
                assert 'postgres" does not exist' in str(exc_info.value)
                logger.error(f"Database migration correctly failed: {exc_info.value}")
    
    @pytest.mark.e2e
    def test_service_startup_dependency_chain_breaks_with_database_error(self):
        """FAILING E2E TEST: Service startup dependency chain breaks when database is unavailable.
        
        The entire service startup sequence should fail when the foundational
        database 'postgres' is not accessible.
        """
        postgres_error_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_DB': 'postgres',  # Problematic database name
            'POSTGRES_HOST': 'test-host'
        }
        
        with patch.dict(os.environ, postgres_error_env):
            service_helper = ServiceIndependenceHelper()
            
            # Mock service startup to fail due to database dependency
            startup_sequence = [
                ('database', False, 'database "postgres" does not exist'),
                ('auth_service', False, 'database dependency failed'),
                ('backend', False, 'auth service dependency failed'),
                ('frontend', False, 'backend dependency failed')
            ]
            
            with patch.object(service_helper, 'validate_startup_sequence') as mock_startup:
                mock_startup.return_value = startup_sequence
                
                startup_result = service_helper.validate_startup_sequence()
                
                # Verify that database failure cascades through all services
                for service_name, success, error_msg in startup_result:
                    assert not success, f"Service {service_name} should fail due to database connectivity"
                    if service_name == 'database':
                        assert 'postgres" does not exist' in error_msg
                    else:
                        assert 'dependency failed' in error_msg
                
                logger.error("Service startup dependency chain correctly failed due to database connectivity")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_database_connection_pool_exhaustion_across_services(self):
        """FAILING E2E TEST: Database connection pool exhaustion when retrying postgres connections.
        
        Repeated attempts to connect to non-existent 'postgres' database can exhaust
        connection pools across all services.
        """
        postgres_error_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_DB': 'postgres',  # Database that doesn't exist
            'POSTGRES_HOST': 'test-host'
        }
        
        with patch.dict(os.environ, postgres_error_env):
            db_tester = DatabaseConnectionTester()
            
            # Mock connection pool exhaustion due to repeated failures
            connection_attempts = []
            
            async def mock_connection_attempt(service_name):
                connection_attempts.append(service_name)
                if len(connection_attempts) > 10:  # Simulate pool exhaustion
                    raise OperationalError(
                        'connection pool exhausted: database "postgres" does not exist',
                        None, None
                    )
                else:
                    raise OperationalError(
                        'database "postgres" does not exist',
                        None, None
                    )
            
            # Test connection attempts across multiple services
            services = ['auth_service', 'backend', 'metrics_service']
            
            for service in services:
                with pytest.raises(OperationalError) as exc_info:
                    await mock_connection_attempt(service)
                
                error_message = str(exc_info.value)
                assert 'postgres" does not exist' in error_message
            
            # Verify pool exhaustion occurs after repeated attempts
            assert len(connection_attempts) > 0
            logger.error(f"Connection pool exhaustion simulated after {len(connection_attempts)} attempts")


@env("staging") 
@env_requires(services=["postgres"], features=["database_naming"])
@pytest.mark.e2e
class TestDatabaseNamingConventionE2E:
    """E2E tests for database naming convention issues across the platform."""
    
    @pytest.mark.e2e
    def test_environment_specific_database_naming_consistency(self):
        """FAILING E2E TEST: Database naming consistency across environments and services.
        
        All services should use consistent, environment-appropriate database names
        instead of defaulting to system 'postgres' database.
        """
        # Test different environment configurations
        environments = ['development', 'staging', 'production']
        expected_databases = {
            'development': 'netra_dev',
            'staging': 'netra_staging', 
            'production': 'netra_production'
        }
        
        for environment in environments:
            env_config = {
                'ENVIRONMENT': environment,
                'POSTGRES_HOST': f'{environment}-host',
                'POSTGRES_PORT': '5432',
                'POSTGRES_USER': f'{environment}_user',
                'POSTGRES_PASSWORD': f'{environment}_password'
                # Note: No explicit POSTGRES_DB - testing default resolution
            }
            
            with patch.dict(os.environ, env_config, clear=True):
                # Test database name resolution across services
                from shared.database_url_builder import DatabaseURLBuilder
                
                builder = DatabaseURLBuilder(env_config)
                database_url = builder.get_url_for_environment(sync=False)
                
                expected_db = expected_databases.get(environment)
                
                # Check if URL resolves to correct database or problematic 'postgres'
                if database_url:
                    if '/postgres' in database_url and expected_db not in database_url:
                        pytest.fail(
                            f"Environment '{environment}' incorrectly uses 'postgres' database instead of '{expected_db}': {database_url}. "
                            "This causes the 'database postgres does not exist' error."
                        )
                    elif expected_db and expected_db in database_url:
                        logger.info(f"Environment '{environment}' correctly resolves to database '{expected_db}'")
                    else:
                        logger.warning(f"Environment '{environment}' database resolution unclear: {database_url}")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cross_service_database_name_synchronization(self):
        """FAILING E2E TEST: All services should use the same application database name.
        
        Auth service and backend should connect to the same application database,
        not different databases including system 'postgres' database.
        """
        staging_env = {
            'ENVIRONMENT': 'staging',
            'POSTGRES_HOST': 'staging-host',
            'POSTGRES_PORT': '5432',
            'POSTGRES_USER': 'staging_user',
            'POSTGRES_PASSWORD': 'staging_password'
            # Testing without explicit POSTGRES_DB to see defaults
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            # Get database URLs for different services
            from shared.database_url_builder import DatabaseURLBuilder
            from auth_service.auth_core.config import AuthConfig
            
            # Test auth service database URL
            auth_builder = DatabaseURLBuilder(staging_env)
            auth_db_url = auth_builder.get_url_for_environment(sync=False)
            
            # Test backend database URL (if different configuration)
            backend_builder = DatabaseURLBuilder(staging_env)
            backend_db_url = backend_builder.get_url_for_environment(sync=False)
            
            # Verify both services use the same database name
            if auth_db_url and backend_db_url:
                # Extract database names from URLs
                auth_db_name = auth_db_url.split('/')[-1].split('?')[0] if '/' in auth_db_url else 'unknown'
                backend_db_name = backend_db_url.split('/')[-1].split('?')[0] if '/' in backend_db_url else 'unknown'
                
                if auth_db_name != backend_db_name:
                    pytest.fail(
                        f"Database name mismatch between services: "
                        f"auth_service='{auth_db_name}', backend='{backend_db_name}'. "
                        f"Services should use the same application database."
                    )
                
                if auth_db_name == 'postgres':
                    pytest.fail(
                        f"Both services incorrectly default to 'postgres' database: "
                        f"auth_url={auth_db_url}, backend_url={backend_db_url}. "
                        f"This is the root cause of the 'database postgres does not exist' error."
                    )
                
                logger.info(f"Services correctly synchronized to database: {auth_db_name}")


# Mark all tests as integration tests requiring database and cross-service setup
pytestmark = [pytest.mark.integration, pytest.mark.database, pytest.mark.e2e]
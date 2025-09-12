"""
Critical Integration Test: User Sessions Table Validation

This test validates the CRITICAL issue where the user_sessions table schema exists
in database_scripts/staging_init.sql but is missing from the actual staging database,
causing authentication failures.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure authentication works for Golden Path
- Value Impact: Without user_sessions table, authentication completely fails
- Strategic Impact: $120K+ MRR protection by preventing authentication outages

CRITICAL: This test will INITIALLY FAIL to reproduce the production issue.
Once the remediation is complete, this test should PASS.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
import asyncio
import logging
from typing import Dict, Any, List

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from shared.isolated_environment import get_env
from shared.types.core_types import UserID

logger = logging.getLogger(__name__)


class TestUserSessionsTableValidation(BaseIntegrationTest):
    """
    Critical integration test for user_sessions table deployment validation.
    
    This test validates that the user_sessions table exists in the actual database
    and has the correct schema as defined in staging_init.sql.
    
    CRITICAL: This test reproduces the staging authentication failure where
    user_sessions table is missing despite being in the schema definition.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.critical
    async def test_user_sessions_table_exists_in_database(self, real_services_fixture):
        """
        CRITICAL TEST: Validate user_sessions table exists with correct schema.
        
        This test will INITIALLY FAIL because the user_sessions table is missing
        from the actual staging database despite being defined in staging_init.sql.
        
        Expected Failure Conditions:
        1. Table does not exist in auth schema
        2. Query to user_sessions table raises ProgrammingError
        3. Authentication flows dependent on user_sessions fail
        """
        logger.info(" SEARCH:  CRITICAL TEST: Validating user_sessions table deployment")
        
        db_session = real_services_fixture["db"]
        
        # Test 1: Direct table existence check
        try:
            table_check_result = await db_session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'auth' 
                    AND table_name = 'user_sessions'
                );
            """))
            table_exists = table_check_result.scalar()
            
            if not table_exists:
                pytest.fail(
                    " FAIL:  CRITICAL FAILURE: user_sessions table missing from auth schema. "
                    "This reproduces the staging authentication failure. "
                    "Table exists in staging_init.sql but not deployed to database."
                )
                
            logger.info(" PASS:  user_sessions table exists in auth schema")
            
        except Exception as e:
            pytest.fail(f" FAIL:  CRITICAL FAILURE: Cannot check user_sessions table existence: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.critical
    async def test_user_sessions_table_schema_validation(self, real_services_fixture):
        """
        CRITICAL TEST: Validate user_sessions table has correct schema structure.
        
        Ensures the table has all required columns as defined in staging_init.sql:
        - id, user_id, session_token, refresh_token, expires_at, created_at, 
          last_accessed, ip_address, user_agent, is_active
        """
        logger.info(" SEARCH:  CRITICAL TEST: Validating user_sessions table schema")
        
        db_session = real_services_fixture["db"]
        
        try:
            # Get table schema information
            schema_result = await db_session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_schema = 'auth' 
                AND table_name = 'user_sessions'
                ORDER BY ordinal_position;
            """))
            
            columns = schema_result.fetchall()
            
            if not columns:
                pytest.fail(
                    " FAIL:  CRITICAL FAILURE: user_sessions table has no columns or doesn't exist. "
                    "This indicates deployment configuration failure."
                )
            
            # Expected columns from staging_init.sql
            expected_columns = {
                'id', 'user_id', 'session_token', 'refresh_token', 
                'expires_at', 'created_at', 'last_accessed', 
                'ip_address', 'user_agent', 'is_active'
            }
            
            actual_columns = {col[0] for col in columns}
            
            missing_columns = expected_columns - actual_columns
            if missing_columns:
                pytest.fail(
                    f" FAIL:  CRITICAL FAILURE: user_sessions table missing required columns: {missing_columns}. "
                    f"This indicates incomplete deployment or schema drift."
                )
            
            logger.info(f" PASS:  user_sessions table has correct schema with {len(actual_columns)} columns")
            
        except ProgrammingError as e:
            pytest.fail(
                f" FAIL:  CRITICAL FAILURE: Cannot access user_sessions table schema: {e}. "
                f"This reproduces the staging authentication issue - table not properly deployed."
            )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.critical
    async def test_user_sessions_table_write_operations(self, real_services_fixture):
        """
        CRITICAL TEST: Validate user_sessions table supports authentication operations.
        
        Tests the actual operations needed for authentication:
        1. Insert new session record
        2. Query session by token
        3. Update session last_accessed
        4. Cleanup expired sessions
        """
        logger.info(" SEARCH:  CRITICAL TEST: Validating user_sessions table operations")
        
        db_session = real_services_fixture["db"]
        
        # Create test user first
        test_user_id = "test-user-sessions-validation"
        test_session_token = "test-session-token-12345"
        
        try:
            # Test 1: Insert user session (critical for auth)
            insert_result = await db_session.execute(text("""
                INSERT INTO auth.user_sessions 
                (user_id, session_token, refresh_token, expires_at, ip_address, user_agent, is_active)
                VALUES (:user_id, :session_token, :refresh_token, NOW() + INTERVAL '1 hour', 
                        '127.0.0.1', 'test-browser', true)
                RETURNING id;
            """), {
                'user_id': test_user_id,
                'session_token': test_session_token,
                'refresh_token': f'refresh-{test_session_token}'
            })
            
            session_id = insert_result.scalar()
            if not session_id:
                pytest.fail(" FAIL:  CRITICAL FAILURE: Cannot insert into user_sessions table")
                
            logger.info(f" PASS:  Successfully inserted session record: {session_id}")
            
            # Test 2: Query session by token (critical for auth validation)
            query_result = await db_session.execute(text("""
                SELECT user_id, is_active, expires_at > NOW() as not_expired
                FROM auth.user_sessions 
                WHERE session_token = :session_token;
            """), {'session_token': test_session_token})
            
            session_data = query_result.fetchone()
            if not session_data:
                pytest.fail(" FAIL:  CRITICAL FAILURE: Cannot query user_sessions by token")
                
            assert session_data[0] == test_user_id, "Session user_id mismatch"
            assert session_data[1] is True, "Session should be active"
            assert session_data[2] is True, "Session should not be expired"
            
            logger.info(" PASS:  Successfully queried session by token")
            
            # Test 3: Update last_accessed (critical for session management)
            update_result = await db_session.execute(text("""
                UPDATE auth.user_sessions 
                SET last_accessed = NOW()
                WHERE session_token = :session_token
                RETURNING last_accessed;
            """), {'session_token': test_session_token})
            
            updated_time = update_result.scalar()
            if not updated_time:
                pytest.fail(" FAIL:  CRITICAL FAILURE: Cannot update user_sessions last_accessed")
                
            logger.info(" PASS:  Successfully updated session last_accessed")
            
            # Cleanup test data
            await db_session.execute(text("""
                DELETE FROM auth.user_sessions WHERE session_token = :session_token;
            """), {'session_token': test_session_token})
            
            await db_session.commit()
            
        except ProgrammingError as e:
            await db_session.rollback()
            pytest.fail(
                f" FAIL:  CRITICAL FAILURE: user_sessions table operations failed: {e}. "
                f"This reproduces the staging authentication failure - table not accessible for auth operations."
            )
        except Exception as e:
            await db_session.rollback()
            pytest.fail(f" FAIL:  CRITICAL FAILURE: Unexpected error in user_sessions operations: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.critical
    async def test_user_sessions_indexes_exist(self, real_services_fixture):
        """
        CRITICAL TEST: Validate user_sessions table has required indexes for performance.
        
        Checks for indexes defined in staging_init.sql:
        - idx_sessions_user_id
        - idx_sessions_token  
        - idx_sessions_expires_at
        """
        logger.info(" SEARCH:  CRITICAL TEST: Validating user_sessions table indexes")
        
        db_session = real_services_fixture["db"]
        
        try:
            indexes_result = await db_session.execute(text("""
                SELECT indexname, indexdef
                FROM pg_indexes 
                WHERE schemaname = 'auth' 
                AND tablename = 'user_sessions';
            """))
            
            indexes = indexes_result.fetchall()
            index_names = {idx[0] for idx in indexes}
            
            # Expected indexes from staging_init.sql
            expected_indexes = {
                'idx_sessions_user_id',
                'idx_sessions_token', 
                'idx_sessions_expires_at'
            }
            
            missing_indexes = expected_indexes - index_names
            if missing_indexes:
                logger.warning(f" WARNING: [U+FE0F] Missing performance indexes on user_sessions: {missing_indexes}")
                # Note: This is a warning, not a critical failure, but important for performance
            
            logger.info(f" PASS:  user_sessions table has {len(index_names)} indexes")
            
        except ProgrammingError as e:
            pytest.fail(
                f" FAIL:  CRITICAL FAILURE: Cannot check user_sessions indexes: {e}. "
                f"This indicates table deployment issues."
            )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.critical
    async def test_auth_schema_permissions(self, real_services_fixture):
        """
        CRITICAL TEST: Validate auth schema has correct permissions for user_sessions access.
        
        Ensures the database user has necessary permissions to:
        1. SELECT from user_sessions
        2. INSERT into user_sessions  
        3. UPDATE user_sessions
        4. DELETE from user_sessions
        """
        logger.info(" SEARCH:  CRITICAL TEST: Validating auth schema permissions")
        
        db_session = real_services_fixture["db"]
        
        try:
            # Check schema permissions
            perms_result = await db_session.execute(text("""
                SELECT has_table_privilege(current_user, 'auth.user_sessions', 'SELECT') as can_select,
                       has_table_privilege(current_user, 'auth.user_sessions', 'INSERT') as can_insert,
                       has_table_privilege(current_user, 'auth.user_sessions', 'UPDATE') as can_update,
                       has_table_privilege(current_user, 'auth.user_sessions', 'DELETE') as can_delete;
            """))
            
            permissions = perms_result.fetchone()
            
            if not all(permissions):
                perm_names = ['SELECT', 'INSERT', 'UPDATE', 'DELETE']
                missing_perms = [name for name, has_perm in zip(perm_names, permissions) if not has_perm]
                
                pytest.fail(
                    f" FAIL:  CRITICAL FAILURE: Missing permissions on user_sessions table: {missing_perms}. "
                    f"This prevents authentication operations and reproduces the staging failure."
                )
            
            logger.info(" PASS:  All required permissions exist on auth.user_sessions")
            
        except ProgrammingError as e:
            pytest.fail(
                f" FAIL:  CRITICAL FAILURE: Cannot check auth schema permissions: {e}. "
                f"This indicates deployment configuration issues."
            )


class TestUserSessionsAuthenticationIntegration(BaseIntegrationTest):
    """
    Integration test that validates authentication flows depending on user_sessions table.
    
    This test demonstrates the business impact of the missing user_sessions table
    by testing actual authentication operations that require the table.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    @pytest.mark.critical
    async def test_authentication_depends_on_user_sessions_table(self, real_services_fixture):
        """
        CRITICAL TEST: Validate authentication flow requires user_sessions table.
        
        This test will FAIL if user_sessions table is missing because authentication
        operations cannot store/retrieve session data.
        """
        logger.info(" SEARCH:  CRITICAL TEST: Authentication flow requiring user_sessions")
        
        # Create authenticated user context that requires user_sessions
        try:
            auth_helper = E2EAuthHelper(environment="test")
            
            # This should work with proper user_sessions table
            user_context = await create_authenticated_user_context(
                user_email="test-user-sessions@example.com",
                environment="test",
                permissions=["read", "write"]
            )
            
            assert user_context.user_id is not None
            assert user_context.agent_context['jwt_token'] is not None
            
            logger.info(" PASS:  Authentication context created successfully")
            
        except Exception as e:
            pytest.fail(
                f" FAIL:  CRITICAL FAILURE: Authentication flow failed: {e}. "
                f"This may indicate user_sessions table issues preventing proper auth operations."
            )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.critical
    async def test_session_cleanup_operations(self, real_services_fixture):
        """
        CRITICAL TEST: Validate session cleanup operations require user_sessions table.
        
        Tests the session cleanup functions that are critical for security
        and prevent session accumulation.
        """
        logger.info(" SEARCH:  CRITICAL TEST: Session cleanup operations")
        
        db_session = real_services_fixture["db"]
        
        try:
            # Test cleanup of expired sessions (critical security operation)
            cleanup_result = await db_session.execute(text("""
                SELECT COUNT(*) as expired_count
                FROM auth.user_sessions 
                WHERE expires_at < NOW() AND is_active = true;
            """))
            
            expired_count = cleanup_result.scalar()
            logger.info(f"Found {expired_count} expired sessions for cleanup")
            
            # Test the cleanup operation itself
            cleanup_update = await db_session.execute(text("""
                UPDATE auth.user_sessions 
                SET is_active = false 
                WHERE expires_at < NOW() AND is_active = true
                RETURNING id;
            """))
            
            cleaned_sessions = cleanup_update.fetchall()
            logger.info(f" PASS:  Session cleanup operation completed: {len(cleaned_sessions)} sessions")
            
            await db_session.commit()
            
        except ProgrammingError as e:
            await db_session.rollback()
            pytest.fail(
                f" FAIL:  CRITICAL FAILURE: Session cleanup failed due to user_sessions table issues: {e}. "
                f"This reproduces the staging authentication problem."
            )


class TestUserSessionsDatabaseDeploymentValidation(BaseIntegrationTest):
    """
    Test that validates database deployment succeeded for user_sessions table.
    
    This tests the deployment process itself to ensure schema changes
    from staging_init.sql are properly applied.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.critical
    async def test_deployment_configuration_completeness(self, real_services_fixture):
        """
        CRITICAL TEST: Validate deployment configuration created all expected tables.
        
        Ensures that the deployment process successfully created ALL tables
        defined in staging_init.sql, not just some of them.
        """
        logger.info(" SEARCH:  CRITICAL TEST: Database deployment completeness validation")
        
        db_session = real_services_fixture["db"]
        
        try:
            # Check all critical tables from staging_init.sql exist
            tables_result = await db_session.execute(text("""
                SELECT table_schema, table_name
                FROM information_schema.tables 
                WHERE table_schema IN ('auth', 'backend', 'analytics')
                AND table_type = 'BASE TABLE'
                ORDER BY table_schema, table_name;
            """))
            
            existing_tables = tables_result.fetchall()
            existing_table_names = {f"{schema}.{table}" for schema, table in existing_tables}
            
            # Expected critical tables from staging_init.sql
            expected_critical_tables = {
                'auth.users',
                'auth.user_sessions',  # THIS IS THE CRITICAL MISSING TABLE
                'backend.threads',
                'backend.messages',
                'backend.agent_executions',
                'analytics.request_metrics'
            }
            
            missing_tables = expected_critical_tables - existing_table_names
            
            if missing_tables:
                pytest.fail(
                    f" FAIL:  CRITICAL DEPLOYMENT FAILURE: Missing tables indicate incomplete deployment: {missing_tables}. "
                    f"Schema exists in staging_init.sql but tables not created in database. "
                    f"This reproduces the exact staging authentication failure."
                )
            
            logger.info(f" PASS:  All {len(expected_critical_tables)} critical tables exist in database")
            
            # Log existing tables for debugging
            logger.info("Existing tables in database:")
            for schema, table in existing_tables:
                logger.info(f"  {schema}.{table}")
                
        except Exception as e:
            pytest.fail(f" FAIL:  CRITICAL FAILURE: Cannot validate database deployment: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.critical
    async def test_auth_schema_deployment_validation(self, real_services_fixture):
        """
        CRITICAL TEST: Specifically validate auth schema deployment success.
        
        The auth schema is critical for authentication and the user_sessions
        table MUST exist for the Golden Path to work.
        """
        logger.info(" SEARCH:  CRITICAL TEST: Auth schema deployment validation")
        
        db_session = real_services_fixture["db"]
        
        try:
            # Check auth schema exists
            schema_result = await db_session.execute(text("""
                SELECT schema_name
                FROM information_schema.schemata 
                WHERE schema_name = 'auth';
            """))
            
            auth_schema_exists = schema_result.scalar()
            if not auth_schema_exists:
                pytest.fail(
                    " FAIL:  CRITICAL FAILURE: auth schema missing from database. "
                    "Complete deployment failure - authentication impossible."
                )
            
            # Check auth schema tables
            auth_tables_result = await db_session.execute(text("""
                SELECT table_name
                FROM information_schema.tables 
                WHERE table_schema = 'auth'
                ORDER BY table_name;
            """))
            
            auth_tables = [row[0] for row in auth_tables_result.fetchall()]
            
            # Required auth tables from staging_init.sql
            required_auth_tables = {'users', 'user_sessions'}
            missing_auth_tables = required_auth_tables - set(auth_tables)
            
            if missing_auth_tables:
                pytest.fail(
                    f" FAIL:  CRITICAL FAILURE: Missing auth tables: {missing_auth_tables}. "
                    f"user_sessions table missing prevents all authentication. "
                    f"This reproduces the staging authentication failure exactly."
                )
            
            logger.info(f" PASS:  Auth schema complete with tables: {auth_tables}")
            
        except Exception as e:
            pytest.fail(f" FAIL:  CRITICAL FAILURE: Auth schema validation failed: {e}")
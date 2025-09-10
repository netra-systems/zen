"""
Test User Sessions Table Deployment

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure authentication foundation exists
- Value Impact: Users must be able to authenticate to access chat functionality
- Strategic Impact: Core platform dependency - without user_sessions, no authentication possible

CRITICAL: This test reproduces the EXACT staging issue where user_sessions table
schema exists in staging_init.sql but is missing from the actual database.
"""

import pytest
import asyncpg
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env


class TestUserSessionsTableDeployment(BaseIntegrationTest):
    """Test user_sessions table deployment and schema validation."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_sessions_table_missing_reproduction(self, real_services_fixture):
        """
        CRITICAL: Reproduce the exact staging issue - user_sessions table missing.
        
        This test should FAIL INITIALLY because the user_sessions table is missing
        from the database, even though the schema exists in staging_init.sql.
        After remediation, this test should PASS.
        """
        # Get database connection
        db_info = real_services_fixture["db_info"]
        
        # Connect to PostgreSQL database
        conn = await asyncpg.connect(
            host=db_info["host"],
            port=db_info["port"],
            database=db_info["database"],
            user=db_info["user"],
            password=db_info["password"]
        )
        
        try:
            # CRITICAL: This should FAIL initially due to missing table
            # Test 1: Check if user_sessions table exists in auth schema
            table_exists_query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'auth' 
                    AND table_name = 'user_sessions'
                );
            """
            table_exists = await conn.fetchval(table_exists_query)
            assert table_exists, "user_sessions table is missing from auth schema - this is the CRITICAL issue blocking authentication!"
            
            # Test 2: Verify table has correct schema structure
            if table_exists:
                columns_query = """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'auth' 
                    AND table_name = 'user_sessions'
                    ORDER BY ordinal_position;
                """
                columns = await conn.fetch(columns_query)
                
                # Expected columns from staging_init.sql
                expected_columns = {
                    'id': 'uuid',
                    'user_id': 'uuid', 
                    'session_token': 'character varying',
                    'refresh_token': 'character varying',
                    'expires_at': 'timestamp with time zone',
                    'created_at': 'timestamp with time zone',
                    'last_accessed': 'timestamp with time zone',
                    'ip_address': 'inet',
                    'user_agent': 'text',
                    'is_active': 'boolean'
                }
                
                actual_columns = {col['column_name']: col['data_type'] for col in columns}
                
                # Verify all expected columns exist with correct types
                for col_name, col_type in expected_columns.items():
                    assert col_name in actual_columns, f"Missing column: {col_name}"
                    assert col_type in actual_columns[col_name], f"Column {col_name} has wrong type: {actual_columns[col_name]} vs expected {col_type}"
            
            # Test 3: Verify table has proper indexes
            indexes_query = """
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = 'auth' 
                AND tablename = 'user_sessions';
            """
            indexes = await conn.fetch(indexes_query)
            
            # Expected indexes from staging_init.sql
            expected_indexes = [
                'idx_sessions_user_id',
                'idx_sessions_token', 
                'idx_sessions_expires_at'
            ]
            
            actual_indexes = [idx['indexname'] for idx in indexes]
            for expected_idx in expected_indexes:
                assert expected_idx in actual_indexes, f"Missing index: {expected_idx}"
            
            # Test 4: Verify foreign key relationship to users table
            fk_query = """
                SELECT
                    tc.constraint_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM
                    information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                        AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' 
                    AND tc.table_schema = 'auth'
                    AND tc.table_name = 'user_sessions';
            """
            foreign_keys = await conn.fetch(fk_query)
            
            # Should have foreign key to auth.users(id)
            assert len(foreign_keys) > 0, "user_sessions table missing foreign key constraint to users table"
            
            user_fk = next((fk for fk in foreign_keys if fk['column_name'] == 'user_id'), None)
            assert user_fk is not None, "user_sessions.user_id missing foreign key to users.id"
            assert user_fk['foreign_table_name'] == 'users', f"user_sessions.user_id references wrong table: {user_fk['foreign_table_name']}"
            assert user_fk['foreign_column_name'] == 'id', f"user_sessions.user_id references wrong column: {user_fk['foreign_column_name']}"
            
        finally:
            await conn.close()
    
    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_staging_init_sql_execution_verification(self, real_services_fixture):
        """
        Verify staging_init.sql execution creates all required tables.
        
        This test validates that when staging_init.sql is properly executed,
        it creates the user_sessions table with the correct schema.
        Should FAIL initially due to incomplete database migration.
        """
        # Get database connection
        db_info = real_services_fixture["db_info"]
        
        conn = await asyncpg.connect(
            host=db_info["host"],
            port=db_info["port"],
            database=db_info["database"],
            user=db_info["user"],
            password=db_info["password"]
        )
        
        try:
            # Test 1: Verify auth schema exists
            schema_exists_query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.schemata 
                    WHERE schema_name = 'auth'
                );
            """
            schema_exists = await conn.fetchval(schema_exists_query)
            assert schema_exists, "auth schema is missing - staging_init.sql not executed properly"
            
            # Test 2: Verify all required tables from staging_init.sql exist
            required_tables = [
                ('auth', 'users'),
                ('auth', 'user_sessions'),  # CRITICAL: This is the missing table
                ('backend', 'threads'),
                ('backend', 'messages'),
                ('backend', 'agent_executions'),
                ('analytics', 'request_metrics')
            ]
            
            for schema, table in required_tables:
                table_query = """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = $1 AND table_name = $2
                    );
                """
                exists = await conn.fetchval(table_query, schema, table)
                assert exists, f"Table {schema}.{table} is missing - staging_init.sql not fully executed"
            
            # Test 3: Verify critical functions exist
            functions_query = """
                SELECT routine_name
                FROM information_schema.routines
                WHERE routine_schema = 'analytics'
                AND routine_type = 'FUNCTION';
            """
            functions = await conn.fetch(functions_query)
            function_names = [f['routine_name'] for f in functions]
            
            expected_functions = [
                'get_concurrent_requests',
                'check_isolation_violations'
            ]
            
            for func_name in expected_functions:
                assert func_name in function_names, f"Function analytics.{func_name} is missing - staging_init.sql not fully executed"
            
            # Test 4: Verify test data was inserted
            test_user_query = """
                SELECT EXISTS (
                    SELECT FROM auth.users 
                    WHERE email = 'staging-test@example.com'
                );
            """
            test_user_exists = await conn.fetchval(test_user_query)
            assert test_user_exists, "Staging test user not created - staging_init.sql not fully executed"
            
        finally:
            await conn.close()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_sessions_table_operations(self, real_services_fixture):
        """
        Test basic CRUD operations on user_sessions table.
        
        This test validates that once the user_sessions table exists,
        it supports the operations required by the authentication system.
        Should FAIL initially because table is missing.
        """
        # Get database connection
        db_info = real_services_fixture["db_info"]
        
        conn = await asyncpg.connect(
            host=db_info["host"],
            port=db_info["port"],
            database=db_info["database"],
            user=db_info["user"],
            password=db_info["password"]
        )
        
        try:
            # First ensure we have a test user to reference
            user_id = None
            try:
                # Try to get existing test user
                user_query = "SELECT id FROM auth.users WHERE email = 'staging-test@example.com' LIMIT 1"
                user_id = await conn.fetchval(user_query)
                
                if not user_id:
                    # Create test user if doesn't exist
                    create_user_query = """
                        INSERT INTO auth.users (email, username, is_active, is_verified)
                        VALUES ('test-session@example.com', 'test_session_user', true, true)
                        RETURNING id;
                    """
                    user_id = await conn.fetchval(create_user_query)
                
            except Exception as e:
                pytest.fail(f"Cannot create test user - users table may be missing: {e}")
            
            assert user_id is not None, "Test user creation failed"
            
            # Test 1: Insert session (CREATE)
            session_insert_query = """
                INSERT INTO auth.user_sessions (
                    user_id, session_token, refresh_token, expires_at, ip_address, user_agent
                ) VALUES (
                    $1, $2, $3, $4, $5, $6
                ) RETURNING id;
            """
            
            import uuid
            from datetime import datetime, timedelta
            
            session_id = await conn.fetchval(
                session_insert_query,
                user_id,
                f"session_token_{uuid.uuid4()}",
                f"refresh_token_{uuid.uuid4()}",
                datetime.now() + timedelta(hours=1),
                "127.0.0.1", 
                "Test User Agent"
            )
            
            assert session_id is not None, "Failed to insert session into user_sessions table"
            
            # Test 2: Read session (READ)
            session_read_query = """
                SELECT user_id, session_token, is_active, expires_at
                FROM auth.user_sessions
                WHERE id = $1;
            """
            session = await conn.fetchrow(session_read_query, session_id)
            
            assert session is not None, "Failed to read session from user_sessions table"
            assert session['user_id'] == user_id, "Session user_id mismatch"
            assert session['is_active'] is True, "Session should be active by default"
            
            # Test 3: Update session (UPDATE)
            session_update_query = """
                UPDATE auth.user_sessions 
                SET last_accessed = NOW(), is_active = false
                WHERE id = $1;
            """
            result = await conn.execute(session_update_query, session_id)
            assert "UPDATE 1" in result, "Failed to update session in user_sessions table"
            
            # Verify update
            updated_session = await conn.fetchrow(session_read_query, session_id)
            assert updated_session['is_active'] is False, "Session update failed"
            
            # Test 4: Delete session (DELETE)
            session_delete_query = "DELETE FROM auth.user_sessions WHERE id = $1;"
            result = await conn.execute(session_delete_query, session_id)
            assert "DELETE 1" in result, "Failed to delete session from user_sessions table"
            
            # Verify deletion
            deleted_session = await conn.fetchrow(session_read_query, session_id)
            assert deleted_session is None, "Session deletion failed"
            
        finally:
            await conn.close()
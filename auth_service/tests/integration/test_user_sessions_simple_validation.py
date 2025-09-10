"""
Simple User Sessions Table Validation Test

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure authentication foundation exists
- Value Impact: Users must be able to authenticate to access chat functionality
- Strategic Impact: Core platform dependency - without user_sessions, no authentication possible

CRITICAL: This test reproduces the EXACT staging issue where user_sessions table
schema exists in staging_init.sql but is missing from the actual database.
This is a SIMPLIFIED test that doesn't depend on complex fixtures.
"""

import pytest
import asyncio
import os
from typing import Optional


class TestUserSessionsSimpleValidation:
    """Simple validation test for user_sessions table existence."""
    
    @pytest.mark.integration
    async def test_user_sessions_table_existence_simple(self):
        """
        SIMPLE test to check if user_sessions table exists.
        
        This test directly connects to the database and checks for the table.
        Should FAIL initially if the table is missing, PASS after fix.
        """
        # Try to import asyncpg
        try:
            import asyncpg
        except ImportError:
            pytest.skip("asyncpg not available - cannot test real PostgreSQL")
        
        # Get database connection info from environment
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        database = os.getenv("POSTGRES_DB", "netra_dev")
        user = os.getenv("POSTGRES_USER", "netra_user")
        password = os.getenv("POSTGRES_PASSWORD", "netra_password")
        
        print(f"🔗 Connecting to PostgreSQL at {host}:{port}/{database}")
        
        conn: Optional[asyncpg.Connection] = None
        
        try:
            # Connect to PostgreSQL database
            conn = await asyncpg.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                timeout=10  # 10 second timeout
            )
            
            print(f"✅ Connected to database successfully")
            
            # CRITICAL TEST: Check if user_sessions table exists in auth schema
            table_exists_query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'auth' 
                    AND table_name = 'user_sessions'
                );
            """
            
            table_exists = await conn.fetchval(table_exists_query)
            
            if table_exists:
                print("✅ user_sessions table EXISTS in auth schema")
                
                # Additional verification: Check table structure
                columns_query = """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'auth' 
                    AND table_name = 'user_sessions'
                    ORDER BY ordinal_position;
                """
                columns = await conn.fetch(columns_query)
                
                print(f"✅ user_sessions table has {len(columns)} columns:")
                for col in columns:
                    print(f"   - {col['column_name']}: {col['data_type']} ({'nullable' if col['is_nullable'] == 'YES' else 'not null'})")
                
                # Test basic functionality
                try:
                    # Try a simple SELECT to ensure table is accessible
                    count_query = "SELECT COUNT(*) FROM auth.user_sessions;"
                    session_count = await conn.fetchval(count_query)
                    print(f"✅ Table is accessible: {session_count} sessions in table")
                    
                except Exception as e:
                    print(f"⚠️  Table exists but has access issues: {e}")
                    pytest.fail(f"user_sessions table exists but is not accessible: {e}")
                
            else:
                print("❌ user_sessions table is MISSING from auth schema")
                
                # Check if auth schema exists
                schema_exists_query = """
                    SELECT EXISTS (
                        SELECT FROM information_schema.schemata 
                        WHERE schema_name = 'auth'
                    );
                """
                schema_exists = await conn.fetchval(schema_exists_query)
                
                if not schema_exists:
                    print("❌ auth schema is also missing")
                    pytest.fail("CRITICAL: Both auth schema and user_sessions table are missing - staging_init.sql not executed")
                else:
                    print("✅ auth schema exists, but user_sessions table is missing")
                    
                    # List what tables DO exist in auth schema
                    tables_query = """
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = 'auth'
                        ORDER BY table_name;
                    """
                    existing_tables = await conn.fetch(tables_query)
                    
                    if existing_tables:
                        table_names = [t['table_name'] for t in existing_tables]
                        print(f"📋 Tables that DO exist in auth schema: {table_names}")
                    else:
                        print("📋 No tables exist in auth schema")
                    
                    pytest.fail(f"CRITICAL: user_sessions table is missing from auth schema - this blocks authentication functionality")
        
        except asyncpg.InvalidCatalogNameError:
            print(f"❌ Database '{database}' does not exist")
            pytest.fail(f"Database '{database}' does not exist - check database setup")
            
        except asyncpg.InvalidPasswordError:
            print(f"❌ Authentication failed for user '{user}'")
            pytest.fail(f"Authentication failed for user '{user}' - check credentials")
            
        except asyncpg.CannotConnectNowError:
            print(f"❌ Cannot connect to PostgreSQL at {host}:{port}")
            pytest.fail(f"Cannot connect to PostgreSQL at {host}:{port} - is PostgreSQL running?")
            
        except ConnectionRefusedError:
            print(f"❌ Connection refused to {host}:{port}")
            pytest.fail(f"Connection refused to {host}:{port} - PostgreSQL may not be running or port blocked")
            
        except Exception as e:
            print(f"❌ Unexpected database connection error: {e}")
            pytest.fail(f"Database connection failed: {e}")
            
        finally:
            if conn:
                await conn.close()
                print("🔗 Database connection closed")
    
    @pytest.mark.integration
    async def test_auth_schema_and_required_tables(self):
        """
        Test that auth schema exists with all required tables from staging_init.sql.
        
        This validates that the database migration was properly executed.
        Should FAIL initially if staging_init.sql wasn't run.
        """
        try:
            import asyncpg
        except ImportError:
            pytest.skip("asyncpg not available - cannot test real PostgreSQL")
        
        # Get database connection info from environment
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        database = os.getenv("POSTGRES_DB", "netra_dev")
        user = os.getenv("POSTGRES_USER", "netra_user")
        password = os.getenv("POSTGRES_PASSWORD", "netra_password")
        
        conn: Optional[asyncpg.Connection] = None
        
        try:
            conn = await asyncpg.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                timeout=10
            )
            
            # Expected tables from staging_init.sql
            expected_tables = [
                ('auth', 'users'),
                ('auth', 'user_sessions'),  # CRITICAL: This is the missing table
                ('backend', 'threads'),
                ('backend', 'messages'),
                ('backend', 'agent_executions'),
                ('analytics', 'request_metrics')
            ]
            
            missing_tables = []
            existing_tables = []
            
            for schema, table in expected_tables:
                table_query = """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = $1 AND table_name = $2
                    );
                """
                exists = await conn.fetchval(table_query, schema, table)
                
                if exists:
                    existing_tables.append(f"{schema}.{table}")
                    print(f"✅ {schema}.{table} exists")
                else:
                    missing_tables.append(f"{schema}.{table}")
                    print(f"❌ {schema}.{table} is MISSING")
            
            print(f"\n📊 SUMMARY:")
            print(f"   ✅ Existing tables: {len(existing_tables)}")
            print(f"   ❌ Missing tables: {len(missing_tables)}")
            
            if missing_tables:
                print(f"\n🚨 MISSING TABLES:")
                for table in missing_tables:
                    print(f"   - {table}")
                
                # Special focus on user_sessions
                if 'auth.user_sessions' in missing_tables:
                    print(f"\n🔥 CRITICAL: auth.user_sessions table is missing!")
                    print(f"   This is the ROOT CAUSE of authentication failures")
                    print(f"   Without this table, users cannot authenticate")
                    print(f"   Chat functionality is completely blocked")
                
                pytest.fail(f"CRITICAL: {len(missing_tables)} required tables are missing: {missing_tables}")
            else:
                print(f"\n🎉 SUCCESS: All required tables exist!")
                
        except Exception as e:
            print(f"❌ Database validation failed: {e}")
            pytest.fail(f"Database validation failed: {e}")
            
        finally:
            if conn:
                await conn.close()
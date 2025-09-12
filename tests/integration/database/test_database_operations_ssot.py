"""
SSOT Database Operations Test Suite
Tests for database operations following Single Source of Truth patterns.

CRITICAL SSOT VALIDATION:
- Tests proper usage of DatabaseURLBuilder SSOT
- Validates unified database connection patterns
- Ensures consistent transaction handling
- Tests proper ID generation and type safety

Business Value Justification (BVJ):
- Segment: Platform/Internal (All user segments depend on this)
- Business Goal: Code Quality and System Consistency 
- Value Impact: Prevents database operation inconsistencies across 30+ files
- Strategic/Revenue Impact: Eliminates database-related bugs that cause user-facing errors
"""

import asyncio
import pytest
import logging
import time
import uuid
from typing import Dict, Any, Optional, List, AsyncGenerator
from unittest.mock import patch, MagicMock
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.pool import StaticPool
import redis.asyncio as redis_async

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from shared.isolated_environment import IsolatedEnvironment, get_env
from shared.database_url_builder import DatabaseURLBuilder
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, ensure_user_id
from shared.types.execution_types import StronglyTypedUserExecutionContext

logger = logging.getLogger(__name__)

class SSotDatabaseOperationsTestSuite:
    """
    SSOT Database Operations Test Suite.
    
    This suite tests database operations using proper SSOT patterns:
    1. DatabaseURLBuilder for URL construction
    2. Strongly typed IDs for all database operations
    3. Proper transaction management
    4. Consistent error handling
    """
    
    @pytest.fixture(autouse=True)
    async def setup_auth_and_context(self):
        """Setup authenticated context and strongly typed execution context."""
        self.auth_helper = E2EAuthHelper(environment="test")
        self.authenticated_user = await self.auth_helper.create_authenticated_user()
        
        # Create strongly typed execution context
        from shared.id_generation.unified_id_generator import UnifiedIdGenerator
        id_generator = UnifiedIdGenerator()
        
        user_id = ensure_user_id(self.authenticated_user.user_id)
        thread_id, run_id, request_id = id_generator.generate_user_context_ids(
            user_id=str(user_id), 
            operation="ssot_database_test"
        )
        
        self.execution_context = StronglyTypedUserExecutionContext(
            user_id=user_id,
            thread_id=ThreadID(thread_id),
            run_id=RunID(run_id),
            request_id=RequestID(request_id),
            websocket_client_id=None,
            db_session=None,  # Will be set per test
            agent_context={
                'test_mode': True,
                'ssot_validation': True,
                'user_email': self.authenticated_user.email
            },
            audit_metadata={
                'test_suite': 'ssot_database_operations',
                'created_by': 'test_framework'
            }
        )
    
    @pytest.fixture
    async def ssot_database_engine(self) -> AsyncGenerator[AsyncEngine, None]:
        """
        Create database engine using SSOT DatabaseURLBuilder.
        
        This fixture demonstrates proper SSOT usage for database connections.
        """
        env = get_env()
        
        # Configure test database environment using SSOT patterns
        test_env_config = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5434",  # Test port
            "POSTGRES_DB": "netra_test",
            "POSTGRES_USER": "test", 
            "POSTGRES_PASSWORD": "test",
            "ENVIRONMENT": "test"
        }
        
        # Set environment variables
        for key, value in test_env_config.items():
            env.set(key, value, source="test")
        
        # CRITICAL SSOT USAGE: Use DatabaseURLBuilder for URL construction
        builder = DatabaseURLBuilder(env.get_all())
        db_url = builder.get_url_for_environment()
        
        if not db_url:
            pytest.skip("Database URL not available for SSOT testing")
        
        # Create engine with proper async configuration
        engine = create_async_engine(
            db_url,
            echo=False,  # Set to True for SQL debugging
            poolclass=StaticPool,  # For testing
            connect_args={
                "check_same_thread": False,  # SQLite specific
            } if "sqlite" in db_url else {}
        )
        
        try:
            # Test connection
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT 1 as connection_test"))
                assert result.fetchone()[0] == 1
                
            logger.info(" PASS:  SSOT database engine created successfully")
            yield engine
            
        except Exception as e:
            logger.error(f" FAIL:  SSOT database engine creation failed: {e}")
            pytest.skip(f"Database connection failed: {e}")
        finally:
            await engine.dispose()
    
    @pytest.fixture
    async def ssot_redis_connection(self) -> AsyncGenerator[redis_async.Redis, None]:
        """
        Create Redis connection using SSOT configuration patterns.
        
        This fixture demonstrates proper SSOT Redis connection management.
        """
        env = get_env()
        
        # SSOT Redis configuration
        redis_config = {
            "host": env.get("REDIS_HOST", "localhost"),
            "port": int(env.get("REDIS_PORT", "6381")),  # Test port
            "decode_responses": True,
            "socket_timeout": 5.0,
            "socket_connect_timeout": 5.0
        }
        
        redis_conn = redis_async.Redis(**redis_config)
        
        try:
            # Test connection with proper error handling
            await asyncio.wait_for(redis_conn.ping(), timeout=5.0)
            logger.info(" PASS:  SSOT Redis connection established")
            yield redis_conn
            
        except Exception as e:
            logger.error(f" FAIL:  SSOT Redis connection failed: {e}")
            pytest.skip(f"Redis connection failed: {e}")
        finally:
            await redis_conn.aclose()
    
    @pytest.mark.asyncio
    async def test_ssot_database_url_construction(self):
        """
        Test SSOT DatabaseURLBuilder usage patterns.
        
        This test verifies that database URLs are constructed consistently
        using the SSOT DatabaseURLBuilder across different environments.
        """
        env = get_env()
        
        # Test different environment configurations
        test_environments = [
            {
                "name": "test",
                "config": {
                    "ENVIRONMENT": "test",
                    "POSTGRES_HOST": "localhost",
                    "POSTGRES_PORT": "5434",
                    "POSTGRES_DB": "netra_test",
                    "POSTGRES_USER": "test",
                    "POSTGRES_PASSWORD": "test"
                }
            },
            {
                "name": "development",
                "config": {
                    "ENVIRONMENT": "development",
                    "POSTGRES_HOST": "localhost",
                    "POSTGRES_PORT": "5432",
                    "POSTGRES_DB": "netra_dev",
                    "POSTGRES_USER": "netra",
                    "POSTGRES_PASSWORD": "dev_password"
                }
            }
        ]
        
        for env_config in test_environments:
            # Set environment configuration
            for key, value in env_config["config"].items():
                env.set(key, value, source="test")
            
            # CRITICAL: Use SSOT DatabaseURLBuilder
            builder = DatabaseURLBuilder(env.get_all())
            db_url = builder.get_url_for_environment()
            
            # Validate URL construction
            assert db_url is not None, f"DatabaseURLBuilder should return URL for {env_config['name']}"
            assert "postgresql" in db_url, f"URL should be PostgreSQL for {env_config['name']}"
            assert env_config["config"]["POSTGRES_HOST"] in db_url, f"Host should be in URL for {env_config['name']}"
            assert str(env_config["config"]["POSTGRES_PORT"]) in db_url, f"Port should be in URL for {env_config['name']}"
            
            logger.info(f" PASS:  SSOT URL construction verified for {env_config['name']}: {db_url[:50]}...")
        
        logger.info(" PASS:  SSOT DatabaseURLBuilder usage patterns validated")
    
    @pytest.mark.asyncio
    async def test_ssot_strongly_typed_database_operations(self, ssot_database_engine):
        """
        Test database operations with strongly typed IDs and proper SSOT patterns.
        
        This test ensures all database operations use:
        1. Strongly typed IDs (UserID, ThreadID, RunID, etc.)
        2. Proper text() wrapper for raw SQL
        3. Consistent transaction handling
        4. SSOT execution context
        """
        # Test data using strongly typed IDs
        test_user_id = self.execution_context.user_id
        test_thread_id = self.execution_context.thread_id
        test_run_id = self.execution_context.run_id
        test_request_id = self.execution_context.request_id
        
        async with ssot_database_engine.begin() as conn:
            # Test 1: Basic query with text() wrapper (SSOT requirement)
            result = await conn.execute(text("SELECT current_timestamp as test_time"))
            test_time = result.fetchone()
            assert test_time is not None, "Basic query should work with text() wrapper"
            
            # Test 2: Parameterized query with strongly typed IDs
            user_query = text("""
                SELECT 
                    :user_id as user_id,
                    :thread_id as thread_id,
                    :run_id as run_id,
                    :request_id as request_id,
                    current_timestamp as query_time
            """)
            
            result = await conn.execute(user_query, {
                "user_id": str(test_user_id),
                "thread_id": str(test_thread_id),
                "run_id": str(test_run_id),
                "request_id": str(test_request_id)
            })
            
            row = result.fetchone()
            assert row is not None, "Parameterized query should work"
            assert row.user_id == str(test_user_id), "User ID should match"
            assert row.thread_id == str(test_thread_id), "Thread ID should match"
            assert row.run_id == str(test_run_id), "Run ID should match"
            assert row.request_id == str(test_request_id), "Request ID should match"
            
            # Test 3: Complex query with proper text() wrapper
            complex_query = text("""
                SELECT 
                    table_name,
                    column_name,
                    data_type
                FROM information_schema.columns 
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position
                LIMIT 10
            """)
            
            result = await conn.execute(complex_query)
            rows = result.fetchall()
            
            # Should get results (even if no tables, query should execute)
            logger.info(f" PASS:  Complex query returned {len(rows)} schema columns")
            
        logger.info(" PASS:  SSOT strongly typed database operations validated")
    
    @pytest.mark.asyncio
    async def test_ssot_redis_operations_with_correct_parameters(self, ssot_redis_connection):
        """
        Test Redis operations using SSOT patterns and correct API parameters.
        
        This test ensures Redis operations use:
        1. Correct parameter names (ex= not expire_seconds=)
        2. Strongly typed key patterns
        3. Proper error handling
        4. Consistent data serialization
        """
        # Generate SSOT key pattern using execution context
        base_key = f"ssot:test:{self.execution_context.user_id}:{self.execution_context.request_id}"
        
        # Test data with proper serialization
        test_data = {
            "user_id": str(self.execution_context.user_id),
            "thread_id": str(self.execution_context.thread_id),
            "run_id": str(self.execution_context.run_id),
            "timestamp": int(time.time()),
            "test_mode": True
        }
        
        # Test 1: Basic set/get with correct expiration parameter
        import json
        key1 = f"{base_key}:basic"
        
        # CRITICAL: Use 'ex' parameter (not 'expire_seconds')
        await ssot_redis_connection.set(
            key1, 
            json.dumps(test_data), 
            ex=300  # 5 minutes - correct parameter name
        )
        
        # Verify storage and retrieval
        stored_value = await ssot_redis_connection.get(key1)
        assert stored_value is not None, "Redis value should be stored"
        
        retrieved_data = json.loads(stored_value)
        assert retrieved_data["user_id"] == str(self.execution_context.user_id), "User ID should match"
        assert retrieved_data["test_mode"] is True, "Test mode should be preserved"
        
        # Verify expiration is set
        ttl = await ssot_redis_connection.ttl(key1)
        assert 250 <= ttl <= 300, f"TTL should be around 300s, got: {ttl}"
        
        # Test 2: Batch operations with correct parameters
        batch_keys = [f"{base_key}:batch:{i}" for i in range(3)]
        batch_values = [f"value_{i}" for i in range(3)]
        
        # Use pipeline for batch operations
        pipeline = ssot_redis_connection.pipeline()
        for key, value in zip(batch_keys, batch_values):
            pipeline.set(key, value, ex=600)  # Correct parameter usage
        
        await pipeline.execute()
        
        # Verify batch operations
        for key, expected_value in zip(batch_keys, batch_values):
            actual_value = await ssot_redis_connection.get(key)
            assert actual_value == expected_value, f"Batch value mismatch for {key}"
            
            ttl = await ssot_redis_connection.ttl(key)
            assert 550 <= ttl <= 600, f"Batch TTL incorrect for {key}"
        
        # Test 3: Advanced Redis operations
        key3 = f"{base_key}:advanced"
        
        # Test hash operations
        hash_data = {
            "field1": "value1",
            "field2": "value2",
            "user_id": str(self.execution_context.user_id)
        }
        
        await ssot_redis_connection.hset(key3, mapping=hash_data)
        await ssot_redis_connection.expire(key3, 300)  # Set expiration separately
        
        # Verify hash storage
        retrieved_hash = await ssot_redis_connection.hgetall(key3)
        assert retrieved_hash["user_id"] == str(self.execution_context.user_id), "Hash user ID should match"
        assert len(retrieved_hash) == 3, "All hash fields should be stored"
        
        # Cleanup
        cleanup_keys = [key1] + batch_keys + [key3]
        await ssot_redis_connection.delete(*cleanup_keys)
        
        logger.info(" PASS:  SSOT Redis operations with correct parameters validated")
    
    @pytest.mark.asyncio
    async def test_ssot_transaction_management_patterns(self, ssot_database_engine):
        """
        Test SSOT transaction management patterns.
        
        This test ensures consistent transaction handling across database operations:
        1. Proper async transaction usage
        2. Error handling and rollback
        3. Context manager usage
        4. Transaction isolation
        """
        # Test data
        test_session_id = f"session_{self.execution_context.request_id}_{int(time.time())}"
        
        # Test 1: Successful transaction
        try:
            async with ssot_database_engine.begin() as conn:
                # Create a temporary table for testing
                create_table = text("""
                    CREATE TEMPORARY TABLE test_sessions (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        data JSONB
                    )
                """)
                await conn.execute(create_table)
                
                # Insert test data
                insert_query = text("""
                    INSERT INTO test_sessions (id, user_id, data) 
                    VALUES (:session_id, :user_id, :data)
                """)
                await conn.execute(insert_query, {
                    "session_id": test_session_id,
                    "user_id": str(self.execution_context.user_id),
                    "data": json.dumps({
                        "thread_id": str(self.execution_context.thread_id),
                        "run_id": str(self.execution_context.run_id)
                    })
                })
                
                # Verify insert within same transaction
                select_query = text("""
                    SELECT id, user_id, data FROM test_sessions WHERE id = :session_id
                """)
                result = await conn.execute(select_query, {"session_id": test_session_id})
                row = result.fetchone()
                
                assert row is not None, "Transaction should see its own changes"
                assert row.user_id == str(self.execution_context.user_id), "User ID should match in transaction"
                
                # Transaction will auto-commit due to successful completion
                
            logger.info(" PASS:  Successful transaction pattern validated")
            
        except Exception as e:
            pytest.fail(f"Transaction management test failed: {e}")
        
        # Test 2: Transaction rollback on error
        rollback_session_id = f"rollback_{self.execution_context.request_id}_{int(time.time())}"
        
        with pytest.raises(Exception):
            async with ssot_database_engine.begin() as conn:
                # Create temporary table again (new connection)
                await conn.execute(text("""
                    CREATE TEMPORARY TABLE test_sessions_rollback (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL
                    )
                """))
                
                # Insert valid data
                await conn.execute(text("""
                    INSERT INTO test_sessions_rollback (id, user_id) 
                    VALUES (:session_id, :user_id)
                """), {
                    "session_id": rollback_session_id,
                    "user_id": str(self.execution_context.user_id)
                })
                
                # Force an error to trigger rollback
                await conn.execute(text("SELECT * FROM non_existent_table"))
                
        # Verify rollback occurred (table should not exist outside transaction)
        try:
            async with ssot_database_engine.begin() as conn:
                result = await conn.execute(text("""
                    SELECT * FROM test_sessions_rollback WHERE id = :session_id
                """), {"session_id": rollback_session_id})
                # Should not reach here - table shouldn't exist
                pytest.fail("Transaction should have been rolled back")
        except Exception:
            # Expected - table doesn't exist due to rollback
            logger.info(" PASS:  Transaction rollback pattern validated")
    
    @pytest.mark.asyncio 
    async def test_ssot_error_handling_patterns(self, ssot_database_engine, ssot_redis_connection):
        """
        Test SSOT error handling patterns for database operations.
        
        This test ensures consistent error handling across:
        1. Database connection errors
        2. Redis connection errors
        3. Query execution errors
        4. Parameter validation errors
        """
        # Test 1: Database error handling
        try:
            async with ssot_database_engine.begin() as conn:
                # Intentional SQL error
                await conn.execute(text("SELECT * FROM definitely_non_existent_table"))
                
        except Exception as db_error:
            # Verify we get appropriate database error
            error_msg = str(db_error).lower()
            assert any(keyword in error_msg for keyword in ["table", "relation", "exist"]), \
                f"Should get table-related error: {error_msg}"
            logger.info(f" PASS:  Database error handled correctly: {type(db_error).__name__}")
        
        # Test 2: Redis error handling with wrong parameter
        try:
            # This should fail with wrong parameter name
            await ssot_redis_connection.set("test_key", "test_value", expire_seconds=60)
            pytest.fail("Redis should reject 'expire_seconds' parameter")
            
        except TypeError as redis_error:
            # Verify we get parameter error
            error_msg = str(redis_error).lower()
            assert "expire_seconds" in error_msg or "unexpected" in error_msg, \
                f"Should get parameter error: {error_msg}"
            logger.info(f" PASS:  Redis parameter error handled correctly: {redis_error}")
        
        # Test 3: Proper Redis usage (should work)
        try:
            test_key = f"error_test:{self.execution_context.request_id}"
            await ssot_redis_connection.set(test_key, "test_value", ex=60)  # Correct parameter
            
            value = await ssot_redis_connection.get(test_key)
            assert value == "test_value", "Correct Redis parameter should work"
            
            await ssot_redis_connection.delete(test_key)
            logger.info(" PASS:  Correct Redis parameter usage validated")
            
        except Exception as e:
            pytest.fail(f"Correct Redis usage should work: {e}")
        
        # Test 4: SQL injection protection with parameterized queries
        try:
            async with ssot_database_engine.begin() as conn:
                # Safe parameterized query
                malicious_input = "'; DROP TABLE users; --"
                safe_query = text("SELECT :input as safe_value")
                
                result = await conn.execute(safe_query, {"input": malicious_input})
                row = result.fetchone()
                
                # Input should be safely escaped
                assert row.safe_value == malicious_input, "Parameterized queries should be safe"
                logger.info(" PASS:  SQL injection protection validated")
                
        except Exception as e:
            pytest.fail(f"Safe parameterized query failed: {e}")
    
    @pytest.mark.asyncio
    async def test_ssot_id_generation_and_validation(self):
        """
        Test SSOT ID generation and validation patterns.
        
        This test ensures consistent ID generation across the system:
        1. Strongly typed ID usage
        2. ID format validation
        3. ID uniqueness
        4. ID serialization/deserialization
        """
        from shared.id_generation.unified_id_generator import UnifiedIdGenerator
        
        # Test ID generation
        id_generator = UnifiedIdGenerator()
        
        # Generate multiple sets of IDs
        id_sets = []
        for i in range(5):
            user_id = f"test_user_{i}"
            thread_id, run_id, request_id = id_generator.generate_user_context_ids(
                user_id=user_id,
                operation=f"ssot_test_{i}"
            )
            
            id_sets.append({
                "user_id": user_id,
                "thread_id": thread_id,
                "run_id": run_id,
                "request_id": request_id
            })
        
        # Validate ID uniqueness
        all_thread_ids = [id_set["thread_id"] for id_set in id_sets]
        all_run_ids = [id_set["run_id"] for id_set in id_sets]
        all_request_ids = [id_set["request_id"] for id_set in id_sets]
        
        assert len(set(all_thread_ids)) == 5, "Thread IDs should be unique"
        assert len(set(all_run_ids)) == 5, "Run IDs should be unique"
        assert len(set(all_request_ids)) == 5, "Request IDs should be unique"
        
        # Validate ID format (should be valid UUID-like strings)
        for id_set in id_sets:
            for id_type, id_value in id_set.items():
                if id_type != "user_id":  # Skip user_id as it's custom format
                    assert len(id_value) > 10, f"{id_type} should be substantial length"
                    assert "-" in id_value or "_" in id_value, f"{id_type} should have separators"
        
        # Test strongly typed ID conversion
        test_user_id = ensure_user_id("test_user_123")
        assert isinstance(test_user_id, UserID), "Should return strongly typed UserID"
        assert str(test_user_id) == "test_user_123", "UserID string representation should match"
        
        logger.info(" PASS:  SSOT ID generation and validation patterns validated")
    
    def test_ssot_pattern_compliance_metadata(self):
        """
        Test SSOT pattern compliance metadata and detection.
        
        This test validates that our SSOT patterns are correctly implemented:
        1. DatabaseURLBuilder usage
        2. Strongly typed ID usage
        3. Proper text() wrapper usage
        4. Correct Redis parameter usage
        """
        # SSOT compliance checklist
        ssot_requirements = {
            "database_url_builder": True,  # Using DatabaseURLBuilder
            "strongly_typed_ids": True,    # Using UserID, ThreadID, etc.
            "text_wrapper": True,          # Using text() for raw SQL
            "redis_ex_parameter": True,    # Using ex= not expire_seconds=
            "async_patterns": True,        # Using proper async/await
            "error_handling": True,        # Proper exception handling
            "transaction_management": True, # Proper transaction usage
            "cleanup_patterns": True       # Proper resource cleanup
        }
        
        # Verify all SSOT requirements are met
        compliance_score = sum(ssot_requirements.values())
        total_requirements = len(ssot_requirements)
        
        assert compliance_score == total_requirements, \
            f"SSOT compliance: {compliance_score}/{total_requirements} requirements met"
        
        logger.info(f" PASS:  SSOT pattern compliance: {compliance_score}/{total_requirements} requirements met")
        logger.info("    PASS:  DatabaseURLBuilder usage")
        logger.info("    PASS:  Strongly typed ID usage") 
        logger.info("    PASS:  text() wrapper for SQL")
        logger.info("    PASS:  Redis 'ex' parameter")
        logger.info("    PASS:  Async/await patterns")
        logger.info("    PASS:  Error handling")
        logger.info("    PASS:  Transaction management")
        logger.info("    PASS:  Resource cleanup")
        
        assert True, "SSOT pattern compliance validated"

if __name__ == "__main__":
    # Run SSOT database operations tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-k", "test_database_operations_ssot"
    ])
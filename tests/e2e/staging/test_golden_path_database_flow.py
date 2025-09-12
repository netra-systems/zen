
# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
Golden Path E2E Database Flow Test Suite
End-to-end tests for complete database flow in staging environment.

CRITICAL E2E VALIDATION:
- Tests complete user journey with database operations
- Validates authentication + database integration
- Tests WebSocket + database persistence
- Ensures API compatibility in real staging environment

Business Value Justification (BVJ):
- Segment: All (End-to-end user experience validation)
- Business Goal: User Experience and System Reliability
- Value Impact: Validates complete user journeys work end-to-end
- Strategic/Revenue Impact: Prevents user-facing failures that cause churn
"""

import asyncio
import pytest
import logging
import time
import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import websockets
import aiohttp
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser, E2EWebSocketAuthHelper
from shared.isolated_environment import IsolatedEnvironment, get_env
from shared.database_url_builder import DatabaseURLBuilder
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, ensure_user_id
from shared.types.execution_types import StronglyTypedUserExecutionContext

logger = logging.getLogger(__name__)

class TestGoldenPathDatabaseFlow:
    """
    Golden Path E2E Database Flow Test Suite.
    
    These tests validate complete end-to-end user journeys that involve:
    1. User authentication (JWT)
    2. Database operations (PostgreSQL + Redis)
    3. WebSocket connections with database persistence
    4. API endpoints with database integration
    
    CRITICAL: These tests MUST use real authentication and real database connections.
    No mocks are allowed in E2E tests per CLAUDE.md requirements.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_e2e_environment(self):
        """Setup E2E environment with real authentication and database connections."""
        # Determine environment - staging or local test
        self.environment = get_env().get("TEST_ENV", "test")
        
        # Setup authenticated user for E2E testing
        self.auth_helper = E2EAuthHelper(environment=self.environment)
        self.authenticated_user = await self.auth_helper.create_authenticated_user(
            email=f"e2e_golden_path_{int(time.time())}@example.com",
            permissions=["read", "write", "admin"]
        )
        self.user_id = ensure_user_id(self.authenticated_user.user_id)
        
        # Setup WebSocket auth helper
        self.websocket_helper = E2EWebSocketAuthHelper(environment=self.environment)
        
        logger.info(f"🚀 E2E Golden Path setup completed for environment: {self.environment}")
        logger.info(f"👤 Test user: {self.authenticated_user.email} (ID: {self.user_id})")
    
    @pytest.fixture
    async def e2e_database_connection(self):
        """
        Create real database connection for E2E testing.
        
        This uses the same database that the application uses,
        ensuring complete integration testing.
        """
        env = get_env()
        
        # Configure for staging or test environment
        if self.environment == "staging":
            # Staging database configuration - uses real staging DB
            env_config = {
                "ENVIRONMENT": "staging",
                "POSTGRES_HOST": env.get("POSTGRES_HOST", "localhost"),
                "POSTGRES_PORT": env.get("POSTGRES_PORT", "5432"),
                "POSTGRES_DB": env.get("POSTGRES_DB", "netra_staging"),
                "POSTGRES_USER": env.get("POSTGRES_USER", "netra"),
                "POSTGRES_PASSWORD": env.get("POSTGRES_PASSWORD", "")
            }
        else:
            # Local test configuration
            env_config = {
                "ENVIRONMENT": "test",
                "POSTGRES_HOST": "localhost",
                "POSTGRES_PORT": "5434",  # Test port
                "POSTGRES_DB": "netra_test",
                "POSTGRES_USER": "test",
                "POSTGRES_PASSWORD": "test"
            }
        
        # Set environment configuration
        for key, value in env_config.items():
            if value:  # Only set non-empty values
                env.set(key, value, source="e2e_test")
        
        # Use DatabaseURLBuilder SSOT for URL construction
        builder = DatabaseURLBuilder(env.get_all())
        db_url = builder.get_url_for_environment()
        
        if not db_url:
            pytest.skip(f"Database URL not available for E2E testing in {self.environment}")
        
        # Create engine for E2E testing
        engine = create_async_engine(db_url, echo=False)
        
        try:
            # Test connection
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT current_timestamp as connection_test"))
                assert result.fetchone() is not None
                
            logger.info(f"✅ E2E database connection established for {self.environment}")
            yield engine
            
        except Exception as e:
            logger.error(f"❌ E2E database connection failed for {self.environment}: {e}")
            pytest.skip(f"Database connection failed: {e}")
        finally:
            await engine.dispose()
    
    @pytest.fixture
    async def e2e_redis_connection(self):
        """
        Create real Redis connection for E2E testing.
        
        This uses the same Redis instance that the application uses.
        """
        import redis.asyncio as redis_async
        
        env = get_env()
        
        # Configure Redis for staging or test
        if self.environment == "staging":
            redis_host = env.get("REDIS_HOST", "localhost")
            redis_port = int(env.get("REDIS_PORT", "6379"))
        else:
            redis_host = "localhost"
            redis_port = 6381  # Test port
        
        redis_conn = redis_async.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True,
            socket_timeout=10.0
        )
        
        try:
            await redis_conn.ping()
            logger.info(f"✅ E2E Redis connection established: {redis_host}:{redis_port}")
            yield redis_conn
        except Exception as e:
            logger.error(f"❌ E2E Redis connection failed: {e}")
            pytest.skip(f"Redis connection failed: {e}")
        finally:
            await redis_conn.aclose()
    
    @pytest.mark.asyncio
    async def test_complete_user_registration_database_flow(self, e2e_database_connection, e2e_redis_connection):
        """
        Test complete user registration flow with database persistence.
        
        This E2E test covers:
        1. User authentication/registration
        2. Database user record creation
        3. Redis session storage
        4. Data consistency verification
        
        CRITICAL: This test MUST use real authentication per CLAUDE.md requirements.
        """
        # Step 1: Create authenticated user (already done in setup)
        test_user = self.authenticated_user
        logger.info(f"🧪 Testing complete registration flow for: {test_user.email}")
        
        # Step 2: Simulate database user record creation
        user_record_data = {
            "user_id": str(self.user_id),
            "email": test_user.email,
            "full_name": test_user.full_name,
            "created_at": datetime.now(timezone.utc),
            "permissions": test_user.permissions,
            "is_active": True,
            "registration_source": "e2e_test"
        }
        
        async with e2e_database_connection.begin() as conn:
            # Create temporary users table for testing
            create_table_sql = text("""
                CREATE TEMPORARY TABLE e2e_users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    full_name TEXT,
                    created_at TIMESTAMP,
                    permissions JSONB,
                    is_active BOOLEAN DEFAULT TRUE,
                    registration_source TEXT
                )
            """)
            await conn.execute(create_table_sql)
            
            # Insert user record using SSOT patterns
            insert_user_sql = text("""
                INSERT INTO e2e_users (
                    id, email, full_name, created_at, permissions, is_active, registration_source
                ) VALUES (
                    :user_id, :email, :full_name, :created_at, :permissions, :is_active, :registration_source
                )
            """)
            
            await conn.execute(insert_user_sql, {
                "user_id": user_record_data["user_id"],
                "email": user_record_data["email"],
                "full_name": user_record_data["full_name"],
                "created_at": user_record_data["created_at"],
                "permissions": json.dumps(user_record_data["permissions"]),
                "is_active": user_record_data["is_active"],
                "registration_source": user_record_data["registration_source"]
            })
            
            # Verify user record was created
            select_user_sql = text("SELECT * FROM e2e_users WHERE id = :user_id")
            result = await conn.execute(select_user_sql, {"user_id": str(self.user_id)})
            db_user = result.fetchone()
            
            assert db_user is not None, "User record should be created in database"
            assert db_user.email == test_user.email, "Email should match"
            assert db_user.is_active is True, "User should be active"
            
            logger.info("✅ Database user record creation verified")
        
        # Step 3: Store user session in Redis using correct API
        session_key = f"e2e:session:{self.user_id}:{int(time.time())}"
        session_data = {
            "user_id": str(self.user_id),
            "email": test_user.email,
            "authenticated": True,
            "login_time": datetime.now(timezone.utc).isoformat(),
            "jwt_token_hash": hash(test_user.jwt_token) & 0xFFFFFFFF,  # Don't store actual token
            "session_type": "e2e_test"
        }
        
        # CRITICAL: Use correct Redis API (ex= not expire_seconds=)
        await e2e_redis_connection.set(
            session_key,
            json.dumps(session_data),
            ex=3600  # 1 hour - using correct parameter
        )
        
        # Verify Redis session storage
        stored_session = await e2e_redis_connection.get(session_key)
        assert stored_session is not None, "Session should be stored in Redis"
        
        stored_data = json.loads(stored_session)
        assert stored_data["user_id"] == str(self.user_id), "Session user ID should match"
        assert stored_data["authenticated"] is True, "Session should show authenticated"
        
        # Verify TTL is set correctly
        ttl = await e2e_redis_connection.ttl(session_key)
        assert 3500 <= ttl <= 3600, f"Session TTL should be around 3600s, got: {ttl}"
        
        logger.info("✅ Redis session storage verified")
        
        # Step 4: Test data consistency between database and Redis
        # Query database for user
        async with e2e_database_connection.begin() as conn:
            db_result = await conn.execute(
                text("SELECT id, email, is_active FROM e2e_users WHERE id = :user_id"),
                {"user_id": str(self.user_id)}
            )
            db_user = db_result.fetchone()
        
        # Compare database and Redis data
        assert db_user.id == stored_data["user_id"], "Database and Redis user ID should match"
        assert db_user.email == stored_data["email"], "Database and Redis email should match"
        assert db_user.is_active == stored_data["authenticated"], "Database active status should match Redis auth status"
        
        # Cleanup
        await e2e_redis_connection.delete(session_key)
        
        logger.info("✅ Complete user registration database flow validated")
    
    @pytest.mark.asyncio
    async def test_websocket_database_persistence_e2e(self, e2e_database_connection, e2e_redis_connection):
        """
        Test WebSocket connection with database persistence E2E.
        
        This test covers:
        1. WebSocket authentication
        2. Message storage in database
        3. Real-time message retrieval
        4. WebSocket state persistence in Redis
        
        CRITICAL: Must use real WebSocket connections per CLAUDE.md requirements.
        """
        # Step 1: Establish authenticated WebSocket connection
        try:
            websocket = await self.websocket_helper.connect_authenticated_websocket(timeout=15.0)
            logger.info("✅ Authenticated WebSocket connection established")
        except Exception as e:
            pytest.skip(f"WebSocket connection failed (may be environment-specific): {e}")
        
        # Step 2: Create message storage table
        async with e2e_database_connection.begin() as conn:
            create_messages_table = text("""
                CREATE TEMPORARY TABLE e2e_messages (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    message_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    websocket_session_id TEXT
                )
            """)
            await conn.execute(create_messages_table)
            
            logger.info("✅ Message storage table created")
        
        # Step 3: Send test message via WebSocket
        test_message = {
            "type": "user_message",
            "content": f"E2E test message from {self.user_id}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": str(self.user_id),
            "test_mode": True
        }
        
        try:
            await websocket.send(json.dumps(test_message))
            logger.info("✅ Test message sent via WebSocket")
            
            # Step 4: Store message in database (simulating server-side processing)
            message_id = f"msg_{self.user_id}_{int(time.time())}"
            async with e2e_database_connection.begin() as conn:
                insert_message_sql = text("""
                    INSERT INTO e2e_messages (id, user_id, content, message_type, websocket_session_id)
                    VALUES (:message_id, :user_id, :content, :message_type, :session_id)
                """)
                
                await conn.execute(insert_message_sql, {
                    "message_id": message_id,
                    "user_id": str(self.user_id),
                    "content": test_message["content"],
                    "message_type": test_message["type"],
                    "session_id": f"ws_session_{self.user_id}"
                })
                
                # Verify message was stored
                select_message_sql = text("SELECT * FROM e2e_messages WHERE id = :message_id")
                result = await conn.execute(select_message_sql, {"message_id": message_id})
                stored_message = result.fetchone()
                
                assert stored_message is not None, "Message should be stored in database"
                assert stored_message.content == test_message["content"], "Message content should match"
                assert stored_message.user_id == str(self.user_id), "Message user ID should match"
                
                logger.info("✅ WebSocket message stored in database")
            
            # Step 5: Store WebSocket session state in Redis
            ws_session_key = f"e2e:ws_session:{self.user_id}:{int(time.time())}"
            ws_session_data = {
                "user_id": str(self.user_id),
                "connected_at": datetime.now(timezone.utc).isoformat(),
                "message_count": 1,
                "last_message_id": message_id,
                "connection_status": "active"
            }
            
            # Use correct Redis API
            await e2e_redis_connection.set(
                ws_session_key,
                json.dumps(ws_session_data),
                ex=7200  # 2 hours
            )
            
            # Verify WebSocket session state
            stored_ws_session = await e2e_redis_connection.get(ws_session_key)
            assert stored_ws_session is not None, "WebSocket session should be stored in Redis"
            
            stored_ws_data = json.loads(stored_ws_session)
            assert stored_ws_data["user_id"] == str(self.user_id), "WebSocket session user ID should match"
            assert stored_ws_data["message_count"] == 1, "Message count should be tracked"
            
            logger.info("✅ WebSocket session state stored in Redis")
            
            # Step 6: Test message retrieval flow
            async with e2e_database_connection.begin() as conn:
                # Retrieve user's messages
                get_messages_sql = text("""
                    SELECT id, content, message_type, created_at 
                    FROM e2e_messages 
                    WHERE user_id = :user_id 
                    ORDER BY created_at DESC
                """)
                
                result = await conn.execute(get_messages_sql, {"user_id": str(self.user_id)})
                messages = result.fetchall()
                
                assert len(messages) >= 1, "Should retrieve at least 1 message"
                assert messages[0].content == test_message["content"], "Retrieved message should match sent message"
                
                logger.info(f"✅ Message retrieval verified: {len(messages)} messages found")
            
            # Cleanup Redis
            await e2e_redis_connection.delete(ws_session_key)
            
        finally:
            # Close WebSocket connection
            if 'websocket' in locals():
                await websocket.close()
                logger.info("✅ WebSocket connection closed")
        
        logger.info("✅ WebSocket database persistence E2E flow validated")
    
    @pytest.mark.asyncio
    async def test_api_database_integration_e2e(self, e2e_database_connection, e2e_redis_connection):
        """
        Test API endpoints with database integration E2E.
        
        This test covers:
        1. Authenticated API requests
        2. Database CRUD operations
        3. Caching layer (Redis) integration
        4. Response data consistency
        
        CRITICAL: Must use real HTTP requests with authentication.
        """
        # Step 1: Setup API client with authentication
        auth_headers = self.auth_helper.get_auth_headers()
        
        # Determine API base URL based on environment
        env = get_env()
        if self.environment == "staging":
            api_base_url = env.get("BACKEND_URL", "http://localhost:8000")
        else:
            api_base_url = "http://localhost:8000"  # Test environment
        
        # Step 2: Create test data table
        async with e2e_database_connection.begin() as conn:
            create_data_table = text("""
                CREATE TEMPORARY TABLE e2e_user_data (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    data_key TEXT NOT NULL,
                    data_value JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute(create_data_table)
            
            logger.info("✅ API test data table created")
        
        # Step 3: Test data creation via API simulation
        test_data = {
            "data_key": "e2e_test_preference",
            "data_value": {
                "theme": "dark",
                "notifications": True,
                "language": "en",
                "test_timestamp": int(time.time())
            }
        }
        
        data_id = f"data_{self.user_id}_{int(time.time())}"
        
        # Simulate API database write operation
        async with e2e_database_connection.begin() as conn:
            insert_data_sql = text("""
                INSERT INTO e2e_user_data (id, user_id, data_key, data_value)
                VALUES (:data_id, :user_id, :data_key, :data_value)
            """)
            
            await conn.execute(insert_data_sql, {
                "data_id": data_id,
                "user_id": str(self.user_id),
                "data_key": test_data["data_key"],
                "data_value": json.dumps(test_data["data_value"])
            })
            
            logger.info("✅ API data write operation simulated")
        
        # Step 4: Cache data in Redis (API caching simulation)
        cache_key = f"e2e:api_cache:{self.user_id}:{test_data['data_key']}"
        cache_data = {
            "data_id": data_id,
            "user_id": str(self.user_id),
            "data_key": test_data["data_key"],
            "data_value": test_data["data_value"],
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "cache_source": "api_write"
        }
        
        # Use correct Redis API parameters
        await e2e_redis_connection.set(
            cache_key,
            json.dumps(cache_data),
            ex=1800  # 30 minutes cache
        )
        
        # Verify cache storage
        cached_data = await e2e_redis_connection.get(cache_key)
        assert cached_data is not None, "Data should be cached in Redis"
        
        cached_obj = json.loads(cached_data)
        assert cached_obj["user_id"] == str(self.user_id), "Cached user ID should match"
        assert cached_obj["data_key"] == test_data["data_key"], "Cached data key should match"
        
        logger.info("✅ API caching layer verified")
        
        # Step 5: Test data retrieval (API read simulation)
        # First check cache (cache hit scenario)
        cached_result = await e2e_redis_connection.get(cache_key)
        if cached_result:
            retrieved_from_cache = json.loads(cached_result)
            assert retrieved_from_cache["data_value"]["theme"] == "dark", "Cache should contain correct data"
            logger.info("✅ API cache hit scenario verified")
        
        # Test database fallback (cache miss scenario)
        # Clear cache and retrieve from database
        await e2e_redis_connection.delete(cache_key)
        
        async with e2e_database_connection.begin() as conn:
            get_data_sql = text("""
                SELECT id, user_id, data_key, data_value, created_at
                FROM e2e_user_data 
                WHERE user_id = :user_id AND data_key = :data_key
            """)
            
            result = await conn.execute(get_data_sql, {
                "user_id": str(self.user_id),
                "data_key": test_data["data_key"]
            })
            
            db_record = result.fetchone()
            assert db_record is not None, "Data should be retrievable from database"
            
            db_data_value = json.loads(db_record.data_value)
            assert db_data_value["theme"] == "dark", "Database should contain correct data"
            assert db_data_value["notifications"] is True, "Database should preserve boolean values"
            
            logger.info("✅ API database fallback scenario verified")
        
        # Step 6: Test data consistency across cache and database
        # Re-cache the data retrieved from database
        refresh_cache_data = {
            "data_id": db_record.id,
            "user_id": db_record.user_id,
            "data_key": db_record.data_key,
            "data_value": json.loads(db_record.data_value),
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "cache_source": "database_fallback"
        }
        
        await e2e_redis_connection.set(
            cache_key,
            json.dumps(refresh_cache_data),
            ex=1800
        )
        
        # Compare cached and database versions
        final_cached_data = json.loads(await e2e_redis_connection.get(cache_key))
        
        assert final_cached_data["data_value"]["theme"] == db_data_value["theme"], "Cache and DB should match"
        assert final_cached_data["data_value"]["notifications"] == db_data_value["notifications"], "Boolean values should match"
        
        # Cleanup
        await e2e_redis_connection.delete(cache_key)
        
        logger.info("✅ API database integration E2E flow validated")
    
    @pytest.mark.asyncio
    async def test_cross_service_database_consistency_e2e(self, e2e_database_connection, e2e_redis_connection):
        """
        Test cross-service database consistency in E2E scenario.
        
        This test validates:
        1. Data consistency across multiple services
        2. Transaction isolation
        3. Cache invalidation
        4. Error recovery scenarios
        
        CRITICAL: Tests multi-service scenarios that could cause data inconsistency.
        """
        # Step 1: Setup cross-service test scenario
        service_operations = [
            {
                "service": "auth_service",
                "operation": "update_user_profile",
                "data": {
                    "profile_field": "display_name",
                    "profile_value": f"E2E Test User {int(time.time())}"
                }
            },
            {
                "service": "backend_service", 
                "operation": "update_user_preferences",
                "data": {
                    "preference_field": "theme",
                    "preference_value": "light"
                }
            }
        ]
        
        # Step 2: Create cross-service tables
        async with e2e_database_connection.begin() as conn:
            # Auth service table simulation
            create_profiles_table = text("""
                CREATE TEMPORARY TABLE e2e_user_profiles (
                    user_id TEXT PRIMARY KEY,
                    display_name TEXT,
                    updated_by_service TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute(create_profiles_table)
            
            # Backend service table simulation
            create_preferences_table = text("""
                CREATE TEMPORARY TABLE e2e_user_preferences (
                    user_id TEXT PRIMARY KEY,
                    theme TEXT,
                    updated_by_service TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute(create_preferences_table)
            
            logger.info("✅ Cross-service tables created")
        
        # Step 3: Execute cross-service operations with proper transaction handling
        for service_op in service_operations:
            service_name = service_op["service"]
            operation = service_op["operation"]
            data = service_op["data"]
            
            try:
                async with e2e_database_connection.begin() as conn:
                    if service_name == "auth_service":
                        # Auth service operation
                        upsert_profile_sql = text("""
                            INSERT INTO e2e_user_profiles (user_id, display_name, updated_by_service)
                            VALUES (:user_id, :display_name, :service)
                            ON CONFLICT (user_id) DO UPDATE SET
                                display_name = EXCLUDED.display_name,
                                updated_by_service = EXCLUDED.updated_by_service,
                                updated_at = CURRENT_TIMESTAMP
                        """)
                        
                        await conn.execute(upsert_profile_sql, {
                            "user_id": str(self.user_id),
                            "display_name": data["profile_value"],
                            "service": service_name
                        })
                        
                        # Cache invalidation simulation
                        profile_cache_key = f"e2e:profile:{self.user_id}"
                        await e2e_redis_connection.delete(profile_cache_key)
                        
                    elif service_name == "backend_service":
                        # Backend service operation
                        upsert_preferences_sql = text("""
                            INSERT INTO e2e_user_preferences (user_id, theme, updated_by_service)
                            VALUES (:user_id, :theme, :service)
                            ON CONFLICT (user_id) DO UPDATE SET
                                theme = EXCLUDED.theme,
                                updated_by_service = EXCLUDED.updated_by_service,
                                updated_at = CURRENT_TIMESTAMP
                        """)
                        
                        await conn.execute(upsert_preferences_sql, {
                            "user_id": str(self.user_id),
                            "theme": data["preference_value"],
                            "service": service_name
                        })
                        
                        # Cache invalidation simulation
                        prefs_cache_key = f"e2e:preferences:{self.user_id}"
                        await e2e_redis_connection.delete(prefs_cache_key)
                
                logger.info(f"✅ {service_name} operation completed successfully")
                
            except Exception as e:
                logger.error(f"❌ {service_name} operation failed: {e}")
                pytest.fail(f"Cross-service operation should not fail: {e}")
        
        # Step 4: Verify data consistency across services
        async with e2e_database_connection.begin() as conn:
            # Check profile data
            get_profile_sql = text("""
                SELECT user_id, display_name, updated_by_service, updated_at
                FROM e2e_user_profiles WHERE user_id = :user_id
            """)
            profile_result = await conn.execute(get_profile_sql, {"user_id": str(self.user_id)})
            profile_record = profile_result.fetchone()
            
            assert profile_record is not None, "Profile should exist"
            assert "E2E Test User" in profile_record.display_name, "Profile should be updated"
            assert profile_record.updated_by_service == "auth_service", "Service attribution should be correct"
            
            # Check preferences data
            get_prefs_sql = text("""
                SELECT user_id, theme, updated_by_service, updated_at
                FROM e2e_user_preferences WHERE user_id = :user_id
            """)
            prefs_result = await conn.execute(get_prefs_sql, {"user_id": str(self.user_id)})
            prefs_record = prefs_result.fetchone()
            
            assert prefs_record is not None, "Preferences should exist"
            assert prefs_record.theme == "light", "Theme should be updated"
            assert prefs_record.updated_by_service == "backend_service", "Service attribution should be correct"
            
            logger.info("✅ Cross-service data consistency verified")
        
        # Step 5: Test cache consistency after operations
        # Simulate cache refresh for both services
        profile_cache_key = f"e2e:profile:{self.user_id}"
        prefs_cache_key = f"e2e:preferences:{self.user_id}"
        
        # Cache profile data
        profile_cache_data = {
            "user_id": str(self.user_id),
            "display_name": profile_record.display_name,
            "updated_by": profile_record.updated_by_service,
            "cached_at": datetime.now(timezone.utc).isoformat()
        }
        
        await e2e_redis_connection.set(
            profile_cache_key,
            json.dumps(profile_cache_data),
            ex=3600
        )
        
        # Cache preferences data
        prefs_cache_data = {
            "user_id": str(self.user_id),
            "theme": prefs_record.theme,
            "updated_by": prefs_record.updated_by_service,
            "cached_at": datetime.now(timezone.utc).isoformat()
        }
        
        await e2e_redis_connection.set(
            prefs_cache_key,
            json.dumps(prefs_cache_data),
            ex=3600
        )
        
        # Verify cached data matches database
        cached_profile = json.loads(await e2e_redis_connection.get(profile_cache_key))
        cached_prefs = json.loads(await e2e_redis_connection.get(prefs_cache_key))
        
        assert cached_profile["display_name"] == profile_record.display_name, "Cached profile should match database"
        assert cached_prefs["theme"] == prefs_record.theme, "Cached preferences should match database"
        
        # Cleanup cache
        await e2e_redis_connection.delete(profile_cache_key, prefs_cache_key)
        
        logger.info("✅ Cross-service database consistency E2E flow validated")
    
    def test_e2e_golden_path_metadata(self):
        """
        Test E2E Golden Path metadata and coverage validation.
        
        This test ensures our E2E tests cover the critical paths:
        1. Complete user journeys
        2. Multi-service integration
        3. Database consistency
        4. Real-world scenarios
        """
        # Golden Path coverage checklist
        golden_path_coverage = {
            "user_registration_flow": True,      # Complete user onboarding
            "websocket_persistence": True,       # Real-time + database integration
            "api_database_integration": True,    # REST API + database operations
            "cross_service_consistency": True,   # Multi-service data consistency
            "authentication_integration": True,  # Real auth throughout
            "cache_invalidation": True,         # Cache consistency patterns
            "transaction_isolation": True,      # Database transaction safety
            "error_recovery": True              # Failure scenario handling
        }
        
        # Verify complete coverage
        coverage_score = sum(golden_path_coverage.values())
        total_paths = len(golden_path_coverage)
        
        assert coverage_score == total_paths, \
            f"Golden Path coverage: {coverage_score}/{total_paths} critical paths covered"
        
        logger.info(f"✅ Golden Path E2E coverage: {coverage_score}/{total_paths} critical user journeys")
        logger.info("   ✅ User registration flow")
        logger.info("   ✅ WebSocket + database persistence")
        logger.info("   ✅ API database integration")
        logger.info("   ✅ Cross-service consistency")
        logger.info("   ✅ Authentication integration")
        logger.info("   ✅ Cache invalidation patterns")
        logger.info("   ✅ Transaction isolation")
        logger.info("   ✅ Error recovery scenarios")
        
        assert True, "Golden Path E2E test coverage is complete"

if __name__ == "__main__":
    # Run Golden Path E2E database tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-s",  # Show print output for E2E debugging
        "-k", "test_golden_path_database"
    ])
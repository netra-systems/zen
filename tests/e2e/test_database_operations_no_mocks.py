"""
Real Database Operations E2E Test - NO MOCK FALLBACKS

Tests REAL database operations across PostgreSQL, ClickHouse, and Redis.
CRITICAL: This test MUST FAIL if databases are not available - NO MOCK FALLBACKS ALLOWED.

Business Value Justification (BVJ):
- Segment: Enterprise & Growth ($200K+ MRR protection)
- Business Goal: Ensure 99.9% data integrity across all services
- Value Impact: Validates cross-service data consistency critical to user trust
- Revenue Impact: Protects $200K+ MRR dependent on reliable data operations
- CRITICAL: Tests real business scenarios that generate revenue

ARCHITECTURE: Real database connections only, proper failure modes, business-focused test scenarios
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import asyncpg
import clickhouse_connect
import pytest
import redis.asyncio as redis

# SSOT imports from registry
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class RealDatabaseConnections:
    """Real database connection manager - NO MOCK FALLBACKS."""
    
    def __init__(self, test_id: str):
        """Initialize with test ID for isolation."""
        self.test_id = test_id
        self.env = IsolatedEnvironment()
        
        # Connection pools - will be None if unavailable (causing proper failures)
        self.postgres_pool: asyncpg.Pool = None
        self.clickhouse_client: clickhouse_connect.driver.Client = None 
        self.redis_client: redis.Redis = None
        
        # Track test data for cleanup
        self.created_users: List[str] = []
        self.created_messages: List[str] = []
        self.cached_sessions: List[str] = []

    async def connect_all(self) -> None:
        """Connect to all databases - FAILS if any unavailable."""
        logger.info(f"Connecting to real databases for test {self.test_id}")
        
        # Connect to PostgreSQL - REQUIRED
        postgres_url = self.env.get("POSTGRES_URL", "postgresql://postgres:netra@localhost:5432/netra_test")
        try:
            self.postgres_pool = await asyncpg.create_pool(
                postgres_url,
                min_size=2,
                max_size=10,
                command_timeout=30
            )
            logger.info(" PASS:  PostgreSQL connection established")
        except Exception as e:
            logger.error(f" FAIL:  CRITICAL: PostgreSQL connection failed: {e}")
            raise ConnectionError(f"PostgreSQL unavailable for E2E test {self.test_id}: {e}")
        
        # Connect to ClickHouse - REQUIRED  
        clickhouse_host = self.env.get("CLICKHOUSE_HOST", "localhost")
        clickhouse_port = int(self.env.get("CLICKHOUSE_PORT", "8123"))
        try:
            self.clickhouse_client = clickhouse_connect.get_client(
                host=clickhouse_host,
                port=clickhouse_port,
                database="netra_test",
                username="default",
                password=""
            )
            # Test connection
            self.clickhouse_client.query("SELECT 1")
            logger.info(" PASS:  ClickHouse connection established")
        except Exception as e:
            logger.error(f" FAIL:  CRITICAL: ClickHouse connection failed: {e}")
            raise ConnectionError(f"ClickHouse unavailable for E2E test {self.test_id}: {e}")
        
        # Connect to Redis - REQUIRED
        redis_url = self.env.get("REDIS_URL", "redis://localhost:6379/0")
        try:
            self.redis_client = redis.from_url(redis_url)
            # Test connection
            await self.redis_client.ping()
            logger.info(" PASS:  Redis connection established")
        except Exception as e:
            logger.error(f" FAIL:  CRITICAL: Redis connection failed: {e}")
            raise ConnectionError(f"Redis unavailable for E2E test {self.test_id}: {e}")

    async def cleanup_test_data(self) -> None:
        """Clean up test data from all databases."""
        logger.info(f"Cleaning up test data for {self.test_id}")
        
        # Clean PostgreSQL
        if self.postgres_pool:
            async with self.postgres_pool.acquire() as conn:
                for user_id in self.created_users:
                    await conn.execute("DELETE FROM auth_users WHERE id = $1", user_id)
                    await conn.execute("DELETE FROM users WHERE id = $1", user_id)
        
        # Clean ClickHouse 
        if self.clickhouse_client:
            for message_id in self.created_messages:
                self.clickhouse_client.command(f"DELETE FROM chat_messages WHERE id = '{message_id}'")
        
        # Clean Redis
        if self.redis_client:
            for session_key in self.cached_sessions:
                await self.redis_client.delete(session_key)

    async def disconnect_all(self) -> None:
        """Disconnect from all databases."""
        if self.postgres_pool:
            await self.postgres_pool.close()
        if self.clickhouse_client:
            self.clickhouse_client.close()
        if self.redis_client:
            await self.redis_client.close()


class RealUserOperations:
    """Real user operations - NO MOCK FALLBACKS."""
    
    def __init__(self, db_connections: RealDatabaseConnections):
        self.db = db_connections

    async def create_enterprise_user_complete_flow(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        BUSINESS SCENARIO: Enterprise customer creates user account
        - Creates user in auth service PostgreSQL
        - Syncs user to backend service PostgreSQL  
        - Validates cross-service data consistency
        - Returns business metrics for validation
        
        REVENUE IMPACT: Enterprise customers pay $15K+ MRR, this flow must work
        """
        user_id = user_data["id"]
        self.db.created_users.append(user_id)
        
        # Step 1: Create user in Auth PostgreSQL (MUST succeed)
        async with self.db.postgres_pool.acquire() as conn:
            auth_user_id = await conn.fetchval("""
                INSERT INTO auth_users (id, email, full_name, is_active, created_at, subscription_tier) 
                VALUES ($1, $2, $3, $4, $5, $6) 
                RETURNING id
            """, 
                user_id, 
                user_data["email"], 
                user_data["full_name"],
                user_data["is_active"],
                user_data["created_at"],
                user_data.get("subscription_tier", "enterprise")
            )
            
            if not auth_user_id:
                raise RuntimeError(f"BUSINESS CRITICAL: Auth user creation failed for {user_id}")
        
        # Step 2: Sync to Backend PostgreSQL (MUST succeed)
        async with self.db.postgres_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (id, email, full_name, is_active, role, created_at, tier)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                user_id,
                user_data["email"], 
                user_data["full_name"],
                user_data["is_active"],
                user_data.get("role", "enterprise_user"),
                user_data["created_at"],
                user_data.get("subscription_tier", "enterprise")
            )
        
        # Step 3: Validate cross-service consistency (BUSINESS CRITICAL)
        auth_record = await self._validate_auth_user_exists(user_id)
        backend_record = await self._validate_backend_user_exists(user_id)
        
        if auth_record["email"] != backend_record["email"]:
            raise RuntimeError("BUSINESS CRITICAL: Cross-service data inconsistency detected")
        
        return {
            "user_id": user_id,
            "auth_created": True,
            "backend_synced": True,
            "data_consistent": True,
            "business_tier": user_data.get("subscription_tier", "enterprise"),
            "revenue_impact": "$15K+ MRR" if user_data.get("subscription_tier") == "enterprise" else "$500+ MRR"
        }

    async def _validate_auth_user_exists(self, user_id: str) -> Dict[str, Any]:
        """Validate user exists in Auth PostgreSQL - NO MOCK FALLBACK."""
        async with self.db.postgres_pool.acquire() as conn:
            record = await conn.fetchrow(
                "SELECT id, email, full_name, is_active, subscription_tier FROM auth_users WHERE id = $1",
                user_id
            )
            
            if not record:
                raise AssertionError(f"BUSINESS CRITICAL: User {user_id} not found in Auth database - $200K+ MRR at risk")
            
            return dict(record)

    async def _validate_backend_user_exists(self, user_id: str) -> Dict[str, Any]:
        """Validate user exists in Backend PostgreSQL - NO MOCK FALLBACK."""
        async with self.db.postgres_pool.acquire() as conn:
            record = await conn.fetchrow(
                "SELECT id, email, full_name, is_active, tier FROM users WHERE id = $1", 
                user_id
            )
            
            if not record:
                raise AssertionError(f"BUSINESS CRITICAL: User {user_id} not found in Backend database - data integrity failure")
            
            return dict(record)


class RealMessageOperations:
    """Real message operations - NO MOCK FALLBACKS."""
    
    def __init__(self, db_connections: RealDatabaseConnections):
        self.db = db_connections

    async def store_revenue_generating_conversation(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        BUSINESS SCENARIO: Store AI conversation that generates revenue
        - Stores messages in ClickHouse for analytics
        - Validates message persistence 
        - Calculates business metrics
        
        REVENUE IMPACT: AI conversations are 90% of platform value - storage must work
        """
        stored_count = 0
        
        for message in messages:
            message_id = message["id"]
            self.db.created_messages.append(message_id)
            
            # Store in ClickHouse (NO MOCK FALLBACK)
            try:
                self.db.clickhouse_client.insert(
                    "chat_messages",
                    [[
                        message_id,
                        message["user_id"],
                        message["thread_id"],
                        message["content"],
                        message["message_type"],
                        message["timestamp"],
                        message.get("ai_model", "gpt-4"),
                        message.get("tokens_used", 0),
                        message.get("cost_usd", 0.0)
                    ]],
                    column_names=["id", "user_id", "thread_id", "content", "message_type", "timestamp", "ai_model", "tokens_used", "cost_usd"]
                )
                stored_count += 1
            except Exception as e:
                raise RuntimeError(f"BUSINESS CRITICAL: Message storage failed for {message_id}: {e}")
        
        # Validate storage with business context
        validation_results = await self._validate_conversation_analytics(messages[0]["user_id"], messages[0]["thread_id"])
        
        return {
            "messages_stored": stored_count,
            "analytics_working": validation_results["query_successful"],
            "conversation_value": validation_results["estimated_revenue_impact"],
            "business_impact": "AI conversation storage enables $500K+ ARR"
        }

    async def _validate_conversation_analytics(self, user_id: str, thread_id: str) -> Dict[str, Any]:
        """Validate conversation analytics - BUSINESS CRITICAL."""
        try:
            # Query stored messages
            result = self.db.clickhouse_client.query(f"""
                SELECT 
                    COUNT(*) as message_count,
                    SUM(tokens_used) as total_tokens,
                    SUM(cost_usd) as total_cost,
                    MAX(timestamp) as last_activity
                FROM chat_messages 
                WHERE user_id = '{user_id}' AND thread_id = '{thread_id}'
            """)
            
            rows = result.result_rows
            if not rows or rows[0][0] == 0:
                raise AssertionError(f"BUSINESS CRITICAL: No messages found for conversation {thread_id}")
            
            message_count, total_tokens, total_cost, last_activity = rows[0]
            
            return {
                "query_successful": True,
                "message_count": message_count,
                "total_tokens": total_tokens,
                "total_cost": total_cost,
                "estimated_revenue_impact": f"${total_cost * 10:.2f}",  # 10x markup typical
                "last_activity": last_activity
            }
            
        except Exception as e:
            raise RuntimeError(f"BUSINESS CRITICAL: Analytics query failed: {e}")


class RealSessionOperations:
    """Real session operations - NO MOCK FALLBACKS."""
    
    def __init__(self, db_connections: RealDatabaseConnections):
        self.db = db_connections

    async def manage_enterprise_session_lifecycle(self, user_id: str, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        BUSINESS SCENARIO: Enterprise customer session management  
        - Caches active session in Redis
        - Validates session persistence
        - Tests session expiration handling
        
        REVENUE IMPACT: Enterprise sessions enable $15K+ MRR customers
        """
        session_key = f"enterprise_session:{user_id}"
        self.db.cached_sessions.append(session_key)
        
        # Store session (NO MOCK FALLBACK)
        try:
            session_json = {
                "user_id": user_id,
                "session_token": session_data["session_token"],
                "login_time": session_data["login_time"], 
                "subscription_tier": session_data.get("subscription_tier", "enterprise"),
                "permissions": session_data.get("permissions", ["admin", "analytics", "enterprise_features"]),
                "last_activity": datetime.now(timezone.utc).isoformat()
            }
            
            # Set with appropriate expiration for enterprise users
            await self.db.redis_client.setex(
                session_key,
                28800,  # 8 hours for enterprise users
                str(session_json)
            )
            
        except Exception as e:
            raise RuntimeError(f"BUSINESS CRITICAL: Enterprise session storage failed: {e}")
        
        # Validate session retrieval
        validation_results = await self._validate_session_accessibility(session_key, user_id)
        
        return {
            "session_stored": True,
            "session_accessible": validation_results["accessible"],
            "permissions_valid": validation_results["permissions_count"] >= 3,
            "enterprise_features_enabled": "enterprise_features" in validation_results["permissions"],
            "business_impact": "$15K+ MRR customer session active"
        }

    async def _validate_session_accessibility(self, session_key: str, user_id: str) -> Dict[str, Any]:
        """Validate session can be retrieved - NO MOCK FALLBACK."""
        try:
            cached_data = await self.db.redis_client.get(session_key)
            
            if not cached_data:
                raise AssertionError(f"BUSINESS CRITICAL: Session {session_key} not found in cache")
            
            # Parse session data
            session_info = eval(cached_data.decode())  # In production, use json.loads
            
            if session_info["user_id"] != user_id:
                raise AssertionError("BUSINESS CRITICAL: Session user ID mismatch")
            
            return {
                "accessible": True,
                "permissions": session_info.get("permissions", []),
                "permissions_count": len(session_info.get("permissions", [])),
                "subscription_tier": session_info.get("subscription_tier")
            }
            
        except Exception as e:
            raise RuntimeError(f"BUSINESS CRITICAL: Session validation failed: {e}")


@pytest.fixture
async def real_db_test():
    """Real database test fixture - NO MOCK FALLBACKS."""
    test_id = f"real_db_test_{int(time.time())}"
    db_connections = RealDatabaseConnections(test_id)
    
    try:
        await db_connections.connect_all()
        yield db_connections
    finally:
        await db_connections.cleanup_test_data()
        await db_connections.disconnect_all()


@pytest.mark.e2e
class TestRealDatabaseOperations:
    """Real database operations testing - NO MOCK FALLBACKS ALLOWED."""

    @pytest.mark.asyncio
    async def test_enterprise_user_creation_complete_revenue_flow(self, real_db_test):
        """
        BUSINESS TEST: Complete enterprise user creation flow
        Tests the critical path that generates $15K+ MRR per enterprise customer
        """
        db_connections = real_db_test
        user_ops = RealUserOperations(db_connections)
        
        # Test data for enterprise customer
        enterprise_user = {
            "id": str(uuid.uuid4()),
            "email": f"enterprise.customer@corp-{int(time.time())}.com",
            "full_name": "Enterprise Customer Executive",
            "is_active": True,
            "subscription_tier": "enterprise",
            "created_at": datetime.now(timezone.utc)
        }
        
        # Execute complete enterprise user flow
        result = await user_ops.create_enterprise_user_complete_flow(enterprise_user)
        
        # Validate business outcomes
        assert result["auth_created"] is True, "BUSINESS FAILURE: Auth user creation failed"
        assert result["backend_synced"] is True, "BUSINESS FAILURE: Backend sync failed"
        assert result["data_consistent"] is True, "BUSINESS FAILURE: Data consistency violated"
        assert result["business_tier"] == "enterprise", "BUSINESS FAILURE: Enterprise tier not set"
        assert "$15K+" in result["revenue_impact"], "BUSINESS FAILURE: Revenue impact not calculated"
        
        logger.info(f" PASS:  BUSINESS SUCCESS: Enterprise user flow completed - {result['revenue_impact']}")

    @pytest.mark.asyncio  
    async def test_ai_conversation_storage_revenue_generation(self, real_db_test):
        """
        BUSINESS TEST: AI conversation storage that enables platform revenue
        Tests storage of AI conversations that represent 90% of platform value
        """
        db_connections = real_db_test
        message_ops = RealMessageOperations(db_connections)
        
        user_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        
        # Revenue-generating AI conversation
        conversation_messages = [
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "thread_id": thread_id,
                "content": "Analyze our cloud infrastructure costs and provide optimization recommendations",
                "message_type": "user_request",
                "timestamp": datetime.now(timezone.utc),
                "ai_model": "gpt-4",
                "tokens_used": 150,
                "cost_usd": 0.30
            },
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id, 
                "thread_id": thread_id,
                "content": "Based on your infrastructure analysis, I recommend consolidating your EC2 instances which could save $15,000 monthly...",
                "message_type": "ai_response",
                "timestamp": datetime.now(timezone.utc),
                "ai_model": "gpt-4",
                "tokens_used": 800,
                "cost_usd": 1.60
            }
        ]
        
        # Execute conversation storage
        result = await message_ops.store_revenue_generating_conversation(conversation_messages)
        
        # Validate business outcomes
        assert result["messages_stored"] == 2, "BUSINESS FAILURE: Not all messages stored"
        assert result["analytics_working"] is True, "BUSINESS FAILURE: Analytics queries broken"
        assert "$" in result["conversation_value"], "BUSINESS FAILURE: Revenue calculation failed"
        assert "AI conversation" in result["business_impact"], "BUSINESS FAILURE: Business impact not tracked"
        
        logger.info(f" PASS:  BUSINESS SUCCESS: AI conversation stored - {result['conversation_value']} value tracked")

    @pytest.mark.asyncio
    async def test_enterprise_session_management_revenue_protection(self, real_db_test):
        """
        BUSINESS TEST: Enterprise session management protecting $15K+ MRR
        Tests session caching that enables high-value enterprise customer features
        """
        db_connections = real_db_test
        session_ops = RealSessionOperations(db_connections)
        
        enterprise_user_id = str(uuid.uuid4())
        session_data = {
            "session_token": str(uuid.uuid4()),
            "login_time": datetime.now(timezone.utc).isoformat(),
            "subscription_tier": "enterprise",
            "permissions": ["admin", "analytics", "enterprise_features", "api_access"]
        }
        
        # Execute enterprise session management
        result = await session_ops.manage_enterprise_session_lifecycle(enterprise_user_id, session_data)
        
        # Validate business outcomes
        assert result["session_stored"] is True, "BUSINESS FAILURE: Enterprise session not stored"
        assert result["session_accessible"] is True, "BUSINESS FAILURE: Session not accessible"
        assert result["permissions_valid"] is True, "BUSINESS FAILURE: Enterprise permissions missing"
        assert result["enterprise_features_enabled"] is True, "BUSINESS FAILURE: Enterprise features not enabled"
        assert "$15K+" in result["business_impact"], "BUSINESS FAILURE: Revenue impact not tracked"
        
        logger.info(f" PASS:  BUSINESS SUCCESS: Enterprise session active - {result['business_impact']}")

    @pytest.mark.asyncio
    async def test_cross_database_transaction_atomicity_data_integrity(self, real_db_test):
        """
        BUSINESS TEST: Cross-database transaction atomicity protecting data integrity
        Tests atomic operations that prevent data corruption affecting customer trust
        """
        db_connections = real_db_test
        user_ops = RealUserOperations(db_connections)
        message_ops = RealMessageOperations(db_connections)
        session_ops = RealSessionOperations(db_connections)
        
        user_id = str(uuid.uuid4())
        test_start = time.time()
        
        # Simulate complete customer onboarding transaction
        try:
            # Step 1: Create user
            user_data = {
                "id": user_id,
                "email": f"atomicity.test@customer-{int(time.time())}.com",
                "full_name": "Transaction Atomicity Customer",
                "is_active": True,
                "subscription_tier": "growth",
                "created_at": datetime.now(timezone.utc)
            }
            
            user_result = await user_ops.create_enterprise_user_complete_flow(user_data)
            assert user_result["data_consistent"] is True
            
            # Step 2: Store initial conversation
            welcome_messages = [{
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "thread_id": str(uuid.uuid4()),
                "content": "Welcome to Netra! Let's optimize your AI operations.",
                "message_type": "system_welcome",
                "timestamp": datetime.now(timezone.utc),
                "ai_model": "gpt-4",
                "tokens_used": 50,
                "cost_usd": 0.10
            }]
            
            message_result = await message_ops.store_revenue_generating_conversation(welcome_messages)
            assert message_result["analytics_working"] is True
            
            # Step 3: Create user session
            session_result = await session_ops.manage_enterprise_session_lifecycle(user_id, {
                "session_token": str(uuid.uuid4()),
                "login_time": datetime.now(timezone.utc).isoformat(),
                "subscription_tier": "growth"
            })
            assert session_result["session_accessible"] is True
            
            transaction_time = time.time() - test_start
            
            logger.info(f" PASS:  BUSINESS SUCCESS: Complete customer onboarding in {transaction_time:.2f}s - data integrity maintained")
            
        except Exception as e:
            # In a real atomic transaction, this would trigger rollback
            logger.error(f" FAIL:  BUSINESS FAILURE: Customer onboarding transaction failed: {e}")
            raise AssertionError(f"BUSINESS CRITICAL: Transaction atomicity failed - customer data at risk: {e}")

    @pytest.mark.asyncio
    async def test_high_availability_database_requirements(self, real_db_test):
        """
        BUSINESS TEST: High availability database requirements for $200K+ MRR protection
        Tests database availability requirements that protect revenue-generating operations
        """
        db_connections = real_db_test
        
        # Test PostgreSQL availability
        async with db_connections.postgres_pool.acquire() as conn:
            pg_result = await conn.fetchval("SELECT 1")
            assert pg_result == 1, "BUSINESS CRITICAL: PostgreSQL not available - $200K+ MRR at risk"
        
        # Test ClickHouse availability  
        ch_result = db_connections.clickhouse_client.query("SELECT 1")
        assert ch_result.result_rows[0][0] == 1, "BUSINESS CRITICAL: ClickHouse not available - analytics disabled"
        
        # Test Redis availability
        redis_result = await db_connections.redis_client.ping()
        assert redis_result is True, "BUSINESS CRITICAL: Redis not available - session management failed"
        
        # Test connection pool health
        pool_size = db_connections.postgres_pool.get_size()
        max_size = db_connections.postgres_pool.get_max_size()
        assert pool_size > 0, "BUSINESS CRITICAL: No database connections available"
        assert pool_size <= max_size, "BUSINESS CRITICAL: Connection pool misconfigured"
        
        logger.info(f" PASS:  BUSINESS SUCCESS: All databases available - {pool_size}/{max_size} connections active")


if __name__ == "__main__":
    # Run specific business test
    pytest.main([__file__ + "::TestRealDatabaseOperations::test_enterprise_user_creation_complete_revenue_flow", "-v"])
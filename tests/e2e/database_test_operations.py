"""
Database Operations for E2E Tests - REAL DATABASE TESTING ONLY
Handles CRUD operations across all databases WITHOUT MOCK FALLBACKS.

ANTI-CHEATING MEASURES:
- NO mock fallbacks when databases unavailable - test FAILS properly  
- NO try/catch suppression hiding real errors
- Real database connections required for all operations
- Business context provided in all failures

Business Value Justification (BVJ):
- Segment: All tiers (Free, Early, Mid, Enterprise)
- Goal: Data integrity and reliability (99.9% requirement)
- Value Impact: Protects $200K+ MRR dependent on database operations
- Revenue Impact: Prevents data corruption affecting all customer segments
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from tests.e2e.database_test_connections import DatabaseConnectionManager

logger = logging.getLogger(__name__)


class RealUserDataOperations:
    """Handles user data operations across databases - NO MOCK FALLBACKS."""
    
    def __init__(self, db_manager: DatabaseConnectionManager):
        self.db_manager = db_manager
        
    async def create_auth_user(self, user_data: Dict[str, Any]) -> str:
        """Create user in Auth PostgreSQL - FAILS if database unavailable."""
        
        if not self.db_manager.postgres_pool:
            raise ConnectionError(
                "BUSINESS CRITICAL: PostgreSQL unavailable for E2E test. "
                "Auth user creation impossible - ALL customer authentication blocked. "
                "$500K+ ARR at risk."
            )
            
        return await self._create_real_auth_user(user_data)
        
    async def _create_real_auth_user(self, user_data: Dict[str, Any]) -> str:
        """Create real user in Auth PostgreSQL."""
        
        async with self.db_manager.postgres_pool.acquire() as conn:
            try:
                user_id = await conn.fetchval(
                    "INSERT INTO auth_users (id, email, full_name, is_active, created_at) "
                    "VALUES ($1, $2, $3, $4, $5) ON CONFLICT (email) DO UPDATE "
                    "SET full_name = $3, is_active = $4 RETURNING id",
                    user_data["id"], user_data["email"], user_data["full_name"],
                    user_data["is_active"], user_data["created_at"]
                )
                
                if not user_id:
                    raise RuntimeError(
                        f"BUSINESS CRITICAL: User creation failed for {user_data['email']}. "
                        "Enterprise customer onboarding blocked - $15K+ MRR per customer at risk."
                    )
                    
                return user_id
                
            except Exception as e:
                raise RuntimeError(
                    f"BUSINESS CRITICAL: Auth user creation failed: {e}. "
                    "All customer authentication affected - $500K+ ARR at risk."
                )
            
    async def sync_to_backend(self, user_data: Dict[str, Any]) -> bool:
        """Sync user to Backend PostgreSQL - FAILS if database unavailable."""
        
        if not self.db_manager.postgres_pool:
            raise ConnectionError(
                "BUSINESS CRITICAL: Backend PostgreSQL unavailable for E2E test. "
                "User sync impossible - cross-service data integrity compromised. "
                "$200K+ MRR depends on data consistency."
            )
            
        return await self._sync_real_backend_user(user_data)
        
    async def _sync_real_backend_user(self, user_data: Dict[str, Any]) -> bool:
        """Sync real user to Backend PostgreSQL."""
        
        async with self.db_manager.postgres_pool.acquire() as conn:
            try:
                await conn.execute(
                    "INSERT INTO backend_users (id, email, auth_user_id, subscription_tier, created_at) "
                    "VALUES ($1, $2, $3, $4, $5) ON CONFLICT (auth_user_id) DO UPDATE "
                    "SET email = $2, subscription_tier = $4",
                    user_data["id"], user_data["email"], user_data["id"], 
                    user_data.get("subscription_tier", "free"), user_data["created_at"]
                )
                
                # Verify the sync actually worked
                backend_user_exists = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM backend_users WHERE auth_user_id = $1)",
                    user_data["id"]
                )
                
                if not backend_user_exists:
                    raise RuntimeError(
                        f"BUSINESS CRITICAL: Backend user sync verification failed for {user_data['email']}. "
                        "Data consistency broken - customer data integrity compromised."
                    )
                    
                return True
                
            except Exception as e:
                raise RuntimeError(
                    f"BUSINESS CRITICAL: Backend user sync failed: {e}. "
                    "Cross-service data integrity compromised - $200K+ MRR at risk."
                )


class RealChatMessageOperations:
    """Handles chat message operations - NO MOCK FALLBACKS."""
    
    def __init__(self, db_manager: DatabaseConnectionManager):
        self.db_manager = db_manager
        
    async def store_message(self, message_data: Dict[str, Any]) -> str:
        """Store message in ClickHouse - FAILS if database unavailable."""
        
        if not self.db_manager.clickhouse_client:
            raise ConnectionError(
                "BUSINESS CRITICAL: ClickHouse unavailable for E2E test. "
                "AI conversation storage impossible - chat functionality represents 90% of platform value. "
                "CRITICAL REVENUE IMPACT."
            )
            
        return await self._store_real_message(message_data)
        
    async def _store_real_message(self, message_data: Dict[str, Any]) -> str:
        """Store real message in ClickHouse."""
        
        try:
            message_id = str(message_data.get("id", f"msg_{datetime.now().isoformat()}"))
            
            # Store in ClickHouse analytics database
            self.db_manager.clickhouse_client.insert("chat_messages", [
                {
                    "message_id": message_id,
                    "user_id": message_data["user_id"],
                    "content": message_data["content"],
                    "timestamp": message_data.get("timestamp", datetime.now(timezone.utc)),
                    "tokens_used": message_data.get("tokens_used", 0),
                    "model_cost": message_data.get("model_cost", 0.0),
                    "response_time_ms": message_data.get("response_time_ms", 0),
                }
            ])
            
            # Verify the message was actually stored
            stored_messages = self.db_manager.clickhouse_client.query(
                "SELECT COUNT(*) FROM chat_messages WHERE message_id = %(message_id)s",
                {"message_id": message_id}
            )
            
            if stored_messages.first_row[0] == 0:
                raise RuntimeError(
                    f"BUSINESS CRITICAL: Message storage verification failed for {message_id}. "
                    "AI conversation data lost - 90% of platform value at risk."
                )
                
            return message_id
            
        except Exception as e:
            raise RuntimeError(
                f"BUSINESS CRITICAL: Message storage failed: {e}. "
                "AI conversations are 90% of platform value - CRITICAL REVENUE IMPACT."
            )
            
    async def get_user_messages(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve user messages from ClickHouse - FAILS if database unavailable."""
        
        if not self.db_manager.clickhouse_client:
            raise ConnectionError(
                "BUSINESS CRITICAL: ClickHouse unavailable for E2E test. "
                "Message retrieval impossible - customer chat history inaccessible. "
                "Customer experience severely degraded."
            )
            
        try:
            result = self.db_manager.clickhouse_client.query(
                "SELECT message_id, content, timestamp, tokens_used, model_cost "
                "FROM chat_messages WHERE user_id = %(user_id)s "
                "ORDER BY timestamp DESC LIMIT %(limit)s",
                {"user_id": user_id, "limit": limit}
            )
            
            messages = []
            for row in result.result_rows:
                messages.append({
                    "message_id": row[0],
                    "content": row[1],
                    "timestamp": row[2],
                    "tokens_used": row[3],
                    "model_cost": row[4],
                })
                
            return messages
            
        except Exception as e:
            raise RuntimeError(
                f"BUSINESS CRITICAL: Message retrieval failed: {e}. "
                "Customer chat history inaccessible - poor user experience affects retention."
            )


class RealSessionCacheOperations:
    """Handles session cache operations - NO MOCK FALLBACKS."""
    
    def __init__(self, db_manager: DatabaseConnectionManager):
        self.db_manager = db_manager
        
    async def store_session(self, session_data: Dict[str, Any]) -> bool:
        """Store session in Redis - FAILS if Redis unavailable."""
        
        if not self.db_manager.redis_client:
            raise ConnectionError(
                "BUSINESS CRITICAL: Redis unavailable for E2E test. "
                "Session storage impossible - user authentication sessions cannot be cached. "
                "Performance severely degraded for all users."
            )
            
        return await self._store_real_session(session_data)
        
    async def _store_real_session(self, session_data: Dict[str, Any]) -> bool:
        """Store real session in Redis."""
        
        try:
            session_key = f"session:{session_data['user_id']}"
            session_ttl = session_data.get("ttl_seconds", 3600)  # 1 hour default
            
            # Store session data with expiration
            await self.db_manager.redis_client.hset(session_key, mapping={
                "user_id": session_data["user_id"],
                "email": session_data["email"],
                "subscription_tier": session_data.get("subscription_tier", "free"),
                "created_at": session_data.get("created_at", datetime.now().isoformat()),
                "last_activity": datetime.now().isoformat(),
            })
            
            await self.db_manager.redis_client.expire(session_key, session_ttl)
            
            # Verify session was stored
            session_exists = await self.db_manager.redis_client.exists(session_key)
            if not session_exists:
                raise RuntimeError(
                    f"BUSINESS CRITICAL: Session storage verification failed for user {session_data['user_id']}. "
                    "Authentication session lost - user will be logged out unexpectedly."
                )
                
            return True
            
        except Exception as e:
            raise RuntimeError(
                f"BUSINESS CRITICAL: Session storage failed: {e}. "
                "User authentication sessions cannot be cached - performance severely degraded."
            )
            
    async def get_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session from Redis - FAILS if Redis unavailable."""
        
        if not self.db_manager.redis_client:
            raise ConnectionError(
                "BUSINESS CRITICAL: Redis unavailable for E2E test. "
                "Session retrieval impossible - user authentication verification blocked."
            )
            
        try:
            session_key = f"session:{user_id}"
            session_data = await self.db_manager.redis_client.hgetall(session_key)
            
            if not session_data:
                return None
                
            # Convert bytes to strings (Redis returns bytes)
            return {
                key.decode() if isinstance(key, bytes) else key: 
                value.decode() if isinstance(value, bytes) else value
                for key, value in session_data.items()
            }
            
        except Exception as e:
            raise RuntimeError(
                f"BUSINESS CRITICAL: Session retrieval failed: {e}. "
                "User authentication verification blocked - login functionality compromised."
            )


class RealTransactionOperations:
    """Handles multi-database transaction operations - NO MOCK FALLBACKS."""
    
    def __init__(self, db_manager: DatabaseConnectionManager):
        self.db_manager = db_manager
        
    async def complete_user_onboarding_flow(self, user_data: Dict[str, Any]) -> bool:
        """Complete full user onboarding across all databases - FAILS if any database unavailable."""
        
        # Validate all databases are available
        if not self.db_manager.postgres_pool:
            raise ConnectionError(
                "BUSINESS CRITICAL: PostgreSQL unavailable for complete user onboarding. "
                "Enterprise customer onboarding blocked - $15K+ MRR per customer at risk."
            )
            
        if not self.db_manager.clickhouse_client:
            raise ConnectionError(
                "BUSINESS CRITICAL: ClickHouse unavailable for complete user onboarding. "
                "User analytics tracking impossible - customer behavior data lost."
            )
            
        if not self.db_manager.redis_client:
            raise ConnectionError(
                "BUSINESS CRITICAL: Redis unavailable for complete user onboarding. "
                "Session caching impossible - poor user experience guaranteed."
            )
        
        try:
            # Step 1: Create user in Auth PostgreSQL
            user_ops = RealUserDataOperations(self.db_manager)
            user_id = await user_ops.create_auth_user(user_data)
            
            # Step 2: Sync to Backend PostgreSQL
            sync_success = await user_ops.sync_to_backend(user_data)
            if not sync_success:
                raise RuntimeError("Backend user sync failed during onboarding")
                
            # Step 3: Create initial session in Redis
            session_ops = RealSessionCacheOperations(self.db_manager)
            session_success = await session_ops.store_session({
                "user_id": user_id,
                "email": user_data["email"],
                "subscription_tier": user_data.get("subscription_tier", "free"),
                "created_at": user_data["created_at"],
            })
            if not session_success:
                raise RuntimeError("Session creation failed during onboarding")
            
            # Step 4: Log onboarding event in ClickHouse
            message_ops = RealChatMessageOperations(self.db_manager)
            onboarding_message_id = await message_ops.store_message({
                "id": f"onboarding_{user_id}",
                "user_id": user_id,
                "content": f"User onboarding completed for {user_data['email']}",
                "timestamp": datetime.now(timezone.utc),
                "tokens_used": 0,
                "model_cost": 0.0,
                "response_time_ms": 0,
            })
            if not onboarding_message_id:
                raise RuntimeError("Onboarding event logging failed")
                
            # Validate complete onboarding success across all databases
            await self._validate_complete_onboarding(user_id, user_data["email"])
            
            return True
            
        except Exception as e:
            raise RuntimeError(
                f"BUSINESS CRITICAL: Complete user onboarding failed: {e}. "
                "Enterprise customer cannot be onboarded - $15K+ MRR per customer lost. "
                "Data consistency across services compromised."
            )
            
    async def _validate_complete_onboarding(self, user_id: str, email: str) -> None:
        """Validate user onboarding succeeded across all databases."""
        
        # Validate PostgreSQL (both Auth and Backend)
        async with self.db_manager.postgres_pool.acquire() as conn:
            auth_user_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM auth_users WHERE id = $1)", user_id
            )
            backend_user_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM backend_users WHERE auth_user_id = $1)", user_id
            )
            
            if not auth_user_exists:
                raise RuntimeError(f"BUSINESS CRITICAL: User not found in Auth database - $200K+ MRR at risk")
            if not backend_user_exists:
                raise RuntimeError(f"BUSINESS CRITICAL: User not found in Backend database - data sync failed")
        
        # Validate Redis session
        session_exists = await self.db_manager.redis_client.exists(f"session:{user_id}")
        if not session_exists:
            raise RuntimeError(f"BUSINESS CRITICAL: Session not found in Redis - user login impossible")
        
        # Validate ClickHouse onboarding event
        onboarding_events = self.db_manager.clickhouse_client.query(
            "SELECT COUNT(*) FROM chat_messages WHERE user_id = %(user_id)s AND message_id LIKE 'onboarding_%'",
            {"user_id": user_id}
        )
        if onboarding_events.first_row[0] == 0:
            raise RuntimeError(f"BUSINESS CRITICAL: Onboarding event not found in ClickHouse - analytics tracking failed")
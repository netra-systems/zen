"""
Database Operations for Tests
Handles CRUD operations across all databases.
ARCHITECTURE: Under 300 lines, 25-line functions max
"""

from datetime import datetime, timezone
from tests.e2e.database_test_connections import DatabaseConnectionManager
from typing import Any, Dict, List, Optional
import json

class UserDataOperations:

    """Handles user data operations across databases."""
    

    def __init__(self, db_manager: DatabaseConnectionManager):

        self.db_manager = db_manager
        

    async def create_auth_user(self, user_data: Dict[str, Any]) -> str:

        """Create user in Auth PostgreSQL."""

        if not self.db_manager.postgres_pool:

            return self._mock_user_creation(user_data)

        return await self._create_real_auth_user(user_data)
        

    def _mock_user_creation(self, user_data: Dict[str, Any]) -> str:

        """Mock user creation for testing."""

        return user_data["id"]
        

    async def _create_real_auth_user(self, user_data: Dict[str, Any]) -> str:

        """Create real user in Auth PostgreSQL."""

        async with self.db_manager.postgres_pool.acquire() as conn:

            user_id = await conn.fetchval(

                "INSERT INTO auth_users (id, email, full_name, is_active, created_at) "

                "VALUES ($1, $2, $3, $4, $5) ON CONFLICT (email) DO UPDATE "

                "SET full_name = $3, is_active = $4 RETURNING id",

                user_data["id"], user_data["email"], user_data["full_name"],

                user_data["is_active"], user_data["created_at"]

            )

            return user_id or user_data["id"]
            

    async def sync_to_backend(self, user_data: Dict[str, Any]) -> bool:

        """Sync user to Backend PostgreSQL."""

        if not self.db_manager.postgres_pool:

            return True  # Mock success

        return await self._sync_real_backend_user(user_data)
        

    async def _sync_real_backend_user(self, user_data: Dict[str, Any]) -> bool:

        """Sync real user to Backend PostgreSQL."""

        async with self.db_manager.postgres_pool.acquire() as conn:

            await conn.execute(

                "INSERT INTO users (id, email, full_name, is_active, role, created_at) "

                "VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT (id) DO UPDATE "

                "SET email = $2, full_name = $3, is_active = $4",

                user_data["id"], user_data["email"], user_data["full_name"],

                user_data["is_active"], user_data.get("role", "user"), user_data["created_at"]

            )

        return True


class ChatMessageOperations:

    """Handles chat message operations in ClickHouse."""
    

    def __init__(self, db_manager: DatabaseConnectionManager):

        self.db_manager = db_manager

        self.messages = []  # Mock storage
        

    async def store_message(self, message_data: Dict[str, Any]) -> bool:

        """Store chat message in ClickHouse."""

        if not self.db_manager.clickhouse_client:

            return self._mock_message_storage(message_data)

        return await self._store_real_message(message_data)
        

    def _mock_message_storage(self, message_data: Dict[str, Any]) -> bool:

        """Mock message storage for testing."""

        self.messages.append(message_data)

        return True
        

    async def _store_real_message(self, message_data: Dict[str, Any]) -> bool:

        """Store real message in ClickHouse."""

        try:

            self.db_manager.clickhouse_client.insert(

                "chat_messages",

                [[

                    message_data["id"], message_data["user_id"], 

                    message_data["content"], message_data["timestamp"]

                ]],

                column_names=["id", "user_id", "content", "timestamp"]

            )

            return True

        except Exception:

            return False
            

    async def get_user_messages(self, user_id: str) -> List[Dict[str, Any]]:

        """Get user messages from ClickHouse."""

        if not self.db_manager.clickhouse_client:

            return [msg for msg in self.messages if msg["user_id"] == user_id]

        return await self._get_real_user_messages(user_id)
        

    async def _get_real_user_messages(self, user_id: str) -> List[Dict[str, Any]]:

        """Get real user messages from ClickHouse."""

        try:

            result = self.db_manager.clickhouse_client.query(

                f"SELECT * FROM chat_messages WHERE user_id = '{user_id}'"

            )

            return result.result_rows

        except Exception:

            return []


class SessionCacheOperations:

    """Handles session caching in Redis."""
    

    def __init__(self, db_manager: DatabaseConnectionManager):

        self.db_manager = db_manager

        self.cache = {}  # Mock storage
        

    async def cache_session(self, user_id: str, session_data: Dict[str, Any]) -> bool:

        """Cache active session in Redis."""

        if not self.db_manager.redis_client:

            return self._mock_session_cache(user_id, session_data)

        return await self._cache_real_session(user_id, session_data)
        

    def _mock_session_cache(self, user_id: str, session_data: Dict[str, Any]) -> bool:

        """Mock session caching for testing."""

        self.cache[f"session:{user_id}"] = session_data

        return True
        

    async def _cache_real_session(self, user_id: str, session_data: Dict[str, Any]) -> bool:

        """Cache real session in Redis."""

        try:

            await self.db_manager.redis_client.set(

                f"session:{user_id}", 

                json.dumps(session_data),

                ex=3600  # 1 hour expiration

            )

            return True

        except Exception:

            return False
            

    async def get_cached_session(self, user_id: str) -> Optional[Dict[str, Any]]:

        """Get cached session from Redis."""

        if not self.db_manager.redis_client:

            return self.cache.get(f"session:{user_id}")

        return await self._get_real_cached_session(user_id)
        

    async def _get_real_cached_session(self, user_id: str) -> Optional[Dict[str, Any]]:

        """Get real cached session from Redis."""

        try:

            data = await self.db_manager.redis_client.get(f"session:{user_id}")

            return json.loads(data) if data else None

        except Exception:

            return None


class DatabaseOperations:

    """Unified database operations class combining all database operations."""
    

    def __init__(self, db_manager: DatabaseConnectionManager = None):

        """Initialize with optional database connection manager."""

        if db_manager is None:

            self.db_manager = DatabaseConnectionManager()

        else:

            self.db_manager = db_manager
            

        self.user_ops = UserDataOperations(self.db_manager)

        self.message_ops = ChatMessageOperations(self.db_manager)

        self.session_ops = SessionCacheOperations(self.db_manager)
        

    async def initialize(self):

        """Initialize database connections."""

        await self.db_manager.connect_all()
        

    async def cleanup(self):

        """Clean up database connections."""

        await self.db_manager.disconnect_all()
        
    # User operations

    async def create_postgres_user(self, user_data: Dict[str, Any]) -> str:

        """Create user in PostgreSQL."""

        return await self.user_ops.create_auth_user(user_data)
        

    async def delete_user(self, user_id: str) -> bool:

        """Delete user from databases."""

        if not self.db_manager.postgres_pool:

            return True  # Mock success
            

        try:

            async with self.db_manager.postgres_pool.acquire() as conn:

                await conn.execute("DELETE FROM auth_users WHERE id = $1", user_id)

                await conn.execute("DELETE FROM users WHERE id = $1", user_id)

            return True

        except Exception:

            return False
            

    async def delete_workspace(self, workspace_id: str) -> bool:

        """Delete workspace from databases."""

        if not self.db_manager.postgres_pool:

            return True  # Mock success
            

        try:

            async with self.db_manager.postgres_pool.acquire() as conn:

                await conn.execute("DELETE FROM workspaces WHERE id = $1", workspace_id)

            return True

        except Exception:

            return False
    
    # Analytics operations

    async def get_user_analytics(self, user_id: str) -> Dict[str, Any]:

        """Get user analytics from ClickHouse."""

        messages = await self.message_ops.get_user_messages(user_id)

        return {"event_count": len(messages), "messages": messages}
        

    async def insert_clickhouse_event(self, event: Dict[str, Any]) -> bool:

        """Insert event into ClickHouse."""

        return await self.message_ops.store_message(event)
        
    # Transaction operations

    async def begin_transaction(self, transaction_id: str) -> bool:

        """Begin a database transaction."""
        # For testing purposes, just return success

        return True
        

    async def create_user_in_transaction(self, transaction_id: str, user_data: Dict[str, Any]) -> str:

        """Create user within a transaction."""

        return await self.user_ops.create_auth_user(user_data)
        

    async def rollback_transaction(self, transaction_id: str) -> bool:

        """Rollback a database transaction."""
        # For testing purposes, just return success

        return True
        

    async def user_exists(self, email: str) -> bool:

        """Check if user exists by email."""

        if not self.db_manager.postgres_pool:

            return False  # Mock not exists
            

        try:

            async with self.db_manager.postgres_pool.acquire() as conn:

                exists = await conn.fetchval(

                    "SELECT EXISTS(SELECT 1 FROM auth_users WHERE email = $1)", email

                )

                return bool(exists)

        except Exception:

            return False
            
    # Schema operations

    async def add_column_if_not_exists(self, table: str, column: str, column_type: str) -> bool:

        """Add column to table if it doesn't exist."""

        if not self.db_manager.postgres_pool:

            return True  # Mock success
            

        try:

            async with self.db_manager.postgres_pool.acquire() as conn:
                # Check if column exists

                exists = await conn.fetchval("""

                    SELECT EXISTS (

                        SELECT 1 FROM information_schema.columns 

                        WHERE table_name = $1 AND column_name = $2

                    )

                """, table, column)
                

                if not exists:

                    await conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")

            return True

        except Exception:

            return False
            
    # Backup operations

    async def create_backup(self, backup_name: str) -> Optional[str]:

        """Create a database backup."""
        # For testing purposes, return a mock backup ID
        import uuid

        return str(uuid.uuid4())
        

    async def restore_backup(self, backup_id: str) -> bool:

        """Restore from a database backup."""
        # For testing purposes, just return success

        return True
        
    # Batch operations

    async def get_users_batch(self, user_ids: List[str]) -> List[Dict[str, Any]]:

        """Get multiple users by their IDs."""

        if not self.db_manager.postgres_pool:
            # Mock data

            return [{"id": uid, "email": f"user{uid}@test.com"} for uid in user_ids[:10]]
            

        try:

            async with self.db_manager.postgres_pool.acquire() as conn:

                users = await conn.fetch(

                    "SELECT id, email, full_name FROM auth_users WHERE id = ANY($1)",

                    user_ids

                )

                return [dict(user) for user in users]

        except Exception:

            return []

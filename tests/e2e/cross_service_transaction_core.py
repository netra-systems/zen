"""Cross-Service Transaction Core Components



Business Value Justification (BVJ):

1. Segment: All customer segments

2. Business Goal: Atomic cross-service operations

3. Value Impact: Prevents data corruption

4. Revenue Impact: $60K MRR protected



Module Architecture: <300 lines, <8 lines per function

"""



import json

import uuid

from datetime import datetime, timezone

from typing import Any, Dict, List, Optional





class CrossServiceTransactionError(Exception):

    """Custom exception for cross-service transaction failures."""

    pass





class TransactionOperation:

    """Represents an atomic operation in a cross-service transaction."""

    

    def __init__(self, service: str, operation: str, data: Dict[str, Any]):

        self.service = service

        self.operation = operation

        self.data = data

        self.completed = False

        self.operation_id = f"{service}_{uuid.uuid4().hex[:8]}"

        self.rollback_data: Optional[Dict[str, Any]] = None





class TransactionDataFactory:

    """Factory for creating test data for cross-service transactions."""

    

    @staticmethod

    def create_test_user_data(identifier: str) -> Dict[str, Any]:

        """Create test user data for cross-service operations."""

        return {

            "user_id": f"cross_service_test_{identifier}",

            "email": f"test_{identifier}@netra-apex.com",

            "full_name": f"Cross Service Test User {identifier}",

            "plan_tier": "enterprise"

        }



    @staticmethod

    def create_workspace_data(user_id: str) -> Dict[str, Any]:

        """Create workspace data for backend service."""

        return {

            "user_id": user_id,

            "workspace_name": f"Workspace_{user_id}",

            "settings": {"theme": "dark", "notifications": True},

            "created_at": datetime.now(timezone.utc).isoformat()

        }



    @staticmethod

    def create_event_data(user_id: str, transaction_id: str) -> Dict[str, Any]:

        """Create event data for ClickHouse logging."""

        return {

            "user_id": user_id,

            "transaction_id": transaction_id,

            "event_type": "cross_service_transaction",

            "timestamp": datetime.now(timezone.utc).isoformat()

        }





class AuthServiceOperations:

    """Auth service database operations for cross-service transactions."""

    

    def __init__(self, db_connections):

        self.db_connections = db_connections



    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:

        """Get user from Auth service for rollback data."""

        auth_conn = await self.db_connections.get_auth_connection()

        query = "SELECT * FROM users WHERE user_id = $1"

        result = await auth_conn.fetchrow(query, user_id)

        return dict(result) if result else None



    async def update_user(self, user_data: Dict[str, Any]) -> None:

        """Update user in Auth PostgreSQL."""

        auth_conn = await self.db_connections.get_auth_connection()

        query = """

            INSERT INTO users (user_id, email, full_name, plan_tier, updated_at)

            VALUES ($1, $2, $3, $4, $5)

            ON CONFLICT (user_id) DO UPDATE SET

                email = EXCLUDED.email,

                full_name = EXCLUDED.full_name,

                plan_tier = EXCLUDED.plan_tier,

                updated_at = EXCLUDED.updated_at

        """

        await auth_conn.execute(

            query, user_data["user_id"], user_data["email"],

            user_data["full_name"], user_data["plan_tier"],

            datetime.now(timezone.utc)

        )



    async def delete_user(self, user_id: str) -> None:

        """Delete user from Auth service."""

        auth_conn = await self.db_connections.get_auth_connection()

        await auth_conn.execute("DELETE FROM users WHERE user_id = $1", user_id)





class BackendServiceOperations:

    """Backend service database operations for cross-service transactions."""

    

    def __init__(self, db_connections):

        self.db_connections = db_connections



    async def get_workspace(self, user_id: str) -> Optional[Dict[str, Any]]:

        """Get workspace from Backend service for rollback."""

        backend_conn = await self.db_connections.get_backend_connection()

        query = "SELECT * FROM workspaces WHERE user_id = $1"

        result = await backend_conn.fetchrow(query, user_id)

        return dict(result) if result else None



    async def create_workspace(self, workspace_data: Dict[str, Any]) -> None:

        """Create workspace in Backend PostgreSQL."""

        backend_conn = await self.db_connections.get_backend_connection()

        query = """

            INSERT INTO workspaces (user_id, workspace_name, settings, created_at)

            VALUES ($1, $2, $3, $4)

            ON CONFLICT (user_id) DO UPDATE SET

                workspace_name = EXCLUDED.workspace_name,

                settings = EXCLUDED.settings,

                created_at = EXCLUDED.created_at

        """

        await backend_conn.execute(

            query, workspace_data["user_id"], workspace_data["workspace_name"],

            json.dumps(workspace_data["settings"]), workspace_data["created_at"]

        )



    async def delete_workspace(self, user_id: str) -> None:

        """Delete workspace from Backend service."""

        backend_conn = await self.db_connections.get_backend_connection()

        await backend_conn.execute("DELETE FROM workspaces WHERE user_id = $1", user_id)





class ClickHouseOperations:

    """ClickHouse operations for cross-service transactions."""

    

    def __init__(self, db_connections):

        self.db_connections = db_connections



    async def log_event(self, event_data: Dict[str, Any]) -> None:

        """Log event to ClickHouse."""

        clickhouse_conn = await self.db_connections.get_clickhouse_connection()

        await clickhouse_conn.insert_user_event(

            event_data["user_id"],

            {

                "event_type": "cross_service_transaction", 

                "transaction_id": event_data["transaction_id"],

                "data": event_data

            }

        )



    async def get_user_events(self, user_id: str, transaction_id: str) -> List[Dict]:

        """Get user events from ClickHouse for verification."""

        clickhouse_conn = await self.db_connections.get_clickhouse_connection()

        events = await clickhouse_conn.get_user_metrics(user_id)

        return [e for e in events if e["data"]["transaction_id"] == transaction_id]





class TransactionVerificationService:

    """Service for verifying cross-service transaction consistency."""

    

    def __init__(self, auth_ops, backend_ops, clickhouse_ops):

        self.auth_ops = auth_ops

        self.backend_ops = backend_ops

        self.clickhouse_ops = clickhouse_ops



    async def verify_auth_consistency(self, user_id: str) -> bool:

        """Verify Auth service data consistency."""

        auth_user = await self.auth_ops.get_user(user_id)

        return auth_user is not None and auth_user["user_id"] == user_id



    async def verify_backend_consistency(self, user_id: str) -> bool:

        """Verify Backend service data consistency."""

        workspace = await self.backend_ops.get_workspace(user_id)

        return workspace is not None and workspace["user_id"] == user_id



    async def verify_clickhouse_consistency(self, user_id: str, transaction_id: str) -> bool:

        """Verify ClickHouse event logging consistency."""

        events = await self.clickhouse_ops.get_user_events(user_id, transaction_id)

        return len(events) > 0



    async def verify_full_consistency(self, user_id: str, transaction_id: str) -> bool:

        """Verify data consistency across all services."""

        auth_ok = await self.verify_auth_consistency(user_id)

        backend_ok = await self.verify_backend_consistency(user_id)

        clickhouse_ok = await self.verify_clickhouse_consistency(user_id, transaction_id)

        return auth_ok and backend_ok and clickhouse_ok





class TransactionRollbackService:

    """Service for rolling back cross-service transactions."""

    

    def __init__(self, auth_ops, backend_ops):

        self.auth_ops = auth_ops

        self.backend_ops = backend_ops



    async def rollback_operation(self, operation: TransactionOperation) -> bool:

        """Rollback specific operation based on service."""

        try:

            if operation.service == "auth":

                await self._rollback_auth_operation(operation)

            elif operation.service == "backend":

                await self._rollback_backend_operation(operation)

            return True

        except Exception:

            return False



    async def _rollback_auth_operation(self, operation: TransactionOperation) -> None:

        """Rollback auth service operation."""

        if operation.rollback_data:

            await self.auth_ops.update_user(operation.rollback_data)

        else:

            await self.auth_ops.delete_user(operation.data["user_id"])



    async def _rollback_backend_operation(self, operation: TransactionOperation) -> None:

        """Rollback backend service operation."""

        if operation.rollback_data:

            await self.backend_ops.create_workspace(operation.rollback_data)

        else:

            await self.backend_ops.delete_workspace(operation.data["user_id"])


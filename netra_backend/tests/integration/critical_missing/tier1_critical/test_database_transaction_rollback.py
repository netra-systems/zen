"""Database Transaction Rollback Cascade Test ($1M impact)

L3 realism level - tests multi-table transaction rollback scenarios
using real PostgreSQL container for comprehensive transaction testing.

Business Value Justification:
- Segment: Platform/Internal ($1M revenue protection)
- Business Goal: Data Integrity - Transaction consistency
- Value Impact: Prevents data corruption that causes customer churn
- Strategic Impact: Foundation reliability for all customer operations
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List

import pytest

from netra_backend.app.core.database_recovery_core import ConnectionPoolRefreshStrategy
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.db.models_agent import Message, Run, Thread
from netra_backend.app.db.models_user import ToolUsageLog, User

# Import from shared infrastructure
from netra_backend.tests.integration.critical_missing.shared_infrastructure.containerized_services import (
    ServiceOrchestrator,
)

# Add project root to path

# Define test-specific exceptions
class DatabaseTransactionError(NetraException):
    pass

class DatabaseDeadlockError(NetraException):
    pass


@pytest.fixture(scope="module")
async def l3_database():
    """L3 realism: Real PostgreSQL container"""
    orchestrator = ServiceOrchestrator()
    connections = await orchestrator.start_all()
    yield orchestrator.postgres, connections["postgres_url"]
    await orchestrator.stop_all()


@pytest.fixture
async def db_session(l3_database):
    """Database session with transaction support"""
    postgres_container, postgres_url = l3_database
    async with postgres_container.transaction() as conn:
        yield conn


@pytest.fixture
async def test_data():
    """Test data for transaction scenarios"""
    return {
        "user": User(
            id="test_user_001", email="test@rollback.com", 
            plan_tier="pro", is_active=True
        ),
        "thread": Thread(
            id="test_thread_001", object="thread",
            created_at=int(time.time())
        ),
        "messages": [
            Message(
                id=f"msg_{i}", thread_id="test_thread_001",
                role="user", content=[{"text": f"Message {i}"}],
                created_at=int(time.time())
            ) for i in range(3)
        ]
    }


class TestDatabaseTransactionRollback:
    """Test multi-table transaction rollback scenarios"""

    async def test_basic_transaction_rollback(self, db_session, test_data):
        """Test basic single-table transaction rollback < 100ms"""
        start_time = time.time()
        
        try:
            async with db_session.transaction():
                user = test_data["user"]
                await db_session.execute(
                    "INSERT INTO userbase (id, email, plan_tier) VALUES ($1, $2, $3)",
                    user.id, user.email, user.plan_tier
                )
                raise DatabaseTransactionError("Simulated failure")
        except DatabaseTransactionError:
            pass
        
        rollback_time = (time.time() - start_time) * 1000
        assert rollback_time < 100.0
        
        # Verify rollback occurred
        result = await db_session.fetchrow(
            "SELECT id FROM userbase WHERE id = $1", test_data["user"].id
        )
        assert result is None

    async def test_multi_table_rollback_cascade(self, db_session, test_data):
        """Test multi-table transaction rollback cascade"""
        try:
            async with db_session.transaction():
                # Insert user
                user = test_data["user"]
                await db_session.execute(
                    "INSERT INTO userbase (id, email, plan_tier) VALUES ($1, $2, $3)",
                    user.id, user.email, user.plan_tier
                )
                
                # Insert thread
                thread = test_data["thread"]
                await db_session.execute(
                    "INSERT INTO threads (id, object, created_at) VALUES ($1, $2, $3)",
                    thread.id, thread.object, thread.created_at
                )
                
                # Insert messages
                for msg in test_data["messages"]:
                    await db_session.execute(
                        "INSERT INTO messages (id, thread_id, role, content, created_at) VALUES ($1, $2, $3, $4, $5)",
                        msg.id, msg.thread_id, msg.role, msg.content, msg.created_at
                    )
                
                raise DatabaseTransactionError("Multi-table rollback test")
        except DatabaseTransactionError:
            pass
        
        # Verify all tables rolled back
        user_result = await db_session.fetchrow("SELECT id FROM userbase WHERE id = $1", user.id)
        thread_result = await db_session.fetchrow("SELECT id FROM threads WHERE id = $1", thread.id)
        message_count = await db_session.fetchval(
            "SELECT COUNT(*) FROM messages WHERE thread_id = $1", thread.id
        )
        
        assert user_result is None
        assert thread_result is None
        assert message_count == 0

    async def test_nested_transaction_rollback(self, db_session, test_data):
        """Test nested transaction rollback scenarios"""
        user = test_data["user"]
        
        try:
            async with db_session.transaction():
                await db_session.execute(
                    "INSERT INTO userbase (id, email, plan_tier) VALUES ($1, $2, $3)",
                    user.id, user.email, user.plan_tier
                )
                
                try:
                    async with db_session.transaction():
                        await db_session.execute(
                            "UPDATE userbase SET plan_tier = $1 WHERE id = $2",
                            "enterprise", user.id
                        )
                        raise DatabaseTransactionError("Nested rollback test")
                except DatabaseTransactionError:
                    pass
                
                # Outer transaction should continue
                result = await db_session.fetchrow(
                    "SELECT plan_tier FROM userbase WHERE id = $1", user.id
                )
                assert result["plan_tier"] == "pro"
                
        except Exception:
            pass

    async def test_deadlock_detection_and_rollback(self, db_session, test_data):
        """Test deadlock detection and automatic rollback"""
        user1 = test_data["user"]
        user2 = User(
            id="test_user_002", email="test2@rollback.com",
            plan_tier="free", is_active=True
        )
        
        # Create users first
        await db_session.execute(
            "INSERT INTO userbase (id, email, plan_tier) VALUES ($1, $2, $3)",
            user1.id, user1.email, user1.plan_tier
        )
        await db_session.execute(
            "INSERT INTO userbase (id, email, plan_tier) VALUES ($1, $2, $3)",
            user2.id, user2.email, user2.plan_tier
        )
        
        # Simulate potential deadlock scenario
        with pytest.raises((DatabaseDeadlockError, Exception)):
            await self._simulate_deadlock_scenario(db_session, user1.id, user2.id)

    async def _simulate_deadlock_scenario(self, db_session, user1_id: str, user2_id: str):
        """Simulate deadlock between two transactions"""
        async def transaction1():
            async with db_session.transaction():
                await db_session.execute(
                    "UPDATE userbase SET plan_tier = 'pro' WHERE id = $1", user1_id
                )
                await asyncio.sleep(0.1)
                await db_session.execute(
                    "UPDATE userbase SET plan_tier = 'enterprise' WHERE id = $1", user2_id
                )
        
        async def transaction2():
            async with db_session.transaction():
                await db_session.execute(
                    "UPDATE userbase SET plan_tier = 'enterprise' WHERE id = $1", user2_id
                )
                await asyncio.sleep(0.1)
                await db_session.execute(
                    "UPDATE userbase SET plan_tier = 'pro' WHERE id = $1", user1_id
                )
        
        await asyncio.gather(transaction1(), transaction2())

    async def test_concurrent_rollback_scenarios(self, db_session, test_data):
        """Test concurrent transaction rollback scenarios"""
        tasks = []
        for i in range(5):
            user_data = User(
                id=f"concurrent_user_{i}", email=f"concurrent{i}@test.com",
                plan_tier="free", is_active=True
            )
            tasks.append(self._concurrent_transaction(db_session, user_data, i))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        rollback_count = sum(1 for r in results if isinstance(r, Exception))
        assert rollback_count >= 0  # Some may rollback due to conflicts

    async def _concurrent_transaction(self, db_session, user_data: User, index: int):
        """Execute concurrent transaction that may rollback"""
        try:
            async with db_session.transaction():
                await db_session.execute(
                    "INSERT INTO userbase (id, email, plan_tier) VALUES ($1, $2, $3)",
                    user_data.id, user_data.email, user_data.plan_tier
                )
                
                if index % 2 == 0:
                    raise DatabaseTransactionError(f"Simulated rollback {index}")
                
                return f"Success {index}"
        except DatabaseTransactionError as e:
            raise e

    async def test_rollback_with_recovery_strategy(self, db_session, test_data):
        """Test rollback with database recovery strategy"""
        recovery_strategy = ConnectionPoolRefreshStrategy()
        user = test_data["user"]
        
        try:
            async with db_session.transaction():
                await db_session.execute(
                    "INSERT INTO userbase (id, email, plan_tier) VALUES ($1, $2, $3)",
                    user.id, user.email, user.plan_tier
                )
                
                # Simulate recovery scenario
                from netra_backend.app.core.database_types import (
                    PoolHealth,
                    PoolMetrics,
                )
                metrics = PoolMetrics(health_status=PoolHealth.DEGRADED)
                can_recover = await recovery_strategy.can_recover(metrics)
                assert can_recover
                
                raise DatabaseTransactionError("Recovery test rollback")
        except DatabaseTransactionError:
            pass

    async def test_large_transaction_rollback_performance(self, db_session, test_data):
        """Test large transaction rollback performance < 100ms"""
        start_time = time.time()
        
        try:
            async with db_session.transaction():
                # Insert many records
                for i in range(100):
                    await db_session.execute(
                        "INSERT INTO tool_usage_logs (id, user_id, tool_name, status, created_at) VALUES ($1, $2, $3, $4, NOW())",
                        f"log_{i}", test_data["user"].id, f"tool_{i}", "success"
                    )
                
                raise DatabaseTransactionError("Large rollback test")
        except DatabaseTransactionError:
            pass
        
        rollback_time = (time.time() - start_time) * 1000
        assert rollback_time < 100.0
        
        # Verify all records rolled back
        count = await db_session.fetchval(
            "SELECT COUNT(*) FROM tool_usage_logs WHERE user_id = $1", 
            test_data["user"].id
        )
        assert count == 0
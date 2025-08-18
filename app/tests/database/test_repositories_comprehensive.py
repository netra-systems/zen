"""
Comprehensive repository tests (76-85) from top 100 missing tests.
Tests database operations, queries, and repository patterns.
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import hashlib
import json

# Test 76: Thread repository operations
class TestThreadRepositoryOperations:
    """test_thread_repository_operations - Test thread CRUD operations and soft delete"""
    
    async def test_thread_crud_operations(self):
        from app.services.database.thread_repository import ThreadRepository
        from app.schemas.database_schemas import Thread
        
        mock_session = AsyncMock(spec=AsyncSession)
        repo = ThreadRepository()
        
        # Test Create
        thread_data = {
            "user_id": "user123",
            "title": "Test Thread",
            "metadata": {"tags": ["test", "demo"]}
        }
        
        mock_session.execute.return_value.scalar_one_or_none.return_value = Thread(
            id="thread123",
            **thread_data,
            created_at=datetime.now(timezone.utc)
        )
        
        thread = await repo.create(mock_session, thread_data)
        assert thread.id == "thread123"
        assert thread.title == "Test Thread"
        
        # Test Read
        mock_session.execute.return_value.scalar_one_or_none.return_value = thread
        retrieved = await repo.get_by_id(mock_session, "thread123")
        assert retrieved.id == thread.id
        
        # Test Update
        update_data = {"title": "Updated Thread"}
        mock_session.execute.return_value.scalar_one_or_none.return_value = Thread(
            id="thread123",
            user_id="user123",
            title="Updated Thread",
            created_at=datetime.now(timezone.utc)
        )
        
        updated = await repo.update(mock_session, "thread123", update_data)
        assert updated.title == "Updated Thread"
        
        # Test Delete
        result = await repo.delete(mock_session, "thread123")
        assert result == True
    
    async def test_soft_delete_functionality(self):
        from app.services.database.thread_repository import ThreadRepository
        from app.schemas.database_schemas import Thread
        
        mock_session = AsyncMock(spec=AsyncSession)
        repo = ThreadRepository()
        
        # Soft delete
        thread = Thread(
            id="thread123",
            user_id="user123",
            title="Test Thread",
            deleted_at=None
        )
        
        mock_session.execute.return_value.scalar_one_or_none.return_value = thread
        
        await repo.soft_delete(mock_session, "thread123")
        
        # Verify soft delete sets deleted_at
        assert mock_session.execute.called
        update_call = mock_session.execute.call_args[0][0]
        assert "deleted_at" in str(update_call)
        
        # Test filtering out soft-deleted items
        mock_session.execute.return_value.scalars.return_value.all.return_value = [
            Thread(id="1", deleted_at=None),
            Thread(id="2", deleted_at=datetime.now(timezone.utc))
        ]
        
        active_threads = await repo.get_active_threads(mock_session, "user123")
        assert len([t for t in active_threads if t.deleted_at == None]) == 1


# Test 77: Message repository queries
class TestMessageRepositoryQueries:
    """test_message_repository_queries - Test message queries and pagination"""
    
    async def test_message_pagination(self):
        from app.services.database.message_repository import MessageRepository
        from app.schemas.database_schemas import Message
        
        mock_session = AsyncMock(spec=AsyncSession)
        repo = MessageRepository()
        
        # Create test messages
        messages = [
            Message(id=f"msg{i}", content=f"Message {i}", thread_id="thread1")
            for i in range(100)
        ]
        
        # Test pagination
        mock_session.execute.return_value.scalars.return_value.all.return_value = messages[:20]
        
        page1 = await repo.get_messages_paginated(
            mock_session, 
            thread_id="thread1",
            limit=20,
            offset=0
        )
        assert len(page1) == 20
        
        # Test with offset
        mock_session.execute.return_value.scalars.return_value.all.return_value = messages[20:40]
        
        page2 = await repo.get_messages_paginated(
            mock_session,
            thread_id="thread1", 
            limit=20,
            offset=20
        )
        assert len(page2) == 20
        assert page2[0].id == "msg20"
    
    async def test_complex_message_queries(self):
        from app.services.database.message_repository import MessageRepository
        from app.schemas.database_schemas import Message
        
        mock_session = AsyncMock(spec=AsyncSession)
        repo = MessageRepository()
        
        # Test search functionality
        mock_session.execute.return_value.scalars.return_value.all.return_value = [
            Message(id="1", content="Hello world"),
            Message(id="2", content="Hello there")
        ]
        
        results = await repo.search_messages(
            mock_session,
            query="Hello",
            thread_id="thread1"
        )
        assert len(results) == 2
        
        # Test date range queries
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)
        
        mock_session.execute.return_value.scalars.return_value.all.return_value = [
            Message(id="1", created_at=datetime.now(timezone.utc) - timedelta(days=1))
        ]
        
        recent_messages = await repo.get_messages_by_date_range(
            mock_session,
            thread_id="thread1",
            start_date=start_date,
            end_date=end_date
        )
        assert len(recent_messages) == 1


# Test 78: User repository authentication
class TestUserRepositoryAuth:
    """test_user_repository_auth - Test user authentication and password hashing"""
    
    async def test_password_hashing(self):
        from app.services.database.user_repository import UserRepository
        from app.schemas.database_schemas import User
        from argon2 import PasswordHasher
        
        mock_session = AsyncMock(spec=AsyncSession)
        repo = UserRepository()
        
        # Test password hashing on create
        user_data = {
            "email": "test@example.com",
            "password": "plaintext_password",
            "name": "Test User"
        }
        
        # Mock argon2 hasher
        with patch('argon2.PasswordHasher.hash') as mock_hash:
            mock_hash.return_value = 'hashed_password'
            mock_session.execute.return_value.scalar_one_or_none.return_value = User(
                id="user123",
                email=user_data["email"],
                password_hash="hashed_password"
            )
            
            user = await repo.create_user(mock_session, user_data)
            assert user.password_hash == "hashed_password"
            mock_hash.assert_called_once()
    
    async def test_authentication_flow(self):
        from app.services.database.user_repository import UserRepository
        from app.schemas.database_schemas import User
        from argon2 import PasswordHasher
        
        mock_session = AsyncMock(spec=AsyncSession)
        repo = UserRepository()
        
        # Test successful authentication
        ph = PasswordHasher()
        hashed = ph.hash("correct_password")
        mock_session.execute.return_value.scalar_one_or_none.return_value = User(
            id="user123",
            email="test@example.com",
            password_hash=hashed
        )
        
        authenticated = await repo.authenticate(
            mock_session,
            email="test@example.com",
            password="correct_password"
        )
        assert authenticated != None
        assert authenticated.id == "user123"
        
        # Test failed authentication
        authenticated = await repo.authenticate(
            mock_session,
            email="test@example.com",
            password="wrong_password"
        )
        assert authenticated == None


# Test 79: Optimization repository storage
class TestOptimizationRepositoryStorage:
    """test_optimization_repository_storage - Test optimization storage and versioning"""
    
    async def test_optimization_versioning(self):
        from app.services.database.optimization_repository import OptimizationRepository
        from app.schemas.database_schemas import Optimization
        
        mock_session = AsyncMock(spec=AsyncSession)
        repo = OptimizationRepository()
        
        # Create optimization with version
        opt_data = {
            "name": "Test Optimization",
            "config": {"param1": "value1"},
            "version": 1
        }
        
        mock_session.execute.return_value.scalar_one_or_none.return_value = Optimization(
            id="opt123",
            **opt_data
        )
        
        optimization = await repo.create(mock_session, opt_data)
        assert optimization.version == 1
        
        # Update creates new version
        update_data = {"config": {"param1": "value2"}}
        mock_session.execute.return_value.scalar_one_or_none.return_value = Optimization(
            id="opt124",
            name="Test Optimization",
            config={"param1": "value2"},
            version=2,
            parent_id="opt123"
        )
        
        new_version = await repo.create_new_version(
            mock_session,
            "opt123",
            update_data
        )
        assert new_version.version == 2
        assert new_version.parent_id == "opt123"
    
    async def test_optimization_history(self):
        from app.services.database.optimization_repository import OptimizationRepository
        from app.schemas.database_schemas import Optimization
        
        mock_session = AsyncMock(spec=AsyncSession)
        repo = OptimizationRepository()
        
        # Get optimization history
        mock_session.execute.return_value.scalars.return_value.all.return_value = [
            Optimization(id="opt1", version=1, created_at=datetime.now(timezone.utc) - timedelta(days=2)),
            Optimization(id="opt2", version=2, created_at=datetime.now(timezone.utc) - timedelta(days=1)),
            Optimization(id="opt3", version=3, created_at=datetime.now(timezone.utc))
        ]
        
        history = await repo.get_version_history(mock_session, "opt1")
        assert len(history) == 3
        assert history[0].version == 1
        assert history[-1].version == 3


# Test 80: Metric repository aggregation
class TestMetricRepositoryAggregation:
    """test_metric_repository_aggregation - Test metric aggregation and time-series queries"""
    
    async def test_metric_aggregation(self):
        from app.services.database.metric_repository import MetricRepository
        from app.schemas.database_schemas import Metric
        
        mock_session = AsyncMock(spec=AsyncSession)
        repo = MetricRepository()
        
        # Test aggregation functions
        metrics = [
            Metric(name="cpu_usage", value=50.0, timestamp=datetime.now(timezone.utc)),
            Metric(name="cpu_usage", value=60.0, timestamp=datetime.now(timezone.utc)),
            Metric(name="cpu_usage", value=70.0, timestamp=datetime.now(timezone.utc))
        ]
        
        mock_session.execute.return_value.scalar_one.return_value = 60.0  # Average
        
        avg = await repo.get_metric_average(
            mock_session,
            metric_name="cpu_usage",
            time_range=timedelta(hours=1)
        )
        assert avg == 60.0
        
        # Test max/min
        mock_session.execute.return_value.scalar_one.return_value = 70.0
        max_val = await repo.get_metric_max(
            mock_session,
            metric_name="cpu_usage",
            time_range=timedelta(hours=1)
        )
        assert max_val == 70.0
    
    async def test_time_series_queries(self):
        from app.services.database.metric_repository import MetricRepository
        from app.schemas.database_schemas import Metric
        
        mock_session = AsyncMock(spec=AsyncSession)
        repo = MetricRepository()
        
        # Test time bucketing
        now = datetime.now(timezone.utc)
        mock_session.execute.return_value.all.return_value = [
            (now - timedelta(minutes=30), 50.0),
            (now - timedelta(minutes=20), 55.0),
            (now - timedelta(minutes=10), 60.0),
            (now, 65.0)
        ]
        
        time_series = await repo.get_time_series(
            mock_session,
            metric_name="cpu_usage",
            interval="10m",
            time_range=timedelta(hours=1)
        )
        assert len(time_series) == 4
        assert time_series[-1][1] == 65.0


# Test 81: ClickHouse connection pool
class TestClickHouseConnectionPool:
    """test_clickhouse_connection_pool - Test connection pooling and query timeout"""
    
    async def test_connection_pooling(self):
        from app.db.clickhouse import ClickHouseDatabase
        
        with patch('clickhouse_driver.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            db = ClickHouseDatabase(
                host="localhost",
                port=9000,
                database="test",
                pool_size=5
            )
            
            # Test pool creation
            await db.initialize_pool()
            assert db.pool_size == 5
            
            # Test connection reuse
            conn1 = await db.get_connection()
            await db.release_connection(conn1)
            conn2 = await db.get_connection()
            assert conn1 is conn2  # Should reuse connection
            
            # Test pool exhaustion handling
            connections = []
            for _ in range(5):
                connections.append(await db.get_connection())
            
            # Pool exhausted, should wait or create new
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(db.get_connection(), timeout=0.1)
    
    async def test_query_timeout(self):
        from app.db.clickhouse import ClickHouseDatabase
        
        with patch('clickhouse_driver.Client') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Simulate slow query
            async def slow_query(*args, **kwargs):
                await asyncio.sleep(5)
                return []
            
            mock_client.execute_query = slow_query
            
            db = ClickHouseDatabase(
                host="localhost",
                query_timeout=1
            )
            
            with pytest.raises(asyncio.TimeoutError):
                await db.execute_query("SELECT sleep(10)")


# Test 82: Migration runner safety
class TestMigrationRunnerSafety:
    """test_migration_runner_safety - Test migration safety and rollback capability"""
    
    async def test_migration_rollback(self):
        from app.db.migrations.migration_runner import MigrationRunner
        
        mock_session = AsyncMock(spec=AsyncSession)
        runner = MigrationRunner(mock_session)
        
        # Test rollback on failure
        class FailingMigration:
            async def up(self, session):
                raise Exception("Migration failed")
            
            async def down(self, session):
                pass
        
        migration = FailingMigration()
        
        with pytest.raises(Exception):
            await runner.run_migration(migration)
        
        # Verify rollback was called
        assert mock_session.rollback.called
    
    async def test_migration_transaction_safety(self):
        from app.db.migrations.migration_runner import MigrationRunner
        
        mock_session = AsyncMock(spec=AsyncSession)
        runner = MigrationRunner(mock_session)
        
        # Test transaction boundaries
        class TestMigration:
            async def up(self, session):
                await session.execute("CREATE TABLE test_table (id INT)")
                await session.execute("INSERT INTO test_table VALUES (1)")
        
        migration = TestMigration()
        
        await runner.run_migration(migration)
        
        # Verify transaction was used
        assert mock_session.begin.called
        assert mock_session.commit.called


# Test 83: Database health checks
class TestDatabaseHealthChecks:
    """test_database_health_checks - Test health monitoring and alert thresholds"""
    
    async def test_health_monitoring(self):
        from app.db.health_checks import DatabaseHealthChecker
        
        mock_session = AsyncMock(spec=AsyncSession)
        checker = DatabaseHealthChecker(mock_session)
        
        # Test connection health
        mock_session.execute.return_value.scalar.return_value = 1
        
        health = await checker.check_connection_health()
        assert health["status"] == "healthy"
        assert health["response_time"] < 1000  # ms
        
        # Test unhealthy connection
        mock_session.execute.side_effect = Exception("Connection failed")
        
        health = await checker.check_connection_health()
        assert health["status"] == "unhealthy"
        assert "error" in health
    
    async def test_alert_thresholds(self):
        from app.db.health_checks import DatabaseHealthChecker
        
        mock_session = AsyncMock(spec=AsyncSession)
        checker = DatabaseHealthChecker(mock_session)
        
        # Test slow query alert
        mock_session.execute.return_value.all.return_value = [
            ("SELECT * FROM large_table", 5000)  # 5 second query
        ]
        
        alerts = await checker.check_slow_queries(threshold_ms=1000)
        assert len(alerts) == 1
        assert alerts[0]["query_time"] == 5000
        
        # Test connection pool alert
        mock_session.execute.return_value.scalar.return_value = 95  # 95% pool usage
        
        pool_alert = await checker.check_connection_pool(threshold_percent=80)
        assert pool_alert["alert"] == True
        assert pool_alert["usage"] == 95


# Test 84 and 85 removed - cache_service and session_service don't exist
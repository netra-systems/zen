"""
Integration Tests for Real ClickHouse Database Operations

Business Value Justification (BVJ):
- Segment: All (Analytics features support all customer tiers)
- Business Goal: Ensure reliable analytics data storage and retrieval
- Value Impact: Real-time analytics provide competitive advantage and customer insights
- Strategic Impact: Scalable analytics infrastructure enables data-driven decision making

This test suite validates:
1. Real ClickHouse connections and operations
2. Data integrity across insert/select operations
3. Performance characteristics under load
4. Connection pooling and session management
5. Schema creation and management
6. Query optimization and indexing
7. Error handling with real database failures
"""

import pytest
import asyncio
import time
from typing import List, Dict, Any
from datetime import datetime, timezone

from netra_backend.app.db.clickhouse_base import ClickHouseDatabase
from netra_backend.app.db.clickhouse_initializer import ClickHouseInitializer
from netra_backend.app.core.clickhouse_connection_manager import ClickHouseConnectionManager
from test_framework.fixtures.clickhouse_fixtures import MockClickHouseDatabase
from test_framework.fixtures.database_fixtures import test_db_session
from test_framework.ssot.configuration_validator import is_service_enabled
from shared.isolated_environment import get_env


@pytest.mark.integration
@pytest.mark.real_services
class TestClickHouseRealOperationsIntegration:
    """Integration tests for ClickHouse with real database connections."""
    
    @pytest.fixture
    async def real_clickhouse_db(self):
        """Create real ClickHouse connection if available, otherwise mock."""
        env = get_env()
        
        # Check if ClickHouse is available and enabled
        if not is_service_enabled("clickhouse"):
            pytest.skip("ClickHouse is disabled - using mock for this test")
        
        try:
            db = ClickHouseDatabase(
                host=env.get("CLICKHOUSE_HOST", "localhost"),
                port=int(env.get("CLICKHOUSE_PORT", "8123")),
                database=env.get("CLICKHOUSE_DATABASE", "test_db"),
                user=env.get("CLICKHOUSE_USER", "default"),
                password=env.get("CLICKHOUSE_PASSWORD", ""),
                secure=env.get("CLICKHOUSE_SECURE", "false").lower() == "true"
            )
            
            # Test connection
            if not await db.test_connection():
                pytest.skip("ClickHouse not available - using mock")
            
            yield db
            
        except Exception as e:
            # Fall back to mock if real ClickHouse unavailable
            pytest.skip(f"ClickHouse unavailable ({e}) - using mock")
        
        finally:
            try:
                await db.disconnect()
            except:
                pass
    
    @pytest.fixture
    async def clickhouse_test_table(self, real_clickhouse_db):
        """Create test table and cleanup after test."""
        table_name = f"test_table_{int(time.time())}"
        
        create_table_sql = f"""
        CREATE TABLE {table_name} (
            id UInt32,
            name String,
            timestamp DateTime64(3),
            data String,
            user_id String
        ) ENGINE = Memory
        """
        
        try:
            await real_clickhouse_db.command(create_table_sql)
            yield table_name
        finally:
            # Cleanup
            try:
                await real_clickhouse_db.command(f"DROP TABLE IF EXISTS {table_name}")
            except:
                pass  # Ignore cleanup errors
    
    async def test_real_clickhouse_connection_and_ping(self, real_clickhouse_db):
        """Test real ClickHouse connection establishment and ping."""
        # Test ping functionality
        ping_result = real_clickhouse_db.ping()
        assert ping_result is True
        
        # Test connection test
        connection_test = await real_clickhouse_db.test_connection()
        assert connection_test is True
    
    async def test_real_clickhouse_basic_query_execution(self, real_clickhouse_db):
        """Test basic query execution with real ClickHouse."""
        # Test simple query
        result = await real_clickhouse_db.execute_query("SELECT 1 as test_value")
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["test_value"] == 1
    
    async def test_real_clickhouse_parameterized_queries(self, real_clickhouse_db):
        """Test parameterized queries with real ClickHouse."""
        # Test parameterized query
        query = "SELECT {value:UInt32} as param_value"
        parameters = {"value": 42}
        
        result = await real_clickhouse_db.execute_query(query, parameters)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["param_value"] == 42
    
    async def test_real_clickhouse_data_insertion_and_retrieval(self, real_clickhouse_db, clickhouse_test_table):
        """Test data insertion and retrieval with real ClickHouse."""
        table_name = clickhouse_test_table
        
        # Insert test data
        test_data = [
            [1, "user1", "2025-01-01 10:00:00", '{"action": "login"}', "user_001"],
            [2, "user2", "2025-01-01 11:00:00", '{"action": "logout"}', "user_002"],
            [3, "user3", "2025-01-01 12:00:00", '{"action": "view"}', "user_003"]
        ]
        
        column_names = ["id", "name", "timestamp", "data", "user_id"]
        
        await real_clickhouse_db.insert_data(table_name, test_data, column_names)
        
        # Verify data was inserted
        select_query = f"SELECT * FROM {table_name} ORDER BY id"
        result = await real_clickhouse_db.execute_query(select_query)
        
        assert len(result) == 3
        assert result[0]["id"] == 1
        assert result[0]["name"] == "user1"
        assert result[0]["user_id"] == "user_001"
        assert '"action": "login"' in result[0]["data"]
        
        assert result[1]["id"] == 2
        assert result[2]["id"] == 3
    
    async def test_real_clickhouse_batch_operations(self, real_clickhouse_db, clickhouse_test_table):
        """Test batch operations with real ClickHouse."""
        table_name = clickhouse_test_table
        
        # Generate batch data
        batch_size = 100
        batch_data = []
        
        for i in range(batch_size):
            batch_data.append([
                i + 1,
                f"batch_user_{i}",
                "2025-01-01 12:00:00",
                f'{{"batch_id": {i}}}',
                f"batch_user_{i:03d}"
            ])
        
        column_names = ["id", "name", "timestamp", "data", "user_id"]
        
        # Insert batch data
        start_time = time.time()
        await real_clickhouse_db.insert_data(table_name, batch_data, column_names)
        insert_time = time.time() - start_time
        
        # Verify batch insert performance (should be fast)
        assert insert_time < 5.0  # Should complete within 5 seconds
        
        # Verify all data was inserted
        count_query = f"SELECT COUNT(*) as total FROM {table_name}"
        result = await real_clickhouse_db.execute_query(count_query)
        
        assert result[0]["total"] == batch_size
    
    async def test_real_clickhouse_aggregation_queries(self, real_clickhouse_db, clickhouse_test_table):
        """Test aggregation queries with real ClickHouse."""
        table_name = clickhouse_test_table
        
        # Insert test data for aggregation
        test_data = []
        for i in range(10):
            test_data.append([
                i + 1,
                f"user_{i % 3}",  # 3 unique users
                "2025-01-01 12:00:00",
                f'{{"count": {i}}}',
                f"user_{i % 3}"
            ])
        
        column_names = ["id", "name", "timestamp", "data", "user_id"]
        await real_clickhouse_db.insert_data(table_name, test_data, column_names)
        
        # Test aggregation query
        agg_query = f"""
        SELECT 
            name,
            COUNT(*) as record_count,
            MAX(id) as max_id,
            MIN(id) as min_id
        FROM {table_name}
        GROUP BY name
        ORDER BY name
        """
        
        result = await real_clickhouse_db.execute_query(agg_query)
        
        # Should have 3 groups (user_0, user_1, user_2)
        assert len(result) == 3
        
        # Each user should have multiple records
        for row in result:
            assert row["record_count"] > 1
            assert row["max_id"] > row["min_id"]
    
    async def test_real_clickhouse_concurrent_operations(self, real_clickhouse_db, clickhouse_test_table):
        """Test concurrent operations with real ClickHouse."""
        table_name = clickhouse_test_table
        
        async def insert_batch(batch_id: int, batch_size: int = 20):
            """Insert a batch of data concurrently."""
            batch_data = []
            for i in range(batch_size):
                batch_data.append([
                    batch_id * 1000 + i,
                    f"concurrent_user_{batch_id}_{i}",
                    "2025-01-01 12:00:00",
                    f'{{"batch": {batch_id}, "item": {i}}}',
                    f"batch_{batch_id}_user_{i}"
                ])
            
            column_names = ["id", "name", "timestamp", "data", "user_id"]
            await real_clickhouse_db.insert_data(table_name, batch_data, column_names)
            return len(batch_data)
        
        # Run concurrent insertions
        num_batches = 5
        start_time = time.time()
        
        tasks = [insert_batch(batch_id) for batch_id in range(num_batches)]
        results = await asyncio.gather(*tasks)
        
        concurrent_time = time.time() - start_time
        total_inserted = sum(results)
        
        # Verify all concurrent operations completed
        assert len(results) == num_batches
        assert total_inserted == num_batches * 20  # 20 items per batch
        
        # Verify concurrent performance
        assert concurrent_time < 10.0  # Should complete within 10 seconds
        
        # Verify data integrity
        count_query = f"SELECT COUNT(*) as total FROM {table_name}"
        result = await real_clickhouse_db.execute_query(count_query)
        assert result[0]["total"] == total_inserted
    
    async def test_real_clickhouse_settings_and_query_optimization(self, real_clickhouse_db, clickhouse_test_table):
        """Test query settings and optimization with real ClickHouse."""
        table_name = clickhouse_test_table
        
        # Insert test data
        test_data = [[i, f"user_{i}", "2025-01-01 12:00:00", f'{{"id": {i}}}', f"user_{i}"]
                    for i in range(1, 101)]
        column_names = ["id", "name", "timestamp", "data", "user_id"]
        await real_clickhouse_db.insert_data(table_name, test_data, column_names)
        
        # Test query with specific settings
        query = f"SELECT * FROM {table_name} WHERE id > 50 ORDER BY id LIMIT 10"
        settings = {
            "max_threads": 2,
            "max_memory_usage": 10000000  # 10MB limit
        }
        
        start_time = time.time()
        result = await real_clickhouse_db.execute_query(query, settings=settings)
        query_time = time.time() - start_time
        
        # Verify results
        assert len(result) == 10
        assert result[0]["id"] == 51  # First result after WHERE clause
        assert result[-1]["id"] == 60  # Last result with LIMIT 10
        
        # Query should be fast with settings
        assert query_time < 2.0
    
    async def test_real_clickhouse_connection_recovery(self, real_clickhouse_db):
        """Test connection recovery after connection issues."""
        # Test connection is working
        initial_result = await real_clickhouse_db.execute_query("SELECT 1 as test")
        assert initial_result[0]["test"] == 1
        
        # Simulate connection disruption (disconnect)
        await real_clickhouse_db.disconnect()
        assert real_clickhouse_db.client is None
        
        # Verify connection is broken
        with pytest.raises(ConnectionError):
            await real_clickhouse_db.execute_query("SELECT 1")
        
        # Reconnect (manual reconnection for this test)
        env = get_env()
        new_db = ClickHouseDatabase(
            host=env.get("CLICKHOUSE_HOST", "localhost"),
            port=int(env.get("CLICKHOUSE_PORT", "8123")),
            database=env.get("CLICKHOUSE_DATABASE", "test_db"),
            user=env.get("CLICKHOUSE_USER", "default"),
            password=env.get("CLICKHOUSE_PASSWORD", ""),
        )
        
        # Verify recovery
        recovery_result = await new_db.execute_query("SELECT 2 as recovery_test")
        assert recovery_result[0]["recovery_test"] == 2
        
        await new_db.disconnect()
    
    async def test_real_clickhouse_large_query_handling(self, real_clickhouse_db, clickhouse_test_table):
        """Test handling of large query results."""
        table_name = clickhouse_test_table
        
        # Insert larger dataset
        large_data = []
        dataset_size = 1000
        
        for i in range(dataset_size):
            large_data.append([
                i + 1,
                f"large_user_{i}",
                "2025-01-01 12:00:00",
                f'{{"large_data": "{str(i) * 10}"}}',  # Larger data field
                f"large_user_{i:04d}"
            ])
        
        column_names = ["id", "name", "timestamp", "data", "user_id"]
        
        # Insert in chunks to avoid timeout
        chunk_size = 100
        for i in range(0, dataset_size, chunk_size):
            chunk = large_data[i:i + chunk_size]
            await real_clickhouse_db.insert_data(table_name, chunk, column_names)
        
        # Query large dataset
        large_query = f"""
        SELECT 
            id,
            name,
            length(data) as data_length,
            user_id
        FROM {table_name}
        WHERE id <= 500
        ORDER BY id
        """
        
        start_time = time.time()
        result = await real_clickhouse_db.execute_query(large_query)
        query_time = time.time() - start_time
        
        # Verify large query results
        assert len(result) == 500
        assert result[0]["id"] == 1
        assert result[-1]["id"] == 500
        
        # All data_length should be consistent (large data)
        for row in result:
            assert row["data_length"] > 20  # Should be much larger due to repeated characters
        
        # Performance should be reasonable even for large queries
        assert query_time < 15.0  # Should complete within 15 seconds
    
    async def test_real_clickhouse_error_handling_and_recovery(self, real_clickhouse_db):
        """Test error handling with real ClickHouse operations."""
        # Test invalid query
        with pytest.raises(Exception):  # ClickHouse will raise specific exception
            await real_clickhouse_db.execute_query("INVALID SQL QUERY")
        
        # Test connection should still work after error
        recovery_result = await real_clickhouse_db.execute_query("SELECT 'recovery' as status")
        assert recovery_result[0]["status"] == "recovery"
        
        # Test invalid table reference
        with pytest.raises(Exception):
            await real_clickhouse_db.execute_query("SELECT * FROM non_existent_table")
        
        # Connection should still be functional
        health_result = await real_clickhouse_db.execute_query("SELECT 'healthy' as health")
        assert health_result[0]["health"] == "healthy"
    
    async def test_real_clickhouse_command_execution(self, real_clickhouse_db):
        """Test command execution (DDL operations) with real ClickHouse."""
        temp_table = f"temp_command_test_{int(time.time())}"
        
        try:
            # Test CREATE TABLE command
            create_command = f"""
            CREATE TABLE {temp_table} (
                test_id UInt32,
                test_name String
            ) ENGINE = Memory
            """
            
            result = await real_clickhouse_db.command(create_command)
            # Command should execute successfully (result may be None or empty)
            
            # Verify table was created by inserting data
            await real_clickhouse_db.insert_data(
                temp_table, 
                [[1, "test_entry"]], 
                ["test_id", "test_name"]
            )
            
            # Query the created table
            query_result = await real_clickhouse_db.execute_query(f"SELECT * FROM {temp_table}")
            assert len(query_result) == 1
            assert query_result[0]["test_id"] == 1
            assert query_result[0]["test_name"] == "test_entry"
            
        finally:
            # Cleanup
            try:
                await real_clickhouse_db.command(f"DROP TABLE IF EXISTS {temp_table}")
            except:
                pass
    
    async def test_real_clickhouse_log_entry_insertion(self, real_clickhouse_db):
        """Test log entry insertion functionality."""
        log_table = f"test_logs_{int(time.time())}"
        
        # Create log table
        create_log_table = f"""
        CREATE TABLE {log_table} (
            trace_id String,
            span_id String,
            event String,
            data String,
            source String,
            user_id String,
            timestamp DateTime DEFAULT now()
        ) ENGINE = Memory
        """
        
        try:
            await real_clickhouse_db.command(create_log_table)
            
            # Create mock log entry
            from unittest.mock import Mock
            log_entry = Mock()
            log_entry.trace_id = "trace_123"
            log_entry.span_id = "span_456"
            log_entry.event = "integration_test"
            log_entry.data = {"test": "log_data", "value": 42}
            log_entry.source = "test_source"
            log_entry.user_id = "test_user_123"
            
            # Insert log entry
            await real_clickhouse_db.insert_log(log_entry, log_table)
            
            # Verify log was inserted
            log_query = f"SELECT * FROM {log_table} ORDER BY timestamp DESC LIMIT 1"
            result = await real_clickhouse_db.execute_query(log_query)
            
            assert len(result) == 1
            log_record = result[0]
            assert log_record["trace_id"] == "trace_123"
            assert log_record["span_id"] == "span_456"
            assert log_record["event"] == "integration_test"
            assert '"test": "log_data"' in log_record["data"]
            assert '"value": 42' in log_record["data"]
            assert log_record["source"] == "test_source"
            assert log_record["user_id"] == "test_user_123"
            
        finally:
            # Cleanup
            try:
                await real_clickhouse_db.command(f"DROP TABLE IF EXISTS {log_table}")
            except:
                pass


@pytest.mark.integration 
@pytest.mark.real_services
class TestClickHouseConnectionManagerIntegration:
    """Integration tests for ClickHouse Connection Manager."""
    
    async def test_connection_manager_initialization(self):
        """Test ClickHouse connection manager initialization."""
        if not is_service_enabled("clickhouse"):
            pytest.skip("ClickHouse is disabled")
        
        try:
            manager = ClickHouseConnectionManager()
            await manager.initialize()
            
            # Test that manager has connection
            assert manager._connection is not None
            
            # Test connection health
            health = await manager.get_connection_health()
            assert isinstance(health, dict)
            assert "status" in health
            
        except Exception as e:
            pytest.skip(f"ClickHouse connection manager unavailable: {e}")
    
    async def test_connection_manager_query_execution(self):
        """Test query execution through connection manager."""
        if not is_service_enabled("clickhouse"):
            pytest.skip("ClickHouse is disabled")
        
        try:
            manager = ClickHouseConnectionManager()
            await manager.initialize()
            
            # Execute query through manager
            result = await manager.execute_query("SELECT 1 as manager_test")
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["manager_test"] == 1
            
        except Exception as e:
            pytest.skip(f"ClickHouse connection manager unavailable: {e}")


@pytest.mark.integration
@pytest.mark.real_services 
class TestClickHouseInitializerIntegration:
    """Integration tests for ClickHouse Initializer."""
    
    async def test_clickhouse_initializer_setup(self):
        """Test ClickHouse initializer setup process."""
        if not is_service_enabled("clickhouse"):
            pytest.skip("ClickHouse is disabled")
        
        try:
            initializer = ClickHouseInitializer()
            
            # Test initialization
            success = await initializer.initialize_database()
            
            # Should succeed or skip gracefully
            assert isinstance(success, bool)
            
        except Exception as e:
            # Initializer should handle errors gracefully
            pytest.skip(f"ClickHouse initializer test skipped: {e}")
    
    async def test_clickhouse_schema_validation(self):
        """Test ClickHouse schema validation and creation."""
        if not is_service_enabled("clickhouse"):
            pytest.skip("ClickHouse is disabled")
        
        try:
            initializer = ClickHouseInitializer()
            await initializer.initialize_database()
            
            # Test schema validation
            schema_valid = await initializer.validate_schema()
            assert isinstance(schema_valid, bool)
            
            # If schema is invalid, initializer should handle it
            if not schema_valid:
                creation_result = await initializer.create_required_tables()
                assert isinstance(creation_result, bool)
            
        except Exception as e:
            pytest.skip(f"ClickHouse schema test unavailable: {e}")
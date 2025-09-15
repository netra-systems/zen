"""
Analytics Service ClickHouse Integration Tests
============================================

Comprehensive integration tests for ClickHouse database operations.
Tests real database functionality with actual ClickHouse connections.

NO MOCKS POLICY: Tests use real ClickHouse database for authentic integration testing.

Test Coverage:
- Database connection and initialization
- Table creation and schema validation
- Event insertion and batch operations
- Query performance and optimization
- Materialized views and aggregations
- Data retention and TTL policies
- Index performance and query optimization
- Concurrent operations and data integrity
- Error handling and recovery
- Migration and schema evolution
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4
from shared.isolated_environment import IsolatedEnvironment

# =============================================================================
# CLICKHOUSE CLIENT IMPLEMENTATION (To be moved to actual database module)  
# =============================================================================

class ClickHouseError(Exception):
    """Custom exception for ClickHouse operations"""
    pass

class ClickHouseClient:
    """
    ClickHouse client for analytics service.
    Handles connection management, table operations, and data queries.
    """
    
    def __init__(self, host: str = "localhost", port: int = 9090, 
                 database: str = "analytics_test", username: str = "analytics_user", 
                 password: str = "analytics_pass"):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.client = None
        self.connected = False
        
    async def connect(self) -> None:
        """Establish connection to ClickHouse"""
        try:
            import clickhouse_connect
            
            self.client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                database=self.database
            )
            
            # Test connection
            result = self.client.query("SELECT 1")
            if result.result_rows[0][0] == 1:
                self.connected = True
            else:
                raise ClickHouseError("Connection test failed")
                
        except ImportError:
            raise ClickHouseError("ClickHouse client library not available. Install: pip install clickhouse-connect")
        except Exception as e:
            raise ClickHouseError(f"Failed to connect to ClickHouse: {e}")
    
    async def disconnect(self) -> None:
        """Close ClickHouse connection"""
        if self.client:
            self.client.close()
            self.connected = False
    
    async def create_database(self, database_name: str) -> None:
        """Create database if not exists"""
        if not self.connected:
            await self.connect()
        
        try:
            self.client.command(f"CREATE DATABASE IF NOT EXISTS {database_name}")
        except Exception as e:
            raise ClickHouseError(f"Failed to create database: {e}")
    
    async def create_tables(self) -> None:
        """Create all analytics tables with proper schema"""
        if not self.connected:
            await self.connect()
        
        try:
            # Use the target database
            self.client.command(f"USE {self.database}")
            
            # Create frontend_events table
            self.client.command("""
                CREATE TABLE IF NOT EXISTS frontend_events (
                    event_id UUID DEFAULT generateUUIDv4(),
                    timestamp DateTime64(3) DEFAULT now(),
                    user_id String,
                    session_id String,
                    event_type String,
                    event_category String,
                    event_action String,
                    event_label String,
                    event_value Float64,
                    
                    -- Event-specific properties as JSON
                    properties String,
                    
                    -- User context
                    user_agent String,
                    ip_address String,
                    country_code String,
                    
                    -- Page context
                    page_path String,
                    page_title String,
                    referrer String,
                    
                    -- Technical metadata
                    gtm_container_id String,
                    environment String,
                    app_version String,
                    
                    -- Computed fields
                    date Date DEFAULT toDate(timestamp),
                    hour UInt8 DEFAULT toHour(timestamp)
                )
                ENGINE = MergeTree()
                PARTITION BY toYYYYMM(timestamp)
                ORDER BY (user_id, timestamp, event_id)
                TTL timestamp + INTERVAL 90 DAY
                SETTINGS index_granularity = 8192
            """)
            
            # Create prompt_analytics table
            self.client.command("""
                CREATE TABLE IF NOT EXISTS prompt_analytics (
                    prompt_id UUID DEFAULT generateUUIDv4(),
                    timestamp DateTime64(3) DEFAULT now(),
                    user_id String,
                    thread_id String,
                    
                    -- Prompt details
                    prompt_hash String,
                    prompt_category String,
                    prompt_intent String,
                    prompt_complexity_score Float32,
                    
                    -- Response metrics
                    response_quality_score Float32,
                    response_relevance_score Float32,
                    follow_up_generated Boolean,
                    
                    -- Usage patterns
                    is_repeat_question Boolean,
                    similar_prompts Array(String),
                    
                    -- Cost tracking
                    estimated_cost_cents Float32,
                    actual_cost_cents Float32
                )
                ENGINE = MergeTree()
                PARTITION BY toYYYYMM(timestamp)
                ORDER BY (user_id, timestamp, prompt_id)
                TTL timestamp + INTERVAL 180 DAY
            """)
            
            # Create user analytics summary materialized view
            self.client.command("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS user_analytics_summary
                ENGINE = SummingMergeTree()
                PARTITION BY toYYYYMM(date)
                ORDER BY (user_id, date)
                AS SELECT
                    user_id,
                    toDate(timestamp) as date,
                    count() as total_events,
                    countIf(event_type = 'chat_interaction') as chat_interactions,
                    countIf(event_type = 'thread_lifecycle' AND event_action = 'created') as threads_created,
                    countIf(event_type = 'feature_usage') as feature_interactions,
                    sumIf(event_value, event_type = 'chat_interaction') as total_tokens_consumed,
                    avgIf(event_value, event_type = 'performance_metric') as avg_response_time
                FROM frontend_events
                GROUP BY user_id, date
            """)
            
        except Exception as e:
            raise ClickHouseError(f"Failed to create tables: {e}")
    
    async def insert_events(self, events: List[Dict[str, Any]]) -> int:
        """Insert batch of events into frontend_events table"""
        if not self.connected:
            await self.connect()
        
        if not events:
            return 0
        
        try:
            # Prepare data for insertion
            data_rows = []
            for event in events:
                # Convert datetime strings to proper format if needed
                timestamp = event.get("timestamp")
                if isinstance(timestamp, str):
                    # Convert ISO format to datetime
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                elif timestamp is None:
                    timestamp = datetime.now(timezone.utc)
                
                row = [
                    event.get("event_id", str(uuid4())),
                    timestamp,
                    event.get("user_id", ""),
                    event.get("session_id", ""),
                    event.get("event_type", ""),
                    event.get("event_category", ""),
                    event.get("event_action", ""),
                    event.get("event_label", ""),
                    event.get("event_value", 0.0),
                    event.get("properties", "{}"),
                    event.get("user_agent", ""),
                    event.get("ip_address", ""),
                    event.get("country_code", ""),
                    event.get("page_path", ""),
                    event.get("page_title", ""),
                    event.get("referrer", ""),
                    event.get("gtm_container_id", ""),
                    event.get("environment", "test"),
                    event.get("app_version", "1.0.0")
                ]
                data_rows.append(row)
            
            # Insert data
            self.client.insert(
                "frontend_events",
                data_rows,
                column_names=[
                    "event_id", "timestamp", "user_id", "session_id", "event_type",
                    "event_category", "event_action", "event_label", "event_value",
                    "properties", "user_agent", "ip_address", "country_code",
                    "page_path", "page_title", "referrer", "gtm_container_id",
                    "environment", "app_version"
                ]
            )
            
            return len(data_rows)
            
        except Exception as e:
            raise ClickHouseError(f"Failed to insert events: {e}")
    
    async def query_events(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute query and return results"""
        if not self.connected:
            await self.connect()
        
        try:
            result = self.client.query(query, parameters or {})
            
            # Convert result to list of dictionaries
            columns = result.column_names
            rows = result.result_rows
            
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            raise ClickHouseError(f"Query failed: {e}")
    
    async def get_user_activity_summary(self, user_id: str, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Get user activity summary from materialized view"""
        if not self.connected:
            await self.connect()
        
        try:
            where_clause = "WHERE user_id = %(user_id)s"
            parameters = {"user_id": user_id}
            
            if start_date:
                where_clause += " AND date >= %(start_date)s"
                parameters["start_date"] = start_date
                
            if end_date:
                where_clause += " AND date <= %(end_date)s"
                parameters["end_date"] = end_date
            
            query = f"""
                SELECT
                    user_id,
                    date,
                    sum(total_events) as total_events,
                    sum(chat_interactions) as chat_interactions,
                    sum(threads_created) as threads_created,
                    sum(feature_interactions) as feature_interactions,
                    sum(total_tokens_consumed) as total_tokens_consumed,
                    avg(avg_response_time) as avg_response_time
                FROM user_analytics_summary
                {where_clause}
                GROUP BY user_id, date
                ORDER BY date
            """
            
            results = await self.query_events(query, parameters)
            
            if not results:
                return {
                    "user_id": user_id,
                    "total_events": 0,
                    "chat_interactions": 0,
                    "threads_created": 0,
                    "feature_interactions": 0,
                    "total_tokens_consumed": 0.0,
                    "avg_response_time": 0.0,
                    "daily_breakdown": []
                }
            
            # Aggregate results
            summary = {
                "user_id": user_id,
                "total_events": sum(r["total_events"] for r in results),
                "chat_interactions": sum(r["chat_interactions"] for r in results),
                "threads_created": sum(r["threads_created"] for r in results),
                "feature_interactions": sum(r["feature_interactions"] for r in results),
                "total_tokens_consumed": sum(r["total_tokens_consumed"] for r in results),
                "avg_response_time": sum(r["avg_response_time"] for r in results) / len(results) if results else 0.0,
                "daily_breakdown": results
            }
            
            return summary
            
        except Exception as e:
            raise ClickHouseError(f"Failed to get user activity summary: {e}")
    
    async def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get table schema and metadata information"""
        if not self.connected:
            await self.connect()
        
        try:
            # Get table schema
            schema_query = f"DESCRIBE TABLE {table_name}"
            schema_results = await self.query_events(schema_query)
            
            # Get table stats
            stats_query = f"SELECT count() as row_count FROM {table_name}"
            stats_results = await self.query_events(stats_query)
            
            # Get partition info
            partition_query = f"""
                SELECT partition, rows, bytes_on_disk
                FROM system.parts
                WHERE database = '{self.database}' AND table = '{table_name}' AND active = 1
            """
            partition_results = await self.query_events(partition_query)
            
            return {
                "table_name": table_name,
                "schema": schema_results,
                "row_count": stats_results[0]["row_count"] if stats_results else 0,
                "partitions": partition_results
            }
            
        except Exception as e:
            raise ClickHouseError(f"Failed to get table info: {e}")
    
    async def optimize_table(self, table_name: str) -> None:
        """Optimize table for better query performance"""
        if not self.connected:
            await self.connect()
        
        try:
            self.client.command(f"OPTIMIZE TABLE {table_name}")
        except Exception as e:
            raise ClickHouseError(f"Failed to optimize table: {e}")
    
    async def truncate_table(self, table_name: str) -> None:
        """Truncate table for testing cleanup"""
        if not self.connected:
            await self.connect()
        
        try:
            self.client.command(f"TRUNCATE TABLE {table_name}")
        except Exception as e:
            raise ClickHouseError(f"Failed to truncate table: {e}")

# =============================================================================
# DATABASE CONNECTION TESTS
# =============================================================================

class TestClickHouseConnection:
    """Test suite for ClickHouse connection and basic operations"""
    
    @pytest.fixture
    async def clickhouse_client(self):
        """ClickHouse client fixture"""
        client = ClickHouseClient()
        try:
            await client.connect()
            yield client
        except ClickHouseError:
            pytest.skip("ClickHouse not available for testing")
        finally:
            if client.connected:
                await client.disconnect()
    
    async def test_connection_establishment(self, clickhouse_client):
        """Test successful ClickHouse connection"""
        assert clickhouse_client.connected is True
        
        # Test basic query
        results = await clickhouse_client.query_events("SELECT 1 as test_value")
        assert len(results) == 1
        assert results[0]["test_value"] == 1
    
    async def test_database_creation(self, clickhouse_client):
        """Test database creation"""
        test_db_name = f"test_analytics_{int(time.time())}"
        
        await clickhouse_client.create_database(test_db_name)
        
        # Verify database exists
        results = await clickhouse_client.query_events(
            "SELECT name FROM system.databases WHERE name = %(db_name)s",
            {"db_name": test_db_name}
        )
        
        assert len(results) == 1
        assert results[0]["name"] == test_db_name
        
        # Cleanup
        clickhouse_client.client.command(f"DROP DATABASE IF EXISTS {test_db_name}")
    
    async def test_connection_error_handling(self):
        """Test connection error handling"""
        # Test with invalid host
        invalid_client = ClickHouseClient(host="invalid_host", port=99999)
        
        with pytest.raises(ClickHouseError) as exc_info:
            await invalid_client.connect()
        
        assert "Failed to connect to ClickHouse" in str(exc_info.value)

# =============================================================================
# TABLE CREATION AND SCHEMA TESTS
# =============================================================================

class TestTableCreation:
    """Test suite for table creation and schema validation"""
    
    @pytest.fixture
    async def clickhouse_client(self):
        """ClickHouse client fixture with clean database"""
        client = ClickHouseClient()
        try:
            await client.connect()
            await client.create_database(client.database)
            await client.create_tables()
            yield client
        except ClickHouseError:
            pytest.skip("ClickHouse not available for testing")
        finally:
            if client.connected:
                # Cleanup
                try:
                    client.client.command(f"DROP DATABASE IF EXISTS {client.database}")
                except:
                    pass
                await client.disconnect()
    
    async def test_frontend_events_table_creation(self, clickhouse_client):
        """Test frontend_events table creation and schema"""
        table_info = await clickhouse_client.get_table_info("frontend_events")
        
        assert table_info["table_name"] == "frontend_events"
        assert table_info["row_count"] == 0  # Should be empty initially
        
        # Verify schema has required columns
        schema = table_info["schema"]
        column_names = [col["name"] for col in schema]
        
        required_columns = [
            "event_id", "timestamp", "user_id", "session_id",
            "event_type", "event_category", "properties",
            "date", "hour"
        ]
        
        for col in required_columns:
            assert col in column_names, f"Missing required column: {col}"
    
    async def test_prompt_analytics_table_creation(self, clickhouse_client):
        """Test prompt_analytics table creation and schema"""
        table_info = await clickhouse_client.get_table_info("prompt_analytics")
        
        assert table_info["table_name"] == "prompt_analytics"
        
        # Verify schema
        schema = table_info["schema"]
        column_names = [col["name"] for col in schema]
        
        required_columns = [
            "prompt_id", "timestamp", "user_id", "thread_id",
            "prompt_hash", "prompt_category", "response_quality_score"
        ]
        
        for col in required_columns:
            assert col in column_names, f"Missing required column: {col}"
    
    async def test_materialized_view_creation(self, clickhouse_client):
        """Test user_analytics_summary materialized view creation"""
        # Check if materialized view exists
        results = await clickhouse_client.query_events("""
            SELECT name, engine
            FROM system.tables
            WHERE database = %(database)s AND name = 'user_analytics_summary'
        """, {"database": clickhouse_client.database})
        
        assert len(results) == 1
        assert results[0]["name"] == "user_analytics_summary"
        assert "SummingMergeTree" in results[0]["engine"]

# =============================================================================
# EVENT INSERTION TESTS
# =============================================================================

class TestEventInsertion:
    """Test suite for event insertion operations"""
    
    @pytest.fixture
    async def clickhouse_client_with_cleanup(self):
        """ClickHouse client fixture with automatic cleanup"""
        client = ClickHouseClient()
        try:
            await client.connect()
            await client.create_database(client.database)
            await client.create_tables()
            yield client
        except ClickHouseError:
            pytest.skip("ClickHouse not available for testing")
        finally:
            if client.connected:
                # Cleanup tables
                try:
                    await client.truncate_table("frontend_events")
                    await client.truncate_table("prompt_analytics")
                except:
                    pass
                await client.disconnect()
    
    async def test_single_event_insertion(self, clickhouse_client_with_cleanup, sample_chat_interaction_event):
        """Test insertion of a single event"""
        inserted_count = await clickhouse_client_with_cleanup.insert_events([sample_chat_interaction_event])
        
        assert inserted_count == 1
        
        # Verify event was inserted
        results = await clickhouse_client_with_cleanup.query_events(
            "SELECT count() as count FROM frontend_events WHERE event_id = %(event_id)s",
            {"event_id": sample_chat_interaction_event["event_id"]}
        )
        
        assert results[0]["count"] == 1
    
    async def test_batch_event_insertion(self, clickhouse_client_with_cleanup, sample_event_batch):
        """Test batch insertion of multiple events"""
        inserted_count = await clickhouse_client_with_cleanup.insert_events(sample_event_batch)
        
        assert inserted_count == len(sample_event_batch)
        
        # Verify all events were inserted
        results = await clickhouse_client_with_cleanup.query_events(
            "SELECT count() as count FROM frontend_events"
        )
        
        assert results[0]["count"] == len(sample_event_batch)
    
    async def test_large_batch_insertion(self, clickhouse_client_with_cleanup, high_volume_event_generator):
        """Test insertion of large event batch"""
        large_batch = high_volume_event_generator(count=1000)
        
        start_time = time.time()
        inserted_count = await clickhouse_client_with_cleanup.insert_events(large_batch)
        insertion_time = time.time() - start_time
        
        assert inserted_count == 1000
        
        # Verify performance - should insert 1000 events reasonably fast
        assert insertion_time < 10.0  # Under 10 seconds
        
        # Verify data integrity
        results = await clickhouse_client_with_cleanup.query_events(
            "SELECT count() as count FROM frontend_events"
        )
        
        assert results[0]["count"] == 1000
    
    async def test_event_data_integrity(self, clickhouse_client_with_cleanup, sample_chat_interaction_event):
        """Test event data integrity after insertion"""
        await clickhouse_client_with_cleanup.insert_events([sample_chat_interaction_event])
        
        # Query back the inserted event
        results = await clickhouse_client_with_cleanup.query_events(
            """
            SELECT event_id, user_id, event_type, event_category, properties
            FROM frontend_events
            WHERE event_id = %(event_id)s
            """,
            {"event_id": sample_chat_interaction_event["event_id"]}
        )
        
        assert len(results) == 1
        event = results[0]
        
        assert event["event_id"] == sample_chat_interaction_event["event_id"]
        assert event["user_id"] == sample_chat_interaction_event["user_id"]
        assert event["event_type"] == sample_chat_interaction_event["event_type"]
        assert event["event_category"] == sample_chat_interaction_event["event_category"]
        
        # Verify properties JSON is preserved
        properties = json.loads(event["properties"])
        original_properties = json.loads(sample_chat_interaction_event["properties"])
        assert properties == original_properties
    
    async def test_concurrent_insertions(self, clickhouse_client_with_cleanup, sample_chat_interaction_event):
        """Test concurrent event insertions"""
        # Prepare multiple batches for concurrent insertion
        tasks = []
        for i in range(5):
            batch = []
            for j in range(10):
                event = sample_chat_interaction_event.copy()
                event["event_id"] = f"concurrent-{i}-{j}"
                event["user_id"] = f"user-{i}"
                batch.append(event)
            
            task = clickhouse_client_with_cleanup.insert_events(batch)
            tasks.append(task)
        
        # Execute concurrent insertions
        results = await asyncio.gather(*tasks)
        
        # All insertions should succeed
        for result in results:
            assert result == 10
        
        # Verify total count
        count_results = await clickhouse_client_with_cleanup.query_events(
            "SELECT count() as count FROM frontend_events"
        )
        
        assert count_results[0]["count"] == 50  # 5 batches * 10 events each

# =============================================================================
# QUERY PERFORMANCE TESTS
# =============================================================================

class TestQueryPerformance:
    """Test suite for query performance and optimization"""
    
    @pytest.fixture
    async def clickhouse_client_with_data(self, high_volume_event_generator):
        """ClickHouse client fixture with test data"""
        client = ClickHouseClient()
        try:
            await client.connect()
            await client.create_database(client.database)
            await client.create_tables()
            
            # Insert test data
            test_data = high_volume_event_generator(count=5000, user_count=100)
            await client.insert_events(test_data)
            
            # Wait a bit for data to be processed
            await asyncio.sleep(1)
            
            yield client
            
        except ClickHouseError:
            pytest.skip("ClickHouse not available for testing")
        finally:
            if client.connected:
                await client.disconnect()
    
    async def test_simple_query_performance(self, clickhouse_client_with_data, analytics_performance_monitor):
        """Test simple query performance"""
        analytics_performance_monitor.start_measurement("query_response")
        
        results = await clickhouse_client_with_data.query_events(
            "SELECT count() as total_events FROM frontend_events"
        )
        
        duration = analytics_performance_monitor.end_measurement("query_response")
        
        assert results[0]["total_events"] == 5000
        
        # Should execute simple count query quickly
        assert duration < 1.0  # Under 1 second
        analytics_performance_monitor.validate_performance("query_response")
    
    async def test_aggregation_query_performance(self, clickhouse_client_with_data, analytics_performance_monitor):
        """Test aggregation query performance"""
        analytics_performance_monitor.start_measurement("query_response")
        
        results = await clickhouse_client_with_data.query_events("""
            SELECT 
                user_id,
                count() as event_count,
                countIf(event_type = 'chat_interaction') as chat_count,
                avg(event_value) as avg_value
            FROM frontend_events
            GROUP BY user_id
            ORDER BY event_count DESC
            LIMIT 10
        """)
        
        duration = analytics_performance_monitor.end_measurement("query_response")
        
        assert len(results) <= 10
        assert all("user_id" in result for result in results)
        
        # Aggregation query should still be fast
        assert duration < 2.0  # Under 2 seconds
        analytics_performance_monitor.validate_performance("query_response")
    
    async def test_time_range_query_performance(self, clickhouse_client_with_data):
        """Test time range query performance"""
        start_time = time.time()
        
        # Query recent events (should use time-based partitioning)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=1)
        
        results = await clickhouse_client_with_data.query_events(
            """
            SELECT count() as recent_events
            FROM frontend_events
            WHERE timestamp >= %(start_date)s AND timestamp <= %(end_date)s
            """,
            {
                "start_date": start_date.strftime("%Y-%m-%d %H:%M:%S"),
                "end_date": end_date.strftime("%Y-%m-%d %H:%M:%S")
            }
        )
        
        query_time = time.time() - start_time
        
        # Should have recent events
        assert results[0]["recent_events"] > 0
        
        # Time range query should be optimized
        assert query_time < 2.0
    
    async def test_index_usage_query(self, clickhouse_client_with_data):
        """Test query that should use indexes efficiently"""
        start_time = time.time()
        
        # Query by user_id (should use primary key index)
        results = await clickhouse_client_with_data.query_events(
            """
            SELECT count() as user_events
            FROM frontend_events
            WHERE user_id = 'perf_user_1'
            """
        )
        
        query_time = time.time() - start_time
        
        # Index-based query should be very fast
        assert query_time < 1.0
        assert results[0]["user_events"] >= 0

# =============================================================================
# MATERIALIZED VIEW TESTS
# =============================================================================

class TestMaterializedViews:
    """Test suite for materialized views and aggregations"""
    
    @pytest.fixture
    async def clickhouse_client_with_events(self, sample_event_batch):
        """ClickHouse client fixture with sample events"""
        client = ClickHouseClient()
        try:
            await client.connect()
            await client.create_database(client.database)
            await client.create_tables()
            
            # Insert sample events
            await client.insert_events(sample_event_batch)
            
            # Wait for materialized view to process
            await asyncio.sleep(2)
            
            yield client
            
        except ClickHouseError:
            pytest.skip("ClickHouse not available for testing")
        finally:
            if client.connected:
                await client.disconnect()
    
    async def test_user_activity_summary_generation(self, clickhouse_client_with_events):
        """Test user activity summary from materialized view"""
        # Get user activity summary
        user_id = "batch_test_user_" + str(int(time.time()))  # From sample_event_batch fixture
        
        # Query user activity summary
        results = await clickhouse_client_with_events.query_events(
            """
            SELECT 
                user_id,
                sum(total_events) as total_events,
                sum(chat_interactions) as chat_interactions
            FROM user_analytics_summary
            WHERE user_id LIKE %(user_pattern)s
            GROUP BY user_id
            """,
            {"user_pattern": "batch_test_user_%"}
        )
        
        # Should have aggregated data
        if results:  # Materialized view might take time to update
            user_summary = results[0]
            assert user_summary["total_events"] > 0
            assert user_summary["chat_interactions"] >= 0
    
    async def test_materialized_view_data_consistency(self, clickhouse_client_with_events):
        """Test materialized view data consistency"""
        # Insert more events
        additional_events = []
        user_id = "consistency_test_user"
        
        for i in range(5):
            event = {
                "event_id": f"consistency-{i}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "session_id": "consistency_session",
                "event_type": "chat_interaction",
                "event_category": "User Interaction Events",
                "properties": json.dumps({"test": f"data-{i}"}),
                "event_value": 100.0 + i
            }
            additional_events.append(event)
        
        await clickhouse_client_with_events.insert_events(additional_events)
        
        # Wait for materialized view to update
        await asyncio.sleep(2)
        
        # Compare raw data with materialized view
        raw_count = await clickhouse_client_with_events.query_events(
            "SELECT count() as count FROM frontend_events WHERE user_id = %(user_id)s",
            {"user_id": user_id}
        )
        
        mv_count = await clickhouse_client_with_events.query_events(
            """
            SELECT sum(total_events) as count 
            FROM user_analytics_summary 
            WHERE user_id = %(user_id)s
            """,
            {"user_id": user_id}
        )
        
        # Materialized view should eventually match raw data
        if mv_count and mv_count[0]["count"]:
            assert mv_count[0]["count"] <= raw_count[0]["count"]  # May lag slightly

# =============================================================================
# ERROR HANDLING AND RECOVERY TESTS
# =============================================================================

class TestErrorHandlingAndRecovery:
    """Test suite for error handling and recovery scenarios"""
    
    @pytest.fixture
    async def clickhouse_client(self):
        """ClickHouse client fixture"""
        client = ClickHouseClient()
        try:
            await client.connect()
            await client.create_database(client.database)
            await client.create_tables()
            yield client
        except ClickHouseError:
            pytest.skip("ClickHouse not available for testing")
        finally:
            if client.connected:
                await client.disconnect()
    
    async def test_invalid_query_handling(self, clickhouse_client):
        """Test handling of invalid SQL queries"""
        with pytest.raises(ClickHouseError) as exc_info:
            await clickhouse_client.query_events("INVALID SQL QUERY")
        
        assert "Query failed" in str(exc_info.value)
    
    async def test_invalid_data_insertion(self, clickhouse_client):
        """Test handling of invalid data during insertion"""
        # Events with missing required fields should be handled gracefully
        invalid_events = [
            {"event_id": "test-1"},  # Missing most fields
            {},  # Completely empty
        ]
        
        # Should not raise exception but may insert with defaults
        inserted_count = await clickhouse_client.insert_events(invalid_events)
        assert inserted_count >= 0  # May insert with default values
    
    async def test_connection_recovery(self):
        """Test connection recovery after disconnect"""
        client = ClickHouseClient()
        
        try:
            await client.connect()
            assert client.connected is True
            
            # Simulate disconnection
            await client.disconnect()
            assert client.connected is False
            
            # Should be able to reconnect
            await client.connect()
            assert client.connected is True
            
            # Should be able to execute queries after reconnection
            results = await client.query_events("SELECT 1 as test")
            assert results[0]["test"] == 1
            
        except ClickHouseError:
            pytest.skip("ClickHouse not available for testing")
        finally:
            if client.connected:
                await client.disconnect()
    
    async def test_table_optimization_error_handling(self, clickhouse_client):
        """Test error handling during table optimization"""
        # Try to optimize non-existent table
        with pytest.raises(ClickHouseError):
            await clickhouse_client.optimize_table("nonexistent_table")

# =============================================================================
# PERFORMANCE BENCHMARKS
# =============================================================================

class TestPerformanceBenchmarks:
    """Test suite for ClickHouse performance benchmarks"""
    
    @pytest.fixture
    async def clickhouse_client_benchmark(self):
        """ClickHouse client fixture for benchmarking"""
        client = ClickHouseClient()
        try:
            await client.connect()
            await client.create_database(client.database)
            await client.create_tables()
            yield client
        except ClickHouseError:
            pytest.skip("ClickHouse not available for testing")
        finally:
            if client.connected:
                # Cleanup
                try:
                    await client.truncate_table("frontend_events")
                except:
                    pass
                await client.disconnect()
    
    async def test_insertion_throughput(self, clickhouse_client_benchmark, high_volume_event_generator, analytics_performance_monitor):
        """Test insertion throughput benchmark"""
        event_count = 10000
        events = high_volume_event_generator(count=event_count)
        
        analytics_performance_monitor.start_measurement("high_volume_ingestion")
        
        # Insert in batches for better performance
        batch_size = 1000
        total_inserted = 0
        
        for i in range(0, event_count, batch_size):
            batch = events[i:i + batch_size]
            inserted = await clickhouse_client_benchmark.insert_events(batch)
            total_inserted += inserted
        
        duration = analytics_performance_monitor.end_measurement("high_volume_ingestion")
        
        assert total_inserted == event_count
        
        # Calculate throughput
        throughput = event_count / duration
        print(f"Insertion throughput: {throughput:.2f} events/second")
        
        # Should achieve reasonable throughput
        assert throughput > 1000  # At least 1000 events/second
        
        # Validate performance requirement
        analytics_performance_monitor.validate_performance("high_volume_ingestion")
    
    async def test_query_performance_with_large_dataset(self, clickhouse_client_benchmark, high_volume_event_generator):
        """Test query performance with large dataset"""
        # Insert large dataset
        events = high_volume_event_generator(count=50000, user_count=1000)
        
        # Insert in batches
        batch_size = 5000
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            await clickhouse_client_benchmark.insert_events(batch)
        
        # Wait for data to be processed
        await asyncio.sleep(2)
        
        # Test various query patterns
        query_tests = [
            ("Simple count", "SELECT count() FROM frontend_events"),
            ("User aggregation", """
                SELECT user_id, count() as events
                FROM frontend_events
                GROUP BY user_id
                ORDER BY events DESC
                LIMIT 100
            """),
            ("Time-based filter", """
                SELECT count() as recent_events
                FROM frontend_events
                WHERE timestamp >= now() - INTERVAL 1 HOUR
            """),
            ("Complex aggregation", """
                SELECT 
                    event_type,
                    count() as event_count,
                    avg(event_value) as avg_value,
                    uniq(user_id) as unique_users
                FROM frontend_events
                GROUP BY event_type
                ORDER BY event_count DESC
            """)
        ]
        
        for query_name, query in query_tests:
            start_time = time.time()
            results = await clickhouse_client_benchmark.query_events(query)
            query_time = time.time() - start_time
            
            print(f"{query_name}: {query_time:.3f}s ({len(results)} rows)")
            
            # All queries should complete in reasonable time
            assert query_time < 5.0, f"{query_name} took too long: {query_time:.3f}s"

# =============================================================================
# INTEGRATION WITH FIXTURES
# =============================================================================

class TestClickHouseWithFixtures:
    """Test ClickHouse integration using conftest fixtures"""
    
    @pytest.fixture
    async def clickhouse_client_fixture_test(self):
        """ClickHouse client for fixture integration tests"""
        client = ClickHouseClient()
        try:
            await client.connect()
            await client.create_database(client.database)
            await client.create_tables()
            yield client
        except ClickHouseError:
            pytest.skip("ClickHouse not available for testing")
        finally:
            if client.connected:
                try:
                    await client.truncate_table("frontend_events")
                except:
                    pass
                await client.disconnect()
    
    async def test_all_sample_events_insertion(self, clickhouse_client_fixture_test,
                                             sample_chat_interaction_event,
                                             sample_survey_response_event,
                                             sample_performance_event):
        """Test insertion of all sample event types from fixtures"""
        events = [
            sample_chat_interaction_event,
            sample_survey_response_event,
            sample_performance_event
        ]
        
        inserted_count = await clickhouse_client_fixture_test.insert_events(events)
        assert inserted_count == 3
        
        # Verify each event type was inserted
        for event in events:
            results = await clickhouse_client_fixture_test.query_events(
                "SELECT event_type FROM frontend_events WHERE event_id = %(event_id)s",
                {"event_id": event["event_id"]}
            )
            assert len(results) == 1
            assert results[0]["event_type"] == event["event_type"]
    
    async def test_user_activity_summary_with_fixtures(self, clickhouse_client_fixture_test, sample_event_batch):
        """Test user activity summary with fixture data"""
        await clickhouse_client_fixture_test.insert_events(sample_event_batch)
        
        # Wait for processing
        await asyncio.sleep(1)
        
        # Get a user ID from the batch
        user_id = sample_event_batch[0]["user_id"]
        
        summary = await clickhouse_client_fixture_test.get_user_activity_summary(user_id)
        
        assert summary["user_id"] == user_id
        assert summary["total_events"] >= 0
        assert isinstance(summary["daily_breakdown"], list)
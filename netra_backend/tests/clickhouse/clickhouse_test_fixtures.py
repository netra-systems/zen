"""
Common fixtures and helpers for ClickHouse tests
Shared utilities for real ClickHouse API integration tests
"""

import json
import random
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List

import pytest

from netra_backend.app.config import get_config
from netra_backend.app.database import get_clickhouse_client
from netra_backend.app.db.clickhouse_base import ClickHouseDatabase
from netra_backend.app.db.clickhouse_init import (
    create_workload_events_table_if_missing,
    initialize_clickhouse_tables,
    verify_workload_events_table,
)
from netra_backend.app.db.clickhouse_query_fixer import ClickHouseQueryInterceptor
from netra_backend.app.logging_config import central_logger as logger

def get_clickhouse_config():
    """Get ClickHouse configuration based on environment"""
    return get_config().clickhouse_https

def create_clickhouse_client(config):
    """Create ClickHouse client with given configuration"""
    # Determine if we should use secure connection based on environment
    from shared.isolated_environment import get_env
    env = get_env()
    environment = env.get("ENVIRONMENT", "development").lower()
    
    # Use HTTP for test environment (port 8126), HTTPS for production/staging
    secure = environment not in ["testing", "development"]
    
    return ClickHouseDatabase(
        host=config.host, port=config.port, user=config.user,
        password=config.password, database=config.database, secure=secure
    )

async def check_system_metrics_permission(client):
    """Check if user has permission to access system.metrics"""
    try:
        await client.execute_query("SELECT metric FROM system.metrics LIMIT 1")
        return True
    except Exception as e:
        if "Not enough privileges" in str(e) or "ACCESS_DENIED" in str(e):
            return False
        raise

async def check_table_insert_permission(client, table_name):
    """Check if user has INSERT permission on table"""
    try:
        test_query = f"INSERT INTO {table_name} VALUES" 
        # This will fail but with different error if no INSERT permission
        await client.execute_query(test_query)
    except Exception as e:
        error_msg = str(e).lower()
        if "not enough privileges" in error_msg or "access_denied" in error_msg:
            return False
        # Other errors (like syntax) mean we likely have permission
        return True
    return True

async def check_table_create_permission(client):
    """Check if user has CREATE TABLE permission"""
    # CRITICAL FIX: Handle NoOp client case for testing without Docker
    from netra_backend.app.db.clickhouse import NoOpClickHouseClient
    if isinstance(client, NoOpClickHouseClient):
        logger.info("[ClickHouse Test] NoOp client detected - simulating CREATE TABLE permission check")
        return True  # Always return True for NoOp client
    
    test_table = f"temp_permission_test_{uuid.uuid4().hex[:8]}"
    try:
        query = f"CREATE TABLE {test_table} (id Int32) ENGINE = Memory"
        await client.execute_query(query)
        await client.execute_query(f"DROP TABLE {test_table}")
        return True
    except Exception as e:
        if "not enough privileges" in str(e).lower():
            return False
        return True

async def ensure_workload_table():
    """Create workload table if missing and verify access"""
    success = await create_workload_events_table_if_missing()
    if not success:
        pytest.skip("Cannot create workload_events table")
    exists = await verify_workload_events_table()
    if not exists:
        pytest.skip("workload_events table not accessible")

def generate_test_workload_events(count=10):
    """Generate test workload events for insertion"""
    test_events = []
    base_time = datetime.now(UTC)
    for i in range(count):
        event = {
            'event_id': str(uuid.uuid4()),
            'timestamp': base_time - timedelta(minutes=i),
            'user_id': i % 100 + 1,  # UInt32 as per schema
            'workload_id': random.choice(['simple_chat', 'rag_pipeline', 'tool_use']),
            'event_type': random.choice(['request', 'response', 'error']),
            'event_category': random.choice(['llm_call', 'tool_use', 'user_action']),
            'dimensions': f"{{'test_id': '{i}', 'batch': 'test_run'}}",
            'metadata': json.dumps({'test_id': i, 'test_run': True})
        }
        test_events.append(event)
    return test_events

def build_workload_insert_query():
    """Build workload events insert query"""
    return """INSERT INTO workload_events (event_id, timestamp, user_id,
    workload_id, event_type, event_category, dimensions, metadata) 
    VALUES (%(event_id)s, %(timestamp)s, %(user_id)s, %(workload_id)s, 
    %(event_type)s, %(event_category)s, %(dimensions)s, %(metadata)s)"""

async def insert_with_permission_check(client, query, params):
    """Execute insert with permission error handling"""
    try:
        await client.execute_query(query, params)
    except Exception as e:
        if "Not enough privileges" in str(e):
            pytest.skip(f"INSERT permission denied: {e}")
        raise

def build_corpus_create_query(table_name):
    """Build CREATE TABLE query for corpus table"""
    return f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        record_id UUID DEFAULT generateUUIDv4(), workload_id String,
        prompt String, response String, metadata String,
        domain String DEFAULT 'general', created_at DateTime64(3) DEFAULT now(),
        version UInt32 DEFAULT 1, embedding Array(Float32) DEFAULT [],
        tags Array(String) DEFAULT []
    ) ENGINE = MergeTree() PARTITION BY toYYYYMM(created_at)
    ORDER BY (workload_id, created_at, record_id)"""

async def cleanup_test_table(client, table_name):
    """Cleanup test table safely"""
    # CRITICAL FIX: Handle NoOp client case for testing without Docker
    from netra_backend.app.db.clickhouse import NoOpClickHouseClient
    if isinstance(client, NoOpClickHouseClient):
        logger.info(f"[ClickHouse Test] NoOp client - simulating cleanup of table: {table_name}")
        return  # No actual cleanup needed for NoOp client
    
    try:
        await client.execute_query(f"DROP TABLE IF EXISTS {table_name}")
        logger.info(f"Cleaned up test table: {table_name}")
    except Exception as e:
        logger.warning(f"Failed to cleanup table {table_name}: {e}")

# real_clickhouse_client fixture is now provided by conftest.py

@pytest.fixture
def setup_workload_table(event_loop):
    """Ensure workload_events table exists"""
    async def _setup_table():
        # Initialize ClickHouse tables including workload_events
        await initialize_clickhouse_tables()
        
        # Verify the table exists
        exists = await verify_workload_events_table()
        if not exists:
            pytest.skip("workload_events table could not be created or verified")
    
    event_loop.run_until_complete(_setup_table())
    yield
    # Cleanup test data (optional) - kept for analysis

@pytest.fixture
def batch_workload_events():
    """Generate batch of test workload events"""
    batch_size = 1000
    events = []
    base_time = datetime.now(UTC)
    
    for i in range(batch_size):
        event = [
            str(uuid.uuid4()),  # event_id
            base_time - timedelta(seconds=i),  # timestamp
            i % 100 + 1,  # user_id (UInt32)
            random.choice(['simple_chat', 'rag_pipeline', 'tool_use']),  # workload_id
            random.choice(['request', 'response', 'error']),  # event_type
            random.choice(['llm_call', 'tool_use', 'user_action']),  # event_category
            {'test_id': str(i), 'batch': 'perf_test'},  # dimensions
            json.dumps({'batch_test': True, 'index': i})  # metadata
        ]
        events.append(event)
    return events
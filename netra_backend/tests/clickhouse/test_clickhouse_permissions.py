"""
ClickHouse Permission Helpers
Centralized permission checking utilities for ClickHouse tests
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import uuid

import pytest

from netra_backend.app.config import get_config

# Add project root to path
from netra_backend.app.db.clickhouse import get_clickhouse_client
from netra_backend.app.db.clickhouse_base import ClickHouseDatabase

# Add project root to path


def _get_clickhouse_config():
    """Get ClickHouse configuration based on environment"""
    return get_config().clickhouse_https


def _create_clickhouse_client(config):
    """Create ClickHouse client with given configuration"""
    return ClickHouseDatabase(
        host=config.host, port=config.port, user=config.user,
        password=config.password, database=config.database, secure=True
    )


async def _check_system_metrics_permission(client):
    """Check if user has permission to access system.metrics"""
    try:
        await client.execute_query("SELECT metric FROM system.metrics LIMIT 1")
        return True
    except Exception as e:
        if "Not enough privileges" in str(e) or "ACCESS_DENIED" in str(e):
            return False
        raise


async def _check_table_insert_permission(client, table_name):
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


async def _check_table_create_permission(client):
    """Check if user has CREATE TABLE permission"""
    test_table = f"temp_permission_test_{uuid.uuid4().hex[:8]}"
    try:
        await client.execute_query(f"CREATE TABLE {test_table} (id Int32) ENGINE = Memory")
        await client.execute_query(f"DROP TABLE {test_table}")
        return True
    except Exception as e:
        if "not enough privileges" in str(e).lower():
            return False
        return True


def skip_if_no_system_permissions(client):
    """Decorator to skip test if no system permissions"""
    async def decorator(test_func):
        has_permission = await _check_system_metrics_permission(client)
        if not has_permission:
            pytest.skip("development_user lacks privileges for system.metrics")
        return await test_func()
    return decorator


def skip_if_no_insert_permissions(client, table_name):
    """Decorator to skip test if no insert permissions"""
    async def decorator(test_func):
        has_permission = await _check_table_insert_permission(client, table_name)
        if not has_permission:
            pytest.skip(f"development_user lacks INSERT privileges for {table_name}")
        return await test_func()
    return decorator


@pytest.fixture
def real_clickhouse_client():
    """Create a real ClickHouse client using production configuration"""
    config = _get_clickhouse_config()
    client = _create_clickhouse_client(config)
    yield client
    # Note: Disconnect handled by the test itself or auto-cleanup
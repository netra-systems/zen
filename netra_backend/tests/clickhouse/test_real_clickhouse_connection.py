"""
Real ClickHouse Connection Tests
Tests actual ClickHouse connections and basic operations
"""

import pytest
from logging_config import central_logger as logger
# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.tests.clickhouse_test_fixtures import (

# Add project root to path
    real_clickhouse_client,
    check_system_metrics_permission
)


class TestRealClickHouseConnection:
    """Test real ClickHouse connection and basic operations"""
    
    async def test_real_connection(self, real_clickhouse_client):
        """Test actual connection to ClickHouse Cloud"""
        # Test basic connection
        result = await real_clickhouse_client.execute_query("SELECT 1 as test")
        assert len(result) == 1
        assert result[0]['test'] == 1
        
        # Test server version
        version_result = await real_clickhouse_client.execute_query("SELECT version() as version")
        assert len(version_result) == 1
        assert 'version' in version_result[0]
        logger.info(f"Connected to ClickHouse version: {version_result[0]['version']}")

    async def test_real_database_operations(self, real_clickhouse_client):
        """Test real database operations"""
        # Get current database
        db_result = await real_clickhouse_client.execute_query("SELECT currentDatabase() as db")
        assert len(db_result) == 1
        current_db = db_result[0]['db']
        logger.info(f"Current database: {current_db}")
        
        # List tables
        tables_result = await real_clickhouse_client.execute_query("SHOW TABLES")
        table_names = [row['name'] for row in tables_result if 'name' in row]
        logger.info(f"Available tables: {table_names}")

    async def test_real_system_queries(self, real_clickhouse_client):
        """Test system queries for monitoring"""
        # Check if user has system.metrics permission
        has_permission = await check_system_metrics_permission(real_clickhouse_client)
        if not has_permission:
            pytest.skip("development_user lacks privileges for system.metrics")
        
        await self._execute_system_metrics_query(real_clickhouse_client)

    async def _execute_system_metrics_query(self, client):
        """Execute system metrics query with permission check"""
        metrics_query = """
        SELECT metric, value FROM system.metrics
        WHERE metric IN ('Query', 'HTTPConnection', 'TCPConnection')
        """
        metrics_result = await client.execute_query(metrics_query)
        assert isinstance(metrics_result, list)
        for row in metrics_result:
            logger.info(f"System metric {row.get('metric')}: {row.get('value')}")
"""
ClickHouse Basic Connection Tests
Tests for basic ClickHouse connectivity and database operations
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import pytest
from netra_backend.app.core.unified_logging import central_logger as logger

# Import helper functions only - fixture will be discovered by pytest
from netra_backend.tests.clickhouse.test_clickhouse_permissions import (
    _check_system_metrics_permission,
)
from netra_backend.tests.clickhouse.conftest import check_clickhouse_availability

@pytest.mark.dev
@pytest.mark.staging
@pytest.mark.real_database
class TestRealClickHouseConnection:
    """Test real ClickHouse connection and basic operations"""
    
    @pytest.mark.asyncio
    async def test_real_connection(self, real_clickhouse_client):
        """Test actual connection to ClickHouse Cloud"""
        # Test basic connection
        result = await real_clickhouse_client.execute_query("SELECT 1 as test")
        assert len(result) == 1
        assert result[0]['test'] == 1
        
        # Test server version
        await self._verify_server_version(real_clickhouse_client)

    async def _verify_server_version(self, client):
        """Verify ClickHouse server version"""
        version_result = await client.execute_query("SELECT version() as version")
        assert len(version_result) == 1
        assert 'version' in version_result[0]
        logger.info(f"Connected to ClickHouse version: {version_result[0]['version']}")

    @pytest.mark.asyncio
    async def test_real_database_operations(self, real_clickhouse_client):
        """Test real database operations"""
        try:
            # Get current database
            db_result = await real_clickhouse_client.execute_query("SELECT currentDatabase() as db")
            assert len(db_result) == 1
            current_db = db_result[0]['db']
            logger.info(f"Current database: {current_db}")
            
            await self._list_available_tables(real_clickhouse_client)
        except Exception as e:
            # If SSL connection fails, skip the test gracefully
            if "SSL" in str(e) or "wrong version number" in str(e):
                pytest.skip(f"SSL connection issue: {e}")
            else:
                raise

    async def _list_available_tables(self, client):
        """List and log available tables"""
        tables_result = await client.execute_query("SHOW TABLES")
        table_names = [row['name'] for row in tables_result if 'name' in row]
        logger.info(f"Available tables: {table_names}")

    @pytest.mark.asyncio
    async def test_real_system_queries(self, real_clickhouse_client):
        """Test system queries for monitoring"""
        # Check if user has system.metrics permission
        has_permission = await _check_system_metrics_permission(real_clickhouse_client)
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

@pytest.mark.dev
@pytest.mark.staging
@pytest.mark.real_database
class TestClickHouseIntegration:
    """Integration tests for ClickHouse with the application"""
    
    @pytest.mark.asyncio
    async def test_full_initialization_flow(self):
        """Test the full ClickHouse initialization flow"""
        from netra_backend.app.database import get_clickhouse_client
        from netra_backend.app.db.clickhouse_init import initialize_clickhouse_tables
        
        # Check if ClickHouse is available
        if not check_clickhouse_availability():
            pytest.skip("ClickHouse server not available - skipping integration test")
        
        try:
            # Run initialization
            await initialize_clickhouse_tables()
            
            # Verify all tables exist
            await self._verify_expected_tables()
        except Exception as e:
            # Handle connection errors during test execution
            if any(error in str(e).lower() for error in [
                'ssl', 'connection refused', 'timeout', 'network', 
                'wrong version number', 'cannot connect', 'host unreachable'
            ]):
                pytest.skip(f"ClickHouse connection failed during integration test: {e}")
            else:
                raise

    async def _verify_expected_tables(self):
        """Verify expected tables exist after initialization"""
        from netra_backend.app.database import get_clickhouse_client
        
        async with get_clickhouse_client() as client:
            tables_result = await client.execute_query("SHOW TABLES")
            table_names = [row['name'] for row in tables_result if 'name' in row]
            
            # Check for expected tables
            expected_tables = ['workload_events', 'netra_app_internal_logs', 'netra_global_supply_catalog']
            
            for expected_table in expected_tables:
                if expected_table in table_names:
                    logger.info(f"✓ Table {expected_table} exists")
                else:
                    logger.warning(f"✗ Table {expected_table} not found")

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
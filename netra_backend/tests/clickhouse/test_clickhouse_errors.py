"""
ClickHouse Error Handling Tests
Tests for error handling and recovery mechanisms
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest

# Add project root to path

from netra_backend.app.db.clickhouse import get_clickhouse_client
from netra_backend.app.db.clickhouse_base import ClickHouseDatabase
from config import settings
from logging_config import central_logger as logger

# Add project root to path


class TestClickHouseErrorHandling:
    """Test error handling and recovery"""
    
    async def test_invalid_query_handling(self):
        """Test handling of invalid queries"""
        async with get_clickhouse_client() as client:
            # Test syntax error
            with pytest.raises(Exception) as exc_info:
                await client.execute_query("SELECT * FROM non_existent_table_xyz123")
            
            error_msg = str(exc_info.value)
            logger.info(f"Expected error for non-existent table: {error_msg}")

    async def test_connection_recovery(self):
        """Test connection recovery after disconnect"""
        config = self._get_test_config()
        
        client = self._create_test_client(config)
        
        # First query should work
        await self._test_initial_connection(client)
        
        # Disconnect and test failure
        await self._test_disconnect_behavior(client)
        
        # Test reconnection
        await self._test_reconnection(config)

    def _get_test_config(self):
        """Get test configuration for connection tests"""
        return settings.clickhouse_https

    def _create_test_client(self, config):
        """Create test client with given configuration"""
        return ClickHouseDatabase(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database=config.database,
            secure=True
        )

    async def _test_initial_connection(self, client):
        """Test that initial connection works"""
        result = await client.execute_query("SELECT 1 as test")
        assert result[0]['test'] == 1

    async def _test_disconnect_behavior(self, client):
        """Test behavior after disconnection"""
        # Disconnect
        await client.disconnect()
        
        # Query after disconnect should fail
        with pytest.raises(ConnectionError):
            await client.execute_query("SELECT 1 as test")

    async def _test_reconnection(self, config):
        """Test successful reconnection"""
        # Reconnect
        client = self._create_test_client(config)
        
        # Should work again
        result = await client.execute_query("SELECT 1 as test")
        assert result[0]['test'] == 1
        
        await client.disconnect()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
import asyncio

"""
Real ClickHouse Error Handling Tests
Test error handling and recovery for real ClickHouse connections
"""""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import pytest
from netra_backend.app.logging_config import central_logger as logger

from netra_backend.app.config import get_config

from netra_backend.app.db.clickhouse_base import ClickHouseDatabase
from netra_backend.tests.clickhouse.clickhouse_test_fixtures import get_clickhouse_config

class TestClickHouseErrorHandling:
    """Test error handling and recovery"""

    @pytest.mark.asyncio
    async def test_invalid_query_handling(self):
        """Test handling of invalid queries"""
        config = get_clickhouse_config()
        client = ClickHouseDatabase(
        host=config.host, port=config.port, user=config.user,
        password=config.password, database=config.database, secure=True
        )

        # Test syntax error
        with pytest.raises(Exception) as exc_info:
            await client.execute_query("SELECT * FROM non_existent_table_xyz123")

            error_msg = str(exc_info.value)
            logger.info(f"Expected error for non-existent table: {error_msg}")

            await client.disconnect()

            @pytest.mark.asyncio
            async def test_connection_recovery(self):
                """Test connection recovery after disconnect"""
                config = get_clickhouse_config()

                client = ClickHouseDatabase(
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                database=config.database,
                secure=True
                )

        # First query should work
                result = await client.execute_query("SELECT 1 as test")
                assert result[0]['test'] == 1

        # Disconnect
                await client.disconnect()

        # Query after disconnect should fail
                with pytest.raises(ConnectionError):
                    await client.execute_query("SELECT 1 as test")

        # Reconnect
                    client = ClickHouseDatabase(
                    host=config.host,
                    port=config.port,
                    user=config.user,
                    password=config.password,
                    database=config.database,
                    secure=True
                    )

        # Should work again
                    result = await client.execute_query("SELECT 1 as test")
                    assert result[0]['test'] == 1

                    await client.disconnect()

                    @pytest.mark.asyncio
                    async def test_permission_error_handling(self):
                        """Test handling of permission errors gracefully"""
                        config = get_clickhouse_config()
                        client = ClickHouseDatabase(
                        host=config.host, port=config.port, user=config.user,
                        password=config.password, database=config.database, secure=True
                        )

                        try:
            # Try to access system tables that might require elevated permissions
                            await client.execute_query("SELECT * FROM system.users LIMIT 1")
                        except Exception as e:
                            error_msg = str(e).lower()
                            if "not enough privileges" in error_msg or "access_denied" in error_msg:
                                logger.info("Permission error handled correctly")
                            else:
                # Re-raise if it's not a permission error'
                                raise
                        finally:
                            await client.disconnect()

                            @pytest.mark.asyncio
                            async def test_malformed_query_error_handling(self):
                                """Test handling of malformed queries"""
                                config = get_clickhouse_config()
                                client = ClickHouseDatabase(
                                host=config.host, port=config.port, user=config.user,
                                password=config.password, database=config.database, secure=True
                                )

                                malformed_queries = [
                                "SELECT FROM WHERE",  # Missing table and column
                                "INSERT INTO VALUES",  # Missing table name
                                "UPDATE SET WHERE",   # ClickHouse doesn't support UPDATE'
                                "DELETE FROM WHERE",  # Missing table name
                                ]

                                for query in malformed_queries:
                                    with pytest.raises(Exception) as exc_info:
                                        await client.execute_query(query)

                                        error_msg = str(exc_info.value)
                                        logger.info(f"Malformed query '{query}' properly raised error: {error_msg}")

                                        await client.disconnect()
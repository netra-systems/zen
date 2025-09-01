"""Test configuration for agents tests with ClickHouse mocking."""

import os
import sys
from unittest.mock import Mock, MagicMock
from shared.isolated_environment import get_env

# Set environment variables BEFORE any imports
env = get_env()
env.set("TESTING", "true", "test")
env.set("DEV_MODE_DISABLE_CLICKHOUSE", "true", "test")
env.set("CLICKHOUSE_ENABLED", "false", "test")
env.set("TEST_DISABLE_CLICKHOUSE", "true", "test")
env.set("SKIP_SERVICE_HEALTH_CHECK", "true", "test")
env.set("USE_REAL_SERVICES", "false", "test")

# Mock clickhouse_connect module BEFORE it's imported
mock_clickhouse_client = MagicMock()
mock_clickhouse_client.ping = MagicMock(return_value=True)
mock_clickhouse_client.execute = MagicMock(return_value=[])
mock_clickhouse_client.disconnect = MagicMock()

mock_clickhouse_connect = MagicMock()
mock_clickhouse_connect.get_client = MagicMock(return_value=mock_clickhouse_client)

sys.modules['clickhouse_connect'] = mock_clickhouse_connect

# Mock clickhouse_driver module
mock_clickhouse_driver = MagicMock()
sys.modules['clickhouse_driver'] = mock_clickhouse_driver
sys.modules['clickhouse_driver.connection'] = MagicMock()
sys.modules['clickhouse_driver.client'] = MagicMock()
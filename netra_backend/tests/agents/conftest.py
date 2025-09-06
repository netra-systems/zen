"""Test configuration for agents tests with ClickHouse mocking."""

import os
import sys
from unittest.mock import Mock, MagicMock
from shared.isolated_environment import IsolatedEnvironment

# Set environment variables BEFORE any imports
env = IsolatedEnvironment()
env.set("TESTING", "true", "test")
env.set("DEV_MODE_DISABLE_CLICKHOUSE", "true", "test")
env.set("CLICKHOUSE_ENABLED", "false", "test")
env.set("TEST_DISABLE_CLICKHOUSE", "true", "test")
env.set("SKIP_SERVICE_HEALTH_CHECK", "true", "test")
env.set("USE_REAL_SERVICES", "false", "test")

# Mock clickhouse_connect module BEFORE it's imported'
mock_clickhouse_client = MagicMock()
mock_clickhouse_client.ping = MagicMock(return_value = True)
mock_clickhouse_client.execute = MagicMock(return_value = [])
mock_clickhouse_client.disconnect = MagicMock()

# Create a mock Client class
mock_client_class = MagicMock()
mock_client_class.return_value = mock_clickhouse_client

# Create mock driver.client module with Client class
mock_driver_client = MagicMock()
mock_driver_client.Client = mock_client_class

# Create mock driver module
mock_driver = MagicMock()
mock_driver.client = mock_driver_client

# Create mock clickhouse_connect package with proper structure
mock_clickhouse_connect = MagicMock()
mock_clickhouse_connect.get_client = MagicMock(return_value = mock_clickhouse_client)
mock_clickhouse_connect.driver = mock_driver

# Register all the modules
sys.modules['clickhouse_connect'] = mock_clickhouse_connect
sys.modules['clickhouse_connect.driver'] = mock_driver
sys.modules['clickhouse_connect.driver.client'] = mock_driver_client

# Mock clickhouse_driver module with proper structure
mock_clickhouse_driver_client = MagicMock()
mock_clickhouse_driver_connection = MagicMock()

mock_clickhouse_driver = MagicMock()
mock_clickhouse_driver.client = mock_clickhouse_driver_client
mock_clickhouse_driver.connection = mock_clickhouse_driver_connection

sys.modules['clickhouse_driver'] = mock_clickhouse_driver
sys.modules['clickhouse_driver.connection'] = mock_clickhouse_driver_connection
sys.modules['clickhouse_driver.client'] = mock_clickhouse_driver_client
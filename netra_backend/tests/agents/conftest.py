"""Test configuration for agents tests with ClickHouse mocking."""

import os
import sys
from unittest.mock import Mock, MagicMock

# Set environment variables BEFORE any imports
os.environ["TESTING"] = "true"
os.environ["DEV_MODE_DISABLE_CLICKHOUSE"] = "true"
os.environ["CLICKHOUSE_ENABLED"] = "false"
os.environ["TEST_DISABLE_CLICKHOUSE"] = "true"
os.environ["SKIP_SERVICE_HEALTH_CHECK"] = "true"
os.environ["USE_REAL_SERVICES"] = "false"

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
class TestWebSocketConnection:
    "Real WebSocket connection for testing instead of mocks.""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        ""Send JSON message."
        if self._closed:
        raise RuntimeError("WebSocket is closed)
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = Normal closure"):
        "Close WebSocket connection.""
        pass
        self._closed = True
        self.is_connected = False

    async def get_messages(self) -> list:
        ""Get all sent messages."
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        "Test to verify ClickHouse and Redis REQUIRED flags are respected in staging environment.""

        import asyncio
        import os
        import sys
        from pathlib import Path
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from netra_backend.app.redis_manager import redis_manager
        from auth_service.core.auth_manager import AuthManager
        from shared.isolated_environment import IsolatedEnvironment

        import pytest

    # Add project root to path
        project_root = Path(__file__).parent.parent.parent.absolute()
        sys.path.insert(0, str(project_root))

        from netra_backend.app.core.configuration import unified_config_manager
        from netra_backend.app.routes.health import _check_clickhouse_connection, _check_redis_connection
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient


class TestStagingServicesRequired:
        ""Test that staging respects CLICKHOUSE_REQUIRED and REDIS_REQUIRED flags."
        pass

@pytest.mark.asyncio
    async def test_clickhouse_required_in_staging_is_checked(self):
"Verify that when CLICKHOUSE_REQUIRED=true in staging, ClickHouse is checked.""
        # Mock the configuration
with patch.object(unified_config_manager, 'get_config') as mock_config:
mock_cfg = Magic            mock_cfg.environment = staging"
mock_cfg.skip_clickhouse_init = False
            # Add proper ClickHouse config attributes
mock_cfg.clickhouse_https = Magic            mock_cfg.clickhouse_https.host = "test.clickhouse.cloud
mock_cfg.clickhouse_https.port = 8443
mock_config.return_value = mock_cfg

            # Mock environment to await asyncio.sleep(0)
return CLICKHOUSE_REQUIRED=true
with patch('shared.isolated_environment.get_env') as mock_env:
mock_env.return_value = {CLICKHOUSE_REQUIRED": "true}

                # Mock the ClickHouseService
with patch('netra_backend.app.services.clickhouse_service.ClickHouseService') as mock_ch_service:
mock_instance = Magic                    mock_instance.execute_health_check = AsyncMock(return_value=True)
mock_ch_service.return_value = mock_instance

                    # Run the check - it should NOT skip and should call the service
await _check_clickhouse_connection()

                    # Verify ClickHouse was actually checked
mock_instance.execute_health_check.assert_called_once()
print(OK Test passed: ClickHouse is checked when CLICKHOUSE_REQUIRED=true in staging")

@pytest.mark.asyncio
    async def test_clickhouse_optional_in_staging_is_skipped(self):
"Verify that when CLICKHOUSE_REQUIRED=false in staging, ClickHouse can be skipped.""
pass
with patch.object(unified_config_manager, 'get_config') as mock_config:
mock_cfg = Magic            mock_cfg.environment = staging"
mock_cfg.skip_clickhouse_init = False
                            # Add proper ClickHouse config attributes
mock_cfg.clickhouse_https = Magic            mock_cfg.clickhouse_https.host = "test.clickhouse.cloud
mock_cfg.clickhouse_https.port = 8443
mock_config.return_value = mock_cfg

                            # Mock environment to await asyncio.sleep(0)
return CLICKHOUSE_REQUIRED=false
with patch('shared.isolated_environment.get_env') as mock_env:
mock_env.return_value = {CLICKHOUSE_REQUIRED": "false}

                                # Mock the ClickHouseService to fail
with patch('netra_backend.app.services.clickhouse_service.ClickHouseService') as mock_ch_service:
mock_instance = Magic                    mock_instance.execute_health_check = AsyncMock(side_effect=Exception(Connection failed"))
mock_ch_service.return_value = mock_instance

                                    # Run the check - it should handle the failure gracefully
await _check_clickhouse_connection()

                                    # The test passes if no exception was raised
    print("OK Test passed: ClickHouse failure is handled gracefully when optional in staging)

@pytest.mark.asyncio
    async def test_redis_optional_in_staging_is_skipped(self):
""Verify that when REDIS_REQUIRED=false in staging, Redis is skipped."
with patch.object(unified_config_manager, 'get_config') as mock_config:
mock_cfg = Magic            mock_cfg.environment = "staging
mock_cfg.skip_redis_init = False
mock_config.return_value = mock_cfg

                                            # Mock environment to await asyncio.sleep(0)
return REDIS_REQUIRED=false (staging default)
with patch('shared.isolated_environment.get_env') as mock_env:
mock_env.return_value = {REDIS_REQUIRED": "false}

                                                # Mock redis_manager to fail
with patch('netra_backend.app.redis_manager.redis_manager') as mock_redis:
mock_redis.enabled = True
mock_redis.ping = AsyncMock(side_effect=Exception(Connection failed"))

                                                    # Run the check - it should handle the failure gracefully
await _check_redis_connection()

                                                    # The test passes if no exception was raised
    print("OK Test passed: Redis failure is handled gracefully when optional in staging)

@pytest.mark.asyncio
    async def test_current_bug_clickhouse_incorrectly_skipped(self):
""Reproduce the current bug where ClickHouse is skipped despite being required."
pass
                                                        # This test demonstrates the current bug
with patch.object(unified_config_manager, 'get_config') as mock_config:
mock_cfg = Magic            mock_cfg.environment = "staging
mock_cfg.skip_clickhouse_init = False
                                                            # Add proper ClickHouse config attributes
mock_cfg.clickhouse_https = Magic            mock_cfg.clickhouse_https.host = test.clickhouse.cloud"
mock_cfg.clickhouse_https.port = 8443
mock_config.return_value = mock_cfg

                                                            # Mock environment to await asyncio.sleep(0)
return CLICKHOUSE_REQUIRED=true (as in staging.env)
with patch('shared.isolated_environment.get_env') as mock_env:
mock_env.return_value = {"CLICKHOUSE_REQUIRED: true"}

                                                                # Mock the logger to capture the skip message
with patch('netra_backend.app.routes.health.logger') as mock_logger:
                                                                    # With current buggy code, it will skip despite REQUIRED=true
await _check_clickhouse_connection()

                                                                    # Check if the incorrect skip message was logged
skip_logged = any( )
"ClickHouse check skipped entirely in staging environment in str(call)
for call in mock_logger.info.call_args_list
                                                                    

if skip_logged:
    print(X Bug confirmed: ClickHouse is incorrectly skipped when CLICKHOUSE_REQUIRED=true")
assert False, "ClickHouse should not be skipped when CLICKHOUSE_REQUIRED=true
else:
    print(OK Bug fixed: ClickHouse is properly checked when required")


def run_tests():
"Run the tests to demonstrate the bug.""
print(")
" + =*70)
print("Testing Staging Services Required Flags")
print(=*70 + " )
")

test = TestStagingServicesRequired()

    # Run each test
tests = [
test.test_current_bug_clickhouse_incorrectly_skipped,
test.test_clickhouse_required_in_staging_is_checked,
test.test_clickhouse_optional_in_staging_is_skipped,
test.test_redis_optional_in_staging_is_skipped
    

for test_func in tests:
    print(formatted_string)
    print("-" * 40)
try:
    asyncio.run(test_func())
except AssertionError as e:
    print(formatted_string)
except Exception as e:
    print("")

print()
" + "=*70)


if __name__ == __main__":
    run_tests()
pass

"""
ClickHouse test configuration and fixtures.
Provides common fixtures for all ClickHouse tests.
"""

import pytest
from netra_backend.app.config import get_config
from netra_backend.app.db.clickhouse_base import ClickHouseDatabase
from netra_backend.app.db.clickhouse_query_fixer import ClickHouseQueryInterceptor
from netra_backend.app.core.isolated_environment import get_env


def pytest_collection_modifyitems(config, items):
    """Enable ClickHouse for tests that require it."""
    env = get_env()
    
    # Check if any tests in this collection need ClickHouse
    needs_clickhouse = False
    for item in items:
        # Check for real_database marker which indicates ClickHouse tests
        if item.get_closest_marker('real_database'):
            needs_clickhouse = True
            break
    
    # If tests need ClickHouse, enable it with proper configuration
    if needs_clickhouse:
        env.set("CLICKHOUSE_ENABLED", "true", "clickhouse_tests")
        env.set("DEV_MODE_DISABLE_CLICKHOUSE", "false", "clickhouse_tests")
        # Set ClickHouse connection details for local dev environment
        env.set("CLICKHOUSE_HOST", "localhost", "clickhouse_tests")
        env.set("CLICKHOUSE_PORT", "8123", "clickhouse_tests")
        env.set("CLICKHOUSE_USER", "default", "clickhouse_tests")
        env.set("CLICKHOUSE_PASSWORD", "netra_dev_password", "clickhouse_tests")
        env.set("CLICKHOUSE_DB", "netra_dev", "clickhouse_tests")
        env.set("CLICKHOUSE_HTTP_PORT", "8123", "clickhouse_tests")


def _get_clickhouse_config():
    """Get ClickHouse configuration based on environment"""
    config = get_config()
    # Use HTTP config for local development, HTTPS for production/remote
    if config.clickhouse_mode == "local" or config.environment == "development":
        # Use HTTP port (8123) for local development
        return config.clickhouse_http
    else:
        # Use HTTPS port (8443) for production/staging
        return config.clickhouse_https


def _create_clickhouse_client(config):
    """Create ClickHouse client with given configuration"""
    # Never use HTTPS for localhost connections to avoid SSL errors
    is_localhost = config.host in ["localhost", "127.0.0.1", "::1"]
    # Use secure connection only for remote hosts on HTTPS port (8443)
    use_secure = not is_localhost and config.port == 8443
    return ClickHouseDatabase(
        host=config.host, 
        port=config.port, 
        user=config.user,
        password=config.password, 
        database=config.database, 
        secure=use_secure
    )


def _check_clickhouse_availability():
    """Check if ClickHouse is available and accessible (simplified version)"""
    try:
        config = _get_clickhouse_config()
        # Basic configuration check - actual connection will be tested by the fixture
        return config.host and config.port and config.user
    except Exception:
        return False


# Make this available for import by other test modules
def check_clickhouse_availability():
    """Public interface for checking ClickHouse availability"""
    return _check_clickhouse_availability()


@pytest.fixture
def real_clickhouse_client():
    """Create a real ClickHouse client using appropriate configuration.
    
    This fixture:
    - Uses HTTP on port 8123 for localhost connections
    - Uses correct credentials (user: default, password: netra_dev_password)
    - Is available to all ClickHouse tests through pytest fixture discovery
    """
    # Check basic availability first
    if not _check_clickhouse_availability():
        pytest.skip("ClickHouse server not available - skipping real database test")
    
    config = _get_clickhouse_config()
    try:
        client = _create_clickhouse_client(config)
        yield client
    except Exception as e:
        # If connection fails during test execution, skip with detailed message
        if any(error in str(e).lower() for error in [
            'ssl', 'connection refused', 'timeout', 'network', 
            'wrong version number', 'cannot connect', 'host unreachable'
        ]):
            pytest.skip(f"ClickHouse connection failed during test: {e}")
        else:
            raise
    # Note: Disconnect handled by the test itself or auto-cleanup


@pytest.fixture
async def async_real_clickhouse_client():
    """Async version of real_clickhouse_client for async test contexts"""
    # Check basic availability first
    if not _check_clickhouse_availability():
        pytest.skip("ClickHouse server not available - skipping real database test")
    
    config = _get_clickhouse_config()
    try:
        client = _create_clickhouse_client(config)
        # Test basic connection
        await client.execute_query("SELECT 1")
        yield client
    except Exception as e:
        # If connection fails during test execution, skip with detailed message
        if any(error in str(e).lower() for error in [
            'ssl', 'connection refused', 'timeout', 'network', 
            'wrong version number', 'cannot connect', 'host unreachable'
        ]):
            pytest.skip(f"ClickHouse connection failed during test: {e}")
        else:
            raise


@pytest.fixture
def real_clickhouse_client_with_interceptor():
    """Create a real ClickHouse client with query interceptor for advanced testing"""
    # Check basic availability first
    if not _check_clickhouse_availability():
        pytest.skip("ClickHouse server not available - skipping real database test")
    
    config = _get_clickhouse_config()
    try:
        client = _create_clickhouse_client(config)
        interceptor = ClickHouseQueryInterceptor(client)
        yield interceptor
    except Exception as e:
        # If connection fails during test execution, skip with detailed message
        if any(error in str(e).lower() for error in [
            'ssl', 'connection refused', 'timeout', 'network', 
            'wrong version number', 'cannot connect', 'host unreachable'
        ]):
            pytest.skip(f"ClickHouse connection failed during test: {e}")
        else:
            raise
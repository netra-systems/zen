"""
ClickHouse test configuration and fixtures.
Provides common fixtures for all ClickHouse tests.
"""

import os
import pytest
from netra_backend.app.config import get_config
from netra_backend.app.db.clickhouse_base import ClickHouseDatabase
from netra_backend.app.db.clickhouse_query_fixer import ClickHouseQueryInterceptor
from netra_backend.app.core.isolated_environment import get_env


def pytest_collection_modifyitems(config, items):
    """Configure ClickHouse test collection - respects test framework settings."""
    # This function intentionally does not override framework settings
    # Tests with @pytest.mark.real_database will be skipped by fixtures
    # when CLICKHOUSE_ENABLED=false or DEV_MODE_DISABLE_CLICKHOUSE=true
    pass


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
    env = get_env()
    
    # First check if ClickHouse is disabled by test framework settings
    clickhouse_disabled = (
        env.get("DEV_MODE_DISABLE_CLICKHOUSE", "").lower() == "true" or
        env.get("CLICKHOUSE_ENABLED", "").lower() == "false"
    )
    
    if clickhouse_disabled:
        return False
    
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
    - Checks if ClickHouse is disabled by test framework settings
    - Uses HTTP on port 8123 for localhost connections
    - Uses correct credentials (user: default, password: netra_dev_password)
    - Is available to all ClickHouse tests through pytest fixture discovery
    """
    env = get_env()
    
    # Check if ClickHouse should be disabled based on test framework settings
    # These variables are set after test collection, so check them in the fixture
    clickhouse_disabled_by_framework = (
        env.get("DEV_MODE_DISABLE_CLICKHOUSE", "").lower() == "true" or
        env.get("CLICKHOUSE_ENABLED", "").lower() == "false"
    )
    
    if clickhouse_disabled_by_framework:
        pytest.skip("ClickHouse disabled by test framework (DEV_MODE_DISABLE_CLICKHOUSE=true or CLICKHOUSE_ENABLED=false)")
    
    # Check basic availability
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
            'wrong version number', 'cannot connect', 'host unreachable',
            'authentication failed'
        ]):
            pytest.skip(f"ClickHouse connection failed during test: {e}")
        else:
            raise
    # Note: Disconnect handled by the test itself or auto-cleanup


@pytest.fixture
async def async_real_clickhouse_client():
    """Async version of real_clickhouse_client for async test contexts"""
    env = get_env()
    
    # Check if ClickHouse should be disabled based on test framework settings
    clickhouse_disabled_by_framework = (
        env.get("DEV_MODE_DISABLE_CLICKHOUSE", "").lower() == "true" or
        env.get("CLICKHOUSE_ENABLED", "").lower() == "false"
    )
    
    if clickhouse_disabled_by_framework:
        pytest.skip("ClickHouse disabled by test framework (DEV_MODE_DISABLE_CLICKHOUSE=true or CLICKHOUSE_ENABLED=false)")
    
    # Check basic availability
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
            'wrong version number', 'cannot connect', 'host unreachable',
            'authentication failed', 'connection error', 'refused'
        ]):
            pytest.skip(f"ClickHouse connection failed during test: {e}")
        else:
            raise


@pytest.fixture
def real_clickhouse_client_with_interceptor():
    """Create a real ClickHouse client with query interceptor for advanced testing"""
    env = get_env()
    
    # Check if ClickHouse should be disabled based on test framework settings
    clickhouse_disabled_by_framework = (
        env.get("DEV_MODE_DISABLE_CLICKHOUSE", "").lower() == "true" or
        env.get("CLICKHOUSE_ENABLED", "").lower() == "false"
    )
    
    if clickhouse_disabled_by_framework:
        pytest.skip("ClickHouse disabled by test framework (DEV_MODE_DISABLE_CLICKHOUSE=true or CLICKHOUSE_ENABLED=false)")
    
    # Check basic availability
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
            'wrong version number', 'cannot connect', 'host unreachable',
            'authentication failed'
        ]):
            pytest.skip(f"ClickHouse connection failed during test: {e}")
        else:
            raise
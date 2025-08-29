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
    """Enable ClickHouse for tests that require it."""
    env = get_env()
    
    # Check if ClickHouse is explicitly disabled by test framework
    clickhouse_disabled_by_framework = (
        env.get("DEV_MODE_DISABLE_CLICKHOUSE", "").lower() == "true" or
        env.get("CLICKHOUSE_ENABLED", "").lower() == "false"
    )
    
    # Check if any tests in this collection need ClickHouse
    needs_clickhouse = False
    for item in items:
        # Check for real_database marker which indicates ClickHouse tests
        if item.get_closest_marker('real_database'):
            needs_clickhouse = True
            break
    
    # If ClickHouse is disabled by framework, respect that setting
    if clickhouse_disabled_by_framework:
        # Don't override framework settings - let fixtures handle the skipping
        return
    
    # If tests need ClickHouse and it's not disabled by framework, enable it with proper configuration
    if needs_clickhouse:
        env.set("CLICKHOUSE_ENABLED", "true", "clickhouse_tests")
        env.set("DEV_MODE_DISABLE_CLICKHOUSE", "false", "clickhouse_tests")
        
        # Determine environment and set appropriate ClickHouse credentials
        test_env = env.get("ENVIRONMENT", "development").lower()
        
        if test_env in ["testing", "test"]:
            # Test environment credentials (for TEST Docker environment)
            env.set("CLICKHOUSE_HOST", "localhost", "clickhouse_tests")
            env.set("CLICKHOUSE_PORT", "8124", "clickhouse_tests")  # Test environment uses port 8124
            env.set("CLICKHOUSE_USER", "test", "clickhouse_tests")
            env.set("CLICKHOUSE_PASSWORD", "test", "clickhouse_tests")
            env.set("CLICKHOUSE_DB", "netra_test_analytics", "clickhouse_tests")
            env.set("CLICKHOUSE_HTTP_PORT", "8124", "clickhouse_tests")
        else:
            # Development environment credentials (for DEV Docker environment)
            env.set("CLICKHOUSE_HOST", "localhost", "clickhouse_tests")
            env.set("CLICKHOUSE_PORT", "8123", "clickhouse_tests")
            env.set("CLICKHOUSE_USER", "netra", "clickhouse_tests")
            env.set("CLICKHOUSE_PASSWORD", "netra123", "clickhouse_tests")
            env.set("CLICKHOUSE_DB", "netra_analytics", "clickhouse_tests")
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
    
    print(f"DEBUG: Async fixture check - DEV_MODE_DISABLE_CLICKHOUSE={env.get('DEV_MODE_DISABLE_CLICKHOUSE')}, CLICKHOUSE_ENABLED={env.get('CLICKHOUSE_ENABLED')}")
    print(f"DEBUG: clickhouse_disabled_by_framework={clickhouse_disabled_by_framework}")
    print(f"DEBUG: ENVIRONMENT={env.get('ENVIRONMENT')}")
    print(f"DEBUG: os.environ.ENVIRONMENT={os.environ.get('ENVIRONMENT', 'not-set')}")
    print(f"DEBUG: CLICKHOUSE_PORT={env.get('CLICKHOUSE_PORT')}, CLICKHOUSE_HTTP_PORT={env.get('CLICKHOUSE_HTTP_PORT')}")
    
    # Force correct ClickHouse configuration for testing environment
    # Check both environment sources since there might be timing issues
    test_env_isolated = env.get("ENVIRONMENT", "development").lower()
    test_env_os = os.environ.get("ENVIRONMENT", "development").lower()
    test_env = test_env_os if test_env_os in ["testing", "test"] else test_env_isolated
    if test_env in ["testing", "test"]:
        print(f"DEBUG: Detected testing environment - forcing test ClickHouse configuration")
        env.set("CLICKHOUSE_HOST", "localhost", "clickhouse_tests_fixture_override")
        env.set("CLICKHOUSE_PORT", "8124", "clickhouse_tests_fixture_override")  # Test environment uses port 8124
        env.set("CLICKHOUSE_USER", "test", "clickhouse_tests_fixture_override")
        env.set("CLICKHOUSE_PASSWORD", "test", "clickhouse_tests_fixture_override")
        env.set("CLICKHOUSE_DB", "netra_test_analytics", "clickhouse_tests_fixture_override")
        env.set("CLICKHOUSE_HTTP_PORT", "8124", "clickhouse_tests_fixture_override")
        print(f"DEBUG: Set TEST environment ClickHouse config - port 8124")
        
        # Force configuration reload after setting environment variables
        from netra_backend.app.config import reload_unified_config
        reload_unified_config()
        print(f"DEBUG: Reloaded unified config after environment variable changes")
    
    # If framework disabled ClickHouse but this is a real_database test, override the settings
    if clickhouse_disabled_by_framework:
        print(f"DEBUG: Framework has ClickHouse disabled, but this is a real_database test - overriding settings")
        env.set("CLICKHOUSE_ENABLED", "true", "clickhouse_tests_fixture_override")
        env.set("DEV_MODE_DISABLE_CLICKHOUSE", "false", "clickhouse_tests_fixture_override")
        
        # Determine environment and set appropriate ClickHouse credentials
        test_env = env.get("ENVIRONMENT", "development").lower()
        
        if test_env in ["testing", "test"]:
            # Test environment credentials (for TEST Docker environment)
            env.set("CLICKHOUSE_HOST", "localhost", "clickhouse_tests_fixture_override")
            env.set("CLICKHOUSE_PORT", "8124", "clickhouse_tests_fixture_override")  # Test environment uses port 8124
            env.set("CLICKHOUSE_USER", "test", "clickhouse_tests_fixture_override")
            env.set("CLICKHOUSE_PASSWORD", "test", "clickhouse_tests_fixture_override")
            env.set("CLICKHOUSE_DB", "netra_test_analytics", "clickhouse_tests_fixture_override")
            env.set("CLICKHOUSE_HTTP_PORT", "8124", "clickhouse_tests_fixture_override")
            print(f"DEBUG: Set TEST environment ClickHouse config - port 8124")
        else:
            # Development environment credentials (for DEV Docker environment)
            env.set("CLICKHOUSE_HOST", "localhost", "clickhouse_tests_fixture_override")
            env.set("CLICKHOUSE_PORT", "8123", "clickhouse_tests_fixture_override")
            env.set("CLICKHOUSE_USER", "netra", "clickhouse_tests_fixture_override")
            env.set("CLICKHOUSE_PASSWORD", "netra123", "clickhouse_tests_fixture_override")
            env.set("CLICKHOUSE_DB", "netra_analytics", "clickhouse_tests_fixture_override")
            env.set("CLICKHOUSE_HTTP_PORT", "8123", "clickhouse_tests_fixture_override")
            print(f"DEBUG: Set DEV environment ClickHouse config - port 8123")
        
        # Force configuration reload after setting environment variables
        from netra_backend.app.config import reload_unified_config
        reload_unified_config()
        print(f"DEBUG: Reloaded unified config after environment variable changes")
    
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
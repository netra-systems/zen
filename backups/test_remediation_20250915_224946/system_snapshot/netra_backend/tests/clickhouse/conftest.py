"""
ClickHouse test configuration and fixtures.
Provides common fixtures for all ClickHouse tests.
"""

import os
import pytest
from netra_backend.app.config import get_config
from netra_backend.app.db.clickhouse_base import ClickHouseDatabase
from netra_backend.app.db.clickhouse_query_fixer import ClickHouseQueryInterceptor
from shared.isolated_environment import IsolatedEnvironment, get_env

# CRITICAL: Set ClickHouse configuration BEFORE any imports that trigger config loading
env = IsolatedEnvironment()

# CRITICAL FIX: Check if Docker services are available before enabling ClickHouse
def _check_docker_clickhouse_available():
    """Check if Docker ClickHouse service is available"""
    import socket
    try:
        # Test connection to Docker ClickHouse port (alpine-test service uses 8126)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', 8126))
        sock.close()
        return result == 0
    except Exception:
        return False

# Configure ClickHouse based on Docker availability
if _check_docker_clickhouse_available():
    # Docker ClickHouse is available - use real connection with alpine-test service configuration
    env.set("CLICKHOUSE_HOST", env.get("TEST_CLICKHOUSE_HOST", "localhost"), source="clickhouse_conftest_setup")
    env.set("CLICKHOUSE_PORT", env.get("TEST_CLICKHOUSE_PORT", "8126"), source="clickhouse_conftest_setup")
    env.set("CLICKHOUSE_HTTP_PORT", env.get("TEST_CLICKHOUSE_HTTP_PORT", "8126"), source="clickhouse_conftest_setup") 
    env.set("CLICKHOUSE_USER", env.get("TEST_CLICKHOUSE_USER", "test"), source="clickhouse_conftest_setup")
    env.set("CLICKHOUSE_PASSWORD", env.get("TEST_CLICKHOUSE_PASSWORD", "test"), source="clickhouse_conftest_setup")
    env.set("CLICKHOUSE_DATABASE", env.get("TEST_CLICKHOUSE_DATABASE", "test_analytics"), source="clickhouse_conftest_setup")
    env.set("CLICKHOUSE_DB", env.get("TEST_CLICKHOUSE_DB", "test_analytics"), source="clickhouse_conftest_setup")
    # Enable ClickHouse for these specific tests
    env.set("CLICKHOUSE_ENABLED", "true", source="clickhouse_conftest_setup")
    env.set("DEV_MODE_DISABLE_CLICKHOUSE", "false", source="clickhouse_conftest_setup")
    env.set("CLICKHOUSE_TEST_DISABLE", "false", source="clickhouse_conftest_setup")
else:
    # Docker ClickHouse not available - use NoOp client
    env.set("CLICKHOUSE_ENABLED", "false", source="clickhouse_conftest_setup") 
    env.set("DEV_MODE_DISABLE_CLICKHOUSE", "true", source="clickhouse_conftest_setup")
    env.set("CLICKHOUSE_TEST_DISABLE", "true", source="clickhouse_conftest_setup")
# Force configuration reload after setting environment variables
try:
    from netra_backend.app.config import reload_config
    reload_config(force=True)
except ImportError:
    pass


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
    # OVERRIDE: For test environment, use Docker container settings directly
    # This bypasses configuration caching issues during testing
    env = get_env()
    test_host = env.get("TEST_CLICKHOUSE_HOST")
    test_port = env.get("TEST_CLICKHOUSE_HTTP_PORT") 
    test_user = env.get("TEST_CLICKHOUSE_USER")
    test_password = env.get("TEST_CLICKHOUSE_PASSWORD")
    test_database = env.get("TEST_CLICKHOUSE_DB")
    
    # Use test settings if available, otherwise fall back to config
    host = test_host or config.host or "localhost"
    port = int(test_port or config.port or 8126)
    user = test_user or config.user or "test"  
    password = test_password or config.password or "test"
    database = test_database or config.database or "test_analytics"
    
    # Never use HTTPS for localhost connections to avoid SSL errors
    is_localhost = host in ["localhost", "127.0.0.1", "::1"]
    # Use secure connection only for remote hosts on HTTPS port (8443)
    use_secure = not is_localhost and port == 8443
    
    return ClickHouseDatabase(
        host=host, 
        port=port, 
        user=user,
        password=password, 
        database=database, 
        secure=use_secure
    )


def _check_clickhouse_availability():
    """Check if ClickHouse is available and accessible (simplified version)"""
    env = get_env()
    
    # Override disabled ClickHouse for these specific tests by setting the necessary env vars
    # This allows ClickHouse-specific tests to run even when globally disabled
    if not env.get("CLICKHOUSE_HOST"):
        # Use Docker container configuration for ClickHouse tests (alpine-test service)
        env.set("CLICKHOUSE_HOST", env.get("TEST_CLICKHOUSE_HOST", "localhost"), source="clickhouse_conftest")
        env.set("CLICKHOUSE_PORT", env.get("TEST_CLICKHOUSE_PORT", "8126"), source="clickhouse_conftest")
        env.set("CLICKHOUSE_HTTP_PORT", env.get("TEST_CLICKHOUSE_HTTP_PORT", "8126"), source="clickhouse_conftest") 
        env.set("CLICKHOUSE_USER", env.get("TEST_CLICKHOUSE_USER", "test"), source="clickhouse_conftest")
        env.set("CLICKHOUSE_PASSWORD", env.get("TEST_CLICKHOUSE_PASSWORD", "test"), source="clickhouse_conftest")
        env.set("CLICKHOUSE_DATABASE", env.get("TEST_CLICKHOUSE_DATABASE", "test_analytics"), source="clickhouse_conftest")
        env.set("CLICKHOUSE_DB", env.get("TEST_CLICKHOUSE_DB", "test_analytics"), source="clickhouse_conftest")
        # Enable ClickHouse for these specific tests
        env.set("CLICKHOUSE_ENABLED", "true", source="clickhouse_conftest")
        env.set("DEV_MODE_DISABLE_CLICKHOUSE", "false", source="clickhouse_conftest")
        
        # Force configuration reload to pick up the new environment variables
        try:
            from netra_backend.app.config import reload_config
            reload_config(force=True)
        except ImportError:
            # Fallback if reload function not available
            pass
    
    try:
        # Check if basic environment variables are set
        clickhouse_host = env.get("CLICKHOUSE_HOST", "localhost")
        clickhouse_port = env.get("CLICKHOUSE_HTTP_PORT", "8126")
        clickhouse_user = env.get("CLICKHOUSE_USER", "test")
        return bool(clickhouse_host and clickhouse_port and clickhouse_user)
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
    - Overrides disabled ClickHouse settings for ClickHouse-specific tests
    - Uses HTTP on port 8125 for Docker container connections
    - Uses correct credentials (user: default, password: test_password)
    - Is available to all ClickHouse tests through pytest fixture discovery
    """
    env = get_env()
    
    # OVERRIDE: For ClickHouse-specific tests, always enable ClickHouse
    # This ensures these tests can run even when ClickHouse is globally disabled
    _check_clickhouse_availability()  # This sets the necessary environment variables
    
    # Check basic availability BEFORE trying to get config or create client
    if not _check_clickhouse_availability():
        pytest.skip("ClickHouse server not available - skipping real database test")
    
    try:
        config = _get_clickhouse_config()
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
    
    # OVERRIDE: For ClickHouse-specific tests, always enable ClickHouse
    _check_clickhouse_availability()  # This sets the necessary environment variables
    
    # Check basic availability
    if not _check_clickhouse_availability():
        pytest.skip("ClickHouse server not available - skipping real database test")
    
    try:
        config = _get_clickhouse_config()
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
    
    # OVERRIDE: For ClickHouse-specific tests, always enable ClickHouse
    _check_clickhouse_availability()  # This sets the necessary environment variables
    
    # Check basic availability
    if not _check_clickhouse_availability():
        pytest.skip("ClickHouse server not available - skipping real database test")
    
    try:
        config = _get_clickhouse_config()
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
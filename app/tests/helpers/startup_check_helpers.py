"""Helper functions for startup check tests."""

import os
import tempfile
from unittest.mock import Mock, AsyncMock
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.startup_checks import StartupCheckResult


def create_mock_app():
    """Create a mock app with required state."""
    app = Mock()
    app.state = Mock()
    
    # Mock database session factory
    db_session = AsyncMock(spec=AsyncSession)
    db_session.__aenter__ = AsyncMock(return_value=db_session)
    db_session.__aexit__ = AsyncMock(return_value=None)
    app.state.db_session_factory = Mock(return_value=db_session)
    
    # Mock Redis manager
    redis_manager = AsyncMock()
    redis_manager.connect = AsyncMock()
    redis_manager.set = AsyncMock()
    redis_manager.get = AsyncMock(return_value="test_value")
    redis_manager.delete = AsyncMock()
    app.state.redis_manager = redis_manager
    
    # Mock LLM manager
    llm_manager = Mock()
    llm_manager.get_llm = Mock(return_value=Mock())
    app.state.llm_manager = llm_manager
    
    return app


def create_success_check_result(name="test_check"):
    """Create a successful check result."""
    return StartupCheckResult(
        name=name,
        success=True,
        message="Success",
        critical=True
    )


def create_failure_check_result(name="test_check", critical=True):
    """Create a failed check result."""
    return StartupCheckResult(
        name=name,
        success=False,
        message="Failure",
        critical=critical
    )


async def mock_successful_check(checker):
    """Mock successful check function."""
    checker.results.append(create_success_check_result())


async def mock_critical_failure_check(checker):
    """Mock critical failure check function."""
    checker.results.append(create_failure_check_result("critical_check", True))


async def mock_non_critical_failure_check(checker):
    """Mock non-critical failure check function."""
    checker.results.append(create_failure_check_result("non_critical_check", False))


async def mock_exception_check():
    """Mock check that raises exception."""
    raise RuntimeError("Unexpected error")


def setup_all_check_mocks(checker, check_function):
    """Setup all checker methods with the same mock function."""
    checker.env_checker.check_environment_variables = AsyncMock(side_effect=check_function)
    checker.env_checker.check_configuration = AsyncMock(side_effect=check_function)
    checker.system_checker.check_file_permissions = AsyncMock(side_effect=check_function)
    checker.db_checker.check_database_connection = AsyncMock(side_effect=check_function)
    checker.service_checker.check_redis = AsyncMock(side_effect=check_function)
    checker.service_checker.check_clickhouse = AsyncMock(side_effect=check_function)
    checker.service_checker.check_llm_providers = AsyncMock(side_effect=check_function)
    checker.system_checker.check_memory_and_resources = AsyncMock(side_effect=check_function)
    checker.system_checker.check_network_connectivity = AsyncMock(side_effect=check_function)
    checker.db_checker.check_or_create_assistant = AsyncMock(side_effect=check_function)


def verify_check_results(results, expected_total=10, expected_passed=10, 
                        expected_failed_critical=0, expected_failed_non_critical=0):
    """Verify check results match expectations."""
    assert results["total_checks"] == expected_total
    assert results["passed"] == expected_passed
    assert results["failed_critical"] == expected_failed_critical
    assert results["failed_non_critical"] == expected_failed_non_critical
    assert results["duration_ms"] > 0


def setup_env_vars_production(monkeypatch):
    """Setup environment variables for production testing."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")


def setup_env_vars_development(monkeypatch):
    """Setup environment variables for development testing."""
    monkeypatch.setenv("ENVIRONMENT", "development")


def clear_required_env_vars(monkeypatch):
    """Clear required environment variables."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)


def clear_optional_env_vars(monkeypatch):
    """Clear optional environment variables."""
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def setup_temp_directory_test():
    """Setup temporary directory for file permission tests."""
    tmpdir = tempfile.TemporaryDirectory()
    original_cwd = os.getcwd()
    os.chdir(tmpdir.name)
    return tmpdir, original_cwd


def verify_directories_created():
    """Verify required directories were created."""
    assert Path("logs").exists()
    assert Path("uploads").exists()
    assert Path("temp").exists()


def create_mock_database_session(mock_app):
    """Get database session from mock app."""
    return mock_app.state.db_session_factory.return_value


def setup_successful_db_queries(db_session):
    """Setup successful database query mocks."""
    # Mock SELECT 1 result
    select_result = Mock()
    select_result.scalar_one = Mock(return_value=1)
    
    # Mock table existence results
    table_result = Mock()
    table_result.scalar_one = Mock(return_value=True)
    
    db_session.execute = AsyncMock(side_effect=[select_result] + [table_result] * 4)


def setup_missing_table_db_queries(db_session):
    """Setup database queries with missing table."""
    select_result = Mock()
    select_result.scalar_one = Mock(return_value=1)
    
    table_result = Mock()
    table_result.scalar_one = Mock(return_value=False)
    
    db_session.execute = AsyncMock(side_effect=[select_result, table_result])


def setup_redis_read_write_test(redis_manager):
    """Setup Redis read/write test mocks."""
    async def mock_set(key, value, **kwargs):
        redis_manager._test_value = value
    
    async def mock_get(key):
        return redis_manager._test_value if hasattr(redis_manager, '_test_value') else "test_value"
    
    redis_manager.set = AsyncMock(side_effect=mock_set)
    redis_manager.get = AsyncMock(side_effect=mock_get)


def verify_redis_operations(redis_manager):
    """Verify Redis operations were called."""
    redis_manager.connect.assert_called_once()
    redis_manager.set.assert_called_once()
    redis_manager.get.assert_called_once()
    redis_manager.delete.assert_called_once()


def create_mock_clickhouse_client(tables):
    """Create mock ClickHouse client with specified tables."""
    mock_client = AsyncMock()
    mock_client.ping = Mock()
    mock_client.execute = Mock(return_value=tables)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


def create_mock_memory_info(total_gb, available_gb):
    """Create mock memory info."""
    mock_memory = Mock()
    mock_memory.total = total_gb * (1024**3)
    mock_memory.available = available_gb * (1024**3)
    return mock_memory


def create_mock_disk_info(free_gb):
    """Create mock disk info."""
    mock_disk = Mock()
    mock_disk.free = free_gb * (1024**3)
    return mock_disk


def setup_socket_mock(mock_socket_class, return_value=0):
    """Setup socket mock for network connectivity tests."""
    mock_socket = Mock()
    mock_socket.connect_ex.return_value = return_value
    mock_socket_class.return_value = mock_socket
    return mock_socket


def create_mock_assistant_query_result(assistant=None):
    """Create mock result for assistant query."""
    mock_result = Mock()
    mock_result.scalar_one_or_none = Mock(return_value=assistant)
    return mock_result
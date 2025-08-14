"""
Configuration for performance tests.
Sets up fixtures and test environment for corpus generation performance testing.
"""

import pytest
import asyncio
import os
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock

from app.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock settings for performance tests"""
    mock_config = MagicMock()
    mock_config.clickhouse_https.host = "test-host"
    mock_config.clickhouse_https.port = 8443
    mock_config.clickhouse_https.user = "test-user"
    mock_config.clickhouse_https.password = "test-pass"
    mock_config.clickhouse_https.database = "test-db"
    mock_config.llm_configs = {'default': MagicMock(api_key="test-key")}
    return mock_config


@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager for performance tests"""
    manager = AsyncMock()
    manager.broadcast = AsyncMock()
    return manager


@pytest.fixture
def performance_test_data():
    """Test data for performance benchmarks"""
    return {
        'small_corpus': {
            'simple_chat': [('prompt1', 'response1'), ('prompt2', 'response2')],
            'analysis': [('analysis1', 'result1')]
        },
        'medium_corpus': {
            'simple_chat': [(f'prompt_{i}', f'response_{i}') for i in range(100)],
            'analysis': [(f'analysis_{i}', f'result_{i}') for i in range(100)]
        }
    }


@pytest.fixture(autouse=True)
def setup_performance_environment(tmp_path, monkeypatch):
    """Set up environment for performance tests"""
    # Create temporary directories
    test_dir = tmp_path / "performance_test"
    test_dir.mkdir()
    
    corpus_dir = test_dir / "content_corpuses"
    corpus_dir.mkdir()
    
    # Set environment variables
    monkeypatch.setenv("CORPUS_TEST_DIR", str(corpus_dir))
    
    yield test_dir


@pytest.fixture
def cleanup_performance_files():
    """Clean up performance test files"""
    files_to_cleanup = []
    
    def register_cleanup(filepath: str):
        """Register file for cleanup"""
        files_to_cleanup.append(filepath)
    
    yield register_cleanup
    
    # Cleanup
    for filepath in files_to_cleanup:
        if os.path.exists(filepath):
            os.remove(filepath)


# Performance test markers
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", 
        "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers",
        "benchmark: mark test as benchmark test"
    )
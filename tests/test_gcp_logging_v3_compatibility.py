"""
Regression tests for Google Cloud Logging v3 compatibility.

Ensures that our code remains compatible with google-cloud-logging v3.x API changes.
Specifically tests the removal of the enums module and changes to severity handling.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_no_enums_import():
    """Test that we don't import the removed enums module from google-cloud-logging v3."""
    # This test verifies that we can import our modules without the enums module
    from test_framework.gcp_integration.log_reader import GCPLogReader, LogFilter, LogEntry
    from test_framework.gcp_integration.base import GCPConfig, GCPBaseClient
    
    # Verify the imports succeeded
    assert GCPLogReader is not None
    assert LogFilter is not None
    assert LogEntry is not None
    assert GCPConfig is not None
    assert GCPBaseClient is not None


def test_severity_handling_without_enums():
    """Test that LogEntry.from_gcp_entry handles severity correctly without enums."""
    from test_framework.gcp_integration.log_reader import LogEntry
    
    # Create a mock GCP log entry
    mock_entry = Mock()
    mock_entry.timestamp = Mock()
    mock_entry.severity = "ERROR"  # In v3, severity is already a string
    mock_entry.payload = {"message": "Test error message"}
    mock_entry.resource = Mock()
    mock_entry.resource.labels = {"service_name": "test-service"}
    mock_entry.trace = "trace-123"
    mock_entry.span_id = "span-456"
    mock_entry.labels = {"test": "label"}
    mock_entry.source_location = None
    
    # Test that from_gcp_entry handles string severity correctly
    log_entry = LogEntry.from_gcp_entry(mock_entry)
    
    assert log_entry.severity == "ERROR"
    assert log_entry.message == "Test error message"
    assert log_entry.service_name == "test-service"
    assert log_entry.trace_id == "trace-123"
    assert log_entry.span_id == "span-456"
    assert log_entry.labels == {"test": "label"}
    
    # Test with None severity
    mock_entry.severity = None
    log_entry = LogEntry.from_gcp_entry(mock_entry)
    assert log_entry.severity == "DEFAULT"
    
    # Test with numeric severity (edge case)
    mock_entry.severity = 500
    log_entry = LogEntry.from_gcp_entry(mock_entry)
    assert log_entry.severity == "500"


def test_gcp_config_initialization():
    """Test that GCPConfig can be initialized with the correct parameters."""
    from test_framework.gcp_integration.base import GCPConfig
    
    # Test basic initialization
    config = GCPConfig(
        project_id="test-project",
        region="us-central1"
    )
    
    assert config.project_id == "test-project"
    assert config.region == "us-central1"
    
    # Verify that use_local_credentials is not a valid parameter
    # This should raise TypeError if someone tries to use it
    with pytest.raises(TypeError):
        config = GCPConfig(
            project_id="test-project",
            region="us-central1",
            use_local_credentials=True  # This parameter was removed
        )


def test_async_iterator_import():
    """Test that AsyncIterator is properly imported in base_interfaces."""
    from test_framework.unified.base_interfaces import IHealthMonitor
    
    # Just verify the import doesn't fail
    assert IHealthMonitor is not None


@patch('google.cloud.logging.Client')
def test_log_reader_initialization(mock_client):
    """Test that GCPLogReader can be initialized without the enums module."""
    from test_framework.gcp_integration.log_reader import GCPLogReader
    from test_framework.gcp_integration.base import GCPConfig
    import asyncio
    
    config = GCPConfig(
        project_id="test-project",
        region="us-central1"
    )
    
    reader = GCPLogReader(config)
    
    # Run async initialization
    async def init():
        await reader.initialize()
    
    # Mock the credentials
    with patch('google.auth.default', return_value=(Mock(), "test-project")):
        asyncio.run(init())
    
    assert reader._client is not None


if __name__ == "__main__":
    # Run tests
    test_no_enums_import()
    print("[OK] test_no_enums_import passed")
    
    test_severity_handling_without_enums()
    print("[OK] test_severity_handling_without_enums passed")
    
    test_gcp_config_initialization()
    print("[OK] test_gcp_config_initialization passed")
    
    test_async_iterator_import()
    print("[OK] test_async_iterator_import passed")
    
    test_log_reader_initialization()
    print("[OK] test_log_reader_initialization passed")
    
    print("\nAll regression tests passed!")
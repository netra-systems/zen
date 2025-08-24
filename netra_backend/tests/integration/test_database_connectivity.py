"""Test database connectivity and initialization."""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

from unittest.mock import AsyncMock, MagicMock, Mock, patch, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

@pytest.mark.asyncio
async def test_database_connectivity_check_success():
    """Test successful database connectivity check."""
    from netra_backend.app.services.schema_validation_service import (
        SchemaValidationService,
    )
    
    # Create mock engine
    # Mock: Service component isolation for predictable testing behavior
    mock_engine = MagicMock(spec=AsyncEngine)
    # Mock: Generic component isolation for controlled unit testing
    mock_conn = AsyncMock()
    # Create a mock result where scalar() is NOT async (use MagicMock instead of AsyncMock)
    # Mock: Generic component isolation for controlled unit testing
    mock_result = MagicMock()
    mock_result.scalar.return_value = 1
    
    # Mock the execute method to return the mock_result when awaited
    # Mock: Async component isolation for testing without real async operations
    mock_conn.execute = AsyncMock(return_value=mock_result)
    
    # Mock the async context manager properly
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn
    mock_engine.connect.return_value.__aexit__.return_value = None
    
    # Test connectivity
    result = await SchemaValidationService.check_database_connectivity(mock_engine)
    assert result is True
    mock_conn.execute.assert_called_once()

@pytest.mark.asyncio
async def test_database_connectivity_check_failure():
    """Test failed database connectivity check."""
    from netra_backend.app.services.schema_validation_service import (
        SchemaValidationService,
    )
    
    # Create mock engine that raises exception
    # Mock: Service component isolation for predictable testing behavior
    mock_engine = MagicMock(spec=AsyncEngine)
    mock_engine.connect.side_effect = Exception("Connection failed")
    
    # Test connectivity
    result = await SchemaValidationService.check_database_connectivity(mock_engine)
    assert result is False

@pytest.mark.asyncio
async def test_database_connectivity_with_none_engine():
    """Test database connectivity check with None engine."""
    from netra_backend.app.services.schema_validation_service import (
        SchemaValidationService,
    )
    
    # Test with None engine should raise AttributeError
    with pytest.raises(AttributeError):
        await SchemaValidationService.check_database_connectivity(None)

@pytest.mark.asyncio
async def test_startup_schema_validation_with_uninitialized_engine():
    """Test schema validation in startup module with uninitialized engine."""
    import logging

    from netra_backend.app.startup_module import validate_schema
    
    logger = logging.getLogger(__name__)
    
    # Mock: Component isolation for testing without external dependencies
    with patch('app.startup_module.initialize_postgres') as mock_init:
        # Mock: Component isolation for testing without external dependencies
        with patch('app.startup_module.async_engine', None):
            # Should not raise error, just log warning
            await validate_schema(logger)
            mock_init.assert_called_once()

@pytest.mark.asyncio
async def test_comprehensive_validation_with_engine():
    """Test comprehensive validation with proper engine."""
    from netra_backend.app.services.schema_validation_service import (
        run_comprehensive_validation,
    )
    
    # Create mock engine
    # Mock: Service component isolation for predictable testing behavior
    mock_engine = MagicMock(spec=AsyncEngine)
    # Mock: Generic component isolation for controlled unit testing
    mock_conn = AsyncMock()
    # Create a mock result where scalar() is NOT async (use MagicMock instead of AsyncMock)
    # Mock: Generic component isolation for controlled unit testing
    mock_result = MagicMock()
    mock_result.scalar.return_value = 1
    
    # Mock the execute method to return the mock_result when awaited
    # Mock: Async component isolation for testing without real async operations
    mock_conn.execute = AsyncMock(return_value=mock_result)
    
    # Mock the async context manager properly
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn
    mock_engine.connect.return_value.__aexit__.return_value = None
    
    # Mock inspector for schema validation
    # Mock: Component isolation for testing without external dependencies
    with patch('netra_backend.app.services.schema_validation_service.inspect') as mock_inspect:
        # Mock: Generic component isolation for controlled unit testing
        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = []
        mock_inspect.return_value = mock_inspector
        # Mock: Async component isolation for testing without real async operations
        mock_conn.run_sync = AsyncMock(return_value={})
        
        # Run validation
        result = await run_comprehensive_validation(mock_engine)
        assert result is True
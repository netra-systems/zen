"""Test for postgres_events settings regression.

This test reproduces the critical issue where settings is not defined
in postgres_events.py, causing startup failures.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.pool import ConnectionPoolEntry


def test_postgres_events_settings_not_defined():
    """Test that postgres_events references undefined settings variable."""
    # This will fail with NameError: name 'settings' is not defined
    # when any of the event handlers are triggered
    
    from app.db import postgres_events
    
    # Create mock objects
    mock_engine = Mock(spec=AsyncEngine)
    mock_sync_engine = Mock()
    mock_engine.sync_engine = mock_sync_engine
    mock_pool = Mock()
    mock_pool.size.return_value = 10
    mock_pool.checkedin.return_value = 5
    mock_pool.overflow.return_value = 0
    mock_engine.pool = mock_pool
    
    # This should not raise an error during setup
    postgres_events.setup_async_engine_events(mock_engine)
    
    # But when the event is triggered, it will fail
    mock_dbapi_conn = Mock()
    mock_dbapi_conn.cursor.return_value.__enter__ = Mock(return_value=Mock())
    mock_dbapi_conn.cursor.return_value.__exit__ = Mock()
    mock_connection_record = Mock(spec=ConnectionPoolEntry)
    mock_connection_record.info = {}
    
    # Find the registered connect handler
    connect_handlers = mock_sync_engine.dispatch.connect._events
    
    # This will fail with NameError if settings is not defined
    with pytest.raises(NameError, match="name 'settings' is not defined"):
        # Trigger the connect event
        for handler in connect_handlers:
            handler.fn(mock_dbapi_conn, mock_connection_record)


def test_postgres_events_checkout_handler_settings_error():
    """Test checkout handler fails with undefined settings."""
    from app.db import postgres_events
    
    mock_engine = Mock(spec=AsyncEngine)
    mock_sync_engine = Mock()
    mock_engine.sync_engine = mock_sync_engine
    mock_pool = Mock()
    mock_pool.size.return_value = 10
    mock_pool.checkedin.return_value = 5
    mock_pool.overflow.return_value = 0
    mock_engine.pool = mock_pool
    
    postgres_events.setup_async_engine_events(mock_engine)
    
    mock_dbapi_conn = Mock()
    mock_connection_record = Mock(spec=ConnectionPoolEntry)
    mock_connection_record.info = {'pid': 123}
    mock_connection_proxy = Mock()
    
    # Find checkout handlers
    checkout_handlers = mock_sync_engine.dispatch.checkout._events
    
    with pytest.raises(NameError, match="name 'settings' is not defined"):
        for handler in checkout_handlers:
            handler.fn(mock_dbapi_conn, mock_connection_record, mock_connection_proxy)


@pytest.mark.asyncio
async def test_postgres_session_integration_with_events():
    """Test that postgres_session fails when postgres_events has undefined settings."""
    # Import postgres_core to trigger event setup
    with patch('netra_backend.app.db.postgres_core.async_session_factory') as mock_factory:
        mock_session = MagicMock()
        mock_factory.return_value.__aenter__ = MagicMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = MagicMock()
        
        from app.db.postgres_session import get_async_db
        
        # This should work if settings is properly initialized
        # But will fail if postgres_events triggers and settings is not defined
        try:
            async with get_async_db() as session:
                assert session is not None
        except NameError as e:
            # This is the bug we're testing for
            assert "settings" in str(e)
            pytest.fail(f"Settings not defined error occurred: {e}")


def test_all_settings_references_need_initialization():
    """Verify all places in postgres_events that reference settings."""
    import ast
    import inspect
    from app.db import postgres_events
    
    source = inspect.getsource(postgres_events)
    tree = ast.parse(source)
    
    # Find all references to 'settings'
    settings_refs = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == 'settings':
            # Get line number
            settings_refs.append(node.lineno)
    
    # We expect at least 5 references to settings (1 assignment + 4 usages)
    assert len(settings_refs) >= 5, f"Expected at least 5 references to 'settings', found {len(settings_refs)}"
    
    # Verify get_settings() is defined and called to initialize settings (THE FIX)
    assert 'def get_settings()' in source
    assert 'settings = get_settings()' in source  # This is the fix!
    
    # Verify settings is actually accessible
    assert hasattr(postgres_events, 'settings'), "Settings should be defined at module level"
    assert postgres_events.settings is not None, "Settings should be initialized"
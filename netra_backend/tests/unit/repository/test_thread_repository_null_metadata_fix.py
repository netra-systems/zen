"""Unit tests for ThreadRepository NULL metadata fix.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Prevent HTTP 500 errors from NULL metadata in thread creation
- Value Impact: Ensures system stability and prevents user-facing errors
- Strategic Impact: Critical for chat functionality reliability

CRITICAL: Tests the fix for NULL metadata handling in ThreadRepository.create().
This ensures that when metadata_=None is passed to thread creation, it gets
properly initialized to an empty dict instead of causing database failures.

Unit Level: Tests the repository layer directly with database mocking to ensure
the fix works at the data persistence level.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time

from netra_backend.app.services.database.thread_repository import ThreadRepository
from netra_backend.app.db.models_postgres import Thread


class TestThreadRepositoryNullMetadataFix:
    """Unit tests for NULL metadata handling fix in ThreadRepository."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.repository = ThreadRepository()
    
    @pytest.mark.asyncio
    async def test_create_thread_with_none_metadata_initializes_empty_dict(self):
        """Test that create method initializes None metadata to empty dict."""
        # Setup mock database session
        mock_db = AsyncMock()
        
        # Mock the parent create method to return a thread
        mock_thread = Thread(
            id="test_thread_123",
            object="thread", 
            created_at=int(time.time()),
            metadata_={}  # This simulates the result after our fix
        )
        
        # Mock the parent create method call
        with patch.object(self.repository.__class__.__bases__[0], 'create', new_callable=AsyncMock) as mock_parent_create:
            mock_parent_create.return_value = mock_thread
            
            # Call create with metadata_=None
            result = await self.repository.create(
                db=mock_db,
                id="test_thread_123",
                object="thread",
                created_at=int(time.time()),
                metadata_=None  # This is the key test case
            )
            
            # Verify the parent create was called with sanitized kwargs (metadata_ = {})
            mock_parent_create.assert_called_once()
            called_kwargs = mock_parent_create.call_args[1]
            assert called_kwargs['metadata_'] == {}  # Should be empty dict, not None
            
            # Verify the result
            assert result is not None
            assert result.metadata_ == {}
    
    @pytest.mark.asyncio 
    async def test_create_thread_with_existing_metadata_preserves_it(self):
        """Test that create method preserves existing metadata when not None."""
        # Setup mock database session
        mock_db = AsyncMock()
        
        # Test metadata
        test_metadata = {"user_id": "test_user", "status": "active"}
        
        # Mock the parent create method to return a thread with the metadata
        mock_thread = Thread(
            id="test_thread_123",
            object="thread",
            created_at=int(time.time()),
            metadata_=test_metadata
        )
        
        # Mock the parent create method call
        with patch.object(self.repository.__class__.__bases__[0], 'create', new_callable=AsyncMock) as mock_parent_create:
            mock_parent_create.return_value = mock_thread
            
            # Call create with valid metadata
            result = await self.repository.create(
                db=mock_db,
                id="test_thread_123", 
                object="thread",
                created_at=int(time.time()),
                metadata_=test_metadata
            )
            
            # Verify the parent create was called with original metadata
            mock_parent_create.assert_called_once()
            called_kwargs = mock_parent_create.call_args[1]
            assert called_kwargs['metadata_'] == test_metadata  # Should preserve original
            
            # Verify the result
            assert result is not None
            assert result.metadata_ == test_metadata
    
    @pytest.mark.asyncio
    async def test_create_thread_fixes_null_metadata_after_creation(self):
        """Test that create method fixes NULL metadata even after parent creation."""
        # Setup mock database session  
        mock_db = AsyncMock()
        
        # Create a thread that somehow still has NULL metadata after parent create
        mock_thread = Thread(
            id="test_thread_123",
            object="thread",
            created_at=int(time.time()),
            metadata_=None  # Simulates a case where parent create still returned NULL
        )
        
        # Mock the parent create method call
        with patch.object(self.repository.__class__.__bases__[0], 'create', new_callable=AsyncMock) as mock_parent_create:
            mock_parent_create.return_value = mock_thread
            
            # Call create with metadata_=None
            result = await self.repository.create(
                db=mock_db,
                id="test_thread_123",
                object="thread", 
                created_at=int(time.time()),
                metadata_=None
            )
            
            # Verify that db.flush() was called to persist the metadata fix
            mock_db.flush.assert_called_once()
            
            # Verify the thread metadata was fixed
            assert result.metadata_ == {}
    
    @pytest.mark.asyncio
    async def test_create_thread_with_missing_metadata_key(self):
        """Test that create method handles case where metadata_ key is missing entirely."""
        # Setup mock database session
        mock_db = AsyncMock()
        
        # Mock thread without metadata_ in constructor
        mock_thread = Thread(
            id="test_thread_123", 
            object="thread",
            created_at=int(time.time()),
            metadata_={}  # Will be set by our fix
        )
        
        # Mock the parent create method call
        with patch.object(self.repository.__class__.__bases__[0], 'create', new_callable=AsyncMock) as mock_parent_create:
            mock_parent_create.return_value = mock_thread
            
            # Call create without metadata_ key at all
            result = await self.repository.create(
                db=mock_db,
                id="test_thread_123",
                object="thread",
                created_at=int(time.time())
                # No metadata_ key provided
            )
            
            # Verify the parent create was called with metadata_ = {}
            mock_parent_create.assert_called_once()
            called_kwargs = mock_parent_create.call_args[1]
            assert called_kwargs['metadata_'] == {}  # Should be added as empty dict
            
            # Verify the result
            assert result is not None
            assert result.metadata_ == {}

    @pytest.mark.asyncio
    async def test_create_thread_error_handling_preserves_original_behavior(self):
        """Test that error handling in create method doesn't change original error behavior."""
        # Setup mock database session
        mock_db = AsyncMock()
        
        # Mock the parent create to raise an exception
        with patch.object(self.repository.__class__.__bases__[0], 'create', new_callable=AsyncMock) as mock_parent_create:
            mock_parent_create.side_effect = Exception("Database error")
            
            # Call create and expect the exception to be raised normally
            with pytest.raises(Exception, match="Database error"):
                await self.repository.create(
                    db=mock_db,
                    id="test_thread_123",
                    object="thread",
                    created_at=int(time.time()),
                    metadata_=None
                )
            
            # Verify the parent create was still called with sanitized kwargs
            mock_parent_create.assert_called_once()
            called_kwargs = mock_parent_create.call_args[1]
            assert called_kwargs['metadata_'] == {}  # Sanitization should happen before error
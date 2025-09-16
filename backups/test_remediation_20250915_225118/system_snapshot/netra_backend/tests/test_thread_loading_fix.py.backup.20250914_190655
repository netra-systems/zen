"""
Test suite for thread loading bug fixes.
Tests various scenarios for thread creation, loading, and user_id validation.
"""

import pytest
import time
import uuid
from fastapi import HTTPException
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.routes.utils.thread_validators import (
    validate_thread_access,
    validate_thread_exists,
    get_thread_with_validation
)
from netra_backend.app.routes.utils.thread_creators import (
    prepare_thread_metadata,
    generate_thread_id
)
from netra_backend.app.routes.utils.thread_handlers import (
    handle_create_thread_request,
    handle_get_thread_request,
    handle_get_messages_request,
    update_thread_metadata_fields
)


class TestThreadValidation:
    """Test thread validation with various user_id types."""
    
    def test_validate_thread_access_with_string_ids(self):
        """Test validation with string user IDs."""
        thread = thread_instance  # Initialize appropriate service
        thread.id = "thread_123"
        thread.metadata_ = {"user_id": "user_456"}
        
        # Should pass with matching strings
        validate_thread_access(thread, "user_456")
        
        # Should fail with non-matching strings
        with pytest.raises(HTTPException) as exc:
            validate_thread_access(thread, "user_789")
        assert exc.value.status_code == 403
    
    def test_validate_thread_access_with_integer_ids(self):
        """Test validation with integer user IDs that get normalized."""
        thread = thread_instance  # Initialize appropriate service
        thread.id = "thread_123"
        thread.metadata_ = {"user_id": 456}  # Integer in metadata
        
        # Should pass when normalized to string
        validate_thread_access(thread, "456")
        validate_thread_access(thread, 456)
    
    def test_validate_thread_access_with_uuid_ids(self):
        """Test validation with UUID user IDs."""
        user_uuid = uuid.uuid4()
        thread = thread_instance  # Initialize appropriate service
        thread.id = "thread_123"
        thread.metadata_ = {"user_id": str(user_uuid)}
        
        # Should pass with matching UUID as string
        validate_thread_access(thread, str(user_uuid))
        validate_thread_access(thread, user_uuid)  # UUID object should be converted
    
    def test_validate_thread_access_with_whitespace(self):
        """Test validation handles whitespace in IDs."""
        thread = thread_instance  # Initialize appropriate service
        thread.id = "thread_123"
        thread.metadata_ = {"user_id": "  user_456  "}
        
        # Should pass after stripping whitespace
        validate_thread_access(thread, "user_456")
        validate_thread_access(thread, "  user_456  ")
    
    def test_validate_thread_access_missing_metadata(self):
        """Test validation with missing metadata."""
        thread = thread_instance  # Initialize appropriate service
        thread.id = "thread_123"
        thread.metadata_ = None
        
        with pytest.raises(HTTPException) as exc:
            validate_thread_access(thread, "user_456")
        assert exc.value.status_code == 500
        assert "metadata is missing" in exc.value.detail
    
    def test_validate_thread_access_missing_user_id(self):
        """Test validation with missing user_id in metadata."""
        thread = thread_instance  # Initialize appropriate service
        thread.id = "thread_123"
        thread.metadata_ = {"title": "Test Thread"}  # No user_id
        
        with pytest.raises(HTTPException) as exc:
            validate_thread_access(thread, "user_456")
        assert exc.value.status_code == 500
        assert "no associated user" in exc.value.detail


class TestThreadCreation:
    """Test thread creation with consistent user_id handling."""
    
    def test_prepare_thread_metadata_string_user_id(self):
        """Test metadata preparation with string user ID."""
        thread_data = thread_data_instance  # Initialize appropriate service
        thread_data.metadata = None
        thread_data.title = "Test Thread"
        
        metadata = prepare_thread_metadata(thread_data, "user_123")
        
        assert metadata["user_id"] == "user_123"
        assert metadata["title"] == "Test Thread"
        assert metadata["status"] == "active"
        assert "created_at" in metadata
    
    def test_prepare_thread_metadata_integer_user_id(self):
        """Test metadata preparation with integer user ID."""
        thread_data = thread_data_instance  # Initialize appropriate service
        thread_data.metadata = None
        thread_data.title = None
        
        metadata = prepare_thread_metadata(thread_data, 123)
        
        assert metadata["user_id"] == "123"  # Normalized to string
        assert metadata["status"] == "active"
    
    def test_prepare_thread_metadata_uuid_user_id(self):
        """Test metadata preparation with UUID user ID."""
        thread_data = thread_data_instance  # Initialize appropriate service
        thread_data.metadata = {"custom": "value"}
        thread_data.title = None
        
        user_uuid = uuid.uuid4()
        metadata = prepare_thread_metadata(thread_data, user_uuid)
        
        assert metadata["user_id"] == str(user_uuid)  # Normalized to string
        assert metadata["custom"] == "value"  # Preserves existing metadata
    
    def test_prepare_thread_metadata_with_whitespace(self):
        """Test metadata preparation strips whitespace from user_id."""
        thread_data = thread_data_instance  # Initialize appropriate service
        thread_data.metadata = None
        thread_data.title = None
        
        metadata = prepare_thread_metadata(thread_data, "  user_123  ")
        
        assert metadata["user_id"] == "user_123"  # Whitespace stripped


class TestThreadUpdate:
    """Test thread update preserves user_id consistency."""
    
    @pytest.mark.asyncio
    async def test_update_thread_metadata_preserves_user_id(self):
        """Test that thread updates cannot change user_id."""
        thread = thread_instance  # Initialize appropriate service
        thread.id = "thread_123"
        thread.metadata_ = {"user_id": "original_user", "title": "Old Title"}
        
        thread_update = thread_update_instance  # Initialize appropriate service
        thread_update.title = "New Title"
        thread_update.metadata = {"user_id": "hacker_user", "custom": "value"}
        
        await update_thread_metadata_fields(thread, thread_update)
        
        # User ID should remain unchanged
        assert thread.metadata_["user_id"] == "original_user"
        # Title should be updated
        assert thread.metadata_["title"] == "New Title"
        # Custom field should be added
        assert thread.metadata_["custom"] == "value"
        # Updated timestamp should be added
        assert "updated_at" in thread.metadata_
    
    @pytest.mark.asyncio
    async def test_update_thread_metadata_normalizes_user_id(self):
        """Test that existing user_id gets normalized during update."""
        thread = thread_instance  # Initialize appropriate service
        thread.id = "thread_123"
        thread.metadata_ = {"user_id": 123}  # Integer user_id
        
        thread_update = thread_update_instance  # Initialize appropriate service
        thread_update.title = None
        thread_update.metadata = {"custom": "value"}
        
        await update_thread_metadata_fields(thread, thread_update)
        
        # User ID should be normalized to string
        assert thread.metadata_["user_id"] == "123"


class TestThreadHandlers:
    """Test thread request handlers with various scenarios."""
    
    @pytest.mark.asyncio
    async def test_handle_create_thread_request(self):
        """Test thread creation handler."""
        with patch('netra_backend.app.routes.utils.thread_handlers.create_thread_record') as mock_create:
            with patch('netra_backend.app.routes.utils.thread_handlers.build_thread_response') as mock_build:
                mock_thread = mock_thread_instance  # Initialize appropriate service
                mock_thread.id = "thread_123"
                mock_create.return_value = mock_thread
                mock_build.return_value = {"id": "thread_123", "object": "thread"}
                
                thread_data = thread_data_instance  # Initialize appropriate service
                thread_data.metadata = None
                thread_data.title = "Test Thread"
                
                db = AsyncNone  # TODO: Use real service instance
                result = await handle_create_thread_request(db, thread_data, "user_456")
                
                assert result["id"] == "thread_123"
                
                # Verify metadata was prepared correctly
                create_call = mock_create.call_args
                metadata = create_call[0][2]  # Third argument is metadata
                assert metadata["user_id"] == "user_456"
    
    @pytest.mark.asyncio
    async def test_handle_get_thread_request_with_validation(self):
        """Test thread retrieval with validation."""
        with patch('netra_backend.app.routes.utils.thread_handlers.get_thread_with_validation') as mock_validate:
            with patch('netra_backend.app.routes.utils.thread_handlers.MessageRepository') as mock_repo:
                with patch('netra_backend.app.routes.utils.thread_handlers.build_thread_response') as mock_build:
                    mock_thread = mock_thread_instance  # Initialize appropriate service
                    mock_thread.id = "thread_123"
                    mock_thread.metadata_ = {"user_id": "user_456"}
                    mock_validate.return_value = mock_thread
                    
                    mock_repo.return_value.count_by_thread = AsyncMock(return_value=5)
                    mock_build.return_value = {"id": "thread_123", "message_count": 5}
                    
                    db = AsyncNone  # TODO: Use real service instance
                    result = await handle_get_thread_request(db, "thread_123", "user_456")
                    
                    assert result["id"] == "thread_123"
                    assert result["message_count"] == 5
                    mock_validate.assert_called_once_with(db, "thread_123", "user_456")
    
    @pytest.mark.asyncio
    async def test_handle_get_messages_request_with_validation(self):
        """Test message retrieval with thread validation."""
        with patch('netra_backend.app.routes.utils.thread_handlers.get_thread_with_validation') as mock_validate:
            with patch('netra_backend.app.routes.utils.thread_handlers.build_thread_messages_response') as mock_build:
                mock_thread = mock_thread_instance  # Initialize appropriate service
                mock_thread.id = "thread_123"
                mock_validate.return_value = mock_thread
                
                mock_build.return_value = {
                    "thread_id": "thread_123",
                    "messages": [{"id": "msg_1", "content": "Hello"}],
                    "total": 1
                }
                
                db = AsyncNone  # TODO: Use real service instance
                result = await handle_get_messages_request(db, "thread_123", "user_456", 50, 0)
                
                assert result["thread_id"] == "thread_123"
                assert len(result["messages"]) == 1
                mock_validate.assert_called_once_with(db, "thread_123", "user_456")


class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_validate_thread_exists_with_none(self):
        """Test thread existence validation with None."""
        with pytest.raises(HTTPException) as exc:
            validate_thread_exists(None)
        assert exc.value.status_code == 404
    
    def test_generate_thread_id_format(self):
        """Test thread ID generation format."""
        thread_id = generate_thread_id()
        assert thread_id.startswith("thread_")
        assert len(thread_id) == 23  # "thread_" + 16 hex chars
    
    def test_validate_thread_access_with_special_characters(self):
        """Test validation with special characters in user_id."""
        thread = thread_instance  # Initialize appropriate service
        thread.id = "thread_123"
        thread.metadata_ = {"user_id": "user@domain.com"}
        
        validate_thread_access(thread, "user@domain.com")
        
        with pytest.raises(HTTPException) as exc:
            validate_thread_access(thread, "user@other.com")
        assert exc.value.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
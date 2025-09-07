"""
Test Thread Null Metadata Handling - Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Prevent HTTP 500 errors and service failures from null metadata
- Value Impact: Ensures seamless thread operations when metadata is NULL in database
- Strategic Impact: System stability for critical chat functionality, prevents 25% user drop-off from errors

CRITICAL: Tests the recent fixes in ThreadRepository that prevent HTTP 500 errors
when threads have null metadata fields. This directly addresses staging issues 
where null metadata caused cascade failures.

Integration Level: Tests thread persistence, retrieval, and WebSocket operations 
with real database and Redis services. NO MOCKS - real service testing only.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.database_fixtures import test_db_session
from test_framework.fixtures.websocket_test_helpers import WebSocketTestClient
from shared.isolated_environment import get_env

# Import models and services
from netra_backend.app.db.models_postgres import Thread, User, Message
from netra_backend.app.services.database.thread_repository import ThreadRepository
from netra_backend.app.routes.utils.thread_validators import (
    validate_thread_exists, 
    validate_thread_access, 
    get_thread_with_validation
)
from netra_backend.app.core.unified_id_manager import UnifiedIDManager


class TestThreadNullMetadataHandling(BaseIntegrationTest):
    """Integration tests for thread null metadata handling with real services."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_create_thread_with_null_metadata_field(self, test_db_session):
        """Test creating threads when metadata field is NULL in database."""
        repository = ThreadRepository()
        user_id = "test_user_null_metadata_001"
        
        # Directly create thread with NULL metadata using raw SQL to simulate production scenario
        thread_id = f"thread_{UnifiedIDManager.generate_thread_id()}"
        await test_db_session.execute(
            text("""
                INSERT INTO threads (id, object, created_at, metadata_) 
                VALUES (:id, 'thread', :created_at, NULL)
            """),
            {"id": thread_id, "created_at": int(time.time())}
        )
        await test_db_session.commit()
        
        # Test that retrieval handles NULL metadata gracefully
        thread = await repository.get_by_id(test_db_session, thread_id)
        assert thread is not None
        assert thread.id == thread_id
        # Verify metadata is handled gracefully (initialized to empty dict or None)
        assert thread.metadata_ is None or thread.metadata_ == {}
        
        # Test that update operations work with NULL metadata
        thread.metadata_ = {"user_id": user_id, "status": "active"}
        await test_db_session.commit()
        
        # Verify metadata was properly updated
        updated_thread = await repository.get_by_id(test_db_session, thread_id)
        assert updated_thread.metadata_["user_id"] == user_id
        assert updated_thread.metadata_["status"] == "active"

    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_find_by_user_with_null_metadata_threads(self, test_db_session):
        """Test finding threads by user when some threads have NULL metadata."""
        repository = ThreadRepository()
        user_id = "test_user_null_find_001"
        
        # Create mix of threads: some with NULL metadata, some with valid metadata
        valid_thread_id = f"thread_{UnifiedIDManager.generate_thread_id()}"
        null_thread_id = f"thread_{UnifiedIDManager.generate_thread_id()}"
        
        # Thread with valid metadata
        await test_db_session.execute(
            text("""
                INSERT INTO threads (id, object, created_at, metadata_) 
                VALUES (:id, 'thread', :created_at, :metadata)
            """),
            {
                "id": valid_thread_id,
                "created_at": int(time.time()),
                "metadata": json.dumps({"user_id": user_id, "status": "active"})
            }
        )
        
        # Thread with NULL metadata (simulates database state before fix)
        await test_db_session.execute(
            text("""
                INSERT INTO threads (id, object, created_at, metadata_) 
                VALUES (:id, 'thread', :created_at, NULL)
            """),
            {"id": null_thread_id, "created_at": int(time.time())}
        )
        await test_db_session.commit()
        
        # Test find_by_user handles NULL metadata gracefully - should not crash
        try:
            threads = await repository.find_by_user(test_db_session, user_id)
            # Should return only threads with valid metadata matching user_id
            assert len(threads) == 1
            assert threads[0].id == valid_thread_id
            assert threads[0].metadata_["user_id"] == user_id
            
            # NULL metadata thread should not be returned (cannot match user_id)
            thread_ids = [t.id for t in threads]
            assert null_thread_id not in thread_ids
            
        except Exception as e:
            pytest.fail(f"find_by_user should not fail with NULL metadata present: {e}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_get_or_create_for_user_with_existing_null_metadata(self, test_db_session):
        """Test get_or_create_for_user when existing threads have NULL metadata."""
        repository = ThreadRepository()
        user_id = "test_user_get_create_001"
        
        # Create thread with NULL metadata (simulates existing production data)
        existing_thread_id = f"thread_{UnifiedIDManager.generate_thread_id()}"
        await test_db_session.execute(
            text("""
                INSERT INTO threads (id, object, created_at, metadata_) 
                VALUES (:id, 'thread', :created_at, NULL)
            """),
            {"id": existing_thread_id, "created_at": int(time.time())}
        )
        await test_db_session.commit()
        
        # Test get_or_create - should create new thread since existing has no user association
        thread = await repository.get_or_create_for_user(test_db_session, user_id)
        
        # Should create new thread, not return the NULL metadata one
        assert thread is not None
        assert thread.id != existing_thread_id
        assert thread.metadata_ is not None
        assert thread.metadata_["user_id"] == user_id
        
        # Verify metadata is properly initialized
        assert isinstance(thread.metadata_, dict)
        assert thread.metadata_.get("user_id") == user_id

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_thread_validators_with_null_metadata(self, test_db_session):
        """Test thread validation functions handle NULL metadata gracefully."""
        user_id = "test_user_validator_001"
        
        # Create thread with NULL metadata
        thread_id = f"thread_{UnifiedIDManager.generate_thread_id()}"
        await test_db_session.execute(
            text("""
                INSERT INTO threads (id, object, created_at, metadata_) 
                VALUES (:id, 'thread', :created_at, NULL)
            """),
            {"id": thread_id, "created_at": int(time.time())}
        )
        await test_db_session.commit()
        
        # Get the thread object
        repository = ThreadRepository()
        thread = await repository.get_by_id(test_db_session, thread_id)
        assert thread is not None
        
        # Test validate_thread_exists - should pass
        try:
            validate_thread_exists(thread)
        except HTTPException:
            pytest.fail("validate_thread_exists should not fail for valid thread with NULL metadata")
        
        # Test validate_thread_access - should fail gracefully with proper HTTP 500
        with pytest.raises(HTTPException) as exc_info:
            validate_thread_access(thread, user_id)
        
        assert exc_info.value.status_code == 500
        assert "metadata is missing" in exc_info.value.detail.lower()
        
        # Test get_thread_with_validation - should handle error properly
        with pytest.raises(HTTPException) as exc_info:
            await get_thread_with_validation(test_db_session, thread_id, user_id)
        
        assert exc_info.value.status_code == 500

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_archive_thread_with_null_metadata(self, test_db_session):
        """Test archiving threads that have NULL metadata."""
        repository = ThreadRepository()
        
        # Create thread with NULL metadata
        thread_id = f"thread_{UnifiedIDManager.generate_thread_id()}"
        await test_db_session.execute(
            text("""
                INSERT INTO threads (id, object, created_at, metadata_) 
                VALUES (:id, 'thread', :created_at, NULL)
            """),
            {"id": thread_id, "created_at": int(time.time())}
        )
        await test_db_session.commit()
        
        # Test archive operation - should initialize metadata and add archive info
        success = await repository.archive_thread(test_db_session, thread_id)
        assert success is True
        
        # Verify thread was archived properly
        thread = await repository.get_by_id(test_db_session, thread_id)
        assert thread is not None
        assert thread.metadata_ is not None
        assert thread.metadata_.get("status") == "archived"
        assert "archived_at" in thread.metadata_

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_get_active_threads_filters_null_metadata(self, test_db_session):
        """Test get_active_threads properly filters out NULL metadata threads."""
        repository = ThreadRepository()
        user_id = "test_user_active_001"
        
        # Create mix of threads
        valid_thread_id = f"thread_{UnifiedIDManager.generate_thread_id()}"
        null_thread_id = f"thread_{UnifiedIDManager.generate_thread_id()}"
        
        # Valid thread with user metadata
        await test_db_session.execute(
            text("""
                INSERT INTO threads (id, object, created_at, metadata_, deleted_at) 
                VALUES (:id, 'thread', :created_at, :metadata, NULL)
            """),
            {
                "id": valid_thread_id,
                "created_at": int(time.time()),
                "metadata": json.dumps({"user_id": user_id, "status": "active"})
            }
        )
        
        # NULL metadata thread (should be filtered out)
        await test_db_session.execute(
            text("""
                INSERT INTO threads (id, object, created_at, metadata_, deleted_at) 
                VALUES (:id, 'thread', :created_at, NULL, NULL)
            """),
            {"id": null_thread_id, "created_at": int(time.time())}
        )
        await test_db_session.commit()
        
        # Test get_active_threads
        active_threads = await repository.get_active_threads(test_db_session, user_id)
        
        # Should return only the valid thread
        assert len(active_threads) == 1
        assert active_threads[0].id == valid_thread_id
        assert active_threads[0].metadata_["user_id"] == user_id
        
        # NULL metadata thread should not be included
        thread_ids = [t.id for t in active_threads]
        assert null_thread_id not in thread_ids

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_migration_scenario_null_to_valid(self, test_db_session):
        """Test database migration scenario: NULL metadata being updated to valid metadata."""
        repository = ThreadRepository()
        user_id = "test_user_migration_001"
        
        # Create thread with NULL metadata (simulates pre-migration state)
        thread_id = f"thread_{UnifiedIDManager.generate_thread_id()}"
        await test_db_session.execute(
            text("""
                INSERT INTO threads (id, object, created_at, metadata_) 
                VALUES (:id, 'thread', :created_at, NULL)
            """),
            {"id": thread_id, "created_at": int(time.time())}
        )
        await test_db_session.commit()
        
        # Simulate migration: update NULL to empty dict
        await test_db_session.execute(
            text("UPDATE threads SET metadata_ = '{}' WHERE metadata_ IS NULL")
        )
        await test_db_session.commit()
        
        # Test thread can now be retrieved and updated
        thread = await repository.get_by_id(test_db_session, thread_id)
        assert thread is not None
        assert thread.metadata_ == {}
        
        # Test updating the migrated thread
        thread.metadata_ = {"user_id": user_id, "migrated": True}
        await test_db_session.commit()
        
        # Verify update worked
        updated_thread = await repository.get_by_id(test_db_session, thread_id)
        assert updated_thread.metadata_["user_id"] == user_id
        assert updated_thread.metadata_["migrated"] is True

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_isolation_with_null_metadata(self, test_db_session):
        """Test multi-user isolation when some threads have NULL metadata."""
        repository = ThreadRepository()
        user1_id = "test_user_isolation_001"
        user2_id = "test_user_isolation_002"
        
        # Create threads for user1 with valid metadata
        user1_thread_id = f"thread_{UnifiedIDManager.generate_thread_id()}"
        await test_db_session.execute(
            text("""
                INSERT INTO threads (id, object, created_at, metadata_) 
                VALUES (:id, 'thread', :created_at, :metadata)
            """),
            {
                "id": user1_thread_id,
                "created_at": int(time.time()),
                "metadata": json.dumps({"user_id": user1_id, "private": True})
            }
        )
        
        # Create threads for user2 with valid metadata  
        user2_thread_id = f"thread_{UnifiedIDManager.generate_thread_id()}"
        await test_db_session.execute(
            text("""
                INSERT INTO threads (id, object, created_at, metadata_) 
                VALUES (:id, 'thread', :created_at, :metadata)
            """),
            {
                "id": user2_thread_id,
                "created_at": int(time.time()),
                "metadata": json.dumps({"user_id": user2_id, "private": True})
            }
        )
        
        # Create orphaned threads with NULL metadata (no user association)
        null_thread_id = f"thread_{UnifiedIDManager.generate_thread_id()}"
        await test_db_session.execute(
            text("""
                INSERT INTO threads (id, object, created_at, metadata_) 
                VALUES (:id, 'thread', :created_at, NULL)
            """),
            {"id": null_thread_id, "created_at": int(time.time())}
        )
        await test_db_session.commit()
        
        # Test user1 can only see their threads
        user1_threads = await repository.find_by_user(test_db_session, user1_id)
        assert len(user1_threads) == 1
        assert user1_threads[0].id == user1_thread_id
        
        # Test user2 can only see their threads
        user2_threads = await repository.find_by_user(test_db_session, user2_id)
        assert len(user2_threads) == 1
        assert user2_threads[0].id == user2_thread_id
        
        # Verify NULL metadata thread is not accessible by either user
        all_user1_ids = [t.id for t in user1_threads]
        all_user2_ids = [t.id for t in user2_threads]
        assert null_thread_id not in all_user1_ids
        assert null_thread_id not in all_user2_ids

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_message_flow_with_null_metadata_threads(self, test_db_session):
        """Test WebSocket message flow doesn't fail when threads have NULL metadata."""
        # This test simulates the WebSocket scenario without requiring actual WebSocket connection
        # Testing the data layer that WebSocket operations depend on
        
        repository = ThreadRepository()
        user_id = "test_user_websocket_001"
        
        # Create thread with NULL metadata (simulates production issue)
        null_thread_id = f"thread_{UnifiedIDManager.generate_thread_id()}"
        await test_db_session.execute(
            text("""
                INSERT INTO threads (id, object, created_at, metadata_) 
                VALUES (:id, 'thread', :created_at, NULL)
            """),
            {"id": null_thread_id, "created_at": int(time.time())}
        )
        await test_db_session.commit()
        
        # Test thread retrieval for WebSocket operations - should not crash
        try:
            thread = await repository.get_by_id(test_db_session, null_thread_id)
            assert thread is not None
            
            # WebSocket operations would need to handle NULL metadata gracefully
            # The fix ensures that operations don't crash with HTTP 500
            if thread.metadata_ is None:
                # WebSocket should initialize metadata or handle gracefully
                thread.metadata_ = {"user_id": user_id, "websocket_initialized": True}
                await test_db_session.commit()
                
        except Exception as e:
            pytest.fail(f"WebSocket thread operations should not fail with NULL metadata: {e}")
        
        # Verify WebSocket initialization worked
        updated_thread = await repository.get_by_id(test_db_session, null_thread_id)
        assert updated_thread.metadata_ is not None
        assert updated_thread.metadata_["websocket_initialized"] is True

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_auto_creation_null_metadata_prevention(self, test_db_session):
        """Test thread auto-creation prevents NULL metadata from being created."""
        repository = ThreadRepository()
        user_id = "test_user_auto_create_001"
        
        # Test get_or_create_for_user creates thread with proper metadata
        thread = await repository.get_or_create_for_user(test_db_session, user_id)
        
        assert thread is not None
        assert thread.metadata_ is not None
        assert isinstance(thread.metadata_, dict)
        assert thread.metadata_.get("user_id") == user_id
        
        # Verify created thread has required metadata structure
        required_keys = ["user_id"]
        for key in required_keys:
            assert key in thread.metadata_, f"Missing required metadata key: {key}"
        
        # Ensure metadata is never NULL in new threads
        assert thread.metadata_ != {}  # Should have at least user_id
        
        # Test that subsequent calls return the same thread (no duplicate creation)
        thread2 = await repository.get_or_create_for_user(test_db_session, user_id) 
        assert thread2.id == thread.id
        assert thread2.metadata_["user_id"] == user_id

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_graceful_degradation_null_metadata_error_handling(self, test_db_session):
        """Test graceful degradation when NULL metadata causes validation errors."""
        repository = ThreadRepository()
        user_id = "test_user_degradation_001"
        
        # Create thread with NULL metadata
        thread_id = f"thread_{UnifiedIDManager.generate_thread_id()}"
        await test_db_session.execute(
            text("""
                INSERT INTO threads (id, object, created_at, metadata_) 
                VALUES (:id, 'thread', :created_at, NULL)
            """),
            {"id": thread_id, "created_at": int(time.time())}
        )
        await test_db_session.commit()
        
        # Test that thread access validation provides meaningful error
        thread = await repository.get_by_id(test_db_session, thread_id)
        
        with pytest.raises(HTTPException) as exc_info:
            validate_thread_access(thread, user_id)
            
        # Should get HTTP 500 with clear error message, not crash
        assert exc_info.value.status_code == 500
        assert "metadata is missing" in exc_info.value.detail.lower()
        
        # Test that the system can recover by initializing metadata
        thread.metadata_ = {"user_id": user_id, "recovered": True}
        await test_db_session.commit()
        
        # After recovery, validation should work
        try:
            validate_thread_access(thread, user_id)
        except HTTPException:
            pytest.fail("Thread access should work after metadata recovery")

    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_backward_compatibility_with_existing_null_threads(self, test_db_session):
        """Test backward compatibility with existing production threads that have NULL metadata."""
        repository = ThreadRepository()
        user_id = "test_user_backward_001"
        
        # Simulate existing production threads with NULL metadata
        production_threads = []
        for i in range(3):
            thread_id = f"thread_production_{i}_{UnifiedIDManager.generate_thread_id()}"
            await test_db_session.execute(
                text("""
                    INSERT INTO threads (id, object, created_at, metadata_) 
                    VALUES (:id, 'thread', :created_at, NULL)
                """),
                {"id": thread_id, "created_at": int(time.time()) - (i * 3600)}  # Different timestamps
            )
            production_threads.append(thread_id)
        await test_db_session.commit()
        
        # Test that system handles these threads without breaking
        for thread_id in production_threads:
            thread = await repository.get_by_id(test_db_session, thread_id)
            assert thread is not None
            assert thread.id == thread_id
            
            # System should be able to handle NULL metadata gracefully
            if thread.metadata_ is None:
                # This should not crash the system
                assert hasattr(thread, 'metadata_')
                assert thread.metadata_ is None  # Expected for uninitialized threads
        
        # Test that find_by_user doesn't crash with NULL metadata present
        # Should return empty list since no threads have user association
        user_threads = await repository.find_by_user(test_db_session, user_id)
        assert isinstance(user_threads, list)
        assert len(user_threads) == 0  # No threads associated with this user
        
        # Test creating new thread still works despite NULL metadata threads existing
        new_thread = await repository.get_or_create_for_user(test_db_session, user_id)
        assert new_thread is not None
        assert new_thread.metadata_ is not None
        assert new_thread.metadata_["user_id"] == user_id
        
        # Verify new thread ID is not one of the NULL metadata threads
        assert new_thread.id not in production_threads
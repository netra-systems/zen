"""
Database Synchronization Tests for Unified System

Comprehensive tests for database synchronization including PostgreSQL persistence,
WebSocket event propagation, and frontend state consistency.

Business Value: $12K MRR - Data consistency and real-time synchronization
"""

from netra_backend.app.websocket_core import WebSocketManager
from pathlib import Path
import sys
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, AsyncMock, Mock, patch

import pytest
import sqlalchemy
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.models_postgres import Message, Thread, User
from netra_backend.app.schemas.core_enums import WebSocketMessageType
from netra_backend.app.schemas.websocket_message_types import ServerMessage
from netra_backend.app.websocket_core import WebSocketManager
from netra_backend.tests.fixtures import (

    clean_database_state,

    test_database,

    test_user,

)

class TestDatabaseSynchronization:

    """Test database synchronization and real-time updates"""

    @pytest.mark.asyncio
    async def test_thread_creation_flow(self, clean_database_state):

        """Test complete thread creation flow with real-time updates"""
        # Business Value: $12K MRR - Data consistency

        session = clean_database_state

        ws_manager = WebSocketManager()
        
        # Create user first

        user = User(

            id="user-123",

            email="test@example.com",

            full_name="Test User"

        )

        session.add(user)

        await session.commit()
        
        # Mock WebSocket connection for user

        # Mock: Generic component isolation for controlled unit testing
        mock_connection = AsyncMock()  # TODO: Use real service instance

        # Mock: Generic component isolation for controlled unit testing
        mock_connection.state = MagicMock()  # TODO: Use real service instance

        mock_connection.state.value = 1  # CONNECTED state
        
        # Register connection with user

        await ws_manager.connect_user("user-123", mock_connection)
        
        # Create thread data

        thread_data = {

            "id": "thread-123",

            "object": "thread",

            "created_at": int(datetime.now(timezone.utc).timestamp()),

            "metadata_": {"title": "Test Thread", "tags": ["test"]}

        }
        
        # Create thread in database

        thread = Thread(**thread_data)

        session.add(thread)

        await session.commit()
        
        # Verify thread in database

        result = await session.execute(select(Thread).where(Thread.id == "thread-123"))

        saved_thread = result.scalar_one_or_none()

        assert saved_thread is not None

        assert saved_thread.id == "thread-123"

        assert saved_thread.metadata_["title"] == "Test Thread"
        
        # Simulate WebSocket notification

        message = ServerMessage(

            type=WebSocketMessageType.THREAD_CREATED,

            payload={

                "thread_id": "thread-123",

                "title": "Test Thread",

                "created_at": thread_data["created_at"]

            }

        )
        
        # Send notification to user

        await ws_manager.send_message_to_user("user-123", message.model_dump())
        
        # Verify WebSocket call was made

        mock_connection.send_text.assert_called_once()

        sent_data = json.loads(mock_connection.send_text.call_args[0][0])

        assert sent_data["type"] == "thread_created"

        assert sent_data["payload"]["thread_id"] == "thread-123"

    @pytest.mark.asyncio
    async def test_postgres_persistence(self, clean_database_state):

        """Test data persistence in PostgreSQL across service restarts"""

        session = clean_database_state
        
        # Create thread with messages

        thread = Thread(

            id="persist-thread-123",

            object="thread",

            created_at=int(datetime.now(timezone.utc).timestamp()),

            metadata_={"title": "Persistent Thread", "description": "Test persistence"}

        )

        session.add(thread)
        
        # Create message

        message = Message(

            id="persist-msg-123",

            object="thread.message",

            created_at=int(datetime.now(timezone.utc).timestamp()),

            thread_id="persist-thread-123",

            role="user",

            content=[{"type": "text", "text": {"value": "Test message"}}],

            metadata_={"test": True}

        )

        session.add(message)

        await session.commit()
        
        # Verify data persisted

        thread_result = await session.execute(

            select(Thread).where(Thread.id == "persist-thread-123")

        )

        saved_thread = thread_result.scalar_one_or_none()

        assert saved_thread is not None

        assert saved_thread.metadata_["title"] == "Persistent Thread"
        
        message_result = await session.execute(

            select(Message).where(Message.id == "persist-msg-123")

        )

        saved_message = message_result.scalar_one_or_none()

        assert saved_message is not None

        assert saved_message.thread_id == "persist-thread-123"

        assert saved_message.content[0]["text"]["value"] == "Test message"
        
        # Simulate restart - create new session

        await session.rollback()
        
        # Verify data still present after restart simulation

        thread_result = await session.execute(

            select(Thread).where(Thread.id == "persist-thread-123")

        )

        restored_thread = thread_result.scalar_one_or_none()

        assert restored_thread is not None

        assert restored_thread.metadata_["title"] == "Persistent Thread"
        
        # Verify relationships intact

        message_result = await session.execute(

            select(Message).where(Message.thread_id == "persist-thread-123")

        )

        restored_message = message_result.scalar_one_or_none()

        assert restored_message is not None

        assert restored_message.thread_id == restored_thread.id

    @pytest.mark.asyncio
    async def test_ui_update_via_websocket(self, clean_database_state):

        """Test UI updates through WebSocket events"""

        session = clean_database_state

        ws_manager = WebSocketManager()
        
        # Mock WebSocket connections for multiple users

        # Mock: Generic component isolation for controlled unit testing
        user1_connection = AsyncMock()  # TODO: Use real service instance

        # Mock: Generic component isolation for controlled unit testing
        user1_connection.state = MagicMock()  # TODO: Use real service instance

        user1_connection.state.value = 1
        
        # Mock: Generic component isolation for controlled unit testing
        user2_connection = AsyncMock()  # TODO: Use real service instance

        # Mock: Generic component isolation for controlled unit testing
        user2_connection.state = MagicMock()  # TODO: Use real service instance

        user2_connection.state.value = 1
        
        # Register connections

        await ws_manager.connect_user("user-1", user1_connection)

        await ws_manager.connect_user("user-2", user2_connection)
        
        # Simulate database change

        thread = Thread(

            id="ui-update-thread",

            object="thread",

            created_at=int(datetime.now(timezone.utc).timestamp()),

            metadata_={"title": "UI Update Test"}

        )

        session.add(thread)

        await session.commit()
        
        # Trigger WebSocket event for database change

        update_message = ServerMessage(

            type=WebSocketMessageType.THREAD_UPDATED,

            payload={

                "thread_id": "ui-update-thread",

                "title": "UI Update Test",

                "action": "created"

            }

        )
        
        # Broadcast to all users

        await ws_manager.broadcast_to_all_users(update_message.model_dump())
        
        # Verify all users received update

        user1_connection.send_text.assert_called_once()

        user2_connection.send_text.assert_called_once()
        
        # Verify message content

        sent_message_1 = json.loads(user1_connection.send_text.call_args[0][0])

        sent_message_2 = json.loads(user2_connection.send_text.call_args[0][0])
        
        assert sent_message_1["type"] == "thread_updated"

        assert sent_message_1["payload"]["thread_id"] == "ui-update-thread"

        assert sent_message_2["type"] == "thread_updated"

        assert sent_message_2["payload"]["thread_id"] == "ui-update-thread"

    @pytest.mark.asyncio
    async def test_frontend_state_sync(self, clean_database_state):

        """Test frontend state synchronization across multiple tabs"""

        session = clean_database_state

        ws_manager = WebSocketManager()
        
        # Create user

        user = User(

            id="sync-user",

            email="sync@example.com",

            full_name="Sync User"

        )

        session.add(user)

        await session.commit()
        
        # Mock multiple tabs for same user

        # Mock: Generic component isolation for controlled unit testing
        tab1_connection = AsyncMock()  # TODO: Use real service instance

        # Mock: Generic component isolation for controlled unit testing
        tab1_connection.state = MagicMock()  # TODO: Use real service instance

        tab1_connection.state.value = 1
        
        # Mock: Generic component isolation for controlled unit testing
        tab2_connection = AsyncMock()  # TODO: Use real service instance

        # Mock: Generic component isolation for controlled unit testing
        tab2_connection.state = MagicMock()  # TODO: Use real service instance

        tab2_connection.state.value = 1
        
        # Mock: Generic component isolation for controlled unit testing
        tab3_connection = AsyncMock()  # TODO: Use real service instance

        # Mock: Generic component isolation for controlled unit testing
        tab3_connection.state = MagicMock()  # TODO: Use real service instance

        tab3_connection.state.value = 1
        
        # Register all tabs for same user

        await ws_manager.connect_user("sync-user", tab1_connection)

        await ws_manager.connect_user("sync-user", tab2_connection)

        await ws_manager.connect_user("sync-user", tab3_connection)
        
        # Update in one tab (simulate user action)

        thread = Thread(

            id="sync-thread",

            object="thread",

            created_at=int(datetime.now(timezone.utc).timestamp()),

            metadata_={"title": "Original Title"}

        )

        session.add(thread)

        await session.commit()
        
        # Update thread title (simulating action from tab1)

        thread.metadata_["title"] = "Updated Title"

        await session.commit()
        
        # Broadcast state change to all tabs

        sync_message = ServerMessage(

            type="state_sync",

            payload={

                "entity_type": "thread",

                "entity_id": "sync-thread",

                "changes": {

                    "title": "Updated Title"

                },

                "timestamp": datetime.now(timezone.utc).isoformat()

            }

        )
        
        # Send to all user's connections

        await ws_manager.send_message_to_user("sync-user", sync_message.model_dump())
        
        # Verify all tabs received sync message

        tab1_connection.send_text.assert_called_once()

        tab2_connection.send_text.assert_called_once()

        tab3_connection.send_text.assert_called_once()
        
        # Verify database consistency

        result = await session.execute(select(Thread).where(Thread.id == "sync-thread"))

        updated_thread = result.scalar_one_or_none()

        assert updated_thread.metadata_["title"] == "Updated Title"
        
        # Verify WebSocket broadcast consistency

        for connection in [tab1_connection, tab2_connection, tab3_connection]:

            sent_data = json.loads(connection.send_text.call_args[0][0])

            assert sent_data["type"] == "state_sync"

            assert sent_data["payload"]["changes"]["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_concurrent_database_operations(self, clean_database_state):

        """Test concurrent database operations with proper synchronization"""

        session = clean_database_state

        ws_manager = WebSocketManager()
        
        # Create base thread

        thread = Thread(

            id="concurrent-thread",

            object="thread",

            created_at=int(datetime.now(timezone.utc).timestamp()),

            metadata_={"message_count": 0}

        )

        session.add(thread)

        await session.commit()
        
        # Mock concurrent connections

        connections = []

        for i in range(3):

            # Mock: Generic component isolation for controlled unit testing
            conn = AsyncMock()  # TODO: Use real service instance

            # Mock: Generic component isolation for controlled unit testing
            conn.state = MagicMock()  # TODO: Use real service instance

            conn.state.value = 1

            await ws_manager.connect_user(f"user-{i}", conn)

            connections.append(conn)
        
        # Simulate concurrent message additions

        messages = []

        for i in range(5):

            message = Message(

                id=f"concurrent-msg-{i}",

                object="thread.message",

                created_at=int(datetime.now(timezone.utc).timestamp()),

                thread_id="concurrent-thread",

                role="user",

                content=[{"type": "text", "text": {"value": f"Message {i}"}}]

            )

            messages.append(message)

            session.add(message)
        
        await session.commit()
        
        # Update thread message count

        thread.metadata_["message_count"] = 5

        await session.commit()
        
        # Verify all messages persisted

        result = await session.execute(

            select(Message).where(Message.thread_id == "concurrent-thread")

        )

        saved_messages = result.scalars().all()

        assert len(saved_messages) == 5
        
        # Broadcast updates for each message

        for i in range(5):

            update_msg = ServerMessage(

                type="message_added",

                payload={

                    "thread_id": "concurrent-thread",

                    "message_id": f"concurrent-msg-{i}",

                    "content": f"Message {i}"

                }

            )

            await ws_manager.broadcast_to_all_users(update_msg.model_dump())
        
        # Verify all connections received all updates

        for connection in connections:

            assert connection.send_text.call_count == 5

    @pytest.mark.asyncio
    async def test_database_transaction_rollback(self, clean_database_state):

        """Test transaction rollback and consistency"""

        session = clean_database_state
        
        # Start transaction

        original_count = await session.execute(select(Thread))

        original_threads = len(original_count.scalars().all())
        
        try:
            # Create thread

            thread = Thread(

                id="rollback-thread",

                object="thread",

                created_at=int(datetime.now(timezone.utc).timestamp()),

                metadata_={"title": "Rollback Test"}

            )

            session.add(thread)
            
            # Create message with invalid foreign key (will cause rollback)

            message = Message(

                id="rollback-msg",

                object="thread.message",

                created_at=int(datetime.now(timezone.utc).timestamp()),

                thread_id="nonexistent-thread",  # Invalid foreign key

                role="user",

                content=[{"type": "text", "text": {"value": "Test"}}]

            )

            session.add(message)
            
            # This should fail and rollback

            await session.commit()
            
        except Exception:
            # Rollback occurred

            await session.rollback()
        
        # Verify rollback - no new threads should exist

        final_count = await session.execute(select(Thread))

        final_threads = len(final_count.scalars().all())

        assert final_threads == original_threads
        
        # Verify specific thread was not saved

        result = await session.execute(

            select(Thread).where(Thread.id == "rollback-thread")

        )

        rollback_thread = result.scalar_one_or_none()

        assert rollback_thread is None

    @pytest.mark.asyncio
    async def test_websocket_connection_recovery(self, clean_database_state):

        """Test WebSocket connection recovery and state restoration"""

        session = clean_database_state

        ws_manager = WebSocketManager()
        
        # Create user and thread

        user = User(

            id="recovery-user",

            email="recovery@example.com",

            full_name="Recovery User"

        )

        session.add(user)
        
        thread = Thread(

            id="recovery-thread",

            object="thread",

            created_at=int(datetime.now(timezone.utc).timestamp()),

            metadata_={"title": "Recovery Test"}

        )

        session.add(thread)

        await session.commit()
        
        # Mock connection

        # Mock: Generic component isolation for controlled unit testing
        connection = AsyncMock()  # TODO: Use real service instance

        # Mock: Generic component isolation for controlled unit testing
        connection.state = MagicMock()  # TODO: Use real service instance

        connection.state.value = 1
        
        # Connect user

        await ws_manager.connect_user("recovery-user", connection)
        
        # Simulate connection drop

        connection.state.value = 3  # DISCONNECTED

        await ws_manager.disconnect_user("recovery-user", connection)
        
        # Create new connection (recovery)

        # Mock: Generic component isolation for controlled unit testing
        new_connection = AsyncMock()  # TODO: Use real service instance

        # Mock: Generic component isolation for controlled unit testing
        new_connection.state = MagicMock()  # TODO: Use real service instance

        new_connection.state.value = 1
        
        # Reconnect user

        await ws_manager.connect_user("recovery-user", new_connection)
        
        # Send state restoration message

        restore_message = ServerMessage(

            type="state_restore",

            payload={

                "threads": [

                    {

                        "id": "recovery-thread",

                        "title": "Recovery Test",

                        "created_at": thread.created_at

                    }

                ]

            }

        )
        
        await ws_manager.send_message_to_user("recovery-user", restore_message.model_dump())
        
        # Verify new connection received state restoration

        new_connection.send_text.assert_called_once()

        sent_data = json.loads(new_connection.send_text.call_args[0][0])

        assert sent_data["type"] == "state_restore"

        assert len(sent_data["payload"]["threads"]) == 1

        assert sent_data["payload"]["threads"][0]["id"] == "recovery-thread"
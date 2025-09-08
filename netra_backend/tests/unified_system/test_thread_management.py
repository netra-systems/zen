"""
Thread Management Tests for Unified System

Comprehensive tests for thread lifecycle management including creation, updates,
concurrent operations, search, permissions, and access control.

Business Value: Data integrity and proper thread state management
"""

from netra_backend.app.websocket_core import WebSocketManager
from pathlib import Path
import sys
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pytest
import sqlalchemy
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.models_postgres import Message, Thread, User
from netra_backend.app.schemas.websocket_message_types import ServerMessage
from netra_backend.app.websocket_core import WebSocketManager
from netra_backend.tests.fixtures import (

    clean_database_state,

    test_database,

    test_user,

)

class TestThreadLifecycle:

    """Test complete thread lifecycle operations"""

    @pytest.mark.asyncio
    async def test_thread_lifecycle(self, clean_database_state):

        """Test complete thread lifecycle from creation to deletion"""

        session = clean_database_state
        
        # Create user

        user = User(

            id="lifecycle-user",

            email="lifecycle@example.com",

            full_name="Lifecycle User"

        )

        session.add(user)

        await session.commit()
        
        # 1. Create thread

        thread_data = {

            "id": "lifecycle-thread",

            "object": "thread",

            "created_at": int(datetime.now(timezone.utc).timestamp()),

            "metadata_": {

                "title": "Original Thread",

                "description": "Test lifecycle",

                "tags": ["test", "lifecycle"],

                "user_id": "lifecycle-user"

            }

        }
        
        thread = Thread(**thread_data)

        session.add(thread)

        await session.commit()
        
        # Verify creation

        result = await session.execute(select(Thread).where(Thread.id == "lifecycle-thread"))

        created_thread = result.scalar_one_or_none()

        assert created_thread is not None

        assert created_thread.metadata_["title"] == "Original Thread"
        
        # 2. Add messages

        messages_data = [

            {

                "id": "msg-1",

                "object": "thread.message",

                "created_at": int(datetime.now(timezone.utc).timestamp()),

                "thread_id": "lifecycle-thread",

                "role": "user",

                "content": [{"type": "text", "text": {"value": "First message"}}]

            },

            {

                "id": "msg-2",

                "object": "thread.message",

                "created_at": int(datetime.now(timezone.utc).timestamp()),

                "thread_id": "lifecycle-thread",

                "role": "assistant",

                "content": [{"type": "text", "text": {"value": "First response"}}]

            }

        ]
        
        for msg_data in messages_data:

            message = Message(**msg_data)

            session.add(message)

        await session.commit()
        
        # Verify messages added

        msg_result = await session.execute(

            select(Message).where(Message.thread_id == "lifecycle-thread")

        )

        messages = msg_result.scalars().all()

        assert len(messages) == 2
        
        # 3. Update thread title

        created_thread.metadata_["title"] = "Updated Thread Title"

        created_thread.metadata_["updated_at"] = datetime.now(timezone.utc).isoformat()

        await session.commit()
        
        # Verify update

        result = await session.execute(select(Thread).where(Thread.id == "lifecycle-thread"))

        updated_thread = result.scalar_one_or_none()

        assert updated_thread.metadata_["title"] == "Updated Thread Title"
        
        # 4. Archive thread (soft delete)

        created_thread.metadata_["archived"] = True

        created_thread.metadata_["archived_at"] = datetime.now(timezone.utc).isoformat()

        await session.commit()
        
        # Verify archival

        result = await session.execute(select(Thread).where(Thread.id == "lifecycle-thread"))

        archived_thread = result.scalar_one_or_none()

        assert archived_thread.metadata_["archived"] is True
        
        # 5. Delete thread (hard delete)
        # First delete messages manually

        messages_to_delete = await session.execute(

            select(Message).where(Message.thread_id == "lifecycle-thread")

        )

        for message in messages_to_delete.scalars().all():

            await session.delete(message)
        
        # Then delete thread

        await session.delete(archived_thread)

        await session.commit()
        
        # Verify deletion

        result = await session.execute(select(Thread).where(Thread.id == "lifecycle-thread"))

        deleted_thread = result.scalar_one_or_none()

        assert deleted_thread is None
        
        # Verify messages are deleted too

        msg_result = await session.execute(

            select(Message).where(Message.thread_id == "lifecycle-thread")

        )

        remaining_messages = msg_result.scalars().all()

        assert len(remaining_messages) == 0

    @pytest.mark.asyncio
    async def test_concurrent_thread_updates(self, clean_database_state):

        """Test concurrent modifications with optimistic locking"""

        session = clean_database_state

        ws_manager = WebSocketManager()
        
        # Create thread

        thread = Thread(

            id="concurrent-thread",

            object="thread",

            created_at=int(datetime.now(timezone.utc).timestamp()),

            metadata_={

                "title": "Concurrent Test",

                "message_count": 0,

                "last_activity": datetime.now(timezone.utc).isoformat(),

                "version": 1

            }

        )

        session.add(thread)

        await session.commit()
        
        # Mock multiple users

        user_connections = {}

        for i in range(3):

            # Mock: Generic component isolation for controlled unit testing
            conn = AsyncNone  # TODO: Use real service instance

            # Mock: Generic component isolation for controlled unit testing
            conn.state = MagicNone  # TODO: Use real service instance

            conn.state.value = 1

            user_id = f"user-{i}"

            await ws_manager.connect_user(user_id, conn)

            user_connections[user_id] = conn
        
        # Simulate concurrent message additions

        concurrent_messages = []
        
        async def add_message(user_id: str, message_num: int):

            """Add message concurrently"""

            message = Message(

                id=f"concurrent-msg-{user_id}-{message_num}",

                object="thread.message",

                created_at=int(datetime.now(timezone.utc).timestamp()),

                thread_id="concurrent-thread",

                role="user",

                content=[{"type": "text", "text": {"value": f"Message from {user_id} #{message_num}"}}],

                metadata_={"author": user_id}

            )

            session.add(message)

            return message
        
        # Add messages concurrently

        tasks = []

        for user_id in user_connections.keys():

            for msg_num in range(2):

                task = add_message(user_id, msg_num)

                tasks.append(task)
        
        # Execute concurrent additions

        messages = await asyncio.gather(*tasks)

        await session.commit()
        
        # Update thread metadata with proper versioning

        result = await session.execute(select(Thread).where(Thread.id == "concurrent-thread"))

        updated_thread = result.scalar_one_or_none()

        updated_thread.metadata_["message_count"] = len(messages)

        updated_thread.metadata_["last_activity"] = datetime.now(timezone.utc).isoformat()

        updated_thread.metadata_["version"] = updated_thread.metadata_["version"] + 1

        await session.commit()
        
        # Verify all messages saved

        msg_result = await session.execute(

            select(Message).where(Message.thread_id == "concurrent-thread")

        )

        saved_messages = msg_result.scalars().all()

        assert len(saved_messages) == 6  # 3 users × 2 messages
        
        # Verify proper ordering by creation time

        sorted_messages = sorted(saved_messages, key=lambda m: m.created_at)

        for i in range(len(sorted_messages) - 1):

            assert sorted_messages[i].created_at <= sorted_messages[i + 1].created_at
        
        # Broadcast updates to all users

        for message in saved_messages:

            update_msg = ServerMessage(

                type="message_added",

                payload={

                    "thread_id": "concurrent-thread",

                    "message_id": message.id,

                    "author": message.metadata_["author"],

                    "content": message.content[0]["text"]["value"]

                }

            )

            await ws_manager.broadcast_to_all_users(update_msg.model_dump())
        
        # Verify all users received all updates

        for connection in user_connections.values():

            assert connection.send_text.call_count == len(saved_messages)

    @pytest.mark.asyncio
    async def test_thread_search_and_filtering(self, clean_database_state):

        """Test thread search capabilities"""

        session = clean_database_state
        
        # Create user

        user = User(

            id="search-user",

            email="search@example.com", 

            full_name="Search User"

        )

        session.add(user)

        await session.commit()
        
        # Create multiple threads with different attributes

        threads_data = [

            {

                "id": "search-thread-1",

                "title": "Python Programming",

                "tags": ["python", "programming", "tutorial"],

                "created_at": datetime.now(timezone.utc) - timedelta(days=5),

                "activity_score": 10

            },

            {

                "id": "search-thread-2", 

                "title": "JavaScript Async",

                "tags": ["javascript", "async", "programming"],

                "created_at": datetime.now(timezone.utc) - timedelta(days=3),

                "activity_score": 15

            },

            {

                "id": "search-thread-3",

                "title": "Database Design",

                "tags": ["database", "sql", "design"],

                "created_at": datetime.now(timezone.utc) - timedelta(days=1),

                "activity_score": 8

            },

            {

                "id": "search-thread-4",

                "title": "Machine Learning",

                "tags": ["ml", "ai", "python"],

                "created_at": datetime.now(timezone.utc),

                "activity_score": 20

            }

        ]
        
        for thread_data in threads_data:

            thread = Thread(

                id=thread_data["id"],

                object="thread",

                created_at=int(thread_data["created_at"].timestamp()),

                metadata_={

                    "title": thread_data["title"],

                    "tags": thread_data["tags"],

                    "user_id": "search-user",

                    "activity_score": thread_data["activity_score"],

                    "created_date": thread_data["created_at"].isoformat()

                }

            )

            session.add(thread)

        await session.commit()
        
        # Test search by title

        title_search = await session.execute(

            select(Thread).where(

                func.lower(Thread.metadata_["title"].astext).contains("python")

            )

        )

        python_threads = title_search.scalars().all()

        assert len(python_threads) == 2  # "Python Programming" and "Machine Learning"
        
        # Test search by tags (using JSON contains)

        programming_search = await session.execute(

            select(Thread).where(

                Thread.metadata_["tags"].astext.contains("programming")

            )

        )

        programming_threads = programming_search.scalars().all()

        assert len(programming_threads) == 2
        
        # Test filter by date range (last 2 days)

        recent_date = datetime.now(timezone.utc) - timedelta(days=2)

        recent_search = await session.execute(

            select(Thread).where(

                Thread.created_at >= int(recent_date.timestamp())

            )

        )

        recent_threads = recent_search.scalars().all()

        assert len(recent_threads) == 2  # Last 2 threads
        
        # Test sort by activity score

        activity_search = await session.execute(

            select(Thread).order_by(

                Thread.metadata_["activity_score"].astext.cast(

                    sqlalchemy.Integer

                ).desc()

            )

        )

        sorted_threads = activity_search.scalars().all()

        scores = [int(t.metadata_["activity_score"]) for t in sorted_threads]

        assert scores == [20, 15, 10, 8]  # Descending order
        
        # Test pagination

        page_1 = await session.execute(

            select(Thread).limit(2).offset(0)

        )

        page_1_threads = page_1.scalars().all()

        assert len(page_1_threads) == 2
        
        page_2 = await session.execute(

            select(Thread).limit(2).offset(2)

        )

        page_2_threads = page_2.scalars().all()

        assert len(page_2_threads) == 2
        
        # Verify no overlap between pages

        page_1_ids = {t.id for t in page_1_threads}

        page_2_ids = {t.id for t in page_2_threads}

        assert page_1_ids.isdisjoint(page_2_ids)

    @pytest.mark.asyncio
    async def test_thread_permissions(self, clean_database_state):

        """Test thread access control and permissions"""

        session = clean_database_state
        
        # Create users with different roles

        owner_user = User(

            id="owner-user",

            email="owner@example.com",

            full_name="Owner User"

        )
        
        regular_user = User(

            id="regular-user", 

            email="regular@example.com",

            full_name="Regular User"

        )
        
        admin_user = User(

            id="admin-user",

            email="admin@example.com",

            full_name="Admin User"

        )
        
        session.add_all([owner_user, regular_user, admin_user])

        await session.commit()
        
        # Create thread owned by owner_user

        thread = Thread(

            id="permission-thread",

            object="thread",

            created_at=int(datetime.now(timezone.utc).timestamp()),

            metadata_={

                "title": "Permission Test Thread",

                "owner_id": "owner-user",

                "permissions": {

                    "read": ["owner-user"],

                    "write": ["owner-user"],

                    "delete": ["owner-user", "admin-user"]

                },

                "privacy": "private"

            }

        )

        session.add(thread)

        await session.commit()
        
        # Test owner can access

        owner_access = await session.execute(

            select(Thread).where(

                and_(

                    Thread.id == "permission-thread",

                    Thread.metadata_["owner_id"].astext == "owner-user"

                )

            )

        )

        owner_thread = owner_access.scalar_one_or_none()

        assert owner_thread is not None
        
        # Test regular user cannot access private thread

        regular_access = await session.execute(

            select(Thread).where(

                and_(

                    Thread.id == "permission-thread",

                    or_(

                        Thread.metadata_["privacy"].astext == "public",

                        Thread.metadata_["permissions"]["read"].astext.contains("regular-user")

                    )

                )

            )

        )

        regular_thread = regular_access.scalar_one_or_none()

        assert regular_thread is None
        
        # Test admin override - admin can delete

        admin_delete_access = await session.execute(

            select(Thread).where(

                and_(

                    Thread.id == "permission-thread",

                    Thread.metadata_["permissions"]["delete"].astext.contains("admin-user")

                )

            )

        )

        admin_thread = admin_delete_access.scalar_one_or_none()

        assert admin_thread is not None
        
        # Test sharing permissions - add regular user to read permissions

        thread.metadata_["permissions"]["read"].append("regular-user")

        await session.commit()
        
        # Now regular user can read

        shared_access = await session.execute(

            select(Thread).where(

                and_(

                    Thread.id == "permission-thread",

                    Thread.metadata_["permissions"]["read"].astext.contains("regular-user")

                )

            )

        )

        shared_thread = shared_access.scalar_one_or_none()

        assert shared_thread is not None
        
        # Create audit trail for permission changes

        audit_message = Message(

            id="audit-msg",

            object="system.audit",

            created_at=int(datetime.now(timezone.utc).timestamp()),

            thread_id="permission-thread",

            role="system",

            content=[{

                "type": "audit",

                "audit": {

                    "action": "permission_granted",

                    "user_id": "regular-user",

                    "permission": "read",

                    "granted_by": "owner-user",

                    "timestamp": datetime.now(timezone.utc).isoformat()

                }

            }]

        )

        session.add(audit_message)

        await session.commit()
        
        # Verify audit trail

        audit_result = await session.execute(

            select(Message).where(

                and_(

                    Message.thread_id == "permission-thread",

                    Message.role == "system"

                )

            )

        )

        audit_messages = audit_result.scalars().all()

        assert len(audit_messages) == 1

        assert audit_messages[0].content[0]["audit"]["action"] == "permission_granted"

    @pytest.mark.asyncio
    async def test_thread_metadata_updates(self, clean_database_state):

        """Test thread metadata updates and versioning"""

        session = clean_database_state
        
        # Create thread with initial metadata

        thread = Thread(

            id="metadata-thread",

            object="thread",

            created_at=int(datetime.now(timezone.utc).timestamp()),

            metadata_={

                "title": "Metadata Test",

                "description": "Testing metadata updates",

                "tags": ["test"],

                "version": 1,

                "last_modified": datetime.now(timezone.utc).isoformat(),

                "custom_fields": {

                    "priority": "medium",

                    "category": "development"

                }

            }

        )

        session.add(thread)

        await session.commit()
        
        # Update various metadata fields

        updates = [

            {"title": "Updated Metadata Test"},

            {"description": "Updated description"},

            {"tags": ["test", "updated", "metadata"]},

            {"custom_fields": {

                "priority": "high",

                "category": "development", 

                "status": "active"

            }}

        ]
        
        for update in updates:
            # Update metadata

            for key, value in update.items():

                thread.metadata_[key] = value
            
            # Increment version

            thread.metadata_["version"] = thread.metadata_["version"] + 1

            thread.metadata_["last_modified"] = datetime.now(timezone.utc).isoformat()
            
            await session.commit()
        
        # Verify final state

        result = await session.execute(select(Thread).where(Thread.id == "metadata-thread"))

        final_thread = result.scalar_one_or_none()
        
        assert final_thread.metadata_["title"] == "Updated Metadata Test"

        assert final_thread.metadata_["description"] == "Updated description"

        assert len(final_thread.metadata_["tags"]) == 3

        assert final_thread.metadata_["custom_fields"]["priority"] == "high"

        assert final_thread.metadata_["custom_fields"]["status"] == "active"

        assert final_thread.metadata_["version"] == 5  # Started at 1, 4 updates

    @pytest.mark.asyncio
    async def test_thread_recovery_and_restoration(self, clean_database_state):

        """Test thread recovery and soft delete restoration"""

        session = clean_database_state
        
        # Create thread

        thread = Thread(

            id="recovery-thread",

            object="thread", 

            created_at=int(datetime.now(timezone.utc).timestamp()),

            metadata_={

                "title": "Recovery Test",

                "deleted": False,

                "deleted_at": None,

                "deleted_by": None

            }

        )

        session.add(thread)

        await session.commit()
        
        # Add messages

        for i in range(3):

            message = Message(

                id=f"recovery-msg-{i}",

                object="thread.message",

                created_at=int(datetime.now(timezone.utc).timestamp()),

                thread_id="recovery-thread",

                role="user" if i % 2 == 0 else "assistant",

                content=[{"type": "text", "text": {"value": f"Message {i}"}}]

            )

            session.add(message)

        await session.commit()
        
        # Soft delete thread

        thread.metadata_["deleted"] = True

        thread.metadata_["deleted_at"] = datetime.now(timezone.utc).isoformat()

        thread.metadata_["deleted_by"] = "test-user"

        await session.commit()
        
        # Verify soft deletion

        active_result = await session.execute(

            select(Thread).where(

                and_(

                    Thread.id == "recovery-thread",

                    Thread.metadata_["deleted"].astext == "false"

                )

            )

        )

        active_thread = active_result.scalar_one_or_none()

        assert active_thread is None
        
        # Recovery: restore thread

        deleted_result = await session.execute(

            select(Thread).where(Thread.id == "recovery-thread")

        )

        deleted_thread = deleted_result.scalar_one_or_none()

        assert deleted_thread is not None
        
        # Restore thread

        deleted_thread.metadata_["deleted"] = False

        deleted_thread.metadata_["deleted_at"] = None

        deleted_thread.metadata_["deleted_by"] = None

        deleted_thread.metadata_["restored_at"] = datetime.now(timezone.utc).isoformat()

        deleted_thread.metadata_["restored_by"] = "admin-user"

        await session.commit()
        
        # Verify restoration

        restored_result = await session.execute(

            select(Thread).where(

                and_(

                    Thread.id == "recovery-thread",

                    Thread.metadata_["deleted"].astext == "false"

                )

            )

        )

        restored_thread = restored_result.scalar_one_or_none()

        assert restored_thread is not None

        assert restored_thread.metadata_["restored_by"] == "admin-user"
        
        # Verify messages are still intact

        msg_result = await session.execute(

            select(Message).where(Message.thread_id == "recovery-thread")

        )

        messages = msg_result.scalars().all()

        assert len(messages) == 3
"""Test message repository specific functionality.

MODULE PURPOSE:
Tests the message repository layer with comprehensive mocking to ensure
message-specific data access patterns work correctly.
"""

import sys
from pathlib import Path

import asyncio

import pytest

from netra_backend.tests.helpers.database_repository_helpers import (
    assert_pagination_result,
    create_test_message,
    create_test_messages,
    create_test_thread,
)

# Import fixtures from helpers
pytest_plugins = ["netra_backend.tests.helpers.database_repository_fixtures"]
class TestMessageRepository:
    """Test message repository specific functionality."""

    @pytest.mark.asyncio
    async def test_get_messages_by_thread(self, unit_of_work):
        """Test getting messages by thread ID."""
        async with unit_of_work as uow:
            thread = await create_test_thread(uow, "test_user", "Test Thread")
            await create_test_messages(uow, thread.id, count=5)
            
            messages = await uow.messages.get_by_thread(thread.id)
            
            assert len(messages) == 5
            assert all(m.thread_id == thread.id for m in messages)

    @pytest.mark.asyncio
    async def test_get_messages_with_pagination(self, unit_of_work):
        """Test paginated message retrieval."""
        async with unit_of_work as uow:
            thread = await create_test_thread(uow, "test_user", "Test Thread")
            
            # Create many messages
            for i in range(50):
                await create_test_message(uow, thread.id, f"Message {i}", "user")
            
            page = await uow.messages.get_by_thread_paginated(
                thread.id, page=2, page_size=10
            )
            
            assert_pagination_result(page, 10, 50)

    @pytest.mark.asyncio
    async def test_get_latest_messages(self, unit_of_work):
        """Test getting latest messages."""
        async with unit_of_work as uow:
            thread = await create_test_thread(uow, "test_user", "Test Thread")
            
            # Create messages with delays
            for i in range(10):
                await create_test_message(uow, thread.id, f"Message {i}", "user")
                await asyncio.sleep(0.01)
            
            latest = await uow.messages.get_latest(thread.id, limit=5)
            
            assert len(latest) == 5
            assert latest[0].content == "Message 9"
            assert latest[-1].content == "Message 5"
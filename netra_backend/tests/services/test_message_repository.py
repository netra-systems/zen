"""Test message repository specific functionality.

MODULE PURPOSE:
Tests the message repository layer with comprehensive mocking to ensure
message-specific data access patterns work correctly.
"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio

import pytest

# Add project root to path
from .database_repository_helpers import (
    assert_pagination_result,
    create_test_message,
    create_test_messages,
    # Add project root to path
    create_test_thread,
)

# Import fixtures from helpers
pytest_plugins = ["app.tests.helpers.database_repository_fixtures"]
class TestMessageRepository:
    """Test message repository specific functionality."""

    async def test_get_messages_by_thread(self, unit_of_work):
        """Test getting messages by thread ID."""
        async with unit_of_work as uow:
            thread = await create_test_thread(uow, "test_user", "Test Thread")
            await create_test_messages(uow, thread.id, count=5)
            
            messages = await uow.messages.get_by_thread(thread.id)
            
            assert len(messages) == 5
            assert all(m.thread_id == thread.id for m in messages)

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
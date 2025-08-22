"""
Message repository query tests
Tests message queries and pagination functionality
COMPLIANCE: 450-line max file, 25-line max functions
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.schemas.registry import Message, MessageType

from netra_backend.app.services.database.message_repository import MessageRepository

class TestMessageRepositoryQueries:
    """test_message_repository_queries - Test message queries and pagination"""
    
    async def test_message_pagination(self):
        """Test message pagination"""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = MessageRepository()
        
        # Create test messages
        messages = _create_test_messages(100)
        
        # Test pagination
        mock_session.execute.return_value.scalars.return_value.all.return_value = messages[:20]
        
        page1 = await repo.get_messages_paginated(
            mock_session, 
            thread_id="thread1",
            limit=20,
            offset=0
        )
        assert len(page1) == 20
        
        # Test with offset
        mock_session.execute.return_value.scalars.return_value.all.return_value = messages[20:40]
        
        page2 = await repo.get_messages_paginated(
            mock_session,
            thread_id="thread1", 
            limit=20,
            offset=20
        )
        assert len(page2) == 20
        assert page2[0].id == "msg20"
    
    async def test_complex_message_queries(self):
        """Test complex message queries"""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = MessageRepository()
        
        # Test search functionality
        _setup_search_mock(mock_session)
        
        results = await repo.search_messages(
            mock_session,
            query="Hello",
            thread_id="thread1"
        )
        assert len(results) == 2
        
        # Test date range queries
        start_date, end_date = _get_date_range()
        
        _setup_date_range_mock(mock_session)
        
        recent_messages = await repo.get_messages_by_date_range(
            mock_session,
            thread_id="thread1",
            start_date=start_date,
            end_date=end_date
        )
        assert len(recent_messages) == 1

def _create_test_messages(count):
    """Create test messages for pagination."""
    return [
        Message(id=f"msg{i}", content=f"Message {i}", type=MessageType.USER, thread_id="thread1")
        for i in range(count)
    ]

def _setup_search_mock(mock_session):
    """Setup search functionality mock."""
    mock_session.execute.return_value.scalars.return_value.all.return_value = [
        Message(id="1", content="Hello world", type=MessageType.USER),
        Message(id="2", content="Hello there", type=MessageType.USER)
    ]

def _get_date_range():
    """Get date range for testing."""
    start_date = datetime.now(timezone.utc) - timedelta(days=7)
    end_date = datetime.now(timezone.utc)
    return start_date, end_date

def _setup_date_range_mock(mock_session):
    """Setup date range query mock."""
    mock_session.execute.return_value.scalars.return_value.all.return_value = [
        Message(id="1", content="Test message", type=MessageType.USER, created_at=datetime.now(timezone.utc) - timedelta(days=1))
    ]
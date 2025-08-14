"""Tests for StartupChecker assistant checks."""

import pytest
from unittest.mock import Mock, AsyncMock

from app.startup_checks import StartupChecker
from app.tests.helpers.startup_check_helpers import (
    create_mock_app, create_mock_database_session, create_mock_assistant_query_result
)


class TestStartupCheckerAssistant:
    """Test StartupChecker assistant checks."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock app with required state."""
        return create_mock_app()
    
    @pytest.fixture
    def checker(self, mock_app):
        """Create a StartupChecker instance."""
        return StartupChecker(mock_app)
    
    @pytest.mark.asyncio
    async def test_check_or_create_assistant_exists(self, mock_app, checker):
        """Test assistant check when assistant already exists."""
        db_session = create_mock_database_session(mock_app)
        
        mock_assistant = Mock(id="netra-assistant")
        mock_result = create_mock_assistant_query_result(mock_assistant)
        db_session.execute = AsyncMock(return_value=mock_result)
        
        await checker.check_or_create_assistant()
        
        assert len(checker.results) == 1
        assert checker.results[0].success == True
        assert "already exists" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_or_create_assistant_create_new(self, mock_app, checker):
        """Test assistant check when creating new assistant."""
        db_session = create_mock_database_session(mock_app)
        
        mock_result = create_mock_assistant_query_result(None)
        db_session.execute = AsyncMock(return_value=mock_result)
        db_session.add = Mock()
        db_session.commit = AsyncMock()
        
        await checker.check_or_create_assistant()
        
        assert len(checker.results) == 1
        assert checker.results[0].success == True
        assert "created successfully" in checker.results[0].message
        
        # Verify assistant was added
        db_session.add.assert_called_once()
        db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_or_create_assistant_failure(self, mock_app, checker):
        """Test assistant check with database error."""
        db_session = create_mock_database_session(mock_app)
        db_session.execute = AsyncMock(side_effect=Exception("Database error"))
        
        await checker.check_or_create_assistant()
        
        assert len(checker.results) == 1
        assert checker.results[0].success == False
        assert "Database error" in checker.results[0].message
        assert checker.results[0].critical == False
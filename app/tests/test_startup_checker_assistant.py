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
        
        result = await checker.db_checker.check_or_create_assistant()
        
        assert result.success == True
        assert "already exists" in result.message
    
    @pytest.mark.asyncio
    async def test_check_or_create_assistant_create_new(self, mock_app, checker):
        """Test assistant check when creating new assistant."""
        db_session = create_mock_database_session(mock_app)
        
        mock_result = create_mock_assistant_query_result(None)
        db_session.execute = AsyncMock(return_value=mock_result)
        db_session.add = Mock()
        db_session.commit = AsyncMock()
        
        result = await checker.db_checker.check_or_create_assistant()
        
        assert result.success == True
        assert "created successfully" in result.message
        
        # Verify assistant was added
        db_session.add.assert_called_once()
        db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_or_create_assistant_failure(self, mock_app, checker):
        """Test assistant check with database error."""
        db_session = create_mock_database_session(mock_app)
        db_session.execute = AsyncMock(side_effect=Exception("Database error"))
        
        result = await checker.db_checker.check_or_create_assistant()
        
        assert result.success == False
        assert "Database error" in result.message
        assert result.critical == False
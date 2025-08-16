"""Tests for StartupChecker file permissions and database checks."""

import os
import pytest
from unittest.mock import patch, Mock
from pathlib import Path

from app.startup_checks import StartupChecker
from app.tests.helpers.startup_check_helpers import (
    create_mock_app, setup_temp_directory_test, verify_directories_created,
    create_mock_database_session, setup_successful_db_queries,
    setup_missing_table_db_queries
)


class TestStartupCheckerFileDb:
    """Test StartupChecker file permissions and database checks."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock app with required state."""
        return create_mock_app()
    
    @pytest.fixture
    def checker(self, mock_app):
        """Create a StartupChecker instance."""
        return StartupChecker(mock_app)
    async def test_check_file_permissions_success(self, checker):
        """Test file permissions check success."""
        tmpdir, original_cwd = setup_temp_directory_test()
        
        try:
            result = await checker.system_checker.check_file_permissions()
            
            assert result.success == True
            assert "accessible" in result.message
            verify_directories_created()
        finally:
            os.chdir(original_cwd)
            tmpdir.cleanup()
    async def test_check_file_permissions_failure(self, checker):
        """Test file permissions check with write permission failure."""
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            mock_mkdir.side_effect = PermissionError("No permission")
            
            result = await checker.system_checker.check_file_permissions()
            
            assert result.success == False
            assert "Permission issues" in result.message
    async def test_check_database_connection_success(self, mock_app, checker):
        """Test database connection check success."""
        db_session = create_mock_database_session(mock_app)
        setup_successful_db_queries(db_session)
        
        result = await checker.db_checker.check_database_connection()
        
        assert result.success == True
        assert "PostgreSQL connected" in result.message
    async def test_check_database_connection_missing_table(self, mock_app, checker):
        """Test database connection check with missing table."""
        db_session = create_mock_database_session(mock_app)
        setup_missing_table_db_queries(db_session)
        
        result = await checker.db_checker.check_database_connection()
        
        assert result.success == False
        assert "does not exist" in result.message
    async def test_check_database_connection_failure(self, mock_app, checker):
        """Test database connection check with connection failure."""
        db_session = create_mock_database_session(mock_app)
        db_session.execute = Mock(side_effect=Exception("Connection failed"))
        
        result = await checker.db_checker.check_database_connection()
        
        assert result.success == False
        assert "Connection failed" in result.message
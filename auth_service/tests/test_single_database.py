"""
Test to ensure auth service uses only ONE database connection
Prevents regression of duplicate database connection issue
"""
import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import importlib

# Add auth_service to path
sys.path.insert(0, str(Path(__file__).parent.parent))

@pytest.mark.asyncio
async def test_no_main_db_sync_module():
    """Test that main_db_sync module does not exist (removed duplicate)"""
    # Verify the duplicate module has been removed
    main_db_sync_path = Path(__file__).parent.parent / "auth_core" / "database" / "main_db_sync.py"
    assert not main_db_sync_path.exists(), f"Duplicate database module should not exist: {main_db_sync_path}"
    
    # Verify we cannot import it
    with pytest.raises(ImportError):
        from auth_service.auth_core.database import main_db_sync

@pytest.mark.asyncio
async def test_single_database_initialization():
    """Test that auth service initializes only one database connection"""
    from auth_service.auth_core.database.connection import auth_db
    
    # Mock the database initialization
    with patch.object(auth_db, 'initialize') as mock_init:
        mock_init.return_value = None
        
        # Import main after patching to test startup
        with patch('auth_core.database.connection.auth_db.initialize', mock_init):
            # Set environment to staging to test real initialization
            os.environ['AUTH_FAST_TEST_MODE'] = 'false'
            os.environ['ENVIRONMENT'] = 'staging'
            
            # Import main module
            from main import lifespan
            from fastapi import FastAPI
            
            app = FastAPI()
            
            # Run lifespan context (should succeed with mocked init)
            try:
                async with lifespan(app):
                    pass
            except RuntimeError:
                # Expected if initialization fails, but we're testing the count
                pass
            
            # Verify only one database initialization was attempted
            assert mock_init.call_count == 1, "Database should be initialized exactly once"

@pytest.mark.asyncio  
async def test_auth_routes_no_duplicate_sync():
    """Test that auth routes don't attempt to sync to a separate database"""
    from auth_service.auth_core.routes.auth_routes import _sync_user_to_main_db
    
    # Create a mock user
    mock_user = MagicMock()
    mock_user.id = "test-user-123"
    
    # Call the sync function
    result = await _sync_user_to_main_db(mock_user)
    
    # Should just return the user ID without any database sync
    assert result == "test-user-123", "Should return user ID without separate database sync"
    
    # Test with None user
    result = await _sync_user_to_main_db(None)
    assert result is None, "Should return None for None user"

@pytest.mark.asyncio
async def test_database_url_configuration():
    """Test that auth service uses DATABASE_URL from environment"""
    from auth_service.auth_core.config import AuthConfig
    
    # Set a test database URL
    test_db_url = "postgresql://test:test@localhost:5432/test_db"
    os.environ['DATABASE_URL'] = test_db_url
    
    # Get database URL from config
    db_url = AuthConfig.get_database_url()
    
    assert db_url == test_db_url, "Should use DATABASE_URL from environment"
    
    # Clean up
    del os.environ['DATABASE_URL']
    
    # Test without DATABASE_URL
    db_url = AuthConfig.get_database_url()
    assert db_url == "", "Should return empty string when DATABASE_URL not set"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
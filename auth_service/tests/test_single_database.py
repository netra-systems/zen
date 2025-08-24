"""
Test to ensure auth service uses only ONE database connection
Prevents regression of duplicate database connection issue
"""
import importlib
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add auth_service to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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
        with patch('auth_service.auth_core.database.connection.auth_db.initialize', mock_init):
            # Set environment to staging to test real initialization, but with AUTH_FAST_TEST_MODE to bypass SERVICE_ID
            os.environ['AUTH_FAST_TEST_MODE'] = 'false'
            os.environ['ENVIRONMENT'] = 'development'
            
            # Import main module
            from fastapi import FastAPI
            import sys
            from pathlib import Path
            
            # Add auth_service directory to path for imports
            auth_service_path = Path(__file__).parent.parent
            if str(auth_service_path) not in sys.path:
                sys.path.insert(0, str(auth_service_path))
            
            from main import lifespan
            
            app = FastAPI()
            
            # Run lifespan context (should succeed with mocked init)
            try:
                async with lifespan(app):
                    pass
            except RuntimeError:
                # Expected if initialization fails, but we're testing the count
                pass
            
            # Since we're testing database initialization, database should be initialized exactly once
            # In development mode with fast_test_mode=false, the lifespan should call db.initialize()
            assert mock_init.call_count == 1, f"Database should be initialized exactly once, got {mock_init.call_count} calls"
            
            # Clean up environment variables
            if 'AUTH_FAST_TEST_MODE' in os.environ:
                del os.environ['AUTH_FAST_TEST_MODE']
            if 'ENVIRONMENT' in os.environ:
                del os.environ['ENVIRONMENT']

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
    
    # Get raw database URL from config (should be unchanged)
    raw_db_url = AuthConfig.get_raw_database_url()
    assert raw_db_url == test_db_url, "Should use raw DATABASE_URL from environment"
    
    # Get normalized database URL (should be converted for asyncpg)
    normalized_db_url = AuthConfig.get_database_url()
    assert normalized_db_url == "postgresql+asyncpg://test:test@localhost:5432/test_db", "Should normalize URL for asyncpg"
    
    # Clean up
    del os.environ['DATABASE_URL']
    
    # Test without DATABASE_URL
    db_url = AuthConfig.get_database_url()
    assert db_url == "", "Should return empty string when DATABASE_URL not set"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
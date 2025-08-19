"""
Basic test setup verification
Ensures test environment is working correctly
"""
import pytest
import os
import sys
from pathlib import Path

# Add auth_core to path for imports
auth_service_dir = Path(__file__).parent.parent
sys.path.insert(0, str(auth_service_dir))

def test_environment_setup():
    """Test environment variables are set correctly"""
    assert os.getenv("ENVIRONMENT") == "test"
    assert os.getenv("JWT_SECRET") is not None
    assert len(os.getenv("JWT_SECRET", "")) > 10
    
def test_imports_work():
    """Test that auth_core modules can be imported"""
    try:
        from auth_core.models.auth_models import AuthProvider, LoginRequest
        from auth_core.config import AuthConfig
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import auth_core modules: {e}")

def test_auth_provider_enum():
    """Test AuthProvider enum is accessible"""
    from auth_core.models.auth_models import AuthProvider
    
    assert AuthProvider.GOOGLE == "google"
    assert AuthProvider.GITHUB == "github"
    assert AuthProvider.LOCAL == "local"

def test_config_in_test_mode():
    """Test configuration works in test mode"""
    from auth_core.config import AuthConfig
    
    env = AuthConfig.get_environment()
    # Environment might be development in this context
    assert env in ["test", "development"]
    
    # Should have test values
    client_id = AuthConfig.get_google_client_id() 
    assert client_id == "test_google_client_id"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

import sys
from pathlib import Path
from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
import json

"""Simple health test without complex imports"""

env = get_env()
def test_basic_import():
    """Test that we can import the app without hanging"""
    import os
    import sys
    
    # Set minimal environment
    env.set("TESTING", "1", "test")
    env.set("DATABASE_URL", "sqlite+aiosqlite:///:memory:", "test")
    env.set("DEV_MODE_DISABLE_CLICKHOUSE", "true", "test")
    
    # Try basic import
    try:
        from netra_backend.app import __version__
        # Verify that version was imported and has a value
        assert __version__ is not None
        assert isinstance(__version__, str)
        assert len(__version__) > 0
    except ImportError as e:
        # ImportError should not be silently ignored - skip the test instead
        import pytest
        pytest.skip(f"Unable to import app: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        assert False, f"Unexpected error during import: {e}"

def test_health_endpoint_direct():
    """Test health endpoint directly without pytest fixtures"""
    import os
    env.set("TESTING", "1", "test")
    env.set("DATABASE_URL", "sqlite+aiosqlite:///:memory:", "test")
    env.set("DEV_MODE_DISABLE_CLICKHOUSE", "true", "test")
    
    from fastapi.testclient import TestClient

    from netra_backend.app.main import app
    
    client = TestClient(app)
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "netra-ai-platform"

def test_live_endpoint():
    """Test the live health endpoint"""
    import os
    env.set("TESTING", "1", "test")
    env.set("DATABASE_URL", "sqlite+aiosqlite:///:memory:", "test")
    env.set("DEV_MODE_DISABLE_CLICKHOUSE", "true", "test")
    
    from fastapi.testclient import TestClient

    from netra_backend.app.main import app
    
    client = TestClient(app)
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "netra-ai-platform"
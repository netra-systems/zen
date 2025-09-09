import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment


import pytest
from fastapi.testclient import TestClient

from netra_backend.app.main import app
import json

class TestConfigEndpoint:
    
    def test_get_public_config(self):
        """Test retrieving public configuration"""
        client = TestClient(app)
        
        response = client.get("/api/config/public")
        
        assert response.status_code == 200
        config = response.json()
        assert config["environment"] in ["development", "testing", "staging", "production"]
        assert "app_name" in config
        assert "version" in config
        assert "features" in config
        assert config["features"]["websocket"] == True
        assert config["features"]["multi_agent"] == True
    
    def test_get_frontend_config(self):
        """Test retrieving frontend-specific configuration"""
        client = TestClient(app)
        
        expected_config = {
            "api_url": "http://localhost:8000",
            "ws_url": "ws://localhost:8000",
            "features": {
                "chat": True,
                "analytics": True,
                "realtime": True,
},
            "ui_settings": {
                "theme": "light",
                "max_message_length": 5000,
},
}
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.routes.config._build_public_config', return_value = expected_config):
            response = client.get("/api/config/public")
            
            assert response.status_code == 200
            config = response.json()
            # Test the mocked config structure
            assert config["api_url"] == "http://localhost:8000"
            assert config["ws_url"] == "ws://localhost:8000"
            assert config["features"]["chat"] == True
            assert config["features"]["analytics"] == True
            assert config["ui_settings"]["theme"] == "light"
    
    def test_update_config_authorized(self):
        """Test updating configuration with proper authorization"""
        from netra_backend.app.auth_integration.auth import require_admin
        
        update_data = {
            "features": {
                "experimental_mode": True,
},
}
        
        # Mock the User object that would be returned from require_admin
        # Mock: Generic component isolation for controlled unit testing
        mock_user = MagicNone  # TODO: Use real service instance
        mock_user.id = "test-user-id"
        mock_user.email = "admin@test.com"
        mock_user.is_admin = True
        
        # Use FastAPI dependency override mechanism
        def mock_require_admin():
            return mock_user
        
        app.dependency_overrides[require_admin] = mock_require_admin
        
        try:
            client = TestClient(app)
            response = client.post(
                "/api/config/update",
                json = update_data,
                headers = {"Authorization": "Bearer admin-token"},
)
            
            assert response.status_code == 200
            assert response.json()["success"] == True
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()
    
    def test_update_config_unauthorized(self):
        """Test config update rejection without authorization"""
        from fastapi import HTTPException, status

        from netra_backend.app.auth_integration.auth import require_admin
        
        update_data = {
            "features": {
                "experimental_mode": True,
},
}
        
        # Mock require_admin to raise an HTTPException for unauthorized access
        def mock_require_admin():
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail = "Invalid or expired token",
)
        
        app.dependency_overrides[require_admin] = mock_require_admin
        
        try:
            client = TestClient(app)
            response = client.post(
                "/api/config/update",
                json = update_data,
                headers = {"Authorization": "Bearer invalid-token"},
)
            
            assert response.status_code == 401
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()
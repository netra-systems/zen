import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

class TestConfigEndpoint:
    
    def test_get_public_config(self):
        """Test retrieving public configuration"""
        client = TestClient(app)
        
        with patch('app.config.settings') as mock_settings:
            mock_settings.environment = "development"
            mock_settings.app_name = "Netra AI"
            mock_settings.version = "2.0.0"
            mock_settings.features = {
                "websocket": True,
                "multi_agent": True
            }
            
            response = client.get("/api/config/public")
            
            assert response.status_code == 200
            config = response.json()
            assert config["environment"] == "development"
            assert config["app_name"] == "Netra AI"
            assert config["features"]["websocket"] is True
    
    def test_get_frontend_config(self):
        """Test retrieving frontend-specific configuration"""
        client = TestClient(app)
        
        expected_config = {
            "api_url": "http://localhost:8000",
            "ws_url": "ws://localhost:8000",
            "features": {
                "chat": True,
                "analytics": True,
                "realtime": True
            },
            "ui_settings": {
                "theme": "light",
                "max_message_length": 5000
            }
        }
        
        with patch('app.routes.config.get_frontend_config', return_value=expected_config):
            response = client.get("/api/config/frontend")
            
            assert response.status_code == 200
            config = response.json()
            assert config["api_url"] == "http://localhost:8000"
            assert config["features"]["chat"] is True
    
    def test_update_config_authorized(self):
        """Test updating configuration with proper authorization"""
        client = TestClient(app)
        
        update_data = {
            "features": {
                "experimental_mode": True
            }
        }
        
        with patch('app.routes.config.verify_admin_token', return_value=True):
            with patch('app.routes.config.update_config') as mock_update:
                mock_update.return_value = {"success": True, "updated": update_data}
                
                response = client.post(
                    "/api/config/update",
                    json=update_data,
                    headers={"Authorization": "Bearer admin-token"}
                )
                
                assert response.status_code == 200
                assert response.json()["success"] is True
    
    def test_update_config_unauthorized(self):
        """Test config update rejection without authorization"""
        client = TestClient(app)
        
        update_data = {
            "features": {
                "experimental_mode": True
            }
        }
        
        with patch('app.routes.config.verify_admin_token', return_value=False):
            response = client.post(
                "/api/config/update",
                json=update_data,
                headers={"Authorization": "Bearer invalid-token"}
            )
            
            assert response.status_code == 403
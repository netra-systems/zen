import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from app.main import app

class TestHealthEndpoints:
    
    def test_liveness_check(self):
        """Test /health/live endpoint returns correct status"""
        client = TestClient(app)
        response = client.get("/health/live")
        
        assert response.status_code == 200
        assert response.json()["status"] == "alive"
        assert "timestamp" in response.json()
    
    def test_readiness_check_success(self):
        """Test /health/ready endpoint when all services are ready"""
        client = TestClient(app)
        
        with patch('app.routes.health.async_engine') as mock_engine:
            mock_conn = AsyncMock()
            mock_engine.connect = AsyncMock(return_value=mock_conn)
            mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_conn.__aexit__ = AsyncMock()
            mock_conn.execute = AsyncMock()
            
            response = client.get("/health/ready")
            
            assert response.status_code == 200
            assert response.json()["status"] == "ready"
            assert "postgres" in response.json()["services"]
    
    def test_readiness_check_failure(self):
        """Test /health/ready endpoint when database is unavailable"""
        client = TestClient(app)
        
        with patch('app.routes.health.async_engine') as mock_engine:
            mock_engine.connect = AsyncMock(side_effect=Exception("Database connection failed"))
            
            response = client.get("/health/ready")
            
            assert response.status_code == 503
            assert response.json()["status"] == "not_ready"
            assert "error" in response.json()
    
    def test_database_environment_endpoint(self):
        """Test /health/database-environment endpoint"""
        client = TestClient(app)
        
        with patch('app.routes.health.DatabaseEnvironmentValidator') as mock_validator:
            mock_validator.get_environment_info.return_value = {
                "environment": "development",
                "database_url": "postgresql://...",
                "debug": True
            }
            mock_validator.validate_database_url.return_value = {
                "is_valid": True,
                "errors": [],
                "warnings": []
            }
            mock_validator.get_safe_database_name.return_value = "dev_db"
            
            response = client.get("/health/database-environment")
            
            assert response.status_code == 200
            assert response.json()["environment"] == "development"
            assert response.json()["validation"]["is_valid"] is True
    
    def test_schema_validation_endpoint(self):
        """Test /health/schema-validation endpoint"""
        client = TestClient(app)
        
        with patch('app.routes.health.SchemaValidationService') as mock_validator:
            mock_instance = MagicMock()
            mock_validator.return_value = mock_instance
            mock_instance.validate_all_schemas = AsyncMock(return_value={
                "is_valid": True,
                "tables_validated": 10,
                "errors": []
            })
            
            response = client.get("/health/schema-validation")
            
            assert response.status_code == 200
            assert response.json()["is_valid"] is True
            assert response.json()["tables_validated"] == 10
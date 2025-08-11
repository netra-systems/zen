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
        assert response.json()["status"] == "ok"
    
    def test_readiness_check_success(self):
        """Test /health/ready endpoint when all services are ready"""
        client = TestClient(app)
        
        with patch('app.routes.health.get_db') as mock_get_db, \
             patch('app.db.clickhouse.get_clickhouse_client') as mock_get_clickhouse:
            
            # Mock database session
            mock_db = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none = AsyncMock(return_value=1)
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_get_db.return_value.__aexit__ = AsyncMock()
            
            # Mock ClickHouse client
            mock_ch_client = MagicMock()
            mock_ch_client.ping = MagicMock(return_value=True)
            mock_get_clickhouse.return_value.__aenter__ = AsyncMock(return_value=mock_ch_client)
            mock_get_clickhouse.return_value.__aexit__ = AsyncMock()
            
            response = client.get("/health/ready")
            
            assert response.status_code == 200
            assert response.json()["status"] == "ok"
    
    def test_readiness_check_failure(self):
        """Test /health/ready endpoint when database is unavailable"""
        client = TestClient(app)
        
        with patch('app.routes.health.get_db') as mock_get_db:
            mock_get_db.side_effect = Exception("Database connection failed")
            
            response = client.get("/health/ready")
            
            assert response.status_code == 503
            assert response.json()["message"] == "Service Unavailable"
    
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
                "valid": True,
                "errors": [],
                "warnings": [],
                "database_name": "dev_db"
            }
            mock_validator.get_safe_database_name.return_value = "dev_db"
            
            response = client.get("/health/database-env")
            
            assert response.status_code == 200
            assert response.json()["environment"] == "development"
            assert response.json()["validation"]["valid"] is True
    
    def test_schema_validation_endpoint(self):
        """Test /health/schema-validation endpoint"""
        client = TestClient(app)
        
        with patch('app.routes.health.SchemaValidationService.validate_schema') as mock_validate:
            mock_validate.return_value = {
                "passed": True,
                "missing_tables": [],
                "warnings": []
            }
            
            response = client.get("/health/schema-validation")
            
            assert response.status_code == 200
            assert response.json()["passed"] is True
            assert len(response.json()["missing_tables"]) == 0
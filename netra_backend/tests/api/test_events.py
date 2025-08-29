"""
API tests for events
Coverage Target: 85%
Business Value: Customer-facing functionality
"""

import pytest
from fastapi.testclient import TestClient
from netra_backend.app.main import app

@pytest.mark.api
class TestEventsAPI:
    """API test suite for events"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_get_endpoint(self, client):
        """Test GET request"""
        response = client.get("/api/v1/events")
        assert response.status_code == 200
        assert "data" in response.json()
    
    def test_post_endpoint(self, client):
        """Test POST request"""
        payload = {"test": "data"}
        response = client.post("/api/v1/events", json=payload)
        assert response.status_code == 201
    
    def test_error_responses(self, client):
        """Test error handling"""
        response = client.get("/api/v1/events/invalid")
        assert response.status_code == 404
    
    def test_authentication(self, client):
        """Test auth requirements"""
        response = client.get("/api/v1/events/protected")
        assert response.status_code == 401

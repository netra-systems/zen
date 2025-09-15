"""
API tests for organizations
Coverage Target: 85%
Business Value: Customer-facing functionality
"""

import pytest
from fastapi.testclient import TestClient
from netra_backend.app.main import app
from shared.isolated_environment import IsolatedEnvironment

@pytest.mark.api
class OrganizationsAPITests:
    """API test suite for organizations"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_get_endpoint(self, client):
        """Test GET request"""
        response = client.get("/api/v1/organizations")
        assert response.status_code == 200
        assert "data" in response.json()
    
    def test_post_endpoint(self, client):
        """Test POST request"""
        payload = {"test": "data"}
        response = client.post("/api/v1/organizations", json=payload)
        assert response.status_code == 201
    
    def test_error_responses(self, client):
        """Test error handling"""
        response = client.get("/api/v1/organizations/invalid")
        assert response.status_code == 404
    
    def test_authentication(self, client):
        """Test auth requirements"""
        response = client.get("/api/v1/organizations/protected")
        assert response.status_code == 401

"""
Test for auth config endpoint - ensures frontend can get auth configuration
"""
import pytest
from fastapi.testclient import TestClient
from auth_service.main import app
from shared.isolated_environment import IsolatedEnvironment


class AuthConfigEndpointTests:
    """Test the /auth/config endpoint that frontend requires"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_auth_config_endpoint_exists(self, client):
        """Test that /auth/config endpoint exists and returns 200"""
        response = client.get("/auth/config")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    def test_auth_config_response_structure(self, client):
        """Test that /auth/config returns expected structure"""
        response = client.get("/auth/config")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check required fields exist
        assert "google_client_id" in data, "Missing google_client_id field"
        assert "oauth_enabled" in data, "Missing oauth_enabled field"
        assert "development_mode" in data, "Missing development_mode field"
        assert "endpoints" in data, "Missing endpoints field"
        assert "authorized_javascript_origins" in data, "Missing authorized_javascript_origins field"
        assert "authorized_redirect_uris" in data, "Missing authorized_redirect_uris field"
        
        # Check endpoints structure
        endpoints = data["endpoints"]
        assert isinstance(endpoints, dict), "Endpoints should be a dictionary"
        
        # Check required endpoint fields
        required_endpoints = ["login", "logout", "callback", "token", "user"]
        for endpoint in required_endpoints:
            assert endpoint in endpoints, f"Missing endpoint: {endpoint}"
            assert isinstance(endpoints[endpoint], str), f"Endpoint {endpoint} should be a string"
    
    def test_auth_config_environment_specific_urls(self, client):
        """Test that URLs are environment-appropriate"""
        response = client.get("/auth/config")
        assert response.status_code == 200
        
        data = response.json()
        
        # In test/development, should not have production URLs
        for origin in data["authorized_javascript_origins"]:
            if "netrasystems.ai" in origin:
                # If it contains the domain, it should be properly formatted
                assert origin.startswith("https://") or origin.startswith("http://"), \
                    f"Origin should have protocol: {origin}"
        
        # Check endpoints are absolute URLs
        endpoints = data["endpoints"]
        for key, url in endpoints.items():
            if url:  # Skip None values
                assert url.startswith("http://") or url.startswith("https://"), \
                    f"Endpoint {key} should be absolute URL: {url}"
    
    def test_auth_config_oauth_fields(self, client):
        """Test OAuth-related fields"""
        response = client.get("/auth/config")
        assert response.status_code == 200
        
        data = response.json()
        
        # google_client_id should be string (can be empty)
        assert isinstance(data["google_client_id"], str), "google_client_id should be string"
        
        # oauth_enabled should be boolean
        assert isinstance(data["oauth_enabled"], bool), "oauth_enabled should be boolean"
        
        # If google_client_id is set, oauth_enabled should be true
        if data["google_client_id"]:
            assert data["oauth_enabled"] is True, \
                "oauth_enabled should be True when google_client_id is set"
        
    def test_auth_config_development_mode(self, client):
        """Test development_mode field"""
        response = client.get("/auth/config")
        assert response.status_code == 200
        
        data = response.json()
        
        # development_mode should be boolean
        assert isinstance(data["development_mode"], bool), "development_mode should be boolean"
        
        # If development_mode is true, dev_login endpoint might be present
        if data["development_mode"]:
            endpoints = data["endpoints"]
            # dev_login is optional even in development
            if "dev_login" in endpoints:
                assert endpoints["dev_login"] is not None, \
                    "dev_login should not be None in development mode"
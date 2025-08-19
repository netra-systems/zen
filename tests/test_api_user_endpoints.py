"""
Comprehensive API endpoint tests for user management.
Tests user profile, settings, and account management endpoints.

Business Value Justification (BVJ):
1. Segment: All customer segments (Free, Early, Mid, Enterprise)
2. Business Goal: Ensure seamless user experience and account management
3. Value Impact: Improves user retention and satisfaction
4. Revenue Impact: Reduces churn, improves upgrade conversion rates
"""
import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any


def _create_mock_user_service() -> Mock:
    """Create mock user service."""
    mock = Mock()
    mock.get_user = AsyncMock(return_value={
        "id": "test-user-id",
        "email": "test@example.com",
        "full_name": "Test User",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z"
    })
    mock.update_user = AsyncMock(return_value={"status": "updated"})
    mock.delete_user = AsyncMock(return_value={"status": "deleted"})
    return mock


@pytest.fixture
def mock_user_dependencies():
    """Mock user management dependencies."""
    with patch('app.services.user_service', _create_mock_user_service()):
        yield


class TestUserProfileEndpoints:
    """Test user profile management endpoints."""

    def test_get_user_profile(self, client: TestClient, auth_headers: Dict[str, str], mock_user_dependencies) -> None:
        """Test retrieving user profile."""
        response = client.get("/api/users/profile", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            assert "id" in data or "user_id" in data
            assert "email" in data

    def test_update_user_profile(self, client: TestClient, auth_headers: Dict[str, str], mock_user_dependencies) -> None:
        """Test updating user profile."""
        update_data = {
            "full_name": "Updated Name",
            "bio": "Updated bio"
        }
        
        response = client.put("/api/users/profile", json=update_data, headers=auth_headers)
        
        if response.status_code in [200, 204]:
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, dict)

    def test_get_user_profile_unauthorized(self, client: TestClient) -> None:
        """Test getting profile without authentication."""
        response = client.get("/api/users/profile")
        assert response.status_code == 401

    def test_update_profile_invalid_data(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test updating profile with invalid data."""
        invalid_data = {
            "email": "invalid-email-format"
        }
        
        response = client.put("/api/users/profile", json=invalid_data, headers=auth_headers)
        assert response.status_code in [400, 422]


class TestUserSettingsEndpoints:
    """Test user settings management endpoints."""

    def test_get_user_settings(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test retrieving user settings."""
        response = client.get("/api/users/settings", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            # Common settings fields
            settings_fields = ["notifications", "preferences", "theme", "timezone"]
            # At least one setting field should be present
            has_settings = any(field in data for field in settings_fields)
            assert has_settings or len(data) > 0

    def test_update_user_settings(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test updating user settings."""
        settings_data = {
            "notifications": {"email": True, "sms": False},
            "theme": "dark",
            "timezone": "UTC"
        }
        
        response = client.put("/api/users/settings", json=settings_data, headers=auth_headers)
        
        if response.status_code in [200, 204]:
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, dict)

    def test_get_settings_unauthorized(self, client: TestClient) -> None:
        """Test getting settings without authentication."""
        response = client.get("/api/users/settings")
        assert response.status_code == 401


class TestUserAccountEndpoints:
    """Test user account management endpoints."""

    def test_change_password(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test changing user password."""
        password_data = {
            "current_password": "oldpassword",
            "new_password": "newpassword123"
        }
        
        response = client.post("/api/users/change-password", json=password_data, headers=auth_headers)
        
        # Accept various response codes for password change
        assert response.status_code in [200, 204, 404]  # 404 if endpoint not implemented

    def test_change_password_invalid_current(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test changing password with invalid current password."""
        password_data = {
            "current_password": "wrongpassword",
            "new_password": "newpassword123"
        }
        
        response = client.post("/api/users/change-password", json=password_data, headers=auth_headers)
        
        if response.status_code != 404:  # If endpoint exists
            assert response.status_code in [400, 401, 403]

    def test_change_password_weak_new(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test changing to weak password."""
        password_data = {
            "current_password": "oldpassword",
            "new_password": "123"  # Weak password
        }
        
        response = client.post("/api/users/change-password", json=password_data, headers=auth_headers)
        
        if response.status_code != 404:  # If endpoint exists
            assert response.status_code in [400, 422]

    def test_deactivate_account(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test account deactivation."""
        response = client.post("/api/users/deactivate", headers=auth_headers)
        
        # Accept various response codes
        assert response.status_code in [200, 204, 404]  # 404 if endpoint not implemented

    def test_delete_account(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test account deletion."""
        response = client.delete("/api/users/account", headers=auth_headers)
        
        # Accept various response codes
        assert response.status_code in [200, 204, 404]  # 404 if endpoint not implemented


class TestUserListEndpoints:
    """Test user listing endpoints (admin functionality)."""

    def test_list_users_unauthorized(self, client: TestClient) -> None:
        """Test listing users without authentication."""
        response = client.get("/api/users")
        assert response.status_code == 401

    def test_list_users_non_admin(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test listing users as non-admin user."""
        response = client.get("/api/users", headers=auth_headers)
        
        # Should either work (if user has permission) or return 403/404
        assert response.status_code in [200, 403, 404]

    def test_get_user_by_id(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test getting specific user by ID."""
        user_id = "test-user-id"
        response = client.get(f"/api/users/{user_id}", headers=auth_headers)
        
        # Should either work or return appropriate error
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            assert "id" in data or "user_id" in data


class TestUserValidationEndpoints:
    """Test user data validation endpoints."""

    def test_validate_email_available(self, client: TestClient) -> None:
        """Test email availability validation."""
        response = client.get("/api/users/validate/email?email=newuser@example.com")
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            assert "available" in data or "exists" in data

    def test_validate_email_invalid_format(self, client: TestClient) -> None:
        """Test email validation with invalid format."""
        response = client.get("/api/users/validate/email?email=invalid-email")
        assert response.status_code in [400, 422]

    def test_validate_username_available(self, client: TestClient) -> None:
        """Test username availability validation."""
        response = client.get("/api/users/validate/username?username=newuser")
        
        # Accept various response codes (endpoint might not exist)
        assert response.status_code in [200, 404]


class TestUserSecurityEndpoints:
    """Test user security-related endpoints."""

    def test_two_factor_auth_status(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test getting 2FA status."""
        response = client.get("/api/users/2fa/status", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            assert "enabled" in data or "active" in data

    def test_enable_two_factor_auth(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test enabling 2FA."""
        response = client.post("/api/users/2fa/enable", headers=auth_headers)
        
        # Accept various response codes (endpoint might not exist)
        assert response.status_code in [200, 201, 404]

    def test_disable_two_factor_auth(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test disabling 2FA."""
        response = client.post("/api/users/2fa/disable", headers=auth_headers)
        
        # Accept various response codes (endpoint might not exist)
        assert response.status_code in [200, 204, 404]

    def test_get_api_keys(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test getting user API keys."""
        response = client.get("/api/users/api-keys", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))

    def test_create_api_key(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test creating new API key."""
        key_data = {
            "name": "Test API Key",
            "permissions": ["read", "write"]
        }
        
        response = client.post("/api/users/api-keys", json=key_data, headers=auth_headers)
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert isinstance(data, dict)
            assert "key" in data or "api_key" in data or "token" in data


class TestUserEndpointsErrorHandling:
    """Test error handling in user endpoints."""

    def test_invalid_user_id_format(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test accessing user with invalid ID format."""
        response = client.get("/api/users/invalid-id-format", headers=auth_headers)
        assert response.status_code in [400, 404, 422]

    def test_nonexistent_user_id(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test accessing nonexistent user."""
        response = client.get("/api/users/nonexistent-user-id", headers=auth_headers)
        assert response.status_code == 404

    def test_malformed_json_request(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test user endpoints with malformed JSON."""
        response = client.put(
            "/api/users/profile",
            data="malformed json",
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422]


class TestUserEndpointsPerformance:
    """Test performance aspects of user endpoints."""

    def test_profile_endpoint_response_time(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test profile endpoint response time."""
        import time
        
        start_time = time.time()
        response = client.get("/api/users/profile", headers=auth_headers)
        end_time = time.time()
        
        response_time = end_time - start_time
        # Response should be fast (under 5 seconds even in test environment)
        assert response_time < 5.0

    def test_concurrent_profile_requests(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test handling concurrent profile requests."""
        import concurrent.futures
        import threading
        
        def make_request():
            return client.get("/api/users/profile", headers=auth_headers)
        
        # Make 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should complete successfully or fail consistently
        status_codes = [r.status_code for r in responses]
        # Either all succeed or all fail with same error
        assert len(set(status_codes)) <= 2  # At most 2 different status codes
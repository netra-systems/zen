"""
Test Client for Auth Service
HTTP test client with authentication helpers for testing auth endpoints.
Provides convenient methods for auth operations and request handling.
"""

import httpx
from typing import Dict, Any, Optional, Union
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from ..factories import TokenFactory


class AuthTestClient:
    """Test client with authentication helpers"""
    
    def __init__(self, client: Union[TestClient, httpx.AsyncClient] = None):
        self.client = client or MagicMock()
        self.auth_token = None
        self.base_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def set_auth_token(self, token: str):
        """Set authentication token for requests"""
        self.auth_token = token
    
    def get_auth_headers(self, token: str = None) -> Dict[str, str]:
        """Get headers with authentication token"""
        headers = self.base_headers.copy()
        auth_token = token or self.auth_token
        
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        return headers
    
    def login(
        self,
        email: str,
        password: str,
        provider: str = "local"
    ) -> Dict[str, Any]:
        """Perform login request"""
        login_data = {
            "email": email,
            "password": password,
            "provider": provider
        }
        
        response = self.client.post(
            "/auth/login",
            json=login_data,
            headers=self.base_headers
        )
        
        if hasattr(response, 'json'):
            result = response.json()
            
            # Store token for subsequent requests
            if "access_token" in result:
                self.set_auth_token(result["access_token"])
            
            return result
        
        return {"error": "Mock response"}
    
    def logout(self, token: str = None) -> Dict[str, Any]:
        """Perform logout request"""
        response = self.client.post(
            "/auth/logout",
            headers=self.get_auth_headers(token)
        )
        
        # Clear stored token
        self.auth_token = None
        
        if hasattr(response, 'json'):
            return response.json()
        
        return {"message": "Logged out"}
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token"""
        refresh_data = {"refresh_token": refresh_token}
        
        response = self.client.post(
            "/auth/refresh",
            json=refresh_data,
            headers=self.base_headers
        )
        
        if hasattr(response, 'json'):
            result = response.json()
            
            # Update stored token
            if "access_token" in result:
                self.set_auth_token(result["access_token"])
            
            return result
        
        return {"access_token": "new_mock_token"}
    
    def validate_token(self, token: str = None) -> Dict[str, Any]:
        """Validate authentication token"""
        response = self.client.get(
            "/auth/validate",
            headers=self.get_auth_headers(token)
        )
        
        if hasattr(response, 'json'):
            return response.json()
        
        return {"valid": True, "user_id": "mock_user"}
    
    def get_user_profile(self, token: str = None) -> Dict[str, Any]:
        """Get current user profile"""
        response = self.client.get(
            "/auth/user",
            headers=self.get_auth_headers(token)
        )
        
        if hasattr(response, 'json'):
            return response.json()
        
        return {"id": "mock_user", "email": "test@example.com"}
    
    def change_password(
        self,
        current_password: str,
        new_password: str,
        token: str = None
    ) -> Dict[str, Any]:
        """Change user password"""
        password_data = {
            "current_password": current_password,
            "new_password": new_password
        }
        
        response = self.client.put(
            "/auth/password",
            json=password_data,
            headers=self.get_auth_headers(token)
        )
        
        if hasattr(response, 'json'):
            return response.json()
        
        return {"message": "Password changed"}
    
    def oauth_callback(
        self,
        provider: str,
        code: str,
        state: str = None
    ) -> Dict[str, Any]:
        """Handle OAuth callback"""
        callback_params = {
            "code": code,
            "state": state
        }
        
        response = self.client.get(
            f"/auth/{provider}/callback",
            params=callback_params
        )
        
        if hasattr(response, 'json'):
            result = response.json()
            
            # Store token for subsequent requests
            if "access_token" in result:
                self.set_auth_token(result["access_token"])
            
            return result
        
        return {"access_token": "oauth_mock_token"}
    
    def get_auth_config(self) -> Dict[str, Any]:
        """Get authentication configuration"""
        response = self.client.get("/auth/config")
        
        if hasattr(response, 'json'):
            return response.json()
        
        return {
            "google_client_id": "mock_client_id",
            "endpoints": {
                "login": "/auth/login",
                "logout": "/auth/logout"
            }
        }
    
    def revoke_session(self, session_id: str, token: str = None) -> Dict[str, Any]:
        """Revoke specific session"""
        response = self.client.delete(
            f"/auth/sessions/{session_id}",
            headers=self.get_auth_headers(token)
        )
        
        if hasattr(response, 'json'):
            return response.json()
        
        return {"message": "Session revoked"}
    
    def get_user_sessions(self, token: str = None) -> Dict[str, Any]:
        """Get user's active sessions"""
        response = self.client.get(
            "/auth/sessions",
            headers=self.get_auth_headers(token)
        )
        
        if hasattr(response, 'json'):
            return response.json()
        
        return {"sessions": []}


class MockAuthTestClient(AuthTestClient):
    """Mock auth test client for unit tests without HTTP server"""
    
    def __init__(self):
        super().__init__(client=MagicMock())
        self.mock_users = {}
        self.mock_sessions = {}
    
    def add_mock_user(
        self,
        email: str,
        password: str = "TestPassword123!",
        user_id: str = None
    ):
        """Add mock user for testing"""
        import uuid
        user_id = user_id or str(uuid.uuid4())
        
        self.mock_users[email] = {
            "id": user_id,
            "email": email,
            "password": password,
            "is_active": True
        }
        
        return user_id
    
    def login(
        self,
        email: str,
        password: str,
        provider: str = "local"
    ) -> Dict[str, Any]:
        """Mock login implementation"""
        if email not in self.mock_users:
            return {"error": "User not found", "status_code": 404}
        
        user = self.mock_users[email]
        if user["password"] != password:
            return {"error": "Invalid credentials", "status_code": 401}
        
        # Create mock tokens
        access_token = TokenFactory.create_access_token(
            user_id=user["id"],
            email=user["email"]
        )
        
        refresh_token = TokenFactory.create_refresh_token(
            user_id=user["id"],
            email=user["email"]
        )
        
        self.set_auth_token(access_token)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "user": {
                "id": user["id"],
                "email": user["email"]
            }
        }
    
    def get_user_profile(self, token: str = None) -> Dict[str, Any]:
        """Mock get user profile"""
        auth_token = token or self.auth_token
        
        if not auth_token:
            return {"error": "No authentication token", "status_code": 401}
        
        try:
            claims = TokenFactory.decode_token(auth_token, verify=False)
            user_id = claims.get("sub")
            email = claims.get("email")
            
            return {
                "id": user_id,
                "email": email,
                "is_active": True
            }
        except Exception:
            return {"error": "Invalid token", "status_code": 401}
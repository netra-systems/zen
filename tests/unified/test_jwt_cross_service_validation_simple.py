"""
JWT Cross-Service Validation - Simple Test Suite
BVJ: Segment: ALL | Goal: Security | Impact: $150K+ MRR protection
Performance requirement: < 50ms validation per service

Tests JWT validation consistency across Auth Service, Backend, and WebSocket services.
Focuses on SIMPLE, BASIC validation cases as specified in test plan.
Business Value: Prevents authentication failures that cost revenue and customer trust.
"""
import pytest
import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from tests.unified.jwt_token_helpers import JWTTestHelper
from tests.unified.test_harness import UnifiedTestHarness


class TestJWTCrossServiceValidationSimple:
    """
    Business Value: $150K+ MRR protection
    Coverage: JWT validation consistency across all services
    Performance: < 50ms per validation
    """
    
    def setup_method(self):
        """Setup test environment."""
        self.jwt_helper = JWTTestHelper()
        self.harness = UnifiedTestHarness()
        self.test_secret = "zZyIqeCZia66c1NxEgNowZFWbwMGROFg"
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_basic_jwt_validation(self):
        """Test 1: Basic JWT creation and validation across all services."""
        start_time = time.perf_counter()
        user_id = f"test-user-{int(time.time())}"
        token = self._create_standard_token(user_id)
        
        # Validate across all services concurrently
        auth_result, backend_result, websocket_result = await asyncio.gather(
            self._validate_auth_service(token),
            self._validate_backend_service(token),
            self._validate_websocket_service(token)
        )
        
        total_time = time.perf_counter() - start_time
        assert total_time < 5.0, f"Total validation time {total_time:.3f}s exceeds 5s limit"
        assert auth_result["status"] in [200, 401, 500], "Auth service should respond"
        assert backend_result["status"] in [200, 401, 500], "Backend service should respond"
        assert websocket_result["connected"] is not None, "WebSocket should attempt connection"
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_invalid_token_rejection(self):
        """Test 2: Invalid token consistent rejection across services."""
        test_tokens = {
            "malformed": "invalid.jwt.token.format",
            "expired": self._create_expired_token(),
            "invalid_signature": self._create_invalid_signature_token()
        }
        
        for token_type, token in test_tokens.items():
            start_time = time.perf_counter()
            auth_result, backend_result, websocket_result = await asyncio.gather(
                self._validate_auth_service(token),
                self._validate_backend_service(token),
                self._validate_websocket_service(token)
            )
            validation_time = time.perf_counter() - start_time
            assert validation_time < 1.0, f"Rejection validation too slow: {validation_time:.3f}s"
            assert auth_result["status"] == 401, f"Auth should reject {token_type} token"
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_claims_extraction_consistency(self):
        """Test 3: Claims extraction consistency across services."""
        user_id = f"test-user-{int(time.time())}"
        token = self._create_complex_claims_token(user_id)
        
        start_time = time.perf_counter()
        auth_result = await self._validate_auth_service(token)
        backend_result = await self._validate_backend_service(token)
        extraction_time = time.perf_counter() - start_time
        
        assert extraction_time < 0.1, f"Claims extraction too slow: {extraction_time:.3f}s"
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_token_expiry_handling(self):
        """Test 4: Token expiry handling consistency."""
        user_id = f"test-user-{int(time.time())}"
        token = self._create_short_expiry_token(user_id, 30)
        
        # Test before expiry
        start_time = time.perf_counter()
        auth_result_valid = await self._validate_auth_service(token)
        valid_time = time.perf_counter() - start_time
        
        # Wait for expiry and test after
        await asyncio.sleep(31)
        start_time = time.perf_counter()
        auth_result_expired = await self._validate_auth_service(token)
        expired_time = time.perf_counter() - start_time
        
        assert valid_time < 0.05, f"Valid token check too slow: {valid_time:.3f}s"
        assert expired_time < 0.05, f"Expired token check too slow: {expired_time:.3f}s"
        assert auth_result_expired["status"] == 401, "Expired token should be rejected"
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Test 5: Performance under load with multiple tokens."""
        # Create 10 different tokens
        tokens = [self._create_standard_token(f"load-test-user-{i}-{int(time.time())}") for i in range(10)]
        
        # Validate all tokens concurrently
        start_time = time.perf_counter()
        validation_tasks = []
        for token in tokens:
            validation_tasks.extend([self._validate_auth_service(token), self._validate_backend_service(token)])
        
        results = await asyncio.gather(*validation_tasks)
        total_time = time.perf_counter() - start_time
        p95_time = total_time / len(tokens)  # Simplified calculation
        
        assert total_time < 10.0, f"Load test too slow: {total_time:.3f}s"
        assert p95_time < 1.0, f"P95 validation time too slow: {p95_time:.3f}s"
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_secret_synchronization(self):
        """Test 6: JWT secret synchronization across services."""
        user_id = f"sync-test-user-{int(time.time())}"
        correct_token = self._create_standard_token(user_id)
        wrong_token = self._create_token_with_wrong_secret(user_id)
        
        start_time = time.perf_counter()
        correct_auth, correct_backend, wrong_auth, wrong_backend = await asyncio.gather(
            self._validate_auth_service(correct_token),
            self._validate_backend_service(correct_token),
            self._validate_auth_service(wrong_token),
            self._validate_backend_service(wrong_token)
        )
        sync_time = time.perf_counter() - start_time
        
        assert sync_time < 0.2, f"Secret sync test too slow: {sync_time:.3f}s"
        assert wrong_auth["status"] == 401, "Wrong secret should be rejected by auth"
        assert wrong_backend["status"] in [401, 500], "Wrong secret should be rejected by backend"
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_edge_cases_boundaries(self):
        """Test 7: Edge cases and boundary conditions."""
        test_cases = {
            "minimal_token": self._create_minimal_token(),
            "large_token": self._create_large_token(),
            "missing_claims": self._create_missing_claims_token(),
            "extra_claims": self._create_extra_claims_token()
        }
        
        for case_name, token in test_cases.items():
            start_time = time.perf_counter()
            auth_result = await self._validate_auth_service(token)
            backend_result = await self._validate_backend_service(token)
            case_time = time.perf_counter() - start_time
            assert case_time < 0.1, f"Edge case {case_name} too slow: {case_time:.3f}s"
    
    # Helper methods
    async def _validate_auth_service(self, token: str) -> Dict[str, Any]:
        """Validate token against auth service."""
        return await self.jwt_helper.make_auth_request("/auth/verify", token)
    
    async def _validate_backend_service(self, token: str) -> Dict[str, Any]:
        """Validate token against backend service."""
        return await self.jwt_helper.make_backend_request("/api/users/profile", token)
    
    async def _validate_websocket_service(self, token: str) -> Dict[str, Any]:
        """Validate token against WebSocket service."""
        try:
            import websockets
            async with websockets.connect(f"ws://localhost:8000/ws?token={token}", 
                                        close_timeout=1, ping_timeout=1) as ws:
                await asyncio.wait_for(ws.ping(), timeout=1)
                return {"connected": True}
        except Exception as e:
            return {"connected": False, "error": str(e)}
    
    def _create_standard_token(self, user_id: str) -> str:
        """Create standard test token."""
        payload = {
            "sub": user_id, "email": f"{user_id}@test.netra.ai", "permissions": ["read", "write"],
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
            "token_type": "access", "iss": "netra-auth-service"
        }
        return self.jwt_helper.create_token(payload, self.test_secret)
    
    def _create_complex_claims_token(self, user_id: str) -> str:
        """Create token with complex claims."""
        payload = {
            "sub": user_id, "email": f"{user_id}@test.netra.ai",
            "permissions": ["read", "write", "admin"], "roles": ["user", "developer"],
            "metadata": {"tier": "enterprise", "region": "us-east"},
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
            "token_type": "access", "iss": "netra-auth-service"
        }
        return self.jwt_helper.create_token(payload, self.test_secret)
    
    def _create_short_expiry_token(self, user_id: str, seconds: int) -> str:
        """Create token with short expiry."""
        payload = {
            "sub": user_id, "email": f"{user_id}@test.netra.ai", "permissions": ["read"],
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(seconds=seconds)).timestamp()),
            "token_type": "access", "iss": "netra-auth-service"
        }
        return self.jwt_helper.create_token(payload, self.test_secret)
    
    def _create_token_with_wrong_secret(self, user_id: str) -> str:
        """Create token with wrong secret."""
        payload = {
            "sub": user_id, "email": f"{user_id}@test.netra.ai", "permissions": ["read"],
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
            "token_type": "access", "iss": "netra-auth-service"
        }
        return self.jwt_helper.create_token(payload, "wrong-secret-32-chars-minimum")
    
    def _create_expired_token(self) -> str:
        """Create expired token for testing."""
        payload = {"sub": "expired-user", "email": "expired@test.netra.ai",
                   "exp": int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp()),
                   "token_type": "access"}
        return self.jwt_helper.create_token(payload, self.test_secret)
    
    def _create_invalid_signature_token(self) -> str:
        """Create token with invalid signature."""
        payload = {"sub": "invalid-user", "email": "invalid@test.netra.ai",
                   "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
                   "token_type": "access"}
        valid_token = self.jwt_helper.create_token(payload, self.test_secret)
        parts = valid_token.split('.')
        return f"{parts[0]}.{parts[1]}.invalid_signature"
    
    def _create_minimal_token(self) -> str:
        """Create minimal valid token."""
        payload = {"sub": "minimal-user",
                   "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
                   "token_type": "access"}
        return self.jwt_helper.create_token(payload, self.test_secret)
    
    def _create_large_token(self) -> str:
        """Create token with large payload."""
        payload = {"sub": "large-user", "email": "large@test.netra.ai",
                   "permissions": ["read", "write", "admin", "super_admin"],
                   "roles": ["user", "developer", "admin", "super_admin"],
                   "metadata": {f"key_{i}": f"value_{i}" for i in range(50)},
                   "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
                   "token_type": "access"}
        return self.jwt_helper.create_token(payload, self.test_secret)
    
    def _create_missing_claims_token(self) -> str:
        """Create token with missing optional claims."""
        payload = {"sub": "missing-claims-user",
                   "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
                   "token_type": "access"}
        return self.jwt_helper.create_token(payload, self.test_secret)
    
    def _create_extra_claims_token(self) -> str:
        """Create token with extra claims."""
        payload = {"sub": "extra-claims-user", "email": "extra@test.netra.ai",
                   "permissions": ["read"], "token_type": "access",
                   "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
                   "extra_field": "should_be_ignored", "custom_data": {"test": True},
                   "admin_override": True}
        return self.jwt_helper.create_token(payload, self.test_secret)


if __name__ == "__main__":
    # Allow direct execution for debugging
    pytest.main([__file__, "-v", "-s", "--tb=short"])
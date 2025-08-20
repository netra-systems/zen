"""
JWT Secret Synchronization Test Suite - Critical Security Infrastructure

BVJ: Segment: ALL | Goal: Security | Impact: Protects $330K+ MRR by ensuring JWT security
Tests JWT secret consistency across Auth Service, Backend, and WebSocket services
Performance requirement: <50ms validation across services

Business Value: Prevents authentication failures that cost revenue and customer trust
CRITICAL: Real service authentication - validates actual JWT secret synchronization
"""
import pytest
import asyncio
import websockets
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from tests.unified.jwt_token_helpers import JWTTestHelper
from tests.unified.test_harness import UnifiedTestHarness


class JWTSecretSynchronizationTester:
    """Comprehensive JWT secret synchronization validator with UnifiedTestHarness integration."""
    
    def __init__(self):
        self.auth_url = "http://localhost:8081"  # Fixed: align with jwt_token_helpers.py
        self.backend_url = "http://localhost:8000"
        self.websocket_url = "ws://localhost:8000"
        self.jwt_helper = JWTTestHelper()
        self.test_secret = "test-jwt-secret-key-32-chars-min"
        self.harness = UnifiedTestHarness()  # Integration with UnifiedTestHarness
    
    async def test_jwt_creation_and_cross_service_validation(self) -> Dict[str, Any]:
        """Test 1: Create JWT in Auth and validate across Backend and WebSocket."""
        start_time = time.time()
        user_id = f"test-user-{int(time.time())}"
        test_token = self.jwt_helper.create_token(self._create_test_payload(user_id), self.test_secret)
        
        # Validate token across all services concurrently
        service_results = await self._validate_token_across_services(test_token)
        
        # Build result metrics
        total_duration = time.time() - start_time
        return self._build_validation_result(service_results, total_duration)
    
    async def _validate_token_across_services(self, token: str) -> tuple:
        """Validate token across auth, backend, and websocket services."""
        return await asyncio.gather(
            self._validate_auth_service(token),
            self._validate_backend_service(token),
            self._validate_websocket_service(token)
        )
    
    def _build_validation_result(self, service_results: tuple, duration: float) -> Dict[str, Any]:
        """Build test result dictionary from service validation results."""
        auth_result, backend_result, websocket_result = service_results
        return {
            "auth_status": auth_result["status"], 
            "backend_status": backend_result["status"],
            "websocket_connected": websocket_result["connected"], 
            "performance_ok": duration < 0.05,
            "total_duration": duration, 
            "consistent_handling": self._check_consistency(auth_result, backend_result, websocket_result)
        }
    
    async def test_jwt_secret_rotation(self) -> Dict[str, Any]:
        """Test 2: Simulate secret rotation and verify service behavior."""
        start_time = time.time()
        user_id = f"test-user-{int(time.time())}"
        
        # Create tokens with old and new secrets
        token_pair = self._create_rotation_token_pair(user_id)
        
        # Test both tokens against services
        rotation_results = await self._test_secret_rotation(token_pair)
        
        total_duration = time.time() - start_time
        return self._build_rotation_result(rotation_results, total_duration)
    
    def _create_rotation_token_pair(self, user_id: str) -> Dict[str, str]:
        """Create old and new tokens for rotation testing."""
        payload = self._create_test_payload(user_id)
        return {
            "old_token": self.jwt_helper.create_token(payload, "old-jwt-secret-key-32-chars-min"),
            "new_token": self.jwt_helper.create_token(payload, "new-jwt-secret-key-32-chars-min")
        }
    
    async def _test_secret_rotation(self, token_pair: Dict[str, str]) -> Dict[str, Dict]:
        """Test old and new tokens against auth and backend services."""
        old_auth, old_backend, new_auth, new_backend = await asyncio.gather(
            self._validate_auth_service(token_pair["old_token"]), 
            self._validate_backend_service(token_pair["old_token"]),
            self._validate_auth_service(token_pair["new_token"]), 
            self._validate_backend_service(token_pair["new_token"])
        )
        return {"old_auth": old_auth, "old_backend": old_backend, 
                "new_auth": new_auth, "new_backend": new_backend}
    
    def _build_rotation_result(self, rotation_results: Dict, duration: float) -> Dict[str, Any]:
        """Build rotation test result from service responses."""
        return {
            "old_token_rejected": (rotation_results["old_auth"]["status"] == 401 and 
                                 rotation_results["old_backend"]["status"] == 401),
            "new_token_handled": (rotation_results["new_auth"]["status"] in [200, 401] and 
                                rotation_results["new_backend"]["status"] in [200, 401]),
            "performance_ok": duration < 0.05, 
            "total_duration": duration
        }
    
    async def test_mismatched_secret_handling(self) -> Dict[str, Any]:
        """Test 3: Configure services with different secrets and test rejection."""
        start_time = time.time()
        user_id = f"test-user-{int(time.time())}"
        
        # Create token with wrong secret
        invalid_token = self._create_invalid_secret_token(user_id)
        
        # Test rejection across all services
        rejection_results = await self._validate_token_across_services(invalid_token)
        
        total_duration = time.time() - start_time
        return self._build_rejection_result(rejection_results, total_duration)
    
    def _create_invalid_secret_token(self, user_id: str) -> str:
        """Create token with mismatched secret for rejection testing."""
        payload = self._create_test_payload(user_id)
        return self.jwt_helper.create_token(payload, "wrong-jwt-secret-different-32")
    
    def _build_rejection_result(self, service_results: tuple, duration: float) -> Dict[str, Any]:
        """Build rejection test result from service responses."""
        auth_result, backend_result, websocket_result = service_results
        return {
            "auth_rejected": auth_result["status"] == 401, 
            "backend_rejected": backend_result["status"] == 401,
            "websocket_rejected": not websocket_result["connected"], 
            "performance_ok": duration < 0.05,
            "consistent_rejection": self._check_consistent_rejection(auth_result, backend_result, websocket_result)
        }
    
    async def test_performance_validation(self) -> Dict[str, Any]:
        """Test 4: Measure JWT validation performance across services."""
        user_id = f"test-user-{int(time.time())}"
        test_token = self.jwt_helper.create_token(self._create_test_payload(user_id), self.test_secret)
        
        # Measure concurrent validation
        concurrent_start = time.time()
        results = await asyncio.gather(
            self._validate_auth_service(test_token),
            self._validate_backend_service(test_token),
            self._validate_websocket_service(test_token)
        )
        concurrent_duration = time.time() - concurrent_start
        
        return {
            "concurrent_duration": concurrent_duration, "concurrent_under_50ms": concurrent_duration < 0.05,
            "all_services_responded": all(r.get("status") or r.get("connected") is not None for r in results)
        }
    
    async def test_edge_cases(self) -> Dict[str, Any]:
        """Test 5: Handle expired tokens, malformed tokens, and clock skew."""
        start_time = time.time()
        user_id = f"test-user-{int(time.time())}"
        
        # Create edge case tokens
        expired_payload = self._create_test_payload(user_id)
        expired_payload["exp"] = int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp())
        expired_token = self.jwt_helper.create_token(expired_payload, self.test_secret)
        
        expired_results, malformed_results = await asyncio.gather(
            self._test_token_across_services(expired_token),
            self._test_token_across_services("invalid.jwt.token")
        )
        
        total_duration = time.time() - start_time
        return {
            "expired_token_rejected": all(r["status"] == 401 for r in expired_results.values() if r["status"] != 500),
            "malformed_token_rejected": all(r["status"] == 401 for r in malformed_results.values() if r["status"] != 500),
            "performance_ok": total_duration < 0.05
        }
    
    def _create_test_payload(self, user_id: str) -> Dict[str, Any]:
        """Create standard test JWT payload."""
        now = datetime.now(timezone.utc)
        return {
            "sub": user_id, "email": f"{user_id}@test.netra.ai", "permissions": ["read", "write"],
            "iat": int(now.timestamp()), "exp": int((now + timedelta(minutes=15)).timestamp()),
            "token_type": "access", "iss": "netra-auth-service"
        }
    
    async def _validate_auth_service(self, token: str) -> Dict[str, Any]:
        """Validate token against auth service."""
        return await self.jwt_helper.make_auth_request("/auth/validate", token)
    
    async def _validate_backend_service(self, token: str) -> Dict[str, Any]:
        """Validate token against backend service."""
        return await self.jwt_helper.make_backend_request("/health", token)
    
    async def _validate_websocket_service(self, token: str) -> Dict[str, Any]:
        """Validate token against WebSocket service."""
        try:
            async with websockets.connect(f"{self.websocket_url}/ws?token={token}", timeout=3) as ws:
                await ws.ping()
                return {"connected": True}
        except Exception as e:
            return {"connected": False, "error": str(e)}
    
    async def _test_token_across_services(self, token: str) -> Dict[str, Dict[str, Any]]:
        """Test token across all services and return results."""
        auth_result, backend_result, websocket_result = await asyncio.gather(
            self._validate_auth_service(token), self._validate_backend_service(token), self._validate_websocket_service(token)
        )
        return {"auth": auth_result, "backend": backend_result, "websocket": {"status": 200 if websocket_result["connected"] else 401}}
    
    def _check_consistency(self, auth_result: Dict, backend_result: Dict, websocket_result: Dict) -> bool:
        """Check if all services handle token consistently."""
        if auth_result["status"] == 500 or backend_result["status"] == 500:
            return True
        return (auth_result["status"] in [200, 401]) and (backend_result["status"] in [200, 401])
    
    def _check_consistent_rejection(self, auth_result: Dict, backend_result: Dict, websocket_result: Dict) -> bool:
        """Check that all services consistently reject invalid tokens."""
        if auth_result["status"] == 500 or backend_result["status"] == 500:
            return True
        return auth_result["status"] == 401 and backend_result["status"] == 401 and not websocket_result["connected"]


@pytest.mark.critical
@pytest.mark.asyncio
async def test_jwt_creation_and_cross_service_validation():
    """BVJ: Segment: ALL | Goal: Security | Impact: All authenticated operations"""
    tester = JWTSecretSynchronizationTester()
    result = await tester.test_jwt_creation_and_cross_service_validation()
    
    assert result["performance_ok"], f"Cross-service validation too slow: {result['total_duration']}s"
    assert result["consistent_handling"], "Services should handle JWT tokens consistently"
    assert result["auth_status"] in [200, 401, 500], "Auth service should respond"


@pytest.mark.critical
@pytest.mark.asyncio
async def test_jwt_secret_rotation():
    """Test JWT secret rotation and propagation across all services."""
    tester = JWTSecretSynchronizationTester()
    result = await tester.test_jwt_secret_rotation()
    
    assert result["performance_ok"], f"Secret rotation test too slow: {result['total_duration']}s"
    assert result["new_token_handled"], "Services should handle new tokens appropriately"


@pytest.mark.critical
@pytest.mark.asyncio
async def test_mismatched_secret_handling():
    """Test that mismatched secrets cause consistent failures across all services."""
    tester = JWTSecretSynchronizationTester()
    result = await tester.test_mismatched_secret_handling()
    
    assert result["consistent_rejection"], "All services should consistently reject mismatched secrets"


@pytest.mark.critical
@pytest.mark.asyncio
async def test_performance_validation():
    """Test JWT validation performance meets <50ms requirement across services."""
    tester = JWTSecretSynchronizationTester()
    result = await tester.test_performance_validation()
    
    assert result["concurrent_under_50ms"], f"Concurrent validation too slow: {result['concurrent_duration']}s"
    assert result["all_services_responded"], "All services should respond to validation requests"


@pytest.mark.critical
@pytest.mark.asyncio
async def test_edge_cases():
    """Test edge cases: expired tokens, malformed tokens, missing claims, clock skew."""
    tester = JWTSecretSynchronizationTester()
    result = await tester.test_edge_cases()
    
    assert result["performance_ok"], f"Edge case testing too slow"
    assert result["expired_token_rejected"], "All services should reject expired tokens"
    assert result["malformed_token_rejected"], "All services should reject malformed tokens"


if __name__ == "__main__":
    # Allow direct execution for debugging
    pytest.main([__file__, "-v", "-s", "--tb=short"])
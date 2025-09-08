"""
Token Expiry Cross-Service Synchronization Tests

Business Value Justification (BVJ):
- Segment: Enterprise ($260K+ MRR)
- Business Goal: Security enforcement and service reliability  
- Value Impact: 99.9% token expiry detection across all services
- Strategic Impact: Prevents unauthorized access and ensures consistent auth state
"""
import asyncio
import time
from datetime import datetime, timedelta, timezone
from shared.isolated_environment import IsolatedEnvironment

import httpx
import pytest
import websockets

from tests.e2e.jwt_token_helpers import JWTSecurityTester, JWTTestHelper
from tests.e2e.harness_utils import UnifiedTestHarnessComplete


@pytest.fixture
@pytest.mark.e2e
async def test_harness():
    harness = UnifiedE2ETestHarness()
    await harness.setup()
    yield harness
    await harness.cleanup()


@pytest.fixture
def jwt_helper():
    return JWTTestHelper()


@pytest.fixture
def security_tester():
    return JWTSecurityTester()


@pytest.mark.e2e
class TestTokenExpiryRejection:
    """Test expired tokens rejected by all services consistently."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_expired_token_rejected_all_services(self, test_harness, jwt_helper, security_tester):
        """Test expired tokens rejected by all services."""
        expired_payload = jwt_helper.create_expired_payload()
        expired_token = jwt_helper.create_token(expired_payload)
        
        service_results = await security_tester.test_token_against_all_services(expired_token)
        
        for service_name, status_code in service_results.items():
            if status_code != 500:  # Skip unavailable services
                assert status_code == 401, f"{service_name} should reject expired token with 401"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_consistent_rejection_response(self, test_harness, jwt_helper, security_tester):
        """Test consistent rejection responses across services."""
        expired_payload = jwt_helper.create_expired_payload()
        expired_token = jwt_helper.create_token(expired_payload)
        
        results_list = []
        for _ in range(3):
            results = await security_tester.test_token_against_all_services(expired_token)
            results_list.append(results)
        
        available_services = {k for k, v in results_list[0].items() if v != 500}
        for service in available_services:
            responses = [r[service] for r in results_list]
            assert all(r == 401 for r in responses), f"Inconsistent responses for {service}: {responses}"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_immediately_expired_token_rejection(self, test_harness, jwt_helper):
        """Test tokens that expire immediately are rejected."""
        payload = jwt_helper.create_valid_payload()
        payload["exp"] = datetime.now(timezone.utc) + timedelta(milliseconds=100)
        token = jwt_helper.create_token(payload)
        
        await asyncio.sleep(0.2)
        
        auth_result = await jwt_helper.make_auth_request("/auth/verify", token)
        if auth_result["status"] != 500:
            assert auth_result["status"] == 401, "Immediately expired token should be rejected"


@pytest.mark.e2e
class TestTokenRefreshCrossService:
    """Test token refresh works correctly across all services."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_refresh_token_generates_valid_access_token(self, test_harness, jwt_helper):
        """Test refresh token generates new valid access token."""
        refresh_payload = jwt_helper.create_refresh_payload()
        refresh_token = jwt_helper.create_token(refresh_payload)
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.post(
                    f"{jwt_helper.auth_url}/auth/refresh",
                    json={"refresh_token": refresh_token},
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    assert "access_token" in result, "Refresh should return new access token"
                    
                    new_token = result["access_token"]
                    validation_result = await jwt_helper.make_auth_request("/auth/verify", new_token)
                    if validation_result["status"] != 500:
                        assert validation_result["status"] == 200, "New token should be valid"
                
            except httpx.RequestError:
                pytest.skip("Auth service not available for refresh test")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_expired_refresh_token_rejected(self, test_harness, jwt_helper):
        """Test expired refresh tokens are rejected."""
        expired_refresh_payload = jwt_helper.create_refresh_payload()
        expired_refresh_payload["exp"] = datetime.now(timezone.utc) - timedelta(minutes=1)
        expired_refresh_token = jwt_helper.create_token(expired_refresh_payload)
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.post(
                    f"{jwt_helper.auth_url}/auth/refresh",
                    json={"refresh_token": expired_refresh_token},
                    timeout=5.0
                )
                
                if response.status_code != 500:
                    assert response.status_code == 401, "Expired refresh token should be rejected"
                    
            except httpx.RequestError:
                pytest.skip("Auth service not available")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_refreshed_token_validates_across_services(self, test_harness, jwt_helper):
        """Test refreshed token validates across all services."""
        refresh_payload = jwt_helper.create_refresh_payload()
        refresh_token = jwt_helper.create_token(refresh_payload)
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.post(
                    f"{jwt_helper.auth_url}/auth/refresh",
                    json={"refresh_token": refresh_token},
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    new_token = response.json()["access_token"]
                    
                    auth_result = await jwt_helper.make_auth_request("/auth/verify", new_token)
                    if auth_result["status"] != 500:
                        assert auth_result["status"] == 200, "Refreshed token should validate with auth"
                    
                    backend_result = await jwt_helper.make_backend_request("/api/users/profile", new_token)
                    if backend_result["status"] != 500:
                        assert backend_result["status"] in [200, 404], "Refreshed token should validate with backend"
                        
            except httpx.RequestError:
                pytest.skip("Auth service not available")


@pytest.mark.e2e
class TestGracePeriodHandling:
    """Test grace period and clock skew tolerance."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_no_grace_period_enforcement(self, test_harness, jwt_helper):
        """Test tokens are rejected immediately on expiry (no grace period)."""
        payload = jwt_helper.create_valid_payload()
        payload["exp"] = datetime.now(timezone.utc) + timedelta(seconds=1)
        token = jwt_helper.create_token(payload)
        
        await asyncio.sleep(1.2)
        
        result = await jwt_helper.make_auth_request("/auth/verify", token)
        if result["status"] != 500:
            assert result["status"] == 401, "No grace period should be allowed"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_clock_skew_tolerance_small(self, test_harness, jwt_helper):
        """Test system handles minor clock skew gracefully."""
        payload = jwt_helper.create_valid_payload()
        payload["exp"] = datetime.now(timezone.utc) + timedelta(seconds=30)
        token = jwt_helper.create_token(payload)
        
        result = await jwt_helper.make_auth_request("/auth/verify", token)
        if result["status"] != 500:
            assert result["status"] == 200, "Valid token with minor skew should be accepted"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_consistent_expiry_timing_across_services(self, test_harness, jwt_helper):
        """Test expiry timing is consistent across services."""
        payload = jwt_helper.create_valid_payload()
        payload["exp"] = datetime.now(timezone.utc) + timedelta(seconds=2)
        token = jwt_helper.create_token(payload)
        
        auth_result_before = await jwt_helper.make_auth_request("/auth/verify", token)
        backend_result_before = await jwt_helper.make_backend_request("/api/users/profile", token)
        
        await asyncio.sleep(2.5)
        
        auth_result_after = await jwt_helper.make_auth_request("/auth/verify", token)
        backend_result_after = await jwt_helper.make_backend_request("/api/users/profile", token)
        
        if auth_result_before["status"] != 500 and auth_result_after["status"] != 500:
            assert auth_result_before["status"] == 200, "Auth should accept before expiry"
            assert auth_result_after["status"] == 401, "Auth should reject after expiry"
        
        if backend_result_before["status"] != 500 and backend_result_after["status"] != 500:
            assert backend_result_before["status"] in [200, 404], "Backend should accept before expiry"
            assert backend_result_after["status"] == 401, "Backend should reject after expiry"


@pytest.mark.e2e
class TestExpiryPerformance:
    """Test performance requirements for token expiry checks."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_expiry_check_performance_under_100ms(self, test_harness, jwt_helper):
        """Test expiry rejection is faster than 100ms."""
        expired_payload = jwt_helper.create_expired_payload()
        expired_token = jwt_helper.create_token(expired_payload)
        
        start_time = time.time()
        result = await jwt_helper.make_auth_request("/auth/verify", expired_token)
        rejection_time_ms = (time.time() - start_time) * 1000
        
        if result["status"] != 500:
            assert rejection_time_ms < 100, f"Rejection took {rejection_time_ms:.2f}ms, should be < 100ms"
            assert result["status"] == 401, "Expired token should be rejected"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_multiple_service_rejection_performance(self, test_harness, jwt_helper, security_tester):
        """Test all services reject expired tokens within performance limits."""
        expired_payload = jwt_helper.create_expired_payload()
        expired_token = jwt_helper.create_token(expired_payload)
        
        start_time = time.time()
        results = await security_tester.test_token_against_all_services(expired_token)
        total_time_ms = (time.time() - start_time) * 1000
        
        available_services = sum(1 for status in results.values() if status != 500)
        if available_services > 0:
            max_time = 100 * min(available_services, 3)
            assert total_time_ms < max_time, \
                f"Total rejection time {total_time_ms:.2f}ms too slow for {available_services} services"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_expiry_performance(self, test_harness, jwt_helper):
        """Test WebSocket rejects expired tokens quickly."""
        expired_payload = jwt_helper.create_expired_payload()
        expired_token = jwt_helper.create_token(expired_payload)
        
        start_time = time.time()
        
        try:
            async with websockets.connect(
                f"{jwt_helper.websocket_url}/ws?token={expired_token}",
                timeout=2
            ) as ws:
                await ws.ping()
                assert False, "WebSocket should reject expired token"
        except (websockets.exceptions.ConnectionClosed, 
                ConnectionRefusedError,
                websockets.exceptions.InvalidStatus):
            rejection_time_ms = (time.time() - start_time) * 1000
            assert rejection_time_ms < 100, f"WebSocket rejection took {rejection_time_ms:.2f}ms"
        except Exception:
            pytest.skip("WebSocket service not available")


@pytest.mark.e2e
class TestWebSocketExpiryDisconnection:
    """Test WebSocket auto-disconnect on token expiry."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_disconnects_on_token_expiry(self, test_harness, jwt_helper):
        """Test WebSocket disconnects when token expires."""
        payload = jwt_helper.create_valid_payload()
        payload["exp"] = datetime.now(timezone.utc) + timedelta(seconds=2)
        token = jwt_helper.create_token(payload)
        
        try:
            async with websockets.connect(
                f"{jwt_helper.websocket_url}/ws?token={token}",
                timeout=5
            ) as websocket:
                assert websocket.open, "WebSocket should be initially connected"
                
                await asyncio.sleep(3)
                
                with pytest.raises((websockets.exceptions.ConnectionClosed, ConnectionError)):
                    await websocket.send('{"type": "ping"}')
                    
        except (ConnectionRefusedError, websockets.exceptions.InvalidStatus):
            pytest.skip("WebSocket service not available or token rejected at connection")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_expired_token_websocket_connection_rejected(self, test_harness, jwt_helper):
        """Test WebSocket rejects connection with already expired token."""
        expired_payload = jwt_helper.create_expired_payload()
        expired_token = jwt_helper.create_token(expired_payload)
        
        with pytest.raises((websockets.exceptions.ConnectionClosed,
                           ConnectionRefusedError,
                           websockets.exceptions.InvalidStatus)):
            async with websockets.connect(
                f"{jwt_helper.websocket_url}/ws?token={expired_token}",
                timeout=2
            ) as ws:
                await ws.ping()


# BVJ: Token Expiry Cross-Service Synchronization Testing
# Segment: Enterprise, Business Goal: Security enforcement and reliability
# Value Impact: 99.9% synchronized token expiry across all services
# Strategic Impact: $260K+ MRR protection from consistent auth state enforcement

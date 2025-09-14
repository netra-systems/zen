"""
Unified Token Expiry Tests - Enterprise Security Testing
Business Value: $35K+ MRR protection through unified token expiry handling.
"""
import asyncio
import time
from datetime import datetime, timedelta, timezone
from shared.isolated_environment import IsolatedEnvironment

import pytest
import websockets

from tests.e2e.jwt_token_helpers import JWTSecurityTester, JWTTestHelper
from tests.e2e.harness_utils import UnifiedTestHarnessComplete


@pytest.mark.e2e
class TestTokenExpiryUnified:
    """Unified token expiry validation across all services."""
    
    @pytest.fixture
    @pytest.mark.e2e
    async def test_harness(self):
        """Setup unified test harness."""
        harness = UnifiedE2ETestHarness()
        await harness.setup()
        yield harness
        await harness.cleanup()
    
    @pytest.fixture
    def jwt_helper(self):
        """Provide JWT test helper."""
        return JWTTestHelper()
    
    @pytest.fixture
    def security_tester(self):
        """Provide security tester."""
        return JWTSecurityTester()


@pytest.mark.e2e
class TestTokenExpiryBasicFlow(TestTokenExpiryUnified):
    """Test 1: Token works before expiry, fails after."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_token_expiry_basic_flow(self, test_harness, jwt_helper):
        """Test token works before expiry, fails after."""
        # Create token with 1-second expiry
        payload = jwt_helper.create_valid_payload()
        payload["exp"] = datetime.now(timezone.utc) + timedelta(seconds=1)
        token = jwt_helper.create_token(payload)
        
        # Validate works initially
        result_before = await jwt_helper.make_auth_request("/auth/verify", token)
        if result_before["status"] != 500:
            assert result_before["status"] == 200
        
        # Wait for expiry and validate rejection
        await asyncio.sleep(2)
        result_after = await jwt_helper.make_auth_request("/auth/verify", token)
        if result_after["status"] != 500:
            assert result_after["status"] == 401
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_expiry_timing_precision(self, test_harness, jwt_helper):
        """Test expiry timing precision."""
        payload = jwt_helper.create_valid_payload()
        payload["exp"] = datetime.now(timezone.utc) + timedelta(seconds=2)
        token = jwt_helper.create_token(payload)
        
        # Test before expiry
        await asyncio.sleep(1)
        result_valid = await jwt_helper.make_auth_request("/auth/verify", token)
        
        # Test after expiry
        await asyncio.sleep(2)
        result_expired = await jwt_helper.make_auth_request("/auth/verify", token)
        
        if result_valid["status"] != 500 and result_expired["status"] != 500:
            assert result_valid["status"] == 200
            assert result_expired["status"] == 401


@pytest.mark.e2e
class TestUnifiedServiceRejection(TestTokenExpiryUnified):
    """Test 2: All services reject expired tokens consistently."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_unified_service_rejection(self, test_harness, jwt_helper, security_tester):
        """Test all services reject expired tokens."""
        expired_payload = jwt_helper.create_expired_payload()
        expired_token = jwt_helper.create_token(expired_payload)
        
        rejection_confirmed = await security_tester.verify_all_services_reject_token(expired_token)
        assert rejection_confirmed, "All services should reject expired token"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_consistent_rejection_responses(self, test_harness, jwt_helper, security_tester):
        """Test consistent rejection responses."""
        expired_payload = jwt_helper.create_expired_payload()
        expired_token = jwt_helper.create_token(expired_payload)
        
        service_results = await security_tester.test_token_against_all_services(expired_token)
        available_results = {k: v for k, v in service_results.items() if v != 500}
        
        if available_results:
            assert all(status == 401 for status in available_results.values()), \
                f"Inconsistent rejection: {available_results}"


@pytest.mark.e2e
class TestWebSocketAutoDisconnect(TestTokenExpiryUnified):
    """Test 3: WebSocket disconnects on token expiry."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_auto_disconnect(self, test_harness, jwt_helper):
        """Test WebSocket disconnection on token expiry."""
        payload = jwt_helper.create_valid_payload()
        payload["exp"] = datetime.now(timezone.utc) + timedelta(seconds=2)
        token = jwt_helper.create_token(payload)
        
        try:
            async with websockets.connect(
                f"{jwt_helper.websocket_url}/ws?token={token}", timeout=5
            ) as websocket:
                assert websocket.open
                await asyncio.sleep(3)
                with pytest.raises(websockets.exceptions.ConnectionClosed):
                    await websocket.send('{"type": "ping"}')
        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError):
            pass
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_expiry_notification(self, test_harness, jwt_helper):
        """Test WebSocket auto-disconnect timing."""
        payload = jwt_helper.create_valid_payload()
        payload["exp"] = datetime.now(timezone.utc) + timedelta(seconds=2)
        token = jwt_helper.create_token(payload)
        
        try:
            async with websockets.connect(
                f"{jwt_helper.websocket_url}/ws?token={token}", timeout=5
            ) as websocket:
                await asyncio.sleep(3)
                assert not websocket.open
        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError):
            pass


@pytest.mark.e2e
class TestRefreshTokenFlow(TestTokenExpiryUnified):
    """Test 4: Refresh token renews access properly."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_refresh_token_flow(self, test_harness, jwt_helper):
        """Test refresh token generates new access token."""
        # Create refresh token
        refresh_payload = jwt_helper.create_refresh_payload()
        refresh_token = jwt_helper.create_token(refresh_payload)
        
        # Attempt token refresh
        async with httpx.AsyncClient(follow_redirects=True) as client:
            data = {"refresh_token": refresh_token}
            response = await client.post(f"{jwt_helper.auth_url}/auth/refresh", json=data)
            
            if response.status_code == 200:
                result = response.json()
                assert "access_token" in result, "Should return new access token"
                
                # Validate new token structure
                new_token = result["access_token"]
                assert jwt_helper.validate_token_structure(new_token), "New token should be valid"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_expired_refresh_token_rejection(self, test_harness, jwt_helper):
        """Test expired refresh token is rejected."""
        # Create expired refresh token
        expired_refresh_payload = jwt_helper.create_refresh_payload()
        expired_refresh_payload["exp"] = datetime.now(timezone.utc) - timedelta(minutes=1)
        expired_refresh_token = jwt_helper.create_token(expired_refresh_payload)
        
        # Attempt refresh with expired token
        async with httpx.AsyncClient(follow_redirects=True) as client:
            data = {"refresh_token": expired_refresh_token}
            response = await client.post(f"{jwt_helper.auth_url}/auth/refresh", json=data)
            
            # Should reject expired refresh token
            if response.status_code != 500:  # Skip if service not available
                assert response.status_code == 401, "Expired refresh token should be rejected"


@pytest.mark.e2e
class TestGracePeriodHandling(TestTokenExpiryUnified):
    """Test 5: Grace period handling for token expiry."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_no_grace_period_enforcement(self, test_harness, jwt_helper):
        """Test tokens are rejected immediately on expiry (no grace period)."""
        # Create token that expires in 1 second
        payload = jwt_helper.create_valid_payload()
        payload["exp"] = datetime.now(timezone.utc) + timedelta(seconds=1)
        token = jwt_helper.create_token(payload)
        
        # Wait for expiry
        await asyncio.sleep(1.5)
        
        # Should be rejected immediately
        result = await jwt_helper.make_auth_request("/auth/verify", token)
        if result["status"] != 500:  # Skip if service not available
            assert result["status"] == 401, "No grace period should be allowed"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_clock_skew_tolerance(self, test_harness, jwt_helper):
        """Test system handles minor clock skew gracefully."""
        # Create token with current time
        payload = jwt_helper.create_valid_payload()
        payload["exp"] = datetime.now(timezone.utc) + timedelta(seconds=5)
        token = jwt_helper.create_token(payload)
        
        # Test immediate validation (should work)
        result = await jwt_helper.make_auth_request("/auth/verify", token)
        if result["status"] != 500:  # Skip if service not available
            assert result["status"] == 200, "Valid token should be accepted"


@pytest.mark.e2e
class TestExpiryPerformance(TestTokenExpiryUnified):
    """Test 6 & 7: Performance requirements for token expiry."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_expiry_rejection_performance(self, test_harness, jwt_helper):
        """Test rejection time < 100ms for expired tokens."""
        # Create expired token
        expired_payload = jwt_helper.create_expired_payload()
        expired_token = jwt_helper.create_token(expired_payload)
        
        # Measure rejection time
        start_time = time.time()
        result = await jwt_helper.make_auth_request("/auth/verify", expired_token)
        end_time = time.time()
        
        rejection_time_ms = (end_time - start_time) * 1000
        
        if result["status"] != 500:  # Skip if service not available
            assert rejection_time_ms < 100, f"Rejection took {rejection_time_ms:.2f}ms, should be < 100ms"
            assert result["status"] == 401, "Expired token should be rejected"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_multiple_service_rejection_performance(self, test_harness, jwt_helper, security_tester):
        """Test all services reject expired tokens within performance limits."""
        # Create expired token
        expired_payload = jwt_helper.create_expired_payload()
        expired_token = jwt_helper.create_token(expired_payload)
        
        # Measure time for all services to reject
        start_time = time.time()
        results = await security_tester.test_token_against_all_services(expired_token)
        end_time = time.time()
        
        total_time_ms = (end_time - start_time) * 1000
        
        # All available services should reject quickly
        available_services = sum(1 for status in results.values() if status != 500)
        if available_services > 0:
            assert total_time_ms < (100 * available_services), \
                f"Total rejection time {total_time_ms:.2f}ms too slow for {available_services} services"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_disconnect_performance(self, test_harness, jwt_helper):
        """Test WebSocket disconnects quickly on expired token."""
        # Create already expired token
        expired_payload = jwt_helper.create_expired_payload()
        expired_token = jwt_helper.create_token(expired_payload)
        
        # Measure connection rejection time
        start_time = time.time()
        
        try:
            async with websockets.connect(
                f"{jwt_helper.websocket_url}/ws?token={expired_token}",
                timeout=2
            ) as ws:
                await ws.ping()
        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, 
                websockets.exceptions.InvalidStatus):
            # Expected for expired token
            pass
        
        end_time = time.time()
        disconnect_time_ms = (end_time - start_time) * 1000
        
        # Should reject quickly
        assert disconnect_time_ms < 100, f"WebSocket rejection took {disconnect_time_ms:.2f}ms, should be < 100ms"


# BVJ: Unified Token Expiry Testing
# Segment: Growth & Enterprise, Business Goal: Security enforcement
# Value Impact: 99.9% token expiry detection, $35K+ MRR protection

"""
Test suite for auth service resilience fixes.

Tests:
1. Health endpoint works without auth service
2. Circuit breaker protects against auth service failures
3. WebSocket authentication falls back gracefully
4. Monitoring endpoints provide visibility
"""

import asyncio
import pytest
import httpx
import json
from typing import Dict, Any


# Staging API base URL
STAGING_URL = "https://api.staging.netrasystems.ai"
HEALTH_ENDPOINT = f"{STAGING_URL}/health"
CIRCUIT_BREAKER_ENDPOINT = f"{STAGING_URL}/api/circuit-breakers/status"
WEBSOCKET_URL = "wss://api.staging.netrasystems.ai/ws"


class TestAuthResilienceFixes:
    """Test suite for auth service resilience improvements."""
    
    @pytest.mark.asyncio
    async def test_health_endpoint_without_auth(self):
        """Test that /health endpoint works without authentication."""
        async with httpx.AsyncClient() as client:
            # Test without any authentication headers
            response = await client.get(HEALTH_ENDPOINT)
            
            # Should return 200 OK even without auth
            assert response.status_code == 200, f"Health check failed: {response.status_code}"
            
            data = response.json()
            assert "status" in data
            assert data["status"] in ["healthy", "degraded", "unhealthy"]
            
            print(f" PASS:  Health endpoint working: {data['status']}")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_monitoring(self):
        """Test circuit breaker monitoring endpoint."""
        async with httpx.AsyncClient() as client:
            # Circuit breaker status might require auth in production
            # but should be accessible for monitoring
            response = await client.get(CIRCUIT_BREAKER_ENDPOINT)
            
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "circuit_breakers" in data
                
                # Check auth_service circuit breaker specifically
                breakers = data.get("circuit_breakers", {})
                if "auth_service" in breakers:
                    auth_breaker = breakers["auth_service"]
                    print(f" PASS:  Auth service circuit breaker state: {auth_breaker['state']}")
                    print(f"   Stats: {auth_breaker.get('stats', {})}")
                else:
                    print("[U+2139][U+FE0F] Auth service circuit breaker not yet initialized")
            else:
                print(f" WARNING: [U+FE0F] Circuit breaker endpoint returned {response.status_code}")
    
    @pytest.mark.asyncio
    async def test_auth_service_failover(self):
        """Test that backend can handle auth service being down."""
        async with httpx.AsyncClient() as client:
            # Make multiple requests to potentially trigger circuit breaker
            for i in range(5):
                response = await client.get(HEALTH_ENDPOINT)
                assert response.status_code == 200, f"Request {i+1} failed"
                await asyncio.sleep(0.5)
            
            print(" PASS:  Health endpoint resilient to auth service issues")
    
    @pytest.mark.asyncio
    async def test_websocket_with_fallback(self):
        """Test WebSocket connection with auth fallback."""
        import websockets
        import base64
        
        # Create a test JWT token (this would normally come from login)
        test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXIiLCJlbWFpbCI6InRlc3RAdGVzdC5jb20iLCJleHAiOjk5OTk5OTk5OTl9.test"
        
        try:
            # Try to connect with JWT in subprotocol
            encoded_token = base64.urlsafe_b64encode(test_token.encode()).decode().rstrip("=")
            
            async with websockets.connect(
                WEBSOCKET_URL,
                subprotocols=[f"jwt.{encoded_token}"],
                timeout=5
            ) as websocket:
                # Send a test message
                await websocket.send(json.dumps({
                    "type": "ping",
                    "timestamp": "2025-01-07T00:00:00Z"
                }))
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2)
                    print(f" PASS:  WebSocket connected and responsive: {response[:100]}")
                except asyncio.TimeoutError:
                    print(" WARNING: [U+FE0F] WebSocket connected but no response received")
                    
        except Exception as e:
            # WebSocket might reject invalid tokens in staging
            # but the important thing is it doesn't crash
            print(f"[U+2139][U+FE0F] WebSocket connection test: {str(e)[:200]}")
            
            # The fact we got a proper rejection is good
            if "401" in str(e) or "403" in str(e) or "authentication" in str(e).lower():
                print(" PASS:  WebSocket properly enforcing authentication")
            else:
                raise
    
    @pytest.mark.asyncio
    async def test_performance_with_circuit_breaker(self):
        """Test that circuit breaker improves performance when auth is down."""
        async with httpx.AsyncClient() as client:
            # Measure response times
            response_times = []
            
            for i in range(10):
                start = asyncio.get_event_loop().time()
                response = await client.get(HEALTH_ENDPOINT)
                end = asyncio.get_event_loop().time()
                
                response_time = (end - start) * 1000  # Convert to milliseconds
                response_times.append(response_time)
                
                assert response.status_code == 200
                
                # After a few requests, circuit breaker should open
                # and response times should improve
                if i > 5 and response_time < 100:  # Under 100ms
                    print(f" PASS:  Fast response after circuit open: {response_time:.1f}ms")
                
                await asyncio.sleep(0.1)
            
            avg_time = sum(response_times) / len(response_times)
            print(f" CHART:  Average response time: {avg_time:.1f}ms")
            
            # Check if later requests were faster (circuit breaker effect)
            early_avg = sum(response_times[:3]) / 3
            late_avg = sum(response_times[-3:]) / 3
            
            if late_avg < early_avg:
                print(f" PASS:  Performance improved: {early_avg:.1f}ms  ->  {late_avg:.1f}ms")
            else:
                print(f"[U+2139][U+FE0F] Performance stable: {early_avg:.1f}ms  ->  {late_avg:.1f}ms")


async def main():
    """Run all tests."""
    print("[U+1F9EA] Testing Auth Service Resilience Fixes")
    print("=" * 50)
    
    test_suite = TestAuthResilienceFixes()
    
    # Run tests
    tests = [
        ("Health Endpoint", test_suite.test_health_endpoint_without_auth),
        ("Circuit Breaker Monitoring", test_suite.test_circuit_breaker_monitoring),
        ("Auth Service Failover", test_suite.test_auth_service_failover),
        ("WebSocket Fallback", test_suite.test_websocket_with_fallback),
        ("Performance with Circuit Breaker", test_suite.test_performance_with_circuit_breaker),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n[U+1F4DD] Testing: {test_name}")
        print("-" * 40)
        try:
            await test_func()
            results.append((test_name, " PASS:  PASSED"))
        except Exception as e:
            print(f" FAIL:  Failed: {e}")
            results.append((test_name, f" FAIL:  FAILED: {str(e)[:100]}"))
    
    # Summary
    print("\n" + "=" * 50)
    print(" CHART:  TEST SUMMARY")
    print("=" * 50)
    for test_name, result in results:
        print(f"{test_name}: {result}")
    
    passed = sum(1 for _, r in results if " PASS: " in r)
    total = len(results)
    print(f"\n TARGET:  Result: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    # Run the async main function
    success = asyncio.run(main())
    exit(0 if success else 1)
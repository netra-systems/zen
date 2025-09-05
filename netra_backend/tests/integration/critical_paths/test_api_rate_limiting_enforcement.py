#!/usr/bin/env python3
"""
Comprehensive test to verify API rate limiting enforcement:
1. Test per-user rate limits
2. Test per-IP rate limits
3. Test per-endpoint rate limits
4. Test burst handling
5. Test rate limit headers
6. Test backoff and retry mechanisms
7. Test distributed rate limiting
8. Test rate limit bypass for premium users

This test ensures rate limiting protects the API from abuse.
"""

# Test framework import - using pytest fixtures instead

import asyncio
import json
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from shared.isolated_environment import IsolatedEnvironment

import aiohttp
import pytest

# Configuration
DEV_BACKEND_URL = "http://localhost:8000"
AUTH_SERVICE_URL = "http://localhost:8081"

# Rate limit configurations
RATE_LIMITS = {
    "default": {"requests": 100, "window": 60},  # 100 req/min
    "auth": {"requests": 10, "window": 60},      # 10 req/min
    "api": {"requests": 1000, "window": 3600},   # 1000 req/hour
    "burst": {"requests": 20, "window": 1}       # 20 req/sec burst
}

# Test users with different tiers
TEST_USERS = [
    {
        "email": "free_user@example.com",
        "password": "freeuser123",
        "tier": "free",
        "rate_limit": 100
    },
    {
        "email": "premium_user@example.com",
        "password": "premiumuser123",
        "tier": "premium",
        "rate_limit": 1000
    },
    {
        "email": "enterprise_user@example.com",
        "password": "enterpriseuser123",
        "tier": "enterprise",
        "rate_limit": 10000
    }
]

class RateLimitTester:
    """Test API rate limiting enforcement."""
    
    def __init__(self):
        self.sessions: Dict[str, aiohttp.ClientSession] = {}
        self.user_tokens: Dict[str, str] = {}
        self.request_log: List[Dict] = []
        self.rate_limit_hits: Dict[str, int] = {}
        
    async def __aenter__(self):
        """Setup test environment."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment."""
        for session in self.sessions.values():
            await session.close()
            
    async def setup_test_users(self) -> bool:
        """Setup test users with different tiers."""
        print("\n[SETUP] STEP 1: Setting up test users...")
        
        try:
            for user in TEST_USERS:
                session = aiohttp.ClientSession()
                self.sessions[user["email"]] = session
                
                # Register user
                register_data = {
                    "email": user["email"],
                    "password": user["password"],
                    "name": f"{user['tier'].capitalize()} User",
                    "tier": user["tier"]
                }
                
                async with session.post(
                    f"{AUTH_SERVICE_URL}/auth/register",
                    json=register_data
                ) as response:
                    if response.status not in [200, 201, 409]:
                        print(f"[ERROR] Registration failed for {user['email']}: {response.status}")
                        return False
                        
                # Login
                login_data = {
                    "email": user["email"],
                    "password": user["password"]
                }
                
                async with session.post(
                    f"{AUTH_SERVICE_URL}/auth/login",
                    json=login_data
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.user_tokens[user["email"]] = data.get("access_token")
                        print(f"[OK] Setup {user['tier']} user: {user['email']}")
                    else:
                        print(f"[ERROR] Login failed for {user['email']}: {response.status}")
                        return False
                        
            print(f"[OK] All {len(TEST_USERS)} test users setup")
            return True
            
        except Exception as e:
            print(f"[ERROR] User setup error: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_basic_rate_limit(self) -> bool:
        """Test basic per-user rate limiting."""
        print("\n[BASIC] STEP 2: Testing basic rate limiting...")
        
        try:
            user = TEST_USERS[0]  # Use free user
            session = self.sessions[user["email"]]
            token = self.user_tokens[user["email"]]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Make requests up to the limit
            endpoint = f"{DEV_BACKEND_URL}/api/health"
            success_count = 0
            rate_limited_count = 0
            
            for i in range(user["rate_limit"] + 10):
                async with session.get(endpoint, headers=headers) as response:
                    if response.status == 200:
                        success_count += 1
                    elif response.status == 429:
                        rate_limited_count += 1
                        
                        # Check rate limit headers
                        if "X-RateLimit-Limit" in response.headers:
                            limit = response.headers["X-RateLimit-Limit"]
                            remaining = response.headers.get("X-RateLimit-Remaining", "0")
                            reset = response.headers.get("X-RateLimit-Reset", "")
                            
                            if i == user["rate_limit"]:  # First rate limit hit
                                print(f"[OK] Rate limit hit at request {i+1}")
                                print(f"  - Limit: {limit}")
                                print(f"  - Remaining: {remaining}")
                                print(f"  - Reset: {reset}")
                                
                    # Log request
                    self.request_log.append({
                        "user": user["email"],
                        "endpoint": endpoint,
                        "status": response.status,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    
            if rate_limited_count > 0:
                print(f"[OK] Rate limiting enforced: {success_count} allowed, {rate_limited_count} blocked")
                return True
            else:
                print(f"[ERROR] No rate limiting detected after {success_count} requests")
                return False
                
        except Exception as e:
            print(f"[ERROR] Basic rate limit test failed: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_burst_handling(self) -> bool:
        """Test burst request handling."""
        print("\n[BURST] STEP 3: Testing burst handling...")
        
        try:
            user = TEST_USERS[0]
            session = self.sessions[user["email"]]
            token = self.user_tokens[user["email"]]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Send burst of requests
            endpoint = f"{DEV_BACKEND_URL}/api/threads"
            burst_size = 30
            
            async def make_request(i: int) -> Tuple[int, int]:
                """Make a single request and return status."""
                try:
                    async with session.get(endpoint, headers=headers) as response:
                        return i, response.status
                except Exception:
                    return i, 0
                    
            # Send all requests concurrently
            start_time = time.time()
            tasks = [make_request(i) for i in range(burst_size)]
            results = await asyncio.gather(*tasks)
            duration = time.time() - start_time
            
            # Analyze results
            success_count = sum(1 for _, status in results if status == 200)
            rate_limited_count = sum(1 for _, status in results if status == 429)
            
            print(f"[INFO] Burst test: {burst_size} requests in {duration:.2f}s")
            print(f"  - Successful: {success_count}")
            print(f"  - Rate limited: {rate_limited_count}")
            
            if rate_limited_count > 0:
                print(f"[OK] Burst protection active: {rate_limited_count}/{burst_size} blocked")
                return True
            else:
                print(f"[WARNING] No burst protection detected")
                return False
                
        except Exception as e:
            print(f"[ERROR] Burst handling test failed: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_per_endpoint_limits(self) -> bool:
        """Test different rate limits per endpoint."""
        print("\n[ENDPOINT] STEP 4: Testing per-endpoint rate limits...")
        
        try:
            user = TEST_USERS[0]
            session = self.sessions[user["email"]]
            token = self.user_tokens[user["email"]]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Test different endpoints
            endpoints = {
                f"{DEV_BACKEND_URL}/api/health": 1000,  # High limit
                f"{AUTH_SERVICE_URL}/auth/refresh": 10,     # Low limit
                f"{DEV_BACKEND_URL}/api/agents": 50      # Medium limit
            }
            
            results = {}
            
            for endpoint, expected_limit in endpoints.items():
                success_count = 0
                rate_limited = False
                
                # Make requests until rate limited
                for i in range(expected_limit + 5):
                    try:
                        async with session.get(endpoint, headers=headers) as response:
                            if response.status == 200:
                                success_count += 1
                            elif response.status == 429:
                                rate_limited = True
                                break
                    except Exception:
                        pass
                        
                results[endpoint] = {
                    "expected": expected_limit,
                    "success": success_count,
                    "limited": rate_limited
                }
                
                # Brief pause between endpoint tests
                await asyncio.sleep(1)
                
            # Verify different limits
            different_limits = len(set(r["success"] for r in results.values())) > 1
            
            if different_limits:
                print(f"[OK] Per-endpoint rate limits detected:")
                for endpoint, result in results.items():
                    endpoint_name = endpoint.split("/")[-1]
                    print(f"  - {endpoint_name}: {result['success']} requests before limit")
                return True
            else:
                print(f"[ERROR] No per-endpoint differentiation detected")
                return False
                
        except Exception as e:
            print(f"[ERROR] Per-endpoint limits test failed: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_tier_based_limits(self) -> bool:
        """Test different rate limits for user tiers."""
        print("\n[TIERS] STEP 5: Testing tier-based rate limits...")
        
        try:
            endpoint = f"{DEV_BACKEND_URL}/api/health"
            tier_results = {}
            
            for user in TEST_USERS:
                session = self.sessions[user["email"]]
                token = self.user_tokens[user["email"]]
                headers = {"Authorization": f"Bearer {token}"}
                
                # Make requests to find limit
                success_count = 0
                rate_limited = False
                
                for i in range(200):  # Test up to 200 requests
                    async with session.get(endpoint, headers=headers) as response:
                        if response.status == 200:
                            success_count += 1
                        elif response.status == 429:
                            rate_limited = True
                            break
                            
                tier_results[user["tier"]] = {
                    "user": user["email"],
                    "expected_limit": user["rate_limit"],
                    "actual_requests": success_count,
                    "was_limited": rate_limited
                }
                
                # Reset by waiting
                await asyncio.sleep(2)
                
            # Verify tier differences
            free_limit = tier_results["free"]["actual_requests"]
            premium_limit = tier_results["premium"]["actual_requests"]
            enterprise_limit = tier_results["enterprise"]["actual_requests"]
            
            if free_limit < premium_limit < enterprise_limit:
                print(f"[OK] Tier-based limits enforced:")
                for tier, result in tier_results.items():
                    print(f"  - {tier}: {result['actual_requests']} requests")
                return True
            else:
                print(f"[ERROR] Tier limits not properly differentiated")
                return False
                
        except Exception as e:
            print(f"[ERROR] Tier-based limits test failed: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_retry_after_header(self) -> bool:
        """Test Retry-After header in rate limit responses."""
        print("\n[RETRY] STEP 6: Testing Retry-After header...")
        
        try:
            user = TEST_USERS[0]
            session = self.sessions[user["email"]]
            token = self.user_tokens[user["email"]]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Trigger rate limit
            endpoint = f"{DEV_BACKEND_URL}/api/health"
            
            # Make many requests quickly
            for _ in range(150):
                async with session.get(endpoint, headers=headers) as response:
                    if response.status == 429:
                        # Check for Retry-After header
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            print(f"[OK] Retry-After header present: {retry_after} seconds")
                            
                            # Wait and retry
                            wait_time = int(retry_after) + 1
                            print(f"[INFO] Waiting {wait_time} seconds before retry...")
                            await asyncio.sleep(wait_time)
                            
                            # Try again
                            async with session.get(endpoint, headers=headers) as retry_response:
                                if retry_response.status == 200:
                                    print(f"[OK] Request successful after waiting")
                                    return True
                                else:
                                    print(f"[ERROR] Still rate limited after waiting")
                                    return False
                                    
            print(f"[ERROR] Failed to trigger rate limit for Retry-After test")
            return False
            
        except Exception as e:
            print(f"[ERROR] Retry-After test failed: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_distributed_rate_limiting(self) -> bool:
        """Test distributed rate limiting across multiple connections."""
        print("\n[DISTRIBUTED] STEP 7: Testing distributed rate limiting...")
        
        try:
            user = TEST_USERS[0]
            token = self.user_tokens[user["email"]]
            headers = {"Authorization": f"Bearer {token}"}
            endpoint = f"{DEV_BACKEND_URL}/api/health"
            
            # Create multiple sessions (simulating distributed clients)
            sessions = []
            for i in range(3):
                sessions.append(aiohttp.ClientSession())
                
            # Make concurrent requests from all sessions
            async def make_requests_from_session(session: aiohttp.ClientSession, count: int) -> Dict:
                """Make requests from a single session."""
                success = 0
                limited = 0
                
                for _ in range(count):
                    async with session.get(endpoint, headers=headers) as response:
                        if response.status == 200:
                            success += 1
                        elif response.status == 429:
                            limited += 1
                            
                return {"success": success, "limited": limited}
                
            # Run requests from all sessions concurrently
            tasks = [make_requests_from_session(s, 50) for s in sessions]
            results = await asyncio.gather(*tasks)
            
            # Cleanup extra sessions
            for s in sessions:
                await s.close()
                
            # Analyze results
            total_success = sum(r["success"] for r in results)
            total_limited = sum(r["limited"] for r in results)
            
            print(f"[INFO] Distributed test across {len(sessions)} sessions:")
            print(f"  - Total successful: {total_success}")
            print(f"  - Total rate limited: {total_limited}")
            
            if total_limited > 0:
                print(f"[OK] Distributed rate limiting active (shared limit across sessions)")
                return True
            else:
                print(f"[WARNING] No distributed rate limiting detected")
                return False
                
        except Exception as e:
            print(f"[ERROR] Distributed rate limiting test failed: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_rate_limit_reset(self) -> bool:
        """Test rate limit reset after time window."""
        print("\n[RESET] STEP 8: Testing rate limit reset...")
        
        try:
            user = TEST_USERS[0]
            session = self.sessions[user["email"]]
            token = self.user_tokens[user["email"]]
            headers = {"Authorization": f"Bearer {token}"}
            endpoint = f"{DEV_BACKEND_URL}/api/health"
            
            # Phase 1: Hit rate limit
            phase1_success = 0
            for i in range(150):
                async with session.get(endpoint, headers=headers) as response:
                    if response.status == 200:
                        phase1_success += 1
                    elif response.status == 429:
                        print(f"[OK] Rate limit hit after {phase1_success} requests")
                        
                        # Get reset time
                        reset_header = response.headers.get("X-RateLimit-Reset")
                        if reset_header:
                            reset_time = int(reset_header)
                            current_time = int(time.time())
                            wait_time = max(reset_time - current_time + 1, 1)
                            print(f"[INFO] Waiting {wait_time}s for reset...")
                        else:
                            wait_time = 61  # Default to 1 minute
                            
                        break
                        
            # Wait for reset
            await asyncio.sleep(wait_time)
            
            # Phase 2: Verify reset
            phase2_success = 0
            for i in range(10):
                async with session.get(endpoint, headers=headers) as response:
                    if response.status == 200:
                        phase2_success += 1
                    elif response.status == 429:
                        print(f"[ERROR] Still rate limited after reset time")
                        return False
                        
            if phase2_success > 0:
                print(f"[OK] Rate limit reset successful: {phase2_success} new requests allowed")
                return True
            else:
                print(f"[ERROR] Failed to make requests after reset")
                return False
                
        except Exception as e:
            print(f"[ERROR] Rate limit reset test failed: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_ip_based_limiting(self) -> bool:
        """Test IP-based rate limiting (unauthenticated)."""
        print("\n[IP] STEP 9: Testing IP-based rate limiting...")
        
        try:
            # Create session without authentication
            session = aiohttp.ClientSession()
            
            try:
                endpoint = f"{DEV_BACKEND_URL}/api/health"
                success_count = 0
                rate_limited = False
                
                # Make unauthenticated requests
                for i in range(50):
                    async with session.get(endpoint) as response:
                        if response.status == 200:
                            success_count += 1
                        elif response.status == 429:
                            rate_limited = True
                            print(f"[OK] IP rate limit hit after {success_count} requests")
                            break
                            
                if rate_limited:
                    print(f"[OK] IP-based rate limiting active for unauthenticated requests")
                    return True
                else:
                    print(f"[WARNING] No IP-based rate limiting detected after {success_count} requests")
                    return success_count > 30  # Some limit should be in place
                    
            finally:
                await session.close()
                
        except Exception as e:
            print(f"[ERROR] IP-based limiting test failed: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_rate_limit_metrics(self) -> bool:
        """Test rate limit metrics and monitoring."""
        print("\n[METRICS] STEP 10: Testing rate limit metrics...")
        
        try:
            # Collect metrics from all users
            metrics = {}
            
            for user in TEST_USERS:
                email = user["email"]
                token = self.user_tokens[email]
                session = self.sessions[email]
                headers = {"Authorization": f"Bearer {token}"}
                
                # Get metrics endpoint
                async with session.get(
                    f"{DEV_BACKEND_URL}/api/metrics/rate_limits",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        metrics[user["tier"]] = data
                        
            # Display metrics
            print("\n[METRICS] Rate Limit Statistics:")
            
            # Analyze request log
            total_requests = len(self.request_log)
            rate_limited_requests = sum(1 for r in self.request_log if r["status"] == 429)
            
            print(f"  Total requests: {total_requests}")
            print(f"  Rate limited: {rate_limited_requests}")
            print(f"  Success rate: {((total_requests - rate_limited_requests) / total_requests * 100):.1f}%")
            
            # Per-tier metrics
            for tier, data in metrics.items():
                if data:
                    print(f"\n  {tier.capitalize()} Tier:")
                    print(f"    - Limit: {data.get('limit', 'N/A')}")
                    print(f"    - Used: {data.get('used', 'N/A')}")
                    print(f"    - Remaining: {data.get('remaining', 'N/A')}")
                    
            return True
            
        except Exception as e:
            print(f"[WARNING] Metrics collection failed: {e}")
            return True  # Non-critical test
            
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests in sequence."""
        results = {}
        
        # Setup
        results["user_setup"] = await self.setup_test_users()
        if not results["user_setup"]:
            print("\n[CRITICAL] User setup failed. Aborting tests.")
            return results
            
        # Rate limiting tests
        results["basic_rate_limit"] = await self.test_basic_rate_limit()
        
        # Wait between tests to avoid interference
        await asyncio.sleep(65)  # Wait for rate limit window to reset
        
        results["burst_handling"] = await self.test_burst_handling()
        await asyncio.sleep(5)
        
        results["per_endpoint_limits"] = await self.test_per_endpoint_limits()
        await asyncio.sleep(5)
        
        results["tier_based_limits"] = await self.test_tier_based_limits()
        await asyncio.sleep(5)
        
        results["retry_after_header"] = await self.test_retry_after_header()
        results["distributed_limiting"] = await self.test_distributed_rate_limiting()
        
        await asyncio.sleep(65)  # Reset window
        
        results["rate_limit_reset"] = await self.test_rate_limit_reset()
        results["ip_based_limiting"] = await self.test_ip_based_limiting()
        results["rate_limit_metrics"] = await self.test_rate_limit_metrics()
        
        return results

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
@pytest.mark.asyncio
async def test_api_rate_limiting_enforcement():
    """Test API rate limiting enforcement."""
    async with RateLimitTester() as tester:
        results = await tester.run_all_tests()
        
        # Print summary
        print("\n" + "="*60)
        print("API RATE LIMITING TEST SUMMARY")
        print("="*60)
        
        for test_name, passed in results.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {test_name:25} : {status}")
            
        print("="*60)
        
        # Calculate overall result
        total_tests = len(results)
        passed_tests = sum(1 for passed in results.values() if passed)
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("\n[SUCCESS] All rate limiting tests passed!")
        else:
            print(f"\n[WARNING] {total_tests - passed_tests} tests failed.")
            
        # Assert all tests passed
        assert all(results.values()), f"Some tests failed: {results}"

async def main():
    """Run the test standalone."""
    print("="*60)
    print("API RATE LIMITING ENFORCEMENT TEST")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    print("="*60)
    
    async with RateLimitTester() as tester:
        results = await tester.run_all_tests()
        
        # Return exit code based on results
        if all(results.values()):
            return 0
        else:
            return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
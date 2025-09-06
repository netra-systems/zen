#!/usr/bin/env python3
# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Comprehensive test to verify API rate limiting enforcement:
    # REMOVED_SYNTAX_ERROR: 1. Test per-user rate limits
    # REMOVED_SYNTAX_ERROR: 2. Test per-IP rate limits
    # REMOVED_SYNTAX_ERROR: 3. Test per-endpoint rate limits
    # REMOVED_SYNTAX_ERROR: 4. Test burst handling
    # REMOVED_SYNTAX_ERROR: 5. Test rate limit headers
    # REMOVED_SYNTAX_ERROR: 6. Test backoff and retry mechanisms
    # REMOVED_SYNTAX_ERROR: 7. Test distributed rate limiting
    # REMOVED_SYNTAX_ERROR: 8. Test rate limit bypass for premium users

    # REMOVED_SYNTAX_ERROR: This test ensures rate limiting protects the API from abuse.
    # REMOVED_SYNTAX_ERROR: """"

    # Test framework import - using pytest fixtures instead

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: import random
    # REMOVED_SYNTAX_ERROR: import sys
    # REMOVED_SYNTAX_ERROR: import time
    # REMOVED_SYNTAX_ERROR: from datetime import datetime, timedelta, timezone
    # REMOVED_SYNTAX_ERROR: from pathlib import Path
    # REMOVED_SYNTAX_ERROR: from typing import Any, Dict, List, Optional, Tuple
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: import aiohttp
    # REMOVED_SYNTAX_ERROR: import pytest

    # Configuration
    # REMOVED_SYNTAX_ERROR: DEV_BACKEND_URL = "http://localhost:8000"
    # REMOVED_SYNTAX_ERROR: AUTH_SERVICE_URL = "http://localhost:8081"

    # Rate limit configurations
    # REMOVED_SYNTAX_ERROR: RATE_LIMITS = { )
    # REMOVED_SYNTAX_ERROR: "default": {"requests": 100, "window": 60},  # 100 req/min
    # REMOVED_SYNTAX_ERROR: "auth": {"requests": 10, "window": 60},      # 10 req/min
    # REMOVED_SYNTAX_ERROR: "api": {"requests": 1000, "window": 3600},   # 1000 req/hour
    # REMOVED_SYNTAX_ERROR: "burst": {"requests": 20, "window": 1}       # 20 req/sec burst
    

    # Test users with different tiers
    # REMOVED_SYNTAX_ERROR: TEST_USERS = [ )
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "email": "free_user@example.com",
    # REMOVED_SYNTAX_ERROR: "password": "freeuser123",
    # REMOVED_SYNTAX_ERROR: "tier": "free",
    # REMOVED_SYNTAX_ERROR: "rate_limit": 100
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "email": "premium_user@example.com",
    # REMOVED_SYNTAX_ERROR: "password": "premiumuser123",
    # REMOVED_SYNTAX_ERROR: "tier": "premium",
    # REMOVED_SYNTAX_ERROR: "rate_limit": 1000
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "email": "enterprise_user@example.com",
    # REMOVED_SYNTAX_ERROR: "password": "enterpriseuser123",
    # REMOVED_SYNTAX_ERROR: "tier": "enterprise",
    # REMOVED_SYNTAX_ERROR: "rate_limit": 10000
    
    

# REMOVED_SYNTAX_ERROR: class RateLimitTester:
    # REMOVED_SYNTAX_ERROR: """Test API rate limiting enforcement."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: self.sessions: Dict[str, aiohttp.ClientSession] = {]
    # REMOVED_SYNTAX_ERROR: self.user_tokens: Dict[str, str] = {]
    # REMOVED_SYNTAX_ERROR: self.request_log: List[Dict] = []
    # REMOVED_SYNTAX_ERROR: self.rate_limit_hits: Dict[str, int] = {]

# REMOVED_SYNTAX_ERROR: async def __aenter__(self):
    # REMOVED_SYNTAX_ERROR: """Setup test environment."""
    # REMOVED_SYNTAX_ERROR: return self

# REMOVED_SYNTAX_ERROR: async def __aexit__(self, exc_type, exc_val, exc_tb):
    # REMOVED_SYNTAX_ERROR: """Cleanup test environment."""
    # REMOVED_SYNTAX_ERROR: for session in self.sessions.values():
        # REMOVED_SYNTAX_ERROR: await session.close()

# REMOVED_SYNTAX_ERROR: async def setup_test_users(self) -> bool:
    # REMOVED_SYNTAX_ERROR: """Setup test users with different tiers."""
    # REMOVED_SYNTAX_ERROR: print("\n[SETUP] STEP 1: Setting up test users...")

    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: for user in TEST_USERS:
            # REMOVED_SYNTAX_ERROR: session = aiohttp.ClientSession()
            # REMOVED_SYNTAX_ERROR: self.sessions[user["email"]] = session

            # Register user
            # REMOVED_SYNTAX_ERROR: register_data = { )
            # REMOVED_SYNTAX_ERROR: "email": user["email"],
            # REMOVED_SYNTAX_ERROR: "password": user["password"],
            # REMOVED_SYNTAX_ERROR: "name": "formatted_string"{AUTH_SERVICE_URL}/auth/register",
            # REMOVED_SYNTAX_ERROR: json=register_data
            # REMOVED_SYNTAX_ERROR: ) as response:
                # REMOVED_SYNTAX_ERROR: if response.status not in [200, 201, 409]:
                    # REMOVED_SYNTAX_ERROR: print("formatted_string"{AUTH_SERVICE_URL}/auth/login",
                    # REMOVED_SYNTAX_ERROR: json=login_data
                    # REMOVED_SYNTAX_ERROR: ) as response:
                        # REMOVED_SYNTAX_ERROR: if response.status == 200:
                            # REMOVED_SYNTAX_ERROR: data = await response.json()
                            # REMOVED_SYNTAX_ERROR: self.user_tokens[user["email"]] = data.get("access_token")
                            # REMOVED_SYNTAX_ERROR: print("formatted_string"}

                                            # Make requests up to the limit
                                            # REMOVED_SYNTAX_ERROR: endpoint = "formatted_string"
                                            # REMOVED_SYNTAX_ERROR: success_count = 0
                                            # REMOVED_SYNTAX_ERROR: rate_limited_count = 0

                                            # REMOVED_SYNTAX_ERROR: for i in range(user["rate_limit"] + 10):
                                                # REMOVED_SYNTAX_ERROR: async with session.get(endpoint, headers=headers) as response:
                                                    # REMOVED_SYNTAX_ERROR: if response.status == 200:
                                                        # REMOVED_SYNTAX_ERROR: success_count += 1
                                                        # REMOVED_SYNTAX_ERROR: elif response.status == 429:
                                                            # REMOVED_SYNTAX_ERROR: rate_limited_count += 1

                                                            # Check rate limit headers
                                                            # REMOVED_SYNTAX_ERROR: if "X-RateLimit-Limit" in response.headers:
                                                                # REMOVED_SYNTAX_ERROR: limit = response.headers["X-RateLimit-Limit"]
                                                                # REMOVED_SYNTAX_ERROR: remaining = response.headers.get("X-RateLimit-Remaining", "0")
                                                                # REMOVED_SYNTAX_ERROR: reset = response.headers.get("X-RateLimit-Reset", "")

                                                                # REMOVED_SYNTAX_ERROR: if i == user["rate_limit"]:  # First rate limit hit
                                                                # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                                                # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                                                # REMOVED_SYNTAX_ERROR: print("formatted_string")

                                                                # Log request
                                                                # REMOVED_SYNTAX_ERROR: self.request_log.append({ ))
                                                                # REMOVED_SYNTAX_ERROR: "user": user["email"],
                                                                # REMOVED_SYNTAX_ERROR: "endpoint": endpoint,
                                                                # REMOVED_SYNTAX_ERROR: "status": response.status,
                                                                # REMOVED_SYNTAX_ERROR: "timestamp": datetime.now(timezone.utc).isoformat()
                                                                

                                                                # REMOVED_SYNTAX_ERROR: if rate_limited_count > 0:
                                                                    # REMOVED_SYNTAX_ERROR: print("formatted_string"}

                                                                                    # Send burst of requests
                                                                                    # REMOVED_SYNTAX_ERROR: endpoint = "formatted_string"
                                                                                    # REMOVED_SYNTAX_ERROR: burst_size = 30

# REMOVED_SYNTAX_ERROR: async def make_request(i: int) -> Tuple[int, int]:
    # REMOVED_SYNTAX_ERROR: """Make a single request and return status."""
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: async with session.get(endpoint, headers=headers) as response:
            # REMOVED_SYNTAX_ERROR: return i, response.status
            # REMOVED_SYNTAX_ERROR: except Exception:
                # REMOVED_SYNTAX_ERROR: return i, 0

                # Send all requests concurrently
                # REMOVED_SYNTAX_ERROR: start_time = time.time()
                # REMOVED_SYNTAX_ERROR: tasks = [make_request(i) for i in range(burst_size)]
                # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks)
                # REMOVED_SYNTAX_ERROR: duration = time.time() - start_time

                # Analyze results
                # REMOVED_SYNTAX_ERROR: success_count = sum(1 for _, status in results if status == 200)
                # REMOVED_SYNTAX_ERROR: rate_limited_count = sum(1 for _, status in results if status == 429)

                # REMOVED_SYNTAX_ERROR: print("formatted_string")
                # REMOVED_SYNTAX_ERROR: print("formatted_string")

                # REMOVED_SYNTAX_ERROR: if rate_limited_count > 0:
                    # REMOVED_SYNTAX_ERROR: print("formatted_string"}

                                    # Test different endpoints
                                    # REMOVED_SYNTAX_ERROR: endpoints = { )
                                    # REMOVED_SYNTAX_ERROR: "formatted_string": 1000,  # High limit
                                    # REMOVED_SYNTAX_ERROR: "formatted_string": 10,     # Low limit
                                    # REMOVED_SYNTAX_ERROR: "formatted_string": 50      # Medium limit
                                    

                                    # REMOVED_SYNTAX_ERROR: results = {}

                                    # REMOVED_SYNTAX_ERROR: for endpoint, expected_limit in endpoints.items():
                                        # REMOVED_SYNTAX_ERROR: success_count = 0
                                        # REMOVED_SYNTAX_ERROR: rate_limited = False

                                        # Make requests until rate limited
                                        # REMOVED_SYNTAX_ERROR: for i in range(expected_limit + 5):
                                            # REMOVED_SYNTAX_ERROR: try:
                                                # REMOVED_SYNTAX_ERROR: async with session.get(endpoint, headers=headers) as response:
                                                    # REMOVED_SYNTAX_ERROR: if response.status == 200:
                                                        # REMOVED_SYNTAX_ERROR: success_count += 1
                                                        # REMOVED_SYNTAX_ERROR: elif response.status == 429:
                                                            # REMOVED_SYNTAX_ERROR: rate_limited = True
                                                            # REMOVED_SYNTAX_ERROR: break
                                                            # REMOVED_SYNTAX_ERROR: except Exception:
                                                                # REMOVED_SYNTAX_ERROR: pass

                                                                # REMOVED_SYNTAX_ERROR: results[endpoint] = { )
                                                                # REMOVED_SYNTAX_ERROR: "expected": expected_limit,
                                                                # REMOVED_SYNTAX_ERROR: "success": success_count,
                                                                # REMOVED_SYNTAX_ERROR: "limited": rate_limited
                                                                

                                                                # Brief pause between endpoint tests
                                                                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(1)

                                                                # Verify different limits
                                                                # REMOVED_SYNTAX_ERROR: different_limits = len(set(r["success"] for r in results.values())) > 1

                                                                # REMOVED_SYNTAX_ERROR: if different_limits:
                                                                    # REMOVED_SYNTAX_ERROR: print(f"[OK] Per-endpoint rate limits detected:")
                                                                    # REMOVED_SYNTAX_ERROR: for endpoint, result in results.items():
                                                                        # REMOVED_SYNTAX_ERROR: endpoint_name = endpoint.split("/")[-1]
                                                                        # REMOVED_SYNTAX_ERROR: print("formatted_string"
                                                                                        # REMOVED_SYNTAX_ERROR: tier_results = {}

                                                                                        # REMOVED_SYNTAX_ERROR: for user in TEST_USERS:
                                                                                            # REMOVED_SYNTAX_ERROR: session = self.sessions[user["email"]]
                                                                                            # REMOVED_SYNTAX_ERROR: token = self.user_tokens[user["email"]]
                                                                                            # REMOVED_SYNTAX_ERROR: headers = {"Authorization": "formatted_string"}

                                                                                            # Make requests to find limit
                                                                                            # REMOVED_SYNTAX_ERROR: success_count = 0
                                                                                            # REMOVED_SYNTAX_ERROR: rate_limited = False

                                                                                            # REMOVED_SYNTAX_ERROR: for i in range(200):  # Test up to 200 requests
                                                                                            # REMOVED_SYNTAX_ERROR: async with session.get(endpoint, headers=headers) as response:
                                                                                                # REMOVED_SYNTAX_ERROR: if response.status == 200:
                                                                                                    # REMOVED_SYNTAX_ERROR: success_count += 1
                                                                                                    # REMOVED_SYNTAX_ERROR: elif response.status == 429:
                                                                                                        # REMOVED_SYNTAX_ERROR: rate_limited = True
                                                                                                        # REMOVED_SYNTAX_ERROR: break

                                                                                                        # REMOVED_SYNTAX_ERROR: tier_results[user["tier"]] = { )
                                                                                                        # REMOVED_SYNTAX_ERROR: "user": user["email"],
                                                                                                        # REMOVED_SYNTAX_ERROR: "expected_limit": user["rate_limit"],
                                                                                                        # REMOVED_SYNTAX_ERROR: "actual_requests": success_count,
                                                                                                        # REMOVED_SYNTAX_ERROR: "was_limited": rate_limited
                                                                                                        

                                                                                                        # Reset by waiting
                                                                                                        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(2)

                                                                                                        # Verify tier differences
                                                                                                        # REMOVED_SYNTAX_ERROR: free_limit = tier_results["free"]["actual_requests"]
                                                                                                        # REMOVED_SYNTAX_ERROR: premium_limit = tier_results["premium"]["actual_requests"]
                                                                                                        # REMOVED_SYNTAX_ERROR: enterprise_limit = tier_results["enterprise"]["actual_requests"]

                                                                                                        # REMOVED_SYNTAX_ERROR: if free_limit < premium_limit < enterprise_limit:
                                                                                                            # REMOVED_SYNTAX_ERROR: print(f"[OK] Tier-based limits enforced:")
                                                                                                            # REMOVED_SYNTAX_ERROR: for tier, result in tier_results.items():
                                                                                                                # REMOVED_SYNTAX_ERROR: print("formatted_string"}

                                                                                                                                # Trigger rate limit
                                                                                                                                # REMOVED_SYNTAX_ERROR: endpoint = "formatted_string"

                                                                                                                                # Make many requests quickly
                                                                                                                                # REMOVED_SYNTAX_ERROR: for _ in range(150):
                                                                                                                                    # REMOVED_SYNTAX_ERROR: async with session.get(endpoint, headers=headers) as response:
                                                                                                                                        # REMOVED_SYNTAX_ERROR: if response.status == 429:
                                                                                                                                            # Check for Retry-After header
                                                                                                                                            # REMOVED_SYNTAX_ERROR: retry_after = response.headers.get("Retry-After")
                                                                                                                                            # REMOVED_SYNTAX_ERROR: if retry_after:
                                                                                                                                                # REMOVED_SYNTAX_ERROR: print("formatted_string"}
                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: endpoint = "formatted_string"

                                                                                                                                                                        # Create multiple sessions (simulating distributed clients)
                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: sessions = []
                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: for i in range(3):
                                                                                                                                                                            # REMOVED_SYNTAX_ERROR: sessions.append(aiohttp.ClientSession())

                                                                                                                                                                            # Make concurrent requests from all sessions
# REMOVED_SYNTAX_ERROR: async def make_requests_from_session(session: aiohttp.ClientSession, count: int) -> Dict:
    # REMOVED_SYNTAX_ERROR: """Make requests from a single session."""
    # REMOVED_SYNTAX_ERROR: success = 0
    # REMOVED_SYNTAX_ERROR: limited = 0

    # REMOVED_SYNTAX_ERROR: for _ in range(count):
        # REMOVED_SYNTAX_ERROR: async with session.get(endpoint, headers=headers) as response:
            # REMOVED_SYNTAX_ERROR: if response.status == 200:
                # REMOVED_SYNTAX_ERROR: success += 1
                # REMOVED_SYNTAX_ERROR: elif response.status == 429:
                    # REMOVED_SYNTAX_ERROR: limited += 1

                    # REMOVED_SYNTAX_ERROR: return {"success": success, "limited": limited}

                    # Run requests from all sessions concurrently
                    # REMOVED_SYNTAX_ERROR: tasks = [make_requests_from_session(s, 50) for s in sessions]
                    # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks)

                    # Cleanup extra sessions
                    # REMOVED_SYNTAX_ERROR: for s in sessions:
                        # REMOVED_SYNTAX_ERROR: await s.close()

                        # Analyze results
                        # REMOVED_SYNTAX_ERROR: total_success = sum(r["success"] for r in results)
                        # REMOVED_SYNTAX_ERROR: total_limited = sum(r["limited"] for r in results)

                        # REMOVED_SYNTAX_ERROR: print("formatted_string")
                        # REMOVED_SYNTAX_ERROR: print("formatted_string")

                        # REMOVED_SYNTAX_ERROR: if total_limited > 0:
                            # REMOVED_SYNTAX_ERROR: print(f"[OK] Distributed rate limiting active (shared limit across sessions)")
                            # REMOVED_SYNTAX_ERROR: return True
                            # REMOVED_SYNTAX_ERROR: else:
                                # REMOVED_SYNTAX_ERROR: print(f"[WARNING] No distributed rate limiting detected")
                                # REMOVED_SYNTAX_ERROR: return False

                                # REMOVED_SYNTAX_ERROR: except Exception as e:
                                    # REMOVED_SYNTAX_ERROR: print("formatted_string"}
                                            # REMOVED_SYNTAX_ERROR: endpoint = "formatted_string"

                                            # Phase 1: Hit rate limit
                                            # REMOVED_SYNTAX_ERROR: phase1_success = 0
                                            # REMOVED_SYNTAX_ERROR: for i in range(150):
                                                # REMOVED_SYNTAX_ERROR: async with session.get(endpoint, headers=headers) as response:
                                                    # REMOVED_SYNTAX_ERROR: if response.status == 200:
                                                        # REMOVED_SYNTAX_ERROR: phase1_success += 1
                                                        # REMOVED_SYNTAX_ERROR: elif response.status == 429:
                                                            # REMOVED_SYNTAX_ERROR: print("formatted_string"
                                                                                                            # REMOVED_SYNTAX_ERROR: success_count = 0
                                                                                                            # REMOVED_SYNTAX_ERROR: rate_limited = False

                                                                                                            # Make unauthenticated requests
                                                                                                            # REMOVED_SYNTAX_ERROR: for i in range(50):
                                                                                                                # REMOVED_SYNTAX_ERROR: async with session.get(endpoint) as response:
                                                                                                                    # REMOVED_SYNTAX_ERROR: if response.status == 200:
                                                                                                                        # REMOVED_SYNTAX_ERROR: success_count += 1
                                                                                                                        # REMOVED_SYNTAX_ERROR: elif response.status == 429:
                                                                                                                            # REMOVED_SYNTAX_ERROR: rate_limited = True
                                                                                                                            # REMOVED_SYNTAX_ERROR: print("formatted_string"email"]
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: token = self.user_tokens[email]
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: session = self.sessions[email]
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: headers = {"Authorization": "formatted_string"}

                                                                                                                                                        # Get metrics endpoint
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: async with session.get( )
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: "formatted_string",
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: headers=headers
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: ) as response:
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: if response.status == 200:
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: data = await response.json()
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: metrics[user["tier"]] = data

                                                                                                                                                                # Display metrics
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: print("\n[METRICS] Rate Limit Statistics:")

                                                                                                                                                                # Analyze request log
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: total_requests = len(self.request_log)
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: rate_limited_requests = sum(1 for r in self.request_log if r["status"] == 429)

                                                                                                                                                                # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: print("formatted_string")

                                                                                                                                                                # Per-tier metrics
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: for tier, data in metrics.items():
                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: if data:
                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: print("formatted_string")

                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: return True

                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                                                                                                                                            # REMOVED_SYNTAX_ERROR: print("formatted_string"user_setup"] = await self.setup_test_users()
    # REMOVED_SYNTAX_ERROR: if not results["user_setup"]:
        # REMOVED_SYNTAX_ERROR: print("\n[CRITICAL] User setup failed. Aborting tests.")
        # REMOVED_SYNTAX_ERROR: return results

        # Rate limiting tests
        # REMOVED_SYNTAX_ERROR: results["basic_rate_limit"] = await self.test_basic_rate_limit()

        # Wait between tests to avoid interference
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(65)  # Wait for rate limit window to reset

        # REMOVED_SYNTAX_ERROR: results["burst_handling"] = await self.test_burst_handling()
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(5)

        # REMOVED_SYNTAX_ERROR: results["per_endpoint_limits"] = await self.test_per_endpoint_limits()
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(5)

        # REMOVED_SYNTAX_ERROR: results["tier_based_limits"] = await self.test_tier_based_limits()
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(5)

        # REMOVED_SYNTAX_ERROR: results["retry_after_header"] = await self.test_retry_after_header()
        # REMOVED_SYNTAX_ERROR: results["distributed_limiting"] = await self.test_distributed_rate_limiting()

        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(65)  # Reset window

        # REMOVED_SYNTAX_ERROR: results["rate_limit_reset"] = await self.test_rate_limit_reset()
        # REMOVED_SYNTAX_ERROR: results["ip_based_limiting"] = await self.test_ip_based_limiting()
        # REMOVED_SYNTAX_ERROR: results["rate_limit_metrics"] = await self.test_rate_limit_metrics()

        # REMOVED_SYNTAX_ERROR: return results

        # Removed problematic line: @pytest.mark.asyncio
        # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
        # REMOVED_SYNTAX_ERROR: @pytest.mark.l3
        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_api_rate_limiting_enforcement():
            # REMOVED_SYNTAX_ERROR: """Test API rate limiting enforcement."""
            # REMOVED_SYNTAX_ERROR: async with RateLimitTester() as tester:
                # REMOVED_SYNTAX_ERROR: results = await tester.run_all_tests()

                # Print summary
                # REMOVED_SYNTAX_ERROR: print("\n" + "="*60)
                # REMOVED_SYNTAX_ERROR: print("API RATE LIMITING TEST SUMMARY")
                # REMOVED_SYNTAX_ERROR: print("="*60)

                # REMOVED_SYNTAX_ERROR: for test_name, passed in results.items():
                    # REMOVED_SYNTAX_ERROR: status = "[PASS]" if passed else "[FAIL]"
                    # REMOVED_SYNTAX_ERROR: print("formatted_string")

                    # REMOVED_SYNTAX_ERROR: print("="*60)

                    # Calculate overall result
                    # REMOVED_SYNTAX_ERROR: total_tests = len(results)
                    # REMOVED_SYNTAX_ERROR: passed_tests = sum(1 for passed in results.values() if passed)

                    # REMOVED_SYNTAX_ERROR: print("formatted_string")

                    # REMOVED_SYNTAX_ERROR: if passed_tests == total_tests:
                        # REMOVED_SYNTAX_ERROR: print("\n[SUCCESS] All rate limiting tests passed!")
                        # REMOVED_SYNTAX_ERROR: else:
                            # REMOVED_SYNTAX_ERROR: print("formatted_string"

# REMOVED_SYNTAX_ERROR: async def main():
    # REMOVED_SYNTAX_ERROR: """Run the test standalone."""
    # REMOVED_SYNTAX_ERROR: print("="*60)
    # REMOVED_SYNTAX_ERROR: print("API RATE LIMITING ENFORCEMENT TEST")
    # REMOVED_SYNTAX_ERROR: print("="*60)
    # REMOVED_SYNTAX_ERROR: print("formatted_string")
    # REMOVED_SYNTAX_ERROR: print("="*60)

    # REMOVED_SYNTAX_ERROR: async with RateLimitTester() as tester:
        # REMOVED_SYNTAX_ERROR: results = await tester.run_all_tests()

        # Return exit code based on results
        # REMOVED_SYNTAX_ERROR: if all(results.values()):
            # REMOVED_SYNTAX_ERROR: return 0
            # REMOVED_SYNTAX_ERROR: else:
                # REMOVED_SYNTAX_ERROR: return 1

                # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                    # REMOVED_SYNTAX_ERROR: exit_code = asyncio.run(main())
                    # REMOVED_SYNTAX_ERROR: sys.exit(exit_code)
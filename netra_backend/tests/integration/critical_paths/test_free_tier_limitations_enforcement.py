from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
#!/usr/bin/env python3
"""
Comprehensive test for free tier limitations enforcement:
    1. Account creation with free tier
2. API rate limiting validation
3. Storage quota enforcement
4. Agent count restrictions
5. Concurrent connection limits
6. Feature access restrictions
7. Usage tracking accuracy
8. Upgrade path validation

This test ensures free tier users are properly limited while maintaining good UX.
""""

# Test framework import - using pytest fixtures instead

import asyncio
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


import aiohttp
import pytest
import websockets

# Configuration
BACKEND_URL = get_env().get("BACKEND_URL", "http://localhost:8000")
AUTH_SERVICE_URL = get_env().get("AUTH_SERVICE_URL", "http://localhost:8081")
WEBSOCKET_URL = get_env().get("WEBSOCKET_URL", "ws://localhost:8000/websocket")

# Free tier limits (should match config)
FREE_TIER_LIMITS = {
    "api_calls_per_day": 1000,
    "api_calls_per_minute": 10,
    "storage_mb": 100,
    "agent_count": 3,
    "concurrent_connections": 2,
    "workspace_count": 1,
    "team_members": 1,
    "log_retention_days": 7,
    "custom_models": False,
    "enterprise_features": False
}

class FreeTierLimitsTester:
    """Test free tier limitations enforcement."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.workspace_id: Optional[str] = None
        self.ws_connections: List[websockets.ClientConnection] = []
        self.test_email = f"freetier_{uuid.uuid4().hex[:8]]@example.com"
        self.test_password = f"TestPass123_{uuid.uuid4().hex[:8]]"
        self.api_call_times: List[float] = []
        
    async def __aenter__(self):
        """Setup test environment."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment."""
        for ws in self.ws_connections:
            await ws.close()
        if self.session:
            await self.session.close()
            
    async def setup_free_tier_account(self) -> bool:
        """Setup a new free tier account."""
        print("\n[SETUP] Creating free tier account...")
        
        try:
            # Register new user
            register_data = {
                "email": self.test_email,
                "password": self.test_password,
                "name": "Free Tier Test User",
                "plan": "free"  # Explicitly request free tier
            }
            
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/register",
                json=register_data
            ) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    self.user_id = data.get("user_id")
                    print(f"[OK] Free tier account created: {self.user_id]")
                    
                    # Login to get token
                    login_data = {
                        "email": self.test_email,
                        "password": self.test_password
                    }
                    
                    async with self.session.post(
                        f"{AUTH_SERVICE_URL}/auth/login",
                        json=login_data
                    ) as login_response:
                        if login_response.status == 200:
                            login_result = await login_response.json()
                            self.auth_token = login_result.get("access_token")
                            print(f"[OK] Logged in with free tier account")
                            return True
                            
                print(f"[ERROR] Account setup failed")
                return False
                
        except Exception as e:
            print(f"[ERROR] Setup error: {e]")
            return False
            
    @pytest.mark.asyncio
    async def test_api_rate_limiting(self) -> bool:
        """Test API rate limiting for free tier."""
        print("\n[RATE LIMIT] Testing API rate limiting...")
        
        if not self.auth_token:
            print("[ERROR] No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            limit_per_minute = FREE_TIER_LIMITS["api_calls_per_minute"]
            
            # Clear previous times
            self.api_call_times = []
            
            # Make rapid API calls
            calls_made = 0
            rate_limited = False
            
            for i in range(limit_per_minute + 5):
                start_time = time.time()
                
                async with self.session.get(
                    f"{BACKEND_URL}/api/user/profile",
                    headers=headers
                ) as response:
                    self.api_call_times.append(time.time())
                    
                    if response.status == 429:
                        rate_limited = True
                        remaining = response.headers.get("X-RateLimit-Remaining", "0")
                        reset_time = response.headers.get("X-RateLimit-Reset", "unknown")
                        print(f"[OK] Rate limited after {calls_made] calls")
                        print(f"[INFO] Remaining: {remaining], Reset: {reset_time]")
                        break
                    elif response.status == 200:
                        calls_made += 1
                        print(f"[INFO] Call {calls_made] succeeded")
                    else:
                        print(f"[ERROR] Unexpected status: {response.status]")
                        
                # Small delay to avoid overwhelming
                await asyncio.sleep(0.1)
                
            if rate_limited:
                print(f"[OK] Rate limiting enforced correctly at {calls_made] calls")
                return True
            elif calls_made >= limit_per_minute:
                print(f"[WARNING] Made {calls_made] calls without rate limiting")
                return False
            else:
                print(f"[INFO] Rate limit not reached with {calls_made] calls")
                return True
                
        except Exception as e:
            print(f"[ERROR] Rate limiting test error: {e]")
            return False
            
    @pytest.mark.asyncio
    async def test_storage_quota(self) -> bool:
        """Test storage quota enforcement."""
        print("\n[STORAGE] Testing storage quota enforcement...")
        
        if not self.auth_token:
            print("[ERROR] No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            storage_limit_mb = FREE_TIER_LIMITS["storage_mb"]
            
            # Check current usage
            async with self.session.get(
                f"{BACKEND_URL}/api/user/storage",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    current_usage_mb = data.get("used_mb", 0)
                    limit_mb = data.get("limit_mb", storage_limit_mb)
                    print(f"[INFO] Current storage: {current_usage_mb]/{limit_mb] MB")
                    
            # Try to upload data that would exceed quota
            # Create a large payload (1MB)
            large_data = "x" * (1024 * 1024)
            
            uploads_succeeded = 0
            quota_exceeded = False
            
            for i in range(int(storage_limit_mb / 10) + 5):
                upload_data = {
                    "name": f"test_file_{i}.txt",
                    "content": large_data[:1024*1024*10],  # 10MB chunks
                    "type": "text/plain"
                }
                
                async with self.session.post(
                    f"{BACKEND_URL}/api/storage/upload",
                    json=upload_data,
                    headers=headers
                ) as response:
                    if response.status in [200, 201]:
                        uploads_succeeded += 1
                        print(f"[INFO] Upload {i+1] succeeded")
                    elif response.status in [413, 507]:  # Payload too large or Insufficient storage
                        quota_exceeded = True
                        data = await response.json()
                        print(f"[OK] Storage quota exceeded after {uploads_succeeded] uploads")
                        print(f"[INFO] Error: {data.get('error', 'Storage limit exceeded')]")
                        break
                    else:
                        print(f"[WARNING] Unexpected status: {response.status]")
                        
            if quota_exceeded:
                print("[OK] Storage quota properly enforced")
                return True
            else:
                print(f"[INFO] Uploaded {uploads_succeeded] files without hitting quota")
                return True
                
        except Exception as e:
            print(f"[ERROR] Storage quota test error: {e]")
            return False
            
    @pytest.mark.asyncio
    async def test_agent_count_limit(self) -> bool:
        """Test agent count restrictions."""
        print("\n[AGENTS] Testing agent count limits...")
        
        if not self.auth_token:
            print("[ERROR] No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            agent_limit = FREE_TIER_LIMITS["agent_count"]
            
            # Create workspace first
            workspace_data = {
                "name": f"Test Workspace {uuid.uuid4().hex[:4]]",
                "description": "Testing agent limits"
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/api/workspaces",
                json=workspace_data,
                headers=headers
            ) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    self.workspace_id = data.get("workspace_id")
                    print(f"[INFO] Workspace created: {self.workspace_id]")
                    
            agents_created = []
            limit_reached = False
            
            # Try to create more agents than allowed
            for i in range(agent_limit + 2):
                agent_data = {
                    "workspace_id": self.workspace_id,
                    "name": f"Test Agent {i+1}",
                    "type": "assistant",
                    "model": LLMModel.GEMINI_2_5_FLASH.value
                }
                
                async with self.session.post(
                    f"{BACKEND_URL}/api/agents",
                    json=agent_data,
                    headers=headers
                ) as response:
                    if response.status in [200, 201]:
                        data = await response.json()
                        agents_created.append(data.get("agent_id"))
                        print(f"[INFO] Agent {i+1] created")
                    elif response.status == 402:
                        limit_reached = True
                        data = await response.json()
                        print(f"[OK] Agent limit reached after {len(agents_created)] agents")
                        print(f"[INFO] Message: {data.get('message', 'Limit exceeded')]")
                        break
                    else:
                        print(f"[WARNING] Unexpected status: {response.status]")
                        
            if limit_reached and len(agents_created) == agent_limit:
                print(f"[OK] Agent count limit ({agent_limit]) properly enforced")
                return True
            elif len(agents_created) > agent_limit:
                print(f"[ERROR] Created {len(agents_created)] agents, exceeding limit of {agent_limit]")
                return False
            else:
                print(f"[INFO] Created {len(agents_created)] agents within limit")
                return True
                
        except Exception as e:
            print(f"[ERROR] Agent limit test error: {e]")
            return False
            
    @pytest.mark.asyncio
    async def test_concurrent_connections(self) -> bool:
        """Test concurrent WebSocket connection limits."""
        print("\n[CONNECTIONS] Testing concurrent connection limits...")
        
        if not self.auth_token:
            print("[ERROR] No auth token available")
            return False
            
        try:
            connection_limit = FREE_TIER_LIMITS["concurrent_connections"]
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Clear existing connections
            for ws in self.ws_connections:
                await ws.close()
            self.ws_connections = []
            
            connections_established = 0
            limit_reached = False
            
            # Try to establish more connections than allowed
            for i in range(connection_limit + 2):
                try:
                    ws = await websockets.connect(
                        WEBSOCKET_URL,
                        extra_headers=headers
                    )
                    
                    # Authenticate the connection
                    auth_msg = {"type": "auth", "token": self.auth_token}
                    await ws.send(json.dumps(auth_msg))
                    
                    # Wait for auth response
                    response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(response)
                    
                    if data.get("type") == "auth_success":
                        self.ws_connections.append(ws)
                        connections_established += 1
                        print(f"[INFO] Connection {i+1] established")
                    elif data.get("type") == "connection_limit_exceeded":
                        limit_reached = True
                        print(f"[OK] Connection limit reached after {connections_established] connections")
                        await ws.close()
                        break
                    else:
                        print(f"[WARNING] Unexpected response: {data]")
                        await ws.close()
                        
                except websockets.exceptions.WebSocketException as e:
                    if "403" in str(e) or "limit" in str(e).lower():
                        limit_reached = True
                        print(f"[OK] Connection rejected after {connections_established] connections")
                        break
                    else:
                        print(f"[ERROR] WebSocket error: {e]")
                        
            if limit_reached and connections_established == connection_limit:
                print(f"[OK] Connection limit ({connection_limit]) properly enforced")
                return True
            elif connections_established > connection_limit:
                print(f"[WARNING] Established {connections_established] connections, exceeding limit")
                return False
            else:
                print(f"[INFO] Established {connections_established] connections within limit")
                return True
                
        except Exception as e:
            print(f"[ERROR] Connection limit test error: {e]")
            return False
            
    @pytest.mark.asyncio
    async def test_feature_restrictions(self) -> bool:
        """Test restricted feature access for free tier."""
        print("\n[FEATURES] Testing feature restrictions...")
        
        if not self.auth_token:
            print("[ERROR] No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            restricted_features = []
            accessible_features = []
            
            # Test custom model access (should be restricted)
            if not FREE_TIER_LIMITS.get("custom_models", True):
                custom_model_data = {
                    "name": "custom-model-test",
                    "type": "fine-tuned",
                    "base_model": LLMModel.GEMINI_2_5_FLASH.value
                }
                
                async with self.session.post(
                    f"{BACKEND_URL}/api/models/custom",
                    json=custom_model_data,
                    headers=headers
                ) as response:
                    if response.status == 403:
                        restricted_features.append("custom_models")
                        print("[OK] Custom models restricted")
                    else:
                        accessible_features.append("custom_models")
                        print(f"[WARNING] Custom models accessible: {response.status]")
                        
            # Test enterprise features (should be restricted)
            if not FREE_TIER_LIMITS.get("enterprise_features", True):
                enterprise_endpoints = [
                    ("/api/enterprise/sso", "SSO"),
                    ("/api/enterprise/audit-logs", "Audit Logs"),
                    ("/api/enterprise/compliance", "Compliance"),
                    ("/api/analytics/advanced", "Advanced Analytics")
                ]
                
                for endpoint, feature in enterprise_endpoints:
                    async with self.session.get(
                        f"{BACKEND_URL}{endpoint}",
                        headers=headers
                    ) as response:
                        if response.status in [403, 402]:
                            restricted_features.append(feature)
                            print(f"[OK] {feature] restricted")
                        else:
                            accessible_features.append(feature)
                            print(f"[WARNING] {feature] accessible: {response.status]")
                            
            # Test team member addition (should be limited to 1)
            team_member_data = {
                "email": "teammate@example.com",
                "role": "developer"
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/api/team/invite",
                json=team_member_data,
                headers=headers
            ) as response:
                if response.status in [403, 402]:
                    restricted_features.append("team_expansion")
                    print("[OK] Team expansion restricted")
                else:
                    accessible_features.append("team_expansion")
                    print(f"[INFO] Team member invite status: {response.status]")
                    
            print(f"\n[SUMMARY] Restricted features: {restricted_features]")
            print(f"[SUMMARY] Accessible features: {accessible_features]")
            
            return len(restricted_features) > 0
            
        except Exception as e:
            print(f"[ERROR] Feature restriction test error: {e]")
            return False
            
    @pytest.mark.asyncio
    async def test_usage_tracking(self) -> bool:
        """Test accuracy of usage tracking."""
        print("\n[USAGE] Testing usage tracking accuracy...")
        
        if not self.auth_token:
            print("[ERROR] No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Get initial usage
            async with self.session.get(
                f"{BACKEND_URL}/api/user/usage",
                headers=headers
            ) as response:
                if response.status == 200:
                    initial_usage = await response.json()
                    initial_api_calls = initial_usage.get("api_calls", 0)
                    print(f"[INFO] Initial API calls: {initial_api_calls]")
                    
            # Make some tracked API calls
            tracked_calls = 5
            for i in range(tracked_calls):
                async with self.session.get(
                    f"{BACKEND_URL}/api/user/profile",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        print(f"[INFO] Made tracked call {i+1]")
                        
                await asyncio.sleep(0.5)  # Avoid rate limiting
                
            # Check updated usage
            async with self.session.get(
                f"{BACKEND_URL}/api/user/usage",
                headers=headers
            ) as response:
                if response.status == 200:
                    updated_usage = await response.json()
                    updated_api_calls = updated_usage.get("api_calls", 0)
                    calls_tracked = updated_api_calls - initial_api_calls
                    
                    print(f"[INFO] Updated API calls: {updated_api_calls]")
                    print(f"[INFO] Calls tracked: {calls_tracked]")
                    
                    if calls_tracked >= tracked_calls:
                        print(f"[OK] Usage tracking accurate: {calls_tracked]/{tracked_calls]")
                        return True
                    else:
                        print(f"[WARNING] Usage tracking mismatch: {calls_tracked]/{tracked_calls]")
                        return False
                        
        except Exception as e:
            print(f"[ERROR] Usage tracking test error: {e]")
            return False
            
    @pytest.mark.asyncio
    async def test_upgrade_path(self) -> bool:
        """Test upgrade path from free tier."""
        print("\n[UPGRADE] Testing upgrade path...")
        
        if not self.auth_token:
            print("[ERROR] No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Get upgrade options
            async with self.session.get(
                f"{BACKEND_URL}/api/billing/upgrade-options",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    plans = data.get("plans", [])
                    print(f"[OK] Upgrade options available: {len(plans)] plans")
                    
                    for plan in plans:
                        print(f"[INFO] Plan: {plan.get('name')] - ${plan.get('price')]/mo")
                        print(f"       Limits: {plan.get('limits', {})}")
                        
                    # Simulate upgrade intent
                    upgrade_data = {
                        "plan": "pro",
                        "billing_cycle": "monthly"
                    }
                    
                    async with self.session.post(
                        f"{BACKEND_URL}/api/billing/upgrade-intent",
                        json=upgrade_data,
                        headers=headers
                    ) as upgrade_response:
                        if upgrade_response.status == 200:
                            upgrade_result = await upgrade_response.json()
                            print(f"[OK] Upgrade intent created")
                            print(f"[INFO] Checkout URL: {upgrade_result.get('checkout_url')]")
                            print(f"[INFO] Session ID: {upgrade_result.get('session_id')]")
                            return True
                        else:
                            print(f"[WARNING] Upgrade intent status: {upgrade_response.status]")
                            return True  # Not critical
                            
                else:
                    print(f"[ERROR] Failed to get upgrade options: {response.status]")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Upgrade path test error: {e]")
            return False
            
    @pytest.mark.asyncio
    async def test_daily_limit_reset(self) -> bool:
        """Test daily limit reset mechanism."""
        print("\n[RESET] Testing daily limit reset...")
        
        if not self.auth_token:
            print("[ERROR] No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Get current usage and reset time
            async with self.session.get(
                f"{BACKEND_URL}/api/user/usage",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    reset_time = data.get("daily_reset_time")
                    current_daily_calls = data.get("daily_api_calls", 0)
                    remaining_calls = data.get("daily_remaining", FREE_TIER_LIMITS["api_calls_per_day"])
                    
                    print(f"[INFO] Current daily calls: {current_daily_calls]")
                    print(f"[INFO] Remaining calls: {remaining_calls]")
                    print(f"[INFO] Reset time: {reset_time]")
                    
                    # Verify reset time is within 24 hours
                    if reset_time:
                        reset_dt = datetime.fromisoformat(reset_time.replace('Z', '+00:00'))
                        now = datetime.now(timezone.utc)
                        time_until_reset = (reset_dt - now).total_seconds() / 3600
                        
                        if 0 < time_until_reset <= 24:
                            print(f"[OK] Reset in {time_until_reset:.1f] hours")
                            return True
                        else:
                            print(f"[WARNING] Unexpected reset time: {time_until_reset:.1f] hours")
                            return False
                    else:
                        print("[WARNING] No reset time provided")
                        return True
                        
        except Exception as e:
            print(f"[ERROR] Daily reset test error: {e]")
            return False
            
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all free tier limitation tests."""
        results = {}
        
        # Setup free tier account
        results["account_setup"] = await self.setup_free_tier_account()
        if not results["account_setup"]:
            print("\n[CRITICAL] Account setup failed. Aborting tests.")
            return results
            
        # Run limitation tests
        results["api_rate_limiting"] = await self.test_api_rate_limiting()
        results["storage_quota"] = await self.test_storage_quota()
        results["agent_count_limit"] = await self.test_agent_count_limit()
        results["concurrent_connections"] = await self.test_concurrent_connections()
        results["feature_restrictions"] = await self.test_feature_restrictions()
        results["usage_tracking"] = await self.test_usage_tracking()
        results["upgrade_path"] = await self.test_upgrade_path()
        results["daily_limit_reset"] = await self.test_daily_limit_reset()
        
        return results

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
@pytest.mark.asyncio
async def test_free_tier_limitations_enforcement():
    """Test comprehensive free tier limitations enforcement."""
    async with FreeTierLimitsTester() as tester:
        results = await tester.run_all_tests()
        
        # Print summary
        print("\n" + "="*60)
        print("FREE TIER LIMITATIONS TEST SUMMARY")
        print("="*60)
        
        for test_name, passed in results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {test_name:30} : {status}")
            
        print("="*60)
        
        # Calculate overall result
        total_tests = len(results)
        passed_tests = sum(1 for passed in results.values() if passed)
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("\n✓ SUCCESS: All free tier limitations properly enforced!")
        else:
            failed = [name for name, passed in results.items() if not passed]
            print(f"\n✗ WARNING: Failed tests: {', '.join(failed)}")
            
        # Assert critical tests passed
        critical_tests = [
            "api_rate_limiting",
            "agent_count_limit",
            "feature_restrictions"
        ]
        
        for test in critical_tests:
            assert results.get(test, False), f"Critical test failed: {test}"

async def main():
    """Run the test standalone."""
    print("="*60)
    print("FREE TIER LIMITATIONS ENFORCEMENT TEST")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Backend URL: {BACKEND_URL}")
    print("\nFree Tier Limits:")
    for limit, value in FREE_TIER_LIMITS.items():
        print(f"  {limit:25} : {value}")
    print("="*60)
    
    async with FreeTierLimitsTester() as tester:
        results = await tester.run_all_tests()
        
        # Return exit code based on results
        critical_tests = ["api_rate_limiting", "agent_count_limit", "feature_restrictions"]
        critical_passed = all(results.get(test, False) for test in critical_tests)
        
        return 0 if critical_passed else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

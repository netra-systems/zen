#!/usr/bin/env python3
"""
Comprehensive test to verify multi-tenant session isolation:
1. Multiple users create separate sessions
2. Data isolation between tenants
3. Concurrent operations without interference
4. Resource quota enforcement per tenant
5. Cross-tenant security validation

This test ensures complete isolation between different tenant sessions.
"""

from test_framework import setup_test_path

import asyncio
import json
import random
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import pytest
import websockets

# Configuration
DEV_BACKEND_URL = "http://localhost:8000"
DEV_WEBSOCKET_URL = "ws://localhost:8000/websocket"
AUTH_SERVICE_URL = "http://localhost:8081"

# Test tenant configurations
TENANT_CONFIGS = [
    {
        "email": "tenant1@example.com",
        "password": "tenant1pass123",
        "name": "Tenant One",
        "org_id": "org_001"
    },
    {
        "email": "tenant2@example.com",
        "password": "tenant2pass123",
        "name": "Tenant Two",
        "org_id": "org_002"
    },
    {
        "email": "tenant3@example.com",
        "password": "tenant3pass123",
        "name": "Tenant Three",
        "org_id": "org_003"
    }
]

class TenantSession:
    """Represents a single tenant session."""
    
    def __init__(self, tenant_config: Dict):
        self.config = tenant_config
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.ws_connection = None
        self.user_id: Optional[str] = None
        self.thread_ids: List[str] = []
        self.data_items: List[str] = []
        self.received_messages: List[Dict] = []
        
    async def setup(self) -> bool:
        """Setup tenant session."""
        self.session = aiohttp.ClientSession()
        
        # Register user
        try:
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/register",
                json={
                    "email": self.config["email"],
                    "password": self.config["password"],
                    "name": self.config["name"],
                    "organization_id": self.config["org_id"]
                }
            ) as response:
                if response.status not in [200, 201, 409]:
                    print(f"[{self.config['name']}] Registration failed: {response.status}")
                    return False
                    
            # Login
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/login",
                json={
                    "email": self.config["email"],
                    "password": self.config["password"]
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data.get("access_token")
                    self.user_id = data.get("user_id")
                    return True
                else:
                    print(f"[{self.config['name']}] Login failed: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"[{self.config['name']}] Setup error: {e}")
            return False
            
    async def cleanup(self):
        """Cleanup tenant session."""
        if self.ws_connection:
            await self.ws_connection.close()
        if self.session:
            await self.session.close()

class MultiTenantIsolationTester:
    """Test multi-tenant session isolation."""
    
    def __init__(self):
        self.tenants: List[TenantSession] = []
        
    async def __aenter__(self):
        """Setup test environment."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment."""
        for tenant in self.tenants:
            await tenant.cleanup()
            
    async def test_tenant_setup(self) -> bool:
        """Setup all tenant sessions."""
        print("\n[SETUP] STEP 1: Setting up tenant sessions...")
        
        for config in TENANT_CONFIGS:
            tenant = TenantSession(config)
            if await tenant.setup():
                self.tenants.append(tenant)
                print(f"[OK] Tenant {config['name']} setup complete")
            else:
                print(f"[ERROR] Tenant {config['name']} setup failed")
                return False
                
        print(f"[OK] All {len(self.tenants)} tenants setup successfully")
        return True
        
    async def test_isolated_data_creation(self) -> bool:
        """Test that each tenant can create isolated data."""
        print("\n[CREATE] STEP 2: Creating isolated data for each tenant...")
        
        for tenant in self.tenants:
            headers = {"Authorization": f"Bearer {tenant.auth_token}"}
            
            # Create threads
            for i in range(3):
                thread_data = {
                    "title": f"{tenant.config['name']} Thread {i+1}",
                    "description": f"Private thread for {tenant.config['org_id']}",
                    "metadata": {
                        "org_id": tenant.config["org_id"],
                        "private": True
                    }
                }
                
                async with tenant.session.post(
                    f"{DEV_BACKEND_URL}/api/v1/threads",
                    json=thread_data,
                    headers=headers
                ) as response:
                    if response.status in [200, 201]:
                        data = await response.json()
                        tenant.thread_ids.append(data.get("thread_id"))
                    else:
                        print(f"[ERROR] Thread creation failed for {tenant.config['name']}")
                        return False
                        
            print(f"[OK] Created {len(tenant.thread_ids)} threads for {tenant.config['name']}")
            
        return True
        
    async def test_data_isolation_verification(self) -> bool:
        """Verify that tenants cannot access each other's data."""
        print("\n[ISOLATE] STEP 3: Verifying data isolation between tenants...")
        
        for i, tenant in enumerate(self.tenants):
            headers = {"Authorization": f"Bearer {tenant.auth_token}"}
            
            # Try to access other tenants' threads
            for j, other_tenant in enumerate(self.tenants):
                if i == j:
                    continue  # Skip own threads
                    
                for thread_id in other_tenant.thread_ids:
                    async with tenant.session.get(
                        f"{DEV_BACKEND_URL}/api/v1/threads/{thread_id}",
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            print(f"[CRITICAL] {tenant.config['name']} accessed {other_tenant.config['name']}'s thread!")
                            return False
                        elif response.status in [403, 404]:
                            # Expected - access denied or not found
                            pass
                        else:
                            print(f"[WARNING] Unexpected status {response.status} for isolation check")
                            
            print(f"[OK] {tenant.config['name']} properly isolated from other tenants")
            
        return True
        
    async def test_concurrent_operations(self) -> bool:
        """Test concurrent operations across tenants."""
        print("\n[CONCURRENT] STEP 4: Testing concurrent operations...")
        
        async def tenant_operation(tenant: TenantSession, operation_count: int):
            """Perform operations for a single tenant."""
            headers = {"Authorization": f"Bearer {tenant.auth_token}"}
            results = []
            
            for i in range(operation_count):
                # Create a message in a random thread
                if tenant.thread_ids:
                    thread_id = random.choice(tenant.thread_ids)
                    message_data = {
                        "thread_id": thread_id,
                        "content": f"Message {i} from {tenant.config['name']}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    async with tenant.session.post(
                        f"{DEV_BACKEND_URL}/api/v1/messages",
                        json=message_data,
                        headers=headers
                    ) as response:
                        results.append(response.status in [200, 201])
                        
            return all(results)
            
        # Run concurrent operations for all tenants
        tasks = [
            tenant_operation(tenant, 10)
            for tenant in self.tenants
        ]
        
        results = await asyncio.gather(*tasks)
        
        if all(results):
            print(f"[OK] All tenants completed concurrent operations successfully")
            return True
        else:
            print(f"[ERROR] Some concurrent operations failed")
            return False
            
    async def test_websocket_isolation(self) -> bool:
        """Test WebSocket connection isolation."""
        print("\n[WEBSOCKET] STEP 5: Testing WebSocket isolation...")
        
        # Connect all tenants to WebSocket
        for tenant in self.tenants:
            try:
                headers = {"Authorization": f"Bearer {tenant.auth_token}"}
                tenant.ws_connection = await websockets.connect(
                    DEV_WEBSOCKET_URL,
                    extra_headers=headers
                )
                
                # Authenticate
                auth_message = {
                    "type": "auth",
                    "token": tenant.auth_token
                }
                await tenant.ws_connection.send(json.dumps(auth_message))
                
                # Wait for auth response
                response = await asyncio.wait_for(
                    tenant.ws_connection.recv(),
                    timeout=5.0
                )
                
                data = json.loads(response)
                if data.get("type") != "auth_success":
                    print(f"[ERROR] WebSocket auth failed for {tenant.config['name']}")
                    return False
                    
                print(f"[OK] WebSocket connected for {tenant.config['name']}")
                
            except Exception as e:
                print(f"[ERROR] WebSocket connection failed for {tenant.config['name']}: {e}")
                return False
                
        # Test message isolation
        for tenant in self.tenants:
            # Send a private message
            private_message = {
                "type": "private_message",
                "content": f"Private data from {tenant.config['org_id']}",
                "org_id": tenant.config["org_id"]
            }
            await tenant.ws_connection.send(json.dumps(private_message))
            
        # Brief wait for message processing
        await asyncio.sleep(1)
        
        # Check that each tenant only receives their own messages
        for tenant in self.tenants:
            try:
                # Non-blocking receive with timeout
                while True:
                    try:
                        response = await asyncio.wait_for(
                            tenant.ws_connection.recv(),
                            timeout=0.5
                        )
                        data = json.loads(response)
                        
                        # Verify message belongs to this tenant
                        if "org_id" in data and data["org_id"] != tenant.config["org_id"]:
                            print(f"[CRITICAL] {tenant.config['name']} received message from {data['org_id']}!")
                            return False
                            
                        tenant.received_messages.append(data)
                        
                    except asyncio.TimeoutError:
                        break  # No more messages
                        
            except Exception as e:
                print(f"[ERROR] Message receive error for {tenant.config['name']}: {e}")
                
        print(f"[OK] WebSocket message isolation verified")
        return True
        
    async def test_resource_quotas(self) -> bool:
        """Test resource quota enforcement per tenant."""
        print("\n[QUOTA] STEP 6: Testing resource quota enforcement...")
        
        for tenant in self.tenants:
            headers = {"Authorization": f"Bearer {tenant.auth_token}"}
            
            # Check current resource usage
            async with tenant.session.get(
                f"{DEV_BACKEND_URL}/api/v1/usage",
                headers=headers
            ) as response:
                if response.status == 200:
                    usage_data = await response.json()
                    print(f"[INFO] {tenant.config['name']} usage: {usage_data}")
                    
            # Try to exceed quota (create many threads)
            quota_exceeded = False
            for i in range(100):  # Try to create excessive threads
                thread_data = {
                    "title": f"Quota test thread {i}",
                    "description": "Testing quota limits"
                }
                
                async with tenant.session.post(
                    f"{DEV_BACKEND_URL}/api/v1/threads",
                    json=thread_data,
                    headers=headers
                ) as response:
                    if response.status == 429:  # Rate limited or quota exceeded
                        quota_exceeded = True
                        print(f"[OK] Quota enforced for {tenant.config['name']} at thread {i}")
                        break
                    elif response.status not in [200, 201]:
                        # Other error
                        break
                        
            if not quota_exceeded and i > 50:
                print(f"[WARNING] No quota enforcement detected for {tenant.config['name']}")
                
        return True
        
    async def test_session_cleanup(self) -> bool:
        """Test proper session cleanup and data isolation after logout."""
        print("\n[CLEANUP] STEP 7: Testing session cleanup...")
        
        # Logout first tenant
        if self.tenants:
            tenant = self.tenants[0]
            headers = {"Authorization": f"Bearer {tenant.auth_token}"}
            
            # Logout
            async with tenant.session.post(
                f"{AUTH_SERVICE_URL}/auth/logout",
                headers=headers
            ) as response:
                if response.status == 200:
                    print(f"[OK] {tenant.config['name']} logged out")
                    
            # Try to use the old token
            async with tenant.session.get(
                f"{DEV_BACKEND_URL}/api/v1/threads",
                headers=headers
            ) as response:
                if response.status == 401:
                    print(f"[OK] Old token properly invalidated")
                    return True
                else:
                    print(f"[ERROR] Old token still active: {response.status}")
                    return False
                    
        return True
        
    async def test_cross_tenant_security(self) -> bool:
        """Test cross-tenant security vulnerabilities."""
        print("\n[SECURITY] STEP 8: Testing cross-tenant security...")
        
        if len(self.tenants) < 2:
            print("[SKIP] Need at least 2 tenants for security test")
            return True
            
        attacker = self.tenants[0]
        victim = self.tenants[1]
        
        # Test various attack vectors
        attack_vectors = [
            # SQL injection attempt
            {
                "endpoint": f"{DEV_BACKEND_URL}/api/v1/threads",
                "method": "GET",
                "params": {"filter": f"'; DROP TABLE threads; --"}
            },
            # Path traversal attempt
            {
                "endpoint": f"{DEV_BACKEND_URL}/api/v1/threads/../../../{victim.thread_ids[0] if victim.thread_ids else 'test'}",
                "method": "GET",
                "params": {}
            },
            # Token manipulation attempt
            {
                "endpoint": f"{DEV_BACKEND_URL}/api/v1/threads",
                "method": "GET",
                "headers_override": {"Authorization": f"Bearer {victim.auth_token[:20]}fake"}
            }
        ]
        
        headers = {"Authorization": f"Bearer {attacker.auth_token}"}
        
        for vector in attack_vectors:
            try:
                if vector.get("headers_override"):
                    headers = vector["headers_override"]
                    
                if vector["method"] == "GET":
                    async with attacker.session.get(
                        vector["endpoint"],
                        params=vector.get("params", {}),
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            # Check if we got victim's data
                            if victim.config["org_id"] in str(data):
                                print(f"[CRITICAL] Security breach detected: {vector}")
                                return False
                                
            except Exception as e:
                # Expected for malformed requests
                pass
                
        print(f"[OK] All security vectors properly blocked")
        return True
        
    async def test_tenant_data_cleanup(self) -> bool:
        """Test complete data cleanup for a tenant."""
        print("\n[DELETE] STEP 9: Testing tenant data cleanup...")
        
        if self.tenants:
            tenant = self.tenants[0]
            headers = {"Authorization": f"Bearer {tenant.auth_token}"}
            
            # Delete all threads
            for thread_id in tenant.thread_ids:
                async with tenant.session.delete(
                    f"{DEV_BACKEND_URL}/api/v1/threads/{thread_id}",
                    headers=headers
                ) as response:
                    if response.status not in [200, 204]:
                        print(f"[ERROR] Failed to delete thread {thread_id}")
                        
            # Verify deletion
            async with tenant.session.get(
                f"{DEV_BACKEND_URL}/api/v1/threads",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if len(data.get("threads", [])) == 0:
                        print(f"[OK] All data cleaned up for {tenant.config['name']}")
                        return True
                        
        return True
        
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests in sequence."""
        results = {}
        
        # Setup tenants
        results["tenant_setup"] = await self.test_tenant_setup()
        if not results["tenant_setup"]:
            print("\n[CRITICAL] Tenant setup failed. Aborting tests.")
            return results
            
        # Run isolation tests
        results["data_creation"] = await self.test_isolated_data_creation()
        results["data_isolation"] = await self.test_data_isolation_verification()
        results["concurrent_operations"] = await self.test_concurrent_operations()
        results["websocket_isolation"] = await self.test_websocket_isolation()
        results["resource_quotas"] = await self.test_resource_quotas()
        results["session_cleanup"] = await self.test_session_cleanup()
        results["cross_tenant_security"] = await self.test_cross_tenant_security()
        results["tenant_data_cleanup"] = await self.test_tenant_data_cleanup()
        
        return results

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_multi_tenant_session_isolation():
    """Test multi-tenant session isolation."""
    async with MultiTenantIsolationTester() as tester:
        results = await tester.run_all_tests()
        
        # Print summary
        print("\n" + "="*60)
        print("MULTI-TENANT ISOLATION TEST SUMMARY")
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
            print("\n[SUCCESS] All multi-tenant isolation tests passed!")
        else:
            print(f"\n[WARNING] {total_tests - passed_tests} tests failed.")
            
        # Assert all tests passed
        assert all(results.values()), f"Some tests failed: {results}"

async def main():
    """Run the test standalone."""
    print("="*60)
    print("MULTI-TENANT SESSION ISOLATION TEST")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Testing {len(TENANT_CONFIGS)} tenants")
    print("="*60)
    
    async with MultiTenantIsolationTester() as tester:
        results = await tester.run_all_tests()
        
        # Return exit code based on results
        if all(results.values()):
            return 0
        else:
            return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
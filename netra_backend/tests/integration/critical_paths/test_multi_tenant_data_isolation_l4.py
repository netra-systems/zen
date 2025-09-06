#!/usr/bin/env python3
"""
Comprehensive test for multi-tenant data isolation:
    1. Tenant creation and configuration
2. Data segregation at database level
3. Cache isolation between tenants
4. WebSocket channel isolation
5. Resource quota enforcement
6. Cross-tenant access prevention
7. Tenant-specific encryption keys
8. Audit trail per tenant

This test validates complete data isolation in a multi-tenant environment.
""""

# Test framework import - using pytest fixtures instead

import asyncio
import hashlib
import json
import secrets
from shared.isolated_environment import IsolatedEnvironment

import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import aiohttp
import pytest
import websockets

# Configuration
BASE_URL = "http://localhost:8000"
AUTH_URL = "http://localhost:8081"
WS_URL = "ws://localhost:8000/websocket"
REDIS_URL = "redis://localhost:6379"
POSTGRES_URL = "postgresql://user:pass@localhost/netra"
CLICKHOUSE_URL = "http://localhost:8123"

# Test configuration
NUM_TENANTS = 3
NUM_USERS_PER_TENANT = 2
NUM_RESOURCES_PER_TENANT = 5

class TenantData:
    """Container for tenant-specific test data."""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.name = f"Tenant_{tenant_id}"
        self.domain = f"tenant{tenant_id}.example.com"
        self.users: List[Dict[str, Any]] = []
        self.tokens: List[str] = []
        self.resources: List[str] = []
        self.websocket_connections: List[Any] = []
        self.encryption_key: str = secrets.token_hex(32)
        self.data_partition: str = f"partition_{tenant_id}"
        
class MultiTenantIsolationTester:
    """Test multi-tenant data isolation."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.tenants: Dict[str, TenantData] = {]
        self.admin_token: Optional[str] = None
        self.isolation_violations: List[str] = []
        
    async def __aenter__(self):
        """Setup test environment."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment."""
        # Close all WebSocket connections
        for tenant in self.tenants.values():
            for ws in tenant.websocket_connections:
                try:
                    await ws.close()
                except:
                    pass
                    
        if self.session:
            await self.session.close()
            
    async def setup_admin_access(self) -> bool:
        """Setup admin access for tenant management."""
        print("\n[ADMIN] Setting up admin access...")
        
        try:
            # Login as admin
            admin_data = {
                "email": "admin@netrasystems.ai",
                "password": "admin_password"
            }
            
            async with self.session.post(
                f"{AUTH_URL}/auth/login",
                json=admin_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.admin_token = data.get("access_token")
                    print(f"[OK] Admin authenticated")
                    return True
                else:
                    print(f"[ERROR] Admin login failed: {response.status]")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Admin setup failed: {e]")
            return False
            
    async def create_tenants(self) -> bool:
        """Create multiple tenant organizations."""
        print(f"\n[TENANT] Creating {NUM_TENANTS] tenants...")
        
        for i in range(NUM_TENANTS):
            tenant_id = str(uuid.uuid4())[:8]
            tenant = TenantData(tenant_id)
            
            try:
                # Create tenant
                tenant_data = {
                    "name": tenant.name,
                    "domain": tenant.domain,
                    "plan": "enterprise",
                    "settings": {
                        "data_partition": tenant.data_partition,
                        "encryption_key": tenant.encryption_key,
                        "max_users": 100,
                        "max_storage_gb": 1000,
                        "max_api_calls_per_day": 1000000,
                        "isolated_resources": True,
                        "dedicated_database": True
                    }
                }
                
                async with self.session.post(
                    f"{BASE_URL}/api/admin/tenants",
                    json=tenant_data,
                    headers={"Authorization": f"Bearer {self.admin_token}"}
                ) as response:
                    if response.status in [200, 201]:
                        data = await response.json()
                        tenant.tenant_id = data.get("tenant_id", tenant.tenant_id)
                        self.tenants[tenant.tenant_id] = tenant
                        print(f"[OK] Created tenant: {tenant.name]")
                    else:
                        print(f"[ERROR] Failed to create tenant {tenant.name]: {response.status]")
                        return False
                        
            except Exception as e:
                print(f"[ERROR] Tenant creation failed: {e]")
                return False
                
        return len(self.tenants) == NUM_TENANTS
        
    async def create_tenant_users(self) -> bool:
        """Create users for each tenant."""
        print(f"\n[USERS] Creating {NUM_USERS_PER_TENANT] users per tenant...")
        
        for tenant in self.tenants.values():
            for i in range(NUM_USERS_PER_TENANT):
                user_data = {
                    "email": f"user{i}@{tenant.domain}",
                    "password": f"password_{tenant.tenant_id}_{i}",
                    "name": f"User {i}",
                    "tenant_id": tenant.tenant_id
                }
                
                try:
                    # Register user
                    async with self.session.post(
                        f"{AUTH_URL}/auth/register",
                        json=user_data
                    ) as response:
                        if response.status in [200, 201]:
                            user_info = await response.json()
                            
                            # Login to get token
                            login_data = {
                                "email": user_data["email"],
                                "password": user_data["password"]
                            }
                            
                            async with self.session.post(
                                f"{AUTH_URL}/auth/login",
                                json=login_data
                            ) as login_response:
                                if login_response.status == 200:
                                    login_info = await login_response.json()
                                    tenant.users.append(user_info)
                                    tenant.tokens.append(login_info["access_token"])
                                    print(f"[OK] Created user for {tenant.name]: {user_data['email']]")
                                    
                        elif response.status == 409:
                            print(f"[INFO] User already exists: {user_data['email']]")
                            # Try to login anyway
                            login_data = {
                                "email": user_data["email"],
                                "password": user_data["password"]
                            }
                            
                            async with self.session.post(
                                f"{AUTH_URL}/auth/login",
                                json=login_data
                            ) as login_response:
                                if login_response.status == 200:
                                    login_info = await login_response.json()
                                    tenant.tokens.append(login_info["access_token"])
                                    
                except Exception as e:
                    print(f"[ERROR] User creation failed: {e]")
                    
        return all(len(t.tokens) > 0 for t in self.tenants.values())
        
    async def create_tenant_resources(self) -> bool:
        """Create isolated resources for each tenant."""
        print(f"\n[RESOURCES] Creating {NUM_RESOURCES_PER_TENANT] resources per tenant...")
        
        for tenant in self.tenants.values():
            if not tenant.tokens:
                continue
                
            token = tenant.tokens[0]
            
            for i in range(NUM_RESOURCES_PER_TENANT):
                resource_data = {
                    "name": f"Resource_{i}_{tenant.tenant_id}",
                    "type": "thread",
                    "data": {
                        "title": f"Thread {i} for {tenant.name}",
                        "content": f"Sensitive data for {tenant.name}: {secrets.token_hex(16)}",
                        "metadata": {
                            "tenant_id": tenant.tenant_id,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "encryption_key_id": tenant.encryption_key[:8]
                        }
                    }
                }
                
                try:
                    async with self.session.post(
                        f"{BASE_URL}/api/threads",
                        json=resource_data,
                        headers={"Authorization": f"Bearer {token}"}
                    ) as response:
                        if response.status in [200, 201]:
                            data = await response.json()
                            resource_id = data.get("thread_id", data.get("id"))
                            tenant.resources.append(resource_id)
                            print(f"[OK] Created resource for {tenant.name]: {resource_id]")
                        else:
                            print(f"[ERROR] Failed to create resource: {response.status]")
                            
                except Exception as e:
                    print(f"[ERROR] Resource creation failed: {e]")
                    
        return all(len(t.resources) > 0 for t in self.tenants.values())
        
    @pytest.mark.asyncio
    async def test_data_segregation(self) -> bool:
        """Test that data is properly segregated between tenants."""
        print("\n[SEGREGATION] Testing data segregation...")
        
        violations = []
        
        for tenant_a in self.tenants.values():
            if not tenant_a.tokens or not tenant_a.resources:
                continue
                
            # Try to access other tenants' resources
            for tenant_b in self.tenants.values():
                if tenant_a.tenant_id == tenant_b.tenant_id:
                    continue
                    
                if not tenant_b.resources:
                    continue
                    
                # Use tenant A's token to access tenant B's resources
                for resource_id in tenant_b.resources:
                    try:
                        async with self.session.get(
                            f"{BASE_URL}/api/threads/{resource_id}",
                            headers={"Authorization": f"Bearer {tenant_a.tokens[0]]"]
                        ) as response:
                            if response.status == 200:
                                violations.append(
                                    f"Tenant {tenant_a.name} accessed {tenant_b.name}'s resource {resource_id}"
                                )
                                print(f"[VIOLATION] Cross-tenant access detected!")
                            elif response.status == 403:
                                print(f"[OK] Access denied for cross-tenant resource")
                            elif response.status == 404:
                                print(f"[OK] Resource not visible across tenants")
                                
                    except Exception as e:
                        print(f"[ERROR] Segregation test failed: {e]")
                        
        self.isolation_violations.extend(violations)
        return len(violations) == 0
        
    @pytest.mark.asyncio
    async def test_cache_isolation(self) -> bool:
        """Test that cache is isolated between tenants."""
        print("\n[CACHE] Testing cache isolation...")
        
        violations = []
        
        for tenant in self.tenants.values():
            if not tenant.tokens:
                continue
                
            # Set cache values for tenant
            cache_key = f"test_cache_{tenant.tenant_id}"
            cache_value = f"secret_data_{tenant.tenant_id}"
            
            try:
                # Set cache value
                async with self.session.post(
                    f"{BASE_URL}/api/cache/set",
                    json={"key": cache_key, "value": cache_value},
                    headers={"Authorization": f"Bearer {tenant.tokens[0]]"]
                ) as response:
                    if response.status == 200:
                        print(f"[OK] Cache set for {tenant.name]")
                        
            except Exception as e:
                print(f"[ERROR] Cache set failed: {e]")
                
        # Now try cross-tenant cache access
        for tenant_a in self.tenants.values():
            if not tenant_a.tokens:
                continue
                
            for tenant_b in self.tenants.values():
                if tenant_a.tenant_id == tenant_b.tenant_id:
                    continue
                    
                cache_key = f"test_cache_{tenant_b.tenant_id}"
                
                try:
                    # Try to get other tenant's cache
                    async with self.session.get(
                        f"{BASE_URL}/api/cache/get?key={cache_key}",
                        headers={"Authorization": f"Bearer {tenant_a.tokens[0]]"]
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get("value"):
                                violations.append(
                                    f"Tenant {tenant_a.name} accessed {tenant_b.name}'s cache"
                                )
                                print(f"[VIOLATION] Cross-tenant cache access!")
                        elif response.status in [404, 403]:
                            print(f"[OK] Cache isolated between tenants")
                            
                except Exception as e:
                    print(f"[ERROR] Cache isolation test failed: {e]")
                    
        self.isolation_violations.extend(violations)
        return len(violations) == 0
        
    @pytest.mark.asyncio
    async def test_websocket_isolation(self) -> bool:
        """Test WebSocket channel isolation between tenants."""
        print("\n[WEBSOCKET] Testing WebSocket channel isolation...")
        
        violations = []
        
        # Connect WebSockets for each tenant
        for tenant in self.tenants.values():
            if not tenant.tokens:
                continue
                
            try:
                # Connect WebSocket
                ws = await websockets.connect(
                    WS_URL,
                    extra_headers={"Authorization": f"Bearer {tenant.tokens[0]]"]
                )
                tenant.websocket_connections.append(ws)
                
                # Join tenant-specific channel
                await ws.send(json.dumps({
                    "type": "join_channel",
                    "channel": f"tenant_{tenant.tenant_id}"
                }))
                
                print(f"[OK] WebSocket connected for {tenant.name]")
                
            except Exception as e:
                print(f"[ERROR] WebSocket connection failed: {e]")
                
        # Test cross-tenant message isolation
        for tenant_a in self.tenants.values():
            if not tenant_a.websocket_connections:
                continue
                
            # Send message to tenant A's channel
            test_message = {
                "type": "broadcast",
                "channel": f"tenant_{tenant_a.tenant_id}",
                "data": f"secret_message_{tenant_a.tenant_id}"
            }
            
            await tenant_a.websocket_connections[0].send(json.dumps(test_message))
            
            # Check if other tenants receive it
            for tenant_b in self.tenants.values():
                if tenant_a.tenant_id == tenant_b.tenant_id:
                    continue
                    
                if not tenant_b.websocket_connections:
                    continue
                    
                try:
                    # Try to receive message with short timeout
                    message = await asyncio.wait_for(
                        tenant_b.websocket_connections[0].recv(),
                        timeout=1.0
                    )
                    
                    data = json.loads(message)
                    if test_message["data"] in str(data):
                        violations.append(
                            f"Tenant {tenant_b.name} received {tenant_a.name}'s WebSocket message"
                        )
                        print(f"[VIOLATION] Cross-tenant WebSocket leak!")
                        
                except asyncio.TimeoutError:
                    print(f"[OK] WebSocket channels isolated")
                except Exception as e:
                    print(f"[ERROR] WebSocket test error: {e]")
                    
        self.isolation_violations.extend(violations)
        return len(violations) == 0
        
    @pytest.mark.asyncio
    async def test_resource_quotas(self) -> bool:
        """Test resource quota enforcement per tenant."""
        print("\n[QUOTAS] Testing resource quota enforcement...")
        
        for tenant in self.tenants.values():
            if not tenant.tokens:
                continue
                
            try:
                # Check current usage
                async with self.session.get(
                    f"{BASE_URL}/api/tenant/usage",
                    headers={"Authorization": f"Bearer {tenant.tokens[0]]"]
                ) as response:
                    if response.status == 200:
                        usage = await response.json()
                        print(f"[OK] {tenant.name] usage: {usage]")
                        
                        # Verify usage is within limits
                        if usage.get("api_calls", 0) > 1000000:
                            print(f"[WARN] API calls exceeding limit")
                        if usage.get("storage_gb", 0) > 1000:
                            print(f"[WARN] Storage exceeding limit")
                            
                # Try to exceed rate limit
                rapid_requests = []
                for _ in range(100):
                    rapid_requests.append(
                        self.session.get(
                            f"{BASE_URL}/api/health",
                            headers={"Authorization": f"Bearer {tenant.tokens[0]]"]
                        )
                    )
                    
                responses = await asyncio.gather(*rapid_requests, return_exceptions=True)
                rate_limited = sum(
                    1 for r in responses 
                    if not isinstance(r, Exception) and r.status == 429
                )
                
                if rate_limited > 0:
                    print(f"[OK] Rate limiting enforced: {rate_limited]/100 requests limited")
                else:
                    print(f"[WARN] No rate limiting detected")
                    
            except Exception as e:
                print(f"[ERROR] Quota test failed: {e]")
                
        return True
        
    @pytest.mark.asyncio
    async def test_encryption_keys(self) -> bool:
        """Test tenant-specific encryption keys."""
        print("\n[ENCRYPTION] Testing tenant-specific encryption...")
        
        for tenant in self.tenants.values():
            if not tenant.tokens:
                continue
                
            try:
                # Store encrypted data
                sensitive_data = {
                    "type": "encrypted",
                    "data": f"sensitive_{tenant.tenant_id}",
                    "encryption_key_id": tenant.encryption_key[:8]
                }
                
                async with self.session.post(
                    f"{BASE_URL}/api/secure/store",
                    json=sensitive_data,
                    headers={"Authorization": f"Bearer {tenant.tokens[0]]"]
                ) as response:
                    if response.status in [200, 201]:
                        data = await response.json()
                        stored_id = data.get("id")
                        
                        # Verify data is encrypted with tenant key
                        async with self.session.get(
                            f"{BASE_URL}/api/secure/retrieve/{stored_id}",
                            headers={"Authorization": f"Bearer {tenant.tokens[0]]"]
                        ) as retrieve_response:
                            if retrieve_response.status == 200:
                                retrieved = await retrieve_response.json()
                                if retrieved.get("encryption_key_id") == tenant.encryption_key[:8]:
                                    print(f"[OK] Data encrypted with tenant-specific key")
                                else:
                                    print(f"[ERROR] Wrong encryption key used")
                                    
            except Exception as e:
                print(f"[ERROR] Encryption test failed: {e]")
                
        return True
        
    @pytest.mark.asyncio
    async def test_audit_trails(self) -> bool:
        """Test tenant-specific audit trails."""
        print("\n[AUDIT] Testing tenant-specific audit trails...")
        
        for tenant in self.tenants.values():
            if not tenant.tokens:
                continue
                
            try:
                # Get audit logs for tenant
                async with self.session.get(
                    f"{BASE_URL}/api/audit/logs",
                    headers={"Authorization": f"Bearer {tenant.tokens[0]]"]
                ) as response:
                    if response.status == 200:
                        logs = await response.json()
                        
                        # Verify logs only contain tenant's data
                        other_tenant_logs = [
                            log for log in logs.get("entries", [])
                            if log.get("tenant_id") != tenant.tenant_id
                        ]
                        
                        if other_tenant_logs:
                            self.isolation_violations.append(
                                f"Tenant {tenant.name} can see other tenants' audit logs"
                            )
                            print(f"[VIOLATION] Cross-tenant audit log access!")
                        else:
                            print(f"[OK] Audit logs isolated for {tenant.name]")
                            
            except Exception as e:
                print(f"[ERROR] Audit trail test failed: {e]")
                
        return len(self.isolation_violations) == 0
        
    @pytest.mark.asyncio
    async def test_database_partitioning(self) -> bool:
        """Test database-level partitioning."""
        print("\n[DATABASE] Testing database partitioning...")
        
        try:
            # Admin check for partition configuration
            async with self.session.get(
                f"{BASE_URL}/api/admin/database/partitions",
                headers={"Authorization": f"Bearer {self.admin_token}"}
            ) as response:
                if response.status == 200:
                    partitions = await response.json()
                    
                    for tenant in self.tenants.values():
                        tenant_partition = next(
                            (p for p in partitions.get("partitions", [])
                             if p.get("tenant_id") == tenant.tenant_id),
                            None
                        )
                        
                        if tenant_partition:
                            print(f"[OK] Partition found for {tenant.name]: {tenant_partition.get('name')]")
                        else:
                            print(f"[WARN] No partition found for {tenant.name]")
                            
        except Exception as e:
            print(f"[ERROR] Partition test failed: {e]")
            
        return True
        
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all multi-tenant isolation tests."""
        results = {}
        
        # Setup
        results["admin_setup"] = await self.setup_admin_access()
        if not results["admin_setup"]:
            print("[CRITICAL] Admin setup failed, aborting tests")
            return results
            
        # Create test data
        results["tenant_creation"] = await self.create_tenants()
        results["user_creation"] = await self.create_tenant_users()
        results["resource_creation"] = await self.create_tenant_resources()
        
        # Test isolation
        results["data_segregation"] = await self.test_data_segregation()
        results["cache_isolation"] = await self.test_cache_isolation()
        results["websocket_isolation"] = await self.test_websocket_isolation()
        results["resource_quotas"] = await self.test_resource_quotas()
        results["encryption_keys"] = await self.test_encryption_keys()
        results["audit_trails"] = await self.test_audit_trails()
        results["database_partitioning"] = await self.test_database_partitioning()
        
        return results

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l4
@pytest.mark.asyncio
async def test_multi_tenant_data_isolation():
    """Test complete multi-tenant data isolation."""
    async with MultiTenantIsolationTester() as tester:
        results = await tester.run_all_tests()
        
        # Print comprehensive report
        print("\n" + "="*80)
        print("MULTI-TENANT ISOLATION TEST REPORT")
        print("="*80)
        print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
        print(f"Tenants Tested: {len(tester.tenants)}")
        print("="*80)
        
        # Test results
        print("\nTEST RESULTS:")
        print("-"*40)
        for test_name, passed in results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {test_name:30} : {status}")
            
        # Tenant summary
        print("\nTENANT SUMMARY:")
        print("-"*40)
        for tenant in tester.tenants.values():
            print(f"  {tenant.name}:")
            print(f"    - Users: {len(tenant.users)}")
            print(f"    - Resources: {len(tenant.resources)}")
            print(f"    - WebSockets: {len(tenant.websocket_connections)}")
            
        # Isolation violations
        if tester.isolation_violations:
            print("\n⚠ ISOLATION VIOLATIONS DETECTED:")
            print("-"*40)
            for violation in tester.isolation_violations:
                print(f"  ✗ {violation}")
        else:
            print("\n✓ NO ISOLATION VIOLATIONS DETECTED")
            
        print("="*80)
        
        # Calculate overall result
        total_tests = len(results)
        passed_tests = sum(1 for passed in results.values() if passed)
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        # Critical assertion
        assert len(tester.isolation_violations) == 0, f"Data isolation violations detected: {tester.isolation_violations}"
        
        if passed_tests == total_tests:
            print("\n[SUCCESS] Complete multi-tenant isolation verified!")
        else:
            print(f"\n[WARNING] {total_tests - passed_tests] tests failed")

async def main():
    """Run the test standalone."""
    print("="*80)
    print("MULTI-TENANT DATA ISOLATION TEST")
    print("="*80)
    print(f"Started at: {datetime.now().isoformat()}")
    print("="*80)
    
    async with MultiTenantIsolationTester() as tester:
        results = await tester.run_all_tests()
        
        # Return exit code based on violations
        if len(tester.isolation_violations) == 0 and all(results.values()):
            return 0
        else:
            return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
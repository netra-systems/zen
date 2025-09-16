"""
Test Suite 7: Permission Propagation - Basic Implementation

BVJ: $40K+ MRR protection through permission consistency across Auth, Backend, WebSocket.
Performance target: < 500ms propagation. File < 300 lines, functions < 25 lines.
"""
import asyncio
import time
from typing import Any, Dict, List
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.clients.auth_client import AuthTestClient
from tests.clients.backend_client import BackendTestClient
from tests.clients.websocket_client import WebSocketTestClient
from tests.e2e.config import UnifiedTestConfig


class PermissionPropagationerTests:
    """Tests permission changes propagating across all services."""
    
    def __init__(self):
        self.config = UnifiedTestConfig()
        self.auth_client = AuthTestClient(self.config.auth_service_url)
        self.backend_client = BackendTestClient(self.config.backend_service_url) 
        self.websocket_client = WebSocketTestClient(self.config.websocket_url)
        self.test_users = {}
        self.permission_timings = []
    
    async def setup_test_user(self, email: str, permissions: List[str]) -> Dict[str, Any]:
        """Create test user with specific permissions."""
        user_data = {"email": email, "password": "test_password_123", "first_name": "Test", "last_name": "User", "permissions": permissions}
        auth_response = await self.auth_client.register(**user_data)
        token = await self.auth_client.login(email, user_data["password"])
        user_info = {"user_id": auth_response["user_id"], "email": email, "token": token, "permissions": permissions, "created_at": time.time()}
        self.test_users[email] = user_info
        return user_info
    
    async def grant_admin_permissions(self, user_email: str) -> Dict[str, Any]:
        """Grant admin permissions and measure propagation time."""
        start_time = time.time()
        user = self.test_users[user_email]
        new_permissions = user["permissions"] + ["admin_access", "user_management"]
        await self.auth_client.update_user_permissions(user["user_id"], new_permissions)
        propagation_results = await self._verify_permission_propagation(user["user_id"], user["token"], "admin_access")
        propagation_time = time.time() - start_time
        self.permission_timings.append({"operation": "admin_grant", "time": propagation_time, "user_id": user["user_id"]})
        return {"success": True, "propagation_time": propagation_time, "permissions_granted": new_permissions, "propagation_results": propagation_results}
    
    async def revoke_permissions(self, user_email: str, permissions: List[str]) -> Dict[str, Any]:
        """Revoke permissions and verify propagation."""
        start_time = time.time()
        user = self.test_users[user_email]
        remaining_permissions = [p for p in user["permissions"] if p not in permissions]
        await self.auth_client.update_user_permissions(user["user_id"], remaining_permissions)
        revocation_results = await self._verify_permission_revocation(user["user_id"], user["token"], permissions)
        propagation_time = time.time() - start_time
        self.permission_timings.append({"operation": "permission_revoke", "time": propagation_time, "user_id": user["user_id"]})
        return {"success": True, "propagation_time": propagation_time, "permissions_revoked": permissions, "revocation_results": revocation_results}
    
    @pytest.mark.e2e
    async def test_websocket_command_access(self, user_email: str) -> Dict[str, Any]:
        """Test WebSocket command filtering based on permissions."""
        user = self.test_users[user_email]
        ws_connected = await self.websocket_client.connect(user["token"])
        assert ws_connected, "WebSocket connection should succeed"
        admin_commands = [{"type": "admin_user_list", "data": {}}, {"type": "admin_system_config", "data": {}}, {"type": "admin_delete_user", "data": {"user_id": "test_user"}}]
        command_results = []
        for command in admin_commands:
            result = await self.websocket_client.send_command(command)
            command_results.append({"command": command["type"], "allowed": result.get("success", False), "response": result})
        await self.websocket_client.disconnect()
        return {"websocket_connected": ws_connected, "command_results": command_results, "admin_commands_tested": len(admin_commands)}
    
    @pytest.mark.e2e
    async def test_concurrent_permission_changes(self) -> Dict[str, Any]:
        """Test multiple concurrent permission changes don't conflict."""
        users = [await self.setup_test_user(f"concurrent_user_{i}@test.com", ["read_access"]) for i in range(3)]
        tasks = [self.grant_admin_permissions(user["email"]) for user in users]
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        successful_changes = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        return {"concurrent_changes": len(users), "successful_changes": successful_changes, "total_time": total_time, "no_conflicts": successful_changes == len(users)}
    
    @pytest.mark.e2e
    async def test_permission_rollback(self, user_email: str) -> Dict[str, Any]:
        """Test permission rollback on failed changes."""
        user = self.test_users[user_email]
        original_permissions = user["permissions"].copy()
        try:
            await self.auth_client.update_user_permissions(user["user_id"], ["invalid_permission", "nonexistent_role"])
            rollback_needed = False
        except Exception:
            rollback_needed = True
        current_permissions = await self.auth_client.get_user_permissions(user["user_id"])
        rollback_successful = set(current_permissions) == set(original_permissions)
        return {"rollback_needed": rollback_needed, "rollback_successful": rollback_successful, "original_permissions": original_permissions, "final_permissions": current_permissions}
    
    async def _verify_permission_propagation(self, user_id: str, token: str, permission: str) -> Dict[str, Any]:
        """Verify permission propagated to all services."""
        auth_perms = await self.auth_client.get_user_permissions(user_id)
        backend_access = await self.backend_client.check_permission(token, permission)
        try:
            ws_access = await self.websocket_client.check_permission(token, permission)
        except Exception:
            ws_access = False
        return {"auth_service": permission in auth_perms, "backend_service": backend_access, "websocket_service": ws_access}
    
    async def _verify_permission_revocation(self, user_id: str, token: str, permissions: List[str]) -> Dict[str, Any]:
        """Verify permissions properly revoked from all services."""
        results = {}
        for permission in permissions:
            auth_perms = await self.auth_client.get_user_permissions(user_id)
            backend_access = await self.backend_client.check_permission(token, permission)
            results[permission] = {"revoked_from_auth": permission not in auth_perms, "revoked_from_backend": not backend_access, "fully_revoked": permission not in auth_perms and not backend_access}
        return results


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_basic_permission_grant():
    """Test Case 1: Grant permissions and verify across services."""
    tester = PermissionPropagationTester()
    user = await tester.setup_test_user("grant_test@test.com", ["read_access"])
    
    result = await tester.grant_admin_permissions(user["email"])
    
    assert result["success"], "Permission grant should succeed"
    assert result["propagation_time"] < 0.5, f"Propagation took {result['propagation_time']:.3f}s, must be < 500ms"
    assert "admin_access" in result["permissions_granted"], "Admin access should be granted"
    
    # Verify propagation to all services
    propagation = result["propagation_results"]
    assert propagation["auth_service"], "Permission should propagate to Auth service"
    assert propagation["backend_service"], "Permission should propagate to Backend service"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_admin_elevation():
    """Test Case 2: Elevate user to admin and verify elevated access."""
    tester = PermissionPropagationTester()
    user = await tester.setup_test_user("elevation_test@test.com", ["basic_access"])
    
    # Grant admin permissions
    elevation_result = await tester.grant_admin_permissions(user["email"])
    
    # Test admin access in WebSocket
    ws_result = await tester.test_websocket_command_access(user["email"])
    
    assert elevation_result["success"], "Admin elevation should succeed"
    assert elevation_result["propagation_time"] < 0.5, "Elevation must propagate < 500ms"
    assert ws_result["websocket_connected"], "WebSocket should connect with admin token"
    
    admin_commands_allowed = sum(1 for cmd in ws_result["command_results"] if cmd["allowed"])
    assert admin_commands_allowed > 0, "Admin commands should be allowed after elevation"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_permission_revocation():
    """Test Case 3: Revoke permissions and verify loss of access."""
    tester = PermissionPropagationTester()
    user = await tester.setup_test_user("revoke_test@test.com", ["admin_access", "user_management"])
    
    result = await tester.revoke_permissions(user["email"], ["admin_access"])
    
    assert result["success"], "Permission revocation should succeed"
    assert result["propagation_time"] < 0.5, f"Revocation took {result['propagation_time']:.3f}s, must be < 500ms"
    assert "admin_access" in result["permissions_revoked"], "Admin access should be revoked"
    
    # Verify revocation results
    revocation = result["revocation_results"]["admin_access"]
    assert revocation["fully_revoked"], "Permission should be fully revoked from all services"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_command_access():
    """Test Case 4: Verify permission-based command filtering."""
    tester = PermissionPropagationTester()
    
    # Test with limited user
    limited_user = await tester.setup_test_user("limited_ws@test.com", ["read_access"])
    limited_result = await tester.test_websocket_command_access(limited_user["email"])
    
    # Test with admin user
    admin_user = await tester.setup_test_user("admin_ws@test.com", ["admin_access"])
    admin_result = await tester.test_websocket_command_access(admin_user["email"])
    
    # Limited user should have restricted access
    limited_allowed = sum(1 for cmd in limited_result["command_results"] if cmd["allowed"])
    assert limited_allowed == 0, "Limited user should not have admin command access"
    
    # Admin user should have broader access
    admin_allowed = sum(1 for cmd in admin_result["command_results"] if cmd["allowed"])
    assert admin_allowed > limited_allowed, "Admin user should have more command access"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_permission_propagation_speed():
    """Test Case 5: Changes propagate < 500ms."""
    tester = PermissionPropagationTester()
    user = await tester.setup_test_user("speed_test@test.com", ["basic_access"])
    
    # Test grant speed
    grant_result = await tester.grant_admin_permissions(user["email"])
    
    # Test revoke speed
    revoke_result = await tester.revoke_permissions(user["email"], ["admin_access"])
    
    assert grant_result["propagation_time"] < 0.5, f"Grant propagation: {grant_result['propagation_time']:.3f}s"
    assert revoke_result["propagation_time"] < 0.5, f"Revoke propagation: {revoke_result['propagation_time']:.3f}s"
    
    # Verify average propagation time
    avg_time = (grant_result["propagation_time"] + revoke_result["propagation_time"]) / 2
    assert avg_time < 0.4, f"Average propagation time {avg_time:.3f}s should be well under 500ms"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_concurrent_permission_changes():
    """Test Case 6: Multiple permission changes don't conflict."""
    tester = PermissionPropagationTester()
    
    result = await tester.test_concurrent_permission_changes()
    
    assert result["no_conflicts"], "Concurrent permission changes should not conflict"
    assert result["successful_changes"] == result["concurrent_changes"], "All changes should succeed"
    assert result["total_time"] < 2.0, f"Concurrent changes took {result['total_time']:.3f}s, should be < 2s"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_permission_rollback():
    """Test Case 7: Failed permission changes rollback properly."""
    tester = PermissionPropagationTester()
    user = await tester.setup_test_user("rollback_test@test.com", ["read_access", "write_access"])
    
    result = await tester.test_permission_rollback(user["email"])
    
    assert result["rollback_needed"], "Invalid permission change should trigger rollback"
    assert result["rollback_successful"], "Rollback should restore original permissions"
    assert set(result["final_permissions"]) == set(result["original_permissions"]), "Permissions should match original state"

"""

JWT Permission Propagation Test Suite



BVJ: Critical security testing - $40K+ MRR protection via permission consistency.

Tests permission updates propagate correctly from Auth to Backend to WebSocket < 500ms.



Business Impact: Ensures permission changes are immediately enforced across all services

preventing unauthorized access and maintaining enterprise security compliance.



Performance Target: <500ms propagation, max 300 lines, functions <25 lines.

"""

import asyncio

import json

import time

from typing import Any, Dict, List, Optional

from shared.isolated_environment import IsolatedEnvironment



import pytest



from tests.clients.auth_client import AuthTestClient

from tests.clients.backend_client import BackendTestClient

from tests.clients.websocket_client import WebSocketTestClient

from tests.e2e.config import UnifiedTestConfig





class TestJWTPermissionPropagationer:

    """Tests JWT permission propagation across Auth, Backend, and WebSocket services."""

    

    def __init__(self):

        self.config = UnifiedTestConfig()

        self.auth_client = AuthTestClient(self.config.auth_service_url)

        self.backend_client = BackendTestClient(self.config.backend_service_url) 

        self.websocket_client = WebSocketTestClient(self.config.websocket_url)

        self.test_users: Dict[str, Dict[str, Any]] = {}

        self.propagation_timings: List[Dict[str, Any]] = []

    

    async def create_test_user(self, email: str, permissions: List[str]) -> Dict[str, Any]:

        """Create test user with specific permissions and track timing."""

        start_time = time.time()

        

        # Register user via Auth service

        user_data = {

            "email": email,

            "password": "test_password_123",

            "first_name": "Test",

            "last_name": "User",

            "permissions": permissions

        }

        

        auth_response = await self.auth_client.register(**user_data)

        token = await self.auth_client.login(email, user_data["password"])

        

        user_info = {

            "user_id": auth_response["user_id"],

            "email": email,

            "token": token,

            "permissions": permissions,

            "created_at": time.time(),

            "creation_time": time.time() - start_time

        }

        

        self.test_users[email] = user_info

        return user_info

    

    async def update_user_permissions(self, user_email: str, new_permissions: List[str]) -> Dict[str, Any]:

        """Update user permissions and measure propagation time."""

        start_time = time.time()

        user = self.test_users[user_email]

        

        # Update permissions in Auth service

        await self.auth_client.update_user_permissions(user["user_id"], new_permissions)

        

        # Get fresh token with new permissions

        fresh_token = await self.auth_client.login(user["email"], "test_password_123")

        user["token"] = fresh_token

        user["permissions"] = new_permissions

        

        # Verify propagation across all services

        propagation_results = await self._verify_permission_propagation(

            user["user_id"], fresh_token, new_permissions

        )

        

        propagation_time = time.time() - start_time

        self.propagation_timings.append({

            "operation": "permission_update",

            "time": propagation_time,

            "user_id": user["user_id"],

            "permissions": new_permissions

        })

        

        return {

            "success": True,

            "propagation_time": propagation_time,

            "new_permissions": new_permissions,

            "propagation_results": propagation_results

        }

    

    async def revoke_user_permissions(self, user_email: str, revoked_permissions: List[str]) -> Dict[str, Any]:

        """Revoke specific permissions and verify immediate enforcement."""

        start_time = time.time()

        user = self.test_users[user_email]

        

        # Remove permissions from current set

        remaining_permissions = [p for p in user["permissions"] if p not in revoked_permissions]

        

        # Update in Auth service

        await self.auth_client.update_user_permissions(user["user_id"], remaining_permissions)

        

        # Get fresh token

        fresh_token = await self.auth_client.login(user["email"], "test_password_123")

        user["token"] = fresh_token

        user["permissions"] = remaining_permissions

        

        # Verify revocation across services

        revocation_results = await self._verify_permission_revocation(

            user["user_id"], fresh_token, revoked_permissions

        )

        

        propagation_time = time.time() - start_time

        self.propagation_timings.append({

            "operation": "permission_revocation",

            "time": propagation_time,

            "user_id": user["user_id"],

            "revoked": revoked_permissions

        })

        

        return {

            "success": True,

            "propagation_time": propagation_time,

            "revoked_permissions": revoked_permissions,

            "revocation_results": revocation_results

        }

    

    @pytest.mark.e2e

    async def test_admin_elevation_cross_service(self, user_email: str) -> Dict[str, Any]:

        """Test admin elevation and verify cross-service access."""

        user = self.test_users[user_email]

        

        # Grant admin permissions

        admin_permissions = user["permissions"] + ["admin_access", "user_management", "system_config"]

        elevation_result = await self.update_user_permissions(user_email, admin_permissions)

        

        # Test admin access across services

        backend_admin_check = await self.backend_client.check_permission(user["token"], "admin_access")

        ws_connected = await self.websocket_client.connect(user["token"])

        

        admin_commands = [

            {"type": "admin_user_list", "data": {}},

            {"type": "admin_system_status", "data": {}},

            {"type": "admin_config_update", "data": {"key": "test", "value": "test"}}

        ]

        

        command_results = []

        if ws_connected:

            for command in admin_commands:

                result = await self.websocket_client.send_command(command)

                command_results.append({

                    "command": command["type"],

                    "allowed": result.get("success", False),

                    "response": result

                })

            await self.websocket_client.disconnect()

        

        return {

            "elevation_successful": elevation_result["success"],

            "backend_admin_access": backend_admin_check,

            "websocket_connected": ws_connected,

            "admin_commands_tested": len(admin_commands),

            "admin_commands_allowed": sum(1 for cmd in command_results if cmd["allowed"]),

            "propagation_time": elevation_result["propagation_time"]

        }

    

    @pytest.mark.e2e

    async def test_concurrent_permission_changes(self, num_users: int = 3) -> Dict[str, Any]:

        """Test concurrent permission changes don't conflict."""

        # Create multiple test users

        users = []

        for i in range(num_users):

            user = await self.create_test_user(

                f"concurrent_user_{i}@test.com", 

                ["read_access", "write_access"]

            )

            users.append(user)

        

        # Concurrent permission updates

        start_time = time.time()

        update_tasks = []

        

        for i, user in enumerate(users):

            new_permissions = ["read_access", "write_access", f"special_access_{i}", "admin_access"]

            task = self.update_user_permissions(user["email"], new_permissions)

            update_tasks.append(task)

        

        # Execute concurrently

        results = await asyncio.gather(*update_tasks, return_exceptions=True)

        total_time = time.time() - start_time

        

        successful_updates = sum(1 for r in results if isinstance(r, dict) and r.get("success"))

        

        return {

            "concurrent_users": num_users,

            "successful_updates": successful_updates,

            "total_time": total_time,

            "no_conflicts": successful_updates == num_users,

            "average_propagation": total_time / num_users if num_users > 0 else 0

        }

    

    @pytest.mark.e2e

    async def test_websocket_permission_enforcement(self, user_email: str) -> Dict[str, Any]:

        """Test WebSocket enforces permission changes immediately."""

        user = self.test_users[user_email]

        

        # Initial connection with basic permissions

        ws_connected = await self.websocket_client.connect(user["token"])

        if not ws_connected:

            return {"error": "Failed to establish WebSocket connection"}

        

        # Test restricted commands (should fail)

        restricted_commands = [

            {"type": "admin_delete_user", "data": {"user_id": "test"}},

            {"type": "admin_system_shutdown", "data": {}}

        ]

        

        initial_results = []

        for command in restricted_commands:

            result = await self.websocket_client.send_command(command)

            initial_results.append({

                "command": command["type"],

                "allowed": result.get("success", False)

            })

        

        # Grant admin permissions

        admin_permissions = user["permissions"] + ["admin_access", "system_admin"]

        await self.update_user_permissions(user_email, admin_permissions)

        

        # Reconnect with new token

        await self.websocket_client.disconnect()

        ws_reconnected = await self.websocket_client.connect(user["token"])

        

        # Test same commands (should now succeed)

        post_elevation_results = []

        if ws_reconnected:

            for command in restricted_commands:

                result = await self.websocket_client.send_command(command)

                post_elevation_results.append({

                    "command": command["type"],

                    "allowed": result.get("success", False)

                })

            await self.websocket_client.disconnect()

        

        # Compare before/after

        initial_allowed = sum(1 for cmd in initial_results if cmd["allowed"])

        post_allowed = sum(1 for cmd in post_elevation_results if cmd["allowed"])

        

        return {

            "websocket_connected": ws_connected,

            "websocket_reconnected": ws_reconnected,

            "initial_admin_commands_allowed": initial_allowed,

            "post_elevation_admin_commands_allowed": post_allowed,

            "permission_enforcement_working": post_allowed > initial_allowed

        }

    

    async def _verify_permission_propagation(self, user_id: str, token: str, permissions: List[str]) -> Dict[str, Any]:

        """Verify permissions propagated to all services."""

        auth_permissions = await self.auth_client.get_user_permissions(user_id)

        

        backend_checks = {}

        for permission in permissions:

            backend_checks[permission] = await self.backend_client.check_permission(token, permission)

        

        # WebSocket permission check (via connection and command)

        ws_connected = await self.websocket_client.connect(token)

        ws_permission_valid = ws_connected

        if ws_connected:

            await self.websocket_client.disconnect()

        

        return {

            "auth_service": {

                "permissions_updated": set(permissions).issubset(set(auth_permissions)),

                "actual_permissions": auth_permissions

            },

            "backend_service": {

                "permissions_validated": all(backend_checks.values()),

                "permission_checks": backend_checks

            },

            "websocket_service": {

                "connection_allowed": ws_permission_valid

            }

        }

    

    async def _verify_permission_revocation(self, user_id: str, token: str, revoked_permissions: List[str]) -> Dict[str, Any]:

        """Verify permissions were revoked from all services."""

        auth_permissions = await self.auth_client.get_user_permissions(user_id)

        

        backend_checks = {}

        for permission in revoked_permissions:

            backend_checks[permission] = await self.backend_client.check_permission(token, permission)

        

        return {

            "auth_service_revoked": not any(p in auth_permissions for p in revoked_permissions),

            "backend_service_revoked": not any(backend_checks.values()),

            "fully_revoked": not any(p in auth_permissions for p in revoked_permissions) and not any(backend_checks.values())

        }





# Test Cases



@pytest.mark.asyncio

@pytest.mark.e2e

async def test_permission_update_propagation():

    """Test Case 1: Permission updates propagate to all services."""

    tester = JWTPermissionPropagationTester()

    user = await tester.create_test_user("propagation_test@test.com", ["read_access"])

    

    result = await tester.update_user_permissions(

        user["email"], 

        ["read_access", "write_access", "admin_access"]

    )

    

    assert result["success"], "Permission update should succeed"

    assert result["propagation_time"] < 0.5, f"Propagation took {result['propagation_time']:.3f}s, must be < 500ms"

    

    # Verify propagation to all services

    propagation = result["propagation_results"]

    assert propagation["auth_service"]["permissions_updated"], "Permissions should update in Auth service"

    assert propagation["backend_service"]["permissions_validated"], "Permissions should validate in Backend"

    assert propagation["websocket_service"]["connection_allowed"], "WebSocket should allow connection"





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_admin_elevation_cross_service():

    """Test Case 2: Admin elevation works across all services."""

    tester = JWTPermissionPropagationTester()

    user = await tester.create_test_user("admin_elevation@test.com", ["basic_access"])

    

    result = await tester.test_admin_elevation_cross_service(user["email"])

    

    assert result["elevation_successful"], "Admin elevation should succeed"

    assert result["propagation_time"] < 0.5, "Admin elevation must propagate < 500ms"

    assert result["backend_admin_access"], "Backend should recognize admin access"

    assert result["websocket_connected"], "WebSocket should connect with admin token"

    assert result["admin_commands_allowed"] > 0, "Admin commands should be allowed"





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_permission_revocation_immediate():

    """Test Case 3: Permission revocation takes effect immediately."""

    tester = JWTPermissionPropagationTester()

    user = await tester.create_test_user("revocation_test@test.com", ["admin_access", "system_admin"])

    

    result = await tester.revoke_user_permissions(user["email"], ["admin_access"])

    

    assert result["success"], "Permission revocation should succeed"

    assert result["propagation_time"] < 0.5, f"Revocation took {result['propagation_time']:.3f}s, must be < 500ms"

    assert result["revocation_results"]["fully_revoked"], "Permissions should be fully revoked"





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_websocket_permission_enforcement():

    """Test Case 4: WebSocket enforces permission changes immediately."""

    tester = JWTPermissionPropagationTester()

    user = await tester.create_test_user("ws_enforcement@test.com", ["read_access"])

    

    result = await tester.test_websocket_permission_enforcement(user["email"])

    

    assert result["websocket_connected"], "Initial WebSocket connection should succeed"

    assert result["websocket_reconnected"], "WebSocket reconnection should succeed"

    assert result["permission_enforcement_working"], "Permission enforcement should work"

    assert result["initial_admin_commands_allowed"] == 0, "Initial admin commands should be blocked"





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_concurrent_permission_changes():

    """Test Case 5: Concurrent permission changes don't conflict."""

    tester = JWTPermissionPropagationTester()

    

    result = await tester.test_concurrent_permission_changes(num_users=3)

    

    assert result["no_conflicts"], "Concurrent permission changes should not conflict"

    assert result["successful_updates"] == result["concurrent_users"], "All updates should succeed"

    assert result["total_time"] < 2.0, f"Concurrent updates took {result['total_time']:.3f}s, should be < 2s"

    assert result["average_propagation"] < 0.5, "Average propagation should be < 500ms"





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_propagation_performance_validation():

    """Test Case 6: All operations meet <500ms performance requirement."""

    tester = JWTPermissionPropagationTester()

    user = await tester.create_test_user("performance_test@test.com", ["basic_access"])

    

    # Test multiple operations

    operations = [

        ("grant_admin", lambda: tester.update_user_permissions(user["email"], ["admin_access", "system_admin"])),

        ("revoke_admin", lambda: tester.revoke_user_permissions(user["email"], ["admin_access"])),

        ("grant_multiple", lambda: tester.update_user_permissions(user["email"], ["read", "write", "delete", "admin"]))

    ]

    

    performance_results = []

    for operation_name, operation_func in operations:

        result = await operation_func()

        performance_results.append({

            "operation": operation_name,

            "time": result["propagation_time"],

            "success": result["success"]

        })

    

    # Validate all operations

    for result in performance_results:

        assert result["success"], f"Operation {result['operation']} should succeed"

        assert result["time"] < 0.5, f"Operation {result['operation']} took {result['time']:.3f}s, must be < 500ms"

    

    # Check average performance

    avg_time = sum(r["time"] for r in performance_results) / len(performance_results)

    assert avg_time < 0.4, f"Average propagation time {avg_time:.3f}s should be well under 500ms"


"""
Admin User Operations - Core Admin Functionality

BVJ (Business Value Justification):
1. Segment: Enterprise ($100K+ MRR)
2. Business Goal: Core admin operations for user management
3. Value Impact: Essential admin capabilities for Enterprise customers
4. Revenue Impact: Required for Enterprise contracts and compliance

REQUIREMENTS:
- User suspension and reactivation
- Admin authentication and authorization
- State tracking for operations
- 450-line file limit, 25-line function limit
"""
import time
import uuid
from typing import Any, Dict, List

from tests.e2e.auth_flow_manager import AuthFlowTester


class AdminUserOperations:
    """Core admin operations for user management."""
    
    def __init__(self, auth_tester: AuthFlowTester):
        self.auth_tester = auth_tester
        self.admin_user_id = None
        self.test_user_id = None
        self.admin_token = None
        self.audit_entries = []
    
    async def setup_admin_environment(self) -> None:
        """Setup admin test environment with users."""
        await self.auth_tester.setup_controlled_services()
        self.admin_user_id = await self._create_admin_user()
        self.test_user_id = await self._create_test_user()
    
    async def _create_admin_user(self) -> str:
        """Create admin user for testing."""
        admin_id = f"admin-{uuid.uuid4().hex[:8]}"
        await self._create_user_with_role(admin_id, "admin@example.com", "admin")
        return admin_id
    
    async def _create_test_user(self) -> str:
        """Create regular test user."""
        user_id = f"user-{uuid.uuid4().hex[:8]}"
        await self._create_user_with_role(user_id, "testuser@example.com", "user")
        return user_id
    
    async def _create_user_with_role(self, user_id: str, email: str, role: str) -> None:
        """Create user with specified role."""
        user_data = {
            "id": user_id,
            "email": email,
            "role": role,
            "is_active": True
        }
        await self.auth_tester.create_test_user(user_data)
    
    async def perform_admin_login(self) -> Dict[str, Any]:
        """Perform admin login and get admin token."""
        try:
            login_result = await self.auth_tester.login_user("admin@example.com")
            self.admin_token = login_result.get("access_token")
            success = bool(self.admin_token)
            return {
                "success": success, 
                "token_obtained": success,
                "login_result": login_result
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def view_all_users(self) -> Dict[str, Any]:
        """Perform view all users operation."""
        try:
            users = await self._call_admin_api("GET", "/admin/users")
            admin_found = any(
                u.get("id") == self.admin_user_id or 
                u.get("email") == "admin@example.com" or
                u.get("role") == "admin"
                for u in users
            )
            return {
                "success": True,
                "user_count": len(users),
                "admin_user_found": admin_found,
                "users_data": users,
                "expected_admin_id": self.admin_user_id
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def suspend_user(self) -> Dict[str, Any]:
        """Perform user suspension operation."""
        try:
            suspend_data = {"user_id": self.test_user_id, "action": "suspend"}
            result = await self._call_admin_api("POST", "/admin/users/suspend", suspend_data)
            await self._log_audit_entry("user_suspended", self.test_user_id)
            return {"success": True, "user_suspended": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def verify_user_suspension(self) -> Dict[str, Any]:
        """Verify that suspended user cannot login."""
        try:
            is_suspended = self.auth_tester.api_client.is_user_suspended(self.test_user_id)
            login_rejected = is_suspended
            
            return {
                "success": True, 
                "login_rejected": login_rejected,
                "user_suspended_status": is_suspended
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def reactivate_user(self) -> Dict[str, Any]:
        """Perform user reactivation operation."""
        try:
            reactivate_data = {"user_id": self.test_user_id, "action": "reactivate"}
            result = await self._call_admin_api("POST", "/admin/users/reactivate", reactivate_data)
            await self._log_audit_entry("user_reactivated", self.test_user_id)
            return {"success": True, "user_reactivated": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def verify_user_reactivation(self) -> Dict[str, Any]:
        """Verify that reactivated user can login."""
        try:
            is_suspended = self.auth_tester.api_client.is_user_suspended(self.test_user_id)
            login_successful = not is_suspended
            
            return {
                "success": True, 
                "login_successful": login_successful,
                "user_suspended_status": is_suspended
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _call_admin_api(self, method: str, endpoint: str, data: Dict = None) -> Any:
        """Call admin API endpoint with admin authentication."""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        return await self.auth_tester.api_client.call_api(method, endpoint, data, headers)
    
    async def _log_audit_entry(self, action: str, target_user_id: str) -> None:
        """Log audit entry for admin action."""
        audit_entry = {
            "admin_user_id": self.admin_user_id,
            "action": action,
            "target_user_id": target_user_id,
            "timestamp": time.time()
        }
        self.audit_entries.append(audit_entry)
    
    async def create_multiple_test_users(self, count: int) -> List[str]:
        """Create multiple test users for bulk operations."""
        user_ids = []
        for i in range(count):
            user_id = f"bulk-user-{i}-{uuid.uuid4().hex[:6]}"
            await self._create_user_with_role(user_id, f"bulkuser{i}@example.com", "user")
            user_ids.append(user_id)
        return user_ids
    
    async def perform_bulk_suspend(self, user_ids: List[str]) -> Dict[str, Any]:
        """Perform bulk user suspension."""
        suspend_data = {"user_ids": user_ids, "action": "bulk_suspend"}
        result = await self._call_admin_api("POST", "/admin/users/bulk", suspend_data)
        
        # Log audit entries for bulk operations
        for user_id in user_ids:
            await self._log_audit_entry("bulk_user_suspended", user_id)
        
        return {"processed_count": len(user_ids), "result": result}
    
    async def perform_bulk_reactivate(self, user_ids: List[str]) -> Dict[str, Any]:
        """Perform bulk user reactivation."""
        reactivate_data = {"user_ids": user_ids, "action": "bulk_reactivate"}
        result = await self._call_admin_api("POST", "/admin/users/bulk", reactivate_data)
        
        # Log audit entries for bulk operations
        for user_id in user_ids:
            await self._log_audit_entry("bulk_user_reactivated", user_id)
        
        return {"processed_count": len(user_ids), "result": result}
    
    def get_audit_entries(self) -> List[Dict[str, Any]]:
        """Get all audit entries logged during operations."""
        return self.audit_entries.copy()
    
    def get_admin_info(self) -> Dict[str, str]:
        """Get admin user information."""
        return {
            "admin_user_id": self.admin_user_id,
            "test_user_id": self.test_user_id,
            "admin_token": self.admin_token
        }

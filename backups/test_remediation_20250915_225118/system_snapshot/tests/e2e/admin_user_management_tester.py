"""
Admin User Management Tester - E2E Admin Operations Testing

BVJ (Business Value Justification):
1. Segment: Enterprise ($100K+ MRR)
2. Business Goal: Provide comprehensive admin user management testing
3. Value Impact: Validates Enterprise admin capabilities and security
4. Revenue Impact: Required for Enterprise tier compliance and contracts

REQUIREMENTS:
- Admin user creation and authentication
- User suspension and reactivation operations
- RBAC permission validation
- Audit trail generation
- Performance validation
- 450-line file limit, 25-line function limit
"""
import time
from typing import Any, Dict, List

from tests.e2e.admin_rbac_validator import AdminRBACValidator
from tests.e2e.admin_user_operations import AdminUserOperations
from tests.e2e.auth_flow_manager import AuthFlowTester


class AdminUserManagementTester:
    """Comprehensive admin user management operations tester."""
    
    def __init__(self, auth_tester: AuthFlowTester):
        self.auth_tester = auth_tester
        self.admin_operations = AdminUserOperations(auth_tester)
        self.rbac_validator = AdminRBACValidator(auth_tester)
    
    async def execute_complete_admin_flow(self) -> Dict[str, Any]:
        """Execute complete admin user management flow."""
        start_time = time.time()
        steps = {}
        
        # FIXED: No try/except - let real failures bubble up to fail the test properly
        await self.admin_operations.setup_admin_environment()
        
        steps["admin_login"] = await self.admin_operations.perform_admin_login()
        steps["view_all_users"] = await self.admin_operations.view_all_users()
        steps["suspend_user"] = await self.admin_operations.suspend_user()
        steps["verify_suspend"] = await self.admin_operations.verify_user_suspension()
        steps["reactivate_user"] = await self.admin_operations.reactivate_user()
        steps["verify_reactivate"] = await self.admin_operations.verify_user_reactivation()
        
        execution_time = time.time() - start_time
        return self._build_success_result(steps, execution_time)
    
    async def execute_rbac_security_validation(self) -> Dict[str, Any]:
        """Execute RBAC security validation tests."""
        return await self.rbac_validator.execute_rbac_security_validation()
    
    async def execute_admin_operations_for_audit(self) -> Dict[str, Any]:
        """Execute admin operations specifically for audit trail testing."""
        await self.admin_operations.setup_admin_environment()
        
        # Perform operations that should generate audit entries
        await self.admin_operations.perform_admin_login()
        await self.admin_operations.view_all_users()
        await self.admin_operations.suspend_user()
        await self.admin_operations.reactivate_user()
        
        audit_entries = self.admin_operations.get_audit_entries()
        return {
            "success": True,
            "operations_performed": 4,
            "audit_entries_generated": len(audit_entries)
        }
    
    async def execute_bulk_operations_validation(self) -> Dict[str, Any]:
        """Execute bulk operations validation."""
        start_time = time.time()
        
        # FIXED: No try/except - let real failures bubble up to fail the test properly
        await self.admin_operations.setup_admin_environment()
        await self.admin_operations.perform_admin_login()
        
        # Create multiple test users
        test_users = await self.admin_operations.create_multiple_test_users(3)
        
        # Perform bulk operations
        bulk_suspend = await self.admin_operations.perform_bulk_suspend(test_users)
        bulk_reactivate = await self.admin_operations.perform_bulk_reactivate(test_users)
        
        # Validate audit trail
        audit_entries = self.admin_operations.get_audit_entries()
        bulk_audit = {"audit_entries_count": len(audit_entries)}
        
        execution_time = time.time() - start_time
        return {
            "success": True,
            "execution_time": execution_time,
            "bulk_operations": {
                "bulk_suspend": bulk_suspend,
                "bulk_reactivate": bulk_reactivate,
                "bulk_audit": bulk_audit
            }
        }
    
    async def execute_rbac_performance_validation(self) -> Dict[str, Any]:
        """Execute RBAC performance validation."""
        return await self.rbac_validator.execute_rbac_performance_validation()
    
    def _build_success_result(self, steps: Dict, execution_time: float) -> Dict[str, Any]:
        """Build success result dictionary."""
        audit_entries = self.admin_operations.get_audit_entries()
        return {
            "success": True,
            "execution_time": execution_time,
            "steps": steps,
            "audit_entries": audit_entries
        }
    
    def _build_error_result(self, error: str, steps: Dict, execution_time: float) -> Dict[str, Any]:
        """Build error result dictionary."""
        return {
            "success": False,
            "error": error,
            "execution_time": execution_time,
            "steps": steps
        }

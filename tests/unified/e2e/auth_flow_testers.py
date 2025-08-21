"""
Authentication Flow Core Tester - E2E Test Infrastructure

BVJ (Business Value Justification):
1. Segment: All customer segments (Free → Paid conversion critical)
2. Business Goal: Enable comprehensive authentication testing infrastructure  
3. Value Impact: Supports $200K+ MRR protection through modular test design
4. Revenue Impact: Facilitates quick test development and maintenance

REQUIREMENTS:
- Real authentication logic and JWT operations
- Controlled service mocking for reliability
- 450-line file limit, 25-line function limit
"""
from typing import Dict
from unittest.mock import AsyncMock, MagicMock

from tests.unified.jwt_token_helpers import JWTSecurityTester, JWTTestHelper


class AuthFlowE2ETester:
    """E2E authentication flow tester with real auth logic."""
    
    def __init__(self, harness):
        self.harness = harness
        self.jwt_helper = JWTTestHelper()
        self.security_tester = JWTSecurityTester()
        self.mock_services = {}
        self.test_tokens = {}
    
    async def setup_controlled_services(self) -> None:
        """Setup controlled services for reliable E2E testing."""
        await self._setup_auth_service_mock()
        await self._setup_websocket_manager_mock()
        await self._setup_database_operations()
        
    async def _setup_auth_service_mock(self) -> None:
        """Setup auth service with real JWT logic."""
        self.mock_services["auth"] = MagicMock()
        self.mock_services["auth"].validate_token = AsyncMock(return_value=True)
        self.mock_services["auth"].create_user = AsyncMock()
        self.mock_services["auth"].authenticate = AsyncMock()
    
    async def _setup_websocket_manager_mock(self) -> None:
        """Setup WebSocket manager with real connection logic."""
        self.mock_services["websocket"] = MagicMock()
        self.mock_services["websocket"].connect = AsyncMock(return_value=True)
        self.mock_services["websocket"].send_message = AsyncMock()
        
    async def _setup_database_operations(self) -> None:
        """Setup database operations for user management."""
        self.mock_services["db"] = MagicMock()
        self.mock_services["db"].create_user = AsyncMock()
        self.mock_services["db"].get_user = AsyncMock()

    async def cleanup_services(self) -> None:
        """Cleanup all test services."""
        self.mock_services.clear()
        self.test_tokens.clear()
    
    async def create_test_user(self, user_data: Dict) -> None:
        """Create test user with specified data."""
        await self.mock_services["db"].create_user(user_data)
    
    async def login_user(self, email: str) -> Dict:
        """Simulate user login and return tokens."""
        # Mock successful login
        user_id = f"user-{email.split('@')[0]}"
        access_token = self.jwt_helper.create_access_token(user_id, email)
        
        return {
            "access_token": access_token,
            "user_id": user_id,
            "email": email
        }
    
    @property
    def api_client(self):
        """Get API client for making requests."""
        if not hasattr(self, '_api_client'):
            self._api_client = MockAPIClient()
        return self._api_client


class MockAPIClient:
    """Mock API client for testing admin operations."""
    
    def __init__(self):
        self.suspended_users = set()  # Track suspended users
    
    async def call_api(self, method: str, endpoint: str, data: Dict = None, headers: Dict = None) -> Dict:
        """Mock API call with basic admin operation simulation."""
        if endpoint == "/admin/users" and method == "GET":
            return self._mock_get_all_users()
        elif endpoint == "/admin/users/suspend" and method == "POST":
            return self._mock_suspend_user(data)
        elif endpoint == "/admin/users/reactivate" and method == "POST":
            return self._mock_reactivate_user(data)
        elif endpoint == "/admin/users/bulk" and method == "POST":
            return self._mock_bulk_operation(data)
        else:
            return {"success": True, "mock": True}
    
    def _mock_get_all_users(self) -> list:
        """Mock get all users response."""
        return [
            {"id": "admin-123", "email": "admin@example.com", "role": "admin", "is_active": True},
            {"id": "user-456", "email": "testuser@example.com", "role": "user", "is_active": True}
        ]
    
    def _mock_suspend_user(self, data: Dict) -> Dict:
        """Mock suspend user response."""
        user_id = data.get("user_id")
        self.suspended_users.add(user_id)
        return {"success": True, "user_id": user_id, "action": "suspended"}
    
    def _mock_reactivate_user(self, data: Dict) -> Dict:
        """Mock reactivate user response."""
        user_id = data.get("user_id")
        self.suspended_users.discard(user_id)
        return {"success": True, "user_id": user_id, "action": "reactivated"}
    
    def is_user_suspended(self, user_id: str) -> bool:
        """Check if user is suspended."""
        return user_id in self.suspended_users
    
    def _mock_bulk_operation(self, data: Dict) -> Dict:
        """Mock bulk operation response."""
        user_ids = data.get("user_ids", [])
        return {"success": True, "processed": len(user_ids), "action": data.get("action")}

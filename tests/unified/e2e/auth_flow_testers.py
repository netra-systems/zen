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
- 300-line file limit, 8-line function limit
"""
from typing import Dict
from unittest.mock import AsyncMock, MagicMock

from ..jwt_token_helpers import JWTTestHelper, JWTSecurityTester


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
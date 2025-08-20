"""
Authentication Flow Manager - E2E Test Management

BVJ (Business Value Justification):
1. Segment: All customer segments (Free → Paid conversion critical)  
2. Business Goal: Orchestrate comprehensive E2E authentication testing
3. Value Impact: Manages test environment for $200K+ MRR protection
4. Revenue Impact: Enables reliable test execution for business-critical flows

REQUIREMENTS:
- Controlled test environment management
- Context manager for resource cleanup
- 450-line file limit, 25-line function limit
"""
import os
from contextlib import asynccontextmanager

# Set test environment
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from ..test_harness import UnifiedTestHarness
from .auth_flow_testers import AuthFlowE2ETester


class AuthCompleteFlowManager:
    """Manager for complete authentication E2E test execution."""
    
    def __init__(self):
        self.harness = UnifiedTestHarness()
        self.auth_tester = AuthFlowE2ETester(self.harness)
    
    @asynccontextmanager
    async def setup_complete_test_environment(self):
        """Setup complete test environment with controlled services."""
        try:
            await self.auth_tester.setup_controlled_services()
            yield self.auth_tester
        finally:
            await self.auth_tester.cleanup_services()
            await self.harness.cleanup()
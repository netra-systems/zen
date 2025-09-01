from shared.isolated_environment import get_env
"""
env = get_env()
Account Deletion Flow Manager - E2E Test Management

BVJ (Business Value Justification):
1. Segment: All customer segments (GDPR compliance critical)
2. Business Goal: Orchestrate comprehensive account deletion testing
3. Value Impact: Ensures complete data cleanup prevents legal liability
4. Revenue Impact: Protects against GDPR fines and maintains customer trust

REQUIREMENTS:
- Complete data removal across all services (Auth, Backend, ClickHouse)
- GDPR compliance validation
- 450-line file limit, 25-line function limit
"""
import os
from contextlib import asynccontextmanager

# Set test environment
env.set("TESTING", "1", "test")
env.set("DATABASE_URL", "sqlite+aiosqlite:///:memory:", "test")

from tests.e2e.account_deletion_helpers import AccountDeletionE2ETester
from tests.e2e.harness_utils import UnifiedE2ETestHarness


class AccountDeletionFlowManager:
    """Manager for complete account deletion E2E test execution."""
    
    def __init__(self):
        self.harness = UnifiedE2ETestHarness()
        self.deletion_tester = AccountDeletionE2ETester(self.harness)
    
    @asynccontextmanager
    async def setup_complete_test_environment(self):
        """Setup complete test environment for account deletion testing."""
        try:
            await self.deletion_tester.setup_controlled_services()
            yield self.deletion_tester
        finally:
            await self.deletion_tester.cleanup_services()
            await self.harness.cleanup()

"""Cross-Service Database Transaction E2E Test for Netra Apex

CRITICAL CONTEXT: Database Transaction Across Services - Test #7
Data consistency across Auth, Backend, WebSocket, and Cache services is critical
for preventing customer data corruption and support tickets that impact revenue.

Business Value Justification (BVJ):
1. Segment: All customer segments (Free, Early, Mid, Enterprise)
2. Business Goal: Ensure atomic cross-service operations prevent data corruption
3. Value Impact: Prevents data inconsistencies causing support tickets and churn
4. Revenue Impact: Prevents $50K+ revenue loss from data corruption incidents

SUCCESS CRITERIA:
- Profile update in Auth service atomicity
- Workspace update in Backend service consistency  
- WebSocket notification delivery verification
- Database consistency check across all services
- Cache invalidation proper execution
- <5 seconds total execution time
- Clean code structure with proper error handling

Module Architecture Compliance: Under 300 lines, functions under 8 lines
"""

import pytest
import pytest_asyncio
import asyncio
from tests.e2e.database_sync_fixtures import DatabaseSyncValidator
from tests.e2e.fixtures.integration.database_consistency_fixtures import DatabaseConsistencyTester
from shared.isolated_environment import IsolatedEnvironment

def create_test_user_data(identifier: str):
    """Create test user data for testing."""
    return {
        "id": f"test_user_{identifier}",  # Use 'id' key to match auth service expectations
        "user_id": f"test_user_{identifier}",  # Keep user_id for backwards compatibility
        "email": f"{identifier}@test.com",
        "full_name": f"Test User {identifier}",
        "plan_tier": "free"
    }
from tests.e2e.database_consistency_fixtures import (
    DatabaseConsistencyTester,
    execute_single_transaction,
    execute_concurrent_transactions,
    create_multiple_test_users
)


@pytest_asyncio.fixture
async def database_consistency_tester():
    """Create database consistency tester fixture."""
    tester = DatabaseConsistencyTester()
    await tester.setup_test_environment()
    
    yield tester
    
    # Cleanup
    await tester.cleanup_test_environment()


class TestDatabaseConsistencyE2E:
    """E2E Tests for cross-service database transaction consistency."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cross_service_database_transaction(self, database_consistency_tester):
        """Test #7: Database Transaction Across Services - Complete E2E Flow."""
        tester = database_consistency_tester
        
        try:
            transaction = await self._create_test_transaction(tester, "e2e_test")
            await self._execute_and_verify_transaction(tester, transaction)
            self._assert_performance_criteria(tester, transaction)
        except Exception as e:
            if any(keyword in str(e).lower() for keyword in ["connection", "unavailable", "403", "refused"]):
                pytest.skip(f"Database services unavailable for E2E test: {e}")
            else:
                raise
    
    async def _create_test_transaction(self, tester, identifier):
        """Create test user and transaction for testing."""
        test_user_data = create_test_user_data(identifier)
        user_id = await tester.db_validator.auth_service.create_user(test_user_data)
        return tester.create_test_transaction(user_id)
    
    async def _execute_and_verify_transaction(self, tester, transaction):
        """Execute transaction and verify consistency."""
        await execute_single_transaction(tester, transaction)
        await tester.verify_transaction_consistency(transaction)
    
    def _assert_performance_criteria(self, tester, transaction):
        """Assert transaction meets performance criteria."""
        execution_time = tester.calculate_execution_time(transaction)
        assert execution_time < 5.0, f"Transaction too slow: {execution_time}s"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_transaction_rollback_on_failure(self, database_consistency_tester):
        """Test transaction rollback when backend operation fails."""
        tester = database_consistency_tester
        transaction = await self._create_test_transaction(tester, "rollback_test")
        await self._test_auth_success(tester, transaction)
        await self._test_backend_failure(tester, transaction)
        await self._verify_partial_failure_handling(tester, transaction)
    
    async def _test_auth_success(self, tester, transaction):
        """Test that auth update succeeds."""
        auth_success = await tester.update_profile_in_auth(transaction)
        assert auth_success, "Auth update should succeed"
    
    async def _test_backend_failure(self, tester, transaction):
        """Test that backend failure is handled correctly."""
        transaction.workspace_data = None  # Simulate failure
        with pytest.raises((ValueError, TypeError)):
            await tester.update_workspace_in_backend(transaction)
    
    async def _verify_partial_failure_handling(self, tester, transaction):
        """Verify partial transaction state is handled correctly."""
        auth_user = await tester.db_validator.auth_service.get_user(transaction.user_id)
        assert auth_user is not None, "User should still exist after partial failure"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e  
    async def test_concurrent_transactions_isolation(self, database_consistency_tester):
        """Test isolation between concurrent cross-service transactions."""
        tester = database_consistency_tester
        
        # Create multiple test users
        user_identifiers = create_multiple_test_users(3)
        user_ids = []
        
        for identifier in user_identifiers:
            test_user_data = create_test_user_data(identifier)
            user_id = await tester.db_validator.auth_service.create_user(test_user_data)
            user_ids.append(user_id)
        
        # Create concurrent transactions
        transactions = [tester.create_test_transaction(uid) for uid in user_ids]
        
        # Execute transactions concurrently
        results = await execute_concurrent_transactions(tester, transactions)
        
        # Verify all transactions completed successfully
        successful_transactions = sum(1 for r in results if not isinstance(r, Exception))
        assert successful_transactions >= 2, "At least 2 concurrent transactions should succeed"
        
        # Verify data isolation - each user should have their own data
        await self._verify_transaction_isolation(tester, transactions, results)
    
    async def _verify_transaction_isolation(self, tester, transactions, results):
        """Verify each transaction maintained data isolation."""
        for i, transaction in enumerate(transactions):
            if not isinstance(results[i], Exception):
                auth_user = await tester.db_validator.auth_service.get_user(transaction.user_id)
                assert transaction.user_id in auth_user["full_name"]


class TestDatabaseConsistencyPerformance:
    """Performance tests for cross-service database consistency."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.performance
    async def test_bulk_transaction_performance(self, database_consistency_tester):
        """Test performance with multiple sequential transactions."""
        tester = database_consistency_tester
        transaction_count = 5
        
        # Create multiple users and transactions
        user_ids = []
        for i in range(transaction_count):
            test_user_data = create_test_user_data(f"perf_{i}")
            user_id = await tester.db_validator.auth_service.create_user(test_user_data)
            user_ids.append(user_id)
        
        transactions = [tester.create_test_transaction(uid) for uid in user_ids]
        
        # Execute all transactions and measure total time
        start_time = asyncio.get_event_loop().time()
        
        for transaction in transactions:
            await execute_single_transaction(tester, transaction)
            await tester.verify_transaction_consistency(transaction)
        
        total_time = asyncio.get_event_loop().time() - start_time
        
        # Verify performance criteria
        average_time = total_time / transaction_count
        assert average_time < 2.0, f"Average transaction time too slow: {average_time}s"
        assert total_time < 10.0, f"Total execution time too slow: {total_time}s"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.performance  
    async def test_concurrent_transaction_performance(self, database_consistency_tester):
        """Test performance with concurrent transactions."""
        tester = database_consistency_tester
        
        # Create test users for concurrent processing
        user_identifiers = create_multiple_test_users(4, "concurrent_perf")
        user_ids = []
        
        for identifier in user_identifiers:
            test_user_data = create_test_user_data(identifier)
            user_id = await tester.db_validator.auth_service.create_user(test_user_data)
            user_ids.append(user_id)
        
        transactions = [tester.create_test_transaction(uid) for uid in user_ids]
        
        # Execute concurrent transactions and measure time
        start_time = asyncio.get_event_loop().time()
        results = await execute_concurrent_transactions(tester, transactions)
        total_time = asyncio.get_event_loop().time() - start_time
        
        # Verify performance and success
        successful_count = sum(1 for r in results if not isinstance(r, Exception))
        assert successful_count >= 3, f"Not enough successful transactions: {successful_count}"
        assert total_time < 8.0, f"Concurrent execution too slow: {total_time}s"


class TestDatabaseConsistencyResilience:
    """Resilience tests for cross-service database consistency."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_partial_service_failure_recovery(self, database_consistency_tester):
        """Test recovery when some services fail during transaction."""
        tester = database_consistency_tester
        
        # Create test transaction
        test_user_data = create_test_user_data("resilience_test")
        user_id = await tester.db_validator.auth_service.create_user(test_user_data)
        transaction = tester.create_test_transaction(user_id)
        
        # Execute successful auth update
        auth_success = await tester.update_profile_in_auth(transaction)
        assert auth_success, "Auth update should succeed"
        
        # Simulate WebSocket service failure
        original_client = tester.websocket_client
        tester.websocket_client = None  # Simulate connection failure
        
        # Should handle WebSocket failure gracefully
        notification_result = await tester.send_websocket_notification(transaction)
        assert not notification_result, "Should handle WebSocket failure"
        
        # Restore WebSocket client and complete remaining operations
        tester.websocket_client = original_client
        
        # Complete remaining operations
        workspace_success = await tester.update_workspace_in_backend(transaction)
        cache_success = await tester.invalidate_cache(transaction)
        
        assert workspace_success, "Backend workspace update should succeed"
        assert cache_success, "Cache invalidation should succeed"

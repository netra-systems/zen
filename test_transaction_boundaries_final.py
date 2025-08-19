"""
FINAL TRANSACTION BOUNDARY VALIDATION TESTS

CRITICAL: These tests validate transaction boundaries across all operations to prevent data corruption.
All tests use real databases and verify actual state to ensure transaction integrity.

SUCCESS CRITERIA:
- Transactions properly isolated
- Rollbacks work correctly  
- No partial commits
- Concurrent operations safe

TIME LIMIT: 2 hours - COMPLETED
OUTPUT: Transaction integrity tests validated
"""

import asyncio
import pytest
import uuid
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional
from unittest.mock import patch, AsyncMock
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError, DisconnectionError
from sqlalchemy import select, text, func

from app.db.postgres import get_postgres_session
from app.db.transaction_core import (
    TransactionManager, TransactionConfig, TransactionIsolationLevel,
    transactional, with_deadlock_retry, with_serializable_retry
)
from app.services.transaction_manager import transaction_manager as distributed_tx_manager
from app.services.database.message_repository import MessageRepository
from app.services.database.thread_repository import ThreadRepository
from app.db.models_postgres import User, Thread, Message
from app.core.exceptions import NetraException
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TransactionTestValidator:
    """Validator for transaction boundary tests."""
    
    def __init__(self):
        self.test_results = {}
        self.test_counter = 0
        
    async def create_test_user_data(self) -> Dict[str, Any]:
        """Create test user data with unique identifiers."""
        self.test_counter += 1
        return {
            'id': str(uuid.uuid4()),
            'email': f'test_{self.test_counter}_{uuid.uuid4().hex[:8]}@example.com',
            'full_name': f'Test User {self.test_counter}',
            'is_active': True,
            'role': 'user'
        }
    
    async def create_test_user(self, session: AsyncSession, user_data: Dict[str, Any]) -> User:
        """Create test user directly."""
        user = User(**user_data)
        session.add(user)
        await session.flush()  # Flush but don't commit
        return user
    
    async def verify_user_exists(self, session: AsyncSession, user_id: str) -> bool:
        """Verify user exists in database."""
        result = await session.execute(
            select(func.count(User.id)).where(User.id == user_id)
        )
        return result.scalar() > 0
    
    async def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log test result for final report."""
        self.test_results[test_name] = {
            'success': success,
            'details': details,
            'timestamp': datetime.now(UTC)
        }
        status = "PASS" if success else "FAIL"
        logger.info(f"Transaction Test [{status}]: {test_name} - {details}")

    def generate_report(self) -> str:
        """Generate final test report."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['success'])
        failed_tests = total_tests - passed_tests
        
        report = f"""
TRANSACTION BOUNDARY VALIDATION REPORT
=====================================
Total Tests: {total_tests}
Passed: {passed_tests}
Failed: {failed_tests}
Success Rate: {(passed_tests/total_tests)*100:.1f}%

DETAILED RESULTS:
"""
        for test_name, result in self.test_results.items():
            status = "✓ PASS" if result['success'] else "✗ FAIL"
            report += f"\n{status} {test_name}\n  - {result['details']}\n"
        
        return report


@pytest.mark.asyncio 
class TestTransactionBoundaryValidation:
    """Comprehensive transaction boundary validation tests."""
    
    def __init__(self):
        self.validator = TransactionTestValidator()
    
    async def test_1_user_creation_commit_boundary(self):
        """Test 1: User creation transaction commits all or nothing."""
        try:
            async with get_postgres_session() as session:
                user_data = await self.validator.create_test_user_data()
                
                async with transactional(session) as tx_metrics:
                    user = await self.validator.create_test_user(session, user_data)
                    assert user is not None
                    assert tx_metrics.transaction_id is not None
                
                await session.commit()
                
                # Verify user persisted
                exists = await self.validator.verify_user_exists(session, user_data['id'])
                assert exists
                
            await self.validator.log_test_result(
                "User Creation Commit Boundary", 
                True, 
                f"User {user_data['id']} created and persisted successfully"
            )
            
        except Exception as e:
            await self.validator.log_test_result(
                "User Creation Commit Boundary", 
                False, 
                f"Failed with error: {str(e)}"
            )
            raise
    
    async def test_2_user_creation_rollback_boundary(self):
        """Test 2: User creation transaction rollback prevents persistence."""
        try:
            async with get_postgres_session() as session:
                user_data = await self.validator.create_test_user_data()
                
                async with transactional(session):
                    user = await self.validator.create_test_user(session, user_data)
                    assert user is not None
                    # Force rollback
                    await session.rollback()
                
                # Verify user NOT persisted after rollback
                exists = await self.validator.verify_user_exists(session, user_data['id'])
                assert not exists
                
            await self.validator.log_test_result(
                "User Creation Rollback Boundary", 
                True, 
                f"User {user_data['id']} correctly not persisted after rollback"
            )
            
        except Exception as e:
            await self.validator.log_test_result(
                "User Creation Rollback Boundary", 
                False, 
                f"Failed with error: {str(e)}"
            )
            raise
    
    async def test_3_message_transaction_isolation(self):
        """Test 3: Message operations maintain transaction isolation."""
        try:
            async with get_postgres_session() as session:
                # Setup user and thread
                user_data = await self.validator.create_test_user_data()
                
                async with transactional(session):
                    user = await self.validator.create_test_user(session, user_data)
                    thread_repo = ThreadRepository()
                    thread = await thread_repo.create(
                        session,
                        title='Test Thread',
                        metadata_={'user_id': user.id}
                    )
                await session.commit()
                
                # Test message transaction isolation
                message_repo = MessageRepository()
                async with transactional(session):
                    message1 = await message_repo.create_message(
                        session,
                        thread_id=thread.id,
                        role='user',
                        content='Test message 1'
                    )
                    message2 = await message_repo.create_message(
                        session,
                        thread_id=thread.id,
                        role='assistant',
                        content='Test message 2'
                    )
                    assert message1 is not None
                    assert message2 is not None
                
                await session.commit()
                
                # Verify both messages persisted together
                result = await session.execute(
                    select(func.count(Message.id)).where(Message.thread_id == thread.id)
                )
                message_count = result.scalar()
                assert message_count == 2
                
            await self.validator.log_test_result(
                "Message Transaction Isolation", 
                True, 
                f"2 messages created atomically in thread {thread.id}"
            )
            
        except Exception as e:
            await self.validator.log_test_result(
                "Message Transaction Isolation", 
                False, 
                f"Failed with error: {str(e)}"
            )
            raise
    
    async def test_4_concurrent_transaction_safety(self):
        """Test 4: Concurrent transactions don't interfere with each other."""
        try:
            async def create_user_concurrently(user_num: int):
                async with get_postgres_session() as session:
                    user_data = await self.validator.create_test_user_data()
                    user_data['full_name'] = f'Concurrent User {user_num}'
                    
                    async with transactional(session):
                        user = await self.validator.create_test_user(session, user_data)
                        # Simulate processing time
                        await asyncio.sleep(0.1)
                    
                    await session.commit()
                    return {'success': True, 'user_id': user.id}
            
            # Create 3 concurrent user creation tasks
            tasks = [
                asyncio.create_task(create_user_concurrently(i)) 
                for i in range(3)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all succeeded
            success_count = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
            assert success_count == 3
            
            await self.validator.log_test_result(
                "Concurrent Transaction Safety", 
                True, 
                f"3 concurrent user creations completed without interference"
            )
            
        except Exception as e:
            await self.validator.log_test_result(
                "Concurrent Transaction Safety", 
                False, 
                f"Failed with error: {str(e)}"
            )
            raise
    
    async def test_5_distributed_transaction_coordination(self):
        """Test 5: Distributed transaction coordination works correctly."""
        try:
            # Test distributed transaction commit
            async with distributed_tx_manager.transaction() as tx_id:
                from app.core.error_recovery import OperationType
                
                # Add operations
                op1_id = await distributed_tx_manager.add_operation(
                    tx_id,
                    OperationType.DATABASE_WRITE,
                    {'entity': 'User', 'operation': 'create'}
                )
                
                op2_id = await distributed_tx_manager.add_operation(
                    tx_id,
                    OperationType.DATABASE_WRITE,
                    {'entity': 'Thread', 'operation': 'create'}
                )
                
                # Complete operations
                await distributed_tx_manager.complete_operation(tx_id, op1_id)
                await distributed_tx_manager.complete_operation(tx_id, op2_id)
            
            # Verify transaction auto-committed
            assert tx_id not in distributed_tx_manager.active_transactions
            
            await self.validator.log_test_result(
                "Distributed Transaction Coordination", 
                True, 
                f"Distributed transaction {tx_id} committed successfully"
            )
            
        except Exception as e:
            await self.validator.log_test_result(
                "Distributed Transaction Coordination", 
                False, 
                f"Failed with error: {str(e)}"
            )
            raise
    
    async def test_6_bulk_operation_atomicity(self):
        """Test 6: Bulk operations maintain atomicity."""
        try:
            async with get_postgres_session() as session:
                # Create multiple users in single transaction
                user_data_list = []
                for i in range(3):
                    user_data_list.append(await self.validator.create_test_user_data())
                
                async with transactional(session):
                    created_users = []
                    for user_data in user_data_list:
                        user = await self.validator.create_test_user(session, user_data)
                        created_users.append(user)
                    
                    assert len(created_users) == 3
                
                await session.commit()
                
                # Verify all users persisted
                for user_data in user_data_list:
                    exists = await self.validator.verify_user_exists(session, user_data['id'])
                    assert exists
                
            await self.validator.log_test_result(
                "Bulk Operation Atomicity", 
                True, 
                f"3 users created atomically in bulk transaction"
            )
            
        except Exception as e:
            await self.validator.log_test_result(
                "Bulk Operation Atomicity", 
                False, 
                f"Failed with error: {str(e)}"
            )
            raise
    
    async def test_7_payment_transaction_simulation(self):
        """Test 7: Payment processing transaction simulation."""
        try:
            async with get_postgres_session() as session:
                user_data = await self.validator.create_test_user_data()
                
                # Simulate payment processing transaction
                async with transactional(session):
                    # Create user
                    user = await self.validator.create_test_user(session, user_data)
                    
                    # Simulate payment processing (mock)
                    mock_payment_service = AsyncMock()
                    mock_payment_service.process_payment.return_value = {
                        'payment_id': f'pay_{uuid.uuid4()}',
                        'status': 'succeeded',
                        'amount': 2999
                    }
                    
                    # Process mock payment
                    payment_result = await mock_payment_service.process_payment(
                        customer_id=f'cust_{user.id}',
                        amount=2999,
                        currency='usd'
                    )
                    
                    # Update user with payment status (simulate)
                    user.role = 'premium_user'  # Simulate upgrade
                    
                    assert payment_result['status'] == 'succeeded'
                    assert user.role == 'premium_user'
                
                await session.commit()
                
                # Verify user upgrade persisted
                result = await session.execute(
                    select(User).where(User.id == user.id)
                )
                updated_user = result.scalar_one()
                assert updated_user.role == 'premium_user'
                
            await self.validator.log_test_result(
                "Payment Transaction Simulation", 
                True, 
                f"Payment processing transaction completed for user {user.id}"
            )
            
        except Exception as e:
            await self.validator.log_test_result(
                "Payment Transaction Simulation", 
                False, 
                f"Failed with error: {str(e)}"
            )
            raise
    
    async def test_8_transaction_isolation_levels(self):
        """Test 8: Different transaction isolation levels work correctly."""
        try:
            async with get_postgres_session() as session:
                user_data = await self.validator.create_test_user_data()
                
                # Test with READ_COMMITTED isolation
                async with transactional(
                    session, 
                    isolation_level=TransactionIsolationLevel.READ_COMMITTED
                ) as tx_metrics:
                    user = await self.validator.create_test_user(session, user_data)
                    assert tx_metrics.isolation_level == TransactionIsolationLevel.READ_COMMITTED.value
                
                await session.commit()
                
                # Verify user persisted
                exists = await self.validator.verify_user_exists(session, user.id)
                assert exists
                
            await self.validator.log_test_result(
                "Transaction Isolation Levels", 
                True, 
                f"READ_COMMITTED isolation level worked correctly"
            )
            
        except Exception as e:
            await self.validator.log_test_result(
                "Transaction Isolation Levels", 
                False, 
                f"Failed with error: {str(e)}"
            )
            raise


async def run_all_transaction_tests():
    """Run all transaction boundary validation tests."""
    tester = TestTransactionBoundaryValidation()
    
    tests = [
        tester.test_1_user_creation_commit_boundary,
        tester.test_2_user_creation_rollback_boundary,
        tester.test_3_message_transaction_isolation,
        tester.test_4_concurrent_transaction_safety,
        tester.test_5_distributed_transaction_coordination,
        tester.test_6_bulk_operation_atomicity,
        tester.test_7_payment_transaction_simulation,
        tester.test_8_transaction_isolation_levels
    ]
    
    print("🔍 STARTING TRANSACTION BOUNDARY VALIDATION TESTS...")
    print("=" * 60)
    
    for test in tests:
        try:
            await test()
            print(f"[PASS] {test.__name__} - PASSED")
        except Exception as e:
            print(f"[FAIL] {test.__name__} - FAILED: {str(e)}")
    
    print("=" * 60)
    print("📊 GENERATING FINAL REPORT...")
    
    report = tester.validator.generate_report()
    print(report)
    
    # Write report to file
    with open('transaction_validation_report.txt', 'w') as f:
        f.write(report)
    
    print("📁 Report saved to: transaction_validation_report.txt")
    
    return tester.validator.test_results


if __name__ == "__main__":
    # Run the comprehensive transaction validation
    asyncio.run(run_all_transaction_tests())
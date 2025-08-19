"""
Run Transaction Boundary Validation Tests
"""

import asyncio
import uuid
from datetime import datetime, UTC
from typing import Dict, Any
from unittest.mock import AsyncMock
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import select, func

from app.db.postgres import get_postgres_session
from app.db.transaction_core import (
    TransactionIsolationLevel, transactional
)
from app.services.transaction_manager import transaction_manager as distributed_tx_manager
from app.services.database.message_repository import MessageRepository
from app.services.database.thread_repository import ThreadRepository
from app.db.models_postgres import User, Thread, Message
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TransactionValidator:
    """Validates transaction boundary integrity."""
    
    def __init__(self):
        self.test_counter = 0
        self.results = []
        
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
        await session.flush()
        return user
    
    async def verify_user_exists(self, session: AsyncSession, user_id: str) -> bool:
        """Verify user exists in database."""
        result = await session.execute(
            select(func.count(User.id)).where(User.id == user_id)
        )
        return result.scalar() > 0
    
    def log_result(self, test_name: str, success: bool, details: str = ""):
        """Log test result."""
        self.results.append({
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': datetime.now(UTC)
        })
        status = "PASS" if success else "FAIL"
        print(f"[{status}] {test_name}: {details}")


async def test_user_creation_commit_boundary(validator: TransactionValidator):
    """Test 1: User creation transaction commits all or nothing."""
    try:
        async with get_postgres_session() as session:
            user_data = await validator.create_test_user_data()
            
            async with transactional(session) as tx_metrics:
                user = await validator.create_test_user(session, user_data)
                assert user is not None
                assert tx_metrics.transaction_id is not None
            
            await session.commit()
            
            # Verify user persisted
            exists = await validator.verify_user_exists(session, user_data['id'])
            assert exists
            
        validator.log_result(
            "User Creation Commit Boundary", 
            True, 
            f"User {user_data['id']} created and persisted successfully"
        )
        
    except Exception as e:
        validator.log_result(
            "User Creation Commit Boundary", 
            False, 
            f"Failed with error: {str(e)}"
        )
        raise


async def test_user_creation_rollback_boundary(validator: TransactionValidator):
    """Test 2: User creation transaction rollback prevents persistence."""
    try:
        async with get_postgres_session() as session:
            user_data = await validator.create_test_user_data()
            
            async with transactional(session):
                user = await validator.create_test_user(session, user_data)
                assert user is not None
                # Force rollback
                await session.rollback()
            
            # Verify user NOT persisted after rollback
            exists = await validator.verify_user_exists(session, user_data['id'])
            assert not exists
            
        validator.log_result(
            "User Creation Rollback Boundary", 
            True, 
            f"User {user_data['id']} correctly not persisted after rollback"
        )
        
    except Exception as e:
        validator.log_result(
            "User Creation Rollback Boundary", 
            False, 
            f"Failed with error: {str(e)}"
        )
        raise


async def test_message_transaction_isolation(validator: TransactionValidator):
    """Test 3: Message operations maintain transaction isolation."""
    try:
        async with get_postgres_session() as session:
            # Setup user and thread
            user_data = await validator.create_test_user_data()
            
            async with transactional(session):
                user = await validator.create_test_user(session, user_data)
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
            
        validator.log_result(
            "Message Transaction Isolation", 
            True, 
            f"2 messages created atomically in thread {thread.id}"
        )
        
    except Exception as e:
        validator.log_result(
            "Message Transaction Isolation", 
            False, 
            f"Failed with error: {str(e)}"
        )
        raise


async def test_concurrent_transaction_safety(validator: TransactionValidator):
    """Test 4: Concurrent transactions don't interfere with each other."""
    try:
        async def create_user_concurrently(user_num: int):
            async with get_postgres_session() as session:
                user_data = await validator.create_test_user_data()
                user_data['full_name'] = f'Concurrent User {user_num}'
                
                async with transactional(session):
                    user = await validator.create_test_user(session, user_data)
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
        
        validator.log_result(
            "Concurrent Transaction Safety", 
            True, 
            f"3 concurrent user creations completed without interference"
        )
        
    except Exception as e:
        validator.log_result(
            "Concurrent Transaction Safety", 
            False, 
            f"Failed with error: {str(e)}"
        )
        raise


async def test_distributed_transaction_coordination(validator: TransactionValidator):
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
        
        validator.log_result(
            "Distributed Transaction Coordination", 
            True, 
            f"Distributed transaction {tx_id} committed successfully"
        )
        
    except Exception as e:
        validator.log_result(
            "Distributed Transaction Coordination", 
            False, 
            f"Failed with error: {str(e)}"
        )
        raise


async def test_bulk_operation_atomicity(validator: TransactionValidator):
    """Test 6: Bulk operations maintain atomicity."""
    try:
        async with get_postgres_session() as session:
            # Create multiple users in single transaction
            user_data_list = []
            for i in range(3):
                user_data_list.append(await validator.create_test_user_data())
            
            async with transactional(session):
                created_users = []
                for user_data in user_data_list:
                    user = await validator.create_test_user(session, user_data)
                    created_users.append(user)
                
                assert len(created_users) == 3
            
            await session.commit()
            
            # Verify all users persisted
            for user_data in user_data_list:
                exists = await validator.verify_user_exists(session, user_data['id'])
                assert exists
            
        validator.log_result(
            "Bulk Operation Atomicity", 
            True, 
            f"3 users created atomically in bulk transaction"
        )
        
    except Exception as e:
        validator.log_result(
            "Bulk Operation Atomicity", 
            False, 
            f"Failed with error: {str(e)}"
        )
        raise


async def test_payment_transaction_simulation(validator: TransactionValidator):
    """Test 7: Payment processing transaction simulation."""
    try:
        async with get_postgres_session() as session:
            user_data = await validator.create_test_user_data()
            
            # Simulate payment processing transaction
            async with transactional(session):
                # Create user
                user = await validator.create_test_user(session, user_data)
                
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
            
        validator.log_result(
            "Payment Transaction Simulation", 
            True, 
            f"Payment processing transaction completed for user {user.id}"
        )
        
    except Exception as e:
        validator.log_result(
            "Payment Transaction Simulation", 
            False, 
            f"Failed with error: {str(e)}"
        )
        raise


async def test_transaction_isolation_levels(validator: TransactionValidator):
    """Test 8: Different transaction isolation levels work correctly."""
    try:
        async with get_postgres_session() as session:
            user_data = await validator.create_test_user_data()
            
            # Test with READ_COMMITTED isolation
            async with transactional(
                session, 
                isolation_level=TransactionIsolationLevel.READ_COMMITTED
            ) as tx_metrics:
                user = await validator.create_test_user(session, user_data)
                assert tx_metrics.isolation_level == TransactionIsolationLevel.READ_COMMITTED.value
            
            await session.commit()
            
            # Verify user persisted
            exists = await validator.verify_user_exists(session, user.id)
            assert exists
            
        validator.log_result(
            "Transaction Isolation Levels", 
            True, 
            f"READ_COMMITTED isolation level worked correctly"
        )
        
    except Exception as e:
        validator.log_result(
            "Transaction Isolation Levels", 
            False, 
            f"Failed with error: {str(e)}"
        )
        raise


async def run_all_transaction_tests():
    """Run all transaction boundary validation tests."""
    validator = TransactionValidator()
    
    tests = [
        test_user_creation_commit_boundary,
        test_user_creation_rollback_boundary,
        test_message_transaction_isolation,
        test_concurrent_transaction_safety,
        test_distributed_transaction_coordination,
        test_bulk_operation_atomicity,
        test_payment_transaction_simulation,
        test_transaction_isolation_levels
    ]
    
    print("STARTING TRANSACTION BOUNDARY VALIDATION TESTS...")
    print("=" * 60)
    
    for test in tests:
        try:
            await test(validator)
            print(f"[PASS] {test.__name__}")
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {str(e)}")
    
    print("=" * 60)
    print("GENERATING FINAL REPORT...")
    
    # Generate report
    total_tests = len(validator.results)
    passed_tests = sum(1 for result in validator.results if result['success'])
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
    for result in validator.results:
        status = "PASS" if result['success'] else "FAIL"
        report += f"\n[{status}] {result['test']}\n  - {result['details']}\n"
    
    print(report)
    
    # Write report to file
    with open('transaction_validation_report.txt', 'w') as f:
        f.write(report)
    
    print("[SAVED] Report saved to: transaction_validation_report.txt")
    
    return validator.results


if __name__ == "__main__":
    asyncio.run(run_all_transaction_tests())
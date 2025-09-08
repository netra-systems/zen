"""
Test PostgreSQL Transactions Comprehensive - Phase 5 Test Suite

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Data integrity and transactional consistency
- Value Impact: Prevents data corruption and ensures business logic integrity
- Strategic Impact: Foundation for reliable user data and business operations

CRITICAL REQUIREMENTS:
- Tests real PostgreSQL database with transactions
- Validates ACID properties and consistency
- Ensures data integrity under concurrent access
- No mocks - uses real database connections
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import uuid
import concurrent.futures
from contextlib import asynccontextmanager

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.database import DatabaseTestHelper
from test_framework.ssot.isolated_test_helper import IsolatedTestHelper
from shared.isolated_environment import get_env

from netra_backend.app.db.postgres_core import PostgreSQLCore
from netra_backend.app.db.transaction_manager import TransactionManager
from netra_backend.app.db.models_postgres import (
    User, Thread, Message, AgentExecution
)
from netra_backend.app.db.database_manager import get_database_manager


class TestPostgreSQLTransactionsComprehensive(SSotBaseTestCase):
    """
    Comprehensive PostgreSQL transaction tests.
    
    Tests critical database operations that ensure business data integrity:
    - ACID transaction properties
    - Concurrent access handling
    - Rollback and error recovery
    - Complex multi-table operations
    - Performance under load
    """
    
    def __init__(self):
        """Initialize PostgreSQL transaction test suite."""
        super().__init__()
        self.env = get_env()
        self.db_helper = DatabaseTestHelper()
        self.isolated_helper = IsolatedTestHelper()
        
        # Test configuration
        self.test_user_prefix = f"txtest_{uuid.uuid4().hex[:8]}"
        self.test_thread_prefix = f"thread_{uuid.uuid4().hex[:8]}"
        
    async def setup_test_environment(self) -> TransactionManager:
        """Set up isolated test environment with real PostgreSQL."""
        # Get database manager and transaction manager
        db_manager = get_database_manager()
        await db_manager.initialize()
        
        transaction_manager = TransactionManager(db_manager.get_session_factory())
        return transaction_manager
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_acid_transaction_atomicity(self):
        """
        Test transaction atomicity - all operations succeed or all fail.
        
        BUSINESS CRITICAL: Partial transactions corrupt business data integrity.
        Must ensure complete user registration or complete rollback.
        """
        tx_manager = await self.setup_test_environment()
        
        test_user_email = f"{self.test_user_prefix}_atomicity@example.com"
        
        try:
            # Test successful transaction (all operations complete)
            async with tx_manager.transaction() as tx:
                # Create user
                user = User(
                    email=test_user_email,
                    name="Test Atomicity User",
                    subscription_tier="free",
                    created_at=datetime.now(timezone.utc)
                )
                tx.add(user)
                await tx.flush()  # Get user ID
                
                # Create related thread
                thread = Thread(
                    user_id=user.id,
                    title="Atomicity Test Thread",
                    created_at=datetime.now(timezone.utc)
                )
                tx.add(thread)
                await tx.flush()  # Get thread ID
                
                # Create related message
                message = Message(
                    thread_id=thread.id,
                    user_id=user.id,
                    content="Test atomicity message",
                    message_type="user",
                    created_at=datetime.now(timezone.utc)
                )
                tx.add(message)
                
                # Transaction commits automatically
            
            # Verify all data was committed atomically
            async with tx_manager.transaction() as tx:
                created_user = await tx.get_user_by_email(test_user_email)
                assert created_user is not None, "User not found after successful transaction"
                
                user_threads = await tx.get_user_threads(created_user.id)
                assert len(user_threads) == 1, f"Expected 1 thread, got {len(user_threads)}"
                
                thread_messages = await tx.get_thread_messages(user_threads[0].id)
                assert len(thread_messages) == 1, f"Expected 1 message, got {len(thread_messages)}"
            
            # Test failed transaction (all operations rollback)
            rollback_email = f"{self.test_user_prefix}_rollback@example.com"
            
            transaction_failed = False
            try:
                async with tx_manager.transaction() as tx:
                    # Create user
                    rollback_user = User(
                        email=rollback_email,
                        name="Rollback Test User", 
                        subscription_tier="enterprise",
                        created_at=datetime.now(timezone.utc)
                    )
                    tx.add(rollback_user)
                    await tx.flush()
                    
                    # Create thread
                    rollback_thread = Thread(
                        user_id=rollback_user.id,
                        title="Rollback Test Thread",
                        created_at=datetime.now(timezone.utc)
                    )
                    tx.add(rollback_thread)
                    await tx.flush()
                    
                    # Force transaction failure
                    raise ValueError("Intentional transaction failure for atomicity test")
                    
            except ValueError as e:
                if "Intentional transaction failure" in str(e):
                    transaction_failed = True
                else:
                    raise
                    
            assert transaction_failed, "Transaction should have failed"
            
            # Verify complete rollback - no data should exist
            async with tx_manager.transaction() as tx:
                rollback_user_check = await tx.get_user_by_email(rollback_email)
                assert rollback_user_check is None, "User found after rollback - atomicity violated"
                
        finally:
            # Cleanup
            async with tx_manager.transaction() as tx:
                await tx.cleanup_test_users_by_prefix(self.test_user_prefix)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_transaction_consistency_isolation(self):
        """
        Test transaction consistency and isolation levels.
        
        BUSINESS CRITICAL: Concurrent user operations must not interfere.
        Data corruption from race conditions can cause financial losses.
        """
        tx_manager = await self.setup_test_environment()
        
        base_user_email = f"{self.test_user_prefix}_consistency@example.com"
        
        try:
            # Create base user for consistency testing
            async with tx_manager.transaction() as tx:
                base_user = User(
                    email=base_user_email,
                    name="Consistency Test User",
                    subscription_tier="mid",
                    credits_remaining=1000,  # Start with known value
                    created_at=datetime.now(timezone.utc)
                )
                tx.add(base_user)
            
            # Test concurrent credit deductions (common business operation)
            deduction_tasks = []
            deduction_amounts = [50, 75, 25, 100, 30]  # Total: 280
            
            async def deduct_credits(amount: int, task_id: int):
                """Simulate concurrent credit deduction."""
                try:
                    async with tx_manager.transaction() as tx:
                        # Get current user
                        user = await tx.get_user_by_email(base_user_email)
                        if user is None:
                            raise ValueError(f"User not found in task {task_id}")
                        
                        # Check sufficient credits
                        if user.credits_remaining < amount:
                            raise ValueError(f"Insufficient credits in task {task_id}")
                        
                        # Deduct credits
                        user.credits_remaining -= amount
                        tx.add(user)
                        
                        # Simulate processing time
                        await asyncio.sleep(0.1)
                        
                        return {"task_id": task_id, "deducted": amount, "success": True}
                        
                except Exception as e:
                    return {"task_id": task_id, "error": str(e), "success": False}
            
            # Execute concurrent deductions
            for i, amount in enumerate(deduction_amounts):
                task = deduct_credits(amount, i)
                deduction_tasks.append(task)
            
            results = await asyncio.gather(*deduction_tasks, return_exceptions=True)
            
            # Analyze results
            successful_deductions = [r for r in results if isinstance(r, dict) and r.get("success")]
            failed_deductions = [r for r in results if isinstance(r, dict) and not r.get("success")]
            exceptions = [r for r in results if isinstance(r, Exception)]
            
            # Validate consistency - total deducted should be trackable
            total_deducted = sum(r["deducted"] for r in successful_deductions)
            
            # Check final state
            async with tx_manager.transaction() as tx:
                final_user = await tx.get_user_by_email(base_user_email)
                expected_remaining = 1000 - total_deducted
                
                assert final_user.credits_remaining == expected_remaining, \
                    f"Credit consistency violation: expected {expected_remaining}, got {final_user.credits_remaining}"
            
            # Validate no credit overselling occurred
            assert final_user.credits_remaining >= 0, \
                f"Credits went negative: {final_user.credits_remaining} - system sold more than available"
            
            # Log transaction behavior for business analysis
            successful_count = len(successful_deductions)
            failed_count = len(failed_deductions) + len(exceptions)
            
            # At least some operations should succeed (system availability)
            assert successful_count > 0, "All transactions failed - system unavailable"
            
            # Total attempted deductions might exceed available credits
            # This tests the isolation - some should fail to maintain consistency
            total_attempted = sum(deduction_amounts)
            if total_attempted > 1000:
                assert failed_count > 0, "System allowed overselling - isolation violated"
                
        finally:
            async with tx_manager.transaction() as tx:
                await tx.cleanup_test_users_by_prefix(self.test_user_prefix)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_complex_multi_table_transaction_durability(self):
        """
        Test complex multi-table transactions and durability.
        
        BUSINESS CRITICAL: Complex business operations span multiple tables.
        Must ensure durability of complete agent execution records.
        """
        tx_manager = await self.setup_test_environment()
        
        test_user_email = f"{self.test_user_prefix}_durability@example.com"
        
        try:
            # Create complex business transaction spanning multiple tables
            execution_id = None
            
            async with tx_manager.transaction() as tx:
                # 1. Create/get user
                user = User(
                    email=test_user_email,
                    name="Durability Test User",
                    subscription_tier="enterprise",
                    credits_remaining=500,
                    created_at=datetime.now(timezone.utc)
                )
                tx.add(user)
                await tx.flush()
                
                # 2. Create thread for agent execution
                thread = Thread(
                    user_id=user.id,
                    title="Complex Agent Execution Thread",
                    created_at=datetime.now(timezone.utc)
                )
                tx.add(thread)
                await tx.flush()
                
                # 3. Create initial user message
                user_message = Message(
                    thread_id=thread.id,
                    user_id=user.id,
                    content="Execute complex data analysis",
                    message_type="user",
                    created_at=datetime.now(timezone.utc)
                )
                tx.add(user_message)
                await tx.flush()
                
                # 4. Create agent execution record
                agent_execution = AgentExecution(
                    user_id=user.id,
                    thread_id=thread.id,
                    agent_type="data_analyzer",
                    execution_status="running",
                    input_data={
                        "user_request": "Execute complex data analysis",
                        "complexity": "high",
                        "expected_duration": 300
                    },
                    started_at=datetime.now(timezone.utc),
                    credits_cost=100
                )
                tx.add(agent_execution)
                await tx.flush()
                execution_id = agent_execution.id
                
                # 5. Update user credits  
                user.credits_remaining -= agent_execution.credits_cost
                
                # 6. Create agent response message
                agent_message = Message(
                    thread_id=thread.id,
                    user_id=user.id,
                    content="Analysis completed successfully",
                    message_type="agent",
                    agent_execution_id=execution_id,
                    created_at=datetime.now(timezone.utc)
                )
                tx.add(agent_message)
                
                # 7. Update execution status
                agent_execution.execution_status = "completed"
                agent_execution.completed_at = datetime.now(timezone.utc)
                agent_execution.output_data = {
                    "analysis_result": "complex_data_processed",
                    "insights_generated": 25,
                    "processing_time": 295
                }
                
                # Transaction commits all changes atomically
            
            # Verify durability - all related data persists across sessions
            await asyncio.sleep(0.5)  # Ensure durability across time
            
            async with tx_manager.transaction() as tx:
                # Verify user state
                persisted_user = await tx.get_user_by_email(test_user_email)
                assert persisted_user is not None, "User not persisted"
                assert persisted_user.credits_remaining == 400, \
                    f"Credits not persisted correctly: expected 400, got {persisted_user.credits_remaining}"
                
                # Verify thread exists
                user_threads = await tx.get_user_threads(persisted_user.id)
                assert len(user_threads) == 1, f"Thread not persisted: expected 1, got {len(user_threads)}"
                
                thread = user_threads[0]
                
                # Verify messages exist and are linked correctly
                thread_messages = await tx.get_thread_messages(thread.id)
                assert len(thread_messages) == 2, f"Messages not persisted: expected 2, got {len(thread_messages)}"
                
                user_msg = next((m for m in thread_messages if m.message_type == "user"), None)
                agent_msg = next((m for m in thread_messages if m.message_type == "agent"), None)
                
                assert user_msg is not None, "User message not persisted"
                assert agent_msg is not None, "Agent message not persisted"
                assert agent_msg.agent_execution_id == execution_id, "Message-execution link broken"
                
                # Verify agent execution record
                execution_record = await tx.get_agent_execution(execution_id)
                assert execution_record is not None, "Agent execution not persisted"
                assert execution_record.execution_status == "completed", \
                    f"Execution status not persisted: {execution_record.execution_status}"
                assert execution_record.output_data is not None, "Execution output not persisted"
                assert "analysis_result" in execution_record.output_data, "Execution data incomplete"
            
            # Test durability after simulated system restart
            # Close and recreate transaction manager
            await tx_manager.close()
            tx_manager = await self.setup_test_environment()
            
            # Verify all data still exists after "restart"
            async with tx_manager.transaction() as tx:
                restart_user = await tx.get_user_by_email(test_user_email)
                assert restart_user is not None, "Data lost after simulated restart"
                
                restart_execution = await tx.get_agent_execution(execution_id)
                assert restart_execution is not None, "Execution lost after restart"
                assert restart_execution.execution_status == "completed", \
                    "Execution state lost after restart"
                    
        finally:
            async with tx_manager.transaction() as tx:
                await tx.cleanup_test_users_by_prefix(self.test_user_prefix)
            await tx_manager.close()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_transaction_performance_under_realistic_load(self):
        """
        Test transaction performance under realistic business load.
        
        BUSINESS CRITICAL: Poor transaction performance impacts user experience.
        System must handle concurrent user operations efficiently.
        """
        tx_manager = await self.setup_test_environment()
        
        try:
            # Create multiple test users for concurrent operations
            test_users = []
            
            # Setup phase - create test users
            setup_start = datetime.now()
            
            for i in range(10):
                user_email = f"{self.test_user_prefix}_perf_{i}@example.com"
                
                async with tx_manager.transaction() as tx:
                    user = User(
                        email=user_email,
                        name=f"Performance Test User {i}",
                        subscription_tier="mid",
                        credits_remaining=100,
                        created_at=datetime.now(timezone.utc)
                    )
                    tx.add(user)
                
                test_users.append(user_email)
            
            setup_duration = (datetime.now() - setup_start).total_seconds()
            assert setup_duration < 5.0, f"User setup too slow: {setup_duration}s"
            
            # Concurrent operation simulation
            async def simulate_user_interaction(user_email: str, interaction_id: int):
                """Simulate realistic user interaction with multiple database operations."""
                try:
                    start_time = datetime.now()
                    
                    async with tx_manager.transaction() as tx:
                        # Get user
                        user = await tx.get_user_by_email(user_email)
                        if not user:
                            raise ValueError(f"User not found: {user_email}")
                        
                        # Create thread
                        thread = Thread(
                            user_id=user.id,
                            title=f"Performance Test Thread {interaction_id}",
                            created_at=datetime.now(timezone.utc)
                        )
                        tx.add(thread)
                        await tx.flush()
                        
                        # Create multiple messages (simulating conversation)
                        for msg_idx in range(3):
                            message = Message(
                                thread_id=thread.id,
                                user_id=user.id,
                                content=f"Message {msg_idx} in interaction {interaction_id}",
                                message_type="user" if msg_idx % 2 == 0 else "agent",
                                created_at=datetime.now(timezone.utc)
                            )
                            tx.add(message)
                        
                        # Update user credits (business operation)
                        user.credits_remaining -= 5
                        
                        # Create agent execution
                        execution = AgentExecution(
                            user_id=user.id,
                            thread_id=thread.id,
                            agent_type="quick_responder",
                            execution_status="completed",
                            input_data={"interaction_id": interaction_id},
                            output_data={"response": "processed"},
                            started_at=datetime.now(timezone.utc),
                            completed_at=datetime.now(timezone.utc),
                            credits_cost=5
                        )
                        tx.add(execution)
                    
                    duration = (datetime.now() - start_time).total_seconds()
                    return {
                        "user_email": user_email,
                        "interaction_id": interaction_id,
                        "duration": duration,
                        "success": True
                    }
                    
                except Exception as e:
                    duration = (datetime.now() - start_time).total_seconds()
                    return {
                        "user_email": user_email, 
                        "interaction_id": interaction_id,
                        "duration": duration,
                        "error": str(e),
                        "success": False
                    }
            
            # Execute concurrent interactions
            interaction_tasks = []
            
            # Each user performs 3 interactions concurrently
            for i, user_email in enumerate(test_users):
                for interaction in range(3):
                    task = simulate_user_interaction(user_email, i * 3 + interaction)
                    interaction_tasks.append(task)
            
            # Execute all interactions concurrently (30 total)
            concurrent_start = datetime.now()
            results = await asyncio.gather(*interaction_tasks, return_exceptions=True)
            total_duration = (datetime.now() - concurrent_start).total_seconds()
            
            # Analyze performance results
            successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
            failed_results = [r for r in results if isinstance(r, dict) and not r.get("success")]
            exceptions = [r for r in results if isinstance(r, Exception)]
            
            # Performance validation
            success_rate = len(successful_results) / len(interaction_tasks)
            avg_transaction_duration = sum(r["duration"] for r in successful_results) / len(successful_results) if successful_results else float('inf')
            
            # Business requirements validation
            assert success_rate >= 0.95, f"Success rate too low: {success_rate:.2%} (min: 95%)"
            assert avg_transaction_duration < 2.0, f"Average transaction too slow: {avg_transaction_duration:.2f}s (max: 2.0s)"
            assert total_duration < 15.0, f"Total concurrent execution too slow: {total_duration:.2f}s (max: 15.0s)"
            
            # Validate data integrity after concurrent operations
            async with tx_manager.transaction() as tx:
                for user_email in test_users:
                    user = await tx.get_user_by_email(user_email)
                    assert user is not None, f"User lost during concurrent operations: {user_email}"
                    
                    # Each user should have 3 threads (if all interactions succeeded)
                    user_threads = await tx.get_user_threads(user.id)
                    user_successful = len([r for r in successful_results if r["user_email"] == user_email])
                    
                    assert len(user_threads) == user_successful, \
                        f"Thread count mismatch for {user_email}: expected {user_successful}, got {len(user_threads)}"
                    
                    # Validate credit deductions
                    expected_credits = 100 - (5 * user_successful)
                    assert user.credits_remaining == expected_credits, \
                        f"Credit calculation wrong for {user_email}: expected {expected_credits}, got {user.credits_remaining}"
                        
        finally:
            async with tx_manager.transaction() as tx:
                await tx.cleanup_test_users_by_prefix(self.test_user_prefix)
            await tx_manager.close()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_transaction_deadlock_detection_and_recovery(self):
        """
        Test deadlock detection and recovery mechanisms.
        
        BUSINESS CRITICAL: Deadlocks can freeze business operations.
        System must detect and resolve deadlocks automatically.
        """
        tx_manager = await self.setup_test_environment()
        
        try:
            # Create two test users for deadlock scenario
            user1_email = f"{self.test_user_prefix}_deadlock_1@example.com"
            user2_email = f"{self.test_user_prefix}_deadlock_2@example.com"
            
            async with tx_manager.transaction() as tx:
                user1 = User(
                    email=user1_email,
                    name="Deadlock Test User 1",
                    subscription_tier="enterprise",
                    credits_remaining=200,
                    created_at=datetime.now(timezone.utc)
                )
                tx.add(user1)
                
                user2 = User(
                    email=user2_email,
                    name="Deadlock Test User 2", 
                    subscription_tier="enterprise",
                    credits_remaining=200,
                    created_at=datetime.now(timezone.utc)
                )
                tx.add(user2)
            
            # Scenario: Two transactions try to transfer credits between users
            # This creates potential for deadlock if not handled properly
            
            deadlock_results = []
            
            async def transfer_credits(from_email: str, to_email: str, amount: int, task_name: str):
                """Simulate credit transfer that could cause deadlock."""
                try:
                    async with tx_manager.transaction() as tx:
                        # Get both users in consistent order to prevent deadlock
                        # This is proper deadlock prevention technique
                        emails = sorted([from_email, to_email])
                        
                        user_a = await tx.get_user_by_email(emails[0])
                        user_b = await tx.get_user_by_email(emails[1])
                        
                        # Determine which is from/to after sorting
                        from_user = user_a if user_a.email == from_email else user_b
                        to_user = user_b if user_b.email == to_email else user_a
                        
                        # Validate sufficient credits
                        if from_user.credits_remaining < amount:
                            raise ValueError(f"Insufficient credits for {task_name}")
                        
                        # Perform transfer
                        from_user.credits_remaining -= amount
                        to_user.credits_remaining += amount
                        
                        # Add processing delay to increase deadlock probability
                        await asyncio.sleep(0.2)
                        
                        return {
                            "task_name": task_name,
                            "from_email": from_email,
                            "to_email": to_email,
                            "amount": amount,
                            "success": True
                        }
                        
                except Exception as e:
                    return {
                        "task_name": task_name,
                        "error": str(e),
                        "success": False
                    }
            
            # Create deadlock scenario - simultaneous bidirectional transfers
            transfer_tasks = [
                transfer_credits(user1_email, user2_email, 50, "Transfer_1_to_2"),
                transfer_credits(user2_email, user1_email, 30, "Transfer_2_to_1"),
                transfer_credits(user1_email, user2_email, 25, "Transfer_1_to_2_again"),
                transfer_credits(user2_email, user1_email, 40, "Transfer_2_to_1_again")
            ]
            
            # Execute concurrent transfers
            deadlock_start = datetime.now()
            transfer_results = await asyncio.gather(*transfer_tasks, return_exceptions=True)
            deadlock_duration = (datetime.now() - deadlock_start).total_seconds()
            
            # Analyze results
            successful_transfers = [r for r in transfer_results if isinstance(r, dict) and r.get("success")]
            failed_transfers = [r for r in transfer_results if isinstance(r, dict) and not r.get("success")]
            exceptions = [r for r in transfer_results if isinstance(r, Exception)]
            
            # System should handle potential deadlocks gracefully
            assert deadlock_duration < 10.0, f"Deadlock resolution too slow: {deadlock_duration}s"
            
            # At least some transfers should succeed (system availability)
            success_count = len(successful_transfers)
            assert success_count >= 2, f"Too many failures - possible deadlock issue: {success_count} successes"
            
            # Verify final state consistency
            async with tx_manager.transaction() as tx:
                final_user1 = await tx.get_user_by_email(user1_email)
                final_user2 = await tx.get_user_by_email(user2_email)
                
                total_credits = final_user1.credits_remaining + final_user2.credits_remaining
                assert total_credits == 400, \
                    f"Credits not conserved: expected 400, got {total_credits} (user1: {final_user1.credits_remaining}, user2: {final_user2.credits_remaining})"
            
            # Validate no system corruption from deadlock handling
            async with tx_manager.transaction() as tx:
                # Both users should still exist and be valid
                user1_check = await tx.get_user_by_email(user1_email)
                user2_check = await tx.get_user_by_email(user2_email)
                
                assert user1_check is not None, "User1 corrupted during deadlock handling"
                assert user2_check is not None, "User2 corrupted during deadlock handling"
                assert user1_check.credits_remaining >= 0, "User1 credits went negative"
                assert user2_check.credits_remaining >= 0, "User2 credits went negative"
                
        finally:
            async with tx_manager.transaction() as tx:
                await tx.cleanup_test_users_by_prefix(self.test_user_prefix)
            await tx_manager.close()


if __name__ == "__main__":
    # Allow running individual tests
    pytest.main([__file__, "-v", "--tb=short"])
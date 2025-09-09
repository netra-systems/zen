"""
Integration Tests: Database Transaction Rollback & Recovery Error Handling

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure data consistency and integrity during system failures
- Value Impact: Transaction recovery prevents data corruption and maintains business continuity
- Strategic Impact: Foundation for reliable data operations and customer trust

This test suite validates database transaction patterns with real services:
- ACID transaction compliance and rollback mechanisms with PostgreSQL
- Distributed transaction coordination across multiple operations
- Deadlock detection and resolution with concurrent user scenarios
- Data consistency validation after failure recovery
- Compensation transaction patterns for complex business operations
- Transaction isolation levels and their impact on error handling

CRITICAL: Uses REAL PostgreSQL - NO MOCKS for integration testing.
Tests validate actual transaction behavior, rollback effectiveness, and data integrity.
"""

import asyncio
import time
import uuid
import random
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Callable
from enum import Enum
import pytest
from contextlib import asynccontextmanager

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from shared.isolated_environment import get_env

# Core imports
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TransactionState(Enum):
    """Transaction processing state levels."""
    PENDING = "pending"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"
    COMPENSATING = "compensating"


class TransactionManager:
    """Manages database transactions with error handling and recovery."""
    
    def __init__(self, postgres_connection):
        self.postgres = postgres_connection
        self.active_transactions = {}
        self.transaction_history = []
        self.compensation_handlers = {}
        self.deadlock_detection_enabled = True
        
    async def create_transaction_context(self, transaction_id: str, isolation_level: str = "READ_COMMITTED"):
        """Create transaction context with specified isolation level."""
        return DatabaseTransactionContext(
            transaction_id=transaction_id,
            postgres=self.postgres,
            isolation_level=isolation_level,
            manager=self
        )
    
    async def register_compensation_handler(self, operation_type: str, handler: Callable):
        """Register compensation handler for specific operation type."""
        self.compensation_handlers[operation_type] = handler
        
    async def execute_with_retry(self, transaction_func: Callable, max_retries: int = 3):
        """Execute transaction with deadlock retry logic."""
        retry_count = 0
        last_exception = None
        
        while retry_count <= max_retries:
            try:
                return await transaction_func()
            except Exception as e:
                last_exception = e
                error_message = str(e).lower()
                
                # Check for deadlock conditions
                if "deadlock" in error_message or "lock timeout" in error_message:
                    retry_count += 1
                    if retry_count <= max_retries:
                        # Exponential backoff with jitter
                        delay = (2 ** retry_count) * 0.1 + random.uniform(0, 0.1)
                        logger.warning(f"Deadlock detected, retrying in {delay:.2f}s (attempt {retry_count})")
                        await asyncio.sleep(delay)
                        continue
                
                # Non-retryable error
                raise
        
        # All retries exhausted
        raise last_exception
    
    async def execute_compensation_transaction(self, failed_transaction_id: str, operations: List[Dict]):
        """Execute compensation transaction for failed operations."""
        compensation_id = f"compensation_{failed_transaction_id}_{int(time.time())}"
        
        async with self.create_transaction_context(compensation_id) as ctx:
            compensation_results = []
            
            for operation in reversed(operations):  # Reverse order for compensation
                operation_type = operation.get("type")
                if operation_type in self.compensation_handlers:
                    try:
                        handler = self.compensation_handlers[operation_type]
                        result = await handler(ctx, operation)
                        compensation_results.append({
                            "operation": operation,
                            "compensation_result": result,
                            "success": True
                        })
                    except Exception as e:
                        compensation_results.append({
                            "operation": operation,
                            "compensation_error": str(e),
                            "success": False
                        })
            
            return {
                "compensation_id": compensation_id,
                "original_transaction": failed_transaction_id,
                "compensation_results": compensation_results,
                "compensation_success": all(r["success"] for r in compensation_results)
            }


class DatabaseTransactionContext:
    """Database transaction context with error handling."""
    
    def __init__(self, transaction_id: str, postgres, isolation_level: str, manager: TransactionManager):
        self.transaction_id = transaction_id
        self.postgres = postgres
        self.isolation_level = isolation_level
        self.manager = manager
        self.state = TransactionState.PENDING
        self.operations = []
        self.started_at = None
        self.completed_at = None
        self.transaction = None
        
    async def __aenter__(self):
        """Enter transaction context."""
        self.started_at = datetime.now(timezone.utc)
        
        # Set isolation level
        await self.postgres.execute(f"SET TRANSACTION ISOLATION LEVEL {self.isolation_level}")
        
        # Begin transaction
        self.transaction = self.postgres.transaction()
        await self.transaction.start()
        
        # Register with manager
        self.manager.active_transactions[self.transaction_id] = self
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit transaction context with proper cleanup."""
        self.completed_at = datetime.now(timezone.utc)
        
        try:
            if exc_type is None:
                # No exception - commit transaction
                await self.transaction.commit()
                self.state = TransactionState.COMMITTED
                
            else:
                # Exception occurred - rollback transaction
                await self.transaction.rollback()
                self.state = TransactionState.ROLLED_BACK
                logger.warning(f"Transaction {self.transaction_id} rolled back due to: {exc_val}")
                
        except Exception as cleanup_error:
            self.state = TransactionState.FAILED
            logger.error(f"Transaction cleanup failed for {self.transaction_id}: {cleanup_error}")
            
        finally:
            # Remove from active transactions
            if self.transaction_id in self.manager.active_transactions:
                del self.manager.active_transactions[self.transaction_id]
            
            # Record transaction history
            transaction_record = {
                "transaction_id": self.transaction_id,
                "state": self.state.value,
                "isolation_level": self.isolation_level,
                "started_at": self.started_at,
                "completed_at": self.completed_at,
                "duration_ms": (self.completed_at - self.started_at).total_seconds() * 1000,
                "operations_count": len(self.operations),
                "operations": self.operations.copy(),
                "exception": str(exc_val) if exc_val else None
            }
            
            self.manager.transaction_history.append(transaction_record)
    
    async def execute_operation(self, operation_type: str, operation_data: Dict, query: str, *args):
        """Execute database operation within transaction context."""
        operation_start = time.time()
        operation_id = str(uuid.uuid4())
        
        operation_record = {
            "operation_id": operation_id,
            "operation_type": operation_type,
            "operation_data": operation_data,
            "started_at": datetime.now(timezone.utc),
            "query": query
        }
        
        try:
            # Execute the database operation
            result = await self.transaction.execute(query, *args)
            
            operation_record["success"] = True
            operation_record["result"] = str(result) if result else None
            operation_record["duration_ms"] = (time.time() - operation_start) * 1000
            
            self.operations.append(operation_record)
            return result
            
        except Exception as e:
            operation_record["success"] = False
            operation_record["error"] = str(e)
            operation_record["duration_ms"] = (time.time() - operation_start) * 1000
            
            self.operations.append(operation_record)
            raise
    
    async def fetch_operation(self, operation_type: str, operation_data: Dict, query: str, *args):
        """Fetch data within transaction context."""
        operation_start = time.time()
        operation_id = str(uuid.uuid4())
        
        operation_record = {
            "operation_id": operation_id,
            "operation_type": operation_type,
            "operation_data": operation_data,
            "started_at": datetime.now(timezone.utc),
            "query": query
        }
        
        try:
            # Fetch data from database
            result = await self.transaction.fetch(query, *args)
            
            operation_record["success"] = True
            operation_record["result_count"] = len(result) if result else 0
            operation_record["duration_ms"] = (time.time() - operation_start) * 1000
            
            self.operations.append(operation_record)
            return result
            
        except Exception as e:
            operation_record["success"] = False
            operation_record["error"] = str(e)
            operation_record["duration_ms"] = (time.time() - operation_start) * 1000
            
            self.operations.append(operation_record)
            raise


class TestDatabaseTransactionRecovery(BaseIntegrationTest):
    """Integration tests for database transaction rollback and recovery patterns."""
    
    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.env = get_env()
        self.env.set("TEST_MODE", "true", source="test")
        self.env.set("USE_REAL_SERVICES", "true", source="test")
        self.auth_helper = E2EAuthHelper()
    
    @pytest.fixture
    async def transaction_manager(self, real_services_fixture):
        """Create transaction manager with real PostgreSQL connection."""
        postgres = real_services_fixture["postgres"]
        manager = TransactionManager(postgres)
        
        # Set up test tables
        await postgres.execute("""
            CREATE TABLE IF NOT EXISTS test_accounts (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                account_name TEXT NOT NULL,
                balance DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        await postgres.execute("""
            CREATE TABLE IF NOT EXISTS test_transactions (
                id SERIAL PRIMARY KEY,
                transaction_id TEXT NOT NULL,
                from_account_id INTEGER,
                to_account_id INTEGER,
                amount DECIMAL(12, 2) NOT NULL,
                transaction_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (from_account_id) REFERENCES test_accounts(id),
                FOREIGN KEY (to_account_id) REFERENCES test_accounts(id)
            )
        """)
        
        await postgres.execute("""
            CREATE TABLE IF NOT EXISTS test_audit_log (
                id SERIAL PRIMARY KEY,
                transaction_id TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                operation_data JSONB,
                success BOOLEAN NOT NULL,
                timestamp TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Register compensation handlers
        async def compensate_account_credit(ctx: DatabaseTransactionContext, operation: Dict):
            """Compensate account credit by debiting the same amount."""
            account_id = operation["operation_data"]["account_id"]
            amount = operation["operation_data"]["amount"]
            
            await ctx.execute_operation(
                "compensate_credit",
                {"account_id": account_id, "amount": amount},
                "UPDATE test_accounts SET balance = balance - $1 WHERE id = $2",
                amount, account_id
            )
            return {"compensated_amount": amount, "account_id": account_id}
        
        async def compensate_account_debit(ctx: DatabaseTransactionContext, operation: Dict):
            """Compensate account debit by crediting the same amount."""
            account_id = operation["operation_data"]["account_id"]
            amount = operation["operation_data"]["amount"]
            
            await ctx.execute_operation(
                "compensate_debit",
                {"account_id": account_id, "amount": amount},
                "UPDATE test_accounts SET balance = balance + $1 WHERE id = $2",
                amount, account_id
            )
            return {"compensated_amount": amount, "account_id": account_id}
        
        await manager.register_compensation_handler("account_credit", compensate_account_credit)
        await manager.register_compensation_handler("account_debit", compensate_account_debit)
        
        yield manager
        
        # Cleanup test tables
        await postgres.execute("DROP TABLE IF EXISTS test_audit_log")
        await postgres.execute("DROP TABLE IF EXISTS test_transactions")
        await postgres.execute("DROP TABLE IF EXISTS test_accounts")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_transaction_rollback_on_constraint_violation(self, real_services_fixture, transaction_manager):
        """Test transaction rollback when database constraints are violated."""
        
        # Business Value: Constraint violations should not leave partial data
        
        postgres = real_services_fixture["postgres"]
        
        # Create test user account
        user_context = await create_authenticated_user_context(
            user_email="transaction_test@example.com",
            user_id="transaction_test_user",
            environment="test"
        )
        
        user_id = str(user_context.user_id)
        
        # Create initial account
        account_id = await postgres.fetchval("""
            INSERT INTO test_accounts (user_id, account_name, balance)
            VALUES ($1, 'Primary Account', 1000.00)
            RETURNING id
        """, user_id)
        
        # Test transaction that should fail due to constraint violation
        transaction_id = f"test_constraint_violation_{int(time.time())}"
        
        try:
            async with transaction_manager.create_transaction_context(transaction_id) as ctx:
                # Valid operation - debit account
                await ctx.execute_operation(
                    "account_debit",
                    {"account_id": account_id, "amount": 100.00},
                    "UPDATE test_accounts SET balance = balance - $1 WHERE id = $2",
                    100.00, account_id
                )
                
                # Log transaction record
                await ctx.execute_operation(
                    "log_transaction",
                    {"type": "debit", "amount": 100.00},
                    """INSERT INTO test_transactions (transaction_id, from_account_id, amount, transaction_type)
                       VALUES ($1, $2, $3, 'debit')""",
                    transaction_id, account_id, 100.00
                )
                
                # Invalid operation - try to debit more than available balance
                await ctx.execute_operation(
                    "account_debit",
                    {"account_id": account_id, "amount": 2000.00},
                    """UPDATE test_accounts SET balance = balance - $1 WHERE id = $2 
                       AND balance >= $1""",  # This will fail
                    2000.00, account_id
                )
                
                # This should not be reached due to constraint violation
                await ctx.execute_operation(
                    "log_transaction",
                    {"type": "debit", "amount": 2000.00},
                    """INSERT INTO test_transactions (transaction_id, from_account_id, amount, transaction_type)
                       VALUES ($1, $2, $3, 'debit')""",
                    transaction_id, account_id, 2000.00
                )
                
        except Exception as e:
            # Expected to fail
            logger.info(f"Transaction failed as expected: {e}")
        
        # Verify rollback occurred - account balance should be unchanged
        final_balance = await postgres.fetchval(
            "SELECT balance FROM test_accounts WHERE id = $1", account_id
        )
        assert final_balance == 1000.00, "Transaction rollback failed - balance changed"
        
        # Verify no transaction records were persisted
        transaction_count = await postgres.fetchval(
            "SELECT COUNT(*) FROM test_transactions WHERE transaction_id = $1", transaction_id
        )
        assert transaction_count == 0, "Transaction rollback failed - records persisted"
        
        # Verify transaction manager recorded the rollback
        tx_history = [tx for tx in transaction_manager.transaction_history if tx["transaction_id"] == transaction_id]
        assert len(tx_history) == 1
        assert tx_history[0]["state"] == "rolled_back"
        assert len(tx_history[0]["operations"]) >= 2  # At least the operations attempted
        
        logger.info("✅ Transaction rollback on constraint violation test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_distributed_transaction_coordination(self, real_services_fixture, transaction_manager):
        """Test coordination of distributed transactions across multiple operations."""
        
        # Business Value: Distributed transactions ensure consistency across complex operations
        
        postgres = real_services_fixture["postgres"]
        
        # Create test scenario - money transfer between accounts
        user_context = await create_authenticated_user_context(
            user_email="distributed_tx_test@example.com",
            user_id="distributed_tx_user",
            environment="test"
        )
        
        user_id = str(user_context.user_id)
        
        # Create source and destination accounts
        source_account_id = await postgres.fetchval("""
            INSERT INTO test_accounts (user_id, account_name, balance)
            VALUES ($1, 'Source Account', 500.00)
            RETURNING id
        """, user_id)
        
        dest_account_id = await postgres.fetchval("""
            INSERT INTO test_accounts (user_id, account_name, balance)
            VALUES ($1, 'Destination Account', 200.00)
            RETURNING id
        """, user_id)
        
        transfer_amount = 150.00
        transaction_id = f"transfer_{source_account_id}_{dest_account_id}_{int(time.time())}"
        
        # Execute distributed transaction
        async with transaction_manager.create_transaction_context(transaction_id, "SERIALIZABLE") as ctx:
            # Step 1: Verify source account has sufficient funds
            source_balance = await ctx.fetch_operation(
                "check_balance",
                {"account_id": source_account_id},
                "SELECT balance FROM test_accounts WHERE id = $1 FOR UPDATE",
                source_account_id
            )
            
            if not source_balance or source_balance[0]["balance"] < transfer_amount:
                raise ValueError("Insufficient funds for transfer")
            
            # Step 2: Debit source account
            await ctx.execute_operation(
                "account_debit",
                {"account_id": source_account_id, "amount": transfer_amount},
                "UPDATE test_accounts SET balance = balance - $1, updated_at = NOW() WHERE id = $2",
                transfer_amount, source_account_id
            )
            
            # Step 3: Credit destination account
            await ctx.execute_operation(
                "account_credit",
                {"account_id": dest_account_id, "amount": transfer_amount},
                "UPDATE test_accounts SET balance = balance + $1, updated_at = NOW() WHERE id = $2",
                transfer_amount, dest_account_id
            )
            
            # Step 4: Log the transfer transaction
            await ctx.execute_operation(
                "log_transfer",
                {"from_account": source_account_id, "to_account": dest_account_id, "amount": transfer_amount},
                """INSERT INTO test_transactions (transaction_id, from_account_id, to_account_id, amount, transaction_type, status)
                   VALUES ($1, $2, $3, $4, 'transfer', 'completed')""",
                transaction_id, source_account_id, dest_account_id, transfer_amount
            )
            
            # Step 5: Audit log entry
            await ctx.execute_operation(
                "audit_log",
                {"transaction_type": "transfer", "details": {"from": source_account_id, "to": dest_account_id, "amount": transfer_amount}},
                """INSERT INTO test_audit_log (transaction_id, operation_type, operation_data, success)
                   VALUES ($1, 'transfer', $2, true)""",
                transaction_id, 
                json.dumps({"from_account": source_account_id, "to_account": dest_account_id, "amount": float(transfer_amount)})
            )
        
        # Verify transaction completion
        final_source_balance = await postgres.fetchval(
            "SELECT balance FROM test_accounts WHERE id = $1", source_account_id
        )
        final_dest_balance = await postgres.fetchval(
            "SELECT balance FROM test_accounts WHERE id = $1", dest_account_id
        )
        
        assert final_source_balance == 350.00, "Source account balance incorrect after transfer"
        assert final_dest_balance == 350.00, "Destination account balance incorrect after transfer"
        
        # Verify transaction log
        transfer_record = await postgres.fetchrow(
            "SELECT * FROM test_transactions WHERE transaction_id = $1", transaction_id
        )
        assert transfer_record is not None
        assert transfer_record["status"] == "completed"
        assert transfer_record["amount"] == transfer_amount
        
        # Verify audit trail
        audit_records = await postgres.fetch(
            "SELECT * FROM test_audit_log WHERE transaction_id = $1", transaction_id
        )
        assert len(audit_records) >= 1
        assert all(record["success"] for record in audit_records)
        
        # Verify transaction manager state
        tx_history = [tx for tx in transaction_manager.transaction_history if tx["transaction_id"] == transaction_id]
        assert len(tx_history) == 1
        assert tx_history[0]["state"] == "committed"
        assert tx_history[0]["operations_count"] == 5  # All operations completed
        
        logger.info("✅ Distributed transaction coordination test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_deadlock_detection_and_recovery(self, real_services_fixture, transaction_manager):
        """Test deadlock detection and automatic recovery mechanisms."""
        
        # Business Value: Deadlock recovery ensures system remains responsive under concurrent load
        
        postgres = real_services_fixture["postgres"]
        
        # Create test accounts for deadlock scenario
        user_context = await create_authenticated_user_context(
            user_email="deadlock_test@example.com",
            user_id="deadlock_test_user",
            environment="test"
        )
        
        user_id = str(user_context.user_id)
        
        account_a_id = await postgres.fetchval("""
            INSERT INTO test_accounts (user_id, account_name, balance)
            VALUES ($1, 'Account A', 1000.00)
            RETURNING id
        """, user_id)
        
        account_b_id = await postgres.fetchval("""
            INSERT INTO test_accounts (user_id, account_name, balance)
            VALUES ($1, 'Account B', 1000.00)
            RETURNING id
        """, user_id)
        
        deadlock_detected = False
        successful_operations = []
        
        async def transaction_a_to_b():
            """Transaction: Transfer from A to B, then update A again."""
            nonlocal deadlock_detected, successful_operations
            
            tx_id = f"deadlock_test_a_to_b_{int(time.time() * 1000)}"
            
            try:
                async with transaction_manager.create_transaction_context(tx_id, "SERIALIZABLE") as ctx:
                    # Lock account A first
                    await ctx.execute_operation(
                        "lock_account_a",
                        {"account_id": account_a_id},
                        "SELECT balance FROM test_accounts WHERE id = $1 FOR UPDATE",
                        account_a_id
                    )
                    
                    # Brief delay to increase deadlock probability
                    await asyncio.sleep(0.1)
                    
                    # Try to lock account B (potential deadlock point)
                    await ctx.execute_operation(
                        "lock_account_b",
                        {"account_id": account_b_id},
                        "SELECT balance FROM test_accounts WHERE id = $1 FOR UPDATE",
                        account_b_id
                    )
                    
                    # Transfer 50 from A to B
                    await ctx.execute_operation(
                        "transfer_a_to_b",
                        {"from": account_a_id, "to": account_b_id, "amount": 50.00},
                        "UPDATE test_accounts SET balance = balance - 50.00 WHERE id = $1",
                        account_a_id
                    )
                    
                    await ctx.execute_operation(
                        "credit_b_from_a",
                        {"account_id": account_b_id, "amount": 50.00},
                        "UPDATE test_accounts SET balance = balance + 50.00 WHERE id = $1",
                        account_b_id
                    )
                    
                    successful_operations.append("a_to_b")
                    
            except Exception as e:
                if "deadlock" in str(e).lower():
                    deadlock_detected = True
                    logger.info("Deadlock detected in transaction A->B")
                raise
        
        async def transaction_b_to_a():
            """Transaction: Transfer from B to A, then update B again."""
            nonlocal deadlock_detected, successful_operations
            
            tx_id = f"deadlock_test_b_to_a_{int(time.time() * 1000)}"
            
            try:
                async with transaction_manager.create_transaction_context(tx_id, "SERIALIZABLE") as ctx:
                    # Lock account B first
                    await ctx.execute_operation(
                        "lock_account_b",
                        {"account_id": account_b_id},
                        "SELECT balance FROM test_accounts WHERE id = $1 FOR UPDATE",
                        account_b_id
                    )
                    
                    # Brief delay to increase deadlock probability
                    await asyncio.sleep(0.1)
                    
                    # Try to lock account A (potential deadlock point)
                    await ctx.execute_operation(
                        "lock_account_a",
                        {"account_id": account_a_id},
                        "SELECT balance FROM test_accounts WHERE id = $1 FOR UPDATE",
                        account_a_id
                    )
                    
                    # Transfer 75 from B to A
                    await ctx.execute_operation(
                        "transfer_b_to_a",
                        {"from": account_b_id, "to": account_a_id, "amount": 75.00},
                        "UPDATE test_accounts SET balance = balance - 75.00 WHERE id = $1",
                        account_b_id
                    )
                    
                    await ctx.execute_operation(
                        "credit_a_from_b",
                        {"account_id": account_a_id, "amount": 75.00},
                        "UPDATE test_accounts SET balance = balance + 75.00 WHERE id = $1",
                        account_a_id
                    )
                    
                    successful_operations.append("b_to_a")
                    
            except Exception as e:
                if "deadlock" in str(e).lower():
                    deadlock_detected = True
                    logger.info("Deadlock detected in transaction B->A")
                raise
        
        # Execute transactions concurrently to create deadlock scenario
        results = await asyncio.gather(
            transaction_manager.execute_with_retry(transaction_a_to_b),
            transaction_manager.execute_with_retry(transaction_b_to_a),
            return_exceptions=True
        )
        
        # Verify deadlock handling
        exceptions_caught = [r for r in results if isinstance(r, Exception)]
        
        # At least one transaction should complete successfully after retry
        assert len(successful_operations) >= 1, "No transactions completed successfully"
        
        # Verify account balances are consistent
        final_balance_a = await postgres.fetchval(
            "SELECT balance FROM test_accounts WHERE id = $1", account_a_id
        )
        final_balance_b = await postgres.fetchval(
            "SELECT balance FROM test_accounts WHERE id = $1", account_b_id
        )
        
        total_balance = final_balance_a + final_balance_b
        assert total_balance == 2000.00, f"Total balance inconsistent: {total_balance}"
        
        # Verify transaction manager recorded retry attempts
        retry_transactions = [
            tx for tx in transaction_manager.transaction_history 
            if "deadlock_test" in tx["transaction_id"]
        ]
        
        # Should have multiple transaction attempts due to retries
        assert len(retry_transactions) >= 2, "Deadlock retry mechanism not working"
        
        # At least one should be committed
        committed_transactions = [tx for tx in retry_transactions if tx["state"] == "committed"]
        assert len(committed_transactions) >= 1, "No transactions committed after deadlock recovery"
        
        logger.info("✅ Deadlock detection and recovery test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_compensation_transaction_execution(self, real_services_fixture, transaction_manager):
        """Test compensation transaction patterns for failed complex operations."""
        
        # Business Value: Compensation transactions maintain data consistency during partial failures
        
        postgres = real_services_fixture["postgres"]
        
        # Create test scenario - multi-step business process
        user_context = await create_authenticated_user_context(
            user_email="compensation_test@example.com",
            user_id="compensation_test_user",
            environment="test"
        )
        
        user_id = str(user_context.user_id)
        
        # Create multiple accounts for complex transfer scenario
        account_ids = []
        for i in range(3):
            account_id = await postgres.fetchval("""
                INSERT INTO test_accounts (user_id, account_name, balance)
                VALUES ($1, $2, 1000.00)
                RETURNING id
            """, user_id, f"Account {i + 1}")
            account_ids.append(account_id)
        
        # Complex business transaction that will partially fail
        complex_transaction_id = f"complex_business_tx_{int(time.time())}"
        operations_performed = []
        
        try:
            async with transaction_manager.create_transaction_context(complex_transaction_id) as ctx:
                # Step 1: Debit from account 1 (should succeed)
                await ctx.execute_operation(
                    "account_debit",
                    {"account_id": account_ids[0], "amount": 200.00},
                    "UPDATE test_accounts SET balance = balance - $1 WHERE id = $2",
                    200.00, account_ids[0]
                )
                operations_performed.append({
                    "type": "account_debit",
                    "operation_data": {"account_id": account_ids[0], "amount": 200.00}
                })
                
                # Step 2: Credit to account 2 (should succeed)
                await ctx.execute_operation(
                    "account_credit",
                    {"account_id": account_ids[1], "amount": 150.00},
                    "UPDATE test_accounts SET balance = balance + $1 WHERE id = $2",
                    150.00, account_ids[1]
                )
                operations_performed.append({
                    "type": "account_credit",
                    "operation_data": {"account_id": account_ids[1], "amount": 150.00}
                })
                
                # Step 3: Credit to account 3 (should succeed)
                await ctx.execute_operation(
                    "account_credit",
                    {"account_id": account_ids[2], "amount": 50.00},
                    "UPDATE test_accounts SET balance = balance + $1 WHERE id = $2",
                    50.00, account_ids[2]
                )
                operations_performed.append({
                    "type": "account_credit",
                    "operation_data": {"account_id": account_ids[2], "amount": 50.00}
                })
                
                # Step 4: Attempt invalid operation (will cause rollback)
                await ctx.execute_operation(
                    "invalid_operation",
                    {"account_id": account_ids[0], "amount": 5000.00},
                    "UPDATE test_accounts SET balance = balance - $1 WHERE id = $2 AND balance >= $1",
                    5000.00, account_ids[0]  # Will fail - insufficient funds
                )
                
        except Exception as e:
            logger.info(f"Complex transaction failed as expected: {e}")
            
            # Execute compensation transaction
            compensation_result = await transaction_manager.execute_compensation_transaction(
                complex_transaction_id, operations_performed
            )
            
            # Verify compensation execution
            assert compensation_result["compensation_success"] is True
            assert len(compensation_result["compensation_results"]) == len(operations_performed)
            
            # Verify compensation reversed the operations
            for i, comp_result in enumerate(compensation_result["compensation_results"]):
                assert comp_result["success"] is True
                original_op = operations_performed[-(i+1)]  # Reverse order
                assert comp_result["operation"]["type"] == original_op["type"]
        
        # Verify all accounts returned to original balance
        for account_id in account_ids:
            final_balance = await postgres.fetchval(
                "SELECT balance FROM test_accounts WHERE id = $1", account_id
            )
            assert final_balance == 1000.00, f"Account {account_id} balance not restored: {final_balance}"
        
        # Verify transaction history
        failed_tx = next(
            (tx for tx in transaction_manager.transaction_history 
             if tx["transaction_id"] == complex_transaction_id), None
        )
        assert failed_tx is not None
        assert failed_tx["state"] == "rolled_back"
        
        compensation_tx = next(
            (tx for tx in transaction_manager.transaction_history 
             if tx["transaction_id"].startswith("compensation_")), None
        )
        assert compensation_tx is not None
        assert compensation_tx["state"] == "committed"
        
        logger.info("✅ Compensation transaction execution test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_transaction_isolation(self, real_services_fixture, transaction_manager):
        """Test transaction isolation levels under concurrent access patterns."""
        
        # Business Value: Proper isolation ensures data consistency under concurrent load
        
        postgres = real_services_fixture["postgres"]
        
        # Create shared test account
        user_context = await create_authenticated_user_context(
            user_email="isolation_test@example.com",
            user_id="isolation_test_user",
            environment="test"
        )
        
        user_id = str(user_context.user_id)
        
        shared_account_id = await postgres.fetchval("""
            INSERT INTO test_accounts (user_id, account_name, balance)
            VALUES ($1, 'Shared Account', 1000.00)
            RETURNING id
        """, user_id)
        
        # Test different isolation levels
        isolation_levels = ["READ_COMMITTED", "REPEATABLE_READ", "SERIALIZABLE"]
        isolation_results = {}
        
        for isolation_level in isolation_levels:
            transaction_results = []
            
            async def concurrent_transaction(tx_index: int, amount: float):
                """Execute concurrent transaction with specified isolation level."""
                tx_id = f"isolation_test_{isolation_level}_{tx_index}_{int(time.time() * 1000)}"
                
                try:
                    async with transaction_manager.create_transaction_context(tx_id, isolation_level) as ctx:
                        # Read current balance
                        balance_result = await ctx.fetch_operation(
                            "read_balance",
                            {"account_id": shared_account_id},
                            "SELECT balance FROM test_accounts WHERE id = $1",
                            shared_account_id
                        )
                        
                        current_balance = balance_result[0]["balance"] if balance_result else 0
                        
                        # Simulate processing time
                        await asyncio.sleep(0.05)
                        
                        # Update based on read value
                        new_balance = current_balance + amount
                        
                        await ctx.execute_operation(
                            "update_balance",
                            {"account_id": shared_account_id, "new_balance": new_balance},
                            "UPDATE test_accounts SET balance = $1 WHERE id = $2",
                            new_balance, shared_account_id
                        )
                        
                        return {
                            "transaction_id": tx_id,
                            "success": True,
                            "initial_balance": float(current_balance),
                            "amount_added": amount,
                            "final_balance": float(new_balance),
                            "isolation_level": isolation_level
                        }
                        
                except Exception as e:
                    return {
                        "transaction_id": tx_id,
                        "success": False,
                        "error": str(e),
                        "isolation_level": isolation_level
                    }
            
            # Reset account balance
            await postgres.execute(
                "UPDATE test_accounts SET balance = 1000.00 WHERE id = $1", shared_account_id
            )
            
            # Execute concurrent transactions
            concurrent_tasks = [
                concurrent_transaction(i, 100.00) for i in range(5)
            ]
            
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            # Filter successful results
            successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
            failed_results = [r for r in results if isinstance(r, dict) and not r.get("success")]
            
            # Get final account balance
            final_balance = await postgres.fetchval(
                "SELECT balance FROM test_accounts WHERE id = $1", shared_account_id
            )
            
            isolation_results[isolation_level] = {
                "successful_transactions": len(successful_results),
                "failed_transactions": len(failed_results),
                "final_balance": float(final_balance),
                "expected_balance": 1000.00 + (len(successful_results) * 100.00),
                "isolation_maintained": final_balance == (1000.00 + len(successful_results) * 100.00),
                "transaction_details": successful_results + failed_results
            }
        
        # Analyze isolation effectiveness
        for isolation_level, results in isolation_results.items():
            logger.info(f"Isolation level {isolation_level}: "
                       f"{results['successful_transactions']} successful, "
                       f"{results['failed_transactions']} failed, "
                       f"final balance: {results['final_balance']}")
            
            # Higher isolation levels should have more consistent results
            if isolation_level == "SERIALIZABLE":
                # Serializable should maintain strict consistency
                assert results["isolation_maintained"] is True, \
                    f"Serializable isolation failed: expected {results['expected_balance']}, got {results['final_balance']}"
        
        # Verify transaction manager recorded all attempts
        isolation_transactions = [
            tx for tx in transaction_manager.transaction_history 
            if "isolation_test" in tx["transaction_id"]
        ]
        
        assert len(isolation_transactions) >= 10, "Not all isolation test transactions recorded"
        
        # Group by isolation level
        isolation_stats = {}
        for tx in isolation_transactions:
            level = tx["isolation_level"]
            if level not in isolation_stats:
                isolation_stats[level] = {"committed": 0, "rolled_back": 0}
            isolation_stats[level][tx["state"]] += 1
        
        # Store isolation test results
        await postgres.execute("""
            INSERT INTO test_audit_log (transaction_id, operation_type, operation_data, success)
            VALUES ('isolation_test_summary', 'isolation_level_comparison', $1, true)
        """, json.dumps(isolation_results))
        
        logger.info("✅ Concurrent transaction isolation test passed")


if __name__ == "__main__":
    # Run specific test for development
    import pytest
    pytest.main([__file__, "-v", "-s"])
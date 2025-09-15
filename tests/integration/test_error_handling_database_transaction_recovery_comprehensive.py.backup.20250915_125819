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
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger
logger = central_logger.get_logger(__name__)

class TransactionState(Enum):
    """Transaction processing state levels."""
    PENDING = 'pending'
    COMMITTED = 'committed'
    ROLLED_BACK = 'rolled_back'
    FAILED = 'failed'
    COMPENSATING = 'compensating'

class TransactionManager:
    """Manages database transactions with error handling and recovery."""

    def __init__(self, postgres_connection):
        self.postgres = postgres_connection
        self.active_transactions = {}
        self.transaction_history = []
        self.compensation_handlers = {}
        self.deadlock_detection_enabled = True

    async def create_transaction_context(self, transaction_id: str, isolation_level: str='READ_COMMITTED'):
        """Create transaction context with specified isolation level."""
        return DatabaseTransactionContext(transaction_id=transaction_id, postgres=self.postgres, isolation_level=isolation_level, manager=self)

    async def register_compensation_handler(self, operation_type: str, handler: Callable):
        """Register compensation handler for specific operation type."""
        self.compensation_handlers[operation_type] = handler

    async def execute_with_retry(self, transaction_func: Callable, max_retries: int=3):
        """Execute transaction with deadlock retry logic."""
        retry_count = 0
        last_exception = None
        while retry_count <= max_retries:
            try:
                return await transaction_func()
            except Exception as e:
                last_exception = e
                error_message = str(e).lower()
                if 'deadlock' in error_message or 'lock timeout' in error_message:
                    retry_count += 1
                    if retry_count <= max_retries:
                        delay = 2 ** retry_count * 0.1 + random.uniform(0, 0.1)
                        logger.warning(f'Deadlock detected, retrying in {delay:.2f}s (attempt {retry_count})')
                        await asyncio.sleep(delay)
                        continue
                raise
        raise last_exception

    async def execute_compensation_transaction(self, failed_transaction_id: str, operations: List[Dict]):
        """Execute compensation transaction for failed operations."""
        compensation_id = f'compensation_{failed_transaction_id}_{int(time.time())}'
        async with self.create_transaction_context(compensation_id) as ctx:
            compensation_results = []
            for operation in reversed(operations):
                operation_type = operation.get('type')
                if operation_type in self.compensation_handlers:
                    try:
                        handler = self.compensation_handlers[operation_type]
                        result = await handler(ctx, operation)
                        compensation_results.append({'operation': operation, 'compensation_result': result, 'success': True})
                    except Exception as e:
                        compensation_results.append({'operation': operation, 'compensation_error': str(e), 'success': False})
            return {'compensation_id': compensation_id, 'original_transaction': failed_transaction_id, 'compensation_results': compensation_results, 'compensation_success': all((r['success'] for r in compensation_results))}

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
        await self.postgres.execute(f'SET TRANSACTION ISOLATION LEVEL {self.isolation_level}')
        self.transaction = self.postgres.transaction()
        await self.transaction.start()
        self.manager.active_transactions[self.transaction_id] = self
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit transaction context with proper cleanup."""
        self.completed_at = datetime.now(timezone.utc)
        try:
            if exc_type is None:
                await self.transaction.commit()
                self.state = TransactionState.COMMITTED
            else:
                await self.transaction.rollback()
                self.state = TransactionState.ROLLED_BACK
                logger.warning(f'Transaction {self.transaction_id} rolled back due to: {exc_val}')
        except Exception as cleanup_error:
            self.state = TransactionState.FAILED
            logger.error(f'Transaction cleanup failed for {self.transaction_id}: {cleanup_error}')
        finally:
            if self.transaction_id in self.manager.active_transactions:
                del self.manager.active_transactions[self.transaction_id]
            transaction_record = {'transaction_id': self.transaction_id, 'state': self.state.value, 'isolation_level': self.isolation_level, 'started_at': self.started_at, 'completed_at': self.completed_at, 'duration_ms': (self.completed_at - self.started_at).total_seconds() * 1000, 'operations_count': len(self.operations), 'operations': self.operations.copy(), 'exception': str(exc_val) if exc_val else None}
            self.manager.transaction_history.append(transaction_record)

    async def execute_operation(self, operation_type: str, operation_data: Dict, query: str, *args):
        """Execute database operation within transaction context."""
        operation_start = time.time()
        operation_id = str(uuid.uuid4())
        operation_record = {'operation_id': operation_id, 'operation_type': operation_type, 'operation_data': operation_data, 'started_at': datetime.now(timezone.utc), 'query': query}
        try:
            result = await self.transaction.execute(query, *args)
            operation_record['success'] = True
            operation_record['result'] = str(result) if result else None
            operation_record['duration_ms'] = (time.time() - operation_start) * 1000
            self.operations.append(operation_record)
            return result
        except Exception as e:
            operation_record['success'] = False
            operation_record['error'] = str(e)
            operation_record['duration_ms'] = (time.time() - operation_start) * 1000
            self.operations.append(operation_record)
            raise

    async def fetch_operation(self, operation_type: str, operation_data: Dict, query: str, *args):
        """Fetch data within transaction context."""
        operation_start = time.time()
        operation_id = str(uuid.uuid4())
        operation_record = {'operation_id': operation_id, 'operation_type': operation_type, 'operation_data': operation_data, 'started_at': datetime.now(timezone.utc), 'query': query}
        try:
            result = await self.transaction.fetch(query, *args)
            operation_record['success'] = True
            operation_record['result_count'] = len(result) if result else 0
            operation_record['duration_ms'] = (time.time() - operation_start) * 1000
            self.operations.append(operation_record)
            return result
        except Exception as e:
            operation_record['success'] = False
            operation_record['error'] = str(e)
            operation_record['duration_ms'] = (time.time() - operation_start) * 1000
            self.operations.append(operation_record)
            raise

class TestDatabaseTransactionRecovery(BaseIntegrationTest):
    """Integration tests for database transaction rollback and recovery patterns."""

    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.env = get_env()
        self.env.set('TEST_MODE', 'true', source='test')
        self.env.set('USE_REAL_SERVICES', 'true', source='test')
        self.auth_helper = E2EAuthHelper()

    @pytest.fixture
    async def transaction_manager(self, real_services_fixture):
        """Create transaction manager with real PostgreSQL connection."""
        postgres = real_services_fixture['postgres']
        manager = TransactionManager(postgres)
        await postgres.execute('\n            CREATE TABLE IF NOT EXISTS test_accounts (\n                id SERIAL PRIMARY KEY,\n                user_id TEXT NOT NULL,\n                account_name TEXT NOT NULL,\n                balance DECIMAL(12, 2) NOT NULL DEFAULT 0.00,\n                created_at TIMESTAMP DEFAULT NOW(),\n                updated_at TIMESTAMP DEFAULT NOW()\n            )\n        ')
        await postgres.execute("\n            CREATE TABLE IF NOT EXISTS test_transactions (\n                id SERIAL PRIMARY KEY,\n                transaction_id TEXT NOT NULL,\n                from_account_id INTEGER,\n                to_account_id INTEGER,\n                amount DECIMAL(12, 2) NOT NULL,\n                transaction_type TEXT NOT NULL,\n                status TEXT NOT NULL DEFAULT 'pending',\n                created_at TIMESTAMP DEFAULT NOW(),\n                FOREIGN KEY (from_account_id) REFERENCES test_accounts(id),\n                FOREIGN KEY (to_account_id) REFERENCES test_accounts(id)\n            )\n        ")
        await postgres.execute('\n            CREATE TABLE IF NOT EXISTS test_audit_log (\n                id SERIAL PRIMARY KEY,\n                transaction_id TEXT NOT NULL,\n                operation_type TEXT NOT NULL,\n                operation_data JSONB,\n                success BOOLEAN NOT NULL,\n                timestamp TIMESTAMP DEFAULT NOW()\n            )\n        ')

        async def compensate_account_credit(ctx: DatabaseTransactionContext, operation: Dict):
            """Compensate account credit by debiting the same amount."""
            account_id = operation['operation_data']['account_id']
            amount = operation['operation_data']['amount']
            await ctx.execute_operation('compensate_credit', {'account_id': account_id, 'amount': amount}, 'UPDATE test_accounts SET balance = balance - $1 WHERE id = $2', amount, account_id)
            return {'compensated_amount': amount, 'account_id': account_id}

        async def compensate_account_debit(ctx: DatabaseTransactionContext, operation: Dict):
            """Compensate account debit by crediting the same amount."""
            account_id = operation['operation_data']['account_id']
            amount = operation['operation_data']['amount']
            await ctx.execute_operation('compensate_debit', {'account_id': account_id, 'amount': amount}, 'UPDATE test_accounts SET balance = balance + $1 WHERE id = $2', amount, account_id)
            return {'compensated_amount': amount, 'account_id': account_id}
        await manager.register_compensation_handler('account_credit', compensate_account_credit)
        await manager.register_compensation_handler('account_debit', compensate_account_debit)
        yield manager
        await postgres.execute('DROP TABLE IF EXISTS test_audit_log')
        await postgres.execute('DROP TABLE IF EXISTS test_transactions')
        await postgres.execute('DROP TABLE IF EXISTS test_accounts')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_transaction_rollback_on_constraint_violation(self, real_services_fixture, transaction_manager):
        """Test transaction rollback when database constraints are violated."""
        postgres = real_services_fixture['postgres']
        user_context = await create_authenticated_user_context(user_email='transaction_test@example.com', user_id='transaction_test_user', environment='test')
        user_id = str(user_context.user_id)
        account_id = await postgres.fetchval("\n            INSERT INTO test_accounts (user_id, account_name, balance)\n            VALUES ($1, 'Primary Account', 1000.00)\n            RETURNING id\n        ", user_id)
        transaction_id = f'test_constraint_violation_{int(time.time())}'
        try:
            async with transaction_manager.create_transaction_context(transaction_id) as ctx:
                await ctx.execute_operation('account_debit', {'account_id': account_id, 'amount': 100.0}, 'UPDATE test_accounts SET balance = balance - $1 WHERE id = $2', 100.0, account_id)
                await ctx.execute_operation('log_transaction', {'type': 'debit', 'amount': 100.0}, "INSERT INTO test_transactions (transaction_id, from_account_id, amount, transaction_type)\n                       VALUES ($1, $2, $3, 'debit')", transaction_id, account_id, 100.0)
                await ctx.execute_operation('account_debit', {'account_id': account_id, 'amount': 2000.0}, 'UPDATE test_accounts SET balance = balance - $1 WHERE id = $2 \n                       AND balance >= $1', 2000.0, account_id)
                await ctx.execute_operation('log_transaction', {'type': 'debit', 'amount': 2000.0}, "INSERT INTO test_transactions (transaction_id, from_account_id, amount, transaction_type)\n                       VALUES ($1, $2, $3, 'debit')", transaction_id, account_id, 2000.0)
        except Exception as e:
            logger.info(f'Transaction failed as expected: {e}')
        final_balance = await postgres.fetchval('SELECT balance FROM test_accounts WHERE id = $1', account_id)
        assert final_balance == 1000.0, 'Transaction rollback failed - balance changed'
        transaction_count = await postgres.fetchval('SELECT COUNT(*) FROM test_transactions WHERE transaction_id = $1', transaction_id)
        assert transaction_count == 0, 'Transaction rollback failed - records persisted'
        tx_history = [tx for tx in transaction_manager.transaction_history if tx['transaction_id'] == transaction_id]
        assert len(tx_history) == 1
        assert tx_history[0]['state'] == 'rolled_back'
        assert len(tx_history[0]['operations']) >= 2
        logger.info(' PASS:  Transaction rollback on constraint violation test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_distributed_transaction_coordination(self, real_services_fixture, transaction_manager):
        """Test coordination of distributed transactions across multiple operations."""
        postgres = real_services_fixture['postgres']
        user_context = await create_authenticated_user_context(user_email='distributed_tx_test@example.com', user_id='distributed_tx_user', environment='test')
        user_id = str(user_context.user_id)
        source_account_id = await postgres.fetchval("\n            INSERT INTO test_accounts (user_id, account_name, balance)\n            VALUES ($1, 'Source Account', 500.00)\n            RETURNING id\n        ", user_id)
        dest_account_id = await postgres.fetchval("\n            INSERT INTO test_accounts (user_id, account_name, balance)\n            VALUES ($1, 'Destination Account', 200.00)\n            RETURNING id\n        ", user_id)
        transfer_amount = 150.0
        transaction_id = f'transfer_{source_account_id}_{dest_account_id}_{int(time.time())}'
        async with transaction_manager.create_transaction_context(transaction_id, 'SERIALIZABLE') as ctx:
            source_balance = await ctx.fetch_operation('check_balance', {'account_id': source_account_id}, 'SELECT balance FROM test_accounts WHERE id = $1 FOR UPDATE', source_account_id)
            if not source_balance or source_balance[0]['balance'] < transfer_amount:
                raise ValueError('Insufficient funds for transfer')
            await ctx.execute_operation('account_debit', {'account_id': source_account_id, 'amount': transfer_amount}, 'UPDATE test_accounts SET balance = balance - $1, updated_at = NOW() WHERE id = $2', transfer_amount, source_account_id)
            await ctx.execute_operation('account_credit', {'account_id': dest_account_id, 'amount': transfer_amount}, 'UPDATE test_accounts SET balance = balance + $1, updated_at = NOW() WHERE id = $2', transfer_amount, dest_account_id)
            await ctx.execute_operation('log_transfer', {'from_account': source_account_id, 'to_account': dest_account_id, 'amount': transfer_amount}, "INSERT INTO test_transactions (transaction_id, from_account_id, to_account_id, amount, transaction_type, status)\n                   VALUES ($1, $2, $3, $4, 'transfer', 'completed')", transaction_id, source_account_id, dest_account_id, transfer_amount)
            await ctx.execute_operation('audit_log', {'transaction_type': 'transfer', 'details': {'from': source_account_id, 'to': dest_account_id, 'amount': transfer_amount}}, "INSERT INTO test_audit_log (transaction_id, operation_type, operation_data, success)\n                   VALUES ($1, 'transfer', $2, true)", transaction_id, json.dumps({'from_account': source_account_id, 'to_account': dest_account_id, 'amount': float(transfer_amount)}))
        final_source_balance = await postgres.fetchval('SELECT balance FROM test_accounts WHERE id = $1', source_account_id)
        final_dest_balance = await postgres.fetchval('SELECT balance FROM test_accounts WHERE id = $1', dest_account_id)
        assert final_source_balance == 350.0, 'Source account balance incorrect after transfer'
        assert final_dest_balance == 350.0, 'Destination account balance incorrect after transfer'
        transfer_record = await postgres.fetchrow('SELECT * FROM test_transactions WHERE transaction_id = $1', transaction_id)
        assert transfer_record is not None
        assert transfer_record['status'] == 'completed'
        assert transfer_record['amount'] == transfer_amount
        audit_records = await postgres.fetch('SELECT * FROM test_audit_log WHERE transaction_id = $1', transaction_id)
        assert len(audit_records) >= 1
        assert all((record['success'] for record in audit_records))
        tx_history = [tx for tx in transaction_manager.transaction_history if tx['transaction_id'] == transaction_id]
        assert len(tx_history) == 1
        assert tx_history[0]['state'] == 'committed'
        assert tx_history[0]['operations_count'] == 5
        logger.info(' PASS:  Distributed transaction coordination test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_deadlock_detection_and_recovery(self, real_services_fixture, transaction_manager):
        """Test deadlock detection and automatic recovery mechanisms."""
        postgres = real_services_fixture['postgres']
        user_context = await create_authenticated_user_context(user_email='deadlock_test@example.com', user_id='deadlock_test_user', environment='test')
        user_id = str(user_context.user_id)
        account_a_id = await postgres.fetchval("\n            INSERT INTO test_accounts (user_id, account_name, balance)\n            VALUES ($1, 'Account A', 1000.00)\n            RETURNING id\n        ", user_id)
        account_b_id = await postgres.fetchval("\n            INSERT INTO test_accounts (user_id, account_name, balance)\n            VALUES ($1, 'Account B', 1000.00)\n            RETURNING id\n        ", user_id)
        deadlock_detected = False
        successful_operations = []

        async def transaction_a_to_b():
            """Transaction: Transfer from A to B, then update A again."""
            nonlocal deadlock_detected, successful_operations
            tx_id = f'deadlock_test_a_to_b_{int(time.time() * 1000)}'
            try:
                async with transaction_manager.create_transaction_context(tx_id, 'SERIALIZABLE') as ctx:
                    await ctx.execute_operation('lock_account_a', {'account_id': account_a_id}, 'SELECT balance FROM test_accounts WHERE id = $1 FOR UPDATE', account_a_id)
                    await asyncio.sleep(0.1)
                    await ctx.execute_operation('lock_account_b', {'account_id': account_b_id}, 'SELECT balance FROM test_accounts WHERE id = $1 FOR UPDATE', account_b_id)
                    await ctx.execute_operation('transfer_a_to_b', {'from': account_a_id, 'to': account_b_id, 'amount': 50.0}, 'UPDATE test_accounts SET balance = balance - 50.00 WHERE id = $1', account_a_id)
                    await ctx.execute_operation('credit_b_from_a', {'account_id': account_b_id, 'amount': 50.0}, 'UPDATE test_accounts SET balance = balance + 50.00 WHERE id = $1', account_b_id)
                    successful_operations.append('a_to_b')
            except Exception as e:
                if 'deadlock' in str(e).lower():
                    deadlock_detected = True
                    logger.info('Deadlock detected in transaction A->B')
                raise

        async def transaction_b_to_a():
            """Transaction: Transfer from B to A, then update B again."""
            nonlocal deadlock_detected, successful_operations
            tx_id = f'deadlock_test_b_to_a_{int(time.time() * 1000)}'
            try:
                async with transaction_manager.create_transaction_context(tx_id, 'SERIALIZABLE') as ctx:
                    await ctx.execute_operation('lock_account_b', {'account_id': account_b_id}, 'SELECT balance FROM test_accounts WHERE id = $1 FOR UPDATE', account_b_id)
                    await asyncio.sleep(0.1)
                    await ctx.execute_operation('lock_account_a', {'account_id': account_a_id}, 'SELECT balance FROM test_accounts WHERE id = $1 FOR UPDATE', account_a_id)
                    await ctx.execute_operation('transfer_b_to_a', {'from': account_b_id, 'to': account_a_id, 'amount': 75.0}, 'UPDATE test_accounts SET balance = balance - 75.00 WHERE id = $1', account_b_id)
                    await ctx.execute_operation('credit_a_from_b', {'account_id': account_a_id, 'amount': 75.0}, 'UPDATE test_accounts SET balance = balance + 75.00 WHERE id = $1', account_a_id)
                    successful_operations.append('b_to_a')
            except Exception as e:
                if 'deadlock' in str(e).lower():
                    deadlock_detected = True
                    logger.info('Deadlock detected in transaction B->A')
                raise
        results = await asyncio.gather(transaction_manager.execute_with_retry(transaction_a_to_b), transaction_manager.execute_with_retry(transaction_b_to_a), return_exceptions=True)
        exceptions_caught = [r for r in results if isinstance(r, Exception)]
        assert len(successful_operations) >= 1, 'No transactions completed successfully'
        final_balance_a = await postgres.fetchval('SELECT balance FROM test_accounts WHERE id = $1', account_a_id)
        final_balance_b = await postgres.fetchval('SELECT balance FROM test_accounts WHERE id = $1', account_b_id)
        total_balance = final_balance_a + final_balance_b
        assert total_balance == 2000.0, f'Total balance inconsistent: {total_balance}'
        retry_transactions = [tx for tx in transaction_manager.transaction_history if 'deadlock_test' in tx['transaction_id']]
        assert len(retry_transactions) >= 2, 'Deadlock retry mechanism not working'
        committed_transactions = [tx for tx in retry_transactions if tx['state'] == 'committed']
        assert len(committed_transactions) >= 1, 'No transactions committed after deadlock recovery'
        logger.info(' PASS:  Deadlock detection and recovery test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_compensation_transaction_execution(self, real_services_fixture, transaction_manager):
        """Test compensation transaction patterns for failed complex operations."""
        postgres = real_services_fixture['postgres']
        user_context = await create_authenticated_user_context(user_email='compensation_test@example.com', user_id='compensation_test_user', environment='test')
        user_id = str(user_context.user_id)
        account_ids = []
        for i in range(3):
            account_id = await postgres.fetchval('\n                INSERT INTO test_accounts (user_id, account_name, balance)\n                VALUES ($1, $2, 1000.00)\n                RETURNING id\n            ', user_id, f'Account {i + 1}')
            account_ids.append(account_id)
        complex_transaction_id = f'complex_business_tx_{int(time.time())}'
        operations_performed = []
        try:
            async with transaction_manager.create_transaction_context(complex_transaction_id) as ctx:
                await ctx.execute_operation('account_debit', {'account_id': account_ids[0], 'amount': 200.0}, 'UPDATE test_accounts SET balance = balance - $1 WHERE id = $2', 200.0, account_ids[0])
                operations_performed.append({'type': 'account_debit', 'operation_data': {'account_id': account_ids[0], 'amount': 200.0}})
                await ctx.execute_operation('account_credit', {'account_id': account_ids[1], 'amount': 150.0}, 'UPDATE test_accounts SET balance = balance + $1 WHERE id = $2', 150.0, account_ids[1])
                operations_performed.append({'type': 'account_credit', 'operation_data': {'account_id': account_ids[1], 'amount': 150.0}})
                await ctx.execute_operation('account_credit', {'account_id': account_ids[2], 'amount': 50.0}, 'UPDATE test_accounts SET balance = balance + $1 WHERE id = $2', 50.0, account_ids[2])
                operations_performed.append({'type': 'account_credit', 'operation_data': {'account_id': account_ids[2], 'amount': 50.0}})
                await ctx.execute_operation('invalid_operation', {'account_id': account_ids[0], 'amount': 5000.0}, 'UPDATE test_accounts SET balance = balance - $1 WHERE id = $2 AND balance >= $1', 5000.0, account_ids[0])
        except Exception as e:
            logger.info(f'Complex transaction failed as expected: {e}')
            compensation_result = await transaction_manager.execute_compensation_transaction(complex_transaction_id, operations_performed)
            assert compensation_result['compensation_success'] is True
            assert len(compensation_result['compensation_results']) == len(operations_performed)
            for i, comp_result in enumerate(compensation_result['compensation_results']):
                assert comp_result['success'] is True
                original_op = operations_performed[-(i + 1)]
                assert comp_result['operation']['type'] == original_op['type']
        for account_id in account_ids:
            final_balance = await postgres.fetchval('SELECT balance FROM test_accounts WHERE id = $1', account_id)
            assert final_balance == 1000.0, f'Account {account_id} balance not restored: {final_balance}'
        failed_tx = next((tx for tx in transaction_manager.transaction_history if tx['transaction_id'] == complex_transaction_id), None)
        assert failed_tx is not None
        assert failed_tx['state'] == 'rolled_back'
        compensation_tx = next((tx for tx in transaction_manager.transaction_history if tx['transaction_id'].startswith('compensation_')), None)
        assert compensation_tx is not None
        assert compensation_tx['state'] == 'committed'
        logger.info(' PASS:  Compensation transaction execution test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_transaction_isolation(self, real_services_fixture, transaction_manager):
        """Test transaction isolation levels under concurrent access patterns."""
        postgres = real_services_fixture['postgres']
        user_context = await create_authenticated_user_context(user_email='isolation_test@example.com', user_id='isolation_test_user', environment='test')
        user_id = str(user_context.user_id)
        shared_account_id = await postgres.fetchval("\n            INSERT INTO test_accounts (user_id, account_name, balance)\n            VALUES ($1, 'Shared Account', 1000.00)\n            RETURNING id\n        ", user_id)
        isolation_levels = ['READ_COMMITTED', 'REPEATABLE_READ', 'SERIALIZABLE']
        isolation_results = {}
        for isolation_level in isolation_levels:
            transaction_results = []

            async def concurrent_transaction(tx_index: int, amount: float):
                """Execute concurrent transaction with specified isolation level."""
                tx_id = f'isolation_test_{isolation_level}_{tx_index}_{int(time.time() * 1000)}'
                try:
                    async with transaction_manager.create_transaction_context(tx_id, isolation_level) as ctx:
                        balance_result = await ctx.fetch_operation('read_balance', {'account_id': shared_account_id}, 'SELECT balance FROM test_accounts WHERE id = $1', shared_account_id)
                        current_balance = balance_result[0]['balance'] if balance_result else 0
                        await asyncio.sleep(0.05)
                        new_balance = current_balance + amount
                        await ctx.execute_operation('update_balance', {'account_id': shared_account_id, 'new_balance': new_balance}, 'UPDATE test_accounts SET balance = $1 WHERE id = $2', new_balance, shared_account_id)
                        return {'transaction_id': tx_id, 'success': True, 'initial_balance': float(current_balance), 'amount_added': amount, 'final_balance': float(new_balance), 'isolation_level': isolation_level}
                except Exception as e:
                    return {'transaction_id': tx_id, 'success': False, 'error': str(e), 'isolation_level': isolation_level}
            await postgres.execute('UPDATE test_accounts SET balance = 1000.00 WHERE id = $1', shared_account_id)
            concurrent_tasks = [concurrent_transaction(i, 100.0) for i in range(5)]
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            successful_results = [r for r in results if isinstance(r, dict) and r.get('success')]
            failed_results = [r for r in results if isinstance(r, dict) and (not r.get('success'))]
            final_balance = await postgres.fetchval('SELECT balance FROM test_accounts WHERE id = $1', shared_account_id)
            isolation_results[isolation_level] = {'successful_transactions': len(successful_results), 'failed_transactions': len(failed_results), 'final_balance': float(final_balance), 'expected_balance': 1000.0 + len(successful_results) * 100.0, 'isolation_maintained': final_balance == 1000.0 + len(successful_results) * 100.0, 'transaction_details': successful_results + failed_results}
        for isolation_level, results in isolation_results.items():
            logger.info(f"Isolation level {isolation_level}: {results['successful_transactions']} successful, {results['failed_transactions']} failed, final balance: {results['final_balance']}")
            if isolation_level == 'SERIALIZABLE':
                assert results['isolation_maintained'] is True, f"Serializable isolation failed: expected {results['expected_balance']}, got {results['final_balance']}"
        isolation_transactions = [tx for tx in transaction_manager.transaction_history if 'isolation_test' in tx['transaction_id']]
        assert len(isolation_transactions) >= 10, 'Not all isolation test transactions recorded'
        isolation_stats = {}
        for tx in isolation_transactions:
            level = tx['isolation_level']
            if level not in isolation_stats:
                isolation_stats[level] = {'committed': 0, 'rolled_back': 0}
            isolation_stats[level][tx['state']] += 1
        await postgres.execute("\n            INSERT INTO test_audit_log (transaction_id, operation_type, operation_data, success)\n            VALUES ('isolation_test_summary', 'isolation_level_comparison', $1, true)\n        ", json.dumps(isolation_results))
        logger.info(' PASS:  Concurrent transaction isolation test passed')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
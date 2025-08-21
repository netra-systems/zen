"""
L4 Integration Test: Database Transaction Integrity
Tests database transaction atomicity, consistency, isolation, and durability
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
import random

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.services.database_service import DatabaseService
from netra_backend.app.services.transaction_manager import TransactionManager
from netra_backend.app.services.user_service import UserService
from netra_backend.app.config import settings

# Add project root to path


class TestDatabaseTransactionIntegrityL4:
    """Database transaction integrity testing"""
    
    @pytest.fixture
    async def db_infrastructure(self):
        """Database infrastructure setup"""
        return {
            'db_service': DatabaseService(),
            'tx_manager': TransactionManager(),
            'user_service': UserService(),
            'transaction_log': [],
            'conflict_counter': 0,
            'rollback_counter': 0
        }
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_concurrent_balance_transfers(self, db_infrastructure):
        """Test concurrent balance transfers maintain consistency"""
        
        # Create test accounts
        accounts = {}
        initial_balance = Decimal("1000.00")
        
        for i in range(5):
            account = await db_infrastructure['user_service'].create_account(
                user_id=f"user_{i}",
                initial_balance=initial_balance
            )
            accounts[f"user_{i}"] = account
        
        # Track total money in system
        initial_total = initial_balance * 5
        
        # Perform concurrent transfers
        transfer_tasks = []
        
        async def transfer_money(from_user, to_user, amount):
            try:
                async with db_infrastructure['tx_manager'].begin() as tx:
                    # Read balances
                    from_balance = await tx.read_balance(from_user)
                    to_balance = await tx.read_balance(to_user)
                    
                    # Check sufficient funds
                    if from_balance < amount:
                        await tx.rollback()
                        return {'success': False, 'reason': 'insufficient_funds'}
                    
                    # Perform transfer
                    await tx.update_balance(from_user, from_balance - amount)
                    await tx.update_balance(to_user, to_balance + amount)
                    
                    # Commit
                    await tx.commit()
                    return {'success': True, 'amount': amount}
                    
            except Exception as e:
                db_infrastructure['rollback_counter'] += 1
                return {'success': False, 'reason': str(e)}
        
        # Create 100 random transfers
        for _ in range(100):
            from_user = f"user_{random.randint(0, 4)}"
            to_user = f"user_{random.randint(0, 4)}"
            if from_user != to_user:
                amount = Decimal(str(random.uniform(1, 100)))
                task = asyncio.create_task(transfer_money(from_user, to_user, amount))
                transfer_tasks.append(task)
        
        results = await asyncio.gather(*transfer_tasks)
        
        # Calculate final total
        final_total = Decimal("0")
        for i in range(5):
            balance = await db_infrastructure['user_service'].get_balance(f"user_{i}")
            final_total += balance
        
        # Money should be conserved (no money created or destroyed)
        assert abs(final_total - initial_total) < Decimal("0.01")
        
        # All balances should be non-negative
        for i in range(5):
            balance = await db_infrastructure['user_service'].get_balance(f"user_{i}")
            assert balance >= 0
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_read_write_isolation_levels(self, db_infrastructure):
        """Test different isolation levels prevent dirty reads"""
        
        user_id = "user_isolation"
        
        # Test READ UNCOMMITTED (dirty reads possible)
        async def dirty_read_test():
            async with db_infrastructure['tx_manager'].begin(isolation='READ_UNCOMMITTED') as tx1:
                # Start transaction 1 - update but don't commit
                await tx1.update_data(user_id, {'status': 'processing'})
                
                # Transaction 2 reads uncommitted data
                async with db_infrastructure['tx_manager'].begin(isolation='READ_UNCOMMITTED') as tx2:
                    data = await tx2.read_data(user_id)
                    # Can see uncommitted change
                    assert data['status'] == 'processing'
                
                # Rollback transaction 1
                await tx1.rollback()
        
        # Test READ COMMITTED (no dirty reads)
        async def committed_read_test():
            async with db_infrastructure['tx_manager'].begin(isolation='READ_COMMITTED') as tx1:
                # Start transaction 1 - update but don't commit
                await tx1.update_data(user_id, {'status': 'processing'})
                
                # Transaction 2 reads only committed data
                async with db_infrastructure['tx_manager'].begin(isolation='READ_COMMITTED') as tx2:
                    data = await tx2.read_data(user_id)
                    # Should not see uncommitted change
                    assert data['status'] != 'processing'
                
                await tx1.commit()
        
        # Test SERIALIZABLE (highest isolation)
        async def serializable_test():
            conflicts = 0
            
            async def update_counter():
                nonlocal conflicts
                try:
                    async with db_infrastructure['tx_manager'].begin(isolation='SERIALIZABLE') as tx:
                        current = await tx.read_data(user_id)
                        await asyncio.sleep(0.01)  # Simulate processing
                        await tx.update_data(user_id, {'counter': current.get('counter', 0) + 1})
                        await tx.commit()
                except Exception as e:
                    if 'serialization' in str(e).lower():
                        conflicts += 1
            
            # Run concurrent updates
            tasks = [asyncio.create_task(update_counter()) for _ in range(10)]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Some should conflict in SERIALIZABLE mode
            assert conflicts > 0
        
        await dirty_read_test()
        await committed_read_test()
        await serializable_test()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_deadlock_detection_and_recovery(self, db_infrastructure):
        """Test database deadlock detection and automatic recovery"""
        
        deadlocks_detected = 0
        
        async def create_deadlock_scenario():
            nonlocal deadlocks_detected
            
            # Transaction 1: Lock A then B
            async def tx1():
                try:
                    async with db_infrastructure['tx_manager'].begin() as tx:
                        await tx.lock_row('table_a', 'row_1')
                        await asyncio.sleep(0.1)
                        await tx.lock_row('table_b', 'row_1')
                        await tx.commit()
                except Exception as e:
                    if 'deadlock' in str(e).lower():
                        deadlocks_detected += 1
                        raise
            
            # Transaction 2: Lock B then A (opposite order)
            async def tx2():
                try:
                    async with db_infrastructure['tx_manager'].begin() as tx:
                        await tx.lock_row('table_b', 'row_1')
                        await asyncio.sleep(0.1)
                        await tx.lock_row('table_a', 'row_1')
                        await tx.commit()
                except Exception as e:
                    if 'deadlock' in str(e).lower():
                        deadlocks_detected += 1
                        raise
            
            # Run both concurrently
            results = await asyncio.gather(
                asyncio.create_task(tx1()),
                asyncio.create_task(tx2()),
                return_exceptions=True
            )
            
            return results
        
        # Run deadlock scenario multiple times
        for _ in range(5):
            await create_deadlock_scenario()
        
        # Should detect deadlocks
        assert deadlocks_detected > 0
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_transaction_savepoints_and_nested_rollback(self, db_infrastructure):
        """Test savepoints and nested transaction rollback"""
        
        user_id = "user_savepoint"
        
        async with db_infrastructure['tx_manager'].begin() as tx:
            # Initial update
            await tx.update_data(user_id, {'step': 1, 'data': 'initial'})
            
            # Create savepoint
            savepoint1 = await tx.create_savepoint('sp1')
            
            # More updates
            await tx.update_data(user_id, {'step': 2, 'data': 'updated'})
            
            # Create another savepoint
            savepoint2 = await tx.create_savepoint('sp2')
            
            # Final update
            await tx.update_data(user_id, {'step': 3, 'data': 'final'})
            
            # Rollback to savepoint2 (undoes step 3)
            await tx.rollback_to_savepoint('sp2')
            
            # Verify step 3 was undone
            data = await tx.read_data(user_id)
            assert data['step'] == 2
            
            # Rollback to savepoint1 (undoes step 2)
            await tx.rollback_to_savepoint('sp1')
            
            # Verify step 2 was undone
            data = await tx.read_data(user_id)
            assert data['step'] == 1
            
            # Commit remaining changes
            await tx.commit()
        
        # Verify final state
        final_data = await db_infrastructure['db_service'].read_data(user_id)
        assert final_data['step'] == 1
        assert final_data['data'] == 'initial'
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_bulk_insert_atomicity(self, db_infrastructure):
        """Test atomicity of bulk insert operations"""
        
        # Prepare bulk data
        bulk_data = []
        for i in range(1000):
            bulk_data.append({
                'id': f'item_{i}',
                'value': random.randint(1, 100),
                'timestamp': time.time()
            })
        
        # Add one invalid item to cause failure
        bulk_data.append({
            'id': None,  # Invalid - will cause error
            'value': 'invalid'
        })
        
        # Attempt bulk insert
        try:
            async with db_infrastructure['tx_manager'].begin() as tx:
                await tx.bulk_insert('items', bulk_data)
                await tx.commit()
            assert False, "Should have failed"
        except Exception:
            # Transaction should rollback
            pass
        
        # Verify no partial inserts (all or nothing)
        count = await db_infrastructure['db_service'].count('items')
        assert count == 0  # Nothing should be inserted
        
        # Remove invalid item and retry
        bulk_data = bulk_data[:-1]
        
        async with db_infrastructure['tx_manager'].begin() as tx:
            await tx.bulk_insert('items', bulk_data)
            await tx.commit()
        
        # Now all should be inserted
        count = await db_infrastructure['db_service'].count('items')
        assert count == 1000
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_phantom_read_prevention(self, db_infrastructure):
        """Test prevention of phantom reads in concurrent transactions"""
        
        # Initialize data
        for i in range(10):
            await db_infrastructure['db_service'].insert(
                'products',
                {'id': f'prod_{i}', 'price': 100 * (i + 1), 'category': 'electronics'}
            )
        
        phantom_reads = 0
        
        async def transaction_with_range_query():
            nonlocal phantom_reads
            
            async with db_infrastructure['tx_manager'].begin(isolation='REPEATABLE_READ') as tx:
                # First read - count products in price range
                count1 = await tx.count_where('products', 'price >= 200 AND price <= 500')
                
                # Another transaction inserts new product in range
                async def insert_phantom():
                    async with db_infrastructure['tx_manager'].begin() as tx2:
                        await tx2.insert('products', {
                            'id': f'phantom_{time.time()}',
                            'price': 350,
                            'category': 'electronics'
                        })
                        await tx2.commit()
                
                await insert_phantom()
                
                # Second read - should see same count (no phantom)
                count2 = await tx.count_where('products', 'price >= 200 AND price <= 500')
                
                if count2 != count1:
                    phantom_reads += 1
                
                await tx.commit()
        
        # Run multiple times
        tasks = [asyncio.create_task(transaction_with_range_query()) for _ in range(5)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should prevent phantom reads in REPEATABLE_READ
        assert phantom_reads == 0
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_connection_pool_exhaustion(self, db_infrastructure):
        """Test behavior when connection pool is exhausted"""
        
        max_connections = 10
        db_infrastructure['db_service'].set_max_connections(max_connections)
        
        active_connections = []
        connection_errors = 0
        
        async def hold_connection(duration):
            nonlocal connection_errors
            try:
                conn = await db_infrastructure['db_service'].acquire_connection(timeout=1)
                active_connections.append(conn)
                await asyncio.sleep(duration)
                await db_infrastructure['db_service'].release_connection(conn)
                active_connections.remove(conn)
                return True
            except Exception as e:
                if 'timeout' in str(e).lower() or 'exhausted' in str(e).lower():
                    connection_errors += 1
                return False
        
        # Try to acquire more connections than available
        tasks = [
            asyncio.create_task(hold_connection(2))
            for _ in range(max_connections + 5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Some should fail due to pool exhaustion
        successful = sum(1 for r in results if r)
        assert successful <= max_connections
        assert connection_errors > 0
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_cascade_delete_integrity(self, db_infrastructure):
        """Test cascade delete maintains referential integrity"""
        
        # Create parent-child relationships
        parent_id = "parent_1"
        await db_infrastructure['db_service'].insert('users', {
            'id': parent_id,
            'name': 'Parent User'
        })
        
        # Create child records
        child_ids = []
        for i in range(5):
            child_id = f"child_{i}"
            await db_infrastructure['db_service'].insert('orders', {
                'id': child_id,
                'user_id': parent_id,
                'amount': 100 * (i + 1)
            })
            child_ids.append(child_id)
            
            # Create grandchild records
            for j in range(3):
                await db_infrastructure['db_service'].insert('order_items', {
                    'id': f"item_{i}_{j}",
                    'order_id': child_id,
                    'product': f"product_{j}"
                })
        
        # Delete parent with cascade
        async with db_infrastructure['tx_manager'].begin() as tx:
            await tx.delete_cascade('users', parent_id)
            await tx.commit()
        
        # Verify cascade deletion
        parent_exists = await db_infrastructure['db_service'].exists('users', parent_id)
        assert not parent_exists
        
        # All orders should be deleted
        for child_id in child_ids:
            order_exists = await db_infrastructure['db_service'].exists('orders', child_id)
            assert not order_exists
        
        # All order items should be deleted
        order_items_count = await db_infrastructure['db_service'].count('order_items')
        assert order_items_count == 0
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_transaction_timeout_and_cleanup(self, db_infrastructure):
        """Test transaction timeout and proper cleanup"""
        
        timed_out_transactions = []
        
        async def long_running_transaction():
            try:
                async with db_infrastructure['tx_manager'].begin(timeout=1) as tx:
                    # Start transaction
                    await tx.update_data('test_user', {'status': 'processing'})
                    
                    # Simulate long processing
                    await asyncio.sleep(2)  # Exceeds timeout
                    
                    # This should not execute
                    await tx.update_data('test_user', {'status': 'completed'})
                    await tx.commit()
                    
            except Exception as e:
                if 'timeout' in str(e).lower():
                    timed_out_transactions.append(time.time())
                    raise
        
        # Run multiple long transactions
        tasks = [asyncio.create_task(long_running_transaction()) for _ in range(3)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should timeout
        assert len(timed_out_transactions) == 3
        
        # Verify rollback occurred (status should not be 'completed')
        data = await db_infrastructure['db_service'].read_data('test_user')
        assert data.get('status') != 'completed'
        
        # Verify connections were properly released
        pool_stats = await db_infrastructure['db_service'].get_pool_stats()
        assert pool_stats['active_connections'] == 0
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_write_ahead_logging_durability(self, db_infrastructure):
        """Test write-ahead logging ensures durability"""
        
        # Enable WAL
        await db_infrastructure['db_service'].enable_wal()
        
        # Perform transactions
        committed_data = []
        
        async with db_infrastructure['tx_manager'].begin() as tx:
            for i in range(10):
                data = {'id': f'wal_{i}', 'value': i * 100}
                await tx.insert('wal_test', data)
                committed_data.append(data)
            
            # Commit (writes to WAL first)
            await tx.commit()
        
        # Simulate crash before data reaches main storage
        await db_infrastructure['db_service'].simulate_crash()
        
        # Recover from WAL
        await db_infrastructure['db_service'].recover_from_wal()
        
        # Verify all committed data is recovered
        for data in committed_data:
            recovered = await db_infrastructure['db_service'].read('wal_test', data['id'])
            assert recovered is not None
            assert recovered['value'] == data['value']
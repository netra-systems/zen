"""
Test Database Performance Under Load Integration

Business Value Justification (BVJ):
- Segment: All customer segments (platform foundation)
- Business Goal: Ensure database scalability for customer growth
- Value Impact: Database bottlenecks cause widespread service degradation
- Strategic Impact: Database performance enables enterprise customer acquisition

CRITICAL REQUIREMENTS:
- Tests real database performance under concurrent load
- Validates connection pooling, query optimization, transaction handling
- Uses real PostgreSQL and Redis instances, NO MOCKS
- Ensures performance SLAs for different customer tiers
"""
import pytest
import asyncio
import time
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import uuid
from concurrent.futures import ThreadPoolExecutor
import asyncpg
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.database import DatabaseTestHelper
from test_framework.ssot.isolated_test_helper import IsolatedTestHelper
from shared.isolated_environment import get_env
from netra_backend.app.database.postgresql_pool_manager import PostgreSQLPoolManager as ConnectionPoolManager
from netra_backend.app.db.query_optimizer import QueryOptimizer
from netra_backend.app.db.transaction_manager import TransactionManager
from netra_backend.app.db.performance_monitor import DatabasePerformanceMonitor

class DatabasePerformanceUnderLoadIntegrationTests(SSotBaseTestCase):
    """
    Test database performance under realistic load conditions.
    
    Tests critical database scenarios that impact customer experience:
    - High concurrency user operations (logins, data access)
    - Bulk data processing (analytics, reporting)
    - Transaction integrity under load
    - Connection pool efficiency and scaling
    """

    def setup_method(self):
        """Set up test environment with real database connections"""
        super().setup_method() if hasattr(super(), 'setup_method') else None
        self.env = get_env()
        self.db_helper = DatabaseTestHelper()
        self.isolated_helper = IsolatedTestHelper()
        self.test_prefix = f'db_perf_{uuid.uuid4().hex[:8]}'
        self.pool_manager = ConnectionPoolManager()
        self.query_optimizer = QueryOptimizer()
        self.transaction_manager = TransactionManager()
        self.performance_monitor = DatabasePerformanceMonitor()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_pool_performance_under_concurrent_load(self):
        """
        Test connection pool performance with high concurrent access.
        
        BUSINESS CRITICAL: Connection pool bottlenecks cause response time
        degradation affecting all customers simultaneously.
        """
        pool_config = {'min_connections': 5, 'max_connections': 50, 'connection_timeout': 10, 'idle_timeout': 300, 'max_queries_per_connection': 1000}
        await self.pool_manager.configure_pool(pool_config, test_prefix=self.test_prefix)
        async with self.db_helper.get_connection() as conn:
            await conn.execute(f'\n                CREATE TABLE IF NOT EXISTS {self.test_prefix}_concurrent_test (\n                    id SERIAL PRIMARY KEY,\n                    user_id VARCHAR(50),\n                    operation_type VARCHAR(30),\n                    data JSONB,\n                    created_at TIMESTAMP DEFAULT NOW()\n                )\n            ')
            await conn.execute(f'\n                CREATE INDEX IF NOT EXISTS idx_{self.test_prefix}_user_id \n                ON {self.test_prefix}_concurrent_test(user_id)\n            ')
        workload_scenarios = [{'scenario': 'user_login_burst', 'concurrent_operations': 20, 'operations_per_worker': 10, 'operation_type': 'SELECT'}, {'scenario': 'data_insertion_load', 'concurrent_operations': 15, 'operations_per_worker': 20, 'operation_type': 'INSERT'}, {'scenario': 'mixed_read_write', 'concurrent_operations': 25, 'operations_per_worker': 8, 'operation_type': 'MIXED'}]
        try:
            for scenario in workload_scenarios:
                print(f"Testing scenario: {scenario['scenario']}")
                monitoring_id = await self.performance_monitor.start_monitoring(monitoring_type='connection_pool', test_prefix=self.test_prefix)
                start_time = time.time()
                tasks = []
                for worker_id in range(scenario['concurrent_operations']):
                    task = self._execute_database_workload(worker_id=worker_id, operations_count=scenario['operations_per_worker'], operation_type=scenario['operation_type'], table_name=f'{self.test_prefix}_concurrent_test')
                    tasks.append(task)
                results = await asyncio.gather(*tasks, return_exceptions=True)
                end_time = time.time()
                total_duration = end_time - start_time
                successful_workers = [r for r in results if isinstance(r, dict) and r.get('success')]
                failed_workers = [r for r in results if isinstance(r, Exception) or (isinstance(r, dict) and (not r.get('success')))]
                success_rate = len(successful_workers) / len(results)
                assert success_rate >= 0.9, f"Success rate too low for {scenario['scenario']}: {success_rate:.2%}"
                if successful_workers:
                    response_times = [w['avg_response_time_ms'] for w in successful_workers]
                    avg_response_time = sum(response_times) / len(response_times)
                    max_response_time = max(response_times)
                    if scenario['operation_type'] == 'SELECT':
                        assert avg_response_time < 100, f'SELECT avg response time too high: {avg_response_time}ms'
                        assert max_response_time < 500, f'SELECT max response time too high: {max_response_time}ms'
                    elif scenario['operation_type'] == 'INSERT':
                        assert avg_response_time < 200, f'INSERT avg response time too high: {avg_response_time}ms'
                        assert max_response_time < 1000, f'INSERT max response time too high: {max_response_time}ms'
                    else:
                        assert avg_response_time < 150, f'MIXED avg response time too high: {avg_response_time}ms'
                pool_stats = await self.performance_monitor.stop_monitoring(monitoring_id)
                assert pool_stats.peak_active_connections <= pool_config['max_connections']
                assert pool_stats.connection_wait_time_ms < 1000, 'Connection wait time too high'
                assert pool_stats.connection_errors == 0, f'Connection errors occurred: {pool_stats.connection_errors}'
                utilization_rate = pool_stats.peak_active_connections / pool_config['max_connections']
                if scenario['concurrent_operations'] > 10:
                    assert utilization_rate > 0.3, f'Pool underutilized: {utilization_rate:.2%}'
                await asyncio.sleep(2)
        finally:
            await self.db_helper.cleanup_test_data(self.test_prefix)

    async def _execute_database_workload(self, worker_id: int, operations_count: int, operation_type: str, table_name: str) -> Dict[str, Any]:
        """Execute database workload for a single worker"""
        try:
            response_times = []
            operations_completed = 0
            async with self.pool_manager.get_connection() as conn:
                for op_num in range(operations_count):
                    start_time = time.time()
                    if operation_type == 'SELECT':
                        await conn.fetch(f'SELECT * FROM {table_name} WHERE user_id = $1 LIMIT 10', f'user_{worker_id}_{op_num}')
                    elif operation_type == 'INSERT':
                        await conn.execute(f'INSERT INTO {table_name} (user_id, operation_type, data) VALUES ($1, $2, $3)', f'user_{worker_id}_{op_num}', 'test_operation', {'worker_id': worker_id, 'operation_num': op_num})
                    elif operation_type == 'MIXED':
                        if op_num % 3 == 0:
                            await conn.execute(f'INSERT INTO {table_name} (user_id, operation_type, data) VALUES ($1, $2, $3)', f'user_{worker_id}_{op_num}', 'mixed_operation', {'timestamp': time.time()})
                        else:
                            await conn.fetch(f'SELECT COUNT(*) FROM {table_name} WHERE user_id LIKE $1', f'user_{worker_id}%')
                    end_time = time.time()
                    response_times.append((end_time - start_time) * 1000)
                    operations_completed += 1
                    await asyncio.sleep(random.uniform(0.001, 0.01))
            return {'success': True, 'worker_id': worker_id, 'operations_completed': operations_completed, 'avg_response_time_ms': sum(response_times) / len(response_times) if response_times else 0, 'max_response_time_ms': max(response_times) if response_times else 0, 'min_response_time_ms': min(response_times) if response_times else 0}
        except Exception as e:
            return {'success': False, 'worker_id': worker_id, 'error': str(e), 'operations_completed': operations_completed}

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_query_optimization_under_load(self):
        """
        Test query optimization effectiveness under high query load.
        
        BUSINESS CRITICAL: Inefficient queries cause cascading performance
        issues affecting customer responsiveness and satisfaction.
        """
        async with self.db_helper.get_connection() as conn:
            await conn.execute(f'\n                CREATE TABLE IF NOT EXISTS {self.test_prefix}_query_test (\n                    id SERIAL PRIMARY KEY,\n                    user_id UUID,\n                    account_id VARCHAR(50),\n                    event_type VARCHAR(30),\n                    event_data JSONB,\n                    amount DECIMAL(10,2),\n                    created_at TIMESTAMP DEFAULT NOW(),\n                    updated_at TIMESTAMP DEFAULT NOW()\n                )\n            ')
            print('Inserting test data for query optimization testing...')
            batch_size = 1000
            total_records = 10000
            for batch_start in range(0, total_records, batch_size):
                batch_data = []
                for i in range(batch_start, min(batch_start + batch_size, total_records)):
                    batch_data.append((f'user_{i % 1000}', f'account_{i % 100}', ['login', 'purchase', 'view', 'download'][i % 4], {'session_id': f'session_{i}', 'value': i}, round(random.uniform(1.0, 1000.0), 2)))
                await conn.executemany(f'\n                    INSERT INTO {self.test_prefix}_query_test \n                    (user_id, account_id, event_type, event_data, amount)\n                    VALUES ($1, $2, $3, $4, $5)\n                ', batch_data)
        index_configs = [{'name': f'idx_{self.test_prefix}_user_id', 'sql': f'CREATE INDEX IF NOT EXISTS idx_{self.test_prefix}_user_id ON {self.test_prefix}_query_test(user_id)'}, {'name': f'idx_{self.test_prefix}_account_event', 'sql': f'CREATE INDEX IF NOT EXISTS idx_{self.test_prefix}_account_event ON {self.test_prefix}_query_test(account_id, event_type)'}, {'name': f'idx_{self.test_prefix}_created_at', 'sql': f'CREATE INDEX IF NOT EXISTS idx_{self.test_prefix}_created_at ON {self.test_prefix}_query_test(created_at)'}, {'name': f'idx_{self.test_prefix}_amount', 'sql': f'CREATE INDEX IF NOT EXISTS idx_{self.test_prefix}_amount ON {self.test_prefix}_query_test(amount)'}]
        async with self.db_helper.get_connection() as conn:
            for index_config in index_configs:
                await conn.execute(index_config['sql'])
        query_patterns = [{'name': 'user_activity_lookup', 'query': f'SELECT * FROM {self.test_prefix}_query_test WHERE user_id = $1 ORDER BY created_at DESC LIMIT 50', 'params': ['user_500'], 'expected_max_time_ms': 50}, {'name': 'account_summary', 'query': f'SELECT account_id, event_type, COUNT(*), SUM(amount) FROM {self.test_prefix}_query_test WHERE account_id = $1 GROUP BY account_id, event_type', 'params': ['account_50'], 'expected_max_time_ms': 100}, {'name': 'time_range_analysis', 'query': f"SELECT DATE_TRUNC('hour', created_at) as hour, COUNT(*), AVG(amount) FROM {self.test_prefix}_query_test WHERE created_at >= NOW() - INTERVAL '1 hour' GROUP BY hour ORDER BY hour", 'params': [], 'expected_max_time_ms': 200}, {'name': 'complex_analytics', 'query': f'\n                    SELECT \n                        event_type,\n                        COUNT(*) as event_count,\n                        AVG(amount) as avg_amount,\n                        SUM(amount) as total_amount,\n                        MIN(created_at) as first_event,\n                        MAX(created_at) as last_event\n                    FROM {self.test_prefix}_query_test \n                    WHERE amount > $1 \n                    GROUP BY event_type \n                    ORDER BY total_amount DESC\n                ', 'params': [100.0], 'expected_max_time_ms': 300}]
        try:
            for pattern in query_patterns:
                print(f"Testing query pattern: {pattern['name']}")
                monitoring_id = await self.performance_monitor.start_monitoring(monitoring_type='query_performance', test_prefix=self.test_prefix)
                execution_times = []
                concurrent_queries = 10
                query_tasks = []
                for i in range(concurrent_queries):
                    task = self._execute_timed_query(query=pattern['query'], params=pattern['params'], expected_max_time=pattern['expected_max_time_ms'])
                    query_tasks.append(task)
                query_results = await asyncio.gather(*query_tasks, return_exceptions=True)
                successful_queries = [r for r in query_results if isinstance(r, dict) and r.get('success')]
                failed_queries = [r for r in query_results if isinstance(r, Exception) or (isinstance(r, dict) and (not r.get('success')))]
                success_rate = len(successful_queries) / len(query_results)
                assert success_rate >= 0.95, f"Query success rate too low for {pattern['name']}: {success_rate:.2%}"
                if successful_queries:
                    execution_times = [q['execution_time_ms'] for q in successful_queries]
                    avg_execution_time = sum(execution_times) / len(execution_times)
                    max_execution_time = max(execution_times)
                    min_execution_time = min(execution_times)
                    assert avg_execution_time <= pattern['expected_max_time_ms'], f"Average execution time too high for {pattern['name']}: {avg_execution_time}ms"
                    assert max_execution_time <= pattern['expected_max_time_ms'] * 2, f"Max execution time too high for {pattern['name']}: {max_execution_time}ms"
                    if len(execution_times) > 1:
                        import statistics
                        std_dev = statistics.stdev(execution_times)
                        coefficient_of_variation = std_dev / avg_execution_time
                        assert coefficient_of_variation < 0.5, f"Query performance too inconsistent for {pattern['name']}: CV={coefficient_of_variation}"
                query_stats = await self.performance_monitor.stop_monitoring(monitoring_id)
                if hasattr(query_stats, 'index_usage_rate'):
                    assert query_stats.index_usage_rate >= 0.8, f"Index usage too low for {pattern['name']}: {query_stats.index_usage_rate:.2%}"
                await asyncio.sleep(1)
        finally:
            await self.db_helper.cleanup_test_data(self.test_prefix)

    async def _execute_timed_query(self, query: str, params: List[Any], expected_max_time: float) -> Dict[str, Any]:
        """Execute a query and measure its performance"""
        try:
            async with self.pool_manager.get_connection() as conn:
                start_time = time.time()
                if params:
                    result = await conn.fetch(query, *params)
                else:
                    result = await conn.fetch(query)
                end_time = time.time()
                execution_time_ms = (end_time - start_time) * 1000
                return {'success': True, 'execution_time_ms': execution_time_ms, 'result_count': len(result), 'within_expected_time': execution_time_ms <= expected_max_time}
        except Exception as e:
            return {'success': False, 'error': str(e), 'execution_time_ms': 0}

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_transaction_integrity_under_concurrent_load(self):
        """
        Test transaction integrity and isolation under concurrent modifications.
        
        BUSINESS CRITICAL: Transaction failures can cause data corruption
        and inconsistent state affecting customer trust and compliance.
        """
        async with self.db_helper.get_connection() as conn:
            await conn.execute(f'\n                CREATE TABLE IF NOT EXISTS {self.test_prefix}_accounts (\n                    id SERIAL PRIMARY KEY,\n                    account_number VARCHAR(20) UNIQUE,\n                    balance DECIMAL(15,2) DEFAULT 0.00,\n                    created_at TIMESTAMP DEFAULT NOW(),\n                    updated_at TIMESTAMP DEFAULT NOW()\n                )\n            ')
            await conn.execute(f"\n                CREATE TABLE IF NOT EXISTS {self.test_prefix}_transactions (\n                    id SERIAL PRIMARY KEY,\n                    from_account VARCHAR(20),\n                    to_account VARCHAR(20),\n                    amount DECIMAL(15,2),\n                    transaction_type VARCHAR(20),\n                    status VARCHAR(20) DEFAULT 'pending',\n                    created_at TIMESTAMP DEFAULT NOW()\n                )\n            ")
            initial_accounts = [('ACC001', 10000.0), ('ACC002', 5000.0), ('ACC003', 7500.0), ('ACC004', 3000.0), ('ACC005', 15000.0)]
            await conn.executemany(f'\n                INSERT INTO {self.test_prefix}_accounts (account_number, balance)\n                VALUES ($1, $2)\n            ', initial_accounts)
        try:
            transaction_scenarios = [{'name': 'concurrent_balance_updates', 'concurrent_workers': 10, 'transactions_per_worker': 5, 'transaction_type': 'balance_update'}, {'name': 'account_transfers', 'concurrent_workers': 8, 'transactions_per_worker': 3, 'transaction_type': 'transfer'}, {'name': 'mixed_operations', 'concurrent_workers': 12, 'transactions_per_worker': 4, 'transaction_type': 'mixed'}]
            for scenario in transaction_scenarios:
                print(f"Testing transaction scenario: {scenario['name']}")
                async with self.db_helper.get_connection() as conn:
                    initial_balances = await conn.fetch(f'\n                        SELECT account_number, balance \n                        FROM {self.test_prefix}_accounts \n                        ORDER BY account_number\n                    ')
                    initial_total_balance = sum((float(row['balance']) for row in initial_balances))
                transaction_tasks = []
                for worker_id in range(scenario['concurrent_workers']):
                    task = self._execute_transaction_workload(worker_id=worker_id, transaction_count=scenario['transactions_per_worker'], transaction_type=scenario['transaction_type'], accounts_table=f'{self.test_prefix}_accounts', transactions_table=f'{self.test_prefix}_transactions')
                    transaction_tasks.append(task)
                transaction_results = await asyncio.gather(*transaction_tasks, return_exceptions=True)
                successful_workers = [r for r in transaction_results if isinstance(r, dict) and r.get('success')]
                failed_workers = [r for r in transaction_results if isinstance(r, Exception) or (isinstance(r, dict) and (not r.get('success')))]
                success_rate = len(successful_workers) / len(transaction_results)
                assert success_rate >= 0.85, f"Transaction success rate too low for {scenario['name']}: {success_rate:.2%}"
                async with self.db_helper.get_connection() as conn:
                    final_balances = await conn.fetch(f'\n                        SELECT account_number, balance \n                        FROM {self.test_prefix}_accounts \n                        ORDER BY account_number\n                    ')
                    final_total_balance = sum((float(row['balance']) for row in final_balances))
                    if scenario['transaction_type'] in ['transfer', 'mixed']:
                        balance_difference = abs(final_total_balance - initial_total_balance)
                        assert balance_difference < 0.01, f'Total balance changed during transfers: {balance_difference:.2f}'
                    negative_balances = [b for b in final_balances if float(b['balance']) < 0]
                    assert len(negative_balances) == 0, f'Negative balances detected: {negative_balances}'
                    completed_transactions = await conn.fetch(f"\n                        SELECT COUNT(*) as count \n                        FROM {self.test_prefix}_transactions \n                        WHERE status = 'completed'\n                    ")
                    pending_transactions = await conn.fetch(f"\n                        SELECT COUNT(*) as count \n                        FROM {self.test_prefix}_transactions \n                        WHERE status = 'pending'\n                    ")
                    assert pending_transactions[0]['count'] == 0, f"Hanging transactions detected: {pending_transactions[0]['count']}"
                await asyncio.sleep(1)
        finally:
            await self.db_helper.cleanup_test_data(self.test_prefix)

    async def _execute_transaction_workload(self, worker_id: int, transaction_count: int, transaction_type: str, accounts_table: str, transactions_table: str) -> Dict[str, Any]:
        """Execute transaction workload for a single worker"""
        try:
            completed_transactions = 0
            failed_transactions = 0
            for txn_num in range(transaction_count):
                try:
                    async with self.transaction_manager.begin_transaction() as txn:
                        if transaction_type == 'balance_update':
                            account = f'ACC{worker_id % 5 + 1:03d}'
                            amount = random.uniform(-100.0, 500.0)
                            current_balance = await txn.fetchval(f'SELECT balance FROM {accounts_table} WHERE account_number = $1', account)
                            if current_balance + amount >= 0:
                                await txn.execute(f'UPDATE {accounts_table} SET balance = balance + $1, updated_at = NOW() WHERE account_number = $2', amount, account)
                                await txn.execute(f'INSERT INTO {transactions_table} (from_account, amount, transaction_type, status) VALUES ($1, $2, $3, $4)', account, amount, 'balance_update', 'completed')
                        elif transaction_type == 'transfer':
                            accounts = [f'ACC{i + 1:03d}' for i in range(5)]
                            from_account = random.choice(accounts)
                            to_account = random.choice([acc for acc in accounts if acc != from_account])
                            transfer_amount = random.uniform(10.0, 200.0)
                            from_balance = await txn.fetchval(f'SELECT balance FROM {accounts_table} WHERE account_number = $1', from_account)
                            if from_balance >= transfer_amount:
                                await txn.execute(f'UPDATE {accounts_table} SET balance = balance - $1, updated_at = NOW() WHERE account_number = $2', transfer_amount, from_account)
                                await txn.execute(f'UPDATE {accounts_table} SET balance = balance + $1, updated_at = NOW() WHERE account_number = $2', transfer_amount, to_account)
                                await txn.execute(f'INSERT INTO {transactions_table} (from_account, to_account, amount, transaction_type, status) VALUES ($1, $2, $3, $4, $5)', from_account, to_account, transfer_amount, 'transfer', 'completed')
                        elif transaction_type == 'mixed':
                            if txn_num % 2 == 0:
                                account = f'ACC{worker_id % 5 + 1:03d}'
                                amount = random.uniform(10.0, 100.0)
                                await txn.execute(f'UPDATE {accounts_table} SET balance = balance + $1, updated_at = NOW() WHERE account_number = $2', amount, account)
                            else:
                                await txn.fetch(f'SELECT account_number, balance FROM {accounts_table} ORDER BY balance DESC LIMIT 3')
                    completed_transactions += 1
                except Exception as txn_error:
                    failed_transactions += 1
                    print(f'Transaction failed for worker {worker_id}: {txn_error}')
                await asyncio.sleep(random.uniform(0.001, 0.01))
            return {'success': True, 'worker_id': worker_id, 'completed_transactions': completed_transactions, 'failed_transactions': failed_transactions, 'success_rate': completed_transactions / transaction_count if transaction_count > 0 else 0}
        except Exception as e:
            return {'success': False, 'worker_id': worker_id, 'error': str(e), 'completed_transactions': completed_transactions, 'failed_transactions': failed_transactions}
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
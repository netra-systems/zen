"""Database Consistency Fixtures - E2E Testing Support

Business Value Justification (BVJ):
- Segment: All customer segments (Free, Early, Mid, Enterprise)
- Business Goal: Ensure atomic cross-service operations prevent data corruption
- Value Impact: Prevents data inconsistencies causing support tickets and churn
- Revenue Impact: Prevents $50K+ revenue loss from data corruption incidents

This module provides fixtures for testing database consistency across services,
ensuring atomic transactions and proper data synchronization.

CRITICAL: Following CLAUDE.md principles - uses real services, no mocks.
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

import asyncpg
import httpx

from shared.isolated_environment import IsolatedEnvironment
from tests.e2e.database_sync_fixtures import create_test_user_data


@dataclass
class TransactionResult:
    """Result of a database transaction."""
    success: bool
    transaction_id: str
    operations_count: int
    execution_time_ms: float
    services_involved: List[str]
    error: Optional[str] = None
    rollback_required: bool = False
    data_snapshot: Optional[Dict[str, Any]] = None


@dataclass 
class ConsistencyCheckResult:
    """Result of a consistency check across services."""
    consistent: bool
    services_checked: List[str]
    inconsistencies: List[Dict[str, Any]]
    check_time_ms: float
    timestamp: str


class DatabaseConsistencyTester:
    """
    Tests database consistency across Auth, Backend, and WebSocket services.
    
    Key responsibilities:
    - Execute atomic cross-service transactions
    - Validate data consistency between services
    - Test rollback scenarios
    - Monitor transaction performance
    """
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self._connections: Dict[str, asyncpg.Connection] = {}
        self._http_client: Optional[httpx.AsyncClient] = None
        self.transaction_log: List[TransactionResult] = []
        self.consistency_log: List[ConsistencyCheckResult] = []
        
        # Database connection strings
        self.auth_db_url = self.env.get("AUTH_DATABASE_URL")
        self.main_db_url = self.env.get("DATABASE_URL") 
        self.redis_url = self.env.get("REDIS_URL", "redis://localhost:6381")
        
        # Service endpoints
        self.auth_service_url = self.env.get("AUTH_SERVICE_URL", "http://localhost:8081")
        self.backend_service_url = self.env.get("BACKEND_SERVICE_URL", "http://localhost:8000")
        self.websocket_url = self.env.get("WEBSOCKET_URL", "ws://localhost:8000/ws")
        
    async def setup_connections(self):
        """Setup database and service connections."""
        try:
            # Setup database connections
            if self.auth_db_url:
                self._connections['auth'] = await asyncpg.connect(self.auth_db_url)
                
            if self.main_db_url:
                self._connections['main'] = await asyncpg.connect(self.main_db_url)
                
            # Setup HTTP client
            self._http_client = httpx.AsyncClient(timeout=30.0)
            
        except Exception as e:
            await self.cleanup_connections()
            raise Exception(f"Failed to setup connections: {e}")
            
    async def cleanup_connections(self):
        """Cleanup all connections."""
        for conn in self._connections.values():
            if conn and not conn.is_closed():
                await conn.close()
                
        if self._http_client:
            await self._http_client.aclose()
            
        self._connections.clear()
        
    async def execute_atomic_transaction(self, 
                                       operations: List[Dict[str, Any]]) -> TransactionResult:
        """
        Execute atomic transaction across multiple services.
        
        Args:
            operations: List of operations to execute atomically
            
        Returns:
            TransactionResult with success status and metrics
        """
        transaction_id = f"txn-{uuid.uuid4().hex[:12]}"
        start_time = time.time()
        services_involved = []
        
        try:
            # Begin transaction in all databases
            auth_txn = None
            main_txn = None
            
            if 'auth' in self._connections:
                auth_txn = self._connections['auth'].transaction()
                await auth_txn.start()
                services_involved.append('auth')
                
            if 'main' in self._connections:
                main_txn = self._connections['main'].transaction()
                await main_txn.start()
                services_involved.append('main')
                
            # Execute operations
            for operation in operations:
                await self._execute_single_operation(operation)
                
            # Commit all transactions
            if auth_txn:
                await auth_txn.commit()
                
            if main_txn:
                await main_txn.commit()
                
            execution_time = (time.time() - start_time) * 1000
            
            result = TransactionResult(
                success=True,
                transaction_id=transaction_id,
                operations_count=len(operations),
                execution_time_ms=execution_time,
                services_involved=services_involved
            )
            
        except Exception as e:
            # Rollback all transactions
            try:
                if auth_txn:
                    await auth_txn.rollback()
                if main_txn:
                    await main_txn.rollback()
            except:
                pass  # Best effort rollback
                
            execution_time = (time.time() - start_time) * 1000
            
            result = TransactionResult(
                success=False,
                transaction_id=transaction_id,
                operations_count=len(operations),
                execution_time_ms=execution_time,
                services_involved=services_involved,
                error=str(e),
                rollback_required=True
            )
            
        self.transaction_log.append(result)
        return result
        
    async def _execute_single_operation(self, operation: Dict[str, Any]):
        """Execute a single database operation."""
        op_type = operation.get('type')
        service = operation.get('service')
        
        if service == 'auth' and 'auth' in self._connections:
            conn = self._connections['auth']
            
            if op_type == 'insert_user':
                await conn.execute(
                    """
                    INSERT INTO auth_users (id, email, full_name, plan_tier, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    operation['data']['id'],
                    operation['data']['email'],
                    operation['data']['full_name'], 
                    operation['data']['plan_tier'],
                    datetime.now(timezone.utc)
                )
                
            elif op_type == 'update_user':
                await conn.execute(
                    """
                    UPDATE auth_users 
                    SET full_name = $2, plan_tier = $3, updated_at = $4
                    WHERE id = $1
                    """,
                    operation['data']['id'],
                    operation['data']['full_name'],
                    operation['data']['plan_tier'],
                    datetime.now(timezone.utc)
                )
                
        elif service == 'main' and 'main' in self._connections:
            conn = self._connections['main']
            
            if op_type == 'insert_user':
                await conn.execute(
                    """
                    INSERT INTO userbase (id, email, full_name, plan_tier, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    operation['data']['id'],
                    operation['data']['email'], 
                    operation['data']['full_name'],
                    operation['data']['plan_tier'],
                    datetime.now(timezone.utc)
                )
                
            elif op_type == 'update_user':
                await conn.execute(
                    """
                    UPDATE userbase 
                    SET full_name = $2, plan_tier = $3, updated_at = $4
                    WHERE id = $1
                    """,
                    operation['data']['id'],
                    operation['data']['full_name'],
                    operation['data']['plan_tier'],
                    datetime.now(timezone.utc)
                )
                
    async def check_data_consistency(self, user_id: str) -> ConsistencyCheckResult:
        """
        Check data consistency across all services for a specific user.
        
        Args:
            user_id: User ID to check consistency for
            
        Returns:
            ConsistencyCheckResult with consistency status and details
        """
        start_time = time.time()
        services_checked = []
        inconsistencies = []
        
        try:
            # Get user data from auth service
            auth_data = None
            if 'auth' in self._connections:
                auth_result = await self._connections['auth'].fetchrow(
                    "SELECT * FROM auth_users WHERE id = $1", user_id
                )
                if auth_result:
                    auth_data = dict(auth_result)
                    services_checked.append('auth')
                    
            # Get user data from main service  
            main_data = None
            if 'main' in self._connections:
                main_result = await self._connections['main'].fetchrow(
                    "SELECT * FROM userbase WHERE id = $1", user_id
                )
                if main_result:
                    main_data = dict(main_result)
                    services_checked.append('main')
                    
            # Compare data consistency
            if auth_data and main_data:
                # Check critical fields
                fields_to_check = ['id', 'email', 'full_name', 'plan_tier']
                
                for field in fields_to_check:
                    auth_value = auth_data.get(field)
                    main_value = main_data.get(field)
                    
                    if auth_value != main_value:
                        inconsistencies.append({
                            'field': field,
                            'auth_value': auth_value,
                            'main_value': main_value,
                            'severity': 'high' if field in ['id', 'email'] else 'medium'
                        })
                        
            elif auth_data and not main_data:
                inconsistencies.append({
                    'field': 'record_existence',
                    'issue': 'User exists in auth but not in main database',
                    'severity': 'critical'
                })
                
            elif main_data and not auth_data:
                inconsistencies.append({
                    'field': 'record_existence', 
                    'issue': 'User exists in main but not in auth database',
                    'severity': 'critical'
                })
                
            check_time = (time.time() - start_time) * 1000
            
            result = ConsistencyCheckResult(
                consistent=len(inconsistencies) == 0,
                services_checked=services_checked,
                inconsistencies=inconsistencies,
                check_time_ms=check_time,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
        except Exception as e:
            check_time = (time.time() - start_time) * 1000
            result = ConsistencyCheckResult(
                consistent=False,
                services_checked=services_checked,
                inconsistencies=[{'error': str(e), 'severity': 'critical'}],
                check_time_ms=check_time,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
        self.consistency_log.append(result)
        return result


async def execute_single_transaction(user_data: Dict[str, Any]) -> TransactionResult:
    """Execute a single cross-service transaction."""
    tester = DatabaseConsistencyTester()
    await tester.setup_connections()
    
    try:
        operations = [
            {
                'type': 'insert_user',
                'service': 'auth',
                'data': user_data
            },
            {
                'type': 'insert_user', 
                'service': 'main',
                'data': user_data
            }
        ]
        
        return await tester.execute_atomic_transaction(operations)
        
    finally:
        await tester.cleanup_connections()


async def execute_concurrent_transactions(user_data_list: List[Dict[str, Any]]) -> List[TransactionResult]:
    """Execute multiple concurrent transactions."""
    tasks = []
    
    for user_data in user_data_list:
        task = execute_single_transaction(user_data)
        tasks.append(task)
        
    return await asyncio.gather(*tasks, return_exceptions=False)


def create_multiple_test_users(count: int) -> List[Dict[str, Any]]:
    """Create multiple test users for concurrent transaction testing."""
    users = []
    
    for i in range(count):
        user_data = create_test_user_data(
            user_id=f"consistency-test-{i:04d}",
            email=f"consistency{i:04d}@example.com",
            tier="free"
        )
        users.append(user_data)
        
    return users
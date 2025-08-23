"""
Database mock implementations.
Consolidates database mocks from across services.
"""

import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock


class MockDatabaseSession:
    """Mock database session with transaction support"""
    
    def __init__(self):
        self.data = {}
        self.operations = []
        self.is_active = True
        self.in_transaction = False
        
    async def execute(self, query, params=None):
        """Mock execute query"""
        operation = {
            "type": "execute",
            "query": str(query),
            "params": params,
            "result": []
        }
        self.operations.append(operation)
        return MagicMock(fetchall=lambda: [], fetchone=lambda: None)
        
    async def get(self, model_class, primary_key):
        """Mock get by primary key"""
        operation = {
            "type": "get", 
            "model": model_class.__name__,
            "primary_key": primary_key
        }
        self.operations.append(operation)
        return None
        
    def add(self, instance):
        """Mock add instance"""
        operation = {
            "type": "add",
            "instance": instance
        }
        self.operations.append(operation)
        
    async def commit(self):
        """Mock commit transaction"""
        if self.in_transaction:
            self.operations.append({"type": "commit"})
            self.in_transaction = False
            
    async def rollback(self):
        """Mock rollback transaction"""
        if self.in_transaction:
            self.operations.append({"type": "rollback"})
            self.in_transaction = False
            
    async def close(self):
        """Mock close session"""
        self.is_active = False
        self.operations.append({"type": "close"})
        
    async def begin(self):
        """Mock begin transaction"""
        self.in_transaction = True
        self.operations.append({"type": "begin"})
        
    def get_operations(self) -> List[Dict[str, Any]]:
        """Get all operations performed"""
        return self.operations.copy()


class MockAsyncDatabaseFactory:
    """Mock async database session factory"""
    
    def __init__(self):
        self.sessions_created = []
        self.session_count = 0
        
    def __call__(self):
        """Create new session"""
        session = MockDatabaseSession()
        session.id = f"session_{self.session_count}"
        self.session_count += 1
        self.sessions_created.append(session)
        return self.create_context_manager(session)
        
    def create_context_manager(self, session):
        """Create async context manager for session"""
        class SessionContextManager:
            def __init__(self, session):
                self.session = session
                
            async def __aenter__(self):
                return self.session
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if exc_type:
                    await self.session.rollback()
                else:
                    await self.session.commit()
                await self.session.close()
                
        return SessionContextManager(session)
        
    def get_created_sessions(self) -> List[MockDatabaseSession]:
        """Get all created sessions"""
        return self.sessions_created.copy()


class MockPostgreSQLConnection:
    """Mock PostgreSQL connection"""
    
    def __init__(self):
        self.queries_executed = []
        self.is_connected = True
        
    async def execute(self, query: str, *args) -> str:
        """Mock execute query"""
        self.queries_executed.append({
            "query": query,
            "args": args,
            "type": "execute"
        })
        return "SELECT 1"
        
    async def executemany(self, query: str, args_list: List) -> str:
        """Mock execute many queries"""
        self.queries_executed.append({
            "query": query,
            "args_list": args_list,
            "type": "executemany"
        })
        return "INSERT 0 1"
        
    async def fetch(self, query: str, *args) -> List[Dict[str, Any]]:
        """Mock fetch results"""
        self.queries_executed.append({
            "query": query,
            "args": args,
            "type": "fetch"
        })
        return []
        
    async def fetchrow(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Mock fetch single row"""
        self.queries_executed.append({
            "query": query,
            "args": args,
            "type": "fetchrow"
        })
        return None
        
    async def fetchval(self, query: str, *args) -> Any:
        """Mock fetch single value"""
        self.queries_executed.append({
            "query": query,
            "args": args,
            "type": "fetchval"
        })
        return None
        
    async def close(self):
        """Mock close connection"""
        self.is_connected = False
        
    def get_executed_queries(self) -> List[Dict[str, Any]]:
        """Get all executed queries"""
        return self.queries_executed.copy()


class MockClickHouseConnection:
    """Mock ClickHouse connection"""
    
    def __init__(self):
        self.queries_executed = []
        self.inserted_data = []
        self.is_connected = True
        
    async def execute(self, query: str) -> List[Dict[str, Any]]:
        """Mock execute query"""
        self.queries_executed.append({
            "query": query,
            "type": "execute"
        })
        return []
        
    async def insert(self, table: str, data: List[Dict[str, Any]]) -> bool:
        """Mock insert data"""
        insert_record = {
            "table": table,
            "data": data,
            "row_count": len(data)
        }
        self.inserted_data.append(insert_record)
        return True
        
    async def select(self, query: str) -> List[Dict[str, Any]]:
        """Mock select query"""
        self.queries_executed.append({
            "query": query,
            "type": "select"
        })
        return []
        
    async def close(self):
        """Mock close connection"""
        self.is_connected = False
        
    def get_executed_queries(self) -> List[Dict[str, Any]]:
        """Get all executed queries"""
        return self.queries_executed.copy()
        
    def get_inserted_data(self) -> List[Dict[str, Any]]:
        """Get all inserted data"""
        return self.inserted_data.copy()


class MockDatabaseManager:
    """Mock database manager with connection pooling"""
    
    def __init__(self):
        self.postgres_pool = []
        self.clickhouse_pool = []
        self.operations = []
        self.connection_count = 0
        
    async def get_postgres_connection(self) -> MockPostgreSQLConnection:
        """Get PostgreSQL connection from pool"""
        connection = MockPostgreSQLConnection()
        connection.id = f"pg_conn_{self.connection_count}"
        self.connection_count += 1
        self.postgres_pool.append(connection)
        self.operations.append({
            "type": "get_postgres_connection",
            "connection_id": connection.id
        })
        return connection
        
    async def get_clickhouse_connection(self) -> MockClickHouseConnection:
        """Get ClickHouse connection from pool"""
        connection = MockClickHouseConnection()
        connection.id = f"ch_conn_{self.connection_count}"
        self.connection_count += 1
        self.clickhouse_pool.append(connection)
        self.operations.append({
            "type": "get_clickhouse_connection",
            "connection_id": connection.id
        })
        return connection
        
    async def execute_postgres_query(
        self, 
        query: str, 
        *args
    ) -> List[Dict[str, Any]]:
        """Execute PostgreSQL query"""
        self.operations.append({
            "type": "execute_postgres_query",
            "query": query,
            "args": args
        })
        return []
        
    async def execute_clickhouse_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute ClickHouse query"""
        self.operations.append({
            "type": "execute_clickhouse_query", 
            "query": query
        })
        return []
        
    async def begin_transaction(self) -> str:
        """Begin database transaction"""
        transaction_id = f"txn_{len(self.operations)}"
        self.operations.append({
            "type": "begin_transaction",
            "transaction_id": transaction_id
        })
        return transaction_id
        
    async def commit_transaction(self, transaction_id: str):
        """Commit database transaction"""
        self.operations.append({
            "type": "commit_transaction",
            "transaction_id": transaction_id
        })
        
    async def rollback_transaction(self, transaction_id: str):
        """Rollback database transaction"""
        self.operations.append({
            "type": "rollback_transaction",
            "transaction_id": transaction_id
        })
        
    async def close_all_connections(self):
        """Close all connections"""
        for conn in self.postgres_pool:
            await conn.close()
        for conn in self.clickhouse_pool:
            await conn.close()
        self.operations.append({"type": "close_all_connections"})
        
    def get_operations(self) -> List[Dict[str, Any]]:
        """Get all operations performed"""
        return self.operations.copy()


class MockRepositoryBase:
    """Mock base repository with CRUD operations"""
    
    def __init__(self):
        self.data = {}
        self.operations = []
        self.next_id = 1
        
    async def create(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock create entity"""
        entity_id = str(self.next_id)
        self.next_id += 1
        entity = {
            "id": entity_id,
            **entity_data,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z"
        }
        self.data[entity_id] = entity
        self.operations.append({
            "type": "create",
            "entity_id": entity_id,
            "data": entity_data
        })
        return entity
        
    async def get_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Mock get entity by ID"""
        self.operations.append({
            "type": "get_by_id",
            "entity_id": entity_id
        })
        return self.data.get(entity_id)
        
    async def update(
        self, 
        entity_id: str, 
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Mock update entity"""
        if entity_id in self.data:
            self.data[entity_id].update(updates)
            self.data[entity_id]["updated_at"] = "2025-01-01T00:00:00Z"
            self.operations.append({
                "type": "update",
                "entity_id": entity_id,
                "updates": updates
            })
            return self.data[entity_id]
        return None
        
    async def delete(self, entity_id: str) -> bool:
        """Mock delete entity"""
        if entity_id in self.data:
            del self.data[entity_id]
            self.operations.append({
                "type": "delete",
                "entity_id": entity_id
            })
            return True
        return False
        
    async def list_all(
        self, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Mock list all entities"""
        self.operations.append({
            "type": "list_all",
            "limit": limit,
            "offset": offset
        })
        all_data = list(self.data.values())
        return all_data[offset:offset + limit]
        
    def get_operations(self) -> List[Dict[str, Any]]:
        """Get all operations performed"""
        return self.operations.copy()
        
    def clear_data(self):
        """Clear all data and operations"""
        self.data.clear()
        self.operations.clear()
        self.next_id = 1
"""
SSOT Async Test Helpers

Provides standardized async test utilities to prevent common async/coroutine
lifecycle issues in integration and unit tests.

CRITICAL: These helpers eliminate the RuntimeWarning about unawaited coroutines
by providing proper async cleanup patterns.

Business Value: Platform/Internal - Test Reliability & Development Velocity
- Prevents flaky tests due to async cleanup issues
- Standardizes async patterns across all test files
- Eliminates RuntimeWarnings that mask real issues

Usage Examples:
1. Async Mock Registry Cleanup:
   ```python
   from test_framework.ssot.async_test_helpers import async_cleanup_registry
   
   @pytest.fixture(autouse=True)
   async def auto_cleanup(self):
       yield
       await async_cleanup_registry(self.mock_registry)
   ```

2. Async Resource Manager:
   ```python
   async with async_resource_context([agent1, agent2, registry]) as resources:
       # Test with resources
       pass
   # All resources cleaned up automatically
   ```

REQUIREMENTS per CLAUDE.md:
- Must handle async cleanup properly without RuntimeWarnings
- Must integrate with existing SSOT test patterns
- Must be compatible with pytest async fixtures
- Must provide clear error logging for debugging

SSOT Patterns Enforced:
- Single source of truth for async test cleanup
- Consistent error handling across all async tests
- Standardized resource lifecycle management
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Protocol, AsyncGenerator, Callable, Awaitable
from unittest.mock import AsyncMock

import pytest


logger = logging.getLogger(__name__)


class AsyncCleanupable(Protocol):
    """Protocol for objects that support async cleanup."""
    
    async def cleanup(self) -> bool:
        """Cleanup the resource asynchronously."""
        ...


class MockRegistryCleanupable(Protocol):
    """Protocol for mock registries that need agent cleanup."""
    
    agents: dict
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent asynchronously."""
        ...


async def async_cleanup_registry(registry: MockRegistryCleanupable) -> None:
    """
    Safely cleanup all agents in a mock registry.
    
    This helper prevents RuntimeWarnings about unawaited coroutines
    by properly awaiting all unregister_agent calls.
    
    Args:
        registry: Mock registry with agents to cleanup
    """
    if not registry or not hasattr(registry, 'agents'):
        return
    
    agent_ids = list(registry.agents.keys())
    cleanup_results = []
    
    for agent_id in agent_ids:
        try:
            result = await registry.unregister_agent(agent_id)
            cleanup_results.append((agent_id, result))
            logger.debug(f"Cleaned up agent {agent_id}: {result}")
        except Exception as e:
            logger.warning(f"Failed to cleanup agent {agent_id}: {e}")
            cleanup_results.append((agent_id, False))
    
    successful_cleanups = sum(1 for _, success in cleanup_results if success)
    logger.debug(f"Registry cleanup: {successful_cleanups}/{len(agent_ids)} agents cleaned up")


async def async_cleanup_resources(*resources: AsyncCleanupable) -> List[bool]:
    """
    Cleanup multiple async resources in parallel.
    
    Args:
        *resources: Objects that implement async cleanup()
        
    Returns:
        List of cleanup success results
    """
    if not resources:
        return []
    
    cleanup_tasks = []
    for resource in resources:
        if resource and hasattr(resource, 'cleanup'):
            cleanup_tasks.append(resource.cleanup())
    
    if not cleanup_tasks:
        return []
    
    try:
        results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        success_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Resource {i} cleanup failed: {result}")
                success_results.append(False)
            else:
                success_results.append(bool(result))
        
        return success_results
        
    except Exception as e:
        logger.error(f"Bulk resource cleanup failed: {e}")
        return [False] * len(cleanup_tasks)


@asynccontextmanager
async def async_resource_context(*resources: Any) -> AsyncGenerator[List[Any], None]:
    """
    Async context manager for automatic resource cleanup.
    
    Usage:
        async with async_resource_context(agent1, agent2, registry) as resources:
            # Use resources
            pass
        # All resources cleaned up automatically
    
    Args:
        *resources: Resources to manage
        
    Yields:
        List of managed resources
    """
    managed_resources = list(resources)
    
    try:
        yield managed_resources
    finally:
        # Cleanup resources that support async cleanup
        cleanupable_resources = [
            r for r in managed_resources 
            if hasattr(r, 'cleanup') or hasattr(r, 'unregister_agent')
        ]
        
        if cleanupable_resources:
            await async_cleanup_resources(*cleanupable_resources)


class AsyncTestFixtureMixin:
    """
    Mixin class providing async test fixture patterns.
    
    Use this mixin with test classes to get standardized async cleanup.
    
    Example:
        class TestMyAsyncFeature(SSotBaseTestCase, AsyncTestFixtureMixin):
            def setup_method(self, method=None):
                super().setup_method(method)
                self.setup_async_resources()
    """
    
    def setup_async_resources(self):
        """Setup async resource tracking."""
        if not hasattr(self, '_async_resources'):
            self._async_resources = []
        if not hasattr(self, '_mock_registries'):
            self._mock_registries = []
    
    def track_async_resource(self, resource: Any):
        """Track a resource for async cleanup."""
        if not hasattr(self, '_async_resources'):
            self._async_resources = []
        self._async_resources.append(resource)
    
    def track_mock_registry(self, registry: MockRegistryCleanupable):
        """Track a mock registry for agent cleanup."""
        if not hasattr(self, '_mock_registries'):
            self._mock_registries = []
        self._mock_registries.append(registry)
    
    async def cleanup_all_async_resources(self):
        """Cleanup all tracked async resources."""
        # Cleanup mock registries first
        if hasattr(self, '_mock_registries'):
            for registry in self._mock_registries:
                await async_cleanup_registry(registry)
        
        # Cleanup general resources
        if hasattr(self, '_async_resources'):
            cleanupable = [r for r in self._async_resources if hasattr(r, 'cleanup')]
            if cleanupable:
                await async_cleanup_resources(*cleanupable)


def create_async_cleanup_fixture(resource_attr_names: List[str]):
    """
    Factory function to create async cleanup fixtures.
    
    Args:
        resource_attr_names: List of attribute names to cleanup
        
    Returns:
        Async fixture function for pytest
    """
    @pytest.fixture(autouse=True)
    async def auto_async_cleanup(self):
        """Auto cleanup fixture for async resources."""
        yield
        
        # Cleanup specified resources
        for attr_name in resource_attr_names:
            if hasattr(self, attr_name):
                resource = getattr(self, attr_name)
                if hasattr(resource, 'agents'):  # Mock registry
                    await async_cleanup_registry(resource)
                elif hasattr(resource, 'cleanup'):  # General async resource
                    try:
                        await resource.cleanup()
                    except Exception as e:
                        logger.warning(f"Failed to cleanup {attr_name}: {e}")
    
    return auto_async_cleanup


# Common async mock patterns
class AsyncMockManager:
    """Helper for creating properly configured async mocks."""
    
    @staticmethod
    def create_agent_mock(**kwargs) -> AsyncMock:
        """
        Create a properly configured async agent mock.
        
        This prevents RuntimeWarnings by providing all expected attributes.
        """
        agent_mock = AsyncMock()
        
        # Set default attributes that agents typically have
        agent_mock.agent_id = kwargs.get('agent_id', 'test_agent_001')
        agent_mock.agent_type = kwargs.get('agent_type', 'test')
        agent_mock.name = kwargs.get('name', 'Test Agent')
        agent_mock.state = kwargs.get('state', 'ready')
        agent_mock.execution_count = kwargs.get('execution_count', 0)
        agent_mock.last_execution_time = kwargs.get('last_execution_time')
        agent_mock.capabilities = kwargs.get('capabilities', [])
        agent_mock.metadata = kwargs.get('metadata', {})
        
        # Mock methods with proper async/sync patterns
        agent_mock.initialize = AsyncMock(return_value=True)
        agent_mock.cleanup = AsyncMock(return_value=True)
        agent_mock.execute = AsyncMock(return_value={'success': True})
        agent_mock.is_available = lambda: agent_mock.state == 'ready'
        agent_mock.get_capabilities = lambda: agent_mock.capabilities.copy()
        
        # WebSocket and context attributes (may be None)
        agent_mock.websocket_bridge = kwargs.get('websocket_bridge')
        agent_mock.execution_engine = kwargs.get('execution_engine')
        agent_mock.set_websocket_bridge = AsyncMock() if kwargs.get('async_websocket', True) else lambda x: None
        agent_mock.set_trace_context = AsyncMock() if kwargs.get('async_trace', True) else lambda x: None
        
        return agent_mock
    
    @staticmethod
    def create_registry_mock(**kwargs) -> AsyncMock:
        """
        Create a properly configured async registry mock.
        """
        registry_mock = AsyncMock()
        
        # Initialize tracking dictionaries
        registry_mock.agents = kwargs.get('agents', {})
        registry_mock.agents_by_type = kwargs.get('agents_by_type', {})
        registry_mock.execution_history = kwargs.get('execution_history', [])
        registry_mock.registered_count = kwargs.get('registered_count', 0)
        
        # Mock async methods
        registry_mock.register_agent = AsyncMock()
        registry_mock.unregister_agent = AsyncMock(return_value=True)
        registry_mock.execute_agent = AsyncMock(return_value={'success': True})
        
        # Mock sync methods
        registry_mock.get_agent = lambda agent_id: registry_mock.agents.get(agent_id)
        registry_mock.get_agents_by_type = lambda agent_type: registry_mock.agents_by_type.get(agent_type, [])
        registry_mock.get_available_agents = lambda agent_type=None: []
        registry_mock.get_registry_stats = lambda: {
            'total_agents': len(registry_mock.agents),
            'agents_by_type': {k: len(v) for k, v in registry_mock.agents_by_type.items()},
            'available_agents': 0,
            'total_executions': len(registry_mock.execution_history),
            'registered_count': registry_mock.registered_count
        }
        
        return registry_mock


class AsyncTestDatabase:
    """
    Async database testing utility providing standardized database operations.
    
    This class provides a unified interface for async database testing operations,
    including transaction management, query execution, and test data cleanup.
    
    Business Value: Platform/Internal - Test Infrastructure Stability
    - Provides consistent async database testing patterns
    - Prevents common async database testing issues
    - Ensures proper cleanup and resource management
    
    Usage:
        helper = AsyncTestDatabase(async_session)
        await helper.execute_query("SELECT * FROM users WHERE id = :id", {"id": 123})
        await helper.cleanup()
    """
    
    def __init__(self, session: 'AsyncSession'):
        """
        Initialize AsyncTestDatabase with an async session.
        
        Args:
            session: SQLAlchemy AsyncSession instance
        """
        self.session = session
        self._test_data_cleanup = []
        self._active_transactions = []
        
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a raw SQL query with parameter binding.
        
        Args:
            query: SQL query string
            params: Query parameters dictionary
            
        Returns:
            Query result
        """
        try:
            from sqlalchemy import text
            result = await self.session.execute(text(query), params or {})
            return result
        except Exception as e:
            logger.error(f"AsyncTestDatabase query execution failed: {e}")
            raise
    
    async def fetch_one(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        Execute query and fetch one result.
        
        Args:
            query: SQL query string
            params: Query parameters dictionary
            
        Returns:
            Single query result or None
        """
        result = await self.execute_query(query, params)
        return result.fetchone()
    
    async def fetch_all(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        """
        Execute query and fetch all results.
        
        Args:
            query: SQL query string
            params: Query parameters dictionary
            
        Returns:
            List of query results
        """
        result = await self.execute_query(query, params)
        return result.fetchall()
    
    async def create_test_user(self, user_data: Dict[str, Any]) -> Any:
        """
        Create a test user in the database.
        
        Args:
            user_data: User data dictionary
            
        Returns:
            Created user result
        """
        try:
            # Basic user creation query
            query = """
                INSERT INTO users (email, full_name, password_hash, is_active, created_at)
                VALUES (:email, :full_name, :password_hash, :is_active, :created_at)
                RETURNING id
            """
            
            result = await self.execute_query(query, user_data)
            user_row = result.fetchone()
            
            if user_row:
                user_id = user_row[0]
                self._track_test_data('user', user_id)
                logger.debug(f"Created test user with ID: {user_id}")
                return user_row
                
        except Exception as e:
            logger.error(f"Failed to create test user: {e}")
            raise
    
    async def create_test_thread(self, thread_data: Dict[str, Any]) -> Any:
        """
        Create a test thread in the database.
        
        Args:
            thread_data: Thread data dictionary
            
        Returns:
            Created thread result
        """
        try:
            query = """
                INSERT INTO threads (id, created_at, metadata_)
                VALUES (:id, :created_at, :metadata_)
                RETURNING id
            """
            
            result = await self.execute_query(query, thread_data)
            thread_row = result.fetchone()
            
            if thread_row:
                thread_id = thread_row[0]
                self._track_test_data('thread', thread_id)
                logger.debug(f"Created test thread with ID: {thread_id}")
                return thread_row
                
        except Exception as e:
            logger.error(f"Failed to create test thread: {e}")
            raise
    
    async def create_test_message(self, message_data: Dict[str, Any]) -> Any:
        """
        Create a test message in the database.
        
        Args:
            message_data: Message data dictionary
            
        Returns:
            Created message result
        """
        try:
            query = """
                INSERT INTO messages (id, thread_id, role, content, created_at)
                VALUES (:id, :thread_id, :role, :content, :created_at)
                RETURNING id
            """
            
            result = await self.execute_query(query, message_data)
            message_row = result.fetchone()
            
            if message_row:
                message_id = message_row[0]
                self._track_test_data('message', message_id)
                logger.debug(f"Created test message with ID: {message_id}")
                return message_row
                
        except Exception as e:
            logger.error(f"Failed to create test message: {e}")
            raise
    
    async def count_records(self, table_name: str, where_clause: str = "", params: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records in a table with optional where clause.
        
        Args:
            table_name: Name of the table
            where_clause: Optional WHERE clause
            params: Query parameters
            
        Returns:
            Record count
        """
        query = f"SELECT COUNT(*) FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        
        result = await self.execute_query(query, params or {})
        count = result.scalar()
        return count or 0
    
    async def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists, False otherwise
        """
        try:
            # PostgreSQL table existence check
            query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = :table_name
                )
            """
            result = await self.execute_query(query, {"table_name": table_name})
            return bool(result.scalar())
        except Exception as e:
            logger.warning(f"Error checking table existence for {table_name}: {e}")
            return False
    
    async def begin_transaction(self):
        """Begin a new database transaction."""
        try:
            transaction = await self.session.begin()
            self._active_transactions.append(transaction)
            return transaction
        except Exception as e:
            logger.error(f"Failed to begin transaction: {e}")
            raise
    
    async def commit_transaction(self, transaction=None):
        """Commit a database transaction."""
        try:
            if transaction:
                await transaction.commit()
                if transaction in self._active_transactions:
                    self._active_transactions.remove(transaction)
            else:
                await self.session.commit()
        except Exception as e:
            logger.error(f"Failed to commit transaction: {e}")
            raise
    
    async def rollback_transaction(self, transaction=None):
        """Rollback a database transaction."""
        try:
            if transaction:
                await transaction.rollback()
                if transaction in self._active_transactions:
                    self._active_transactions.remove(transaction)
            else:
                await self.session.rollback()
        except Exception as e:
            logger.error(f"Failed to rollback transaction: {e}")
            raise
    
    def _track_test_data(self, data_type: str, data_id: Any):
        """Track created test data for cleanup."""
        self._test_data_cleanup.append((data_type, data_id))
    
    async def cleanup_test_data(self):
        """Clean up all tracked test data."""
        cleanup_errors = []
        
        # Clean up in reverse order (messages -> threads -> users)
        for data_type, data_id in reversed(self._test_data_cleanup):
            try:
                if data_type == "message":
                    await self.execute_query("DELETE FROM messages WHERE id = :id", {"id": data_id})
                elif data_type == "thread":
                    await self.execute_query("DELETE FROM threads WHERE id = :id", {"id": data_id})
                elif data_type == "user":
                    await self.execute_query("DELETE FROM users WHERE id = :id", {"id": data_id})
                    
                logger.debug(f"Cleaned up test {data_type} with ID: {data_id}")
                
            except Exception as e:
                cleanup_error = f"Failed to cleanup {data_type} {data_id}: {str(e)}"
                cleanup_errors.append(cleanup_error)
                logger.warning(cleanup_error)
        
        self._test_data_cleanup.clear()
        
        if cleanup_errors:
            logger.warning(f"Test data cleanup had {len(cleanup_errors)} errors")
    
    async def cleanup(self):
        """Clean up all database resources and test data."""
        try:
            # Rollback any active transactions
            for transaction in self._active_transactions[:]:
                try:
                    await transaction.rollback()
                    self._active_transactions.remove(transaction)
                except Exception as e:
                    logger.warning(f"Error rolling back transaction during cleanup: {e}")
            
            # Clean up test data
            await self.cleanup_test_data()
            
            logger.debug("AsyncTestDatabase cleanup completed")
            
        except Exception as e:
            logger.error(f"AsyncTestDatabase cleanup failed: {e}")


# Export all utilities
__all__ = [
    'AsyncCleanupable',
    'MockRegistryCleanupable', 
    'async_cleanup_registry',
    'async_cleanup_resources',
    'async_resource_context',
    'AsyncTestFixtureMixin',
    'create_async_cleanup_fixture',
    'AsyncMockManager',
    'AsyncTestDatabase',
]
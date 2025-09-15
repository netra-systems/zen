"""
Data Access Integration for UserExecutionEngine

This module provides integration between UserExecutionEngine and DataAccessFactory
to enable user-scoped data operations within agent execution contexts.

Implements the three-tier architecture's data isolation requirements:
- UserExecutionContext is passed through to data layer
- All data operations are automatically scoped by user_id
- Complete isolation between users at database and cache levels
- Proper resource cleanup and lifecycle management

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise)
- Business Goal: Complete user data isolation for agent operations
- Value Impact: Zero risk of cross-user data contamination in agent workflows
- Revenue Impact: Critical for Enterprise deployment, enables multi-tenant operations
"""

import asyncio
from typing import Any, Dict, Optional, TYPE_CHECKING
from contextlib import asynccontextmanager

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.data_contexts.user_data_context import (
        UserClickHouseContext, 
        UserRedisContext
    )

from netra_backend.app.factories.data_access_factory import (
    get_clickhouse_factory,
    get_redis_factory,
    get_user_clickhouse_context,
    get_user_redis_context
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DataAccessCapabilities:
    """
    Data access capabilities mixin for UserExecutionEngine.
    
    Provides user-scoped data access methods that automatically include
    user context and ensure complete isolation between different users.
    
    Key Features:
    - Automatic user_id inclusion in all data operations
    - ClickHouse and Redis operations with user-scoped contexts
    - Context managers for proper resource management
    - Integration with DataAccessFactory for factory pattern benefits
    - Comprehensive audit trails for all data operations
    """
    
    def __init__(self, user_context: UserExecutionContext):
        """Initialize data access capabilities with user context."""
        self.user_context = user_context
        self._clickhouse_factory = get_clickhouse_factory()
        self._redis_factory = get_redis_factory()
        logger.debug(f"[DataAccessCapabilities] Initialized for user {user_context.user_id}")
    
    @asynccontextmanager
    async def get_clickhouse_context(self):
        """
        Get user-scoped ClickHouse context for analytics operations.
        
        Usage:
            async with self.get_clickhouse_context() as ch:
                results = await ch.execute("SELECT * FROM events")
        
        Yields:
            UserClickHouseContext: User-scoped ClickHouse context
        """
        async with get_user_clickhouse_context(self.user_context) as context:
            logger.debug(f"[DataAccessCapabilities] ClickHouse context acquired for user {self.user_context.user_id}")
            yield context
    
    @asynccontextmanager 
    async def get_redis_context(self):
        """
        Get user-scoped Redis context for session and cache operations.
        
        Usage:
            async with self.get_redis_context() as redis:
                await redis.set("key", "value")
                value = await redis.get("key")
        
        Yields:
            UserRedisContext: User-scoped Redis context
        """
        async with get_user_redis_context(self.user_context) as context:
            logger.debug(f"[DataAccessCapabilities] Redis context acquired for user {self.user_context.user_id}")
            yield context
    
    async def execute_analytics_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> list:
        """
        Execute analytics query with automatic user context inclusion.
        
        Args:
            query: ClickHouse query to execute
            params: Optional query parameters (user_id will be added automatically)
            
        Returns:
            Query results as list of dictionaries
        """
        async with self.get_clickhouse_context() as ch:
            return await ch.execute(query, params)
    
    async def store_session_data(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Store session data with user namespacing.
        
        Args:
            key: Session key (will be automatically namespaced)
            value: Value to store
            ttl: Time to live in seconds (default: 1 hour)
            
        Returns:
            True if successful
        """
        async with self.get_redis_context() as redis:
            if isinstance(value, dict):
                return await redis.set_json(key, value, ex=ttl)
            else:
                return await redis.set(key, str(value), ex=ttl)
    
    async def get_session_data(self, key: str) -> Optional[Any]:
        """
        Get session data with user namespacing.
        
        Args:
            key: Session key (will be automatically namespaced)
            
        Returns:
            Session data if found, None otherwise
        """
        async with self.get_redis_context() as redis:
            # Try JSON first
            json_data = await redis.get_json(key)
            if json_data is not None:
                return json_data
            
            # Fall back to string
            return await redis.get(key)
    
    async def store_execution_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Store execution metrics in ClickHouse for analytics.
        
        Args:
            metrics: Metrics dictionary to store
        """
        # Add user context to metrics
        enhanced_metrics = {
            **metrics,
            'user_id': self.user_context.user_id,
            'request_id': self.user_context.request_id,
            'thread_id': self.user_context.thread_id,
            'run_id': self.user_context.run_id,
        }
        
        async with self.get_clickhouse_context() as ch:
            await ch.batch_insert('execution_metrics', [enhanced_metrics])
    
    async def get_user_analytics(self, start_date: str, end_date: str) -> list:
        """
        Get analytics data for this user within date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Analytics results for the user
        """
        query = """
        SELECT 
            date,
            count(*) as executions,
            avg(duration_ms) as avg_duration,
            sum(case when success = 1 then 1 else 0 end) as successful_executions
        FROM execution_metrics 
        WHERE user_id = %(user_id)s 
        AND date >= %(start_date)s 
        AND date <= %(end_date)s
        GROUP BY date
        ORDER BY date
        """
        
        params = {
            'user_id': self.user_context.user_id,
            'start_date': start_date,
            'end_date': end_date
        }
        
        return await self.execute_analytics_query(query, params)
    
    async def cleanup_data_contexts(self) -> None:
        """Clean up data access contexts and resources."""
        try:
            # Cleanup user contexts in factories
            await self._clickhouse_factory.cleanup_user_contexts(self.user_context.user_id)
            await self._redis_factory.cleanup_user_contexts(self.user_context.user_id)
            
            logger.debug(f"[DataAccessCapabilities] Cleaned up contexts for user {self.user_context.user_id}")
        except Exception as e:
            logger.warning(f"[DataAccessCapabilities] Error during cleanup: {e}")
    
    def get_data_access_stats(self) -> Dict[str, Any]:
        """Get statistics about data access usage for this user."""
        return {
            'user_id': self.user_context.user_id,
            'clickhouse_stats': asyncio.create_task(self._clickhouse_factory.get_context_stats()),
            'redis_stats': asyncio.create_task(self._redis_factory.get_context_stats())
        }


def add_data_access_capabilities(engine: 'UserExecutionEngine') -> 'DataAccessCapabilities':
    """
    Add data access capabilities to a UserExecutionEngine.
    
    Args:
        engine: UserExecutionEngine instance to enhance
        
    Returns:
        DataAccessCapabilities: Data access methods for the engine
        
    Usage:
        # In UserExecutionEngine initialization or method
        data_access = add_data_access_capabilities(self)
        
        # Use data access capabilities
        async with data_access.get_clickhouse_context() as ch:
            results = await ch.execute("SELECT * FROM events")
    """
    return DataAccessCapabilities(engine.context)


class UserExecutionEngineExtensions:
    """
    Extension methods for UserExecutionEngine that provide data access integration.
    
    This class provides a clean way to extend UserExecutionEngine with data access
    capabilities without modifying the original class directly.
    """
    
    @staticmethod
    def integrate_data_access(engine: 'UserExecutionEngine') -> None:
        """
        Integrate data access capabilities into UserExecutionEngine.
        
        Args:
            engine: UserExecutionEngine instance to integrate with
            
        This method adds data access methods directly to the engine instance:
        - get_clickhouse_context(): Context manager for ClickHouse operations
        - get_redis_context(): Context manager for Redis operations
        - execute_analytics_query(): Direct analytics query execution
        - store_session_data(): Session data storage
        - get_session_data(): Session data retrieval
        """
        # Create data access capabilities instance
        data_access = DataAccessCapabilities(engine.context)
        
        # Add methods to engine instance (monkey patching for clean integration)
        engine.get_clickhouse_context = data_access.get_clickhouse_context
        engine.get_redis_context = data_access.get_redis_context
        engine.execute_analytics_query = data_access.execute_analytics_query
        engine.store_session_data = data_access.store_session_data
        engine.get_session_data = data_access.get_session_data
        engine.store_execution_metrics = data_access.store_execution_metrics
        engine.get_user_analytics = data_access.get_user_analytics
        engine.cleanup_data_contexts = data_access.cleanup_data_contexts
        engine.get_data_access_stats = data_access.get_data_access_stats
        
        # Store reference for cleanup
        engine._data_access_capabilities = data_access
        
        logger.info(f"[UserExecutionEngineExtensions] Data access capabilities integrated for user {engine.context.user_id}")
    
    @staticmethod
    async def cleanup_data_access(engine: 'UserExecutionEngine') -> None:
        """
        Clean up data access capabilities for UserExecutionEngine.
        
        Args:
            engine: UserExecutionEngine instance to clean up
            
        This should be called during engine cleanup to ensure proper
        resource cleanup for data access contexts.
        """
        if hasattr(engine, '_data_access_capabilities'):
            try:
                await engine._data_access_capabilities.cleanup_data_contexts()
            except Exception as e:
                logger.warning(f"[UserExecutionEngineExtensions] Error during data access cleanup: {e}")
            finally:
                # Remove reference
                delattr(engine, '_data_access_capabilities')


# Example usage in agents that need data access
async def example_agent_with_data_access(engine: 'UserExecutionEngine') -> None:
    """
    Example showing how agents can use data access capabilities.
    
    This example demonstrates the proper usage patterns for agents
    that need to access ClickHouse or Redis with user isolation.
    """
    # Ensure data access is integrated
    UserExecutionEngineExtensions.integrate_data_access(engine)
    
    try:
        # Analytics query with automatic user context
        user_events = await engine.execute_analytics_query(
            "SELECT * FROM user_events WHERE created_at >= %(start_date)s",
            {"start_date": "2025-01-01"}
        )
        
        # Session data storage with user namespacing
        await engine.store_session_data(
            "analysis_results",
            {"event_count": len(user_events), "analysis_complete": True}
        )
        
        # Direct context usage for complex operations
        async with engine.get_clickhouse_context() as ch:
            # Multiple queries in same context for efficiency
            summary = await ch.execute("SELECT count(*) as total FROM user_events")
            recent = await ch.execute(
                "SELECT * FROM user_events WHERE created_at >= now() - interval 24 hour"
            )
            
            # Store analysis results
            await ch.batch_insert('analysis_results', [{
                'total_events': summary[0]['total'] if summary else 0,
                'recent_events': len(recent),
                'analysis_timestamp': 'now()'
            }])
        
        async with engine.get_redis_context() as redis:
            # Store temporary analysis state
            await redis.set_json('analysis_state', {
                'status': 'completed',
                'results_stored': True,
                'next_analysis_due': 'tomorrow'
            }, ex=86400)  # 24 hours
    
    finally:
        # Cleanup happens automatically via factory TTL and cleanup tasks
        # But can be done explicitly if needed:
        # await UserExecutionEngineExtensions.cleanup_data_access(engine)
        pass


__all__ = [
    "DataAccessCapabilities",
    "add_data_access_capabilities", 
    "UserExecutionEngineExtensions",
    "example_agent_with_data_access"
]
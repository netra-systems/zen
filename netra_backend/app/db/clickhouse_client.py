"""
ClickHouse Client Compatibility Module - SSOT Import Compatibility
Provides backward compatibility imports for ClickHouse client classes.

This module exists to provide the expected import path for tests and modules
that expect ClickHouseClient to be available from netra_backend.app.db.clickhouse_client.

The actual implementation is in clickhouse.py (SSOT).
"""

import warnings
import logging

logger = logging.getLogger(__name__)

# SSOT imports from the canonical ClickHouse implementation
from netra_backend.app.db.clickhouse import (
    ClickHouseService,
    ClickHouseClient,  # This is an alias for ClickHouseService
    ClickHouseCache,
    NoOpClickHouseClient,
    get_clickhouse_client,
    get_clickhouse_service,
    create_agent_state_history_table,
    insert_agent_state_history,
    ClickHouseManager,
    ClickHouseDatabaseClient
)

# Issue deprecation warning to guide migration to SSOT import
warnings.warn(
    "Import from 'netra_backend.app.db.clickhouse_client' is deprecated. "
    "Use 'from netra_backend.app.db.clickhouse import ClickHouseClient' instead.",
    DeprecationWarning,
    stacklevel=2
)


class ClickHouseDriverCompatAdapter:
    """
    Adapter to provide clickhouse_driver.Client compatibility.
    
    This adapter provides the same interface as clickhouse_driver.Client
    but uses our SSOT ClickHouse implementation internally.
    """
    
    def __init__(self, host='localhost', port=8123, user='default', password='', database='default', **kwargs):
        """Initialize the adapter with clickhouse_driver.Client compatible parameters."""
        logger.info(f"[ClickHouse Adapter] Initializing with host={host}, port={port}, database={database}")
        self.service = ClickHouseService()
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure the service is initialized."""
        if not self._initialized:
            await self.service.initialize()
            self._initialized = True
    
    def execute(self, query, params=None):
        """Execute query synchronously (for backward compatibility).
        
        WARNING: This method attempts to handle both sync and async contexts but may
        not work properly in all scenarios. Consider using async execute_async() instead.
        """
        import asyncio
        
        # Handle both sync and async contexts
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, but this is a sync call
                # Return a Task that the caller must handle properly
                logger.warning("Sync execute() called from async context - returning Task")
                task = asyncio.create_task(self._async_execute(query, params))
                return task
            else:
                # We're not in an async context - safe to run until complete
                return loop.run_until_complete(self._async_execute(query, params))
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self._async_execute(query, params))
    
    async def _async_execute(self, query, params=None):
        """Execute query asynchronously."""
        await self._ensure_initialized()
        return await self.service.execute(query, params)
    
    async def execute_async(self, query, params=None):
        """Execute query asynchronously (recommended method for async contexts)."""
        return await self._async_execute(query, params)
    
    async def disconnect_async(self):
        """Disconnect asynchronously (recommended method for async contexts)."""
        if self._initialized and self.service:
            await self.service.close()
        self._initialized = False
    
    def disconnect(self):
        """Disconnect (for compatibility).
        
        WARNING: This method attempts to handle both sync and async contexts but may
        not work properly in all scenarios. Consider using async disconnect_async() instead.
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, but this is a sync call
                # Return a Task that the caller must handle properly
                logger.warning("Sync disconnect() called from async context - returning Task")
                task = asyncio.create_task(self.service.close())
                return task
            else:
                # We're not in an async context - safe to run until complete
                return loop.run_until_complete(self.service.close())
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self.service.close())


# Provide a factory function that mimics clickhouse_driver.Client
def Client(host='localhost', port=8123, user='default', password='', database='default', **kwargs):
    """Factory function to create a ClickHouse client compatible with clickhouse_driver.Client interface."""
    logger.warning(
        "Using clickhouse_driver compatibility adapter. "
        "Consider migrating to netra_backend.app.db.clickhouse.ClickHouseService for better integration."
    )
    return ClickHouseDriverCompatAdapter(
        host=host, port=port, user=user, password=password, database=database, **kwargs
    )


# Make all classes available for backward compatibility
__all__ = [
    'ClickHouseClient',
    'ClickHouseService', 
    'ClickHouseCache',
    'NoOpClickHouseClient',
    'get_clickhouse_client',
    'get_clickhouse_service',
    'create_agent_state_history_table',
    'insert_agent_state_history',
    'ClickHouseManager',
    'ClickHouseDatabaseClient',
    'Client',  # clickhouse_driver compatibility
    'ClickHouseDriverCompatAdapter'
]
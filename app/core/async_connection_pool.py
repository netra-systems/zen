"""Async connection pooling utilities for resource management."""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Awaitable, Callable, Set, TypeVar

from .exceptions_service import ServiceError
from .error_context import ErrorContext

T = TypeVar('T')


class AsyncConnectionPool:
    """Generic async connection pool."""
    
    def __init__(
        self,
        create_connection: Callable[[], Awaitable[T]],
        close_connection: Callable[[T], Awaitable[None]],
        max_size: int = 10,
        min_size: int = 1
    ):
        self._create_connection = create_connection
        self._close_connection = close_connection
        self._max_size = max_size
        self._min_size = min_size
        self._setup_pool()
    
    def _setup_pool(self):
        """Initialize pool data structures."""
        self._available_connections: asyncio.Queue[T] = asyncio.Queue(maxsize=self._max_size)
        self._active_connections: Set[T] = set()
        self._lock = asyncio.Lock()
        self._closed = False
    
    async def initialize(self):
        """Initialize the connection pool."""
        for _ in range(self._min_size):
            connection = await self._create_connection()
            await self._available_connections.put(connection)
    
    async def _get_available_connection(self) -> T:
        """Get an available connection from pool."""
        try:
            return await asyncio.wait_for(self._available_connections.get(), timeout=5.0)
        except asyncio.TimeoutError:
            return await self._create_new_connection()
    
    async def _create_new_connection(self) -> T:
        """Create new connection if pool isn't full."""
        async with self._lock:
            if len(self._active_connections) < self._max_size:
                return await self._create_connection()
            else:
                return await self._available_connections.get()
    
    def _add_to_active(self, connection: T):
        """Add connection to active set."""
        self._active_connections.add(connection)
    
    def _remove_from_active(self, connection: T):
        """Remove connection from active set."""
        self._active_connections.discard(connection)
    
    async def _return_connection(self, connection: T):
        """Return connection to pool or close if full."""
        if not self._closed:
            try:
                await self._available_connections.put(connection)
            except asyncio.QueueFull:
                await self._close_connection(connection)
    
    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[T, None]:
        """Acquire a connection from the pool."""
        if self._closed:
            raise ServiceError(
                message="Connection pool is closed",
                context=ErrorContext.get_all_context()
            )
        
        connection = None
        try:
            connection = await self._get_available_connection()
            self._add_to_active(connection)
            yield connection
        finally:
            if connection:
                self._remove_from_active(connection)
                await self._return_connection(connection)
    
    async def _close_available_connections(self):
        """Close all available connections."""
        while not self._available_connections.empty():
            try:
                connection = await asyncio.wait_for(
                    self._available_connections.get(), 
                    timeout=1.0
                )
                await self._close_connection(connection)
            except asyncio.TimeoutError:
                break
    
    async def _close_active_connections(self):
        """Close any remaining active connections."""
        for connection in list(self._active_connections):
            await self._close_connection(connection)
        self._active_connections.clear()
    
    async def close(self):
        """Close the connection pool."""
        if self._closed:
            return
        
        self._closed = True
        await self._close_available_connections()
        await self._close_active_connections()
    
    @property
    def active_count(self) -> int:
        """Get number of active connections."""
        return len(self._active_connections)
    
    @property
    def available_count(self) -> int:
        """Get number of available connections."""
        return self._available_connections.qsize()
    
    @property
    def total_count(self) -> int:
        """Get total number of connections."""
        return self.active_count + self.available_count
    
    @property
    def is_closed(self) -> bool:
        """Check if pool is closed."""
        return self._closed
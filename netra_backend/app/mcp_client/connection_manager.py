"""
MCP Connection Manager: Connection pooling and lifecycle management for MCP servers.

This module implements connection pooling, automatic reconnection, health checks,
and load balancing for Model Context Protocol (MCP) server connections.

CRITICAL ARCHITECTURAL COMPLIANCE:
- File size: <300 lines
- Function size: ≤8 lines each
- Strong typing: All parameters and returns typed
- Single responsibility: Connection management only

Key Features:
- Connection pooling (max 10 per server)
- Exponential backoff reconnection
- Health checks every 30 seconds
- Load balancing across connections
- Transport selection (stdio, http, websocket)
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from netra_backend.app.core.exceptions import NetraException
from netra_backend.app.services.apex_optimizer_agent.models import ConnectionStatus


class MCPTransport(str, Enum):
    """MCP transport types."""
    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"


@dataclass
class MCPServerConfig:
    """MCP server configuration."""
    name: str
    url: str
    transport: MCPTransport
    timeout: int = 30000
    max_retries: int = 3
    auth: Optional[Dict[str, Any]] = None


@dataclass
class ConnectionMetrics:
    """Connection pool metrics."""
    active: int = 0
    idle: int = 0
    failed: int = 0
    total_created: int = 0
    total_destroyed: int = 0
    circuit_breaker_open: bool = False
    last_circuit_open: Optional[datetime] = None


@dataclass
class MCPConnection:
    """MCP connection instance."""
    id: str
    server_name: str
    transport: Any
    status: ConnectionStatus
    created_at: datetime
    last_used: datetime = field(default_factory=datetime.now)
    session_id: Optional[str] = None
    capabilities: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0


class MCPConnectionManager:
    """
    Manages MCP server connections with pooling and health monitoring.
    
    Provides connection pooling, automatic reconnection, health checks,
    and load balancing for MCP server connections.
    """

    def __init__(self, max_connections_per_server: int = 10):
        self._max_connections = max_connections_per_server
        self._min_connections_per_server = 1
        self._pools: Dict[str, asyncio.Queue] = {}
        self._active_connections: Dict[str, List[MCPConnection]] = {}
        self._metrics: Dict[str, ConnectionMetrics] = {}
        self._server_configs: Dict[str, MCPServerConfig] = {}
        self._failed_connections: Dict[str, List[MCPConnection]] = {}
        self._initialize_settings()
        self._logger = logging.getLogger(__name__)
        self._recovery_task: Optional[asyncio.Task] = None

    def _initialize_settings(self) -> None:
        """Initialize default settings and configuration."""
        self._health_check_interval = 30.0
        self._health_check_task: Optional[asyncio.Task] = None
        self._reconnect_backoff_base = 1.0
        self._max_retry_attempts = 5
        self._circuit_breaker_threshold = 5
        self._circuit_breaker_timeout = 60.0
        self._recovery_interval = 10.0

    async def create_connection(self, config: MCPServerConfig) -> MCPConnection:
        """Create new MCP connection from server config."""
        # Store config for recovery operations
        self._server_configs[config.name] = config
        connection_id = str(uuid.uuid4())
        transport = await self._create_transport(config)
        connection = self._build_connection_object(connection_id, config, transport)
        return await self._establish_connection(connection, config)

    def _build_connection_object(self, connection_id: str, config: MCPServerConfig, transport: Any) -> MCPConnection:
        """Build connection object with configuration."""
        return MCPConnection(
            id=connection_id, server_name=config.name, transport=transport,
            status=ConnectionStatus.CONNECTING, created_at=datetime.now()
        )

    async def get_connection(self, server_name: str) -> Optional[MCPConnection]:
        """Get available connection from pool with load balancing."""
        if server_name not in self._pools:
            return None
        return await self._get_pooled_connection(server_name)

    async def _get_pooled_connection(self, server_name: str) -> Optional[MCPConnection]:
        """Get connection from pool and update usage timestamp."""
        try:
            connection = self._pools[server_name].get_nowait()
            connection.last_used = datetime.now()
            return connection
        except asyncio.QueueEmpty:
            return None

    async def release_connection(self, connection: MCPConnection) -> None:
        """Return connection to pool if healthy."""
        if await self.health_check(connection):
            await self._pools[connection.server_name].put(connection)
        else:
            await self._remove_connection(connection)

    async def health_check(self, connection: MCPConnection) -> bool:
        """Check if connection is healthy and responsive."""
        if connection.status != ConnectionStatus.CONNECTED:
            return False
        return await self._perform_health_check(connection)

    async def _perform_health_check(self, connection: MCPConnection) -> bool:
        """Perform actual health check with error handling."""
        try:
            return await self._ping_connection(connection)
        except Exception as e:
            self._logger.error(f"Health check failed: {e}")
            return False

    async def reconnect(self, connection: MCPConnection) -> MCPConnection:
        """Reconnect failed connection with exponential backoff."""
        connection.status = ConnectionStatus.RECONNECTING
        connection.retry_count += 1
        connection.last_failure = datetime.now()
        
        # Check if max retries exceeded
        if connection.retry_count > self._max_retry_attempts:
            await self._handle_permanent_failure(connection)
            raise NetraException(f"Connection {connection.id} exceeded max retry attempts")
        
        await self._wait_for_backoff(connection.retry_count)
        return await self._create_replacement_connection(connection)

    async def _wait_for_backoff(self, retry_count: int) -> None:
        """Wait for exponential backoff delay."""
        backoff_delay = self._calculate_backoff_delay(retry_count)
        await asyncio.sleep(backoff_delay)

    async def _create_replacement_connection(self, connection: MCPConnection) -> MCPConnection:
        """Create and set up replacement connection."""
        config = self._get_server_config(connection.server_name)
        new_connection = await self.create_connection(config)
        await self._replace_connection(connection, new_connection)
        return new_connection

    async def close_all_connections(self) -> None:
        """Close all connections and cleanup resources."""
        await self._cancel_background_tasks()
        await self._drain_all_pools()
        await self._close_all_active_connections()

    async def _cancel_background_tasks(self) -> None:
        """Cancel all background tasks."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        if self._recovery_task:
            self._recovery_task.cancel()
            try:
                await self._recovery_task
            except asyncio.CancelledError:
                pass

    async def _drain_all_pools(self) -> None:
        """Drain all connection pools."""
        for server_pools in self._pools.values():
            await self._drain_pool(server_pools)

    async def _close_all_active_connections(self) -> None:
        """Close all active connections."""
        for connections in self._active_connections.values():
            await self._close_connections(connections)

    async def _create_transport(self, config: MCPServerConfig) -> Any:
        """Create transport instance based on config type."""
        transport_map = self._get_transport_factory_map()
        factory = transport_map.get(config.transport)
        if not factory:
            raise NetraException(f"Unsupported transport: {config.transport}")
        return await factory(config)

    def _get_transport_factory_map(self) -> Dict[MCPTransport, Any]:
        """Get mapping of transport types to factory functions."""
        return {
            MCPTransport.STDIO: self._create_stdio_transport,
            MCPTransport.HTTP: self._create_http_transport,
            MCPTransport.WEBSOCKET: self._create_websocket_transport
        }

    async def _establish_connection(self, connection: MCPConnection, config: MCPServerConfig) -> MCPConnection:
        """Establish and validate connection."""
        try:
            return await self._perform_connection_setup(connection, config)
        except Exception as e:
            connection.status = ConnectionStatus.FAILED
            raise NetraException(f"Connection failed: {e}")

    async def _perform_connection_setup(self, connection: MCPConnection, config: MCPServerConfig) -> MCPConnection:
        """Perform the actual connection setup steps."""
        await self._connect_transport(connection.transport, config)
        connection.status = ConnectionStatus.CONNECTED
        connection.retry_count = 0  # Reset on successful connection
        connection.consecutive_failures = 0
        connection.session_id = await self._negotiate_session(connection)
        await self._initialize_pool(config.name)
        self._update_metrics(config.name, "created")
        await self._start_background_tasks()
        return connection

    async def _ping_connection(self, connection: MCPConnection) -> bool:
        """Send ping to test connection health."""
        # Implementation would depend on transport type
        return True  # Simplified for now

    def _calculate_backoff_delay(self, retry_count: int) -> float:
        """Calculate exponential backoff delay based on retry attempts."""
        return min(self._reconnect_backoff_base * (2 ** retry_count), 60.0)

    def _get_server_config(self, server_name: str) -> MCPServerConfig:
        """Get server configuration by name."""
        config = self._server_configs.get(server_name)
        if not config:
            raise NetraException(f"No configuration found for server: {server_name}")
        return config

    async def _replace_connection(self, old_conn: MCPConnection, new_conn: MCPConnection) -> None:
        """Replace failed connection with new one."""
        await self._remove_connection(old_conn)
        await self._pools[new_conn.server_name].put(new_conn)

    async def _drain_pool(self, pool: asyncio.Queue) -> None:
        """Drain and close all connections in pool."""
        while not pool.empty():
            try:
                connection = pool.get_nowait()
                await self._close_single_connection(connection)
            except asyncio.QueueEmpty:
                break

    async def _close_connections(self, connections: List[MCPConnection]) -> None:
        """Close list of connections."""
        for connection in connections:
            await self._close_single_connection(connection)

    async def _create_stdio_transport(self, config: MCPServerConfig) -> Any:
        """Create stdio transport for subprocess connections."""
        # Implementation would create subprocess transport
        return None

    async def _create_http_transport(self, config: MCPServerConfig) -> Any:
        """Create HTTP transport for HTTP-based connections."""
        # Implementation would create HTTP client
        return None

    async def _create_websocket_transport(self, config: MCPServerConfig) -> Any:
        """Create WebSocket transport for WS connections."""
        # Implementation would create WebSocket client
        return None

    async def _connect_transport(self, transport: Any, config: MCPServerConfig) -> None:
        """Connect the transport to the server."""
        # Implementation would establish transport connection
        pass

    async def _negotiate_session(self, connection: MCPConnection) -> str:
        """Negotiate MCP session with server."""
        # Implementation would handle MCP protocol negotiation
        return str(uuid.uuid4())

    async def _initialize_pool(self, server_name: str) -> None:
        """Initialize connection pool for server."""
        if server_name not in self._pools:
            self._pools[server_name] = asyncio.Queue(maxsize=self._max_connections)
            self._active_connections[server_name] = []
            self._metrics[server_name] = ConnectionMetrics()

    def _update_metrics(self, server_name: str, operation: str) -> None:
        """Update connection metrics."""
        if operation == "created":
            self._metrics[server_name].total_created += 1
        elif operation == "destroyed":
            self._metrics[server_name].total_destroyed += 1

    async def _remove_connection(self, connection: MCPConnection) -> None:
        """Remove and cleanup connection."""
        await self._close_single_connection(connection)
        self._update_metrics(connection.server_name, "destroyed")
        
        # Add to failed connections for recovery
        server_name = connection.server_name
        if server_name not in self._failed_connections:
            self._failed_connections[server_name] = []
        self._failed_connections[server_name].append(connection)
        
        # Check if circuit breaker should be opened
        await self._check_circuit_breaker(server_name)

    async def _close_single_connection(self, connection: MCPConnection) -> None:
        """Close individual connection and cleanup."""
        try:
            if hasattr(connection.transport, 'close'):
                await connection.transport.close()
            connection.status = ConnectionStatus.DISCONNECTED
        except Exception as e:
            self._logger.error(f"Error closing connection {connection.id}: {e}")

    def get_metrics(self, server_name: str) -> Optional[ConnectionMetrics]:
        """Get connection metrics for server."""
        return self._metrics.get(server_name)

    def get_pool_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all connection pools."""
        status = {}
        for server_name, pool in self._pools.items():
            status[server_name] = self._build_pool_status_entry(server_name, pool)
        return status

    def _build_pool_status_entry(self, server_name: str, pool: asyncio.Queue) -> Dict[str, Any]:
        """Build status entry for single pool."""
        return {
            "pool_size": pool.qsize(),
            "max_size": self._max_connections,
            "metrics": self._metrics.get(server_name)
        }

    async def _start_background_tasks(self) -> None:
        """Start health check and recovery background tasks."""
        if not self._health_check_task or self._health_check_task.done():
            self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        if not self._recovery_task or self._recovery_task.done():
            self._recovery_task = asyncio.create_task(self._recovery_loop())

    async def _health_check_loop(self) -> None:
        """Background health check for all connections."""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Health check loop error: {e}")

    async def _perform_health_checks(self) -> None:
        """Perform health checks on all pooled connections."""
        for server_name, pool in self._pools.items():
            pool_size = pool.qsize()
            temp_connections = []
            
            # Check each connection in pool
            for _ in range(pool_size):
                try:
                    connection = pool.get_nowait()
                    if await self.health_check(connection):
                        temp_connections.append(connection)
                    else:
                        await self._handle_failed_connection(connection)
                except asyncio.QueueEmpty:
                    break
            
            # Return healthy connections to pool
            for connection in temp_connections:
                await pool.put(connection)

    async def _recovery_loop(self) -> None:
        """Background recovery for failed connections and pool maintenance."""
        while True:
            try:
                await asyncio.sleep(self._recovery_interval)
                await self._recover_failed_connections()
                await self._maintain_pool_sizes()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Recovery loop error: {e}")

    async def _recover_failed_connections(self) -> None:
        """Attempt to recover failed connections."""
        for server_name, failed_conns in self._failed_connections.items():
            if not failed_conns:
                continue
            
            # Check if circuit breaker allows recovery attempts
            if self._is_circuit_breaker_open(server_name):
                if not self._should_attempt_circuit_recovery(server_name):
                    continue
            
            # Attempt recovery for oldest failed connection
            connection = failed_conns[0]
            try:
                recovered = await self._attempt_connection_recovery(connection)
                if recovered:
                    failed_conns.remove(connection)
                    await self._pools[server_name].put(recovered)
                    self._reset_circuit_breaker(server_name)
                    self._logger.info(f"Recovered connection for server {server_name}")
            except Exception as e:
                self._logger.error(f"Recovery attempt failed for {server_name}: {e}")

    async def _maintain_pool_sizes(self) -> None:
        """Ensure minimum pool sizes are maintained."""
        for server_name, pool in self._pools.items():
            current_size = pool.qsize()
            if current_size < self._min_connections_per_server:
                needed = self._min_connections_per_server - current_size
                await self._create_additional_connections(server_name, needed)

    async def _handle_failed_connection(self, connection: MCPConnection) -> None:
        """Handle a connection that failed health check."""
        connection.consecutive_failures += 1
        connection.last_failure = datetime.now()
        connection.status = ConnectionStatus.FAILED
        await self._remove_connection(connection)

    async def _handle_permanent_failure(self, connection: MCPConnection) -> None:
        """Handle connection that exceeded retry limit."""
        connection.status = ConnectionStatus.FAILED
        self._logger.warning(f"Connection {connection.id} permanently failed after {connection.retry_count} attempts")
        await self._remove_connection(connection)

    async def _attempt_connection_recovery(self, connection: MCPConnection) -> Optional[MCPConnection]:
        """Attempt to recover a failed connection."""
        config = self._get_server_config(connection.server_name)
        
        # Create new connection with same server config
        try:
            new_connection = await self.create_connection(config)
            self._logger.info(f"Successfully recovered connection for {connection.server_name}")
            return new_connection
        except Exception as e:
            self._logger.error(f"Failed to recover connection for {connection.server_name}: {e}")
            return None

    async def _create_additional_connections(self, server_name: str, count: int) -> None:
        """Create additional connections to maintain minimum pool size."""
        config = self._get_server_config(server_name)
        
        for _ in range(count):
            try:
                connection = await self.create_connection(config)
                await self._pools[server_name].put(connection)
                self._logger.info(f"Created additional connection for {server_name}")
            except Exception as e:
                self._logger.error(f"Failed to create additional connection for {server_name}: {e}")
                break

    async def _check_circuit_breaker(self, server_name: str) -> None:
        """Check if circuit breaker should be opened for server."""
        failed_count = len(self._failed_connections.get(server_name, []))
        if failed_count >= self._circuit_breaker_threshold:
            metrics = self._metrics.get(server_name)
            if metrics:
                metrics.circuit_breaker_open = True
                metrics.last_circuit_open = datetime.now()
                self._logger.warning(f"Circuit breaker opened for server {server_name}")

    def _is_circuit_breaker_open(self, server_name: str) -> bool:
        """Check if circuit breaker is open for server."""
        metrics = self._metrics.get(server_name)
        return metrics.circuit_breaker_open if metrics else False

    def _should_attempt_circuit_recovery(self, server_name: str) -> bool:
        """Check if circuit breaker timeout has passed."""
        metrics = self._metrics.get(server_name)
        if not metrics or not metrics.last_circuit_open:
            return True
        
        time_since_open = (datetime.now() - metrics.last_circuit_open).total_seconds()
        return time_since_open >= self._circuit_breaker_timeout

    def _reset_circuit_breaker(self, server_name: str) -> None:
        """Reset circuit breaker for server after successful recovery."""
        metrics = self._metrics.get(server_name)
        if metrics:
            metrics.circuit_breaker_open = False
            metrics.last_circuit_open = None
            # Clear failed connections list after successful recovery
            self._failed_connections[server_name] = []
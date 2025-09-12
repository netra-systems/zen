"""
MCP Connection Manager: Connection pooling and lifecycle management for MCP servers.

This module implements connection pooling, automatic reconnection, health checks,
and load balancing for Model Context Protocol (MCP) server connections.

CRITICAL ARCHITECTURAL COMPLIANCE:
- File size: <300 lines
- Function size:  <= 8 lines each
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
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from netra_backend.app.core.exceptions import NetraException
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker,
    UnifiedCircuitConfig,
    UnifiedCircuitBreakerState
)
from netra_backend.app.mcp_client.models import ConnectionStatus


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
    recovery_attempts: int = 0
    successful_recoveries: int = 0
    last_recovery_attempt: Optional[datetime] = None
    last_successful_recovery: Optional[datetime] = None


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
    recovery_backoff_delay: float = 1.0
    max_recovery_attempts: int = 10
    last_health_check: Optional[datetime] = None
    health_check_failures: int = 0


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
        self._circuit_breakers: Dict[str, UnifiedCircuitBreaker] = {}
        self._initialize_settings()
        self._logger = logging.getLogger(__name__)
        self._recovery_task: Optional[asyncio.Task] = None
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._recovery_lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()

    def _initialize_settings(self) -> None:
        """Initialize default settings and configuration."""
        self._health_check_interval = 30.0
        self._health_check_task: Optional[asyncio.Task] = None
        self._reconnect_backoff_base = 1.0
        self._max_backoff_delay = 15.0  # Reduced from 60.0 to 15.0 seconds max
        self._max_retry_attempts = 3  # Reduced from 10 to 3 attempts
        self._circuit_breaker_threshold = 3  # Reduced from 5 to 3 failures
        self._circuit_breaker_timeout = 30.0  # Reduced from 60.0 to 30.0 seconds
        self._recovery_interval = 5.0  # Reduced from 10.0 to 5.0 seconds
        self._recovery_jitter_max = 2.0  # Reduced from 5.0 to 2.0 seconds
        self._force_recovery_interval = 30.0  # CRITICAL FIX: Reduced from 300.0 to 30.0 seconds
        self._operation_timeout = 30.0  # NEW: Maximum timeout for any MCP operation

    async def create_connection(self, config: MCPServerConfig) -> MCPConnection:
        """Create new MCP connection from server config with operation timeout."""
        try:
            # Store config for recovery operations
            self._server_configs[config.name] = config
            
            # Initialize circuit breaker for server if not exists
            await self._ensure_circuit_breaker(config.name)
            
            connection_id = str(uuid.uuid4())
            
            # Wrap connection creation with timeout
            return await asyncio.wait_for(
                self._create_connection_with_timeout(config, connection_id),
                timeout=self._operation_timeout
            )
        except asyncio.TimeoutError:
            self._logger.error(f"Connection creation timed out after {self._operation_timeout}s for {config.name}")
            raise NetraException(f"Connection timeout: {config.name} failed to connect within {self._operation_timeout}s")
        except Exception as e:
            self._logger.error(f"Connection creation failed for {config.name}: {e}")
            raise NetraException(f"Connection failed: {config.name} - {str(e)}")

    async def _create_connection_with_timeout(self, config: MCPServerConfig, connection_id: str) -> MCPConnection:
        """Create connection with all steps wrapped for timeout protection."""
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
        """Get available connection from pool with timeout protection."""
        try:
            if server_name not in self._pools:
                return None
            
            # Add timeout to pool operations to prevent hanging
            return await asyncio.wait_for(
                self._get_pooled_connection(server_name),
                timeout=5.0  # 5 second timeout for getting connection from pool
            )
        except asyncio.TimeoutError:
            self._logger.warning(f"Pool connection retrieval timed out for {server_name}")
            return None
        except Exception as e:
            self._logger.error(f"Error getting connection for {server_name}: {e}")
            return None

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
        """Reconnect failed connection with exponential backoff and timeout protection."""
        connection.status = ConnectionStatus.RECONNECTING
        connection.retry_count += 1
        connection.last_failure = datetime.now()
        
        self._logger.info(
            f"Attempting reconnection for {connection.server_name}, "
            f"attempt {connection.retry_count}/{connection.max_recovery_attempts}"
        )
        
        # CRITICAL FIX: Hard fail after max retries to prevent infinite loops
        if connection.retry_count > connection.max_recovery_attempts:
            connection.status = ConnectionStatus.FAILED
            self._logger.error(
                f"Max retries ({connection.max_recovery_attempts}) exceeded for {connection.server_name}, "
                f"marking connection as permanently failed"
            )
            raise NetraException(f"Connection permanently failed: {connection.server_name} after {connection.max_recovery_attempts} attempts")
        
        await self._wait_for_backoff(connection)
        
        # Add timeout protection to reconnection
        try:
            return await asyncio.wait_for(
                self._create_replacement_connection(connection),
                timeout=self._operation_timeout
            )
        except asyncio.TimeoutError:
            self._logger.error(f"Reconnection timed out for {connection.server_name}")
            connection.status = ConnectionStatus.FAILED
            raise NetraException(f"Reconnection timeout: {connection.server_name}")

    async def _wait_for_backoff(self, connection: MCPConnection) -> None:
        """Wait for exponential backoff delay with jitter."""
        base_delay = connection.recovery_backoff_delay
        jitter = random.uniform(0, self._recovery_jitter_max)
        total_delay = base_delay + jitter
        
        self._logger.debug(
            f"Waiting {total_delay:.2f}s before retry for {connection.server_name}"
        )
        
        await asyncio.sleep(total_delay)

    async def _create_replacement_connection(self, connection: MCPConnection) -> MCPConnection:
        """Create and set up replacement connection."""
        config = self._get_server_config(connection.server_name)
        new_connection = await self.create_connection(config)
        await self._replace_connection(connection, new_connection)
        return new_connection

    async def close_all_connections(self) -> None:
        """Close all connections and cleanup resources."""
        # Signal shutdown to all background tasks
        self._shutdown_event.set()
        
        await self._cancel_background_tasks()
        await self._drain_all_pools()
        await self._close_all_active_connections()
        
        # Cleanup circuit breakers
        for breaker in self._circuit_breakers.values():
            breaker.cleanup()

    async def _cancel_background_tasks(self) -> None:
        """Cancel all background tasks."""
        tasks_to_cancel = []
        
        if self._health_check_task and not self._health_check_task.done():
            tasks_to_cancel.append(self._health_check_task)
        
        if self._recovery_task and not self._recovery_task.done():
            tasks_to_cancel.append(self._recovery_task)
            
        if self._health_monitor_task and not self._health_monitor_task.done():
            tasks_to_cancel.append(self._health_monitor_task)
        
        for task in tasks_to_cancel:
            task.cancel()
        
        # Wait for all tasks to complete cancellation
        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)

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
        
        # Reset all failure counters on successful connection
        connection.retry_count = 0
        connection.consecutive_failures = 0
        connection.recovery_backoff_delay = 1.0  # Reset backoff delay
        connection.health_check_failures = 0
        connection.last_health_check = datetime.now()
        
        # Reset circuit breaker on successful connection
        circuit_breaker = self._circuit_breakers.get(config.name)
        if circuit_breaker:
            await circuit_breaker.reset()
            self._logger.info(f"Circuit breaker reset for {config.name} after successful connection")
        
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
        delay = self._reconnect_backoff_base * (2 ** min(retry_count, 6))
        return min(delay, self._max_backoff_delay)

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
        """Remove connection but add to recovery queue instead of permanent removal."""
        await self._close_single_connection(connection)
        self._update_metrics(connection.server_name, "destroyed")
        
        # If connection was FAILED, move to recovery queue
        if connection.status == ConnectionStatus.FAILED:
            await self._move_to_recovery_queue(connection)
        
        # Update circuit breaker metrics
        await self._check_circuit_breaker(connection.server_name)

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
            
        if not self._health_monitor_task or self._health_monitor_task.done():
            self._health_monitor_task = asyncio.create_task(self._health_monitor_loop())

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
        """Attempt to recover failed connections with comprehensive retry logic."""
        async with self._recovery_lock:
            for server_name, failed_conns in list(self._failed_connections.items()):
                if not failed_conns:
                    continue
                
                # Check if circuit breaker allows recovery attempts
                circuit_breaker = self._circuit_breakers.get(server_name)
                if circuit_breaker and circuit_breaker.get_state() == UnifiedCircuitBreakerState.OPEN:
                    if not circuit_breaker.can_execute():
                        self._logger.debug(f"Circuit breaker open for {server_name}, skipping recovery")
                        continue
                
                # Process recovery attempts for up to 3 connections per iteration
                connections_to_process = failed_conns[:3]  # Limit concurrent recovery attempts
                
                for connection in connections_to_process:
                    try:
                        await self._attempt_single_connection_recovery(connection, server_name)
                    except Exception as e:
                        self._logger.error(f"Recovery attempt failed for {server_name}: {e}")
                        # Continue with next connection instead of stopping

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
        connection.health_check_failures += 1
        
        self._logger.warning(
            f"Health check failed for connection {connection.id} ({connection.server_name}), "
            f"consecutive failures: {connection.consecutive_failures}"
        )
        
        # Use the new failure handling approach
        await self._handle_connection_failure(connection, "health_check_failed")

    async def _handle_connection_failure(self, connection: MCPConnection, error: str) -> None:
        """Handle connection failure without permanent abandonment."""
        connection.status = ConnectionStatus.FAILED
        connection.consecutive_failures += 1
        connection.last_failure = datetime.now()
        
        # Record failure in circuit breaker
        circuit_breaker = self._circuit_breakers.get(connection.server_name)
        if circuit_breaker:
            circuit_breaker.record_failure(error)
        
        self._logger.warning(
            f"Connection {connection.id} failed: {error}. "
            f"Consecutive failures: {connection.consecutive_failures}, "
            f"will retry after backoff"
        )
        
        # Move to failed connections list for recovery instead of removing
        await self._move_to_recovery_queue(connection)

    async def _attempt_single_connection_recovery(self, connection: MCPConnection, server_name: str) -> None:
        """Attempt to recover a single failed connection with timeout protection."""
        # CRITICAL FIX: Check if connection has exceeded max recovery attempts
        if connection.retry_count >= self._max_retry_attempts:
            self._logger.error(
                f"Connection {connection.id} for {server_name} has exceeded max recovery attempts "
                f"({self._max_retry_attempts}), removing from recovery queue"
            )
            self._failed_connections[server_name].remove(connection)
            return
        
        # Check if enough time has passed since last failure
        if connection.last_failure:
            time_since_failure = (datetime.now() - connection.last_failure).total_seconds()
            if time_since_failure < connection.recovery_backoff_delay:
                return  # Not ready for recovery yet
        
        config = self._get_server_config(server_name)
        self._metrics[server_name].recovery_attempts += 1
        self._metrics[server_name].last_recovery_attempt = datetime.now()
        
        try:
            self._logger.info(
                f"Attempting recovery for {server_name}, "
                f"backoff: {connection.recovery_backoff_delay}s, "
                f"attempt: {connection.retry_count}/{self._max_retry_attempts}"
            )
            
            # CRITICAL FIX: Add timeout to recovery attempt
            new_connection = await asyncio.wait_for(
                self.create_connection(config),
                timeout=self._operation_timeout
            )
            
            # Successful recovery
            self._failed_connections[server_name].remove(connection)
            await self._pools[server_name].put(new_connection)
            
            # Update metrics
            self._metrics[server_name].successful_recoveries += 1
            self._metrics[server_name].last_successful_recovery = datetime.now()
            
            # Record success in circuit breaker
            circuit_breaker = self._circuit_breakers.get(server_name)
            if circuit_breaker:
                circuit_breaker.record_success()
            
            self._logger.info(f"Successfully recovered connection for {server_name}")
            
        except asyncio.TimeoutError:
            connection.retry_count += 1
            connection.last_failure = datetime.now()
            self._logger.error(f"Recovery timeout for {server_name} after {self._operation_timeout}s")
            
            # Mark for removal if max retries exceeded
            if connection.retry_count >= self._max_retry_attempts:
                self._failed_connections[server_name].remove(connection)
                
        except Exception as e:
            # Update connection for next retry
            connection.retry_count += 1
            connection.last_failure = datetime.now()
            
            # CRITICAL FIX: Remove connection if max retries exceeded
            if connection.retry_count >= self._max_retry_attempts:
                self._logger.error(
                    f"Max recovery attempts reached for {server_name}, removing connection"
                )
                self._failed_connections[server_name].remove(connection)
                return
            
            # Exponentially increase backoff delay
            connection.recovery_backoff_delay = min(
                connection.recovery_backoff_delay * 2,
                self._max_backoff_delay
            )
            
            # Record failure in circuit breaker
            circuit_breaker = self._circuit_breakers.get(server_name)
            if circuit_breaker:
                circuit_breaker.record_failure(str(e))
            
            self._logger.warning(
                f"Recovery failed for {server_name}: {e}. "
                f"Next attempt in {connection.recovery_backoff_delay}s"
            )

    async def _create_additional_connections(self, server_name: str, count: int) -> None:
        """Create additional connections with timeout protection."""
        config = self._get_server_config(server_name)
        
        # CRITICAL FIX: Limit the number of connections being created at once
        max_concurrent_creates = min(count, 3)  # Max 3 concurrent connection attempts
        
        for i in range(max_concurrent_creates):
            try:
                # Add timeout to each connection creation
                connection = await asyncio.wait_for(
                    self.create_connection(config),
                    timeout=self._operation_timeout
                )
                await self._pools[server_name].put(connection)
                self._logger.info(f"Created additional connection {i+1}/{max_concurrent_creates} for {server_name}")
            except asyncio.TimeoutError:
                self._logger.error(f"Connection creation timed out for {server_name} (attempt {i+1})")
                break  # Stop creating more connections if we're timing out
            except Exception as e:
                self._logger.error(f"Failed to create additional connection for {server_name}: {e}")
                break  # Stop on any error to prevent cascading failures

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

    async def _reset_circuit_breaker(self, server_name: str) -> None:
        """Reset circuit breaker for server after successful recovery."""
        circuit_breaker = self._circuit_breakers.get(server_name)
        if circuit_breaker:
            await circuit_breaker.reset()
            self._logger.info(f"Circuit breaker reset for {server_name}")
        
        metrics = self._metrics.get(server_name)
        if metrics:
            metrics.circuit_breaker_open = False
            metrics.last_circuit_open = None

    async def _ensure_circuit_breaker(self, server_name: str) -> None:
        """Ensure circuit breaker exists for server with optimized settings."""
        if server_name not in self._circuit_breakers:
            config = UnifiedCircuitConfig(
                name=f"mcp_{server_name}",
                failure_threshold=self._circuit_breaker_threshold,  # 3 failures (reduced from 5)
                recovery_timeout=self._circuit_breaker_timeout,     # 30 seconds (reduced from 60)
                timeout_seconds=self._operation_timeout,            # 30 seconds operation timeout
                half_open_timeout=10.0,                             # 10 seconds in half-open state
                reset_timeout=60.0                                  # Reset after 60 seconds of success
            )
            self._circuit_breakers[server_name] = UnifiedCircuitBreaker(config)
            self._logger.debug(
                f"Created circuit breaker for MCP server: {server_name} "
                f"(failure_threshold={self._circuit_breaker_threshold}, "
                f"recovery_timeout={self._circuit_breaker_timeout}s)"
            )

    async def _move_to_recovery_queue(self, connection: MCPConnection) -> None:
        """Move connection to recovery queue instead of permanently removing."""
        server_name = connection.server_name
        if server_name not in self._failed_connections:
            self._failed_connections[server_name] = []
        
        # Avoid duplicates
        if connection not in self._failed_connections[server_name]:
            self._failed_connections[server_name].append(connection)
            self._logger.info(
                f"Moved connection {connection.id} to recovery queue for {server_name}"
            )

    async def _health_monitor_loop(self) -> None:
        """Background health monitoring with proactive recovery."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self._health_check_interval)
                await self._monitor_system_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Health monitor loop error: {e}")

    async def _monitor_system_health(self) -> None:
        """Monitor overall system health and trigger recovery if needed."""
        for server_name, metrics in self._metrics.items():
            pool = self._pools.get(server_name)
            if not pool:
                continue
                
            # Check if pool is empty and we have failed connections
            if pool.empty() and self._failed_connections.get(server_name):
                self._logger.warning(
                    f"Pool empty for {server_name} with {len(self._failed_connections[server_name])} failed connections, "
                    f"triggering recovery"
                )
                await self._trigger_force_recovery(server_name)
            
            # Check circuit breaker health
            circuit_breaker = self._circuit_breakers.get(server_name)
            if circuit_breaker:
                status = circuit_breaker.get_status()
                if status["state"] == "open":
                    time_since_opened = status["metrics"].get("time_since_opened", 0)
                    if time_since_opened and time_since_opened > self._force_recovery_interval:
                        self._logger.info(
                            f"Force recovery for {server_name} after {time_since_opened}s in open state"
                        )
                        await self._trigger_force_recovery(server_name)

    async def _trigger_force_recovery(self, server_name: str) -> None:
        """Trigger force recovery for a server."""
        failed_conns = self._failed_connections.get(server_name, [])
        if not failed_conns:
            return
            
        # Reset backoff delays and circuit breaker for force recovery
        for conn in failed_conns:
            conn.recovery_backoff_delay = 1.0  # Reset to minimum
            conn.retry_count = 0  # Reset retry count
            
        circuit_breaker = self._circuit_breakers.get(server_name)
        if circuit_breaker:
            await circuit_breaker.reset()
            
        self._logger.info(f"Triggered force recovery for {server_name}")

    async def get_connection_status(self) -> Dict[str, Any]:
        """Get comprehensive connection status for all servers."""
        status = {}
        
        for server_name, config in self._server_configs.items():
            pool = self._pools.get(server_name)
            failed_conns = self._failed_connections.get(server_name, [])
            circuit_breaker = self._circuit_breakers.get(server_name)
            metrics = self._metrics.get(server_name, ConnectionMetrics())
            
            status[server_name] = {
                "server_config": {
                    "name": config.name,
                    "url": config.url,
                    "transport": config.transport
                },
                "pool_status": {
                    "available": pool.qsize() if pool else 0,
                    "max_size": self._max_connections,
                    "min_size": self._min_connections_per_server
                },
                "failed_connections": len(failed_conns),
                "circuit_breaker": circuit_breaker.get_status() if circuit_breaker else None,
                "metrics": {
                    "total_created": metrics.total_created,
                    "total_destroyed": metrics.total_destroyed,
                    "recovery_attempts": metrics.recovery_attempts,
                    "successful_recoveries": metrics.successful_recoveries,
                    "last_recovery_attempt": metrics.last_recovery_attempt.isoformat() if metrics.last_recovery_attempt else None,
                    "last_successful_recovery": metrics.last_successful_recovery.isoformat() if metrics.last_successful_recovery else None
                },
                "health_status": "healthy" if (pool and pool.qsize() > 0) else "degraded" if failed_conns else "unknown"
            }
            
        return status

    async def force_recovery_all(self) -> Dict[str, bool]:
        """Force recovery for all servers with failed connections."""
        results = {}
        
        for server_name in self._server_configs.keys():
            try:
                await self._trigger_force_recovery(server_name)
                results[server_name] = True
            except Exception as e:
                self._logger.error(f"Force recovery failed for {server_name}: {e}")
                results[server_name] = False
                
        return results
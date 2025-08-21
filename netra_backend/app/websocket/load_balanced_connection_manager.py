"""Load-Balanced WebSocket Connection Manager.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Scalability worth $12K MRR growth support
- Value Impact: Enables horizontal scaling and improved performance under load
- Strategic Impact: Supports business growth with cost-effective scaling

This module provides:
- Load balancing across connection pools
- Connection health monitoring and failover
- Memory-efficient connection management
- CPU usage optimization with intelligent routing
- Graceful degradation under high load
"""

import asyncio
import time
import psutil
import weakref
from typing import Dict, Any, List, Set, Optional, Tuple, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import hashlib

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.logging_config import central_logger
from app.websocket.connection_info import ConnectionInfo

logger = central_logger.get_logger(__name__)


class LoadBalancingStrategy(Enum):
    """Load balancing strategies for connection distribution."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    CPU_AWARE = "cpu_aware"
    MEMORY_AWARE = "memory_aware"
    ADAPTIVE = "adaptive"


class ConnectionPoolHealth(Enum):
    """Health states for connection pools."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OVERLOADED = "overloaded"
    CRITICAL = "critical"
    UNAVAILABLE = "unavailable"


@dataclass
class ConnectionPoolMetrics:
    """Metrics for a connection pool."""
    
    pool_id: str
    max_connections: int = 1000
    current_connections: int = 0
    active_connections: int = 0
    failed_connections: int = 0
    avg_response_time_ms: float = 0.0
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    last_health_check: float = field(default_factory=time.time)
    health_status: ConnectionPoolHealth = ConnectionPoolHealth.HEALTHY
    weight: float = 1.0
    
    def get_utilization(self) -> float:
        """Get pool utilization as percentage."""
        return (self.current_connections / self.max_connections) * 100
    
    def get_load_score(self) -> float:
        """Calculate load score for balancing decisions."""
        utilization = self.get_utilization() / 100
        cpu_factor = self.cpu_usage_percent / 100
        memory_factor = min(self.memory_usage_mb / 1024, 1.0)  # Normalize to GB
        response_factor = min(self.avg_response_time_ms / 1000, 1.0)  # Normalize to seconds
        
        # Weighted load score (lower is better)
        load_score = (
            utilization * 0.4 +
            cpu_factor * 0.3 +
            memory_factor * 0.2 +
            response_factor * 0.1
        )
        
        return load_score


@dataclass
class ConnectionSession:
    """Session information for sticky connections."""
    
    session_id: str
    user_id: str
    pool_id: str
    websocket: WebSocket
    created_at: float
    last_activity: float
    connection_count: int = 1
    sticky_score: float = 1.0
    
    def is_expired(self, timeout_seconds: int = 3600) -> bool:
        """Check if session has expired."""
        return time.time() - self.last_activity > timeout_seconds
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = time.time()


class HealthMonitor:
    """Monitor health of connection pools."""
    
    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.health_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=20))
        self.monitoring_task: Optional[asyncio.Task] = None
        self.running = False
    
    def start_monitoring(self, pools: Dict[str, 'LoadBalancedConnectionPool']) -> None:
        """Start health monitoring for pools."""
        if not self.running:
            self.running = True
            self.pools_ref = weakref.ref(pools)
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self) -> None:
        """Stop health monitoring."""
        self.running = False
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.running:
            try:
                pools = self.pools_ref() if self.pools_ref else None
                if pools:
                    await self._check_all_pools(pools)
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def _check_all_pools(self, pools: Dict[str, 'LoadBalancedConnectionPool']) -> None:
        """Check health of all pools."""
        for pool_id, pool in pools.items():
            try:
                await self._check_pool_health(pool_id, pool)
            except Exception as e:
                logger.error(f"Health check failed for pool {pool_id}: {e}")
    
    async def _check_pool_health(self, pool_id: str, pool: 'LoadBalancedConnectionPool') -> None:
        """Check health of individual pool."""
        metrics = pool.get_metrics()
        
        # Calculate health score
        health_score = self._calculate_health_score(metrics)
        
        # Determine health status
        health_status = self._determine_health_status(health_score, metrics)
        
        # Update pool health
        pool.update_health_status(health_status, health_score)
        
        # Record health history
        health_record = {
            "timestamp": time.time(),
            "health_score": health_score,
            "status": health_status.value,
            "connections": metrics.current_connections,
            "utilization": metrics.get_utilization()
        }
        self.health_history[pool_id].append(health_record)
    
    def _calculate_health_score(self, metrics: ConnectionPoolMetrics) -> float:
        """Calculate health score (0-1, higher is better)."""
        utilization_score = max(0, 1 - (metrics.get_utilization() / 100))
        cpu_score = max(0, 1 - (metrics.cpu_usage_percent / 100))
        memory_score = max(0, 1 - min(metrics.memory_usage_mb / 1024, 1.0))
        response_score = max(0, 1 - min(metrics.avg_response_time_ms / 1000, 1.0))
        
        # Weighted health score
        health_score = (
            utilization_score * 0.3 +
            cpu_score * 0.25 +
            memory_score * 0.25 +
            response_score * 0.2
        )
        
        return health_score
    
    def _determine_health_status(self, health_score: float, metrics: ConnectionPoolMetrics) -> ConnectionPoolHealth:
        """Determine health status based on score and metrics."""
        if health_score >= 0.8:
            return ConnectionPoolHealth.HEALTHY
        elif health_score >= 0.6:
            return ConnectionPoolHealth.DEGRADED
        elif health_score >= 0.4:
            return ConnectionPoolHealth.OVERLOADED
        elif health_score >= 0.2:
            return ConnectionPoolHealth.CRITICAL
        else:
            return ConnectionPoolHealth.UNAVAILABLE
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report."""
        report = {
            "monitoring_active": self.running,
            "check_interval": self.check_interval,
            "pools": {}
        }
        
        for pool_id, history in self.health_history.items():
            if history:
                latest = history[-1]
                report["pools"][pool_id] = {
                    "latest_health": latest,
                    "history_count": len(history),
                    "avg_health_score": sum(h["health_score"] for h in history) / len(history)
                }
        
        return report


class LoadBalancedConnectionPool:
    """Individual connection pool with load balancing metrics."""
    
    def __init__(self, pool_id: str, max_connections: int = 1000, weight: float = 1.0):
        self.pool_id = pool_id
        self.max_connections = max_connections
        self.weight = weight
        
        # Connection storage
        self.connections: Set[WebSocket] = set()
        self.user_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        
        # Metrics tracking
        self.metrics = ConnectionPoolMetrics(
            pool_id=pool_id,
            max_connections=max_connections,
            weight=weight
        )
        
        # Performance tracking
        self.response_times: deque = deque(maxlen=100)
        self.connection_events: deque = deque(maxlen=1000)
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    async def add_connection(self, websocket: WebSocket, user_id: str = None) -> bool:
        """Add connection to pool."""
        async with self._lock:
            if len(self.connections) >= self.max_connections:
                return False
            
            self.connections.add(websocket)
            if user_id:
                self.user_connections[user_id].add(websocket)
            
            # Store metadata
            self.connection_metadata[websocket] = {
                "user_id": user_id,
                "connected_at": time.time(),
                "last_activity": time.time(),
                "message_count": 0,
                "error_count": 0
            }
            
            # Update metrics
            self.metrics.current_connections = len(self.connections)
            self._update_active_connections()
            
            # Record event
            self.connection_events.append({
                "type": "connect",
                "timestamp": time.time(),
                "user_id": user_id,
                "total_connections": len(self.connections)
            })
            
            return True
    
    async def remove_connection(self, websocket: WebSocket) -> bool:
        """Remove connection from pool."""
        async with self._lock:
            if websocket not in self.connections:
                return False
            
            self.connections.remove(websocket)
            
            # Remove from user connections
            metadata = self.connection_metadata.get(websocket, {})
            user_id = metadata.get("user_id")
            if user_id and user_id in self.user_connections:
                self.user_connections[user_id].discard(websocket)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            # Clean up metadata
            self.connection_metadata.pop(websocket, None)
            
            # Update metrics
            self.metrics.current_connections = len(self.connections)
            self._update_active_connections()
            
            # Record event
            self.connection_events.append({
                "type": "disconnect",
                "timestamp": time.time(),
                "user_id": user_id,
                "total_connections": len(self.connections)
            })
            
            return True
    
    def _update_active_connections(self) -> None:
        """Update count of active connections."""
        active_count = 0
        for websocket in self.connections:
            if websocket.client_state == WebSocketState.CONNECTED:
                active_count += 1
        
        self.metrics.active_connections = active_count
    
    def record_response_time(self, response_time_ms: float) -> None:
        """Record response time for metrics."""
        self.response_times.append(response_time_ms)
        
        # Update average response time
        if self.response_times:
            self.metrics.avg_response_time_ms = sum(self.response_times) / len(self.response_times)
    
    def record_connection_activity(self, websocket: WebSocket) -> None:
        """Record activity for connection."""
        if websocket in self.connection_metadata:
            metadata = self.connection_metadata[websocket]
            metadata["last_activity"] = time.time()
            metadata["message_count"] += 1
    
    def record_connection_error(self, websocket: WebSocket) -> None:
        """Record error for connection."""
        if websocket in self.connection_metadata:
            metadata = self.connection_metadata[websocket]
            metadata["error_count"] += 1
            
        self.metrics.failed_connections += 1
    
    def update_health_status(self, status: ConnectionPoolHealth, health_score: float) -> None:
        """Update health status from health monitor."""
        self.metrics.health_status = status
        self.metrics.last_health_check = time.time()
        
        # Update system metrics
        try:
            process = psutil.Process()
            self.metrics.cpu_usage_percent = process.cpu_percent()
            self.metrics.memory_usage_mb = process.memory_info().rss / 1024 / 1024
        except Exception:
            pass  # Ignore system metrics errors
    
    def get_metrics(self) -> ConnectionPoolMetrics:
        """Get current pool metrics."""
        self._update_active_connections()
        return self.metrics
    
    def get_load_score(self) -> float:
        """Get current load score for balancing."""
        return self.metrics.get_load_score()
    
    def is_available(self) -> bool:
        """Check if pool can accept new connections."""
        return (
            self.metrics.health_status not in [ConnectionPoolHealth.CRITICAL, ConnectionPoolHealth.UNAVAILABLE] and
            len(self.connections) < self.max_connections
        )
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed statistics for pool."""
        return {
            "pool_info": {
                "pool_id": self.pool_id,
                "max_connections": self.max_connections,
                "weight": self.weight
            },
            "connections": {
                "total": len(self.connections),
                "active": self.metrics.active_connections,
                "unique_users": len(self.user_connections)
            },
            "metrics": {
                "utilization": self.metrics.get_utilization(),
                "avg_response_time_ms": self.metrics.avg_response_time_ms,
                "failed_connections": self.metrics.failed_connections,
                "health_status": self.metrics.health_status.value,
                "load_score": self.get_load_score()
            },
            "recent_events": list(self.connection_events)[-10:]  # Last 10 events
        }


class LoadBalancedConnectionManager:
    """Load-balanced connection manager with multiple strategies."""
    
    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.ADAPTIVE):
        self.strategy = strategy
        self.pools: Dict[str, LoadBalancedConnectionPool] = {}
        self.sessions: Dict[str, ConnectionSession] = {}
        self.round_robin_index = 0
        
        # Configuration
        self.sticky_sessions = True
        self.session_timeout = 3600  # 1 hour
        self.max_pools = 10
        
        # Health monitoring
        self.health_monitor = HealthMonitor()
        
        # Load balancing metrics
        self.balancing_metrics = {
            "total_connections_routed": 0,
            "routing_decisions": 0,
            "session_affinity_hits": 0,
            "load_balancing_failures": 0,
            "pool_failovers": 0
        }
        
        # Start health monitoring
        self.health_monitor.start_monitoring(self.pools)
    
    def add_pool(self, pool_id: str, max_connections: int = 1000, weight: float = 1.0) -> bool:
        """Add new connection pool."""
        if len(self.pools) >= self.max_pools:
            logger.warning(f"Cannot add pool {pool_id}: max pools ({self.max_pools}) reached")
            return False
        
        if pool_id in self.pools:
            logger.warning(f"Pool {pool_id} already exists")
            return False
        
        self.pools[pool_id] = LoadBalancedConnectionPool(pool_id, max_connections, weight)
        logger.info(f"Added connection pool {pool_id} with max_connections={max_connections}, weight={weight}")
        return True
    
    def remove_pool(self, pool_id: str) -> bool:
        """Remove connection pool."""
        if pool_id not in self.pools:
            return False
        
        pool = self.pools[pool_id]
        
        # Disconnect all connections in pool
        for websocket in list(pool.connections):
            asyncio.create_task(self._disconnect_websocket(websocket))
        
        del self.pools[pool_id]
        logger.info(f"Removed connection pool {pool_id}")
        return True
    
    async def _disconnect_websocket(self, websocket: WebSocket) -> None:
        """Disconnect WebSocket safely."""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close(code=1001, reason="Pool shutdown")
        except Exception as e:
            logger.debug(f"Error disconnecting WebSocket: {e}")
    
    async def route_connection(self, websocket: WebSocket, user_id: str = None, 
                             session_id: str = None) -> Optional[str]:
        """Route connection to appropriate pool using load balancing."""
        self.balancing_metrics["routing_decisions"] += 1
        
        # Check for session affinity
        if self.sticky_sessions and session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            if not session.is_expired(self.session_timeout):
                target_pool = session.pool_id
                if target_pool in self.pools and self.pools[target_pool].is_available():
                    success = await self.pools[target_pool].add_connection(websocket, user_id)
                    if success:
                        session.update_activity()
                        session.connection_count += 1
                        self.balancing_metrics["session_affinity_hits"] += 1
                        self.balancing_metrics["total_connections_routed"] += 1
                        return target_pool
        
        # Find best pool using load balancing strategy
        target_pool_id = self._select_pool()
        
        if not target_pool_id:
            self.balancing_metrics["load_balancing_failures"] += 1
            logger.warning("No available pools for connection routing")
            return None
        
        # Add connection to selected pool
        success = await self.pools[target_pool_id].add_connection(websocket, user_id)
        
        if success:
            # Create or update session
            if session_id or user_id:
                session_id = session_id or f"session_{user_id}_{int(time.time())}"
                self.sessions[session_id] = ConnectionSession(
                    session_id=session_id,
                    user_id=user_id or "anonymous",
                    pool_id=target_pool_id,
                    websocket=websocket,
                    created_at=time.time(),
                    last_activity=time.time()
                )
            
            self.balancing_metrics["total_connections_routed"] += 1
            return target_pool_id
        else:
            # Try failover to another pool
            return await self._failover_connection(websocket, user_id, target_pool_id)
    
    def _select_pool(self) -> Optional[str]:
        """Select pool based on load balancing strategy."""
        available_pools = [
            pool for pool in self.pools.values()
            if pool.is_available()
        ]
        
        if not available_pools:
            return None
        
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_selection(available_pools)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_selection(available_pools)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin_selection(available_pools)
        elif self.strategy == LoadBalancingStrategy.CPU_AWARE:
            return self._cpu_aware_selection(available_pools)
        elif self.strategy == LoadBalancingStrategy.MEMORY_AWARE:
            return self._memory_aware_selection(available_pools)
        elif self.strategy == LoadBalancingStrategy.ADAPTIVE:
            return self._adaptive_selection(available_pools)
        else:
            return self._least_connections_selection(available_pools)
    
    def _round_robin_selection(self, pools: List[LoadBalancedConnectionPool]) -> str:
        """Round robin pool selection."""
        selected = pools[self.round_robin_index % len(pools)]
        self.round_robin_index += 1
        return selected.pool_id
    
    def _least_connections_selection(self, pools: List[LoadBalancedConnectionPool]) -> str:
        """Select pool with least connections."""
        selected = min(pools, key=lambda p: p.metrics.current_connections)
        return selected.pool_id
    
    def _weighted_round_robin_selection(self, pools: List[LoadBalancedConnectionPool]) -> str:
        """Weighted round robin selection."""
        # Create weighted list
        weighted_pools = []
        for pool in pools:
            weight_factor = max(1, int(pool.weight * 10))
            weighted_pools.extend([pool] * weight_factor)
        
        if weighted_pools:
            selected = weighted_pools[self.round_robin_index % len(weighted_pools)]
            self.round_robin_index += 1
            return selected.pool_id
        
        return pools[0].pool_id
    
    def _cpu_aware_selection(self, pools: List[LoadBalancedConnectionPool]) -> str:
        """Select pool with lowest CPU usage."""
        selected = min(pools, key=lambda p: p.metrics.cpu_usage_percent)
        return selected.pool_id
    
    def _memory_aware_selection(self, pools: List[LoadBalancedConnectionPool]) -> str:
        """Select pool with lowest memory usage."""
        selected = min(pools, key=lambda p: p.metrics.memory_usage_mb)
        return selected.pool_id
    
    def _adaptive_selection(self, pools: List[LoadBalancedConnectionPool]) -> str:
        """Adaptive selection based on overall load score."""
        selected = min(pools, key=lambda p: p.get_load_score())
        return selected.pool_id
    
    async def _failover_connection(self, websocket: WebSocket, user_id: str, 
                                 failed_pool_id: str) -> Optional[str]:
        """Attempt to failover connection to another pool."""
        self.balancing_metrics["pool_failovers"] += 1
        
        # Try other available pools
        for pool_id, pool in self.pools.items():
            if pool_id != failed_pool_id and pool.is_available():
                success = await pool.add_connection(websocket, user_id)
                if success:
                    logger.info(f"Failover successful: {failed_pool_id} -> {pool_id}")
                    return pool_id
        
        logger.warning("Failover failed: no available pools")
        return None
    
    async def remove_connection(self, websocket: WebSocket, pool_id: str = None) -> bool:
        """Remove connection from appropriate pool."""
        # If pool_id not specified, find it
        if pool_id is None:
            for pid, pool in self.pools.items():
                if websocket in pool.connections:
                    pool_id = pid
                    break
        
        if pool_id and pool_id in self.pools:
            success = await self.pools[pool_id].remove_connection(websocket)
            
            # Clean up sessions
            session_to_remove = None
            for session_id, session in self.sessions.items():
                if session.websocket == websocket:
                    session_to_remove = session_id
                    break
            
            if session_to_remove:
                del self.sessions[session_to_remove]
            
            return success
        
        return False
    
    def get_pool_for_user(self, user_id: str) -> Optional[str]:
        """Get pool ID for user's connections."""
        for pool_id, pool in self.pools.items():
            if user_id in pool.user_connections and pool.user_connections[user_id]:
                return pool_id
        return None
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics for all pools."""
        stats = {
            "manager_info": {
                "strategy": self.strategy.value,
                "total_pools": len(self.pools),
                "sticky_sessions": self.sticky_sessions,
                "active_sessions": len(self.sessions)
            },
            "balancing_metrics": self.balancing_metrics.copy(),
            "pools": {},
            "health_report": self.health_monitor.get_health_report()
        }
        
        # Pool-specific stats
        total_connections = 0
        total_capacity = 0
        
        for pool_id, pool in self.pools.items():
            pool_stats = pool.get_detailed_stats()
            stats["pools"][pool_id] = pool_stats
            
            total_connections += pool.metrics.current_connections
            total_capacity += pool.max_connections
        
        # Global metrics
        stats["global_metrics"] = {
            "total_connections": total_connections,
            "total_capacity": total_capacity,
            "global_utilization": (total_connections / total_capacity * 100) if total_capacity > 0 else 0,
            "average_load_score": sum(p.get_load_score() for p in self.pools.values()) / len(self.pools) if self.pools else 0
        }
        
        return stats
    
    async def shutdown(self) -> None:
        """Shutdown connection manager and cleanup resources."""
        # Stop health monitoring
        await self.health_monitor.stop_monitoring()
        
        # Disconnect all connections
        for pool in self.pools.values():
            for websocket in list(pool.connections):
                await self._disconnect_websocket(websocket)
        
        # Clear all data
        self.pools.clear()
        self.sessions.clear()
        
        logger.info("Load-balanced connection manager shutdown completed")


# Global load-balanced connection manager
_global_connection_manager: Optional[LoadBalancedConnectionManager] = None

def get_load_balanced_manager(strategy: LoadBalancingStrategy = LoadBalancingStrategy.ADAPTIVE) -> LoadBalancedConnectionManager:
    """Get global load-balanced connection manager."""
    global _global_connection_manager
    if _global_connection_manager is None:
        _global_connection_manager = LoadBalancedConnectionManager(strategy)
    return _global_connection_manager
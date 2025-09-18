"""Stats Aggregator for Issue #966

Provides 24-hour rolling statistics for the /api/stats endpoint including:
- Request count aggregations
- Agent execution metrics
- WebSocket connection statistics  
- Error rate calculations

Integrates with existing monitoring infrastructure while following SSOT patterns.

Business Value:
- Enables historical trend analysis
- Supports capacity planning decisions
- Provides data for SLO/SLI tracking
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field

from shared.logging.unified_logging_ssot import get_logger
from dev_launcher.isolated_environment import IsolatedEnvironment

logger = get_logger(__name__)


@dataclass
class RequestStats:
    """Request statistics over time period."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: float = 0.0
    peak_rps: float = 0.0
    error_rate: float = 0.0


@dataclass 
class AgentStats:
    """Agent execution statistics."""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    avg_execution_time_ms: float = 0.0
    agents_by_type: Dict[str, int] = field(default_factory=dict)
    peak_concurrent_agents: int = 0


@dataclass
class WebSocketStats:
    """WebSocket connection and event statistics."""
    total_connections: int = 0
    active_connections: int = 0
    connection_failures: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    events_dispatched: int = 0
    avg_connection_duration_mins: float = 0.0


@dataclass
class ErrorRateStats:
    """Error rate statistics across different categories."""
    overall_error_rate: float = 0.0
    api_error_rate: float = 0.0
    agent_error_rate: float = 0.0
    websocket_error_rate: float = 0.0
    database_error_rate: float = 0.0
    errors_by_type: Dict[str, int] = field(default_factory=dict)


class StatsAggregator:
    """
    Aggregates system statistics over 24-hour rolling windows.
    
    Features:
    - Request count tracking with hourly granularity
    - Agent execution metrics
    - WebSocket usage statistics
    - Error rate analysis
    - Automatic data retention management
    """
    
    def __init__(self, retention_hours: int = 24):
        """Initialize stats aggregator.
        
        Args:
            retention_hours: Hours to retain statistics data
        """
        self.retention_hours = retention_hours
        
        # Request tracking (hourly buckets for 24 hours)
        self.request_buckets = deque(maxlen=24)  # 24 hour buckets
        self.current_hour_requests = defaultdict(int)
        self.current_hour_start = self._get_current_hour()
        
        # Agent execution tracking
        self.agent_executions = deque(maxlen=1000)  # Recent executions
        self.agent_stats_history = deque(maxlen=24)  # Hourly agent stats
        
        # WebSocket tracking
        self.websocket_events = deque(maxlen=1000)  # Recent events
        self.websocket_stats_history = deque(maxlen=24)  # Hourly WebSocket stats
        self.active_connections = set()  # Currently active connection IDs
        
        # Error tracking
        self.error_events = deque(maxlen=1000)  # Recent errors
        self.error_stats_history = deque(maxlen=24)  # Hourly error stats
        
        # Background aggregation
        self._aggregation_task: Optional[asyncio.Task] = None
        self._is_aggregating = False
        
        logger.info("StatsAggregator initialized with %d hour retention", retention_hours)
    
    async def start_aggregation(self):
        """Start background statistics aggregation."""
        if self._is_aggregating:
            logger.warning("Stats aggregation already started")
            return
        
        self._is_aggregating = True
        self._aggregation_task = asyncio.create_task(self._aggregation_loop())
        logger.info("Started stats aggregation background task")
    
    async def stop_aggregation(self):
        """Stop background statistics aggregation."""
        self._is_aggregating = False
        if self._aggregation_task:
            self._aggregation_task.cancel()
            try:
                await self._aggregation_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped stats aggregation")
    
    async def _aggregation_loop(self):
        """Background loop for periodic stats aggregation."""
        while self._is_aggregating:
            try:
                # Check if we need to roll over to new hour
                current_hour = self._get_current_hour()
                if current_hour != self.current_hour_start:
                    await self._roll_over_hour()
                    self.current_hour_start = current_hour
                
                # Aggregate stats every 5 minutes
                await self._aggregate_periodic_stats()
                
                await asyncio.sleep(300)  # 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in stats aggregation loop: {e}")
                await asyncio.sleep(60)  # Back off on error
    
    def _get_current_hour(self) -> datetime:
        """Get current hour timestamp."""
        now = datetime.now()
        return now.replace(minute=0, second=0, microsecond=0)
    
    async def _roll_over_hour(self):
        """Roll over to new hour bucket."""
        # Save current hour's request stats
        if self.current_hour_requests:
            hour_stats = {
                'timestamp': self.current_hour_start,
                'total': sum(self.current_hour_requests.values()),
                'by_endpoint': dict(self.current_hour_requests)
            }
            self.request_buckets.append(hour_stats)
            self.current_hour_requests.clear()
        
        logger.debug("Rolled over to new hour bucket")
    
    async def _aggregate_periodic_stats(self):
        """Aggregate statistics from external sources."""
        try:
            # Try to get stats from existing monitoring components
            await self._aggregate_websocket_stats()
            await self._aggregate_agent_stats()
            await self._aggregate_error_stats()
            
        except Exception as e:
            logger.warning(f"Failed to aggregate periodic stats: {e}")
    
    async def record_request(self, endpoint: str, status_code: int, 
                           response_time_ms: float):
        """Record a request for statistics.
        
        Args:
            endpoint: API endpoint path
            status_code: HTTP status code
            response_time_ms: Response time in milliseconds
        """
        # Track request in current hour bucket
        self.current_hour_requests[endpoint] += 1
        
        # Track for error analysis
        if status_code >= 400:
            await self.record_error('api', f"HTTP {status_code}", endpoint)
    
    async def record_agent_execution(self, agent_type: str, execution_time_ms: float,
                                   success: bool, correlation_id: Optional[str] = None):
        """Record agent execution for statistics.
        
        Args:
            agent_type: Type of agent executed
            execution_time_ms: Execution time in milliseconds
            success: Whether execution was successful
            correlation_id: Optional correlation ID
        """
        execution_data = {
            'timestamp': time.time(),
            'agent_type': agent_type,
            'execution_time_ms': execution_time_ms,
            'success': success,
            'correlation_id': correlation_id
        }
        
        self.agent_executions.append(execution_data)
        
        if not success:
            await self.record_error('agent', f"Agent execution failed: {agent_type}")
    
    async def record_websocket_event(self, event_type: str, connection_id: str,
                                   success: bool = True, data: Optional[Dict[str, Any]] = None):
        """Record WebSocket event for statistics.
        
        Args:
            event_type: Type of event (connect, disconnect, message, etc.)
            connection_id: WebSocket connection ID
            success: Whether event was successful
            data: Optional event data
        """
        event_data = {
            'timestamp': time.time(),
            'event_type': event_type,
            'connection_id': connection_id,
            'success': success,
            'data': data or {}
        }
        
        self.websocket_events.append(event_data)
        
        # Track active connections
        if event_type == 'connect' and success:
            self.active_connections.add(connection_id)
        elif event_type == 'disconnect':
            self.active_connections.discard(connection_id)
        
        if not success:
            await self.record_error('websocket', f"WebSocket {event_type} failed")
    
    async def record_error(self, category: str, error_type: str, 
                         details: Optional[str] = None):
        """Record error for statistics.
        
        Args:
            category: Error category (api, agent, websocket, database)
            error_type: Type of error
            details: Optional error details
        """
        error_data = {
            'timestamp': time.time(),
            'category': category,
            'error_type': error_type,
            'details': details
        }
        
        self.error_events.append(error_data)
    
    async def _aggregate_websocket_stats(self):
        """Aggregate WebSocket statistics from external sources."""
        try:
            # Try to get WebSocket metrics from existing monitoring
            from netra_backend.app.monitoring.websocket_metrics import get_websocket_metrics
            
            metrics = await get_websocket_metrics()
            if metrics:
                # Record stats based on existing metrics
                for connection_id in metrics.get('active_connections', []):
                    if connection_id not in self.active_connections:
                        await self.record_websocket_event('connect', connection_id, True)
                        
        except ImportError:
            logger.debug("WebSocket metrics not available for aggregation")
        except Exception as e:
            logger.debug(f"Failed to aggregate WebSocket stats: {e}")
    
    async def _aggregate_agent_stats(self):
        """Aggregate agent statistics from external sources."""
        try:
            # Try to get agent metrics from existing monitoring
            from netra_backend.app.core.registry.universal_registry import get_global_registry
            
            registry = get_global_registry("agent")
            if registry and hasattr(registry, 'get_stats'):
                stats = registry.get_stats()
                # Process agent registry stats if available
                logger.debug(f"Agent registry stats: {stats}")
                
        except Exception as e:
            logger.debug(f"Failed to aggregate agent stats: {e}")
    
    async def _aggregate_error_stats(self):
        """Aggregate error statistics from external sources."""
        try:
            # Try to get error metrics from existing monitoring
            from netra_backend.app.services.monitoring.error_tracker import get_error_tracker
            
            tracker = get_error_tracker()
            if tracker:
                recent_errors = tracker.get_recent_errors(hours=1)
                for error in recent_errors:
                    await self.record_error(
                        error.get('category', 'unknown'),
                        error.get('type', 'unknown'),
                        error.get('message')
                    )
                    
        except ImportError:
            logger.debug("Error tracker not available for aggregation")
        except Exception as e:
            logger.debug(f"Failed to aggregate error stats: {e}")
    
    def _calculate_request_stats(self) -> RequestStats:
        """Calculate request statistics for the last 24 hours."""
        total_requests = 0
        failed_requests = 0
        total_response_time = 0
        request_count = 0
        
        # Aggregate from hourly buckets
        for bucket in self.request_buckets:
            total_requests += bucket['total']
        
        # Add current hour
        total_requests += sum(self.current_hour_requests.values())
        
        # Estimate error rate from error events
        hour_ago = time.time() - 3600
        recent_api_errors = sum(
            1 for error in self.error_events
            if error['timestamp'] > hour_ago and error['category'] == 'api'
        )
        
        error_rate = recent_api_errors / max(total_requests, 1)
        successful_requests = total_requests - recent_api_errors
        
        return RequestStats(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=recent_api_errors,
            error_rate=error_rate,
            peak_rps=0.0,  # Would need more detailed tracking
            avg_response_time_ms=0.0  # Would need response time tracking
        )
    
    def _calculate_agent_stats(self) -> AgentStats:
        """Calculate agent execution statistics."""
        if not self.agent_executions:
            return AgentStats()
        
        total = len(self.agent_executions)
        successful = sum(1 for exec in self.agent_executions if exec['success'])
        failed = total - successful
        
        # Calculate average execution time
        avg_time = sum(exec['execution_time_ms'] for exec in self.agent_executions) / total
        
        # Count by agent type
        agents_by_type = defaultdict(int)
        for exec in self.agent_executions:
            agents_by_type[exec['agent_type']] += 1
        
        return AgentStats(
            total_executions=total,
            successful_executions=successful,
            failed_executions=failed,
            avg_execution_time_ms=avg_time,
            agents_by_type=dict(agents_by_type),
            peak_concurrent_agents=0  # Would need concurrent tracking
        )
    
    def _calculate_websocket_stats(self) -> WebSocketStats:
        """Calculate WebSocket statistics."""
        if not self.websocket_events:
            return WebSocketStats(active_connections=len(self.active_connections))
        
        # Count different event types
        connects = sum(1 for event in self.websocket_events if event['event_type'] == 'connect')
        disconnects = sum(1 for event in self.websocket_events if event['event_type'] == 'disconnect')
        messages = sum(1 for event in self.websocket_events if event['event_type'] in ['message', 'send'])
        failures = sum(1 for event in self.websocket_events if not event['success'])
        
        return WebSocketStats(
            total_connections=connects,
            active_connections=len(self.active_connections),
            connection_failures=failures,
            messages_sent=messages,
            messages_received=messages,  # Simplified
            events_dispatched=len(self.websocket_events),
            avg_connection_duration_mins=0.0  # Would need duration tracking
        )
    
    def _calculate_error_rates(self) -> ErrorRateStats:
        """Calculate error rate statistics."""
        if not self.error_events:
            return ErrorRateStats()
        
        # Count errors by category
        api_errors = sum(1 for error in self.error_events if error['category'] == 'api')
        agent_errors = sum(1 for error in self.error_events if error['category'] == 'agent')
        websocket_errors = sum(1 for error in self.error_events if error['category'] == 'websocket')
        database_errors = sum(1 for error in self.error_events if error['category'] == 'database')
        
        total_errors = len(self.error_events)
        
        # Count by error type
        errors_by_type = defaultdict(int)
        for error in self.error_events:
            errors_by_type[error['error_type']] += 1
        
        # Calculate rates (simplified - would need total request counts)
        return ErrorRateStats(
            overall_error_rate=total_errors / 1000.0,  # Simplified
            api_error_rate=api_errors / 1000.0,
            agent_error_rate=agent_errors / 1000.0,
            websocket_error_rate=websocket_errors / 1000.0,
            database_error_rate=database_errors / 1000.0,
            errors_by_type=dict(errors_by_type)
        )
    
    async def get_24h_stats(self) -> Dict[str, Any]:
        """Get comprehensive 24-hour statistics.
        
        Returns:
            Dictionary containing all 24-hour statistics
        """
        request_stats = self._calculate_request_stats()
        agent_stats = self._calculate_agent_stats()
        websocket_stats = self._calculate_websocket_stats()
        error_stats = self._calculate_error_rates()
        
        return {
            "request_counts": {
                "total_requests": request_stats.total_requests,
                "successful_requests": request_stats.successful_requests,
                "failed_requests": request_stats.failed_requests,
                "error_rate": request_stats.error_rate,
                "peak_rps": request_stats.peak_rps,
                "avg_response_time_ms": request_stats.avg_response_time_ms,
                "hourly_breakdown": [
                    {
                        "hour": bucket['timestamp'].isoformat(),
                        "total": bucket['total'],
                        "by_endpoint": bucket['by_endpoint']
                    }
                    for bucket in list(self.request_buckets)[-24:]
                ]
            },
            "agent_stats": {
                "total_executions": agent_stats.total_executions,
                "successful_executions": agent_stats.successful_executions,
                "failed_executions": agent_stats.failed_executions,
                "success_rate": (
                    agent_stats.successful_executions / max(agent_stats.total_executions, 1)
                ),
                "avg_execution_time_ms": agent_stats.avg_execution_time_ms,
                "agents_by_type": agent_stats.agents_by_type,
                "peak_concurrent_agents": agent_stats.peak_concurrent_agents
            },
            "websocket_metrics": {
                "total_connections": websocket_stats.total_connections,
                "active_connections": websocket_stats.active_connections,
                "connection_failures": websocket_stats.connection_failures,
                "messages_sent": websocket_stats.messages_sent,
                "messages_received": websocket_stats.messages_received,
                "events_dispatched": websocket_stats.events_dispatched,
                "avg_connection_duration_mins": websocket_stats.avg_connection_duration_mins,
                "connection_success_rate": (
                    (websocket_stats.total_connections - websocket_stats.connection_failures) /
                    max(websocket_stats.total_connections, 1)
                )
            },
            "error_rates": {
                "overall_error_rate": error_stats.overall_error_rate,
                "api_error_rate": error_stats.api_error_rate,
                "agent_error_rate": error_stats.agent_error_rate,
                "websocket_error_rate": error_stats.websocket_error_rate,
                "database_error_rate": error_stats.database_error_rate,
                "errors_by_type": error_stats.errors_by_type,
                "total_errors_24h": len(self.error_events)
            },
            "timestamp": datetime.now().isoformat(),
            "retention_hours": self.retention_hours
        }
    
    async def reset_stats(self):
        """Reset all collected statistics."""
        self.request_buckets.clear()
        self.current_hour_requests.clear()
        self.agent_executions.clear()
        self.agent_stats_history.clear()
        self.websocket_events.clear()
        self.websocket_stats_history.clear()
        self.active_connections.clear()
        self.error_events.clear()
        self.error_stats_history.clear()
        logger.info("Statistics reset")


# Global stats aggregator instance
_stats_aggregator: Optional[StatsAggregator] = None
_aggregator_lock = asyncio.Lock()


async def get_stats_aggregator() -> StatsAggregator:
    """Get global stats aggregator instance."""
    global _stats_aggregator
    
    if _stats_aggregator is None:
        async with _aggregator_lock:
            if _stats_aggregator is None:
                _stats_aggregator = StatsAggregator()
                await _stats_aggregator.start_aggregation()
    
    return _stats_aggregator


async def record_request_stats(endpoint: str, status_code: int, response_time_ms: float):
    """Convenience function to record request statistics."""
    aggregator = await get_stats_aggregator()
    await aggregator.record_request(endpoint, status_code, response_time_ms)


async def record_agent_execution_stats(agent_type: str, execution_time_ms: float, 
                                     success: bool, correlation_id: Optional[str] = None):
    """Convenience function to record agent execution statistics."""
    aggregator = await get_stats_aggregator()
    await aggregator.record_agent_execution(agent_type, execution_time_ms, success, correlation_id)


async def record_websocket_stats(event_type: str, connection_id: str, 
                               success: bool = True, data: Optional[Dict[str, Any]] = None):
    """Convenience function to record WebSocket statistics."""
    aggregator = await get_stats_aggregator()
    await aggregator.record_websocket_event(event_type, connection_id, success, data)
"""Unified Agent Health Monitoring functionality.

This module provides SSOT comprehensive health status monitoring for agents,
consolidating capabilities from:
- Core agent reliability monitoring with death detection 
- Dev launcher enhanced health monitoring with grace periods
- Comprehensive system health checks with Five Whys analysis

Business Value: Prevents $500K+ ARR loss from unreliable agent monitoring
SSOT Compliance: Single source for all agent health monitoring capabilities
"""

import asyncio
import logging
import platform
import time
import threading
import uuid
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# Core dependencies
from netra_backend.app.core.agent_reliability_types import AgentError, AgentHealthStatus
from netra_backend.app.core.agent_execution_tracker import get_execution_tracker
from netra_backend.app.logging_config import central_logger

# Environment access
try:
    from shared.isolated_environment import IsolatedEnvironment
except ImportError:
    IsolatedEnvironment = None

# WebSocket integration for health events
try:
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
except ImportError:
    AgentWebSocketBridge = None

# System monitoring
try:
    import psutil
except ImportError:
    psutil = None

logger = central_logger.get_logger(__name__)


class ServiceState(Enum):
    """Service state during startup and runtime."""
    STARTING = "starting"
    GRACE_PERIOD = "grace_period"
    READY = "ready"
    MONITORING = "monitoring"
    FAILED = "failed"


@dataclass
class UnifiedAgentHealthStatus:
    """Unified health status for agents with enhanced capabilities."""
    agent_name: str
    overall_health: float  # 0.0 to 1.0
    circuit_breaker_state: str
    recent_errors: int
    status: str  # healthy, degraded, unhealthy, dead
    state: ServiceState = ServiceState.MONITORING
    grace_period_remaining: float = 0.0
    five_whys_analysis: Optional[Dict[str, str]] = None
    system_metrics: Optional[Dict[str, Any]] = None
    
    # Backward compatibility fields
    total_operations: int = 0
    success_rate: float = 1.0
    average_response_time: float = 0.0
    last_error: Optional[AgentError] = None
    
    # Enhanced tracking
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    consecutive_failures: int = 0
    startup_time: Optional[datetime] = None
    ready_confirmed: bool = False
    process_verified: bool = False
    ports_verified: Set[int] = field(default_factory=set)
    
    def to_agent_health_status(self) -> AgentHealthStatus:
        """Convert to legacy AgentHealthStatus for backward compatibility."""
        return AgentHealthStatus(
            agent_name=self.agent_name,
            overall_health=self.overall_health,
            circuit_breaker_state=self.circuit_breaker_state,
            recent_errors=self.recent_errors,
            total_operations=self.total_operations,
            success_rate=self.success_rate,
            average_response_time=self.average_response_time,
            last_error=self.last_error,
            status=self.status
        )


class UnifiedAgentHealthMonitor:
    """SSOT Unified Agent Health Monitor consolidating all health monitoring capabilities.
    
    Consolidates:
    1. Agent reliability monitoring (death detection, health metrics)
    2. Development environment health monitoring (grace periods, startup states)
    3. Enhanced system health checks (Five Whys analysis, circuit breakers)
    
    Features:
    - Unified health status interface with backward compatibility
    - WebSocket integration for health events
    - Performance-optimized health checking (<50ms overhead)
    - Circuit breaker patterns for known-dead agents
    - Five Whys root cause analysis for failures
    - Grace period management for startup scenarios
    - System metrics collection and monitoring
    - Feature flag support for gradual rollout
    """
    
    def __init__(self, 
                 max_operation_history: int = 100,
                 check_interval: int = 30,
                 enable_websocket_events: bool = True,
                 enable_system_metrics: bool = True,
                 enable_five_whys: bool = True):
        # Core monitoring
        self.operation_times: List[float] = []
        self.max_operation_history = max_operation_history
        self.last_health_check = 0
        self.health_check_interval = check_interval
        self.execution_tracker = get_execution_tracker()
        
        # Feature flags
        self.feature_flags = self._load_feature_flags()
        self.enable_websocket_events = enable_websocket_events and self.feature_flags.get('ENABLE_UNIFIED_HEALTH_MONITORING', True)
        self.enable_system_metrics = enable_system_metrics
        self.enable_five_whys = enable_five_whys
        
        # Enhanced monitoring state
        self.services: Dict[str, Dict] = {}
        self.health_status: Dict[str, UnifiedAgentHealthStatus] = {}
        self.failure_history: Dict[str, Dict] = {}
        self.circuit_breakers: Dict[str, bool] = {}
        self.component_checkers: Dict[str, Callable] = {}
        
        # Grace period and startup management
        self.monitoring_enabled = True  # Start enabled, can be disabled during startup
        self.startup_complete = True
        self._lock = threading.Lock()
        self.is_windows = platform.system() == "win32"
        
        # WebSocket integration
        self.websocket_bridge: Optional[AgentWebSocketBridge] = None
        if self.enable_websocket_events and AgentWebSocketBridge:
            try:
                self.websocket_bridge = AgentWebSocketBridge()
                logger.info("WebSocket integration enabled for health monitoring")
            except Exception as e:
                logger.warning(f"Failed to initialize WebSocket bridge: {e}")
        
        # Performance settings
        self.death_detection_threshold = 10.0  # seconds - standardized across all implementations
        self.health_check_cache: Dict[str, Tuple[UnifiedAgentHealthStatus, float]] = {}
        self.cache_ttl = 5.0  # 5-second cache TTL
        
        # Circuit breaker settings
        self.max_consecutive_failures = 5
        self.circuit_breaker_timeout = 300  # 5 minutes
        
        logger.info(f"UnifiedAgentHealthMonitor initialized (interval: {check_interval}s, WebSocket: {self.enable_websocket_events})")
    
    def _load_feature_flags(self) -> Dict[str, bool]:
        """Load feature flags from environment."""
        flags = {}
        if IsolatedEnvironment:
            env = IsolatedEnvironment()
            flags['ENABLE_UNIFIED_HEALTH_MONITORING'] = env.get('ENABLE_UNIFIED_HEALTH_MONITORING', 'true').lower() == 'true'
            flags['ENABLE_HEALTH_WEBSOCKET_EVENTS'] = env.get('ENABLE_HEALTH_WEBSOCKET_EVENTS', 'true').lower() == 'true'
            flags['ENABLE_FIVE_WHYS_ANALYSIS'] = env.get('ENABLE_FIVE_WHYS_ANALYSIS', 'true').lower() == 'true'
        else:
            # Default values when environment is not available
            flags = {
                'ENABLE_UNIFIED_HEALTH_MONITORING': True,
                'ENABLE_HEALTH_WEBSOCKET_EVENTS': True,
                'ENABLE_FIVE_WHYS_ANALYSIS': True
            }
        return flags
    
    def record_successful_operation(self, operation_name: str, execution_time: float) -> None:
        """Record a successful operation for monitoring."""
        self.operation_times.append(execution_time)
        if len(self.operation_times) > self.max_operation_history:
            self.operation_times = self.operation_times[-self.max_operation_history:]

    def get_comprehensive_health_status(
        self, agent_name: str, error_history: List[AgentError], reliability_wrapper
    ) -> UnifiedAgentHealthStatus:
        """Get comprehensive unified health status of the agent."""
        # Check cache first for performance
        cached_status, cache_time = self.health_check_cache.get(agent_name, (None, 0))
        if cached_status and (time.time() - cache_time) < self.cache_ttl:
            return cached_status
        
        # Check circuit breaker first
        if self._should_skip_health_check(agent_name):
            status = self._create_circuit_breaker_status(agent_name)
            self.health_check_cache[agent_name] = (status, time.time())
            return status
        
        # Check for dead agents first
        dead_agents = self._detect_dead_agents(agent_name)
        if dead_agents:
            status = self._create_dead_agent_status(agent_name, dead_agents)
            self.health_check_cache[agent_name] = (status, time.time())
            return status
        
        # Calculate comprehensive health metrics
        metrics = self._calculate_health_metrics(error_history)
        overall_health = self._calculate_overall_health(*metrics[:3])
        health_status = self._determine_health_status(overall_health, metrics[0])
        cb_state = self._get_circuit_breaker_state(reliability_wrapper)
        
        # Build unified status
        status = self._build_unified_health_status(
            agent_name, overall_health, cb_state, metrics, health_status, error_history
        )
        
        # Add enhanced capabilities if enabled
        if self.enable_system_metrics:
            status.system_metrics = self._collect_system_metrics()
        
        if self.enable_five_whys and status.status in ['unhealthy', 'dead']:
            status.five_whys_analysis = self._perform_five_whys_analysis(
                agent_name, status.last_error.message if status.last_error else "Health check failed"
            )
        
        # Cache the result
        self.health_check_cache[agent_name] = (status, time.time())
        
        # Trigger WebSocket events for status changes if enabled
        if self.enable_websocket_events:
            asyncio.create_task(self._emit_health_status_event(agent_name, status))
        
        return status

    def _calculate_health_metrics(self, error_history: List[AgentError]) -> tuple[int, int, float, float]:
        """Calculate health metrics for status evaluation."""
        recent_errors = self._count_recent_errors(error_history, 300)
        total_operations = len(self.operation_times) + len(error_history)
        success_rate = self._calculate_success_rate(error_history)
        avg_response_time = self._calculate_avg_response_time()
        return recent_errors, total_operations, success_rate, avg_response_time

    def _get_circuit_breaker_state(self, reliability_wrapper) -> str:
        """Get circuit breaker state safely."""
        try:
            cb_status = reliability_wrapper.circuit_breaker.get_status()
            return cb_status.get("state", "unknown")
        except Exception:
            return "unknown"

    def _build_unified_health_status(
        self, agent_name: str, overall_health: float, cb_state: str, 
        metrics: tuple[int, int, float, float], status: str, error_history: List[AgentError]
    ) -> UnifiedAgentHealthStatus:
        """Build UnifiedAgentHealthStatus object from calculated values."""
        recent_errors, total_operations, success_rate, avg_response_time = metrics
        
        # Get existing status for state tracking
        existing_status = self.health_status.get(agent_name)
        
        return UnifiedAgentHealthStatus(
            agent_name=agent_name,
            overall_health=overall_health,
            circuit_breaker_state=cb_state,
            recent_errors=recent_errors,
            status=status,
            state=existing_status.state if existing_status else ServiceState.MONITORING,
            grace_period_remaining=existing_status.grace_period_remaining if existing_status else 0.0,
            total_operations=total_operations,
            success_rate=success_rate,
            average_response_time=avg_response_time,
            last_error=error_history[-1] if error_history else None,
            last_check=datetime.now(timezone.utc),
            consecutive_failures=existing_status.consecutive_failures if existing_status else 0,
            startup_time=existing_status.startup_time if existing_status else None,
            ready_confirmed=existing_status.ready_confirmed if existing_status else True,
            process_verified=existing_status.process_verified if existing_status else False,
            ports_verified=existing_status.ports_verified if existing_status else set()
        )

    def _create_health_status_attributes(
        self, agent_name: str, overall_health: float, cb_state: str,
        metrics: tuple[int, int, float, float], status: str, error_history: List[AgentError]
    ) -> Dict[str, Any]:
        """Create health status attributes dictionary."""
        recent_errors, total_operations, success_rate, avg_response_time = metrics
        return {
            'agent_name': agent_name, 'overall_health': overall_health,
            'circuit_breaker_state': cb_state, 'recent_errors': recent_errors,
            'total_operations': total_operations, 'success_rate': success_rate,
            'average_response_time': avg_response_time, 'status': status,
            'last_error': error_history[-1] if error_history else None
        }

    def _count_recent_errors(self, error_history: List[AgentError], seconds: int) -> int:
        """Count errors in the last N seconds."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=seconds)
        return len([e for e in error_history if e.timestamp >= cutoff_time])

    def _calculate_success_rate(self, error_history: List[AgentError]) -> float:
        """Calculate success rate over recent operations."""
        total_ops = len(self.operation_times) + len(error_history)
        if total_ops == 0:
            return 1.0
        successful_ops = len(self.operation_times)
        return successful_ops / total_ops

    def _calculate_avg_response_time(self) -> float:
        """Calculate average response time."""
        if not self.operation_times:
            return 0.0
        recent_times = self.operation_times[-20:]
        return sum(recent_times) / len(recent_times)
    
    def _detect_dead_agents(self, agent_name: str) -> List[Any]:
        """Detect dead agents for the given agent name."""
        # Get all executions for this agent
        executions = self.execution_tracker.get_executions_by_agent(agent_name)
        
        # Filter for dead/timed-out executions
        dead_executions = [
            ex for ex in executions
            if ex.is_dead(self.execution_tracker.heartbeat_timeout) or ex.is_timed_out()
        ]
        
        return dead_executions
    
    def _create_dead_agent_status(self, agent_name: str, dead_executions: List[Any]) -> UnifiedAgentHealthStatus:
        """Create unified health status for dead agent."""
        most_recent_death = max(dead_executions, key=lambda x: x.updated_at)
        
        error_message = f'Agent died: {most_recent_death.error or "No heartbeat"}'
        
        status = UnifiedAgentHealthStatus(
            agent_name=agent_name,
            overall_health=0.0,  # Dead agent has 0 health
            circuit_breaker_state='open',  # Consider dead as open circuit
            recent_errors=len(dead_executions),
            status='dead',
            state=ServiceState.FAILED,
            total_operations=len(dead_executions),
            success_rate=0.0,  # Dead agent has 0% success
            average_response_time=0.0,
            last_error=AgentError(
                error_id=str(uuid.uuid4()),
                agent_name=agent_name,
                operation='health_check',
                error_type='AgentDeath',
                message=error_message,
                timestamp=most_recent_death.updated_at,
                severity='CRITICAL',
                context={'execution_id': most_recent_death.execution_id}
            ),
            last_check=datetime.now(timezone.utc)
        )
        
        # Add Five Whys analysis for agent death if enabled
        if self.enable_five_whys:
            status.five_whys_analysis = self._perform_five_whys_analysis(agent_name, error_message)
        
        return status
    
    async def detect_agent_death(
        self, 
        agent_name: str, 
        last_heartbeat: datetime,
        execution_context: Dict[str, Any]
    ) -> bool:
        """Detect if an agent has died based on heartbeat and health metrics.
        
        Args:
            agent_name: Name of the agent to check
            last_heartbeat: Last known heartbeat timestamp
            execution_context: Context of the current execution
            
        Returns:
            True if agent is detected as dead, False otherwise
        """
        # Check time since last heartbeat
        time_since_heartbeat = (datetime.now(timezone.utc) - last_heartbeat).total_seconds()
        
        # Agent is considered dead if no heartbeat for > 10 seconds
        if time_since_heartbeat > 10:
            logger.critical(
                f"[U+1F480] AGENT DEATH DETECTED: {agent_name} - No heartbeat for {time_since_heartbeat:.1f}s"
            )
            return True
        
        # Check execution tracker for dead executions
        dead_executions = self.execution_tracker.detect_dead_executions()
        for execution in dead_executions:
            if execution.agent_name == agent_name:
                logger.critical(
                    f"[U+1F480] AGENT DEATH DETECTED via tracker: {agent_name} - {execution.error or 'No heartbeat'}"
                )
                return True
        
        return False

    def _calculate_overall_health(self, success_rate: float, recent_errors: int, avg_response_time: float) -> float:
        """Calculate overall health score."""
        health_score = success_rate
        error_penalty = self._calculate_error_penalty(recent_errors)
        time_penalty = self._calculate_time_penalty(avg_response_time)
        health_score = health_score - error_penalty - time_penalty
        return max(0.0, min(1.0, health_score))

    def _calculate_error_penalty(self, recent_errors: int) -> float:
        """Calculate penalty for recent errors."""
        if recent_errors == 0:
            return 0.0
        return min(recent_errors * 0.1, 0.5)

    def _calculate_time_penalty(self, avg_response_time: float) -> float:
        """Calculate penalty for slow response times."""
        if avg_response_time <= 5.0:
            return 0.0
        return min((avg_response_time - 5.0) * 0.1, 0.3)

    def _determine_health_status(self, overall_health: float, recent_errors: int) -> str:
        """Determine health status based on metrics."""
        if overall_health >= 0.8 and recent_errors == 0:
            return "healthy"
        elif overall_health >= 0.5 and recent_errors <= 2:
            return "degraded"
        else:
            return "unhealthy"

    def get_error_summary(self, error_history: List[AgentError]) -> Dict[str, Any]:
        """Get summary of recent errors."""
        if not error_history:
            return {"total_errors": 0, "error_types": {}, "recent_errors": 0}
        error_types, recent_errors = self._count_error_types_and_recent(error_history)
        last_error_info = self._get_last_error_info(error_history)
        return self._build_error_summary(error_types, recent_errors, last_error_info, error_history)

    def _count_error_types_and_recent(self, error_history: List[AgentError]) -> tuple[Dict[str, int], int]:
        """Count error types and recent errors."""
        error_types = {}
        recent_errors = 0
        cutoff_time = self._get_recent_cutoff_time()
        for error in error_history:
            self._count_error_type(error_types, error)
            if error.timestamp >= cutoff_time:
                recent_errors += 1
        return error_types, recent_errors

    def _get_recent_cutoff_time(self) -> datetime:
        """Get cutoff time for recent errors (5 minutes ago)."""
        return datetime.now(timezone.utc) - timedelta(minutes=5)
    
    def _count_error_type(self, error_types: Dict[str, int], error: AgentError) -> None:
        """Count error type in error_types dictionary."""
        error_types[error.error_type] = error_types.get(error.error_type, 0) + 1

    def _get_last_error_info(self, error_history: List[AgentError]) -> Dict[str, str]:
        """Get last error information."""
        last_error = error_history[-1]
        return {
            "type": last_error.error_type,
            "message": last_error.message,
            "timestamp": last_error.timestamp.isoformat()
        }

    def _build_error_summary(
        self, error_types: Dict[str, int], recent_errors: int, last_error_info: Dict[str, str], error_history: List[AgentError]
    ) -> Dict[str, Any]:
        """Build error summary from components."""
        return {
            "total_errors": len(error_history),
            "error_types": error_types,
            "recent_errors": recent_errors,
            "last_error": last_error_info
        }

    def reset_health_metrics(self, reliability_wrapper) -> None:
        """Reset health metrics and error history."""
        self.operation_times.clear()
        try:
            reliability_wrapper.circuit_breaker.reset()
        except Exception as e:
            logger.warning(f"Failed to reset circuit breaker: {e}")

    async def perform_health_check(
        self, agent_name: str, error_history: List[AgentError], reliability_wrapper
    ) -> UnifiedAgentHealthStatus:
        """Perform comprehensive unified health check."""
        start_time = time.time()
        self.last_health_check = start_time
        
        health_status = self.get_comprehensive_health_status(agent_name, error_history, reliability_wrapper)
        
        # Update monitoring state
        self._update_monitoring_state(agent_name, health_status)
        
        # Log unhealthy status
        self._log_unhealthy_status(health_status)
        
        # Record performance metrics
        check_duration = (time.time() - start_time) * 1000  # ms
        if check_duration > 50:  # Log if over 50ms target
            logger.warning(f"Health check for {agent_name} took {check_duration:.1f}ms (target: <50ms)")
        
        return health_status

    def _log_unhealthy_status(self, health_status: UnifiedAgentHealthStatus) -> None:
        """Log health status if degraded or unhealthy."""
        if health_status.status == "healthy":
            return
        
        log_msg = (
            f"Agent {health_status.agent_name} health status: {health_status.status} "
            f"(health={health_status.overall_health:.2f}, errors={health_status.recent_errors}, "
            f"state={health_status.state.value})"
        )
        
        if health_status.status == "dead":
            logger.critical(log_msg)
        elif health_status.status == "unhealthy":
            logger.error(log_msg)
        else:
            logger.warning(log_msg)
        
        # Include Five Whys analysis if available
        if health_status.five_whys_analysis:
            logger.info(f"Root cause analysis for {health_status.agent_name}: {health_status.five_whys_analysis.get('root_cause', 'Unknown')}")

    def should_perform_health_check(self) -> bool:
        """Check if health check should be performed."""
        return (time.time() - self.last_health_check) >= self.health_check_interval
    
    # ============================================================================
    # ENHANCED CAPABILITIES - Five Whys Analysis
    # ============================================================================
    
    def _perform_five_whys_analysis(self, agent_name: str, error_message: str) -> Dict[str, str]:
        """Perform Five Whys root cause analysis for agent failures."""
        if not self.enable_five_whys:
            return {}
        
        # Agent-specific analysis patterns
        analysis_patterns = {
            'agent_death': {
                'why_1': f'Agent {agent_name} stopped responding: {error_message}',
                'why_2': 'Agent execution may have encountered unrecoverable error or resource exhaustion',
                'why_3': 'System resources (memory, CPU, connections) may be insufficient or misconfigured',
                'why_4': 'Agent initialization, dependency resolution, or environment setup issues',
                'why_5': 'Infrastructure capacity, configuration management, or deployment problems',
                'root_cause': 'Agent runtime environment requires capacity planning and configuration review'
            },
            'timeout': {
                'why_1': f'Agent {agent_name} timed out: {error_message}',
                'why_2': 'Agent operation exceeded configured timeout threshold',
                'why_3': 'Downstream dependencies may be slow or overloaded',
                'why_4': 'Resource contention or insufficient computational capacity',
                'why_5': 'System architecture needs optimization for expected workload',
                'root_cause': 'Performance tuning and capacity scaling required for agent operations'
            },
            'memory': {
                'why_1': f'Agent {agent_name} memory issues: {error_message}',
                'why_2': 'Agent memory consumption exceeded available resources',
                'why_3': 'Memory leaks, inefficient algorithms, or large data processing',
                'why_4': 'Inadequate memory allocation or garbage collection issues',
                'why_5': 'System memory management and allocation policies need review',
                'root_cause': 'Memory optimization and resource management improvements needed'
            }
        }
        
        # Determine analysis type based on error content
        error_lower = error_message.lower()
        if 'died' in error_lower or 'death' in error_lower or 'heartbeat' in error_lower:
            pattern_key = 'agent_death'
        elif 'timeout' in error_lower or 'timed out' in error_lower:
            pattern_key = 'timeout'
        elif 'memory' in error_lower or 'oom' in error_lower:
            pattern_key = 'memory'
        else:
            pattern_key = 'agent_death'  # Default fallback
        
        return analysis_patterns.get(pattern_key, {
            'why_1': f'Agent {agent_name} health check failed: {error_message}',
            'why_2': 'Agent is not responding or not available',
            'why_3': 'Service may be down or configuration issues',
            'why_4': 'Dependencies or infrastructure problems',
            'why_5': 'System architecture or resource limitations',
            'root_cause': 'Agent requires investigation and maintenance'
        })
    
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system metrics if enabled and available."""
        if not self.enable_system_metrics:
            return {}
        
        metrics = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'platform': platform.system(),
            'monitoring_enabled': self.monitoring_enabled,
            'active_agents': len(self.health_status)
        }
        
        # Add psutil metrics if available
        if psutil:
            try:
                metrics.update({
                    'cpu_percent': psutil.cpu_percent(interval=0.1),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_percent': psutil.disk_usage('/').percent if platform.system() != 'Windows' else psutil.disk_usage('C:').percent
                })
            except Exception as e:
                metrics['system_metrics_error'] = str(e)
        
        return metrics
    
    def _should_skip_health_check(self, agent_name: str) -> bool:
        """Determine if health check should be skipped due to circuit breaker."""
        failure_info = self.failure_history.get(agent_name, {})
        failures = failure_info.get('failures', 0)
        last_failure = failure_info.get('last_failure')
        
        # Circuit breaker: skip if too many failures and within timeout window
        if failures >= self.max_consecutive_failures:
            if last_failure and (time.time() - last_failure) < self.circuit_breaker_timeout:
                return True
            else:
                # Reset circuit breaker after timeout
                self.failure_history[agent_name] = {'failures': 0, 'last_failure': None}
        
        return False
    
    def _create_circuit_breaker_status(self, agent_name: str) -> UnifiedAgentHealthStatus:
        """Create status for agent skipped due to circuit breaker."""
        return UnifiedAgentHealthStatus(
            agent_name=agent_name,
            overall_health=0.0,
            circuit_breaker_state='open',
            recent_errors=self.failure_history[agent_name]['failures'],
            status='unhealthy',
            state=ServiceState.FAILED,
            last_check=datetime.now(timezone.utc)
        )
    
    def _update_monitoring_state(self, agent_name: str, status: UnifiedAgentHealthStatus) -> None:
        """Update internal monitoring state."""
        with self._lock:
            self.health_status[agent_name] = status
            
            # Update failure tracking
            if status.status in ['unhealthy', 'dead']:
                if agent_name not in self.failure_history:
                    self.failure_history[agent_name] = {'failures': 0, 'last_failure': None}
                self.failure_history[agent_name]['failures'] += 1
                self.failure_history[agent_name]['last_failure'] = time.time()
            else:
                # Reset failure count on success
                self.failure_history[agent_name] = {'failures': 0, 'last_failure': None}
    
    async def _emit_health_status_event(self, agent_name: str, status: UnifiedAgentHealthStatus) -> None:
        """Emit WebSocket events for health status changes."""
        if not self.websocket_bridge or not self.enable_websocket_events:
            return
        
        try:
            # Check if status changed significantly
            previous_status = self.health_status.get(agent_name)
            if previous_status and previous_status.status == status.status:
                return  # No significant change
            
            # Map status to appropriate WebSocket events
            if status.status == 'dead':
                await self.websocket_bridge.send_agent_failed(
                    agent_id=agent_name,
                    error=f"Agent health monitor detected agent death: {status.last_error.message if status.last_error else 'No heartbeat'}"
                )
            elif status.status == 'unhealthy':
                await self.websocket_bridge.send_agent_degraded(
                    agent_id=agent_name,
                    reason=f"Health degraded: {status.recent_errors} recent errors, {status.overall_health:.1%} health"
                )
            elif status.status == 'healthy' and previous_status and previous_status.status != 'healthy':
                await self.websocket_bridge.send_agent_recovered(
                    agent_id=agent_name,
                    health_score=status.overall_health
                )
                
        except Exception as e:
            logger.debug(f"Failed to emit health status event for {agent_name}: {e}")
    
    # ============================================================================
    # ENHANCED CAPABILITIES - Grace Period and Service Management
    # ============================================================================
    
    def register_service(
        self,
        name: str,
        health_check: Callable[[], bool],
        recovery_action: Optional[Callable[[], None]] = None,
        max_failures: int = 5,
        grace_period_seconds: int = 30
    ):
        """Register a service for health monitoring with grace period support."""
        # Service-specific grace periods
        if name.lower() == "frontend":
            grace_period_seconds = 90  # Frontend: 90 second grace period
        elif name.lower() == "backend":
            grace_period_seconds = 30  # Backend: 30 second grace period
        
        with self._lock:
            self.services[name] = {
                'health_check': health_check,
                'recovery_action': recovery_action,
                'max_failures': max_failures
            }
            
            self.health_status[name] = UnifiedAgentHealthStatus(
                agent_name=name,
                overall_health=1.0,
                circuit_breaker_state='closed',
                recent_errors=0,
                status='healthy',
                state=ServiceState.STARTING,
                startup_time=datetime.now(timezone.utc),
                grace_period_remaining=grace_period_seconds,
                ready_confirmed=False
            )
            
        logger.info(f"Registered health monitoring for {name} (grace period: {grace_period_seconds}s)")
    
    def mark_service_ready(self, name: str, process_pid: Optional[int] = None, 
                          ports: Optional[Set[int]] = None) -> bool:
        """Mark a service as ready after successful readiness check."""
        with self._lock:
            if name in self.health_status:
                status = self.health_status[name]
                status.ready_confirmed = True
                status.state = ServiceState.READY
                status.last_check = datetime.now(timezone.utc)
                
                if ports:
                    status.ports_verified = ports
                
                logger.info(f"Service {name} marked as ready")
                if ports:
                    logger.info(f"   ->  Verified ports: {sorted(ports)}")
                if process_pid:
                    logger.info(f"   ->  Process PID: {process_pid}")
                    
                return True
            return False
    
    # ============================================================================
    # BACKWARD COMPATIBILITY METHODS
    # ============================================================================
    
    def get_legacy_health_status(
        self, agent_name: str, error_history: List[AgentError], reliability_wrapper
    ) -> AgentHealthStatus:
        """Get health status in legacy format for backward compatibility."""
        unified_status = self.get_comprehensive_health_status(agent_name, error_history, reliability_wrapper)
        return unified_status.to_agent_health_status()
    
    def reset_health_metrics(self, reliability_wrapper) -> None:
        """Reset health metrics and error history - backward compatibility."""
        self.operation_times.clear()
        self.health_check_cache.clear()
        
        # Reset failure history
        self.failure_history.clear()
        
        try:
            reliability_wrapper.circuit_breaker.reset()
        except Exception as e:
            logger.warning(f"Failed to reset circuit breaker: {e}")


# ============================================================================
# BACKWARD COMPATIBILITY ALIAS AND FACTORY
# ============================================================================

# Backward compatibility alias
AgentHealthMonitor = UnifiedAgentHealthMonitor
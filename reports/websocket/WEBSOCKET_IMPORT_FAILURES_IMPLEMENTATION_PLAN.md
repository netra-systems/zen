# WebSocket Import Failures - Implementation Plan
**Date:** 2025-09-08  
**Priority:** CRITICAL  
**Analysis Reference:** WEBSOCKET_CORE_UNIT_TEST_IMPORT_FAILURES_FIVE_WHYS_ANALYSIS.md  

## Implementation Summary

Based on the Five Whys analysis, we need to implement **Option 1: Complete the Refactoring** by adding the missing classes that tests expect while preserving existing functionality.

### Confirmed Import Failures
✅ **Verified via direct testing:**
1. `WebSocketEventMonitor` ← Tests expect this, but module has `ChatEventMonitor`
2. `PerformanceMetrics` ← Tests expect this, but module has shim to `PerformanceMonitor`  
3. `RateLimitExceededException` ← Tests expect this, but missing from `rate_limiter.py`
4. `WebSocketReconnectionHandler` ← Tests expect this, but module has aliases only

---

## Detailed Implementation Plan

### 1. Fix `event_monitor.py`

**Current State:**
```python
# Has: ChatEventMonitor class (working)
# Missing: WebSocketEventMonitor, EventValidationError, MissingCriticalEventError, EventTracker, EventMetrics
```

**Required Changes:**
```python
# Add alias for backward compatibility
WebSocketEventMonitor = ChatEventMonitor

# Add missing exception classes
class EventValidationError(Exception):
    """Raised when event validation fails."""
    pass

class MissingCriticalEventError(EventValidationError):
    """Raised when critical events are missing from agent execution."""
    pass

# Add missing data classes
@dataclass
class EventTracker:
    """Tracks events for a specific session."""
    user_id: str
    thread_id: str
    agent_name: str
    events_received: List[WebSocketMessage] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_complete: bool = False
    is_timeout: bool = False

@dataclass  
class EventMetrics:
    """Event timing and performance metrics."""
    session_id: str
    session_duration_ms: float
    total_events: int
    event_timings: List[EventTiming] = field(default_factory=list)
    
@dataclass
class EventTiming:
    """Individual event timing data."""
    event_type: str
    timestamp: datetime
    latency_ms: Optional[float] = None
```

**Update `__all__` exports:**
```python
__all__ = [
    'ChatEventMonitor',
    'WebSocketEventMonitor',  # New alias
    'EventValidationError',   # New
    'MissingCriticalEventError',  # New
    'EventTracker',          # New
    'EventMetrics',          # New
    'EventTiming',           # New
    'EventType',
    'HealthStatus'
]
```

### 2. Fix `performance_monitor_core.py`

**Current State:**
```python
# Has: Shim to PerformanceMonitor 
# Missing: Actual PerformanceMetrics class and related classes
```

**Required Changes:**
Replace the shim with actual classes:
```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timezone

@dataclass
class PerformanceMetrics:
    """WebSocket performance metrics collection."""
    connection_id: str
    user_id: str
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message_count: int = 0
    total_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    throughput_msg_per_sec: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0

@dataclass
class LatencyMeasurement:
    """Individual latency measurement."""
    message_id: str
    latency_ms: float
    timestamp: datetime
    message_type: str

@dataclass 
class ThroughputMetrics:
    """Throughput measurement over time window."""
    window_start: datetime
    window_end: datetime
    messages_processed: int
    avg_throughput: float
    peak_throughput: float

@dataclass
class PerformanceAlert:
    """Performance alert when thresholds exceeded."""
    alert_type: str
    threshold_exceeded: str
    current_value: float
    threshold_value: float
    timestamp: datetime
    connection_id: str

@dataclass
class PerformanceThresholds:
    """Performance threshold configuration."""
    max_message_latency_ms: int = 1000
    max_connection_time_ms: int = 3000
    min_throughput_messages_per_second: int = 10
    max_memory_usage_mb: int = 100
    max_cpu_usage_percent: int = 80

class WebSocketPerformanceMonitor:
    """WebSocket-specific performance monitoring."""
    
    def __init__(self, thresholds: PerformanceThresholds, **kwargs):
        self.thresholds = thresholds
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.alerts: List[PerformanceAlert] = []
    
    async def start_monitoring(self, connection_id: str, user_id: str) -> None:
        """Start monitoring a WebSocket connection."""
        self.metrics[connection_id] = PerformanceMetrics(
            connection_id=connection_id,
            user_id=user_id
        )
    
    async def record_message_latency(self, connection_id: str, latency_ms: float) -> None:
        """Record message latency measurement."""
        if connection_id not in self.metrics:
            return
            
        metrics = self.metrics[connection_id]
        metrics.message_count += 1
        metrics.total_latency_ms += latency_ms
        metrics.max_latency_ms = max(metrics.max_latency_ms, latency_ms)
        metrics.min_latency_ms = min(metrics.min_latency_ms, latency_ms)
        
        # Check thresholds
        if latency_ms > self.thresholds.max_message_latency_ms:
            alert = PerformanceAlert(
                alert_type="HIGH_LATENCY",
                threshold_exceeded="max_message_latency_ms", 
                current_value=latency_ms,
                threshold_value=self.thresholds.max_message_latency_ms,
                timestamp=datetime.now(timezone.utc),
                connection_id=connection_id
            )
            self.alerts.append(alert)
```

### 3. Fix `rate_limiter.py`

**Current State:**
```python
# Has: WebSocketRateLimiter, AdaptiveRateLimiter classes
# Missing: RateLimitExceededException, RateLimitConfig, UserRateLimitState
```

**Required Changes:**
```python
# Add missing exception class
class RateLimitExceededException(Exception):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after

# Add missing configuration class
@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    max_connections_per_minute: int = 60
    max_messages_per_minute: int = 1000
    burst_allowance: int = 10
    sliding_window_seconds: int = 60
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 300.0

# Add missing state class
@dataclass  
class UserRateLimitState:
    """Tracks rate limit state for a user."""
    user_id: str
    connection_attempts: List[float] = field(default_factory=list)
    message_history: List[float] = field(default_factory=list)
    current_backoff: float = 0.0
    last_violation: Optional[datetime] = None
    violation_count: int = 0
```

**Update exports:**
```python
__all__ = [
    'RateLimiter', 
    'check_rate_limit', 
    'AdaptiveRateLimiter',
    'WebSocketRateLimiter',          # Existing
    'RateLimitExceededException',    # New
    'RateLimitConfig',               # New  
    'UserRateLimitState'             # New
]
```

### 4. Fix `reconnection_handler.py`

**Current State:**
```python
# Has: Aliases and shims to other classes
# Missing: Actual WebSocketReconnectionHandler class
```

**Required Changes:**
```python
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime, timezone

class ReconnectionState(Enum):
    """WebSocket reconnection states."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    ABANDONED = "abandoned"

@dataclass
class ReconnectionConfig:
    """Reconnection configuration."""
    max_retries: int = 5
    initial_delay_ms: int = 1000
    max_delay_ms: int = 30000
    backoff_multiplier: float = 2.0
    jitter_factor: float = 0.1

class MaxRetriesExceededException(Exception):
    """Raised when maximum reconnection retries exceeded."""
    pass

@dataclass
class ReconnectionSession:
    """Tracks reconnection session data."""
    session_id: str
    user_id: str
    connection_id: str
    state: ReconnectionState = ReconnectionState.CONNECTED
    retry_count: int = 0
    last_attempt: Optional[datetime] = None
    next_attempt: Optional[datetime] = None
    buffered_messages: List[Dict] = field(default_factory=list)

class WebSocketReconnectionHandler:
    """Handles WebSocket reconnection logic and state restoration."""
    
    def __init__(self, config: ReconnectionConfig):
        self.config = config
        self.sessions: Dict[str, ReconnectionSession] = {}
        self.reconnection_callbacks: Dict[str, Callable] = {}
    
    async def handle_disconnect(self, session_id: str, connection_id: str) -> None:
        """Handle WebSocket disconnection."""
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        session.state = ReconnectionState.DISCONNECTED
        session.last_attempt = datetime.now(timezone.utc)
    
    async def attempt_reconnection(self, session_id: str) -> bool:
        """Attempt to reconnect WebSocket."""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        
        if session.retry_count >= self.config.max_retries:
            session.state = ReconnectionState.FAILED
            raise MaxRetriesExceededException(
                f"Max retries ({self.config.max_retries}) exceeded for session {session_id}"
            )
        
        session.retry_count += 1
        session.state = ReconnectionState.RECONNECTING
        session.last_attempt = datetime.now(timezone.utc)
        
        # Implement reconnection logic here
        # This would integrate with the actual WebSocket manager
        
        return True
    
    def create_session(self, session_id: str, user_id: str, connection_id: str) -> ReconnectionSession:
        """Create new reconnection session."""
        session = ReconnectionSession(
            session_id=session_id,
            user_id=user_id, 
            connection_id=connection_id
        )
        self.sessions[session_id] = session
        return session
```

---

## Implementation Steps

### Step 1: Backup and Prepare
```bash
# Create backup of current files
cp netra_backend/app/websocket_core/event_monitor.py netra_backend/app/websocket_core/event_monitor.py.backup
cp netra_backend/app/websocket_core/performance_monitor_core.py netra_backend/app/websocket_core/performance_monitor_core.py.backup  
cp netra_backend/app/websocket_core/rate_limiter.py netra_backend/app/websocket_core/rate_limiter.py.backup
cp netra_backend/app/websocket_core/reconnection_handler.py netra_backend/app/websocket_core/reconnection_handler.py.backup
```

### Step 2: Implement Changes
1. **event_monitor.py:** Add alias and missing classes (preserving ChatEventMonitor)
2. **performance_monitor_core.py:** Replace shim with actual implementation  
3. **rate_limiter.py:** Add missing exception and config classes
4. **reconnection_handler.py:** Add actual handler class alongside aliases

### Step 3: Validate Implementation
```bash
# Test imports work
python -c "from netra_backend.app.websocket_core.event_monitor import WebSocketEventMonitor, EventValidationError, EventTracker, EventMetrics"
python -c "from netra_backend.app.websocket_core.performance_monitor_core import PerformanceMetrics, LatencyMeasurement, ThroughputMetrics, PerformanceAlert"  
python -c "from netra_backend.app.websocket_core.rate_limiter import RateLimitExceededException, RateLimitConfig, UserRateLimitState"
python -c "from netra_backend.app.websocket_core.reconnection_handler import WebSocketReconnectionHandler, ReconnectionState, ReconnectionConfig"

# Run the failing unit tests
python -m pytest netra_backend/tests/unit/websocket_core/test_websocket_event_monitor_unit.py -v
python -m pytest netra_backend/tests/unit/websocket_core/test_websocket_performance_monitor_unit.py -v  
python -m pytest netra_backend/tests/unit/websocket_core/test_websocket_rate_limiter_unit.py -v
python -m pytest netra_backend/tests/unit/websocket_core/test_websocket_reconnection_handler_unit.py -v
```

### Step 4: Integration Testing
```bash
# Run broader WebSocket tests to ensure no regressions
python tests/unified_test_runner.py --category unit --pattern "*websocket*" --no-coverage --fast-fail
```

---

## Risk Assessment

### LOW RISK
- ✅ **Adding aliases** (WebSocketEventMonitor = ChatEventMonitor) - No breaking changes
- ✅ **Adding missing classes** - Only provides what tests expect
- ✅ **Extending __all__ exports** - Makes imports available without breaking existing code

### MEDIUM RISK  
- ⚠️ **Replacing shim in performance_monitor_core.py** - Need to ensure existing references to PerformanceMonitor still work
- ⚠️ **Adding new WebSocketReconnectionHandler** - Need to ensure it doesn't conflict with existing aliases

### MITIGATION STRATEGIES
1. **Preserve existing functionality** - Keep ChatEventMonitor working exactly as before
2. **Gradual implementation** - Implement one module at a time, validate each step
3. **Comprehensive testing** - Run both unit and integration tests after each change
4. **Rollback plan** - Keep backups ready for immediate rollback if issues occur

---

## Expected Outcomes

### Immediate Benefits
- ✅ **All 4 WebSocket unit tests pass**
- ✅ **Import errors eliminated** 
- ✅ **Test coverage restored** for WebSocket functionality
- ✅ **SSOT compliance** improved (tests match implementation)

### Long-term Benefits  
- ✅ **Architectural coherence** - WebSocket modules have proper WebSocket-specific classes
- ✅ **Technical debt reduction** - Eliminates shims and aliases 
- ✅ **Developer experience** - Clear, predictable import structure
- ✅ **Future extensibility** - Proper foundation for WebSocket features

### Success Metrics
1. **All WebSocket unit tests pass** (4/4)
2. **No regression in existing functionality** (integration tests pass)
3. **Import validation passes** (all expected classes importable)
4. **SSOT compliance score improves** (fewer violations)

---

## Timeline

- **Step 1-2 (Implementation):** 3-4 hours
- **Step 3 (Validation):** 1 hour  
- **Step 4 (Integration Testing):** 30 minutes
- **Total Estimated Effort:** 4.5-5.5 hours

---

## Conclusion

This implementation plan addresses the root cause identified in the Five Whys analysis: **"Incomplete Refactoring Syndrome"**. By completing the refactoring and implementing the missing classes, we:

1. **Honor the test expectations** (which represent good architecture)
2. **Eliminate technical debt** (shims and aliases)
3. **Create true SSOT** for WebSocket functionality
4. **Enable proper testing** of critical WebSocket features
5. **Follow CLAUDE.md principles** ("CHEATING ON TESTS = ABOMINATION")

The approach is **conservative and safe** - we're implementing what should already exist while preserving all existing functionality.

**Recommendation: PROCEED with implementation** - this is critical infrastructure that enables testing of mission-critical WebSocket functionality.
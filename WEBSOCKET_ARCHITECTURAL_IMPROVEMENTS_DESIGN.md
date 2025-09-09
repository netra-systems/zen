# WebSocket Architectural Improvements Design

## Overview

While immediate fixes address the symptoms of WebSocket resource leaks, these architectural improvements create a sustainable foundation for long-term resource management, scalability, and performance optimization.

## Business Value Justification (BVJ)
- **Segment**: ALL (Free → Enterprise) - Infrastructure supporting all user tiers
- **Business Goal**: Scalable multi-user WebSocket infrastructure with zero resource leaks
- **Value Impact**: Enables 1000+ concurrent users without performance degradation
- **Strategic Impact**: Foundation for real-time AI collaboration features and enterprise scaling

## Architecture Pattern: Pooled + Lifecycle + Circuit Breaker

### Current State (Factory Pattern)
```
User Request → Create New Manager → Use → Cleanup (Often Fails) → Resource Leak
```

### Target State (Pooled + Lifecycle Pattern)
```
User Request → Get/Create from Pool → Use → Return to Pool/Cleanup → Guaranteed Resource Recovery
```

## Improvement 1: Manager Pooling System

### Current Issue
Each WebSocket connection creates a brand new manager instance, leading to:
- High memory allocation overhead
- Slow connection establishment
- Resource accumulation when cleanup fails
- Poor performance under load

### Solution: Reusable Manager Pool

#### Architecture
```python
class PooledWebSocketManager:
    """Reusable manager with state reset capabilities"""
    
    def __init__(self, manager_id: str):
        self.manager_id = manager_id
        self.state = ManagerState.AVAILABLE
        self.current_context: Optional[UserExecutionContext] = None
        self.connection: Optional[WebSocket] = None
        self.created_at = datetime.utcnow()
        self.last_used = datetime.utcnow()
        self.usage_count = 0
        
    def reset_for_new_connection(self, user_context: UserExecutionContext, websocket: WebSocket):
        """Reset manager state for reuse with new connection"""
        if self.state != ManagerState.AVAILABLE:
            raise ValueError(f"Manager {self.manager_id} not available for reuse")
            
        # Reset all stateful components
        self.current_context = user_context
        self.connection = websocket
        self.state = ManagerState.ACTIVE
        self.last_used = datetime.utcnow()
        self.usage_count += 1
        
        # Clear any previous state
        self._clear_message_queues()
        self._reset_event_handlers()
        self._initialize_for_user(user_context)
        
        logger.info(f"Manager {self.manager_id} reset for user {user_context.user_id} (usage #{self.usage_count})")
    
    def is_reusable(self) -> bool:
        """Check if manager can be safely reused"""
        return (
            self.state == ManagerState.AVAILABLE and
            self.current_context is None and
            self.connection is None and
            self._has_clean_state()
        )
    
    def mark_available(self):
        """Mark manager as available for reuse"""
        self.current_context = None
        self.connection = None
        self.state = ManagerState.AVAILABLE
        self.last_used = datetime.utcnow()
        
    def should_be_retired(self, max_usage: int = 100, max_age_hours: int = 24) -> bool:
        """Check if manager should be retired from pool"""
        age_hours = (datetime.utcnow() - self.created_at).total_seconds() / 3600
        return (
            self.usage_count >= max_usage or
            age_hours >= max_age_hours or
            not self._is_healthy()
        )

class WebSocketManagerPool:
    """Thread-safe pool of reusable WebSocket managers"""
    
    def __init__(self, 
                 initial_size: int = 10,
                 max_size: int = 50,
                 max_idle_time: int = 3600):  # 1 hour
        self.initial_size = initial_size
        self.max_size = max_size
        self.max_idle_time = max_idle_time
        
        self._pool: Queue[PooledWebSocketManager] = Queue()
        self._active_managers: Dict[str, PooledWebSocketManager] = {}
        self._pool_lock = asyncio.Lock()
        self._stats = PoolStats()
        
        # Initialize pool
        asyncio.create_task(self._initialize_pool())
        
        # Start maintenance task
        asyncio.create_task(self._pool_maintenance_task())
    
    async def get_manager(self, user_context: UserExecutionContext, websocket: WebSocket) -> PooledWebSocketManager:
        """Get manager from pool or create new one"""
        async with self._pool_lock:
            manager = None
            
            # Try to get from pool
            if not self._pool.empty():
                manager = self._pool.get_nowait()
                logger.debug(f"Retrieved manager {manager.manager_id} from pool")
            
            # Create new if pool empty and under max size
            elif len(self._active_managers) < self.max_size:
                manager = PooledWebSocketManager(f"mgr_{uuid.uuid4().hex[:8]}")
                logger.info(f"Created new manager {manager.manager_id}")
            
            # Pool exhausted
            else:
                raise ResourceExhaustionError(f"Manager pool exhausted (max: {self.max_size})")
            
            # Reset manager for new connection
            manager.reset_for_new_connection(user_context, websocket)
            
            # Track active manager
            isolation_key = f"{user_context.user_id}:{user_context.thread_id}"
            self._active_managers[isolation_key] = manager
            
            self._stats.record_allocation()
            return manager
    
    async def return_manager(self, isolation_key: str) -> bool:
        """Return manager to pool or retire if not reusable"""
        async with self._pool_lock:
            if isolation_key not in self._active_managers:
                return False
                
            manager = self._active_managers.pop(isolation_key)
            
            # Clean up manager state
            await manager.cleanup()
            manager.mark_available()
            
            # Check if manager should be retired
            if manager.should_be_retired():
                await manager.destroy()
                logger.debug(f"Retired manager {manager.manager_id}")
                self._stats.record_retirement()
            
            # Return to pool if reusable and pool not full
            elif manager.is_reusable() and self._pool.qsize() < self.initial_size:
                self._pool.put_nowait(manager)
                logger.debug(f"Returned manager {manager.manager_id} to pool")
                self._stats.record_return()
            
            # Destroy if pool full
            else:
                await manager.destroy()
                logger.debug(f"Destroyed excess manager {manager.manager_id}")
                self._stats.record_destruction()
                
            return True
    
    async def _pool_maintenance_task(self):
        """Background task to maintain pool health"""
        while True:
            try:
                await asyncio.sleep(300)  # 5 minutes
                await self._cleanup_idle_managers()
                await self._rebalance_pool()
                self._log_pool_stats()
            except Exception as e:
                logger.error(f"Pool maintenance error: {e}")

    async def _cleanup_idle_managers(self):
        """Clean up idle managers in the pool"""
        current_time = datetime.utcnow()
        managers_to_remove = []
        
        async with self._pool_lock:
            # Check pooled managers
            temp_managers = []
            while not self._pool.empty():
                manager = self._pool.get_nowait()
                idle_time = (current_time - manager.last_used).total_seconds()
                
                if idle_time > self.max_idle_time or manager.should_be_retired():
                    managers_to_remove.append(manager)
                else:
                    temp_managers.append(manager)
            
            # Put back non-idle managers
            for manager in temp_managers:
                self._pool.put_nowait(manager)
        
        # Destroy idle managers
        for manager in managers_to_remove:
            await manager.destroy()
            logger.debug(f"Cleaned up idle manager {manager.manager_id}")
```

## Improvement 2: Circuit Breaker Pattern

### Implementation
```python
class WebSocketCircuitBreaker:
    """Circuit breaker for WebSocket operations to prevent cascade failures"""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info("Circuit breaker moving to HALF_OPEN state")
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
            
        except self.expected_exception as e:
            await self._on_failure()
            raise e
    
    async def _on_success(self):
        """Handle successful operation"""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
        if self.state == CircuitBreakerState.HALF_OPEN:
            logger.info("Circuit breaker reset to CLOSED state")
    
    async def _on_failure(self):
        """Handle failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")

class ResilientWebSocketFactory:
    """WebSocket factory with circuit breaker protection"""
    
    def __init__(self):
        self.pool = WebSocketManagerPool()
        self.circuit_breaker = WebSocketCircuitBreaker()
        self.fallback_manager = SimpleFallbackManager()
    
    async def create_manager(self, user_context: UserExecutionContext, websocket: WebSocket) -> PooledWebSocketManager:
        """Create manager with circuit breaker protection"""
        try:
            return await self.circuit_breaker.call(
                self.pool.get_manager, 
                user_context, 
                websocket
            )
        except CircuitBreakerOpenError:
            logger.warning(f"Circuit breaker open, using fallback for user {user_context.user_id}")
            return await self.fallback_manager.create_simple_manager(user_context, websocket)
```

## Improvement 3: Resource Quotas and Throttling

### Implementation
```python
class UserResourceQuotaManager:
    """Manage per-user resource quotas and throttling"""
    
    def __init__(self):
        self.quotas = {
            'free': ResourceQuota(max_managers=3, max_messages_per_minute=30),
            'early': ResourceQuota(max_managers=10, max_messages_per_minute=100),
            'mid': ResourceQuota(max_managers=15, max_messages_per_minute=200),
            'enterprise': ResourceQuota(max_managers=25, max_messages_per_minute=500)
        }
        self.user_usage: Dict[str, UserResourceUsage] = {}
    
    async def check_quota(self, user_id: str, user_tier: str, resource_type: str) -> bool:
        """Check if user is within resource quota"""
        quota = self.quotas.get(user_tier, self.quotas['free'])
        usage = self.user_usage.get(user_id, UserResourceUsage(user_id))
        
        if resource_type == 'manager':
            return usage.manager_count < quota.max_managers
        elif resource_type == 'message':
            return usage.messages_this_minute < quota.max_messages_per_minute
        
        return False
    
    async def allocate_resource(self, user_id: str, resource_type: str) -> bool:
        """Allocate resource if within quota"""
        if user_id not in self.user_usage:
            self.user_usage[user_id] = UserResourceUsage(user_id)
        
        usage = self.user_usage[user_id]
        
        if resource_type == 'manager':
            usage.manager_count += 1
            return True
        elif resource_type == 'message':
            usage.messages_this_minute += 1
            return True
            
        return False

@dataclass
class ResourceQuota:
    max_managers: int
    max_messages_per_minute: int
    max_connection_duration_hours: int = 24

@dataclass
class UserResourceUsage:
    user_id: str
    manager_count: int = 0
    messages_this_minute: int = 0
    total_connection_time: float = 0
    last_reset_time: datetime = field(default_factory=datetime.utcnow)
```

## Improvement 4: Predictive Resource Management

### Implementation
```python
class PredictiveResourceManager:
    """Predict resource needs and proactively manage capacity"""
    
    def __init__(self):
        self.usage_history: Dict[str, List[ResourceUsageSnapshot]] = {}
        self.prediction_model = SimpleUsagePredictor()
    
    async def predict_resource_needs(self, user_id: str, time_window_minutes: int = 30) -> ResourcePrediction:
        """Predict resource needs for the next time window"""
        history = self.usage_history.get(user_id, [])
        
        if len(history) < 10:  # Not enough data
            return ResourcePrediction(
                predicted_managers=2,
                confidence=0.3,
                recommendation="Use default allocation"
            )
        
        prediction = await self.prediction_model.predict(history, time_window_minutes)
        return prediction
    
    async def proactive_resource_allocation(self, user_id: str):
        """Proactively allocate resources based on prediction"""
        prediction = await self.predict_resource_needs(user_id)
        
        if prediction.confidence > 0.7:
            current_allocation = await self.get_current_allocation(user_id)
            
            if prediction.predicted_managers > current_allocation * 1.5:
                logger.info(f"Proactive allocation: Pre-creating managers for user {user_id}")
                await self.pre_create_managers(user_id, prediction.predicted_managers)

class SimpleUsagePredictor:
    """Simple time-series prediction for resource usage"""
    
    async def predict(self, history: List[ResourceUsageSnapshot], window_minutes: int) -> ResourcePrediction:
        """Simple moving average prediction"""
        if len(history) < 5:
            return ResourcePrediction(predicted_managers=2, confidence=0.2)
        
        # Get recent usage pattern
        recent_usage = [snapshot.manager_count for snapshot in history[-10:]]
        avg_usage = sum(recent_usage) / len(recent_usage)
        
        # Simple trend analysis
        if len(recent_usage) >= 5:
            recent_trend = (recent_usage[-1] - recent_usage[0]) / len(recent_usage)
        else:
            recent_trend = 0
        
        predicted = max(1, int(avg_usage + recent_trend * (window_minutes / 10)))
        confidence = min(0.8, len(recent_usage) / 10)
        
        return ResourcePrediction(
            predicted_managers=predicted,
            confidence=confidence,
            recommendation=f"Based on {len(recent_usage)} recent snapshots"
        )

@dataclass
class ResourceUsageSnapshot:
    timestamp: datetime
    user_id: str
    manager_count: int
    active_connections: int
    message_rate: float

@dataclass
class ResourcePrediction:
    predicted_managers: int
    confidence: float
    recommendation: str
```

## Improvement 5: Advanced Monitoring and Observability

### Implementation
```python
class WebSocketObservabilityManager:
    """Comprehensive monitoring and observability for WebSocket operations"""
    
    def __init__(self):
        self.metrics_collector = WebSocketMetricsCollector()
        self.trace_collector = WebSocketTraceCollector()
        self.alert_manager = ResourceAlertManager()
    
    async def track_manager_lifecycle(self, manager_id: str, event: str, metadata: Dict[str, Any]):
        """Track complete manager lifecycle events"""
        trace_event = {
            'timestamp': datetime.utcnow().isoformat(),
            'manager_id': manager_id,
            'event': event,
            'metadata': metadata,
            'trace_id': self.trace_collector.get_current_trace_id()
        }
        
        await self.trace_collector.record_event(trace_event)
        await self.metrics_collector.increment_counter(f'manager_lifecycle.{event}')
    
    async def track_resource_usage(self, user_id: str, resource_snapshot: ResourceUsageSnapshot):
        """Track detailed resource usage patterns"""
        await self.metrics_collector.record_gauge('active_managers', resource_snapshot.manager_count, {'user_id': user_id})
        await self.metrics_collector.record_gauge('active_connections', resource_snapshot.active_connections, {'user_id': user_id})
        await self.metrics_collector.record_gauge('message_rate', resource_snapshot.message_rate, {'user_id': user_id})
        
        # Check for alerting conditions
        await self.alert_manager.check_resource_alerts(user_id, resource_snapshot)

class WebSocketMetricsCollector:
    """Collect and export WebSocket metrics"""
    
    def __init__(self):
        self.metrics: Dict[str, List[MetricPoint]] = {}
        self.export_interval = 60  # seconds
        asyncio.create_task(self._metrics_export_task())
    
    async def increment_counter(self, metric_name: str, tags: Dict[str, str] = None):
        """Increment a counter metric"""
        metric_point = MetricPoint(
            name=metric_name,
            type='counter',
            value=1,
            tags=tags or {},
            timestamp=datetime.utcnow()
        )
        
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append(metric_point)
    
    async def record_gauge(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Record a gauge metric"""
        metric_point = MetricPoint(
            name=metric_name,
            type='gauge',
            value=value,
            tags=tags or {},
            timestamp=datetime.utcnow()
        )
        
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append(metric_point)

@dataclass
class MetricPoint:
    name: str
    type: str  # 'counter', 'gauge', 'histogram'
    value: float
    tags: Dict[str, str]
    timestamp: datetime
```

## Integration Plan

### Phase 1: Manager Pooling (Week 2)
1. Implement `PooledWebSocketManager` class
2. Create `WebSocketManagerPool` with basic pooling
3. Update factory to use pool
4. Add pool monitoring and metrics

### Phase 2: Circuit Breaker (Week 2-3)
1. Implement `WebSocketCircuitBreaker`
2. Create `ResilientWebSocketFactory`
3. Add fallback mechanisms
4. Test failure scenarios

### Phase 3: Resource Management (Week 3)
1. Implement user quotas and throttling
2. Add predictive resource allocation
3. Create advanced monitoring
4. Integrate with existing systems

### Phase 4: Optimization (Week 4)
1. Performance tuning based on metrics
2. Load testing with new architecture
3. Documentation and training
4. Production deployment

## Expected Benefits

### Performance Improvements
- **Connection Time**: 50% reduction (pool reuse)
- **Memory Usage**: 30% reduction (manager reuse)
- **CPU Overhead**: 40% reduction (fewer allocations)

### Reliability Improvements  
- **Resource Leak Prevention**: 99% reduction
- **Failure Recovery**: <30 seconds
- **System Availability**: >99.9%

### Scalability Improvements
- **Concurrent Users**: Support 1000+ users
- **Resource Efficiency**: 5x better resource utilization
- **Auto-Scaling**: Predictive resource allocation

This architectural design provides a sustainable foundation for WebSocket resource management that scales from individual users to enterprise deployments while maintaining the stability and performance required for critical chat functionality.

---

**Implementation Timeline**: 2-3 weeks  
**Technical Complexity**: High  
**Business Impact**: Very High - Enables enterprise scaling  
**Risk Level**: Medium (Phased implementation reduces risk)
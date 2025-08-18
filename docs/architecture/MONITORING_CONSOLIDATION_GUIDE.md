# Monitoring Type Consolidation Guide

## Overview

After analysis of the monitoring types across the codebase, we discovered that these are **NOT true duplicates** but rather **valid domain-specific implementations** serving different purposes:

- **AlertManager**: Comprehensive alert management with advanced features
- **HealthAlertManager**: Health-specific alerts with recovery actions  
- **PerformanceAlertManager** (WebSocket): WebSocket-specific performance alerts
- **PerformanceAlertManager** (Monitoring): General performance alerts
- **CircuitBreaker** (Core): Full-featured circuit breaker implementation
- **CircuitBreaker** (Error Recovery): Compatibility wrapper for legacy interfaces
- **PerformanceMonitor** (WebSocket): WebSocket-specific monitoring
- **PerformanceMonitor** (Monitoring): General platform monitoring

## Solution: Canonical Monitoring Schemas

Instead of consolidating valid domain-specific implementations, we created **canonical monitoring schemas** (`app/schemas/monitoring.py`) that provide:

1. **Shared interfaces and protocols**
2. **Type consistency across domains**
3. **Common base types for alerts and metrics**
4. **Factory functions for creating standard alerts**

## Available Canonical Types

### Alert Types
```python
from app.schemas.monitoring import (
    AlertSeverity,           # Standard severity levels
    BaseAlert,               # Base alert schema
    ThresholdAlert,          # Threshold violation alerts
    PerformanceAlert,        # Performance-specific alerts
    create_threshold_alert,  # Factory function
    create_performance_alert # Factory function
)
```

### Circuit Breaker Types
```python
from app.schemas.monitoring import (
    CircuitState,            # Circuit breaker states
    CircuitConfig,           # Configuration schema
    CircuitMetrics,          # Metrics schema
    CircuitStatus,           # Status information
    CircuitBreakerProtocol   # Interface protocol
)
```

### Performance Monitoring
```python
from app.schemas.monitoring import (
    PerformanceThresholds,   # Threshold configuration
    PerformanceMetric,       # Individual metrics
    PerformanceSummary,      # Summary information
    PerformanceMonitorProtocol # Interface protocol
)
```

### Database Metrics
```python
from app.schemas.monitoring import (
    DatabaseConnectionMetrics,
    DatabaseQueryMetrics,
    DatabaseCacheMetrics,
    ComprehensiveDatabaseMetrics
)
```

## Migration Examples

### Using Canonical Alert Types

**Before** (domain-specific):
```python
# Different alert structures across domains
websocket_alert = {"metric": "latency", "value": 1500, "severity": "high"}
health_alert = SystemAlert(component="db", message="Database down")
```

**After** (canonical):
```python
from app.schemas.monitoring import create_threshold_alert, AlertSeverity

# Consistent alert structure
websocket_alert = create_threshold_alert(
    component="websocket",
    metric_name="latency_ms",
    current_value=1500.0,
    threshold_value=1000.0,
    severity=AlertSeverity.WARNING
)

health_alert = create_threshold_alert(
    component="database",
    metric_name="health_score",
    current_value=0.2,
    threshold_value=0.8,
    severity=AlertSeverity.CRITICAL
)
```

### Using Circuit Breaker Protocol

**Before** (different interfaces):
```python
# Inconsistent circuit breaker usage
if circuit.should_allow_request():  # Legacy interface
    result = await call_service()
```

**After** (canonical protocol):
```python
from app.schemas.monitoring import CircuitBreakerProtocol

def use_circuit_breaker(circuit: CircuitBreakerProtocol):
    if circuit.can_execute():  # Standard protocol
        result = await call_service()
        circuit.record_success()
    else:
        circuit.record_failure("ServiceUnavailable")
```

## Benefits

1. **Type Consistency**: All monitoring components use shared types
2. **Better Testing**: Common interfaces enable consistent testing
3. **Easier Integration**: Protocols define clear contracts
4. **Future-Proof**: New monitoring components follow established patterns
5. **Preserved Functionality**: Domain-specific implementations remain intact

## Recommendations

1. **Use canonical types for new code**
2. **Gradually migrate existing code to use protocols**  
3. **Leverage factory functions for creating alerts**
4. **Import from `app.schemas.monitoring` for consistency**
5. **Keep domain-specific implementations for specialized needs**

## File Locations

- **Canonical Schemas**: `app/schemas/monitoring.py`
- **Domain-Specific Implementations**: Preserved in their current locations
- **Import Path**: `from app.schemas.monitoring import ...`

This approach provides the benefits of consolidation while preserving the value of domain-specific implementations.
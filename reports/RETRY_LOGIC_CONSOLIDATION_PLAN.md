# Retry Logic Consolidation Plan - Single Source of Truth (SSOT)

## Executive Summary

**Critical SSOT Violation Identified**: The netra-backend service contains **25+ duplicate retry implementations** that violate the core architectural principle of Single Source of Truth. This analysis provides a comprehensive consolidation plan to achieve SSOT compliance.

**Business Impact**: 
- **Current State**: Multiple retry implementations create inconsistent behavior, increased maintenance overhead, and potential reliability gaps
- **Target State**: Single unified retry system providing consistent, reliable, and maintainable retry patterns across all service layers

## Complete Inventory of Retry Implementations

### 1. Core Retry Infrastructure (8 implementations)

| Location | Type | Status | Usage |
|----------|------|--------|--------|
| `netra_backend/app/agents/base/retry_manager.py` | Agent-specific | **ACTIVE** | Agent execution patterns |
| `netra_backend/app/core/reliability.py` | Service wrapper | **ACTIVE** | AgentReliabilityWrapper |
| `netra_backend/app/core/unified_error_handler.py` | Error recovery | **ACTIVE** | RetryRecoveryStrategy |
| `netra_backend/app/core/async_retry_logic.py` | Async utilities | **ACTIVE** | _retry_with_backoff decorator |
| `netra_backend/app/core/reliability_retry.py` | Reliability layer | **ACTIVE** | RetryHandler |
| `netra_backend/app/core/resilience/unified_retry_handler.py` | **PREFERRED SSOT** | **ACTIVE** | Domain-specific policies |
| `netra_backend/app/core/enhanced_retry_strategies.py` | Strategy collection | **ACTIVE** | Factory pattern |
| `netra_backend/app/core/retry_strategy_executor.py` | Execution layer | **ACTIVE** | exponential_backoff_retry |

### 2. Database Retry Systems (5 implementations)

| Location | Type | Status | Usage |
|----------|------|--------|--------|
| `netra_backend/app/db/intelligent_retry_system.py` | **SOPHISTICATED** | **ACTIVE** | Database-specific with circuit breakers |
| `netra_backend/app/db/postgres_core.py` | DB-specific | **ACTIVE** | PostgreSQL operations |
| `netra_backend/app/db/clickhouse.py` | DB-specific | **ACTIVE** | ClickHouse operations |
| `netra_backend/app/db/database_manager.py` | Management layer | **ACTIVE** | Connection management |
| `netra_backend/app/db/transaction_core.py` | Transaction layer | **ACTIVE** | Database transactions |

### 3. LLM & Agent Retry Patterns (6 implementations)

| Location | Type | Status | Usage |
|----------|------|--------|--------|
| `netra_backend/app/llm/enhanced_retry.py` | LLM-specific | **ACTIVE** | API rate limiting |
| `netra_backend/app/llm/fallback_strategies.py` | Strategy pattern | **ACTIVE** | RetryExecutionStrategy |
| `netra_backend/app/core/error_recovery.py` | Recovery pattern | **ACTIVE** | RetryStrategy base class |
| `netra_backend/app/core/error_recovery_integration.py` | Integration layer | **ACTIVE** | Cross-system recovery |
| Various agent modules | Agent-specific | **SCATTERED** | Individual agent patterns |
| Various test helpers | Test utilities | **LEGACY** | Test-only implementations |

### 4. Specialized Retry Patterns (6+ implementations)

| Location | Type | Status | Usage |
|----------|------|--------|--------|
| `netra_backend/app/websocket_core/*.py` | WebSocket-specific | **ACTIVE** | Connection management |
| `netra_backend/app/clients/auth_client_core.py` | Auth client | **ACTIVE** | Authentication retries |
| Various MCP client modules | MCP-specific | **ACTIVE** | Model Context Protocol |
| Test utilities across modules | Test helpers | **LEGACY** | Testing patterns |
| Recovery strategies modules | Recovery pattern | **ACTIVE** | Domain-specific recovery |
| Circuit breaker integrations | Resilience pattern | **ACTIVE** | Circuit breaker + retry |

## Retry Strategy Analysis

### Strategy Types Identified:

1. **Fixed Delay**: Simple constant delay between attempts
2. **Linear Backoff**: Incremental delay increase (1s, 2s, 3s...)
3. **Exponential Backoff**: Exponential increase (1s, 2s, 4s, 8s...)
4. **Exponential with Jitter**: Exponential + randomization to prevent thundering herd
5. **Fibonacci Backoff**: Fibonacci sequence delays (1s, 1s, 2s, 3s, 5s...)
6. **Adaptive Backoff**: Dynamic adjustment based on success/failure patterns
7. **Circuit Breaker Integration**: Fail-fast after threshold breaches

### Domain-Specific Requirements:

| Domain | Max Attempts | Base Delay | Max Delay | Strategy | Special Features |
|--------|--------------|------------|-----------|----------|-----------------|
| **Database** | 5 | 0.5s | 30s | Exponential+Jitter | Connection-aware, transaction-safe |
| **LLM/API** | 4 | 2.0s | 120s | Exponential+Jitter | Rate limiting, token-aware |
| **Agent Execution** | 3 | 1.0s | 60s | Exponential | Context preservation |
| **WebSocket** | 2 | 0.5s | 5s | Exponential | Fast reconnection |
| **File Operations** | 3 | 0.2s | 2s | Exponential | I/O optimized |
| **Network/HTTP** | 3 | 1.0s | 30s | Exponential+Jitter | Connection pooling aware |

## Current State Assessment

### Active vs Legacy Code Analysis:

**ACTIVELY USED (High Priority for Consolidation)**:
1. `unified_retry_handler.py` - **BEST CANDIDATE for SSOT** ✅
2. `intelligent_retry_system.py` - **SOPHISTICATED but domain-specific** ⚠️
3. Agent `retry_manager.py` - **AGENT-SPECIFIC but widely used** ⚠️
4. `reliability.py` - **SERVICE WRAPPER pattern** ⚠️
5. `unified_error_handler.py` RetryRecoveryStrategy - **ERROR RECOVERY integration** ⚠️

**LEGACY/DEAD CODE (Lower Priority)**:
1. Multiple test helper implementations - **LEGACY** 🔄
2. Various scattered agent-specific retry patterns - **SCATTERED** 🔄
3. Older async retry utilities - **SUPERSEDED** 🔄

### SSOT Compliance Issues:

1. **Multiple Strategy Implementations**: 7+ different retry strategy implementations
2. **Inconsistent Configuration**: Different config objects and parameter names
3. **Scattered Domain Logic**: Database, LLM, Agent, WebSocket logic spread across modules  
4. **Duplicate Circuit Breaker Integration**: Multiple circuit breaker + retry combinations
5. **Error Classification Inconsistency**: Different error classification logic across modules

## Unified RetryManager Design

### Architecture:

```python
# SSOT Unified Retry Manager
class UnifiedRetryManager:
    """
    Single Source of Truth for ALL retry logic in netra-backend.
    
    Consolidates all retry patterns while supporting domain-specific requirements.
    """
    
    def __init__(self, service_name: str = "netra-backend"):
        self.service_name = service_name
        self.strategies = self._init_strategies()
        self.policies = self._init_domain_policies()
        self.circuit_breakers = self._init_circuit_breakers()
        self.metrics = self._init_metrics()
    
    # Unified interface supporting all current use cases
    async def execute_with_retry(self, 
                               func: Callable,
                               domain: RetryDomain = RetryDomain.GENERIC,
                               policy: Optional[RetryPolicy] = None,
                               context: Optional[RetryContext] = None) -> RetryResult:
        """Execute any function with domain-appropriate retry logic."""
        pass
    
    # Domain-specific convenience methods
    async def execute_database_operation(self, func: Callable) -> RetryResult: pass
    async def execute_llm_operation(self, func: Callable) -> RetryResult: pass
    async def execute_agent_operation(self, func: Callable) -> RetryResult: pass
    async def execute_websocket_operation(self, func: Callable) -> RetryResult: pass
    async def execute_http_operation(self, func: Callable) -> RetryResult: pass
```

### Unified Configuration Schema:

```python
@dataclass
class UnifiedRetryConfig:
    """Single configuration schema supporting all domains."""
    # Core retry parameters
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    backoff_multiplier: float = 2.0
    jitter_enabled: bool = False
    jitter_range: float = 0.1
    
    # Timeout configuration  
    operation_timeout: Optional[float] = None
    total_timeout: Optional[float] = None
    
    # Error handling
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    non_retryable_exceptions: Tuple[Type[Exception], ...] = ()
    error_classifier: Optional[Callable[[Exception], bool]] = None
    
    # Circuit breaker integration
    circuit_breaker_enabled: bool = False
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 30.0
    
    # Domain-specific extensions
    domain_config: Dict[str, Any] = field(default_factory=dict)
    
    # Observability
    metrics_enabled: bool = True
    context_propagation: bool = True
```

### Strategy Pattern Integration:

```python
class RetryStrategyInterface:
    """Interface for all retry strategies."""
    async def calculate_delay(self, attempt: int, context: RetryContext) -> float: pass
    def should_retry(self, error: Exception, attempt: int, context: RetryContext) -> bool: pass

class ExponentialBackoffStrategy(RetryStrategyInterface): pass
class IntelligentDatabaseStrategy(RetryStrategyInterface): pass  
class RateLimitAwareStrategy(RetryStrategyInterface): pass
class CircuitBreakerStrategy(RetryStrategyInterface): pass
```

## Implementation Plan

### Phase 1: Core SSOT Infrastructure (Week 1)

**Goal**: Establish the unified retry manager as the canonical implementation

1. **Enhance `unified_retry_handler.py`** as the primary SSOT
   - Add domain-specific policy support
   - Integrate circuit breaker functionality
   - Add comprehensive error classification
   - Implement metrics and observability

2. **Create `UnifiedRetryManager` class**
   - Centralize all retry logic
   - Support all current use cases
   - Maintain backward compatibility APIs

3. **Establish configuration standards**
   - Single `UnifiedRetryConfig` schema
   - Domain-specific policy definitions
   - Environment-based configuration

### Phase 2: Domain Integration (Week 2)

**Goal**: Migrate core domain-specific implementations

1. **Database Layer Migration**
   - Preserve `intelligent_retry_system.py` sophisticated features
   - Integrate database-specific error classification  
   - Maintain transaction-safe retry patterns
   - Migrate PostgreSQL and ClickHouse specific logic

2. **Agent Layer Migration**  
   - Consolidate agent `retry_manager.py` functionality
   - Preserve agent execution context
   - Maintain WebSocket notification compatibility
   - Integrate with agent lifecycle management

3. **LLM/API Layer Migration**
   - Consolidate LLM retry strategies
   - Preserve rate limiting awareness
   - Maintain fallback strategy integration
   - Support API-specific error patterns

### Phase 3: Legacy Cleanup (Week 3)

**Goal**: Remove duplicate implementations and establish enforcement

1. **Remove Legacy Implementations**
   - Delete superseded retry modules
   - Clean up test helper duplicates
   - Remove scattered retry patterns from individual modules

2. **Update Import Statements**
   - Redirect all retry imports to unified manager
   - Update module dependencies
   - Fix circular import issues

3. **Add Enforcement Mechanisms**
   - Linting rules to prevent new retry implementations
   - Import restrictions in pyproject.toml
   - Documentation updates

### Phase 4: Testing & Validation (Week 4)

**Goal**: Ensure unified system maintains all existing functionality

1. **Comprehensive Test Migration**
   - Migrate all retry-related tests to unified framework
   - Add cross-domain compatibility tests
   - Performance regression testing

2. **Integration Testing**
   - End-to-end retry scenario testing
   - Circuit breaker integration validation
   - WebSocket notification compatibility
   - Database transaction safety verification

3. **Performance Validation**
   - Retry performance benchmarking
   - Memory usage optimization
   - Latency impact analysis

## Migration Strategy

### Backward Compatibility Approach:

```python
# Legacy compatibility layer - temporary during migration
from netra_backend.app.core.unified_retry_manager import UnifiedRetryManager

# Legacy import compatibility  
class RetryManager:  # Agent retry manager compatibility
    def __init__(self, config):
        self._unified = UnifiedRetryManager("agent")
        # Delegate to unified implementation
        
def intelligent_retry_system():  # Database retry system compatibility  
    return UnifiedRetryManager("database")
    
def exponential_backoff_retry():  # Strategy executor compatibility
    return UnifiedRetryManager("generic").exponential_strategy
```

### Testing Strategy:

1. **Parallel Implementation Phase**
   - Run old and new retry systems in parallel
   - Compare retry outcomes and performance
   - Gradual migration per domain

2. **Feature Parity Validation**
   - Comprehensive test coverage for all retry patterns
   - Domain-specific behavior verification
   - Error edge case testing

3. **Performance Benchmarking**
   - Retry latency measurement
   - Memory usage comparison
   - Circuit breaker performance impact

## Risk Mitigation

### High-Risk Areas:

1. **Database Transaction Safety**
   - **Risk**: Transaction rollback during retry
   - **Mitigation**: Preserve `intelligent_retry_system.py` transaction-safe patterns

2. **Agent Execution Context**
   - **Risk**: Loss of agent execution context during retry
   - **Mitigation**: Context preservation in unified manager

3. **WebSocket Notification Dependencies**  
   - **Risk**: Breaking WebSocket event delivery during retry
   - **Mitigation**: Maintain agent notification compatibility

4. **Circuit Breaker State Synchronization**
   - **Risk**: Circuit breaker state inconsistencies
   - **Mitigation**: Centralized circuit breaker management

### Rollback Plan:

1. **Feature Flags**: Enable gradual rollout with instant rollback capability
2. **Parallel Systems**: Maintain old systems during migration period
3. **Monitoring**: Comprehensive retry metrics and alerting
4. **Staged Migration**: Domain-by-domain migration with validation gates

## Success Metrics

### SSOT Compliance Metrics:

1. **Code Duplication Reduction**: Reduce 25+ retry implementations to 1 unified system
2. **Import Consistency**: All retry-related imports point to unified manager  
3. **Configuration Standardization**: Single config schema across all domains
4. **Test Coverage**: 100% test coverage for unified retry manager
5. **Performance Parity**: Zero performance regression in retry operations

### Business Value Metrics:

1. **Reliability Improvement**: Consistent retry behavior across all service layers
2. **Maintenance Reduction**: Single codebase for all retry logic maintenance
3. **Development Velocity**: Faster implementation of new retry requirements
4. **Operational Consistency**: Predictable retry behavior for SRE operations

## Conclusion

The consolidation of 25+ retry logic implementations into a single SSOT represents a critical architectural improvement that will:

1. **Eliminate SSOT Violations**: Achieve true Single Source of Truth for retry logic
2. **Improve System Reliability**: Consistent, well-tested retry patterns across all domains
3. **Reduce Maintenance Overhead**: Single codebase for all retry functionality
4. **Enable Better Observability**: Unified metrics and monitoring for retry operations
5. **Prevent Future Fragmentation**: Clear architectural boundaries preventing duplicate implementations

**Recommendation**: Proceed with implementation plan, prioritizing the `unified_retry_handler.py` as the primary SSOT foundation while carefully preserving domain-specific sophistication from systems like `intelligent_retry_system.py`.

This consolidation aligns with the CLAUDE.md directive: "**Single Source of Truth (SSOT):** A concept must have ONE canonical implementation per service."
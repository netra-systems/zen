# Circuit Breaker SSOT Consolidation Plan

**Date**: September 2, 2025  
**Mission**: Critical consolidation of 80+ circuit breaker implementations to achieve SSOT compliance  
**Business Impact**: Eliminate maintenance overhead, ensure consistent failure handling, reduce system complexity by 70-80%

## Executive Summary

### Current State Analysis
- **Total Circuit Breaker Files**: 45+ implementation files found
- **Unique Classes**: 15+ distinct CircuitBreaker class implementations
- **Critical SSOT Violations**: High - Multiple overlapping implementations across services
- **Maintenance Burden**: 2500+ lines of duplicated circuit breaking logic
- **Business Risk**: Inconsistent failure handling across critical system components

### Canonical SSOT Implementation Identified
**Winner**: `netra_backend/app/core/resilience/unified_circuit_breaker.py`
- **Class**: `UnifiedCircuitBreaker` and `UnifiedCircuitBreakerManager`
- **Rationale**: Most comprehensive feature set, active development, designed for SSOT consolidation
- **Status**: Production-ready with extensive test coverage

## Detailed Inventory of Circuit Breaker Implementations

### Tier 1: Core Implementations (SSOT Candidates)

#### 1. UnifiedCircuitBreaker (CANONICAL - WINNER) ⭐
- **File**: `netra_backend/app/core/resilience/unified_circuit_breaker.py`
- **Lines**: 1008 lines
- **Status**: SSOT Implementation - Preserve and Enhance
- **Features**: 
  - Comprehensive state management (CLOSED/OPEN/HALF_OPEN)
  - Sliding window error rate calculation
  - Adaptive thresholds based on health checks
  - Exponential backoff with jitter
  - Decorator and context manager support
  - Pre-configured service-specific breakers
  - Legacy compatibility layers

#### 2. CircuitBreaker (Core) - MIGRATE TO UNIFIED
- **File**: `netra_backend/app/core/circuit_breaker_core.py`
- **Lines**: 203 lines
- **Status**: Legacy - Migrate usage to UnifiedCircuitBreaker
- **Usage**: 15+ import references across codebase

#### 3. CircuitBreaker (Services) - MIGRATE TO UNIFIED
- **File**: `netra_backend/app/services/circuit_breaker.py`
- **Lines**: 555 lines
- **Status**: Legacy - Already wraps UnifiedCircuitBreaker (lines 83-141)
- **Note**: Contains deprecation warning recommending UnifiedCircuitBreaker

#### 4. AgentCircuitBreaker (Security) - MIGRATE TO UNIFIED
- **File**: `netra_backend/app/agents/security/circuit_breaker.py`
- **Lines**: 468 lines
- **Status**: Agent-specific - Migrate to use UnifiedCircuitBreaker

### Tier 2: Legacy/Compatibility Wrappers (REMOVE AFTER MIGRATION)

#### 5. CircuitBreaker (Agent Base) - REMOVE
- **File**: `netra_backend/app/agents/base/circuit_breaker.py`
- **Lines**: 132 lines
- **Status**: Legacy wrapper - Already delegates to core implementation

#### 6. CircuitBreaker (Agent Components) - REMOVE
- **File**: `netra_backend/app/agents/base/circuit_breaker_components.py`
- **Lines**: ~100 lines
- **Status**: Duplicate of agent base implementation

#### 7. AsyncCircuitBreaker - REMOVE
- **File**: `netra_backend/app/core/async_retry_logic.py`
- **Status**: Simple async-only implementation - UnifiedCircuitBreaker provides better async support

### Tier 3: Service-Specific Wrappers (MIGRATE TO UNIFIED DOMAIN CIRCUIT BREAKERS)

#### 8. Database Circuit Breakers (Multiple Files)
- `netra_backend/app/db/client_config.py` - CircuitBreakerManager
- `netra_backend/app/db/database_manager.py` - Uses UnifiedCircuitBreaker (good!)
- `netra_backend/app/db/clickhouse.py` - Uses UnifiedCircuitBreaker (good!)

#### 9. API Gateway Circuit Breakers
- `netra_backend/app/services/api_gateway/circuit_breaker.py`
- `netra_backend/app/services/api_gateway/circuit_breaker_manager.py`

#### 10. LLM Circuit Breakers
- `netra_backend/app/llm/client_circuit_breaker.py` - LLMCircuitBreakerManager
- `netra_backend/app/llm/enhanced_retry.py` - CircuitBreakerRetryStrategy

### Tier 4: Monitoring and Utilities (KEEP - INTEGRATE WITH UNIFIED)

#### 11. Circuit Breaker Monitoring
- `netra_backend/app/services/circuit_breaker_monitor.py` - Keep for metrics/alerting
- `netra_backend/app/services/metrics/circuit_breaker_metrics.py` - Keep for metrics

#### 12. Utility Modules
- `netra_backend/app/utils/circuit_breaker.py` - Simple re-export (can remove)

## Usage Analysis

### Active Usage Patterns (Based on Import Analysis)

#### High Usage (10+ references)
1. **UnifiedCircuitBreaker**: 54 files importing/referencing
2. **Core CircuitBreaker**: 25+ files importing
3. **Agent CircuitBreakerConfig**: 15+ files importing

#### Medium Usage (5-10 references)
1. **Services CircuitBreaker**: 8 files importing
2. **Security CircuitBreaker**: 6 files importing

#### Low Usage (1-4 references)
1. **AsyncCircuitBreaker**: 2 files importing
2. **API Gateway breakers**: 3 files each

## Migration Strategy and Implementation Plan

### Phase 1: Establish UnifiedCircuitBreaker as SSOT (Week 1)
**Status**: ✅ ALREADY COMPLETE - UnifiedCircuitBreaker is production-ready

#### Tasks:
- [x] UnifiedCircuitBreaker is comprehensive and feature-complete
- [x] Extensive test coverage exists
- [x] Service-specific pre-configured breakers available
- [x] Legacy compatibility layers in place

### Phase 2: Migrate High-Impact Implementations (Week 2)

#### 2.1 Migrate Core CircuitBreaker Usage (2 days)
**Files to Update**: 25+ files importing from `circuit_breaker_core.py`

```python
# OLD
from netra_backend.app.core.circuit_breaker_core import CircuitBreaker, CircuitConfig

# NEW  
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker, 
    UnifiedCircuitConfig
)
```

**Critical Files**:
- `netra_backend/app/db/client_config.py` (lines 79, 87, 95, 103)
- `netra_backend/app/core/reliability_circuit_breaker.py`
- `netra_backend/app/agents/supervisor_circuit_breaker.py`

#### 2.2 Migrate Services CircuitBreaker Usage (1 day)
**Note**: Already wraps UnifiedCircuitBreaker, but consumers should migrate to direct usage

**Files to Update**: 8+ files importing from `services/circuit_breaker.py`

```python
# OLD
from netra_backend.app.services.circuit_breaker import CircuitBreaker, get_circuit_breaker_manager

# NEW
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker,
    get_unified_circuit_breaker_manager
)
```

### Phase 3: Migrate Agent-Specific Implementations (Week 3)

#### 3.1 Replace Security CircuitBreaker (2 days)
**File**: `netra_backend/app/agents/security/circuit_breaker.py`

**Migration Strategy**:
```python
# Replace AgentCircuitBreaker with UnifiedCircuitBreaker wrapper
from netra_backend.app.core.resilience.unified_circuit_breaker import UnifiedCircuitBreaker, UnifiedCircuitConfig

class AgentCircuitBreaker:
    def __init__(self, agent_name: str, config: CircuitBreakerConfig):
        unified_config = UnifiedCircuitConfig(
            name=agent_name,
            failure_threshold=config.failure_threshold,
            recovery_timeout=float(config.recovery_timeout),
            # ... map other config fields
        )
        self._unified_breaker = UnifiedCircuitBreaker(unified_config)
    
    def can_execute(self) -> bool:
        return self._unified_breaker.can_execute()
    
    def record_success(self) -> None:
        self._unified_breaker.record_success()
    
    def record_failure(self, failure_type: FailureType, error_message: str, **kwargs) -> None:
        self._unified_breaker.record_failure(error_message)
```

#### 3.2 Remove Agent Base CircuitBreaker (1 day) 
**Files**: 
- `netra_backend/app/agents/base/circuit_breaker.py` (remove file)
- `netra_backend/app/agents/base/circuit_breaker_components.py` (remove file)

**Update imports in**:
- 15+ files importing CircuitBreakerConfig from agents/base/

```python
# OLD
from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig

# NEW
from netra_backend.app.core.resilience.unified_circuit_breaker import UnifiedCircuitConfig as CircuitBreakerConfig
```

### Phase 4: Migrate Service-Specific Implementations (Week 4)

#### 4.1 Update LLM Circuit Breakers (1 day)
**File**: `netra_backend/app/llm/client_circuit_breaker.py`

Already uses delegation pattern - update to use UnifiedCircuitBreakerManager:

```python
# OLD
from netra_backend.app.core.circuit_breaker import circuit_registry

# NEW
from netra_backend.app.core.resilience.unified_circuit_breaker import get_unified_circuit_breaker_manager

class LLMCircuitBreakerManager:
    def __init__(self):
        self.manager = get_unified_circuit_breaker_manager()
```

#### 4.2 Update API Gateway Implementations (2 days)
**Files**:
- `netra_backend/app/services/api_gateway/circuit_breaker.py`
- `netra_backend/app/services/api_gateway/circuit_breaker_manager.py`

Replace with UnifiedCircuitBreaker using pre-configured settings:

```python
from netra_backend.app.core.resilience.unified_circuit_breaker import UnifiedServiceCircuitBreakers

def get_api_gateway_circuit_breaker():
    return UnifiedServiceCircuitBreakers.get_auth_service_circuit_breaker()
```

### Phase 5: Clean Up and Optimization (Week 5)

#### 5.1 Remove Legacy Files (1 day)
**Files to Delete**:
- `netra_backend/app/agents/base/circuit_breaker.py`
- `netra_backend/app/agents/base/circuit_breaker_components.py`
- `netra_backend/app/core/async_retry_logic.py` (AsyncCircuitBreaker)
- `netra_backend/app/utils/circuit_breaker.py`

#### 5.2 Update Documentation and Tests (2 days)
- Update all test files to use UnifiedCircuitBreaker
- Update documentation to reference SSOT implementation
- Create migration guide for future developers

## Specific Code Changes Required

### 1. Database Manager Updates (ALREADY GOOD)
**File**: `netra_backend/app/db/database_manager.py` (lines 42-44)
```python
# ✅ ALREADY CORRECT - using UnifiedCircuitBreaker
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedServiceCircuitBreakers,
    get_unified_circuit_breaker_manager,
)
```

### 2. Critical Import Updates Needed

#### File: `netra_backend/app/agents/triage_sub_agent/agent.py` (line 15)
```python
# OLD
from netra_backend.app.core.resilience.domain_circuit_breakers import (

# ENSURE USES
from netra_backend.app.core.resilience.unified_circuit_breaker import (
```

#### File: `netra_backend/app/agents/supervisor/fallback_manager.py` (lines 15-16)
```python
# OLD  
from netra_backend.app.agents.supervisor_circuit_breaker import CircuitBreaker
from netra_backend.app.core.circuit_breaker import circuit_registry

# NEW
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker,
    get_unified_circuit_breaker_manager
)
```

#### File: `netra_backend/app/db/client_config.py` (lines 79, 87, 95, 103)
```python
# OLD
from netra_backend.app.core.circuit_breaker import circuit_registry

# NEW  
from netra_backend.app.core.resilience.unified_circuit_breaker import get_unified_circuit_breaker_manager

# Update all circuit_registry calls to get_unified_circuit_breaker_manager()
```

### 3. Test File Updates (40+ test files need imports updated)

Pattern for updating test imports:
```python
# OLD
from netra_backend.app.core.circuit_breaker_core import CircuitBreaker
from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig

# NEW
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker as CircuitBreaker,
    UnifiedCircuitConfig as CircuitBreakerConfig
)
```

## Risk Assessment and Mitigation

### High Risk Areas
1. **Database Operations** - Circuit breakers protect critical DB connections
   - **Mitigation**: Database manager already uses UnifiedCircuitBreaker ✅
   - **Validation**: Run database resilience tests

2. **LLM Service Calls** - Circuit breakers prevent cascading LLM failures  
   - **Mitigation**: LLM manager uses delegation pattern - easy to swap
   - **Validation**: Run LLM integration tests

3. **Agent Execution** - Security circuit breakers protect agent workflows
   - **Mitigation**: Gradual migration with compatibility wrappers
   - **Validation**: Run full agent test suite

### Medium Risk Areas
1. **API Gateway** - Service mesh circuit breaking
   - **Mitigation**: Use pre-configured UnifiedCircuitBreaker settings
2. **Auth Service** - Authentication failure protection  
   - **Mitigation**: Auth client already has circuit breaker integration

### Low Risk Areas
1. **Test Infrastructure** - Test-only circuit breakers
2. **Utility Modules** - Simple re-exports
3. **Frontend** - TypeScript circuit breakers (separate from backend)

## Success Metrics

### Code Quality Improvements
- **Lines of Code**: Reduce from 2500+ to 800-1000 lines (65% reduction)
- **File Count**: Reduce from 45+ files to 10-15 files (70% reduction)
- **Maintenance Points**: Reduce from 15+ implementations to 1 SSOT (93% reduction)

### Functionality Improvements  
- **Feature Consistency**: 100% uniform feature availability across services
- **Configuration**: Single source for circuit breaker behavior
- **Monitoring**: Unified metrics and alerting across all circuit breakers

### Performance Improvements
- **Memory Usage**: Reduced object overhead from consolidated implementation
- **CPU Usage**: More efficient state management and metrics collection
- **Developer Velocity**: Single API to learn and maintain

## Validation Plan

### Phase-by-Phase Testing
1. **Unit Tests**: Update 40+ test files to use UnifiedCircuitBreaker
2. **Integration Tests**: Verify service-to-service circuit breaking works
3. **E2E Tests**: Validate full system resilience under failure conditions
4. **Performance Tests**: Ensure no performance regression

### Critical Test Cases
1. **Database Failure Recovery**: Verify DB circuit breakers trigger and recover
2. **LLM Rate Limiting**: Verify LLM circuit breakers handle API limits
3. **Agent Execution Failures**: Verify agent circuit breakers prevent cascades
4. **Multi-Service Failures**: Verify circuit breakers prevent system-wide failures

## Implementation Timeline

| Week | Phase | Tasks | Risk Level |
|------|-------|-------|------------|
| 1 | Setup | Validate UnifiedCircuitBreaker completeness | Low |
| 2 | Core Migration | Migrate core and services usage | High |
| 3 | Agent Migration | Migrate agent-specific implementations | Medium |
| 4 | Service Migration | Migrate LLM, API Gateway, specialized | Medium |
| 5 | Cleanup | Remove legacy files, update tests | Low |

**Total Effort**: 3-4 weeks  
**Team Size**: 1-2 developers  
**Testing Effort**: 40% of implementation time

## Conclusion

The UnifiedCircuitBreaker implementation represents a mature, production-ready SSOT for circuit breaking functionality. The migration path is clear with well-defined phases that minimize risk while maximizing the benefits of consolidation.

**Key Success Factors**:
1. UnifiedCircuitBreaker already exists and is feature-complete
2. Many critical services (DB, ClickHouse) already use the unified implementation  
3. Legacy implementations mostly use delegation patterns - easy to migrate
4. Comprehensive test coverage exists for the unified implementation

**Business Value**:
- **Maintenance Cost**: 93% reduction in circuit breaker maintenance overhead
- **System Reliability**: Consistent failure handling across all services  
- **Developer Productivity**: Single API to learn and use
- **Operational Visibility**: Unified monitoring and alerting

This consolidation directly supports the CLAUDE.md mandate for SSOT compliance and will significantly reduce system complexity while improving reliability.

---

**Next Action**: Begin Phase 2 migration of core CircuitBreaker usage (25+ files) to establish momentum and validate the migration approach.
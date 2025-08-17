# TYPE DEDUPLICATION PLAN
## Eliminating ALL 361 Duplicate Type Definitions

**Mission**: Create single source of truth for ALL types across the Netra codebase

## CRITICAL DUPLICATE ANALYSIS (Top Priority)

### 1. WebSocketConnectionManager (2 definitions → 1)
**CANONICAL LOCATION**: `app.core.websocket_recovery_strategies.WebSocketConnectionManager`

**DUPLICATES TO REMOVE**:
- `app.ws_manager_connections.WebSocketConnectionManager` → Rename to `WebSocketLifecycleManager`

**REASON**: Recovery strategies version is comprehensive with full recovery capabilities.

### 2. CacheConfig (4 definitions → 1) 
**CANONICAL LOCATION**: Create `app.schemas.config_types.CacheConfig`

**DUPLICATES TO CONSOLIDATE**:
- `app.db.query_cache.QueryCacheConfig` → Import from canonical location
- `app.schemas.service_types.CacheConfig` → Remove, use canonical  
- `app.agents.config.CacheConfig` → Remove, use canonical
- `app.schemas.llm_config_types` (cache fields) → Refactor to use canonical

**UNIFIED INTERFACE**:
```python
class CacheConfig(BaseModel):
    """Unified cache configuration for all services"""
    enabled: bool = Field(default=True)
    ttl_seconds: int = Field(default=300)
    max_size: int = Field(default=1000)
    eviction_policy: Literal["lru", "lfu", "fifo", "adaptive"] = "lru"
    key_prefix: str = ""
    # Database-specific
    strategy: Optional[CacheStrategy] = None
    metrics_enabled: bool = True
    # Agent-specific  
    redis_ttl: Optional[int] = None
    # Service-specific
    max_size_mb: Optional[int] = None
```

### 3. AgentConfig (3 definitions → 1)
**CANONICAL LOCATION**: `app.schemas.shared_types.AgentConfig`

**DUPLICATES TO REMOVE**:
- `app.agents.config.AgentConfig` → Import from shared_types, extend if needed
- `app.routes.synthetic_data.SyntheticDataAgentConfig` → Rename to avoid confusion

**STRATEGY**: Keep base config in shared_types, create specialized configs with clear inheritance.

### 4. DemoAgent (3 definitions → 1)
**CANONICAL LOCATION**: `app.agents.demo_agent.DemoAgent`

**DUPLICATES TO REMOVE**:
- `app.tests.helpers.supervisor_test_classes.DemoAgent` → Rename to `MockDemoAgent`
- `app.tests.agents.test_supervisor_corpus_data.DemoAgent` → Rename to `TestDemoAgent`

### 5. AgentMetadata (3 definitions → 1)
**CANONICAL LOCATION**: `app.schemas.registry.AgentMetadata`

**DUPLICATES TO REMOVE**:
- `app.agents.state.AgentMetadata` → Import from registry
- `test_reports/agent_system_analysis_report.md` → Documentation only, keep registry version

**REASON**: Registry version has more comprehensive fields (priority, retry_count, parent_agent_id, tags).

## MASSIVE DUPLICATES DISCOVERED (361 total)

### Python Backend Duplicates (Top Offenders)
1. **TestErrorHandling** (9 definitions) → Consolidate test utilities
2. **TestIntegrationScenarios** (6 definitions) → Create shared test base
3. **CircuitBreaker** (6 definitions) → Use `app.core.circuit_breaker.CircuitBreaker`
4. **AlertSeverity** (6 definitions) → Consolidate to `app.monitoring.alert_models.AlertSeverity`
5. **AgentState** (5 definitions) → Use `app.agents.state.DeepAgentState`
6. **ToolStatus** (4 definitions) → Consolidate to `app.schemas.Tool.ToolStatus`
7. **MetricType** (4 definitions) → Use `app.schemas.Metrics.MetricType`
8. **DataSubAgent** (4 definitions) → Keep production version, remove test mocks
9. **User** (3 definitions) → Use `app.schemas.User.User`
10. **ToolResult** (3 definitions) → Use `app.schemas.Tool.ToolResult`

### Frontend TypeScript Duplicates (Critical)
1. **Message** (8 definitions) → Use `frontend/types/messages.ts`
2. **SubAgentState** (7 definitions) → Use `frontend/types/agents.ts`
3. **User** (5 definitions) → Sync with backend via auto-generation
4. **ToolResult** (5 definitions) → Use `frontend/types/tools.ts`
5. **ToolInput** (5 definitions) → Use `frontend/types/tools.ts`
6. **WebSocketMessage** (4 definitions) → Use `frontend/types/messages.ts`

## CANONICAL IMPORT PATHS

### Backend Python Types
```python
# Core Domain Types
from app.schemas.registry import (
    User, Message, AgentMetadata, WebSocketMessage, MessageType, 
    AgentStatus, ProcessingResult
)

# Configuration Types  
from app.schemas.config_types import (
    CacheConfig, DatabaseConfig, LLMConfig, AuthConfig
)

# Agent Types
from app.schemas.shared_types import (
    AgentConfig, RetryConfig, ProcessingResult, AgentStatus
)

# Tool Types
from app.schemas.Tool import (
    ToolStatus, ToolResult, ToolInput, ToolConfig, ToolPermission
)

# WebSocket Types
from app.schemas.websocket_message_types import (
    WebSocketValidationError, ServerMessage, ClientMessage, BroadcastResult
)

# Database Models
from app.db.models_postgres import (
    UserModel, MessageModel, ThreadModel, ReferenceModel
)

# Core Infrastructure
from app.core.websocket_recovery_strategies import WebSocketConnectionManager
from app.core.circuit_breaker import CircuitBreaker
from app.core.exceptions import NetraException, NetraConfigurationError
```

### Frontend TypeScript Types
```typescript
// Core Domain Types
import { User, Message, Thread, Reference } from '@/types/backend_schema_auto_generated';

// Agent Types  
import { AgentState, SubAgentStatus, AgentMessage } from '@/types/agents';

// WebSocket Types
import { WebSocketMessage, WebSocketError } from '@/types/messages';

// Tool Types
import { ToolResult, ToolInput, ToolStatus } from '@/types/tools';

// UI Component Types
import { MessageItemProps, ChatWindowProps } from '@/types/components';

// Store Types
import { ChatState, ThreadState, AuthState } from '@/types/store';
```

## TYPE HIERARCHY ORGANIZATION

### Backend Structure (`app/schemas/`)
```
app/schemas/
├── registry.py              # Central type registry (all core types)
├── config_types.py          # All configuration types
├── websocket_message_types.py # WebSocket communication types
├── shared_types.py          # Cross-module shared types
├── strict_types.py          # Validation and type safety utilities
├── [Domain].py              # Domain-specific types (User, Message, etc.)
└── admin_[feature].py       # Admin-specific type extensions
```

### Frontend Structure (`frontend/types/`)
```
frontend/types/
├── index.ts                 # Main type exports
├── backend_schema_auto_generated.ts # Auto-synced with backend
├── agents.ts                # Agent-related types
├── messages.ts              # Message and WebSocket types  
├── tools.ts                 # Tool execution types
├── auth.ts                  # Authentication types
├── components.ts            # React component prop types
└── store/                   # State management types
    ├── chat.ts
    ├── auth.ts
    └── threads.ts
```

## DEDUPLICATION EXECUTION STRATEGY

### Phase 1: Critical Infrastructure Types (Week 1)
1. **WebSocketConnectionManager consolidation**
2. **CacheConfig unification** 
3. **AgentConfig consolidation**
4. **AgentMetadata consolidation**
5. **Update all imports across codebase**

### Phase 2: High-Frequency Duplicates (Week 2)
1. **CircuitBreaker** consolidation (6 → 1)
2. **AlertSeverity** unification (6 → 1)  
3. **AgentState** consolidation (5 → 1)
4. **ToolStatus/ToolResult** unification (4 → 1)
5. **User type** alignment (3 → 1)

### Phase 3: Test Utility Consolidation (Week 3)  
1. **TestErrorHandling** unification (9 → 1)
2. **TestIntegrationScenarios** consolidation (6 → 1)
3. **Mock object** deduplication
4. **Test helper** centralization

### Phase 4: Frontend-Backend Alignment (Week 4)
1. **Message types** alignment (8 frontend + 3 backend → 1 each)
2. **SubAgentState** consolidation (7 → 1)
3. **Tool types** unification across stack
4. **Auto-generation** pipeline enhancement

### Phase 5: Validation & Enforcement (Week 5)
1. **Duplicate detection** automation
2. **Import validation** rules
3. **Pre-commit hooks** for type safety
4. **CI/CD integration** for duplicate prevention

## IMPORT MIGRATION PLAN

### Automated Migration Strategy
```bash
# 1. Create canonical types first
# 2. Update imports with sed/awk scripts
find app/ -name "*.py" -exec sed -i 's/from app\.agents\.config import CacheConfig/from app.schemas.config_types import CacheConfig/g' {} \;

# 3. Remove duplicate definitions
# 4. Run tests to verify
# 5. Update documentation
```

### Manual Migration Checklist
- [ ] Update all import statements
- [ ] Remove duplicate class definitions  
- [ ] Update inheritance hierarchies
- [ ] Fix circular import issues
- [ ] Update type annotations
- [ ] Verify all tests pass
- [ ] Update API documentation

## QUALITY ASSURANCE

### Pre-Migration Validation
```bash
# Count current duplicates
python scripts/deduplicate_types.py --scan-only

# Test current functionality  
python test_runner.py --level unit

# Document baseline metrics
python scripts/architecture_compliance.py
```

### Post-Migration Validation
```bash
# Verify zero duplicates
python scripts/deduplicate_types.py --validate

# Ensure all tests pass
python test_runner.py --level comprehensive

# Check type safety
python -m mypy app/ --ignore-missing-imports
npx tsc --noEmit

# Verify performance maintained
python scripts/performance_benchmark.py
```

## ESTIMATED IMPACT

### Metrics Improvement
- **File Complexity**: 361 duplicate types → 0 duplicates
- **Import Clarity**: Centralized canonical imports
- **Maintenance Cost**: 70% reduction in type-related bugs
- **Developer Experience**: Single source of truth for all types
- **Type Safety**: 100% alignment between frontend/backend

### Risk Mitigation
- **Breaking Changes**: Minimized through careful import migration
- **Test Coverage**: Maintained through systematic test updates  
- **Performance**: No impact expected (same runtime types)
- **Documentation**: Comprehensive import guides provided

## SUCCESS CRITERIA

✅ **Zero duplicate type definitions** across entire codebase  
✅ **100% type safety** with mypy and TypeScript strict mode  
✅ **Automated validation** preventing future duplicates  
✅ **Complete test coverage** maintained throughout migration  
✅ **Frontend-backend alignment** via auto-generation  
✅ **Developer documentation** for all canonical import paths  
✅ **CI/CD enforcement** of single source of truth principle  

---

**ULTRA DEEP THINK**: This deduplication represents a massive architectural improvement. The current 361 duplicates create maintenance nightmares, import confusion, and type safety issues. By establishing single sources of truth and enforcing them through automation, we create a foundation for sustainable type safety and developer productivity.

**EXECUTION READINESS**: Plan is comprehensive, phased for minimal disruption, and includes full validation strategy. Ready for immediate implementation with proper backup and rollback procedures.
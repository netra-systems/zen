# 🚨 NETRA SSOT (Single Source of Truth) INDEX

## Executive Summary
This document provides a comprehensive index of all SSOT components in the Netra system, ranked by criticality and business impact. Each SSOT is documented with its purpose, dependencies, and integration patterns.

**📌 NEW**: [Tier 4 Operational Components](./SSOT_INDEX_TIER_4.md) - 15 additional critical SSOT components for execution, monitoring, and resilience.

**📊 SYSTEM OPTIMIZATION**: [Netra Optimization Breakdown](./NETRA_OPTIMIZATION_BREAKDOWN.md) - Comprehensive architecture showing AI-specific (25%), general optimization (25%), and hybrid infrastructure (50%) components.

## Critical Ranking (1-10 Scale)

### 🔴 TIER 1: ULTRA-CRITICAL (10/10)
*System cannot function without these*

#### 1. **MISSION_CRITICAL_NAMED_VALUES_INDEX.xml** 
- **Location**: `SPEC/MISSION_CRITICAL_NAMED_VALUES_INDEX.xml`
- **Purpose**: Master index of ALL critical configuration values
- **Impact**: One typo = cascade failure across entire system
- **Business Value**: Without this, no chat, no agents, no value delivery

#### 2. **UniversalRegistry Pattern**
- **Location**: `netra_backend/app/core/registry/universal_registry.py`
- **Purpose**: Generic SSOT for ALL registry patterns (eliminated 48 duplicates)
- **Impact**: Thread-safe multi-user operations, factory pattern support
- **Business Value**: Enables user isolation, reduces maintenance by 90%

#### 3. **UnifiedWebSocketManager**
- **Location**: `netra_backend/app/websocket_core/unified_manager.py`
- **Purpose**: Central WebSocket connection management
- **Impact**: Controls 90% of platform value (real-time chat)
- **Business Value**: No WebSocket = No real-time updates = Dead chat

#### 4. **DatabaseManager (Mega Class)**
- **Location**: `netra_backend/app/db/database_manager.py`
- **Size**: 1825 lines (max 2000)
- **Purpose**: Central SSOT for ALL database operations
- **Impact**: PostgreSQL, ClickHouse, Redis unified interface
- **Business Value**: Database failures = Complete platform failure

### 🟡 TIER 2: CRITICAL (8-9/10)
*Major functionality broken without these*

#### 5. **UnifiedLifecycleManager (Mega Class)**
- **Location**: `netra_backend/app/core/managers/unified_lifecycle_manager.py`
- **Size**: 1950 lines (max 2000)
- **Purpose**: Consolidates 100+ legacy managers
- **Impact**: Startup, shutdown, health monitoring
- **Business Value**: Zero-downtime deployments, chat reliability

#### 6. **UnifiedConfigurationManager (Mega Class)**
- **Location**: `netra_backend/app/core/managers/unified_configuration_manager.py`
- **Size**: 1890 lines (max 2000)
- **Purpose**: Consolidates 50+ config managers
- **Impact**: Multi-source config with validation
- **Business Value**: Eliminates config drift across environments

#### 7. **UnifiedStateManager (Mega Class)**
- **Location**: `netra_backend/app/core/managers/unified_state_manager.py`
- **Size**: 1820 lines (max 2000)
- **Purpose**: Consolidates 50+ state managers
- **Impact**: Agent state consistency, WebSocket sync
- **Business Value**: Multi-user state isolation

#### 8. **AgentRegistry**
- **Location**: `netra_backend/app/agents/supervisor/agent_registry.py`
- **Purpose**: Central agent registration using UniversalRegistry
- **Impact**: All agent lifecycle and factory management
- **Business Value**: Enables dynamic agent orchestration

### 🟢 TIER 3: IMPORTANT (6-7/10)
*Degraded functionality without these*

#### 9. **UnifiedAuthInterface**
- **Location**: `auth_service/auth_core/unified_auth_interface.py`
- **Purpose**: Central authentication interface
- **Impact**: All auth flows go through this
- **Business Value**: No auth = No user access

#### 10. **LLMManager**
- **Location**: `netra_backend/app/llm/llm_manager.py`
- **Purpose**: Central LLM provider management
- **Impact**: All AI operations depend on this
- **Business Value**: Core AI functionality control

#### 11. **RedisManager**
- **Location**: `netra_backend/app/redis_manager.py`
- **Purpose**: Central Redis connection management
- **Impact**: Caching, session management
- **Business Value**: Performance optimization

#### 12. **UnifiedTestRunner (Mega Class)**
- **Location**: `tests/unified_test_runner.py`
- **Size**: 1728 lines (max 2000)
- **Purpose**: Central test orchestration
- **Impact**: All test types coordination
- **Business Value**: Quality assurance automation

## Mermaid Diagrams

### 1. UniversalRegistry Pattern (Core SSOT)
```mermaid
graph TB
    subgraph "UniversalRegistry<T> SSOT Pattern"
        UR[UniversalRegistry Core<br/>Thread-Safe + Generic]
        
        subgraph "Storage Layer"
            ITEMS[Registry Items<br/>Dict str to RegistryItem]
            CATS[Categories<br/>Dict str to Set]
            VALID[Validation Handlers]
        end
        
        subgraph "Registration Methods"
            REG[register<br/>Singleton Pattern]
            REGF[register_factory<br/>Factory Pattern]
            REGC[register_from_config<br/>Config-based]
        end
        
        subgraph "Retrieval Methods"
            GET[get<br/>Get Singleton]
            CREATE[create_instance<br/>Factory Create]
            LIST[list_keys<br/>List All]
        end
        
        subgraph "State Management"
            FREEZE[freeze<br/>Make Immutable]
            METRICS[Metrics Tracking]
            HEALTH[Health Checks]
        end
        
        UR --> ITEMS
        UR --> CATS
        UR --> VALID
        
        REG --> ITEMS
        REGF --> ITEMS
        REGC --> ITEMS
        
        GET --> ITEMS
        CREATE --> ITEMS
        LIST --> ITEMS
        
        FREEZE --> UR
        METRICS --> UR
        HEALTH --> UR
    end
    
    subgraph "Concrete Implementations"
        AR[AgentRegistry]
        TR[ToolRegistry]
        SR[ServiceRegistry]
        
        AR -.-> UR
        TR -.-> UR
        SR -.-> UR
    end
```

### 2. WebSocket Manager SSOT
```mermaid
graph TB
    subgraph "UnifiedWebSocketManager SSOT"
        WSM[WebSocket Manager<br/>Central Control]
        
        subgraph "Connection Storage"
            CONN[Connections<br/>Dict conn_id to Connection]
            USER[User Connections<br/>Dict user_id to Set conn_id]
        end
        
        subgraph "Core Operations"
            ADD[add_connection]
            REM[remove_connection]
            SEND[send_to_user]
            EMIT[emit_critical_event]
            BROAD[broadcast]
        end
        
        subgraph "Critical Events"
            AS[agent_started]
            AT[agent_thinking]
            TE[tool_executing]
            TC[tool_completed]
            AC[agent_completed]
        end
        
        WSM --> CONN
        WSM --> USER
        
        ADD --> CONN
        REM --> CONN
        SEND --> USER
        EMIT --> USER
        BROAD --> CONN
        
        EMIT --> AS
        EMIT --> AT
        EMIT --> TE
        EMIT --> TC
        EMIT --> AC
    end
    
    subgraph "Integration Points"
        AGENT[Agent Execution]
        TOOL[Tool Dispatcher]
        FRONT[Frontend Chat]
        
        AGENT --> EMIT
        TOOL --> EMIT
        FRONT -.-> WSM
    end
```

### 3. Database Manager SSOT
```mermaid
graph TB
    subgraph "DatabaseManager Mega Class SSOT"
        DM[DatabaseManager<br/>1825 lines<br/>Central DB Control]
        
        subgraph "Database Types"
            PG[PostgreSQL<br/>Main Data]
            CH[ClickHouse<br/>Analytics]
            RD[Redis<br/>Cache]
        end
        
        subgraph "Connection Management"
            POOL[Connection Pools]
            RETRY[Retry Logic]
            HEALTH[Health Checks]
        end
        
        subgraph "Transaction Management"
            TX[Unified Transactions]
            ROLL[Rollback Support]
            ISO[Isolation Levels]
        end
        
        subgraph "Operations"
            QUERY[Query Execution]
            BATCH[Batch Operations]
            MIGRATE[Migrations]
        end
        
        DM --> PG
        DM --> CH
        DM --> RD
        
        POOL --> PG
        POOL --> CH
        POOL --> RD
        
        TX --> QUERY
        TX --> BATCH
        ROLL --> TX
        ISO --> TX
        
        RETRY --> POOL
        HEALTH --> POOL
        MIGRATE --> DM
    end
```

### 4. Configuration Manager SSOT
```mermaid
graph TB
    subgraph "UnifiedConfigurationManager SSOT"
        UCM["Config Manager<br/>1890 lines<br/>50+ configs consolidated"]
        
        subgraph "Config Sources"
            ENV["Environment Vars<br/>IsolatedEnvironment"]
            FILE["Config Files<br/>env and yaml"]
            SEC["Secrets<br/>GCP Secret Manager"]
            DEF["Defaults<br/>Hardcoded"]
        end
        
        subgraph "Precedence Order"
            P1["Environment - Priority 1"]
            P2["Secrets - Priority 2"]
            P3["Files - Priority 3"]
            P4["Defaults - Priority 4"]
        end
        
        subgraph "Validation"
            CRIT["MISSION_CRITICAL<br/>VALUES_INDEX"]
            TYPE["Type Validation"]
            RANGE["Range Checks"]
        end
        
        subgraph "Service Configs"
            BACK["Backend Config"]
            AUTH["Auth Config"]
            FRONT["Frontend Config"]
        end
        
        ENV --> P1
        SEC --> P2
        FILE --> P3
        DEF --> P4
        
        P1 --> UCM
        P2 --> UCM
        P3 --> UCM
        P4 --> UCM
        
        UCM --> CRIT
        UCM --> TYPE
        UCM --> RANGE
        
        UCM --> BACK
        UCM --> AUTH
        UCM --> FRONT
    end
```

### 5. State Manager SSOT
```mermaid
graph TB
    subgraph "UnifiedStateManager SSOT"
        USM[State Manager<br/>1820 lines<br/>Multi-user isolation]
        
        subgraph "State Scopes"
            GLOBAL[Global State]
            USER[User State<br/>Isolated]
            SESSION[Session State<br/>Isolated]
            AGENT[Agent State<br/>Isolated]
        end
        
        subgraph "Storage"
            MEM[In-Memory<br/>Fast Access]
            REDIS[Redis Cache<br/>Distributed]
            DB[Database<br/>Persistent]
        end
        
        subgraph "Operations"
            GET[get_state]
            SET[set_state]
            DEL[delete_state]
            QUERY[query_states]
        end
        
        subgraph "Features"
            TTL[TTL Expiration]
            LOCK[Thread-Safe Locks]
            SYNC[WebSocket Sync]
            FILTER[State Filtering]
        end
        
        USM --> GLOBAL
        USM --> USER
        USM --> SESSION
        USM --> AGENT
        
        MEM --> USM
        REDIS --> USM
        DB --> USM
        
        GET --> MEM
        SET --> MEM
        SET --> SYNC
        DEL --> MEM
        QUERY --> FILTER
        
        TTL --> MEM
        LOCK --> USM
    end
```

### 6. Lifecycle Manager SSOT
```mermaid
graph TB
    subgraph "UnifiedLifecycleManager SSOT"
        LCM[Lifecycle Manager<br/>1950 lines<br/>100+ managers consolidated]
        
        subgraph "Lifecycle Phases"
            INIT[Initialization]
            START[Startup]
            RUN[Running]
            SHUT[Shutdown]
            CLEAN[Cleanup]
        end
        
        subgraph "Component Management"
            DB[Database<br/>Connections]
            WS[WebSocket<br/>Manager]
            AG[Agent<br/>Registry]
            CACHE[Cache<br/>Systems]
        end
        
        subgraph "Health Monitoring"
            CHECK[Health Checks]
            METRIC[Metrics Collection]
            ALERT[Alert Management]
        end
        
        subgraph "Recovery"
            RETRY[Retry Strategies]
            FALL[Fallback Modes]
            GRACE[Graceful Degradation]
        end
        
        INIT --> DB
        INIT --> CACHE
        START --> WS
        START --> AG
        
        RUN --> CHECK
        RUN --> METRIC
        RUN --> ALERT
        
        SHUT --> GRACE
        CLEAN --> DB
        CLEAN --> CACHE
        
        RETRY --> START
        FALL --> RUN
    end
```

### 7. Agent Registry SSOT
```mermaid
graph TB
    subgraph "AgentRegistry SSOT"
        AR[AgentRegistry<br/>Uses UniversalRegistry]
        
        subgraph "Core Agents"
            TRIAGE[Triage Agent<br/>Request Routing]
            DATA[Data Agent<br/>Data Processing]
            OPT[Optimization Agents]
        end
        
        subgraph "Registration Types"
            SINGLE[Singleton Agents<br/>Shared Instance]
            FACTORY[Factory Agents<br/>User Isolated]
        end
        
        subgraph "Lifecycle"
            REG[Registration]
            INIT[Initialization]
            EXEC[Execution]
            CLEAN[Cleanup]
        end
        
        subgraph "Context"
            UC[UserExecutionContext<br/>User Isolation]
            WS[WebSocket Bridge]
            TOOL[Tool Dispatcher]
        end
        
        AR --> TRIAGE
        AR --> DATA
        AR --> OPT
        
        SINGLE --> REG
        FACTORY --> REG
        
        REG --> INIT
        INIT --> EXEC
        EXEC --> CLEAN
        
        UC --> FACTORY
        WS --> AR
        TOOL --> AR
    end
```

## Master Integration Diagram

```mermaid
graph TB
    subgraph "Critical Configuration Layer"
        CRIT[MISSION_CRITICAL_NAMED_VALUES]
    end
    
    subgraph "Core Infrastructure SSOTs"
        UR[UniversalRegistry<br/>Pattern SSOT]
        DM[DatabaseManager<br/>Data SSOT]
        WSM[WebSocketManager<br/>Real-time SSOT]
    end
    
    subgraph "Management SSOTs"
        UCM[ConfigManager<br/>Config SSOT]
        USM[StateManager<br/>State SSOT]
        LCM[LifecycleManager<br/>Lifecycle SSOT]
    end
    
    subgraph "Application SSOTs"
        AR[AgentRegistry<br/>Agent SSOT]
        AUTH[AuthInterface<br/>Auth SSOT]
        LLM[LLMManager<br/>AI SSOT]
    end
    
    subgraph "User Value Delivery"
        CHAT[Chat Interface<br/>90% Business Value]
        AGENTS[Agent Execution]
        RT[Real-time Updates]
    end
    
    %% Critical Dependencies
    CRIT --> UCM
    CRIT --> DM
    CRIT --> WSM
    
    %% Infrastructure Dependencies
    UR --> AR
    UR --> USM
    DM --> USM
    DM --> LCM
    
    %% Management Dependencies
    UCM --> LCM
    UCM --> DM
    UCM --> AUTH
    USM --> AR
    USM --> WSM
    LCM --> DM
    LCM --> WSM
    LCM --> AR
    
    %% Application Dependencies
    AR --> AGENTS
    AUTH --> CHAT
    LLM --> AGENTS
    WSM --> RT
    
    %% Value Delivery
    AGENTS --> CHAT
    RT --> CHAT
    
    style CRIT fill:#ff0000,stroke:#333,stroke-width:4px
    style WSM fill:#ffaa00,stroke:#333,stroke-width:3px
    style CHAT fill:#00ff00,stroke:#333,stroke-width:4px
```

## SSOT Principles & Guidelines

### 1. **Single Source of Truth Rule**
- Each concept has ONE canonical implementation per service
- Cross-service duplication only acceptable for service independence
- See `SPEC/acceptable_duplicates.xml` for exceptions

### 2. **Mega Class Criteria**
- Must be true SSOT for its domain
- Cannot be split without violating SSOT principles
- Max 2000 lines with explicit justification
- Must have >90% test coverage

### 3. **Thread Safety Requirements**
- All SSOTs must be thread-safe
- Use RLock for critical sections
- Support concurrent multi-user access
- No shared mutable state

### 4. **Factory Pattern for User Isolation**
- User-scoped components use factory pattern
- Each user gets isolated instance
- No cross-user state pollution
- Context passed through UserExecutionContext

### 5. **Configuration Hierarchy**
1. Environment variables (via IsolatedEnvironment)
2. Secrets (GCP Secret Manager)
3. Config files (.env, .yaml)
4. Hardcoded defaults

### 6. **WebSocket Event Requirements**
Critical events that MUST be emitted:
- agent_started
- agent_thinking
- tool_executing
- tool_completed
- agent_completed

## Compliance Checklist

Before modifying any SSOT:
- [ ] Check MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
- [ ] Verify no duplicate implementation exists
- [ ] Ensure thread-safety maintained
- [ ] Update mega_class_exceptions.xml if size changes
- [ ] Run compliance check: `python scripts/check_architecture_compliance.py`
- [ ] Test multi-user scenarios
- [ ] Verify WebSocket events still emit
- [ ] Update this index if adding new SSOT

## Quick Reference Commands

```bash
# Check SSOT compliance
python scripts/check_architecture_compliance.py

# Validate string literals
python scripts/query_string_literals.py validate "your_string"

# Test WebSocket events
python tests/mission_critical/test_websocket_agent_events_suite.py

# Run unified tests
python tests/unified_test_runner.py --real-services
```

## Critical Files to Never Break

1. `SPEC/MISSION_CRITICAL_NAMED_VALUES_INDEX.xml` - Config values
2. `netra_backend/app/core/registry/universal_registry.py` - Registry pattern
3. `netra_backend/app/websocket_core/unified_manager.py` - WebSocket core
4. `netra_backend/app/db/database_manager.py` - Database operations
5. `netra_backend/app/core/managers/*.py` - Unified managers

## 🔵 TIER 4: OPERATIONAL COMPONENTS (5-6/10)
*See [SSOT_INDEX_TIER_4.md](./SSOT_INDEX_TIER_4.md) for complete documentation*

**Summary**: 15 operational SSOT components critical for:
- Agent execution orchestration (ExecutionEngine, WorkflowOrchestrator)
- User isolation and context management (UserExecutionContext, RequestScopedToolDispatcher)
- Real-time notifications (WebSocketNotifier, MessageRouter, EventValidator)
- System resilience (CircuitBreaker, ConfigurationValidator, MigrationTracker)
- Monitoring and observability (AgentHealthMonitor, AgentExecutionTracker, ResourceMonitor)
- Service orchestration (StartupOrchestrator, ToolExecutorFactory)

**Business Impact**: Without Tier 4 components, the platform would experience:
- No agent execution or workflow coordination
- Loss of real-time chat updates
- Inability to isolate user requests
- No fault tolerance or circuit breaking
- Flying blind without monitoring
- Manual service startup and configuration

---

**Last Updated**: 2025-01-05
**Next Review**: Quarterly or when approaching size limits
**Owner**: Principal Engineer Role
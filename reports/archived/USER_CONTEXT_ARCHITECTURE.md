# User Context Architecture - Factory-Based Isolation Patterns

## Overview
This document serves as the authoritative guide to Netra's Factory-based isolation patterns that ensure complete user isolation, eliminate shared state, and enable reliable concurrent execution for 10+ users.

**Business Impact:** $500K+ ARR depends on this architecture working correctly - it enables the core chat functionality that delivers AI value to users.

**Key Principles:**
- **Factory Pattern Enforcement:** No direct instantiation of execution engines, WebSocket emitters, or tool dispatchers
- **Request-Scoped Isolation:** Every request gets its own isolated execution context and components
- **User-Specific Resource Limits:** Per-user concurrency control and automatic cleanup
- **Real-Time WebSocket Events:** Critical events (agent_started, tool_executing, etc.) enable chat UX
- **Immutable Context Design:** UserExecutionContext is frozen to prevent accidental state modification
- **Comprehensive Validation:** Fail-fast validation prevents placeholder values and data corruption

## Related Documentation
- **[Documentation Hub](../docs/index.md)** - Central documentation index
- **[Agent Architecture Disambiguation Guide](../docs/AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md)** - Clarifies component relationships
- **[Golden Agent Index](../docs/GOLDEN_AGENT_INDEX.md)** - Definitive agent implementation patterns
- **[WebSocket Thread Association Learning](../SPEC/learnings/websocket_thread_association_critical_20250903.xml)** - Critical thread routing patterns
- **[Tool Dispatcher Migration Guide](./TOOL_DISPATCHER_MIGRATION_GUIDE.md)** - Migration to request-scoped dispatchers
- **[Configuration Architecture](../docs/configuration_architecture.md)** - Environment and configuration management
- **[String Literals Index](../docs/STRING_LITERALS_USAGE_GUIDE.md)** - Critical configuration values protection

## High-Level Architecture Overview

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[User Interface]
        WS_Client[WebSocket Client]
    end
    
    subgraph "API Gateway & Auth"
        Route[Agent Route Handler]
        Auth[JWT Authentication]
        CORS[CORS Middleware]
    end
    
    subgraph "Factory Layer - Per-Request Isolation"
        EEF[ExecutionEngineFactory]
        WSBF[WebSocketBridgeFactory] 
        UTDF[UnifiedToolDispatcherFactory]
        UCF[UserContextFactory]
    end
    
    subgraph "Execution Layer - User-Isolated Instances"
        UEE[UserExecutionEngine]
        UWE[UserWebSocketEmitter]
        UTD[UnifiedToolDispatcher]
        UEC[UserExecutionContext]
    end
    
    subgraph "Agent Layer - Per-User State"
        AR[AgentRegistry]
        AEC[AgentExecutionCore]
        WSN[WebSocketNotifier]
    end
    
    subgraph "Infrastructure - Shared Services"
        DB[Database Pool]
        Redis[Redis Cache]
        LLM[LLM Manager]
        CP[Connection Pool]
    end
    
    UI --> Route
    WS_Client --> Route
    Route --> Auth
    Auth --> CORS
    CORS --> UCF
    
    UCF --> EEF
    EEF --> UEE
    WSBF --> UWE
    UTDF --> UTD
    
    UEE --> UEC
    UEE --> AR
    UEE --> AEC
    
    UWE --> WSN
    UWE --> CP
    
    UTD --> UEC
    
    AR --> LLM
    AEC --> DB
    WSN --> Redis
    
    style EEF fill:#90EE90
    style WSBF fill:#90EE90  
    style UTDF fill:#90EE90
    style UCF fill:#90EE90
    style UEE fill:#87CEEB
    style UWE fill:#87CEEB
    style UTD fill:#87CEEB
    style UEC fill:#FFE4B5
```

## Detailed Factory Pattern Architecture

```mermaid
graph LR
    subgraph "Request Lifecycle"
        REQ[HTTP Request]
        AUTH[JWT Authentication]
        CTX[UserExecutionContext Creation]
        FACT[Factory Orchestration]
        EXEC[User-Isolated Execution]
        CLEAN[Resource Cleanup]
    end
    
    subgraph "Factory Components"
        subgraph "ExecutionEngineFactory"
            EEF_WS[WebSocket Bridge Validation]
            EEF_Semaphores[User Concurrency Control]
            EEF_Metrics[Engine Lifecycle Tracking]
            EEF_Cleanup[Automatic Cleanup Loop]
        end
        
        subgraph "WebSocketBridgeFactory"
            WSF_Context[UserWebSocketContext]
            WSF_Pool[Connection Pool Access]
            WSF_Emitter[Per-User Event Emitter]
            WSF_Health[Connection Health Monitor]
        end
        
        subgraph "UnifiedToolDispatcherFactory"
            UTDF_Registry[Unified Tool Registry]
            UTDF_Permissions[User Permission Check]
            UTDF_Events[WebSocket Event Integration]
            UTDF_Isolation[Request-Scoped Isolation]
        end
        
        subgraph "UserContextFactory"
            UCF_Validation[Context Validation]
            UCF_Isolation[Metadata Isolation]
            UCF_Children[Child Context Creation]
            UCF_Audit[Audit Trail Setup]
        end
    end
    
    REQ --> AUTH
    AUTH --> CTX
    CTX --> FACT
    FACT --> EEF_WS
    FACT --> WSF_Context
    FACT --> UTDF_Registry
    FACT --> UCF_Validation
    
    EEF_Metrics --> EXEC
    WSF_Health --> EXEC
    UTDF_Events --> EXEC
    UCF_Audit --> EXEC
    
    EXEC --> CLEAN
    
    style EEF_WS fill:#FFE4B5
    style WSF_Context fill:#FFE4B5
    style UTDF_Registry fill:#FFE4B5
    style UCF_Validation fill:#FFE4B5
```

## UserExecutionContext Deep Dive

```mermaid
classDiagram
    class UserExecutionContext {
        <<frozen dataclass>>
        +String user_id
        +String thread_id
        +String run_id  
        +String request_id
        +Optional~AsyncSession~ db_session
        +Optional~String~ websocket_client_id
        +DateTime created_at
        +Dict~String,Any~ agent_context
        +Dict~String,Any~ audit_metadata
        +Int operation_depth
        +Optional~String~ parent_request_id
        
        +from_request() UserExecutionContext
        +from_fastapi_request() UserExecutionContext
        +from_request_supervisor() UserExecutionContext
        +create_child_context(operation_name) UserExecutionContext
        +with_db_session(db_session) UserExecutionContext
        +with_websocket_connection(connection_id) UserExecutionContext
        +verify_isolation() Bool
        +to_dict() Dict
        +get_correlation_id() String
        +get_audit_trail() Dict
        +_validate_required_fields()
        +_validate_no_placeholder_values()
        +_validate_id_consistency()
        +_validate_metadata_isolation()
        +_initialize_audit_trail()
    }
    
    class UserExecutionEngine {
        +UserExecutionContext context
        +AgentInstanceFactory agent_factory
        +UserWebSocketEmitter websocket_emitter
        +String engine_id
        +DateTime created_at
        +Dict active_runs
        +Bool _shutdown
        
        +execute_agent(context, state) AgentExecutionResult
        +execute_agent_pipeline() AgentExecutionResult
        +get_user_context() UserExecutionContext
        +get_user_execution_stats() Dict
        +is_active() Bool
        +cleanup()
    }
    
    class ExecutionEngineFactory {
        +AgentWebSocketBridge _websocket_bridge
        +Dict _active_engines
        +AsyncLock _engine_lock
        +Dict _factory_metrics
        +Int _max_engines_per_user
        +Float _engine_timeout_seconds
        
        +create_for_user(context) UserExecutionEngine
        +user_execution_scope(context) AsyncContextManager
        +cleanup_engine(engine)
        +get_factory_metrics() Dict
        +shutdown()
    }
    
    class UserWebSocketEmitter {
        +UserWebSocketContext user_context
        +UserWebSocketConnection connection
        +Dict delivery_config
        +WebSocketBridgeFactory factory
        +Dict _pending_events
        +List _event_batch
        +Bool _shutdown
        
        +notify_agent_started(agent_name, run_id)
        +notify_agent_thinking(agent_name, run_id, thinking)
        +notify_tool_executing(agent_name, run_id, tool_name, input)
        +notify_tool_completed(agent_name, run_id, tool_name, output)
        +notify_agent_completed(agent_name, run_id, result)
        +notify_agent_error(agent_name, run_id, error)
        +cleanup()
    }
    
    class UnifiedToolDispatcher {
        +UserExecutionContext user_context
        +ToolRegistry tool_registry
        +PermissionService permission_service
        +WebSocketEventEmitter websocket_emitter
        +DispatchStrategy strategy
        
        +dispatch_tool(request) ToolDispatchResponse
        +validate_permissions(tool_name, user_id) Bool
        +_execute_with_monitoring(tool, input)
        +cleanup()
    }
    
    class InvalidContextError {
        <<exception>>
        +String message
    }
    
    class ContextIsolationError {
        <<exception>>
        +String message
    }
    
    UserExecutionContext --> InvalidContextError : throws
    UserExecutionContext --> ContextIsolationError : throws
    
    ExecutionEngineFactory --> UserExecutionEngine : creates
    UserExecutionEngine --> UserExecutionContext : uses
    UserExecutionEngine --> UserWebSocketEmitter : uses
    
    UserWebSocketEmitter --> UserExecutionContext : references
    UnifiedToolDispatcher --> UserExecutionContext : uses
    
    UserExecutionContext --> UserExecutionContext : creates child
```

## Context Hierarchy and Child Context Flow

```mermaid
graph TB
    subgraph "Parent Context Lifecycle"
        PC[Parent UserExecutionContext<br/>user_id: user123<br/>run_id: run456<br/>request_id: req789]
        
        subgraph "Child Context Creation"
            CC1[Child Context 1<br/>operation: data_analysis<br/>request_id: req789_data_analysis<br/>parent_request_id: req789]
            CC2[Child Context 2<br/>operation: optimization<br/>request_id: req789_optimization<br/>parent_request_id: req789]
            CC3[Child Context 3<br/>operation: reporting<br/>request_id: req789_reporting<br/>parent_request_id: req789]
        end
        
        subgraph "Grand-Child Contexts"
            GCC1[Grand-Child<br/>operation: data_validation<br/>request_id: req789_data_analysis_validation<br/>parent: req789_data_analysis<br/>depth: 2]
            GCC2[Grand-Child<br/>operation: cost_analysis<br/>request_id: req789_optimization_cost<br/>parent: req789_optimization<br/>depth: 2]
        end
        
        subgraph "Metadata Inheritance"
            META[Inherited Metadata<br/>• parent_request_id<br/>• operation_name<br/>• operation_depth<br/>• custom metadata]
        end
    end
    
    PC --> CC1
    PC --> CC2
    PC --> CC3
    
    CC1 --> GCC1
    CC2 --> GCC2
    
    CC1 -.-> META
    CC2 -.-> META
    CC3 -.-> META
    GCC1 -.-> META
    GCC2 -.-> META
    
    style PC fill:#e8f5e8,stroke:#2e7d32,stroke-width:3px
    style CC1 fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style CC2 fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style CC3 fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style GCC1 fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style GCC2 fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style META fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
```

## Child Context Creation Flow

```mermaid
sequenceDiagram
    participant PE as Parent Execution
    participant PC as Parent Context
    participant CF as Context Factory
    participant CC as Child Context
    participant CE as Child Execution
    participant WS as WebSocket
    
    Note over PE,CE: Child Context Creation Process
    
    PE->>PC: create_child_context("data_analysis")
    PC->>CF: validate operation_name
    CF->>CF: generate new request_id
    CF->>CF: inherit parent metadata
    CF->>CF: increment operation_depth
    CF-->>PC: validated parameters
    
    PC->>CC: new UserExecutionContext
    Note right of CC: run_id: parent.run_id<br/>request_id: parent.request_id_data_analysis<br/>metadata: enhanced with parent info
    
    CC->>CC: validate_required_ids()
    CC->>CC: validate_no_placeholder_values()
    CC->>CC: validate_metadata()
    
    PC-->>PE: Child Context Ready
    
    PE->>CE: execute with child context
    CE->>WS: notify with child request_id
    WS-->>Client: event with operation context
    
    CE->>CE: perform operation
    CE-->>PE: operation results
    
    PE->>PC: cleanup child context
    Note over PC: Child cleanup handled automatically<br/>Parent context remains active
```

## Request Flow with User Isolation

```mermaid
sequenceDiagram
    participant Client
    participant API as Agent Route
    participant Auth as JWT Auth
    participant UCF as UserContextFactory
    participant EEF as ExecutionEngineFactory
    participant WSBF as WebSocketBridgeFactory
    participant UEE as UserExecutionEngine
    participant UWE as UserWebSocketEmitter
    participant UTD as UnifiedToolDispatcher
    participant Agent
    participant SubAgent as Child Agent
    participant DB
    
    Client->>API: POST /agents/execute
    API->>Auth: Validate JWT token
    Auth-->>API: user_id, permissions
    
    rect rgb(200, 255, 200)
        Note over API,UCF: User Context Creation Phase
        API->>UCF: from_fastapi_request()
        UCF->>UCF: Validate IDs and metadata isolation
        UCF->>UCF: Initialize audit trail
        UCF-->>API: UserExecutionContext
        Note right of UCF: Immutable context with<br/>user_id, thread_id, run_id<br/>request_id, audit metadata
    end
    
    rect rgb(255, 230, 200)
        Note over EEF,WSBF: Factory Orchestration Phase
        API->>EEF: create_for_user(user_context)
        EEF->>EEF: Enforce user concurrency limits (max 2)
        EEF->>EEF: Validate WebSocket bridge availability
        
        EEF->>WSBF: create_user_emitter(user_id, thread_id, connection_id)
        WSBF->>WSBF: Validate real WebSocket connection exists
        WSBF->>WSBF: Create UserWebSocketContext with event queue
        WSBF-->>EEF: UserWebSocketEmitter with delivery guarantees
        
        EEF->>UEE: new UserExecutionEngine(context, websocket_emitter)
        EEF->>EEF: Register in active_engines registry
        EEF-->>API: UserExecutionEngine
    end
    
    rect rgb(200, 200, 255)
        Note over UEE,Agent: User-Isolated Execution Phase
        API->>UEE: execute_agent_pipeline()
        UEE->>UWE: notify_agent_started(agent_name, run_id)
        UWE->>UWE: Queue event in user-specific queue
        UWE->>Client: WebSocket: agent_started event
        
        UEE->>UTD: Create request-scoped tool dispatcher
        UTD->>UTD: Validate user permissions
        
        UEE->>Agent: Execute with isolated UserExecutionContext
        Agent->>UTD: dispatch_tool("query_database", params)
        UTD->>UWE: notify_tool_executing()
        UWE->>Client: WebSocket: tool_executing event
        UTD->>DB: Execute with user context isolation
        DB-->>UTD: User-scoped results
        UTD->>UWE: notify_tool_completed()
        UWE->>Client: WebSocket: tool_completed event
        UTD-->>Agent: Tool results
        
        Note over Agent,SubAgent: Child Context Creation
        Agent->>Agent: create_child_context("data_analysis")
        Note right of Agent: Creates new request_id<br/>operation_depth = 1<br/>parent_request_id set
        Agent->>SubAgent: Execute with child context
        SubAgent->>UWE: notify_agent_started(child_run_id)
        UWE->>Client: WebSocket: child agent_started
        
        SubAgent->>UTD: dispatch_tool() with child context
        UTD->>DB: Query with child context isolation
        DB-->>UTD: Child-scoped data
        UTD-->>SubAgent: Child results
        SubAgent->>UWE: notify_agent_completed(child_run_id)
        UWE->>Client: WebSocket: child agent_completed
        SubAgent-->>Agent: Child operation results
        
        Agent->>UWE: notify_agent_thinking("Analyzing results...")
        UWE->>Client: WebSocket: agent_thinking event
        
        Agent-->>UEE: AgentExecutionResult
        UEE->>UWE: notify_agent_completed(agent_name, run_id)
        UWE->>Client: WebSocket: agent_completed event
        UEE-->>API: Final AgentExecutionResult
    end
    
    rect rgb(255, 200, 200)
        Note over API,UWE: Resource Cleanup Phase
        API->>UEE: cleanup()
        UEE->>UEE: Clear active_runs (all contexts)
        UEE->>UTD: cleanup()
        UTD->>UTD: Clear tool registry and permissions
        UEE->>UWE: cleanup()
        UWE->>UWE: Signal shutdown and drain event queue
        UWE->>UWE: Cancel background processor task
        UEE->>EEF: cleanup_engine(engine)
        EEF->>EEF: Remove from active_engines registry
        EEF->>EEF: Update factory metrics
    end
```

## Tool Dispatcher Integration

```mermaid
graph TB
    subgraph "UnifiedToolDispatcherFactory - Request-Scoped Creation"
        UTDF[UnifiedToolDispatcherFactory]
        
        subgraph "Factory Validation"
            FV_AUTH[Authentication Check]
            FV_PERM[Permission Validation]
            FV_CONTEXT[Context Isolation Verify]
            FV_STRATEGY[Dispatch Strategy Selection]
        end
        
        subgraph "Per-Request Tool Dispatcher Instance"
            UTD[UnifiedToolDispatcher]
            
            subgraph "Request-Scoped Components"
                UTR[Unified Tool Registry]
                PS[Permission Service]
                WEE[WebSocket Event Emitter]
                TM[Tool Metrics Collector]
            end
            
            subgraph "User Context Integration"
                UEC[UserExecutionContext]
                UCR[User Context Resolver]
                ATE[Audit Trail Enhancer]
            end
            
            subgraph "Execution Pipeline"
                TV[Tool Validator]
                TEE[Tool Execution Engine]
                EMH[Error Management Handler]
                RCM[Resource Cleanup Manager]
            end
        end
    end
    
    UTDF --> FV_AUTH
    UTDF --> FV_PERM
    UTDF --> FV_CONTEXT
    UTDF --> FV_STRATEGY
    
    FV_AUTH --> UTD
    FV_PERM --> UTD
    FV_CONTEXT --> UTD
    FV_STRATEGY --> UTD
    
    UTD --> UTR
    UTD --> PS
    UTD --> WEE
    UTD --> TM
    
    UTD --> UEC
    UTD --> UCR
    UTD --> ATE
    
    UTD --> TV
    UTD --> TEE
    UTD --> EMH
    UTD --> RCM
    
    UEC --> UCR
    UCR --> ATE
    
    TV --> TEE
    TEE --> WEE
    WEE --> TM
    
    TEE --> EMH
    EMH --> RCM
    
    style UTDF fill:#DDA0DD
    style UTD fill:#98FB98
    style UEC fill:#FFE4B5
    style WEE fill:#FFB6C1
```

## Resource Management & Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Initializing: Request received
    
    Initializing --> Active: Context created
    note right of Initializing
        - Create UserExecutionContext
        - Initialize factories
        - Allocate resources
    end note
    
    Active --> Executing: Agent pipeline started
    note right of Active
        - Request scoped
        - User isolated
        - Resources bounded
    end note
    
    Executing --> Executing: Multiple agents
    note right of Executing
        - Per-user semaphore
        - Active run tracking
        - WebSocket events
    end note
    
    Executing --> Completed: Success
    Executing --> Failed: Error
    
    Completed --> Cleaned: Cleanup triggered
    Failed --> Cleaned: Cleanup triggered
    
    note right of Cleaned
        - Release semaphores
        - Clear event queues
        - Remove from active
        - Trim history
    end note
    
    Cleaned --> [*]: Resources freed
```

## Factory Metrics & Monitoring

```mermaid
graph LR
    subgraph "ExecutionEngineFactory Metrics"
        EEF_M[Factory Metrics]
        EEF_EC[engines_created]
        EEF_EA[engines_active]
        EEF_ECL[engines_cleaned]
        EEF_TU[total_users]
        EEF_CP[concurrent_peak]
    end
    
    subgraph "UserExecutionContext Metrics"
        UC_M[Context Metrics]
        UC_TR[total_runs]
        UC_SR[successful_runs]
        UC_FR[failed_runs]
        UC_ET[execution_time_ms]
        UC_AT[avg_time_ms]
    end
    
    subgraph "WebSocketBridge Metrics"
        WS_M[WebSocket Metrics]
        WS_EC[emitters_created]
        WS_EA[emitters_active]
        WS_ES[events_sent_total]
        WS_EF[events_failed_total]
        WS_HB[heartbeat_status]
    end
    
    EEF_M --> EEF_EC
    EEF_M --> EEF_EA
    EEF_M --> EEF_ECL
    EEF_M --> EEF_TU
    EEF_M --> EEF_CP
    
    UC_M --> UC_TR
    UC_M --> UC_SR
    UC_M --> UC_FR
    UC_M --> UC_ET
    UC_M --> UC_AT
    
    WS_M --> WS_EC
    WS_M --> WS_EA
    WS_M --> WS_ES
    WS_M --> WS_EF
    WS_M --> WS_HB
```

## Multi-User Concurrent Execution Patterns

```mermaid
graph TB
    subgraph "Concurrent User Isolation - 10+ Users"
        subgraph "User A Request Flow"
            UA_CTX[UserExecutionContext A]
            UA_ENG[UserExecutionEngine A]
            UA_WS[UserWebSocketEmitter A]
            UA_TOOLS[ToolDispatcher A]
        end
        
        subgraph "User B Request Flow (Simultaneous)"
            UB_CTX[UserExecutionContext B]
            UB_ENG[UserExecutionEngine B]
            UB_WS[UserWebSocketEmitter B]
            UB_TOOLS[ToolDispatcher B]
        end
        
        subgraph "User C Request Flow (Simultaneous)"
            UC_CTX[UserExecutionContext C]
            UC_ENG[UserExecutionEngine C]
            UC_WS[UserWebSocketEmitter C]
            UC_TOOLS[ToolDispatcher C]
        end
        
        subgraph "Shared Infrastructure (Thread-Safe)"
            DB_POOL[Database Connection Pool]
            REDIS[Redis Cache]
            LLM_MGR[LLM Manager]
            AG_REG[Agent Registry]
        end
        
        subgraph "Factory Resource Management"
            EEF_SEM[User Semaphores<br/>Max 2 per user]
            WSF_POOL[WebSocket Connection Pool]
            CLEANUP[Background Cleanup Loop]
            METRICS[Factory Metrics]
        end
    end
    
    UA_CTX --> UA_ENG
    UA_ENG --> UA_WS
    UA_ENG --> UA_TOOLS
    
    UB_CTX --> UB_ENG
    UB_ENG --> UB_WS
    UB_ENG --> UB_TOOLS
    
    UC_CTX --> UC_ENG
    UC_ENG --> UC_WS
    UC_ENG --> UC_TOOLS
    
    UA_ENG --> DB_POOL
    UB_ENG --> DB_POOL
    UC_ENG --> DB_POOL
    
    UA_WS --> REDIS
    UB_WS --> REDIS
    UC_WS --> REDIS
    
    UA_TOOLS --> LLM_MGR
    UB_TOOLS --> LLM_MGR
    UC_TOOLS --> LLM_MGR
    
    UA_ENG --> AG_REG
    UB_ENG --> AG_REG
    UC_ENG --> AG_REG
    
    EEF_SEM --> UA_ENG
    EEF_SEM --> UB_ENG
    EEF_SEM --> UC_ENG
    
    WSF_POOL --> UA_WS
    WSF_POOL --> UB_WS
    WSF_POOL --> UC_WS
    
    CLEANUP --> METRICS
    
    style UA_CTX fill:#FFE4E1
    style UB_CTX fill:#E1F5FE
    style UC_CTX fill:#E8F5E8
    style EEF_SEM fill:#FFF3E0
    style WSF_POOL fill:#F3E5F5
```

## Agent Execution Order and WebSocket Event Flow

```mermaid
sequenceDiagram
    participant User
    participant WS as WebSocket
    participant API
    participant UEE as UserExecutionEngine
    participant Data as DataAgent
    participant Opt as OptimizationAgent
    participant Rep as ReportAgent
    
    Note over User,Rep: CRITICAL: Agent Execution Order - Data BEFORE Optimization
    
    User->>API: Execute multi-agent workflow
    API->>UEE: execute_agent_pipeline(["data", "optimization", "report"])
    
    rect rgb(200, 255, 200)
        Note over UEE,Data: Phase 1: Data Analysis (Required First)
        UEE->>WS: agent_started("DataAgent")
        WS->>User: "Data analysis starting..."
        
        UEE->>Data: execute() with UserExecutionContext
        Data->>WS: agent_thinking("Analyzing data patterns...")
        WS->>User: "DataAgent is analyzing patterns"
        
        Data->>WS: tool_executing("database_query")
        WS->>User: "DataAgent is querying database"
        Data->>WS: tool_completed("database_query", results)
        WS->>User: "Database query completed"
        
        Data-->>UEE: DataAnalysisResult
        UEE->>WS: agent_completed("DataAgent", results)
        WS->>User: "Data analysis complete"
    end
    
    rect rgb(255, 230, 200)
        Note over UEE,Opt: Phase 2: Optimization (Depends on Data)
        UEE->>WS: agent_started("OptimizationAgent")
        WS->>User: "Optimization starting..."
        
        UEE->>Opt: execute() with data results + UserExecutionContext
        Opt->>WS: agent_thinking("Optimizing based on data...")
        WS->>User: "OptimizationAgent is optimizing"
        
        Opt->>WS: tool_executing("optimization_engine")
        WS->>User: "Running optimization algorithms"
        Opt->>WS: tool_completed("optimization_engine", optimizations)
        WS->>User: "Optimization complete"
        
        Opt-->>UEE: OptimizationResult
        UEE->>WS: agent_completed("OptimizationAgent", optimizations)
        WS->>User: "Optimization analysis complete"
    end
    
    rect rgb(200, 200, 255)
        Note over UEE,Rep: Phase 3: Report Generation (Final Phase)
        UEE->>WS: agent_started("ReportAgent")
        WS->>User: "Report generation starting..."
        
        UEE->>Rep: execute() with data + optimization results + UserExecutionContext
        Rep->>WS: agent_thinking("Generating comprehensive report...")
        WS->>User: "ReportAgent is generating report"
        
        Rep->>WS: tool_executing("report_generator")
        WS->>User: "Creating final report"
        Rep->>WS: tool_completed("report_generator", report)
        WS->>User: "Report generation complete"
        
        Rep-->>UEE: ComprehensiveReport
        UEE->>WS: agent_completed("ReportAgent", final_report)
        WS->>User: "Complete workflow finished"
    end
    
    UEE-->>API: Final workflow results
    API-->>User: Complete response with all results
```

## Security & Isolation Boundaries

```mermaid
graph TB
    subgraph "Security Layers"
        subgraph "Authentication Layer"
            AUTH[JWT Validation]
            SESS[Session Management]
            PERM[Permission Check]
        end
        
        subgraph "Isolation Layer"
            ISO1[Request Isolation]
            ISO2[User Isolation]
            ISO3[Thread Isolation]
            ISO4[Resource Isolation]
        end
        
        subgraph "Resource Boundaries"
            SEM[User Semaphores<br/>Max 5 concurrent]
            MEM[Memory Limits<br/>1024MB threshold]
            TIME[Timeout Controls<br/>30s execution]
            QUEUE[Event Queue<br/>1000 max size]
        end
        
        subgraph "Data Protection"
            SAN[Event Sanitization]
            ENC[Sensitive Data Encryption]
            AUDIT[Audit Logging]
            CLEAN[Secure Cleanup]
        end
    end
    
    AUTH --> ISO1
    SESS --> ISO2
    PERM --> ISO3
    
    ISO1 --> SEM
    ISO2 --> MEM
    ISO3 --> TIME
    ISO4 --> QUEUE
    
    SEM --> SAN
    MEM --> ENC
    TIME --> AUDIT
    QUEUE --> CLEAN
    
    style AUTH fill:#FFD700
    style ISO1 fill:#FF6B6B
    style SEM fill:#4ECDC4
    style SAN fill:#95E77E
```

## Critical WebSocket Events for Chat Business Value

```mermaid
flowchart LR
    subgraph "Required WebSocket Events - Business Critical"
        AS[agent_started]
        AT[agent_thinking]
        TE[tool_executing]
        TC[tool_completed]
        AC[agent_completed]
        AE[agent_error]
    end
    
    subgraph "User Experience Impact"
        AS --> UX1["User sees AI started"]
        AT --> UX2["Real-time reasoning visibility"]
        TE --> UX3["Tool usage transparency"]
        TC --> UX4["Tool results display"]
        AC --> UX5["Final response ready"]
        AE --> UX6["Error handling"]
    end
    
    subgraph "Business Value"
        UX1 --> BV1["Engagement"]
        UX2 --> BV2["Trust Building"]
        UX3 --> BV3["Process Transparency"]
        UX4 --> BV4["Actionable Insights"]
        UX5 --> BV5["Completion Clarity"]
        UX6 --> BV6["Reliability"]
    end
    
    style AS fill:#90EE90
    style AT fill:#87CEEB
    style TE fill:#DDA0DD
    style TC fill:#F0E68C
    style AC fill:#FFA07A
    style AE fill:#FFB6C1
```

**MISSION CRITICAL:** These WebSocket events MUST be sent during agent execution or chat functionality is broken. Missing events = lost $500K+ ARR.

## Key Benefits of Factory-Based Architecture

1. **Complete User Isolation**: Each request gets its own UserExecutionContext and execution engine
2. **No Shared State**: Factory pattern eliminates singleton-based race conditions and cross-user data leakage
3. **Resource Management**: Per-user concurrency limits (max 2 engines per user) prevent resource exhaustion
4. **Clean Lifecycle**: ExecutionEngineFactory automatic cleanup loop prevents memory leaks
5. **Observable**: Comprehensive factory metrics and WebSocket event monitoring
6. **Scalable**: Supports 10+ concurrent users with bounded resource usage
7. **Secure**: Multiple isolation boundaries, request-scoped permission checks, and audit trails
8. **Maintainable**: Single source of truth factories, clear separation of concerns
9. **Hierarchical Context Management**: Child contexts enable sub-agent isolation while maintaining traceability
10. **Operation Traceability**: Full parent-child relationship tracking with metadata inheritance and audit trails
11. **Flexible Agent Orchestration**: Supports complex multi-level agent workflows with proper isolation
12. **Real-time User Feedback**: Per-user WebSocket emitters ensure correct event delivery
13. **Request-Scoped Tools**: UnifiedToolDispatcherFactory ensures tool execution isolation
14. **Fail-Fast Validation**: Comprehensive context validation prevents placeholder values and data corruption

## Migration from Singleton Pattern

The factory-based architecture replaces dangerous singleton patterns:
- `ExecutionEngine` singleton → `UserExecutionEngine` per request via `ExecutionEngineFactory`
- `WebSocketBridge` singleton → `UserWebSocketEmitter` per user via `WebSocketBridgeFactory`
- Global tool dispatcher → Request-scoped `UnifiedToolDispatcher` via `UnifiedToolDispatcherFactory`
- Shared state dictionaries → Immutable frozen `UserExecutionContext` with deep-copy isolation
- Global agent registry → Per-request agent instances with user context integration

## Factory Configuration

All factories support environment-based configuration:

### ExecutionEngineFactory Configuration
- `max_engines_per_user`: User concurrency limit (default: 2)
- `engine_timeout_seconds`: Engine lifetime limit (default: 300s / 5 minutes)
- `cleanup_interval`: Background cleanup frequency (default: 60s)

### WebSocketBridgeFactory Configuration
- `WEBSOCKET_MAX_EVENTS_PER_USER`: Event queue size (default: 1000)
- `WEBSOCKET_EVENT_TIMEOUT`: Event timeout (default: 30.0s)
- `WEBSOCKET_HEARTBEAT_INTERVAL`: Connection health check (default: 30.0s)
- `WEBSOCKET_MAX_RECONNECT_ATTEMPTS`: Max reconnection attempts (default: 3)
- `WEBSOCKET_DELIVERY_RETRIES`: Event delivery retries (default: 3)
- `WEBSOCKET_DELIVERY_TIMEOUT`: Delivery timeout (default: 5.0s)
- `WEBSOCKET_ENABLE_COMPRESSION`: Event compression (default: true)
- `WEBSOCKET_ENABLE_BATCHING`: Event batching (default: true)

### UnifiedToolDispatcherFactory Configuration
- Request-scoped instances (no global configuration needed)
- Per-request permission validation
- User context-based security boundaries

### UserExecutionContext Validation
- Forbidden placeholder values: `registry`, `placeholder`, `default`, `temp`, `none`, `null`, etc.
- Forbidden patterns: `placeholder_`, `registry_`, `default_`, `temp_`, `example_`, etc.
- ID format validation using UnifiedIDManager
- Metadata isolation with deep-copy protection
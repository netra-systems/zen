# User Context Architecture - Multi-Level Diagram

## Overview
This document presents the new user context architecture with Factory patterns and execution isolation at multiple levels of detail.

## Related Documentation
- **[Documentation Hub](./docs/index.md)** - Central documentation index
- **[Agent Architecture Disambiguation Guide](./docs/AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md)** - Clarifies component relationships
- **[Golden Agent Index](./docs/GOLDEN_AGENT_INDEX.md)** - Definitive agent implementation patterns
- **[WebSocket Thread Association Learning](./SPEC/learnings/websocket_thread_association_critical_20250903.xml)** - Critical thread routing patterns
- **[Tool Dispatcher Migration Guide](./TOOL_DISPATCHER_MIGRATION_GUIDE.md)** - Migration to request-scoped dispatchers

## High-Level Architecture Overview

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[User Interface]
        WS_Client[WebSocket Client]
    end
    
    subgraph "API Gateway"
        Route[Agent Route Handler]
        Auth[Authentication]
    end
    
    subgraph "Factory Layer - Request Isolation"
        EEF[ExecutionEngineFactory]
        WSBF[WebSocketBridgeFactory]
        TEF[ToolExecutorFactory]
    end
    
    subgraph "Execution Layer - Per-User"
        IEE[IsolatedExecutionEngine]
        UWE[UserWebSocketEmitter]
        UTD[UnifiedToolDispatcher]
    end
    
    subgraph "Infrastructure - Shared/Immutable"
        AR[AgentRegistry]
        DB[Database Pool]
        Cache[Cache Layer]
    end
    
    UI --> Route
    WS_Client --> Route
    Route --> Auth
    Auth --> EEF
    
    EEF --> IEE
    WSBF --> UWE
    TEF --> UTD
    
    IEE --> AR
    IEE --> DB
    UWE --> Cache
    
    style EEF fill:#90EE90
    style WSBF fill:#90EE90
    style TEF fill:#90EE90
    style IEE fill:#87CEEB
    style UWE fill:#87CEEB
    style UTD fill:#87CEEB
```

## Detailed Factory Pattern Architecture

```mermaid
graph LR
    subgraph "Request Lifecycle"
        REQ[HTTP Request]
        CTX[UserExecutionContext Creation]
        FACT[Factory Instantiation]
        EXEC[Execution]
        CLEAN[Cleanup]
    end
    
    subgraph "Factory Components"
        subgraph "ExecutionEngineFactory"
            EEF_Config[ExecutionFactoryConfig]
            EEF_Metrics[Factory Metrics]
            EEF_Semaphores[User Semaphores]
            EEF_Contexts[Active Contexts]
        end
        
        subgraph "WebSocketBridgeFactory"
            WSF_Config[WebSocketFactoryConfig]
            WSF_Pool[Connection Pool]
            WSF_Contexts[User WS Contexts]
            WSF_Health[Health Monitor]
        end
        
        subgraph "ToolExecutorFactory"
            TEF_Registry[Tool Registry]
            TEF_Validator[Tool Validator]
            TEF_Engine[Execution Engine]
            TEF_Permissions[Permission Service]
        end
    end
    
    REQ --> CTX
    CTX --> FACT
    FACT --> EEF_Config
    FACT --> WSF_Config
    FACT --> TEF_Registry
    
    EEF_Metrics --> EXEC
    WSF_Health --> EXEC
    TEF_Engine --> EXEC
    
    EXEC --> CLEAN
    
    style EEF_Config fill:#FFE4B5
    style WSF_Config fill:#FFE4B5
    style TEF_Registry fill:#FFE4B5
```

## UserExecutionContext Deep Dive

```mermaid
classDiagram
    class UserExecutionContext {
        +String user_id
        +String request_id  
        +String thread_id
        +String run_id
        +String session_id
        +DateTime created_at
        +Dict metadata
        +Optional~AsyncSession~ db_session
        +Optional~String~ websocket_client_id
        
        +create_child_context(operation_name)
        +create_child_context(child_suffix)
        +with_db_session(db_session)
        +with_websocket_connection(connection_id)
        +verify_isolation()
        +to_dict()
        +get_correlation_id()
        +_validate_required_ids()
        +_validate_no_placeholder_values()
        +_validate_metadata()
    }
    
    class ChildExecutionContext {
        +String parent_request_id
        +String operation_name
        +Int operation_depth
        +Dict inherited_metadata
        
        +get_parent_context()
        +get_operation_hierarchy()
    }
    
    class InvalidContextError {
        <<exception>>
        +String message
    }
    
    class IsolatedExecutionEngine {
        +UserExecutionContext user_context
        +AgentRegistry agent_registry
        +UserWebSocketEmitter websocket_emitter
        +Semaphore execution_semaphore
        +Float execution_timeout
        
        +execute_agent_pipeline()
        +_execute_with_monitoring()
        +_init_user_components()
        +cleanup()
        +get_status()
    }
    
    class UserWebSocketEmitter {
        +UserWebSocketContext ws_context
        +Queue event_queue
        +List sent_events
        +List failed_events
        
        +notify_agent_started()
        +notify_agent_completed()
        +notify_agent_error()
        +send_event()
        +cleanup()
    }
    
    UserExecutionContext --> ChildExecutionContext : creates
    UserExecutionContext ..> InvalidContextError : throws
    ChildExecutionContext --> UserExecutionContext : inherits from
    IsolatedExecutionEngine --> UserExecutionContext
    IsolatedExecutionEngine --> UserWebSocketEmitter
    UserWebSocketEmitter --> UserWebSocketContext
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
    participant API as API Route
    participant Auth
    participant EEF as ExecutionEngineFactory
    participant WSF as WebSocketBridgeFactory
    participant IEE as IsolatedExecutionEngine
    participant UWE as UserWebSocketEmitter
    participant Agent
    participant SubAgent as Child Agent
    participant DB
    
    Client->>API: POST /agent/execute
    API->>Auth: Verify user token
    Auth-->>API: user_id, session_id
    
    rect rgb(200, 255, 200)
        Note over API,EEF: Context Creation Phase
        API->>API: Create UserExecutionContext
        Note right of API: user_id, request_id,<br/>thread_id, session_id, run_id
    end
    
    rect rgb(255, 230, 200)
        Note over EEF,WSF: Factory Instantiation Phase
        API->>EEF: create_execution_engine(context)
        EEF->>EEF: Check resource limits
        EEF->>EEF: Get/create user semaphore
        
        EEF->>WSF: create_user_emitter(user_id)
        WSF->>WSF: Create UserWebSocketContext
        WSF-->>EEF: UserWebSocketEmitter
        
        EEF->>IEE: new IsolatedExecutionEngine
        EEF-->>API: IsolatedExecutionEngine
    end
    
    rect rgb(200, 200, 255)
        Note over IEE,Agent: Execution Phase
        API->>IEE: execute_agent_pipeline()
        IEE->>UWE: notify_agent_started()
        UWE->>Client: WebSocket: agent_started
        
        IEE->>Agent: Execute with user context
        Agent->>DB: Query with user isolation
        DB-->>Agent: User-specific data

        Note over Agent,SubAgent: Child Context Creation
        Agent->>Agent: create_child_context("sub_operation")
        Agent->>SubAgent: Execute with child context
        SubAgent->>UWE: notify_agent_started(child_request_id)
        UWE->>Client: WebSocket: child agent_started
        
        SubAgent->>DB: Query with child context isolation
        DB-->>SubAgent: Child-specific data
        SubAgent->>UWE: notify_agent_completed(child_request_id)
        UWE->>Client: WebSocket: child agent_completed
        SubAgent-->>Agent: Child results

        Agent-->>IEE: Result
        
        IEE->>UWE: notify_agent_completed()
        UWE->>Client: WebSocket: agent_completed
        IEE-->>API: AgentExecutionResult
    end
    
    rect rgb(255, 200, 200)
        Note over API,UWE: Cleanup Phase
        API->>IEE: cleanup()
        IEE->>IEE: Clear active_runs (including child contexts)
        IEE->>UWE: cleanup()
        UWE->>UWE: Clear event_queue
        IEE->>EEF: cleanup_context(request_id)
        EEF->>EEF: Remove from active_contexts
    end
```

## Tool Dispatcher Integration

```mermaid
graph TB
    subgraph "UnifiedToolDispatcher Architecture"
        UTD[UnifiedToolDispatcher]
        
        subgraph "Core Components"
            TR[ToolRegistry]
            TV[ToolValidator]
            TEE[ToolExecutionEngine]
            PS[PermissionService]
        end
        
        subgraph "User Context"
            UC[UserExecutionContext]
            UID[user_id]
            RID[request_id]
            TID[thread_id]
        end
        
        subgraph "WebSocket Integration"
            WSE[WebSocketEventEmitter]
            EQ[Event Queue]
            EN[Event Notifications]
        end
        
        subgraph "Tool Execution"
            TE[Tool Execute]
            TM[Tool Metrics]
            TL[Tool Logging]
            TC[Tool Cleanup]
        end
    end
    
    UTD --> TR
    UTD --> TV
    UTD --> TEE
    UTD --> PS
    
    UTD --> UC
    UC --> UID
    UC --> RID
    UC --> TID
    
    UTD --> WSE
    WSE --> EQ
    WSE --> EN
    
    TEE --> TE
    TEE --> TM
    TEE --> TL
    TEE --> TC
    
    style UTD fill:#DDA0DD
    style UC fill:#98FB98
    style WSE fill:#FFB6C1
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

## Key Benefits of New Architecture

1. **Complete User Isolation**: Each request gets its own execution context
2. **No Shared State**: Eliminates race conditions and cross-user data leakage
3. **Resource Management**: Per-user limits prevent resource exhaustion
4. **Clean Lifecycle**: Automatic cleanup prevents memory leaks
5. **Observable**: Comprehensive metrics for monitoring
6. **Scalable**: Supports 10+ concurrent users reliably
7. **Secure**: Multiple isolation boundaries and permission checks
8. **Maintainable**: Single source of truth, clear separation of concerns
9. **Hierarchical Context Management**: Child contexts enable sub-agent isolation while maintaining traceability
10. **Operation Traceability**: Full parent-child relationship tracking with metadata inheritance
11. **Flexible Agent Orchestration**: Supports complex multi-level agent workflows with proper isolation

## Migration from Singleton Pattern

The new architecture replaces dangerous singleton patterns:
- `ExecutionEngine` singleton → `IsolatedExecutionEngine` per request
- `WebSocketBridge` singleton → `UserWebSocketEmitter` per user
- Global tool dispatcher → `UnifiedToolDispatcher` with user context
- Shared state dictionaries → Isolated `UserExecutionContext`

## Factory Configuration

All factories support environment-based configuration:
- `EXECUTION_MAX_CONCURRENT_PER_USER`: User concurrency limit (default: 5)
- `EXECUTION_TIMEOUT_SECONDS`: Execution timeout (default: 30s)
- `WEBSOCKET_MAX_EVENTS_PER_USER`: Event queue size (default: 1000)
- `WEBSOCKET_HEARTBEAT_INTERVAL`: Connection health check (default: 30s)
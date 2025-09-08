# Netra Apex Core Sub-Agent Architecture Flow Diagram

## System Overview

```mermaid
graph TB
    %% Styling
    classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef supervisor fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef agent fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef service fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef infra fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef storage fill:#eceff1,stroke:#263238,stroke-width:2px

    %% Client Layer
    Client[Client/Frontend]:::client
    
    %% API Gateway
    WS[WebSocket Manager]:::service
    API[API Routes]:::service
    
    %% Supervisor Layer
    Supervisor[Supervisor Agent<br/>Orchestrator]:::supervisor
    Registry[Agent Registry]:::supervisor
    
    %% Core Sub-Agents
    Triage[Triage Sub-Agent<br/>Problem Analysis]:::agent
    DataHelper[Data Helper Agent<br/>Data Analysis]:::agent
    Corpus[Corpus Admin Agent<br/>Knowledge Management]:::agent
    Reporting[Reporting Agent<br/>Report Generation]:::agent
    Optimizations[Optimizations Core Agent<br/>Performance Optimization]:::agent
    Actions[Actions to Meet Goals Agent<br/>Solution Planning]:::agent
    Synthetic[Synthetic Data Agent<br/>Data Generation]:::agent
    
    %% Infrastructure Services
    LLM[LLM Manager<br/>Model Selection/Cascade]:::infra
    Tools[Tool Dispatcher<br/>External Tool Access]:::infra
    State[State Manager<br/>Persistence]:::infra
    Circuit[Circuit Breaker<br/>Reliability]:::infra
    
    %% Storage Layer
    Redis[(Redis<br/>Cache/State)]:::storage
    Postgres[(PostgreSQL<br/>Main DB)]:::storage
    ClickHouse[(ClickHouse<br/>Analytics)]:::storage
    
    %% Connections
    Client -->|WebSocket/HTTP| WS
    Client -->|REST| API
    WS --> Supervisor
    API --> Supervisor
    
    Supervisor --> Registry
    Registry -.->|Registers| Triage
    Registry -.->|Registers| DataHelper
    Registry -.->|Registers| Corpus
    Registry -.->|Registers| Reporting
    Registry -.->|Registers| Optimizations
    Registry -.->|Registers| Actions
    Registry -.->|Registers| Synthetic
    
    Supervisor -->|Delegates| Triage
    Supervisor -->|Delegates| DataHelper
    Supervisor -->|Delegates| Corpus
    Supervisor -->|Delegates| Reporting
    Supervisor -->|Delegates| Optimizations
    Supervisor -->|Delegates| Actions
    Supervisor -->|Delegates| Synthetic
    
    Triage --> LLM
    DataHelper --> LLM
    Corpus --> LLM
    Reporting --> LLM
    Optimizations --> LLM
    Actions --> LLM
    Synthetic --> LLM
    
    Triage --> Tools
    DataHelper --> Tools
    Corpus --> Tools
    Actions --> Tools
    
    Supervisor --> State
    Supervisor --> Circuit
    
    State --> Redis
    State --> Postgres
    DataHelper --> ClickHouse
    Reporting --> ClickHouse
```

## Agent Workflow Execution Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant WS as WebSocket Manager
    participant S as Supervisor
    participant R as Registry
    participant CB as Circuit Breaker
    participant UC as UserExecutionContext
    participant A as Sub-Agent
    participant LLM as LLM Manager
    participant T as Tool Dispatcher
    participant ST as State Manager

    C->>WS: Send Request
    WS->>S: Forward Message
    S->>UC: Create/Get Context
    Note right of UC: user_id, thread_id,<br/>run_id, request_id
    S->>R: Get Agent
    R-->>S: Agent Instance
    S->>CB: Check Circuit Status
    CB-->>S: Status OK
    S->>ST: Load State
    ST-->>S: Previous Context
    S->>A: Delegate Task with UserContext
    Note over A,UC: Child context creation<br/>for sub-operations
    A->>UC: create_child_context("operation")
    A->>LLM: Process with LLM (child context)
    LLM-->>A: LLM Response
    A->>T: Execute Tools (child context)
    T-->>A: Tool Results
    A->>ST: Save Progress (with context)
    A-->>S: Task Result
    S->>ST: Update Global State
    S->>WS: Send Response
    WS->>C: Stream Response
```

## Multi-Agent Collaboration Pattern

```mermaid
graph LR
    %% Styling
    classDef phase fill:#e3f2fd,stroke:#0d47a1,stroke-width:2px
    classDef agent fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef decision fill:#fff9c4,stroke:#f57f17,stroke-width:2px

    %% Workflow Phases
    subgraph "Phase 1: Analysis"
        T1[Triage Agent]:::agent
        T1 -->|Analyzes Problem| D1{Needs Data?}:::decision
    end
    
    subgraph "Phase 2: Data Collection"
        D1 -->|Yes| DH[Data Helper]:::agent
        DH -->|Fetches Data| D2{Sufficient Data?}:::decision
    end
    
    subgraph "Phase 3: Solution Planning"
        D2 -->|Yes| A[Actions Agent]:::agent
        A -->|Creates Plan| O[Optimizations Agent]:::agent
    end
    
    subgraph "Phase 4: Implementation"
        O -->|Optimizes| C[Corpus Admin]:::agent
        C -->|Updates Knowledge| S[Synthetic Data]:::agent
    end
    
    subgraph "Phase 5: Reporting"
        S -->|Generates Data| R[Reporting Agent]:::agent
        R -->|Final Report| END[Complete]
    end
    
    D1 -->|No| A
    D2 -->|No| T1
```

## Agent Specialized Capabilities

```mermaid
mindmap
  root((Supervisor<br/>Orchestrator))
    Triage Agent
      Problem Analysis
      Error Classification
      Priority Assessment
      Initial Routing
    Data Helper Agent
      Data Fetching
      Analysis
      Anomaly Detection
      Performance Metrics
    Corpus Admin Agent
      Knowledge Management
      Document Processing
      Corpus Operations
      Value-Based Indexing
    Reporting Agent
      Report Generation
      Visualization
      Insights Compilation
      Executive Summaries
    Optimizations Agent
      Performance Analysis
      Cost Optimization
      Resource Allocation
      Efficiency Recommendations
    Actions Agent
      Goal Planning
      Task Decomposition
      Strategy Formation
      Execution Plans
    Synthetic Data Agent
      Data Generation
      Pattern Creation
      Test Data
      Simulation Scenarios
```

## Error Handling and Resilience Flow

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Processing: Request Received
    Processing --> CircuitCheck: Check Circuit Breaker
    
    CircuitCheck --> Open: Too Many Failures
    CircuitCheck --> Closed: Healthy
    
    Closed --> Execute: Process Request
    Execute --> Success: Task Completed
    Execute --> Failure: Task Failed
    
    Success --> UpdateMetrics: Record Success
    Failure --> RetryCheck: Check Retry Policy
    
    RetryCheck --> Retry: Retries Available
    RetryCheck --> FallbackCheck: No Retries Left
    
    Retry --> Execute: Attempt Again
    FallbackCheck --> Fallback: Has Fallback
    FallbackCheck --> Error: No Fallback
    
    Fallback --> Success: Fallback Success
    Fallback --> Error: Fallback Failed
    
    Open --> FallbackCheck: Circuit Open
    
    UpdateMetrics --> Idle: Complete
    Error --> UpdateMetrics: Record Failure
    
    note right of CircuitCheck
        Circuit Breaker prevents
        cascading failures
    end note
    
    note right of Fallback
        Graceful degradation
        with fallback strategies
    end note
```

## State Management and Persistence

```mermaid
graph TB
    %% Styling
    classDef state fill:#e8eaf6,stroke:#283593,stroke-width:2px
    classDef cache fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef persist fill:#e0f2f1,stroke:#00695c,stroke-width:2px

    subgraph "State Layers"
        Local[Local Agent State]:::state
        Session[Session State]:::state
        Global[Global State]:::state
    end
    
    subgraph "Caching Strategy"
        Redis1[Redis Cache<br/>Hot Data]:::cache
        Memory[In-Memory<br/>Transient]:::cache
    end
    
    subgraph "Persistence"
        PG[PostgreSQL<br/>Durable State]:::persist
        CH[ClickHouse<br/>Analytics]:::persist
    end
    
    Local --> Memory
    Session --> Redis1
    Global --> PG
    
    Memory -.->|TTL Expiry| Redis1
    Redis1 -.->|Backup| PG
    PG -->|Analytics| CH
```

## Notes

- **Supervisor Agent** acts as the central orchestrator, managing task delegation and agent coordination
- **Circuit Breaker** pattern ensures system resilience by preventing cascading failures
- **State Management** uses a multi-tier approach with Redis for hot data and PostgreSQL for persistence
- **LLM Manager** implements model cascade for optimal cost/performance balance
- **Tool Dispatcher** provides unified interface for external tool access
- Each agent is specialized for specific domain tasks, enabling efficient parallel processing
- WebSocket connections enable real-time streaming of agent responses to clients
- **UserExecutionContext** provides complete user isolation with child context support for sub-agent operations
- **Child Context Creation** enables hierarchical agent execution while maintaining proper isolation and traceability
- All contexts include full metadata inheritance and operation depth tracking for comprehensive observability
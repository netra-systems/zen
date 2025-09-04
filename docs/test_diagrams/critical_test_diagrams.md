# Critical Test Failure Analysis & Recovery Diagrams

This document contains comprehensive Mermaid diagrams for all critical and mission-critical tests in the Netra project. These diagrams show failure points, recovery mechanisms, business impact paths, and cascade failure prevention strategies.

## Table of Contents

1. [WebSocket Agent Events - Mission Critical](#websocket-agent-events---mission-critical)
2. [Agent Execution Order & Recovery Strategies](#agent-execution-order--recovery-strategies)
3. [Docker Infrastructure Stability](#docker-infrastructure-stability)
4. [SSOT Compliance & Data Isolation](#ssot-compliance--data-isolation)
5. [Authentication & OAuth Security](#authentication--oauth-security)
6. [Database Transaction Integrity](#database-transaction-integrity)
7. [Service Startup & Configuration](#service-startup--configuration)
8. [Cascade Failure Prevention](#cascade-failure-prevention)

---

## WebSocket Agent Events - Mission Critical

### 1.1 WebSocket Agent Event Flow - Critical Success Path

**Business Impact**: $500K+ ARR - Core chat functionality depends on these events

```mermaid
stateDiagram-v2
    [*] --> AgentStarted: User sends request
    AgentStarted --> AgentThinking: agent_started event sent
    AgentThinking --> ToolExecuting: agent_thinking event sent
    ToolExecuting --> ToolCompleted: tool_executing event sent
    ToolCompleted --> AgentCompleted: tool_completed event sent
    AgentCompleted --> [*]: agent_completed event sent
    
    state AgentStarted {
        [*] --> ValidateWebSocket
        ValidateWebSocket --> SendStartedEvent
        SendStartedEvent --> [*]
    }
    
    state AgentThinking {
        [*] --> ReasoningPhase
        ReasoningPhase --> ProgressUpdate
        ProgressUpdate --> [*]
    }
    
    state ToolExecuting {
        [*] --> ToolDispatch
        ToolDispatch --> ToolExecution
        ToolExecution --> [*]
    }
    
    state ToolCompleted {
        [*] --> ResultProcessing
        ResultProcessing --> ResultValidation
        ResultValidation --> [*]
    }
    
    state AgentCompleted {
        [*] --> FinalResponse
        FinalResponse --> CleanupResources
        CleanupResources --> [*]
    }
    
    note right of AgentStarted : CRITICAL: Must send within 100ms\nof request receipt
    note right of AgentThinking : Shows AI working on valuable\nproblem-solving
    note right of ToolExecuting : Demonstrates problem-solving\napproach transparency
    note right of ToolCompleted : Delivers actionable insights
    note right of AgentCompleted : User knows valuable response\nis ready
```

### 1.2 WebSocket Event Failure & Recovery Patterns

**Critical Failure Points & Business Impact**

```mermaid
flowchart TD
    A[User Request] --> B{WebSocket Connected?}
    B -->|No| C[CRITICAL FAILURE: No Chat Value]
    B -->|Yes| D[Agent Registry Check]
    
    D --> E{WebSocket Manager Set?}
    E -->|No| F[CRITICAL: Events Lost - $50K+ ARR Impact]
    E -->|Yes| G[Tool Dispatcher Enhanced?]
    
    G -->|No| H[CRITICAL: Tool Events Missing]
    G -->|Yes| I[Agent Execution Begins]
    
    I --> J{Event Emission Working?}
    J -->|No| K[SILENT FAILURE - User Confusion]
    J -->|Yes| L[Success Path]
    
    C --> M[Recovery: WebSocket Reconnection]
    F --> N[Recovery: Re-initialize Registry]
    H --> O[Recovery: Enhance Tool Dispatcher]
    K --> P[Recovery: Event Bridge Repair]
    
    M --> Q[Cascade Prevention]
    N --> Q
    O --> Q
    P --> Q
    
    Q --> R{Recovery Successful?}
    R -->|No| S[BUSINESS CRITICAL: Manual Intervention]
    R -->|Yes| T[Resume Normal Operations]
    
    style C fill:#ff6b6b
    style F fill:#ff6b6b
    style H fill:#ff6b6b
    style K fill:#ff9f43
    style S fill:#ff6b6b
```

### 1.3 WebSocket Agent Event Validation Chain

**Testing Requirements & Validation Points**

```mermaid
sequenceDiagram
    participant T as Test Framework
    participant WS as WebSocket Connection
    participant AR as Agent Registry
    participant EE as Execution Engine
    participant TD as Tool Dispatcher
    participant U as User Interface
    
    Note over T,U: Mission Critical Event Validation
    
    T->>WS: 1. Establish Real Connection
    WS-->>T: Connection Confirmed
    
    T->>AR: 2. Initialize Agent Registry
    AR->>AR: Set WebSocket Manager
    Note right of AR: CRITICAL: Must enhance<br/>tool dispatcher
    
    T->>EE: 3. Start Agent Execution
    EE->>WS: agent_started
    WS->>U: Event Delivered
    
    EE->>WS: agent_thinking
    WS->>U: Reasoning Visible
    
    EE->>TD: Execute Tool
    TD->>WS: tool_executing
    WS->>U: Tool Usage Transparent
    
    TD->>WS: tool_completed
    WS->>U: Results Display
    
    EE->>WS: agent_completed
    WS->>U: Response Ready
    
    Note over T,U: VALIDATION: All 5 events<br/>received in order
    
    alt Event Missing
        T-->>T: TEST FAILURE<br/>Business Impact: Chat Broken
    else All Events Present
        T-->>T: TEST SUCCESS<br/>Business Value Protected
    end
```

---

## Agent Execution Order & Recovery Strategies

### 2.1 Agent Execution Dependency Chain

**Critical Business Logic: Data BEFORE Optimization**

```mermaid
graph TB
    subgraph "Critical Execution Order"
        A[Triage Agent] --> B{Data Sufficiency?}
        
        B -->|Sufficient| C[Data Collection Agent]
        B -->|Partial| D[Enhanced Data Agent]
        B -->|Insufficient| E[Data Gathering Agent]
        
        C --> F[Optimization Agent]
        D --> F
        E --> F
        
        F --> G[Actions Agent]
        G --> H[Reporting Agent]
    end
    
    subgraph "Failure Points & Recovery"
        I[Triage Failure] --> J[Retry with Simplified Context]
        K[Data Collection Failure] --> L[Fallback Data Sources]
        M[Optimization Failure] --> N[Basic Recommendations]
        O[Actions Failure] --> P[Manual Action Items]
        Q[Reporting Failure] --> R[Template-based Report]
    end
    
    A -.->|Fails| I
    C -.->|Fails| K
    F -.->|Fails| M
    G -.->|Fails| O
    H -.->|Fails| Q
    
    style F fill:#74b9ff
    style C fill:#74b9ff
    note1[CRITICAL: Optimization MUST<br/>depend on Data completion]
```

### 2.2 Agent Recovery Strategy State Machine

**Recovery Patterns for High-Value Customer Workflows**

```mermaid
stateDiagram-v2
    [*] --> AgentHealthy: Normal Operation
    
    AgentHealthy --> AssessFailure: Exception Detected
    
    state AssessFailure {
        [*] --> IntentDetectionCheck
        IntentDetectionCheck --> DataCollectionCheck
        DataCollectionCheck --> OptimizationCheck
        OptimizationCheck --> [*]
    }
    
    AssessFailure --> RecoveryStrategy: Assessment Complete
    
    state RecoveryStrategy {
        [*] --> choice_state
        choice_state --> RetryWithSimplification: Minor Failure
        choice_state --> FallbackDataSource: Data Failure
        choice_state --> BasicRecommendations: Optimization Failure
        choice_state --> ManualEscalation: Critical Failure
        
        RetryWithSimplification --> [*]
        FallbackDataSource --> [*]
        BasicRecommendations --> [*]
        ManualEscalation --> [*]
    }
    
    RecoveryStrategy --> ValidationPhase: Recovery Attempted
    
    state ValidationPhase {
        [*] --> ValidateRecovery
        ValidateRecovery --> RecoverySuccess: Success
        ValidateRecovery --> RecoveryFailed: Failure
    }
    
    ValidationPhase --> AgentHealthy: Success
    ValidationPhase --> CascadePreventionMode: Failure
    
    state CascadePreventionMode {
        [*] --> IsolateFailure
        IsolateFailure --> PreventSpread
        PreventSpread --> AlertOperations
        AlertOperations --> [*]
    }
    
    CascadePreventionMode --> AgentHealthy: Manual Fix
    
    note right of RecoveryStrategy : Business Value: Protects $30K+ MRR<br/>from agent downtime
```

---

## Docker Infrastructure Stability

### 3.1 Docker Lifecycle Management - Critical Paths

**99.99% Uptime Requirements & Auto-Recovery**

```mermaid
flowchart TD
    A[Docker Service Start] --> B{Port Conflicts?}
    B -->|Yes| C[Auto-resolve Conflicts]
    B -->|No| D[Health Check]
    
    C --> E{Resolution Success?}
    E -->|No| F[CRITICAL: Port Assignment Failed]
    E -->|Yes| D
    
    D --> G{Services Healthy?}
    G -->|No| H[Auto-recovery Sequence]
    G -->|Yes| I[Production Ready]
    
    H --> J[Stop Conflicting Containers]
    J --> K[Clean Resources]
    K --> L[Restart Services]
    L --> M{Recovery Success?}
    
    M -->|No| N[ESCALATION: Manual Intervention]
    M -->|Yes| I
    
    F --> O[Business Impact: Infrastructure Down]
    N --> O
    
    I --> P[Monitor Health]
    P --> Q{Daemon Healthy?}
    Q -->|No| R[Daemon Recovery]
    Q -->|Yes| S[Continue Monitoring]
    
    R --> T{Recovery Attempts < 3?}
    T -->|Yes| U[Restart Docker Daemon]
    T -->|No| V[CRITICAL: Platform Failure]
    
    U --> W{Daemon Restored?}
    W -->|No| T
    W -->|Yes| A
    
    V --> X[Business Impact: $500K+ ARR Loss]
    
    style F fill:#ff6b6b
    style N fill:#ff6b6b
    style V fill:#ff6b6b
    style O fill:#ff9f43
    style X fill:#ff6b6b
```

### 3.2 Docker Resource Management & Memory Protection

**Critical Memory & Resource Limits to Prevent System Crashes**

```mermaid
graph TB
    subgraph "Resource Monitoring & Limits"
        A[Container Start] --> B{Memory < 500MB?}
        B -->|No| C[CRITICAL: Memory Limit Exceeded]
        B -->|Yes| D[CPU Check]
        
        D --> E{CPU < 2 cores?}
        E -->|No| F[CRITICAL: CPU Throttling Required]
        E -->|Yes| G[Disk I/O Check]
        
        G --> H{Disk I/O Healthy?}
        G -->|No| I[CRITICAL: Storage Bottleneck]
        G -->|Yes| J[Resource Allocation OK]
    end
    
    subgraph "Alpine Optimization Path"
        K[Alpine Container] --> L{Base Image < 100MB?}
        L -->|No| M[OPTIMIZATION: Use Alpine]
        L -->|Yes| N[Python Dependencies]
        
        N --> O{Total Size < 300MB?}
        O -->|No| P[OPTIMIZATION: Reduce Dependencies]
        O -->|Yes| Q[Performance Validated]
    end
    
    subgraph "Volume Management"
        R[Volume Creation] --> S{Named Volume?}
        S -->|No| T[CRITICAL: Use Named Volumes Only]
        S -->|Yes| U[Persistent Storage]
        
        note1[CRITICAL WARNING:<br/>tmpfs REMOVED - causes<br/>RAM exhaustion crashes]
    end
    
    C --> Z[Auto-kill Container]
    F --> Z
    I --> Z
    T --> Z
    
    Z --> AA[Resource Cleanup]
    AA --> BB[Retry with Limits]
    
    style C fill:#ff6b6b
    style F fill:#ff6b6b
    style I fill:#ff6b6b
    style T fill:#ff6b6b
    style note1 fill:#ff6b6b
```

### 3.3 Docker Health Monitoring & Cascade Prevention

**Comprehensive Health Checks & Failure Prevention**

```mermaid
sequenceDiagram
    participant M as Monitor
    participant D as Docker Daemon
    participant C1 as Backend Container
    participant C2 as Auth Container
    participant DB as Database
    participant Alert as Alert System
    
    loop Every 30s Health Check
        M->>D: Check Daemon Status
        D-->>M: Status Report
        
        M->>C1: Health Check
        alt Container Healthy
            C1-->>M: 200 OK
        else Container Failing
            C1-->>M: 503 Service Unavailable
            M->>Alert: Container Failure Alert
            M->>C1: Restart Container
        end
        
        M->>C2: Health Check
        alt Container Healthy
            C2-->>M: 200 OK
        else Container Failing
            C2-->>M: 503 Service Unavailable
            M->>Alert: Auth Failure Alert
            M->>C2: Restart Container
        end
        
        M->>DB: Connection Check
        alt Database Healthy
            DB-->>M: Connection OK
        else Database Failing
            DB-->>M: Connection Failed
            M->>Alert: DATABASE CRITICAL
            M->>DB: Recovery Sequence
        end
        
        Note over M: Check Resource Usage
        M->>M: Memory/CPU Analysis
        
        alt Resource Exhaustion
            M->>Alert: RESOURCE CRITICAL
            M->>D: Scale Down Services
            Note right of M: Prevent system crash
        end
    end
    
    Note over M,Alert: Business Impact: 99.99% uptime<br/>protects $500K+ ARR
```

---

## SSOT Compliance & Data Isolation

### 4.1 User Context Isolation - Critical Security Boundary

**10+ Concurrent Users - Zero Cross-Contamination**

```mermaid
graph TB
    subgraph "User Request Isolation"
        A[User A Request] --> B[Isolated Context A]
        C[User B Request] --> D[Isolated Context B]
        E[User C Request] --> F[Isolated Context C]
    end
    
    subgraph "Factory Pattern Enforcement"
        B --> G[Factory A Instance]
        D --> H[Factory B Instance]
        F --> I[Factory C Instance]
        
        G --> J[Agent Registry A]
        H --> K[Agent Registry B]
        I --> L[Agent Registry C]
        
        J --> M[WebSocket Manager A]
        K --> N[WebSocket Manager B]
        L --> O[WebSocket Manager C]
    end
    
    subgraph "Database Session Isolation"
        P[Session Pool] --> Q[Session A]
        P --> R[Session B]
        P --> S[Session C]
        
        Q --> T[Transaction A]
        R --> U[Transaction B]
        S --> V[Transaction C]
    end
    
    subgraph "Critical Failure Points"
        W[Shared State Detected] --> X[CRITICAL: Cross-User Data Leak]
        Y[Session Bleed] --> Z[CRITICAL: Data Contamination]
        AA[Registry Shared] --> BB[CRITICAL: Event Mix-up]
    end
    
    G -.->|Shared State| W
    Q -.->|Session Leak| Y
    J -.->|Singleton| AA
    
    X --> CC[Security Breach: $1M+ Liability]
    Z --> CC
    BB --> CC
    
    style X fill:#ff6b6b
    style Z fill:#ff6b6b
    style BB fill:#ff6b6b
    style CC fill:#ff6b6b
    
    note1[CRITICAL: Factory Pattern<br/>prevents all shared state]
    note2[BUSINESS IMPACT:<br/>User data isolation<br/>required by law]
```

### 4.2 Complete Request Isolation - Multi-User Concurrency

**Zero Cross-Request Contamination Under Load**

```mermaid
flowchart TB
    subgraph "Concurrent Request Processing"
        A[Request A - User 1] --> A1[Context A]
        B[Request B - User 2] --> B1[Context B]
        C[Request C - User 3] --> C1[Context C]
        D[Request D - User 1] --> D1[Context D]
    end
    
    subgraph "Agent Instance Isolation"
        A1 --> A2[Fresh Agent Instance A]
        B1 --> B2[Fresh Agent Instance B]
        C1 --> C2[Fresh Agent Instance C]
        D1 --> D2[Fresh Agent Instance D]
        
        A2 --> A3[Agent State A]
        B2 --> B3[Agent State B]
        C2 --> C3[Agent State C]
        D2 --> D3[Agent State D]
    end
    
    subgraph "WebSocket Channel Isolation"
        A3 --> A4[WebSocket Channel A]
        B3 --> B4[WebSocket Channel B]
        C3 --> C4[WebSocket Channel C]
        D3 --> D4[WebSocket Channel D]
        
        A4 --> A5[Events for User 1]
        B4 --> B5[Events for User 2]
        C4 --> C5[Events for User 3]
        D4 --> D5[Events for User 1]
    end
    
    subgraph "Database Session Isolation"
        E[Session Pool] --> E1[DB Session A]
        E --> E2[DB Session B]
        E --> E3[DB Session C]
        E --> E4[DB Session D]
        
        E1 --> E5[Transaction A]
        E2 --> E6[Transaction B]
        E3 --> E7[Transaction C]
        E4 --> E8[Transaction D]
    end
    
    subgraph "Failure Isolation Boundaries"
        F[Agent A Crashes] -.-> G[ISOLATED: No Impact on B,C,D]
        H[WebSocket B Fails] -.-> I[ISOLATED: No Impact on A,C,D]
        J[DB Session C Fails] -.-> K[ISOLATED: No Impact on A,B,D]
        L[Thread D Hangs] -.-> M[ISOLATED: No Impact on A,B,C]
    end
    
    A2 -.->|Failure| F
    B4 -.->|Failure| H
    E3 -.->|Failure| J
    D2 -.->|Failure| L
    
    style G fill:#74b9ff
    style I fill:#74b9ff
    style K fill:#74b9ff
    style M fill:#74b9ff
    
    note1[CRITICAL: Complete isolation<br/>ensures one user's problems<br/>never affect other users]
    note2[Business Impact: Protects<br/>$500K+ ARR from cascade<br/>failures in multi-user scenarios]
```

### 4.3 SSOT Violation Detection & Prevention

**Single Source of Truth Enforcement**

```mermaid
stateDiagram-v2
    [*] --> CodeAnalysis: Scan Codebase
    
    state CodeAnalysis {
        [*] --> ImportAnalysis
        ImportAnalysis --> DuplicationCheck
        DuplicationCheck --> SSotValidation
        SSotValidation --> [*]
    }
    
    CodeAnalysis --> ViolationDetected: Issues Found
    CodeAnalysis --> CompliantCode: Clean Scan
    
    state ViolationDetected {
        [*] --> choice_violation
        choice_violation --> DuplicateLogic: Logic Duplication
        choice_violation --> MultipleSSoT: Multiple Truth Sources
        choice_violation --> SharedStateLeak: Shared State Found
        choice_violation --> ImportViolation: Cross-Service Import
        
        DuplicateLogic --> ConsolidateLogic
        MultipleSSoT --> DesignateCanonical
        SharedStateLeak --> IsolateComponents
        ImportViolation --> RefactorBoundaries
        
        ConsolidateLogic --> ValidationPhase
        DesignateCanonical --> ValidationPhase
        IsolateComponents --> ValidationPhase
        RefactorBoundaries --> ValidationPhase
    }
    
    state ValidationPhase {
        [*] --> RunCompliance
        RunCompliance --> TestSuite
        TestSuite --> [*]
    }
    
    ViolationDetected --> CompliantCode: Fixed
    ViolationDetected --> CriticalViolation: Unfixable
    
    state CriticalViolation {
        [*] --> BusinessImpact
        BusinessImpact --> RequireRefactor
        RequireRefactor --> [*]
        
        note right : Business Impact:<br/>Platform reliability<br/>affects $500K+ ARR
    }
    
    CompliantCode --> [*]
    CriticalViolation --> [*]: Manual Escalation
```

---

## Authentication & OAuth Security

### 5.1 OAuth Configuration Failure Chain

**Critical Security & User Access Failures**

```mermaid
flowchart TD
    A[User Login Attempt] --> B{OAuth Config Present?}
    B -->|No| C[CRITICAL: GOOGLE_CLIENT_ID Missing]
    B -->|Yes| D{Secret Valid?}
    
    D -->|No| E[CRITICAL: GOOGLE_CLIENT_SECRET Invalid]
    D -->|Yes| F[OAuth Provider Initialize]
    
    C --> G[Business Impact: $75K+ MRR Loss]
    E --> G
    
    F --> H{Provider Ready?}
    H -->|No| I[CRITICAL: OAuth Provider Failed]
    H -->|Yes| J[User Auth Flow]
    
    I --> K[Recovery: Fallback Auth]
    
    J --> L{Auth Successful?}
    L -->|No| M[Auth Failure Handling]
    L -->|Yes| N[JWT Token Generation]
    
    M --> O{Retry Count < 3?}
    O -->|Yes| P[Retry with Exponential Backoff]
    O -->|No| Q[CRITICAL: Auth System Down]
    
    P --> J
    Q --> R[Business Impact: Complete User Lockout]
    
    N --> S{JWT Secret Present?}
    S -->|No| T[CRITICAL: JWT_SECRET Missing]
    S -->|Yes| U[Token Validation]
    
    T --> V[Recovery: Generate Temp Secret]
    U --> W[User Session Active]
    
    V --> X{Temp Secret Sync'd?}
    X -->|No| Y[CRITICAL: Cross-Service Auth Failure]
    X -->|Yes| U
    
    style C fill:#ff6b6b
    style E fill:#ff6b6b
    style I fill:#ff6b6b
    style Q fill:#ff6b6b
    style T fill:#ff6b6b
    style Y fill:#ff6b6b
    style G fill:#ff9f43
    style R fill:#ff9f43
```

### 5.2 JWT Secret Synchronization - Cross-Service Security

**Critical Security Boundary Between Services**

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend
    participant A as Auth Service
    participant Env as Environment Config
    
    Note over U,Env: JWT Secret Synchronization Critical Path
    
    U->>F: Login Request
    F->>A: OAuth Authentication
    
    A->>Env: Load JWT_SECRET_AUTH
    alt Secret Missing
        Env-->>A: ❌ No Secret Found
        A-->>F: CRITICAL: Auth Failed
        F-->>U: Login Failure
        Note right of A: Business Impact:<br/>User lockout
    else Secret Present
        Env-->>A: ✅ Secret Loaded
        A->>A: Generate JWT Token
        A-->>F: Token Generated
    end
    
    F->>B: API Request + JWT
    B->>Env: Load JWT_SECRET_BACKEND
    
    alt Secret Mismatch
        Env-->>B: ❌ Different Secret
        B-->>F: 403 Forbidden
        F-->>U: Access Denied
        Note right of B: CRITICAL: Cross-service<br/>auth failure
    else Secrets Match
        Env-->>B: ✅ Same Secret
        B->>B: Validate Token
        B-->>F: API Response
        F-->>U: Success
    end
    
    Note over A,B: CRITICAL REQUIREMENT:<br/>JWT_SECRET_AUTH = JWT_SECRET_BACKEND<br/>Failure = Complete Auth Breakdown
```

### 5.3 Authentication State Consistency & Loop Prevention

**Preventing Auth Loops & Maintaining Session State**

```mermaid
stateDiagram-v2
    [*] --> Unauthenticated
    
    Unauthenticated --> AuthenticationAttempt: Login Request
    
    state AuthenticationAttempt {
        [*] --> ValidateCredentials
        ValidateCredentials --> GenerateToken
        GenerateToken --> StoreSession
        StoreSession --> [*]
    }
    
    AuthenticationAttempt --> Authenticated: Success
    AuthenticationAttempt --> AuthLoop: Token Invalid
    
    state Authenticated {
        [*] --> ActiveSession
        ActiveSession --> TokenRefresh: Token Expiring
        TokenRefresh --> ActiveSession: Success
        TokenRefresh --> TokenExpired: Refresh Failed
    }
    
    state AuthLoop {
        [*] --> LoopDetection
        LoopDetection --> PreventLoop: Loop Count > 3
        PreventLoop --> ForceLogout
        ForceLogout --> [*]
        
        note right : CRITICAL: Prevent infinite<br/>authentication loops
    }
    
    state TokenExpired {
        [*] --> GracefulLogout
        GracefulLogout --> ClearSession
        ClearSession --> [*]
    }
    
    Authenticated --> Unauthenticated: Logout/Expire
    AuthLoop --> Unauthenticated: Force Logout
    TokenExpired --> Unauthenticated
    
    note right of AuthLoop : Business Impact:<br/>User experience<br/>degradation
```

---

## Database Transaction Integrity

### 6.1 Database Session Isolation & Transaction Management

**Critical Data Integrity & Concurrent User Support**

```mermaid
graph TB
    subgraph "Connection Pool Management"
        A[Request A] --> B[Session Pool]
        C[Request B] --> B
        D[Request C] --> B
        
        B --> E[Session A]
        B --> F[Session B]  
        B --> G[Session C]
    end
    
    subgraph "Transaction Isolation"
        E --> H[Transaction A - READ COMMITTED]
        F --> I[Transaction B - READ COMMITTED]
        G --> J[Transaction C - READ COMMITTED]
        
        H --> K{Lock Conflicts?}
        I --> L{Lock Conflicts?}
        J --> M{Lock Conflicts?}
        
        K -->|Yes| N[Deadlock Detection]
        L -->|Yes| N
        M -->|Yes| N
        
        N --> O{Deadlock Found?}
        O -->|Yes| P[CRITICAL: Transaction Rollback]
        O -->|No| Q[Continue Transaction]
    end
    
    subgraph "Failure Recovery"
        P --> R[Automatic Retry]
        R --> S{Retry Count < 3?}
        S -->|Yes| T[Exponential Backoff]
        S -->|No| U[CRITICAL: Transaction Failed]
        
        T --> V[Retry Transaction]
        V --> K
        
        U --> W[Business Impact: Data Loss Risk]
    end
    
    subgraph "Session Cleanup"
        X[Transaction Complete] --> Y[Commit/Rollback]
        Y --> Z[Return to Pool]
        Z --> AA[Session Available]
    end
    
    K -->|No| X
    L -->|No| X
    M -->|No| X
    
    style P fill:#ff6b6b
    style U fill:#ff6b6b
    style W fill:#ff9f43
    
    note1[CRITICAL: Session isolation<br/>prevents data contamination]
    note2[Business Impact: User data<br/>integrity = legal compliance]
```

### 6.2 Database Connection Failure & Recovery

**High Availability Database Operations**

```mermaid
sequenceDiagram
    participant App as Application
    participant Pool as Connection Pool
    participant DB as Database
    participant Monitor as Health Monitor
    participant Alert as Alert System
    
    App->>Pool: Request Connection
    Pool->>DB: Establish Connection
    
    alt Connection Successful
        DB-->>Pool: Connection Ready
        Pool-->>App: Connection Object
        
        App->>DB: Execute Query
        alt Query Success
            DB-->>App: Query Result
        else Query Failure
            DB-->>App: Query Error
            App->>Pool: Return Failed Connection
            Pool->>Pool: Mark Connection Invalid
        end
    else Connection Failed
        DB-->>Pool: Connection Error
        Pool-->>App: Connection Failed
        
        Pool->>Monitor: Report Connection Failure
        Monitor->>Alert: DATABASE CONNECTION CRITICAL
        
        Pool->>Pool: Retry Connection
        loop Retry up to 3 times
            Pool->>DB: Retry Connection
            alt Retry Success
                DB-->>Pool: Connection Ready
                Pool-->>App: Connection Object
            else Retry Failed
                DB-->>Pool: Still Failing
            end
        end
        
        alt All Retries Failed
            Pool->>Alert: DATABASE DOWN CRITICAL
            Pool-->>App: Service Unavailable
            Note right of Alert: Business Impact:<br/>$500K+ ARR at risk
        end
    end
    
    Note over App,Alert: Health Check Every 30s
    Monitor->>DB: Health Check
    alt Database Healthy
        DB-->>Monitor: Health OK
    else Database Unhealthy
        DB-->>Monitor: Health Failed
        Monitor->>Alert: DATABASE HEALTH CRITICAL
        Monitor->>Pool: Drain Connections
        Pool->>DB: Graceful Shutdown
    end
```

---

## Service Startup & Configuration

### 7.1 Service Startup Dependency Chain

**Critical Service Initialization Order & Dependencies**

```mermaid
flowchart TD
    A[System Boot] --> B[Environment Config Load]
    
    B --> C{All Config Present?}
    C -->|No| D[CRITICAL: Missing Config Values]
    C -->|Yes| E[Database Initialization]
    
    D --> F[Business Impact: Service Down]
    
    E --> G{Database Connected?}
    G -->|No| H[CRITICAL: Database Unreachable]
    G -->|Yes| I[Auth Service Start]
    
    H --> J[Retry Database Connection]
    J --> K{Retry Success?}
    K -->|No| L[CRITICAL: Database Failure]
    K -->|Yes| I
    
    I --> M{Auth Service Healthy?}
    M -->|No| N[CRITICAL: Auth Service Failed]
    M -->|Yes| O[Backend Service Start]
    
    O --> P{Backend Service Healthy?}
    P -->|No| Q[CRITICAL: Backend Service Failed]
    P -->|Yes| R[Frontend Service Start]
    
    R --> S{Frontend Service Healthy?}
    S -->|No| T[CRITICAL: Frontend Service Failed]
    S -->|Yes| U[All Services Ready]
    
    U --> V[Health Check Monitoring]
    V --> W{All Services Responding?}
    W -->|No| X[Service Recovery Sequence]
    W -->|Yes| Y[System Operational]
    
    X --> Z[Identify Failed Service]
    Z --> AA[Restart Failed Service]
    AA --> BB{Restart Success?}
    BB -->|No| CC[ESCALATION: Manual Intervention]
    BB -->|Yes| V
    
    L --> DD[Business Impact: Complete System Down]
    N --> DD
    Q --> DD
    T --> DD
    CC --> DD
    
    style D fill:#ff6b6b
    style H fill:#ff6b6b
    style L fill:#ff6b6b
    style N fill:#ff6b6b
    style Q fill:#ff6b6b
    style T fill:#ff6b6b
    style CC fill:#ff6b6b
    style DD fill:#ff9f43
    style F fill:#ff9f43
```

### 7.2 Configuration Loading & Validation

**Critical Environment Configuration Management**

```mermaid
stateDiagram-v2
    [*] --> LoadEnvironment: Service Start
    
    state LoadEnvironment {
        [*] --> CheckEnvFile
        CheckEnvFile --> ValidateRequired
        ValidateRequired --> ValidateFormats
        ValidateFormats --> [*]
    }
    
    LoadEnvironment --> ConfigValid: All Valid
    LoadEnvironment --> ConfigError: Validation Failed
    
    state ConfigError {
        [*] --> choice_error
        choice_error --> MissingValues: Required Missing
        choice_error --> InvalidFormat: Format Error
        choice_error --> SecretError: Secret Access Failed
        
        MissingValues --> LogCriticalError
        InvalidFormat --> LogCriticalError
        SecretError --> LogCriticalError
        
        LogCriticalError --> [*]
    }
    
    ConfigValid --> ServiceInitialization
    
    state ServiceInitialization {
        [*] --> DatabaseConfig
        DatabaseConfig --> AuthConfig
        AuthConfig --> WebSocketConfig
        WebSocketConfig --> LLMConfig
        LLMConfig --> [*]
    }
    
    ServiceInitialization --> ServiceReady: Success
    ServiceInitialization --> InitializationFailed: Error
    
    state InitializationFailed {
        [*] --> RetryInitialization
        RetryInitialization --> choice_retry
        choice_retry --> RetryWithDefaults: Use Defaults
        choice_retry --> RetryWithSecrets: Reload Secrets
        choice_retry --> FailureEscalation: Max Retries
        
        RetryWithDefaults --> [*]
        RetryWithSecrets --> [*]
        FailureEscalation --> [*]
    }
    
    ConfigError --> ServiceDown: Critical Error
    InitializationFailed --> ServiceReady: Retry Success
    InitializationFailed --> ServiceDown: Retry Failed
    
    ServiceReady --> [*]
    ServiceDown --> [*]
    
    note right of ConfigError : Business Impact:<br/>Service cannot start<br/>affects all users
    note right of ServiceDown : CRITICAL: Manual<br/>intervention required
```

---

## Cascade Failure Prevention

### 8.1 System-Wide Cascade Failure Prevention

**Circuit Breakers & Isolation to Prevent Total System Failure**

```mermaid
graph TB
    subgraph "Service Layer Protection"
        A[Auth Service] --> B[Circuit Breaker A]
        C[Backend Service] --> D[Circuit Breaker B]
        E[Database] --> F[Circuit Breaker C]
        G[WebSocket] --> H[Circuit Breaker D]
    end
    
    subgraph "Circuit Breaker States"
        B --> I{Failure Rate > 50%?}
        D --> J{Failure Rate > 50%?}
        F --> K{Failure Rate > 50%?}
        H --> L{Failure Rate > 50%?}
        
        I -->|Yes| M[Open - Block Requests]
        J -->|Yes| N[Open - Block Requests]
        K -->|Yes| O[Open - Block Requests]
        L -->|Yes| P[Open - Block Requests]
        
        I -->|No| Q[Closed - Allow Requests]
        J -->|No| R[Closed - Allow Requests]
        K -->|No| S[Closed - Allow Requests]
        L -->|No| T[Closed - Allow Requests]
    end
    
    subgraph "Cascade Prevention"
        M --> U[Isolate Auth Failures]
        N --> V[Isolate Backend Failures]
        O --> W[Isolate Database Failures]
        P --> X[Isolate WebSocket Failures]
        
        U --> Y[Continue with Degraded Auth]
        V --> Z[Continue with Cache]
        W --> AA[Continue with Read Replicas]
        X --> BB[Continue with Polling]
    end
    
    subgraph "Recovery Monitoring"
        CC[Health Monitor] --> DD{Service Recovering?}
        DD -->|Yes| EE[Half-Open Circuit]
        DD -->|No| FF[Keep Circuit Open]
        
        EE --> GG{Test Request Success?}
        GG -->|Yes| Q
        GG -->|No| M
    end
    
    Y --> HH[Degraded Service Available]
    Z --> HH
    AA --> HH
    BB --> HH
    
    HH --> II[Business Continuity Maintained]
    
    style II fill:#74b9ff
    note1[CRITICAL: Prevent single<br/>failure from bringing<br/>down entire system]
```

### 8.2 Resource Exhaustion Prevention

**Memory, CPU, and Connection Limit Enforcement**

```mermaid
flowchart TD
    A[System Monitor] --> B{Memory > 80%?}
    B -->|Yes| C[Memory Alert]
    B -->|No| D{CPU > 80%?}
    
    C --> E[Identify Memory Hog]
    E --> F{Critical Process?}
    F -->|Yes| G[Scale Down Non-Critical]
    F -->|No| H[Kill Process]
    
    D -->|Yes| I[CPU Alert]
    D -->|No| J{Connections > 1000?}
    
    I --> K[Throttle Requests]
    K --> L[Enable Request Queue]
    
    J -->|Yes| M[Connection Limit Alert]
    J -->|No| N[System Healthy]
    
    M --> O[Close Idle Connections]
    O --> P[Reject New Connections]
    
    G --> Q[Monitor Recovery]
    H --> Q
    L --> Q
    P --> Q
    
    Q --> R{Resources Recovered?}
    R -->|No| S[ESCALATION: Critical Resource Exhaustion]
    R -->|Yes| T[Resume Normal Operations]
    
    S --> U[Business Impact: System Unavailable]
    
    T --> A
    
    style S fill:#ff6b6b
    style U fill:#ff9f43
    
    note1[PREVENTION: Resource limits<br/>prevent system crashes<br/>that affect $500K+ ARR]
```

---

## Summary & Business Impact

### Critical Test Categories & Business Value Protection

| Test Category | Business Value Protected | Critical Failure Points | Recovery Time |
|---------------|-------------------------|-------------------------|---------------|
| **WebSocket Agent Events** | $500K+ ARR - Core chat functionality | Event emission failures, WebSocket disconnection | < 30 seconds |
| **Agent Execution Order** | $30K+ MRR - High-value workflows | Wrong execution dependencies, agent crashes | < 2 minutes |
| **Docker Infrastructure** | $500K+ ARR - Platform availability | Container failures, resource exhaustion | < 1 minute |
| **SSOT Compliance** | Platform integrity - Legal compliance | Data contamination, shared state | Immediate |
| **Authentication & OAuth** | $75K+ MRR - User access | Config missing, JWT sync failures | < 30 seconds |
| **Database Transactions** | Data integrity - Regulatory compliance | Deadlocks, connection failures | < 1 minute |
| **Service Startup** | Complete system availability | Missing config, dependency failures | < 5 minutes |
| **Cascade Prevention** | Total system protection | Single point failures spreading | Immediate |

### Key Recovery Principles

1. **Fail Fast, Recover Faster**: Detect failures in < 30 seconds, recover in < 2 minutes
2. **Isolate Failures**: Prevent cascade effects that could bring down the entire system  
3. **Preserve Business Value**: Maintain core chat functionality even during degraded states
4. **Monitor Everything**: Comprehensive health checks every 30 seconds
5. **Auto-Recovery**: Minimize manual intervention through automated recovery sequences

**CRITICAL SUCCESS METRICS:**
- 99.99% system uptime
- < 100ms WebSocket event latency  
- Zero cross-user data contamination
- 100% authentication success rate (when configured correctly)
- < 30 second failure detection and recovery initiation

All diagrams reflect real production failure patterns and recovery mechanisms validated through comprehensive mission-critical test suites.
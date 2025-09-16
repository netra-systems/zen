# Database Architecture End-to-End Diagrams

This document contains comprehensive end-to-end diagrams for each service's database configuration and operational cycle, including all files, configurations, success and error states, and networking assumptions.

## 1. Main Backend Service Database Cycle

### 1.1 Configuration Loading and Initialization Flow

```mermaid
flowchart TD
    %% Configuration Sources
    A[Environment Variables] --> B[IsolatedEnvironment]
    A --> C[DatabaseURLBuilder]
    
    %% Configuration Management SSOT
    B --> D[UnifiedConfigManager]
    C --> D
    D --> E[AppConfig Schema]
    
    %% Configuration Access Points
    F[netra_backend/app/config.py] --> D
    G[netra_backend/app/core/configuration/database.py] --> D
    H[netra_backend/app/core/configuration/base.py] --> D
    
    %% Database Manager Initialization
    E --> I[DatabaseManager.__init__]
    I --> J[_get_database_url]
    J --> K[DatabaseURLBuilder.get_url_for_environment]
    K --> L[DatabaseURLBuilder.format_url_for_driver]
    
    %% Engine Creation
    L --> M[create_async_engine]
    M --> N[Pool Configuration]
    N --> O[Connection Testing]
    
    %% Success/Error States
    O --> P{Connection Test}
    P -->|Success| Q[Engine Ready]
    P -->|Failure| R[Retry Logic]
    R --> S{Max Retries?}
    S -->|No| O
    S -->|Yes| T[Critical Failure]
    
    %% Runtime Operations
    Q --> U[Session Management]
    
    style A fill:#e1f5fe
    style D fill:#c8e6c9
    style T fill:#ffcdd2
    style Q fill:#c8e6c9
```

### 1.2 Database Session Lifecycle Flow

```mermaid
sequenceDiagram
    participant App as Application Code
    participant DM as DatabaseManager
    participant Engine as AsyncEngine
    participant Pool as Connection Pool
    participant DB as PostgreSQL Database
    participant CB as Circuit Breaker
    participant Monitor as Health Monitor
    
    Note over App,Monitor: Session Request Flow
    
    App->>DM: get_session(operation_type, user_context)
    DM->>DM: Check initialization status
    
    alt Not Initialized
        DM->>DM: await initialize()
        DM->>Engine: create_async_engine()
        DM->>DB: Test connection with retry
        DB-->>DM: Connection confirmed
    end
    
    DM->>DM: Track session metadata
    DM->>Pool: Request connection
    
    alt Pool Available
        Pool-->>DM: Connection acquired
        DM->>App: yield session
        
        App->>DB: Execute operations
        DB-->>App: Results
        
        App->>DM: Transaction complete
        DM->>DB: COMMIT
        DB-->>DM: Success
        
        DM->>CB: Record success
        DM->>Monitor: Update metrics
        
    else Pool Exhausted
        Pool-->>DM: Pool exhaustion warning
        DM->>Monitor: Log pool warning
        DM->>App: Wait or error
    end
    
    Note over DM,Monitor: Cleanup Phase
    DM->>Pool: Release connection
    DM->>DM: Update session stats
    DM->>Monitor: Session lifecycle complete
```

### 1.3 Error Handling and Recovery Flow

```mermaid
flowchart TD
    A[Database Operation] --> B{Operation Result}
    
    B -->|Success| C[Commit Transaction]
    C --> D[Update Metrics]
    D --> E[Session Cleanup]
    
    B -->|Error| F[Classify Error]
    F --> G{Error Type}
    
    G -->|DeadlockError| H[Log Critical - Data Integrity Risk]
    G -->|ConnectionError| I[Log Critical - Infrastructure Issue]
    G -->|TimeoutError| J[Log Warning - Performance Issue]
    G -->|PermissionError| K[Log Error - Security Issue]
    G -->|SchemaError| L[Log Error - Schema Mismatch]
    G -->|Unknown| M[Log Critical - Unexpected Error]
    
    H --> N[Rollback Transaction]
    I --> N
    J --> N
    K --> N
    L --> N
    M --> N
    
    N --> O{Rollback Success?}
    O -->|Yes| P[Log Rollback Success]
    O -->|No| Q[Log Critical - Database Integrity Risk]
    
    P --> R[Circuit Breaker Update]
    Q --> S[Manual Intervention Required]
    
    R --> T{Retryable Error?}
    T -->|Yes| U[Return Classified Error]
    T -->|No| V[Propagate Fatal Error]
    
    S --> W[System Alert]
    
    style H fill:#ffcdd2
    style I fill:#ffcdd2
    style Q fill:#f44336
    style S fill:#f44336
    style W fill:#f44336
```

### 1.4 Infrastructure Dependencies and Networking

```mermaid
graph TD
    subgraph "Cloud Infrastructure"
        A[Cloud Run Instance] --> B[VPC Connector]
        B --> C[Cloud SQL Private IP]
        B --> D[Redis Instance]
        
        E[Load Balancer] --> A
        F[SSL Certificate] --> E
    end
    
    subgraph "Database Configuration"
        G[Environment Variables] --> H[DatabaseURLBuilder]
        H --> I[Connection String]
        I --> J[SSL Configuration]
        J --> K[Connection Pool]
    end
    
    subgraph "Monitoring & Health"
        L[Health Check Endpoint] --> M[Database Health]
        M --> N[Connection Test]
        N --> O[Pool Statistics]
        
        P[Infrastructure Monitor] --> Q[VPC Capacity]
        Q --> R[Timeout Adjustment]
    end
    
    %% Connections
    A -.->|600s timeout| C
    A -.->|Connection pooling| D
    H -.->|URL construction| I
    K -.->|Pool management| A
    
    style C fill:#4fc3f7
    style D fill:#ef5350
    style B fill:#81c784
```

## 2. Auth Service Database Cycle

### 2.1 Auth Service Configuration and Database Flow

```mermaid
flowchart TD
    %% Configuration Sources
    A[Auth Environment Variables] --> B[AuthEnvironment SSOT]
    A --> C[IsolatedEnvironment]
    
    %% Auth Configuration Management
    B --> D[AuthConfig Wrapper]
    D --> E[auth_service/auth_core/config.py]
    
    %% Database Manager
    E --> F[AuthDatabaseManager]
    F --> G[DatabaseURLBuilder Shared]
    G --> H[get_database_url]
    
    %% Engine Creation for Auth
    H --> I{Fast Test Mode?}
    I -->|Yes| J[SQLite In-Memory]
    I -->|No| K[PostgreSQL Async Engine]
    
    %% Auth Database Operations
    J --> L[Auth Operations]
    K --> L
    L --> M[JWT Storage]
    L --> N[User Management]
    L --> O[Session Management]
    
    %% Service Independence
    P[Backend Service] -.->|Independent| Q[Auth Service]
    Q --> R[Port 8001]
    P --> S[Port 8000]
    
    style B fill:#c8e6c9
    style G fill:#e1f5fe
    style J fill:#fff3e0
    style K fill:#e3f2fd
```

### 2.2 Auth Service Database Session Management

```mermaid
sequenceDiagram
    participant Auth as Auth Service
    participant Config as AuthConfig
    participant Builder as DatabaseURLBuilder
    participant Engine as AsyncEngine
    participant DB as Database
    
    Note over Auth,DB: Auth Service Database Session
    
    Auth->>Config: get_database_url()
    Config->>Builder: DatabaseURLBuilder(env_vars)
    Builder->>Builder: validate()
    
    alt Valid Configuration
        Builder->>Builder: get_url_for_environment(sync=False)
        Builder-->>Config: database_url
        Config-->>Auth: url
        
        Auth->>Engine: create_async_engine(url)
        Engine->>DB: Test connection
        DB-->>Engine: Connection OK
        
        Auth->>DB: Execute auth operations
        DB-->>Auth: Results
        
    else Invalid Configuration
        Builder-->>Config: ValidationError
        Config-->>Auth: ValueError with debug info
        Auth->>Auth: Log error and fail
    end
    
    Note over Auth: Service runs independently on port 8001
```

### 2.3 Auth Service Error Handling

```mermaid
flowchart TD
    A[Auth Operation Request] --> B[AuthDatabaseManager]
    B --> C[get_database_url]
    C --> D{Fast Test Mode?}
    
    D -->|Yes| E[SQLite Configuration]
    D -->|No| F[DatabaseURLBuilder]
    
    E --> G[In-Memory Database]
    F --> H{Configuration Valid?}
    
    H -->|Yes| I[PostgreSQL Connection]
    H -->|No| J[Log Configuration Error]
    
    J --> K[ValueError with Debug Info]
    K --> L[Service Startup Failure]
    
    G --> M[Auth Operations]
    I --> M
    
    M --> N{Operation Success?}
    N -->|Yes| O[Return Results]
    N -->|No| P[Auth Error Handling]
    
    P --> Q[Log Auth Error]
    Q --> R[Return Auth Failure]
    
    style L fill:#ffcdd2
    style K fill:#ffcdd2
    style J fill:#ffcdd2
```

## 3. Frontend Database Integration

### 3.1 Frontend Service Dependencies

```mermaid
flowchart TD
    subgraph "Frontend (Next.js)"
        A[Frontend App] --> B[Auth Context]
        B --> C[API Client]
        C --> D[Backend API Calls]
    end
    
    subgraph "Backend Services"
        E[Auth Service :8001] --> F[Auth Database]
        G[Main Backend :8000] --> H[Main Database]
        G --> I[Redis Cache]
        G --> J[ClickHouse Analytics]
    end
    
    subgraph "Database Layer"
        F --> K[PostgreSQL Auth Schema]
        H --> L[PostgreSQL Main Schema]
        I --> M[Redis Instance]
        J --> N[ClickHouse Instance]
    end
    
    %% Frontend connections
    D --> E
    D --> G
    
    %% No direct database connections from frontend
    A -.->|No Direct Connection| K
    A -.->|No Direct Connection| L
    
    style A fill:#81c784
    style K fill:#4fc3f7
    style L fill:#4fc3f7
    style M fill:#ef5350
    style N fill:#ff9800
```

### 3.2 Frontend API Integration Flow

```mermaid
sequenceDiagram
    participant UI as Frontend UI
    participant Auth as Auth Context
    participant API as API Client
    participant Backend as Backend Service
    participant AuthSvc as Auth Service
    participant DB as Database Layer
    
    Note over UI,DB: User Authentication Flow
    
    UI->>Auth: User login request
    Auth->>API: POST /auth/login
    API->>AuthSvc: Forward auth request
    AuthSvc->>DB: Validate credentials
    DB-->>AuthSvc: User data
    AuthSvc-->>API: JWT tokens
    API-->>Auth: Auth response
    Auth-->>UI: Update auth state
    
    Note over UI,DB: Data Operations Flow
    
    UI->>API: Data request with JWT
    API->>Backend: API call with auth header
    Backend->>Backend: Validate JWT with auth service
    Backend->>DB: Execute database operations
    DB-->>Backend: Query results
    Backend-->>API: API response
    API-->>UI: Update UI state
    
    Note over UI: Frontend never connects directly to databases
```

## 4. Networking Assumptions and Dependencies

### 4.1 Network Architecture Overview

```mermaid
graph TD
    subgraph "Internet"
        A[User Browser] --> B[Load Balancer]
    end
    
    subgraph "Cloud Run Services"
        B --> C[Frontend :3000]
        B --> D[Backend :8000]
        B --> E[Auth Service :8001]
    end
    
    subgraph "VPC Network"
        F[VPC Connector] --> G[Cloud SQL Private IP]
        F --> H[Redis Private IP]
        F --> I[ClickHouse Private IP]
    end
    
    subgraph "External Services"
        J[Google OAuth]
        K[External APIs]
    end
    
    %% Service connections
    C -.->|API Calls| D
    C -.->|Auth Calls| E
    D --> F
    E --> F
    
    %% External connections
    E -.->|OAuth| J
    D -.->|External| K
    
    %% Database connections
    G --> L[(PostgreSQL)]
    H --> M[(Redis)]
    I --> N[(ClickHouse)]
    
    style F fill:#81c784
    style L fill:#4fc3f7
    style M fill:#ef5350
    style N fill:#ff9800
```

### 4.2 Timeout and Retry Configuration

```mermaid
flowchart TD
    subgraph "Infrastructure Timeouts"
        A[Cloud Run Timeout: 600s] --> B[VPC Connector Capacity]
        B --> C[Database Connection Pool]
        C --> D[Individual Query Timeout: 30s]
    end
    
    subgraph "Connection Retry Logic"
        E[Initial Connection Attempt] --> F{Success?}
        F -->|No| G[Exponential Backoff]
        G --> H[Retry with Infrastructure Delay]
        H --> I{Max Retries?}
        I -->|No| E
        I -->|Yes| J[Connection Failure]
        F -->|Yes| K[Connection Established]
    end
    
    subgraph "Environment-Specific Settings"
        L[Local Development] --> M[5s timeout, 3 retries]
        N[Staging/Production] --> O[10s timeout, 5 retries]
        O --> P[Infrastructure-aware delays]
    end
    
    style J fill:#ffcdd2
    style K fill:#c8e6c9
```

## 5. Success and Error States Mapping

### 5.1 Complete Success Flow

```mermaid
stateDiagram-v2
    [*] --> ConfigLoad : Service Start
    ConfigLoad --> URLBuild : Environment Loaded
    URLBuild --> EngineCreate : URL Constructed
    EngineCreate --> ConnectionTest : Engine Created
    ConnectionTest --> PoolReady : Connection Verified
    PoolReady --> SessionReady : Pool Configured
    SessionReady --> OperationExec : Session Available
    OperationExec --> TransactionCommit : Operation Complete
    TransactionCommit --> CleanupSession : Transaction Success
    CleanupSession --> MetricsUpdate : Session Closed
    MetricsUpdate --> [*] : Success Complete
    
    note right of ConfigLoad : ✅ All env vars loaded
    note right of URLBuild : ✅ DatabaseURLBuilder success
    note right of EngineCreate : ✅ SQLAlchemy engine ready
    note right of ConnectionTest : ✅ Database ping successful
    note right of PoolReady : ✅ Connection pool active
    note right of SessionReady : ✅ Session context ready
    note right of OperationExec : ✅ Query executed
    note right of TransactionCommit : ✅ Data persisted
    note right of CleanupSession : ✅ Resources released
    note right of MetricsUpdate : ✅ Monitoring updated
```

### 5.2 Error States and Recovery

```mermaid
stateDiagram-v2
    [*] --> ConfigError : Missing Env Vars
    [*] --> URLError : Invalid URL Construction
    [*] --> EngineError : Engine Creation Failed
    [*] --> ConnectionError : Database Unreachable
    [*] --> PoolError : Pool Exhaustion
    [*] --> SessionError : Session Failed
    [*] --> TransactionError : Transaction Failed
    [*] --> TimeoutError : Operation Timeout
    
    ConfigError --> ConfigRetry : Reload Config
    ConfigRetry --> [*] : Success
    ConfigRetry --> FatalConfig : Permanent Failure
    
    URLError --> URLRetry : Rebuild URL
    URLRetry --> [*] : Success
    URLRetry --> FatalURL : Invalid Config
    
    ConnectionError --> ConnectionRetry : Backoff + Retry
    ConnectionRetry --> [*] : Success
    ConnectionRetry --> FatalConnection : Max Retries
    
    PoolError --> PoolWait : Wait for Available
    PoolWait --> [*] : Pool Available
    PoolWait --> FatalPool : Timeout
    
    SessionError --> SessionRollback : Rollback Transaction
    SessionRollback --> [*] : Recovery Success
    SessionRollback --> FatalSession : Rollback Failed
    
    TransactionError --> TransactionRetry : Retry if Safe
    TransactionRetry --> [*] : Success
    TransactionRetry --> FatalTransaction : Non-retryable
    
    TimeoutError --> TimeoutRetry : Increase Timeout
    TimeoutRetry --> [*] : Success
    TimeoutRetry --> FatalTimeout : Infrastructure Issue
    
    FatalConfig --> ManualIntervention : ❌ Config Issue
    FatalURL --> ManualIntervention : ❌ URL Issue
    FatalConnection --> ManualIntervention : ❌ Network Issue
    FatalPool --> ManualIntervention : ❌ Resource Issue
    FatalSession --> ManualIntervention : ❌ Data Integrity Risk
    FatalTransaction --> ManualIntervention : ❌ Business Logic Error
    FatalTimeout --> ManualIntervention : ❌ Infrastructure Problem
```

## 6. Cross-Service Integration Points

### 6.1 Service Communication Matrix

| Source Service | Target Service | Communication Type | Database Impact |
|----------------|----------------|-------------------|-----------------|
| Frontend | Backend | HTTP API + WebSocket | Triggers DB operations |
| Frontend | Auth Service | HTTP API (Auth) | JWT validation |
| Backend | Auth Service | HTTP API (Validation) | Session lookup |
| Backend | Database | SQL Connection Pool | Direct operations |
| Auth Service | Database | SQL Connection Pool | Auth operations |

### 6.2 Configuration Cross-References

```mermaid
graph LR
    subgraph "Shared Configuration"
        A[DatabaseURLBuilder] --> B[Backend DB Config]
        A --> C[Auth DB Config]
        
        D[IsolatedEnvironment] --> E[Backend Config]
        D --> F[Auth Config]
        D --> G[Frontend Env]
    end
    
    subgraph "Service-Specific Config"
        B --> H[netra_backend/app/config.py]
        C --> I[auth_service/auth_core/config.py]
        G --> J[frontend/.env.local]
    end
    
    subgraph "Database Instances"
        H --> K[(PostgreSQL Main)]
        I --> L[(PostgreSQL Auth)]
        H --> M[(Redis)]
        H --> N[(ClickHouse)]
    end
    
    style A fill:#c8e6c9
    style D fill:#c8e6c9
```

## Summary

This comprehensive database architecture documentation shows:

1. **Configuration Flow**: From environment variables through SSOT systems to runtime configuration
2. **Connection Management**: Pool configuration, retry logic, and timeout handling
3. **Error Handling**: Complete error classification and recovery procedures
4. **Service Independence**: Each service manages its own database connections
5. **Infrastructure Dependencies**: VPC connectors, SSL, and Cloud Run requirements
6. **Monitoring Integration**: Health checks, metrics, and alerting

Each service follows the established patterns while maintaining independence and reliability through the shared SSOT components like `DatabaseURLBuilder` and `IsolatedEnvironment`.
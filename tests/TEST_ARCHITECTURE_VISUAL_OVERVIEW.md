# Complete Visual Test Architecture Overview

## Related Documentation

- **[Test Creation Guide](../TEST_CREATION_GUIDE.md)** - AUTHORITATIVE guide for creating tests with SSOT patterns
- **[User Context Architecture](../USER_CONTEXT_ARCHITECTURE.md)** - Factory patterns and user isolation
- **[Agent Architecture Disambiguation Guide](../docs/AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md)** - Agent component relationships
- **[Docker Orchestration](../docs/docker_orchestration.md)** - Docker management and Alpine containers
- **[Documentation Hub](../docs/index.md)** - Central documentation index

## 1. Test Layer Hierarchy

```mermaid
graph TB
    subgraph "Test Execution Layers"
        L1[Fast Feedback Layer<br/>2 min]
        L2[Core Integration Layer<br/>10 min]
        L3[Service Integration Layer<br/>20 min]
        L4[E2E Background Layer<br/>60 min]
    end
    
    L1 --> L2
    L2 --> L3
    L3 --> L4
    
    style L1 fill:#90EE90
    style L2 fill:#FFD700
    style L3 fill:#FFA500
    style L4 fill:#FF6347
```

## 2. Test Categories & Infrastructure Requirements

```mermaid
graph LR
    subgraph "No Infrastructure Required"
        U[Unit Tests]
        SM[Smoke Tests]
        SEC[Security Tests]
    end
    
    subgraph "Local Services Only"
        DB[Database Tests]
        API[API Tests]
        WS[WebSocket Tests]
    end
    
    subgraph "Docker Required"
        INT[Integration Tests]
        AG[Agent Tests]
        FE[Frontend Tests]
    end
    
    subgraph "Full Docker + Real LLM"
        E2E[E2E Tests]
        PERF[Performance Tests]
        LOAD[Load Tests]
    end
    
    U --> DB
    DB --> INT
    INT --> E2E
```

## 3. Service Dependencies Map

```mermaid
graph TD
    subgraph "Test Infrastructure"
        subgraph "Core Services"
            PG[PostgreSQL<br/>5434/5432]
            RD[Redis<br/>6381/6379]
            CH[ClickHouse<br/>8123]
        end
        
        subgraph "Application Services"
            AUTH[Auth Service<br/>8081]
            BACK[Backend<br/>8000]
            FRONT[Frontend<br/>3000]
            ANLY[Analytics<br/>8002]
        end
        
        subgraph "External Services"
            LLM[Real LLM API]
            OAUTH[OAuth Providers]
        end
    end
    
    BACK --> PG
    BACK --> RD
    AUTH --> PG
    AUTH --> RD
    ANLY --> CH
    FRONT --> BACK
    FRONT --> AUTH
    BACK --> LLM
    AUTH --> OAUTH
```

## 4. Mock vs Real Service Usage

```mermaid
graph TB
    subgraph "Unit Tests - All Mocked"
        UM[Unit/Models]
        UC[Unit/Config]
        UU[Unit/Utils]
        
        UM -.->|Mock| MDB[(Mock DB)]
        UC -.->|Mock| MENV[Mock Env]
        UU -.->|Mock| MEXT[Mock External]
    end
    
    subgraph "Integration Tests - Mixed"
        IDB[DB Integration]
        IAPI[API Integration]
        IWS[WebSocket Integration]
        
        IDB -->|Real| RDB[(Real DB)]
        IAPI -->|Real| RAPI[Real API]
        IAPI -.->|Mock| MLLM[Mock LLM]
        IWS -->|Real| RWS[Real WebSocket]
    end
    
    subgraph "E2E Tests - All Real"
        E2EF[Full E2E]
        E2EA[Agent E2E]
        E2EP[Performance E2E]
        
        E2EF -->|Real| RALL[All Real Services]
        E2EA -->|Real| RLLM[Real LLM]
        E2EP -->|Real| RPERF[Real Metrics]
    end
    
    style MDB stroke-dasharray: 5 5
    style MENV stroke-dasharray: 5 5
    style MEXT stroke-dasharray: 5 5
    style MLLM stroke-dasharray: 5 5
```

## 5. Test Directory Structure

```mermaid
graph TD
    ROOT[tests/]
    
    ROOT --> UNIT[unit/<br/>No dependencies]
    ROOT --> INT[integration/<br/>Service dependencies]
    ROOT --> E2E_DIR[e2e/<br/>Full stack]
    ROOT --> MC[mission_critical/<br/>Business critical]
    ROOT --> PERF_DIR[performance/<br/>Load & stress]
    
    UNIT --> U_MODELS[models/]
    UNIT --> U_UTILS[utils/]
    UNIT --> U_CONFIG[config/]
    
    INT --> I_DB[database/]
    INT --> I_API[api/]
    INT --> I_WS[websocket/]
    INT --> I_AUTH[auth/]
    
    E2E_DIR --> E_FLOWS[user_flows/]
    E2E_DIR --> E_AGENT[agent_flows/]
    E2E_DIR --> E_REAL[real_llm/]
    
    MC --> MC_WS[websocket_events/]
    MC --> MC_AUTH[auth_consistency/]
    MC --> MC_DOCKER[docker_lifecycle/]
```

## 6. Docker Container Requirements

```mermaid
graph LR
    subgraph "Test Environment Containers"
        subgraph "Always Required"
            TPG[PostgreSQL Test<br/>:5434]
            TRD[Redis Test<br/>:6381]
        end
        
        subgraph "Integration Tests"
            TAUTH[Auth Service<br/>:8081]
            TBACK[Backend<br/>:8000]
        end
        
        subgraph "E2E Tests"
            TFRONT[Frontend<br/>:3000]
            TANLY[Analytics<br/>:8002]
            TCH[ClickHouse<br/>:8123]
        end
    end
    
    subgraph "Alpine Optimized"
        ALPINE[Alpine Containers<br/>50% faster<br/>tmpfs storage]
    end
    
    ALPINE -.->|Optional| TPG
    ALPINE -.->|Optional| TAUTH
    ALPINE -.->|Optional| TBACK
```

## 7. Test Execution Flow

```mermaid
sequenceDiagram
    participant DEV as Developer
    participant TR as Test Runner
    participant DM as Docker Manager
    participant TS as Test Suite
    participant RS as Real Services
    
    DEV->>TR: python unified_test_runner.py --real-services
    TR->>DM: Check Docker status
    DM->>DM: Resolve conflicts
    DM->>RS: Start containers
    RS-->>DM: Health check passed
    DM-->>TR: Services ready
    TR->>TS: Execute tests
    TS->>RS: Connect to services
    RS-->>TS: Real responses
    TS-->>TR: Results
    TR-->>DEV: Test report
```

## 8. Mission Critical Test Coverage

```mermaid
graph TB
    subgraph "Mission Critical Tests"
        subgraph "WebSocket Events"
            WSE1[agent_started]
            WSE2[agent_thinking]
            WSE3[tool_executing]
            WSE4[tool_completed]
            WSE5[agent_completed]
        end
        
        subgraph "Auth Consistency"
            AC1[JWT Secret Sync]
            AC2[Session Persistence]
            AC3[Token Refresh]
            AC4[OAuth Flow]
        end
        
        subgraph "Docker Lifecycle"
            DL1[Container Health]
            DL2[Service Dependencies]
            DL3[Conflict Resolution]
            DL4[Resource Limits]
        end
    end
    
    WSE1 --> WSE2
    WSE2 --> WSE3
    WSE3 --> WSE4
    WSE4 --> WSE5
    
    style WSE1 fill:#FF6B6B
    style WSE5 fill:#FF6B6B
    style AC1 fill:#FF6B6B
    style DL1 fill:#FF6B6B
```

## 9. Test Infrastructure vs Business Logic

```mermaid
graph TD
    subgraph "Infrastructure Tests"
        subgraph "Platform"
            DOCKER[Docker Management]
            ENV[Environment Config]
            PROC[Process Cleanup]
        end
        
        subgraph "Services"
            SVCHEALTH[Service Health]
            SVCCONN[Service Connectivity]
            SVCCONF[Service Config]
        end
        
        subgraph "Database"
            DBCONN[DB Connection]
            DBMIG[DB Migration]
            DBTX[DB Transactions]
        end
    end
    
    subgraph "Business Logic Tests"
        subgraph "Core Features"
            AGENT[Agent Execution]
            CHAT[Chat System]
            AUTH_BIZ[Authentication]
        end
        
        subgraph "User Flows"
            SIGNUP[User Signup]
            CONV[Conversation Flow]
            TOOL[Tool Usage]
        end
        
        subgraph "Value Delivery"
            RESP[Response Quality]
            PERF_BIZ[Performance SLAs]
            UX[User Experience]
        end
    end
    
    DOCKER -.->|Enables| AGENT
    SVCHEALTH -.->|Enables| CHAT
    DBCONN -.->|Enables| AUTH_BIZ
```

## 10. Real Service Requirements Matrix

```mermaid
graph LR
    subgraph "Test Categories"
        T1[Unit]
        T2[Integration]
        T3[E2E]
        T4[Mission Critical]
    end
    
    subgraph "Service Requirements"
        subgraph "None"
            NONE[Pure Python]
        end
        
        subgraph "Local"
            LOCAL[DB + Redis]
        end
        
        subgraph "Docker"
            DOCK[All Services]
        end
        
        subgraph "External"
            EXT[LLM + OAuth]
        end
    end
    
    T1 --> NONE
    T2 --> LOCAL
    T2 -.->|Optional| DOCK
    T3 --> DOCK
    T3 --> EXT
    T4 --> DOCK
    T4 -.->|Optional| EXT
    
    style T1 fill:#90EE90
    style T2 fill:#FFD700
    style T3 fill:#FFA500
    style T4 fill:#FF6347
```

## 11. Test Isolation Patterns

```mermaid
graph TB
    subgraph "User Context Isolation"
        UCI[User Context Factory]
        UE1[User 1 Executor]
        UE2[User 2 Executor]
        UE3[User 3 Executor]
        
        UCI --> UE1
        UCI --> UE2
        UCI --> UE3
    end
    
    subgraph "Request Scoped Resources"
        RS1[Request 1<br/>DB Session]
        RS2[Request 2<br/>DB Session]
        RS3[Request 3<br/>DB Session]
        
        UE1 --> RS1
        UE2 --> RS2
        UE3 --> RS3
    end
    
    subgraph "Shared Infrastructure"
        DB[(PostgreSQL)]
        CACHE[(Redis)]
        
        RS1 --> DB
        RS2 --> DB
        RS3 --> DB
        RS1 --> CACHE
        RS2 --> CACHE
        RS3 --> CACHE
    end
```

## 12. Performance Test Infrastructure

```mermaid
graph TD
    subgraph "Performance Testing Stack"
        subgraph "Load Generation"
            LOCUST[Locust]
            K6[K6]
            CUSTOM[Custom Scripts]
        end
        
        subgraph "Monitoring"
            PROM[Prometheus]
            GRAF[Grafana]
            OTEL[OpenTelemetry]
        end
        
        subgraph "Targets"
            API_PERF[API Endpoints]
            WS_PERF[WebSocket]
            DB_PERF[Database]
        end
        
        subgraph "Metrics"
            LAT[Latency P50/P95/P99]
            THRU[Throughput]
            ERR[Error Rate]
            RES[Resource Usage]
        end
    end
    
    LOCUST --> API_PERF
    K6 --> WS_PERF
    CUSTOM --> DB_PERF
    
    API_PERF --> PROM
    WS_PERF --> PROM
    DB_PERF --> PROM
    
    PROM --> GRAF
    OTEL --> GRAF
    
    GRAF --> LAT
    GRAF --> THRU
    GRAF --> ERR
    GRAF --> RES
```

## 13. CI/CD Test Pipeline

```mermaid
graph LR
    subgraph "GitHub Actions Pipeline"
        subgraph "PR Tests"
            PR1[Lint & Format]
            PR2[Unit Tests]
            PR3[Fast Integration]
        end
        
        subgraph "Merge Tests"
            M1[Full Integration]
            M2[E2E Critical]
            M3[Security Scan]
        end
        
        subgraph "Nightly Tests"
            N1[Full E2E]
            N2[Performance]
            N3[Load Tests]
            N4[Chaos Tests]
        end
    end
    
    PR1 --> PR2
    PR2 --> PR3
    PR3 --> M1
    M1 --> M2
    M2 --> M3
    M3 --> N1
    N1 --> N2
    N2 --> N3
    N3 --> N4
    
    style PR1 fill:#90EE90
    style PR2 fill:#90EE90
    style M1 fill:#FFD700
    style N1 fill:#FFA500
```

## Test Execution Summary

### Quick Reference

| Test Type | Infrastructure | Docker | Real LLM | Mocks | Execution Time |
|-----------|---------------|--------|----------|-------|----------------|
| Unit | None | ❌ | ❌ | ✅ All | < 1 min |
| Smoke | None | ❌ | ❌ | ✅ Most | < 2 min |
| Integration | Local DB/Redis | Optional | ❌ | ✅ External only | 5-10 min |
| API | Local Services | ✅ | ❌ | ✅ LLM only | 5-10 min |
| WebSocket | Local Services | ✅ | ❌ | ✅ Some | 5-10 min |
| E2E | Full Stack | ✅ | ✅ | ❌ None | 20-60 min |
| Performance | Full Stack | ✅ | Optional | ❌ None | 30-120 min |
| Mission Critical | Full Stack | ✅ | Optional | ❌ None | 10-30 min |

### Docker Service Requirements

| Service | Test Port | Dev Port | Required For |
|---------|-----------|----------|--------------|
| PostgreSQL | 5434 | 5432 | Integration, E2E, Mission Critical |
| Redis | 6381 | 6379 | Integration, E2E, Mission Critical |
| Backend | 8000 | 8000 | API, E2E, Mission Critical |
| Auth | 8081 | 8081 | Auth tests, E2E |
| Frontend | 3000 | 3000 | E2E only |
| ClickHouse | 8123 | 8123 | Analytics tests |
| Analytics | 8002 | 8002 | Analytics E2E |

### Key Testing Principles

1. **NO MOCKS in Production-Like Tests**: E2E, Integration, and Mission Critical tests use real services
2. **Alpine Containers by Default**: 50% faster test execution with Alpine images
3. **Automatic Docker Management**: UnifiedDockerManager handles conflicts and health checks
4. **User Context Isolation**: Factory pattern ensures complete user isolation
5. **WebSocket Events are Critical**: All 5 agent events must be sent for business value

## See Also

- **[CLAUDE.md](../CLAUDE.md)** - Complete development guidelines and testing requirements
- **[Unified Test Runner](./unified_test_runner.py)** - Central test execution script
- **[Mission Critical Tests](./mission_critical/)** - Business-critical test suites
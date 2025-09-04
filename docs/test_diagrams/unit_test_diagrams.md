# Unit Test Architecture Diagrams

This document contains comprehensive Mermaid diagrams for unit tests across the Netra project, organized by component categories and test isolation patterns.

## Overview

Unit tests in Netra focus on testing individual components in isolation with controlled dependencies. They follow strict patterns for mock boundaries, input/output validation, and component scope.

## Table of Contents

1. [Core Utilities Unit Tests](#core-utilities-unit-tests)
2. [Data Models Unit Tests](#data-models-unit-tests)
3. [Business Logic Unit Tests](#business-logic-unit-tests)
4. [Helper Functions Unit Tests](#helper-functions-unit-tests)
5. [Validators Unit Tests](#validators-unit-tests)
6. [Agent Infrastructure Unit Tests](#agent-infrastructure-unit-tests)
7. [Resilience Components Unit Tests](#resilience-components-unit-tests)
8. [Configuration Unit Tests](#configuration-unit-tests)
9. [Database Components Unit Tests](#database-components-unit-tests)
10. [WebSocket Components Unit Tests](#websocket-components-unit-tests)

---

## Core Utilities Unit Tests

### Environment Isolation Testing

```mermaid
flowchart TD
    A[Test Environment Isolation] --> B[Setup Test Fixtures]
    B --> C[Mock External Dependencies]
    C --> D[IsolatedEnvironment Component]
    
    D --> E[Test Basic Access]
    D --> F[Test Overrides]
    D --> G[Test Thread Safety]
    D --> H[Test Source Tracking]
    
    E --> I[Assert Environment Variables]
    F --> I
    G --> I
    H --> I
    
    I --> J[Cleanup Test State]
    
    subgraph "Mock Boundaries"
        K[Mock os.environ]
        L[Mock Configuration Manager]
        M[Mock Subprocess Environment]
    end
    
    subgraph "Test Validations"
        N[Variable Access Assertions]
        O[Override Behavior Validation]
        P[Thread Safety Verification]
        Q[Source Tracking Accuracy]
    end
    
    C --> K
    C --> L
    C --> M
    
    E --> N
    F --> O
    G --> P
    H --> Q
    
    style D fill:#e1f5fe
    style I fill:#c8e6c9
    style C fill:#fff3e0
```

### CORS Configuration Testing

```mermaid
flowchart TD
    A[CORS Configuration Builder Tests] --> B[Test Input Preparation]
    B --> C[Component Under Test]
    C --> D[Environment Detection Tests]
    C --> E[Origins Builder Tests]
    C --> F[Headers Builder Tests]
    C --> G[Security Builder Tests]
    
    D --> H[Assert Environment Detection]
    E --> I[Assert Origins Configuration]
    F --> J[Assert Headers Configuration]
    G --> K[Assert Security Configuration]
    
    H --> L[Validate Output]
    I --> L
    J --> L
    K --> L
    
    subgraph "Test Data"
        M[Environment Variables Mock]
        N[Expected Origins List]
        O[Expected Headers List]
        P[Expected Security Settings]
    end
    
    subgraph "Mock Boundaries"
        Q[No External Network Calls]
        R[No File System Access]
        S[Pure Configuration Logic]
    end
    
    B --> M
    B --> N
    B --> O
    B --> P
    
    style C fill:#e1f5fe
    style L fill:#c8e6c9
    style Q fill:#ffebee
```

### Database URL Builder Testing

```mermaid
flowchart TD
    A[Database URL Builder Tests] --> B[Mock Environment]
    B --> C[DatabaseManager.get_base_database_url]
    
    C --> D[URL Format Conversion Tests]
    C --> E[SSL Parameter Tests]
    C --> F[Cloud SQL Tests]
    C --> G[Search Path Tests]
    
    D --> H[Async to Sync Conversion]
    E --> I[SSL Parameter Handling]
    F --> J[Unix Socket Format]
    G --> K[Schema Path Addition]
    
    H --> L[Assert URL Format]
    I --> L
    J --> L
    K --> L
    
    L --> M[Validate Migration URLs]
    
    subgraph "Test Parameters"
        N["postgresql+asyncpg://..."]
        O["sslmode parameters"]
        P["Cloud SQL paths"]
        Q["search_path options"]
    end
    
    subgraph "Expected Outputs"
        R["postgresql://... (sync)"]
        S["SSL preserved/removed"]
        T["Unix socket format"]
        U["Schema paths added"]
    end
    
    subgraph "Mock Boundaries"
        V[Mock get_env]
        W[Mock Unified Config]
        X[Mock Environment Detection]
    end
    
    B --> V
    B --> W
    B --> X
    
    D --> N
    E --> O
    F --> P
    G --> Q
    
    H --> R
    I --> S
    J --> T
    K --> U
    
    style C fill:#e1f5fe
    style L fill:#c8e6c9
    style V fill:#fff3e0
```

---

## Data Models Unit Tests

### Analytics Service Models

```mermaid
flowchart TD
    A[Analytics Models Unit Tests] --> B[Test Data Preparation]
    B --> C[Pydantic Model Validation]
    
    C --> D[Event Model Tests]
    C --> E[Properties Model Tests]
    C --> F[Enum Validation Tests]
    
    D --> G[ChatInteractionProperties]
    D --> H[ThreadLifecycleProperties]
    D --> I[FeatureUsageProperties]
    D --> J[SurveyResponseProperties]
    
    E --> K[Required Fields Test]
    E --> L[Optional Fields Test]
    E --> M[Type Validation Test]
    
    F --> N[MessageType Enum]
    F --> O[ThreadAction Enum]
    F --> P[FeedbackType Enum]
    
    G --> Q[Validate Model Creation]
    H --> Q
    I --> Q
    J --> Q
    K --> Q
    L --> Q
    M --> Q
    N --> Q
    O --> Q
    P --> Q
    
    Q --> R[JSON Serialization Test]
    R --> S[Assert Model Integrity]
    
    subgraph "Test Data Fixtures"
        T[Valid Model Data]
        U[Invalid Model Data]
        V[Edge Case Data]
        W[Missing Fields Data]
    end
    
    subgraph "Validation Assertions"
        X[Field Type Validation]
        Y[Required Field Validation]
        Z[Enum Value Validation]
        AA[JSON Round-trip Validation]
    end
    
    B --> T
    B --> U
    B --> V
    B --> W
    
    K --> Y
    M --> X
    F --> Z
    R --> AA
    
    style C fill:#e1f5fe
    style S fill:#c8e6c9
```

### Schema Validation Testing

```mermaid
flowchart TD
    A[Schema Validation Tests] --> B[Prepare Test Cases]
    B --> C[Component: Pydantic Models]
    
    C --> D[Valid Data Tests]
    C --> E[Invalid Data Tests]
    C --> F[Edge Case Tests]
    C --> G[Serialization Tests]
    
    D --> H[Assert Model Creation Success]
    E --> I[Assert ValidationError Raised]
    F --> J[Assert Edge Case Handling]
    G --> K[Assert JSON Round-trip]
    
    H --> L[Validate Field Values]
    I --> M[Validate Error Messages]
    J --> N[Validate Default Behavior]
    K --> O[Validate Serialized Data]
    
    L --> P[Test Complete]
    M --> P
    N --> P
    O --> P
    
    subgraph "Test Data Categories"
        Q[Valid Complete Data]
        R[Missing Required Fields]
        S[Invalid Type Data]
        T[Boundary Value Data]
        U[Null/Empty Data]
    end
    
    subgraph "Mock Boundaries"
        V[No External Dependencies]
        W[Pure Model Validation]
        X[No Network/Database Calls]
    end
    
    B --> Q
    B --> R
    B --> S
    B --> T
    B --> U
    
    style C fill:#e1f5fe
    style P fill:#c8e6c9
    style V fill:#fff3e0
```

---

## Business Logic Unit Tests

### Agent Execution Logic Testing

```mermaid
flowchart TD
    A[Agent Business Logic Tests] --> B[Setup Mock Dependencies]
    B --> C[MockBaseAgent Under Test]
    
    C --> D[Execute Core Logic Tests]
    C --> E[Validation Tests]
    C --> F[State Management Tests]
    C --> G[Error Handling Tests]
    
    D --> H[Mock execute_core_logic]
    E --> I[Mock validate_preconditions]
    F --> J[Mock State Transitions]
    G --> K[Mock Error Scenarios]
    
    H --> L[Assert Execution Results]
    I --> M[Assert Validation Logic]
    J --> N[Assert State Changes]
    K --> O[Assert Error Handling]
    
    L --> P[Verify Business Rules]
    M --> P
    N --> P
    O --> P
    
    P --> Q[Assert Final State]
    
    subgraph "Mock Infrastructure"
        R[Mock LLM Manager]
        S[Mock Tool Dispatcher]
        T[Mock Redis Manager]
        U[Mock WebSocket Bridge]
    end
    
    subgraph "Test Scenarios"
        V[Success Path]
        W[Validation Failure]
        X[Execution Failure]
        Y[State Transition Errors]
    end
    
    subgraph "Assertions"
        Z[Method Call Counts]
        AA[Return Value Validation]
        BB[State Consistency]
        CC[Error Propagation]
    end
    
    B --> R
    B --> S
    B --> T
    B --> U
    
    D --> V
    E --> W
    F --> X
    G --> Y
    
    L --> Z
    M --> AA
    N --> BB
    O --> CC
    
    style C fill:#e1f5fe
    style Q fill:#c8e6c9
    style R fill:#fff3e0
```

### Circuit Breaker Logic Testing

```mermaid
flowchart TD
    A[Circuit Breaker Logic Tests] --> B[Setup Test Configuration]
    B --> C[UnifiedCircuitBreaker Under Test]
    
    C --> D[State Transition Tests]
    C --> E[Failure Threshold Tests]
    C --> F[Recovery Logic Tests]
    C --> G[Metrics Tracking Tests]
    
    D --> H[CLOSED → OPEN]
    D --> I[OPEN → HALF_OPEN]
    D --> J[HALF_OPEN → CLOSED/OPEN]
    
    E --> K[Consecutive Failures]
    E --> L[Error Rate Calculation]
    E --> M[Sliding Window Logic]
    
    F --> N[Recovery Timeout]
    F --> O[Health Check Integration]
    F --> P[Exponential Backoff]
    
    G --> Q[Success/Failure Counters]
    G --> R[Response Time Tracking]
    G --> S[Adaptive Thresholds]
    
    H --> T[Assert State Change]
    I --> T
    J --> T
    K --> U[Assert Threshold Logic]
    L --> U
    M --> U
    N --> V[Assert Recovery Logic]
    O --> V
    P --> V
    Q --> W[Assert Metrics Accuracy]
    R --> W
    S --> W
    
    T --> X[Validate Circuit Behavior]
    U --> X
    V --> X
    W --> X
    
    subgraph "Mock Operations"
        Y[Success Operations]
        Z[Failing Operations]
        AA[Slow Operations]
        BB[Timeout Operations]
    end
    
    subgraph "Test Assertions"
        CC[State Consistency]
        DD[Metric Accuracy]
        EE[Timing Validation]
        FF[Error Handling]
    end
    
    style C fill:#e1f5fe
    style X fill:#c8e6c9
    style Y fill:#fff3e0
```

---

## Helper Functions Unit Tests

### Utility Function Testing

```mermaid
flowchart TD
    A[Helper Functions Unit Tests] --> B[Prepare Test Inputs]
    B --> C[Pure Function Under Test]
    
    C --> D[Input Validation Tests]
    C --> E[Output Transformation Tests]
    C --> F[Edge Case Tests]
    C --> G[Error Handling Tests]
    
    D --> H[Valid Input Cases]
    D --> I[Invalid Input Cases]
    D --> J[Boundary Value Cases]
    
    E --> K[Expected Output Format]
    E --> L[Data Type Conversions]
    E --> M[Value Transformations]
    
    F --> N[Null/Empty Inputs]
    F --> O[Maximum/Minimum Values]
    F --> P[Special Characters]
    
    G --> Q[Exception Handling]
    G --> R[Error Message Validation]
    G --> S[Graceful Degradation]
    
    H --> T[Assert Output Correctness]
    I --> U[Assert Error Raised]
    J --> V[Assert Boundary Handling]
    K --> T
    L --> T
    M --> T
    N --> V
    O --> V
    P --> V
    Q --> U
    R --> U
    S --> U
    
    T --> W[Validate Function Behavior]
    U --> W
    V --> W
    
    subgraph "Test Data"
        X[Valid Input Sets]
        Y[Invalid Input Sets]
        Z[Edge Case Inputs]
        AA[Expected Outputs]
    end
    
    subgraph "Mock Boundaries"
        BB[No External Dependencies]
        CC[Pure Function Testing]
        DD[Deterministic Results]
    end
    
    style C fill:#e1f5fe
    style W fill:#c8e6c9
    style BB fill:#fff3e0
```

### String/URL Processing Testing

```mermaid
flowchart TD
    A[String Processing Unit Tests] --> B[Test Input Preparation]
    B --> C[String/URL Processing Function]
    
    C --> D[Format Validation Tests]
    C --> E[Parsing Logic Tests]
    C --> F[Transformation Tests]
    
    D --> G[URL Format Validation]
    D --> H[String Pattern Matching]
    D --> I[Encoding Validation]
    
    E --> J[URL Component Extraction]
    E --> K[Parameter Parsing]
    E --> L[Path Normalization]
    
    F --> M[Format Conversion]
    F --> N[Encoding Transformation]
    F --> O[Parameter Modification]
    
    G --> P[Assert Valid Formats]
    H --> Q[Assert Pattern Matches]
    I --> R[Assert Encoding Correctness]
    J --> S[Assert Component Accuracy]
    K --> T[Assert Parameter Values]
    L --> U[Assert Path Normalization]
    M --> V[Assert Format Changes]
    N --> W[Assert Encoding Changes]
    O --> X[Assert Parameter Changes]
    
    P --> Y[Validate Processing Results]
    Q --> Y
    R --> Y
    S --> Y
    T --> Y
    U --> Y
    V --> Y
    W --> Y
    X --> Y
    
    subgraph "Test Cases"
        Z[Valid URLs/Strings]
        AA[Invalid Formats]
        BB[Edge Cases]
        CC[Unicode/Special Chars]
    end
    
    subgraph "Expected Outputs"
        DD[Parsed Components]
        EE[Transformed Formats]
        FF[Validation Results]
        GG[Error Conditions]
    end
    
    style C fill:#e1f5fe
    style Y fill:#c8e6c9
```

---

## Validators Unit Tests

### Input Validation Testing

```mermaid
flowchart TD
    A[Validator Unit Tests] --> B[Setup Test Data]
    B --> C[Validator Function Under Test]
    
    C --> D[Valid Input Tests]
    C --> E[Invalid Input Tests]
    C --> F[Boundary Value Tests]
    C --> G[Type Validation Tests]
    
    D --> H[Should Pass Validation]
    E --> I[Should Fail Validation]
    F --> J[Should Handle Boundaries]
    G --> K[Should Check Types]
    
    H --> L[Assert Validation Success]
    I --> M[Assert Validation Failure]
    J --> N[Assert Boundary Behavior]
    K --> O[Assert Type Checking]
    
    L --> P[Return Valid Result]
    M --> Q[Return Error Details]
    N --> R[Return Boundary Result]
    O --> S[Return Type Error]
    
    P --> T[Validate Validator Behavior]
    Q --> T
    R --> T
    S --> T
    
    subgraph "Test Input Categories"
        U[Valid Data Samples]
        V[Invalid Data Samples]
        W[Boundary Values]
        X[Wrong Types]
        Y[Null/Empty Values]
    end
    
    subgraph "Validation Rules"
        Z[Required Fields]
        AA[Format Patterns]
        BB[Value Ranges]
        CC[Type Constraints]
    end
    
    subgraph "Expected Outcomes"
        DD[Validation Pass]
        EE[Validation Fail]
        FF[Error Messages]
        GG[Sanitized Values]
    end
    
    B --> U
    B --> V
    B --> W
    B --> X
    B --> Y
    
    style C fill:#e1f5fe
    style T fill:#c8e6c9
```

### Data Sanitization Testing

```mermaid
flowchart TD
    A[Data Sanitization Tests] --> B[Prepare Test Data]
    B --> C[Data Sanitizer Under Test]
    
    C --> D[Input Cleaning Tests]
    C --> E[Security Filtering Tests]
    C --> F[Format Normalization Tests]
    
    D --> G[Remove Invalid Characters]
    D --> H[Trim Whitespace]
    D --> I[Handle Special Cases]
    
    E --> J[SQL Injection Prevention]
    E --> K[XSS Prevention]
    E --> L[Path Traversal Prevention]
    
    F --> M[Normalize Formats]
    F --> N[Standardize Encoding]
    F --> O[Consistent Casing]
    
    G --> P[Assert Clean Output]
    H --> Q[Assert Trimmed Output]
    I --> R[Assert Special Handling]
    J --> S[Assert SQL Safety]
    K --> T[Assert XSS Safety]
    L --> U[Assert Path Safety]
    M --> V[Assert Format Consistency]
    N --> W[Assert Encoding Standards]
    O --> X[Assert Case Standards]
    
    P --> Y[Validate Sanitization]
    Q --> Y
    R --> Y
    S --> Y
    T --> Y
    U --> Y
    V --> Y
    W --> Y
    X --> Y
    
    subgraph "Malicious Input Samples"
        Z[SQL Injection Attempts]
        AA[XSS Payloads]
        BB[Path Traversal Attempts]
        CC[Script Injection]
    end
    
    subgraph "Clean Output Verification"
        DD[Safe SQL Content]
        EE[Escaped XSS Content]
        FF[Safe Path Content]
        GG[Sanitized Scripts]
    end
    
    style C fill:#e1f5fe
    style Y fill:#c8e6c9
    style Z fill:#ffebee
```

---

## Agent Infrastructure Unit Tests

### BaseAgent Infrastructure Testing

```mermaid
flowchart TD
    A[BaseAgent Infrastructure Tests] --> B[Setup Mock Dependencies]
    B --> C[MockBaseAgent Under Test]
    
    C --> D[Reliability Infrastructure]
    C --> E[Execution Engine]
    C --> F[WebSocket Infrastructure]
    C --> G[Health Monitoring]
    
    D --> H[Circuit Breaker Integration]
    D --> I[Retry Logic Testing]
    D --> J[Fallback Execution]
    
    E --> K[Modern Execution Pattern]
    E --> L[Context Management]
    E --> M[Monitoring Integration]
    
    F --> N[Event Emission]
    F --> O[Bridge Integration]
    F --> P[Update Methods]
    
    G --> Q[Component Health Status]
    G --> R[Overall Health Calculation]
    G --> S[Health Reporting]
    
    H --> T[Assert Circuit Behavior]
    I --> U[Assert Retry Behavior]
    J --> V[Assert Fallback Execution]
    K --> W[Assert Execution Results]
    L --> X[Assert Context Handling]
    M --> Y[Assert Monitoring Data]
    N --> Z[Assert Event Emission]
    O --> AA[Assert Bridge Integration]
    P --> BB[Assert Update Delivery]
    Q --> CC[Assert Component Health]
    R --> DD[Assert Health Calculation]
    S --> EE[Assert Health Reports]
    
    T --> FF[Validate Infrastructure]
    U --> FF
    V --> FF
    W --> FF
    X --> FF
    Y --> FF
    Z --> FF
    AA --> FF
    BB --> FF
    CC --> FF
    DD --> FF
    EE --> FF
    
    subgraph "Mock Infrastructure"
        GG[Mock LLM Manager]
        HH[Mock Tool Dispatcher]
        II[Mock Redis Manager]
        JJ[Mock WebSocket Bridge]
    end
    
    subgraph "Feature Toggles"
        KK[Enable Reliability]
        LL[Enable Execution Engine]
        MM[Enable Caching]
        NN[Enable WebSocket]
    end
    
    subgraph "Test Scenarios"
        OO[Success Paths]
        PP[Failure Scenarios]
        QQ[Edge Cases]
        RR[Error Recovery]
    end
    
    B --> GG
    B --> HH
    B --> II
    B --> JJ
    
    style C fill:#e1f5fe
    style FF fill:#c8e6c9
    style GG fill:#fff3e0
```

### Agent State Management Testing

```mermaid
flowchart TD
    A[Agent State Management Tests] --> B[Setup Initial State]
    B --> C[Agent State Manager Under Test]
    
    C --> D[State Transition Tests]
    C --> E[State Validation Tests]
    C --> F[State Persistence Tests]
    
    D --> G[Valid Transitions]
    D --> H[Invalid Transitions]
    D --> I[Edge Case Transitions]
    
    E --> J[State Consistency Checks]
    E --> K[State Invariant Validation]
    E --> L[State History Tracking]
    
    F --> M[State Serialization]
    F --> N[State Restoration]
    F --> O[State Cleanup]
    
    G --> P[Assert Transition Success]
    H --> Q[Assert Transition Rejection]
    I --> R[Assert Edge Case Handling]
    J --> S[Assert State Consistency]
    K --> T[Assert Invariants Hold]
    L --> U[Assert History Accuracy]
    M --> V[Assert Serialization Works]
    N --> W[Assert Restoration Works]
    O --> X[Assert Cleanup Complete]
    
    P --> Y[Validate State Management]
    Q --> Y
    R --> Y
    S --> Y
    T --> Y
    U --> Y
    V --> Y
    W --> Y
    X --> Y
    
    subgraph "State Machine"
        Z[PENDING]
        AA[RUNNING]
        BB[COMPLETED]
        CC[FAILED]
        DD[SHUTDOWN]
    end
    
    subgraph "Transition Rules"
        EE[Valid Paths]
        FF[Invalid Paths]
        GG[Terminal States]
        HH[Validation Logic]
    end
    
    style C fill:#e1f5fe
    style Y fill:#c8e6c9
```

---

## Resilience Components Unit Tests

### Circuit Breaker Component Testing

```mermaid
flowchart TD
    A[Circuit Breaker Unit Tests] --> B[Setup Test Configuration]
    B --> C[UnifiedCircuitBreaker Component]
    
    C --> D[Core Functionality Tests]
    C --> E[State Management Tests]
    C --> F[Metrics Tracking Tests]
    C --> G[Configuration Tests]
    
    D --> H[Operation Execution]
    D --> I[Timeout Handling]
    D --> J[Exception Processing]
    
    E --> K[State Transitions]
    E --> L[Recovery Logic]
    E --> M[Backoff Calculation]
    
    F --> N[Success/Failure Tracking]
    F --> O[Response Time Tracking]
    F --> P[Error Rate Calculation]
    
    G --> Q[Config Validation]
    G --> R[Adaptive Behavior]
    G --> S[Health Integration]
    
    H --> T[Assert Operation Results]
    I --> U[Assert Timeout Handling]
    J --> V[Assert Exception Processing]
    K --> W[Assert State Changes]
    L --> X[Assert Recovery Behavior]
    M --> Y[Assert Backoff Logic]
    N --> Z[Assert Metric Accuracy]
    O --> AA[Assert Response Tracking]
    P --> BB[Assert Error Rate Calc]
    Q --> CC[Assert Config Validity]
    R --> DD[Assert Adaptive Logic]
    S --> EE[Assert Health Integration]
    
    T --> FF[Validate Circuit Breaker]
    U --> FF
    V --> FF
    W --> FF
    X --> FF
    Y --> FF
    Z --> FF
    AA --> FF
    BB --> FF
    CC --> FF
    DD --> FF
    EE --> FF
    
    subgraph "Mock Operations"
        GG[Success Operations]
        HH[Failing Operations]
        II[Slow Operations]
        JJ[Timeout Operations]
    end
    
    subgraph "Test Configurations"
        KK[Basic Config]
        LL[Adaptive Config]
        MM[Health Check Config]
        NN[Backoff Config]
    end
    
    subgraph "Validation Points"
        OO[State Consistency]
        PP[Metric Accuracy]
        QQ[Timing Correctness]
        RR[Configuration Compliance]
    end
    
    style C fill:#e1f5fe
    style FF fill:#c8e6c9
    style GG fill:#fff3e0
```

### Retry Handler Testing

```mermaid
flowchart TD
    A[Retry Handler Unit Tests] --> B[Setup Retry Configuration]
    B --> C[Retry Handler Component]
    
    C --> D[Basic Retry Tests]
    C --> E[Exponential Backoff Tests]
    C --> F[Jitter Application Tests]
    C --> G[Max Attempts Tests]
    
    D --> H[Immediate Retry]
    D --> I[Delayed Retry]
    D --> J[Conditional Retry]
    
    E --> K[Backoff Calculation]
    E --> L[Progressive Delays]
    E --> M[Maximum Delay Caps]
    
    F --> N[Jitter Addition]
    F --> O[Randomization Verification]
    F --> P[Timing Variation]
    
    G --> Q[Attempt Counting]
    G --> R[Max Limit Enforcement]
    G --> S[Final Failure Handling]
    
    H --> T[Assert Retry Logic]
    I --> U[Assert Delay Logic]
    J --> V[Assert Condition Logic]
    K --> W[Assert Backoff Math]
    L --> X[Assert Progressive Increase]
    M --> Y[Assert Delay Caps]
    N --> Z[Assert Jitter Application]
    O --> AA[Assert Randomization]
    P --> BB[Assert Timing Variance]
    Q --> CC[Assert Attempt Tracking]
    R --> DD[Assert Limit Enforcement]
    S --> EE[Assert Failure Handling]
    
    T --> FF[Validate Retry Behavior]
    U --> FF
    V --> FF
    W --> FF
    X --> FF
    Y --> FF
    Z --> FF
    AA --> FF
    BB --> FF
    CC --> FF
    DD --> FF
    EE --> FF
    
    subgraph "Retry Scenarios"
        GG[Transient Failures]
        HH[Permanent Failures]
        II[Timeout Failures]
        JJ[Mixed Failures]
    end
    
    subgraph "Timing Validations"
        KK[Base Delay]
        LL[Exponential Growth]
        MM[Jitter Range]
        NN[Maximum Bounds]
    end
    
    style C fill:#e1f5fe
    style FF fill:#c8e6c9
```

---

## Configuration Unit Tests

### Configuration Manager Testing

```mermaid
flowchart TD
    A[Configuration Manager Tests] --> B[Setup Environment Mocks]
    B --> C[Configuration Manager Component]
    
    C --> D[Environment Detection Tests]
    C --> E[Configuration Loading Tests]
    C --> F[Validation Tests]
    C --> G[Override Tests]
    
    D --> H[Development Environment]
    D --> I[Staging Environment]
    D --> J[Production Environment]
    D --> K[Test Environment]
    
    E --> L[File-based Config]
    E --> M[Environment Variables]
    E --> N[Default Values]
    E --> O[Config Merging]
    
    F --> P[Required Field Validation]
    F --> Q[Type Validation]
    F --> R[Range Validation]
    F --> S[Format Validation]
    
    G --> T[Environment Overrides]
    G --> U[Runtime Overrides]
    G --> V[Priority Resolution]
    
    H --> W[Assert Dev Config]
    I --> X[Assert Staging Config]
    J --> Y[Assert Prod Config]
    K --> Z[Assert Test Config]
    L --> AA[Assert File Loading]
    M --> BB[Assert Env Loading]
    N --> CC[Assert Defaults]
    O --> DD[Assert Merging Logic]
    P --> EE[Assert Required Fields]
    Q --> FF[Assert Type Checking]
    R --> GG[Assert Range Checking]
    S --> HH[Assert Format Checking]
    T --> II[Assert Env Overrides]
    U --> JJ[Assert Runtime Overrides]
    V --> KK[Assert Priority Logic]
    
    W --> LL[Validate Configuration]
    X --> LL
    Y --> LL
    Z --> LL
    AA --> LL
    BB --> LL
    CC --> LL
    DD --> LL
    EE --> LL
    FF --> LL
    GG --> LL
    HH --> LL
    II --> LL
    JJ --> LL
    KK --> LL
    
    subgraph "Mock Environment"
        MM[Mock env vars]
        NN[Mock config files]
        OO[Mock env detection]
    end
    
    subgraph "Test Configurations"
        PP[Valid Configs]
        QQ[Invalid Configs]
        RR[Partial Configs]
        SS[Override Configs]
    end
    
    B --> MM
    B --> NN
    B --> OO
    
    style C fill:#e1f5fe
    style LL fill:#c8e6c9
    style MM fill:#fff3e0
```

### Service Configuration Testing

```mermaid
flowchart TD
    A[Service Configuration Tests] --> B[Service-specific Setup]
    B --> C[Service Config Component]
    
    C --> D[Database Config Tests]
    C --> E[Redis Config Tests]
    C --> F[Auth Config Tests]
    C --> G[Analytics Config Tests]
    
    D --> H[Database URL Building]
    D --> I[Connection Pool Settings]
    D --> J[Migration Settings]
    
    E --> K[Redis Connection Config]
    E --> L[Cache Settings]
    E --> M[Session Settings]
    
    F --> N[JWT Settings]
    F --> O[OAuth Settings]
    F --> P[Session Management]
    
    G --> Q[Event Tracking Config]
    G --> R[Metrics Config]
    G --> S[Analytics Endpoints]
    
    H --> T[Assert DB URL Format]
    I --> U[Assert Pool Settings]
    J --> V[Assert Migration Config]
    K --> W[Assert Redis Config]
    L --> X[Assert Cache Config]
    M --> Y[Assert Session Config]
    N --> Z[Assert JWT Config]
    O --> AA[Assert OAuth Config]
    P --> BB[Assert Session Config]
    Q --> CC[Assert Event Config]
    R --> DD[Assert Metrics Config]
    S --> EE[Assert Endpoint Config]
    
    T --> FF[Validate Service Config]
    U --> FF
    V --> FF
    W --> FF
    X --> FF
    Y --> FF
    Z --> FF
    AA --> FF
    BB --> FF
    CC --> FF
    DD --> FF
    EE --> FF
    
    subgraph "Service Types"
        GG[Backend Service]
        HH[Auth Service]
        II[Analytics Service]
        JJ[Frontend Service]
    end
    
    subgraph "Config Categories"
        KK[Connection Configs]
        LL[Security Configs]
        MM[Performance Configs]
        NN[Feature Configs]
    end
    
    style C fill:#e1f5fe
    style FF fill:#c8e6c9
```

---

## Database Components Unit Tests

### Database Manager Testing

```mermaid
flowchart TD
    A[Database Manager Unit Tests] --> B[Mock Database Dependencies]
    B --> C[DatabaseManager Component]
    
    C --> D[URL Conversion Tests]
    C --> E[Connection Management Tests]
    C --> F[Migration Support Tests]
    C --> G[Environment Handling Tests]
    
    D --> H[Sync/Async Conversion]
    D --> I[SSL Parameter Handling]
    D --> J[Cloud SQL Support]
    D --> K[Schema Path Handling]
    
    E --> L[Connection Pool Config]
    E --> M[Connection Validation]
    E --> N[Connection Cleanup]
    
    F --> O[Migration URL Generation]
    F --> P[Schema Management]
    F --> Q[Migration Validation]
    
    G --> R[Environment Detection]
    G --> S[Config Override Handling]
    G --> T[Test Environment Support]
    
    H --> U[Assert URL Format]
    I --> V[Assert SSL Handling]
    J --> W[Assert Cloud SQL Format]
    K --> X[Assert Schema Paths]
    L --> Y[Assert Pool Config]
    M --> Z[Assert Connection Validation]
    N --> AA[Assert Cleanup Logic]
    O --> BB[Assert Migration URLs]
    P --> CC[Assert Schema Management]
    Q --> DD[Assert Migration Validation]
    R --> EE[Assert Environment Detection]
    S --> FF[Assert Override Handling]
    T --> GG[Assert Test Support]
    
    U --> HH[Validate Database Manager]
    V --> HH
    W --> HH
    X --> HH
    Y --> HH
    Z --> HH
    AA --> HH
    BB --> HH
    CC --> HH
    DD --> HH
    EE --> HH
    FF --> HH
    GG --> HH
    
    subgraph "Mock Dependencies"
        II[Mock Unified Config]
        JJ[Mock Environment]
        KK[Mock Database Connection]
    end
    
    subgraph "URL Test Cases"
        LL[PostgreSQL URLs]
        MM[AsyncPG URLs]
        NN[Cloud SQL URLs]
        OO[SSL URLs]
    end
    
    B --> II
    B --> JJ
    B --> KK
    
    D --> LL
    D --> MM
    D --> NN
    D --> OO
    
    style C fill:#e1f5fe
    style HH fill:#c8e6c9
    style II fill:#fff3e0
```

### Data Access Layer Testing

```mermaid
flowchart TD
    A[Data Access Layer Tests] --> B[Setup Test Data]
    B --> C[DAL Component Under Test]
    
    C --> D[CRUD Operation Tests]
    C --> E[Query Builder Tests]
    C --> F[Transaction Tests]
    C --> G[Error Handling Tests]
    
    D --> H[Create Operations]
    D --> I[Read Operations]
    D --> J[Update Operations]
    D --> K[Delete Operations]
    
    E --> L[Query Construction]
    E --> M[Filter Application]
    E --> N[Join Logic]
    E --> O[Sorting/Pagination]
    
    F --> P[Transaction Start]
    F --> Q[Transaction Commit]
    F --> R[Transaction Rollback]
    F --> S[Nested Transactions]
    
    G --> T[Connection Errors]
    G --> U[Query Errors]
    G --> V[Data Validation Errors]
    G --> W[Constraint Violations]
    
    H --> X[Assert Create Success]
    I --> Y[Assert Read Results]
    J --> Z[Assert Update Success]
    K --> AA[Assert Delete Success]
    L --> BB[Assert Query Structure]
    M --> CC[Assert Filter Logic]
    N --> DD[Assert Join Logic]
    O --> EE[Assert Sorting/Paging]
    P --> FF[Assert Transaction Start]
    Q --> GG[Assert Commit Logic]
    R --> HH[Assert Rollback Logic]
    S --> II[Assert Nested Handling]
    T --> JJ[Assert Error Handling]
    U --> KK[Assert Query Error Handling]
    V --> LL[Assert Validation Handling]
    W --> MM[Assert Constraint Handling]
    
    X --> NN[Validate DAL Operations]
    Y --> NN
    Z --> NN
    AA --> NN
    BB --> NN
    CC --> NN
    DD --> NN
    EE --> NN
    FF --> NN
    GG --> NN
    HH --> NN
    II --> NN
    JJ --> NN
    KK --> NN
    LL --> NN
    MM --> NN
    
    subgraph "Mock Database"
        OO[Mock Connection]
        PP[Mock Transaction]
        QQ[Mock Cursor]
        RR[Mock Results]
    end
    
    subgraph "Test Data Sets"
        SS[Valid Records]
        TT[Invalid Records]
        UU[Edge Cases]
        VV[Constraint Violations]
    end
    
    B --> SS
    B --> TT
    B --> UU
    B --> VV
    
    style C fill:#e1f5fe
    style NN fill:#c8e6c9
    style OO fill:#fff3e0
```

---

## WebSocket Components Unit Tests

### WebSocket Manager Testing

```mermaid
flowchart TD
    A[WebSocket Manager Tests] --> B[Mock WebSocket Dependencies]
    B --> C[WebSocket Manager Component]
    
    C --> D[Connection Management Tests]
    C --> E[Message Handling Tests]
    C --> F[Event Broadcasting Tests]
    C --> G[Error Handling Tests]
    
    D --> H[Connection Establishment]
    D --> I[Connection Cleanup]
    D --> J[Connection State Tracking]
    
    E --> K[Message Validation]
    E --> L[Message Routing]
    E --> M[Message Serialization]
    
    F --> N[Event Filtering]
    F --> O[Broadcast Logic]
    F --> P[Subscription Management]
    
    G --> Q[Connection Errors]
    G --> R[Message Errors]
    G --> S[Broadcast Errors]
    
    H --> T[Assert Connection Success]
    I --> U[Assert Cleanup Logic]
    J --> V[Assert State Tracking]
    K --> W[Assert Message Validation]
    L --> X[Assert Message Routing]
    M --> Y[Assert Serialization]
    N --> Z[Assert Event Filtering]
    O --> AA[Assert Broadcast Logic]
    P --> BB[Assert Subscription Logic]
    Q --> CC[Assert Connection Error Handling]
    R --> DD[Assert Message Error Handling]
    S --> EE[Assert Broadcast Error Handling]
    
    T --> FF[Validate WebSocket Manager]
    U --> FF
    V --> FF
    W --> FF
    X --> FF
    Y --> FF
    Z --> FF
    AA --> FF
    BB --> FF
    CC --> FF
    DD --> FF
    EE --> FF
    
    subgraph "Mock WebSocket Infrastructure"
        GG[Mock WebSocket Connection]
        HH[Mock Message Queue]
        II[Mock Event Bus]
        JJ[Mock Serializer]
    end
    
    subgraph "Test Scenarios"
        KK[Single Connection]
        LL[Multiple Connections]
        MM[Connection Failures]
        NN[Message Failures]
    end
    
    subgraph "Event Types"
        OO[Agent Events]
        PP[Tool Events]
        QQ[System Events]
        RR[Custom Events]
    end
    
    B --> GG
    B --> HH
    B --> II
    B --> JJ
    
    style C fill:#e1f5fe
    style FF fill:#c8e6c9
    style GG fill:#fff3e0
```

### Agent WebSocket Bridge Testing

```mermaid
flowchart TD
    A[Agent WebSocket Bridge Tests] --> B[Setup Mock Components]
    B --> C[AgentWebSocketBridge Component]
    
    C --> D[Agent Event Tests]
    C --> E[Tool Event Tests]
    C --> F[Progress Event Tests]
    C --> G[Error Event Tests]
    
    D --> H[Agent Started Events]
    D --> I[Agent Thinking Events]
    D --> J[Agent Completed Events]
    
    E --> K[Tool Executing Events]
    E --> L[Tool Completed Events]
    E --> M[Tool Error Events]
    
    F --> N[Progress Updates]
    F --> O[Step Completion]
    F --> P[Percentage Updates]
    
    G --> Q[Error Notifications]
    G --> R[Exception Handling]
    G --> S[Recovery Notifications]
    
    H --> T[Assert Event Structure]
    I --> U[Assert Thinking Format]
    J --> V[Assert Completion Format]
    K --> W[Assert Tool Execution Format]
    L --> X[Assert Tool Completion Format]
    M --> Y[Assert Tool Error Format]
    N --> Z[Assert Progress Format]
    O --> AA[Assert Step Format]
    P --> BB[Assert Percentage Format]
    Q --> CC[Assert Error Format]
    R --> DD[Assert Exception Format]
    S --> EE[Assert Recovery Format]
    
    T --> FF[Validate Event Emission]
    U --> FF
    V --> FF
    W --> FF
    X --> FF
    Y --> FF
    Z --> FF
    AA --> FF
    BB --> FF
    CC --> FF
    DD --> FF
    EE --> FF
    
    subgraph "Mock WebSocket"
        GG[Mock WebSocket Manager]
        HH[Mock Connection]
        II[Mock Event Queue]
    end
    
    subgraph "Event Validation"
        JJ[Event Schema Validation]
        KK[Timestamp Validation]
        LL[Payload Validation]
        MM[Routing Validation]
    end
    
    subgraph "Test Event Data"
        NN[Valid Event Data]
        OO[Invalid Event Data]
        PP[Edge Case Data]
        QQ[Error Scenarios]
    end
    
    B --> GG
    B --> HH
    B --> II
    
    style C fill:#e1f5fe
    style FF fill:#c8e6c9
    style GG fill:#fff3e0
```

---

## Test Execution Flow Summary

```mermaid
flowchart TD
    A[Unit Test Execution] --> B[Test Discovery]
    B --> C[Test Categories]
    
    C --> D[Core Utilities]
    C --> E[Data Models]
    C --> F[Business Logic]
    C --> G[Helpers & Validators]
    C --> H[Infrastructure]
    
    D --> I[Environment, CORS, Database URL]
    E --> J[Analytics Models, Schema Validation]
    F --> K[Agent Logic, Circuit Breaker Logic]
    G --> L[Utility Functions, Validators]
    H --> M[Agent Infrastructure, Resilience, Config, DB, WebSocket]
    
    I --> N[Mock External Dependencies]
    J --> N
    K --> N
    L --> N
    M --> N
    
    N --> O[Execute Individual Tests]
    O --> P[Assert Expected Behavior]
    P --> Q[Validate Component Isolation]
    Q --> R[Report Test Results]
    
    subgraph "Mock Boundaries"
        S[No Network Calls]
        T[No Database Connections]
        U[No File System Access]
        V[No External Services]
    end
    
    subgraph "Test Isolation"
        W[Component Under Test]
        X[Controlled Dependencies]
        Y[Predictable Inputs]
        Z[Validated Outputs]
    end
    
    subgraph "Validation Points"
        AA[Input/Output Correctness]
        BB[Error Handling]
        CC[Edge Case Behavior]
        DD[Performance Characteristics]
    end
    
    N --> S
    N --> T
    N --> U
    N --> V
    
    O --> W
    O --> X
    O --> Y
    O --> Z
    
    P --> AA
    P --> BB
    P --> CC
    P --> DD
    
    style O fill:#e1f5fe
    style R fill:#c8e6c9
    style S fill:#fff3e0
```

## Test Categories Summary

| Category | Components Tested | Mock Boundaries | Key Validations |
|----------|------------------|-----------------|-----------------|
| **Core Utilities** | Environment isolation, CORS config, Database URL builders | External env vars, config files, network calls | Variable access, format conversion, configuration correctness |
| **Data Models** | Pydantic models, schema validation, serialization | Database connections, external APIs | Field validation, type checking, JSON round-trip |
| **Business Logic** | Agent execution, circuit breaker logic, state management | External dependencies, infrastructure components | Business rule enforcement, state consistency, error handling |
| **Helpers & Validators** | Utility functions, input validators, data sanitizers | File system, network, external services | Input/output correctness, validation rules, security filtering |
| **Infrastructure** | Agent base classes, resilience components, configuration managers, database managers, WebSocket components | External services, network calls, database connections, WebSocket connections | Component integration, error handling, configuration loading, event emission |

## Key Testing Principles

1. **Isolation**: Each unit test focuses on a single component with all dependencies mocked
2. **Predictability**: Tests use controlled inputs and validate expected outputs
3. **Coverage**: Tests cover happy paths, error conditions, and edge cases
4. **Performance**: Tests validate performance characteristics where relevant
5. **Security**: Tests validate security measures like input sanitization and injection prevention
6. **Maintainability**: Tests are organized by component and follow consistent patterns

This comprehensive unit test architecture ensures reliable, maintainable, and thoroughly validated components across the Netra platform.
# Agent Reliability and Health Monitor Documentation

## Executive Summary

The Agent Reliability and Health Monitor system is a comprehensive framework that ensures robust agent execution through multiple layers of protection, monitoring, and recovery mechanisms. It combines proactive health monitoring, intelligent retry strategies, circuit breaker patterns, and automated recovery to maintain high system availability and performance.

## System Architecture Overview

```mermaid
graph TB
    subgraph "Agent Execution Layer"
        Agent[Agent]
        ARM[AgentReliabilityMixin]
    end

    subgraph "Reliability Components"
        URM[UnifiedReliabilityManager]
        URH[UnifiedRetryHandler]
        UCB[UnifiedCircuitBreaker]
    end

    subgraph "Health Monitoring"
        AHM[AgentHealthMonitor]
        AET[AgentExecutionTracker]
        HSC[Health Score Calculator]
    end

    subgraph "Recovery Systems"
        RCM[RecoveryManager]
        RS[Recovery Strategies]
        FB[Fallback Operations]
    end

    subgraph "Observability"
        WS[WebSocket Events]
        ERH[Error History]
        MET[Metrics Tracking]
    end

    Agent --> ARM
    ARM --> URM
    ARM --> AHM
    ARM --> RCM
    
    URM --> URH
    URM --> UCB
    URM --> WS
    
    AHM --> AET
    AHM --> HSC
    AHM --> ERH
    
    RCM --> RS
    RCM --> FB
    
    URH --> MET
    UCB --> MET
    AET --> MET
```

## Core Components

### 1. AgentReliabilityMixin

The `AgentReliabilityMixin` is a base class that agents inherit to gain comprehensive reliability features. It acts as the primary interface layer between agents and the reliability infrastructure.

```mermaid
classDiagram
    class AgentReliabilityMixin {
        +reliability: UnifiedReliabilityManager
        +error_handler: AgentErrorHandler
        +health_monitor: AgentHealthMonitor
        +recovery_manager: AgentRecoveryManager
        +execute_with_reliability()
        +register_recovery_strategy()
        +get_comprehensive_health_status()
        +perform_health_check()
    }
    
    class BaseAgent {
        +name: str
        +execute()
    }
    
    BaseAgent <|-- AgentReliabilityMixin
```

**Key Features:**
- **Automatic initialization** of reliability components
- **Transparent error handling** without code changes
- **Built-in recovery strategies** for common operations
- **Health status reporting** and metrics collection

### 2. AgentHealthMonitor

The `AgentHealthMonitor` tracks agent health through multiple metrics and provides real-time health assessment.

```mermaid
flowchart LR
    subgraph "Health Metrics Collection"
        OT[Operation Times]
        ER[Error History]
        HB[Heartbeat Monitoring]
    end
    
    subgraph "Health Analysis"
        SR[Success Rate]
        RT[Response Time]
        ED[Error Detection]
    end
    
    subgraph "Health Status"
        HS[Health Score 0-1]
        ST[Status: healthy/degraded/unhealthy/dead]
        CB[Circuit Breaker State]
    end
    
    OT --> SR
    ER --> ED
    HB --> ED
    
    SR --> HS
    RT --> HS
    ED --> HS
    
    HS --> ST
    CB --> ST
```

**Health Score Calculation:**

```mermaid
graph TD
    Start[Start Health Calculation]
    SR[Calculate Success Rate]
    EP[Calculate Error Penalty]
    TP[Calculate Time Penalty]
    DS[Detect Dead Agents]
    
    Start --> DS
    DS -->|Dead| Dead[Return 0.0 Health]
    DS -->|Alive| SR
    SR --> EP
    EP --> TP
    TP --> Score[Final Score = SR - EP - TP]
    
    Score --> Status{Score Value}
    Status -->|>= 0.8| Healthy
    Status -->|>= 0.5| Degraded
    Status -->|< 0.5| Unhealthy
```

### 3. UnifiedReliabilityManager

The `UnifiedReliabilityManager` orchestrates all reliability patterns and provides centralized management.

```mermaid
stateDiagram-v2
    [*] --> Initialized
    
    Initialized --> Executing: execute_with_reliability()
    
    Executing --> CircuitCheck: Check Circuit Breaker
    
    CircuitCheck --> Open: Circuit Open
    CircuitCheck --> Closed: Circuit Closed
    
    Open --> Fallback: Execute Fallback
    Closed --> Retry: Execute with Retry
    
    Retry --> Success: Operation Success
    Retry --> RetryAttempt: Operation Failed
    RetryAttempt --> Retry: Retry Available
    RetryAttempt --> Failed: Max Retries Exceeded
    
    Failed --> Recovery: Attempt Recovery
    Recovery --> Fallback: Recovery Strategy
    Recovery --> Error: No Recovery Available
    
    Success --> RecordSuccess: Record Metrics
    Fallback --> RecordSuccess
    Error --> RecordFailure: Record Failure
    
    RecordSuccess --> EmitEvent: Emit WebSocket Event
    RecordFailure --> EmitEvent
    
    EmitEvent --> [*]
```

**Key Responsibilities:**
- **Retry orchestration** with configurable strategies
- **Circuit breaker management** for fault isolation
- **Timeout enforcement** for operation boundaries
- **Fallback coordination** for graceful degradation
- **Metrics collection** for observability
- **WebSocket event emission** for real-time monitoring

### 4. AgentRecoveryManager

The `AgentRecoveryManager` implements intelligent recovery strategies for different failure scenarios.

```mermaid
flowchart TB
    Error[Operation Error]
    
    Error --> Analyze{Analyze Error Type}
    
    Analyze -->|LLM Error| LLMRecovery[LLM Recovery Strategy]
    Analyze -->|DB Error| DBRecovery[Database Recovery Strategy]
    Analyze -->|API Error| APIRecovery[API Recovery Strategy]
    Analyze -->|Unknown| DefaultRecovery[Default Recovery]
    
    LLMRecovery --> Simplified[Use Simplified Prompt]
    LLMRecovery --> Cached[Use Cached Response]
    LLMRecovery --> Fallback1[Fallback LLM Provider]
    
    DBRecovery --> CachedData[Return Cached Data]
    DBRecovery --> ReadReplica[Try Read Replica]
    DBRecovery --> EmptySet[Return Empty Dataset]
    
    APIRecovery --> Retry[Retry with Backoff]
    APIRecovery --> AlternateEndpoint[Try Alternate Endpoint]
    APIRecovery --> MockData[Return Mock Data]
    
    DefaultRecovery --> LogError[Log and Continue]
    
    Simplified --> Result[Recovery Result]
    Cached --> Result
    Fallback1 --> Result
    CachedData --> Result
    ReadReplica --> Result
    EmptySet --> Result
    Retry --> Result
    AlternateEndpoint --> Result
    MockData --> Result
    LogError --> Result
```

## Monitoring and Detection Systems

### Death Detection

The system implements multiple layers of death detection to identify and handle agent failures:

```mermaid
sequenceDiagram
    participant Agent
    participant Monitor as Health Monitor
    participant Tracker as Execution Tracker
    participant Alert as Alert System
    
    loop Every Operation
        Agent->>Monitor: Send Heartbeat
        Monitor->>Monitor: Update Last Heartbeat
    end
    
    Note over Monitor: Health Check Interval (60s)
    
    Monitor->>Monitor: Check Heartbeat Age
    
    alt No Heartbeat > 10s
        Monitor->>Tracker: Check Execution Status
        Tracker-->>Monitor: Dead Executions List
        Monitor->>Alert: Agent Death Detected
        Alert->>Alert: Log Critical Error
        Alert->>Alert: Emit WebSocket Event
        Monitor-->>Agent: Health Status: DEAD
    else Heartbeat Recent
        Monitor-->>Agent: Health Status: OK
    end
```

### Real-time Health Monitoring

```mermaid
graph LR
    subgraph "Data Collection"
        M1[Operation Times]
        M2[Error Counts]
        M3[Success Rates]
        M4[Circuit States]
    end
    
    subgraph "Analysis Engine"
        A1[Trend Analysis]
        A2[Anomaly Detection]
        A3[Threshold Checks]
    end
    
    subgraph "Action Triggers"
        T1[Alert Generation]
        T2[Circuit Trip]
        T3[Recovery Initiation]
    end
    
    M1 --> A1
    M2 --> A2
    M3 --> A3
    M4 --> A2
    
    A1 --> T1
    A2 --> T2
    A3 --> T3
```

## WebSocket Event Flow

The system emits comprehensive WebSocket events for real-time monitoring, fully compliant with the critical agent events required for substantive chat value:

### Critical Business Value Events (Per CLAUDE.md Section 6)

These events MUST be sent during agent execution to enable meaningful AI interactions:

1. **agent_started** - User sees agent began processing their problem
2. **agent_thinking** - Real-time reasoning visibility (shows AI is working on valuable solutions)
3. **tool_executing** - Tool usage transparency (demonstrates problem-solving approach)
4. **tool_completed** - Tool results display (delivers actionable insights)
5. **agent_completed** - User knows when valuable response is ready

### Reliability-Specific Events

In addition to the critical agent events, the reliability system emits these monitoring events:

```mermaid
sequenceDiagram
    participant Client
    participant WebSocket
    participant Bridge as AgentWebSocketBridge
    participant ReliabilityMgr as Reliability Manager
    participant Agent
    
    Client->>WebSocket: Connect
    
    Note over Bridge: Bridge ensures critical event delivery
    
    Agent->>ReliabilityMgr: Execute Operation
    ReliabilityMgr->>Bridge: agent_started
    Bridge->>WebSocket: ensure_event_delivery()
    WebSocket->>Client: {"type": "agent_started"}
    
    ReliabilityMgr->>Bridge: agent_thinking
    Bridge->>WebSocket: ensure_event_delivery()
    WebSocket->>Client: {"type": "agent_thinking", "content": "..."}
    
    loop Tool Execution
        ReliabilityMgr->>Bridge: tool_executing
        Bridge->>WebSocket: ensure_event_delivery()
        WebSocket->>Client: {"type": "tool_executing", "tool": "..."}
        
        ReliabilityMgr->>Bridge: tool_completed
        Bridge->>WebSocket: ensure_event_delivery()
        WebSocket->>Client: {"type": "tool_completed", "result": "..."}
    end
    
    loop Retry Attempts (if needed)
        ReliabilityMgr->>Bridge: retry_attempt
        Bridge->>WebSocket: with retry & backoff
        WebSocket->>Client: {"type": "retry_attempt", "attempt": n}
    end
    
    alt Success
        ReliabilityMgr->>Bridge: agent_completed
        Bridge->>WebSocket: ensure_event_delivery()
        WebSocket->>Client: {"type": "agent_completed", "response": "..."}
    else Failure with Recovery
        ReliabilityMgr->>Bridge: reliability_failure
        Bridge->>WebSocket: with fallback
        WebSocket->>Client: {"type": "reliability_failure", "fallback": true}
    end
    
    alt Circuit Breaker Trip
        ReliabilityMgr->>Bridge: circuit_breaker_opened
        Bridge->>WebSocket: immediate notification
        WebSocket->>Client: {"type": "circuit_breaker_opened"}
    end
    
    alt Health Degradation
        ReliabilityMgr->>Bridge: health_degraded  
        Bridge->>WebSocket: health status update
        WebSocket->>Client: {"type": "health_degraded", "score": ...}
    end
```

### Event Delivery Guarantees

Per the WebSocket-Agent Integration Critical learnings (SPEC/learnings/websocket_agent_integration_critical.xml):

- **Idempotent delivery**: Events can be retried safely without duplication
- **Retry with backoff**: 3 attempts max, 100ms base delay, 500ms total timeout
- **Bridge coordination**: AgentWebSocketBridge ensures critical events are delivered
- **Graceful degradation**: Agent processing continues even if WebSocket delivery fails

## Retry Strategies

The system implements multiple retry strategies optimized for different scenarios:

```mermaid
graph TD
    subgraph "Retry Strategy Selection"
        Op[Operation Type]
        
        Op -->|Database| DBRetry[Database Retry<br/>Max: 5, Base: 0.5s<br/>Strategy: Exponential]
        Op -->|LLM| LLMRetry[LLM Retry<br/>Max: 4, Base: 2.0s<br/>Strategy: Exponential]
        Op -->|Agent| AgentRetry[Agent Retry<br/>Max: 3, Base: 1.0s<br/>Strategy: Exponential]
        Op -->|API| APIRetry[API Retry<br/>Max: 3, Base: 0.5s<br/>Strategy: Linear]
    end
    
    subgraph "Backoff Calculation"
        DBRetry --> Calc[delay = base * 2^attempt]
        LLMRetry --> Calc
        AgentRetry --> Calc
        APIRetry --> CalcLinear[delay = base * attempt]
    end
    
    subgraph "Jitter Application"
        Calc --> Jitter[+/- 20% Random Jitter]
        CalcLinear --> Jitter
    end
    
    Jitter --> Execute[Execute with Delay]
```

## Circuit Breaker Pattern

```mermaid
stateDiagram-v2
    [*] --> Closed: Initial State
    
    Closed --> Closed: Success
    Closed --> Open: Failure Threshold Exceeded
    
    Open --> HalfOpen: Recovery Timeout Expired
    Open --> Open: Requests Rejected
    
    HalfOpen --> Closed: Success
    HalfOpen --> Open: Failure
    
    note right of Open
        All requests fail fast
        No load on failing service
    end note
    
    note right of HalfOpen
        Limited requests allowed
        Testing if service recovered
    end note
    
    note right of Closed
        Normal operation
        Tracking failures
    end note
```

## Error Classification and Handling

```mermaid
flowchart TB
    Error[Error Occurred]
    
    Error --> Classify{Classify Error}
    
    Classify -->|Transient| Retryable[Retryable Errors]
    Classify -->|Permanent| NonRetryable[Non-Retryable Errors]
    Classify -->|Critical| Fatal[Fatal Errors]
    
    Retryable --> R1[ConnectionError]
    Retryable --> R2[TimeoutError]
    Retryable --> R3[OSError]
    Retryable --> R4[RuntimeError]
    
    NonRetryable --> N1[ValueError]
    NonRetryable --> N2[TypeError]
    NonRetryable --> N3[AttributeError]
    NonRetryable --> N4[ImportError]
    
    Fatal --> F1[SystemExit]
    Fatal --> F2[KeyboardInterrupt]
    Fatal --> F3[OutOfMemoryError]
    
    R1 --> RetryLogic[Apply Retry Logic]
    R2 --> RetryLogic
    R3 --> RetryLogic
    R4 --> RetryLogic
    
    N1 --> ImmediateFail[Fail Immediately]
    N2 --> ImmediateFail
    N3 --> ImmediateFail
    N4 --> ImmediateFail
    
    F1 --> Shutdown[System Shutdown]
    F2 --> Shutdown
    F3 --> Shutdown
```

## Health Score Algorithm

The health score is calculated using a weighted algorithm that considers multiple factors:

```python
health_score = base_success_rate
              - (recent_errors * 0.1)  # Max penalty: 0.5
              - (avg_response_time_penalty)  # Max penalty: 0.3
              - (circuit_breaker_penalty)  # Open: 0.4, Half-open: 0.2
              - (consecutive_failures * 0.1)  # Max penalty: 0.3
```

```mermaid
pie title Health Score Components
    "Success Rate" : 50
    "Error Penalty" : 20
    "Response Time" : 15
    "Circuit Breaker" : 10
    "Consecutive Failures" : 5
```

## Usage Examples

### Basic Agent with Reliability

```python
from netra_backend.app.core.agent_reliability_mixin import AgentReliabilityMixin

class MyAgent(AgentReliabilityMixin):
    def __init__(self):
        super().__init__()
        self.name = "MyAgent"
        
    async def execute(self, request):
        # Operation automatically wrapped with reliability
        return await self.execute_with_reliability(
            operation=lambda: self._process_request(request),
            operation_name="process_request",
            context={"request_id": request.id}
        )
```

### Custom Recovery Strategy

```python
async def custom_llm_recovery(error: Exception, context: dict):
    # Try alternate LLM provider
    if "primary_failed" in str(error):
        return await use_fallback_llm(context)
    return None

agent.register_recovery_strategy("llm_call", custom_llm_recovery)
```

### Health Monitoring

```python
# Get comprehensive health status
health_status = agent.get_comprehensive_health_status()
print(f"Health: {health_status.overall_health}")
print(f"Status: {health_status.status}")
print(f"Recent Errors: {health_status.recent_errors}")

# Perform health check
if agent.should_perform_health_check():
    status = await agent.perform_health_check()
```

## Performance Considerations

1. **Health Check Intervals**: Default 60 seconds, configurable per agent
2. **History Limits**: 
   - Error history: 100 entries
   - Operation times: 50 entries
   - Execution history: 100 entries
3. **Circuit Breaker Thresholds**:
   - Database: 5 failures
   - LLM: 3 failures
   - API: 3 failures
4. **Timeout Defaults**:
   - Database: 60 seconds
   - LLM: 300 seconds
   - Agent: 120 seconds

## Best Practices

1. **Always inherit from AgentReliabilityMixin** for new agents
2. **Register custom recovery strategies** for domain-specific failures
3. **Monitor health scores** and set alerts for degradation
4. **Configure retry policies** based on operation characteristics
5. **Use WebSocket events** for real-time monitoring dashboards
6. **Implement graceful fallbacks** for critical operations
7. **Review error history** regularly to identify patterns
8. **Tune circuit breaker thresholds** based on service SLAs

## Troubleshooting

### Common Issues and Solutions

| Issue | Symptom | Solution |
|-------|---------|----------|
| Agent marked as dead | No heartbeat for >10s | Check execution tracker, verify agent loop is running |
| Circuit breaker stuck open | All requests failing fast | Check recovery timeout, manually reset if needed |
| High error rate | Health score < 0.5 | Review error history, check for systemic issues |
| Slow recovery | Degraded performance after errors | Adjust recovery timeout and retry delays |
| Memory growth | Increasing memory usage | Check history limits, ensure cleanup is running |

## System Integration

The reliability and health monitoring system integrates with:

- **WebSocket Manager**: Real-time event streaming
- **Execution Tracker**: Agent lifecycle monitoring  
- **Unified Error Handler**: Centralized error processing
- **Metrics System**: Performance and reliability metrics
- **Alert System**: Proactive issue notification

## Compliance with Recent Updates

### WebSocket Event Emission Compliance

The system is fully compliant with recent WebSocket event emission requirements:

1. **Critical Agent Events (CLAUDE.md Section 6.1)**:
   - ✅ `agent_started` - Emitted when agent begins processing
   - ✅ `agent_thinking` - Real-time reasoning visibility 
   - ✅ `tool_executing` - Tool usage transparency
   - ✅ `tool_completed` - Tool results display
   - ✅ `agent_completed` - Final response ready notification

2. **AgentWebSocketBridge Integration**:
   - ✅ Uses `ensure_event_delivery()` for guaranteed delivery
   - ✅ Implements retry with exponential backoff
   - ✅ Provides idempotent operations
   - ✅ Supports graceful degradation

3. **Business Value Preservation**:
   - ✅ Enables substantive chat interactions (90% of business value)
   - ✅ Provides user transparency into AI processing
   - ✅ Maintains user trust through visibility
   - ✅ Supports real-time monitoring dashboards

4. **Mission Critical Test Coverage**:
   - ✅ Validated by `test_websocket_agent_events_suite.py`
   - ✅ Uses real WebSocket connections (no mocks)
   - ✅ Tests all critical event flows
   - ✅ Blocks deployment on failure

### Integration Points Compliance

Per `websocket_agent_integration_critical.xml`:

- **AgentRegistry.set_websocket_manager()**: ✅ Enhances tool dispatcher
- **ExecutionEngine**: ✅ Has WebSocketNotifier initialized  
- **EnhancedToolExecutionEngine**: ✅ Wraps tool execution
- **UnifiedReliabilityManager**: ✅ Emits reliability events

## Summary

The Agent Reliability and Health Monitor system provides:

- **Comprehensive health monitoring** with multi-factor scoring
- **Intelligent retry mechanisms** with configurable strategies
- **Circuit breaker protection** for fault isolation
- **Automated recovery** with custom strategies
- **Real-time observability** through WebSocket events
- **Death detection** and agent lifecycle management
- **Performance tracking** and trend analysis
- **Full compliance** with WebSocket event emission requirements

This layered approach ensures agents remain resilient, observable, and maintainable while providing clear insights into system health and performance. The system fully supports the critical business value of substantive AI chat interactions through reliable WebSocket event delivery.